"""
Encryption Module for PII Data Protection.

Provides AES-256 encryption using Fernet for encrypting sensitive
data before storing in the database.
"""

import base64
import hashlib
import logging
import os
from typing import Optional, Union
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption errors."""
    pass


class DecryptionError(EncryptionError):
    """Raised when decryption fails."""
    pass


class KeyDerivationError(EncryptionError):
    """Raised when key derivation fails."""
    pass


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.
    
    Uses Fernet (AES-128-CBC with HMAC) for symmetric encryption.
    Supports key rotation and multiple encryption keys.
    """
    
    def __init__(
        self,
        master_key: Optional[str] = None,
        salt: Optional[str] = None,
    ):
        """
        Initialize the encryption service.
        
        Args:
            master_key: Master encryption key (falls back to env var).
            salt: Salt for key derivation (falls back to env var).
        """
        self._master_key = master_key or os.getenv("ENCRYPTION_MASTER_KEY")
        self._salt = salt or os.getenv("ENCRYPTION_SALT")
        
        if not self._master_key:
            raise EncryptionError(
                "ENCRYPTION_MASTER_KEY environment variable is required"
            )
        
        if not self._salt:
            raise EncryptionError(
                "ENCRYPTION_SALT environment variable is required"
            )
        
        self._fernet = self._create_fernet()
        
        # Support for key rotation - old keys for decryption
        self._old_fernets: list[Fernet] = []
        old_keys = os.getenv("ENCRYPTION_OLD_KEYS", "").split(",")
        for old_key in old_keys:
            if old_key.strip():
                try:
                    old_fernet = self._create_fernet(old_key.strip())
                    self._old_fernets.append(old_fernet)
                except Exception as e:
                    logger.warning(f"Failed to initialize old encryption key: {e}")
    
    def _create_fernet(self, key: Optional[str] = None) -> Fernet:
        """
        Create a Fernet instance from the master key.
        
        Uses PBKDF2 to derive a proper encryption key from the master key.
        """
        try:
            key_bytes = (key or self._master_key).encode()
            salt_bytes = self._salt.encode()
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=100000,
                backend=default_backend(),
            )
            
            derived_key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
            return Fernet(derived_key)
        except Exception as e:
            raise KeyDerivationError(f"Failed to derive encryption key: {e}")
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: The string to encrypt.
        
        Returns:
            Base64-encoded encrypted string.
        
        Raises:
            EncryptionError: If encryption fails.
        """
        if not plaintext:
            return ""
        
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.
        
        Tries the current key first, then falls back to old keys.
        
        Args:
            ciphertext: Base64-encoded encrypted string.
        
        Returns:
            Decrypted plaintext string.
        
        Raises:
            DecryptionError: If decryption fails with all keys.
        """
        if not ciphertext:
            return ""
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
        except Exception as e:
            raise DecryptionError(f"Invalid ciphertext format: {e}")
        
        # Try current key
        try:
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except InvalidToken:
            pass
        
        # Try old keys for key rotation support
        for old_fernet in self._old_fernets:
            try:
                decrypted_bytes = old_fernet.decrypt(encrypted_bytes)
                return decrypted_bytes.decode()
            except InvalidToken:
                continue
        
        raise DecryptionError("Decryption failed: invalid key or corrupted data")
    
    def encrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing data.
            fields: List of field names to encrypt.
        
        Returns:
            Dictionary with specified fields encrypted.
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                result[field] = self.encrypt(str(result[field]))
        return result
    
    def decrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data.
            fields: List of field names to decrypt.
        
        Returns:
            Dictionary with specified fields decrypted.
        """
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                try:
                    result[field] = self.decrypt(str(result[field]))
                except DecryptionError:
                    logger.warning(f"Failed to decrypt field: {field}")
        return result
    
    def hash_for_search(self, value: str) -> str:
        """
        Create a deterministic hash for searchable encrypted fields.
        
        Note: This reduces security but enables searching.
        Use sparingly and only for fields that need to be searchable.
        
        Args:
            value: The value to hash.
        
        Returns:
            SHA-256 hash of the value.
        """
        if not value:
            return ""
        
        combined = f"{self._salt}:{value}".encode()
        return hashlib.sha256(combined).hexdigest()
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new random encryption key."""
        return Fernet.generate_key().decode()
    
    @staticmethod
    def generate_salt() -> str:
        """Generate a new random salt."""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create the global encryption service."""
    global _encryption_service
    
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    
    return _encryption_service


def encrypt_pii(value: str) -> str:
    """Convenience function to encrypt PII data."""
    return get_encryption_service().encrypt(value)


def decrypt_pii(value: str) -> str:
    """Convenience function to decrypt PII data."""
    return get_encryption_service().decrypt(value)

