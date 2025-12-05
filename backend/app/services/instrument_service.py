from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from storage.repositories import InstrumentRepository
from storage.models import Instrument


class InstrumentService:
    """Service for instrument operations"""
    
    def __init__(self, db: Session):
        self.repository = InstrumentRepository(db)
    
    def get_all_instruments(self, active_only: bool = True) -> List[Instrument]:
        """Get all instruments"""
        return self.repository.get_all(active_only)
    
    def get_instrument_by_id(self, instrument_id: int) -> Optional[Instrument]:
        """Get instrument by ID"""
        return self.repository.get_by_id(instrument_id)
    
    def get_instrument_by_symbol(self, symbol: str) -> Optional[Instrument]:
        """Get instrument by symbol string"""
        return self.repository.get_by_symbol(symbol)
    
    def create_instrument(self, instrument_data: Dict[str, Any]) -> Instrument:
        """Create new instrument"""
        # Validate required fields
        required_fields = ['symbol']
        for field in required_fields:
            if field not in instrument_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate symbol format (basic validation)
        symbol = instrument_data['symbol']
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        
        # Check if symbol already exists
        existing_instrument = self.repository.get_by_symbol(symbol)
        if existing_instrument:
            raise ValueError(f"Instrument with symbol {symbol} already exists")
        
        return self.repository.create(instrument_data)
    
    def update_instrument(self, instrument_id: int, instrument_data: Dict[str, Any]) -> Optional[Instrument]:
        """Update instrument"""
        # Validate that we're not trying to change the symbol to an existing one
        if 'symbol' in instrument_data:
            existing_instrument = self.repository.get_by_symbol(instrument_data['symbol'])
            if existing_instrument and existing_instrument.id != instrument_id:
                raise ValueError(f"Instrument with symbol {instrument_data['symbol']} already exists")
        
        return self.repository.update(instrument_id, instrument_data)
    
    def deactivate_instrument(self, instrument_id: int) -> Optional[Instrument]:
        """Deactivate an instrument"""
        return self.repository.update(instrument_id, {'is_active': False})
    
    def activate_instrument(self, instrument_id: int) -> Optional[Instrument]:
        """Activate an instrument"""
        return self.repository.update(instrument_id, {'is_active': True})
    
    def search_instruments(self, query: str, active_only: bool = True) -> List[Instrument]:
        """Search instruments by symbol or name"""
        all_instruments = self.repository.get_all(active_only)
        
        query_lower = query.lower()
        results = []
        
        for instrument in all_instruments:
            if (query_lower in instrument.symbol.lower() or 
                (instrument.name and query_lower in instrument.name.lower())):
                results.append(instrument)
        
        return results
    
    def get_instruments_by_exchange(self, exchange: str, active_only: bool = True) -> List[Instrument]:
        """Get instruments by exchange"""
        all_instruments = self.repository.get_all(active_only)
        return [instrument for instrument in all_instruments 
                if instrument.exchange and instrument.exchange.lower() == exchange.lower()]
    
    def validate_instrument_exists(self, instrument_id: int) -> bool:
        """Validate that an instrument exists"""
        return self.repository.get_by_id(instrument_id) is not None
    
    def validate_instrument_active(self, instrument_id: int) -> bool:
        """Validate that an instrument exists and is active"""
        instrument = self.repository.get_by_id(instrument_id)
        return instrument is not None and instrument.is_active
    
    def get_instrument_details(self, instrument_id: int) -> Dict[str, Any]:
        """Get detailed instrument information including market data and technical indicators"""
        instrument = self.repository.get_by_id(instrument_id)
        if not instrument:
            raise ValueError(f"Instrument with ID {instrument_id} not found")
        
        # Get latest market data
        latest_market_data = None
        if instrument.market_data:
            latest_market_data = sorted(instrument.market_data, key=lambda x: x.timestamp, reverse=True)[0] if instrument.market_data else None
        
        # Get latest technical indicators
        latest_indicators = None
        if instrument.technical_indicators:
            latest_indicators = sorted(instrument.technical_indicators, key=lambda x: x.timestamp, reverse=True)[0] if instrument.technical_indicators else None
        
        return {
            'id': instrument.id,
            'symbol': instrument.symbol,
            'name': instrument.name,
            'exchange': instrument.exchange,
            'currency': instrument.currency,
            'is_active': instrument.is_active,
            'created_at': instrument.created_at,
            'updated_at': instrument.updated_at,
            'latest_market_data': {
                'timestamp': latest_market_data.timestamp if latest_market_data else None,
                'open': float(latest_market_data.open) if latest_market_data else None,
                'high': float(latest_market_data.high) if latest_market_data else None,
                'low': float(latest_market_data.low) if latest_market_data else None,
                'close': float(latest_market_data.close) if latest_market_data else None,
                'volume': latest_market_data.volume if latest_market_data else None
            } if latest_market_data else None,
            'latest_technical_indicators': {
                'timestamp': latest_indicators.timestamp if latest_indicators else None,
                'sma_20': float(latest_indicators.sma_20) if latest_indicators and latest_indicators.sma_20 else None,
                'sma_50': float(latest_indicators.sma_50) if latest_indicators and latest_indicators.sma_50 else None,
                'sma_200': float(latest_indicators.sma_200) if latest_indicators and latest_indicators.sma_200 else None,
                'rsi_14': float(latest_indicators.rsi_14) if latest_indicators and latest_indicators.rsi_14 else None
            } if latest_indicators else None
        }
