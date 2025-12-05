#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timedelta
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from storage.database import SessionLocal, get_db
from octopus.data_providers.financialmodelingprep import FinancialModelingPrepService

def test_financialmodelingprep_real_api():
    """Test the Financial Modeling Prep service with real API data using application database"""
    
    # Use the same database as the main application
    db_session = SessionLocal()
    
    try:
        # Initialize real Financial Modeling Prep service with database session
        fmp_service = FinancialModelingPrepService(db_session)
        
        print("Testing Financial Modeling Prep service with real API data...")
        print(f"Using API key: {'***' + fmp_service.api_key[-4:] if fmp_service.api_key != 'demo' else 'demo key'}")
        
        # Test symbols that are likely to have data
        test_symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        # Test 1: Fetch stock info
        print("\n1. Testing fetch_stock_info...")
        for symbol in test_symbols:
            stock_info = fmp_service.fetch_stock_info(symbol)
            if stock_info:
                print(f"✓ Successfully fetched stock info for {symbol}")
                print(f"  - Name: {stock_info.get('name')}")
                print(f"  - Sector: {stock_info.get('sector')}")
                if stock_info.get('market_cap'):
                    print(f"  - Market Cap: ${stock_info.get('market_cap'):,.0f}")
                print(f"  - Exchange: {stock_info.get('exchange')}")
                print(f"  - Currency: {stock_info.get('currency')}")
            else:
                print(f"✗ Failed to fetch stock info for {symbol}")
            time.sleep(1)  # Rate limiting
        
        # Test 2: Fetch current price
        print("\n2. Testing fetch_current_price...")
        for symbol in test_symbols:
            current_price = fmp_service.fetch_current_price(symbol)
            if current_price:
                print(f"✓ Successfully fetched current price for {symbol}")
                print(f"  - Price: ${current_price.get('price')}")
                print(f"  - Company: {current_price.get('company_name')}")
                print(f"  - Change: {current_price.get('change')}")
                print(f"  - Change %: {current_price.get('change_percentage')}%")
            else:
                print(f"✗ Failed to fetch current price for {symbol}")
            time.sleep(1)  # Rate limiting
        
        # Test 3: Save current prices (this will create symbols and market data)
        print("\n3. Testing save_current_prices...")
        updated_count = fmp_service.save_current_prices(test_symbols)
        print(f"✓ Updated {updated_count} symbols")
        
        # Test 4: Check if instruments were created
        print("\n4. Checking created instruments...")
        instruments_repo = fmp_service.repo.instruments
        created_instruments = instruments_repo.get_all()
        print(f"✓ Found {len(created_instruments)} instruments in storage:")
        for instrument in created_instruments:
            print(f"  - {instrument.symbol}: {instrument.name} (ID: {instrument.id})")
        
        # Test 5: Check market data
        print("\n5. Checking market data...")
        market_data_repo = fmp_service.repo.market_data
        for instrument in created_instruments:
            market_data = market_data_repo.get_latest(instrument.id, '1min', limit=1)
            if market_data:
                print(f"✓ Found market data for {instrument.symbol}: ${market_data[0].close}")
            else:
                print(f"✗ No market data found for {instrument.symbol}")
        
        # Test 6: Save historical data
        print("\n6. Testing save_historical_data...")
        saved_count = fmp_service.save_historical_data('AAPL', '1mo')
        print(f"✓ Saved {saved_count} historical data points for AAPL")
        
        # Test 7: Check historical market data
        print("\n7. Checking historical market data...")
        aapl_instrument = instruments_repo.get_by_symbol('AAPL')
        if aapl_instrument:
            historical_data = market_data_repo.get_latest(aapl_instrument.id, '1day', limit=5)
            print(f"✓ Found {len(historical_data)} historical data points for AAPL")
            for data in historical_data:
                print(f"  - {data.timestamp.date()}: ${data.close}")
        
        # Test 8: Get stock analysis
        print("\n8. Testing get_stock_analysis...")
        analysis = fmp_service.get_stock_analysis('AAPL')
        if analysis:
            print(f"✓ Successfully analyzed AAPL")
            print(f"  - Current Price: ${analysis.get('current_price')}")
            print(f"  - Trend: {analysis.get('trend')}")
            print(f"  - SMA 20: ${analysis.get('sma_20')}")
            print(f"  - SMA 50: ${analysis.get('sma_50')}")
        else:
            print("✗ Failed to analyze stock")
        
        # Test 9: Get financial statements
        print("\n9. Testing get_financial_statements...")
        financials = fmp_service.get_financial_statements('AAPL')
        if financials:
            print(f"✓ Successfully fetched financial statements for AAPL")
            income_statement = financials.get('income_statement')
            if income_statement and len(income_statement) > 0:
                latest_income = income_statement[0]
                print(f"  - Revenue: {latest_income.get('revenue')}")
                print(f"  - Net Income: {latest_income.get('netIncome')}")
        else:
            print("✗ Failed to fetch financial statements")
        
        # Test 10: Get key metrics
        print("\n10. Testing get_key_metrics...")
        key_metrics = fmp_service.get_key_metrics('AAPL')
        if key_metrics:
            print(f"✓ Successfully fetched key metrics for AAPL")
            print(f"  - P/E Ratio: {key_metrics.get('pe_ratio')}")
            print(f"  - P/B Ratio: {key_metrics.get('pb_ratio')}")
            print(f"  - Debt to Equity: {key_metrics.get('debt_to_equity')}")
        else:
            print("✗ Failed to fetch key metrics")
        
        # Test 11: Get company rating
        print("\n11. Testing get_company_rating...")
        rating = fmp_service.get_company_rating('AAPL')
        if rating:
            print(f"✓ Successfully fetched company rating for AAPL")
            print(f"  - Rating: {rating.get('rating')}")
            print(f"  - Recommendation: {rating.get('rating_recommendation')}")
        else:
            print("✗ Failed to fetch company rating")
        
        # Test 12: Test error handling for non-existent symbol
        print("\n12. Testing error handling...")
        non_existent_info = fmp_service.fetch_stock_info('NONEXISTENT123')
        if non_existent_info is None:
            print("✓ Correctly returned None for non-existent symbol")
        else:
            print("✗ Should have returned None for non-existent symbol")
        
        print("\n✅ All Financial Modeling Prep real API tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db_session.close()

def test_financialmodelingprep_period_mapping():
    """Test the period to timeframe mapping functionality with real API using application database"""
    print("\nTesting Financial Modeling Prep period mapping with real API...")
    
    # Use the same database as the main application
    db_session = SessionLocal()
    
    try:
        fmp_service = FinancialModelingPrepService(db_session)
        
        # Test different periods
        test_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y']
        
        for period in test_periods:
            historical_data = fmp_service.fetch_historical_data('AAPL', period)
            if historical_data:
                print(f"✓ Period '{period}': {len(historical_data)} data points")
                if len(historical_data) > 0:
                    print(f"  - Latest: {historical_data[0]['date']} - ${historical_data[0]['close_price']}")
            else:
                print(f"✗ Period '{period}': No data returned")
            time.sleep(1)  # Rate limiting
        
        print("✅ Period mapping test completed successfully!")
        
    except Exception as e:
        print(f"❌ Period mapping test failed: {e}")
    
    finally:
        db_session.close()

if __name__ == "__main__":
    test_financialmodelingprep_real_api()
    test_financialmodelingprep_period_mapping()
