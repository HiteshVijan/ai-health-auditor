"""
Email sending service using SMTP.

Provides functionality to send emails with attachments
for notifications and letter delivery.
"""

import logging
import os
import smtplib
import ssl
from dataclasses import dataclass
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DeliveryStatus(str, Enum):
    """Email delivery status."""

    SENT = "sent"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class EmailResult:
    """Result of email sending operation."""

    status: DeliveryStatus
    message_id: Optional[str] = None
    error: Optional[str] = None
    recipients: list[str] = None

    def __post_init__(self):
        if self.recipients is None:
            self.recipients = []

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "status": self.status.value,
            "message_id": self.message_id,
            "error": self.error,
            "recipients": self.recipients,
        }


@dataclass
class SMTPConfig:
    """SMTP server configuration."""

    host: str = "localhost"
    port: int = 587
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True
    use_ssl: bool = False
    timeout: int = 30
    from_email: str = "noreply@healthauditor.com"
    from_name: str = "Health Bill Auditor"

    @classmethod
    def from_env(cls) -> "SMTPConfig":
        """
        Create config from environment variables.

        Environment variables:
            SMTP_HOST: SMTP server hostname
            SMTP_PORT: SMTP server port
            SMTP_USERNAME: SMTP authentication username
            SMTP_PASSWORD: SMTP authentication password
            SMTP_USE_TLS: Use STARTTLS (default: true)
            SMTP_USE_SSL: Use SSL/TLS (default: false)
            SMTP_FROM_EMAIL: Sender email address
            SMTP_FROM_NAME: Sender display name

        Returns:
            SMTPConfig: Configuration instance.
        """
        return cls(
            host=os.getenv("SMTP_HOST", "localhost"),
            port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USERNAME"),
            password=os.getenv("SMTP_PASSWORD"),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            use_ssl=os.getenv("SMTP_USE_SSL", "false").lower() == "true",
            timeout=int(os.getenv("SMTP_TIMEOUT", "30")),
            from_email=os.getenv("SMTP_FROM_EMAIL", "noreply@healthauditor.com"),
            from_name=os.getenv("SMTP_FROM_NAME", "Health Bill Auditor"),
        )


