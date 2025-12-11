"""
Authentication endpoints for login and registration.

Provides endpoints for user authentication and token management.
Simplified for local development with SQLite.
"""

from typing import Annotated
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserRead
from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
)
from app.core.rate_limiter import limiter, RATE_LIMITS

router = APIRouter()


def get_email_hash(email: str) -> str:
    """Generate a hash of the email for searching."""
    return hashlib.sha256(email.lower().encode()).hexdigest()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit(RATE_LIMITS["register"])
async def register(
    request: Request,
    user_in: UserCreate,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Register a new user account.
    """
    # Check if user exists (using raw SQL for SQLite compatibility)
    result = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": user_in.email}
    ).fetchone()
    
    if result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user with raw SQL (SQLite compatible)
    hashed_password = get_password_hash(user_in.password)
    
    db.execute(
        text("""
            INSERT INTO users (email, hashed_password, full_name, is_active)
            VALUES (:email, :hashed_password, :full_name, 1)
        """),
        {
            "email": user_in.email,
            "hashed_password": hashed_password,
            "full_name": user_in.full_name or "",
        }
    )
    db.commit()
    
    # Get the created user
    user = db.execute(
        text("SELECT id, email, full_name, is_active FROM users WHERE email = :email"),
        {"email": user_in.email}
    ).fetchone()
    
    return {
        "id": user[0],
        "email": user[1],
        "full_name": user[2],
        "is_active": bool(user[3]),
    }


@router.post(
    "/login",
    response_model=Token,
    summary="Login and get access token",
)
@limiter.limit(RATE_LIMITS["login"])
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    """
    Authenticate user and return JWT access token.
    """
    # Find user by email
    result = db.execute(
        text("SELECT id, email, hashed_password, is_active FROM users WHERE email = :email"),
        {"email": form_data.username}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id, email, hashed_password, is_active = result
    
    # Verify password
    if not verify_password(form_data.password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    
    # Create access token
    access_token = create_access_token(subject=user_id)
    
    return Token(access_token=access_token, token_type="bearer")
