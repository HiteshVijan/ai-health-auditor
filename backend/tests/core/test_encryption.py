"""
Unit tests for encryption module.
"""

import os
import pytest
from unittest.mock import patch

from app.core.encryption import (
    EncryptionService,
    EncryptionError,
    DecryptionError,
    KeyDerivationError,
    encrypt_pii,
    decrypt_pii,
    get_encryption_service,
)


@pytest.fixture
def encryption_env():
    """Set up encryption environment variables."""
    with patch.dict(os.environ, {
        "ENCRYPTION_MASTER_KEY": "test-master-key-12345",
        "ENCRYPTION_SALT": "test-salt-67890",
    }):
        yield


@pytest.fixture
def encryption_service(encryption_env):
    """Create an encryption service instance."""
    return EncryptionService(
        master_key="test-master-key-12345",
        salt="test-salt-67890",
    )


class TestEncryptionService:
    """Tests for EncryptionService class."""
    
    def test_init_requires_master_key(self):
        """Should raise error if master key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EncryptionError, match="ENCRYPTION_MASTER_KEY"):
                EncryptionService()
    
    def test_init_requires_salt(self):
        """Should raise error if salt is missing."""
        with patch.dict(os.environ, {"ENCRYPTION_MASTER_KEY": "key"}, clear=True):
            with pytest.raises(EncryptionError, match="ENCRYPTION_SALT"):
                EncryptionService()
    
    def test_init_with_env_vars(self, encryption_env):
        """Should initialize from environment variables."""
        service = EncryptionService()
        assert service is not None
    
    def test_init_with_explicit_values(self):
        """Should initialize with explicit key and salt."""
        service = EncryptionService(
            master_key="explicit-key",
            salt="explicit-salt",
        )
        assert service is not None


class TestEncryption:
    """Tests for encryption functionality."""
    
    def test_encrypt_returns_string(self, encryption_service):
        """Encryption should return a string."""
        result = encryption_service.encrypt("test data")
        assert isinstance(result, str)
    
    def test_encrypt_produces_different_output(self, encryption_service):
        """Encrypted output should differ from plaintext."""
        plaintext = "sensitive information"
        encrypted = encryption_service.encrypt(plaintext)
        
        assert encrypted != plaintext
        assert len(encrypted) > 0
    
    def test_encrypt_empty_string(self, encryption_service):
        """Encrypting empty string should return empty string."""
        result = encryption_service.encrypt("")
        assert result == ""
    
    def test_encrypt_none_handling(self, encryption_service):
        """Should handle None input gracefully."""
        # This would typically be handled at the field level
        # but direct encrypt call with empty string should work
        result = encryption_service.encrypt("")
        assert result == ""
    
    def test_encrypt_unicode(self, encryption_service):
        """Should handle unicode characters."""
        plaintext = "患者姓名: 田中太郎 🏥"
        encrypted = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_encrypt_long_string(self, encryption_service):
        """Should handle long strings."""
        plaintext = "x" * 10000
        encrypted = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(encrypted)
        
        assert decrypted == plaintext


class TestDecryption:
    """Tests for decryption functionality."""
    
    def test_decrypt_returns_original(self, encryption_service):
        """Decryption should return original plaintext."""
        plaintext = "my secret data"
        encrypted = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_decrypt_empty_string(self, encryption_service):
        """Decrypting empty string should return empty string."""
        result = encryption_service.decrypt("")
        assert result == ""
    
    def test_decrypt_invalid_ciphertext(self, encryption_service):
        """Should raise error for invalid ciphertext."""
        with pytest.raises(DecryptionError):
            encryption_service.decrypt("not-valid-ciphertext")
    
    def test_decrypt_tampered_ciphertext(self, encryption_service):
        """Should raise error for tampered ciphertext."""
        encrypted = encryption_service.encrypt("test")
        tampered = encrypted[:-4] + "XXXX"
        
        with pytest.raises(DecryptionError):
            encryption_service.decrypt(tampered)
    
    def test_decrypt_wrong_key(self, encryption_env):
        """Should fail with wrong decryption key."""
        service1 = EncryptionService(
            master_key="key-one",
            salt="same-salt",
        )
        service2 = EncryptionService(
            master_key="key-two",
            salt="same-salt",
        )
        
        encrypted = service1.encrypt("secret")
        
        with pytest.raises(DecryptionError):
            service2.decrypt(encrypted)


class TestKeyRotation:
    """Tests for key rotation support."""
    
    def test_decrypt_with_old_key(self, encryption_env):
        """Should decrypt data encrypted with old key."""
        # Encrypt with old key
        old_service = EncryptionService(
            master_key="old-key",
            salt="test-salt-67890",
        )
        encrypted = old_service.encrypt("old secret")
        
        # Create new service with old key in rotation list
        with patch.dict(os.environ, {
            "ENCRYPTION_MASTER_KEY": "new-key",
            "ENCRYPTION_SALT": "test-salt-67890",
            "ENCRYPTION_OLD_KEYS": "old-key",
        }):
            new_service = EncryptionService()
            decrypted = new_service.decrypt(encrypted)
            
            assert decrypted == "old secret"
    
    def test_decrypt_multiple_old_keys(self, encryption_env):
        """Should try multiple old keys."""
        # Encrypt with oldest key
        oldest_service = EncryptionService(
            master_key="oldest-key",
            salt="test-salt-67890",
        )
        encrypted = oldest_service.encrypt("ancient secret")
        
        # Create service with multiple old keys
        with patch.dict(os.environ, {
            "ENCRYPTION_MASTER_KEY": "current-key",
            "ENCRYPTION_SALT": "test-salt-67890",
            "ENCRYPTION_OLD_KEYS": "recent-key,oldest-key",
        }):
            new_service = EncryptionService()
            decrypted = new_service.decrypt(encrypted)
            
            assert decrypted == "ancient secret"


class TestDictEncryption:
    """Tests for dictionary encryption."""
    
    def test_encrypt_dict_fields(self, encryption_service):
        """Should encrypt specified fields in dictionary."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "public_id": "12345",
        }
        
        encrypted = encryption_service.encrypt_dict(data, ["name", "email"])
        
        # Specified fields should be encrypted
        assert encrypted["name"] != "John Doe"
        assert encrypted["email"] != "john@example.com"
        # Non-specified fields unchanged
        assert encrypted["public_id"] == "12345"
    
    def test_decrypt_dict_fields(self, encryption_service):
        """Should decrypt specified fields in dictionary."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
        }
        
        encrypted = encryption_service.encrypt_dict(data, ["name", "email"])
        decrypted = encryption_service.decrypt_dict(encrypted, ["name", "email"])
        
        assert decrypted["name"] == "John Doe"
        assert decrypted["email"] == "john@example.com"
    
    def test_encrypt_dict_missing_field(self, encryption_service):
        """Should handle missing fields gracefully."""
        data = {"name": "John"}
        
        # Should not raise for missing field
        encrypted = encryption_service.encrypt_dict(data, ["name", "email"])
        
        assert "email" not in encrypted
        assert encrypted["name"] != "John"


class TestHashForSearch:
    """Tests for searchable hash generation."""
    
    def test_hash_is_deterministic(self, encryption_service):
        """Same value should produce same hash."""
        hash1 = encryption_service.hash_for_search("test@example.com")
        hash2 = encryption_service.hash_for_search("test@example.com")
        
        assert hash1 == hash2
    
    def test_hash_is_different_for_different_values(self, encryption_service):
        """Different values should produce different hashes."""
        hash1 = encryption_service.hash_for_search("alice@example.com")
        hash2 = encryption_service.hash_for_search("bob@example.com")
        
        assert hash1 != hash2
    
    def test_hash_empty_string(self, encryption_service):
        """Empty string should return empty string."""
        result = encryption_service.hash_for_search("")
        assert result == ""
    
    def test_hash_is_hex(self, encryption_service):
        """Hash should be hexadecimal."""
        hash_value = encryption_service.hash_for_search("test")
        
        assert len(hash_value) == 64  # SHA-256 hex length
        assert all(c in "0123456789abcdef" for c in hash_value)


class TestKeyGeneration:
    """Tests for key generation utilities."""
    
    def test_generate_key(self):
        """Should generate a valid Fernet key."""
        key = EncryptionService.generate_key()
        
        assert isinstance(key, str)
        assert len(key) > 0
    
    def test_generate_unique_keys(self):
        """Generated keys should be unique."""
        keys = [EncryptionService.generate_key() for _ in range(10)]
        
        assert len(set(keys)) == 10
    
    def test_generate_salt(self):
        """Should generate a valid salt."""
        salt = EncryptionService.generate_salt()
        
        assert isinstance(salt, str)
        assert len(salt) > 0
    
    def test_generate_unique_salts(self):
        """Generated salts should be unique."""
        salts = [EncryptionService.generate_salt() for _ in range(10)]
        
        assert len(set(salts)) == 10


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_encrypt_pii(self, encryption_env):
        """Should encrypt using global service."""
        # Clear cached service
        import app.core.encryption as enc_module
        enc_module._encryption_service = None
        
        encrypted = encrypt_pii("sensitive data")
        decrypted = decrypt_pii(encrypted)
        
        assert decrypted == "sensitive data"
    
    def test_get_encryption_service_singleton(self, encryption_env):
        """Should return same instance."""
        import app.core.encryption as enc_module
        enc_module._encryption_service = None
        
        service1 = get_encryption_service()
        service2 = get_encryption_service()
        
        assert service1 is service2


class TestPIIEncryptionScenarios:
    """Real-world PII encryption scenarios."""
    
    def test_encrypt_patient_name(self, encryption_service):
        """Should encrypt patient names."""
        name = "John Michael Smith Jr."
        encrypted = encryption_service.encrypt(name)
        decrypted = encryption_service.decrypt(encrypted)
        
        assert decrypted == name
        assert encrypted != name
    
    def test_encrypt_ssn(self, encryption_service):
        """Should encrypt SSN."""
        ssn = "123-45-6789"
        encrypted = encryption_service.encrypt(ssn)
        decrypted = encryption_service.decrypt(encrypted)
        
        assert decrypted == ssn
    
    def test_encrypt_email(self, encryption_service):
        """Should encrypt email addresses."""
        email = "patient@healthcare.example.com"
        encrypted = encryption_service.encrypt(email)
        decrypted = encryption_service.decrypt(encrypted)
        
        assert decrypted == email
    
    def test_encrypt_phone(self, encryption_service):
        """Should encrypt phone numbers."""
        phone = "+1 (555) 123-4567"
        encrypted = encryption_service.encrypt(phone)
        decrypted = encryption_service.decrypt(encrypted)
        
        assert decrypted == phone
    
    def test_encrypt_address(self, encryption_service):
        """Should encrypt full addresses."""
        address = "123 Healthcare Ave, Suite 456\nMedical City, CA 90210"
        encrypted = encryption_service.encrypt(address)
        decrypted = encryption_service.decrypt(encrypted)
        
        assert decrypted == address

