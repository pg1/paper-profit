#!/usr/bin/env python3

"""
Test script for parameter_functions module
"""

import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import SessionLocal, get_db
from utils import ParameterFunctions, get_all_parameters_for_stock


def test_parameter_functions():
    """Test the parameter functions with sample stocks"""
    
    # Initialize database
    db_session = SessionLocal()
    
    try:
        # Create parameter functions instance
        pf = ParameterFunctions(db_session)
        
        # Test stocks
        test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
        
        print("Testing Parameter Functions")
        print("=" * 50)
        
        for symbol in test_symbols:
            print(f"\nTesting {symbol}:")
            print("-" * 30)
            
            try:
                # Test individual functions
                quality_score = pf.get_quality_score(symbol)
                pe_ratio = pf.get_pe_ratio(symbol)
                current_price = pf.get_current_price(symbol)
                sector = pf.get_sector(symbol)
                market_cap = pf.get_market_cap(symbol)
                
                print(f"  Quality Score: {quality_score}")
                print(f"  P/E Ratio: {pe_ratio}")
                print(f"  Current Price: ${current_price:.2f}" if current_price else "  Current Price: N/A")
                print(f"  Sector: {sector}")
                print(f"  Market Cap: ${market_cap:,.0f}" if market_cap else "  Market Cap: N/A")
                
                # Test boolean functions
                meets_quality = pf.meets_quality_requirement(symbol, 70)
                meets_valuation = pf.meets_valuation_requirement(symbol, 25, 3)
                
                print(f"  Meets Quality (70+): {meets_quality}")
                print(f"  Meets Valuation (P/E<25, P/B<3): {meets_valuation}")
                
            except Exception as e:
                print(f"  Error testing {symbol}: {e}")
        
        print("\n" + "=" * 50)
        print("Testing get_all_parameters_for_stock function:")
        print("-" * 50)
        
        # Test the convenience function
        for symbol in test_symbols[:2]:  # Just test first two to avoid too much output
            print(f"\nAll parameters for {symbol}:")
            all_params = get_all_parameters_for_stock(db_session, symbol)
            
            for param_name, param_value in all_params.items():
                if param_value is not None:
                    if isinstance(param_value, float):
                        print(f"  {param_name}: {param_value:.2f}")
                    else:
                        print(f"  {param_name}: {param_value}")
                else:
                    print(f"  {param_name}: N/A")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db_session.close()


if __name__ == "__main__":
    test_parameter_functions()
