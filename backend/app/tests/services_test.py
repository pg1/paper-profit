#!/usr/bin/env python3
"""
Test file for all services in the services directory.
Run with: python services.py
"""

import sys
import os
import unittest
from unittest.mock import Mock

# Add the parent directories to the path so we can import the services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import services
from app.services.account_service import AccountService
from app.services.position_service import PositionService
from app.services.instrument_service import InstrumentService
from app.services.log_service import LogService
from app.storage.models import Account, Instrument, Position, SystemLog


class TestAccountService(unittest.TestCase):
    """Test cases for AccountService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.mock_repository = Mock()
        
        # Patch the repository to use our mock
        with unittest.mock.patch('app.services.account_service.AccountRepository', return_value=self.mock_repository):
            self.account_service = AccountService(self.mock_db)
        
        # Mock account data
        self.test_account_data = {
            'account_id': 'test_account_123',
            'cash_balance': 10000.00
        }
        
        self.test_account = Mock(spec=Account)
        self.test_account.account_id = 'test_account_123'
        self.test_account.cash_balance = 10000.00
        self.test_account.positions = []
    
    def test_get_all_accounts(self):
        """Test getting all accounts"""
        self.account_service.repository.get_all.return_value = [self.test_account]
        accounts = self.account_service.get_all_accounts()
        
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].account_id, 'test_account_123')
        self.account_service.repository.get_all.assert_called_once()
    
    def test_get_account_by_id(self):
        """Test getting account by ID"""
        self.account_service.repository.get_by_id.return_value = self.test_account
        account = self.account_service.get_account_by_id('test_account_123')
        
        self.assertEqual(account.account_id, 'test_account_123')
        self.account_service.repository.get_by_id.assert_called_once_with('test_account_123')
    
    def test_create_account_valid_data(self):
        """Test creating account with valid data"""
        self.account_service.repository.get_by_id.return_value = None
        self.account_service.repository.create.return_value = self.test_account
        
        account = self.account_service.create_account(self.test_account_data)
        
        self.assertEqual(account.account_id, 'test_account_123')
        self.account_service.repository.create.assert_called_once_with(self.test_account_data)
    
    def test_create_account_missing_required_fields(self):
        """Test creating account with missing required fields"""
        invalid_data = {'account_id': 'test_account_123'}  # Missing cash_balance
        
        with self.assertRaises(ValueError) as context:
            self.account_service.create_account(invalid_data)
        
        self.assertIn("Missing required field: cash_balance", str(context.exception))
    
    def test_create_account_negative_balance(self):
        """Test creating account with negative cash balance"""
        invalid_data = {
            'account_id': 'test_account_123',
            'cash_balance': -100.00
        }
        
        with self.assertRaises(ValueError) as context:
            self.account_service.create_account(invalid_data)
        
        self.assertIn("Cash balance cannot be negative", str(context.exception))
    
    def test_create_account_already_exists(self):
        """Test creating account that already exists"""
        self.account_service.repository.get_by_id.return_value = self.test_account
        
        with self.assertRaises(ValueError) as context:
            self.account_service.create_account(self.test_account_data)
        
        self.assertIn("Account with ID test_account_123 already exists", str(context.exception))
    
    def test_update_cash_balance_valid(self):
        """Test updating cash balance with valid amount"""
        self.account_service.repository.update_cash_balance.return_value = self.test_account
        
        account = self.account_service.update_cash_balance('test_account_123', 15000.00)
        
        self.assertEqual(account.account_id, 'test_account_123')
        self.account_service.repository.update_cash_balance.assert_called_once_with('test_account_123', 15000.00)
    
    def test_update_cash_balance_negative(self):
        """Test updating cash balance with negative amount"""
        with self.assertRaises(ValueError) as context:
            self.account_service.update_cash_balance('test_account_123', -100.00)
        
        self.assertIn("Cash balance cannot be negative", str(context.exception))
    
    def test_get_account_summary(self):
        """Test getting account summary"""
        self.account_service.repository.get_by_id.return_value = self.test_account
        
        summary = self.account_service.get_account_summary('test_account_123')
        
        self.assertEqual(summary['account_id'], 'test_account_123')
        self.assertEqual(summary['cash_balance'], 10000.00)
        self.assertEqual(summary['portfolio_value'], 0.0)
        self.assertEqual(summary['total_equity'], 10000.00)
        self.assertEqual(summary['number_of_positions'], 0)
    
    def test_validate_account_exists(self):
        """Test validating account existence"""
        self.account_service.repository.get_by_id.return_value = self.test_account
        exists = self.account_service.validate_account_exists('test_account_123')
        
        self.assertTrue(exists)
        self.account_service.repository.get_by_id.assert_called_once_with('test_account_123')
    
    def test_validate_account_not_exists(self):
        """Test validating account non-existence"""
        self.account_service.repository.get_by_id.return_value = None
        exists = self.account_service.validate_account_exists('non_existent_account')
        
        self.assertFalse(exists)


class TestPositionService(unittest.TestCase):
    """Test cases for PositionService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.mock_repository = Mock()
        
        # Patch the repository to use our mock
        with unittest.mock.patch('app.services.position_service.PositionRepository', return_value=self.mock_repository):
            self.position_service = PositionService(self.mock_db)
        
        # Mock position data
        self.test_position = Mock(spec=Position)
        self.test_position.id = 1
        self.test_position.symbol_id = 1
        self.test_position.account_id = 'test_account_123'
        self.test_position.quantity = 100.0
        self.test_position.average_entry_price = 150.00
        self.test_position.current_price = 160.00
        self.test_position.unrealized_pnl = 1000.00
    
    def test_get_all_positions(self):
        """Test getting all positions"""
        self.position_service.repository.get_all.return_value = [self.test_position]
        positions = self.position_service.get_all_positions()
        
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].symbol_id, 1)
        self.position_service.repository.get_all.assert_called_once()
    
    def test_get_position_by_symbol(self):
        """Test getting position by symbol ID"""
        self.position_service.repository.get_by_symbol.return_value = self.test_position
        position = self.position_service.get_position_by_symbol(1)
        
        self.assertEqual(position.symbol_id, 1)
        self.position_service.repository.get_by_symbol.assert_called_once_with(1)
    
    def test_get_positions_by_account(self):
        """Test getting positions by account ID"""
        self.position_service.repository.get_all.return_value = [self.test_position]
        positions = self.position_service.get_positions_by_account('test_account_123')
        
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].account_id, 'test_account_123')
    
    def test_update_position_valid(self):
        """Test updating position with valid data"""
        self.position_service.repository.update_position.return_value = self.test_position
        
        position = self.position_service.update_position(
            symbol_id=1, 
            quantity=150.0, 
            average_entry_price=155.00,
            account_id='test_account_123'
        )
        
        self.assertEqual(position.symbol_id, 1)
        self.position_service.repository.update_position.assert_called_once_with(1, 150.0, 155.00)
    
    def test_update_position_negative_quantity(self):
        """Test updating position with negative quantity"""
        with self.assertRaises(ValueError) as context:
            self.position_service.update_position(
                symbol_id=1, 
                quantity=-50.0, 
                average_entry_price=155.00,
                account_id='test_account_123'
            )
        
        self.assertIn("Position quantity cannot be negative", str(context.exception))
    
    def test_update_position_invalid_price(self):
        """Test updating position with invalid average entry price"""
        with self.assertRaises(ValueError) as context:
            self.position_service.update_position(
                symbol_id=1, 
                quantity=150.0, 
                average_entry_price=0.00,
                account_id='test_account_123'
            )
        
        self.assertIn("Average entry price must be positive", str(context.exception))
    
    def test_calculate_position_value(self):
        """Test calculating position value and P&L"""
        position_value = self.position_service.calculate_position_value(self.test_position)
        
        self.assertEqual(position_value['symbol_id'], 1)
        self.assertEqual(position_value['quantity'], 100.0)
        self.assertEqual(position_value['average_entry_price'], 150.00)
        self.assertEqual(position_value['current_price'], 160.00)
        self.assertEqual(position_value['market_value'], 16000.00)
        self.assertEqual(position_value['cost_basis'], 15000.00)
        self.assertEqual(position_value['unrealized_pnl'], 1000.00)
    
    def test_get_portfolio_summary(self):
        """Test getting portfolio summary"""
        self.position_service.repository.get_all.return_value = [self.test_position]
        
        summary = self.position_service.get_portfolio_summary('test_account_123')
        
        self.assertEqual(summary['account_id'], 'test_account_123')
        self.assertEqual(summary['number_of_positions'], 1)
        self.assertEqual(summary['total_market_value'], 16000.00)
        self.assertEqual(summary['total_cost_basis'], 15000.00)
        self.assertEqual(summary['total_unrealized_pnl'], 1000.00)
    
    def test_validate_position_exists(self):
        """Test validating position existence"""
        self.position_service.repository.get_by_symbol.return_value = self.test_position
        exists = self.position_service.validate_position_exists(1, 'test_account_123')
        
        self.assertTrue(exists)
    
    def test_validate_position_not_exists(self):
        """Test validating position non-existence"""
        self.position_service.repository.get_by_symbol.return_value = None
        exists = self.position_service.validate_position_exists(999, 'test_account_123')
        
        self.assertFalse(exists)


