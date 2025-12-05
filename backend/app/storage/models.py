from sqlalchemy import Column, Integer, String, DateTime, Boolean, DECIMAL, BigInteger, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class Account(Base):
    """Accounts table"""
    __tablename__ = "accounts"

    account_id = Column(String, primary_key=True)
    account_name = Column(String, nullable=False)  # Display name for the account
    account_type = Column(String, nullable=False, default='virtual')  # 'virtual', 'alpaca', etc.
    cash_balance = Column(DECIMAL(15, 2), nullable=False)
    currency = Column(String, default='USD')  # Account currency
    status = Column(String, default='active')  # 'active', 'inactive', 'suspended'
    description = Column(Text)  # Optional account description
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)  # Associated strategy
    is_active = Column(Boolean, default=True)  # Soft delete flag
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    account_summaries = relationship("AccountSummary", back_populates="account")
    orders = relationship("Order", back_populates="account")
    positions = relationship("Position", back_populates="account")
    trades = relationship("Trade", back_populates="account")
    strategy = relationship("Strategy", back_populates="accounts")

class Instrument(Base):
    """Instruments table"""
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False, unique=True)  # e.g., 'AAPL', 'TSLA'
    name = Column(String)  # Full company name
    exchange = Column(String)  # e.g., 'NASDAQ', 'NYSE'
    currency = Column(String, default='USD')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    market_data = relationship("MarketData", back_populates="instrument")
    technical_indicators = relationship("TechnicalIndicator", back_populates="instrument")
    trading_signals = relationship("TradingSignal", back_populates="instrument")
    orders = relationship("Order", back_populates="instrument")
    positions = relationship("Position", back_populates="instrument")
    trades = relationship("Trade", back_populates="instrument")
    news_sentiment = relationship("NewsSentiment", back_populates="instrument")


class MarketData(Base):
    """Market data (OHLCV + timestamp)"""
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)  # Time of the data point
    interval = Column(String, nullable=False)  # '1min', '5min', '1hour', '1day'
    open = Column(DECIMAL(15, 6), nullable=False)
    high = Column(DECIMAL(15, 6), nullable=False)
    low = Column(DECIMAL(15, 6), nullable=False)
    close = Column(DECIMAL(15, 6), nullable=False)
    volume = Column(BigInteger, nullable=False)
    vwap = Column(DECIMAL(15, 6))  # Volume Weighted Average Price
    trade_count = Column(Integer)  # Number of trades in the interval
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    instrument = relationship("Instrument", back_populates="market_data")
    technical_indicators = relationship("TechnicalIndicator", back_populates="market_data")

    # Unique constraint
    __table_args__ = (UniqueConstraint('symbol_id', 'timestamp', 'interval', name='uq_market_data_symbol_timestamp_interval'),)


class TechnicalIndicator(Base):
    """Technical indicators (calculated from market data)"""
    __tablename__ = "technical_indicators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_data_id = Column(Integer, ForeignKey("market_data.id"), nullable=False)
    symbol_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    interval = Column(String, nullable=False)

    # Moving Averages
    sma_20 = Column(DECIMAL(15, 6))
    sma_50 = Column(DECIMAL(15, 6))
    sma_200 = Column(DECIMAL(15, 6))
    ema_12 = Column(DECIMAL(15, 6))
    ema_26 = Column(DECIMAL(15, 6))

    # Bollinger Bands
    bb_upper = Column(DECIMAL(15, 6))
    bb_middle = Column(DECIMAL(15, 6))
    bb_lower = Column(DECIMAL(15, 6))
    bb_width = Column(DECIMAL(15, 6))

    # RSI
    rsi_14 = Column(DECIMAL(10, 6))

    # MACD
    macd = Column(DECIMAL(15, 6))
    macd_signal = Column(DECIMAL(15, 6))
    macd_histogram = Column(DECIMAL(15, 6))

    # Volume indicators
    volume_sma = Column(DECIMAL(15, 2))
    obv = Column(DECIMAL(15, 2))  # On Balance Volume

    # Support/Resistance
    support_level = Column(DECIMAL(15, 6))
    resistance_level = Column(DECIMAL(15, 6))

    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    instrument = relationship("Instrument", back_populates="technical_indicators")
    market_data = relationship("MarketData", back_populates="technical_indicators")

    # Unique constraint
    __table_args__ = (UniqueConstraint('symbol_id', 'timestamp', 'interval', name='uq_technical_indicators_symbol_timestamp_interval'),)


class Strategy(Base):
    """Trading strategies"""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)  # e.g., 'mean_reversion', 'breakout'
    description = Column(Text)
    parameters = Column(JSON)  # Strategy-specific parameters
    category = Column(String)  # 'Long', 'Short'
    strategy_type = Column(String)  # 'Buy Hold', 'Growth', 'Swing Trade', 'Day Trade', etc.
    stock_list_mode = Column(String)  # 'Manual', 'AI'
    stock_list = Column(Text)  # List of stocks for the strategy
    stock_list_ai_prompt = Column(Text)  # Ai prompt to get a stock list
    parameters_json = Column(Text)  # Parameters in JSON format
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    trading_signals = relationship("TradingSignal", back_populates="strategy")
    orders = relationship("Order", back_populates="strategy")
    trades = relationship("Trade", back_populates="strategy")
    accounts = relationship("Account", back_populates="strategy")