class EmailSender:
    """
    Email sender service using SMTP.

    Handles email composition and delivery with support for
    HTML content and file attachments.
    """

    def __init__(self, config: Optional[SMTPConfig] = None):
        """
        Initialize email sender.

        Args:
            config: SMTP configuration. Uses environment if None.
        """
        self.config = config or SMTPConfig.from_env()

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: Optional[list[str]] = None,
        html_body: Optional[str] = None,
        cc: Optional[list[str]] = None,
        bcc: Optional[list[str]] = None,
        reply_to: Optional[str] = None,
    ) -> EmailResult:
        """
        Send an email with optional attachments.

        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            body: Plain text email body.
            attachments: List of file paths to attach.
            html_body: Optional HTML version of body.
            cc: Carbon copy recipients.
            bcc: Blind carbon copy recipients.
            reply_to: Reply-to email address.

        Returns:
            EmailResult: Delivery status and details.

        Example:
            >>> sender = EmailSender()
            >>> result = sender.send_email(
            ...     to_email="patient@example.com",
            ...     subject="Your Bill Audit Results",
            ...     body="Please find your audit report attached.",
            ...     attachments=["report.pdf"]
            ... )
            >>> print(result.status)
            DeliveryStatus.SENT
        """
        attachments = attachments or []
        cc = cc or []
        bcc = bcc or []

        logger.info(f"Sending email to {to_email}: {subject}")

        try:
            # Create message
            message = self._create_message(
                to_email=to_email,
                subject=subject,
                body=body,
                html_body=html_body,
                cc=cc,
                reply_to=reply_to,
            )

            # Add attachments
            for attachment_path in attachments:
                self._add_attachment(message, attachment_path)

            # Get all recipients
            all_recipients = [to_email] + cc + bcc

            # Send email
            message_id = self._send_via_smtp(message, all_recipients)

            logger.info(f"Email sent successfully to {to_email}, ID: {message_id}")

            return EmailResult(
                status=DeliveryStatus.SENT,
                message_id=message_id,
                recipients=all_recipients,
            )

        except FileNotFoundError as e:
            error_msg = f"Attachment not found: {e}"
            logger.error(error_msg)
            return EmailResult(
                status=DeliveryStatus.FAILED,
                error=error_msg,
                recipients=[to_email],
            )

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed: {e}"
            logger.error(error_msg)
            return EmailResult(
                status=DeliveryStatus.FAILED,
                error=error_msg,
                recipients=[to_email],
            )

        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipients refused: {e}"
            logger.error(error_msg)
            return EmailResult(
                status=DeliveryStatus.FAILED,
                error=error_msg,
                recipients=[to_email],
            )

        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {e}"
            logger.error(error_msg)
            return EmailResult(
                status=DeliveryStatus.FAILED,
                error=error_msg,
                recipients=[to_email],
            )

        except Exception as e:
            error_msg = f"Unexpected error sending email: {e}"
            logger.exception(error_msg)
            return EmailResult(
                status=DeliveryStatus.FAILED,
                error=error_msg,
                recipients=[to_email],
            )

    def _create_message(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[list[str]] = None,
        reply_to: Optional[str] = None,
    ) -> MIMEMultipart:
        """
        Create MIME message.

        Args:
            to_email: Recipient email.
            subject: Email subject.
            body: Plain text body.
            html_body: Optional HTML body.
            cc: CC recipients.
            reply_to: Reply-to address.

        Returns:
            MIMEMultipart: Composed message.
        """
        message = MIMEMultipart("mixed")

        # Set headers
        message["Subject"] = subject
        message["From"] = f"{self.config.from_name} <{self.config.from_email}>"
        message["To"] = to_email

        if cc:
            message["Cc"] = ", ".join(cc)

        if reply_to:
            message["Reply-To"] = reply_to

        # Create body part
        body_part = MIMEMultipart("alternative")

        # Add plain text
        text_part = MIMEText(body, "plain", "utf-8")
        body_part.attach(text_part)

        # Add HTML if provided
        if html_body:
            html_part = MIMEText(html_body, "html", "utf-8")
            body_part.attach(html_part)

        message.attach(body_part)

        return message

    def _add_attachment(
        self,
        message: MIMEMultipart,
        file_path: str,
    ) -> None:
        """
        Add file attachment to message.

        Args:
            message: Message to attach to.
            file_path: Path to file to attach.

        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        # Determine MIME type
        mime_type = self._get_mime_type(path)
        main_type, sub_type = mime_type.split("/", 1)

        # Read and encode file
        with open(path, "rb") as f:
            attachment = MIMEBase(main_type, sub_type)
            attachment.set_payload(f.read())

        encoders.encode_base64(attachment)

        # Set filename header
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=path.name,
        )

        message.attach(attachment)
        logger.debug(f"Attached file: {path.name}")

    def _get_mime_type(self, path: Path) -> str:
        """
        Get MIME type for file.

        Args:
            path: File path.

        Returns:
            str: MIME type string.
        """
        extension_map = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".txt": "text/plain",
            ".html": "text/html",
            ".csv": "text/csv",
            ".json": "application/json",
            ".zip": "application/zip",
        }

        suffix = path.suffix.lower()
        return extension_map.get(suffix, "application/octet-stream")

    def _send_via_smtp(
        self,
        message: MIMEMultipart,
        recipients: list[str],
    ) -> str:
        """
        Send message via SMTP.

        Args:
            message: Composed message.
            recipients: All recipient addresses.

        Returns:
            str: Message ID.

        Raises:
            smtplib.SMTPException: If sending fails.
        """
        if self.config.use_ssl:
            # Use SSL from the start
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(
                self.config.host,
                self.config.port,
                timeout=self.config.timeout,
                context=context,
            )
        else:
            # Use regular SMTP, optionally with STARTTLS
            server = smtplib.SMTP(
                self.config.host,
                self.config.port,
                timeout=self.config.timeout,
            )

        try:
            server.ehlo()

            if self.config.use_tls and not self.config.use_ssl:
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()

            # Authenticate if credentials provided
            if self.config.username and self.config.password:
                server.login(self.config.username, self.config.password)

            # Send email
            server.sendmail(
                self.config.from_email,
                recipients,
                message.as_string(),
            )

            # Generate message ID
            message_id = message.get("Message-ID", f"<{id(message)}@local>")

            return message_id

        finally:
            server.quit()

    def send_bulk(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        attachments: Optional[list[str]] = None,
    ) -> list[EmailResult]:
        """
        Send email to multiple recipients individually.

        Args:
            recipients: List of recipient emails.
            subject: Email subject.
            body: Email body.
            attachments: Optional attachments.

        Returns:
            list[EmailResult]: Results for each recipient.
        """
        results = []
        for recipient in recipients:
            result = self.send_email(
                to_email=recipient,
                subject=subject,
                body=body,
                attachments=attachments,
            )
            results.append(result)
        return results

    def test_connection(self) -> bool:
        """
        Test SMTP connection.

        Returns:
            bool: True if connection successful.
        """
        try:
            if self.config.use_ssl:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(
                    self.config.host,
                    self.config.port,
                    timeout=self.config.timeout,
                    context=context,
                )
            else:
                server = smtplib.SMTP(
                    self.config.host,
                    self.config.port,
                    timeout=self.config.timeout,
                )

            server.ehlo()

            if self.config.use_tls and not self.config.use_ssl:
                server.starttls()

            if self.config.username and self.config.password:
                server.login(self.config.username, self.config.password)

            server.quit()
            logger.info("SMTP connection test successful")
            return True

        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False


# Convenience function
def send_email(
    to_email: str,
    subject: str,
    body: str,
    attachments: Optional[list[str]] = None,
    config: Optional[SMTPConfig] = None,
) -> EmailResult:
    """
    Send an email using default configuration.

    Convenience function that creates an EmailSender instance
    and sends a single email.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        body: Plain text email body.
        attachments: List of file paths to attach.
        config: Optional SMTP configuration.

    Returns:
        EmailResult: Delivery status and details.

    Example:
        >>> result = send_email(
        ...     to_email="user@example.com",
        ...     subject="Test Email",
        ...     body="This is a test.",
        ... )
        >>> if result.status == DeliveryStatus.SENT:
        ...     print("Email sent!")
    """
    sender = EmailSender(config=config)
    return sender.send_email(
        to_email=to_email,
        subject=subject,
        body=body,
        attachments=attachments,
    )

