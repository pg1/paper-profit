import math
import logging
from decimal import Decimal, InvalidOperation
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
    
    def _safe_decimal(self, value: Any, default: Decimal = Decimal('0')) -> Decimal:
        """Safely convert a value to Decimal, handling NaN, Infinity, empty strings, and invalid values.
        
        Args:
            value: The value to convert (float, str, Decimal, etc.)
            default: The default Decimal to return if conversion fails
            
        Returns:
            A valid Decimal, or the default value if conversion fails
        """
        try:
            # Handle None
            if value is None:
                return default
            
            # Handle NaN, Infinity, -Infinity (float or string representations)
            if isinstance(value, float):
                if math.isnan(value) or math.isinf(value):
                    logger.warning(f"Invalid numeric value encountered: {value}, using default {default}")
                    return default
            
            # Convert to string and check for empty/invalid string representations
            str_value = str(value).strip().lower()
            if not str_value:
                logger.warning(f"Empty value encountered, using default {default}")
                return default
            if str_value in ('nan', 'inf', 'infinity', '-nan', '-inf', '-infinity', 'snan'):
                logger.warning(f"Invalid numeric string encountered: '{value}', using default {default}")
                return default
            
            return Decimal(str_value)
        except (InvalidOperation, ValueError, TypeError) as e:
            logger.warning(f"Could not convert '{value}' to Decimal: {e}, using default {default}")
            return default
    
    def calculate_position_size(self, account: Account, price: float, 
                               strategy_params: Dict[str, Any]) -> float:
        """Calculate position size based on risk management rules"""

        # Calculate maximum position value (use Decimal for precision)
        # Default to 20% if max_position_pct is empty or not set
        raw_max_pct = strategy_params.get('max_position_pct', '')
        if raw_max_pct == '' or raw_max_pct is None:
            raw_max_pct = 20.0
        max_position_pct = self._safe_decimal(raw_max_pct)
        price_decimal = self._safe_decimal(price)
        
        # If price is invalid (zero or default), return 0
        if price_decimal <= Decimal('0'):
            logger.warning(f"Invalid price ({price}) for position sizing, returning 0")
            return 0
        
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