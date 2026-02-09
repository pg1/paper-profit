#!/usr/bin/env python3

"""pytest tests for fundamental and technical parameter functions.

These are lightweight integration-style tests that call the project's
fundamental and technical functions for a real ticker (AAPL). The tests
are resilient to missing external data: they assert that the functions
return well-formed values (numbers, dicts, or None) rather than hard
numeric expectations.
"""

import sys
import os
from typing import Any, Dict

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import SessionLocal
from analysis.fundamental_functions import FundamentalFunctions, get_all_parameters_for_stock
from analysis.technical_functions import TechnicalFunctions, get_all_technical_indicators_for_stock


def _is_number_or_none(x: Any) -> bool:
    return x is None or isinstance(x, (int, float))


def test_fundamental_functions_aapl():
    """Fundamental functions should return a well-formed parameters dict for AAPL."""
    db = SessionLocal()
    try:
        pf = FundamentalFunctions(db)
        params = get_all_parameters_for_stock(db, "AAPL")

        if __name__ == "__main__":
            print(params)

        assert isinstance(params, dict), "Expected dict of parameters"
        # Basic required keys
        for key in ["symbol", "pe_ratio", "market_cap", "quality_score", "current_price"]:
            assert key in params

        # symbol should match
        assert params.get("symbol") == "AAPL"

        # numeric-ish fields are either numbers or None
        for num_key in ["pe_ratio", "pb_ratio", "dividend_yield", "beta", "market_cap", "current_price", "roe"]:
            assert _is_number_or_none(params.get(num_key)), f"{num_key} should be number or None"

        # quality and conviction scores should be int or None
        q = params.get("quality_score")
        if q is not None:
            assert isinstance(q, int)
            assert 0 <= q <= 100

    finally:
        db.close()


def test_technical_functions_aapl():
    """Technical functions should return well-formed indicators for AAPL."""
    db = SessionLocal()
    try:
        tf = TechnicalFunctions(db)
        indicators = get_all_technical_indicators_for_stock(db, "AAPL")
        if __name__ == "__main__":
            print(indicators)

        assert isinstance(indicators, dict), "Expected dict of technical indicators"

        # Basic keys
        for key in ["symbol", "current_price", "sma_20", "rsi"]:
            assert key in indicators

        assert indicators.get("symbol") == "AAPL"

        # numeric fields or None
        for num_key in ["current_price", "sma_20", "sma_50", "sma_200", "ema_20", "rsi", "volatility"]:
            assert _is_number_or_none(indicators.get(num_key)), f"{num_key} should be number or None"

        # MACD if present should be dict with macd/signal/histogram
        macd = indicators.get("macd")
        if macd is not None:
            assert isinstance(macd, dict)
            for sub in ["macd", "signal", "histogram"]:
                assert _is_number_or_none(macd.get(sub)), f"macd.{sub} should be number or None"

    finally:
        db.close()

if __name__ == "__main__":
    print("="*60)
    print("Testing AI Parameter Implementation")
    print("="*60)
    
    test_fundamental_functions_aapl()
    test_technical_functions_aapl()