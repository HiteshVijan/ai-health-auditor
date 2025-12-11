"""
Unit tests for email sender service.

Tests email sending with mock SMTP server.
"""

import pytest
import smtplib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from email.mime.multipart import MIMEMultipart
import sys
import os

# Add backend directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.email_sender import (
    EmailSender,
    SMTPConfig,
    EmailResult,
    DeliveryStatus,
    send_email,
)


@pytest.fixture
def smtp_config() -> SMTPConfig:
    """Create test SMTP configuration."""
    return SMTPConfig(
        host="smtp.test.com",
        port=587,
        username="testuser",
        password="testpass",
        use_tls=True,
        use_ssl=False,
        from_email="test@healthauditor.com",
        from_name="Test Sender",
    )


@pytest.fixture
def email_sender(smtp_config: SMTPConfig) -> EmailSender:
    """Create email sender with test config."""
    return EmailSender(config=smtp_config)


@pytest.fixture
def mock_smtp():
    """Create mock SMTP server."""
    with patch("app.services.email_sender.smtplib.SMTP") as mock:
        mock_server = MagicMock()
        mock.return_value = mock_server
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.starttls.return_value = (220, b"OK")
        mock_server.login.return_value = (235, b"OK")
        mock_server.sendmail.return_value = {}
        mock_server.quit.return_value = (221, b"Bye")
        yield mock_server


@pytest.fixture
def mock_smtp_ssl():
    """Create mock SMTP_SSL server."""
    with patch("app.services.email_sender.smtplib.SMTP_SSL") as mock:
        mock_server = MagicMock()
        mock.return_value = mock_server
        mock_server.ehlo.return_value = (250, b"OK")
        mock_server.login.return_value = (235, b"OK")
        mock_server.sendmail.return_value = {}
        mock_server.quit.return_value = (221, b"Bye")
        yield mock_server


@pytest.fixture
def sample_attachment(tmp_path) -> str:
    """Create a sample attachment file."""
    file_path = tmp_path / "test_report.pdf"
    file_path.write_bytes(b"%PDF-1.4 fake pdf content")
    return str(file_path)