class TradingSignal(Base):
    """Trading signals generated by strategies"""
    __tablename__ = "trading_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    signal_type = Column(String, nullable=False)  # 'BUY', 'SELL', 'HOLD'
    strength = Column(DECIMAL(10, 6))  # Signal strength (0-1 or -1 to 1)
    price = Column(DECIMAL(15, 6))  # Price when signal was generated
    confidence = Column(DECIMAL(5, 4))  # Confidence level 0-1

    # Signal metadata
    indicators_used = Column(JSON)  # Which indicators contributed
    reason = Column(Text)  # Human-readable reason for signal

    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    instrument = relationship("Instrument", back_populates="trading_signals")
    strategy = relationship("Strategy", back_populates="trading_signals")


class Order(Base):
    """Orders table"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    symbol_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)

    # Order details
    order_id = Column(String, unique=True)  # Broker's order ID
    order_type = Column(String, nullable=False)  # 'MARKET', 'LIMIT', 'STOP'
    side = Column(String, nullable=False)  # 'BUY', 'SELL'
    quantity = Column(DECIMAL(15, 6), nullable=False)
    price = Column(DECIMAL(15, 6))  # Limit price for limit orders
    stop_price = Column(DECIMAL(15, 6))  # Stop price for stop orders

    # Order status
    status = Column(String, nullable=False)  # 'PENDING', 'FILLED', 'CANCELLED', 'REJECTED'
    filled_quantity = Column(DECIMAL(15, 6), default=0)
    average_fill_price = Column(DECIMAL(15, 6))
    commission = Column(DECIMAL(10, 2), default=0)

    # Timestamps
    submitted_at = Column(DateTime)
    filled_at = Column(DateTime)
    cancelled_at = Column(DateTime)

    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    account = relationship("Account", back_populates="orders")
    instrument = relationship("Instrument", back_populates="orders")
    strategy = relationship("Strategy", back_populates="orders")


class Position(Base):
    """Portfolio positions"""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    symbol_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    quantity = Column(DECIMAL(15, 6), nullable=False, default=0)
    average_entry_price = Column(DECIMAL(15, 6), nullable=False)
    current_price = Column(DECIMAL(15, 6))
    unrealized_pnl = Column(DECIMAL(15, 6), default=0)
    realized_pnl = Column(DECIMAL(15, 6), default=0)

    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    account = relationship("Account", back_populates="positions")
    instrument = relationship("Instrument", back_populates="positions")

    # Unique constraint
    __table_args__ = (UniqueConstraint('account_id', 'symbol_id', name='uq_positions_account_symbol'),)


class Trade(Base):
    """Trade history (completed trades)"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    symbol_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)

    # Trade details
    side = Column(String, nullable=False)  # 'BUY', 'SELL'
    quantity = Column(DECIMAL(15, 6), nullable=False)
    entry_price = Column(DECIMAL(15, 6), nullable=False)
    exit_price = Column(DECIMAL(15, 6), nullable=False)

    # P&L calculations
    gross_pnl = Column(DECIMAL(15, 6), nullable=False)
    commission = Column(DECIMAL(10, 2), default=0)
    net_pnl = Column(DECIMAL(15, 6), nullable=False)
    pnl_percentage = Column(DECIMAL(10, 4))

    # Timestamps
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=False)
    holding_period_days = Column(Integer)

    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    account = relationship("Account", back_populates="trades")
    instrument = relationship("Instrument", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")


class AccountSummary(Base):
    """Account summary"""
    __tablename__ = "account_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    # Account values
    total_equity = Column(DECIMAL(15, 2), nullable=False)
    cash_balance = Column(DECIMAL(15, 2), nullable=False)
    portfolio_value = Column(DECIMAL(15, 2), nullable=False)
    buying_power = Column(DECIMAL(15, 2))

    # Performance metrics
    daily_pnl = Column(DECIMAL(15, 2), default=0)
    unrealized_pnl = Column(DECIMAL(15, 2), default=0)
    realized_pnl = Column(DECIMAL(15, 2), default=0)

    # Risk metrics
    max_drawdown = Column(DECIMAL(10, 4))
    sharpe_ratio = Column(DECIMAL(10, 4))

    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    account = relationship("Account", back_populates="account_summaries")

    # Unique constraint
    __table_args__ = (UniqueConstraint('account_id', 'timestamp', name='uq_account_summary_account_timestamp'),)


class NewsSentiment(Base):
    """News and sentiment data"""
    __tablename__ = "news_sentiment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    headline = Column(Text, nullable=False)
    source = Column(String)
    published_at = Column(DateTime, nullable=False)
    sentiment_score = Column(DECIMAL(5, 4))  # -1 (negative) to +1 (positive)
    sentiment_magnitude = Column(DECIMAL(5, 4))  # 0 to 1 (strength of sentiment)
    url = Column(Text)

    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    instrument = relationship("Instrument", back_populates="news_sentiment")


class SystemLog(Base):
    """System logs for debugging and monitoring"""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=func.current_timestamp())
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=True)
    level = Column(String, nullable=False)  # 'INFO', 'WARNING', 'ERROR', 'DEBUG'
    module = Column(String)  # Which part of the system
    message = Column(Text, nullable=False)
    details = Column(Text)  # JSON or detailed error info

    # Relationships
    account = relationship("Account", backref="system_logs")


class Setting(Base):
    """Application settings table"""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String, default='general')  # Category for grouping settings
    name = Column(String, nullable=False, unique=True)  # Setting key/name
    parameters = Column(Text)  # Setting value (stored as text, can be JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
