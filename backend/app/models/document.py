"""
Document model for uploaded files.

Stores metadata for uploaded PDFs and images.
"""

from sqlalchemy import String, Integer, ForeignKey, BigInteger, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base, IDMixin, TimestampMixin


class DocumentStatus(str, enum.Enum):
    """Enum for document processing status."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base, IDMixin, TimestampMixin):
    """
    Document model for uploaded files.

    Attributes:
        id: Primary key.
        user_id: Foreign key to the uploading user.
        filename: Original filename.
        file_key: S3/MinIO object key.
        content_type: MIME type of the file.
        file_size: Size in bytes.
        status: Processing status.
    """

    __tablename__ = "documents"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        unique=True,
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus),
        default=DocumentStatus.UPLOADED,
        nullable=False,
    )

    # Relationships
    user = relationship("User", backref="documents")

    def __repr__(self) -> str:
        """String representation of Document."""
        return f"<Document(id={self.id}, filename={self.filename})>"

