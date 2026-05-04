"""
TradingBot — orchestrates data fetching, signal generation, and order routing.

Supports two signal generation paths:
1. Scoring-based: Uses TA/FA/sentiment scoring (generate_trading_signal)
2. Condition-based: Uses frontend Entry/Exit conditions (generate_condition_based_signal)
"""

import sys
import os
import math
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

# Add the parent directory to Python path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import get_session
from storage.repositories import RepositoryFactory
from storage.models import Account, Strategy, Instrument, Position

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

        #if list is empty try from strategy parameters
        if not stock_list:
            stock_list = self.instrument_discovery.get_stocks_by_universe(strategy)
 
        if not stock_list:
            logger.warning(f"No stock list found for strategy {strategy.name}")
            return
 
        logger.info(f"Strategy: {strategy.name}, Stocks: {len(stock_list)}, Account: {account.account_id}")
        
        # Get current positions for this account
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

    def _extract_required_indicators(self, strategy_params: Dict[str, Any]) -> List[str]:
        """Extract the list of indicators needed by this strategy.
        
        Analyzes both condition-based (entryConditions/exit rules) and 
        scoring-based strategy parameters to determine which indicators 
        need to be fetched.
        
        Returns:
            List of indicator names (e.g. ['rsi', 'sma_20', 'sma_50'])
        """
        required = set()
        
        # 1. Check entry conditions (condition-based path)
        entry_conditions = strategy_params.get('entryConditions', [])
        for condition in entry_conditions:
            indicator = condition.get('indicator', '').lower()
            if indicator:
                # Map frontend indicator names to our internal names
                indicator_map = {
                    'rsi': 'rsi',
                    'sma': 'sma_20',  # Default period
                    'ema': 'ema_12',  # Default period
                    'close': 'current_price',
                    'volume': 'volume_ratio',
                    'bb_upper': 'bb_upper',
                    'bb_lower': 'bb_lower',
                }
                mapped = indicator_map.get(indicator)
                if mapped:
                    required.add(mapped)
                else:
                    # Try to use the indicator name directly
                    required.add(indicator)
        
        # 2. Check exit rules (condition-based path)
        exit_rules = strategy_params.get('strategy', [])
        for rule in exit_rules:
            if rule.get('type') == 'exit':
                params = rule.get('parameters', {})
                indicator = params.get('indicator', '').lower()
                if indicator:
                    indicator_map = {
                        'rsi': 'rsi',
                        'close': 'current_price',
                        'sma': 'sma_20',
                        'ema': 'ema_12',
                    }
                    mapped = indicator_map.get(indicator)
                    if mapped:
                        required.add(mapped)
                    else:
                        required.add(indicator)
        
        # 3. Check scoring-based parameters
        scoring_indicators = {
            'rsi_oversold': 'rsi',
            'rsi_overbought': 'rsi',
            'min_volume': 'volume_ratio',
            'max_pe': 'pe_ratio',
            'max_pb': 'pb_ratio',
            'max_peg': 'peg_ratio',
            'minimum_roe_percent': 'roe',
            'min_dividend_yield': 'dividend_yield',
            'min_revenue_growth': 'revenue_growth',
            'min_eps_growth': 'eps_growth',
            'min_quality_score': 'quality_score',
        }
        
        for param_key, indicator in scoring_indicators.items():
            value = strategy_params.get(param_key)
            if value is not None and value != '':
                required.add(indicator)
        
        # 4. Always include current_price and basic market data
        required.add('current_price')
        
        logger.debug(f"Required indicators for strategy: {sorted(required)}")
        return list(required)

# ── For each stock collect data and generate signal    
    def _process_stock(self, account, strategy, symbol, strategy_params, current_positions):
        """Process trading logic for a single stock"""
        
        # Get or create instrument
        instrument = self.portfolio_manager.get_or_create_instrument(symbol)
        
        # Get current market data
        market_data = self.data_collector.get_latest_market_data(instrument.id)
        if not market_data:
            logger.warning(f"No market data available for {symbol}")
            return
        
        # Determine which indicators this strategy actually needs
        required_indicators = self._extract_required_indicators(strategy_params)
        
        # Get only the technical indicators needed by this strategy
        indicators = self.data_collector.get_technical_indicators_for_strategy(
            instrument.id, required_indicators
        )
        
        # Check if we have an existing position
        has_position = symbol in current_positions
        position_data = current_positions.get(symbol) if has_position else None
        
        # Determine which signal path to use based on strategy parameters
        has_entry_conditions = bool(strategy_params.get('entryConditions'))
        has_exit_rules = bool(strategy_params.get('strategy'))
        
        if has_entry_conditions or has_exit_rules:
            # ── Condition-based path (from frontend Entry/Exit tabs) ──
            position_info = None
            if position_data:
                position_info = {
                    'average_entry_price': float(position_data.average_entry_price) if position_data.average_entry_price else 0,
                    'quantity': float(position_data.quantity) if position_data.quantity else 0
                }
            
            # Merge technical indicators into market_data so condition evaluation
            # can find indicator values like rsi, sma_20, etc.
            market_data.update(indicators)
            
            signal = self.strategy_signal.generate_condition_based_signal(
                account, strategy, instrument, market_data, strategy_params, position_info
            )
        else:
            # ── Scoring-based path (TA/FA/sentiment scoring) ──
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
            max_positions_raw = strategy_params.get('max_positions', 10)
            try:
                max_positions = int(max_positions_raw) if max_positions_raw != '' else 10
            except (ValueError, TypeError):
                max_positions = 10
            if self.risk_manager.check_max_positions_limit(current_positions, max_positions):
                return
            
            # Validate price before position sizing
            price = signal.get('price', 0)
            if not price or price == '' or (isinstance(price, float) and (math.isnan(price) or math.isinf(price))):
                logger.warning(f"Invalid price ({price}) for {symbol} BUY order, skipping")
                return
            
            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                account, price, strategy_params
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

