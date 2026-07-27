```python
"""
Database connection and session management for ContractLens.

This module provides SQLAlchemy engine configuration, session management,
and base model setup for the application.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base for model inheritance
Base = declarative_base()

# Database engine configuration
engine_kwargs = {
    "pool_pre_ping": True,  # Verify connections before using them
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_MAX_OVERFLOW,
    "pool_recycle": 3600,  # Recycle connections after 1 hour
    "echo": settings.DB_ECHO,  # Log SQL statements in development
}

# Use NullPool for testing to avoid connection issues
if settings.ENVIRONMENT == "test":
    engine_kwargs["poolclass"] = pool.NullPool
    engine_kwargs.pop("pool_size", None)
    engine_kwargs.pop("max_overflow", None)

# Create the SQLAlchemy engine
try:
    engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
    logger.info(f"Database engine created for {settings.ENVIRONMENT} environment")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise


# Enable SQLite foreign key constraints if using SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints for SQLite connections."""
    if "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Prevent lazy loading issues after commit
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    
    Yields:
        Session: SQLAlchemy database session
        
    Example:
        @app.get("/contracts")
        def get_contracts(db: Session = Depends(get_db)):
            return db.query(Contract).all()
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions outside of FastAPI routes.
    
    Yields:
        Session: SQLAlchemy database session
        
    Example:
        with get_db_context() as db:
            contract = db.query(Contract).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database context error: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in database context: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    This should be called during application startup or in migration scripts.
    In production, use Alembic migrations instead.
    """
    try:
        # Import all models here to ensure they're registered with Base
        from backend.models import (
            Contract,
            RiskAnalysis,
            User,
            Clause,
            Recommendation,
        )
        
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def drop_db() -> None:
    """
    Drop all database tables.
    
    WARNING: This will delete all data. Use only in development/testing.
    """
    if settings.ENVIRONMENT == "production":
        raise RuntimeError("Cannot drop database in production environment")
    
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


def check_db_connection() -> bool:
    """
    Check if the database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection check successful")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


class DatabaseHealthCheck:
    """Health check utility for database monitoring."""
    
    @staticmethod
    def is_healthy() -> dict:
        """
        Perform a comprehensive health check on the database.
        
        Returns:
            dict: Health check results including status and metrics
        """
        health_status = {
            "status": "unhealthy",
            "connection": False,
            "pool_size": 0,
            "pool_overflow": 0,
            "pool_checked_out": 0,
        }
        
        try:
            # Check basic connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            health_status["connection"] = True
            
            # Get pool statistics
            pool_status = engine.pool.status()
            health_status["pool_size"] = engine.pool.size()
            health_status["pool_checked_out"] = engine.pool.checkedout()
            
            health_status["status"] = "healthy"
            logger.debug(f"Database health check: {health_status}")
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status["error"] = str(e)
        
        return health_status


# Utility function for transaction management
def execute_with_retry(
    func,
    max_retries: int = 3,
    retry_delay: float = 0.5
) -> any:
    """
    Execute a database operation with automatic retry on failure.
    
    Args:
        func: Function to execute (should accept db session as first arg)
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Result of the function execution
        
    Raises:
        SQLAlchemyError: If all retry attempts fail
    """
    import time
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            with get_db_context() as db:
                return func(db)
        except SQLAlchemyError as e:
            last_exception = e
            logger.warning(
                f"Database operation failed (attempt {attempt + 1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    logger.error(f"Database operation failed after {max_retries} attempts")
    raise last_exception

```