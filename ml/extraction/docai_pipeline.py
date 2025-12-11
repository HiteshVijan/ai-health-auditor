"""
Document AI Pipeline for orchestrating document parsing.

Coordinates OCR, table extraction, and field parsing to process
uploaded documents and store results in the database.
"""

import io
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional, TypedDict

from PIL import Image
import fitz  # PyMuPDF

# Import extraction modules
from extraction.ocr_utils import extract_text_from_image, preprocess_image_for_ocr
from extraction.table_extractor import extract_tables_from_pdf, get_table_summary
from extraction.field_parser import parse_fields, ParsedFields

logger = logging.getLogger(__name__)

# Confidence threshold for creating review tasks
REVIEW_THRESHOLD = 0.75


class PipelineResult(TypedDict):
    """Type definition for pipeline result."""

    document_id: int
    success: bool
    parse_time_seconds: float
    num_pages: int
    num_tables: int
    fields: dict
    review_tasks_created: int
    error: Optional[str]


class DocumentAIPipeline:
    """
    Pipeline for processing documents through OCR and field extraction.

    Orchestrates the full document parsing workflow including:
    - Downloading from S3/MinIO
    - OCR text extraction
    - Table extraction
    - Field parsing
    - Database persistence
    - Review task creation
    """

    def __init__(
        self,
        storage_client=None,
        db_session=None,
    ):
        """
        Initialize the pipeline.

        Args:
            storage_client: MinIO/S3 storage client for downloading files.
            db_session: SQLAlchemy database session for persistence.
        """
        self.storage_client = storage_client
        self.db_session = db_session

    def parse_document(self, document_id: int) -> PipelineResult:
        """
        Parse a document and extract structured fields.

        Downloads the document from storage, performs OCR and table
        extraction, parses fields, saves results to database, and
        creates review tasks for low-confidence extractions.

        Args:
            document_id: ID of the document to parse.

        Returns:
            PipelineResult: Dictionary containing:
                - document_id: The processed document ID.
                - success: Whether parsing succeeded.
                - parse_time_seconds: Total processing time.
                - num_pages: Number of pages processed.
                - num_tables: Number of tables extracted.
                - fields: Extracted field values and confidence.
                - review_tasks_created: Count of review tasks created.
                - error: Error message if failed.

        Example:
            >>> pipeline = DocumentAIPipeline(storage, db)
            >>> result = pipeline.parse_document(123)
            >>> print(f"Parsed in {result['parse_time_seconds']:.2f}s")
        """
        start_time = time.time()
        logger.info(f"Starting document parsing for document_id={document_id}")

        try:
            # Fetch document from database
            document = self._get_document(document_id)
            if not document:
                return self._error_result(
                    document_id,
                    "Document not found",
                    start_time,
                )

            # Download file from storage
            file_content = self._download_file(document.file_key)
            if not file_content:
                return self._error_result(
                    document_id,
                    "Failed to download file from storage",
                    start_time,
                )

            # Process based on content type
            if document.content_type == "application/pdf":
                page_texts, tables, num_pages = self._process_pdf(file_content)
            else:
                page_texts, tables, num_pages = self._process_image(file_content)

            num_tables = len(tables)
            logger.info(
                f"Document {document_id}: {num_pages} pages, {num_tables} tables extracted"
            )

            # Parse fields from extracted content
            parsed_fields = parse_fields(page_texts, tables)

            # Save parsed fields to database
            saved_fields = self._save_parsed_fields(document_id, parsed_fields)

            # Create review tasks for low-confidence fields
            review_count = self._create_review_tasks(
                document_id,
                parsed_fields,
                saved_fields,
            )

            # Update document status
            self._update_document_status(document_id, "completed")

            parse_time = time.time() - start_time
            logger.info(
                f"Document {document_id} parsed successfully in {parse_time:.2f}s. "
                f"Tables: {num_tables}, Review tasks: {review_count}"
            )

            return PipelineResult(
                document_id=document_id,
                success=True,
                parse_time_seconds=round(parse_time, 3),
                num_pages=num_pages,
                num_tables=num_tables,
                fields=self._format_fields(parsed_fields),
                review_tasks_created=review_count,
                error=None,
            )

        except Exception as e:
            logger.exception(f"Error parsing document {document_id}: {e}")
            self._update_document_status(document_id, "failed")
            return self._error_result(document_id, str(e), start_time)

    def _get_document(self, document_id: int):
        """
        Fetch document record from database.

        Args:
            document_id: Document ID to fetch.

        Returns:
            Document model instance or None.
        """
        if not self.db_session:
            logger.warning("No database session provided")
            return None

        from app.models.document import Document

        return self.db_session.query(Document).filter(
            Document.id == document_id
        ).first()

    def _download_file(self, file_key: str) -> Optional[bytes]:
        """
        Download file content from S3/MinIO storage.

        Args:
            file_key: S3 object key.

        Returns:
            File content as bytes or None if failed.
        """
        if not self.storage_client:
            logger.warning("No storage client provided")
            return None

        try:
            response = self.storage_client.get_object(
                bucket_name=self.storage_client.bucket_name,
                object_name=file_key,
            )
            content = response.read()
            response.close()
            response.release_conn()
            return content
        except Exception as e:
            logger.error(f"Failed to download file {file_key}: {e}")
            return None

    def _process_pdf(
        self,
        file_content: bytes,
    ) -> tuple[list[str], list, int]:
        """
        Process PDF file for text and table extraction.

        Args:
            file_content: PDF file bytes.

        Returns:
            Tuple of (page_texts, tables, num_pages).
        """
        page_texts = []
        tables = []

        # Save to temp file for table extraction
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name

        try:
            # Extract tables using Camelot/pdfplumber
            tables = extract_tables_from_pdf(tmp_path)

            # Extract text from each page using PyMuPDF + OCR
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            num_pages = len(pdf_document)

            for page_num in range(num_pages):
                page = pdf_document[page_num]

                # Try to extract text directly first
                text = page.get_text()

                # If no text (scanned PDF), use OCR
                if not text.strip():
                    # Render page as image
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    # Preprocess and OCR
                    img = preprocess_image_for_ocr(img)
                    ocr_result = extract_text_from_image(img)
                    text = ocr_result["page_text"]

                page_texts.append(text)

            pdf_document.close()

        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

        return page_texts, tables, num_pages

    def _process_image(
        self,
        file_content: bytes,
    ) -> tuple[list[str], list, int]:
        """
        Process image file for text extraction.

        Args:
            file_content: Image file bytes.

        Returns:
            Tuple of (page_texts, tables, num_pages).
        """
        # Load image
        img = Image.open(io.BytesIO(file_content))

        # Convert to RGB if necessary
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Preprocess and OCR
        preprocessed = preprocess_image_for_ocr(img)
        ocr_result = extract_text_from_image(preprocessed)

        # Images don't have tables in the same way PDFs do
        return [ocr_result["page_text"]], [], 1

    def _save_parsed_fields(
        self,
        document_id: int,
        parsed_fields: ParsedFields,
    ) -> dict:
        """
        Save parsed fields to database.

        Args:
            document_id: Document ID.
            parsed_fields: Extracted fields.

        Returns:
            Dictionary mapping field names to saved model instances.
        """
        if not self.db_session:
            return {}

        from app.models.parsed_field import ParsedField

        saved = {}

        for field_name, field_data in parsed_fields.items():
            parsed_field = ParsedField(
                document_id=document_id,
                field_name=field_name,
                field_value=field_data["value"],
                confidence=field_data["confidence"],
                source=field_data["source"],
            )
            self.db_session.add(parsed_field)
            self.db_session.flush()  # Get the ID
            saved[field_name] = parsed_field

        self.db_session.commit()
        return saved

    def _create_review_tasks(
        self,
        document_id: int,
        parsed_fields: ParsedFields,
        saved_fields: dict,
    ) -> int:
        """
        Create review tasks for fields below confidence threshold.

        Args:
            document_id: Document ID.
            parsed_fields: Extracted fields with confidence scores.
            saved_fields: Dictionary of saved ParsedField models.

        Returns:
            Number of review tasks created.
        """
        if not self.db_session:
            return 0

        from app.models.review_task import ReviewTask, ReviewStatus

        count = 0

        for field_name, field_data in parsed_fields.items():
            if field_data["confidence"] < REVIEW_THRESHOLD:
                parsed_field = saved_fields.get(field_name)
                if not parsed_field:
                    continue

                review_task = ReviewTask(
                    document_id=document_id,
                    parsed_field_id=parsed_field.id,
                    field_name=field_name,
                    extracted_value=field_data["value"],
                    confidence=field_data["confidence"],
                    status=ReviewStatus.PENDING,
                )
                self.db_session.add(review_task)
                count += 1

                logger.info(
                    f"Created review task for {field_name} "
                    f"(confidence: {field_data['confidence']:.2f})"
                )

        self.db_session.commit()
        return count

    def _update_document_status(self, document_id: int, status: str) -> None:
        """
        Update document processing status.

        Args:
            document_id: Document ID.
            status: New status string.
        """
        if not self.db_session:
            return

        from app.models.document import Document, DocumentStatus

        document = self.db_session.query(Document).filter(
            Document.id == document_id
        ).first()

        if document:
            if status == "completed":
                document.status = DocumentStatus.COMPLETED
            elif status == "failed":
                document.status = DocumentStatus.FAILED
            self.db_session.commit()

    def _format_fields(self, parsed_fields: ParsedFields) -> dict:
        """
        Format parsed fields for API response.

        Args:
            parsed_fields: Extracted fields.

        Returns:
            Simplified field dictionary.
        """
        return {
            name: {
                "value": data["value"],
                "confidence": round(data["confidence"], 3),
                "source": data["source"],
                "needs_review": data["confidence"] < REVIEW_THRESHOLD,
            }
            for name, data in parsed_fields.items()
        }

    def _error_result(
        self,
        document_id: int,
        error: str,
        start_time: float,
    ) -> PipelineResult:
        """
        Create error result.

        Args:
            document_id: Document ID.
            error: Error message.
            start_time: Processing start time.

        Returns:
            PipelineResult with error.
        """
        return PipelineResult(
            document_id=document_id,
            success=False,
            parse_time_seconds=round(time.time() - start_time, 3),
            num_pages=0,
            num_tables=0,
            fields={},
            review_tasks_created=0,
            error=error,
        )


def parse_document(document_id: int) -> dict:
    """
    Convenience function to parse a document.

    Creates pipeline with default storage and database connections.

    Args:
        document_id: ID of the document to parse.

    Returns:
        dict: Pipeline result.
    """
    # Import here to avoid circular imports
    from app.db.session import SessionLocal
    from app.services.storage_service import storage_service

    db = SessionLocal()
    try:
        pipeline = DocumentAIPipeline(
            storage_client=storage_service.client,
            db_session=db,
        )
        # Set bucket name on client for convenience
        pipeline.storage_client.bucket_name = storage_service.bucket_name
        return pipeline.parse_document(document_id)
    finally:
        db.close()

