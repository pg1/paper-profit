from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from .models import (
    Instrument, MarketData, TechnicalIndicator, Strategy, TradingSignal,
    Order, Position, Trade, Account, AccountSummary, NewsSentiment, SystemLog, Setting
)


class InstrumentRepository:
    """Repository for instrument operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self, active_only: bool = True) -> List[Instrument]:
        """Get all instruments"""
        query = self.db.query(Instrument)
        if active_only:
            query = query.filter(Instrument.is_active == True)
        return query.all()
    
    def get_by_id(self, instrument_id: int) -> Optional[Instrument]:
        """Get instrument by ID"""
        return self.db.query(Instrument).filter(Instrument.id == instrument_id).first()
    
    def get_by_symbol(self, symbol: str) -> Optional[Instrument]:
        """Get instrument by symbol string"""
        return self.db.query(Instrument).filter(Instrument.symbol == symbol).first()
    
    def create(self, instrument_data: Dict[str, Any]) -> Instrument:
        """Create new instrument"""
        instrument = Instrument(**instrument_data)
        self.db.add(instrument)
        self.db.commit()
        self.db.refresh(instrument)
        return instrument
    
    def update(self, instrument_id: int, instrument_data: Dict[str, Any]) -> Optional[Instrument]:
        """Update instrument"""
        instrument = self.get_by_id(instrument_id)
        if instrument:
            for key, value in instrument_data.items():
                setattr(instrument, key, value)
            self.db.commit()
            self.db.refresh(instrument)
        return instrument
    
    def get_watchlist(self) -> List[Instrument]:
        """Get all instruments in the watchlist"""
        return self.db.query(Instrument).filter(Instrument.watch_list == 1).all()
    
    def add_to_watchlist(self, symbol: str) -> Optional[Instrument]:
        """Add instrument to watchlist by symbol. Creates instrument if it doesn't exist.
        Also computes and stores overall_score, risk_score and sector."""
        import logging as _logging
        _logger = _logging.getLogger(__name__)

        instrument = self.get_by_symbol(symbol)

        if not instrument:
            # Instrument doesn't exist — try to fetch basic info first
            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                info = ticker.info

                instrument_data = {
                    "symbol": symbol,
                    "name": info.get('longName') or info.get('shortName') or symbol,
                    "exchange": info.get('exchange') or 'Unknown',
                    "currency": info.get('currency') or 'USD',
                    "watch_list": 1,
                }
                instrument = self.create(instrument_data)
            except Exception:
                instrument_data = {
                    "symbol": symbol,
                    "name": symbol,
                    "exchange": "Unknown",
                    "currency": "USD",
                    "watch_list": 1,
                }
                instrument = self.create(instrument_data)
        else:
            # Instrument already exists — just flag it as watched
            instrument.watch_list = 1
            self.db.commit()
            self.db.refresh(instrument)

        # Compute and persist scores + sector classification
        try:
            from analysis.stock_scoring import score_and_classify_stock
            scores = score_and_classify_stock(symbol)
            instrument.overall_score = scores['overall_score']
            instrument.risk_score = scores['risk_score']
            instrument.sector = scores['sector_bucket']
            self.db.commit()
            self.db.refresh(instrument)
        except Exception as e:
            _logger.warning(f"Could not compute scores for {symbol}: {e}")
            # Set default values when scoring fails
            instrument.overall_score = None
            instrument.risk_score = None
            instrument.sector = 'Unknown'
            self.db.commit()
            self.db.refresh(instrument)

        return instrument
    
    def remove_from_watchlist(self, symbol: str) -> Optional[Instrument]:
        """Remove instrument from watchlist by symbol"""
        instrument = self.get_by_symbol(symbol)
        if instrument:
            instrument.watch_list = 0
            self.db.commit()
            self.db.refresh(instrument)
        return instrument
    
    def is_in_watchlist(self, symbol: str) -> bool:
        """Check if instrument is in watchlist"""
        instrument = self.get_by_symbol(symbol)
        return instrument is not None and instrument.watch_list == 1


class MarketDataRepository:
    """Repository for market data operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_latest(self, symbol_id: int, interval: str, limit: int = 100) -> List[MarketData]:
        """Get latest market data for a symbol"""
        return (self.db.query(MarketData)
                .filter(MarketData.symbol_id == symbol_id, MarketData.interval == interval)
                .order_by(desc(MarketData.timestamp))
                .limit(limit)
                .all())
    
    def get_latest_by_symbol(self, symbol: str, interval: str, limit: int = 100) -> List[MarketData]:
        """Get latest market data for a symbol string"""
        return (self.db.query(MarketData)
                .join(Instrument, MarketData.symbol_id == Instrument.id)
                .filter(Instrument.symbol == symbol, MarketData.interval == interval)
                .order_by(desc(MarketData.timestamp))
                .limit(limit)
                .all())
    
    def get_by_timestamp_range(self, symbol_id: int, interval: str, 
                              start_time: str, end_time: str) -> List[MarketData]:
        """Get market data for a time range"""
        return (self.db.query(MarketData)
                .filter(
                    MarketData.symbol_id == symbol_id,
                    MarketData.interval == interval,
                    MarketData.timestamp >= start_time,
                    MarketData.timestamp <= end_time
                )
                .order_by(asc(MarketData.timestamp))
                .all())
    
    def create(self, market_data: Dict[str, Any]) -> MarketData:
        """Create new market data entry"""
        data = MarketData(**market_data)
        self.db.add(data)
        self.db.commit()
        self.db.refresh(data)
        return data
    
    def create_bulk(self, market_data_list: List[Dict[str, Any]]) -> List[MarketData]:
        """Create multiple market data entries"""
        data_objects = [MarketData(**data) for data in market_data_list]
        self.db.bulk_save_objects(data_objects)
        self.db.commit()
        return data_objects


