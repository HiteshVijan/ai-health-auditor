"""
User model with role and encrypted PII fields.

Supports RBAC and transparent PII encryption.
"""

from typing import Optional
from sqlalchemy import String, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.db.base import Base, IDMixin, TimestampMixin
from app.models.encrypted_fields import EncryptedString, EncryptedEmail, EncryptedPhone


class UserRole(str, enum.Enum):
    """User role enumeration."""
    
    USER = "user"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class User(Base, IDMixin, TimestampMixin):
    """
    User model with RBAC and encrypted PII.
    
    Attributes:
        id: Primary key.
        email: User email (encrypted).
        email_hash: Hash of email for searching.
        username: Username (unique).
        hashed_password: Bcrypt hashed password.
        full_name: Full name (encrypted).
        phone: Phone number (encrypted).
        role: User role for RBAC.
        is_active: Whether user can login.
        is_verified: Whether email is verified.
    """
    
    __tablename__ = "users"
    
    # Encrypted email with hash for searching
    email: Mapped[str] = mapped_column(
        EncryptedEmail(length=500),
        nullable=False,
    )
    email_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    
    # Username (not encrypted - needed for login)
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    
    # Password hash (already hashed, no encryption needed)
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # Encrypted PII fields
    full_name: Mapped[Optional[str]] = mapped_column(
        EncryptedString(length=500),
        nullable=True,
    )
    phone: Mapped[Optional[str]] = mapped_column(
        EncryptedPhone(length=500),
        nullable=True,
    )
    
    # RBAC role
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False,
        index=True,
    )
    
    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_reviewer(self) -> bool:
        """Check if user is a reviewer or admin."""
        return self.role in (UserRole.REVIEWER, UserRole.ADMIN)
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role."""
        return self.role == role
    
    def can_access_user(self, target_user_id: int) -> bool:
        """Check if user can access another user's data."""
        if self.id == target_user_id:
            return True
        return self.is_admin
