"""
Negotiation model for tracking negotiation attempts.

Stores negotiation letter delivery history and status.
"""

from sqlalchemy import String, Integer, Float, ForeignKey, Text, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import enum

from app.db.base import Base, IDMixin, TimestampMixin


class DeliveryChannel(str, enum.Enum):
    """Delivery channel options."""

    EMAIL = "email"
    WHATSAPP = "whatsapp"
    BOTH = "both"


class NegotiationStatus(str, enum.Enum):
    """Negotiation delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class Negotiation(Base, IDMixin, TimestampMixin):
    """
    Model for tracking negotiation letter deliveries.

    Attributes:
        id: Primary key.
        document_id: Foreign key to the source document.
        user_id: Foreign key to the user who initiated.
        channel: Delivery channel (email, whatsapp, both).
        tone: Letter tone used (formal, friendly, assertive).
        status: Current delivery status.
        letter_content: Generated letter text.
        recipient_email: Email address used.
        recipient_phone: Phone number used.
        retry_count: Number of retry attempts.
        last_error: Last error message if failed.
        sent_at: Timestamp when successfully sent.
        delivered_at: Timestamp when delivery confirmed.
    """

    __tablename__ = "negotiations"

    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[DeliveryChannel] = mapped_column(
        Enum(DeliveryChannel),
        nullable=False,
    )
    tone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="formal",
    )
    status: Mapped[NegotiationStatus] = mapped_column(
        Enum(NegotiationStatus),
        default=NegotiationStatus.PENDING,
        nullable=False,
        index=True,
    )
    letter_content: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )
    recipient_email: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )
    recipient_phone: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    last_error: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    document = relationship("Document", backref="negotiations")
    user = relationship("User", backref="negotiations")

    def __repr__(self) -> str:
        """String representation of Negotiation."""
        return f"<Negotiation(id={self.id}, document_id={self.document_id}, status={self.status})>"

    def can_retry(self) -> bool:
        """Check if retry is allowed."""
        return self.retry_count < self.max_retries and self.status == NegotiationStatus.FAILED

