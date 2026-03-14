"""AES-256-GCM encryption for sensitive data at rest (coldkey addresses)."""

import base64
import os
from functools import lru_cache
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

_NONCE_BYTES = 12


@lru_cache(maxsize=1)
def _get_key() -> bytes:
    """Load and decode the encryption key from the environment.

    Returns 32 raw bytes for AES-256. The env var is base64-encoded.
    In debug mode with no key set, returns a deterministic dev key.
    """
    from engine.core.config import settings

    raw = settings.address_encryption_key
    if not raw:
        # Debug mode only — production raises in config validation
        return b"\x00" * 32
    return base64.b64decode(raw)


def encrypt_address(plaintext: str | None) -> str | None:
    """Encrypt a plaintext string with AES-256-GCM.

    Returns base64-encoded nonce + ciphertext.
    """
    if plaintext is None:
        return None
    key = _get_key()
    nonce = os.urandom(_NONCE_BYTES)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_address(token: str | None) -> str | None:
    """Decrypt a base64-encoded nonce + ciphertext back to plaintext."""
    if token is None:
        return None
    key = _get_key()
    raw = base64.b64decode(token)
    nonce = raw[:_NONCE_BYTES]
    ciphertext = raw[_NONCE_BYTES:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


class EncryptedString(TypeDecorator[str]):
    """SQLAlchemy type that transparently encrypts/decrypts via AES-256-GCM."""

    impl = String(512)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        """Encrypt on write."""
        if value is None:
            return None
        return encrypt_address(str(value))

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        """Decrypt on read."""
        if value is None:
            return None
        return decrypt_address(str(value))
