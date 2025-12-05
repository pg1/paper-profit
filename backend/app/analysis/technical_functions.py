#!/usr/bin/env python3

"""
Technical Functions Module

This module provides functions for calculating technical indicators and parameters
using data from various third-party services via the octopus data providers.

Each function takes a stock symbol as input and returns the calculated technical indicator value.
"""

import logging
from typing import Optional, Union, Dict, Any, List
from sqlalchemy.orm import Session
from octopus.data_providers.alpha_vantage import AlphaVantageService
from octopus.data_providers.financialmodelingprep import FinancialModelingPrepService
from octopus.data_providers.yahoo_finance import YahooFinanceService

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TechnicalFunctions:
    """Class containing functions for calculating technical indicators"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.alpha_vantage = AlphaVantageService(db_session)
        self.fmp = FinancialModelingPrepService(db_session)
        self.yahoo = YahooFinanceService(db_session)
    
    def _get_best_data_provider(self, symbol: str, data_type: str = "technical") -> Dict[str, Any]:
        """
        Try multiple data providers to get the best available data for a symbol
        
        Args:
            symbol: Stock symbol
            data_type: Type of data needed ("technical", "price", "historical")
            
        Returns:
            Dictionary with the best available data
        """
        data = None
        
        # Try Alpha Vantage first for technical data
        if data_type == "technical":
            try:
                data = self.alpha_vantage.get_technical_indicators(symbol)
                if data and data.get('rsi') is not None:
                    logger.info(f"Using Alpha Vantage technical data for {symbol}")
                    return data
            except Exception as e:
                logger.debug(f"Alpha Vantage technical indicators failed for {symbol}: {e}")
        
        # Try Yahoo Finance for price/historical data
        try:
            if data_type == "price":
                data = self.yahoo.fetch_current_price(symbol)
            elif data_type == "historical":
                data = self.yahoo.fetch_historical_data(symbol, "6mo")
            else:
                data = self.yahoo.get_stock_analysis(symbol)
                
            if data:
                logger.info(f"Using Yahoo Finance data for {symbol}")
                return data
        except Exception as e:
            logger.debug(f"Yahoo Finance failed for {symbol}: {e}")
        
        # Try Financial Modeling Prep
        try:
            data = self.fmp.get_stock_analysis(symbol)
            if data:
                logger.info(f"Using Financial Modeling Prep data for {symbol}")
                return data
        except Exception as e:
            logger.debug(f"Financial Modeling Prep failed for {symbol}: {e}")
        
        logger.warning(f"No technical data available for {symbol} from any provider")
        return {}
    
    def _get_historical_prices(self, symbol: str, period: str = "6mo") -> Optional[List[float]]:
        """Get historical closing prices for a symbol"""
        try:
            # Try Yahoo Finance first
            historical_data = self.yahoo.fetch_historical_data(symbol, period)
            if historical_data:
                close_prices = [data['close_price'] for data in historical_data]
                return close_prices
            
            # Try Alpha Vantage
            historical_data = self.alpha_vantage.fetch_historical_data(symbol, period)
            if historical_data:
                close_prices = [data['close_price'] for data in historical_data]
                return close_prices
            
            # Try Financial Modeling Prep
            historical_data = self.fmp.fetch_historical_data(symbol, period)
            if historical_data:
                close_prices = [data['close_price'] for data in historical_data]
                return close_prices
                
        except Exception as e:
            logger.error(f"Error getting historical prices for {symbol}: {e}")
        
        return None
    
    # Technical Indicators
    
    def get_simple_moving_average(self, symbol: str, window: int = 20) -> Optional[float]:
        """
        Calculate Simple Moving Average (SMA)
        
        Args:
            symbol: Stock symbol
            window: Number of periods for SMA calculation
            
        Returns:
            SMA value or None if data unavailable
        """
        try:
            close_prices = self._get_historical_prices(symbol, "6mo")
            if not close_prices or len(close_prices) < window:
                return None
            
            sma = sum(close_prices[-window:]) / window
            return sma
            
        except Exception as e:
            logger.error(f"Error calculating SMA for {symbol}: {e}")
            return None
    
    def get_exponential_moving_average(self, symbol: str, window: int = 20) -> Optional[float]:
        """
        Calculate Exponential Moving Average (EMA)
        
        Args:
            symbol: Stock symbol
            window: Number of periods for EMA calculation
            
        Returns:
            EMA value or None if data unavailable
        """
        try:
            close_prices = self._get_historical_prices(symbol, "6mo")
            if not close_prices or len(close_prices) < window:
                return None
            
            # Calculate EMA
            multiplier = 2 / (window + 1)
            ema = close_prices[0]
            
            for price in close_prices[1:]:
                ema = (price - ema) * multiplier + ema
            
            return ema
            
        except Exception as e:
            logger.error(f"Error calculating EMA for {symbol}: {e}")
            return None
    
    def get_relative_strength_index(self, symbol: str, period: int = 14) -> Optional[float]:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            symbol: Stock symbol
            period: RSI period (typically 14)
            
        Returns:
            RSI value (0-100) or None if data unavailable
        """
        try:
            # Try to get RSI directly from data providers
            data = self._get_best_data_provider(symbol, "technical")
            if data and data.get('rsi') is not None:
                return data.get('rsi')
            
            # Calculate RSI manually if we have historical data
            close_prices = self._get_historical_prices(symbol, "6mo")
            if not close_prices or len(close_prices) < period + 1:
                return None
            
            # Calculate price changes
            changes = [close_prices[i] - close_prices[i-1] for i in range(1, len(close_prices))]
            
            # Separate gains and losses
            gains = [change if change > 0 else 0 for change in changes]
            losses = [-change if change < 0 else 0 for change in changes]
            
            # Calculate average gains and losses
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            logger.error(f"Error calculating RSI for {symbol}: {e}")
            return None
    
    def get_moving_average_convergence_divergence(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with MACD, signal line, and histogram values or None if data unavailable
        """
        try:
            close_prices = self._get_historical_prices(symbol, "1y")
            if not close_prices or len(close_prices) < 26:
                return None
            
            # Calculate EMA(12) and EMA(26)
            ema_12 = self._calculate_ema(close_prices, 12)
            ema_26 = self._calculate_ema(close_prices, 26)
            
            if ema_12 is None or ema_26 is None:
                return None
            
            # MACD line = EMA(12) - EMA(26)
            macd_line = ema_12 - ema_26
            
            # Signal line = EMA of MACD line (9 period)
            # We need MACD values for last 9+ periods to calculate signal line
            macd_values = []
            for i in range(len(close_prices)):
                if i >= 25:  # Need at least 26 prices to calculate first MACD
                    ema_12_i = self._calculate_ema(close_prices[:i+1], 12)
                    ema_26_i = self._calculate_ema(close_prices[:i+1], 26)
                    if ema_12_i is not None and ema_26_i is not None:
                        macd_values.append(ema_12_i - ema_26_i)
            
            if len(macd_values) < 9:
                signal_line = macd_line  # Use current MACD as signal if not enough data
            else:
                signal_line = self._calculate_ema(macd_values, 9)
            
            # Histogram = MACD line - Signal line
            histogram = macd_line - signal_line
            
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
            
        except Exception as e:
            logger.error(f"Error calculating MACD for {symbol}: {e}")
            return None
    
    def _calculate_ema(self, prices: List[float], window: int) -> Optional[float]:
        """Helper function to calculate EMA"""
        if not prices or len(prices) < window:
            return None
        
        multiplier = 2 / (window + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def get_bollinger_bands(self, symbol: str, window: int = 20, num_std: float = 2.0) -> Optional[Dict[str, float]]:
        """
        Calculate Bollinger Bands
        
        Args:
            symbol: Stock symbol
            window: Moving average window
            num_std: Number of standard deviations for bands
            
        Returns:
            Dictionary with upper, middle, and lower band values or None if data unavailable
        """
        try:
            close_prices = self._get_historical_prices(symbol, "6mo")
            if not close_prices or len(close_prices) < window:
                return None
            
            recent_prices = close_prices[-window:]
            
            # Middle band = SMA
            middle_band = sum(recent_prices) / window
            
            # Calculate standard deviation
            variance = sum((price - middle_band) ** 2 for price in recent_prices) / window
            std_dev = variance ** 0.5
            
            # Upper and lower bands
            upper_band = middle_band + (num_std * std_dev)
            lower_band = middle_band - (num_std * std_dev)
            
            return {
                'upper': upper_band,
                'middle': middle_band,
                'lower': lower_band
            }
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands for {symbol}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a stock (technical perspective)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Current price or None if data unavailable
        """
        try:
            # Try Yahoo Finance first for price data
            price_data = self.yahoo.fetch_current_price(symbol)
            if price_data and price_data.get('price'):
                return price_data['price']
            
            # Try Alpha Vantage
            price_data = self.alpha_vantage.fetch_current_price(symbol)
            if price_data and price_data.get('price'):
                return price_data['price']
            
            # Try Financial Modeling Prep
            price_data = self.fmp.fetch_current_price(symbol)
            if price_data and price_data.get('price'):
                return price_data['price']
                
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
        
        return None
    
    def get_price_trend(self, symbol: str) -> Optional[str]:
        """
        Determine price trend based on moving averages
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Trend ("BULLISH", "BEARISH", "SIDEWAYS") or None if data unavailable
        """
        try:
            sma_20 = self.get_simple_moving_average(symbol, 20)
            sma_50 = self.get_simple_moving_average(symbol, 50)
            current_price = self.get_current_price(symbol)
            
            if not all([sma_20, sma_50, current_price]):
                return None
            
            # Determine trend
            if current_price > sma_20 and current_price > sma_50:
                return "BULLISH"
            elif current_price < sma_20 and current_price < sma_50:
                return "BEARISH"
            else:
                return "SIDEWAYS"
            
        except Exception as e:
            logger.error(f"Error determining price trend for {symbol}: {e}")
            return None
    
    def get_volume_trend(self, symbol: str) -> Optional[str]:
        """
        Determine volume trend
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Volume trend ("HIGH", "LOW", "AVERAGE") or None if data unavailable
        """
        try:
            # Get stock analysis which includes volume trend
            analysis = self.yahoo.get_stock_analysis(symbol)
            if analysis and analysis.get('volume_trend'):
                return analysis.get('volume_trend')
            
            # Try other providers
            analysis = self.fmp.get_stock_analysis(symbol)
            if analysis and analysis.get('volume_trend'):
                return analysis.get('volume_trend')
            
            analysis = self.alpha_vantage.get_stock_analysis(symbol)
            if analysis and analysis.get('volume_trend'):
                return analysis.get('volume_trend')
            
            return None
            
        except Exception as e:
            logger.error(f"Error determining volume trend for {symbol}: {e}")
            return None
    
    def get_support_resistance_levels(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Identify support and resistance levels
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with support and resistance levels or None if data unavailable
        """
        try:
            close_prices = self._get_historical_prices(symbol, "3mo")
            if not close_prices or len(close_prices) < 20:
                return None
            
            # Simple implementation: use recent highs and lows
            recent_high = max(close_prices[-20:])
            recent_low = min(close_prices[-20:])
            current_price = close_prices[-1]
            
            # Calculate potential support and resistance levels
            pivot_point = (recent_high + recent_low + current_price) / 3
            
            resistance_1 = (2 * pivot_point) - recent_low
            support_1 = (2 * pivot_point) - recent_high
            
            resistance_2 = pivot_point + (recent_high - recent_low)
            support_2 = pivot_point - (recent_high - recent_low)
            
            return {
                'pivot': pivot_point,
                'resistance_1': resistance_1,
                'resistance_2': resistance_2,
                'support_1': support_1,
                'support_2': support_2,
                'recent_high': recent_high,
                'recent_low': recent_low
            }
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance levels for {symbol}: {e}")
            return None
    
    def get_volatility(self, symbol: str, window: int = 20) -> Optional[float]:
        """
        Calculate price volatility
        
        Args:
            symbol: Stock symbol
            window: Number of periods for volatility calculation
            
        Returns:
            Volatility (standard deviation of returns) or None if data unavailable
        """
        try:
            close_prices = self._get_historical_prices(symbol, "3mo")
            if not close_prices or len(close_prices) < window + 1:
                return None
            
            # Calculate daily returns
            returns = []
            for i in range(1, len(close_prices)):
                if close_prices[i-1] > 0:
                    daily_return = (close_prices[i] - close_prices[i-1]) / close_prices[i-1]
                    returns.append(daily_return)
            
            if len(returns) < window:
                return None
            
            recent_returns = returns[-window:]
            
            # Calculate standard deviation of returns (annualized)
            mean_return = sum(recent_returns) / len(recent_returns)
            variance = sum((r - mean_return) ** 2 for r in recent_returns) / len(recent_returns)
            daily_volatility = variance ** 0.5
            
            # Annualize (assuming 252 trading days)
            annual_volatility = daily_volatility * (252 ** 0.5)
            
            return annual_volatility
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return None
    
    # Boolean parameter helpers for technical analysis
    
    def is_overbought(self, symbol: str, rsi_threshold: float = 70.0) -> Optional[bool]:
        """
        Check if stock is overbought based on RSI
        
        Args:
            symbol: Stock symbol
            rsi_threshold: RSI threshold for overbought condition
            
        Returns:
            True if overbought, False otherwise, or None if data unavailable
        """
        try:
            rsi = self.get_relative_strength_index(symbol)
            if rsi is not None:
                return rsi >= rsi_threshold
            return None
        except Exception as e:
            logger.error(f"Error checking overbought condition for {symbol}: {e}")
            return None
    
    def is_oversold(self, symbol: str, rsi_threshold: float = 30.0) -> Optional[bool]:
        """
        Check if stock is oversold based on RSI
        
        Args:
            symbol: Stock symbol
            rsi_threshold: RSI threshold for oversold condition
            
        Returns:
            True if oversold, False otherwise, or None if data unavailable
        """
        try:
            rsi = self.get_relative_strength_index(symbol)
            if rsi is not None:
                return rsi <= rsi_threshold
            return None
        except Exception as e:
            logger.error(f"Error checking oversold condition for {symbol}: {e}")
            return None
    
    def is_above_moving_average(self, symbol: str, window: int = 20) -> Optional[bool]:
        """
        Check if current price is above moving average
        
        Args:
            symbol: Stock symbol
            window: Moving average window
            
        Returns:
            True if above MA, False otherwise, or None if data unavailable
        """
        try:
            sma = self.get_simple_moving_average(symbol, window)
            current_price = self.get_current_price(symbol)
            
            if sma is not None and current_price is not None:
                return current_price > sma
            return None
        except Exception as e:
            logger.error(f"Error checking price vs moving average for {symbol}: {e}")
            return None
    
    def has_golden_cross(self, symbol: str) -> Optional[bool]:
        """
        Check for golden cross (short-term MA crossing above long-term MA)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if golden cross detected, False otherwise, or None if data unavailable
        """
        try:
            sma_50 = self.get_simple_moving_average(symbol, 50)
            sma_200 = self.get_simple_moving_average(symbol, 200)
            
            if sma_50 is not None and sma_200 is not None:
                return sma_50 > sma_200
            return None
        except Exception as e:
            logger.error(f"Error checking for golden cross for {symbol}: {e}")
            return None
    
    def has_death_cross(self, symbol: str) -> Optional[bool]:
        """
        Check for death cross (short-term MA crossing below long-term MA)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if death cross detected, False otherwise, or None if data unavailable
        """
        try:
            sma_50 = self.get_simple_moving_average(symbol, 50)
            sma_200 = self.get_simple_moving_average(symbol, 200)
            
            if sma_50 is not None and sma_200 is not None:
                return sma_50 < sma_200
            return None
        except Exception as e:
            logger.error(f"Error checking for death cross for {symbol}: {e}")
            return None
    
    def is_price_near_support(self, symbol: str, threshold_percent: float = 5.0) -> Optional[bool]:
        """
        Check if price is near support level
        
        Args:
            symbol: Stock symbol
            threshold_percent: Percentage threshold for "near" support
            
        Returns:
            True if near support, False otherwise, or None if data unavailable
        """
        try:
            levels = self.get_support_resistance_levels(symbol)
            current_price = self.get_current_price(symbol)
            
            if levels and current_price:
                support_1 = levels.get('support_1')
                if support_1:
                    price_diff_percent = abs(current_price - support_1) / support_1 * 100
                    return price_diff_percent <= threshold_percent
            return None
        except Exception as e:
            logger.error(f"Error checking price near support for {symbol}: {e}")
            return None
    
    def is_price_near_resistance(self, symbol: str, threshold_percent: float = 5.0) -> Optional[bool]:
        """
        Check if price is near resistance level
        
        Args:
            symbol: Stock symbol
            threshold_percent: Percentage threshold for "near" resistance
            
        Returns:
            True if near resistance, False otherwise, or None if data unavailable
        """
        try:
            levels = self.get_support_resistance_levels(symbol)
            current_price = self.get_current_price(symbol)
            
            if levels and current_price:
                resistance_1 = levels.get('resistance_1')
                if resistance_1:
                    price_diff_percent = abs(current_price - resistance_1) / resistance_1 * 100
                    return price_diff_percent <= threshold_percent
            return None
        except Exception as e:
            logger.error(f"Error checking price near resistance for {symbol}: {e}")
            return None
    
    def get_all_technical_indicators(self, symbol: str) -> Dict[str, Any]:
        """
        Get all available technical indicators for a stock
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary containing all calculated technical indicators
        """
        indicators = {
            'symbol': symbol,
            'current_price': self.get_current_price(symbol),
            'sma_20': self.get_simple_moving_average(symbol, 20),
            'sma_50': self.get_simple_moving_average(symbol, 50),
            'sma_200': self.get_simple_moving_average(symbol, 200),
            'ema_20': self.get_exponential_moving_average(symbol, 20),
            'rsi': self.get_relative_strength_index(symbol),
            'macd': self.get_moving_average_convergence_divergence(symbol),
            'bollinger_bands': self.get_bollinger_bands(symbol),
            'price_trend': self.get_price_trend(symbol),
            'volume_trend': self.get_volume_trend(symbol),
            'support_resistance_levels': self.get_support_resistance_levels(symbol),
            'volatility': self.get_volatility(symbol),
            'is_overbought': self.is_overbought(symbol),
            'is_oversold': self.is_oversold(symbol),
            'is_above_moving_average': self.is_above_moving_average(symbol, 20),
            'has_golden_cross': self.has_golden_cross(symbol),
            'has_death_cross': self.has_death_cross(symbol),
            'is_price_near_support': self.is_price_near_support(symbol),
            'is_price_near_resistance': self.is_price_near_resistance(symbol)
        }
        
        return indicators


# Convenience functions for direct usage
def create_technical_functions(db_session: Session) -> TechnicalFunctions:
    """
    Create a TechnicalFunctions instance
    
    Args:
        db_session: Database session
        
    Returns:
        TechnicalFunctions instance
    """
    return TechnicalFunctions(db_session)


def get_technical_indicator(db_session: Session, symbol: str, indicator_name: str) -> Any:
    """
    Get a specific technical indicator value for a stock
    
    Args:
        db_session: Database session
        symbol: Stock symbol
        indicator_name: Name of the technical indicator to get
        
    Returns:
        Indicator value or None if unavailable
    """
    tf = TechnicalFunctions(db_session)
    
    # Map indicator names to method calls
    indicator_methods = {
        'current_price': tf.get_current_price,
        'sma_20': lambda s: tf.get_simple_moving_average(s, 20),
        'sma_50': lambda s: tf.get_simple_moving_average(s, 50),
        'rsi': tf.get_relative_strength_index,
        'macd': tf.get_moving_average_convergence_divergence,
        'price_trend': tf.get_price_trend,
        'is_overbought': tf.is_overbought,
        'is_oversold': tf.is_oversold
    }
    
    method = indicator_methods.get(indicator_name)
    if method:
        return method(symbol)
    else:
        logger.warning(f"Unknown technical indicator: {indicator_name}")
        return None


def get_all_technical_indicators_for_stock(db_session: Session, symbol: str) -> Dict[str, Any]:
    """
    Get all technical indicators for a stock
    
    Args:
        db_session: Database session
        symbol: Stock symbol
        
    Returns:
        Dictionary containing all technical indicators
    """
    tf = TechnicalFunctions(db_session)
    return tf.get_all_technical_indicators(symbol)
