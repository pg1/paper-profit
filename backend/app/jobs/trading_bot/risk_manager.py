import logging
from decimal import Decimal
from typing import Dict, Any
from sqlalchemy.orm import Session

from storage.repositories import RepositoryFactory
from storage.models import Account, Position

logger = logging.getLogger(__name__)


class RiskManager:
    """Module for risk management and position sizing"""
    
    def __init__(self, db: Session, repo_factory: RepositoryFactory):
        self.db = db
        self.repo_factory = repo_factory
    
    def calculate_position_size(self, account: Account, price: float, 
                               strategy_params: Dict[str, Any]) -> float:
        """Calculate position size based on risk management rules"""

        # Calculate maximum position value (use Decimal for precision)
        max_position_pct = Decimal(str(strategy_params.get('max_position_pct', 10.0)))
        price_decimal = Decimal(str(price))
        max_position_value = (account.cash_balance * max_position_pct) / Decimal('100')
        
        # Calculate number of shares
        max_shares = max_position_value / price_decimal
        
        # Ensure we don't exceed available cash
        available_shares = account.cash_balance / price_decimal
        
        # Use the smaller of the two
        position_shares = min(max_shares, available_shares)
        
        # Round down to whole shares
        position_shares = int(position_shares)
        
        logger.debug(f"Position calculation for account {account.account_id}: "
                    f"cash=${account.cash_balance:.2f}, price=${price:.2f}, "
                    f"max_shares={max_shares:.0f}, final_shares={position_shares}")
        
        return position_shares
    
    def check_max_positions_limit(self, current_positions: Dict[str, Position], 
                                 max_positions: int) -> bool:
        """Check if maximum positions limit has been reached"""
        if len(current_positions) >= max_positions:
            logger.info(f"Maximum positions limit reached: {len(current_positions)}/{max_positions}")
            return True
        return False
    
    def check_existing_position(self, symbol: str, current_positions: Dict[str, Position]) -> bool:
        """Check if we already have a position in the symbol"""
        existing_position = current_positions.get(symbol)
        if existing_position:
            logger.info(f"Already have position in {symbol}, skipping BUY")
            return True
        return False
    
    def check_position_to_sell(self, symbol: str, current_positions: Dict[str, Position]) -> bool:
        """Check if we have a position to sell"""
        existing_position = current_positions.get(symbol)
        if not existing_position or existing_position.quantity <= 0:
            logger.info(f"No position to sell for {symbol}")
            return False
        return True
    
    def get_sell_quantity(self, symbol: str, current_positions: Dict[str, Position]) -> float:
        """Get the quantity to sell for a position"""
        existing_position = current_positions.get(symbol)
        if existing_position:
            return existing_position.quantity
        return 0.0