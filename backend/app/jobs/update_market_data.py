import sys
import os
from sqlalchemy.orm import Session
from datetime import datetime
import logging

# Add the parent directory to Python path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import get_session
from storage.repositories import RepositoryFactory
from storage.models import Instrument, MarketData
from octopus.data_providers.yahoo_finance import YahooFinanceService
from utils.market_hours import market_hours

# Set up logging - use WARNING level to reduce noise for background jobs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress SQLAlchemy engine INFO logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def update_market_data(db_session: Session):
    """Update market data for all active instruments using Yahoo Finance"""
    
    # Check if market is open
    if not market_hours.is_market_open():
        logger.info("Market is closed, skipping market data update")
        return 0
    
    logger.info("Starting market data update...")
    
    repo = RepositoryFactory(db_session)
    yahoo_service = YahooFinanceService(db_session)
    
    # Get all active instruments
    instruments = repo.instruments.get_all(active_only=True)
    
    if not instruments:
        logger.info("No active instruments found to update")
        return 0
    
    updated_count = 0
    failed_count = 0
    
    for instrument in instruments:
        try:
            symbol = instrument.symbol
            current_time = datetime.now()
            
            # Fetch current price data from Yahoo Finance
            price_data = yahoo_service.fetch_current_price(symbol)
            if not price_data or 'price' not in price_data:
                logger.warning(f"Could not fetch current price for {symbol}")
                failed_count += 1
                continue
            
            current_price = price_data['price']
            
            # Create market data entry
            market_data = {
                'symbol_id': instrument.id,
                'timestamp': current_time,
                'interval': '1min',
                'open': float(current_price),
                'high': float(current_price),
                'low': float(current_price),
                'close': float(current_price),
                'volume': 0,  # Volume not available from current price fetch
                'vwap': float(current_price),
                'trade_count': 1
            }
            
            # Save to database
            repo.market_data.create(market_data)
            updated_count += 1
            
            logger.info(f"Updated market data for {symbol}: ${current_price:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating market data for {symbol}: {e}")
            failed_count += 1
    
    logger.info(f"Market data update completed: {updated_count} updated, {failed_count} failed")
    return updated_count


def run():
    """Main job execution function"""
    logger.info("Starting update market data job...")
    
    try:
        with get_session() as db_session:
            updated_count = update_market_data(db_session)
            logger.info(f"Update market data job completed: {updated_count} instruments updated")
            
    except Exception as e:
        logger.error(f"Error in update market data job: {e}")
        raise


if __name__ == "__main__":
    run()
