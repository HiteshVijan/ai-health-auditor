"""
Unit tests for Document AI Pipeline.

Tests the parse_document function with mocked S3 and database.
"""

import pytest
import io
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from PIL import Image, ImageDraw
import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))

from extraction.docai_pipeline import (
    DocumentAIPipeline,
    parse_document,
    PipelineResult,
    REVIEW_THRESHOLD,
)


@pytest.fixture
def mock_document():
    """Create a mock Document model instance."""
    doc = MagicMock()
    doc.id = 1
    doc.file_key = "uploads/1/test_bill.pdf"
    doc.content_type = "application/pdf"
    doc.filename = "test_bill.pdf"
    return doc


@pytest.fixture
def mock_image_document():
    """Create a mock image Document model instance."""
    doc = MagicMock()
    doc.id = 2
    doc.file_key = "uploads/1/test_scan.png"
    doc.content_type = "image/png"
    doc.filename = "test_scan.png"
    return doc


@pytest.fixture
def mock_db_session(mock_document):
    """Create a mock database session."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = mock_document
    session.add = MagicMock()
    session.flush = MagicMock()
    session.commit = MagicMock()
    return session


@pytest.fixture
def mock_storage_client():
    """Create a mock S3/MinIO storage client."""
    client = MagicMock()
    client.bucket_name = "test-bucket"
    return client


@pytest.fixture
def sample_pdf_bytes():
    """Create sample PDF bytes for testing."""
    # This is a minimal valid PDF
    return b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length 44 >> stream
BT /F1 12 Tf 100 700 Td (Test Bill) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
trailer << /Size 5 /Root 1 0 R >>
startxref
306
%%EOF"""


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes for testing."""
    # Create a simple image with text
    img = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "Invoice #12345", fill="black")
    draw.text((20, 60), "Patient: John Doe", fill="black")
    draw.text((20, 100), "Total: $150.00", fill="black")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def mock_parsed_fields():
    """Create mock parsed fields result."""
    return {
        "total_amount": {"value": "150.00", "confidence": 0.9, "source": "regex"},
        "invoice_number": {"value": "INV-12345", "confidence": 0.85, "source": "regex"},
        "patient_name": {"value": "John Doe", "confidence": 0.6, "source": "fuzzy"},
        "bill_date": {"value": "2024-01-15", "confidence": 0.5, "source": "fuzzy"},
    }


class TestDocumentAIPipeline:
    """Test cases for DocumentAIPipeline class."""

    def test_pipeline_initialization(
        self,
        mock_storage_client,
        mock_db_session,
    ):
        """Test pipeline initializes correctly."""
        pipeline = DocumentAIPipeline(
            storage_client=mock_storage_client,
            db_session=mock_db_session,
        )

        assert pipeline.storage_client == mock_storage_client
        assert pipeline.db_session == mock_db_session

    def test_parse_document_success(
        self,
        mock_storage_client,
        mock_db_session,
        mock_document,
        sample_pdf_bytes,
        mock_parsed_fields,
    ):
        """Test successful document parsing."""
        # Setup mocks
        mock_response = MagicMock()
        mock_response.read.return_value = sample_pdf_bytes
        mock_storage_client.get_object.return_value = mock_response

        pipeline = DocumentAIPipeline(
            storage_client=mock_storage_client,
            db_session=mock_db_session,
        )
        pipeline.storage_client.bucket_name = "test-bucket"

        with patch.object(pipeline, "_process_pdf") as mock_process, \
             patch("extraction.docai_pipeline.parse_fields") as mock_parse:

            mock_process.return_value = (["Invoice #12345\nTotal: $150.00"], [], 1)
            mock_parse.return_value = mock_parsed_fields

            result = pipeline.parse_document(1)

            assert result["success"] is True
            assert result["document_id"] == 1
            assert result["num_pages"] == 1
            assert "parse_time_seconds" in result
            assert result["error"] is None

    def test_parse_document_not_found(
        self,
        mock_storage_client,
        mock_db_session,
    ):
        """Test handling of non-existent document."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        pipeline = DocumentAIPipeline(
            storage_client=mock_storage_client,
            db_session=mock_db_session,
        )

        result = pipeline.parse_document(999)

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_parse_document_download_failure(
        self,
        mock_storage_client,
        mock_db_session,
        mock_document,
    ):
        """Test handling of S3 download failure."""
        mock_storage_client.get_object.side_effect = Exception("S3 error")

        pipeline = DocumentAIPipeline(
            storage_client=mock_storage_client,
            db_session=mock_db_session,
        )
        pipeline.storage_client.bucket_name = "test-bucket"

        result = pipeline.parse_document(1)

        assert result["success"] is False
        assert "download" in result["error"].lower() or "S3" in result["error"]

    def test_creates_review_tasks_for_low_confidence(
        self,
        mock_storage_client,
        mock_db_session,
        mock_document,
        sample_pdf_bytes,
        mock_parsed_fields,
    ):
        """Test that review tasks are created for low-confidence fields."""
        mock_response = MagicMock()
        mock_response.read.return_value = sample_pdf_bytes
        mock_storage_client.get_object.return_value = mock_response

        pipeline = DocumentAIPipeline(
            storage_client=mock_storage_client,
            db_session=mock_db_session,
        )
        pipeline.storage_client.bucket_name = "test-bucket"

        with patch.object(pipeline, "_process_pdf") as mock_process, \
             patch("extraction.docai_pipeline.parse_fields") as mock_parse:

            mock_process.return_value = (["test text"], [], 1)
            mock_parse.return_value = mock_parsed_fields

            result = pipeline.parse_document(1)

            # Should create review tasks for patient_name (0.6) and bill_date (0.5)
            assert result["review_tasks_created"] == 2

    def test_logs_parse_time(
        self,
        mock_storage_client,
        mock_db_session,
        mock_document,
        sample_pdf_bytes,
        mock_parsed_fields,
        caplog,
    ):
        """Test that parse time is logged."""
        import logging

        mock_response = MagicMock()
        mock_response.read.return_value = sample_pdf_bytes
        mock_storage_client.get_object.return_value = mock_response

        pipeline = DocumentAIPipeline(
            storage_client=mock_storage_client,
            db_session=mock_db_session,
        )
        pipeline.storage_client.bucket_name = "test-bucket"

        with patch.object(pipeline, "_process_pdf") as mock_process, \
             patch("extraction.docai_pipeline.parse_fields") as mock_parse:

            mock_process.return_value = (["test"], [], 1)
            mock_parse.return_value = mock_parsed_fields

            with caplog.at_level(logging.INFO):
                result = pipeline.parse_document(1)

            assert result["parse_time_seconds"] > 0
            assert "parsed successfully" in caplog.text.lower()

    def test_logs_table_count(
        self,
        mock_storage_client,
        mock_db_session,
        mock_document,
        sample_pdf_bytes,
        mock_parsed_fields,
        caplog,
    ):
        """Test that number of tables is logged."""
        import logging

        mock_response = MagicMock()
        mock_response.read.return_value = sample_pdf_bytes
        mock_storage_client.get_object.return_value = mock_response

        pipeline = DocumentAIPipeline(
            storage_client=mock_storage_client,
            db_session=mock_db_session,
        )
        pipeline.storage_client.bucket_name = "test-bucket"

        # Mock 3 tables extracted
        import pandas as pd
        mock_tables = [pd.DataFrame(), pd.DataFrame(), pd.DataFrame()]

        with patch.object(pipeline, "_process_pdf") as mock_process, \
             patch("extraction.docai_pipeline.parse_fields") as mock_parse:

            mock_process.return_value = (["test"], mock_tables, 1)
            mock_parse.return_value = mock_parsed_fields

            with caplog.at_level(logging.INFO):
                result = pipeline.parse_document(1)

            assert result["num_tables"] == 3
            assert "3 tables" in caplog.text


