import json
import logging
import yaml
import os
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from storage.repositories import RepositoryFactory
from storage.models import Account, Strategy, Instrument, QuantitativeData
from analysis.fundamental_functions import FundamentalFunctions
from analysis.technical_functions import TechnicalFunctions

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)  # Set logger level


class QuantitativeDataMapper:
    """Maps quantitative data YAML configuration to database queries"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Calculate absolute path like data_collector.py does
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'config', 'quantitative_data.yaml'
            )
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load quantitative data configuration from YAML"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config.get('quantitative_data', {})
        except Exception as e:
            logger.error(f"Failed to load quantitative data config: {e}")
            return {}
    
    def get_all_parameter_names(self) -> List[str]:
        """Get all parameter names from the configuration"""
        param_names = []
        
        # Technical parameters
        technical = self.config.get('technical', {})
        for category, params in technical.items():
            if isinstance(params, dict):
                param_names.extend(params.keys())
        
        # Fundamental parameters
        fundamental = self.config.get('fundamental', {})
        for category, params in fundamental.items():
            if isinstance(params, dict):
                param_names.extend(params.keys())
        
        # Market parameters
        market = self.config.get('market', {})
        for category, params in market.items():
            if isinstance(params, dict):
                param_names.extend(params.keys())
        
        # Microstructure parameters
        microstructure = self.config.get('microstructure', {})
        for category, params in microstructure.items():
            if isinstance(params, dict):
                param_names.extend(params.keys())
        
        # Options parameters
        options = self.config.get('options', {})
        for category, params in options.items():
            if isinstance(params, dict):
                param_names.extend(params.keys())
        
        # Sentiment parameters
        sentiment = self.config.get('sentiment', {})
        for category, params in sentiment.items():
            if isinstance(params, dict):
                param_names.extend(params.keys())
        
        return param_names
    
    def get_parameter_config(self, param_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific parameter"""
        # Search through all categories
        for category in ['technical', 'fundamental', 'market', 'microstructure', 'options', 'sentiment']:
            category_data = self.config.get(category, {})
            if isinstance(category_data, dict):
                for subcategory, params in category_data.items():
                    if isinstance(params, dict) and param_name in params:
                        return params[param_name]
        return None
    
    def get_refresh_rate(self, param_name: str) -> Optional[int]:
        """Get refresh rate for a parameter in minutes"""
        config = self.get_parameter_config(param_name)
        if config:
            return config.get('refresh_rate')
        return None
    
    def get_parameter_type(self, param_name: str) -> Optional[str]:
        """Get parameter type"""
        config = self.get_parameter_config(param_name)
        if config:
            return config.get('type')
        return None
    
    def get_parameter_category(self, param_name: str) -> Optional[str]:
        """Get parameter category (technical, fundamental, etc.)"""
        for category in ['technical', 'fundamental', 'market', 'microstructure', 'options', 'sentiment']:
            category_data = self.config.get(category, {})
            if isinstance(category_data, dict):
                for subcategory, params in category_data.items():
                    if isinstance(params, dict) and param_name in params:
                        return category
        return None


