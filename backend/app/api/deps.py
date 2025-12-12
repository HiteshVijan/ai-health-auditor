"""
API dependencies for dependency injection.

Provides common dependencies like database sessions and authentication.
Simplified for local SQLite development.
"""

from typing import Generator, Annotated, Optional

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.core.security import verify_token
from app.core.exceptions import CredentialsException

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user_id(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> int:
    """
    Get the current user ID from JWT token.
    Simplified version that works with SQLite.
    """
    user_id = verify_token(token)
    if user_id is None:
        raise CredentialsException()

    # Verify user exists
    result = db.execute(
        text("SELECT id, is_active FROM users WHERE id = :user_id"),
        {"user_id": int(user_id)}
    ).fetchone()
    
    if result is None:
        raise CredentialsException("User not found")
    
    if not result[1]:  # is_active
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    
    return int(user_id)


# Import User model only if needed (avoid circular imports with SQLite mode)
try:
    from app.models.user import User
except ImportError:
    User = None


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        db: Database session.
        token: JWT access token from Authorization header.

    Returns:
        User: The authenticated user.

    Raises:
        CredentialsException: If token is invalid or user not found.
    """
    user_id = verify_token(token)
    if user_id is None:
        raise CredentialsException()

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise CredentialsException("User not found")

    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get the current active user.

    Args:
        current_user: The authenticated user.

    Returns:
        User: The active user.

    Raises:
        HTTPException: If user is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Get the current superuser.

    Args:
        current_user: The authenticated active user.

    Returns:
        User: The superuser.

    Raises:
        HTTPException: If user is not a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )
    return current_user


def get_optional_user_id(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[Optional[str], Depends(oauth2_scheme_optional)] = None,
) -> Optional[int]:
    """
    Get the current user ID if authenticated, None otherwise.
    
    Used for endpoints that work both with and without authentication,
    providing enhanced features for authenticated users.
    """
    if not token:
        return None
    
    try:
        user_id = verify_token(token)
        if user_id is None:
            return None
        
        # Verify user exists and is active
        result = db.execute(
            text("SELECT id, is_active FROM users WHERE id = :user_id"),
            {"user_id": int(user_id)}
        ).fetchone()
        
        if result is None or not result[1]:
            return None
        
        return int(user_id)
    except Exception:
        return None

