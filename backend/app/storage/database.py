import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration - use absolute path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)  # Go up from app/storage to app
project_root = os.path.dirname(backend_dir)  # Go up from app to backend
database_path = os.path.join(project_root, "PaperProfit.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{database_path}")

# Create SQLite engine with appropriate configuration
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    poolclass=StaticPool if DATABASE_URL.startswith("sqlite") else None,
    echo=False  # Set to False to disable SQLAlchemy engine logging
)

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
