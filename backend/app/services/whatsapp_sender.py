"""
WhatsApp messaging service using WhatsApp Business Cloud API.

Provides functionality to send WhatsApp messages with media attachments
for notifications and document delivery.
"""

import logging
import mimetypes
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class DeliveryStatus(str, Enum):
    """WhatsApp message delivery status."""

    SENT = "sent"
    FAILED = "failed"
    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"


class MessageType(str, Enum):
    """WhatsApp message types."""

    TEXT = "text"
    DOCUMENT = "document"
    IMAGE = "image"
    TEMPLATE = "template"


@dataclass
class WhatsAppResult:
    """Result of WhatsApp message sending operation."""

    status: DeliveryStatus
    message_id: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[int] = None
    recipient: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "status": self.status.value,
            "message_id": self.message_id,
            "error": self.error,
            "error_code": self.error_code,
            "recipient": self.recipient,
        }


@dataclass
class WhatsAppConfig:
    """WhatsApp Business Cloud API configuration."""

    access_token: str = ""
    phone_number_id: str = ""
    api_version: str = "v18.0"
    api_base_url: str = "https://graph.facebook.com"
    timeout: int = 30

    @property
    def messages_url(self) -> str:
        """Get the messages API endpoint URL."""
        return f"{self.api_base_url}/{self.api_version}/{self.phone_number_id}/messages"

    @property
    def media_url(self) -> str:
        """Get the media upload API endpoint URL."""
        return f"{self.api_base_url}/{self.api_version}/{self.phone_number_id}/media"

    @classmethod
    def from_env(cls) -> "WhatsAppConfig":
        """
        Create config from environment variables.

        Environment variables:
            WHATSAPP_ACCESS_TOKEN: Meta access token
            WHATSAPP_PHONE_NUMBER_ID: WhatsApp phone number ID
            WHATSAPP_API_VERSION: API version (default: v18.0)

        Returns:
            WhatsAppConfig: Configuration instance.
        """
        return cls(
            access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
            phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
            api_version=os.getenv("WHATSAPP_API_VERSION", "v18.0"),
            timeout=int(os.getenv("WHATSAPP_TIMEOUT", "30")),
        )

    def is_configured(self) -> bool:
        """Check if required configuration is present."""
        return bool(self.access_token and self.phone_number_id)


