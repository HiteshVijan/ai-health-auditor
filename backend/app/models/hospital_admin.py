"""
Hospital Admin Model - B2B Authentication.

Separate model for hospital administrators.
Completely independent from B2C User model.
"""

from datetime import datetime, timezone
from typing import Optional
import enum

from sqlalchemy import (
    String, Integer, Float, ForeignKey, Text, Boolean,
    Enum, DateTime, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, TimestampMixin


class AdminPermission(str, enum.Enum):
    """Permissions for hospital admins."""
    VIEW_DASHBOARD = "view_dashboard"
    VIEW_PRICING = "view_pricing"
    VIEW_COMPETITORS = "view_competitors"
    MANAGE_STAFF = "manage_staff"
    EXPORT_DATA = "export_data"
    API_ACCESS = "api_access"


class HospitalAdmin(Base, IDMixin, TimestampMixin):
    """
    Hospital administrator account for B2B access.
    
    Completely separate from B2C User model.
    Each admin is linked to exactly one hospital.
    """
    __tablename__ = "hospital_admins"
    
    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Billing Manager"
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Hospital linkage
    hospital_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("hospitals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)  # Primary admin for hospital
    
    # Verification
    verification_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Permissions (stored as comma-separated string for simplicity)
    permissions: Mapped[str] = mapped_column(
        String(500),
        default="view_dashboard,view_pricing,view_competitors",
        nullable=False,
    )
    
    # Last activity tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships
    hospital = relationship("Hospital", backref="admins")
    
    __table_args__ = (
        Index('ix_hospital_admin_hospital', 'hospital_id'),
    )
    
    def __repr__(self) -> str:
        return f"<HospitalAdmin(id={self.id}, email={self.email}, hospital_id={self.hospital_id})>"
    
    def has_permission(self, permission: AdminPermission) -> bool:
        """Check if admin has a specific permission."""
        return permission.value in self.permissions.split(',')
    
    def get_permissions(self) -> list[str]:
        """Get list of permissions."""
        return [p.strip() for p in self.permissions.split(',') if p.strip()]
    
    def set_permissions(self, perms: list[AdminPermission]) -> None:
        """Set permissions."""
        self.permissions = ','.join(p.value for p in perms)


class HospitalAdminInvite(Base, IDMixin, TimestampMixin):
    """
    Invitation for new hospital admins.
    
    Primary admin can invite other staff members.
    """
    __tablename__ = "hospital_admin_invites"
    
    hospital_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("hospitals.id", ondelete="CASCADE"),
        nullable=False,
    )
    invited_by_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("hospital_admins.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    invite_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    
    # Status
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital")
    invited_by = relationship("HospitalAdmin")
    
    def __repr__(self) -> str:
        return f"<HospitalAdminInvite(email={self.email}, hospital_id={self.hospital_id})>"

