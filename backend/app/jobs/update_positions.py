import sys
import os
from sqlalchemy.orm import Session
from datetime import datetime
import logging

# Add the parent directory to Python path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import get_session
from storage.repositories import RepositoryFactory
from storage.models import Order, Position, Instrument
from octopus.data_providers.yahoo_finance import YahooFinanceService

# Set up logging - use WARNING level to reduce noise for background jobs
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Suppress SQLAlchemy engine INFO logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def update_position_prices(db_session: Session):
    """Update current prices for all positions using Yahoo Finance"""
    logger.info("Starting position price update...")
    
    repo = RepositoryFactory(db_session)
    yahoo_service = YahooFinanceService(db_session)
    
    # Get all positions
    positions = repo.positions.get_all()
    
    if not positions:
        logger.info("No positions found to update")
        return 0
    
    updated_count = 0
    failed_count = 0
    
    for position in positions:
        try:
            # Get the instrument symbol for this position
            instrument = repo.instruments.get_by_id(position.symbol_id)
            if not instrument:
                logger.warning(f"Instrument not found for position ID {position.id}")
                failed_count += 1
                continue
            
            symbol = instrument.symbol
            
            # Fetch current price from Yahoo Finance
            price_data = yahoo_service.fetch_current_price(symbol)
            if not price_data or 'price' not in price_data:
                logger.warning(f"Could not fetch current price for {symbol}")
                failed_count += 1
                continue
            
            current_price = price_data['price']
            
            # Update position with current price (convert float to decimal)
            position.current_price = float(current_price)
            
            # Calculate unrealized P&L if we have both current price and average entry price
            if position.average_entry_price and position.quantity:
                unrealized_pnl = (float(current_price) - float(position.average_entry_price)) * float(position.quantity)
                position.unrealized_pnl = unrealized_pnl
            
            db_session.commit()
            updated_count += 1
            logger.info(f"Updated {symbol}: ${current_price:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating price for position ID {position.id}: {e}")
            db_session.rollback()
            failed_count += 1
    
    logger.info(f"Position price update completed: {updated_count} updated, {failed_count} failed")
    return updated_count


def run():
    """Main job execution function"""
    logger.info("Starting update positions job...")
    
    try:
        with get_session() as db_session:
            updated_count = update_position_prices(db_session)
            logger.info(f"Update positions job completed: {updated_count} positions updated")
            
    except Exception as e:
        logger.error(f"Error in update positions job: {e}")
        raise
   
if __name__ == "__main__":
    run()
