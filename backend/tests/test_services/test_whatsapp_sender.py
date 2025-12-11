"""
Unit tests for WhatsApp sender service.

Tests WhatsApp messaging with mocked API.
"""

import pytest
import requests
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import os

# Add backend directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.whatsapp_sender import (
    WhatsAppSender,
    WhatsAppConfig,
    WhatsAppResult,
    DeliveryStatus,
    MessageType,
    send_whatsapp,
)


@pytest.fixture
def whatsapp_config() -> WhatsAppConfig:
    """Create test WhatsApp configuration."""
    return WhatsAppConfig(
        access_token="test_access_token_12345",
        phone_number_id="1234567890",
        api_version="v18.0",
        timeout=30,
    )


@pytest.fixture
def whatsapp_sender(whatsapp_config: WhatsAppConfig) -> WhatsAppSender:
    """Create WhatsApp sender with test config."""
    return WhatsAppSender(config=whatsapp_config)


@pytest.fixture
def mock_session():
    """Create mock requests session."""
    session = MagicMock(spec=requests.Session)
    return session


@pytest.fixture
def successful_send_response():
    """Create successful API response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "messaging_product": "whatsapp",
        "contacts": [{"input": "1234567890", "wa_id": "1234567890"}],
        "messages": [{"id": "wamid.HBgLMTIzNDU2Nzg5MBUCABEYEjM="}],
    }
    return response


@pytest.fixture
def failed_send_response():
    """Create failed API response."""
    response = MagicMock()
    response.status_code = 400
    response.json.return_value = {
        "error": {
            "message": "Invalid recipient",
            "type": "OAuthException",
            "code": 100,
            "fbtrace_id": "ABC123",
        }
    }
    return response


@pytest.fixture
def successful_upload_response():
    """Create successful media upload response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "id": "media_id_12345",
    }
    return response


@pytest.fixture
def sample_attachment(tmp_path) -> str:
    """Create a sample attachment file."""
    file_path = tmp_path / "test_report.pdf"
    file_path.write_bytes(b"%PDF-1.4 fake pdf content")
    return str(file_path)


@pytest.fixture
def sample_image(tmp_path) -> str:
    """Create a sample image file."""
    file_path = tmp_path / "test_image.png"
    file_path.write_bytes(b"\x89PNG fake image content")
    return str(file_path)


