# Analysis Module

## Overview

The **Analysis** module is the quantitative evaluation and stock bucketing layer of the PaperProfit trading platform. It provides comprehensive stock analysis through a sophisticated scoring system that evaluates stocks across multiple dimensions including risk, valuation, growth, and quality metrics. The module categorizes stocks into intuitive buckets for sector classification and risk profiles.

## Architecture

The Analysis module is built around a systematic evaluation framework with three main components:

### 1. **Data Acquisition**
- Fetches stock data from Yahoo Finance via yfinance library
- Robust error handling for missing or invalid data
- Validation and normalization of financial metrics
- Safe handling of edge cases (negative values, missing data, infinity)

### 2. **Scoring Engine**
- **Risk Score**: Evaluates stock stability based on beta, dividends, debt, and margins
- **Valuation Score**: Assesses stock price fairness using PE ratios
- **Growth Score**: Measures revenue growth momentum
- **Quality Score**: Evaluates profitability through ROE and margins
- **Overall Score**: Weighted composite of all scoring dimensions

### 3. **Bucketing System**
- **Sector Buckets**: 10 categories for industry/sector classification
- **Risk Style Buckets**: 3 categories for risk profile (Safe, Balanced, Wild)
- **Letter Grades**: A+ through D grading scale for overall quality

## Sector Buckets

The module classifies stocks into 10 intuitive sector categories:

1. **MEGA TECH** - Trillion-dollar tech giants (AAPL, GOOGL, MSFT, AMZN, META)
2. **OLD ECONOMY** - Traditional industrial and energy companies (XOM, BA, GE)
3. **NEW ECONOMY** - Disruptive modern businesses (TSLA, UBER, NFLX)
4. **CONSUMER FAVORITES** - Popular retail and consumer brands (SBUX, MCD, NKE)
5. **HEALTHCARE** - Pharmaceutical, biotech, and medical devices (PFE, UNH)
6. **FINANCIAL GIANTS** - Banks, payment processors, and investment firms (JPM, V, GS)
7. **INFRASTRUCTURE** - Utilities, telecom, and essential services (NEE, VZ, AMT)
8. **REAL ESTATE** - REITs and property companies (DLR, SPG, EQR)
9. **MATERIALS & MINING** - Mining, metals, and commodities (NEM, FCX, CF)
10. **ENTERTAINMENT & MEDIA** - Entertainment, gaming, and media (DIS, EA, SPOT)

### Classification Logic
- **Manual Overrides**: 40+ hand-curated ticker assignments for accuracy
- **Market Cap Rules**: Companies over $1T automatically classified as MEGA TECH
- **GICS Sector Mapping**: Standard sector classification as baseline
- **Keyword Analysis**: Description and industry text analysis for ambiguous cases
- **Nuanced Detection**: Distinguishes new vs old economy within sectors

## Risk Style Buckets

Stocks are classified into risk profiles based on a 0-100 risk score:

### STEADY & SAFE (70-100)
- Low volatility (beta near or below 1.0)
- Healthy dividend yields
- Strong profit margins
- Conservative debt levels

### MODERATE & BALANCED (50-69)
- Moderate volatility
- Balanced risk-reward profile
- Average financial health
- Suitable for diversified portfolios

### RISKY & WILD (0-49)
- High volatility (beta significantly above 1.0)
- Limited or no dividends
- Higher debt levels or lower margins
- Growth-focused with higher risk

## Scoring Methodology

### Risk Score Components (0-100)
- **Beta Score (30%)**: Lower volatility = higher score
  - Baseline: 1.0 beta = 75 points
  - Sensitivity: 50 points per unit deviation
- **Dividend Score (20%)**: Higher yield = higher score
  - Target: 4% yield = 100 points
- **Debt Score (30%)**: Lower debt-to-equity = higher score
  - Healthy: <1.0 debt/equity ratio
  - Penalty: 25 points per ratio point above 1.0
