"""
Stock Scoring Library
Handles calculating and saving stock scores (overall_score, risk_score, sector) to the database.
All scoring thresholds, sector overrides and keywords are loaded from config/stock-bucketing.yaml.
"""

import yaml
import logging
from typing import Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from sqlalchemy.orm import Session

from octopus.data_providers.yahoo_finance import YahooFinanceService

from storage.repositories import RepositoryFactory
from storage.models import Instrument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'stock-bucketing.yaml'


def _load_bucketing_config() -> Dict:
    try:
        with open(_CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Could not load stock-bucketing config from {_CONFIG_PATH}: {e}")
        return {}


_cfg = _load_bucketing_config()
_thresholds: Dict = _cfg.get('scoring_thresholds', {})
_sector_overrides: Dict = _cfg.get('sector_overrides', {})
_sector_keywords: Dict = _cfg.get('sector_keywords', {})
_mega_cap_threshold: float = _cfg.get('mega_cap_threshold', 1_000_000_000_000)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class StockData:
    """Holds the raw financial metrics fetched from Yahoo Finance."""
    name: str
    sector: str
    industry: str
    description: str
    market_cap: float
    beta: float
    dividend_yield: float
    debt_to_equity: float
    profit_margins: float
    trailing_pe: Optional[float]
    forward_pe: Optional[float]
    revenue_growth: float
    return_on_equity: float


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _safe_get(info: dict, key: str, default=0, multiplier: float = 1) -> float:
    value = info.get(key, default)
    if value is None:
        return default
    try:
        result = float(value) * multiplier
        if not (-1e10 < result < 1e10):
            return default
        return result
    except (ValueError, TypeError):
        return default


def _safe_percentage(info: dict, key: str, default: float = 0) -> float:
    return _safe_get(info, key, default, multiplier=100)


def _clamp(value: float, min_val: float = 0, max_val: float = 100) -> float:
    return max(min_val, min(max_val, value))


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------


def fetch_stock_data(ticker: str) -> StockData:
    """
    Fetch required stock metrics from Yahoo Finance via octopus wrapper.

    Raises:
        ValueError: If the ticker is invalid or data cannot be retrieved.
    """
    ticker = ticker.upper().strip()
    try:
        # Use yfinance directly to fetch comprehensive stock data
        import yfinance as yf
        
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Extract required fields with safe defaults
        name = info.get('longName') or info.get('shortName') or ticker
        sector = info.get('sector') or 'Unknown'
        industry = info.get('industry') or 'Unknown'
        description = info.get('longBusinessSummary') or info.get('description') or ''
        
        # Market cap - convert to float if present
        market_cap = info.get('marketCap')
        if market_cap:
            try:
                market_cap = float(market_cap)
            except (ValueError, TypeError):
                market_cap = 0.0
        else:
            market_cap = 0.0
        
        # Beta
        beta = info.get('beta')
        if beta:
            try:
                beta = float(beta)
            except (ValueError, TypeError):
                beta = 1.0
        else:
            beta = 1.0
        
        # Dividend yield - convert from percentage to decimal if needed
        dividend_yield = info.get('dividendYield')
        if dividend_yield:
            try:
                dividend_yield = float(dividend_yield)
                # If it looks like a percentage (e.g., 2.5 for 2.5%), convert to decimal
                if dividend_yield > 1:
                    dividend_yield = dividend_yield / 100.0
            except (ValueError, TypeError):
                dividend_yield = 0.0
        else:
            dividend_yield = 0.0
        
        # Debt to equity
        debt_to_equity = info.get('debtToEquity')
        if debt_to_equity:
            try:
                debt_to_equity = float(debt_to_equity)
            except (ValueError, TypeError):
                debt_to_equity = 0.0
        else:
            debt_to_equity = 0.0
        
        # Profit margins
        profit_margins = info.get('profitMargins')
        if profit_margins:
            try:
                profit_margins = float(profit_margins)
            except (ValueError, TypeError):
                profit_margins = 0.0
        else:
            profit_margins = 0.0
        
        # Trailing PE
        trailing_pe = info.get('trailingPE')
        if trailing_pe:
            try:
                trailing_pe = float(trailing_pe)
            except (ValueError, TypeError):
                trailing_pe = None
        
        # Forward PE
        forward_pe = info.get('forwardPE')
        if forward_pe:
            try:
                forward_pe = float(forward_pe)
            except (ValueError, TypeError):
                forward_pe = None
        
        # Revenue growth - try to get from financials or use a default
        revenue_growth = 0.0
        try:
            # Try to get revenue growth from financials
            financials = stock.financials
            if not financials.empty and 'Total Revenue' in financials.index:
                revenue_data = financials.loc['Total Revenue']
                if len(revenue_data) >= 2:
                    current_rev = revenue_data.iloc[0]
                    previous_rev = revenue_data.iloc[1]
                    if previous_rev > 0:
                        revenue_growth = (current_rev - previous_rev) / previous_rev
        except:
            revenue_growth = 0.0
        
        # Return on equity
        return_on_equity = info.get('returnOnEquity')
        if return_on_equity:
            try:
                return_on_equity = float(return_on_equity)
            except (ValueError, TypeError):
                return_on_equity = 0.0
        else:
            return_on_equity = 0.0
        
        return StockData(
            name=name,
            sector=sector,
            industry=industry,
            description=description,
            market_cap=market_cap,
            beta=beta,
            dividend_yield=dividend_yield,
            debt_to_equity=debt_to_equity,
            profit_margins=profit_margins,
            trailing_pe=trailing_pe,
            forward_pe=forward_pe,
            revenue_growth=revenue_growth,
            return_on_equity=return_on_equity,
        )
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        raise ValueError(f"Could not fetch data for ticker {ticker}: {e}")


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------


def calculate_risk_score(data: StockData) -> int:
    """
    Calculate risk score (0-100, higher = safer).

    Components: beta, dividend yield, debt-to-equity, profit margins.
    """
    beta_baseline = _thresholds.get('beta_baseline', 1.0)
    beta_sensitivity = _thresholds.get('beta_sensitivity', 50)
    div_yield_target = _thresholds.get('div_yield_target', 4.0)
    debt_healthy = _thresholds.get('debt_to_equity_healthy', 1.0)
    debt_sensitivity = _thresholds.get('debt_sensitivity', 25)
    margin_sensitivity = _thresholds.get('margin_sensitivity', 5)

    beta_score = _clamp(100 - abs(data.beta - beta_baseline) * beta_sensitivity)
    div_score = _clamp(data.dividend_yield * (100 / div_yield_target))
    debt_penalty = max(0, (data.debt_to_equity - debt_healthy) * debt_sensitivity)
    debt_score = _clamp(100 - debt_penalty)
    margins_score = _clamp(data.profit_margins * margin_sensitivity)

    risk_score = (
        beta_score * 0.3 +
        div_score * 0.2 +
        debt_score * 0.3 +
        margins_score * 0.2
    )
    return round(risk_score)


def get_risk_style_bucket(risk_score: int) -> str:
    """Return human-readable risk style label from a numeric risk score."""
    safe_threshold = _thresholds.get('risk_safe_threshold', 70)
    moderate_threshold = _thresholds.get('risk_moderate_threshold', 50)

    if risk_score >= safe_threshold:
        return 'STEADY & SAFE'
    elif risk_score >= moderate_threshold:
        return 'MODERATE & BALANCED'
    else:
        return 'RISKY & WILD'


def calculate_overall_score(data: StockData, risk_score: int) -> int:
    """
    Compute overall quantitative score (0-100).

    Components: valuation (PE), growth, quality (ROE + margins), risk.
    """
    pe_fair_value = _thresholds.get('pe_fair_value', 20.0)
    pe_sensitivity = _thresholds.get('pe_sensitivity', 2.5)
    growth_sensitivity = _thresholds.get('growth_sensitivity', 5)
    roe_sensitivity = _thresholds.get('roe_sensitivity', 5)
    margin_sensitivity = _thresholds.get('margin_sensitivity', 5)

    pe = data.forward_pe if data.forward_pe is not None else data.trailing_pe

    if pe is None or pe <= 0:
        val_score = 40
    elif pe < pe_fair_value:
        val_score = _clamp(100 - (pe_fair_value - pe) * pe_sensitivity)
    else:
        val_score = _clamp(100 - (pe - pe_fair_value) * pe_sensitivity)

    growth_score = _clamp(50 + data.revenue_growth * growth_sensitivity)
    roe_score = _clamp(data.return_on_equity * roe_sensitivity)
    margin_score = _clamp(data.profit_margins * margin_sensitivity)
    quality_score = (roe_score + margin_score) / 2

    overall_score = (
        val_score * 0.25 +
        growth_score * 0.25 +
        quality_score * 0.25 +
        risk_score * 0.25
    )
    return round(overall_score)


def get_letter_grade(score: int) -> str:
    """Convert a numeric score to a letter grade."""
    if score >= _thresholds.get('grade_a_plus', 90):
        return 'A+'
    elif score >= _thresholds.get('grade_a', 80):
        return 'A'
    elif score >= _thresholds.get('grade_b_plus', 70):
        return 'B+'
    elif score >= _thresholds.get('grade_b', 60):
        return 'B'
    elif score >= _thresholds.get('grade_c', 50):
        return 'C'
    else:
        return 'D'


# ---------------------------------------------------------------------------
# Sector classification
# ---------------------------------------------------------------------------


def get_sector_bucket(ticker: str, data: StockData) -> str:
    """
    Determine the sector bucket for a stock.

    Priority order: explicit override → GICS sector mapping → keyword fallback.
    """
    ticker = ticker.upper()

    if ticker in _sector_overrides:
        return _sector_overrides[ticker]

    sector = data.sector.lower()
    industry = data.industry.lower()
    desc = data.description.lower()
    market_cap = data.market_cap

    if 'technology' in sector or 'software' in industry:
        return 'MEGA TECH' if market_cap > _mega_cap_threshold else 'NEW ECONOMY'

    if 'energy' in sector:
        return 'OLD ECONOMY'

    if 'industrials' in sector:
        if any(kw in desc for kw in ['electric vehicle', 'renewable', 'solar']):
            return 'NEW ECONOMY'
        return 'OLD ECONOMY'

    if 'materials' in sector or 'basic materials' in sector:
        return 'MATERIALS & MINING'

    if 'consumer' in sector:
        if any(kw in desc for kw in ['electric', 'ride', 'delivery', 'fintech', 'app', 'platform']):
            return 'NEW ECONOMY'
        return 'CONSUMER FAVORITES'

    if 'health' in sector:
        return 'HEALTHCARE'

    if 'financial' in sector:
        return 'FINANCIAL GIANTS'

    if 'utilities' in sector or 'utility' in sector:
        return 'INFRASTRUCTURE'

    if 'real estate' in sector:
        return 'REAL ESTATE'

    if 'communication' in sector:
        if any(kw in desc for kw in ['telecom', 'tower', 'wireless', 'broadband']):
            return 'INFRASTRUCTURE'
        return 'ENTERTAINMENT & MEDIA'

    # Keyword-matching fallback
    max_score = 0
    best_sector = 'OLD ECONOMY'
    for sec, keywords in _sector_keywords.items():
        score = sum(1 for kw in keywords if kw in desc or kw in industry)
        if score > max_score:
            max_score = score
            best_sector = sec

    return best_sector


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------


def score_and_classify_stock(ticker: str) -> Dict[str, Any]:
    """
    Fetch stock data and compute all scores/classifications in one call.

    Returns:
        Dict with keys: ticker, name, sector_bucket, risk_score, risk_style,
                        overall_score, letter_grade.

    Raises:
        ValueError: If data cannot be fetched for the ticker.
    """
    data = fetch_stock_data(ticker)
    sector_bucket = get_sector_bucket(ticker, data)
    risk_score = calculate_risk_score(data)
    risk_style = get_risk_style_bucket(risk_score)
    overall_score = calculate_overall_score(data, risk_score)
    letter_grade = get_letter_grade(overall_score)

    return {
        'ticker': ticker.upper(),
        'name': data.name,
        'sector_bucket': sector_bucket,
        'risk_score': risk_score,
        'risk_style': risk_style,
        'overall_score': overall_score,
        'letter_grade': letter_grade,
    }


# ---------------------------------------------------------------------------
# Database service
# ---------------------------------------------------------------------------


class StockScoringService:
    """Service for managing stock scoring data in the database."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.repo_factory = RepositoryFactory(db_session)

    def load_config(self, config_path: str = None) -> Dict:
        """Load stock bucketing configuration from YAML file."""
        path = config_path or str(_CONFIG_PATH)
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded stock bucketing config from {path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config from {path}: {e}")
            raise

    def compute_and_save(self, ticker: str) -> Optional[Instrument]:
        """
        Compute scores for a ticker using live data and persist them.

        Returns:
            Updated Instrument object, or None on failure.
        """
        try:
            scores = score_and_classify_stock(ticker)
            return self.save_stock_scores(
                ticker,
                scores['overall_score'],
                scores['risk_score'],
                scores['sector_bucket'],
            )
        except Exception as e:
            logger.error(f"Failed to compute and save scores for {ticker}: {e}")
            return None

    def save_stock_scores(
        self, ticker: str, overall_score: int, risk_score: int, sector: str
    ) -> Optional[Instrument]:
        """
        Persist stock scores to the instruments table.

        Creates the instrument row if it does not yet exist.
        """
        try:
            instrument_repo = self.repo_factory.instruments
            instrument = instrument_repo.get_by_symbol(ticker)

            if not instrument:
                logger.warning(f"Instrument {ticker} not found in database. Creating new entry.")
                instrument_data = {
                    "symbol": ticker.upper(),
                    "name": ticker.upper(),
                    "exchange": "Unknown",
                    "currency": "USD",
                    "overall_score": overall_score,
                    "risk_score": risk_score,
                    "sector": sector,
                }
                instrument = instrument_repo.create(instrument_data)
                logger.info(f"Created new instrument entry for {ticker} with scores")
            else:
                update_data = {
                    "overall_score": overall_score,
                    "risk_score": risk_score,
                    "sector": sector,
                }
                instrument = instrument_repo.update(instrument.id, update_data)
                logger.info(
                    f"Updated scores for {ticker}: overall={overall_score}, "
                    f"risk={risk_score}, sector={sector}"
                )

            return instrument

        except Exception as e:
            logger.error(f"Failed to save scores for {ticker}: {e}")
            return None

    def get_stock_scores(self, ticker: str) -> Optional[Dict]:
        """Return stored scores for a ticker, or None if not found."""
        try:
            instrument = self.repo_factory.instruments.get_by_symbol(ticker)
            if instrument and (
                instrument.overall_score is not None
                or instrument.risk_score is not None
                or instrument.sector is not None
            ):
                return {
                    "ticker": instrument.symbol,
                    "name": instrument.name,
                    "overall_score": instrument.overall_score,
                    "risk_score": instrument.risk_score,
                    "sector": instrument.sector,
                    "updated_at": instrument.updated_at,
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get scores for {ticker}: {e}")
            return None

    def batch_save_stock_scores(self, scores_data: Dict[str, Dict]) -> Dict[str, bool]:
        """
        Save scores for multiple stocks in batch.

        Args:
            scores_data: Mapping of ticker -> {overall_score, risk_score, sector}

        Returns:
            Mapping of ticker -> success flag.
        """
        results = {}
        for ticker, score_data in scores_data.items():
            try:
                overall_score = score_data.get('overall_score')
                risk_score = score_data.get('risk_score')
                sector = score_data.get('sector')

                if overall_score is None or risk_score is None or sector is None:
                    logger.warning(f"Incomplete score data for {ticker}, skipping")
                    results[ticker] = False
                    continue

                instrument = self.save_stock_scores(ticker, overall_score, risk_score, sector)
                results[ticker] = instrument is not None
            except Exception as e:
                logger.error(f"Failed to save batch scores for {ticker}: {e}")
                results[ticker] = False

        success_count = sum(1 for s in results.values() if s)
        logger.info(f"Batch save completed: {success_count}/{len(results)} successful")
        return results

    def get_all_scored_instruments(self) -> list:
        """Return all instruments that have at least one score field populated."""
        try:
            instruments = self.repo_factory.instruments.get_all(active_only=True)
            return [
                {
                    "id": i.id,
                    "symbol": i.symbol,
                    "name": i.name,
                    "overall_score": i.overall_score,
                    "risk_score": i.risk_score,
                    "sector": i.sector,
                    "updated_at": i.updated_at,
                }
                for i in instruments
                if i.overall_score is not None
                or i.risk_score is not None
                or i.sector is not None
            ]
        except Exception as e:
            logger.error(f"Failed to get scored instruments: {e}")
            return []

    def clear_stock_scores(self, ticker: str) -> bool:
        """Clear scores for a specific stock."""
        try:
            instrument = self.repo_factory.instruments.get_by_symbol(ticker)
            if instrument:
                self.repo_factory.instruments.update(
                    instrument.id,
                    {"overall_score": None, "risk_score": None, "sector": None},
                )
                logger.info(f"Cleared scores for {ticker}")
                return True
            logger.warning(f"Instrument {ticker} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to clear scores for {ticker}: {e}")
            return False


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def save_stock_scores_to_db(
    db_session: Session, ticker: str, overall_score: int, risk_score: int, sector: str
) -> Optional[Instrument]:
    """Save stock scores to the database."""
    return StockScoringService(db_session).save_stock_scores(
        ticker, overall_score, risk_score, sector
    )


def get_stock_scores_from_db(db_session: Session, ticker: str) -> Optional[Dict]:
    """Retrieve stored scores for a ticker from the database."""
    return StockScoringService(db_session).get_stock_scores(ticker)
