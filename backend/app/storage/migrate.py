#!/usr/bin/env python3
"""
Database migration script for the PaperProfit database.
This script handles database initialization and schema migrations.
"""

import os
import sys
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .database import init_db, get_engine
from .models import Base
from .repositories import RepositoryFactory, SystemLogRepository


class DatabaseMigrator:
    """Handles database migration operations"""
    
    def __init__(self, db_path: str = "../PaperProfit.db"):
        self.db_path = db_path
        self.engine = get_engine()
    
    def initialize_database(self):
        """Initialize the database with all tables"""
        print("Initializing database...")
        
        try:
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            print("✓ Database tables created successfully")
            
            # Log the initialization using proper session
            from .database import get_session
            session = get_session()
            try:
                repo_factory = RepositoryFactory(session)
                repo_factory.system_logs.log_info(
                    "DatabaseMigrator", 
                    "Database initialized with all tables"
                )
            finally:
                session.close()
            
            print("✓ Database initialization completed")
            return True
            
        except Exception as e:
            print(f"✗ Database initialization failed: {e}")
            return False
    
    def check_database_status(self):
        """Check the current status of the database"""
        print("Checking database status...")
        
        try:
            # Check if database file exists
            if not os.path.exists(self.db_path):
                print("✗ Database file does not exist")
                return False
            
            # Check if all tables exist
            with self.engine.connect() as conn:
                inspector = self.engine.dialect.inspector(conn)
                existing_tables = inspector.get_table_names()
                
                required_tables = [
                    'symbols', 'market_data', 'technical_indicators', 
                    'strategies', 'trading_signals', 'orders', 
                    'positions', 'trades', 'account_summary', 
                    'news_sentiment', 'system_logs'
                ]
                
                missing_tables = [table for table in required_tables if table not in existing_tables]
                
                if missing_tables:
                    print(f"✗ Missing tables: {', '.join(missing_tables)}")
                    return False
                else:
                    print("✓ All required tables exist")
                    return True
                    
        except Exception as e:
            print(f"✗ Database status check failed: {e}")
            return False
    
    def run_migration_sql(self, sql_file_path: str):
        """Run a SQL migration file"""
        print(f"Running migration: {sql_file_path}")
        
        try:
            # Read the SQL file
            with open(sql_file_path, 'r') as f:
                sql_content = f.read()
            
            # Execute the SQL
            with self.engine.connect() as conn:
                # Parse SQL content, handling comments and empty lines
                statements = []
                current_statement = []
                
                for line in sql_content.split('\n'):
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Remove inline comments (everything after --)
                    if '--' in line:
                        line = line.split('--')[0].strip()
                        # If the line is empty after removing comment, skip it
                        if not line:
                            continue
                    
                    # Skip lines that are only comments
                    if line.startswith('--'):
                        continue
                    
                    # Add line to current statement
                    current_statement.append(line)
                    
                    # If line ends with semicolon, complete the statement
                    if line.endswith(';'):
                        # Remove the semicolon from the line
                        line_without_semicolon = line[:-1].strip()
                        if line_without_semicolon:
                            current_statement[-1] = line_without_semicolon
                        
                        statement = ' '.join(current_statement)
                        if statement.strip():
                            statements.append(statement)
                        current_statement = []
                
                # Handle any remaining statement without trailing semicolon
                if current_statement:
                    statement = ' '.join(current_statement)
                    if statement.strip():
                        statements.append(statement)
                
                # Execute each statement with idempotency checks
                for statement in statements:
                    if statement.strip():
                        # Check if we should skip this statement due to existing schema
                        if self._should_skip_statement(conn, statement):
                            print(f"  Skipping (already applied): {statement[:100]}...")
                            continue
                        
                        # Use text() for SQLAlchemy compatibility
                        from sqlalchemy import text
                        conn.execute(text(statement))
                
                conn.commit()
            
            print(f"✓ Migration {sql_file_path} completed successfully")
            return True
            
        except Exception as e:
            print(f"✗ Migration {sql_file_path} failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _should_skip_statement(self, conn, statement: str) -> bool:
        """Check if a SQL statement should be skipped because it would fail due to existing schema."""
        statement_upper = statement.upper()
        
        # Check for CREATE TABLE IF NOT EXISTS - these are already idempotent
        if "CREATE TABLE IF NOT EXISTS" in statement_upper:
            return False
        
        # Check for CREATE INDEX IF NOT EXISTS - these are already idempotent
        if "CREATE INDEX IF NOT EXISTS" in statement_upper:
            return False
        
        # Check for ALTER TABLE ADD COLUMN - need to check if column already exists
        if "ALTER TABLE" in statement_upper and "ADD COLUMN" in statement_upper:
            # Parse table name and column name from statement
            # Example: ALTER TABLE instruments ADD COLUMN watch_list INTEGER;
            try:
                # Simple parsing - this could be improved for complex cases
                parts = statement.split()
                table_index = parts.index("TABLE") + 1
                table_name = parts[table_index]
                
                add_column_index = statement_upper.find("ADD COLUMN")
                if add_column_index != -1:
                    # Get everything after "ADD COLUMN"
                    after_add = statement[add_column_index + len("ADD COLUMN"):].strip()
                    # First word is column name
                    column_name = after_add.split()[0].strip()
                    
                    # Check if column already exists in table
                    from sqlalchemy import text
                    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                    columns = [row[1] for row in result.fetchall()]
                    
                    if column_name in columns:
                        return True  # Skip, column already exists
            except (ValueError, IndexError) as e:
                # If parsing fails, just execute the statement and let it fail if needed
                print(f"  Warning: Could not parse ALTER TABLE statement: {e}")
                return False
        
        # Check for CREATE TABLE without IF NOT EXISTS - check if table exists
        if "CREATE TABLE" in statement_upper and "IF NOT EXISTS" not in statement_upper:
            # Parse table name from statement
            # Example: CREATE TABLE instruments (...)
            try:
                parts = statement.split()
                table_index = parts.index("TABLE") + 1
                table_name = parts[table_index]
                
                # Check if table exists
                from sqlalchemy import text
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
                ), {"table_name": table_name})
                
                if result.fetchone():
                    return True  # Skip, table already exists
            except (ValueError, IndexError) as e:
                # If parsing fails, just execute the statement
                print(f"  Warning: Could not parse CREATE TABLE statement: {e}")
                return False
        
        return False
    
    def run_all_migrations(self, migration_dir: str = None):
        """Run all migration files in the migration directory in order"""
        if migration_dir is None:
            # Default to the migration directory relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            migration_dir = os.path.join(current_dir, "migration")
        
        print(f"Running all migrations from: {migration_dir}")
        
        # Check if migration directory exists
        if not os.path.exists(migration_dir):
            print(f"✗ Migration directory not found: {migration_dir}")
            return False
        
        # Get all SQL files in the migration directory
        migration_files = []
        for file in os.listdir(migration_dir):
            if file.endswith('.sql'):
                migration_files.append(file)
        
        # Sort files by name (001_, 002_, etc.)
        migration_files.sort()
        
        if not migration_files:
            print("✗ No migration files found")
            return False
        
        print(f"Found {len(migration_files)} migration files: {', '.join(migration_files)}")
        
        # Run each migration file in order
        success_count = 0
        for migration_file in migration_files:
            migration_path = os.path.join(migration_dir, migration_file)
            if self.run_migration_sql(migration_path):
                success_count += 1
            else:
                print(f"✗ Failed to run migration: {migration_file}")
                return False
        
        print(f"✓ Successfully ran {success_count}/{len(migration_files)} migrations")
        return True

