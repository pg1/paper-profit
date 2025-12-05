#!/usr/bin/env python3
"""
Main entry point for the PaperProfit application.
Handles command-line interface and application startup.
"""

import sys
import os
import argparse
from pathlib import Path

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def run_migration():
    """Run the database migration script"""
    try:
        # Import and run the migration script
        from storage.migrate import main as migrate_main
        
        # Create a mock sys.argv for the migration script
        original_argv = sys.argv.copy()
        
        # Set up arguments for the migration script
        # Default to 'init' action if no specific migration action provided
        sys.argv = ['migrate.py', 'init']
        
        # Run the migration
        migrate_main()
        
        # Restore original argv
        sys.argv = original_argv
        
        print("✓ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False


def start_api():
    """Start the FastAPI server"""
    try:
        print("Starting FastAPI server...")
        print("Server will be available at: http://localhost:5000")
        print("API documentation: http://localhost:5000/docs")
        print("Press Ctrl+C to stop the server")
        
        # Import and run the API directly
        import uvicorn
        uvicorn.run("api:app", host="0.0.0.0", port=5000, reload=False)
        
        return True
        
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        return True
    except Exception as e:
        print(f"✗ Failed to start API server: {e}")
        return False


def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description="PaperProfit Trading System")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Run database migrations')
    migrate_parser.add_argument('--action', choices=['init', 'status', 'migrate', 'sample'], 
                               default='init', help='Migration action to perform')
    migrate_parser.add_argument('--sql-file', help='Path to SQL migration file (for migrate action)')
    
    # API command
    api_parser = subparsers.add_parser('api', help='Start the FastAPI server')
    api_parser.add_argument('--host', default='0.0.0.0', help='Host to bind the server to')
    api_parser.add_argument('--port', type=int, default=5000, help='Port to bind the server to')
    
    args = parser.parse_args()
    
    if args.command == 'migrate':
        if run_migration():
            return 0
        else:
            return 1
    elif args.command == 'api':
        if start_api():
            return 0
        else:
            return 1
    else:
        # If no command provided, show help
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
