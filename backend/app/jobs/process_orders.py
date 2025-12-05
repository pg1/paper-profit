import sys
import os
from sqlalchemy.orm import Session
from datetime import datetime
import logging

# Add the parent directory to Python path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import get_session
from storage.repositories import RepositoryFactory
from storage.models import Order, Position
from octopus.data_providers.yahoo_finance import YahooFinanceService

# Set up logging - use WARNING level to reduce noise for background jobs
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Suppress SQLAlchemy engine INFO logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def run():
    """Process pending orders and create positions for filled orders"""
    logger.info("Starting order processing job...")
    
    # Get database session directly
    db: Session = get_session()
    repo_factory = RepositoryFactory(db)
    
    try:
        # Get pending orders
        pending_orders = repo_factory.orders.get_pending_orders()
        
        if not pending_orders:
            logger.info("No pending orders found.")
            return
        
        logger.info(f"Found {len(pending_orders)} pending orders to process.")
        
        processed_count = 0
        for order in pending_orders:
            try:
                # Process the order (simulate order execution)
                if process_order(order, repo_factory):
                    processed_count += 1
                    logger.info(f"Successfully processed order {order.id} for {order.instrument.symbol}")
                else:
                    logger.warning(f"Failed to process order {order.id}")
                    
            except Exception as e:
                logger.error(f"Error processing order {order.id}: {str(e)}")
                # Log the error to system logs
                repo_factory.system_logs.log_error(
                    module="process_orders",
                    message=f"Error processing order {order.id}",
                    details=str(e)
                )
        
        logger.info(f"Order processing completed. Processed {processed_count} orders.")
        
    except Exception as e:
        logger.error(f"Error in order processing job: {str(e)}")
        raise
    finally:
        # Close the session properly
        db.close()


def process_order(order: Order, repo_factory: RepositoryFactory) -> bool:
    """Process a single pending order and create position if needed"""
    
    # For now, we'll simulate order execution by immediately filling the order
    # In a real system, this would interact with a broker API
    
    try:
        # Update order status to FILLED
        updated_order = repo_factory.orders.update_status(
            order_id=order.id,
            status='FILLED',
            filled_quantity=order.quantity,
            average_fill_price=order.price or get_current_market_price(order.symbol_id, repo_factory)
        )
        
        if not updated_order:
            logger.error(f"Failed to update order {order.id} status")
            return False
        
        # Create or update position based on order side
        if order.side.upper() == 'BUY':
            return create_or_update_position_for_buy(order, repo_factory)
        elif order.side.upper() == 'SELL':
            return create_or_update_position_for_sell(order, repo_factory)
        else:
            logger.error(f"Unknown order side: {order.side} for order {order.id}")
            return False
            
    except Exception as e:
        logger.error(f"Error processing order {order.id}: {str(e)}")
        return False


def create_or_update_position_for_buy(order: Order, repo_factory: RepositoryFactory) -> bool:
    """Create or update position for a BUY order"""
    try:
        # Calculate total cost of the buy order
        fill_price = order.average_fill_price or order.price
        if not fill_price:
            logger.error(f"No fill price available for BUY order {order.id}")
            return False
        
        total_cost = order.quantity * fill_price
        
        # Get account and check if there's sufficient cash balance
        account = repo_factory.accounts.get_by_id(order.account_id)
        if not account:
            logger.error(f"Account {order.account_id} not found for BUY order {order.id}")
            return False
        
        if account.cash_balance < total_cost:
            repo_factory.orders.update_status(
                order_id=order.id,
                status='REJECTED',
            )
            logger.error(f"Insufficient cash balance for BUY order {order.id}. Available: {account.cash_balance}, Required: {total_cost}")
            return False
        
        # Deduct the cost from account cash balance
        new_cash_balance = account.cash_balance - total_cost
        account.cash_balance = new_cash_balance
        
        # Get existing position for this symbol and account
        # We need to filter by both symbol_id and account_id
        existing_position = (repo_factory.db.query(Position)
                           .filter(Position.symbol_id == order.symbol_id, 
                                  Position.account_id == order.account_id)
                           .first())
        
        if existing_position:
            # Update existing position
            new_quantity = existing_position.quantity + order.quantity
            new_avg_price = calculate_weighted_average_price(
                existing_position.quantity, existing_position.average_entry_price,
                order.quantity, fill_price
            )
            
            existing_position.quantity = new_quantity
            existing_position.average_entry_price = new_avg_price
            repo_factory.db.commit()
            repo_factory.db.refresh(existing_position)
            
        else:
            # Create new position with account_id
            new_position = Position(
                account_id=order.account_id,
                symbol_id=order.symbol_id,
                quantity=order.quantity,
                average_entry_price=fill_price
            )
            repo_factory.db.add(new_position)
            repo_factory.db.commit()
            repo_factory.db.refresh(new_position)
        
        logger.info(f"BUY order {order.id} processed. Deducted ${total_cost:.2f} from account {order.account_id}. New cash balance: ${new_cash_balance:.2f}")
        return True
            
    except Exception as e:
        logger.error(f"Error creating/updating position for BUY order {order.id}: {str(e)}")
        return False


