"""Data encryption utilities for LLMHive.

This module provides encryption/decryption functionality for sensitive data
stored in the database, using AES-256-GCM (strong symmetric encryption) or
Fernet (for backwards compatibility).
"""
from __future__ import annotations

import base64
import logging
import os
import secrets
from typing import Optional

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    Fernet = None  # type: ignore
    AESGCM = None  # type: ignore
    logger.warning("cryptography package not available, encryption disabled")

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption and decryption of sensitive data.
    
    Uses AES-256-GCM (strong symmetric encryption) for field-level encryption.
    Falls back to Fernet for backwards compatibility.
    The encryption key is loaded from environment variable ENCRYPTION_KEY.
    If the key is missing, the system will log a warning and default to no encryption (for dev).
    """

    def __init__(self, encryption_key: Optional[str] = None, require_key: bool = False, use_aes_gcm: bool = True):
        """Initialize encryption manager.
        
        Args:
            encryption_key: Optional encryption key. If None, loads from ENCRYPTION_KEY env var.
            require_key: If True, raises error if key is missing. If False, encryption is disabled.
            use_aes_gcm: If True, use AES-256-GCM. If False, use Fernet (backwards compatibility).
        
        Raises:
            ValueError: If require_key is True and no key is available
        """
        self.fernet: Optional[Fernet] = None
        self.aes_gcm: Optional[AESGCM] = None
        self.use_aes_gcm = use_aes_gcm and CRYPTOGRAPHY_AVAILABLE
        self.enabled = False
        
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("Encryption: cryptography package not available, encryption disabled")
            if require_key:
                raise ValueError(
                    "Encryption is required but cryptography package is not installed. "
                    "Install it with: pip install cryptography"
                )
            return
        
        # Get encryption key
        key_str = encryption_key or os.getenv("ENCRYPTION_KEY")
        
        if not key_str:
            if require_key:
                raise ValueError(
                    "ENCRYPTION_KEY environment variable is required for data encryption. "
                    "Set it to a base64-encoded Fernet key or a password string."
                )
            logger.warning("Encryption: No encryption key provided, encryption disabled")
            return
        
        # Initialize encryption
        try:
            if self.use_aes_gcm:
                # AES-256-GCM: Derive 32-byte key from password
                logger.info("Encryption: Using AES-256-GCM for field-level encryption")
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,  # AES-256 requires 32 bytes
                    salt=b'llmhive_aes_salt',  # In production, use a random salt stored separately
                    iterations=100000,
                )
                key = kdf.derive(key_str.encode())
                self.aes_gcm = AESGCM(key)
                self.enabled = True
                logger.info("Encryption: AES-256-GCM encryption manager initialized successfully")
            else:
                # Fernet (backwards compatibility)
                try:
                    key = base64.urlsafe_b64decode(key_str.encode())
                    if len(key) != 32:
                        raise ValueError("Invalid key length")
                    self.fernet = Fernet(key_str.encode())
                except (ValueError, base64.binascii.Error):
                    # If not a valid Fernet key, derive one from password using PBKDF2
                    logger.info("Encryption: Deriving Fernet key from password using PBKDF2")
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=b'llmhive_salt',
                        iterations=100000,
                    )
                    key = base64.urlsafe_b64encode(kdf.derive(key_str.encode()))
                    self.fernet = Fernet(key)
                
                self.enabled = True
                logger.info("Encryption: Fernet encryption manager initialized successfully")
        except Exception as exc:
            if require_key:
                raise ValueError(f"Failed to initialize encryption: {exc}") from exc
            logger.warning("Encryption: Failed to initialize encryption, encryption disabled: %s", exc)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string using AES-256-GCM or Fernet.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Encrypted string (base64-encoded with nonce/iv), or original string if encryption disabled
        """
        if not self.enabled:
            return plaintext
        
        try:
            if self.use_aes_gcm and self.aes_gcm:
                # AES-256-GCM: Generate random nonce and encrypt
                nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
                plaintext_bytes = plaintext.encode('utf-8')
                ciphertext = self.aes_gcm.encrypt(nonce, plaintext_bytes, None)
                # Combine nonce + ciphertext and encode as base64
                combined = nonce + ciphertext
                return base64.urlsafe_b64encode(combined).decode('utf-8')
            elif self.fernet:
                # Fernet (backwards compatibility)
                encrypted = self.fernet.encrypt(plaintext.encode('utf-8'))
                return base64.urlsafe_b64encode(encrypted).decode('utf-8')
            else:
                return plaintext
        except Exception as exc:
            logger.error("Encryption: Failed to encrypt data: %s", exc)
            # In production, you might want to raise here instead of returning plaintext
            return plaintext

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a ciphertext string using AES-256-GCM or Fernet.
        
        Args:
            ciphertext: Encrypted string (base64-encoded with nonce/iv), or plaintext if encryption was disabled
            
        Returns:
            Decrypted string, or original string if decryption fails or encryption was disabled
        """
        if not self.enabled:
            # If encryption is disabled, assume the data is already plaintext
            return ciphertext
        
        try:
            decoded = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
            
            if self.use_aes_gcm and self.aes_gcm:
                # AES-256-GCM: Extract nonce (first 12 bytes) and ciphertext
                if len(decoded) < 12:
                    raise ValueError("Ciphertext too short for AES-GCM")
                nonce = decoded[:12]
                ciphertext_bytes = decoded[12:]
                decrypted = self.aes_gcm.decrypt(nonce, ciphertext_bytes, None)
                return decrypted.decode('utf-8')
            elif self.fernet:
                # Fernet (backwards compatibility)
                decrypted = self.fernet.decrypt(decoded)
                return decrypted.decode('utf-8')
            else:
                return ciphertext
        except (ValueError, base64.binascii.Error) as e:
            # If decryption fails, assume the data is plaintext (backwards compatibility)
            logger.debug("Encryption: Decryption failed, assuming plaintext (backwards compatibility): %s", e)
            return ciphertext
        except Exception as exc:
            logger.error("Encryption: Failed to decrypt data: %s", exc)
            # Return original on error (for backwards compatibility with unencrypted data)
            return ciphertext

    def is_encrypted(self, data: str) -> bool:
        """Check if a string appears to be encrypted.
        
        This is a heuristic check - encrypted data is base64-encoded and typically
        longer than the original plaintext.
        
        Args:
            data: String to check
            
        Returns:
            True if data appears to be encrypted, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Try to decode as base64
            base64.urlsafe_b64decode(data.encode('utf-8'))
            # If successful and data is longer than a typical plaintext, assume encrypted
            return len(data) > 50  # Heuristic: encrypted data is typically longer
        except (ValueError, base64.binascii.Error):
            return False


# Global encryption manager instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager(require_key: bool = True) -> EncryptionManager:
    """Get the global encryption manager instance.
    
    Args:
        require_key: If True, raises error if key is missing. If False, encryption is disabled.
        
    Returns:
        EncryptionManager instance
    """
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager(require_key=require_key)
    return _encryption_manager