class WhatsAppSender:
    """
    WhatsApp message sender using Business Cloud API.

    Handles text messages and media attachments via the
    Meta WhatsApp Business Cloud API.
    """

    def __init__(
        self,
        config: Optional[WhatsAppConfig] = None,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize WhatsApp sender.

        Args:
            config: WhatsApp API configuration. Uses environment if None.
            session: Optional requests session for connection pooling.
        """
        self.config = config or WhatsAppConfig.from_env()
        self.session = session or requests.Session()

    @property
    def _headers(self) -> dict:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {self.config.access_token}",
            "Content-Type": "application/json",
        }

    def send_whatsapp(
        self,
        to_number: str,
        message: str,
        attachments: Optional[list[str]] = None,
        preview_url: bool = False,
    ) -> WhatsAppResult:
        """
        Send a WhatsApp message with optional attachments.

        Args:
            to_number: Recipient phone number (with country code, no +).
            message: Text message content.
            attachments: List of file paths to send as documents.
            preview_url: Whether to show URL previews in message.

        Returns:
            WhatsAppResult: Delivery status and details.

        Example:
            >>> sender = WhatsAppSender()
            >>> result = sender.send_whatsapp(
            ...     to_number="1234567890",
            ...     message="Your audit report is ready!",
            ...     attachments=["report.pdf"]
            ... )
            >>> print(result.status)
            DeliveryStatus.SENT
        """
        attachments = attachments or []

        # Validate configuration
        if not self.config.is_configured():
            return WhatsAppResult(
                status=DeliveryStatus.FAILED,
                error="WhatsApp API not configured. Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID.",
                recipient=to_number,
            )

        # Normalize phone number
        to_number = self._normalize_phone_number(to_number)

        logger.info(f"Sending WhatsApp message to {to_number}")

        try:
            results = []

            # Send text message first
            if message:
                text_result = self._send_text_message(to_number, message, preview_url)
                results.append(text_result)

                if text_result.status == DeliveryStatus.FAILED:
                    return text_result

            # Send attachments
            for attachment_path in attachments:
                attachment_result = self._send_document(to_number, attachment_path, message="")
                results.append(attachment_result)

                if attachment_result.status == DeliveryStatus.FAILED:
                    return attachment_result

            # Return last successful result
            if results:
                return results[-1]

            return WhatsAppResult(
                status=DeliveryStatus.FAILED,
                error="No message or attachments to send",
                recipient=to_number,
            )

        except requests.exceptions.Timeout:
            error_msg = "Request timed out"
            logger.error(f"WhatsApp API timeout: {error_msg}")
            return WhatsAppResult(
                status=DeliveryStatus.FAILED,
                error=error_msg,
                recipient=to_number,
            )

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {e}"
            logger.error(f"WhatsApp API connection error: {error_msg}")
            return WhatsAppResult(
                status=DeliveryStatus.FAILED,
                error=error_msg,
                recipient=to_number,
            )

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.exception(f"WhatsApp send error: {error_msg}")
            return WhatsAppResult(
                status=DeliveryStatus.FAILED,
                error=error_msg,
                recipient=to_number,
            )

    def _send_text_message(
        self,
        to_number: str,
        message: str,
        preview_url: bool = False,
    ) -> WhatsAppResult:
        """
        Send a text message.

        Args:
            to_number: Recipient phone number.
            message: Text content.
            preview_url: Show URL previews.

        Returns:
            WhatsAppResult: Delivery result.
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": message,
            },
        }

        return self._send_message(payload, to_number)

    def _send_document(
        self,
        to_number: str,
        file_path: str,
        message: str = "",
    ) -> WhatsAppResult:
        """
        Send a document attachment.

        Args:
            to_number: Recipient phone number.
            file_path: Path to document file.
            message: Optional caption.

        Returns:
            WhatsAppResult: Delivery result.
        """
        path = Path(file_path)

        if not path.exists():
            return WhatsAppResult(
                status=DeliveryStatus.FAILED,
                error=f"File not found: {file_path}",
                recipient=to_number,
            )

        # Upload media first
        media_id = self._upload_media(file_path)
        if not media_id:
            return WhatsAppResult(
                status=DeliveryStatus.FAILED,
                error=f"Failed to upload media: {file_path}",
                recipient=to_number,
            )

        # Determine message type based on file
        message_type = self._get_message_type(path)

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": message_type,
            message_type: {
                "id": media_id,
                "filename": path.name,
            },
        }

        # Add caption if provided
        if message:
            payload[message_type]["caption"] = message

        return self._send_message(payload, to_number)

    def _upload_media(self, file_path: str) -> Optional[str]:
        """
        Upload media file to WhatsApp servers.

        Args:
            file_path: Path to file to upload.

        Returns:
            Optional[str]: Media ID if successful, None otherwise.
        """
        path = Path(file_path)
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                files = {
                    "file": (path.name, f, mime_type),
                }
                data = {
                    "messaging_product": "whatsapp",
                    "type": mime_type,
                }

                response = self.session.post(
                    self.config.media_url,
                    headers={"Authorization": f"Bearer {self.config.access_token}"},
                    files=files,
                    data=data,
                    timeout=self.config.timeout,
                )

            if response.status_code == 200:
                result = response.json()
                media_id = result.get("id")
                logger.info(f"Media uploaded successfully: {media_id}")
                return media_id
            else:
                logger.error(f"Media upload failed: {response.text}")
                return None

        except Exception as e:
            logger.exception(f"Media upload error: {e}")
            return None

    def _send_message(self, payload: dict, to_number: str) -> WhatsAppResult:
        """
        Send message payload to WhatsApp API.

        Args:
            payload: Message payload.
            to_number: Recipient number.

        Returns:
            WhatsAppResult: Delivery result.
        """
        response = self.session.post(
            self.config.messages_url,
            headers=self._headers,
            json=payload,
            timeout=self.config.timeout,
        )

        if response.status_code in (200, 201):
            result = response.json()
            messages = result.get("messages", [])
            message_id = messages[0].get("id") if messages else None

            logger.info(f"WhatsApp message sent: {message_id}")

            return WhatsAppResult(
                status=DeliveryStatus.SENT,
                message_id=message_id,
                recipient=to_number,
            )
        else:
            error_data = response.json().get("error", {})
            error_message = error_data.get("message", "Unknown error")
            error_code = error_data.get("code")

            logger.error(f"WhatsApp API error: {error_message} (code: {error_code})")

            return WhatsAppResult(
                status=DeliveryStatus.FAILED,
                error=error_message,
                error_code=error_code,
                recipient=to_number,
            )

    def _normalize_phone_number(self, phone: str) -> str:
        """
        Normalize phone number format.

        Removes common formatting characters and ensures
        proper format for WhatsApp API.

        Args:
            phone: Raw phone number.

        Returns:
            str: Normalized phone number.
        """
        # Remove common formatting characters
        phone = phone.replace("+", "")
        phone = phone.replace("-", "")
        phone = phone.replace(" ", "")
        phone = phone.replace("(", "")
        phone = phone.replace(")", "")

        return phone

    def _get_message_type(self, path: Path) -> str:
        """
        Determine WhatsApp message type from file.

        Args:
            path: File path.

        Returns:
            str: Message type (document, image, etc.).
        """
        suffix = path.suffix.lower()

        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        video_extensions = {".mp4", ".3gp"}
        audio_extensions = {".mp3", ".ogg", ".amr", ".m4a"}

        if suffix in image_extensions:
            return "image"
        elif suffix in video_extensions:
            return "video"
        elif suffix in audio_extensions:
            return "audio"
        else:
            return "document"

    def send_template(
        self,
        to_number: str,
        template_name: str,
        language_code: str = "en_US",
        components: Optional[list] = None,
    ) -> WhatsAppResult:
        """
        Send a template message.

        Args:
            to_number: Recipient phone number.
            template_name: Approved template name.
            language_code: Template language code.
            components: Template components (header, body, buttons).

        Returns:
            WhatsAppResult: Delivery result.
        """
        if not self.config.is_configured():
            return WhatsAppResult(
                status=DeliveryStatus.FAILED,
                error="WhatsApp API not configured",
                recipient=to_number,
            )

        to_number = self._normalize_phone_number(to_number)

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code,
                },
            },
        }

        if components:
            payload["template"]["components"] = components

        return self._send_message(payload, to_number)

    def send_bulk(
        self,
        recipients: list[str],
        message: str,
        attachments: Optional[list[str]] = None,
    ) -> list[WhatsAppResult]:
        """
        Send message to multiple recipients.

        Args:
            recipients: List of phone numbers.
            message: Message text.
            attachments: Optional attachments.

        Returns:
            list[WhatsAppResult]: Results for each recipient.
        """
        results = []
        for recipient in recipients:
            result = self.send_whatsapp(
                to_number=recipient,
                message=message,
                attachments=attachments,
            )
            results.append(result)
        return results

    def check_health(self) -> bool:
        """
        Check WhatsApp API connectivity.

        Returns:
            bool: True if API is accessible.
        """
        if not self.config.is_configured():
            return False

        try:
            # Try to get phone number info
            url = f"{self.config.api_base_url}/{self.config.api_version}/{self.config.phone_number_id}"
            response = self.session.get(
                url,
                headers=self._headers,
                timeout=10,
            )
            return response.status_code == 200

        except Exception as e:
            logger.error(f"WhatsApp health check failed: {e}")
            return False


# Convenience function
def send_whatsapp(
    to_number: str,
    message: str,
    attachments: Optional[list[str]] = None,
    config: Optional[WhatsAppConfig] = None,
) -> WhatsAppResult:
    """
    Send a WhatsApp message using default configuration.

    Convenience function that creates a WhatsAppSender instance
    and sends a single message.

    Args:
        to_number: Recipient phone number (with country code).
        message: Text message content.
        attachments: List of file paths to attach.
        config: Optional WhatsApp configuration.

    Returns:
        WhatsAppResult: Delivery status and details.

    Example:
        >>> result = send_whatsapp(
        ...     to_number="1234567890",
        ...     message="Hello from Health Auditor!",
        ... )
        >>> if result.status == DeliveryStatus.SENT:
        ...     print("Message sent!")
    """
    sender = WhatsAppSender(config=config)
    return sender.send_whatsapp(
        to_number=to_number,
        message=message,
        attachments=attachments,
    )

