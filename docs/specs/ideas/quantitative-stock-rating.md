# Quantitative Stock Rating System (QSR)

## Overview
The quantitative stock rating system provides an objective, data-driven evaluation of stocks across four key dimensions. Each stock receives individual scores (0-100 scale) for Past Performance, Growth, Risk, and Valuation, which are then combined into an overall rating.

## Score Categories

### 1. Past Performance Score (0-100)
Evaluates historical stock performance and consistency.

#### Metrics
- **1-Year Return** (30%): Total return over the past 12 months
- **3-Year Annualized Return** (25%): CAGR over 3 years
- **5-Year Annualized Return** (20%): CAGR over 5 years
- **Relative Performance vs S&P 500** (15%): Alpha generation
- **Consistency Score** (10%): Sharpe ratio over past 3 years

#### Calculation Method
```python
# Scoring thresholds (example)
def calculate_past_performance_score(stock_data):
    score = 0

    # 1-Year Return (0-30 points)
    one_year_return = stock_data['1y_return']
    if one_year_return >= 30: score += 30
    elif one_year_return >= 15: score += 25
    elif one_year_return >= 0: score += 15
    else: score += max(0, 15 + one_year_return / 2)

    # 3-Year Return (0-25 points)
    three_year_cagr = stock_data['3y_cagr']
    if three_year_cagr >= 20: score += 25
    elif three_year_cagr >= 10: score += 20
    elif three_year_cagr >= 0: score += 10
    else: score += max(0, 10 + three_year_cagr / 2)

    # 5-Year Return (0-20 points)
    five_year_cagr = stock_data['5y_cagr']
    if five_year_cagr >= 20: score += 20
    elif five_year_cagr >= 10: score += 15
    elif five_year_cagr >= 0: score += 8
    else: score += max(0, 8 + five_year_cagr / 2)

    # Alpha vs S&P 500 (0-15 points)
    alpha = stock_data['alpha_vs_spy']
    if alpha >= 10: score += 15
    elif alpha >= 5: score += 12
    elif alpha >= 0: score += 8
    else: score += max(0, 8 + alpha / 2)

    # Sharpe Ratio (0-10 points)
    sharpe = stock_data['sharpe_ratio']
    if sharpe >= 1.5: score += 10
    elif sharpe >= 1.0: score += 7
    elif sharpe >= 0.5: score += 4
    else: score += 0

    return min(100, score)
```

#### Data Sources
- Historical price data: yfinance, Alpha Vantage
- Benchmark data: S&P 500 (^GSPC)

---

### 2. Growth Score (0-100)
Measures company's growth trajectory and future potential.

#### Metrics
- **Revenue Growth (YoY)** (25%): Year-over-year revenue growth rate
- **Earnings Growth (YoY)** (25%): Year-over-year EPS growth
- **Revenue Growth (3Y CAGR)** (20%): 3-year revenue CAGR
- **Earnings Growth (3Y CAGR)** (15%): 3-year earnings CAGR
- **Free Cash Flow Growth** (10%): YoY FCF growth
- **Analyst Growth Estimates** (5%): Forward earnings growth estimates

#### Calculation Method
```python
def calculate_growth_score(fundamentals):
    score = 0

    # Revenue Growth YoY (0-25 points)
    rev_growth_yoy = fundamentals['revenue_growth_yoy']
    if rev_growth_yoy >= 25: score += 25
    elif rev_growth_yoy >= 15: score += 20
    elif rev_growth_yoy >= 5: score += 12
    elif rev_growth_yoy >= 0: score += 5
    else: score += 0

    # Earnings Growth YoY (0-25 points)
    eps_growth_yoy = fundamentals['eps_growth_yoy']
    if eps_growth_yoy >= 25: score += 25
    elif eps_growth_yoy >= 15: score += 20
    elif eps_growth_yoy >= 5: score += 12
    elif eps_growth_yoy >= 0: score += 5
    else: score += 0

    # Revenue Growth 3Y CAGR (0-20 points)
    rev_growth_3y = fundamentals['revenue_cagr_3y']
    if rev_growth_3y >= 20: score += 20
    elif rev_growth_3y >= 10: score += 15
    elif rev_growth_3y >= 5: score += 8
    else: score += 0

    # Earnings Growth 3Y CAGR (0-15 points)
    eps_growth_3y = fundamentals['eps_cagr_3y']
    if eps_growth_3y >= 20: score += 15
    elif eps_growth_3y >= 10: score += 10
    elif eps_growth_3y >= 5: score += 5
    else: score += 0

    # FCF Growth (0-10 points)
    fcf_growth = fundamentals['fcf_growth_yoy']
    if fcf_growth >= 20: score += 10
    elif fcf_growth >= 10: score += 7
    elif fcf_growth >= 0: score += 3
    else: score += 0

    # Analyst Estimates (0-5 points)
    forward_growth = fundamentals['forward_eps_growth']
    if forward_growth >= 15: score += 5
    elif forward_growth >= 10: score += 3
    elif forward_growth >= 5: score += 2
    else: score += 0

    return min(100, score)
```

