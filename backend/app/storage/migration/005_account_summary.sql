CREATE TABLE IF NOT EXISTS account_summary (
    id INTEGER NOT NULL, 
    account_id VARCHAR NOT NULL, 
    timestamp DATETIME NOT NULL, 
    total_equity DECIMAL(15, 2) NOT NULL, 
    cash_balance DECIMAL(15, 2) NOT NULL, 
    portfolio_value DECIMAL(15, 2) NOT NULL, 
    buying_power DECIMAL(15, 2), 
    daily_pnl DECIMAL(15, 2), 
    unrealized_pnl DECIMAL(15, 2), 
    realized_pnl DECIMAL(15, 2), 
    max_drawdown DECIMAL(10, 4), 
    sharpe_ratio DECIMAL(10, 4), 
    created_at DATETIME, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_account_summary_account_timestamp UNIQUE (account_id, timestamp), 
    FOREIGN KEY(account_id) REFERENCES accounts (account_id)
)