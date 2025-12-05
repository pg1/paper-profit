import sys
import os
import json
import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging
from typing import List, Dict, Any, Optional

# Add the parent directory to Python path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import get_session
from storage.repositories import RepositoryFactory
from storage.models import Account, Strategy, Order, Position, TradingSignal
from octopus.data_providers.yahoo_finance import YahooFinanceService
from analysis.technical_functions import TechnicalFunctions
from analysis.fundamental_functions import FundamentalFunctions

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
        self.yahoo_service = YahooFinanceService(db)
        self.technical_functions = TechnicalFunctions(db)
        self.fundamental_functions = FundamentalFunctions(db)
        
    def run(self):
        """Main trading bot execution loop"""
        logger.info("Starting trading bot...")
        
        try:
            # Get all active accounts with strategies
            active_accounts = self._get_active_accounts_with_strategies()
            
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
    
    def _get_active_accounts_with_strategies(self) -> List[Account]:
        """Get all active accounts that have strategies assigned"""
        accounts = self.repo_factory.accounts.get_all()
        return [acc for acc in accounts if acc.is_active and acc.strategy_id and acc.status == 'active']
    
    def _process_account(self, account: Account):
        """Process trading for a single account"""
        logger.info(f"Processing account: {account.account_id}")
        
        # Get the strategy for this account
        strategy = self.repo_factory.strategies.get_by_id(account.strategy_id)
        if not strategy or not strategy.is_active:
            logger.warning(f"Strategy {account.strategy_id} not found or inactive for account {account.account_id}")
            return
        
        # Parse strategy parameters
        strategy_params = self._parse_strategy_parameters(strategy)
        
        # Get stock list for this strategy
        stock_list = self._get_stock_list(strategy)
        if not stock_list:
            logger.warning(f"No stock list found for strategy {strategy.name}")
            return
        
        logger.info(f"Strategy: {strategy.name}, Stocks: {len(stock_list)}, Account: {account.account_id}")
        
        # Get current positions for this account
        #TODO: Figure out if we need to sell
        current_positions = self._get_account_positions(account.account_id)
        
        # Process each stock in the strategy
        for symbol in stock_list:
            try:
                self._process_stock(account, strategy, symbol, strategy_params, current_positions)
            except Exception as e:
                logger.error(f"Error processing stock {symbol} for account {account.account_id}: {str(e)}")
    
    def _parse_strategy_parameters(self, strategy: Strategy) -> Dict[str, Any]:
        """Parse strategy parameters from JSON or text fields"""
        params = {}
        
        # Try to parse from parameters field (could be dict or JSON string)
        if strategy.parameters:
            if isinstance(strategy.parameters, dict):
                # Already a dictionary
                params = strategy.parameters
            else:
                # Try to parse as JSON string
                try:
                    params = json.loads(str(strategy.parameters))
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Could not parse parameters for strategy {strategy.name}")
        
        # Try to parse from parameters_json text field
        if strategy.parameters_json:
            try:
                parsed_json = json.loads(str(strategy.parameters_json))
                if isinstance(parsed_json, dict):
                    params.update(parsed_json)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Could not parse parameters_json for strategy {strategy.name}")
        
        # Set default values for required parameters
        defaults = {
            'max_position_size_percent': 10.0,  # Max 10% of account per position
            'max_portfolio_risk_percent': 25.0,  # Max 25% of account at risk
            'stop_loss_percent': 5.0,  # 5% stop loss
            'take_profit_percent': 15.0,  # 15% take profit
            'rsi_oversold': 30.0,  # RSI oversold threshold
            'rsi_overbought': 70.0,  # RSI overbought threshold
            'min_volume': 1000000,  # Minimum daily volume
            'max_positions': 10,  # Maximum number of positions
        }
        
        for key, value in defaults.items():
            if key not in params:
                params[key] = value
        
        return params
    
    def _get_stock_list(self, strategy: Strategy) -> List[str]:
        """Get stock list from strategy - supports AI-generated lists"""
        # Check if strategy uses AI for stock list generation
        if strategy.stock_list_mode == 'AI' and strategy.stock_list_ai_prompt:
            logger.info(f"Generating AI stock list for strategy: {strategy.name}")
            stock_list = self._generate_ai_stock_list(strategy)
            
            # Save the generated list back to the database
            if stock_list:
                self._save_generated_stock_list(strategy, stock_list)
                return stock_list
            else:
                logger.warning(f"Failed to generate AI stock list for strategy: {strategy.name}")
                # Fall back to existing stock list if AI generation fails
                if strategy.stock_list:
                    logger.info(f"Using existing stock list as fallback for strategy: {strategy.name}")
        
        # Parse existing stock list (could be comma-separated, newline-separated, or JSON array)
        if not strategy.stock_list:
            return []
        
        stock_list = []
        
        # Try JSON first
        try:
            stocks_json = json.loads(strategy.stock_list)
            if isinstance(stocks_json, list):
                stock_list = [str(s).strip().upper() for s in stocks_json if s]
        except json.JSONDecodeError:
            # Try comma-separated
            if ',' in strategy.stock_list:
                stock_list = [s.strip().upper() for s in strategy.stock_list.split(',') if s.strip()]
            else:
                # Try newline-separated
                stock_list = [s.strip().upper() for s in strategy.stock_list.split('\n') if s.strip()]
        
        return stock_list
    
    def _generate_ai_stock_list(self, strategy: Strategy) -> List[str]:
        """Generate stock list using AI based on the strategy's AI prompt"""
        try:
            # Get AI service based on strategy parameters or default
            ai_platform = 'deepseek'  # Default AI platform
            if strategy.parameters and isinstance(strategy.parameters, dict):
                ai_platform = strategy.parameters.get('ai_platform', 'deepseek')
            elif strategy.parameters_json:
                try:
                    params = json.loads(str(strategy.parameters_json))
                    ai_platform = params.get('ai_platform', 'deepseek')
                except:
                    pass
            
            # Use the AI prompt from the strategy
            ai_prompt = strategy.stock_list_ai_prompt
            if not ai_prompt:
                logger.warning(f"No AI prompt found for strategy {strategy.name}")
                return []
            
            # Check cache first
            cache_key = f"ai_stock_list_cache_{hash(ai_prompt)}_{ai_platform}"
            cached_result = self._get_cached_stock_list(cache_key)
            if cached_result is not None:
                logger.info(f"Using cached AI stock list for strategy: {strategy.name}")
                return cached_result
            
            logger.info(f"Generating AI stock list for strategy: {strategy.name} using {ai_platform}")
            logger.info(f"AI prompt: {ai_prompt[:200]}...")
            
            # Call AI service to generate stock list
            stock_list = self._call_ai_service_for_stock_list(ai_platform, ai_prompt)
            
            if stock_list:
                # Cache the result
                self._cache_stock_list(cache_key, stock_list)
                logger.info(f"Generated AI stock list with {len(stock_list)} stocks: {stock_list}")
                return stock_list
            else:
                logger.warning(f"Failed to generate AI stock list for strategy: {strategy.name}")
                # Fall back to mock data for now
                return self._get_fallback_stock_list(ai_prompt)
            
        except Exception as e:
            logger.error(f"Error generating AI stock list: {str(e)}")
            return []
    
    def _save_generated_stock_list(self, strategy: Strategy, stock_list: List[str]):
        """Save generated stock list back to the database"""
        try:
            # Convert list to comma-separated string
            stock_list_str = ','.join(stock_list)
            
            # Update the strategy with the new stock list
            update_data = {
                'stock_list': stock_list_str
            }
            
            # Only update if the list has changed
            if strategy.stock_list != stock_list_str:
                self.repo_factory.strategies.update(strategy.id, update_data)
                logger.info(f"Updated stock list for strategy '{strategy.name}' with {len(stock_list)} stocks")
            else:
                logger.info(f"Stock list unchanged for strategy '{strategy.name}'")
                
        except Exception as e:
            logger.error(f"Error saving generated stock list: {str(e)}")
    
    def _get_account_positions(self, account_id: str) -> Dict[str, Position]:
        """Get current positions for an account, indexed by symbol"""
        positions = {}
        account_positions = self.db.query(Position).filter(
            Position.account_id == account_id,
            Position.quantity > 0
        ).all()
        
        for position in account_positions:
            instrument = self.repo_factory.instruments.get_by_id(position.symbol_id)
            if instrument:
                positions[instrument.symbol] = position
        
        return positions
    
    def _process_stock(self, account: Account, strategy: Strategy, symbol: str, 
                      strategy_params: Dict[str, Any], current_positions: Dict[str, Position]):
        """Process trading logic for a single stock"""
        
        # Get or create instrument
        instrument = self.repo_factory.instruments.get_by_symbol(symbol)
        if not instrument:
            logger.warning(f"Instrument {symbol} not found, creating new instrument")
            instrument = self.repo_factory.instruments.create({
                'symbol': symbol,
                'name': symbol,
                'currency': 'USD',
                'is_active': True
            })
        
        # Get current market data and technical indicators
        market_data = self._get_latest_market_data(instrument.id)
        if not market_data:
            logger.warning(f"No market data available for {symbol}")
            return
        
        # Get technical indicators
        indicators = self._get_technical_indicators(instrument.id)
        
        # Generate trading signal
        signal = self._generate_trading_signal(account, strategy, instrument, market_data, indicators, strategy_params)
        
        if signal and signal['action'] != 'HOLD':
            # Execute the trade
            self._execute_trade(account, strategy, instrument, signal, strategy_params, current_positions)
        else:
            self._log_hold_signal(account, strategy, instrument, signal)
    
    def _get_latest_market_data(self, symbol_id: int) -> Optional[Dict[str, Any]]:
        """Get latest market data for a symbol"""
        try:
            market_data = self.repo_factory.market_data.get_latest(symbol_id, '1day', limit=1)
            if market_data:
                latest = market_data[0]
                return {
                    'timestamp': latest.timestamp,
                    'open': float(latest.open),
                    'high': float(latest.high),
                    'low': float(latest.low),
                    'close': float(latest.close),
                    'volume': latest.volume,
                    'vwap': float(latest.vwap) if latest.vwap else None
                }
        except Exception as e:
            logger.error(f"Error getting market data for symbol_id {symbol_id}: {str(e)}")
        
        # Fallback: Try to fetch current price directly from Yahoo Finance
        try:
            instrument = self.repo_factory.instruments.get_by_id(symbol_id)
            if instrument:
                logger.info(f"Fetching current price for {instrument.symbol} from Yahoo Finance...")
                price_data = self.yahoo_service.fetch_current_price(instrument.symbol)
                
                if price_data and 'price' in price_data:
                    current_price = float(price_data['price'])
                    logger.info(f"Fetched current price for {instrument.symbol}: ${current_price:.2f}")
                    
                    # Return mock market data with current price
                    return {
                        'timestamp': datetime.now(),
                        'open': current_price,
                        'high': current_price,
                        'low': current_price,
                        'close': current_price,
                        'volume': 1000000,  # Default volume
                        'vwap': current_price
                    }
        except Exception as e:
            logger.error(f"Error fetching fallback market data for symbol_id {symbol_id}: {str(e)}")
        
        return None
    
    def _get_technical_indicators(self, symbol_id: int) -> Dict[str, Any]:
        """Get latest technical indicators for a symbol using technical analysis module"""
        try:
            # Get instrument symbol
            instrument = self.repo_factory.instruments.get_by_id(symbol_id)
            if not instrument:
                return {}
            
            # Use technical functions module to get indicators
            indicators = self.technical_functions.get_all_technical_indicators(instrument.symbol)
            
            # Also check database for historical signals
            indicators_data = self.db.query(TradingSignal).filter(
                TradingSignal.symbol_id == symbol_id
            ).order_by(TradingSignal.timestamp.desc()).first()
            
            if indicators_data:
                indicators['historical_rsi'] = float(indicators_data.strength) if indicators_data.strength else None
                indicators['historical_timestamp'] = indicators_data.timestamp
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error getting technical indicators for symbol_id {symbol_id}: {str(e)}")
        
        return {}
    
    def _has_fundamental_parameters(self, strategy_params: Dict[str, Any]) -> bool:
        """Check if strategy has fundamental analysis parameters"""
        fundamental_param_keys = [
            'min_quality_score', 'max_pe', 'max_pb', 'min_dividend_yield',
            'max_pe_ratio', 'minimum_roe_percent', 'conviction_score_minimum',
            'preferred_industry_moat', 'sell_on_fundamental_shift',
            'underlying_quality_required', 'narrative_match_required',
            'min_revenue_growth', 'min_eps_growth', 'max_peg',
            'discount_to_intrinsic_value', 'required_margin_of_safety_percent'
        ]
        
        return any(key in strategy_params for key in fundamental_param_keys)
    
    def _generate_trading_signal(self, account: Account, strategy: Strategy, instrument, 
                                market_data: Dict[str, Any], indicators: Dict[str, Any], 
                                strategy_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate trading signal based on strategy and market conditions using TA and FA"""
        
        current_price = market_data['close']
        volume = market_data['volume']
        symbol = instrument.symbol
        
        # Basic volume filter
        if volume < strategy_params.get('min_volume', 1000000):
            return {'action': 'HOLD', 'reason': 'Low volume'}
        
        # Get technical indicators
        rsi = indicators.get('rsi')
        price_trend = indicators.get('price_trend')
        is_overbought = indicators.get('is_overbought')
        is_oversold = indicators.get('is_oversold')
        macd = indicators.get('macd')
        bollinger_bands = indicators.get('bollinger_bands')
        
        # Get fundamental indicators only if strategy has fundamental parameters
        fundamental_params = {}
        quality_score = None
        pe_ratio = None
        meets_quality = None
        meets_valuation = None
        
        if self._has_fundamental_parameters(strategy_params):
            fundamental_params = self.fundamental_functions.get_all_parameters(symbol)
            quality_score = fundamental_params.get('quality_score')
            pe_ratio = fundamental_params.get('pe_ratio')
            meets_quality = fundamental_params.get('meets_quality_requirement')
            meets_valuation = fundamental_params.get('meets_valuation_requirement')
        
        # Calculate composite signal score
        signal_score = 0
        reasons = []
        
        # Technical analysis factors
        if rsi:
            if rsi < strategy_params.get('rsi_oversold', 30.0):
                signal_score += 2
                reasons.append(f'RSI oversold ({rsi:.2f})')
            elif rsi > strategy_params.get('rsi_overbought', 70.0):
                signal_score -= 2
                reasons.append(f'RSI overbought ({rsi:.2f})')
        
        if price_trend == 'BULLISH':
            signal_score += 1
            reasons.append('Bullish price trend')
        elif price_trend == 'BEARISH':
            signal_score -= 1
            reasons.append('Bearish price trend')
        
        if is_oversold:
            signal_score += 1
            reasons.append('Oversold condition')
        if is_overbought:
            signal_score -= 1
            reasons.append('Overbought condition')
        
        # Fundamental analysis factors - only check if parameters exist in strategy
        if quality_score is not None:
            min_quality = strategy_params.get('min_quality_score', 70)
            if quality_score > min_quality:
                signal_score += 1
                reasons.append(f'High quality score ({quality_score})')
        
        if meets_quality is not None and strategy_params.get('underlying_quality_required'):
            if meets_quality:
                signal_score += 1
                reasons.append('Meets quality requirements')
        
        if meets_valuation is not None:
            # Check if any valuation parameters are in strategy
            valuation_params = ['max_pe', 'max_pb', 'max_pe_ratio', 'max_peg', 
                              'discount_to_intrinsic_value', 'required_margin_of_safety_percent']
            if any(param in strategy_params for param in valuation_params):
                if meets_valuation:
                    signal_score += 1
                    reasons.append('Good valuation')
        
        # Check if price is near support/resistance
        is_near_support = indicators.get('is_price_near_support')
        is_near_resistance = indicators.get('is_price_near_resistance')
        
        if is_near_support:
            signal_score += 1
            reasons.append('Price near support level')
        if is_near_resistance:
            signal_score -= 1
            reasons.append('Price near resistance level')
        
        # Generate signal based on composite score
        if signal_score >= 3:
            confidence = min(0.9, signal_score / 10.0 + 0.5)
            return {
                'action': 'BUY',
                'price': current_price,
                'reason': ', '.join(reasons),
                'confidence': confidence,
                'signal_score': signal_score
            }
        elif signal_score <= -3:
            confidence = min(0.9, abs(signal_score) / 10.0 + 0.5)
            return {
                'action': 'SELL',
                'price': current_price,
                'reason': ', '.join(reasons),
                'confidence': confidence,
                'signal_score': signal_score
            }
        else:
            # Default to HOLD if no clear signal
            hold_reason = 'No clear signal'
            if reasons:
                hold_reason = f'Mixed signals: {", ".join(reasons)}'
            return {'action': 'HOLD', 'reason': hold_reason, 'signal_score': signal_score}
    
    def _execute_trade(self, account: Account, strategy: Strategy, instrument, 
                      signal: Dict[str, Any], strategy_params: Dict[str, Any], 
                      current_positions: Dict[str, Position]):
        """Execute a trade based on the signal"""
        
        action = signal['action']
        symbol = instrument.symbol
        
        # Risk management and position sizing
        if action == 'BUY':
            self._execute_buy_order(account, strategy, instrument, signal, strategy_params, current_positions)
        elif action == 'SELL':
            self._execute_sell_order(account, strategy, instrument, signal, strategy_params, current_positions)
        elif action == 'HOLD': #TODO: do we need this here?
            # Log HOLD signals too for tracking
            self._log_hold_signal(account, strategy, instrument, signal)
    
    def _execute_buy_order(self, account: Account, strategy: Strategy, instrument, 
                          signal: Dict[str, Any], strategy_params: Dict[str, Any], 
                          current_positions: Dict[str, Position]):
        """Execute a BUY order with risk management"""
        
        symbol = instrument.symbol
        current_price = signal['price']
        
        # Check if we already have a position
        existing_position = current_positions.get(symbol)
        
        if existing_position:
            logger.info(f"Already have position in {symbol}, skipping BUY")
            return
        
        # Calculate position size
        position_size = self._calculate_position_size(account, current_price, strategy_params)
        
        if position_size <= 0:
            logger.info(f"Insufficient funds for {symbol} BUY order")
            return
        
        # Check maximum positions limit
        if len(current_positions) >= strategy_params.get('max_positions', 10):
            logger.info(f"Maximum positions limit reached for account {account.account_id}")
            return
        
        # Create BUY order
        order_data = {
            'account_id': account.account_id,
            'symbol_id': instrument.id,
            'strategy_id': strategy.id,
            'order_type': 'MARKET',
            'side': 'BUY',
            'quantity': position_size,
            'price': current_price,
            'status': 'PENDING',
            'submitted_at': datetime.now()
        }
        
        try:
            order = self.repo_factory.orders.create(order_data)
            logger.info(f"Created BUY order for {symbol}: {position_size} shares at ${current_price:.2f}")
            
            # Get technical indicators for this symbol to include in signal metadata
            indicators = self._get_technical_indicators(instrument.id)
            
            # Extract key indicators used in decision making
            indicators_used = self._extract_indicators_used(signal, indicators)
            
            # Log the trading signal with detailed metadata
            self.repo_factory.trading_signals.create({
                'symbol_id': instrument.id,
                'strategy_id': strategy.id,
                'timestamp': datetime.now(),
                'signal_type': 'BUY',
                'strength': signal.get('signal_score', 0),
                'price': current_price,
                'confidence': signal.get('confidence', 0.5),
                'indicators_used': json.dumps(indicators_used),
                'reason': signal.get('reason', 'Trading bot signal')
            })
            
        except Exception as e:
            logger.error(f"Error creating BUY order for {symbol}: {str(e)}")
    
    def _execute_sell_order(self, account: Account, strategy: Strategy, instrument, 
                           signal: Dict[str, Any], strategy_params: Dict[str, Any], 
                           current_positions: Dict[str, Position]):
        """Execute a SELL order with risk management"""
        
        symbol = instrument.symbol
        current_price = signal['price']
        
        # Check if we have a position to sell
        existing_position = current_positions.get(symbol)
        
        if not existing_position or existing_position.quantity <= 0:
            logger.info(f"No position to sell for {symbol}")
            return
        
        # Sell the entire position
        sell_quantity = existing_position.quantity
        
        # Create SELL order
        order_data = {
            'account_id': account.account_id,
            'symbol_id': instrument.id,
            'strategy_id': strategy.id,
            'order_type': 'MARKET',
            'side': 'SELL',
            'quantity': sell_quantity,
            'price': current_price,
            'status': 'PENDING',
            'submitted_at': datetime.now()
        }
        
        try:
            order = self.repo_factory.orders.create(order_data)
            logger.info(f"Created SELL order for {symbol}: {sell_quantity} shares at ${current_price:.2f}")
            
            # Get technical indicators for this symbol to include in signal metadata
            indicators = self._get_technical_indicators(instrument.id)
            
            # Extract key indicators used in decision making
            indicators_used = self._extract_indicators_used(signal, indicators)
            
            # Log the trading signal with detailed metadata
            self.repo_factory.trading_signals.create({
                'symbol_id': instrument.id,
                'strategy_id': strategy.id,
                'timestamp': datetime.now(),
                'signal_type': 'SELL',
                'strength': signal.get('signal_score', 0),
                'price': current_price,
                'confidence': signal.get('confidence', 0.5),
                'indicators_used': json.dumps(indicators_used),
                'reason': signal.get('reason', 'Trading bot signal')
            })
            
        except Exception as e:
            logger.error(f"Error creating SELL order for {symbol}: {str(e)}")
    
    def _calculate_position_size(self, account: Account, price: float, 
                                strategy_params: Dict[str, Any]) -> float:
        """Calculate position size based on risk management rules"""
        
        # Calculate maximum position value
        max_position_value = (account.cash_balance * strategy_params.get('max_position_size_percent', 10.0)) / 100.0
        
        # Calculate number of shares
        max_shares = max_position_value / price
        
        # Ensure we don't exceed available cash
        available_shares = account.cash_balance / price
        
        # Use the smaller of the two
        position_shares = min(max_shares, available_shares)
        
        # Round down to whole shares
        position_shares = int(position_shares)
        
        logger.debug(f"Position calculation for account {account.account_id}: "
                    f"cash=${account.cash_balance:.2f}, price=${price:.2f}, "
                    f"max_shares={max_shares:.0f}, final_shares={position_shares}")
        
        return position_shares
    
    def _extract_indicators_used(self, signal: Dict[str, Any], indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key indicators used in decision making for signal metadata"""
        indicators_used = {}
        
        # Extract technical indicators that contributed to the signal
        if 'reason' in signal:
            reason = signal['reason']
            
            # Check which indicators are mentioned in the reason
            indicator_keywords = {
                'rsi': ['RSI', 'rsi'],
                'price_trend': ['price trend', 'trend', 'bullish', 'bearish'],
                'support': ['support', 'near support'],
                'resistance': ['resistance', 'near resistance'],
                'oversold': ['oversold'],
                'overbought': ['overbought'],
                'quality_score': ['quality score', 'quality'],
                'valuation': ['valuation', 'valuation requirement'],
                'volume': ['volume']
            }
            
            for indicator_key, keywords in indicator_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in reason.lower():
                        # Add the actual indicator value if available
                        if indicator_key in indicators:
                            indicators_used[indicator_key] = indicators[indicator_key]
                        else:
                            indicators_used[indicator_key] = 'mentioned_in_reason'
                        break
        
        # Always include signal score and confidence
        indicators_used['signal_score'] = signal.get('signal_score', 0)
        indicators_used['confidence'] = signal.get('confidence', 0.5)
        
        # Include any other relevant indicators from the indicators dict
        important_indicators = ['rsi', 'price_trend', 'is_overbought', 'is_oversold', 
                               'is_price_near_support', 'is_price_near_resistance']
        
        for indicator in important_indicators:
            if indicator in indicators and indicators[indicator] is not None:
                indicators_used[indicator] = indicators[indicator]
        
        # Convert any non-JSON-serializable values to serializable ones
        return self._make_json_serializable(indicators_used)
    
    def _make_json_serializable(self, data: Any) -> Any:
        """Convert data to JSON-serializable format"""
        if isinstance(data, dict):
            return {k: self._make_json_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._make_json_serializable(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(self._make_json_serializable(item) for item in data)
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        elif hasattr(data, 'item'):  # numpy scalar types
            try:
                return data.item()
            except:
                return str(data)
        elif hasattr(data, 'isoformat'):  # datetime objects
            try:
                return data.isoformat()
            except:
                return str(data)
        else:
            # For any other type, convert to string
            return str(data)
    
    def _log_hold_signal(self, account: Account, strategy: Strategy, instrument, signal: Dict[str, Any]):
        """Log HOLD signals to the database for tracking and analysis"""
        try:
            # Get technical indicators for this symbol
            indicators = self._get_technical_indicators(instrument.id)
            
            # Extract key indicators used in decision making
            indicators_used = self._extract_indicators_used(signal, indicators)
            
            # Log the HOLD signal with detailed metadata
            self.repo_factory.trading_signals.create({
                'symbol_id': instrument.id,
                'strategy_id': strategy.id,
                'timestamp': datetime.now(),
                'signal_type': 'HOLD',
                'strength': signal.get('signal_score', 0),
                'price': signal.get('price', 0),
                'confidence': signal.get('confidence', 0.5),
                'indicators_used': json.dumps(indicators_used),
                'reason': signal.get('reason', 'No clear trading signal')
            })
            
            logger.debug(f"Logged HOLD signal for {instrument.symbol}: {signal.get('reason', 'No reason')}")
            
        except Exception as e:
            logger.error(f"Error logging HOLD signal for {instrument.symbol}: {str(e)}")
    
    def _get_cached_stock_list(self, cache_key: str) -> Optional[List[str]]:
        """Get cached stock list from database"""
        try:
            setting = self.repo_factory.settings.get_by_name(cache_key)
            if setting and setting.parameters:
                # Parse cached data
                cache_data = json.loads(setting.parameters)
                cached_at_str = cache_data.get('cached_at')
                stock_list = cache_data.get('stock_list', [])
                
                if cached_at_str and stock_list:
                    cached_at = datetime.fromisoformat(cached_at_str)
                    # Check if cache is still valid (24 hours)
                    if datetime.now() - cached_at < timedelta(hours=24):
                        logger.debug(f"Cache hit for key: {cache_key}")
                        return stock_list
                    else:
                        logger.debug(f"Cache expired for key: {cache_key}")
                else:
                    logger.debug(f"Invalid cache data for key: {cache_key}")
        except Exception as e:
            logger.debug(f"Error reading cache for key {cache_key}: {str(e)}")
        
        return None
    
    def _cache_stock_list(self, cache_key: str, stock_list: List[str]):
        """Cache stock list in database"""
        try:
            cache_data = {
                'stock_list': stock_list,
                'cached_at': datetime.now().isoformat(),
                'cache_key': cache_key
            }
            
            self.repo_factory.settings.upsert(
                name=cache_key,
                parameters=json.dumps(cache_data),
                category='ai_cache',
                is_active=True
            )
            logger.debug(f"Cached stock list for key: {cache_key}")
        except Exception as e:
            logger.error(f"Error caching stock list for key {cache_key}: {str(e)}")
    
    def _call_ai_service_for_stock_list(self, ai_platform: str, ai_prompt: str) -> List[str]:
        """Call AI service to generate stock list from prompt"""
        try:
            # Import and create AI service
            if ai_platform.lower() == 'claude':
                from octopus.ai_platforms.claude import ClaudeService
                ai_service = ClaudeService(self.db)
                # Use Claude's API directly for stock list generation
                response = self._call_claude_for_stock_list(ai_service, ai_prompt)
            elif ai_platform.lower() == 'openai':
                from octopus.ai_platforms.openai import OpenAIService
                ai_service = OpenAIService(self.db)
                # Use OpenAI's API directly for stock list generation
                response = self._call_openai_for_stock_list(ai_service, ai_prompt)
            else:  # Default to deepseek
                from octopus.ai_platforms.deepseek import DeepSeekService
                ai_service = DeepSeekService(self.db)
                # Use DeepSeek's API directly for stock list generation
                response = self._call_deepseek_for_stock_list(ai_service, ai_prompt)
            
            if response:
                # Parse the AI response to extract stock symbols
                stock_list = self._parse_ai_response_for_stocks(response)
                return stock_list
            else:
                logger.warning(f"No response from AI service {ai_platform}")
                return []
                
        except Exception as e:
            logger.error(f"Error calling AI service {ai_platform}: {str(e)}")
            return []
    
    def _call_claude_for_stock_list(self, ai_service, ai_prompt: str) -> Optional[str]:
        """Call Claude API for stock list generation"""
        try:
            # Create a prompt specifically for stock list generation
            system_prompt = """You are a financial analyst. Given an investment strategy prompt, 
            provide a list of stock symbols (tickers) that match the criteria. 
            Return ONLY a comma-separated list of stock symbols, nothing else.
            Example: AAPL, MSFT, GOOGL, AMZN, TSLA"""
            
            # Use the AI service's internal API call method
            # Note: This is a simplified approach - in reality we'd need to adapt to Claude's API
            payload = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Based on this investment strategy: {ai_prompt}\n\nProvide a list of stock symbols that match this strategy."
                    }
                ]
            }
            
            # Since ClaudeService doesn't expose _make_api_request, we'll use demo mode or mock
            # For now, return mock response
            logger.info(f"Calling Claude API for stock list (mock implementation)")
            return "AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, JPM, BAC, WFC"
            
        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            return None
    
    def _call_openai_for_stock_list(self, ai_service, ai_prompt: str) -> Optional[str]:
        """Call OpenAI API for stock list generation"""
        try:
            # Create a prompt specifically for stock list generation
            system_prompt = """You are a financial analyst. Given an investment strategy prompt, 
            provide a list of stock symbols (tickers) that match the criteria. 
            Return ONLY a comma-separated list of stock symbols, nothing else.
            Example: AAPL, MSFT, GOOGL, AMZN, TSLA"""
            
            # Use the AI service's internal API call method
            # Note: This is a simplified approach - in reality we'd need to adapt to OpenAI's API
            payload = {
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Based on this investment strategy: {ai_prompt}\n\nProvide a list of stock symbols that match this strategy."
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 500
            }
            
            # Since OpenAIService doesn't expose _make_api_request, we'll use demo mode or mock
            # For now, return mock response
            logger.info(f"Calling OpenAI API for stock list (mock implementation)")
            return "AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, JPM, BAC, WFC"
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return None
    
    def _call_deepseek_for_stock_list(self, ai_service, ai_prompt: str) -> Optional[str]:
        """Call DeepSeek API for stock list generation"""
        try:
            # Create a prompt specifically for stock list generation
            system_prompt = """You are a financial analyst. Given an investment strategy prompt, 
            provide a list of stock symbols (tickers) that match the criteria. 
            Return ONLY a comma-separated list of stock symbols, nothing else.
            Example: AAPL, MSFT, GOOGL, AMZN, TSLA"""
            
            # Use the AI service's internal API call method
            # Note: This is a simplified approach - in reality we'd need to adapt to DeepSeek's API
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Based on this investment strategy: {ai_prompt}\n\nProvide a list of stock symbols that match this strategy."
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 500
            }
            
            # Since DeepSeekService doesn't expose _make_api_request, we'll use demo mode or mock
            # For now, return mock response
            logger.info(f"Calling DeepSeek API for stock list (mock implementation)")
            return "AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, JPM, BAC, WFC"
            
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {str(e)}")
            return None
    
    def _parse_ai_response_for_stocks(self, ai_response: str) -> List[str]:
        """Parse AI response to extract stock symbols"""
        try:
            # Clean the response
            response = ai_response.strip()
            
            # Remove any markdown formatting or extra text
            # Look for patterns like "AAPL, MSFT, GOOGL" or "Symbols: AAPL, MSFT, GOOGL"
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                # Remove common prefixes
                prefixes = ['Symbols:', 'Stocks:', 'Tickers:', 'Recommendations:', '•', '-', '*']
                for prefix in prefixes:
                    if line.startswith(prefix):
                        line = line[len(prefix):].strip()
                
                # Check if line contains stock symbols (uppercase letters, possibly with dots)
                if any(c.isalpha() for c in line) and any(c.isupper() for c in line):
                    # Split by common delimiters
                    for delimiter in [',', ';', '|', ' ', '\t']:
                        if delimiter in line:
                            symbols = [s.strip().upper() for s in line.split(delimiter) if s.strip()]
                            # Filter valid stock symbols (1-5 uppercase letters, possibly with dots)
                            valid_symbols = []
                            for symbol in symbols:
                                # Remove any parentheses or extra characters
                                symbol = symbol.split('(')[0].split('[')[0].strip()
                                # Check if it looks like a stock symbol
                                if 1 <= len(symbol) <= 5 and symbol.isalpha() and symbol.isupper():
                                    valid_symbols.append(symbol)
                            
                            if valid_symbols:
                                logger.debug(f"Parsed stock symbols from AI response: {valid_symbols}")
                                return valid_symbols
            
            # If no pattern matched, try to extract all uppercase words
            import re
            potential_symbols = re.findall(r'\b[A-Z]{1,5}\b', response)
            if potential_symbols:
                # Filter out common words that aren't stock symbols
                common_words = {'THE', 'AND', 'FOR', 'WITH', 'THIS', 'THAT', 'FROM', 'HAVE', 'WILL', 'ARE', 'NOT'}
                stock_symbols = [s for s in potential_symbols if s not in common_words]
                if stock_symbols:
                    logger.debug(f"Extracted stock symbols using regex: {stock_symbols}")
                    return stock_symbols
            
            logger.warning(f"Could not parse stock symbols from AI response: {response[:100]}...")
            return []
            
        except Exception as e:
            logger.error(f"Error parsing AI response for stocks: {str(e)}")
            return []
    
    def _get_fallback_stock_list(self, ai_prompt: str) -> List[str]:
        """Get fallback stock list based on prompt keywords (mock implementation)"""
        # This is the original mock implementation
        ai_prompt_lower = ai_prompt.lower()
        
        if 'tech' in ai_prompt_lower or 'technology' in ai_prompt_lower:
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META']
        elif 'finance' in ai_prompt_lower or 'bank' in ai_prompt_lower:
            return ['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS']
        elif 'health' in ai_prompt_lower or 'pharma' in ai_prompt_lower:
            return ['JNJ', 'PFE', 'MRK', 'ABT', 'UNH', 'LLY']
        elif 'energy' in ai_prompt_lower or 'oil' in ai_prompt_lower:
            return ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC']
        elif 'consumer' in ai_prompt_lower or 'retail' in ai_prompt_lower:
            return ['WMT', 'TGT', 'COST', 'HD', 'LOW', 'AMZN']
        elif 'industrial' in ai_prompt_lower:
            return ['CAT', 'BA', 'HON', 'GE', 'MMM', 'UTX']
        else:
            # Default to some popular stocks
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'JNJ']


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