#### Data Sources
- Financial statements: Financial Modeling Prep, Alpha Vantage
- Analyst estimates: Yahoo Finance

---

### 3. Risk Score (0-100)
Evaluates stock volatility and financial stability (higher score = lower risk).

#### Metrics
- **Beta** (25%): Volatility relative to market
- **Standard Deviation** (20%): Price volatility
- **Maximum Drawdown** (15%): Largest peak-to-trough decline
- **Debt-to-Equity Ratio** (15%): Financial leverage
- **Current Ratio** (10%): Liquidity position
- **Interest Coverage** (10%): Ability to service debt
- **Profit Margin Stability** (5%): Earnings consistency

#### Calculation Method
```python
def calculate_risk_score(risk_data):
    score = 0

    # Beta (0-25 points) - Lower is better
    beta = risk_data['beta']
    if beta <= 0.7: score += 25
    elif beta <= 1.0: score += 20
    elif beta <= 1.3: score += 12
    elif beta <= 1.5: score += 5
    else: score += 0

    # Standard Deviation (0-20 points) - Lower is better
    std_dev = risk_data['annual_std_dev']
    if std_dev <= 15: score += 20
    elif std_dev <= 25: score += 15
    elif std_dev <= 35: score += 8
    elif std_dev <= 50: score += 3
    else: score += 0

    # Max Drawdown (0-15 points) - Lower is better
    max_drawdown = abs(risk_data['max_drawdown'])
    if max_drawdown <= 15: score += 15
    elif max_drawdown <= 25: score += 12
    elif max_drawdown <= 35: score += 7
    elif max_drawdown <= 50: score += 3
    else: score += 0

    # Debt-to-Equity (0-15 points) - Lower is better
    debt_to_equity = risk_data['debt_to_equity']
    if debt_to_equity <= 0.5: score += 15
    elif debt_to_equity <= 1.0: score += 12
    elif debt_to_equity <= 1.5: score += 7
    elif debt_to_equity <= 2.0: score += 3
    else: score += 0

    # Current Ratio (0-10 points)
    current_ratio = risk_data['current_ratio']
    if current_ratio >= 2.0: score += 10
    elif current_ratio >= 1.5: score += 7
    elif current_ratio >= 1.0: score += 3
    else: score += 0

    # Interest Coverage (0-10 points)
    interest_coverage = risk_data['interest_coverage']
    if interest_coverage >= 10: score += 10
    elif interest_coverage >= 5: score += 7
    elif interest_coverage >= 3: score += 4
    elif interest_coverage >= 1.5: score += 2
    else: score += 0

    # Profit Margin Stability (0-5 points)
    margin_std = risk_data['profit_margin_std']
    if margin_std <= 2: score += 5
    elif margin_std <= 5: score += 3
    elif margin_std <= 10: score += 1
    else: score += 0

    return min(100, score)
```

#### Data Sources
- Price volatility: yfinance
- Financial ratios: Financial Modeling Prep, Alpha Vantage

---

### 4. Valuation Score (0-100)
Determines if stock is undervalued, fairly valued, or overvalued.

