"""
Negotiation orchestrator for managing letter generation and delivery.

Coordinates LLM-powered letter generation with multi-channel delivery
(email, WhatsApp) and handles retries and status tracking.
"""

import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, TypedDict
from pathlib import Path
import tempfile

# Add ML path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "ml"))

logger = logging.getLogger(__name__)


class DeliveryChannel(str, Enum):
    """Delivery channel options."""

    EMAIL = "email"
    WHATSAPP = "whatsapp"
    BOTH = "both"


class DeliveryStatus(str, Enum):
    """Delivery status options."""

    PENDING = "pending"
    SENT = "sent"
    PARTIALLY_SENT = "partially_sent"
    FAILED = "failed"
    RETRYING = "retrying"


class ChannelResult(TypedDict):
    """Result for a single channel delivery."""

    channel: str
    status: str
    message_id: Optional[str]
    error: Optional[str]
    timestamp: str


class NegotiationResult(TypedDict):
    """Result of negotiation execution."""

    document_id: int
    status: str
    letter_generated: bool
    channels: list[ChannelResult]
    retry_count: int
    total_attempts: int
    timestamp: str
    error: Optional[str]


@dataclass
class RecipientInfo:
    """Recipient contact information."""

    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    provider_name: Optional[str] = None
    account_number: Optional[str] = None
    date_of_service: Optional[str] = None


@dataclass
class OrchestratorConfig:
    """Configuration for negotiation orchestrator."""

    max_retries: int = 3
    retry_delay_seconds: int = 60
    save_letter_to_db: bool = True
    attach_audit_report: bool = True
    email_subject_template: str = "Medical Bill Dispute - Account {account_number}"
    
    # Feature flags
    enable_email: bool = True
    enable_whatsapp: bool = True


