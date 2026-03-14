"""Tests for structlog configuration and address redaction."""

from engine.core.logging import _redact_addresses


def test_address_redaction() -> None:
    """SS58 addresses are redacted in log output."""
    event_dict = {
        "event": "portfolio_loaded",
        "address": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
    }
    result = _redact_addresses(None, "", event_dict)  # type: ignore[arg-type]
    assert result["address"] == "5GrwvaEF...utQY"


def test_no_redaction_on_short_strings() -> None:
    """Short strings that don't match SS58 pattern are not modified."""
    event_dict = {"event": "test", "message": "hello world"}
    result = _redact_addresses(None, "", event_dict)  # type: ignore[arg-type]
    assert result["message"] == "hello world"


def test_redaction_preserves_non_string_values() -> None:
    """Non-string values pass through unchanged."""
    event_dict = {"event": "test", "count": 42, "active": True}
    result = _redact_addresses(None, "", event_dict)  # type: ignore[arg-type]
    assert result["count"] == 42
    assert result["active"] is True
