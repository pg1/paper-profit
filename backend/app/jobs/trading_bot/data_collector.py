import logging
import yaml
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from storage.repositories import RepositoryFactory
from storage.models import TradingSignal
from octopus.data_providers.yahoo_finance import YahooFinanceService
from analysis.technical_functions import TechnicalFunctions
from analysis.fundamental_functions import FundamentalFunctions

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)  # Set logger level


class DataCollector:
    """Module for collecting market data and technical indicators"""
    
    def __init__(self, db: Session, repo_factory: RepositoryFactory):
        self.db = db
        self.repo_factory = repo_factory
        self.yahoo_service = YahooFinanceService(db)
        self.technical_functions = TechnicalFunctions(db)
        self.fundamental_functions = FundamentalFunctions(db)
        
        # Cache for YAML configuration
        self._quantitative_config = None
        self._config_loaded = False
    
    def _load_quantitative_config(self) -> Dict[str, Dict[str, Any]]:
        """Load and cache quantitative data configuration from YAML file"""
        if self._config_loaded:
            return self._quantitative_config
        
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'config', 'quantitative_data.yaml'
            )
            
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Extract the quantitative_data section from YAML
            if not config_data or 'quantitative_data' not in config_data:
                logger.error("No quantitative_data section found in YAML configuration")
                return {}
            
            # Flatten the nested YAML structure (only the quantitative_data section)
            self._quantitative_config = self._flatten_yaml_config(config_data['quantitative_data'])
            self._config_loaded = True
            
            logger.debug(f"Loaded quantitative data configuration with {len(self._quantitative_config)} metrics")
            return self._quantitative_config
            
        except Exception as e:
            logger.error(f"Error loading quantitative data configuration: {str(e)}")
            return {}
    
    def _flatten_yaml_config(self, config_data: Dict, parent_key: str = '', sep: str = '.') -> Dict[str, Dict[str, Any]]:
        """Flatten nested YAML configuration into flat dictionary"""
        flat_config = {}
        
        if not config_data:
            return flat_config
        
        for key, value in config_data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            
            if isinstance(value, dict):
                # Check if this is a metric definition (has 'refresh_rate' key)
                if 'refresh_rate' in value:
                    flat_config[new_key] = value
                else:
                    # Continue flattening nested structure
                    flat_config.update(self._flatten_yaml_config(value, new_key, sep))
            else:
                # Skip non-dict values
                continue
        
        return flat_config
    
    def _check_needs_refresh(self, symbol_id: int, metric_name: str, refresh_rate: int) -> bool:
        """Check if a metric needs refresh based on last update time and refresh rate"""
        try:
            # Get latest entry for this symbol and metric
            latest = self.repo_factory.quantitative_data.get_latest(
                symbol_id, meta=metric_name, limit=1
            )
            
            if not latest:
                logger.debug(f"No existing data for {metric_name}, needs refresh")
                return True  # No existing data, needs refresh
            
            last_update = latest[0].timestamp
            time_diff = datetime.now() - last_update
            minutes_diff = time_diff.total_seconds() / 60
            
            # Debug logging
            logger.debug(f"Checking refresh for {metric_name}: last_update={last_update}, "
                        f"minutes_diff={minutes_diff:.2f}, refresh_rate={refresh_rate}")
            
            # Check if refresh_rate minutes have passed
            needs_refresh = minutes_diff > refresh_rate
            if needs_refresh:
                logger.debug(f"Metric {metric_name} needs refresh ({minutes_diff:.2f} > {refresh_rate} minutes)")
            else:
                logger.debug(f"Metric {metric_name} is fresh ({minutes_diff:.2f} <= {refresh_rate} minutes)")
            
            return needs_refresh
            
        except Exception as e:
            logger.debug(f"Error checking refresh for {metric_name}: {str(e)}")
            return True  # On error, assume refresh is needed
    
    def _get_metrics_needing_refresh(self, symbol_id: int) -> Dict[str, Dict[str, Any]]:
        """Get all metrics that need refresh based on their refresh_rate.
        
        Returns a dict of metric_name -> config for metrics that are stale.
        """
        config = self._load_quantitative_config()
        stale_metrics = {}
        
        for yaml_metric_name, metric_config in config.items():
            refresh_rate = metric_config.get('refresh_rate')
            if refresh_rate is None:
                continue  # Skip metrics without refresh_rate
            
            if self._check_needs_refresh(symbol_id, yaml_metric_name, refresh_rate):
                stale_metrics[yaml_metric_name] = metric_config
        
        return stale_metrics
    
    def _get_cached_quantitative_data(self, symbol_id: int) -> Dict[str, Any]:
        """Get all fresh quantitative data from database cache.
        
        Returns a dict of metric_name -> value for metrics that are still fresh.
        """
        config = self._load_quantitative_config()
        cached_data = {}
        
        for yaml_metric_name, metric_config in config.items():
            refresh_rate = metric_config.get('refresh_rate')
            if refresh_rate is None:
                continue
            
            # Check if data is still fresh
            if not self._check_needs_refresh(symbol_id, yaml_metric_name, refresh_rate):
                # Get the cached value
                latest = self.repo_factory.quantitative_data.get_latest(
                    symbol_id, meta=yaml_metric_name, limit=1
                )
                if latest:
                    try:
                        cached_data[yaml_metric_name] = float(latest[0].value)
                    except (ValueError, TypeError):
                        cached_data[yaml_metric_name] = latest[0].value
        
        return cached_data
    
    def _categorize_stale_metrics(self, stale_metrics: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """Categorize stale metrics by their data source (technical, fundamental, market, etc.)"""
        categories = {
            'technical': [],
            'fundamental': [],
            'market': [],
            'microstructure': [],
            'options': [],
            'sentiment': []
        }
        
        for metric_name in stale_metrics.keys():
            # Extract the top-level category from metric name
            parts = metric_name.split('.')
            if len(parts) >= 2:
                category = parts[0]
                if category in categories:
                    categories[category].append(metric_name)
        
        return categories
    
    def _gather_quantitative_data_for_categories(self, symbol: str, categories: Dict[str, List[str]]) -> Dict[str, Any]:
        """Gather quantitative data only for specified categories that have stale metrics.
        
        Args:
            symbol: The stock symbol
            categories: Dict mapping category names to list of stale metric names
            
        Returns:
            Dict of metric_name -> value for fetched data
        """
        all_data = {}
        
        # Check if we need market/yahoo data
        needs_market = bool(categories.get('market'))
        needs_microstructure = bool(categories.get('microstructure'))
        needs_options = bool(categories.get('options'))
        needs_sentiment = bool(categories.get('sentiment'))
        
        # 1. Get data from Yahoo Finance Service (only if market-related categories need refresh)
        if needs_market or needs_microstructure or needs_options or needs_sentiment:
            try:
                yahoo_data = self.yahoo_service.fetch_quantitative_data(symbol)
                if yahoo_data:
                    all_data.update(yahoo_data)
                    logger.debug(f"Got {len(yahoo_data)} metrics from Yahoo Finance for {symbol}")
            except Exception as e:
                logger.debug(f"Error fetching Yahoo Finance data for {symbol}: {str(e)}")
        
        # 2. Get technical indicators (only if technical category needs refresh)
        if categories.get('technical'):
            try:
                technical_data = self.technical_functions.get_all_technical_indicators(symbol)
                if technical_data:
                    # Flatten nested technical data
                    for key, value in technical_data.items():
                        if isinstance(value, dict):
                            # Handle nested dicts like MACD, Bollinger Bands
                            for sub_key, sub_value in value.items():
                                all_data[f"{key}_{sub_key}"] = sub_value
                        else:
                            all_data[key] = value
                    logger.debug(f"Got {len(technical_data)} technical indicators for {symbol}")
            except Exception as e:
                logger.debug(f"Error fetching technical indicators for {symbol}: {str(e)}")
        
        # 3. Get fundamental data (only if fundamental category needs refresh)
        if categories.get('fundamental'):
            try:
                fundamental_data = self.fundamental_functions.get_all_parameters(symbol)
                if fundamental_data:
                    all_data.update(fundamental_data)
                    logger.debug(f"Got {len(fundamental_data)} fundamental metrics for {symbol}")
            except Exception as e:
                logger.debug(f"Error fetching fundamental data for {symbol}: {str(e)}")
        
        return all_data
    
    def _gather_all_quantitative_data(self, symbol: str) -> Dict[str, Any]:
        """Gather quantitative data from all available sources (legacy method for full refresh)"""
        # Create categories dict with all categories populated to trigger full fetch
        all_categories = {
            'technical': ['all'],
            'fundamental': ['all'],
            'market': ['all'],
            'microstructure': ['all'],
            'options': ['all'],
            'sentiment': ['all']
        }
        return self._gather_quantitative_data_for_categories(symbol, all_categories)
    
    def _map_metric_name(self, yaml_metric_name: str, available_data: Dict[str, Any]) -> Optional[str]:
        """Map YAML metric name to available data key"""
        # Try direct match first
        if yaml_metric_name in available_data:
            return yaml_metric_name
        
        # Try to map common metric names
        metric_mapping = {
            # Technical metrics
            'technical.trend.sma_20': 'sma_20',
            'technical.trend.sma_50': 'sma_50',
            'technical.trend.sma_200': 'sma_200',
            'technical.trend.ema_12': 'ema_12',
            'technical.trend.ema_26': 'ema_26',
            'technical.momentum.rsi': 'rsi',
            'technical.oscillators.macd': 'macd_macd',
            'technical.oscillators.macd_signal': 'macd_signal',
            'technical.oscillators.macd_histogram': 'macd_histogram',
            'technical.volatility.bb_upper': 'bollinger_bands_upper',
            'technical.volatility.bb_middle': 'bollinger_bands_middle',
            'technical.volatility.bb_lower': 'bollinger_bands_lower',
            
            # Fundamental metrics
            'fundamental.valuation.pe': 'pe_ratio',
            'fundamental.valuation.pb': 'pb_ratio',
            'fundamental.valuation.peg': 'peg_ratio',
            'fundamental.dividends.dividend_yield': 'dividend_yield',
            'fundamental.profitability.roe': 'roe',
            'fundamental.growth.revenue_growth_yoy': 'revenue_growth',
            'fundamental.growth.eps_growth_yoy': 'eps_growth',
            
            # Market metrics
            'market.pricing.last_price': 'current_price',
        }
        
        mapped_name = metric_mapping.get(yaml_metric_name)
        if mapped_name and mapped_name in available_data:
            return mapped_name
        
        # Try to extract base name from YAML path
        base_name = yaml_metric_name.split('.')[-1]
        if base_name in available_data:
            return base_name
        
        return None
    
    def get_latest_market_data(self, symbol_id: int) -> Optional[Dict[str, Any]]:
        """Get latest market data for a symbol.
        
        Checks database freshness using refresh_rate from quantitative_data.yaml 
        (market.pricing.last_price = 1 minute) before calling external APIs.
        """
        # Get refresh_rate for market pricing from config (default 1 minute)
        config = self._load_quantitative_config()
        refresh_rate = 1  # Default 1 minute for market data
        if config and 'market.pricing.last_price' in config:
            refresh_rate = config['market.pricing.last_price'].get('refresh_rate', 1)
        
        # STEP 1: Check cached quantitative data for fresh price
        cached_price = self.repo_factory.quantitative_data.get_latest(
            symbol_id, meta='market.pricing.last_price', limit=1
        )
        if cached_price:
            last_update = cached_price[0].timestamp
            time_diff = datetime.now() - last_update
            
            # If data is fresh (within refresh_rate minutes), use cached value
            if time_diff.total_seconds() / 60 <= refresh_rate:
                try:
                    current_price = float(cached_price[0].value)
                    logger.debug(f"Using cached market data for symbol_id {symbol_id}")
                    return {
                        'timestamp': last_update,
                        'open': current_price,
                        'high': current_price,
                        'low': current_price,
                        'close': current_price,
                        'volume': 1000000,
                        'vwap': current_price
                    }
                except (ValueError, TypeError):
                    pass  # Fall through to fetch from other sources
        
        # STEP 2: Check market_data table
        try:
            market_data = self.repo_factory.market_data.get_latest(symbol_id, '1day', limit=1)
            if market_data:
                latest = market_data[0]
                time_diff = datetime.now() - latest.timestamp
                
                # If market_data is fresh, use it
                if time_diff.total_seconds() / 60 <= refresh_rate:
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
        
        # STEP 3: Fallback - fetch from Yahoo Finance only if data is stale
        try:
            instrument = self.repo_factory.instruments.get_by_id(symbol_id)
            if instrument:
                logger.info(f"Fetching current price for {instrument.symbol} from Yahoo Finance (data stale)...")
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
    
    def get_technical_indicators(self, symbol_id: int) -> Dict[str, Any]:
        """Get latest technical indicators for a symbol using technical analysis module.
        
        Checks database freshness using refresh_rate from quantitative_data.yaml 
        before recalculating indicators.
        """
        try:
            # Get instrument symbol
            instrument = self.repo_factory.instruments.get_by_id(symbol_id)
            if not instrument:
                return {}
            
            symbol = instrument.symbol
            
            # Get refresh_rate for technical indicators from config
            config = self._load_quantitative_config()
            
            # Check if we have fresh technical data in quantitative_data table
            fresh_indicators = {}
            if config:
                # Common technical metrics to check
                technical_metrics = [
                    'technical.momentum.rsi',
                    'technical.trend.sma_20',
                    'technical.trend.sma_50',
                    'technical.trend.sma_200',
                    'technical.oscillators.macd',
                    'technical.oscillators.macd_signal',
                    'technical.oscillators.macd_histogram',
                    'technical.volatility.bb_upper',
                    'technical.volatility.bb_middle',
                    'technical.volatility.bb_lower'
                ]
                
                for metric_name in technical_metrics:
                    if metric_name in config:
                        refresh_rate = config[metric_name].get('refresh_rate', 1)
                        if not self._check_needs_refresh(symbol_id, metric_name, refresh_rate):
                            # Get cached value
                            latest = self.repo_factory.quantitative_data.get_latest(
                                symbol_id, meta=metric_name, limit=1
                            )
                            if latest:
                                try:
                                    fresh_indicators[metric_name] = float(latest[0].value)
                                except (ValueError, TypeError):
                                    fresh_indicators[metric_name] = latest[0].value
            
            # If we have fresh data for all key metrics, return them
            if len(fresh_indicators) >= 5:  # Arbitrary threshold - if we have at least 5 fresh metrics
                logger.debug(f"Using cached technical indicators for {symbol}")
                return fresh_indicators
            
            # Otherwise, calculate fresh indicators
            logger.debug(f"Calculating fresh technical indicators for {symbol}")
            indicators = self.technical_functions.get_all_technical_indicators(symbol)
            
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
    
    def get_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        """Get fundamental data for a symbol.
        
        Checks database freshness using refresh_rate from quantitative_data.yaml 
        before calling external APIs.
        """
        try:
            # Get instrument ID from symbol
            instrument = self.repo_factory.instruments.get_by_symbol(symbol)
            if not instrument:
                return {}
            
            symbol_id = instrument.id
            
            # Get refresh_rate for fundamental data from config (default 1440 minutes = 24 hours)
            config = self._load_quantitative_config()
            
            # Check if we have fresh fundamental data in quantitative_data table
            fresh_fundamentals = {}
            if config:
                # Common fundamental metrics to check
                fundamental_metrics = [
                    'fundamental.valuation.pe',
                    'fundamental.valuation.pb',
                    'fundamental.valuation.peg',
                    'fundamental.dividends.dividend_yield',
                    'fundamental.profitability.roe',
                    'fundamental.growth.revenue_growth_yoy',
                    'fundamental.growth.eps_growth_yoy'
                ]
                
                for metric_name in fundamental_metrics:
                    if metric_name in config:
                        refresh_rate = config[metric_name].get('refresh_rate', 1440)  # Default 24 hours
                        if not self._check_needs_refresh(symbol_id, metric_name, refresh_rate):
                            # Get cached value
                            latest = self.repo_factory.quantitative_data.get_latest(
                                symbol_id, meta=metric_name, limit=1
                            )
                            if latest:
                                try:
                                    fresh_fundamentals[metric_name] = float(latest[0].value)
                                except (ValueError, TypeError):
                                    fresh_fundamentals[metric_name] = latest[0].value
            
            # If we have fresh data for key metrics, return them
            if len(fresh_fundamentals) >= 3:  # Arbitrary threshold - if we have at least 3 fresh metrics
                logger.debug(f"Using cached fundamental data for {symbol}")
                return fresh_fundamentals
            
            # Otherwise, fetch fresh fundamental data
            logger.debug(f"Fetching fresh fundamental data for {symbol}")
            return self.fundamental_functions.get_all_parameters(symbol)
            
        except Exception as e:
            logger.error(f"Error getting fundamental data for {symbol}: {str(e)}")
            return {}

    def collect_quantitative_data(self, symbol_id: int) -> int:
        """Fetch quantitative metrics from all sources and save to quantitative_data table.
        
        Optimized to check database freshness FIRST using refresh_rate from 
        quantitative_data.yaml, and only fetch data from external APIs if needed.
        
        Returns the number of metrics successfully saved.
        """
        # Get instrument symbol
        instrument = self.repo_factory.instruments.get_by_id(symbol_id)
        if not instrument:
            return 0

        symbol = instrument.symbol
        
        # Load YAML configuration
        config = self._load_quantitative_config()
        if not config:
            logger.warning(f"No quantitative data configuration loaded for {symbol}")
            return 0
        
        logger.debug(f"Loaded {len(config)} metrics from YAML config for {symbol}")
        
        # STEP 1: Check which metrics need refresh BEFORE making any API calls
        stale_metrics = self._get_metrics_needing_refresh(symbol_id)
        
        logger.debug(f"Found {len(stale_metrics)} stale metrics out of {len(config)} total metrics")
        
        if not stale_metrics:
            logger.info(f"All metrics are fresh for {symbol}, skipping API calls")
            return 0
        
        # Log some sample stale metrics
        sample_stale = list(stale_metrics.keys())[:5]
        logger.debug(f"Sample stale metrics: {sample_stale}")
        
        # STEP 2: Categorize stale metrics by data source
        categories = self._categorize_stale_metrics(stale_metrics)
        
        # Log which categories need refresh
        stale_categories = [cat for cat, metrics in categories.items() if metrics]
        logger.info(f"Stale categories for {symbol}: {stale_categories}")
        
        # STEP 3: Only fetch data for categories that have stale metrics
        logger.debug(f"Fetching data for stale categories: {stale_categories}")
        all_data = self._gather_quantitative_data_for_categories(symbol, categories)
        
        if not all_data:
            logger.warning(f"No quantitative data fetched for {symbol}")
            return 0
        
        logger.debug(f"Fetched {len(all_data)} data points for {symbol}")
        
        timestamp = datetime.now()
        saved = 0
        
        # STEP 4: Process only stale metrics
        for yaml_metric_name, metric_config in stale_metrics.items():
            # Map YAML metric name to available data key
            data_key = self._map_metric_name(yaml_metric_name, all_data)
            if not data_key:
                logger.debug(f"Metric {yaml_metric_name} not found in fetched data")
                continue  # Metric not available in fetched data
            
            value = all_data.get(data_key)
            if value is None:
                logger.debug(f"Metric {yaml_metric_name} has null value")
                continue  # Skip null values
            
            # Save to database
            try:
                self.repo_factory.quantitative_data.upsert(
                    symbol_id=symbol_id,
                    timestamp=timestamp,
                    meta=yaml_metric_name,
                    value=str(value),
                )
                saved += 1
                logger.debug(f"Saved metric {yaml_metric_name} = {value}")
            except Exception as e:
                logger.debug(f"Error saving quantitative metric '{yaml_metric_name}' for {symbol}: {str(e)}")
        
        # Log single summary line
        if saved > 0:
            logger.info(f"Saved {saved} quantitative metrics for {symbol}")
        else:
            logger.warning(f"No metrics saved for {symbol} despite fetching data")
        
        return saved
