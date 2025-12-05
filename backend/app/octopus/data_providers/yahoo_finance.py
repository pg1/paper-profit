#!/usr/bin/env python3

import yfinance as yf
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from storage.repositories import RepositoryFactory
from storage.models import Instrument, MarketData, TechnicalIndicator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YahooFinanceService:
    """Yahoo Finance API service for fetching real stock data"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.repo = RepositoryFactory(db_session)
    
    def fetch_stock_info(self, symbol):
        """Fetch basic stock information"""
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            
            stock_data = {
                'symbol': symbol,
                'name': info.get('longName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow')
            }
            
            logger.info(f"Fetched info for {symbol}")
            return stock_data
            
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {e}")
            return None
    
    def fetch_current_price(self, symbol):
        """Fetch current stock price with improved error handling"""
        try:
            stock = yf.Ticker(symbol)
            
            # Try multiple approaches to get current price
            current_price = None
            
            # Approach 1: Try to get current price from info
            try:
                info = stock.info
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                if current_price:
                    logger.debug(f"Got price for {symbol} from info: ${current_price}")
            except Exception as e:
                logger.debug(f"Could not get price from info for {symbol}: {e}")
            
            # Approach 2: Try to get price from history with different periods
            if not current_price:
                for period in ["1d", "5d", "1wk"]:
                    try:
                        hist = stock.history(period=period)
                        if not hist.empty:
                            current_price = hist['Close'].iloc[-1]
                            logger.debug(f"Got price for {symbol} from {period} history: ${current_price}")
                            break
                    except Exception as e:
                        logger.debug(f"Could not get price from {period} history for {symbol}: {e}")
            
            # Approach 3: Try to get price from fast_info
            if not current_price:
                try:
                    fast_info = stock.fast_info
                    current_price = fast_info.get('lastPrice')
                    if current_price:
                        logger.debug(f"Got price for {symbol} from fast_info: ${current_price}")
                except Exception as e:
                    logger.debug(f"Could not get price from fast_info for {symbol}: {e}")
            
            if current_price:
                # Get company information
                try:
                    info = stock.info
                    company_name = info.get('longName') or info.get('shortName') or symbol
                    sector = info.get('sector') or 'Unknown'
                    exchange = info.get('exchange') or 'Unknown'
                    currency = info.get('currency') or 'USD'
                except Exception as e:
                    logger.warning(f"Could not get company info for {symbol}: {e}")
                    company_name = symbol
                    sector = 'Unknown'
                    exchange = 'Unknown'
                    currency = 'USD'
                
                return {
                    'symbol': symbol,
                    'price': current_price,
                    'company_name': company_name,
                    'sector': sector,
                    'exchange': exchange,
                    'currency': currency
                }
            else:
                logger.warning(f"No price data available for {symbol} after multiple attempts")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None
    
    def fetch_historical_data(self, symbol, period="1mo"):
        """Fetch historical stock data for a given period"""
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period=period)
            
            historical_data = []
            for date, row in hist.iterrows():
                data_point = {
                    'symbol': symbol,
                    'date': date.strftime('%Y-%m-%d'),
                    'open_price': row['Open'],
                    'high_price': row['High'],
                    'low_price': row['Low'],
                    'close_price': row['Close'],
                    'volume': row['Volume']
                }
                historical_data.append(data_point)
            
            logger.info(f"Fetched {len(historical_data)} historical data points for {symbol}")
            return historical_data
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
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
                    logger.error(f"Error saving current price for {symbol}: {e}")
        
        logger.info(f"Updated current prices for {updated_count} symbols")
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
                logger.info(f"Saved {saved_count} historical data points for {symbol}")
            except Exception as e:
                logger.error(f"Error saving bulk historical data for {symbol}: {e}")
                saved_count = 0
        
        return saved_count
    
    def get_stock_analysis(self, symbol):
        """Get technical analysis for a stock using storage model"""
        try:
            # Get instrument from storage
            existing_instrument = self.repo.instruments.get_by_symbol(symbol)
            if not existing_instrument:
                logger.warning(f"Instrument {symbol} not found in storage")
                return None
            
            # Fetch current data from Yahoo Finance
            stock = yf.Ticker(symbol)
            hist = stock.history(period="6mo")
            
            if hist.empty:
                return None
            
            # Calculate simple moving averages
            sma_20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
            
            current_price = hist['Close'].iloc[-1]
            
            analysis = {
                'symbol_id': existing_instrument.id,
                'symbol': symbol,
                'current_price': current_price,
                'sma_20': sma_20,
                'sma_50': sma_50,
                'trend': 'BULLISH' if current_price > sma_20 and current_price > sma_50 else 'BEARISH',
                'volume_trend': 'HIGH' if hist['Volume'].iloc[-1] > hist['Volume'].mean() else 'LOW'
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