- **Margin Score (20%)**: Higher profit margins = higher score
  - Excellent: 20%+ margins = 100 points
  - Sensitivity: 5 points per percentage

### Overall Score Components (0-100)
- **Valuation (25%)**: PE ratio analysis
  - Fair value: 20 PE ratio
  - Expensive: 40+ PE ratio
  - Penalty/bonus: 2.5 points per PE point deviation
- **Growth (25%)**: Revenue growth rate
  - Baseline: 0% growth = 50 points
  - Sensitivity: 5 points per percentage of growth
- **Quality (25%)**: Average of ROE and margin scores
  - Excellence threshold: 20% ROE or margins
- **Risk (25%)**: Risk score from above

### Letter Grade Thresholds
- **A+**: 90-100 points
- **A**: 80-89 points
- **B+**: 70-79 points
- **B**: 60-69 points
- **C**: 50-59 points
- **D**: 0-49 points

## Key Features

### Robust Data Handling
- **Safe Value Extraction**: Handles missing, null, or invalid data gracefully
- **Bounds Checking**: Prevents infinity and NaN values from corrupting scores
- **Default Values**: Sensible defaults for missing financial metrics
- **Validation**: Confirms ticker validity before analysis

### Comprehensive Metrics
- Market cap, beta, dividend yield
- Debt-to-equity, profit margins
- PE ratios (trailing and forward)
- Revenue growth, return on equity
- Industry and sector information

### Multiple Output Formats
- **Simple Summary**: Concise 4-line analysis with ticker, sector, risk style, and grade
- **Detailed Dictionary**: Complete metrics and scores for programmatic access
- **Description Truncation**: Intelligent summarization of business descriptions

### Error Handling
- Graceful handling of invalid tickers
- Logging for debugging and monitoring
- Clear error messages for users
- Fallback values for unavailable metrics

## API Integration

The Analysis module is integrated into the main API through instrument endpoints:

```python
@app.get("/api/instruments/{symbol}")
async def get_instrument(symbol: str, db: Session = Depends(get_db)):
    # Fetch stock buckets and analysis
    analysis = get_stock_buckets(symbol)

    # Or get detailed metrics
    detailed = get_stock_buckets_detailed(symbol)
```

### Available Functions
- `get_stock_buckets(ticker)` - Returns formatted string summary
- `get_stock_buckets_detailed(ticker)` - Returns comprehensive dictionary

## Use Cases

### Portfolio Construction
- **Diversification**: Ensure coverage across sector buckets
- **Risk Management**: Balance safe, balanced, and risky stocks
- **Quality Filtering**: Screen stocks by letter grade

### Stock Screening
- Find high-quality STEADY & SAFE stocks (A/A+ grade + 70+ risk score)
- Identify undervalued opportunities (low PE + high quality)
- Spot growth plays (high revenue growth + NEW ECONOMY sector)

### Educational Tool
- Learn sector classification and stock characteristics
- Understand risk-reward tradeoffs
- Compare stocks within and across sectors

## Configuration

### Scoring Thresholds
All thresholds are configured in the `ScoringThresholds` class:
- Beta sensitivity and baseline
- Dividend yield targets
- Debt-to-equity healthy levels
- Margin and ROE excellence thresholds
- PE ratio fair value and expensive thresholds
- Risk style boundaries
- Grade boundaries

### Sector Configuration
- `SECTOR_OVERRIDES` - Manual ticker-to-sector mappings
- `SECTOR_KEYWORDS` - Keyword lists for automated classification
- `MEGA_CAP_THRESHOLD` - Market cap threshold for MEGA TECH ($1T)

## Purpose

The Analysis module serves as the intelligent evaluation engine of PaperProfit, transforming raw financial data into actionable insights through systematic scoring and intuitive categorization. By combining quantitative metrics with qualitative bucketing, it enables users to quickly assess stocks, build diversified portfolios, and make informed trading decisions based on a consistent and transparent methodology.