def main():
    """Main function to handle command line arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration tool for PaperProfit")
    parser.add_argument("action", choices=["init", "status", "migrate", "migrate-all", "sample"], 
                       help="Action to perform")
    parser.add_argument("--sql-file", help="Path to SQL migration file (for migrate action)")
    
    args = parser.parse_args()
    
    migrator = DatabaseMigrator()
    
    if args.action == "init":
        success = migrator.initialize_database()
        if success:
            print("\nDatabase initialized successfully!")
        else:
            print("\nDatabase initialization failed!")
            sys.exit(1)
    
    elif args.action == "status":
        success = migrator.check_database_status()
        if success:
            print("\nDatabase status: OK")
        else:
            print("\nDatabase status: Issues detected")
            sys.exit(1)
    
    elif args.action == "migrate":
        if not args.sql_file:
            print("Error: --sql-file parameter is required for migrate action")
            sys.exit(1)
        
        if not os.path.exists(args.sql_file):
            print(f"Error: SQL file not found: {args.sql_file}")
            sys.exit(1)
        
        success = migrator.run_migration_sql(args.sql_file)
        if success:
            print("\nMigration completed successfully!")
        else:
            print("\nMigration failed!")
            sys.exit(1)
    
    elif args.action == "migrate-all":
        success = migrator.run_all_migrations()
        if success:
            print("\nAll migrations completed successfully!")
        else:
            print("\nMigration failed!")
            sys.exit(1)


if __name__ == "__main__":
    main()
