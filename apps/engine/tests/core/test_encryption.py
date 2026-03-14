"""Tests for AES-256-GCM address encryption."""

import base64
import os

import pytest

from engine.core.config import settings
from engine.core.encryption import _get_key, decrypt_address, encrypt_address


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set a valid 32-byte encryption key for tests and clear the key cache."""
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setattr(settings, "address_encryption_key", key)
    _get_key.cache_clear()
    yield
    _get_key.cache_clear()


class TestEncryptDecrypt:
    """Round-trip encryption tests."""

    def test_round_trip(self) -> None:
        """Encrypting then decrypting returns the original plaintext."""
        address = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
        ciphertext = encrypt_address(address)
        assert decrypt_address(ciphertext) == address

    def test_different_nonces(self) -> None:
        """Each encryption produces different ciphertext (unique nonce)."""
        address = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
        ct1 = encrypt_address(address)
        ct2 = encrypt_address(address)
        assert ct1 != ct2

    def test_ciphertext_is_base64(self) -> None:
        """Ciphertext is valid base64 and fits in String(512)."""
        address = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
        ciphertext = encrypt_address(address)
        decoded = base64.b64decode(ciphertext)
        assert len(decoded) > 0
        assert len(ciphertext) <= 512

    def test_none_passthrough(self) -> None:
        """None values pass through unchanged."""
        assert encrypt_address(None) is None  # type: ignore[arg-type]
        assert decrypt_address(None) is None  # type: ignore[arg-type]

    def test_empty_string(self) -> None:
        """Empty string encrypts and decrypts correctly."""
        ciphertext = encrypt_address("")
        assert ciphertext is not None
        assert decrypt_address(ciphertext) == ""

    def test_tampered_ciphertext_raises(self) -> None:
        """Tampered ciphertext raises an error on decryption."""
        address = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
        ciphertext = encrypt_address(address)
        # Tamper with a byte in the middle of the ciphertext
        raw = bytearray(base64.b64decode(ciphertext))
        raw[len(raw) // 2] ^= 0xFF
        tampered = base64.b64encode(bytes(raw)).decode()
        with pytest.raises(Exception):  # noqa: B017
            decrypt_address(tampered)

    def test_wrong_key_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Decryption with a different key fails."""
        address = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
        ciphertext = encrypt_address(address)

        # Change the encryption key and clear cache
        new_key = base64.b64encode(os.urandom(32)).decode()
        monkeypatch.setattr(settings, "address_encryption_key", new_key)
        _get_key.cache_clear()

        with pytest.raises(Exception):  # noqa: B017
            decrypt_address(ciphertext)
