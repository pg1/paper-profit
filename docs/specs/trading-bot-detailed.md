# Trading Bot System - Detailed Documentation

## Overview

The Trading Bot (`backend/app/jobs/trading_bot.py`) is the core automated trading system in the Paper Profit platform. It runs as a background job, configurable via the UI, and orchestrates the entire trading workflow from stock discovery to order execution. Each account is assigned a strategy which drives the bot's behaviour across instrument discovery, signal generation, portfolio construction, risk management, and trade execution.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Main TradingBot Class](#main-tradingbot-class)
3. [Module Components](#module-components)
   - [InstrumentDiscovery](#instrumentdiscovery)
   - [DataCollector](#datacollector)
   - [StrategySignal](#strategysignal)
   - [PortfolioManager](#portfoliomanager)
   - [RiskManager](#riskmanager)
   - [ExecutionManager](#executionmanager)
4. [Bot Run Lifecycle](#bot-run-lifecycle)
5. [Database Models](#database-models)
6. [Configuration and Parameters](#configuration-and-parameters)
7. [Error Handling and Logging](#error-handling-and-logging)
8. [Running the Bot](#running-the-bot)
9. [Conclusion](#conclusion)

## Architecture Overview

The Trading Bot follows a layered pipeline architecture:

```
Market Data Layer          (Yahoo Finance / Alpha Vantage / FMP)
        ↓
Feature / Indicator Engine (SMA, EMA, RSI, MACD, Bollinger Bands, VWAP, Fundamentals)
        ↓
Research Environment       (Stock discovery, scoring, filtering)
        ↓
Strategy Engine            (generate_signal → BUY / HOLD / SELL)
        ↓
Portfolio Construction     (position sizing, diversification rules)
        ↓
Risk Manager               (drawdown limits, sector caps, stop-loss)
        ↓
Execution Engine           (order creation, order processing)
        ↓
Logger                     (all decisions and events logged to system log)
```

**Module flow:**

```
TradingBot.run()
    ↓
PortfolioManager.get_active_accounts()
    ↓
For each account:
    PortfolioManager.get_account_positions()
    StrategySignal.parse_parameters()
    InstrumentDiscovery.get_stock_list()
    ↓
    For each stock:
        DataCollector.get_market_data()
        DataCollector.get_technical_indicators()
        ↓
        StrategySignal.generate_signal()
        ↓
        If signal != HOLD:
            RiskManager.calculate_position_size()
            RiskManager.check_risk_limits()
            ↓
            ExecutionManager.execute_trade()
        Else:
            ExecutionManager.log_hold_signal()
```

## Main TradingBot Class

The `TradingBot` class is the orchestrator that coordinates all modules. Key methods:

### `__init__(self, db: Session)`
Initializes all six modules with database session and repository factory.

### `run(self)`
Main execution loop:
1. Fetches all active accounts with strategies
2. Processes each account individually
3. Handles errors at account level
4. Logs completion

### `_process_account(self, account)`
Processes a single account:
1. Retrieves the account's strategy
2. Parses strategy parameters
3. Gets stock list for the strategy
4. Retrieves current positions
5. Processes each stock in the list

### `_process_stock(self, account, strategy, symbol, strategy_params, current_positions)`
Processes a single stock:
1. Gets or creates instrument
2. Collects market data and technical indicators
3. Generates trading signal
4. Executes trade with risk management if signal is not HOLD

### `_execute_trade_with_risk_management(...)`
Executes trades with risk checks:
- For BUY: Checks existing positions, max positions limit, calculates position size
- For SELL: Checks if position exists, gets sell quantity

## Module Components

### InstrumentDiscovery

**Location:** `backend/app/jobs/trading_bot/instrument_discovery.py`

**Purpose:** Discovers and manages instruments (stocks) for trading based on strategy parameters.

**Key Features:**
- Multiple stock universe selection methods
- Support for watchlists, screeners, and sector filters
- Fallback mechanisms for stock discovery

**Stock Universe Types:**
1. `strategy_list` - Uses the strategy's predefined stock list
2. `sector_filters` - Filters instruments by sector using `stock-bucketing.yaml` taxonomy (include/exclude)
3. `watchlist` - Gets all stocks from the watchlist
4. `screener` - Generic screener combining multiple filters (score, risk, sector)
5. `winners` - Top day gainers from Yahoo Finance
6. `losers` - Top day losers from Yahoo Finance

**Filtering pipeline:**
1. Start from strategy's configured stock list or universe
2. Apply sector cap filter (exclude over-represented sectors)
3. Score each stock using `overall_score` and `risk_score`
4. Rank by signal strength and score
5. Return top N candidates (configurable per strategy)

**Key Methods:**
- `get_stock_list(strategy)` - Parses stock list from strategy (JSON, comma-separated, or newline)
- `get_stocks_by_universe(strategy, limit)` - Main method to get stocks based on universe type
- `_get_watchlist_stocks()` - Retrieves stocks from watchlist
- `_get_screener_stocks(screener_type, limit)` - Gets stocks from Yahoo Finance screeners
- `_get_sector_filtered_stocks(strategy, limit)` - Filters by sector inclusion/exclusion

### DataCollector

**Location:** `backend/app/jobs/trading_bot/data_collector.py`

**Purpose:** Collects market data, technical indicators, and fundamental data for analysis.

**Key Features:**
- Fetches latest market data from database
- Retrieves technical indicators using TechnicalFunctions module
- Collects fundamental data using FundamentalFunctions module
- Integrates with data providers for real-time data
- Collects quantitative data for scoring

**Data Sources (priority order):**
1. Yahoo Finance (`octopus/data_providers/yahoo_finance.py`)
2. Alpha Vantage (`octopus/data_providers/alpha_vantage.py`)
3. Financial Modeling Prep (`octopus/data_providers/financialmodelingprep.py`)
4. Database (historical market data)

**Technical indicators (stored in `technical_indicators`):**
- Moving averages: SMA 20, SMA 50, SMA 200, EMA 12, EMA 26
- Momentum: RSI (14), MACD (line, signal, histogram)
- Volatility: Bollinger Bands (upper, middle, lower), ATR
- Volume: VWAP

**Fundamental indicators:**
- PE ratio, forward PE
- Dividend yield
- Earnings surprise (reported vs estimated EPS)
- Revenue growth YoY

**Composite scores (stored in `instruments`):**
- `overall_score` — blended technical + fundamental score (0–100)
- `risk_score` — volatility-based risk rating (0–100, lower = safer)

**Background job:** `update_market_data` runs every 60 seconds and refreshes prices for all instruments in active accounts and watchlists.

**Key Methods:**
- `get_latest_market_data(symbol_id)` - Gets OHLCV data for a symbol
- `get_technical_indicators(symbol_id)` - Retrieves technical indicators (RSI, MACD, etc.)
- `get_fundamental_data(symbol)` - Gets fundamental analysis data
- `collect_quantitative_data(symbol_id)` - Fetches and saves quantitative metrics

### StrategySignal

**Location:** `backend/app/jobs/trading_bot/strategy_signal.py`

**Purpose:** Generates trading signals (BUY/SELL/HOLD) based on strategy rules and market conditions.

**Key Features:**
- Combines technical and fundamental analysis
- Configurable strategy parameters
- Composite signal scoring system
- Support for both quantitative and qualitative factors
- Optional AI-assisted signal enhancement

**Signal object:**
```
signal_type:  BUY | HOLD | SELL
strength:     float  (0.0 – 1.0)
confidence:   float  (0.0 – 1.0)
reasoning:    str    (human-readable explanation)
strategy_id:  int
symbol_id:    int
```

**Strategy categories and their signal logic:**

| Category | Example Strategies | Core Signal Logic |
|---|---|---|
| Long Term | Buy & Hold, DCA, Value Investing | Fundamental score + fair value discount |
| Swing | Trend Following, Breakout, Momentum | SMA crossovers, RSI, price breaks |
| Day Trading | VWAP, Opening Range, Scalping | Intraday price action vs VWAP/range |
| Mean Reversion | Bollinger, RSI Reversion | Price extended from bands → expect snap back |
| Famous Investors | Buffett, Lynch, Dalio | Strategy-specific filters (moat, PEG ratio, balance) |

**Signal Generation Process:**
1. Load strategy parameters from `strategies.parameters` (JSON)
2. Fetch latest indicators for the symbol
3. Apply strategy rules combining technical and fundamental factors:
   - RSI (oversold/overbought thresholds)
   - Price trend (bullish/bearish), support/resistance levels, volume
   - Quality score thresholds, valuation metrics (P/E, P/B), growth metrics, margin of safety
4. (Optional) Pass context to AI layer for enhanced reasoning
5. Save signal to `trading_signals` table
6. Return signal to portfolio construction layer

**Composite Scoring:**
- Each factor contributes to overall signal score
- BUY: score ≥ 3
- SELL: score ≤ -3
- HOLD: score between -3 and 3

**AI-assisted signal enhancement (optional):**
- Uses Claude / OpenAI via `octopus/ai_platforms/`
- Adds qualitative reasoning from news sentiment and market context
- Controlled by `use_ai_signals` strategy parameter

**Key Methods:**
- `parse_strategy_parameters(strategy)` - Parses and validates strategy parameters
- `generate_trading_signal(...)` - Main signal generation method
- `has_fundamental_parameters(strategy_params)` - Checks if strategy uses fundamental analysis
- `extract_indicators_used(signal, indicators)` - Extracts metadata for logging

**Default Parameters:**
- `max_position_size_percent`: 10.0%
- `max_portfolio_risk_percent`: 25.0%
- `stop_loss_percent`: 5.0%
- `take_profit_percent`: 15.0%
- `rsi_oversold`: 30.0
- `rsi_overbought`: 70.0
- `min_volume`: 1,000,000
- `max_positions`: 10

### PortfolioManager

**Location:** `backend/app/jobs/trading_bot/portfolio_manager.py`

**Purpose:** Manages portfolio positions, account-strategy relationships, and diversification.

**Key Features:**
- Retrieves active accounts with strategies
- Manages current positions
- Creates instruments as needed
- Links accounts to their strategies
- Enforces diversification rules and rebalancing

**Position Sizing Rules:**
- Max position size: configurable per strategy (default 5% of portfolio value)
- Scale size by signal strength: `size = max_position * signal.strength * signal.confidence`
- Minimum order value: $100 (ignore smaller allocations)
- Round to whole shares

**Diversification Modes (set in strategy parameters):**
- `diversified` — spread across sectors, max N stocks per sector
- `sector_focused` — concentrate in one or two sectors
- `concentrated` — few high-conviction positions (like Buffett style)
- `equal_weight` — equal dollar allocation across all positions

**Rebalancing:**
- On each bot run, check if existing positions deviate > threshold from target weight
- Generate SELL signals for over-weight positions
- Generate BUY signals for under-weight positions (if cash available)

**Key Methods:**
- `get_active_accounts_with_strategies()` - Finds accounts ready for trading
- `get_account_positions(account_id)` - Gets current positions for an account
- `get_or_create_instrument(symbol)` - Ensures instrument exists in database
- `get_account_strategy(account)` - Retrieves strategy for an account

**Position Management:**
- Positions are indexed by symbol for quick lookup
- Only positions with quantity > 0 are considered active
- Automatically creates missing instruments

### RiskManager

**Location:** `backend/app/jobs/trading_bot/risk_manager.py`

**Purpose:** Implements risk management rules and position sizing.

**Risk Rules (all configurable in strategy parameters):**

| Rule | Default | Description |
|---|---|---|
| Max position size | 5% | No single stock > 5% of total portfolio |
| Max sector exposure | 20% | No sector > 20% of total portfolio |
| Max drawdown | 15% | Pause bot if account drawdown exceeds 15% |
| Stop loss per trade | 8% | Auto-SELL if position drops 8% below entry |
| Take profit | 20% | Auto-SELL if position gains 20% (optional) |
| Cash reserve | 10% | Always keep ≥ 10% cash, never fully invested |
| Max open positions | 20 | Don't hold more than 20 positions simultaneously |

**Risk checks run before every order:**
1. Would this order breach position size limit? → Reduce size or reject
2. Would this order breach sector limit? → Reject
3. Is account drawdown above max? → Halt all BUY orders
4. Does existing position have an active stop loss triggered? → Emit SELL signal

**Drawdown Calculation:**
```
peak_equity = max(account_summary.total_equity over trailing period)
current_drawdown = (peak_equity - current_equity) / peak_equity
```

**Position Sizing Logic:**
1. Calculate maximum position value: `account.cash_balance × max_position_size_percent`
2. Calculate maximum shares: `max_position_value ÷ price`
3. Calculate available shares: `account.cash_balance ÷ price`
4. Use minimum of max_shares and available_shares
5. Round down to whole shares

**Key Methods:**
- `calculate_position_size(account, price, strategy_params)` - Calculates safe position size
- `check_max_positions_limit(current_positions, max_positions)` - Enforces position limits
- `check_existing_position(symbol, current_positions)` - Prevents duplicate positions
- `check_position_to_sell(symbol, current_positions)` - Validates sell eligibility
- `get_sell_quantity(symbol, current_positions)` - Gets quantity to sell

### ExecutionManager

**Location:** `backend/app/jobs/trading_bot/execution_manager.py`

**Purpose:** Executes trades and logs trading signals.

**Key Features:**
- Creates BUY and SELL orders
- Logs all trading signals (including HOLD)
- Extracts and stores indicator metadata
- Handles order creation in database
- Order deduplication to prevent duplicate signals

**Order Types Used by Bot:**
- `MARKET` — immediate execution at current price (default for bot)
- `LIMIT` — set at a specific price (used for take-profit and stop-loss orders)
- `STOP` — triggered when price falls to stop level

**Execution Flow:**
1. Risk Manager approves the signal
2. Execution Engine creates an `Order` record (status: `PENDING`)
3. Background job `process_orders` (runs every 5 seconds) picks up `PENDING` orders
4. Order is filled at current market price
5. Position is created or updated in `positions` table
6. Completed trade recorded in `trades` table
7. Account cash balance updated
8. Log entry created

**Order Deduplication:**
- Before creating a BUY order, check if a `PENDING` order for the same symbol/account already exists
- Do not create duplicate orders for the same signal cycle

**SELL Order Triggers:**
- Bot generates SELL signal (strategy says exit)
- Stop loss triggered (price fell below threshold)
- Take profit triggered (price reached target)
- Risk Manager halts due to drawdown

**Key Methods:**
- `execute_trade(...)` - Generic trade execution method
- `execute_buy_order(...)` - Creates BUY order with metadata
- `execute_sell_order(...)` - Creates SELL order with metadata
- `log_trading_signal(...)` - Logs signal to trading_signals table
- `log_hold_signal(...)` - Logs HOLD signals for tracking

**Signal Logging:**
- All signals (BUY, SELL, HOLD) are logged
- Includes signal strength, confidence, and reasons
- Stores which indicators contributed to the decision
- Enables performance analysis and strategy refinement

## Bot Run Lifecycle

```
1.  Scheduler triggers bot run for each active account with a strategy
2.  Load account state (balance, positions, strategy config)
3.  Resolve stock universe from strategy stock_list + sector filters
4.  Fetch / refresh market data for all candidate symbols
5.  Calculate / refresh indicators for all candidates
6.  Score and rank candidates
7.  Run strategy engine → generate signals for each candidate
8.  Check existing positions → generate HOLD/SELL signals where needed
9.  Pass all signals through risk manager
10. Send approved orders to execution engine
11. Log summary of run
```

**Run frequency:** Configurable per account/strategy (default: every 5 minutes during market hours)

**Market hours guard:** The bot only places new BUY orders during market hours (09:30–16:00 ET, weekdays). Stop-loss and take-profit SELL orders can execute at any time.

### Signal Generation Flowchart

```
Start
  ↓
Get Account & Strategy
  ↓
Parse Strategy Parameters
  ↓
Get Stock List
  ↓
For each Stock:
  ↓
Get Market Data & Indicators
  ↓
Generate Signal Score
  ↓
  ├── Score ≥ 3 → BUY Signal
  ├── Score ≤ -3 → SELL Signal
  └── -3 < Score < 3 → HOLD Signal
  ↓
Apply Risk Management
  ↓
Execute/Lock Trade
  ↓
Next Stock
```

## Database Models

The trading bot interacts with several key database tables:

| Table | Role |
|---|---|
| `accounts` | Source of truth for cash balance and active status |
| `strategies` | Bot configuration and parameters |
| `instruments` | Stock metadata, scores |
| `market_data` | OHLCV price history for indicator calculation |
| `technical_indicators` | Pre-calculated indicators |
| `trading_signals` | Signals generated each run |
| `orders` | Pending and filled orders |
| `positions` | Current holdings |
| `trades` | Historical completed trades |
| `account_summary` | Equity snapshots for drawdown calculation |
| `system_logs` | Bot events, errors, and decisions |
| `news_sentiment` | Sentiment input for AI-enhanced signals |

### Account (`accounts`)
- `account_id`: Primary key
- `cash_balance`: Available cash for trading
- `strategy_id`: Associated trading strategy
- `is_active`: Whether account is active for trading
- `status`: Account status ('active', 'inactive', 'suspended')

### Instrument (`instruments`)
- `symbol`: Stock symbol (e.g., 'AAPL')
- `overall_score`: Quantitative score 0-100
- `risk_score`: Risk score 0-100 (lower = safer)
- `sector`: Sector classification
- `watch_list`: Watchlist flag

### Strategy (`strategies`)
- `name`: Strategy name
- `parameters`: JSON configuration for strategy
- `stock_list`: List of stocks for the strategy
- `stock_list_mode`: 'Manual' or 'AI'
- `is_active`: Whether strategy is active

### MarketData (`market_data`)
- OHLCV data with timestamps
- Supports multiple intervals (1min, 5min, 1hour, 1day)
- Includes VWAP (Volume Weighted Average Price)

### TradingSignal (`trading_signals`)
- `signal_type`: 'BUY', 'SELL', or 'HOLD'
- `strength`: Signal strength (0.0 to 1.0)
- `confidence`: Confidence level (0.0 to 1.0)
- `indicators_used`: JSON of contributing indicators
- `reason`: Human-readable explanation

### Order (`orders`)
- `order_type`: 'MARKET', 'LIMIT', 'STOP'
- `side`: 'BUY' or 'SELL'
- `status`: 'PENDING', 'FILLED', 'CANCELLED', 'REJECTED'
- `quantity`: Number of shares
- `price`: Order price

### Position (`positions`)
- `quantity`: Current position size
- `average_entry_price`: Average cost basis
- `current_price`: Latest market price
- `unrealized_pnl`: Unrealized profit/loss

### QuantitativeData (`quantitative_data`)
- `meta`: Parameter name (e.g., 'sma_short', 'min_dividend_yield')
- `value`: Calculated value as text
- Stores quantitative metrics for analysis

## Configuration and Parameters

### Strategy Parameters Structure

Strategies are configured via JSON parameters in the `strategies` table:

```json
{
  "stock_list": ["AAPL", "MSFT", "GOOGL"],
  "max_position_size_percent": 10.0,
  "max_portfolio_risk_percent": 25.0,
  "max_sector_pct": 0.20,
  "max_drawdown_pct": 0.15,
  "stop_loss_percent": 5.0,
  "take_profit_percent": 15.0,
  "cash_reserve_pct": 0.10,
  "rsi_oversold": 30.0,
  "rsi_overbought": 70.0,
  "min_volume": 1000000,
  "max_positions": 10,
  "stock_universe": "strategy_list",
  "sector_include": ["Technology", "Healthcare"],
  "sector_exclude": ["Energy"],
  "diversification_mode": "diversified",
  "rebalance": true,
  "use_ai_signals": false,
  "run_frequency_minutes": 5,
  "signal_min_confidence": 0.6,
  "min_quality_score": 70,
  "max_pe_ratio": 25.0,
  "required_margin_of_safety_percent": 20.0
}
```

### Stock Universe Configuration

The `stock_universe` parameter determines how stocks are selected:

1. **strategy_list**: Uses predefined list from `stock_list` field
2. **sector_filters**: Filters by sector inclusion/exclusion
3. **watchlist**: Uses instruments marked in watchlist
4. **screener**: Applies multiple filters (score, risk, sector)
5. **winners**: Top day gainers from Yahoo Finance
6. **losers**: Top day losers from Yahoo Finance

### UI Controls

Users configure the bot via the Strategy form in the UI. The account detail page should include:

- Enable/disable bot per account (toggle on Account detail)
- Show last bot run timestamp and status
- Show signal log (what signals were generated on last run)
- Show risk events (stop losses triggered, drawdown warnings)

## Error Handling and Logging

### Error Hierarchy

1. **Account-level Errors**: Errors processing a specific account don't stop other accounts
2. **Stock-level Errors**: Errors with a specific stock don't stop other stocks
3. **System-level Errors**: Critical errors stop the entire bot

### Logging System

The bot uses Python's logging module with multiple log levels:

- **INFO**: Normal operation messages
- **WARNING**: Non-critical issues
- **ERROR**: Errors that need attention
- **DEBUG**: Detailed debugging information

### What Gets Logged

- Bot run started / completed (with timestamp and account_id)
- Stocks evaluated (symbol, score, signal generated)
- Signals generated (type, strength, confidence, reasoning)
- Risk checks (passed / failed and why)
- Orders created (symbol, side, quantity, price)
- Orders filled (execution price, slippage)
- Stop loss / take profit triggers
- Errors and exceptions

**Log destination:** `system_logs` table (via `LogService`)

### Example Error Handling

```python
try:
    self._process_account(account)
except Exception as e:
    logger.error(f"Error processing account {account.account_id}: {str(e)}")
    self.repo_factory.system_logs.log_error(
        module="trading_bot",
        message=f"Error processing account {account.account_id}",
        details=str(e)
    )
```

## Running the Bot

### Direct Execution

```bash
cd /home/peter/work/paper-profit/paper-profit/backend
python -m app.jobs.trading_bot
```

### As a Scheduled Job

The bot is designed to run periodically (default: every 5 minutes during market hours) via:
- Cron jobs
- Systemd timers
- Task schedulers

### Integration with Background Jobs

The bot can be integrated with the platform's background job system:
- Scheduled execution via Celery or similar
- Event-driven triggering
- Manual execution via admin interface

### Monitoring and Maintenance

1. **Performance Monitoring**: Track signal accuracy and profitability
2. **Error Monitoring**: Review system logs regularly
3. **Database Maintenance**: Clean up old data, optimize queries
4. **Strategy Refinement**: Update parameters based on performance

### Testing the Bot

```bash
# Unit tests for individual modules
python -m pytest backend/app/tests/trading_bot/

# Integration tests
python -m pytest backend/app/tests/test_trading_bot_updates.py
```

## Conclusion

The Trading Bot is a sophisticated, modular system that implements automated trading with comprehensive risk management. Its architecture separates concerns into distinct modules, making it maintainable, testable, and extensible.

### Key Strengths

1. **Modular Design**: Each component has a clear responsibility and can be developed/tested independently
2. **Risk Management**: Built-in risk controls prevent overexposure and manage portfolio risk
3. **Flexible Configuration**: Strategies can be customized through JSON parameters
4. **Comprehensive Logging**: All decisions are logged for analysis and debugging
5. **Error Resilience**: Errors at one level don't cascade to stop the entire system

### Extension Points

The system can be extended in several ways:

1. **New Strategy Types**: Add new signal generation algorithms
2. **Additional Data Sources**: Integrate more market data providers
3. **Advanced Risk Models**: Implement more sophisticated risk calculations
4. **Machine Learning**: Incorporate ML models for signal generation
5. **Multi-Asset Support**: Extend beyond stocks to options, futures, etc.

### Best Practices for Usage

1. **Start Small**: Begin with conservative parameters and small position sizes
2. **Monitor Regularly**: Review logs and performance metrics frequently
3. **Backtest Strategies**: Test strategies on historical data before live deployment
4. **Use Paper Trading**: Test with virtual accounts before real money
5. **Implement Circuit Breakers**: Add additional safety controls for production use

### Future Development Directions

1. **Real-time Processing**: Move to streaming data for faster signal generation
2. **Portfolio Optimization**: Implement modern portfolio theory for position sizing
3. **Sentiment Analysis**: Incorporate news and social media sentiment
4. **Multi-timeframe Analysis**: Combine signals from different timeframes
5. **Automated Strategy Optimization**: Use genetic algorithms to optimize parameters

## Appendix: Code Examples

### Basic Usage

```python
from storage.database import get_session
from app.jobs.trading_bot import TradingBot

# Get database session
db = get_session()

# Create and run trading bot
bot = TradingBot(db)
bot.run()

# Close session
db.close()
```

### Custom Strategy Configuration

```python
# Example strategy configuration
strategy_config = {
    "name": "Conservative Growth",
    "parameters": {
        "max_position_size_percent": 5.0,
        "max_portfolio_risk_percent": 15.0,
        "stop_loss_percent": 3.0,
        "take_profit_percent": 10.0,
        "rsi_oversold": 25.0,
        "rsi_overbought": 75.0,
        "min_volume": 2000000,
        "max_positions": 5,
        "stock_universe": "screener",
        "min_quality_score": 80,
        "required_margin_of_safety_percent": 30.0
    },
    "stock_list": "AAPL,MSFT,GOOGL,AMZN,TSLA",
    "stock_list_mode": "Manual"
}
```

### Monitoring Script

```python
# Simple monitoring script
import logging
from storage.database import get_session
from storage.repositories import RepositoryFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def monitor_trading_bot():
    """Monitor trading bot performance"""
    db = get_session()
    repo_factory = RepositoryFactory(db)

    try:
        # Get recent signals
        recent_signals = repo_factory.trading_signals.get_recent(limit=50)

        # Get recent errors
        recent_errors = repo_factory.system_logs.get_by_level('ERROR', limit=20)

        # Log summary
        logger.info(f"Recent signals: {len(recent_signals)}")
        logger.info(f"Recent errors: {len(recent_errors)}")

        # Check for critical issues
        if len(recent_errors) > 10:
            logger.warning("High error rate detected!")

    finally:
        db.close()

if __name__ == "__main__":
    monitor_trading_bot()
```

## Files

| File | Purpose |
|---|---|
| `jobs/trading_bot.py` | Main bot orchestrator (run per account) |
| `jobs/trading_bot/instrument_discovery.py` | Stock universe resolution |
| `jobs/trading_bot/data_collector.py` | Market data and indicator fetching |
| `jobs/trading_bot/strategy_signal.py` | Signal generation |
| `jobs/trading_bot/portfolio_manager.py` | Position and account management |
| `jobs/trading_bot/risk_manager.py` | Risk checks and position sizing |
| `jobs/trading_bot/execution_manager.py` | Order creation and trade logging |
| `background.py` | Scheduler — triggers bot runs |
| `analysis/technical_functions.py` | Indicator calculations |
| `analysis/fundamental_functions.py` | Fundamental metric calculations |
| `octopus/data_providers/yahoo_finance.py` | Yahoo Finance data provider |
| `octopus/data_providers/alpha_vantage.py` | Alpha Vantage data provider |
| `octopus/data_providers/financialmodelingprep.py` | FMP data provider |
| `octopus/ai_platforms/` | Optional AI signal enhancement |
| `config/strategy-parameters.yaml` | Default strategy parameters |
| `config/stock-bucketing.yaml` | Sector/category taxonomy |

## References

- [Paper Profit Architecture Documentation](../architecture-layers/jobs.md)
- [Strategy Parameters Guide](../../frontend/src/utils/strategyParameters.js)
- [Database Models](../storage/models.py)
- [Trading Bot Tests](../../backend/app/tests/trading_bot/)

---

*Documentation last updated: March 2026*
