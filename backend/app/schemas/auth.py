"""
Authentication schemas for JWT token handling.

Defines Pydantic models for login and token operations.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema for user login request."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenPayload(BaseModel):
    """Schema for decoded JWT token payload."""

    sub: Optional[str] = Field(None, description="Subject (user ID)")
    exp: Optional[int] = Field(None, description="Expiration timestamp")

