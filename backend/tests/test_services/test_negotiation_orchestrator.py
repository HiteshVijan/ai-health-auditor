"""
Unit tests for negotiation orchestrator.

Tests the full negotiation workflow with synthetic audit JSON.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
import sys
import os

# Add backend directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.negotiation_orchestrator import (
    NegotiationOrchestrator,
    OrchestratorConfig,
    RecipientInfo,
    DeliveryChannel,
    DeliveryStatus,
    NegotiationResult,
    ChannelResult,
    execute_negotiation,
)


@pytest.fixture
def sample_audit_json() -> dict:
    """Create synthetic audit JSON for testing."""
    return {
        "score": 65,
        "total_issues": 4,
        "critical_count": 1,
        "high_count": 2,
        "medium_count": 1,
        "low_count": 0,
        "potential_savings": 275.50,
        "issues": [
            {
                "id": 1,
                "type": "arithmetic_mismatch",
                "severity": "critical",
                "description": "Calculated total ($500.00) does not match stated total ($550.00)",
                "amount_impact": 50.00,
            },
            {
                "id": 2,
                "type": "duplicate_charge",
                "severity": "high",
                "description": "Duplicate charge detected: 'CBC' appears 2 times",
                "amount_impact": 45.00,
            },
            {
                "id": 3,
                "type": "overcharge",
                "severity": "high",
                "description": "Potential overcharge for 'Office Visit': $350.00 exceeds expected $175.00",
                "amount_impact": 175.00,
            },
            {
                "id": 4,
                "type": "tax_mismatch",
                "severity": "medium",
                "description": "Tax rate 18.0% is outside normal range",
                "amount_impact": 5.50,
            },
        ],
    }


@pytest.fixture
def sample_recipient() -> RecipientInfo:
    """Create sample recipient information."""
    return RecipientInfo(
        email="billing@hospital.com",
        phone="15551234567",
        name="John Doe",
        provider_name="City Hospital",
        account_number="ACC-123456",
        date_of_service="2024-01-15",
    )


@pytest.fixture
def orchestrator_config() -> OrchestratorConfig:
    """Create test orchestrator configuration."""
    return OrchestratorConfig(
        max_retries=3,
        retry_delay_seconds=1,
        save_letter_to_db=False,
        attach_audit_report=False,
        enable_email=True,
        enable_whatsapp=True,
    )


@pytest.fixture
def mock_email_sender():
    """Create mock email sender."""
    sender = MagicMock()
    result = MagicMock()
    result.status.value = "sent"
    result.message_id = "email-123"
    result.error = None
    sender.send_email.return_value = result
    return sender


@pytest.fixture
def mock_whatsapp_sender():
    """Create mock WhatsApp sender."""
    sender = MagicMock()
    result = MagicMock()
    result.status.value = "sent"
    result.message_id = "wamid-456"
    result.error = None
    sender.send_whatsapp.return_value = result
    return sender


@pytest.fixture
def mock_failed_email_sender():
    """Create mock email sender that fails."""
    sender = MagicMock()
    result = MagicMock()
    result.status.value = "failed"
    result.message_id = None
    result.error = "Connection refused"
    sender.send_email.return_value = result
    return sender


@pytest.fixture
def orchestrator(
    orchestrator_config: OrchestratorConfig,
    mock_email_sender,
    mock_whatsapp_sender,
) -> NegotiationOrchestrator:
    """Create orchestrator with mocked senders."""
    return NegotiationOrchestrator(
        config=orchestrator_config,
        email_sender=mock_email_sender,
        whatsapp_sender=mock_whatsapp_sender,
    )


class TestOrchestratorConfig:
    """Test cases for orchestrator configuration."""

    def test_default_values(self):
        """Test default configuration values."""
        config = OrchestratorConfig()

        assert config.max_retries == 3
        assert config.save_letter_to_db is True
        assert config.enable_email is True
        assert config.enable_whatsapp is True

    def test_custom_values(self):
        """Test custom configuration."""
        config = OrchestratorConfig(
            max_retries=5,
            save_letter_to_db=False,
        )

        assert config.max_retries == 5
        assert config.save_letter_to_db is False


class TestRecipientInfo:
    """Test cases for recipient information."""

    def test_full_recipient(self, sample_recipient: RecipientInfo):
        """Test recipient with all fields."""
        assert sample_recipient.email == "billing@hospital.com"
        assert sample_recipient.phone == "15551234567"
        assert sample_recipient.name == "John Doe"

    def test_partial_recipient(self):
        """Test recipient with partial info."""
        recipient = RecipientInfo(email="test@test.com")

        assert recipient.email == "test@test.com"
        assert recipient.phone is None


class TestExecuteNegotiation:
    """Test cases for execute_negotiation method."""

    def test_email_channel_success(
        self,
        orchestrator: NegotiationOrchestrator,
        sample_audit_json: dict,
        sample_recipient: RecipientInfo,
    ):
        """Test successful email delivery."""
        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = "Generated letter content"

            result = orchestrator.execute_negotiation(
                document_id=123,
                channel="email",
                tone="formal",
                recipient=sample_recipient,
                audit_json=sample_audit_json,
            )

            assert result["status"] == "sent"
            assert result["letter_generated"] is True
            assert len(result["channels"]) == 1
            assert result["channels"][0]["channel"] == "email"
            assert result["channels"][0]["status"] == "sent"

    def test_whatsapp_channel_success(
        self,
        orchestrator: NegotiationOrchestrator,
        sample_audit_json: dict,
        sample_recipient: RecipientInfo,
    ):
        """Test successful WhatsApp delivery."""
        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = "Generated letter content"

            result = orchestrator.execute_negotiation(
                document_id=123,
                channel="whatsapp",
                tone="friendly",
                recipient=sample_recipient,
                audit_json=sample_audit_json,
            )

            assert result["status"] == "sent"
            assert result["channels"][0]["channel"] == "whatsapp"

    def test_both_channels_success(
        self,
        orchestrator: NegotiationOrchestrator,
        sample_audit_json: dict,
        sample_recipient: RecipientInfo,
    ):
        """Test successful delivery on both channels."""
        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = "Generated letter content"

            result = orchestrator.execute_negotiation(
                document_id=123,
                channel="both",
                tone="assertive",
                recipient=sample_recipient,
                audit_json=sample_audit_json,
            )

            assert result["status"] == "sent"
            assert len(result["channels"]) == 2

    def test_invalid_channel(
        self,
        orchestrator: NegotiationOrchestrator,
        sample_audit_json: dict,
        sample_recipient: RecipientInfo,
    ):
        """Test error for invalid channel."""
        result = orchestrator.execute_negotiation(
            document_id=123,
            channel="fax",  # Invalid
            tone="formal",
            recipient=sample_recipient,
            audit_json=sample_audit_json,
        )

        assert result["status"] == "failed"
        assert "Invalid channel" in result["error"]

    def test_invalid_tone(
        self,
        orchestrator: NegotiationOrchestrator,
        sample_audit_json: dict,
        sample_recipient: RecipientInfo,
    ):
        """Test error for invalid tone."""
        result = orchestrator.execute_negotiation(
            document_id=123,
            channel="email",
            tone="angry",  # Invalid
            recipient=sample_recipient,
            audit_json=sample_audit_json,
        )

        assert result["status"] == "failed"
        assert "Invalid tone" in result["error"]

    def test_letter_generation_failure(
        self,
        orchestrator: NegotiationOrchestrator,
        sample_audit_json: dict,
        sample_recipient: RecipientInfo,
    ):
        """Test handling of letter generation failure."""
        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = None  # Simulate failure

            result = orchestrator.execute_negotiation(
                document_id=123,
                channel="email",
                tone="formal",
                recipient=sample_recipient,
                audit_json=sample_audit_json,
            )

            assert result["status"] == "failed"
            assert "Failed to generate" in result["error"]

    def test_missing_recipient_email(
        self,
        orchestrator: NegotiationOrchestrator,
        sample_audit_json: dict,
    ):
        """Test handling of missing email for email channel."""
        recipient = RecipientInfo(phone="1234567890")  # No email

        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = "Generated letter"

            result = orchestrator.execute_negotiation(
                document_id=123,
                channel="email",
                tone="formal",
                recipient=recipient,
                audit_json=sample_audit_json,
            )

            # Should fail due to no email
            assert result["status"] == "failed"

    def test_missing_recipient_phone(
        self,
        orchestrator: NegotiationOrchestrator,
        sample_audit_json: dict,
    ):
        """Test handling of missing phone for WhatsApp channel."""
        recipient = RecipientInfo(email="test@test.com")  # No phone

        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = "Generated letter"

            result = orchestrator.execute_negotiation(
                document_id=123,
                channel="whatsapp",
                tone="formal",
                recipient=recipient,
                audit_json=sample_audit_json,
            )

            assert result["status"] == "failed"


class TestRetryLogic:
    """Test cases for retry functionality."""

    def test_retry_on_email_failure(
        self,
        orchestrator_config: OrchestratorConfig,
        mock_failed_email_sender,
        sample_audit_json: dict,
        sample_recipient: RecipientInfo,
    ):
        """Test that failed emails are retried."""
        orchestrator = NegotiationOrchestrator(
            config=orchestrator_config,
            email_sender=mock_failed_email_sender,
        )

        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = "Generated letter"

            result = orchestrator.execute_negotiation(
                document_id=123,
                channel="email",
                tone="formal",
                recipient=sample_recipient,
                audit_json=sample_audit_json,
            )

            # Should have retried max_retries times
            assert result["retry_count"] == orchestrator_config.max_retries
            assert result["total_attempts"] == orchestrator_config.max_retries + 1

    def test_retry_succeeds_eventually(
        self,
        orchestrator_config: OrchestratorConfig,
        sample_audit_json: dict,
        sample_recipient: RecipientInfo,
    ):
        """Test that retry succeeds after initial failure."""
        # Create sender that fails first, then succeeds
        sender = MagicMock()
        fail_result = MagicMock()
        fail_result.status.value = "failed"
        fail_result.message_id = None
        fail_result.error = "Temporary error"

        success_result = MagicMock()
        success_result.status.value = "sent"
        success_result.message_id = "email-123"
        success_result.error = None

        sender.send_email.side_effect = [fail_result, success_result]

        orchestrator = NegotiationOrchestrator(
            config=orchestrator_config,
            email_sender=sender,
        )

        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = "Generated letter"

            result = orchestrator.execute_negotiation(
                document_id=123,
                channel="email",
                tone="formal",
                recipient=sample_recipient,
                audit_json=sample_audit_json,
            )

            assert result["status"] == "sent"
            assert result["retry_count"] == 1


class TestPartialSuccess:
    """Test cases for partial delivery success."""

    def test_partial_success_both_channels(
        self,
        orchestrator_config: OrchestratorConfig,
        mock_email_sender,
        mock_failed_email_sender,
        mock_whatsapp_sender,
        sample_audit_json: dict,
        sample_recipient: RecipientInfo,
    ):
        """Test partial success when one channel fails."""
        # Email fails, WhatsApp succeeds
        orchestrator = NegotiationOrchestrator(
            config=orchestrator_config,
            email_sender=mock_failed_email_sender,
            whatsapp_sender=mock_whatsapp_sender,
        )

        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = "Generated letter"

            result = orchestrator.execute_negotiation(
                document_id=123,
                channel="both",
                tone="formal",
                recipient=sample_recipient,
                audit_json=sample_audit_json,
            )

            assert result["status"] == "partially_sent"
            assert len(result["channels"]) == 2


class TestLogging:
    """Test cases for logging functionality."""

    def test_logs_delivery_status(
        self,
        orchestrator: NegotiationOrchestrator,
        sample_audit_json: dict,
        sample_recipient: RecipientInfo,
        caplog,
    ):
        """Test that delivery status is logged."""
        import logging

        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = "Generated letter"

            with caplog.at_level(logging.INFO):
                orchestrator.execute_negotiation(
                    document_id=123,
                    channel="email",
                    tone="formal",
                    recipient=sample_recipient,
                    audit_json=sample_audit_json,
                )

            assert "Starting negotiation" in caplog.text
            assert "123" in caplog.text

    def test_logs_timestamp(
        self,
        orchestrator: NegotiationOrchestrator,
        sample_audit_json: dict,
        sample_recipient: RecipientInfo,
    ):
        """Test that result includes timestamp."""
        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = "Generated letter"

            result = orchestrator.execute_negotiation(
                document_id=123,
                channel="email",
                tone="formal",
                recipient=sample_recipient,
                audit_json=sample_audit_json,
            )

            assert "timestamp" in result
            assert result["timestamp"] is not None


class TestAuditAttachment:
    """Test cases for audit report attachment."""

    def test_creates_audit_attachment(
        self,
        orchestrator: NegotiationOrchestrator,
        sample_audit_json: dict,
    ):
        """Test audit attachment creation."""
        attachment_path = orchestrator._create_audit_attachment(
            sample_audit_json,
            document_id=123,
        )

        assert attachment_path is not None

        # Read and verify content
        with open(attachment_path, 'r') as f:
            content = f.read()

        assert "AUDIT SCORE: 65" in content
        assert "Total Issues Found: 4" in content
        assert "275.50" in content

        # Clean up
        import os
        os.unlink(attachment_path)


class TestConvenienceFunction:
    """Test cases for execute_negotiation convenience function."""

    def test_convenience_function(self, sample_audit_json: dict):
        """Test standalone function."""
        recipient = RecipientInfo(email="test@test.com")
        config = OrchestratorConfig(
            enable_email=False,
            enable_whatsapp=False,
        )

        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = "Generated letter"

            result = execute_negotiation(
                document_id=123,
                channel="email",
                tone="formal",
                recipient=recipient,
                audit_json=sample_audit_json,
                config=config,
            )

            # Should fail due to disabled channels
            assert result["status"] == "failed"


class TestIntegration:
    """Integration tests for complete workflow."""

    def test_full_email_workflow(
        self,
        orchestrator_config: OrchestratorConfig,
        mock_email_sender,
        sample_audit_json: dict,
    ):
        """Test complete email workflow."""
        recipient = RecipientInfo(
            email="billing@hospital.com",
            name="John Doe",
            account_number="ACC-123",
            provider_name="City Hospital",
            date_of_service="2024-01-15",
        )

        orchestrator = NegotiationOrchestrator(
            config=orchestrator_config,
            email_sender=mock_email_sender,
        )

        with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
            mock_gen.return_value = """Dear Billing Department,

I am writing to dispute charges on my medical bill...

Sincerely,
John Doe"""

            result = orchestrator.execute_negotiation(
                document_id=123,
                channel="email",
                tone="formal",
                recipient=recipient,
                audit_json=sample_audit_json,
            )

            assert result["status"] == "sent"
            assert result["letter_generated"] is True
            assert result["document_id"] == 123

            # Verify email was called with letter content
            mock_email_sender.send_email.assert_called_once()
            call_args = mock_email_sender.send_email.call_args
            assert "billing@hospital.com" in str(call_args)

    def test_all_tones(
        self,
        orchestrator: NegotiationOrchestrator,
        sample_audit_json: dict,
        sample_recipient: RecipientInfo,
    ):
        """Test all tone options work."""
        tones = ["formal", "friendly", "assertive"]

        for tone in tones:
            with patch("app.services.negotiation_orchestrator.generate_letter") as mock_gen:
                mock_gen.return_value = f"Letter in {tone} tone"

                result = orchestrator.execute_negotiation(
                    document_id=123,
                    channel="email",
                    tone=tone,
                    recipient=sample_recipient,
                    audit_json=sample_audit_json,
                )

                assert result["status"] == "sent", f"Failed for tone: {tone}"

