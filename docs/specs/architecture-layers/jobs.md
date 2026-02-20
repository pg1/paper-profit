# Background Jobs

## Overview

The **Jobs** module handles scheduled and asynchronous background tasks that keep the PaperProfit trading platform running smoothly. These jobs ensure that market data stays current, positions are accurately valued, orders are processed promptly, and trading strategies execute automatically.

## Architecture

Background jobs are organized into four main categories based on their function and execution timing:

### 1. **Trading Bot Jobs**
Automated strategy execution and signal generation
- **Frequency**: Configurable (e.g., every minute, hour, or custom schedule)
- **Purpose**: Execute trading strategies and generate buy/sell signals
- **Dependencies**: Market data, strategy definitions, account positions

### 2. **Order Processing Jobs**
Handle pending orders and execute trades
- **Frequency**: High-frequency (every few seconds during market hours)
- **Purpose**: Process pending orders, check limit/stop conditions, execute fills
- **Dependencies**: Current market prices, order queue, account balances

### 3. **Market Data Update Jobs**
Fetch latest prices and market information
- **Frequency**: Real-time or near-real-time during market hours
- **Purpose**: Keep instrument prices current for valuations and order execution
- **Dependencies**: External data providers (Yahoo Finance, Alpha Vantage, etc.)

### 4. **Position Valuation Jobs**
Update position values and P&L calculations
- **Frequency**: Regular intervals (e.g., every 5-15 minutes)
- **Purpose**: Recalculate position values, unrealized P&L, and account summaries
- **Dependencies**: Current market prices, position holdings

## Job Scheduling

### Market Hours vs After-Hours
- **Active Trading Hours**: High-frequency updates for market data and order processing
- **After-Hours**: Reduced frequency, focus on end-of-day summaries
- **Weekends**: Minimal activity, primarily maintenance and data cleanup

### Priority Levels
1. **Critical**: Order processing (must execute immediately)
2. **High**: Market data updates (sub-minute latency)
3. **Medium**: Position valuations (5-15 minute intervals)
4. **Low**: Strategy signal generation (hourly or daily)

## Key Job Details

### Trading Bot
- Evaluates trading strategy conditions
- Generates TradingSignal records
- Checks entry/exit criteria
- Respects position size limits
- Logs all decisions for audit trail

### Process Orders
- Monitors pending orders
- Checks market prices against limit/stop prices
- Executes fills when conditions met
- Updates position quantities and average prices
- Creates Trade records for completed orders
- Handles partial fills and order cancellations

### Update Market Data
- Fetches current prices from data providers
- Updates Instrument.last_price field
- Stores historical OHLCV in MarketData table
- Handles API rate limits and errors
- Caches data to reduce redundant calls

### Update Positions
- Recalculates current_price * quantity for each position
- Updates unrealized_pnl based on entry price
- Aggregates portfolio value per account
- Generates AccountSummary snapshots
- Triggers alerts for significant P&L changes

## Error Handling

### Retry Logic
- **Transient Errors**: Automatic retry with exponential backoff
- **API Limits**: Respect rate limits, queue requests
- **Network Issues**: Retry with circuit breaker pattern

### Fallback Mechanisms
- Use cached data when external APIs unavailable
- Defer non-critical jobs during outages
- Alert administrators for persistent failures

### Logging and Monitoring
- All jobs log start/end times
- Error logs captured in SystemLog table
- Performance metrics tracked (execution time, success rate)
- Alerts for jobs that fail repeatedly or take too long

## Implementation Technologies

### Task Queue Options
- **Celery** - Distributed task queue with Python
- **APScheduler** - Lightweight in-process scheduler
- **Cron Jobs** - Simple time-based scheduling
- **FastAPI Background Tasks** - Simple async tasks

### Message Broker (if using Celery)
- **Redis** - Fast in-memory broker
- **RabbitMQ** - Robust message queue

### Database Integration
- Jobs read/write using the Storage module repositories
- Proper transaction management for consistency
- Connection pooling for efficiency

## Configuration

### Job Timing
```python
JOBS_CONFIG = {
    'trading_bot': {
        'enabled': True,
        'interval': '1h',  # Every hour
        'market_hours_only': True
    },
    'process_orders': {
        'enabled': True,
        'interval': '5s',  # Every 5 seconds
        'market_hours_only': True
    },
    'update_market_data': {
        'enabled': True,
        'interval': '1m',  # Every minute
        'market_hours_only': False  # Can run after-hours
    },
    'update_positions': {
        'enabled': True,
        'interval': '10m',  # Every 10 minutes
        'market_hours_only': False
    }
}
```

### Market Hours Definition
- Regular hours: 9:30 AM - 4:00 PM ET
- Pre-market: 4:00 AM - 9:30 AM ET (optional)
- After-hours: 4:00 PM - 8:00 PM ET (optional)
- Timezone handling for global markets

## API Integration

Jobs can be monitored and controlled through API endpoints:

```python
# Trigger job manually
@app.post("/api/jobs/{job_name}/trigger")
async def trigger_job(job_name: str):
    # Manually execute a specific job

# Get job status
@app.get("/api/jobs/status")
async def get_job_status():
    # Return status of all background jobs

# Enable/disable jobs
@app.put("/api/jobs/{job_name}/toggle")
async def toggle_job(job_name: str, enabled: bool):
    # Enable or disable a specific job
```

## Future Enhancements

### Advanced Features
- **Job Chaining**: Execute jobs in sequence with dependencies
- **Conditional Execution**: Skip jobs based on market conditions
- **Parallel Processing**: Distribute work across multiple workers
- **Job History**: Track execution history and performance trends

### Additional Jobs
- **Portfolio Rebalancing**: Automatically rebalance to target allocations
- **Risk Monitoring**: Alert on excessive drawdowns or concentration
- **News Sentiment**: Fetch and analyze news for holdings
- **Technical Indicators**: Calculate and store technical analysis metrics
- **Reporting**: Generate daily/weekly/monthly performance reports

## Purpose

The Jobs module is the automation engine of PaperProfit, ensuring that the platform operates continuously and autonomously. By handling routine tasks in the background, it frees users to focus on strategy and decision-making while the system maintains accurate data, processes orders reliably, and executes strategies consistently.
