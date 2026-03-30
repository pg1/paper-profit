"""
TradingBot — orchestrates data fetching, signal generation, and order routing.
"""

import sys
import os
import logging
from sqlalchemy.orm import Session

# Add the parent directory to Python path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import get_session
from storage.repositories import RepositoryFactory

# Import the new modules
from jobs.trading_bot.instrument_discovery import InstrumentDiscovery
from jobs.trading_bot.data_collector import DataCollector
from jobs.trading_bot.strategy_signal import StrategySignal
from jobs.trading_bot.portfolio_manager import PortfolioManager
from jobs.trading_bot.risk_manager import RiskManager
from jobs.trading_bot.execution_manager import ExecutionManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress SQLAlchemy engine INFO logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


class TradingBot:
    """Trading bot that runs continuously and executes trades based on strategies"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo_factory = RepositoryFactory(db)
        
        # Initialize all modules
        self.instrument_discovery = InstrumentDiscovery(db, self.repo_factory)
        self.data_collector = DataCollector(db, self.repo_factory)
        self.strategy_signal = StrategySignal(db, self.repo_factory)
        self.portfolio_manager = PortfolioManager(db, self.repo_factory)
        self.risk_manager = RiskManager(db, self.repo_factory)
        self.execution_manager = ExecutionManager(db, self.repo_factory)
    
# ── Start bot     
    def run(self):
        """Main trading bot execution loop"""
        logger.info("Starting trading bot...")
        
        try:
            # Get all active accounts with strategies
            active_accounts = self.portfolio_manager.get_active_accounts_with_strategies()
            
            if not active_accounts:
                logger.info("No active accounts with strategies found.")
                return
            
            logger.info(f"Found {len(active_accounts)} active accounts with strategies.")
            
            # Process each account
            for account in active_accounts:
                try:
                    self._process_account(account)
                except Exception as e:
                    logger.error(f"Error processing account {account.account_id}: {str(e)}")
                    self.repo_factory.system_logs.log_error(
                        module="trading_bot",
                        message=f"Error processing account {account.account_id}",
                        details=str(e)
                    )
            
            logger.info("Trading bot cycle completed.")
            
        except Exception as e:
            logger.error(f"Error in trading bot: {str(e)}")
            raise
    
# ── Process each account which has strategy 
    def _process_account(self, account):
        """Process trading for a single account"""
        logger.info(f"Processing account: {account.account_id}")
        
        try:
            # Get the strategy for this account
            strategy = self.portfolio_manager.get_account_strategy(account)
        except ValueError as e:
            logger.warning(str(e))
            return
        
        # Parse strategy parameters
        strategy_params = self.strategy_signal.parse_strategy_parameters(strategy)

        # Get stock list from input
        stock_list = self.instrument_discovery.get_stock_list(strategy)

        #if list is empty try from stategy parameters
        if not stock_list:
            stock_list = self.instrument_discovery.get_stocks_by_universe(strategy)
 
        if not stock_list:
            logger.warning(f"No stock list found for strategy {strategy.name}")
            return
 
        logger.info(f"Strategy: {strategy.name}, Stocks: {len(stock_list)}, Account: {account.account_id}")
        
        #Add stocks to list in current account
        current_positions = self.portfolio_manager.get_account_positions(account.account_id)
        
        # Add holding stocks to the stock list
        holding_stocks = list(current_positions.keys())
        if holding_stocks:
            # Combine strategy stocks with holding stocks, removing duplicates
            combined_stocks = list(set(stock_list + holding_stocks))
            logger.info(f"Added {len(holding_stocks)} holding stocks to stock list. Total stocks: {len(combined_stocks)}")
            stock_list = combined_stocks

        # Process each stock in the strategy
        for symbol in stock_list:
            try:
                self._process_stock(account, strategy, symbol, strategy_params, current_positions)
            except Exception as e:
                logger.error(f"Error processing stock {symbol} for account {account.account_id}: {str(e)}")

# ── For each stock collect data and generate signal    
    def _process_stock(self, account, strategy, symbol, strategy_params, current_positions):
        """Process trading logic for a single stock"""
        
        # Get or create instrument
        instrument = self.portfolio_manager.get_or_create_instrument(symbol)
        
        # Get current market data and technical indicators
        #market_data = self.data_collector.get_latest_market_data(instrument.id)
        market_data = []
        if not market_data:
            logger.warning(f"No market data available for {symbol}")
            #return
        
        # Get technical indicators
        #indicators = self.data_collector.get_technical_indicators(instrument.id)

        # Get quantitative data
        #quantitative_data = self.data_collector.collect_quantitative_data(instrument.id)
        
        indicators = []

        # Generate trading signal
        signal = self.strategy_signal.generate_trading_signal(
            account, strategy, instrument, market_data, indicators, strategy_params
        )
        
        # Log signal
        self.execution_manager.log_trading_signal(instrument, strategy, signal, indicators)

        if signal and signal['action'] != 'HOLD':
            # Execute the trade
            self._execute_trade_with_risk_management(
                account, strategy, instrument, signal, strategy_params, current_positions, indicators
            )
        
# ── Try to execute trade                 
    def _execute_trade_with_risk_management(self, account, strategy, instrument, signal, 
                                           strategy_params, current_positions, indicators):
        """Execute a trade with risk management checks"""
        
        action = signal['action']
        symbol = instrument.symbol
        
        if action == 'BUY':
            # Check if we already have a position
            if self.risk_manager.check_existing_position(symbol, current_positions):
                return
            
            # Check maximum positions limit
            if self.risk_manager.check_max_positions_limit(
                current_positions, strategy_params.get('max_positions', 10)
            ):
                return
            
            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                account, signal['price'], strategy_params
            )

            if position_size <= 0:
                logger.info(f"Insufficient funds for {symbol} BUY order")
                return
            
            # Add quantity to signal for execution
            signal['quantity'] = position_size
           
            # Execute BUY order
            self.execution_manager.execute_buy_order(
                account, strategy, instrument, signal, strategy_params, current_positions, indicators
            )
            
        elif action == 'SELL':
            # Check if we have a position to sell
            if not self.risk_manager.check_position_to_sell(symbol, current_positions):
                return
            
            # Get sell quantity
            sell_quantity = self.risk_manager.get_sell_quantity(symbol, current_positions)
            
            # Add quantity to signal for execution
            signal['quantity'] = sell_quantity
            
            # Execute SELL order
            self.execution_manager.execute_sell_order(
                account, strategy, instrument, signal, strategy_params, current_positions, indicators
            )


def run():
    """Main function to run the trading bot"""
    logger.info("Starting trading bot job...")
    
    # Get database session directly
    db: Session = get_session()
    
    try:
        bot = TradingBot(db)
        bot.run()
    except Exception as e:
        logger.error(f"Error in trading bot job: {str(e)}")
        raise
    finally:
        # Close the session properly
        db.close()


if __name__ == "__main__":
    run()