#!/usr/bin/env python3

import requests
from datetime import datetime
import logging
import json
from sqlalchemy.orm import Session
from storage.repositories import RepositoryFactory
from storage.models import Instrument, MarketData, TechnicalIndicator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinancialModelingPrepService:
    """Financial Modeling Prep API service for fetching real stock data"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.repo = RepositoryFactory(db_session)
        self.api_key = self._get_api_key_from_settings()
        self.base_url = "https://financialmodelingprep.com/stable/"
        logger.info(f"Financial Modeling Prep API key loaded: {'***' + self.api_key[-4:] if self.api_key != 'demo' else 'demo key'}")
    
    def _get_api_key_from_settings(self):
        """Get Financial Modeling Prep API key from settings table"""
        try:
            setting = self.repo.settings.get_by_name('Financial_modeling_prep')
            if setting and setting.parameters:
                # Parse the JSON parameters field
                params = json.loads(setting.parameters)
                api_key = params.get('key', 'demo')
                logger.info(f"Loaded Financial Modeling Prep API key from settings table")
                return api_key
            else:
                logger.warning("Financial_modeling_prep setting not found in database, using demo key")
                return 'demo'
        except Exception as e:
            logger.error(f"Error loading Financial Modeling Prep API key from settings: {e}")
            return 'demo'
    
    def _make_api_request(self, endpoint, params=None):
        """Make API request to Financial Modeling Prep"""
        try:
            if params is None:
                params = {}
            
            params['apikey'] = self.api_key
            
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for subscription requirement error
            if isinstance(data, dict) and 'Error Message' in data:
                error_msg = data['Error Message']
                if 'Legacy Endpoint' in error_msg or 'subscription' in error_msg.lower():
                    logger.warning(f"Financial Modeling Prep subscription required for {endpoint}: {error_msg}")
                    return None
            
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing API response for {endpoint}: {e}")
            return None
    
    def fetch_stock_info(self, symbol):
        """Fetch basic stock information using Financial Modeling Prep"""
        try:
            # Get company profile
            data = self._make_api_request(f"profile/?symbol={symbol}")
            
            if not data or len(data) == 0:
                logger.warning(f"No company profile data available for {symbol}")
                return None
            
            company_data = data[0]
            
            stock_data = {
                'symbol': symbol,
                'name': company_data.get('companyName', 'N/A'),
                'sector': company_data.get('sector', 'N/A'),
                'industry': company_data.get('industry', 'N/A'),
                'market_cap': company_data.get('mktCap'),
                'pe_ratio': company_data.get('pe'),
                'beta': company_data.get('beta'),
                'fifty_two_week_high': company_data.get('range', '').split('-')[1] if company_data.get('range') else None,
                'fifty_two_week_low': company_data.get('range', '').split('-')[0] if company_data.get('range') else None,
                'description': company_data.get('description', ''),
                'exchange': company_data.get('exchange', 'Unknown'),
                'currency': company_data.get('currency', 'USD'),
                'country': company_data.get('country', 'US'),
                'website': company_data.get('website', '')
            }
            
            # Convert string values to appropriate types
            if stock_data['market_cap']:
                try:
                    stock_data['market_cap'] = float(stock_data['market_cap'])
                except (ValueError, TypeError):
                    stock_data['market_cap'] = None
            
            if stock_data['pe_ratio']:
                try:
                    stock_data['pe_ratio'] = float(stock_data['pe_ratio'])
                except (ValueError, TypeError):
                    stock_data['pe_ratio'] = None
            
            if stock_data['beta']:
                try:
                    stock_data['beta'] = float(stock_data['beta'])
                except (ValueError, TypeError):
                    stock_data['beta'] = None
            
            if stock_data['fifty_two_week_high']:
                try:
                    stock_data['fifty_two_week_high'] = float(stock_data['fifty_two_week_high'])
                except (ValueError, TypeError):
                    stock_data['fifty_two_week_high'] = None
            
            if stock_data['fifty_two_week_low']:
                try:
                    stock_data['fifty_two_week_low'] = float(stock_data['fifty_two_week_low'])
                except (ValueError, TypeError):
                    stock_data['fifty_two_week_low'] = None
            
            logger.info(f"Fetched Financial Modeling Prep info for {symbol}")
            return stock_data
            
        except Exception as e:
            logger.error(f"Error fetching Financial Modeling Prep info for {symbol}: {e}")
            return None
    
    def fetch_current_price(self, symbol):
        """Fetch current stock price using Financial Modeling Prep"""
        try:
            # Get real-time quote
            data = self._make_api_request(f"quote/?symbol={symbol}")
            
            if not data or len(data) == 0:
                logger.warning(f"No real-time quote available for {symbol}")
                return None
            
            quote_data = data[0]
            
            current_price = quote_data.get('price')
            if current_price is None:
                logger.warning(f"No price data available for {symbol} from Financial Modeling Prep")
                return None
            
            # Get company information for additional context
            company_info = self.fetch_stock_info(symbol)
            if company_info:
                company_name = company_info.get('name', symbol)
                sector = company_info.get('sector', 'Unknown')
                exchange = company_info.get('exchange', 'Unknown')
                currency = company_info.get('currency', 'USD')
            else:
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
                'currency': currency,
                'change': quote_data.get('change'),
                'change_percentage': quote_data.get('changesPercentage'),
                'day_high': quote_data.get('dayHigh'),
                'day_low': quote_data.get('dayLow'),
                'volume': quote_data.get('volume')
            }
                
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol} from Financial Modeling Prep: {e}")
            return None
    
    def fetch_historical_data(self, symbol, period="1mo"):
        """Fetch historical stock data for a given period using Financial Modeling Prep"""
        try:
            # Map period to Financial Modeling Prep timeframe
            timeframe_map = {
                "1d": "1min",  # For intraday data
                "5d": "5min",
                "1mo": "daily",
                "3mo": "daily",
                "6mo": "daily",
                "1y": "daily",
                "2y": "daily",
                "5y": "daily"
            }
            
            timeframe = timeframe_map.get(period, "daily")
            
            if timeframe in ["1min", "5min"]:
                # Intraday data
                data = self._make_api_request(f"historical-chart/{timeframe}/?symbol={symbol}")
            else:
                # Daily data
                data = self._make_api_request(f"historical-price-full/?symbol={symbol}")
                if data and 'historical' in data:
                    data = data['historical']
            
            if not data:
                logger.warning(f"No historical data available for {symbol}")
                return []
            
            historical_data = []
            for item in data:
                try:
                    # Handle different data formats for intraday vs daily
                    if timeframe in ["1min", "5min"]:
                        date_str = item.get('date')
                        open_price = item.get('open')
                        high_price = item.get('high')
                        low_price = item.get('low')
                        close_price = item.get('close')
                        volume = item.get('volume')
                    else:
                        date_str = item.get('date')
                        open_price = item.get('open')
                        high_price = item.get('high')
                        low_price = item.get('low')
                        close_price = item.get('close')
                        volume = item.get('volume')
                    
                    if all([date_str, open_price, high_price, low_price, close_price]):
                        data_point = {
                            'symbol': symbol,
                            'date': date_str,
                            'open_price': open_price,
                            'high_price': high_price,
                            'low_price': low_price,
                            'close_price': close_price,
                            'volume': volume or 0
                        }
                        historical_data.append(data_point)
                except Exception as e:
                    logger.debug(f"Error processing historical data point for {symbol}: {e}")
                    continue
            
            logger.info(f"Fetched {len(historical_data)} historical data points for {symbol} from Financial Modeling Prep")
            return historical_data
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol} from Financial Modeling Prep: {e}")
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
                        'volume': stock_data.get('volume', 0),
                        'vwap': stock_data['price']
                    }
                    
                    self.repo.market_data.create(market_data)
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error saving current price for {symbol} from Financial Modeling Prep: {e}")
        
        logger.info(f"Updated current prices for {updated_count} symbols using Financial Modeling Prep")
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
                timestamp = datetime.strptime(data_point['date'], '%Y-%m-%d %H:%M:%S' if ' ' in data_point['date'] else '%Y-%m-%d')
                
                market_data = {
                    'symbol_id': existing_instrument.id,
                    'timestamp': timestamp,
                    'interval': '1min' if ' ' in data_point['date'] else '1day',
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
                logger.info(f"Saved {saved_count} historical data points for {symbol} using Financial Modeling Prep")
            except Exception as e:
                logger.error(f"Error saving bulk historical data for {symbol}: {e}")
                saved_count = 0
        
        return saved_count
    
    def get_stock_analysis(self, symbol):
        """Get technical analysis for a stock using Financial Modeling Prep"""
        try:
            # Get historical data for analysis
            historical_data = self.fetch_historical_data(symbol, "6mo")
            
            if not historical_data:
                return None
            
            # Extract close prices for analysis
            close_prices = [data['close_price'] for data in historical_data]
            
            if len(close_prices) < 50:
                logger.warning(f"Insufficient data for technical analysis of {symbol}")
                return None
            
            # Calculate simple moving averages
            sma_20 = sum(close_prices[-20:]) / 20
            sma_50 = sum(close_prices[-50:]) / 50
            
            current_price = close_prices[-1]
            
            analysis = {
                'symbol': symbol,
                'current_price': current_price,
                'sma_20': sma_20,
                'sma_50': sma_50,
                'trend': 'BULLISH' if current_price > sma_20 and current_price > sma_50 else 'BEARISH',
                'volume_trend': 'HIGH' if historical_data[-1]['volume'] > sum([d['volume'] for d in historical_data]) / len(historical_data) else 'LOW'
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol} with Financial Modeling Prep: {e}")
            return None
    
    def get_financial_statements(self, symbol):
        """Get financial statements (income statement, balance sheet, cash flow)"""
        try:
            # Get income statement
            income_statement = self._make_api_request(f"income-statement/?symbol={symbol}")
            balance_sheet = self._make_api_request(f"balance-sheet-statement/?symbol={symbol}")
            cash_flow = self._make_api_request(f"cash-flow-statement/?symbol={symbol}")
            
            financials = {
                'symbol': symbol,
                'income_statement': income_statement,
                'balance_sheet': balance_sheet,
                'cash_flow': cash_flow
            }
            
            return financials
            
        except Exception as e:
            logger.error(f"Error fetching financial statements for {symbol}: {e}")
            return None
    
    def get_key_metrics(self, symbol):
        """Get key financial metrics"""
        try:
            data = self._make_api_request(f"key-metrics/?symbol={symbol}")
            
            if not data or len(data) == 0:
                return None
            
            latest_metrics = data[0]  # Get the most recent metrics
            
            key_metrics = {
                'symbol': symbol,
                'revenue_per_share': latest_metrics.get('revenuePerShare'),
                'net_income_per_share': latest_metrics.get('netIncomePerShare'),
                'operating_cash_flow_per_share': latest_metrics.get('operatingCashFlowPerShare'),
                'free_cash_flow_per_share': latest_metrics.get('freeCashFlowPerShare'),
                'cash_per_share': latest_metrics.get('cashPerShare'),
                'book_value_per_share': latest_metrics.get('bookValuePerShare'),
                'tangible_book_value_per_share': latest_metrics.get('tangibleBookValuePerShare'),
                'shareholders_equity_per_share': latest_metrics.get('shareholdersEquityPerShare'),
                'interest_debt_per_share': latest_metrics.get('interestDebtPerShare'),
                'market_cap': latest_metrics.get('marketCap'),
                'enterprise_value': latest_metrics.get('enterpriseValue'),
                'pe_ratio': latest_metrics.get('peRatio'),
                'price_to_sales_ratio': latest_metrics.get('priceToSalesRatio'),
                'pocf_ratio': latest_metrics.get('pocfratio'),
                'pfcf_ratio': latest_metrics.get('pfcfRatio'),
                'pb_ratio': latest_metrics.get('pbRatio'),
                'ptb_ratio': latest_metrics.get('ptbRatio'),
                'ev_to_sales': latest_metrics.get('evToSales'),
                'enterprise_value_over_ebitda': latest_metrics.get('enterpriseValueOverEBITDA'),
                'ev_to_operating_cash_flow': latest_metrics.get('evToOperatingCashFlow'),
                'ev_to_free_cash_flow': latest_metrics.get('evToFreeCashFlow'),
                'earnings_yield': latest_metrics.get('earningsYield'),
                'free_cash_flow_yield': latest_metrics.get('freeCashFlowYield'),
                'debt_to_equity': latest_metrics.get('debtToEquity'),
                'debt_to_assets': latest_metrics.get('debtToAssets'),
                'net_debt_to_ebitda': latest_metrics.get('netDebtToEBITDA'),
                'current_ratio': latest_metrics.get('currentRatio'),
                'interest_coverage': latest_metrics.get('interestCoverage'),
                'income_quality': latest_metrics.get('incomeQuality')
            }
            
            return key_metrics
            
        except Exception as e:
            logger.error(f"Error fetching key metrics for {symbol}: {e}")
            return None
    
    def get_company_rating(self, symbol):
        """Get company rating and recommendations"""
        try:
            data = self._make_api_request(f"rating/?symbol={symbol}")
            
            if not data or len(data) == 0:
                return None
            
            rating_data = data[0]
            
            rating = {
                'symbol': symbol,
                'rating': rating_data.get('rating'),
                'rating_score': rating_data.get('ratingScore'),
                'rating_recommendation': rating_data.get('ratingRecommendation'),
                'rating_details_dcf': rating_data.get('ratingDetailsDCF'),
                'rating_details_roe': rating_data.get('ratingDetailsROE'),
                'rating_details_roa': rating_data.get('ratingDetailsROA'),
                'rating_details_de': rating_data.get('ratingDetailsDE'),
                'rating_details_pe': rating_data.get('ratingDetailsPE'),
                'rating_details_pb': rating_data.get('ratingDetailsPB')
            }
            
            return rating
            
        except Exception as e:
            logger.error(f"Error fetching company rating for {symbol}: {e}")
            return None
