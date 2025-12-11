"""
Document processing Celery tasks.

Handles background parsing and processing of uploaded documents.
"""

from celery_app.celery import celery_app
from app.db.session import SessionLocal
from app.models.document import Document, DocumentStatus


@celery_app.task(bind=True, max_retries=3)
def parse_document_task(self, document_id: int) -> dict:
    """
    Parse an uploaded document (PDF/image).

    Extracts text, tables, and structured data from the document.

    Args:
        document_id: ID of the document to parse.

    Returns:
        dict: Parsing result with status and extracted data.
    """
    db = SessionLocal()
    try:
        # Fetch document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return {"status": "error", "message": "Document not found"}

        # Update status to processing
        document.status = DocumentStatus.PROCESSING
        db.commit()

        # TODO: Implement actual parsing logic
        # - Download file from MinIO
        # - Use pdfplumber/Camelot for PDF tables
        # - Use pytesseract for OCR on images
        # - Extract line items and billing codes

        # Placeholder for parsing logic
        # parsing_result = process_document(document.file_key)

        # Update status to completed
        document.status = DocumentStatus.COMPLETED
        db.commit()

        return {
            "status": "success",
            "document_id": document_id,
            "message": "Document parsed successfully",
        }

    except Exception as exc:
        # Update status to failed
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = DocumentStatus.FAILED
            db.commit()

        # Retry on failure
        raise self.retry(exc=exc, countdown=60)

    finally:
        db.close()

