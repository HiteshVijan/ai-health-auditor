"""
File upload endpoints.

Features:
- Max 10 uploads per user (auto-deletes oldest)
- Supports PDF and images
- OCR-ready for bill analysis
"""

import io
import os
import logging
from typing import Annotated
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.api.deps import get_current_user_id
from app.services.storage_service import storage_service
from app.core.rate_limiter import limiter, RATE_LIMITS

logger = logging.getLogger(__name__)
router = APIRouter()

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_UPLOADS_PER_USER = 10  # Auto-delete oldest when exceeded
UPLOAD_BASE_PATH = Path(__file__).parent.parent.parent.parent.parent / "data"

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "text/plain",
}


def cleanup_old_uploads(db: Session, user_id: int):
    """
    Keep only the latest MAX_UPLOADS_PER_USER documents.
    Deletes oldest files when limit exceeded.
    """
    # Get count
    count_result = db.execute(
        text("SELECT COUNT(*) FROM documents WHERE user_id = :user_id"),
        {"user_id": user_id}
    ).fetchone()
    
    count = count_result[0] if count_result else 0
    
    if count >= MAX_UPLOADS_PER_USER:
        # Get oldest documents to delete
        to_delete = count - MAX_UPLOADS_PER_USER + 1  # +1 for the new one
        
        oldest = db.execute(
            text("""SELECT id, file_key FROM documents 
                    WHERE user_id = :user_id 
                    ORDER BY created_at ASC 
                    LIMIT :limit"""),
            {"user_id": user_id, "limit": to_delete}
        ).fetchall()
        
        for doc_id, file_key in oldest:
            # Delete file from storage
            if file_key:
                for base in [UPLOAD_BASE_PATH, UPLOAD_BASE_PATH / "uploads"]:
                    file_path = base / file_key
                    if file_path.exists():
                        try:
                            os.remove(file_path)
                            logger.info(f"🗑️ Deleted old file: {file_path}")
                        except Exception as e:
                            logger.error(f"Failed to delete file: {e}")
            
            # Delete from database
            db.execute(
                text("DELETE FROM documents WHERE id = :doc_id"),
                {"doc_id": doc_id}
            )
            logger.info(f"🗑️ Deleted old document: {doc_id}")
        
        db.commit()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
@limiter.limit(RATE_LIMITS["upload"])
async def upload_document(
    request: Request,
    file: Annotated[UploadFile, File(description="PDF or image file (max 10MB)")],
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[int, Depends(get_current_user_id)],
):
    """Upload a document for processing."""
    
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: PDF, PNG, JPEG, TIFF, TXT",
        )

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 10MB",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file not allowed",
        )

    # Generate file key and upload
    file_key = storage_service.generate_file_key(
        user_id=user_id,
        filename=file.filename or "document",
    )

    try:
        storage_service.upload_file(
            file_data=io.BytesIO(file_content),
            file_key=file_key,
            content_type=file.content_type,
            file_size=file_size,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )

    # Cleanup old uploads if limit exceeded (keep only 10)
    cleanup_old_uploads(db, user_id)
    
    # Create document record in database
    db.execute(
        text("""
            INSERT INTO documents (user_id, filename, file_key, content_type, file_size, status)
            VALUES (:user_id, :filename, :file_key, :content_type, :file_size, 'uploaded')
        """),
        {
            "user_id": user_id,
            "filename": file.filename or "document",
            "file_key": file_key,
            "content_type": file.content_type,
            "file_size": file_size,
        }
    )
    db.commit()
    
    logger.info(f"📤 Uploaded: {file.filename} for user {user_id}")

    # Get the created document ID
    result = db.execute(
        text("SELECT id FROM documents WHERE file_key = :file_key"),
        {"file_key": file_key}
    ).fetchone()

    return {
        "document_id": result[0],
        "filename": file.filename,
        "status": "uploaded",
        "message": "Document uploaded successfully",
    }
