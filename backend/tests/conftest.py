"""
Pytest fixtures for backend tests.

Provides common test fixtures for database, client, and authentication.
"""

import pytest
from typing import Generator
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.core.security import get_password_hash, create_access_token


# Test database URL (SQLite in-memory)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Test session factory
TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Create a fresh database for each test.

    Yields:
        Session: Test database session.
    """
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with database override.

    Args:
        db: Test database session.

    Yields:
        TestClient: FastAPI test client.
    """

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db: Session) -> User:
    """
    Create a test user.

    Args:
        db: Test database session.

    Returns:
        User: The created test user.
    """
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> dict:
    """
    Create authentication headers for test user.

    Args:
        test_user: The test user.

    Returns:
        dict: Authorization headers with JWT token.
    """
    token = create_access_token(subject=test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_storage_service():
    """Mock the storage service for upload tests."""
    with patch("app.api.v1.endpoints.uploads.storage_service") as mock:
        mock.generate_file_key.return_value = "uploads/1/test_file.pdf"
        mock.upload_file.return_value = "uploads/1/test_file.pdf"
        yield mock


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for upload tests."""
    with patch("app.api.v1.endpoints.uploads.parse_document_task") as mock:
        mock.delay.return_value = MagicMock(id="test-task-id")
        yield mock

