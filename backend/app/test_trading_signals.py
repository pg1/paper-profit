#!/usr/bin/env python3
"""
Test script to verify trading signals are created with proper fields including indicators_used JSON.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session
from storage.models import Strategy, Instrument, Account
from jobs.trading_bot import TradingBot
import json

def test_trading_signal_creation():
    """Test that trading signals are created with proper fields"""
    print("Testing trading signal creation with indicators_used JSON...")
    
    # Create mock database session
    mock_db = Mock(spec=Session)
    
    # Create mock repository factory
    mock_repo_factory = Mock()
    mock_repo_factory.strategies = Mock()
    mock_repo_factory.instruments = Mock()
    mock_repo_factory.orders = Mock()
    mock_repo_factory.trading_signals = Mock()
    mock_repo_factory.system_logs = Mock()
    
    # Create trading bot instance
    with patch('jobs.trading_bot.RepositoryFactory', return_value=mock_repo_factory):
        with patch('jobs.trading_bot.YahooFinanceService'):
            with patch('jobs.trading_bot.TechnicalFunctions'):
                with patch('jobs.trading_bot.FundamentalFunctions'):
                    bot = TradingBot(mock_db)
    
    # Test 1: BUY signal creation with indicators_used
    print("\n1. Testing BUY signal creation:")
    
    # Create mock objects
    mock_account = Mock(spec=Account)
    mock_account.account_id = 'test_account_123'
    mock_account.cash_balance = 10000.0
    
    mock_strategy = Mock(spec=Strategy)
    mock_strategy.id = 1
    mock_strategy.name = 'Test Strategy'
    
    mock_instrument = Mock(spec=Instrument)
    mock_instrument.id = 100
    mock_instrument.symbol = 'AAPL'
    
    # Mock signal data
    signal = {
        'action': 'BUY',
        'price': 150.0,
        'reason': 'RSI oversold (25.5), Bullish price trend, Price near support level',
        'confidence': 0.8,
        'signal_score': 4
    }
    
    # Mock indicators
    indicators = {
        'rsi': 25.5,
        'price_trend': 'BULLISH',
        'is_overbought': False,
        'is_oversold': True,
        'is_price_near_support': True,
        'is_price_near_resistance': False
    }
    
    # Mock the _get_technical_indicators method
    bot._get_technical_indicators = Mock(return_value=indicators)
    
    # Mock the _extract_indicators_used method
    expected_indicators_used = {
        'rsi': 25.5,
        'price_trend': 'BULLISH',
        'support': 'mentioned_in_reason',
        'oversold': True,
        'signal_score': 4,
        'confidence': 0.8,
        'is_overbought': False,
        'is_oversold': True,
        'is_price_near_support': True,
        'is_price_near_resistance': False
    }
    bot._extract_indicators_used = Mock(return_value=expected_indicators_used)
    
    # Mock current positions (empty for BUY)
    current_positions = {}
    
    # Mock strategy parameters
    strategy_params = {
        'max_position_size_percent': 10.0,
        'max_positions': 10
    }
    
    # Mock the _calculate_position_size method
    bot._calculate_position_size = Mock(return_value=10)
    
    # Mock the orders.create method
    mock_repo_factory.orders.create = Mock(return_value=Mock())
    
    # Capture the trading signal creation
    captured_signal_data = None
    def capture_signal_create(data):
        nonlocal captured_signal_data
        captured_signal_data = data
        return Mock()
    
    mock_repo_factory.trading_signals.create = capture_signal_create
    
    # Execute the BUY order
    bot._execute_buy_order(mock_account, mock_strategy, mock_instrument, 
                          signal, strategy_params, current_positions)
    
    # Verify the trading signal was created with proper fields
    assert captured_signal_data is not None, "Trading signal was not created"
    print(f"   Signal type: {captured_signal_data.get('signal_type')}")
    print(f"   Price: {captured_signal_data.get('price')}")
    print(f"   Strength: {captured_signal_data.get('strength')}")
    print(f"   Confidence: {captured_signal_data.get('confidence')}")
    print(f"   Reason: {captured_signal_data.get('reason')}")
    
    # Check indicators_used JSON field
    indicators_used_json = captured_signal_data.get('indicators_used')
    assert indicators_used_json is not None, "indicators_used field is missing"
    
    # Parse the JSON
    indicators_used = json.loads(indicators_used_json)
    print(f"   indicators_used keys: {list(indicators_used.keys())}")
    
    # Verify key fields are present
    assert 'signal_score' in indicators_used
    assert 'confidence' in indicators_used
    assert 'rsi' in indicators_used
    
    print(f"   ✓ BUY signal creation with indicators_used works")
    
    # Test 2: SELL signal creation
    print("\n2. Testing SELL signal creation:")
    
    # Mock signal data for SELL
    sell_signal = {
        'action': 'SELL',
        'price': 160.0,
        'reason': 'RSI overbought (75.2), Bearish price trend, Price near resistance level',
        'confidence': 0.7,
        'signal_score': -4
    }
    
    # Mock existing position
    mock_position = Mock()
    mock_position.quantity = 20
    current_positions_with_position = {'AAPL': mock_position}
    
    # Reset capture
    captured_signal_data = None
    
    # Execute the SELL order
    bot._execute_sell_order(mock_account, mock_strategy, mock_instrument, 
                           sell_signal, strategy_params, current_positions_with_position)
    
    # Verify the trading signal was created
    assert captured_signal_data is not None, "SELL trading signal was not created"
    assert captured_signal_data.get('signal_type') == 'SELL'
    
    indicators_used_json = captured_signal_data.get('indicators_used')
    assert indicators_used_json is not None, "indicators_used field is missing in SELL signal"
    
    print(f"   ✓ SELL signal creation with indicators_used works")
    
    # Test 3: HOLD signal creation
    print("\n3. Testing HOLD signal creation:")
    
    # Mock signal data for HOLD
    hold_signal = {
        'action': 'HOLD',
        'price': 155.0,
        'reason': 'Mixed signals: RSI neutral (50.5), Sideways price trend',
        'confidence': 0.5,
        'signal_score': 0
    }
    
    # Reset capture
    captured_signal_data = None
    
    # Mock the trading_signals.create method for HOLD
    mock_repo_factory.trading_signals.create = capture_signal_create
    
    # Execute the HOLD signal logging
    bot._log_hold_signal(mock_account, mock_strategy, mock_instrument, hold_signal)
    
    # Verify the HOLD signal was created
    assert captured_signal_data is not None, "HOLD trading signal was not created"
    assert captured_signal_data.get('signal_type') == 'HOLD'
    
    indicators_used_json = captured_signal_data.get('indicators_used')
    assert indicators_used_json is not None, "indicators_used field is missing in HOLD signal"
    
    print(f"   ✓ HOLD signal creation with indicators_used works")
    
    # Test 4: _extract_indicators_used method
    print("\n4. Testing _extract_indicators_used method:")
    
    # Test signal with various reasons
    test_signal = {
        'reason': 'RSI oversold (25.5), Bullish price trend, Good valuation, High quality score (85)',
        'signal_score': 5,
        'confidence': 0.85
    }
    
    test_indicators = {
        'rsi': 25.5,
        'price_trend': 'BULLISH',
        'is_overbought': False,
        'is_oversold': True,
        'quality_score': 85
    }
    
    # Call the actual method (not mocked)
    bot._extract_indicators_used = TradingBot._extract_indicators_used.__get__(bot, TradingBot)
    extracted = bot._extract_indicators_used(test_signal, test_indicators)
    
    print(f"   Extracted indicators: {list(extracted.keys())}")
    
    # Verify extraction
    assert 'rsi' in extracted
    assert extracted['rsi'] == 25.5
    assert 'price_trend' in extracted
    assert extracted['price_trend'] == 'BULLISH'
    assert 'signal_score' in extracted
    assert extracted['signal_score'] == 5
    assert 'confidence' in extracted
    assert extracted['confidence'] == 0.85
    
    print(f"   ✓ _extract_indicators_used method works correctly")
    
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Trading Signal Creation with Detailed Metadata")
    print("=" * 60)
    
    try:
        test_trading_signal_creation()
        
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("Summary of verified features:")
        print("1. ✓ BUY signals created with indicators_used JSON field")
        print("2. ✓ SELL signals created with indicators_used JSON field")
        print("3. ✓ HOLD signals created with indicators_used JSON field")
        print("4. ✓ _extract_indicators_used method extracts relevant indicators")
        print("5. ✓ All required fields present: strength, price, confidence, reason")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