class StrategySignal:
    """Module for generating trading signals based on strategy"""
    
    def __init__(self, db: Session, repo_factory: RepositoryFactory):
        self.db = db
        self.repo_factory = repo_factory
        self.fundamental_functions = FundamentalFunctions(db)
        self.technical_functions = TechnicalFunctions(db)
        self.quantitative_mapper = QuantitativeDataMapper()
    
    def parse_strategy_parameters(self, strategy: Strategy) -> Dict[str, Any]:
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
    
    def get_quantitative_data_for_symbol(self, symbol: str, param_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get quantitative data for a symbol from database"""
        try:
            instrument = self.repo_factory.instruments.get_by_symbol(symbol)
            if not instrument:
                logger.warning(f"Instrument not found for symbol: {symbol}")
                return {}
            
            if param_names is None:
                # Get all parameter names from config
                param_names = self.quantitative_mapper.get_all_parameter_names()
            
            quantitative_data = {}
            for param_name in param_names:
                # Get latest value from quantitative data table
                data = self.repo_factory.quantitative_data.get_latest(
                    instrument.id, meta=param_name, limit=1
                )
                if data:
                    try:
                        # Convert value based on parameter type
                        param_config = self.quantitative_mapper.get_parameter_config(param_name)
                        param_type = param_config.get('type') if param_config else None
                        
                        value = data[0].value
                        if param_type == 'float':
                            quantitative_data[param_name] = float(value)
                        elif param_type == 'integer':
                            quantitative_data[param_name] = int(value)
                        elif param_type == 'percentage':
                            quantitative_data[param_name] = float(value)
                        else:
                            quantitative_data[param_name] = value
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Could not convert value for {param_name}: {e}")
                        quantitative_data[param_name] = data[0].value
            
            return quantitative_data
            
        except Exception as e:
            logger.error(f"Error getting quantitative data for {symbol}: {e}")
            return {}
    
    def evaluate_technical_signals(self, symbol: str, strategy_params: Dict[str, Any], 
                                  quantitative_data: Dict[str, Any]) -> Tuple[int, List[str]]:
        """Evaluate technical signals based on strategy parameters and quantitative data"""
        signal_score = 0
        reasons = []
        
        # Get technical indicators from quantitative data or calculate them
        rsi = quantitative_data.get('rsi')
        if rsi is None:
            # Fallback to technical functions
            rsi = self.technical_functions.get_relative_strength_index(symbol)
        
        # RSI evaluation
        if rsi is not None:
            # Ensure all values are numeric (convert from numpy/string types)
            try:
                rsi = float(rsi)
            except (ValueError, TypeError):
                rsi = None
        
        if rsi is not None:
            rsi_oversold = self._get_numeric_param(strategy_params, 'rsi_oversold', 30.0)
            rsi_overbought = self._get_numeric_param(strategy_params, 'rsi_overbought', 70.0)
            
            if rsi < rsi_oversold:
                signal_score += 2
                reasons.append(f'RSI oversold ({rsi:.1f} < {rsi_oversold})')
            elif rsi > rsi_overbought:
                signal_score -= 2
                reasons.append(f'RSI overbought ({rsi:.1f} > {rsi_overbought})')
        
        # Price trend evaluation
        price_trend = quantitative_data.get('price_trend')
        if price_trend is None:
            price_trend = self.technical_functions.get_price_trend(symbol)
        
        if price_trend == 'BULLISH':
            signal_score += 1
            reasons.append('Bullish price trend')
        elif price_trend == 'BEARISH':
            signal_score -= 1
            reasons.append('Bearish price trend')
        
        # Moving average evaluation
        sma_20 = quantitative_data.get('sma_20')
        sma_50 = quantitative_data.get('sma_50')
        current_price = quantitative_data.get('current_price')
        
        if current_price is None:
            current_price = self.technical_functions.get_current_price(symbol)
        
        if current_price is not None:
            if sma_20 is not None and current_price > sma_20:
                signal_score += 1
                reasons.append(f'Price above SMA20 ({current_price:.2f} > {sma_20:.2f})')
            if sma_50 is not None and current_price > sma_50:
                signal_score += 1
                reasons.append(f'Price above SMA50 ({current_price:.2f} > {sma_50:.2f})')
        
        # MACD evaluation
        '''
        macd_data = quantitative_data.get('macd')
        if macd_data is None:
            macd_data = self.technical_functions.get_moving_average_convergence_divergence(symbol)
        
        if isinstance(macd_data, dict) and 'histogram' in macd_data:
            if macd_data['histogram'] > 0:
                signal_score += 1
                reasons.append('MACD histogram positive (bullish)')
            elif macd_data['histogram'] < 0:
                signal_score -= 1
                reasons.append('MACD histogram negative (bearish)')
        '''

        # Bollinger Bands evaluation
        bb_data = quantitative_data.get('bollinger_bands')
        if bb_data is None:
            bb_data = self.technical_functions.get_bollinger_bands(symbol)
        
        if isinstance(bb_data, dict) and current_price is not None:
            bb_lower = bb_data.get('lower')
            bb_upper = bb_data.get('upper')
            
            if bb_lower is not None and current_price < bb_lower:
                signal_score += 1
                reasons.append(f'Price below Bollinger lower band ({current_price:.2f} < {bb_lower:.2f})')
            elif bb_upper is not None and current_price > bb_upper:
                signal_score -= 1
                reasons.append(f'Price above Bollinger upper band ({current_price:.2f} > {bb_upper:.2f})')
        
        # Volume evaluation
        volume_ratio = quantitative_data.get('volume_ratio')
        if volume_ratio is not None and volume_ratio > 1.5:
            signal_score += 1
            reasons.append(f'High volume ratio ({volume_ratio:.2f}x average)')
        
        return signal_score, reasons
    
    def evaluate_fundamental_signals(self, symbol: str, strategy_params: Dict[str, Any],
                                    quantitative_data: Dict[str, Any]) -> Tuple[int, List[str]]:
        """Evaluate fundamental signals based on strategy parameters and quantitative data"""
        signal_score = 0
        reasons = []
        
        # Get fundamental data
        fundamental_data = self.fundamental_functions.get_all_parameters(symbol)
        
        # Quality score evaluation
        min_quality = self._to_float(strategy_params.get('min_quality_score'))
        quality_score = self._to_float(fundamental_data.get('quality_score'))
        
        if min_quality is not None and quality_score is not None:
            if quality_score >= min_quality:
                signal_score += 1
                reasons.append(f'Quality score meets requirement ({quality_score} >= {min_quality})')
            else:
                signal_score -= 1
                reasons.append(f'Quality score below requirement ({quality_score} < {min_quality})')
        
        # P/E ratio evaluation
        max_pe = self._to_float(strategy_params.get('max_pe')) or self._to_float(strategy_params.get('max_pe_ratio'))
        pe_ratio = self._to_float(fundamental_data.get('pe_ratio')) or self._to_float(quantitative_data.get('pe'))
        
        if max_pe is not None and pe_ratio is not None:
            if pe_ratio <= max_pe:
                signal_score += 1
                reasons.append(f'P/E ratio within limit ({pe_ratio:.1f} <= {max_pe})')
            else:
                signal_score -= 1
                reasons.append(f'P/E ratio exceeds limit ({pe_ratio:.1f} > {max_pe})')
        
        # P/B ratio evaluation
        max_pb = self._to_float(strategy_params.get('max_pb'))
        pb_ratio = self._to_float(fundamental_data.get('pb_ratio')) or self._to_float(quantitative_data.get('pb'))
        
        if max_pb is not None and pb_ratio is not None:
            if pb_ratio <= max_pb:
                signal_score += 1
                reasons.append(f'P/B ratio within limit ({pb_ratio:.2f} <= {max_pb})')
            else:
                signal_score -= 1
                reasons.append(f'P/B ratio exceeds limit ({pb_ratio:.2f} > {max_pb})')
        
        # PEG ratio evaluation
        max_peg = self._to_float(strategy_params.get('max_peg'))
        peg_ratio = self._to_float(fundamental_data.get('peg_ratio')) or self._to_float(quantitative_data.get('peg'))
        
        if max_peg is not None and peg_ratio is not None:
            if peg_ratio <= max_peg:
                signal_score += 1
                reasons.append(f'PEG ratio within limit ({peg_ratio:.2f} <= {max_peg})')
            else:
                signal_score -= 1
                reasons.append(f'PEG ratio exceeds limit ({peg_ratio:.2f} > {max_peg})')
        
        # ROE evaluation
        min_roe = self._to_float(strategy_params.get('minimum_roe_percent'))
        roe = self._to_float(fundamental_data.get('roe'))
        
        if min_roe is not None and roe is not None:
            roe_percent = roe * 100 if roe < 1 else roe
            if roe_percent >= min_roe:
                signal_score += 1
                reasons.append(f'ROE meets requirement ({roe_percent:.1f}% >= {min_roe}%)')
            else:
                signal_score -= 1
                reasons.append(f'ROE below requirement ({roe_percent:.1f}% < {min_roe}%)')
        
        # Growth evaluation
        min_revenue_growth = self._to_float(strategy_params.get('min_revenue_growth'))
        min_eps_growth = self._to_float(strategy_params.get('min_eps_growth'))
        
        revenue_growth = self._to_float(fundamental_data.get('revenue_growth'))
        eps_growth = self._to_float(fundamental_data.get('eps_growth'))
        
        if min_revenue_growth is not None and revenue_growth is not None:
            revenue_growth_pct = revenue_growth * 100 if revenue_growth < 1 else revenue_growth
            if revenue_growth_pct >= min_revenue_growth:
                signal_score += 1
                reasons.append(f'Revenue growth meets requirement ({revenue_growth_pct:.1f}% >= {min_revenue_growth}%)')
        
        if min_eps_growth is not None and eps_growth is not None:
            eps_growth_pct = eps_growth * 100 if eps_growth < 1 else eps_growth
            if eps_growth_pct >= min_eps_growth:
                signal_score += 1
                reasons.append(f'EPS growth meets requirement ({eps_growth_pct:.1f}% >= {min_eps_growth}%)')
        
        # Dividend yield evaluation
        min_dividend_yield = self._to_float(strategy_params.get('min_dividend_yield'))
        dividend_yield = self._to_float(fundamental_data.get('dividend_yield'))
        
        if min_dividend_yield is not None and dividend_yield is not None:
            dividend_yield_pct = dividend_yield * 100 if dividend_yield < 1 else dividend_yield
            if dividend_yield_pct >= min_dividend_yield:
                signal_score += 1
                reasons.append(f'Dividend yield meets requirement ({dividend_yield_pct:.1f}% >= {min_dividend_yield}%)')
        
        # Fundamental shift check
        sell_on_fundamental_shift = strategy_params.get('sell_on_fundamental_shift', False)
        has_fundamental_shift = fundamental_data.get('has_fundamental_shift')
        
        if sell_on_fundamental_shift and has_fundamental_shift:
            signal_score -= 2
            reasons.append('Fundamental deterioration detected')
        
        return signal_score, reasons
    
    def evaluate_market_sentiment_signals(self, symbol: str, strategy_params: Dict[str, Any],
                                         quantitative_data: Dict[str, Any]) -> Tuple[int, List[str]]:
        """Evaluate market and sentiment signals"""
        signal_score = 0
        reasons = []
        
        # Beta evaluation (risk)
        beta = quantitative_data.get('beta')
        if beta is not None:
            if beta < 0.8:
                signal_score += 1
                reasons.append(f'Low beta ({beta:.2f}) - defensive')
            elif beta > 1.2:
                signal_score -= 1
                reasons.append(f'High beta ({beta:.2f}) - aggressive')
        
        # Analyst sentiment
        consensus_rating = quantitative_data.get('consensus_rating')
        upside_potential = quantitative_data.get('upside_potential')
        
        if consensus_rating is not None:
            if consensus_rating >= 4.0:  # Strong buy
                signal_score += 1
                reasons.append(f'Strong analyst rating ({consensus_rating:.1f}/5)')
            elif consensus_rating <= 2.0:  # Sell
                signal_score -= 1
                reasons.append(f'Weak analyst rating ({consensus_rating:.1f}/5)')
        
        if upside_potential is not None and upside_potential > 20:
            signal_score += 1
            reasons.append(f'High upside potential ({upside_potential:.1f}%)')
        
        # Social sentiment
        social_sentiment = quantitative_data.get('social_sentiment_score')
        if social_sentiment is not None:
            if social_sentiment > 0.5:
                signal_score += 1
                reasons.append(f'Positive social sentiment ({social_sentiment:.2f})')
            elif social_sentiment < -0.5:
                signal_score -= 1
                reasons.append(f'Negative social sentiment ({social_sentiment:.2f})')
        
        return signal_score, reasons
    
    def has_fundamental_parameters(self, strategy_params: Dict[str, Any]) -> bool:
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
    
    def generate_trading_signal(self, account: Account, strategy: Strategy, instrument: Instrument,
                               market_data: Dict[str, Any], indicators: Dict[str, Any], 
                               strategy_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate trading signal based on strategy and market conditions using TA and FA"""
        
        current_price = market_data['close']
        volume = market_data['volume']
        symbol = instrument.symbol
        
        # Basic volume filter - ensure min_volume is numeric
        min_volume = self._get_numeric_param(strategy_params, 'min_volume', 1000000)
        if volume < min_volume:
            return {'action': 'HOLD', 'reason': f'Low volume ({volume:,} < {min_volume:,})'}
        
        # Get quantitative data from database
        quantitative_data = self.get_quantitative_data_for_symbol(symbol)
        
        # Evaluate signals from different categories
        technical_score, technical_reasons = self.evaluate_technical_signals(
            symbol, strategy_params, quantitative_data
        )
        
        fundamental_score, fundamental_reasons = self.evaluate_fundamental_signals(
            symbol, strategy_params, quantitative_data
        )
        
        market_sentiment_score, market_sentiment_reasons = self.evaluate_market_sentiment_signals(
            symbol, strategy_params, quantitative_data
        )
        
        # Calculate composite signal score
        signal_score = technical_score + fundamental_score + market_sentiment_score
        all_reasons = technical_reasons + fundamental_reasons + market_sentiment_reasons
        
        # Add legacy indicator-based reasons for backward compatibility
        rsi = indicators.get('rsi')
        price_trend = indicators.get('price_trend')
        is_overbought = indicators.get('is_overbought')
        is_oversold = indicators.get('is_oversold')
        
        if rsi is not None:
            # Ensure RSI is numeric before comparison
            try:
                rsi = float(rsi)
                rsi_oversold = self._get_numeric_param(strategy_params, 'rsi_oversold', 30.0)
                rsi_overbought = self._get_numeric_param(strategy_params, 'rsi_overbought', 70.0)
                
                if rsi < rsi_oversold:
                    all_reasons.append(f'RSI oversold ({rsi:.2f})')
                elif rsi > rsi_overbought:
                    all_reasons.append(f'RSI overbought ({rsi:.2f})')
            except (ValueError, TypeError):
                pass  # Skip RSI comparison if not numeric
        
        if price_trend == 'BULLISH':
            all_reasons.append('Bullish price trend')
        elif price_trend == 'BEARISH':
            all_reasons.append('Bearish price trend')
        
        if is_oversold:
            all_reasons.append('Oversold condition')
        if is_overbought:
            all_reasons.append('Overbought condition')
        
        # Remove duplicate reasons
        unique_reasons = []
        for reason in all_reasons:
            if reason not in unique_reasons:
                unique_reasons.append(reason)
        
        # Generate signal based on composite score
        if signal_score >= 4:
            confidence = min(0.95, signal_score / 15.0 + 0.5)
            return {
                'action': 'BUY',
                'price': current_price,
                'reason': '; '.join(unique_reasons),
                'confidence': round(confidence, 2),
                'signal_score': signal_score,
                'contributing_factors': {
                    'technical_score': technical_score,
                    'fundamental_score': fundamental_score,
                    'market_sentiment_score': market_sentiment_score,
                    'technical_reasons': technical_reasons,
                    'fundamental_reasons': fundamental_reasons,
                    'market_sentiment_reasons': market_sentiment_reasons
                }
            }
        elif signal_score <= -4:
            confidence = min(0.95, abs(signal_score) / 15.0 + 0.5)
            return {
                'action': 'SELL',
                'price': current_price,
                'reason': '; '.join(unique_reasons),
                'confidence': round(confidence, 2),
                'signal_score': signal_score,
                'contributing_factors': {
                    'technical_score': technical_score,
                    'fundamental_score': fundamental_score,
                    'market_sentiment_score': market_sentiment_score,
                    'technical_reasons': technical_reasons,
                    'fundamental_reasons': fundamental_reasons,
                    'market_sentiment_reasons': market_sentiment_reasons
                }
            }
        else:
            # Default to HOLD if no clear signal
            hold_reason = 'No clear signal'
            if unique_reasons:
                hold_reason = f'Mixed signals: {"; ".join(unique_reasons)}'
            return {
                'action': 'HOLD',
                'reason': hold_reason,
                'signal_score': signal_score,
                'contributing_factors': {
                    'technical_score': technical_score,
                    'fundamental_score': fundamental_score,
                    'market_sentiment_score': market_sentiment_score,
                    'technical_reasons': technical_reasons,
                    'fundamental_reasons': fundamental_reasons,
                    'market_sentiment_reasons': market_sentiment_reasons
                }
            }
    
    def generate_signal_with_quantitative_data(self, account: Account, strategy: Strategy, 
                                              instrument: Instrument, strategy_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate trading signal using only quantitative data (no market_data or indicators required)"""
        symbol = instrument.symbol
        
        # Get quantitative data from database
        quantitative_data = self.get_quantitative_data_for_symbol(symbol)
        
        # Get current price from quantitative data or fallback
        current_price = quantitative_data.get('current_price')
        if current_price is None:
            current_price = self.technical_functions.get_current_price(symbol)
            if current_price is None:
                logger.warning(f"Cannot generate signal for {symbol}: No price data available")
                return None
        
        # Get volume from quantitative data
        volume = quantitative_data.get('volume')
        min_volume = self._get_numeric_param(strategy_params, 'min_volume', 1000000)
        
        if volume is not None and volume < min_volume:
            return {'action': 'HOLD', 'reason': f'Low volume ({volume:,} < {min_volume:,})'}
        
        # Evaluate signals from different categories
        technical_score, technical_reasons = self.evaluate_technical_signals(
            symbol, strategy_params, quantitative_data
        )
        
        fundamental_score, fundamental_reasons = self.evaluate_fundamental_signals(
            symbol, strategy_params, quantitative_data
        )
        
        market_sentiment_score, market_sentiment_reasons = self.evaluate_market_sentiment_signals(
            symbol, strategy_params, quantitative_data
        )
        
        # Calculate composite signal score
        signal_score = technical_score + fundamental_score + market_sentiment_score
        all_reasons = technical_reasons + fundamental_reasons + market_sentiment_reasons
        
        # Remove duplicate reasons
        unique_reasons = []
        for reason in all_reasons:
            if reason not in unique_reasons:
                unique_reasons.append(reason)
        
        # Generate signal based on composite score
        if signal_score >= 4:
            confidence = min(0.95, signal_score / 15.0 + 0.5)
            return {
                'action': 'BUY',
                'price': current_price,
                'reason': '; '.join(unique_reasons),
                'confidence': round(confidence, 2),
                'signal_score': signal_score,
                'contributing_factors': {
                    'technical_score': technical_score,
                    'fundamental_score': fundamental_score,
                    'market_sentiment_score': market_sentiment_score,
                    'technical_reasons': technical_reasons,
                    'fundamental_reasons': fundamental_reasons,
                    'market_sentiment_reasons': market_sentiment_reasons
                }
            }
        elif signal_score <= -4:
            confidence = min(0.95, abs(signal_score) / 15.0 + 0.5)
            return {
                'action': 'SELL',
                'price': current_price,
                'reason': '; '.join(unique_reasons),
                'confidence': round(confidence, 2),
                'signal_score': signal_score,
                'contributing_factors': {
                    'technical_score': technical_score,
                    'fundamental_score': fundamental_score,
                    'market_sentiment_score': market_sentiment_score,
                    'technical_reasons': technical_reasons,
                    'fundamental_reasons': fundamental_reasons,
                    'market_sentiment_reasons': market_sentiment_reasons
                }
            }
        else:
            # Default to HOLD if no clear signal
            hold_reason = 'No clear signal'
            if unique_reasons:
                hold_reason = f'Mixed signals: {"; ".join(unique_reasons)}'
            return {
                'action': 'HOLD',
                'reason': hold_reason,
                'signal_score': signal_score,
                'contributing_factors': {
                    'technical_score': technical_score,
                    'fundamental_score': fundamental_score,
                    'market_sentiment_score': market_sentiment_score,
                    'technical_reasons': technical_reasons,
                    'fundamental_reasons': fundamental_reasons,
                    'market_sentiment_reasons': market_sentiment_reasons
                }
            }
    
    def extract_indicators_used(self, signal: Dict[str, Any], indicators: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def _to_float(self, value: Any, default: Optional[float] = None) -> Optional[float]:
        """Safely convert any value to float, handling numpy types, empty strings, etc."""
        if value is None or value == '':
            return default
        
        try:
            # Handle numpy scalar types
            if hasattr(value, 'item'):
                return float(value.item())
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _get_numeric_param(self, params: Dict[str, Any], key: str, default: float) -> float:
        """Safely get a numeric parameter from params dict, handling empty strings and type conversion"""
        value = params.get(key)
        
        # Handle None or empty string
        if value is None or value == '':
            return default
        
        # Try to convert to float
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert parameter '{key}' value '{value}' to number, using default {default}")
            return default
    
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