class TradingSignalRepository:
    """Repository for trading signal operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_recent_signals(self, symbol_id: Optional[int] = None, 
                          strategy_id: Optional[int] = None,
                          limit: int = 50) -> List[TradingSignal]:
        """Get recent trading signals"""
        query = self.db.query(TradingSignal)
        
        if symbol_id:
            query = query.filter(TradingSignal.symbol_id == symbol_id)
        if strategy_id:
            query = query.filter(TradingSignal.strategy_id == strategy_id)
        
        return query.order_by(desc(TradingSignal.timestamp)).limit(limit).all()
    
    def create(self, signal_data: Dict[str, Any]) -> TradingSignal:
        """Create new trading signal"""
        signal = TradingSignal(**signal_data)
        self.db.add(signal)
        self.db.commit()
        self.db.refresh(signal)
        return signal


class OrderRepository:
    """Repository for order operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_pending_orders(self) -> List[Order]:
        """Get all pending orders"""
        return self.db.query(Order).filter(Order.status == 'PENDING').all()
    
    def get_by_status(self, status: str) -> List[Order]:
        """Get orders by status"""
        return self.db.query(Order).filter(Order.status == status).all()
    
    def get_by_account_id(self, account_id: str, limit: int = 20) -> List[Order]:
        """Get last N orders for an account"""
        return (self.db.query(Order)
                .filter(Order.account_id == account_id)
                .order_by(desc(Order.submitted_at))
                .limit(limit)
                .all())
    
    def create(self, order_data: Dict[str, Any]) -> Order:
        """Create new order"""
        order = Order(**order_data)
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def update_status(self, order_id: int, status: str, 
                     filled_quantity: Optional[float] = None,
                     average_fill_price: Optional[float] = None) -> Optional[Order]:
        """Update order status"""
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = status
            if filled_quantity is not None:
                order.filled_quantity = filled_quantity
            if average_fill_price is not None:
                order.average_fill_price = average_fill_price
            
            if status == 'FILLED':
                order.filled_at = func.current_timestamp()
            elif status == 'CANCELLED':
                order.cancelled_at = func.current_timestamp()
            
            self.db.commit()
            self.db.refresh(order)
        return order


