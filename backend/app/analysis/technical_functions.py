#!/usr/bin/env python3

"""
Technical Functions Module

This module provides functions for calculating technical indicators and parameters
using data from various third-party services via the octopus data providers.

Each function takes a stock symbol as input and returns the calculated technical indicator value.

Optimized to use DataFetcher for efficient API calls with caching.
"""

import logging
from typing import Optional, Union, Dict, Any, List
from sqlalchemy.orm import Session

from analysis.data_fetcher import DataFetcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TechnicalFunctions:
    """Class containing functions for calculating technical indicators"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.data_fetcher = DataFetcher(db_session)
        
        # Cache for calculated indicators to avoid redundant calculations
        self._calculated_cache = {}
    
    def _get_historical_prices(self, symbol: str, period: str = "6mo", refresh_rate_minutes: Optional[int] = None) -> Optional[List[float]]:
        """
        Get historical closing prices for a symbol using DataFetcher with caching
        
        Args:
            symbol: Stock symbol
            period: Time period (e.g., "6mo", "1y")
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            List of closing prices or None if unavailable
        """
        return self.data_fetcher.fetch_historical_prices(symbol, period, refresh_rate_minutes)
    
    def _get_current_price(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """
        Get current price for a symbol using DataFetcher with caching
        
        Args:
            symbol: Stock symbol
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Current price or None if unavailable
        """
        return self.data_fetcher.fetch_current_price(symbol, refresh_rate_minutes)
    
    def _get_technical_indicators(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Dict[str, Any]:
        """
        Get technical indicators for a symbol using DataFetcher with caching
        
        Args:
            symbol: Stock symbol
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Dictionary with technical indicators or empty dict if unavailable
        """
        return self.data_fetcher.fetch_technical_indicators(symbol, refresh_rate_minutes)
    
    def _get_calculated_cache_key(self, symbol: str, indicator_name: str, *args) -> str:
        """Generate cache key for calculated indicators"""
        args_str = "_".join(str(arg) for arg in args)
        return f"{symbol}_{indicator_name}_{args_str}" if args_str else f"{symbol}_{indicator_name}"
    
    def _get_calculated_indicator(self, symbol: str, indicator_name: str, calculator_func, *args, **kwargs):
        """
        Get calculated indicator with caching to avoid redundant calculations
        
        Args:
            symbol: Stock symbol
            indicator_name: Name of the indicator
            calculator_func: Function to calculate the indicator
            *args, **kwargs: Arguments to pass to calculator_func
            
        Returns:
            Calculated indicator value
        """
        cache_key = self._get_calculated_cache_key(symbol, indicator_name, *args)
        
        if cache_key in self._calculated_cache:
            return self._calculated_cache[cache_key]
        
        result = calculator_func(symbol, *args, **kwargs)
        self._calculated_cache[cache_key] = result
        return result
    
    def clear_calculated_cache(self, symbol: str = None):
        """
        Clear calculated cache for specific symbol or all symbols
        
        Args:
            symbol: Optional stock symbol to clear
        """
        if symbol is None:
            self._calculated_cache.clear()
            logger.debug("Cleared all calculated cache")
        else:
            keys_to_delete = [k for k in self._calculated_cache.keys() if k.startswith(f"{symbol}_")]
            for key in keys_to_delete:
                del self._calculated_cache[key]
            logger.debug(f"Cleared calculated cache for {symbol}")
    
    def _calculate_ema(self, prices: List[float], window: int) -> Optional[float]:
        """Helper function to calculate EMA"""
        if not prices or len(prices) < window:
            return None
        
        multiplier = 2 / (window + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    # Technical Indicators
    
    def get_simple_moving_average(self, symbol: str, window: int = 20, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """
        Calculate Simple Moving Average (SMA)
        
        Args:
            symbol: Stock symbol
            window: Number of periods for SMA calculation
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            SMA value or None if data unavailable
        """
        return self._get_calculated_indicator(
            symbol, f'sma_{window}', self._calculate_sma, window, refresh_rate_minutes
        )
    
    def _calculate_sma(self, symbol: str, window: int = 20, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """Internal method to calculate SMA"""
        try:
            close_prices = self._get_historical_prices(symbol, "6mo", refresh_rate_minutes)
            if not close_prices or len(close_prices) < window:
                return None
            
            sma = sum(close_prices[-window:]) / window
            return sma
            
        except Exception as e:
            logger.error(f"Error calculating SMA for {symbol}: {e}")
            return None
    
    def get_exponential_moving_average(self, symbol: str, window: int = 20, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """
        Calculate Exponential Moving Average (EMA)
        
        Args:
            symbol: Stock symbol
            window: Number of periods for EMA calculation
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            EMA value or None if data unavailable
        """
        return self._get_calculated_indicator(
            symbol, f'ema_{window}', self._calculate_ema_method, window, refresh_rate_minutes
        )
    
    def _calculate_ema_method(self, symbol: str, window: int = 20, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """Internal method to calculate EMA"""
        try:
            close_prices = self._get_historical_prices(symbol, "6mo", refresh_rate_minutes)
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
    
    def get_relative_strength_index(self, symbol: str, period: int = 14, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            symbol: Stock symbol
            period: RSI period (typically 14)
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            RSI value (0-100) or None if data unavailable
        """
        return self._get_calculated_indicator(
            symbol, f'rsi_{period}', self._calculate_rsi, period, refresh_rate_minutes
        )
    
    def _calculate_rsi(self, symbol: str, period: int = 14, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """Internal method to calculate RSI"""
        try:
            # Try to get RSI directly from data providers
            data = self._get_technical_indicators(symbol, refresh_rate_minutes)
            if data and data.get('rsi') is not None:
                return data.get('rsi')
            
            # Calculate RSI manually if we have historical data
            close_prices = self._get_historical_prices(symbol, "6mo", refresh_rate_minutes)
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
    
    def get_moving_average_convergence_divergence(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Optional[Dict[str, float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            symbol: Stock symbol
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Dictionary with MACD, signal line, and histogram values or None if data unavailable
        """
        return self._get_calculated_indicator(
            symbol, 'macd', self._calculate_macd, refresh_rate_minutes
        )
    
    def _calculate_macd(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Optional[Dict[str, float]]:
        """Internal method to calculate MACD"""
        try:
            close_prices = self._get_historical_prices(symbol, "1y", refresh_rate_minutes)
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
    
    def get_bollinger_bands(self, symbol: str, window: int = 20, num_std: float = 2.0, refresh_rate_minutes: Optional[int] = None) -> Optional[Dict[str, float]]:
        """
        Calculate Bollinger Bands
        
        Args:
            symbol: Stock symbol
            window: Moving average window
            num_std: Number of standard deviations for bands
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Dictionary with upper, middle, and lower band values or None if data unavailable
        """
        return self._get_calculated_indicator(
            symbol, f'bollinger_{window}_{num_std}', self._calculate_bollinger_bands, window, num_std, refresh_rate_minutes
        )
    
    def _calculate_bollinger_bands(self, symbol: str, window: int = 20, num_std: float = 2.0, refresh_rate_minutes: Optional[int] = None) -> Optional[Dict[str, float]]:
        """Internal method to calculate Bollinger Bands"""
        try:
            close_prices = self._get_historical_prices(symbol, "6mo", refresh_rate_minutes)
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
    
    def get_current_price(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """
        Get current price for a stock (technical perspective)
        
        Args:
            symbol: Stock symbol
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Current price or None if data unavailable
        """
        return self._get_current_price(symbol, refresh_rate_minutes)
    
    def get_price_trend(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Optional[str]:
        """
        Determine price trend based on moving averages
        
        Args:
            symbol: Stock symbol
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Trend ("BULLISH", "BEARISH", "SIDEWAYS") or None if data unavailable
        """
        try:
            sma_20 = self.get_simple_moving_average(symbol, 20, refresh_rate_minutes)
            sma_50 = self.get_simple_moving_average(symbol, 50, refresh_rate_minutes)
            current_price = self.get_current_price(symbol, refresh_rate_minutes)
            
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
    
    def get_volume_trend(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Optional[str]:
        """
        Determine volume trend
        
        Args:
            symbol: Stock symbol
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Volume trend ("HIGH", "LOW", "AVERAGE") or None if data unavailable
        """
        try:
            # Get technical indicators which might include volume trend
            data = self._get_technical_indicators(symbol, refresh_rate_minutes)
            if data and data.get('volume_trend'):
                return data.get('volume_trend')
            
            return None
            
        except Exception as e:
            logger.error(f"Error determining volume trend for {symbol}: {e}")
            return None
    
    def get_support_resistance_levels(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Optional[Dict[str, float]]:
        """
        Identify support and resistance levels
        
        Args:
            symbol: Stock symbol
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Dictionary with support and resistance levels or None if data unavailable
        """
        return self._get_calculated_indicator(
            symbol, 'support_resistance', self._calculate_support_resistance, refresh_rate_minutes
        )
    
    def _calculate_support_resistance(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Optional[Dict[str, float]]:
        """Internal method to calculate support and resistance levels"""
        try:
            close_prices = self._get_historical_prices(symbol, "3mo", refresh_rate_minutes)
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
    
    def get_volatility(self, symbol: str, window: int = 20, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """
        Calculate price volatility
        
        Args:
            symbol: Stock symbol
            window: Number of periods for volatility calculation
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Volatility (standard deviation of returns) or None if data unavailable
        """
        return self._get_calculated_indicator(
            symbol, f'volatility_{window}', self._calculate_volatility, window, refresh_rate_minutes
        )
    
    def _calculate_volatility(self, symbol: str, window: int = 20, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """Internal method to calculate volatility"""
        try:
            close_prices = self._get_historical_prices(symbol, "3mo", refresh_rate_minutes)
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
    
    def get_average_true_range(self, symbol: str, period: int = 14, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """Calculate Average True Range (ATR)"""
        return self._get_calculated_indicator(
            symbol, f'atr_{period}', self._calculate_atr, period, refresh_rate_minutes
        )

    def _calculate_atr(self, symbol: str, period: int = 14, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """Internal method to calculate ATR"""
        try:
            # Try data provider first
            data = self._get_technical_indicators(symbol, refresh_rate_minutes)
            if data and data.get('atr') is not None:
                return float(data.get('atr'))

            # Fallback: approximate using close-to-close absolute differences
            close_prices = self._get_historical_prices(symbol, "3mo", refresh_rate_minutes)
            if not close_prices or len(close_prices) < period + 1:
                return None

            tr_values = [abs(close_prices[i] - close_prices[i - 1]) for i in range(1, len(close_prices))]
            if len(tr_values) < period:
                return None

            return sum(tr_values[-period:]) / period

        except Exception as e:
            logger.error(f"Error calculating ATR for {symbol}: {e}")
            return None

    def get_stochastic(self, symbol: str, period: int = 14, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """Calculate Stochastic %K"""
        return self._get_calculated_indicator(
            symbol, f'stoch_{period}', self._calculate_stochastic, period, refresh_rate_minutes
        )

    def _calculate_stochastic(self, symbol: str, period: int = 14, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """Internal method to calculate Stochastic %K"""
        try:
            # Try data provider first
            data = self._get_technical_indicators(symbol, refresh_rate_minutes)
            if data and data.get('stochastic_k') is not None:
                return float(data.get('stochastic_k'))

            # Fallback: calculate from close prices (close as proxy for high/low)
            close_prices = self._get_historical_prices(symbol, "3mo", refresh_rate_minutes)
            if not close_prices or len(close_prices) < period:
                return None

            recent = close_prices[-period:]
            highest_high = max(recent)
            lowest_low = min(recent)

            if highest_high == lowest_low:
                return 50.0

            stoch_k = (close_prices[-1] - lowest_low) / (highest_high - lowest_low) * 100
            return stoch_k

        except Exception as e:
            logger.error(f"Error calculating Stochastic for {symbol}: {e}")
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
            'atr': self.get_average_true_range(symbol),
            'stoch': self.get_stochastic(symbol),
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