class TestWhatsAppConfig:
    """Test cases for WhatsApp configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = WhatsAppConfig()

        assert config.api_version == "v18.0"
        assert config.api_base_url == "https://graph.facebook.com"
        assert config.timeout == 30

    def test_messages_url(self, whatsapp_config: WhatsAppConfig):
        """Test messages URL generation."""
        url = whatsapp_config.messages_url

        assert "graph.facebook.com" in url
        assert "v18.0" in url
        assert "1234567890" in url
        assert "messages" in url

    def test_media_url(self, whatsapp_config: WhatsAppConfig):
        """Test media URL generation."""
        url = whatsapp_config.media_url

        assert "media" in url

    def test_is_configured(self, whatsapp_config: WhatsAppConfig):
        """Test configuration check."""
        assert whatsapp_config.is_configured() is True

        empty_config = WhatsAppConfig()
        assert empty_config.is_configured() is False

    def test_from_env(self):
        """Test loading from environment variables."""
        with patch.dict(os.environ, {
            "WHATSAPP_ACCESS_TOKEN": "env_token",
            "WHATSAPP_PHONE_NUMBER_ID": "env_phone_id",
            "WHATSAPP_API_VERSION": "v17.0",
        }):
            config = WhatsAppConfig.from_env()

            assert config.access_token == "env_token"
            assert config.phone_number_id == "env_phone_id"
            assert config.api_version == "v17.0"


class TestWhatsAppResult:
    """Test cases for WhatsAppResult."""

    def test_sent_result(self):
        """Test successful result."""
        result = WhatsAppResult(
            status=DeliveryStatus.SENT,
            message_id="wamid.123",
            recipient="1234567890",
        )

        assert result.status == DeliveryStatus.SENT
        assert result.message_id == "wamid.123"
        assert result.error is None

    def test_failed_result(self):
        """Test failed result."""
        result = WhatsAppResult(
            status=DeliveryStatus.FAILED,
            error="Invalid recipient",
            error_code=100,
            recipient="1234567890",
        )

        assert result.status == DeliveryStatus.FAILED
        assert result.error == "Invalid recipient"
        assert result.error_code == 100

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = WhatsAppResult(
            status=DeliveryStatus.SENT,
            message_id="wamid.123",
            recipient="1234567890",
        )

        data = result.to_dict()

        assert data["status"] == "sent"
        assert data["message_id"] == "wamid.123"


class TestWhatsAppSender:
    """Test cases for WhatsAppSender class."""

    def test_initialization(self, whatsapp_config: WhatsAppConfig):
        """Test sender initialization."""
        sender = WhatsAppSender(config=whatsapp_config)

        assert sender.config == whatsapp_config

    def test_initialization_default_config(self):
        """Test sender with default config."""
        sender = WhatsAppSender()

        assert sender.config is not None

    def test_headers(self, whatsapp_sender: WhatsAppSender):
        """Test authorization headers."""
        headers = whatsapp_sender._headers

        assert "Authorization" in headers
        assert "Bearer" in headers["Authorization"]
        assert "Content-Type" in headers


class TestSendWhatsApp:
    """Test cases for send_whatsapp method."""

    def test_send_text_message(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
        successful_send_response,
    ):
        """Test sending a simple text message."""
        mock_session.post.return_value = successful_send_response

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        result = sender.send_whatsapp(
            to_number="1234567890",
            message="Hello, this is a test!",
        )

        assert result.status == DeliveryStatus.SENT
        assert result.message_id is not None
        mock_session.post.assert_called_once()

    def test_send_message_with_attachment(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
        successful_send_response,
        successful_upload_response,
        sample_attachment: str,
    ):
        """Test sending message with attachment."""
        # First call uploads media, second sends message, third sends document
        mock_session.post.side_effect = [
            successful_send_response,  # text message
            successful_upload_response,  # media upload
            successful_send_response,  # document message
        ]

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        result = sender.send_whatsapp(
            to_number="1234567890",
            message="Please see attached.",
            attachments=[sample_attachment],
        )

        assert result.status == DeliveryStatus.SENT
        assert mock_session.post.call_count == 3

    def test_send_message_failed(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
        failed_send_response,
    ):
        """Test handling of failed message."""
        mock_session.post.return_value = failed_send_response

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        result = sender.send_whatsapp(
            to_number="invalid",
            message="Test message",
        )

        assert result.status == DeliveryStatus.FAILED
        assert result.error == "Invalid recipient"
        assert result.error_code == 100

    def test_send_without_config(self):
        """Test error when API not configured."""
        config = WhatsAppConfig()  # Empty config
        sender = WhatsAppSender(config=config)

        result = sender.send_whatsapp(
            to_number="1234567890",
            message="Test",
        )

        assert result.status == DeliveryStatus.FAILED
        assert "not configured" in result.error

    def test_send_missing_attachment(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
        successful_send_response,
    ):
        """Test error for missing attachment file."""
        mock_session.post.return_value = successful_send_response

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        result = sender.send_whatsapp(
            to_number="1234567890",
            message="Test",
            attachments=["/nonexistent/file.pdf"],
        )

        assert result.status == DeliveryStatus.FAILED
        assert "not found" in result.error.lower()

    def test_send_timeout(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
    ):
        """Test handling of timeout."""
        mock_session.post.side_effect = requests.exceptions.Timeout()

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        result = sender.send_whatsapp(
            to_number="1234567890",
            message="Test",
        )

        assert result.status == DeliveryStatus.FAILED
        assert "timed out" in result.error.lower()

    def test_send_connection_error(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
    ):
        """Test handling of connection error."""
        mock_session.post.side_effect = requests.exceptions.ConnectionError()

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        result = sender.send_whatsapp(
            to_number="1234567890",
            message="Test",
        )

        assert result.status == DeliveryStatus.FAILED
        assert "connection" in result.error.lower()


class TestNormalizePhoneNumber:
    """Test cases for phone number normalization."""

    def test_removes_plus(self, whatsapp_sender: WhatsAppSender):
        """Test removal of plus sign."""
        result = whatsapp_sender._normalize_phone_number("+1234567890")
        assert result == "1234567890"

    def test_removes_dashes(self, whatsapp_sender: WhatsAppSender):
        """Test removal of dashes."""
        result = whatsapp_sender._normalize_phone_number("123-456-7890")
        assert result == "1234567890"

    def test_removes_spaces(self, whatsapp_sender: WhatsAppSender):
        """Test removal of spaces."""
        result = whatsapp_sender._normalize_phone_number("123 456 7890")
        assert result == "1234567890"

    def test_removes_parentheses(self, whatsapp_sender: WhatsAppSender):
        """Test removal of parentheses."""
        result = whatsapp_sender._normalize_phone_number("(123) 456-7890")
        assert result == "1234567890"

    def test_complex_format(self, whatsapp_sender: WhatsAppSender):
        """Test complex phone format."""
        result = whatsapp_sender._normalize_phone_number("+1 (555) 123-4567")
        assert result == "15551234567"


class TestGetMessageType:
    """Test cases for message type detection."""

    def test_pdf_is_document(self, whatsapp_sender: WhatsAppSender):
        """Test PDF detection."""
        result = whatsapp_sender._get_message_type(Path("file.pdf"))
        assert result == "document"

    def test_image_types(self, whatsapp_sender: WhatsAppSender):
        """Test image type detection."""
        assert whatsapp_sender._get_message_type(Path("file.jpg")) == "image"
        assert whatsapp_sender._get_message_type(Path("file.jpeg")) == "image"
        assert whatsapp_sender._get_message_type(Path("file.png")) == "image"
        assert whatsapp_sender._get_message_type(Path("file.gif")) == "image"

    def test_video_types(self, whatsapp_sender: WhatsAppSender):
        """Test video type detection."""
        assert whatsapp_sender._get_message_type(Path("file.mp4")) == "video"
        assert whatsapp_sender._get_message_type(Path("file.3gp")) == "video"

    def test_audio_types(self, whatsapp_sender: WhatsAppSender):
        """Test audio type detection."""
        assert whatsapp_sender._get_message_type(Path("file.mp3")) == "audio"
        assert whatsapp_sender._get_message_type(Path("file.ogg")) == "audio"

    def test_unknown_is_document(self, whatsapp_sender: WhatsAppSender):
        """Test unknown types default to document."""
        result = whatsapp_sender._get_message_type(Path("file.xyz"))
        assert result == "document"


class TestSendTemplate:
    """Test cases for template messages."""

    def test_send_template_message(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
        successful_send_response,
    ):
        """Test sending a template message."""
        mock_session.post.return_value = successful_send_response

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        result = sender.send_template(
            to_number="1234567890",
            template_name="audit_complete",
            language_code="en_US",
        )

        assert result.status == DeliveryStatus.SENT

        # Verify payload contains template
        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        assert payload["type"] == "template"
        assert payload["template"]["name"] == "audit_complete"

    def test_send_template_with_components(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
        successful_send_response,
    ):
        """Test sending template with components."""
        mock_session.post.return_value = successful_send_response

        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "John Doe"},
                    {"type": "text", "text": "$150.00"},
                ],
            }
        ]

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        result = sender.send_template(
            to_number="1234567890",
            template_name="audit_result",
            components=components,
        )

        assert result.status == DeliveryStatus.SENT

        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        assert "components" in payload["template"]


class TestSendBulk:
    """Test cases for bulk sending."""

    def test_send_to_multiple_recipients(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
        successful_send_response,
    ):
        """Test sending to multiple recipients."""
        mock_session.post.return_value = successful_send_response

        recipients = ["111", "222", "333"]

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        results = sender.send_bulk(
            recipients=recipients,
            message="Bulk test message",
        )

        assert len(results) == 3
        assert all(r.status == DeliveryStatus.SENT for r in results)
        assert mock_session.post.call_count == 3


class TestCheckHealth:
    """Test cases for health check."""

    def test_health_check_success(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
    ):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        result = sender.check_health()

        assert result is True

    def test_health_check_failure(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
    ):
        """Test failed health check."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_session.get.return_value = mock_response

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        result = sender.check_health()

        assert result is False

    def test_health_check_not_configured(self):
        """Test health check without configuration."""
        config = WhatsAppConfig()
        sender = WhatsAppSender(config=config)

        result = sender.check_health()

        assert result is False


