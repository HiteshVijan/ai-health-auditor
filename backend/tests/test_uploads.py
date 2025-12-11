"""
Unit tests for document upload endpoint.

Tests the POST /uploads endpoint functionality.
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus


class TestUploadEndpoint:
    """Test cases for the upload endpoint."""

    def test_upload_pdf_success(
        self,
        client: TestClient,
        db: Session,
        auth_headers: dict,
        mock_storage_service,
        mock_celery_task,
    ):
        """Test successful PDF upload."""
        # Create a fake PDF file
        pdf_content = b"%PDF-1.4 fake pdf content"
        files = {
            "file": ("test_bill.pdf", io.BytesIO(pdf_content), "application/pdf")
        }

        response = client.post(
            "/api/v1/uploads/",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "document_id" in data
        assert data["status"] == "uploaded"

        # Verify document was saved to database
        document = db.query(Document).filter(
            Document.id == data["document_id"]
        ).first()
        assert document is not None
        assert document.filename == "test_bill.pdf"
        assert document.content_type == "application/pdf"
        assert document.status == DocumentStatus.UPLOADED

        # Verify storage service was called
        mock_storage_service.upload_file.assert_called_once()

        # Verify Celery task was enqueued
        mock_celery_task.delay.assert_called_once_with(document.id)

    def test_upload_image_success(
        self,
        client: TestClient,
        db: Session,
        auth_headers: dict,
        mock_storage_service,
        mock_celery_task,
    ):
        """Test successful image upload."""
        # Create a fake PNG file
        png_content = b"\x89PNG\r\n\x1a\n fake image content"
        files = {
            "file": ("scan.png", io.BytesIO(png_content), "image/png")
        }

        response = client.post(
            "/api/v1/uploads/",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "uploaded"

    def test_upload_invalid_file_type(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test upload rejection for invalid file type."""
        # Create a fake text file
        text_content = b"This is not a PDF or image"
        files = {
            "file": ("document.txt", io.BytesIO(text_content), "text/plain")
        }

        response = client.post(
            "/api/v1/uploads/",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_file_too_large(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test upload rejection for files exceeding 10MB limit."""
        # Create content larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        files = {
            "file": ("large.pdf", io.BytesIO(large_content), "application/pdf")
        }

        response = client.post(
            "/api/v1/uploads/",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "too large" in response.json()["detail"]

    def test_upload_empty_file(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """Test upload rejection for empty files."""
        files = {
            "file": ("empty.pdf", io.BytesIO(b""), "application/pdf")
        }

        response = client.post(
            "/api/v1/uploads/",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Empty file" in response.json()["detail"]

    def test_upload_without_authentication(
        self,
        client: TestClient,
    ):
        """Test upload rejection without JWT token."""
        pdf_content = b"%PDF-1.4 fake pdf content"
        files = {
            "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
        }

        response = client.post(
            "/api/v1/uploads/",
            files=files,
        )

        assert response.status_code == 401

    def test_upload_with_invalid_token(
        self,
        client: TestClient,
    ):
        """Test upload rejection with invalid JWT token."""
        pdf_content = b"%PDF-1.4 fake pdf content"
        files = {
            "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
        }
        headers = {"Authorization": "Bearer invalid_token"}

        response = client.post(
            "/api/v1/uploads/",
            files=files,
            headers=headers,
        )

        assert response.status_code == 401

    def test_upload_jpeg_success(
        self,
        client: TestClient,
        db: Session,
        auth_headers: dict,
        mock_storage_service,
        mock_celery_task,
    ):
        """Test successful JPEG upload."""
        jpeg_content = b"\xff\xd8\xff\xe0 fake jpeg content"
        files = {
            "file": ("bill_scan.jpg", io.BytesIO(jpeg_content), "image/jpeg")
        }

        response = client.post(
            "/api/v1/uploads/",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "uploaded"

        document = db.query(Document).filter(
            Document.id == data["document_id"]
        ).first()
        assert document.content_type == "image/jpeg"