class TestInstrumentService(unittest.TestCase):
    """Test cases for InstrumentService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.mock_repository = Mock()
        
        # Patch the repository to use our mock
        with unittest.mock.patch('app.services.instrument_service.InstrumentRepository', return_value=self.mock_repository):
            self.instrument_service = InstrumentService(self.mock_db)
        
        # Mock instrument data
        self.test_instrument = Mock(spec=Instrument)
        self.test_instrument.id = 1
        self.test_instrument.symbol = 'AAPL'
        self.test_instrument.name = 'Apple Inc.'
        self.test_instrument.exchange = 'NASDAQ'
        self.test_instrument.currency = 'USD'
        self.test_instrument.is_active = True
        self.test_instrument.market_data = []
        self.test_instrument.technical_indicators = []
    
    def test_get_all_instruments(self):
        """Test getting all instruments"""
        self.instrument_service.repository.get_all.return_value = [self.test_instrument]
        instruments = self.instrument_service.get_all_instruments()
        
        self.assertEqual(len(instruments), 1)
        self.assertEqual(instruments[0].symbol, 'AAPL')
        self.instrument_service.repository.get_all.assert_called_once_with(True)
    
    def test_get_instrument_by_id(self):
        """Test getting instrument by ID"""
        self.instrument_service.repository.get_by_id.return_value = self.test_instrument
        instrument = self.instrument_service.get_instrument_by_id(1)
        
        self.assertEqual(instrument.symbol, 'AAPL')
        self.instrument_service.repository.get_by_id.assert_called_once_with(1)
    
    def test_get_instrument_by_symbol(self):
        """Test getting instrument by symbol string"""
        self.instrument_service.repository.get_by_symbol.return_value = self.test_instrument
        instrument = self.instrument_service.get_instrument_by_symbol('AAPL')
        
        self.assertEqual(instrument.symbol, 'AAPL')
        self.instrument_service.repository.get_by_symbol.assert_called_once_with('AAPL')
    
    def test_create_instrument_valid(self):
        """Test creating instrument with valid data"""
        self.instrument_service.repository.get_by_symbol.return_value = None
        self.instrument_service.repository.create.return_value = self.test_instrument
        
        instrument_data = {
            'symbol': 'AAPL',
            'name': 'Apple Inc.',
            'exchange': 'NASDAQ'
        }
        
        instrument = self.instrument_service.create_instrument(instrument_data)
        
        self.assertEqual(instrument.symbol, 'AAPL')
        self.instrument_service.repository.create.assert_called_once_with(instrument_data)
    
    def test_create_instrument_missing_symbol(self):
        """Test creating instrument with missing symbol"""
        invalid_data = {'name': 'Apple Inc.'}
        
        with self.assertRaises(ValueError) as context:
            self.instrument_service.create_instrument(invalid_data)
        
        self.assertIn("Missing required field: symbol", str(context.exception))
    
    def test_create_instrument_invalid_symbol(self):
        """Test creating instrument with invalid symbol"""
        invalid_data = {'symbol': ''}
        
        with self.assertRaises(ValueError) as context:
            self.instrument_service.create_instrument(invalid_data)
        
        self.assertIn("Symbol must be a non-empty string", str(context.exception))
    
    def test_create_instrument_already_exists(self):
        """Test creating instrument that already exists"""
        self.instrument_service.repository.get_by_symbol.return_value = self.test_instrument
        
        instrument_data = {'symbol': 'AAPL'}
        
        with self.assertRaises(ValueError) as context:
            self.instrument_service.create_instrument(instrument_data)
        
        self.assertIn("Instrument with symbol AAPL already exists", str(context.exception))
    
    def test_search_instruments(self):
        """Test searching instruments"""
        self.instrument_service.repository.get_all.return_value = [self.test_instrument]
        
        results = self.instrument_service.search_instruments('apple')
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].symbol, 'AAPL')
    
    def test_validate_instrument_exists(self):
        """Test validating instrument existence"""
        self.instrument_service.repository.get_by_id.return_value = self.test_instrument
        exists = self.instrument_service.validate_instrument_exists(1)
        
        self.assertTrue(exists)
    
    def test_validate_instrument_active(self):
        """Test validating instrument is active"""
        self.instrument_service.repository.get_by_id.return_value = self.test_instrument
        is_active = self.instrument_service.validate_instrument_active(1)
        
        self.assertTrue(is_active)
    
    def test_get_instrument_details(self):
        """Test getting instrument details"""
        self.instrument_service.repository.get_by_id.return_value = self.test_instrument
        
        details = self.instrument_service.get_instrument_details(1)
        
        self.assertEqual(details['id'], 1)
        self.assertEqual(details['symbol'], 'AAPL')
        self.assertEqual(details['name'], 'Apple Inc.')
        self.assertEqual(details['exchange'], 'NASDAQ')
        self.assertEqual(details['is_active'], True)


class TestLogService(unittest.TestCase):
    """Test cases for LogService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = Mock()
        self.mock_repository = Mock()
        
        # Patch the repository to use our mock
        with unittest.mock.patch('app.services.log_service.SystemLogRepository', return_value=self.mock_repository):
            self.log_service = LogService(self.mock_db)
        
        # Mock log data
        self.test_log = Mock(spec=SystemLog)
        self.test_log.id = 1
        self.test_log.level = 'INFO'
        self.test_log.module = 'test_module'
        self.test_log.message = 'Test message'
        self.test_log.details = 'Test details'
        self.test_log.timestamp = Mock()
    
    def test_log_info(self):
        """Test logging info message"""
        self.log_service.repository.log_info.return_value = None
        
        self.log_service.log_info('test_module', 'Test info message', 'Test details')
        
        self.log_service.repository.log_info.assert_called_once_with('test_module', 'Test info message', 'Test details')
    
    def test_log_warning(self):
        """Test logging warning message"""
        self.log_service.repository.log_warning.return_value = None
        
        self.log_service.log_warning('test_module', 'Test warning message', 'Test details')
        
        self.log_service.repository.log_warning.assert_called_once_with('test_module', 'Test warning message', 'Test details')
    
    def test_log_error(self):
        """Test logging error message"""
        self.log_service.repository.log_error.return_value = None
        
        self.log_service.log_error('test_module', 'Test error message', 'Test details')
        
        self.log_service.repository.log_error.assert_called_once_with('test_module', 'Test error message', 'Test details')
    
    def test_log_debug(self):
        """Test logging debug message"""
        # Mock the internal _log method
        with unittest.mock.patch.object(self.log_service, '_log') as mock_log:
            self.log_service.log_debug('test_module', 'Test debug message', 'Test details')
            
            mock_log.assert_called_once_with('DEBUG', 'test_module', 'Test debug message', 'Test details')
    
    def test_log_custom_valid_level(self):
        """Test logging custom level message with valid level"""
        # Mock the internal _log method
        with unittest.mock.patch.object(self.log_service, '_log') as mock_log:
            self.log_service.log_custom('INFO', 'test_module', 'Test custom message', 'Test details')
            
            mock_log.assert_called_once_with('INFO', 'test_module', 'Test custom message', 'Test details')
    
    def test_log_custom_invalid_level(self):
        """Test logging custom level message with invalid level"""
        with self.assertRaises(ValueError) as context:
            self.log_service.log_custom('INVALID', 'test_module', 'Test message')
        
        self.assertIn("Invalid log level: INVALID", str(context.exception))
    
    def test_get_logs_with_level_filter(self):
        """Test getting logs with level filter"""
        mock_query = Mock()
        self.log_service.repository.db.query.return_value = mock_query
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [self.test_log]
        
        logs = self.log_service.get_logs(level='INFO')
        
        self.assertEqual(len(logs), 1)
        mock_query.filter.assert_called_once()
    
    def test_get_logs_with_module_filter(self):
        """Test getting logs with module filter"""
        mock_query = Mock()
        self.log_service.repository.db.query.return_value = mock_query
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [self.test_log]
        
        logs = self.log_service.get_logs(module='test_module')
        
        self.assertEqual(len(logs), 1)
        mock_query.filter.assert_called_once()
    
    def test_get_logs_by_time_range(self):
        """Test getting logs by time range"""
        mock_query = Mock()
        self.log_service.repository.db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [self.test_log]
        
        logs = self.log_service.get_logs_by_time_range('2023-01-01', '2023-12-31', level='INFO', module='test_module')
        
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].level, 'INFO')
    
    def test_get_error_logs(self):
        """Test getting error logs"""
        with unittest.mock.patch.object(self.log_service, 'get_logs') as mock_get_logs:
            mock_get_logs.return_value = [self.test_log]
            
            error_logs = self.log_service.get_error_logs(limit=25)
            
            mock_get_logs.assert_called_once_with(level='ERROR', limit=25)
            self.assertEqual(len(error_logs), 1)
    
    def test_get_warning_logs(self):
        """Test getting warning logs"""
        with unittest.mock.patch.object(self.log_service, 'get_logs') as mock_get_logs:
            mock_get_logs.return_value = [self.test_log]
            
            warning_logs = self.log_service.get_warning_logs(limit=25)
            
            mock_get_logs.assert_called_once_with(level='WARNING', limit=25)
            self.assertEqual(len(warning_logs), 1)
    
    def test_get_log_by_id(self):
        """Test getting log by ID"""
        self.log_service.repository.db.query.return_value.filter.return_value.first.return_value = self.test_log
        
        log = self.log_service.get_log_by_id(1)
        
        self.assertEqual(log.id, 1)
        self.assertEqual(log.level, 'INFO')
    
    def test_get_log_summary(self):
        """Test getting log summary"""
        # Mock the query counts
        mock_total_query = Mock()
        mock_total_query.count.return_value = 100
        
        mock_level_query = Mock()
        mock_level_query.filter.return_value.count.return_value = 25
        
        self.log_service.repository.db.query.return_value = mock_total_query
        mock_total_query.filter.return_value.count.return_value = 25
        
        # Mock recent logs
        with unittest.mock.patch.object(self.log_service, 'get_logs') as mock_get_logs:
            mock_get_logs.return_value = [self.test_log]
            
            summary = self.log_service.get_log_summary()
            
            self.assertEqual(summary['total_logs'], 100)
            self.assertIn('level_counts', summary)
            self.assertIn('recent_activity', summary)
            self.assertEqual(len(summary['recent_activity']), 1)
    
    def test_clear_old_logs_valid(self):
        """Test clearing old logs with valid days"""
        mock_result = Mock()
        mock_result.rowcount = 10
        self.log_service.repository.db.execute.return_value = mock_result
        
        deleted_count = self.log_service.clear_old_logs(days=30)
        
        self.assertEqual(deleted_count, 10)
        self.log_service.repository.db.commit.assert_called_once()
    
    def test_clear_old_logs_invalid_days(self):
        """Test clearing old logs with invalid days"""
        with self.assertRaises(ValueError) as context:
            self.log_service.clear_old_logs(days=0)
        
        self.assertIn("Days must be a positive integer", str(context.exception))
    
    def test_clear_old_logs_negative_days(self):
        """Test clearing old logs with negative days"""
        with self.assertRaises(ValueError) as context:
            self.log_service.clear_old_logs(days=-5)
        
        self.assertIn("Days must be a positive integer", str(context.exception))


def run_all_tests():
    """Run all test cases"""
    # Create test suite using TestLoader
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add test cases from all test classes
    test_suite.addTest(loader.loadTestsFromTestCase(TestAccountService))
    test_suite.addTest(loader.loadTestsFromTestCase(TestPositionService))
    test_suite.addTest(loader.loadTestsFromTestCase(TestInstrumentService))
    test_suite.addTest(loader.loadTestsFromTestCase(TestLogService))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return success/failure
    return result.wasSuccessful()


if __name__ == '__main__':
    print("Running all service tests...")
    print("=" * 50)
    
    success = run_all_tests()
    
    print("=" * 50)
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)