class TestSMTPConfig:
    """Test cases for SMTP configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SMTPConfig()

        assert config.host == "localhost"
        assert config.port == 587
        assert config.use_tls is True
        assert config.use_ssl is False

    def test_custom_values(self):
        """Test custom configuration."""
        config = SMTPConfig(
            host="mail.example.com",
            port=465,
            use_ssl=True,
            use_tls=False,
        )

        assert config.host == "mail.example.com"
        assert config.port == 465
        assert config.use_ssl is True

    def test_from_env(self):
        """Test loading from environment variables."""
        with patch.dict(os.environ, {
            "SMTP_HOST": "env.smtp.com",
            "SMTP_PORT": "2525",
            "SMTP_USERNAME": "envuser",
            "SMTP_PASSWORD": "envpass",
            "SMTP_USE_TLS": "false",
            "SMTP_FROM_EMAIL": "env@test.com",
        }):
            config = SMTPConfig.from_env()

            assert config.host == "env.smtp.com"
            assert config.port == 2525
            assert config.username == "envuser"
            assert config.use_tls is False
            assert config.from_email == "env@test.com"


class TestEmailResult:
    """Test cases for EmailResult."""

    def test_sent_result(self):
        """Test successful email result."""
        result = EmailResult(
            status=DeliveryStatus.SENT,
            message_id="<123@test>",
            recipients=["user@test.com"],
        )

        assert result.status == DeliveryStatus.SENT
        assert result.message_id == "<123@test>"
        assert result.error is None

    def test_failed_result(self):
        """Test failed email result."""
        result = EmailResult(
            status=DeliveryStatus.FAILED,
            error="Connection refused",
            recipients=["user@test.com"],
        )

        assert result.status == DeliveryStatus.FAILED
        assert result.error == "Connection refused"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = EmailResult(
            status=DeliveryStatus.SENT,
            message_id="<123@test>",
            recipients=["user@test.com"],
        )

        data = result.to_dict()

        assert data["status"] == "sent"
        assert data["message_id"] == "<123@test>"


class TestEmailSender:
    """Test cases for EmailSender class."""

    def test_initialization(self, smtp_config: SMTPConfig):
        """Test sender initialization."""
        sender = EmailSender(config=smtp_config)

        assert sender.config == smtp_config

    def test_initialization_default_config(self):
        """Test sender with default config."""
        sender = EmailSender()

        assert sender.config is not None
        assert sender.config.host == "localhost"


class TestSendEmail:
    """Test cases for send_email method."""

    def test_send_simple_email(
        self,
        email_sender: EmailSender,
        mock_smtp,
    ):
        """Test sending a simple email."""
        result = email_sender.send_email(
            to_email="recipient@test.com",
            subject="Test Subject",
            body="Test body content",
        )

        assert result.status == DeliveryStatus.SENT
        assert "recipient@test.com" in result.recipients
        mock_smtp.sendmail.assert_called_once()

    def test_send_email_with_attachment(
        self,
        email_sender: EmailSender,
        mock_smtp,
        sample_attachment: str,
    ):
        """Test sending email with attachment."""
        result = email_sender.send_email(
            to_email="recipient@test.com",
            subject="Test with Attachment",
            body="Please see attached.",
            attachments=[sample_attachment],
        )

        assert result.status == DeliveryStatus.SENT
        mock_smtp.sendmail.assert_called_once()

        # Verify sendmail was called with message containing attachment
        call_args = mock_smtp.sendmail.call_args
        message_str = call_args[0][2]
        assert "test_report.pdf" in message_str

    def test_send_email_with_html(
        self,
        email_sender: EmailSender,
        mock_smtp,
    ):
        """Test sending email with HTML body."""
        result = email_sender.send_email(
            to_email="recipient@test.com",
            subject="HTML Email",
            body="Plain text version",
            html_body="<h1>HTML Version</h1>",
        )

        assert result.status == DeliveryStatus.SENT

        call_args = mock_smtp.sendmail.call_args
        message_str = call_args[0][2]
        assert "text/plain" in message_str
        assert "text/html" in message_str

    def test_send_email_with_cc(
        self,
        email_sender: EmailSender,
        mock_smtp,
    ):
        """Test sending email with CC recipients."""
        result = email_sender.send_email(
            to_email="primary@test.com",
            subject="CC Test",
            body="Test body",
            cc=["cc1@test.com", "cc2@test.com"],
        )

        assert result.status == DeliveryStatus.SENT
        assert len(result.recipients) == 3

        call_args = mock_smtp.sendmail.call_args
        recipients = call_args[0][1]
        assert "primary@test.com" in recipients
        assert "cc1@test.com" in recipients
        assert "cc2@test.com" in recipients

    def test_send_email_with_bcc(
        self,
        email_sender: EmailSender,
        mock_smtp,
    ):
        """Test sending email with BCC recipients."""
        result = email_sender.send_email(
            to_email="primary@test.com",
            subject="BCC Test",
            body="Test body",
            bcc=["bcc@test.com"],
        )

        assert result.status == DeliveryStatus.SENT

        call_args = mock_smtp.sendmail.call_args
        recipients = call_args[0][1]
        assert "bcc@test.com" in recipients

    def test_send_email_missing_attachment(
        self,
        email_sender: EmailSender,
        mock_smtp,
    ):
        """Test error handling for missing attachment."""
        result = email_sender.send_email(
            to_email="recipient@test.com",
            subject="Test",
            body="Test body",
            attachments=["/nonexistent/file.pdf"],
        )

        assert result.status == DeliveryStatus.FAILED
        assert "not found" in result.error.lower()
        mock_smtp.sendmail.assert_not_called()

    def test_send_email_auth_failure(
        self,
        email_sender: EmailSender,
        mock_smtp,
    ):
        """Test handling of authentication failure."""
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(
            535, b"Authentication failed"
        )

        result = email_sender.send_email(
            to_email="recipient@test.com",
            subject="Test",
            body="Test body",
        )

        assert result.status == DeliveryStatus.FAILED
        assert "authentication" in result.error.lower()

    def test_send_email_recipients_refused(
        self,
        email_sender: EmailSender,
        mock_smtp,
    ):
        """Test handling of refused recipients."""
        mock_smtp.sendmail.side_effect = smtplib.SMTPRecipientsRefused(
            {"bad@test.com": (550, b"User unknown")}
        )

        result = email_sender.send_email(
            to_email="bad@test.com",
            subject="Test",
            body="Test body",
        )

        assert result.status == DeliveryStatus.FAILED
        assert "refused" in result.error.lower()

    def test_send_email_smtp_error(
        self,
        email_sender: EmailSender,
        mock_smtp,
    ):
        """Test handling of general SMTP error."""
        mock_smtp.sendmail.side_effect = smtplib.SMTPException("Server error")

        result = email_sender.send_email(
            to_email="recipient@test.com",
            subject="Test",
            body="Test body",
        )

        assert result.status == DeliveryStatus.FAILED
        assert "smtp" in result.error.lower()

    def test_send_email_uses_starttls(
        self,
        smtp_config: SMTPConfig,
        mock_smtp,
    ):
        """Test that STARTTLS is used when configured."""
        smtp_config.use_tls = True
        smtp_config.use_ssl = False
        sender = EmailSender(config=smtp_config)

        sender.send_email(
            to_email="recipient@test.com",
            subject="Test",
            body="Test body",
        )

        mock_smtp.starttls.assert_called_once()

    def test_send_email_uses_ssl(self, mock_smtp_ssl):
        """Test sending over SSL."""
        config = SMTPConfig(
            host="smtp.test.com",
            port=465,
            use_ssl=True,
            use_tls=False,
        )
        sender = EmailSender(config=config)

        result = sender.send_email(
            to_email="recipient@test.com",
            subject="SSL Test",
            body="Test body",
        )

        assert result.status == DeliveryStatus.SENT


class TestSendBulk:
    """Test cases for bulk email sending."""

    def test_send_to_multiple_recipients(
        self,
        email_sender: EmailSender,
        mock_smtp,
    ):
        """Test sending to multiple recipients."""
        recipients = ["user1@test.com", "user2@test.com", "user3@test.com"]

        results = email_sender.send_bulk(
            recipients=recipients,
            subject="Bulk Test",
            body="Test body",
        )

        assert len(results) == 3
        assert all(r.status == DeliveryStatus.SENT for r in results)
        assert mock_smtp.sendmail.call_count == 3


class TestTestConnection:
    """Test cases for connection testing."""

    def test_successful_connection(
        self,
        email_sender: EmailSender,
        mock_smtp,
    ):
        """Test successful connection test."""
        result = email_sender.test_connection()

        assert result is True
        mock_smtp.ehlo.assert_called()
        mock_smtp.quit.assert_called()

    def test_failed_connection(
        self,
        email_sender: EmailSender,
    ):
        """Test failed connection test."""
        with patch("app.services.email_sender.smtplib.SMTP") as mock:
            mock.side_effect = ConnectionRefusedError("Connection refused")

            result = email_sender.test_connection()

            assert result is False


class TestCreateMessage:
    """Test cases for message creation."""

    def test_creates_multipart_message(
        self,
        email_sender: EmailSender,
    ):
        """Test message structure."""
        message = email_sender._create_message(
            to_email="recipient@test.com",
            subject="Test Subject",
            body="Test body",
        )

        assert isinstance(message, MIMEMultipart)
        assert message["Subject"] == "Test Subject"
        assert message["To"] == "recipient@test.com"
        assert "Test Sender" in message["From"]

    def test_includes_reply_to(
        self,
        email_sender: EmailSender,
    ):
        """Test reply-to header."""
        message = email_sender._create_message(
            to_email="recipient@test.com",
            subject="Test",
            body="Test body",
            reply_to="reply@test.com",
        )

        assert message["Reply-To"] == "reply@test.com"


class TestAddAttachment:
    """Test cases for attachment handling."""

    def test_adds_pdf_attachment(
        self,
        email_sender: EmailSender,
        sample_attachment: str,
    ):
        """Test adding PDF attachment."""
        message = MIMEMultipart()

        email_sender._add_attachment(message, sample_attachment)

        # Check that attachment was added
        payloads = message.get_payload()
        assert len(payloads) == 1

    def test_raises_for_missing_file(
        self,
        email_sender: EmailSender,
    ):
        """Test error for missing attachment file."""
        message = MIMEMultipart()

        with pytest.raises(FileNotFoundError):
            email_sender._add_attachment(message, "/nonexistent/file.pdf")

    def test_multiple_attachments(
        self,
        email_sender: EmailSender,
        tmp_path,
    ):
        """Test adding multiple attachments."""
        # Create test files
        file1 = tmp_path / "doc1.pdf"
        file2 = tmp_path / "doc2.txt"
        file1.write_bytes(b"PDF content")
        file2.write_text("Text content")

        message = MIMEMultipart()
        email_sender._add_attachment(message, str(file1))
        email_sender._add_attachment(message, str(file2))

        payloads = message.get_payload()
        assert len(payloads) == 2


class TestGetMimeType:
    """Test cases for MIME type detection."""

    def test_pdf_mime_type(self, email_sender: EmailSender):
        """Test PDF MIME type."""
        mime = email_sender._get_mime_type(Path("document.pdf"))
        assert mime == "application/pdf"

    def test_image_mime_types(self, email_sender: EmailSender):
        """Test image MIME types."""
        assert email_sender._get_mime_type(Path("image.png")) == "image/png"
        assert email_sender._get_mime_type(Path("photo.jpg")) == "image/jpeg"
        assert email_sender._get_mime_type(Path("photo.jpeg")) == "image/jpeg"

    def test_unknown_mime_type(self, email_sender: EmailSender):
        """Test fallback for unknown extension."""
        mime = email_sender._get_mime_type(Path("file.xyz"))
        assert mime == "application/octet-stream"


class TestConvenienceFunction:
    """Test cases for send_email convenience function."""

    def test_send_email_function(self, mock_smtp):
        """Test standalone send_email function."""
        config = SMTPConfig(
            host="test.smtp.com",
            port=587,
        )

        result = send_email(
            to_email="recipient@test.com",
            subject="Function Test",
            body="Test body",
            config=config,
        )

        assert result.status == DeliveryStatus.SENT


class TestIntegration:
    """Integration tests for email sending."""

    def test_complete_email_flow(
        self,
        mock_smtp,
        tmp_path,
    ):
        """Test complete email sending flow."""
        # Create config
        config = SMTPConfig(
            host="smtp.test.com",
            port=587,
            username="user",
            password="pass",
            use_tls=True,
            from_email="sender@test.com",
            from_name="Test App",
        )

        # Create attachment
        attachment = tmp_path / "report.pdf"
        attachment.write_bytes(b"PDF content")

        # Create sender and send
        sender = EmailSender(config=config)
        result = sender.send_email(
            to_email="recipient@test.com",
            subject="Complete Test",
            body="Plain text body",
            html_body="<p>HTML body</p>",
            attachments=[str(attachment)],
            cc=["cc@test.com"],
            reply_to="reply@test.com",
        )

        # Verify success
        assert result.status == DeliveryStatus.SENT
        assert len(result.recipients) == 2

        # Verify SMTP calls
        mock_smtp.ehlo.assert_called()
        mock_smtp.starttls.assert_called()
        mock_smtp.login.assert_called_with("user", "pass")
        mock_smtp.sendmail.assert_called_once()
        mock_smtp.quit.assert_called()