#### Metrics
- **P/E Ratio vs Industry** (25%): Price-to-earnings relative to sector
- **P/B Ratio vs Industry** (15%): Price-to-book relative to sector
- **PEG Ratio** (20%): P/E to growth ratio
- **P/S Ratio vs Industry** (10%): Price-to-sales relative to sector
- **EV/EBITDA vs Industry** (15%): Enterprise value to EBITDA
- **Dividend Yield vs Industry** (10%): Dividend attractiveness
- **Price vs 52-Week Range** (5%): Current price position

#### Calculation Method
```python
def calculate_valuation_score(valuation_data):
    score = 0

    # P/E vs Industry (0-25 points) - Lower is better
    pe_percentile = valuation_data['pe_industry_percentile']
    if pe_percentile <= 25: score += 25  # Bottom quartile (cheap)
    elif pe_percentile <= 50: score += 18
    elif pe_percentile <= 75: score += 10
    else: score += 3  # Top quartile (expensive)

    # P/B vs Industry (0-15 points)
    pb_percentile = valuation_data['pb_industry_percentile']
    if pb_percentile <= 25: score += 15
    elif pb_percentile <= 50: score += 10
    elif pb_percentile <= 75: score += 5
    else: score += 2

    # PEG Ratio (0-20 points)
    peg = valuation_data['peg_ratio']
    if peg <= 1.0: score += 20  # Undervalued
    elif peg <= 1.5: score += 15
    elif peg <= 2.0: score += 8
    elif peg <= 3.0: score += 3
    else: score += 0  # Overvalued

    # P/S vs Industry (0-10 points)
    ps_percentile = valuation_data['ps_industry_percentile']
    if ps_percentile <= 25: score += 10
    elif ps_percentile <= 50: score += 7
    elif ps_percentile <= 75: score += 3
    else: score += 1

    # EV/EBITDA vs Industry (0-15 points)
    ev_ebitda_percentile = valuation_data['ev_ebitda_percentile']
    if ev_ebitda_percentile <= 25: score += 15
    elif ev_ebitda_percentile <= 50: score += 10
    elif ev_ebitda_percentile <= 75: score += 5
    else: score += 2

    # Dividend Yield vs Industry (0-10 points)
    div_percentile = valuation_data['div_yield_percentile']
    if div_percentile >= 75: score += 10  # High yield
    elif div_percentile >= 50: score += 7
    elif div_percentile >= 25: score += 4
    else: score += 2

    # Price vs 52-Week Range (0-5 points)
    price_position = valuation_data['price_52w_position']
    if price_position <= 0.3: score += 5  # Near 52-week low
    elif price_position <= 0.5: score += 3
    elif price_position <= 0.7: score += 2
    else: score += 0  # Near 52-week high

    return min(100, score)
```

#### Data Sources
- Valuation ratios: Financial Modeling Prep, yfinance
- Industry comparisons: Financial Modeling Prep sector metrics

---

## Overall Rating

### Aggregation Method
The overall rating combines all four scores with customizable weights:

```python
def calculate_overall_rating(scores, weights=None):
    """
    Calculate weighted overall rating

    Args:
        scores: dict with keys 'performance', 'growth', 'risk', 'valuation'
        weights: dict with same keys, default equal weights

    Returns:
        Overall score (0-100) and rating letter grade
    """
    if weights is None:
        weights = {
            'performance': 0.25,
            'growth': 0.30,
            'risk': 0.20,
            'valuation': 0.25
        }

    overall_score = (
        scores['performance'] * weights['performance'] +
        scores['growth'] * weights['growth'] +
        scores['risk'] * weights['risk'] +
        scores['valuation'] * weights['valuation']
    )

    # Convert to letter grade
    if overall_score >= 90: grade = 'A+'
    elif overall_score >= 85: grade = 'A'
    elif overall_score >= 80: grade = 'A-'
    elif overall_score >= 75: grade = 'B+'
    elif overall_score >= 70: grade = 'B'
    elif overall_score >= 65: grade = 'B-'
    elif overall_score >= 60: grade = 'C+'
    elif overall_score >= 55: grade = 'C'
    elif overall_score >= 50: grade = 'C-'
    elif overall_score >= 45: grade = 'D+'
    elif overall_score >= 40: grade = 'D'
    else: grade = 'F'

    return overall_score, grade
```