class TestProcessImage:
    """Test cases for image processing."""

    def test_process_image_extracts_text(
        self,
        mock_storage_client,
        mock_db_session,
        mock_image_document,
        sample_image_bytes,
        mock_parsed_fields,
    ):
        """Test image OCR extraction."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_image_document
        )

        mock_response = MagicMock()
        mock_response.read.return_value = sample_image_bytes
        mock_storage_client.get_object.return_value = mock_response

        pipeline = DocumentAIPipeline(
            storage_client=mock_storage_client,
            db_session=mock_db_session,
        )
        pipeline.storage_client.bucket_name = "test-bucket"

        with patch("extraction.docai_pipeline.extract_text_from_image") as mock_ocr, \
             patch("extraction.docai_pipeline.parse_fields") as mock_parse:

            mock_ocr.return_value = {"page_text": "Invoice #12345", "words": []}
            mock_parse.return_value = mock_parsed_fields

            result = pipeline.parse_document(2)

            assert result["success"] is True
            assert result["num_pages"] == 1
            mock_ocr.assert_called_once()


class TestProcessPdf:
    """Test cases for PDF processing."""

    def test_process_pdf_with_text(
        self,
        mock_storage_client,
        mock_db_session,
    ):
        """Test PDF with embedded text."""
        pipeline = DocumentAIPipeline(
            storage_client=mock_storage_client,
            db_session=mock_db_session,
        )

        with patch("extraction.docai_pipeline.extract_tables_from_pdf") as mock_tables, \
             patch("extraction.docai_pipeline.fitz") as mock_fitz:

            mock_tables.return_value = []

            # Mock PDF with text
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Invoice #12345\nTotal: $150.00"

            mock_pdf = MagicMock()
            mock_pdf.__len__ = MagicMock(return_value=1)
            mock_pdf.__iter__ = MagicMock(return_value=iter([mock_page]))
            mock_pdf.__getitem__ = MagicMock(return_value=mock_page)

            mock_fitz.open.return_value = mock_pdf

            pdf_bytes = b"%PDF-1.4 test"
            page_texts, tables, num_pages = pipeline._process_pdf(pdf_bytes)

            assert len(page_texts) == 1
            assert "Invoice" in page_texts[0]
            assert num_pages == 1


class TestFieldsNeedingReview:
    """Test cases for review threshold logic."""

    def test_high_confidence_no_review(self, mock_parsed_fields):
        """Test that high-confidence fields don't need review."""
        pipeline = DocumentAIPipeline()

        # Manually check fields
        needs_review = [
            name for name, data in mock_parsed_fields.items()
            if data["confidence"] < REVIEW_THRESHOLD
        ]

        # patient_name (0.6) and bill_date (0.5) should need review
        assert "patient_name" in needs_review
        assert "bill_date" in needs_review
        assert "total_amount" not in needs_review
        assert "invoice_number" not in needs_review

    def test_threshold_boundary(self):
        """Test exact threshold boundary."""
        assert REVIEW_THRESHOLD == 0.75

        # Exactly at threshold should not need review
        assert 0.75 >= REVIEW_THRESHOLD

        # Just below should need review
        assert 0.74 < REVIEW_THRESHOLD


