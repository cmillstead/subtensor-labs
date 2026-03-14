"""Tests for Settings validation logic."""

import pytest
from pydantic import ValidationError

from engine.core.config import Settings


def test_validate_encryption_key_raises_when_not_debug_and_key_missing() -> None:
    """Production mode requires ENGINE_ADDRESS_ENCRYPTION_KEY."""
    with pytest.raises(ValidationError, match="ENGINE_ADDRESS_ENCRYPTION_KEY"):
        Settings(debug=False, address_encryption_key="")


def test_validate_encryption_key_passes_in_debug_mode() -> None:
    """Debug mode allows empty encryption key."""
    s = Settings(debug=True, address_encryption_key="")
    assert s.debug is True
    assert s.address_encryption_key == ""


def test_validate_encryption_key_passes_when_key_set() -> None:
    """Production mode passes when key is provided."""
    s = Settings(debug=False, address_encryption_key="supersecretkey123")
    assert s.address_encryption_key == "supersecretkey123"


def test_default_values() -> None:
    """Default settings use expected values."""
    s = Settings(debug=True)
    assert s.port == 8000
    assert s.host == "0.0.0.0"
    assert s.cache_ttl_metagraph == 180
    assert s.cache_ttl_portfolio == 300
    assert s.redis_max_connections == 20


def test_wildcard_cors_rejected_in_production() -> None:
    """Production mode rejects wildcard '*' in CORS origins."""
    with pytest.raises(ValidationError, match="must not contain"):
        Settings(debug=False, address_encryption_key="key123", cors_origins=["*"])


def test_wildcard_cors_allowed_in_debug() -> None:
    """Debug mode allows wildcard CORS origins."""
    s = Settings(debug=True, cors_origins=["*"])
    assert s.cors_origins == ["*"]
