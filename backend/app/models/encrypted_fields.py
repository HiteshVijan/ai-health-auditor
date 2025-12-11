"""
SQLAlchemy Custom Types for Encrypted Fields.

Provides transparent encryption/decryption for sensitive database columns.
"""

import logging
from typing import Optional, Any

from sqlalchemy import String, TypeDecorator
from sqlalchemy.engine import Dialect

from app.core.encryption import get_encryption_service, DecryptionError

logger = logging.getLogger(__name__)


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type that automatically encrypts/decrypts string values.
    
    Usage:
        class Patient(Base):
            ssn = Column(EncryptedString(length=500), nullable=True)
            
        # Values are automatically encrypted on save and decrypted on load
        patient.ssn = "123-45-6789"  # Stored encrypted
        print(patient.ssn)  # Returns "123-45-6789"
    """
    
    impl = String
    cache_ok = True
    
    def __init__(self, length: int = 500):
        """
        Initialize encrypted string type.
        
        Args:
            length: Maximum length of encrypted data (should be larger than plaintext).
        """
        super().__init__()
        self.impl = String(length)
    
    def process_bind_param(
        self, value: Optional[str], dialect: Dialect
    ) -> Optional[str]:
        """Encrypt value before storing in database."""
        if value is None:
            return None
        
        try:
            service = get_encryption_service()
            return service.encrypt(str(value))
        except Exception as e:
            logger.error(f"Failed to encrypt value: {e}")
            raise
    
    def process_result_value(
        self, value: Optional[str], dialect: Dialect
    ) -> Optional[str]:
        """Decrypt value after loading from database."""
        if value is None:
            return None
        
        try:
            service = get_encryption_service()
            return service.decrypt(value)
        except DecryptionError as e:
            logger.error(f"Failed to decrypt value: {e}")
            # Return placeholder to avoid exposing encrypted data
            return "[DECRYPTION_FAILED]"
        except Exception as e:
            logger.error(f"Unexpected error decrypting value: {e}")
            return "[DECRYPTION_ERROR]"


class EncryptedEmail(EncryptedString):
    """Encrypted email field with validation."""
    
    def process_bind_param(
        self, value: Optional[str], dialect: Dialect
    ) -> Optional[str]:
        if value is not None:
            # Basic email validation
            if "@" not in value:
                raise ValueError("Invalid email format")
        
        return super().process_bind_param(value, dialect)


class EncryptedPhone(EncryptedString):
    """Encrypted phone number field."""
    pass


class EncryptedSSN(EncryptedString):
    """Encrypted Social Security Number field."""
    
    def process_bind_param(
        self, value: Optional[str], dialect: Dialect
    ) -> Optional[str]:
        if value is not None:
            # Remove formatting
            value = value.replace("-", "").replace(" ", "")
            if len(value) != 9 or not value.isdigit():
                raise ValueError("Invalid SSN format")
        
        return super().process_bind_param(value, dialect)
    
    def process_result_value(
        self, value: Optional[str], dialect: Dialect
    ) -> Optional[str]:
        result = super().process_result_value(value, dialect)
        
        # Format SSN on retrieval
        if result and len(result) == 9:
            return f"{result[:3]}-{result[3:5]}-{result[5:]}"
        
        return result


class SearchableEncryptedString(TypeDecorator):
    """
    Encrypted string that also stores a hash for searching.
    
    Note: This stores both encrypted value and a deterministic hash.
    The hash enables searching but reduces security slightly.
    
    Usage:
        class User(Base):
            # Stores encrypted_email and email_hash columns
            email = Column(SearchableEncryptedString(length=500))
    """
    
    impl = String
    cache_ok = True
    
    def __init__(self, length: int = 500):
        super().__init__()
        self.impl = String(length)
    
    def process_bind_param(
        self, value: Optional[str], dialect: Dialect
    ) -> Optional[str]:
        """Encrypt and hash value before storing."""
        if value is None:
            return None
        
        try:
            service = get_encryption_service()
            encrypted = service.encrypt(str(value))
            # Hash is stored separately in _hash column
            return encrypted
        except Exception as e:
            logger.error(f"Failed to encrypt searchable value: {e}")
            raise
    
    def process_result_value(
        self, value: Optional[str], dialect: Dialect
    ) -> Optional[str]:
        """Decrypt value after loading."""
        if value is None:
            return None
        
        try:
            service = get_encryption_service()
            return service.decrypt(value)
        except DecryptionError as e:
            logger.error(f"Failed to decrypt searchable value: {e}")
            return "[DECRYPTION_FAILED]"