class TestFormatFields:
    """Test cases for field formatting."""

    def test_format_fields_output(self, mock_parsed_fields):
        """Test field formatting for API response."""
        pipeline = DocumentAIPipeline()
        formatted = pipeline._format_fields(mock_parsed_fields)

        assert "total_amount" in formatted
        assert formatted["total_amount"]["value"] == "150.00"
        assert formatted["total_amount"]["confidence"] == 0.9
        assert formatted["total_amount"]["needs_review"] is False

        assert formatted["patient_name"]["needs_review"] is True
        assert formatted["bill_date"]["needs_review"] is True


class TestErrorHandling:
    """Test cases for error handling."""

    def test_handles_processing_exception(
        self,
        mock_storage_client,
        mock_db_session,
        mock_document,
    ):
        """Test graceful handling of processing exceptions."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"invalid content"
        mock_storage_client.get_object.return_value = mock_response

        pipeline = DocumentAIPipeline(
            storage_client=mock_storage_client,
            db_session=mock_db_session,
        )
        pipeline.storage_client.bucket_name = "test-bucket"

        with patch.object(pipeline, "_process_pdf") as mock_process:
            mock_process.side_effect = Exception("Processing error")

            result = pipeline.parse_document(1)

            assert result["success"] is False
            assert result["error"] == "Processing error"

    def test_no_db_session(self):
        """Test handling when no database session provided."""
        pipeline = DocumentAIPipeline(storage_client=None, db_session=None)

        result = pipeline._get_document(1)
        assert result is None

        saved = pipeline._save_parsed_fields(1, {})
        assert saved == {}

        count = pipeline._create_review_tasks(1, {}, {})
        assert count == 0


class TestIntegration:
    """Integration tests with real file processing."""

    @pytest.fixture
    def create_test_pdf(self, tmp_path) -> str:
        """Create a test PDF file."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            pdf_path = tmp_path / "test_bill.pdf"

            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            c.drawString(100, 750, "MEDICAL BILLING STATEMENT")
            c.drawString(100, 700, "Invoice #: INV-2024-00123")
            c.drawString(100, 650, "Patient Name: John Michael Smith")
            c.drawString(100, 600, "Date: 01/15/2024")
            c.drawString(100, 500, "Total Amount Due: $450.00")
            c.save()

            return str(pdf_path)
        except ImportError:
            pytest.skip("reportlab not installed")

    @pytest.mark.skipif(
        not os.environ.get("RUN_INTEGRATION_TESTS"),
        reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to run.",
    )
    def test_full_pipeline_with_real_pdf(
        self,
        create_test_pdf,
        mock_db_session,
    ):
        """Test full pipeline with a real PDF file."""
        # Read the test PDF
        with open(create_test_pdf, "rb") as f:
            pdf_content = f.read()

        mock_storage_client = MagicMock()
        mock_response = MagicMock()
        mock_response.read.return_value = pdf_content
        mock_storage_client.get_object.return_value = mock_response
        mock_storage_client.bucket_name = "test-bucket"

        pipeline = DocumentAIPipeline(
            storage_client=mock_storage_client,
            db_session=mock_db_session,
        )
        pipeline.storage_client.bucket_name = "test-bucket"

        result = pipeline.parse_document(1)

        assert result["success"] is True
        assert result["num_pages"] >= 1
        assert "fields" in result

