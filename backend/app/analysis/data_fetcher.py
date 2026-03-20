#!/usr/bin/env python3

"""
Data Fetcher Module

This module provides a unified interface for fetching stock data from various providers
with intelligent caching to minimize API calls.

Key features:
- Single API call per symbol per data type
- In-memory caching with TTL based on refresh_rate from quantitative_data.yaml
- Provider priority: Yahoo Finance first, then fallbacks
- Batch data fetching where possible
"""

import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from octopus.data_providers.alpha_vantage import AlphaVantageService
from octopus.data_providers.financialmodelingprep import FinancialModelingPrepService
from octopus.data_providers.yahoo_finance import YahooFinanceService

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataFetcher:
    """Unified data fetcher with caching for all stock data providers"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.yahoo = YahooFinanceService(db_session)
        self.alpha_vantage = AlphaVantageService(db_session)
        self.fmp = FinancialModelingPrepService(db_session)
        
        # Cache structure: {cache_key: (timestamp, data)}
        self._cache = {}
        
        # Failure tracking: {failure_key: (timestamp, failure_count)}
        self._failures = {}
        
        # Default TTLs in seconds (will be overridden by YAML config)
        self._default_ttls = {
            'fundamental': 3600,  # 1 hour for fundamental data
            'technical': 300,     # 5 minutes for technical data
            'price': 60,          # 1 minute for price data
            'historical': 3600,   # 1 hour for historical data
        }
        
        # Failure backoff settings (in seconds)
        self._failure_backoff = {
            'initial': 300,       # 5 minutes after first failure
            'max': 86400,         # 24 hours maximum backoff
            'multiplier': 2,      # Double backoff time on each failure
        }
        
        #logger.info("DataFetcher initialized with Yahoo-first provider priority and failure tracking")
    
    def _get_cache_key(self, symbol: str, data_type: str, provider: str = None) -> str:
        """Generate cache key for a symbol and data type"""
        if provider:
            return f"{symbol}_{data_type}_{provider}"
        return f"{symbol}_{data_type}"
    
    def _is_cache_valid(self, cache_key: str, ttl_seconds: int) -> bool:
        """Check if cached data is still valid based on TTL"""
        if cache_key not in self._cache:
            return False
        
        timestamp, _ = self._cache[cache_key]
        age_seconds = time.time() - timestamp
        
        return age_seconds < ttl_seconds
    
    def _get_from_cache(self, cache_key: str, ttl_seconds: int) -> Optional[Any]:
        """Get data from cache if valid"""
        if self._is_cache_valid(cache_key, ttl_seconds):
            _, data = self._cache[cache_key]
            logger.debug(f"Cache hit for {cache_key}")
            return data
        
        logger.debug(f"Cache miss for {cache_key}")
        return None
    
    def _set_to_cache(self, cache_key: str, data: Any):
        """Store data in cache with current timestamp"""
        self._cache[cache_key] = (time.time(), data)
        logger.debug(f"Cached data for {cache_key}")
    
    def _get_ttl_for_data_type(self, data_type: str, refresh_rate_minutes: Optional[int] = None) -> int:
        """Get TTL in seconds for a data type"""
        if refresh_rate_minutes is not None:
            # Convert minutes to seconds
            return refresh_rate_minutes * 60
        
        # Use default TTLs based on data type
        return self._default_ttls.get(data_type, 300)  # Default 5 minutes
    
    def _get_failure_key(self, symbol: str, provider: str, data_type: str) -> str:
        """Generate failure tracking key"""
        return f"{symbol}_{provider}_{data_type}"
    
    def _should_skip_provider(self, symbol: str, provider: str, data_type: str) -> bool:
        """Check if we should skip a provider due to recent failures"""
        failure_key = self._get_failure_key(symbol, provider, data_type)
        
        if failure_key not in self._failures:
            return False
        
        failure_time, failure_count = self._failures[failure_key]
        time_since_failure = time.time() - failure_time
        
        # Calculate backoff time (exponential backoff)
        backoff_time = self._failure_backoff['initial'] * (self._failure_backoff['multiplier'] ** (failure_count - 1))
        backoff_time = min(backoff_time, self._failure_backoff['max'])
        
        if time_since_failure < backoff_time:
            logger.debug(f"Skipping {provider} for {symbol} {data_type} (backoff: {backoff_time/60:.1f} minutes)")
            return True
        
        return False
    
    def _record_failure(self, symbol: str, provider: str, data_type: str):
        """Record a failure for a provider"""
        failure_key = self._get_failure_key(symbol, provider, data_type)
        
        if failure_key in self._failures:
            failure_time, failure_count = self._failures[failure_key]
            self._failures[failure_key] = (time.time(), failure_count + 1)
            logger.warning(f"Recorded failure #{failure_count + 1} for {provider} on {symbol} {data_type}")
        else:
            self._failures[failure_key] = (time.time(), 1)
            logger.warning(f"Recorded first failure for {provider} on {symbol} {data_type}")
    
    def _record_success(self, symbol: str, provider: str, data_type: str):
        """Record a success for a provider (clear failures)"""
        failure_key = self._get_failure_key(symbol, provider, data_type)
        if failure_key in self._failures:
            del self._failures[failure_key]
            logger.debug(f"Cleared failure record for {provider} on {symbol} {data_type}")
    
    def _try_provider(self, symbol: str, provider: str, data_type: str, fetch_func, *args, **kwargs):
        """Try a provider with failure tracking"""
        # Check if we should skip this provider due to failures
        if self._should_skip_provider(symbol, provider, data_type):
            return None
        
        try:
            result = fetch_func(*args, **kwargs)
            if result:
                # Record success if we got valid data
                self._record_success(symbol, provider, data_type)
            return result
        except Exception as e:
            # Record failure
            self._record_failure(symbol, provider, data_type)
            logger.debug(f"{provider} failed for {symbol} {data_type}: {e}")
            return None
    
    def fetch_fundamental_data(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch fundamental data for a symbol with caching
        
        Args:
            symbol: Stock symbol
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Dictionary with fundamental data or empty dict if unavailable
        """
        cache_key = self._get_cache_key(symbol, 'fundamental')
        ttl_seconds = self._get_ttl_for_data_type('fundamental', refresh_rate_minutes)
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key, ttl_seconds)
        if cached_data is not None:
            return cached_data
        
        logger.info(f"Fetching fundamental data for {symbol} (cache miss)")
        
        # Try Yahoo Finance first
        data = self._try_provider(symbol, 'yahoo', 'fundamental', self.yahoo.fetch_stock_info, symbol)
        if data and data.get('pe_ratio') is not None:
            logger.info(f"Using Yahoo Finance fundamental data for {symbol}")
            self._set_to_cache(cache_key, data)
            return data
        
        # Try Financial Modeling Prep
        data = self._try_provider(symbol, 'fmp', 'fundamental', self.fmp.fetch_stock_info, symbol)
        if data and data.get('pe_ratio') is not None:
            logger.info(f"Using Financial Modeling Prep fundamental data for {symbol}")
            self._set_to_cache(cache_key, data)
            return data
        
        # Try Alpha Vantage
        data = self._try_provider(symbol, 'alpha_vantage', 'fundamental', self.alpha_vantage.fetch_stock_info, symbol)
        if data and data.get('pe_ratio') is not None:
            logger.info(f"Using Alpha Vantage fundamental data for {symbol}")
            self._set_to_cache(cache_key, data)
            return data
        
        logger.warning(f"No fundamental data available for {symbol} from any provider")
        return {}
    
    def fetch_current_price(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Optional[float]:
        """
        Fetch current price for a symbol with caching
        
        Args:
            symbol: Stock symbol
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Current price or None if unavailable
        """
        cache_key = self._get_cache_key(symbol, 'price')
        ttl_seconds = self._get_ttl_for_data_type('price', refresh_rate_minutes)
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key, ttl_seconds)
        if cached_data is not None:
            return cached_data
        
        logger.info(f"Fetching current price for {symbol} (cache miss)")
        
        # Try Yahoo Finance first
        price_data = self._try_provider(symbol, 'yahoo', 'price', self.yahoo.fetch_current_price, symbol)
        if price_data and price_data.get('price'):
            price = price_data['price']
            logger.info(f"Using Yahoo Finance price for {symbol}: ${price:.2f}")
            self._set_to_cache(cache_key, price)
            return price
        
        # Try Alpha Vantage
        price_data = self._try_provider(symbol, 'alpha_vantage', 'price', self.alpha_vantage.fetch_current_price, symbol)
        if price_data and price_data.get('price'):
            price = price_data['price']
            logger.info(f"Using Alpha Vantage price for {symbol}: ${price:.2f}")
            self._set_to_cache(cache_key, price)
            return price
        
        # Try Financial Modeling Prep
        price_data = self._try_provider(symbol, 'fmp', 'price', self.fmp.fetch_current_price, symbol)
        if price_data and price_data.get('price'):
            price = price_data['price']
            logger.info(f"Using Financial Modeling Prep price for {symbol}: ${price:.2f}")
            self._set_to_cache(cache_key, price)
            return price
        
        logger.warning(f"No price data available for {symbol} from any provider")
        return None
    
    def fetch_historical_prices(self, symbol: str, period: str = "6mo", 
                                refresh_rate_minutes: Optional[int] = None) -> Optional[List[float]]:
        """
        Fetch historical closing prices for a symbol with caching
        
        Args:
            symbol: Stock symbol
            period: Time period (e.g., "6mo", "1y")
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            List of closing prices or None if unavailable
        """
        cache_key = self._get_cache_key(symbol, f'historical_{period}')
        ttl_seconds = self._get_ttl_for_data_type('historical', refresh_rate_minutes)
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key, ttl_seconds)
        if cached_data is not None:
            return cached_data
        
        logger.info(f"Fetching historical prices for {symbol} period={period} (cache miss)")
        
        # Try Yahoo Finance first
        historical_data = self._try_provider(symbol, 'yahoo', 'historical', self.yahoo.fetch_historical_data, symbol, period)
        if historical_data:
            close_prices = [data['close_price'] for data in historical_data]
            logger.info(f"Using Yahoo Finance historical data for {symbol}: {len(close_prices)} data points")
            self._set_to_cache(cache_key, close_prices)
            return close_prices
        
        # Try Alpha Vantage
        historical_data = self._try_provider(symbol, 'alpha_vantage', 'historical', self.alpha_vantage.fetch_historical_data, symbol, period)
        if historical_data:
            close_prices = [data['close_price'] for data in historical_data]
            logger.info(f"Using Alpha Vantage historical data for {symbol}: {len(close_prices)} data points")
            self._set_to_cache(cache_key, close_prices)
            return close_prices
        
        # Try Financial Modeling Prep
        historical_data = self._try_provider(symbol, 'fmp', 'historical', self.fmp.fetch_historical_data, symbol, period)
        if historical_data:
            close_prices = [data['close_price'] for data in historical_data]
            logger.info(f"Using Financial Modeling Prep historical data for {symbol}: {len(close_prices)} data points")
            self._set_to_cache(cache_key, close_prices)
            return close_prices
        
        logger.warning(f"No historical data available for {symbol} period={period} from any provider")
        return None
    
    def fetch_technical_indicators(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch technical indicators for a symbol with caching
        
        Args:
            symbol: Stock symbol
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Dictionary with technical indicators or empty dict if unavailable
        """
        cache_key = self._get_cache_key(symbol, 'technical')
        ttl_seconds = self._get_ttl_for_data_type('technical', refresh_rate_minutes)
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key, ttl_seconds)
        if cached_data is not None:
            return cached_data
        
        logger.info(f"Fetching technical indicators for {symbol} (cache miss)")
        
        # Try Alpha Vantage first for technical indicators
        data = self._try_provider(symbol, 'alpha_vantage', 'technical', self.alpha_vantage.get_technical_indicators, symbol)
        if data and data.get('rsi') is not None:
            logger.info(f"Using Alpha Vantage technical indicators for {symbol}")
            self._set_to_cache(cache_key, data)
            return data
        
        # Try Yahoo Finance
        data = self._try_provider(symbol, 'yahoo', 'technical', self.yahoo.get_stock_analysis, symbol)
        if data:
            logger.info(f"Using Yahoo Finance technical analysis for {symbol}")
            self._set_to_cache(cache_key, data)
            return data
        
        # Try Financial Modeling Prep
        data = self._try_provider(symbol, 'fmp', 'technical', self.fmp.get_stock_analysis, symbol)
        if data:
            logger.info(f"Using Financial Modeling Prep stock analysis for {symbol}")
            self._set_to_cache(cache_key, data)
            return data
        
        logger.warning(f"No technical indicators available for {symbol} from any provider")
        return {}
    
    def fetch_quantitative_data(self, symbol: str, refresh_rate_minutes: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch quantitative data for a symbol with caching
        
        Args:
            symbol: Stock symbol
            refresh_rate_minutes: Optional refresh rate in minutes from YAML config
            
        Returns:
            Dictionary with quantitative data or empty dict if unavailable
        """
        cache_key = self._get_cache_key(symbol, 'quantitative')
        ttl_seconds = self._get_ttl_for_data_type('fundamental', refresh_rate_minutes)  # Use fundamental TTL
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key, ttl_seconds)
        if cached_data is not None:
            return cached_data
        
        logger.info(f"Fetching quantitative data for {symbol} (cache miss)")
        
        # Try Yahoo Finance first (has quantitative data method)
        data = self._try_provider(symbol, 'yahoo', 'quantitative', self.yahoo.fetch_quantitative_data, symbol)
        if data:
            logger.info(f"Using Yahoo Finance quantitative data for {symbol}")
            self._set_to_cache(cache_key, data)
            return data
        
        # For other providers, we'd need to implement similar methods
        # For now, return empty dict
        logger.warning(f"No quantitative data available for {symbol} from any provider")
        return {}
    
    def clear_cache(self, symbol: str = None, data_type: str = None):
        """
        Clear cache for specific symbol and/or data type
        
        Args:
            symbol: Optional stock symbol to clear
            data_type: Optional data type to clear
        """
        if symbol is None and data_type is None:
            # Clear all cache
            self._cache.clear()
            logger.info("Cleared all cache")
        elif symbol is not None and data_type is not None:
            # Clear specific symbol and data type
            cache_key = self._get_cache_key(symbol, data_type)
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.info(f"Cleared cache for {symbol} {data_type}")
        elif symbol is not None:
            # Clear all cache for symbol
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(f"{symbol}_")]
            for key in keys_to_delete:
                del self._cache[key]
            logger.info(f"Cleared all cache for {symbol}")
        elif data_type is not None:
            # Clear all cache for data type
            keys_to_delete = [k for k in self._cache.keys() if f"_{data_type}" in k]
            for key in keys_to_delete:
                del self._cache[key]
            logger.info(f"Cleared all cache for data type {data_type}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_items = len(self._cache)
        cache_size = sum(len(str(v)) for v in self._cache.values())
        
        # Count by data type
        by_data_type = {}
        for key in self._cache.keys():
            # Extract data type from key (symbol_datatype or symbol_datatype_provider)
            parts = key.split('_')
            if len(parts) >= 2:
                data_type = parts[1]
                by_data_type[data_type] = by_data_type.get(data_type, 0) + 1
        
        return {
            'total_items': total_items,
            'cache_size_bytes': cache_size,
            'by_data_type': by_data_type
        }


# Convenience function for direct usage
def create_data_fetcher(db_session: Session) -> DataFetcher:
    """
    Create a DataFetcher instance
    
    Args:
        db_session: Database session
        
    Returns:
        DataFetcher instance
    """
    return DataFetcher(db_session)