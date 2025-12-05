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
                # Split by semicolon and execute each statement
                statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                for statement in statements:
                    if statement:  # Skip empty statements
                        conn.execute(statement)
                conn.commit()
            
            print(f"✓ Migration {sql_file_path} completed successfully")
            return True
            
        except Exception as e:
            print(f"✗ Migration {sql_file_path} failed: {e}")
            return False

def main():
    """Main function to handle command line arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration tool for PaperProfit")
    parser.add_argument("action", choices=["init", "status", "migrate", "sample"], 
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


if __name__ == "__main__":
    main()