class TestUploadMedia:
    """Test cases for media upload."""

    def test_upload_success(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
        successful_upload_response,
        sample_attachment: str,
    ):
        """Test successful media upload."""
        mock_session.post.return_value = successful_upload_response

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        media_id = sender._upload_media(sample_attachment)

        assert media_id == "media_id_12345"

    def test_upload_failure(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
        sample_attachment: str,
    ):
        """Test failed media upload."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Upload failed"
        mock_session.post.return_value = mock_response

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        media_id = sender._upload_media(sample_attachment)

        assert media_id is None


class TestConvenienceFunction:
    """Test cases for send_whatsapp convenience function."""

    def test_send_whatsapp_function(
        self,
        whatsapp_config: WhatsAppConfig,
    ):
        """Test standalone send_whatsapp function."""
        with patch.object(WhatsAppSender, "send_whatsapp") as mock_send:
            mock_send.return_value = WhatsAppResult(
                status=DeliveryStatus.SENT,
                message_id="test_id",
                recipient="1234567890",
            )

            result = send_whatsapp(
                to_number="1234567890",
                message="Test message",
                config=whatsapp_config,
            )

            assert result.status == DeliveryStatus.SENT


class TestIntegration:
    """Integration tests for WhatsApp sending."""

    def test_complete_message_flow(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
        successful_send_response,
        successful_upload_response,
        sample_attachment: str,
    ):
        """Test complete message sending flow."""
        mock_session.post.side_effect = [
            successful_send_response,  # text
            successful_upload_response,  # upload
            successful_send_response,  # document
        ]

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        result = sender.send_whatsapp(
            to_number="+1 (555) 123-4567",
            message="Your audit report is attached.",
            attachments=[sample_attachment],
        )

        assert result.status == DeliveryStatus.SENT
        assert mock_session.post.call_count == 3

    def test_image_attachment_flow(
        self,
        whatsapp_config: WhatsAppConfig,
        mock_session,
        successful_send_response,
        successful_upload_response,
        sample_image: str,
    ):
        """Test sending image attachment."""
        mock_session.post.side_effect = [
            successful_send_response,  # text
            successful_upload_response,  # upload
            successful_send_response,  # image
        ]

        sender = WhatsAppSender(config=whatsapp_config, session=mock_session)
        result = sender.send_whatsapp(
            to_number="1234567890",
            message="Check out this image.",
            attachments=[sample_image],
        )

        assert result.status == DeliveryStatus.SENT

        # Verify image message type was used
        calls = mock_session.post.call_args_list
        last_call = calls[-1]
        payload = last_call[1]["json"]
        assert payload["type"] == "image"

