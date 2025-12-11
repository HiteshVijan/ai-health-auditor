"""
Database session configuration.

Provides SQLAlchemy engine and session factory for database operations.
Supports both PostgreSQL and SQLite for local development.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings

# Get database URL - prefer environment variable, then check for SQLite option
DATABASE_URL = os.environ.get("DATABASE_URL", settings.DATABASE_URL)

# If PostgreSQL isn't available and we're in debug mode, use SQLite
if "postgresql" in DATABASE_URL and settings.DEBUG:
    # Check if we should use SQLite for local dev
    sqlite_path = Path(__file__).parent.parent.parent.parent / "data" / "local_dev.db"
    if sqlite_path.exists() or os.environ.get("USE_SQLITE", "").lower() in ("1", "true", "yes"):
        DATABASE_URL = f"sqlite:///{sqlite_path}"

# Create SQLAlchemy engine with appropriate settings
if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific settings
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Needed for SQLite
    )
else:
    # PostgreSQL settings
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Yields a database session and ensures it's closed after use.

    Yields:
        Session: SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

