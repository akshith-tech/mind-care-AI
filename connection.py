"""
database/connection.py
======================
Handles database engine creation, table initialization, and session 
lifecycle management for MindCare AI using SQLAlchemy and SQLite.
"""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base

# Database File and URL Configuration
DB_FILENAME = os.getenv("DB_FILENAME", "mindcare_wellness.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_FILENAME}")

# Engine Setup
# connect_args={"check_same_thread": False} is required for SQLite when running in Streamlit's multi-threaded environment.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,  # Set to True to output raw SQL queries to console for debugging
)

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initializes the database by creating all tables mapped in models.py."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency generator to yield a database session and guarantee closure.
    
    Usage:
        db = next(get_db())
        try:
            # db operations
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for handling transactions safely with auto-commit/rollback.
    
    Usage:
        with get_db_session() as db:
            user = db.query(User).filter_by(id=1).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()