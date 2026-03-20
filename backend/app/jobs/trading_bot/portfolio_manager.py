import logging
from typing import List, Dict
from sqlalchemy.orm import Session

from storage.repositories import RepositoryFactory
from storage.models import Account, Strategy, Position

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Module for managing positions and portfolio"""
    
    def __init__(self, db: Session, repo_factory: RepositoryFactory):
        self.db = db
        self.repo_factory = repo_factory
    
    def get_active_accounts_with_strategies(self) -> List[Account]:
        """Get all active accounts that have strategies assigned"""
        accounts = self.repo_factory.accounts.get_all()
        return [acc for acc in accounts if acc.is_active and acc.strategy_id and acc.status == 'active']
    
    def get_account_positions(self, account_id: str) -> Dict[str, Position]:
        """Get current positions for an account, indexed by symbol"""
        positions = {}
        account_positions = self.db.query(Position).filter(
            Position.account_id == account_id,
            Position.quantity > 0
        ).all()
        
        for position in account_positions:
            instrument = self.repo_factory.instruments.get_by_id(position.symbol_id)
            if instrument:
                positions[instrument.symbol] = position
        
        return positions
    
    def get_or_create_instrument(self, symbol: str):
        """Get or create instrument for a symbol"""
        instrument = self.repo_factory.instruments.get_by_symbol(symbol)
        if not instrument:
            logger.info(f"Instrument {symbol} not found, creating new instrument")
            #TODO: Fix name. IT should be company name and not symbol
            instrument = self.repo_factory.instruments.create({
                'symbol': symbol,
                'name': symbol,
                'currency': 'USD',
                'is_active': True
            })
        return instrument
    
    def get_account_strategy(self, account: Account) -> Strategy:
        """Get the strategy for an account"""
        strategy = self.repo_factory.strategies.get_by_id(account.strategy_id)
        if not strategy or not strategy.is_active:
            raise ValueError(f"Strategy {account.strategy_id} not found or inactive for account {account.account_id}")
        return strategy