### Default Weights
- **Growth**: 30% (most important for long-term returns)
- **Past Performance**: 25% (track record matters)
- **Valuation**: 25% (entry price affects returns)
- **Risk**: 20% (capital preservation)

### Customizable Weight Profiles

**Growth Investor Profile**
```python
growth_weights = {
    'performance': 0.20,
    'growth': 0.50,
    'risk': 0.10,
    'valuation': 0.20
}
```

**Value Investor Profile**
```python
value_weights = {
    'performance': 0.20,
    'growth': 0.15,
    'risk': 0.20,
    'valuation': 0.45
}
```

**Conservative Profile**
```python
conservative_weights = {
    'performance': 0.25,
    'growth': 0.15,
    'risk': 0.40,
    'valuation': 0.20
}
```

---

## Implementation Plan

### Phase 1: Data Collection
1. Create data fetcher classes for each score category
2. Implement caching to minimize API calls
3. Handle missing data gracefully

### Phase 2: Scoring Engine
1. Implement scoring functions for each category
2. Create score normalization utilities
3. Build aggregation engine

### Phase 3: API Endpoints
```python
# New endpoints to add
GET /api/instruments/{symbol}/rating
    Returns: {
        "symbol": "AAPL",
        "overall_score": 82.5,
        "overall_grade": "A-",
        "scores": {
            "performance": 85,
            "growth": 88,
            "risk": 75,
            "valuation": 82
        },
        "metrics": {...},  # Detailed metrics used
        "updated_at": "2026-02-13T10:30:00Z"
    }

POST /api/instruments/{symbol}/rating
    Body: {
        "weights": {
            "performance": 0.25,
            "growth": 0.30,
            "risk": 0.20,
            "valuation": 0.25
        }
    }
    Returns: Custom weighted rating

GET /api/instruments/ratings/batch
    Query: ?symbols=AAPL,MSFT,GOOGL
    Returns: Array of ratings for multiple stocks
```

### Phase 4: UI Components
1. Rating display component (score cards)
2. Radar chart visualization
3. Detailed breakdown view
4. Comparison table

### Phase 5: Caching & Updates
1. Cache ratings for 24 hours
2. Background job to update popular stock ratings
3. On-demand calculation for less common stocks

---

## Database Schema

### New Table: `stock_ratings`
```sql
CREATE TABLE stock_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(10) NOT NULL,
    overall_score FLOAT NOT NULL,
    overall_grade VARCHAR(3) NOT NULL,
    performance_score FLOAT NOT NULL,
    growth_score FLOAT NOT NULL,
    risk_score FLOAT NOT NULL,
    valuation_score FLOAT NOT NULL,
    metrics_json TEXT,  -- Store all detailed metrics
    calculation_weights TEXT,  -- Store weights used
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol)
);

CREATE INDEX idx_stock_ratings_symbol ON stock_ratings(symbol);
CREATE INDEX idx_stock_ratings_overall_score ON stock_ratings(overall_score DESC);
CREATE INDEX idx_stock_ratings_updated_at ON stock_ratings(updated_at);
```

---

## Testing & Validation

### Test Cases
1. **Edge Cases**: Negative earnings, missing data, outliers
2. **Sector Comparisons**: Tech vs utilities vs financials
3. **Extreme Values**: Very high/low ratios
4. **Historical Validation**: Backtest if high scores correlate with future returns

### Quality Metrics
- Score distribution should be roughly normal
- Top-rated stocks should outperform bottom-rated (backtesting)
- Scores should be stable over short periods (1 week)
- Industry peers should have similar scores

---

## Future Enhancements
1. **Machine Learning**: Train models on historical data
2. **Sector-Specific Scoring**: Different weights per sector
3. **Momentum Indicators**: Add technical analysis scores
4. **Sentiment Analysis**: Incorporate news sentiment
5. **Insider Trading**: Track insider buy/sell activity
6. **Institutional Ownership**: Monitor institutional interest
