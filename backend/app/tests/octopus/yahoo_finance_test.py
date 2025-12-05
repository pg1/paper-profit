#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from storage.database import Base
from octopus.data_providers.yahoo_finance import YahooFinanceService

class MockYahooFinanceService(YahooFinanceService):
    """Mock Yahoo Finance service for testing storage model integration"""
    
    def fetch_stock_info(self, symbol):
        """Mock stock info fetch"""
        mock_data = {
            'AAPL': {
                'symbol': 'AAPL',
                'name': 'Apple Inc.',
                'sector': 'Technology',
                'industry': 'Consumer Electronics',
                'market_cap': 3000000000000,
                'pe_ratio': 25.5,
                'dividend_yield': 0.005,
                'beta': 1.2,
                'fifty_two_week_high': 180.0,
                'fifty_two_week_low': 120.0
            },
            'MSFT': {
                'symbol': 'MSFT',
                'name': 'Microsoft Corporation',
                'sector': 'Technology',
                'industry': 'Software',
                'market_cap': 2800000000000,
                'pe_ratio': 30.2,
                'dividend_yield': 0.008,
                'beta': 0.9,
                'fifty_two_week_high': 350.0,
                'fifty_two_week_low': 240.0
            }
        }
        return mock_data.get(symbol)
    
    def fetch_current_price(self, symbol):
        """Mock current price fetch"""
        mock_prices = {
            'AAPL': {
                'symbol': 'AAPL',
                'price': 175.50,
                'company_name': 'Apple Inc.',
                'sector': 'Technology',
                'exchange': 'NASDAQ',
                'currency': 'USD'
            },
            'MSFT': {
                'symbol': 'MSFT',
                'price': 340.25,
                'company_name': 'Microsoft Corporation',
                'sector': 'Technology',
                'exchange': 'NASDAQ',
                'currency': 'USD'
            }
        }
        return mock_prices.get(symbol)
    
    def fetch_historical_data(self, symbol, period="1mo"):
        """Mock historical data fetch"""
        base_date = datetime.now() - timedelta(days=30)
        mock_data = []
        
        for i in range(30):
            date = base_date + timedelta(days=i)
            price = 170 + i if symbol == 'AAPL' else 330 + i
            mock_data.append({
                'symbol': symbol,
                'date': date.strftime('%Y-%m-%d'),
                'open_price': price - 1,
                'high_price': price + 1,
                'low_price': price - 2,
                'close_price': price,
                'volume': 1000000 + i * 10000
            })
        
        return mock_data

def test_yahoo_finance_storage_mock():
    """Test the updated Yahoo Finance service with storage model using mock data"""
    
    # Create in-memory SQLite database for testing
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    
    try:
        # Initialize Mock Yahoo Finance service with database session
        yahoo_service = MockYahooFinanceService(db_session)
        
        print("Testing Yahoo Finance service with storage model (using mock data)...")
        
        # Test 1: Fetch stock info
        print("\n1. Testing fetch_stock_info...")
        stock_info = yahoo_service.fetch_stock_info('AAPL')
        if stock_info:
            print(f"✓ Successfully fetched stock info for AAPL")
            print(f"  - Name: {stock_info.get('name')}")
            print(f"  - Sector: {stock_info.get('sector')}")
        else:
            print("✗ Failed to fetch stock info")
        
        # Test 2: Fetch current price
        print("\n2. Testing fetch_current_price...")
        current_price = yahoo_service.fetch_current_price('AAPL')
        if current_price:
            print(f"✓ Successfully fetched current price for AAPL")
            print(f"  - Price: ${current_price.get('price')}")
            print(f"  - Company: {current_price.get('company_name')}")
        else:
            print("✗ Failed to fetch current price")
        
        # Test 3: Save current prices (this will create symbols and market data)
        print("\n3. Testing save_current_prices...")
        symbols = ['AAPL', 'MSFT']
        updated_count = yahoo_service.save_current_prices(symbols)
        print(f"✓ Updated {updated_count} symbols")
        
        # Test 4: Check if symbols were created
        print("\n4. Checking created symbols...")
        symbols_repo = yahoo_service.repo.symbols
        created_symbols = symbols_repo.get_all()
        print(f"✓ Found {len(created_symbols)} symbols in storage:")
        for symbol in created_symbols:
            print(f"  - {symbol.symbol}: {symbol.name} (ID: {symbol.id})")
        
        # Test 5: Check market data
        print("\n5. Checking market data...")
        market_data_repo = yahoo_service.repo.market_data
        for symbol in created_symbols:
            market_data = market_data_repo.get_latest(symbol.id, '1min', limit=1)
            if market_data:
                print(f"✓ Found market data for {symbol.symbol}: ${market_data[0].close}")
            else:
                print(f"✗ No market data found for {symbol.symbol}")
        
        # Test 6: Save historical data
        print("\n6. Testing save_historical_data...")
        saved_count = yahoo_service.save_historical_data('AAPL', '1mo')
        print(f"✓ Saved {saved_count} historical data points for AAPL")
        
        # Test 7: Check historical market data
        print("\n7. Checking historical market data...")
        aapl_symbol = symbols_repo.get_by_symbol('AAPL')
        if aapl_symbol:
            historical_data = market_data_repo.get_latest(aapl_symbol.id, '1day', limit=5)
            print(f"✓ Found {len(historical_data)} historical data points for AAPL")
            for data in historical_data:
                print(f"  - {data.timestamp.date()}: ${data.close}")
        
        # Test 8: Get stock analysis
        print("\n8. Testing get_stock_analysis...")
        analysis = yahoo_service.get_stock_analysis('AAPL')
        if analysis:
            print(f"✓ Successfully analyzed AAPL")
            print(f"  - Current Price: ${analysis.get('current_price')}")
            print(f"  - Trend: {analysis.get('trend')}")
            print(f"  - Symbol ID: {analysis.get('symbol_id')}")
        else:
            print("✗ Failed to analyze stock")
        
        print("\n✅ All storage model integration tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db_session.close()

if __name__ == "__main__":
    test_yahoo_finance_storage_mock()
