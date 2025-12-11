"""
ReviewTask model for human review of low-confidence extractions.

Tracks fields that require manual verification.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, ForeignKey, Text, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base, IDMixin, TimestampMixin


class ReviewTaskStatus(str, enum.Enum):
    """Enum for review task status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ReviewTask(Base, IDMixin, TimestampMixin):
    """
    Model for human review tasks on extracted fields.

    Created when a field's confidence score is below threshold.

    Attributes:
        id: Primary key.
        document_id: Foreign key to the source document.
        field_name: Name of the field requiring review.
        extracted_value: Original extracted value.
        corrected_value: Human-corrected value (if any).
        confidence: Original confidence score.
        status: Current review status.
        assigned_to_user_id: User ID of assigned reviewer.
        reviewer_notes: Reviewer notes.
        reviewed_at: Timestamp when review was completed.
    """

    __tablename__ = "review_tasks"

    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    extracted_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    corrected_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    status: Mapped[ReviewTaskStatus] = mapped_column(
        Enum(ReviewTaskStatus),
        default=ReviewTaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewer_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Relationships
    document = relationship("Document", backref="review_tasks")
    assignee = relationship("User", backref="assigned_review_tasks")

    def __repr__(self) -> str:
        """String representation of ReviewTask."""
        return f"<ReviewTask(id={self.id}, field={self.field_name}, status={self.status})>"
