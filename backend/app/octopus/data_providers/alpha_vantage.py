#!/usr/bin/env python3

from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData
from datetime import datetime
import logging
import json
from sqlalchemy.orm import Session
from storage.repositories import RepositoryFactory
from storage.models import Instrument, MarketData, TechnicalIndicator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AlphaVantageService:
    """Alpha Vantage API service for fetching real stock data"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.repo = RepositoryFactory(db_session)
        self.api_key = self._get_api_key_from_settings()
        logger.info(f"Alpha Vantage API key loaded: {'***' + self.api_key[-4:] if self.api_key != 'demo' else 'demo key'}")
        self.ts = TimeSeries(key=self.api_key, output_format='pandas')
        self.fd = FundamentalData(key=self.api_key, output_format='pandas')
    
    def _get_api_key_from_settings(self):
        """Get Alpha Vantage API key from settings table"""
        try:
            setting = self.repo.settings.get_by_name('Alpha_vantage')
            if setting and setting.parameters:
                # Parse the JSON parameters field
                params = json.loads(setting.parameters)
                api_key = params.get('key', 'demo')
                logger.info(f"Loaded Alpha Vantage API key from settings table")
                return api_key
            else:
                logger.warning("Alpha_vantage setting not found in database, using demo key")
                return None
        except Exception as e:
            logger.error(f"Error loading Alpha Vantage API key from settings: {e}")
            return None
    
    def fetch_stock_info(self, symbol):
        """Fetch basic stock information using Alpha Vantage"""
        try:
            # Get company overview
            overview, _ = self.fd.get_company_overview(symbol=symbol)
            
            if overview is None or overview.empty:
                logger.warning(f"No company overview data available for {symbol}")
                return None
            
            stock_data = {
                'symbol': symbol,
                'name': overview.get('Name', ['N/A']).iloc[0] if 'Name' in overview else 'N/A',
                'sector': overview.get('Sector', ['N/A']).iloc[0] if 'Sector' in overview else 'N/A',
                'industry': overview.get('Industry', ['N/A']).iloc[0] if 'Industry' in overview else 'N/A',
                'market_cap': float(overview.get('MarketCapitalization', [0]).iloc[0]) if 'MarketCapitalization' in overview else None,
                'pe_ratio': float(overview.get('PERatio', [0]).iloc[0]) if 'PERatio' in overview else None,
                'dividend_yield': float(overview.get('DividendYield', [0]).iloc[0]) if 'DividendYield' in overview else None,
                'beta': float(overview.get('Beta', [0]).iloc[0]) if 'Beta' in overview else None,
                'fifty_two_week_high': float(overview.get('52WeekHigh', [0]).iloc[0]) if '52WeekHigh' in overview else None,
                'fifty_two_week_low': float(overview.get('52WeekLow', [0]).iloc[0]) if '52WeekLow' in overview else None
            }
            
            logger.info(f"Fetched Alpha Vantage info for {symbol}")
            return stock_data
            
        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage info for {symbol}: {e}")
            return None
    
    def fetch_current_price(self, symbol):
        """Fetch current stock price using Alpha Vantage"""
        try:
            # Try to get real-time quote
            quote, _ = self.ts.get_quote_endpoint(symbol=symbol)
            
            if quote is None or quote.empty:
                logger.warning(f"No real-time quote available for {symbol}")
                return None
            
            current_price = None
            
            # Try different price fields
            price_fields = ['05. price', 'latestPrice', 'price']
            for field in price_fields:
                if field in quote.columns:
                    current_price = float(quote[field].iloc[0])
                    break
            
            if current_price is None:
                # Fallback to daily data
                data, _ = self.ts.get_daily(symbol=symbol, outputsize='compact')
                if not data.empty:
                    current_price = float(data['4. close'].iloc[-1])
            
            if current_price:
                # Get company information
                company_info = self.fetch_stock_info(symbol)
                if company_info:
                    company_name = company_info.get('name', symbol)
                    sector = company_info.get('sector', 'Unknown')
                else:
                    company_name = symbol
                    sector = 'Unknown'
                
                return {
                    'symbol': symbol,
                    'price': current_price,
                    'company_name': company_name,
                    'sector': sector,
                    'exchange': 'Unknown',  # Alpha Vantage doesn't provide exchange info
                    'currency': 'USD'  # Default to USD
                }
            else:
                logger.warning(f"No price data available for {symbol} from Alpha Vantage")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol} from Alpha Vantage: {e}")
            return None
    
    def fetch_historical_data(self, symbol, period="1mo"):
        """Fetch historical stock data for a given period using Alpha Vantage"""
        try:
            # Map period to Alpha Vantage output size
            output_size_map = {
                "1d": "compact",
                "5d": "compact", 
                "1mo": "compact",
                "3mo": "compact",
                "6mo": "compact",
                "1y": "compact",
                "2y": "full",
                "5y": "full"
            }
            
            output_size = output_size_map.get(period, "compact")
            
            data, _ = self.ts.get_daily(symbol=symbol, outputsize=output_size)
            
            historical_data = []
            for date, row in data.iterrows():
                data_point = {
                    'symbol': symbol,
                    'date': date.strftime('%Y-%m-%d'),
                    'open_price': float(row['1. open']),
                    'high_price': float(row['2. high']),
                    'low_price': float(row['3. low']),
                    'close_price': float(row['4. close']),
                    'volume': int(row['5. volume'])
                }
                historical_data.append(data_point)
            
            logger.info(f"Fetched {len(historical_data)} historical data points for {symbol} from Alpha Vantage")
            return historical_data
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol} from Alpha Vantage: {e}")
            return []
    
    def save_current_prices(self, symbols):
        """Save current prices for multiple symbols to database using storage model"""
        updated_count = 0
        
        for symbol in symbols:
            stock_data = self.fetch_current_price(symbol)
            if stock_data:
                try:
                    # Check if instrument exists, if not create it
                    existing_instrument = self.repo.instruments.get_by_symbol(symbol)
                    if not existing_instrument:
                        # Create new instrument
                        instrument_data = {
                            'symbol': symbol,
                            'name': stock_data.get('company_name'),
                            'exchange': stock_data.get('exchange'),
                            'currency': stock_data.get('currency')
                        }
                        existing_instrument = self.repo.instruments.create(instrument_data)
                        logger.info(f"Created new instrument: {symbol}")
                    
                    # Save current price as market data
                    market_data = {
                        'symbol_id': existing_instrument.id,
                        'timestamp': datetime.now(),
                        'interval': '1min',
                        'open': stock_data['price'],
                        'high': stock_data['price'],
                        'low': stock_data['price'],
                        'close': stock_data['price'],
                        'volume': 0,  # Volume not available from current price fetch
                        'vwap': stock_data['price']
                    }
                    
                    self.repo.market_data.create(market_data)
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error saving current price for {symbol} from Alpha Vantage: {e}")
        
        logger.info(f"Updated current prices for {updated_count} symbols using Alpha Vantage")
        return updated_count
    
    def save_historical_data(self, symbol, period="1mo"):
        """Save historical data for a symbol to database using storage model"""
        historical_data = self.fetch_historical_data(symbol, period)
        
        if not historical_data:
            return 0
        
        # Check if instrument exists, if not create it
        existing_instrument = self.repo.instruments.get_by_symbol(symbol)
        if not existing_instrument:
            # Create basic instrument entry
            instrument_data = {
                'symbol': symbol,
                'name': symbol,
                'exchange': 'Unknown',
                'currency': 'USD'
            }
            existing_instrument = self.repo.instruments.create(instrument_data)
            logger.info(f"Created new instrument for historical data: {symbol}")
        
        saved_count = 0
        market_data_list = []
        
        for data_point in historical_data:
            try:
                # Convert date string to datetime
                timestamp = datetime.strptime(data_point['date'], '%Y-%m-%d')
                
                market_data = {
                    'symbol_id': existing_instrument.id,
                    'timestamp': timestamp,
                    'interval': '1day',
                    'open': data_point['open_price'],
                    'high': data_point['high_price'],
                    'low': data_point['low_price'],
                    'close': data_point['close_price'],
                    'volume': data_point['volume'],
                    'vwap': data_point['close_price']  # Use close as VWAP approximation
                }
                market_data_list.append(market_data)
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Error processing historical data for {symbol}: {e}")
        
        # Save all market data in bulk
        if market_data_list:
            try:
                self.repo.market_data.create_bulk(market_data_list)
                logger.info(f"Saved {saved_count} historical data points for {symbol} using Alpha Vantage")
            except Exception as e:
                logger.error(f"Error saving bulk historical data for {symbol}: {e}")
                saved_count = 0
        
        return saved_count
    
    def get_stock_analysis(self, symbol):
        """Get technical analysis for a stock using Alpha Vantage"""
        try:
            # Get historical data for analysis
            data, _ = self.ts.get_daily(symbol=symbol, outputsize='full')
            
            if data.empty:
                return None
            
            # Calculate simple moving averages
            sma_20 = data['4. close'].rolling(window=20).mean().iloc[-1]
            sma_50 = data['4. close'].rolling(window=50).mean().iloc[-1]
            
            current_price = data['4. close'].iloc[-1]
            
            analysis = {
                'symbol': symbol,
                'current_price': current_price,
                'sma_20': sma_20,
                'sma_50': sma_50,
                'trend': 'BULLISH' if current_price > sma_20 and current_price > sma_50 else 'BEARISH',
                'volume_trend': 'HIGH' if data['5. volume'].iloc[-1] > data['5. volume'].mean() else 'LOW'
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol} with Alpha Vantage: {e}")
            return None
    
    def get_intraday_data(self, symbol, interval='5min'):
        """Get intraday stock data"""
        try:
            data, _ = self.ts.get_intraday(symbol=symbol, interval=interval, outputsize='compact')
            
            intraday_data = []
            for timestamp, row in data.iterrows():
                data_point = {
                    'symbol': symbol,
                    'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'open_price': float(row['1. open']),
                    'high_price': float(row['2. high']),
                    'low_price': float(row['3. low']),
                    'close_price': float(row['4. close']),
                    'volume': int(row['5. volume'])
                }
                intraday_data.append(data_point)
            
            return intraday_data
            
        except Exception as e:
            logger.error(f"Error fetching intraday data for {symbol}: {e}")
            return []
    
    def get_technical_indicators(self, symbol):
        """Get technical indicators like RSI, MACD, etc."""
        try:
            # Note: This would require additional Alpha Vantage functions
            # For now, return basic indicators calculated from price data
            data, _ = self.ts.get_daily(symbol=symbol, outputsize='full')
            
            if data.empty:
                return None
            
            close_prices = data['4. close']
            
            # Calculate RSI (simplified)
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            indicators = {
                'symbol': symbol,
                'rsi': float(rsi.iloc[-1]) if not rsi.empty else None,
                'current_price': float(close_prices.iloc[-1]),
                'volume': int(data['5. volume'].iloc[-1])
            }
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators for {symbol}: {e}")
            return None
