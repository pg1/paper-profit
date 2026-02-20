# Stock Bucketing System

## Overview
A 2-level bucket system that categorizes stocks in plain English for easy understanding. This system helps users quickly understand what a company does (Level 1: Sector) and its risk/volatility profile (Level 2: Risk Style).

## Level 1: Sector Buckets
Describes the industry or business category in simple terms.

### MEGA TECH
Giant technology companies that dominate their markets
- Examples: iPhone maker (AAPL), Search giant (GOOGL), Social media giant (META), Cloud king (MSFT), E-commerce titan (AMZN)

### OLD ECONOMY
Traditional industrial and energy companies
- Examples: Oil giant (XOM), Airplane maker (BA), Industrial conglomerate (GE), Chemical maker (DOW), Railroad operator (UNP)

### NEW ECONOMY
Modern, disruptive companies reshaping industries
- Examples: Electric cars (TSLA), Streaming service (NFLX), Ride-sharing (UBER), Food delivery (DASH), Fintech pioneer (SQ)

### CONSUMER FAVORITES
Retail, food, and lifestyle brands people know and love
- Examples: Coffee chain (SBUX), Fast food king (MCD), Athletic wear (NKE), Luxury goods (LVMH), Home improvement (HD)

### HEALTHCARE
Medical, pharmaceutical, and biotech companies
- Examples: Drug maker (PFE), Biotech innovator (GILD), Medical devices (MDT), Health insurer (UNH), Gene therapy (CRSP)

### FINANCIAL GIANTS
Banks, payment processors, and financial services
- Examples: Big bank (JPM), Credit card network (V), Investment bank (GS), Insurance giant (BRK), Payment platform (PYPL)

### INFRASTRUCTURE
Utilities, telecom, and essential services
- Examples: Electric utility (NEE), Telecom provider (VZ), Water utility (AWK), Cell tower operator (AMT), Natural gas (DUK)

### REAL ESTATE
Property developers, REITs, and real estate services
- Examples: Data center REIT (DLR), Apartment REIT (EQR), Shopping malls (SPG), Office buildings (BXP), Self-storage (PSA)

### MATERIALS & MINING
Raw materials, mining, and commodity producers
- Examples: Gold miner (NEM), Steel maker (X), Copper producer (FCX), Aluminum (AA), Agricultural chemicals (CF)

### ENTERTAINMENT & MEDIA
Content creators, studios, and media companies
- Examples: Movie studio (DIS), Gaming company (EA), Music streaming (SPOT), Sports network (DKNG), Publishing (NYT)

## Level 2: Risk Style Buckets
Describes the stock's volatility and risk characteristics, typically derived from the quantitative Risk Score.

### STEADY & SAFE
Low volatility, established companies with stable earnings
- **Characteristics:**
  - Low beta (< 1.0)
  - Consistent dividend payments
  - Stable profit margins
  - Strong balance sheets (low debt-to-equity)
  - Lower growth but predictable returns
- **Risk Score:** Typically 70-100
- **Examples:** Utilities, consumer staples, established industrials

### MODERATE & BALANCED
Average volatility with balanced risk/reward profile
- **Characteristics:**
  - Beta around 1.0
  - Moderate growth potential
  - Reasonable debt levels
  - Some dividend payments
  - Established business model
- **Risk Score:** Typically 50-69
- **Examples:** Large-cap tech, major banks, healthcare leaders

### RISKY & WILD
High volatility, growth-focused with significant price swings
- **Characteristics:**
  - High beta (> 1.5)
  - Minimal or no dividends
  - High growth potential
  - Unpredictable earnings
  - More speculative business models
- **Risk Score:** Typically below 50
- **Examples:** Small-cap biotech, unprofitable tech startups, speculative growth stocks

## Complete Examples

### Format: [SECTOR] - [RISK STYLE]: Description (TICKER)

**Steady Examples:**
- INFRASTRUCTURE - STEADY & SAFE: Electric utility (NEE)
- CONSUMER FAVORITES - STEADY & SAFE: Household products (PG)
- FINANCIAL GIANTS - STEADY & SAFE: Dividend bank (WFC)

**Moderate Examples:**
- MEGA TECH - MODERATE & BALANCED: iPhone maker (AAPL)
- HEALTHCARE - MODERATE & BALANCED: Drug maker (PFE)
- OLD ECONOMY - MODERATE & BALANCED: Airplane maker (BA)

**Risky Examples:**
- NEW ECONOMY - RISKY & WILD: Electric cars (TSLA)
- HEALTHCARE - RISKY & WILD: Gene therapy startup (CRSP)
- MEGA TECH - RISKY & WILD: AI chipmaker (NVDA)

## Integration with Quantitative Rating

The bucketing system complements the quantitative rating scores:

1. **Sector Bucket**: Determined by company's primary business (static, manually assigned)
2. **Risk Style Bucket**: Automatically determined by Risk Score from quantitative system
   - Risk Score 70-100 → STEADY & SAFE
   - Risk Score 50-69 → MODERATE & BALANCED
   - Risk Score 0-49 → RISKY & WILD

## User Experience

When displaying a stock, show:
```
AAPL - Apple Inc.
MEGA TECH - MODERATE & BALANCED: iPhone maker
Overall Rating: A+ (92/100)
```

This gives users instant context about:
1. What the company does (plain English)
2. How risky/volatile it is
3. How well it scores overall

## Implementation Notes

- Sector buckets should be stored as metadata for each stock
- Risk style buckets are calculated dynamically based on current Risk Score
- Plain English descriptions should be concise (2-4 words)
- Buckets should be displayed prominently in the UI
- Allow filtering by both sector and risk style
