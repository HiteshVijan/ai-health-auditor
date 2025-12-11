"""
User schemas for request/response validation.

Defines Pydantic models for user-related API operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base schema with common user fields."""

    email: EmailStr = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(
        ...,
        min_length=8,
        description="Password (minimum 8 characters)",
    )


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    email: Optional[EmailStr] = Field(None, description="New email address")
    full_name: Optional[str] = Field(None, description="New full name")
    password: Optional[str] = Field(
        None,
        min_length=8,
        description="New password (minimum 8 characters)",
    )


class UserRead(UserBase):
    """Schema for reading user data."""

    id: int = Field(..., description="User ID")
    is_active: bool = Field(True, description="Whether user is active")
    is_superuser: bool = Field(False, description="Whether user is admin")
    created_at: Optional[datetime] = Field(None, description="Account creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")

    class Config:
        from_attributes = True