class NegotiationOrchestrator:
    """
    Orchestrates the negotiation letter workflow.

    Coordinates:
    - LLM-powered letter generation
    - Multi-channel delivery (email, WhatsApp)
    - Retry logic for failed deliveries
    - Status tracking and logging
    """

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        db_session=None,
        email_sender=None,
        whatsapp_sender=None,
    ):
        """
        Initialize the orchestrator.

        Args:
            config: Orchestrator configuration.
            db_session: Database session for persistence.
            email_sender: Email sender service instance.
            whatsapp_sender: WhatsApp sender service instance.
        """
        self.config = config or OrchestratorConfig()
        self.db_session = db_session
        self.email_sender = email_sender
        self.whatsapp_sender = whatsapp_sender

    def execute_negotiation(
        self,
        document_id: int,
        channel: str,
        tone: str,
        recipient: Optional[RecipientInfo] = None,
        audit_json: Optional[dict] = None,
    ) -> NegotiationResult:
        """
        Execute the full negotiation workflow.

        Generates a negotiation letter using LLM and delivers it
        through the specified channel(s).

        Args:
            document_id: ID of the document being disputed.
            channel: Delivery channel ("email", "whatsapp", "both").
            tone: Letter tone ("formal", "friendly", "assertive").
            recipient: Recipient contact information.
            audit_json: Audit results for letter generation.

        Returns:
            NegotiationResult: Execution result with status and details.

        Example:
            >>> orchestrator = NegotiationOrchestrator()
            >>> result = orchestrator.execute_negotiation(
            ...     document_id=123,
            ...     channel="email",
            ...     tone="formal",
            ...     recipient=RecipientInfo(email="billing@hospital.com"),
            ...     audit_json=audit_results,
            ... )
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        logger.info(
            f"Starting negotiation for document {document_id}, "
            f"channel={channel}, tone={tone}"
        )

        # Validate channel
        try:
            delivery_channel = DeliveryChannel(channel.lower())
        except ValueError:
            return self._error_result(
                document_id,
                f"Invalid channel: {channel}. Must be 'email', 'whatsapp', or 'both'",
                timestamp,
            )

        # Validate tone
        valid_tones = ["formal", "friendly", "assertive"]
        if tone.lower() not in valid_tones:
            return self._error_result(
                document_id,
                f"Invalid tone: {tone}. Must be one of {valid_tones}",
                timestamp,
            )

        # Get audit data if not provided
        if audit_json is None:
            audit_json = self._fetch_audit_data(document_id)
            if audit_json is None:
                return self._error_result(
                    document_id,
                    "Could not fetch audit data for document",
                    timestamp,
                )

        # Generate letter
        letter_content = self._generate_letter(audit_json, tone, recipient)
        if letter_content is None:
            return self._error_result(
                document_id,
                "Failed to generate negotiation letter",
                timestamp,
            )

        logger.info(f"Letter generated for document {document_id}")

        # Deliver through channel(s)
        channel_results = []
        retry_count = 0

        if delivery_channel in (DeliveryChannel.EMAIL, DeliveryChannel.BOTH):
            if self.config.enable_email and recipient and recipient.email:
                email_result = self._deliver_email(
                    letter_content,
                    recipient,
                    audit_json,
                    document_id,
                )
                channel_results.append(email_result)

                # Retry if failed
                while (
                    email_result["status"] == "failed"
                    and retry_count < self.config.max_retries
                ):
                    retry_count += 1
                    logger.info(
                        f"Retrying email delivery, attempt {retry_count + 1}"
                    )
                    email_result = self._deliver_email(
                        letter_content,
                        recipient,
                        audit_json,
                        document_id,
                    )
                    channel_results[-1] = email_result

        if delivery_channel in (DeliveryChannel.WHATSAPP, DeliveryChannel.BOTH):
            if self.config.enable_whatsapp and recipient and recipient.phone:
                whatsapp_result = self._deliver_whatsapp(
                    letter_content,
                    recipient,
                    document_id,
                )
                channel_results.append(whatsapp_result)

                # Retry if failed
                wa_retry_count = 0
                while (
                    whatsapp_result["status"] == "failed"
                    and wa_retry_count < self.config.max_retries
                ):
                    wa_retry_count += 1
                    retry_count = max(retry_count, wa_retry_count)
                    logger.info(
                        f"Retrying WhatsApp delivery, attempt {wa_retry_count + 1}"
                    )
                    whatsapp_result = self._deliver_whatsapp(
                        letter_content,
                        recipient,
                        document_id,
                    )
                    channel_results[-1] = whatsapp_result

        # Determine overall status
        if not channel_results:
            overall_status = DeliveryStatus.FAILED
            error = "No valid delivery channel configured or recipient info missing"
        elif all(r["status"] == "sent" for r in channel_results):
            overall_status = DeliveryStatus.SENT
            error = None
        elif any(r["status"] == "sent" for r in channel_results):
            overall_status = DeliveryStatus.PARTIALLY_SENT
            error = "Some channels failed"
        else:
            overall_status = DeliveryStatus.FAILED
            error = "; ".join(r.get("error", "") for r in channel_results if r.get("error"))

        # Save to database
        if self.config.save_letter_to_db:
            self._save_negotiation(
                document_id=document_id,
                channel=channel,
                tone=tone,
                letter_content=letter_content,
                recipient=recipient,
                status=overall_status,
                retry_count=retry_count,
                error=error,
            )

        result = NegotiationResult(
            document_id=document_id,
            status=overall_status.value,
            letter_generated=True,
            channels=channel_results,
            retry_count=retry_count,
            total_attempts=retry_count + 1,
            timestamp=timestamp,
            error=error,
        )

        logger.info(
            f"Negotiation complete for document {document_id}: "
            f"status={overall_status.value}, retries={retry_count}"
        )

        return result

    def _generate_letter(
        self,
        audit_json: dict,
        tone: str,
        recipient: Optional[RecipientInfo],
    ) -> Optional[str]:
        """
        Generate negotiation letter using LLM.

        Args:
            audit_json: Audit results.
            tone: Letter tone.
            recipient: Recipient information.

        Returns:
            Optional[str]: Generated letter or None if failed.
        """
        try:
            from llm.negotiation_letter import generate_letter

            # Build patient info from recipient
            patient_info = None
            if recipient:
                patient_info = {
                    "patient_name": recipient.name or "[PATIENT NAME]",
                    "account_number": recipient.account_number or "[ACCOUNT NUMBER]",
                    "date_of_service": recipient.date_of_service or "[DATE OF SERVICE]",
                    "provider_name": recipient.provider_name or "[PROVIDER NAME]",
                }

            letter = generate_letter(
                parsed_audit_json=audit_json,
                tone=tone,
                patient_info=patient_info,
            )

            return letter

        except Exception as e:
            logger.exception(f"Letter generation failed: {e}")
            return None

    def _deliver_email(
        self,
        letter_content: str,
        recipient: RecipientInfo,
        audit_json: dict,
        document_id: int,
    ) -> ChannelResult:
        """
        Deliver letter via email.

        Args:
            letter_content: Generated letter text.
            recipient: Recipient information.
            audit_json: Audit data for attachments.
            document_id: Document ID.

        Returns:
            ChannelResult: Delivery result.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        if not recipient.email:
            return ChannelResult(
                channel="email",
                status="failed",
                message_id=None,
                error="No email address provided",
                timestamp=timestamp,
            )

        try:
            # Use injected sender or create new one
            if self.email_sender:
                sender = self.email_sender
            else:
                from app.services.email_sender import EmailSender
                sender = EmailSender()

            # Build subject
            subject = self.config.email_subject_template.format(
                account_number=recipient.account_number or document_id,
            )

            # Prepare attachments
            attachments = []
            if self.config.attach_audit_report:
                # Create temp file with audit summary
                audit_file = self._create_audit_attachment(audit_json, document_id)
                if audit_file:
                    attachments.append(audit_file)

            # Send email
            result = sender.send_email(
                to_email=recipient.email,
                subject=subject,
                body=letter_content,
                attachments=attachments,
            )

            # Clean up temp files
            for attachment in attachments:
                try:
                    Path(attachment).unlink(missing_ok=True)
                except Exception:
                    pass

            if result.status.value == "sent":
                logger.info(f"Email sent successfully to {recipient.email}")
                return ChannelResult(
                    channel="email",
                    status="sent",
                    message_id=result.message_id,
                    error=None,
                    timestamp=timestamp,
                )
            else:
                logger.error(f"Email failed: {result.error}")
                return ChannelResult(
                    channel="email",
                    status="failed",
                    message_id=None,
                    error=result.error,
                    timestamp=timestamp,
                )

        except Exception as e:
            logger.exception(f"Email delivery error: {e}")
            return ChannelResult(
                channel="email",
                status="failed",
                message_id=None,
                error=str(e),
                timestamp=timestamp,
            )

    def _deliver_whatsapp(
        self,
        letter_content: str,
        recipient: RecipientInfo,
        document_id: int,
    ) -> ChannelResult:
        """
        Deliver letter via WhatsApp.

        Args:
            letter_content: Generated letter text.
            recipient: Recipient information.
            document_id: Document ID.

        Returns:
            ChannelResult: Delivery result.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        if not recipient.phone:
            return ChannelResult(
                channel="whatsapp",
                status="failed",
                message_id=None,
                error="No phone number provided",
                timestamp=timestamp,
            )

        try:
            # Use injected sender or create new one
            if self.whatsapp_sender:
                sender = self.whatsapp_sender
            else:
                from app.services.whatsapp_sender import WhatsAppSender
                sender = WhatsAppSender()

            # WhatsApp has message length limits, may need to split
            # For now, send as single message (max ~4096 chars)
            message = letter_content[:4000] if len(letter_content) > 4000 else letter_content

            result = sender.send_whatsapp(
                to_number=recipient.phone,
                message=message,
            )

            if result.status.value == "sent":
                logger.info(f"WhatsApp sent successfully to {recipient.phone}")
                return ChannelResult(
                    channel="whatsapp",
                    status="sent",
                    message_id=result.message_id,
                    error=None,
                    timestamp=timestamp,
                )
            else:
                logger.error(f"WhatsApp failed: {result.error}")
                return ChannelResult(
                    channel="whatsapp",
                    status="failed",
                    message_id=None,
                    error=result.error,
                    timestamp=timestamp,
                )

        except Exception as e:
            logger.exception(f"WhatsApp delivery error: {e}")
            return ChannelResult(
                channel="whatsapp",
                status="failed",
                message_id=None,
                error=str(e),
                timestamp=timestamp,
            )

    def _create_audit_attachment(
        self,
        audit_json: dict,
        document_id: int,
    ) -> Optional[str]:
        """
        Create audit summary attachment file.

        Args:
            audit_json: Audit data.
            document_id: Document ID.

        Returns:
            Optional[str]: Path to temp file or None.
        """
        try:
            import json

            # Create formatted audit summary
            summary = f"""MEDICAL BILL AUDIT REPORT
