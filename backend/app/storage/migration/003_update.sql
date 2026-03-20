CREATE TABLE IF NOT EXISTS quantitative_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,           -- Time of the data point
    meta TEXT, 
    value REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol_id) REFERENCES instruments(id),
    UNIQUE(symbol_id, timestamp, meta)
);