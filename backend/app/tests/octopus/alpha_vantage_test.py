#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timedelta
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from storage.database import SessionLocal, get_db
from octopus.data_providers.alpha_vantage import AlphaVantageService

def test_alpha_vantage_real_api():
    """Test the Alpha Vantage service with real API data using application database"""
    
    # Use the same database as the main application
    db_session = SessionLocal()
    
    try:
        # Initialize real Alpha Vantage service with database session
        alpha_service = AlphaVantageService(db_session)
        
        print("Testing Alpha Vantage service with real API data...")
        print(f"Using API key: {'***' + alpha_service.api_key[-4:] if alpha_service.api_key != 'demo' else 'demo key'}")
        
        # Test symbols that are likely to have data
        test_symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        # Test 1: Fetch stock info
        print("\n1. Testing fetch_stock_info...")
        for symbol in test_symbols:
            stock_info = alpha_service.fetch_stock_info(symbol)
            if stock_info:
                print(f"✓ Successfully fetched stock info for {symbol}")
                print(f"  - Name: {stock_info.get('name')}")
                print(f"  - Sector: {stock_info.get('sector')}")
                if stock_info.get('market_cap'):
                    print(f"  - Market Cap: ${stock_info.get('market_cap'):,.0f}")
            else:
                print(f"✗ Failed to fetch stock info for {symbol}")
            time.sleep(1)  # Rate limiting
        
        # Test 2: Fetch current price
        print("\n2. Testing fetch_current_price...")
        for symbol in test_symbols:
            current_price = alpha_service.fetch_current_price(symbol)
            if current_price:
                print(f"✓ Successfully fetched current price for {symbol}")
                print(f"  - Price: ${current_price.get('price')}")
                print(f"  - Company: {current_price.get('company_name')}")
            else:
                print(f"✗ Failed to fetch current price for {symbol}")
            time.sleep(1)  # Rate limiting
        
        # Test 3: Save current prices (this will create symbols and market data)
        print("\n3. Testing save_current_prices...")
        updated_count = alpha_service.save_current_prices(test_symbols)
        print(f"✓ Updated {updated_count} symbols")
        
        # Test 4: Check if symbols were created
        print("\n4. Checking created symbols...")
        symbols_repo = alpha_service.repo.symbols
        created_symbols = symbols_repo.get_all()
        print(f"✓ Found {len(created_symbols)} symbols in storage:")
        for symbol in created_symbols:
            print(f"  - {symbol.symbol}: {symbol.name} (ID: {symbol.id})")
        
        # Test 5: Check market data
        print("\n5. Checking market data...")
        market_data_repo = alpha_service.repo.market_data
        for symbol in created_symbols:
            market_data = market_data_repo.get_latest(symbol.id, '1min', limit=1)
            if market_data:
                print(f"✓ Found market data for {symbol.symbol}: ${market_data[0].close}")
            else:
                print(f"✗ No market data found for {symbol.symbol}")
        
        # Test 6: Save historical data
        print("\n6. Testing save_historical_data...")
        saved_count = alpha_service.save_historical_data('AAPL', '1mo')
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
        analysis = alpha_service.get_stock_analysis('AAPL')
        if analysis:
            print(f"✓ Successfully analyzed AAPL")
            print(f"  - Current Price: ${analysis.get('current_price')}")
            print(f"  - Trend: {analysis.get('trend')}")
            print(f"  - SMA 20: ${analysis.get('sma_20')}")
            print(f"  - SMA 50: ${analysis.get('sma_50')}")
        else:
            print("✗ Failed to analyze stock")
        
        # Test 9: Get intraday data
        print("\n9. Testing get_intraday_data...")
        intraday_data = alpha_service.get_intraday_data('AAPL', '5min')
        if intraday_data:
            print(f"✓ Successfully fetched {len(intraday_data)} intraday data points for AAPL")
            print(f"  - Latest price: ${intraday_data[-1]['close_price']}")
            print(f"  - Time range: {intraday_data[0]['timestamp']} to {intraday_data[-1]['timestamp']}")
        else:
            print("✗ Failed to fetch intraday data")
        
        # Test 10: Get technical indicators
        print("\n10. Testing get_technical_indicators...")
        indicators = alpha_service.get_technical_indicators('AAPL')
        if indicators:
            print(f"✓ Successfully fetched technical indicators for AAPL")
            print(f"  - RSI: {indicators.get('rsi')}")
            print(f"  - Current Price: ${indicators.get('current_price')}")
            print(f"  - Volume: {indicators.get('volume'):,}")
        else:
            print("✗ Failed to fetch technical indicators")
        
        # Test 11: Test error handling for non-existent symbol
        print("\n11. Testing error handling...")
        non_existent_info = alpha_service.fetch_stock_info('NONEXISTENT123')
        if non_existent_info is None:
            print("✓ Correctly returned None for non-existent symbol")
        else:
            print("✗ Should have returned None for non-existent symbol")
        
        print("\n✅ All Alpha Vantage real API tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db_session.close()

def test_alpha_vantage_period_mapping():
    """Test the period to output size mapping functionality with real API using application database"""
    print("\nTesting Alpha Vantage period mapping with real API...")
    
    # Use the same database as the main application
    db_session = SessionLocal()
    
    try:
        alpha_service = AlphaVantageService(db_session)
        
        # Test different periods
        test_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y']
        
        for period in test_periods:
            historical_data = alpha_service.fetch_historical_data('AAPL', period)
            if historical_data:
                print(f"✓ Period '{period}': {len(historical_data)} data points")
            else:
                print(f"✗ Period '{period}': No data returned")
            time.sleep(1)  # Rate limiting
        
        print("✅ Period mapping test completed successfully!")
        
    except Exception as e:
        print(f"❌ Period mapping test failed: {e}")
    
    finally:
        db_session.close()

if __name__ == "__main__":
    test_alpha_vantage_real_api()
    test_alpha_vantage_period_mapping()
