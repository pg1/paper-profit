#!/usr/bin/env python3
"""Test script to verify the stock_scoring.py fix"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.stock_scoring import fetch_stock_data, score_and_classify_stock

def test_fetch_stock_data():
    """Test the fetch_stock_data function with a known ticker"""
    print("Testing fetch_stock_data function...")
    
    # Test with a known ticker (Apple)
    ticker = "AAPL"
    
    try:
        print(f"Fetching data for {ticker}...")
        stock_data = fetch_stock_data(ticker)
        
        print(f"\nSuccessfully fetched data for {ticker}:")
        print(f"  Name: {stock_data.name}")
        print(f"  Sector: {stock_data.sector}")
        print(f"  Industry: {stock_data.industry}")
        print(f"  Market Cap: ${stock_data.market_cap:,.2f}")
        print(f"  Beta: {stock_data.beta}")
        print(f"  Dividend Yield: {stock_data.dividend_yield:.4f}")
        print(f"  Debt to Equity: {stock_data.debt_to_equity}")
        print(f"  Profit Margins: {stock_data.profit_margins:.4f}")
        print(f"  Trailing PE: {stock_data.trailing_pe}")
        print(f"  Forward PE: {stock_data.forward_pe}")
        print(f"  Revenue Growth: {stock_data.revenue_growth:.4f}")
        print(f"  Return on Equity: {stock_data.return_on_equity:.4f}")
        
        return True
        
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return False

def test_score_and_classify():
    """Test the score_and_classify_stock function"""
    print("\n\nTesting score_and_classify_stock function...")
    
    # Test with a known ticker (Apple)
    ticker = "AAPL"
    
    try:
        print(f"Scoring and classifying {ticker}...")
        result = score_and_classify_stock(ticker)
        
        print(f"\nSuccessfully scored and classified {ticker}:")
        print(f"  Ticker: {result['ticker']}")
        print(f"  Name: {result['name']}")
        print(f"  Sector Bucket: {result['sector_bucket']}")
        print(f"  Risk Score: {result['risk_score']}")
        print(f"  Risk Style: {result['risk_style']}")
        print(f"  Overall Score: {result['overall_score']}")
        print(f"  Letter Grade: {result['letter_grade']}")
        
        return True
        
    except Exception as e:
        print(f"Error scoring and classifying {ticker}: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("Testing stock_scoring.py fix")
    print("=" * 60)
    
    # Test fetch_stock_data
    fetch_success = test_fetch_stock_data()
    
    # Test score_and_classify_stock
    score_success = test_score_and_classify()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"  fetch_stock_data: {'PASS' if fetch_success else 'FAIL'}")
    print(f"  score_and_classify_stock: {'PASS' if score_success else 'FAIL'}")
    
    if fetch_success and score_success:
        print("\nAll tests passed! The fix is working correctly.")
        return 0
    else:
        print("\nSome tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())