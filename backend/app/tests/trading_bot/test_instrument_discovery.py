#!/usr/bin/env python3
"""
Test script for InstrumentDiscovery class.
Tests stock list parsing and fallback stock list generation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session
from storage.models import Strategy
from jobs.trading_bot.instrument_discovery import InstrumentDiscovery


def create_mock_strategy(stock_list: str) -> Mock:
    """Helper to create a mock strategy with a given stock list"""
    mock_strategy = Mock(spec=Strategy)
    mock_strategy.id = 1
    mock_strategy.name = 'Test Strategy'
    mock_strategy.stock_list = stock_list
    return mock_strategy


def test_get_stock_list_json_format():
    """Test parsing stock list in JSON array format"""
    print("\n1. Testing JSON array format parsing:")
    
    mock_db = Mock(spec=Session)
    mock_repo_factory = Mock()
    
    discovery = InstrumentDiscovery(mock_db, mock_repo_factory)
    
    # Test JSON array format
    strategy = create_mock_strategy('["AAPL", "MSFT", "GOOGL"]')
    result = discovery.get_stock_list(strategy)
    
    assert result == ['AAPL', 'MSFT', 'GOOGL'], f"Expected ['AAPL', 'MSFT', 'GOOGL'], got {result}"
    print(f"   ✓ JSON array parsed correctly: {result}")
    
    # Test JSON with lowercase (should be converted to uppercase)
    strategy = create_mock_strategy('["aapl", "msft"]')
    result = discovery.get_stock_list(strategy)
    
    assert result == ['AAPL', 'MSFT'], f"Expected ['AAPL', 'MSFT'], got {result}"
    print(f"   ✓ JSON array with lowercase converted to uppercase: {result}")


def test_get_stock_list_comma_separated():
    """Test parsing stock list in comma-separated format"""
    print("\n2. Testing comma-separated format parsing:")
    
    mock_db = Mock(spec=Session)
    mock_repo_factory = Mock()
    
    discovery = InstrumentDiscovery(mock_db, mock_repo_factory)
    
    # Test comma-separated format
    strategy = create_mock_strategy('AAPL, MSFT, GOOGL')
    result = discovery.get_stock_list(strategy)
    
    assert result == ['AAPL', 'MSFT', 'GOOGL'], f"Expected ['AAPL', 'MSFT', 'GOOGL'], got {result}"
    print(f"   ✓ Comma-separated parsed correctly: {result}")
    
    # Test with extra spaces
    strategy = create_mock_strategy('  AAPL  ,  MSFT  ,  GOOGL  ')
    result = discovery.get_stock_list(strategy)
    
    assert result == ['AAPL', 'MSFT', 'GOOGL'], f"Expected ['AAPL', 'MSFT', 'GOOGL'], got {result}"
    print(f"   ✓ Comma-separated with extra spaces parsed correctly: {result}")


def test_get_stock_list_newline_separated():
    """Test parsing stock list in newline-separated format"""
    print("\n3. Testing newline-separated format parsing:")
    
    mock_db = Mock(spec=Session)
    mock_repo_factory = Mock()
    
    discovery = InstrumentDiscovery(mock_db, mock_repo_factory)
    
    # Test newline-separated format
    strategy = create_mock_strategy('AAPL\nMSFT\nGOOGL')
    result = discovery.get_stock_list(strategy)
    
    assert result == ['AAPL', 'MSFT', 'GOOGL'], f"Expected ['AAPL', 'MSFT', 'GOOGL'], got {result}"
    print(f"   ✓ Newline-separated parsed correctly: {result}")
    
    # Test with empty lines
    strategy = create_mock_strategy('AAPL\n\nMSFT\n\nGOOGL\n')
    result = discovery.get_stock_list(strategy)
    
    assert result == ['AAPL', 'MSFT', 'GOOGL'], f"Expected ['AAPL', 'MSFT', 'GOOGL'], got {result}"
    print(f"   ✓ Newline-separated with empty lines parsed correctly: {result}")


def test_get_fallback_stock_list():
    """Test fallback stock list generation based on prompt keywords"""
    print("\n4. Testing fallback stock list generation:")
    
    mock_db = Mock(spec=Session)
    mock_repo_factory = Mock()
    
    discovery = InstrumentDiscovery(mock_db, mock_repo_factory)
    
    # Test tech prompt
    result = discovery._get_fallback_stock_list("Get me some technology stocks")
    assert 'AAPL' in result and 'MSFT' in result, f"Tech stocks should include AAPL and MSFT, got {result}"
    print(f"   ✓ Tech prompt returns tech stocks: {result}")
    
    # Test finance prompt
    result = discovery._get_fallback_stock_list("I want bank stocks")
    assert 'JPM' in result, f"Finance stocks should include JPM, got {result}"
    print(f"   ✓ Finance/bank prompt returns finance stocks: {result}")
    
    # Test health prompt
    result = discovery._get_fallback_stock_list("healthcare and pharma companies")
    assert 'JNJ' in result or 'PFE' in result, f"Health stocks should include JNJ or PFE, got {result}"
    print(f"   ✓ Health prompt returns health stocks: {result}")
    
    # Test energy prompt
    result = discovery._get_fallback_stock_list("oil and energy sector")
    assert 'XOM' in result or 'CVX' in result, f"Energy stocks should include XOM or CVX, got {result}"
    print(f"   ✓ Energy prompt returns energy stocks: {result}")
    
    # Test consumer/retail prompt
    result = discovery._get_fallback_stock_list("consumer retail companies")
    assert 'WMT' in result or 'TGT' in result, f"Consumer stocks should include WMT or TGT, got {result}"
    print(f"   ✓ Consumer prompt returns consumer stocks: {result}")
    
    # Test default (no matching keywords)
    result = discovery._get_fallback_stock_list("random stocks please")
    assert len(result) > 0, "Default should return some stocks"
    print(f"   ✓ Default prompt returns popular stocks: {result}")


def test_get_stock_list_empty_values():
    """Test handling of empty or whitespace-only values"""
    print("\n5. Testing empty value handling:")
    
    mock_db = Mock(spec=Session)
    mock_repo_factory = Mock()
    
    discovery = InstrumentDiscovery(mock_db, mock_repo_factory)
    
    # Test empty JSON array
    strategy = create_mock_strategy('[]')
    result = discovery.get_stock_list(strategy)
    assert result == [], f"Expected empty list, got {result}"
    print(f"   ✓ Empty JSON array returns empty list: {result}")
    
    # Test comma-separated with empty values
    strategy = create_mock_strategy('AAPL,, ,MSFT')
    result = discovery.get_stock_list(strategy)
    assert result == ['AAPL', 'MSFT'], f"Expected ['AAPL', 'MSFT'], got {result}"
    print(f"   ✓ Comma-separated with empty values filters correctly: {result}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing InstrumentDiscovery Class")
    print("=" * 60)
    
    try:
        test_get_stock_list_json_format()
        test_get_stock_list_comma_separated()
        test_get_stock_list_newline_separated()
        test_get_fallback_stock_list()
        test_get_stock_list_empty_values()
        
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("Summary of verified features:")
        print("1. ✓ JSON array format parsing")
        print("2. ✓ Comma-separated format parsing")
        print("3. ✓ Newline-separated format parsing")
        print("4. ✓ Fallback stock list generation by keyword")
        print("5. ✓ Empty value handling")
        print("=" * 60)
        
        return True
        
    except AssertionError as e:
        print(f"\n✗ Assertion failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
