"""
Deletion Log Model for GDPR Compliance.

Tracks all data deletions for audit and compliance purposes.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, Enum, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IDMixin, TimestampMixin


class DeletionReason(str, enum.Enum):
    """Reason for data deletion."""
    
    USER_REQUEST = "user_request"           # User requested deletion (GDPR)
    ADMIN_REQUEST = "admin_request"         # Admin initiated deletion
    RETENTION_POLICY = "retention_policy"   # Automatic retention policy
    LEGAL_REQUIREMENT = "legal_requirement" # Legal/compliance requirement
    DATA_BREACH = "data_breach"             # Data breach response
    ACCOUNT_DELETION = "account_deletion"   # Full account deletion


class DeletionStatus(str, enum.Enum):
    """Status of deletion operation."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"       # Some components failed
    FAILED = "failed"


class DeletionLog(Base, IDMixin, TimestampMixin):
    """
    Audit log for data deletions.
    
    Maintains a permanent record of what was deleted, when, and by whom
    for GDPR compliance and audit purposes.
    """
    
    __tablename__ = "deletion_logs"
    
    # What was deleted
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    resource_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    resource_identifier: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    # Who deleted it
    deleted_by_user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    deleted_by_username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    deleted_by_role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    
    # Owner of the deleted resource
    resource_owner_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    
    # Deletion details
    reason: Mapped[DeletionReason] = mapped_column(
        Enum(DeletionReason),
        nullable=False,
    )
    reason_details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Status tracking
    status: Mapped[DeletionStatus] = mapped_column(
        Enum(DeletionStatus),
        default=DeletionStatus.PENDING,
        nullable=False,
    )
    
    # What was deleted (for audit)
    deleted_components: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Timing
    deletion_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    deletion_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # IP address for audit
    request_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
    )
    
    def __repr__(self) -> str:
        return (
            f"<DeletionLog(id={self.id}, "
            f"resource={self.resource_type}:{self.resource_id}, "
            f"status={self.status})>"
        )