Document ID: {document_id}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

AUDIT SCORE: {audit_json.get('score', 'N/A')}/100

SUMMARY:
- Total Issues Found: {audit_json.get('total_issues', 0)}
- Critical Issues: {audit_json.get('critical_count', 0)}
- High Severity: {audit_json.get('high_count', 0)}
- Medium Severity: {audit_json.get('medium_count', 0)}
- Low Severity: {audit_json.get('low_count', 0)}
- Potential Savings: ${audit_json.get('potential_savings', 0):.2f}

ISSUES DETAIL:
"""
            for i, issue in enumerate(audit_json.get('issues', []), 1):
                summary += f"""
{i}. [{issue.get('severity', 'unknown').upper()}] {issue.get('type', 'Unknown')}
   Description: {issue.get('description', 'No description')}
   Impact: ${issue.get('amount_impact', 0) or 0:.2f}
"""

            # Write to temp file
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.txt',
                prefix=f'audit_report_{document_id}_',
                delete=False,
            )
            temp_file.write(summary)
            temp_file.close()

            return temp_file.name

        except Exception as e:
            logger.error(f"Failed to create audit attachment: {e}")
            return None

    def _fetch_audit_data(self, document_id: int) -> Optional[dict]:
        """
        Fetch audit data from database.

        Args:
            document_id: Document ID.

        Returns:
            Optional[dict]: Audit data or None.
        """
        if not self.db_session:
            logger.warning("No database session, cannot fetch audit data")
            return None

        try:
            # This would fetch from ParsedField and run audit
            # For now, return None to indicate data should be provided
            logger.warning("Audit data fetch not implemented, provide audit_json")
            return None

        except Exception as e:
            logger.error(f"Failed to fetch audit data: {e}")
            return None

    def _save_negotiation(
        self,
        document_id: int,
        channel: str,
        tone: str,
        letter_content: str,
        recipient: Optional[RecipientInfo],
        status: DeliveryStatus,
        retry_count: int,
        error: Optional[str],
    ) -> None:
        """
        Save negotiation record to database.

        Args:
            document_id: Document ID.
            channel: Delivery channel.
            tone: Letter tone.
            letter_content: Generated letter.
            recipient: Recipient info.
            status: Delivery status.
            retry_count: Number of retries.
            error: Error message if failed.
        """
        if not self.db_session:
            logger.warning("No database session, skipping save")
            return

        try:
            from app.models.negotiation import (
                Negotiation,
                NegotiationStatus,
                DeliveryChannel as DBDeliveryChannel,
            )

            negotiation = Negotiation(
                document_id=document_id,
                user_id=1,  # TODO: Get from context
                channel=DBDeliveryChannel(channel),
                tone=tone,
                status=NegotiationStatus(status.value),
                letter_content=letter_content,
                recipient_email=recipient.email if recipient else None,
                recipient_phone=recipient.phone if recipient else None,
                retry_count=retry_count,
                last_error=error,
                sent_at=datetime.now(timezone.utc) if status == DeliveryStatus.SENT else None,
            )

            self.db_session.add(negotiation)
            self.db_session.commit()

            logger.info(f"Saved negotiation record: {negotiation.id}")

        except Exception as e:
            logger.error(f"Failed to save negotiation: {e}")

    def _error_result(
        self,
        document_id: int,
        error: str,
        timestamp: str,
    ) -> NegotiationResult:
        """Create error result."""
        logger.error(f"Negotiation error for document {document_id}: {error}")
        return NegotiationResult(
            document_id=document_id,
            status=DeliveryStatus.FAILED.value,
            letter_generated=False,
            channels=[],
            retry_count=0,
            total_attempts=1,
            timestamp=timestamp,
            error=error,
        )

    def retry_failed(self, negotiation_id: int) -> NegotiationResult:
        """
        Retry a failed negotiation.

        Args:
            negotiation_id: ID of failed negotiation to retry.

        Returns:
            NegotiationResult: Retry result.
        """
        if not self.db_session:
            return self._error_result(
                0,
                "No database session for retry",
                datetime.now(timezone.utc).isoformat(),
            )

        try:
            from app.models.negotiation import Negotiation

            negotiation = self.db_session.query(Negotiation).filter(
                Negotiation.id == negotiation_id
            ).first()

            if not negotiation:
                return self._error_result(
                    0,
                    f"Negotiation {negotiation_id} not found",
                    datetime.now(timezone.utc).isoformat(),
                )

            if not negotiation.can_retry():
                return self._error_result(
                    negotiation.document_id,
                    f"Cannot retry: max retries ({negotiation.max_retries}) exceeded",
                    datetime.now(timezone.utc).isoformat(),
                )

            # Build recipient from saved data
            recipient = RecipientInfo(
                email=negotiation.recipient_email,
                phone=negotiation.recipient_phone,
            )

            # Execute retry
            return self.execute_negotiation(
                document_id=negotiation.document_id,
                channel=negotiation.channel.value,
                tone=negotiation.tone,
                recipient=recipient,
            )

        except Exception as e:
            logger.exception(f"Retry failed: {e}")
            return self._error_result(
                0,
                str(e),
                datetime.now(timezone.utc).isoformat(),
            )


# Convenience function
def execute_negotiation(
    document_id: int,
    channel: str,
    tone: str,
    recipient: Optional[RecipientInfo] = None,
    audit_json: Optional[dict] = None,
    config: Optional[OrchestratorConfig] = None,
) -> NegotiationResult:
    """
    Execute negotiation workflow.

    Convenience function that creates an orchestrator and
    executes the full negotiation workflow.

    Args:
        document_id: Document ID.
        channel: Delivery channel.
        tone: Letter tone.
        recipient: Recipient information.
        audit_json: Audit results.
        config: Optional configuration.

    Returns:
        NegotiationResult: Execution result.
    """
    orchestrator = NegotiationOrchestrator(config=config)
    return orchestrator.execute_negotiation(
        document_id=document_id,
        channel=channel,
        tone=tone,
        recipient=recipient,
        audit_json=audit_json,
    )