class PositionRepository:
    """Repository for position operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self) -> List[Position]:
        """Get all positions"""
        return self.db.query(Position).all()
    
    def get_by_symbol(self, symbol_id: int) -> Optional[Position]:
        """Get position by symbol"""
        return self.db.query(Position).filter(Position.symbol_id == symbol_id).first()
    
    def update_position(self, symbol_id: int, quantity: float, 
                       average_entry_price: float) -> Position:
        """Update or create position"""
        position = self.get_by_symbol(symbol_id)
        
        if position:
            # Update existing position
            position.quantity = quantity
            position.average_entry_price = average_entry_price
        else:
            # Create new position
            position = Position(
                symbol_id=symbol_id,
                quantity=quantity,
                average_entry_price=average_entry_price
            )
            self.db.add(position)
        
        self.db.commit()
        self.db.refresh(position)
        return position


class TradeRepository:
    """Repository for trade operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_recent_trades(self, limit: int = 100) -> List[Trade]:
        """Get recent trades"""
        return (self.db.query(Trade)
                .order_by(desc(Trade.entry_time))
                .limit(limit)
                .all())
    
    def get_by_strategy(self, strategy_id: int) -> List[Trade]:
        """Get trades by strategy"""
        return (self.db.query(Trade)
                .filter(Trade.strategy_id == strategy_id)
                .order_by(desc(Trade.entry_time))
                .all())
    
    def create(self, trade_data: Dict[str, Any]) -> Trade:
        """Create new trade"""
        trade = Trade(**trade_data)
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade


class AccountRepository:
    """Repository for account operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self) -> List[Account]:
        """Get all accounts"""
        return self.db.query(Account).all()
    
    def get_by_id(self, account_id: str) -> Optional[Account]:
        """Get account by ID"""
        return self.db.query(Account).filter(Account.account_id == account_id).first()
    
    def create(self, account_data: Dict[str, Any]) -> Account:
        """Create new account"""
        account = Account(**account_data)
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account
    
    def update_cash_balance(self, account_id: str, cash_balance: float) -> Optional[Account]:
        """Update account cash balance"""
        account = self.get_by_id(account_id)
        if account:
            account.cash_balance = cash_balance
            self.db.commit()
            self.db.refresh(account)
        return account
    
    def update(self, account_id: str, account_data: Dict[str, Any]) -> Optional[Account]:
        """Update account"""
        account = self.get_by_id(account_id)
        if account:
            for key, value in account_data.items():
                setattr(account, key, value)
            self.db.commit()
            self.db.refresh(account)
        return account


class StrategyRepository:
    """Repository for strategy operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self, active_only: bool = True) -> List[Strategy]:
        """Get all strategies"""
        query = self.db.query(Strategy)
        if active_only:
            query = query.filter(Strategy.is_active == True)
        return query.all()
    
    def get_by_id(self, strategy_id: int) -> Optional[Strategy]:
        """Get strategy by ID"""
        return self.db.query(Strategy).filter(Strategy.id == strategy_id).first()
    
    def get_by_name(self, name: str) -> Optional[Strategy]:
        """Get strategy by name"""
        return self.db.query(Strategy).filter(Strategy.name == name).first()
    
    def create(self, strategy_data: Dict[str, Any]) -> Strategy:
        """Create new strategy"""
        strategy = Strategy(**strategy_data)
        self.db.add(strategy)
        self.db.commit()
        self.db.refresh(strategy)
        return strategy
    
    def update(self, strategy_id: int, strategy_data: Dict[str, Any]) -> Optional[Strategy]:
        """Update strategy"""
        strategy = self.get_by_id(strategy_id)
        if strategy:
            for key, value in strategy_data.items():
                setattr(strategy, key, value)
            self.db.commit()
            self.db.refresh(strategy)
        return strategy
    
    def delete(self, strategy_id: int) -> bool:
        """Delete strategy (soft delete by setting is_active=False)"""
        strategy = self.get_by_id(strategy_id)
        if strategy:
            strategy.is_active = False
            self.db.commit()
            return True
        return False


