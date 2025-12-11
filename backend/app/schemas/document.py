"""
Document schemas for upload request/response validation.

Defines Pydantic models for document upload operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""

    document_id: int = Field(..., description="Unique document ID")
    status: str = Field(..., description="Upload status")


class DocumentRead(BaseModel):
    """Schema for reading document data."""

    id: int = Field(..., description="Document ID")
    user_id: int = Field(..., description="Owner user ID")
    filename: str = Field(..., description="Original filename")
    file_key: str = Field(..., description="S3/MinIO object key")
    content_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Processing status")
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

