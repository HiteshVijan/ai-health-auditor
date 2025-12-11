"""
User management endpoints.

Provides endpoints for user profile and management operations.
"""

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.api.deps import get_current_active_user, get_current_superuser
from app.core.security import get_password_hash
from app.core.exceptions import NotFoundException

router = APIRouter()


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user profile",
)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    Get the current authenticated user's profile.

    Args:
        current_user: The authenticated user.

    Returns:
        User: Current user's profile data.
    """
    return current_user


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update current user profile",
)
async def update_current_user(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Update the current user's profile.

    Args:
        user_update: Fields to update.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        User: Updated user profile.
    """
    # Update fields if provided
    if user_update.email is not None:
        # Check if email is taken
        existing = db.query(User).filter(
            User.email == user_update.email,
            User.id != current_user.id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )
        current_user.email = user_update.email

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    if user_update.password is not None:
        current_user.hashed_password = get_password_hash(user_update.password)

    db.commit()
    db.refresh(current_user)

    return current_user


@router.get(
    "/",
    response_model=List[UserRead],
    summary="List all users (admin only)",
)
async def list_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_superuser)],
    skip: int = 0,
    limit: int = 100,
) -> List[User]:
    """
    List all users (superuser only).

    Args:
        db: Database session.
        current_user: The authenticated superuser.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        List[User]: List of users.
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get user by ID (admin only)",
)
async def get_user_by_id(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_superuser)],
) -> User:
    """
    Get a user by ID (superuser only).

    Args:
        user_id: The user's ID.
        db: Database session.
        current_user: The authenticated superuser.

    Returns:
        User: The requested user.

    Raises:
        NotFoundException: If user not found.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException(f"User with id {user_id} not found")
    return user