def create_or_update_position_for_sell(order: Order, repo_factory: RepositoryFactory) -> bool:
    """Create or update position for a SELL order"""
    try:
        # Calculate total proceeds from the sell order
        fill_price = order.average_fill_price or order.price
        if not fill_price:
            logger.error(f"No fill price available for SELL order {order.id}")
            return False
        
        total_proceeds = order.quantity * fill_price
        
        # Get account to update cash balance
        account = repo_factory.accounts.get_by_id(order.account_id)
        if not account:
            logger.error(f"Account {order.account_id} not found for SELL order {order.id}")
            return False
        
        # Get existing position for this symbol and account
        existing_position = (repo_factory.db.query(Position)
                           .filter(Position.symbol_id == order.symbol_id, 
                                  Position.account_id == order.account_id)
                           .first())
        
        if not existing_position:
            logger.error(f"No existing position found for SELL order {order.id}")
            return False
        
        if existing_position.quantity < order.quantity:
            logger.error(f"Insufficient position quantity for SELL order {order.id}")
            return False
        
        # Update position quantity (reduce position)
        new_quantity = existing_position.quantity - order.quantity
        
        if new_quantity == 0:
            # Position is closed, set quantity to zero
            existing_position.quantity = 0
        else:
            # Reduce position but keep average entry price
            existing_position.quantity = new_quantity
        
        # Add the proceeds to account cash balance
        new_cash_balance = account.cash_balance + total_proceeds
        account.cash_balance = new_cash_balance
        
        repo_factory.db.commit()
        repo_factory.db.refresh(existing_position)
        
        logger.info(f"SELL order {order.id} processed. Added ${total_proceeds:.2f} to account {order.account_id}. New cash balance: ${new_cash_balance:.2f}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating/updating position for SELL order {order.id}: {str(e)}")
        return False


def get_current_market_price(symbol_id: int, repo_factory: RepositoryFactory) -> float:
    """Get current market price for a symbol using Yahoo Finance"""
    try:
        # Get the instrument by ID to get the symbol
        instrument = repo_factory.instruments.get_by_id(symbol_id)
        if not instrument:
            logger.error(f"Instrument with ID {symbol_id} not found")
            return 100.0  # Fallback price
        
        # Create Yahoo Finance service instance
        yahoo_service = YahooFinanceService(repo_factory.db)
        
        # Fetch current price using the symbol
        price_data = yahoo_service.fetch_current_price(instrument.symbol)
        
        if price_data and 'price' in price_data:
            logger.info(f"Fetched current price for {instrument.symbol}: ${price_data['price']}")
            return float(price_data['price'])
        else:
            logger.warning(f"Could not fetch current price for {instrument.symbol}, using fallback price")
            return 100.0  # Fallback price
            
    except Exception as e:
        logger.error(f"Error fetching current market price for symbol_id {symbol_id}: {str(e)}")
        return 100.0  # Fallback price


def calculate_weighted_average_price(qty1: float, price1: float, qty2: float, price2: float) -> float:
    """Calculate weighted average price for position averaging"""
    if qty1 + qty2 == 0:
        return 0.0
    return ((qty1 * price1) + (qty2 * price2)) / (qty1 + qty2)


if __name__ == "__main__":
    run()
