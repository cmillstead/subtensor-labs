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
    s = Settings(debug=False, address_encryption_key="supersecretkey123", taostats_api_key="ts-key")
    assert s.address_encryption_key == "supersecretkey123"


def test_default_values() -> None:
    """Default settings use expected values."""
    s = Settings(debug=True)
    assert s.port == 8000
    assert s.host == "0.0.0.0"
    assert s.cache_ttl_metagraph == 180
    assert s.cache_ttl_portfolio == 300
    assert s.redis_max_connections == 20
    assert s.taostats_api_url == "https://api.taostats.io"
    assert s.taostats_backfill_hour_utc == 3
    assert s.taostats_backfill_workers == 2
    assert s.taostats_request_timeout_seconds == 30
    assert s.taostats_backfill_batch_size == 200
    assert s.taostats_rate_limit_max_retries == 5


def test_validate_taostats_api_key_raises_in_production() -> None:
    """Production mode requires ENGINE_TAOSTATS_API_KEY."""
    with pytest.raises(ValidationError, match="ENGINE_TAOSTATS_API_KEY"):
        Settings(debug=False, address_encryption_key="key123", taostats_api_key="")


def test_wildcard_cors_rejected_in_production() -> None:
    """Production mode rejects wildcard '*' in CORS origins."""
    with pytest.raises(ValidationError, match="must not contain"):
        Settings(
            debug=False,
            address_encryption_key="key123",
            taostats_api_key="ts-key",
            cors_origins=["*"],
        )


def test_wildcard_cors_allowed_in_debug() -> None:
    """Debug mode allows wildcard CORS origins."""
    s = Settings(debug=True, cors_origins=["*"])
    assert s.cors_origins == ["*"]
