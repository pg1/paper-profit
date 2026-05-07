import os
import time
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Database configuration - use absolute path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)  # Go up from app/storage to app
project_root = os.path.dirname(backend_dir)  # Go up from app to backend
database_path = os.path.join(project_root, "PaperProfit.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{database_path}")

# SQLite timeout in seconds - how long to wait before giving up on a locked database
SQLITE_TIMEOUT = 30

# Create SQLite engine with appropriate configuration
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": SQLITE_TIMEOUT} if DATABASE_URL.startswith("sqlite") else {},
    poolclass=StaticPool if DATABASE_URL.startswith("sqlite") else None,
    echo=False  # Set to False to disable SQLAlchemy engine logging
)


# Enable WAL mode for SQLite to allow concurrent reads and writes
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better concurrent access"""
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        # WAL mode allows concurrent reads while writing
        cursor.execute("PRAGMA journal_mode=WAL")
        # Busy timeout - how long to wait before raising "database is locked"
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_TIMEOUT * 1000}")
        # Synchronous mode set to NORMAL for better performance with WAL
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database
def init_db():
    """Initialize database by creating all tables"""
    Base.metadata.create_all(bind=engine)


# Database utilities
def get_engine():
    """Get database engine instance"""
    return engine


def get_session():
    """Get database session instance"""
    return SessionLocal()


def retry_on_lock(max_retries=5, delay=1.0, backoff=2.0):
    """Decorator that retries a function when a database lock error occurs.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay in seconds between retries
        backoff: Multiplier for delay after each retry
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()
                    
                    # Check if this is a database lock error
                    is_lock_error = (
                        "database is locked" in error_str or
                        "database is locked" in str(getattr(e, 'orig', '')) or
                        "locked" in error_str or
                        "rolled back" in error_str
                    )
                    
                    if is_lock_error and attempt < max_retries:
                        logger.warning(
                            f"Database lock detected (attempt {attempt + 1}/{max_retries + 1}), "
                            f"retrying in {current_delay:.1f}s... Error: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        # Not a lock error or out of retries, re-raise
                        raise
            
            raise last_exception
        
        return wrapper
    return decorator

