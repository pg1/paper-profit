from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from storage.repositories import PositionRepository
from storage.models import Position as PositionModel


class PositionService:
    """Service for position operations"""
    
    def __init__(self, db: Session):
        self.repository = PositionRepository(db)
    
    def get_all_positions(self) -> List[PositionModel]:
        """Get all positions"""
        return self.repository.get_all()
    
    def get_position_by_symbol(self, symbol_id: int) -> Optional[PositionModel]:
        """Get position by symbol ID"""
        return self.repository.get_by_symbol(symbol_id)
    
    def get_positions_by_account(self, account_id: str) -> List[PositionModel]:
        """Get all positions for a specific account"""
        all_positions = self.repository.get_all()
        return [position for position in all_positions if position.account_id == account_id]
    
    def update_position(self, symbol_id: int, quantity: float, 
                       average_entry_price: float, account_id: str) -> PositionModel:
        """Update or create position"""
        if quantity < 0:
            raise ValueError("Position quantity cannot be negative")
        
        if average_entry_price <= 0:
            raise ValueError("Average entry price must be positive")
        
        # For now, we'll use the repository's update_position method
        # In a real implementation, we might want to handle account-specific positions
        return self.repository.update_position(symbol_id, quantity, average_entry_price)
    
    def close_position(self, symbol_id: int, account_id: str) -> Optional[PositionModel]:
        """Close a position by setting quantity to zero"""
        position = self.repository.get_by_symbol(symbol_id)
        if position and position.account_id == account_id:
            return self.repository.update_position(symbol_id, 0, position.average_entry_price)
        return None
    
    def calculate_position_value(self, position: PositionModel, current_price: Optional[float] = None) -> Dict[str, Any]:
        """Calculate position value and P&L"""
        if current_price is None:
            current_price = position.current_price or 0
        
        quantity = position.quantity or 0
        average_entry_price = position.average_entry_price or 0
        
        market_value = quantity * current_price
        cost_basis = quantity * average_entry_price
        unrealized_pnl = market_value - cost_basis
        
        return {
            'position_id': position.id,
            'symbol_id': position.symbol_id,
            'quantity': float(quantity),
            'average_entry_price': float(average_entry_price),
            'current_price': float(current_price),
            'market_value': float(market_value),
            'cost_basis': float(cost_basis),
            'unrealized_pnl': float(unrealized_pnl),
            'unrealized_pnl_percentage': float(unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
        }
    
    def get_portfolio_summary(self, account_id: str) -> Dict[str, Any]:
        """Get portfolio summary for an account"""
        positions = self.get_positions_by_account(account_id)
        
        total_market_value = 0.0
        total_cost_basis = 0.0
        total_unrealized_pnl = 0.0
        
        for position in positions:
            position_value = self.calculate_position_value(position)
            total_market_value += position_value['market_value']
            total_cost_basis += position_value['cost_basis']
            total_unrealized_pnl += position_value['unrealized_pnl']
        
        return {
            'account_id': account_id,
            'number_of_positions': len(positions),
            'total_market_value': total_market_value,
            'total_cost_basis': total_cost_basis,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_unrealized_pnl_percentage': (total_unrealized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0,
            'positions': [self.calculate_position_value(pos) for pos in positions]
        }
    
    def validate_position_exists(self, symbol_id: int, account_id: str) -> bool:
        """Validate that a position exists for the given symbol and account"""
        position = self.repository.get_by_symbol(symbol_id)
        return position is not None and position.account_id == account_id
