import json
import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from storage.repositories import RepositoryFactory
from storage.models import Account, Strategy, Instrument, Position

logger = logging.getLogger(__name__)


class ExecutionManager:
    """Module for executing trades and orders"""
    
    def __init__(self, db: Session, repo_factory: RepositoryFactory):
        self.db = db
        self.repo_factory = repo_factory
    
    def execute_trade(self, account: Account, strategy: Strategy, instrument: Instrument,
                     signal: Dict[str, Any], strategy_params: Dict[str, Any], 
                     current_positions: Dict[str, Position], indicators: Dict[str, Any] = None):
        """Execute a trade based on the signal"""
        
        action = signal['action']
        
        if action == 'BUY':
            self.execute_buy_order(account, strategy, instrument, signal, strategy_params, current_positions, indicators)
        elif action == 'SELL':
            self.execute_sell_order(account, strategy, instrument, signal, strategy_params, current_positions, indicators)
            
    def execute_buy_order(self, account: Account, strategy: Strategy, instrument: Instrument,
                         signal: Dict[str, Any], strategy_params: Dict[str, Any], 
                         current_positions: Dict[str, Position], indicators: Dict[str, Any] = None):
        """Execute a BUY order with risk management"""
        
        symbol = instrument.symbol
        current_price = signal['price']
        
        # Create BUY order
        order_data = {
            'account_id': account.account_id,
            'symbol_id': instrument.id,
            'strategy_id': strategy.id,
            'order_type': 'MARKET',
            'side': 'BUY',
            'quantity': signal.get('quantity', 0),  # Quantity should be calculated by RiskManager
            'price': current_price,
            'status': 'PENDING',
            'submitted_at': datetime.now()
        }
        
        try:
            order = self.repo_factory.orders.create(order_data)
            logger.info(f"Created BUY order for {symbol}: {order_data['quantity']} shares at ${current_price:.2f}")
            
            # Log the trading signal with detailed metadata
            #self.log_trading_signal(instrument, strategy, signal, 'BUY', indicators)
            
        except Exception as e:
            logger.error(f"Error creating BUY order for {symbol}: {str(e)}")
    
    def execute_sell_order(self, account: Account, strategy: Strategy, instrument: Instrument,
                          signal: Dict[str, Any], strategy_params: Dict[str, Any], 
                          current_positions: Dict[str, Position], indicators: Dict[str, Any] = None):
        """Execute a SELL order with risk management"""
        
        symbol = instrument.symbol
        current_price = signal['price']
        
        # Create SELL order
        order_data = {
            'account_id': account.account_id,
            'symbol_id': instrument.id,
            'strategy_id': strategy.id,
            'order_type': 'MARKET',
            'side': 'SELL',
            'quantity': signal.get('quantity', 0),  # Quantity should be provided by RiskManager
            'price': current_price,
            'status': 'PENDING',
            'submitted_at': datetime.now()
        }
        
        try:
            order = self.repo_factory.orders.create(order_data)
            logger.info(f"Created SELL order for {symbol}: {order_data['quantity']} shares at ${current_price:.2f}")
            
            # Log the trading signal with detailed metadata
            #self.log_trading_signal(instrument, strategy, signal, 'SELL', indicators)
            
        except Exception as e:
            logger.error(f"Error creating SELL order for {symbol}: {str(e)}")
    
    def log_trading_signal(self, instrument: Instrument, strategy: Strategy, 
                          signal: Dict[str, Any], 
                          indicators: Dict[str, Any] = None):
        """Log trading signal to the database"""
        try:
            indicators_used = self._extract_indicators_used(signal, indicators)
            
            # Log the trading signal with detailed metadata
            self.repo_factory.trading_signals.create({
                'symbol_id': instrument.id,
                'strategy_id': strategy.id,
                'timestamp': datetime.now(),
                'signal_type': signal['action'],
                'strength': signal.get('signal_score', 0),
                'price': signal.get('price', 0),
                'confidence': signal.get('confidence', 0.5),
                'indicators_used': json.dumps(indicators_used),
                'reason': signal.get('reason', 'Trading bot signal')
            })
            
        except Exception as e:
            logger.error(f"Error logging {signal['action']} signal for {instrument.symbol}: {str(e)}")
        
    def _extract_indicators_used(self, signal: Dict[str, Any], indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key indicators used in decision making for signal metadata"""
        indicators_used = {}
        
        # Extract technical indicators that contributed to the signal
        if 'reason' in signal and indicators:
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
        if indicators:
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