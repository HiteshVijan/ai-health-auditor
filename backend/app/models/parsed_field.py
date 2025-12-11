"""
ParsedField model for storing extracted document fields.

Stores field values extracted from documents with confidence scores.
"""

from sqlalchemy import String, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, TimestampMixin


class ParsedField(Base, IDMixin, TimestampMixin):
    """
    Model for storing extracted fields from documents.

    Attributes:
        id: Primary key.
        document_id: Foreign key to the source document.
        field_name: Name of the extracted field.
        field_value: Extracted value.
        confidence: Confidence score (0.0 to 1.0).
        source: Extraction method used.
    """

    __tablename__ = "parsed_fields"

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
    field_value: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
    )

    # Relationships
    document = relationship("Document", backref="parsed_fields")

    def __repr__(self) -> str:
        """String representation of ParsedField."""
        return f"<ParsedField(id={self.id}, field={self.field_name}, value={self.field_value})>"

