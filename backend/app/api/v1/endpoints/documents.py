"""
Document API Endpoints.

Simplified for local SQLite development.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.api.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# Schemas
# ============================================

class DocumentResponse(BaseModel):
    """Document response schema."""
    id: int
    filename: str
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    status: str
    user_id: int
    created_at: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Paginated document list response."""
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int


# ============================================
# Endpoints
# ============================================

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List documents for the current user."""
    
    # Count total
    count_result = db.execute(
        text("SELECT COUNT(*) FROM documents WHERE user_id = :user_id"),
        {"user_id": user_id}
    ).fetchone()
    total = count_result[0] if count_result else 0
    
    # Get documents
    offset = (page - 1) * page_size
    result = db.execute(
        text("""
            SELECT id, filename, content_type, file_size, status, user_id, created_at
            FROM documents 
            WHERE user_id = :user_id 
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"user_id": user_id, "limit": page_size, "offset": offset}
    ).fetchall()
    
    documents = [
        DocumentResponse(
            id=row[0],
            filename=row[1],
            content_type=row[2],
            file_size=row[3],
            status=row[4] or "uploaded",
            user_id=row[5],
            created_at=str(row[6]) if row[6] else None,
        )
        for row in result
    ]
    
    return DocumentListResponse(
        documents=documents,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get a specific document."""
    
    result = db.execute(
        text("""
            SELECT id, filename, content_type, file_size, status, user_id, created_at
            FROM documents 
            WHERE id = :doc_id AND user_id = :user_id
        """),
        {"doc_id": document_id, "user_id": user_id}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    return DocumentResponse(
        id=result[0],
        filename=result[1],
        content_type=result[2],
        file_size=result[3],
        status=result[4] or "uploaded",
        user_id=result[5],
        created_at=str(result[6]) if result[6] else None,
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a document."""
    
    # Check ownership
    result = db.execute(
        text("SELECT id FROM documents WHERE id = :doc_id AND user_id = :user_id"),
        {"doc_id": document_id, "user_id": user_id}
    ).fetchone()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Delete
    db.execute(
        text("DELETE FROM documents WHERE id = :doc_id"),
        {"doc_id": document_id}
    )
    db.commit()
    
    return {"success": True, "message": "Document deleted"}


@router.get("/{document_id}/deletion-logs")
async def get_document_deletion_logs(
    document_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get deletion logs (simplified - returns empty for local dev)."""
    return []


@router.delete("/user/{target_user_id}/all")
async def delete_all_user_documents(
    target_user_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Delete all documents for a user."""
    
    # Only allow users to delete their own documents
    if target_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete other user's documents",
        )
    
    result = db.execute(
        text("DELETE FROM documents WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    db.commit()
    
    return {"success": True, "message": "All documents deleted"}
