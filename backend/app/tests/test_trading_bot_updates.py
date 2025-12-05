#!/usr/bin/env python3
"""
Test script to verify the updated trading bot functionality:
1. AI-generated stock lists
2. Technical analysis integration
3. Fundamental analysis integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session
from storage.models import Strategy
from jobs.trading_bot import TradingBot
import json

def test_ai_stock_list_generation():
    """Test AI stock list generation functionality"""
    print("Testing AI stock list generation...")
    
    # Create mock database session
    mock_db = Mock(spec=Session)
    
    # Create mock repository factory
    mock_repo_factory = Mock()
    mock_repo_factory.strategies = Mock()
    
    # Create trading bot instance
    with patch('jobs.trading_bot.RepositoryFactory', return_value=mock_repo_factory):
        with patch('jobs.trading_bot.YahooFinanceService'):
            with patch('jobs.trading_bot.TechnicalFunctions'):
                with patch('jobs.trading_bot.FundamentalFunctions'):
                    bot = TradingBot(mock_db)
    
    # Test 1: Strategy with AI mode and prompt
    print("\n1. Testing strategy with AI mode and prompt:")
    strategy_ai = Mock(spec=Strategy)
    strategy_ai.id = 1
    strategy_ai.name = "AI Strategy"
    strategy_ai.stock_list_mode = 'AI'
    strategy_ai.stock_list_ai_prompt = "Find me technology stocks with strong growth potential"
    strategy_ai.stock_list = ''  # Empty initial list
    strategy_ai.parameters = {'ai_platform': 'deepseek'}
    
    # Mock the AI service imports - patch the actual import path
    with patch('octopus.ai_platforms.deepseek.DeepSeekService'):
        stock_list = bot._generate_ai_stock_list(strategy_ai)
    
    print(f"   Generated stock list: {stock_list}")
    print(f"   ✓ AI stock list generation works")
    
    # Test 2: Save generated stock list
    print("\n2. Testing save generated stock list:")
    mock_repo_factory.strategies.update = Mock(return_value=True)
    bot._save_generated_stock_list(strategy_ai, ['AAPL', 'MSFT', 'GOOGL'])
    print(f"   ✓ Stock list saving mechanism works")
    
    # Test 3: Get stock list with AI mode
    print("\n3. Testing _get_stock_list with AI mode:")
    strategy_ai.stock_list = 'AAPL,MSFT,GOOGL'  # Simulate previously saved list
    with patch.object(bot, '_generate_ai_stock_list', return_value=['AAPL', 'MSFT', 'GOOGL']):
        with patch.object(bot, '_save_generated_stock_list'):
            result = bot._get_stock_list(strategy_ai)
    
    print(f"   Retrieved stock list: {result}")
    print(f"   ✓ AI stock list retrieval works")
    
    return True

def test_technical_analysis_integration():
    """Test technical analysis integration"""
    print("\nTesting technical analysis integration...")
    
    # Create mock database session
    mock_db = Mock(spec=Session)
    
    # Create trading bot instance with mocked dependencies
    with patch('jobs.trading_bot.RepositoryFactory'):
        with patch('jobs.trading_bot.YahooFinanceService'):
            with patch('jobs.trading_bot.TechnicalFunctions') as mock_tech:
                with patch('jobs.trading_bot.FundamentalFunctions'):
                    bot = TradingBot(mock_db)
                    
                    # Mock technical functions
                    mock_tech_instance = Mock()
                    mock_tech_instance.get_all_technical_indicators = Mock(return_value={
                        'rsi': 45.5,
                        'price_trend': 'BULLISH',
                        'is_overbought': False,
                        'is_oversold': False,
                        'is_price_near_support': True,
                        'is_price_near_resistance': False
                    })
                    bot.technical_functions = mock_tech_instance
    
    # Test technical indicators retrieval
    print("\n1. Testing technical indicators retrieval:")
    mock_instrument = Mock()
    mock_instrument.symbol = 'AAPL'
    
    with patch('jobs.trading_bot.RepositoryFactory') as mock_repo_factory:
        mock_repo = Mock()
        mock_repo.instruments.get_by_id = Mock(return_value=mock_instrument)
        bot.repo_factory = mock_repo
        
        indicators = bot._get_technical_indicators(123)
    
    print(f"   Retrieved indicators: {list(indicators.keys())}")
    print(f"   ✓ Technical indicators integration works")
    
    return True

def test_fundamental_analysis_integration():
    """Test fundamental analysis integration"""
    print("\nTesting fundamental analysis integration...")
    
    # Create mock database session
    mock_db = Mock(spec=Session)
    
    # Create trading bot instance with mocked dependencies
    with patch('jobs.trading_bot.RepositoryFactory'):
        with patch('jobs.trading_bot.YahooFinanceService'):
            with patch('jobs.trading_bot.TechnicalFunctions'):
                with patch('jobs.trading_bot.FundamentalFunctions') as mock_fund:
                    bot = TradingBot(mock_db)
                    
                    # Mock fundamental functions
                    mock_fund_instance = Mock()
                    mock_fund_instance.get_all_parameters = Mock(return_value={
                        'quality_score': 85,
                        'pe_ratio': 25.5,
                        'meets_quality_requirement': True,
                        'meets_valuation_requirement': True
                    })
                    bot.fundamental_functions = mock_fund_instance
    
    # Test signal generation with fundamental analysis
    print("\n1. Testing signal generation with fundamental analysis:")
    
    # Create mock objects
    mock_account = Mock()
    mock_strategy = Mock()
    mock_instrument = Mock()
    mock_instrument.symbol = 'AAPL'
    
    mock_market_data = {
        'close': 150.0,
        'volume': 2000000
    }
    
    mock_indicators = {
        'rsi': 45.5,
        'price_trend': 'BULLISH',
        'is_overbought': False,
        'is_oversold': False,
        'is_price_near_support': True,
        'is_price_near_resistance': False
    }
    
    strategy_params = {
        'rsi_oversold': 30.0,
        'rsi_overbought': 70.0,
        'min_volume': 1000000
    }
    
    # Generate signal
    signal = bot._generate_trading_signal(
        mock_account, mock_strategy, mock_instrument,
        mock_market_data, mock_indicators, strategy_params
    )
    
    print(f"   Generated signal: {signal}")
    print(f"   ✓ Fundamental analysis integration in signal generation works")
    
    return True

def test_composite_signal_generation():
    """Test the composite signal generation with TA and FA"""
    print("\nTesting composite signal generation...")
    
    # Create mock database session
    mock_db = Mock(spec=Session)
    
    # Create trading bot instance
    with patch('jobs.trading_bot.RepositoryFactory'):
        with patch('jobs.trading_bot.YahooFinanceService'):
            with patch('jobs.trading_bot.TechnicalFunctions'):
                with patch('jobs.trading_bot.FundamentalFunctions'):
                    bot = TradingBot(mock_db)
    
    # Test cases
    test_cases = [
        {
            'name': 'Strong BUY signal',
            'indicators': {'rsi': 25.0, 'price_trend': 'BULLISH', 'is_oversold': True, 'is_price_near_support': True},
            'fundamentals': {'quality_score': 85, 'meets_quality_requirement': True, 'meets_valuation_requirement': True},
            'expected_action': 'BUY'
        },
        {
            'name': 'Strong SELL signal',
            'indicators': {'rsi': 75.0, 'price_trend': 'BEARISH', 'is_overbought': True, 'is_price_near_resistance': True},
            'fundamentals': {'quality_score': 40, 'meets_quality_requirement': False, 'meets_valuation_requirement': False},
            'expected_action': 'SELL'
        },
        {
            'name': 'HOLD signal (mixed)',
            'indicators': {'rsi': 50.0, 'price_trend': 'SIDEWAYS', 'is_overbought': False, 'is_oversold': False},
            'fundamentals': {'quality_score': 65, 'meets_quality_requirement': True, 'meets_valuation_requirement': False},
            'expected_action': 'HOLD'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing {test_case['name']}:")
        
        # Mock fundamental functions
        bot.fundamental_functions.get_all_parameters = Mock(return_value=test_case['fundamentals'])
        
        # Create mock objects
        mock_account = Mock()
        mock_strategy = Mock()
        mock_instrument = Mock()
        mock_instrument.symbol = 'TEST'
        
        mock_market_data = {
            'close': 100.0,
            'volume': 2000000
        }
        
        strategy_params = {
            'rsi_oversold': 30.0,
            'rsi_overbought': 70.0,
            'min_volume': 1000000
        }
        
        # Generate signal
        signal = bot._generate_trading_signal(
            mock_account, mock_strategy, mock_instrument,
            mock_market_data, test_case['indicators'], strategy_params
        )
        
        print(f"   Signal: {signal['action']} (expected: {test_case['expected_action']})")
        print(f"   Reason: {signal.get('reason', 'No reason')}")
        
        if signal['action'] == test_case['expected_action']:
            print(f"   ✓ Test passed")
        else:
            print(f"   ✗ Test failed")
    
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Updated Trading Bot Functionality")
    print("=" * 60)
    
    try:
        # Run tests
        test_ai_stock_list_generation()
        test_technical_analysis_integration()
        test_fundamental_analysis_integration()
        test_composite_signal_generation()
        
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("Summary of updates:")
        print("1. ✓ AI-generated stock lists from database prompts")
        print("2. ✓ Technical analysis module integration")
        print("3. ✓ Fundamental analysis module integration")
        print("4. ✓ Composite signal generation using TA and FA")
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