class SystemLogRepository:
    """Repository for system log operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_info(self, module: str, message: str, details: Optional[str] = None, account_id: Optional[str] = None):
        """Log info message"""
        self._log('INFO', module, message, details, account_id)
    
    def log_warning(self, module: str, message: str, details: Optional[str] = None, account_id: Optional[str] = None):
        """Log warning message"""
        self._log('WARNING', module, message, details, account_id)
    
    def log_error(self, module: str, message: str, details: Optional[str] = None, account_id: Optional[str] = None):
        """Log error message"""
        self._log('ERROR', module, message, details, account_id)
    
    def _log(self, level: str, module: str, message: str, details: Optional[str] = None, account_id: Optional[str] = None):
        """Internal log method"""
        log = SystemLog(
            level=level,
            module=module,
            message=message,
            details=details,
            account_id=account_id
        )
        self.db.add(log)
        self.db.commit()


class SettingsRepository:
    """Repository for settings operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self, category: Optional[str] = None, active_only: bool = True) -> List[Setting]:
        """Get all settings, optionally filtered by category"""
        query = self.db.query(Setting)
        if category:
            query = query.filter(Setting.category == category)
        if active_only:
            query = query.filter(Setting.is_active == True)
        return query.order_by(Setting.category, Setting.name).all()
    
    def get_by_name(self, name: str) -> Optional[Setting]:
        """Get setting by name"""
        return self.db.query(Setting).filter(Setting.name == name).first()
    
    def get_by_category(self, category: str, active_only: bool = True) -> List[Setting]:
        """Get all settings in a category"""
        query = self.db.query(Setting).filter(Setting.category == category)
        if active_only:
            query = query.filter(Setting.is_active == True)
        return query.all()
    
    def create(self, setting_data: Dict[str, Any]) -> Setting:
        """Create new setting"""
        setting = Setting(**setting_data)
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting
    
    def update(self, name: str, setting_data: Dict[str, Any]) -> Optional[Setting]:
        """Update setting by name"""
        setting = self.get_by_name(name)
        if setting:
            for field, value in setting_data.items():
                setattr(setting, field, value)
            self.db.commit()
            self.db.refresh(setting)
        return setting
    
    def upsert(self, name: str, parameters: str, category: str = 'general', 
               is_active: bool = True) -> Setting:
        """Create or update a setting"""
        setting = self.get_by_name(name)
        if setting:
            # Update existing setting
            setting.parameters = parameters
            setting.category = category
            setting.is_active = is_active
        else:
            # Create new setting
            setting = Setting(
                name=name,
                parameters=parameters,
                category=category,
                is_active=is_active
            )
            self.db.add(setting)
        
        self.db.commit()
        self.db.refresh(setting)
        return setting
    
    def delete(self, name: str) -> bool:
        """Delete setting by name (soft delete by setting is_active=False)"""
        setting = self.get_by_name(name)
        if setting:
            setting.is_active = False
            self.db.commit()
            return True
        return False


# Repository factory for easy access
class RepositoryFactory:
    """Factory class to provide repository instances"""
    
    def __init__(self, db: Session):
        self.db = db
    
    @property
    def accounts(self) -> AccountRepository:
        return AccountRepository(self.db)
    
    @property
    def symbols(self) -> InstrumentRepository:
        """Alias for instruments repository for backward compatibility"""
        return InstrumentRepository(self.db)
    
    @property
    def instruments(self) -> InstrumentRepository:
        return InstrumentRepository(self.db)
    
    @property
    def market_data(self) -> MarketDataRepository:
        return MarketDataRepository(self.db)
    
    @property
    def trading_signals(self) -> TradingSignalRepository:
        return TradingSignalRepository(self.db)
    
    @property
    def orders(self) -> OrderRepository:
        return OrderRepository(self.db)
    
    @property
    def positions(self) -> PositionRepository:
        return PositionRepository(self.db)
    
    @property
    def trades(self) -> TradeRepository:
        return TradeRepository(self.db)
    
    @property
    def strategies(self) -> StrategyRepository:
        return StrategyRepository(self.db)
    
    @property
    def system_logs(self) -> SystemLogRepository:
        return SystemLogRepository(self.db)
    
    @property
    def settings(self) -> SettingsRepository:
        return SettingsRepository(self.db)
