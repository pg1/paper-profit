import sys
import os
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
import logging

# Add the parent directory to Python path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import get_session, retry_on_lock
from storage.repositories import AccountRepository
from storage.models import AccountSummary

# Set up logging - use WARNING level to reduce noise for background jobs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress SQLAlchemy engine INFO logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def update_account_summaries(db_session: Session):
    """Update account_summary table for all accounts.
    
    Creates a new record each day, or updates the existing record for today
    with the latest portfolio values and performance metrics.
    """
    logger.info("Starting account summary update...")
    
    account_repo = AccountRepository(db_session)
    accounts = account_repo.get_all()
    
    if not accounts:
        logger.info("No accounts found to update")
        return 0
    
    today = date.today()
    tomorrow = today + timedelta(days=1)
    updated_count = 0
    created_count = 0
    
    for account in accounts:
        try:
            # Calculate portfolio value from positions
            portfolio_value = 0.0
            total_cost_basis = 0.0
            total_unrealized_pnl = 0.0
            total_realized_pnl = 0.0
            
            for position in account.positions:
                if position.current_price and position.quantity:
                    position_value = float(position.quantity) * float(position.current_price)
                    portfolio_value += position_value
                    total_unrealized_pnl += float(position.unrealized_pnl) if position.unrealized_pnl else 0.0
                
                if position.quantity and position.average_entry_price:
                    total_cost_basis += float(position.quantity) * float(position.average_entry_price)
            
            # Calculate total realized P&L from trades
            for trade in account.trades:
                total_realized_pnl += float(trade.net_pnl) if trade.net_pnl else 0.0
            
            cash_balance = float(account.cash_balance)
            total_equity = cash_balance + portfolio_value
            
            # Calculate daily P&L - compare with the latest summary if available
            daily_pnl = 0.0
            yesterday_summary = (db_session.query(AccountSummary)
                                .filter(AccountSummary.account_id == account.account_id)
                                .order_by(AccountSummary.timestamp.desc())
                                .first())
            if yesterday_summary:
                yesterday_equity = float(yesterday_summary.total_equity)
                daily_pnl = total_equity - yesterday_equity
            
            # Calculate max drawdown from all historical summaries + current equity
            max_drawdown = 0.0
            all_summaries = (db_session.query(AccountSummary)
                            .filter(AccountSummary.account_id == account.account_id)
                            .order_by(AccountSummary.timestamp.asc())
                            .all())
            
            peak = float(account.cash_balance)  # Start with initial cash as peak
            if all_summaries:
                peak = float(all_summaries[0].total_equity)
                for s in all_summaries:
                    equity = float(s.total_equity)
                    if equity > peak:
                        peak = equity
                    drawdown = (peak - equity) / peak if peak > 0 else 0
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
            
            # Also consider current equity for drawdown
            if total_equity > peak:
                peak = total_equity
            current_drawdown = (peak - total_equity) / peak if peak > 0 else 0
            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown
            
            # Calculate Sharpe ratio (simplified)
            daily_return_pct = 0.0
            if total_cost_basis > 0:
                daily_return_pct = (daily_pnl / total_cost_basis) * 100
            elif total_equity > 0:
                daily_return_pct = (daily_pnl / total_equity) * 100
            
            volatility = 0.15  # Simplified - 15% annual volatility
            sharpe_ratio = 0.0
            if volatility > 0:
                sharpe_ratio = (daily_return_pct * 252) / (volatility * 16)
            
            # Check if a summary already exists for today
            existing_summary = (db_session.query(AccountSummary)
                               .filter(
                                   AccountSummary.account_id == account.account_id,
                                   AccountSummary.timestamp >= today,
                                   AccountSummary.timestamp < tomorrow
                               )
                               .first())
            
            now = datetime.utcnow()
            
            if existing_summary:
                # Update existing record for today
                existing_summary.total_equity = total_equity
                existing_summary.cash_balance = cash_balance
                existing_summary.portfolio_value = portfolio_value
                existing_summary.daily_pnl = daily_pnl
                existing_summary.unrealized_pnl = total_unrealized_pnl
                existing_summary.realized_pnl = total_realized_pnl
                existing_summary.max_drawdown = max_drawdown
                existing_summary.sharpe_ratio = sharpe_ratio
                existing_summary.timestamp = now
                db_session.commit()
                updated_count += 1
                logger.info(f"Updated summary for {account.account_id}: equity=${total_equity:.2f}, daily_pnl=${daily_pnl:.2f}")
            else:
                # Create new record
                new_summary = AccountSummary(
                    account_id=account.account_id,
                    timestamp=now,
                    total_equity=total_equity,
                    cash_balance=cash_balance,
                    portfolio_value=portfolio_value,
                    daily_pnl=daily_pnl,
                    unrealized_pnl=total_unrealized_pnl,
                    realized_pnl=total_realized_pnl,
                    max_drawdown=max_drawdown,
                    sharpe_ratio=sharpe_ratio
                )
                db_session.add(new_summary)
                db_session.commit()
                created_count += 1
                logger.info(f"Created summary for {account.account_id}: equity=${total_equity:.2f}, daily_pnl=${daily_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating summary for account {account.account_id}: {e}")
            try:
                db_session.rollback()
            except Exception as rollback_error:
                logger.error(f"Error during rollback for account {account.account_id}: {rollback_error}")
    
    logger.info(f"Account summary update completed: {created_count} created, {updated_count} updated")
    return created_count + updated_count


@retry_on_lock(max_retries=5, delay=1.0, backoff=2.0)
def run():
    """Main job execution function"""
    logger.info("Starting update account summary job...")
    
    try:
        with get_session() as db_session:
            total = update_account_summaries(db_session)
            logger.info(f"Update account summary job completed: {total} records processed")
            
    except Exception as e:
        logger.error(f"Error in update account summary job: {e}")
        raise


if __name__ == "__main__":
    run()
