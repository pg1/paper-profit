from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from storage.repositories import AccountRepository, InstrumentRepository, OrderRepository
from storage.models import Account as AccountModel, Strategy
from .log_service import LogService
from uuid import uuid4
from datetime import datetime


class AccountService:
    """Service for account operations"""
    
    def __init__(self, db: Session):
        self.repository = AccountRepository(db)
        self.db = db
    
    def get_all_accounts(self) -> List[AccountModel]:
        """Get all accounts"""
        return self.repository.get_all()
    
    def get_account_by_id(self, account_id: str) -> Optional[AccountModel]:
        """Get account by ID"""
        return self.repository.get_by_id(account_id)
    
    def create_account(self, account_data: Dict[str, Any]) -> AccountModel:
        """Create new account"""
        # Validate required fields
        required_fields = ['account_id', 'account_name', 'cash_balance']
        for field in required_fields:
            if field not in account_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate cash balance is non-negative
        if account_data['cash_balance'] < 0:
            raise ValueError("Cash balance cannot be negative")
        
        # Check if account already exists
        existing_account = self.repository.get_by_id(account_data['account_id'])
        if existing_account:
            raise ValueError(f"Account with ID {account_data['account_id']} already exists")
        
        # Set default values for optional fields
        account_data.setdefault('account_type', 'virtual')
        account_data.setdefault('currency', 'USD')
        account_data.setdefault('status', 'active')
        account_data.setdefault('is_active', True)
        
        # Create the account
        account = self.repository.create(account_data)
        
        # Log successful account creation
        log_service = LogService(self.repository.db)
        log_service.log_info(
            module="AccountService",
            message=f"Account created successfully: {account.account_id}",
            details=f"Initial cash balance: {account.cash_balance}, Type: {account.account_type}"
        )
        
        return account
    
    def update_cash_balance(self, account_id: str, cash_balance: float) -> Optional[AccountModel]:
        """Update account cash balance"""
        if cash_balance < 0:
            raise ValueError("Cash balance cannot be negative")
        
        return self.repository.update_cash_balance(account_id, cash_balance)
    
    def update_account(self, account_id: str, account_data: Dict[str, Any]) -> Optional[AccountModel]:
        """Update account"""
        # Validate account exists
        existing_account = self.repository.get_by_id(account_id)
        if not existing_account:
            raise ValueError(f"Account with ID {account_id} not found")
        
        # Validate cash balance is non-negative if provided
        if 'cash_balance' in account_data and account_data['cash_balance'] < 0:
            raise ValueError("Cash balance cannot be negative")
        
        # Update the account
        updated_account = self.repository.update(account_id, account_data)
        
        # Log successful account update
        log_service = LogService(self.repository.db)
        log_service.log_info(
            module="AccountService",
            message=f"Account updated successfully: {account_id}",
            details=f"Updated fields: {list(account_data.keys())}"
        )
        
        return updated_account
    
    def get_account_summary(self, account_id: str) -> Dict[str, Any]:
        """Get account summary including positions and performance"""
        account = self.repository.get_by_id(account_id)
        if not account:
            raise ValueError(f"Account with ID {account_id} not found")
        
        # Calculate portfolio value from positions
        portfolio_value = 0.0
        unrealized_pnl = 0.0
        
        for position in account.positions:
            if position.current_price and position.quantity:
                # Convert decimal values to float before arithmetic operations
                position_value = float(position.quantity) * float(position.current_price)
                portfolio_value += position_value
                unrealized_pnl += float(position.unrealized_pnl) if position.unrealized_pnl else 0.0
        
        total_equity = float(account.cash_balance) + portfolio_value
        
        return {
            'account_id': account.account_id,
            'cash_balance': float(account.cash_balance),
            'portfolio_value': portfolio_value,
            'total_equity': total_equity,
            'unrealized_pnl': unrealized_pnl,
            'number_of_positions': len(account.positions),
            'created_at': account.created_at
        }
    
    def validate_account_exists(self, account_id: str) -> bool:
        """Validate that an account exists"""
        return self.repository.get_by_id(account_id) is not None
    
    def create_buy_order(self, account_id: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a buy order for an account"""
        # Basic payload validation
        if 'stock_symbol' not in order_data or 'shares' not in order_data:
            raise ValueError("Payload must include 'stock_symbol' and 'shares'")

        stock_symbol = str(order_data['stock_symbol']).upper()
        try:
            shares = float(order_data['shares'])
        except Exception:
            raise ValueError("'shares' must be a number")

        if shares <= 0:
            raise ValueError("'shares' must be greater than zero")

        # Validate account exists
        if not self.validate_account_exists(account_id):
            raise ValueError(f"Account {account_id} not found")

        # Ensure instrument exists or create it
        instr_repo = InstrumentRepository(self.db)
        instrument = instr_repo.get_by_symbol(stock_symbol)
        if not instrument:
            instrument = instr_repo.create({
                'symbol': stock_symbol,
                'name': None,
                'exchange': None,
                'currency': 'USD',
                'is_active': True
            })

        '''
        # Ensure a default 'manual' strategy exists (used for user-initiated orders)
        strategy = self.db.query(Strategy).filter(Strategy.name == 'manual').first()
        if not strategy:
            strategy = Strategy(name='manual', description='Manual user orders', parameters=None, is_active=True)
            self.db.add(strategy)
            self.db.commit()
            self.db.refresh(strategy)
        '''

        # Build order payload for repository
        order_repo = OrderRepository(self.db)
        new_order = {
            'account_id': account_id,
            'symbol_id': instrument.id,
            'strategy_id': 0,
            'order_id': str(uuid4()),
            'order_type': (order_data.get('order_type') or 'market').upper(),
            'side': 'BUY',
            'quantity': shares,
            'price': order_data.get('price'),
            'stop_price': order_data.get('stop_price'),
            'status': 'PENDING',
            'submitted_at': datetime.utcnow()
        }

        order = order_repo.create(new_order)

        # Log successful order creation
        log_service = LogService(self.db)
        log_service.log_info(
            module="AccountService",
            message=f"Buy order created for account {account_id}",
            details=f"Symbol: {stock_symbol}, Shares: {shares}, Order ID: {order.order_id}"
        )

        return {
            'id': order.id,
            'order_id': order.order_id,
            'account_id': order.account_id,
            'symbol_id': order.symbol_id,
            'strategy_id': order.strategy_id,
            'order_type': order.order_type,
            'side': order.side,
            'quantity': float(order.quantity),
            'status': order.status,
            'submitted_at': order.submitted_at,
            'created_at': order.created_at
        }

    def get_account_portfolio(self, account_id: str) -> Dict[str, Any]:
        """Get account portfolio holdings"""
        account = self.repository.get_by_id(account_id)
        if not account:
            raise ValueError(f"Account with ID {account_id} not found")
        
        holdings = {}
        total_portfolio_value = 0.0
        
        for position in account.positions:
            if position.quantity > 0:  # Only include positions with shares
                symbol = position.instrument.symbol
                current_price = float(position.current_price) if position.current_price else 0.0
                value = float(position.quantity) * current_price
                total_portfolio_value += value
                
                holdings[symbol] = {
                    'company_name': position.instrument.name or symbol,
                    'shares': float(position.quantity),
                    'price': current_price,
                    'value': value,
                    'average_entry_price': float(position.average_entry_price),
                    'unrealized_pnl': float(position.unrealized_pnl) if position.unrealized_pnl else 0.0
                }
        
        # Get last 20 orders for the account
        order_repo = OrderRepository(self.db)
        recent_orders = order_repo.get_by_account_id(account_id, limit=20)
        
        # Format orders for response
        formatted_orders = []
        for order in recent_orders:
            formatted_orders.append({
                'id': order.id,
                'order_id': order.order_id,
                'symbol': order.instrument.symbol,
                'order_type': order.order_type,
                'side': order.side,
                'quantity': float(order.quantity),
                'price': float(order.price) if order.price else None,
                'stop_price': float(order.stop_price) if order.stop_price else None,
                'status': order.status,
                'filled_quantity': float(order.filled_quantity) if order.filled_quantity else 0.0,
                'average_fill_price': float(order.average_fill_price) if order.average_fill_price else None,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at,
                'cancelled_at': order.cancelled_at,
                'created_at': order.created_at
            })
        
        return {
            'account_id': account_id,
            'holdings': holdings,
            'total_portfolio_value': total_portfolio_value,
            'cash_balance': float(account.cash_balance),
            'total_equity': total_portfolio_value + float(account.cash_balance),
            'number_of_holdings': len(holdings),
            'recent_orders': formatted_orders
        }

    def create_sell_order(self, account_id: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a sell order for an account"""
        # Basic payload validation
        if 'stock_symbol' not in order_data or 'shares' not in order_data:
            raise ValueError("Payload must include 'stock_symbol' and 'shares'")

        stock_symbol = str(order_data['stock_symbol']).upper()
        try:
            shares = float(order_data['shares'])
        except Exception:
            raise ValueError("'shares' must be a number")

        if shares <= 0:
            raise ValueError("'shares' must be greater than zero")

        # Validate account exists
        account = self.get_account_by_id(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")

        # Check if account has sufficient position to sell
        instrument_repo = InstrumentRepository(self.db)
        instrument = instrument_repo.get_by_symbol(stock_symbol)
        if not instrument:
            raise ValueError(f"Instrument {stock_symbol} not found")

        # Check if account has position in this instrument
        position = None
        for pos in account.positions:
            if pos.symbol_id == instrument.id:
                position = pos
                break

        if not position:
            raise ValueError(f"Account {account_id} has no position in {stock_symbol}")

        if position.quantity < shares:
            raise ValueError(f"Insufficient shares to sell. Available: {position.quantity}, Requested: {shares}")

        '''    
        # Ensure a default 'manual' strategy exists (used for user-initiated orders)
        strategy = self.db.query(Strategy).filter(Strategy.name == 'manual').first()
        if not strategy:
            strategy = Strategy(name='manual', description='Manual user orders', parameters=None, is_active=True)
            self.db.add(strategy)
            self.db.commit()
            self.db.refresh(strategy)
        '''

        # Build order payload for repository
        order_repo = OrderRepository(self.db)
        new_order = {
            'account_id': account_id,
            'symbol_id': instrument.id,
            'strategy_id': 0,
            'order_id': str(uuid4()),
            'order_type': (order_data.get('order_type') or 'market').upper(),
            'side': 'SELL',
            'quantity': shares,
            'price': order_data.get('price'),
            'stop_price': order_data.get('stop_price'),
            'status': 'PENDING',
            'submitted_at': datetime.utcnow()
        }

        order = order_repo.create(new_order)

        # Log successful order creation
        log_service = LogService(self.db)
        log_service.log_info(
            module="AccountService",
            message=f"Sell order created for account {account_id}",
            details=f"Symbol: {stock_symbol}, Shares: {shares}, Order ID: {order.order_id}"
        )

        return {
            'id': order.id,
            'order_id': order.order_id,
            'account_id': order.account_id,
            'symbol_id': order.symbol_id,
            'strategy_id': order.strategy_id,
            'order_type': order.order_type,
            'side': order.side,
            'quantity': float(order.quantity),
            'status': order.status,
            'submitted_at': order.submitted_at,
            'created_at': order.created_at
        }

    def get_account_performance(self, account_id: str) -> Dict[str, Any]:
        """Get account performance metrics"""
        account = self.repository.get_by_id(account_id)
        if not account:
            raise ValueError(f"Account with ID {account_id} not found")
        
        # Calculate current portfolio metrics
        portfolio_value = 0.0
        total_unrealized_pnl = 0.0
        total_realized_pnl = 0.0
        
        for position in account.positions:
            if position.current_price and position.quantity:
                # Convert decimal values to float before arithmetic operations
                position_value = float(position.quantity) * float(position.current_price)
                portfolio_value += position_value
                total_unrealized_pnl += float(position.unrealized_pnl) if position.unrealized_pnl else 0.0
        
        # Calculate total realized P&L from trades
        for trade in account.trades:
            total_realized_pnl += float(trade.net_pnl) if trade.net_pnl else 0.0
        
        total_equity = float(account.cash_balance) + portfolio_value
        
        # Calculate performance metrics
        initial_balance = float(account.cash_balance)  # For now, use current cash as initial (simplified)
        total_pnl = total_unrealized_pnl + total_realized_pnl
        
        # Calculate percentage returns
        if initial_balance > 0:
            total_return_percentage = (total_pnl / initial_balance) * 100
        else:
            total_return_percentage = 0.0
        
        # Calculate daily performance (simplified - would need historical data for accurate calculation)
        account_age_days = (datetime.utcnow() - account.created_at).days if account.created_at else 1
        daily_return_percentage = total_return_percentage / max(account_age_days, 1)
        
        # Calculate risk metrics (simplified)
        volatility = self._calculate_portfolio_volatility(account_id)
        sharpe_ratio = self._calculate_sharpe_ratio(daily_return_percentage, volatility)
        
        return {
            'account_id': account.account_id,
            'current_equity': total_equity,
            'portfolio_value': portfolio_value,
            'cash_balance': float(account.cash_balance),
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_realized_pnl': total_realized_pnl,
            'total_pnl': total_pnl,
            'total_return_percentage': round(total_return_percentage, 2),
            'daily_return_percentage': round(daily_return_percentage, 2),
            'volatility': round(volatility, 4),
            'sharpe_ratio': round(sharpe_ratio, 4),
            'number_of_positions': len(account.positions),
            'number_of_trades': len(account.trades),
            'account_age_days': account_age_days
        }

    def _calculate_portfolio_volatility(self, account_id: str) -> float:
        """Calculate portfolio volatility (simplified implementation)"""
        # This is a simplified implementation
        # In a real system, you would calculate based on historical returns
        return 0.15  # Placeholder - 15% annual volatility

    def _calculate_sharpe_ratio(self, daily_return: float, volatility: float) -> float:
        """Calculate Sharpe ratio (simplified implementation)"""
        # Assuming risk-free rate of 0% for simplicity
        if volatility == 0:
            return 0.0
        return (daily_return * 252) / (volatility * 16)  # Annualized Sharpe ratio
