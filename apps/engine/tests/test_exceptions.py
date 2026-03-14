"""Tests for exception hierarchy."""

from engine.core.exceptions import (
    ChainError,
    EngineError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)


def test_engine_error_defaults() -> None:
    err = EngineError("something broke")
    assert err.message == "something broke"
    assert err.error_type == "engine_error"
    assert err.code == 500


def test_not_found_error() -> None:
    err = NotFoundError("user not found")
    assert err.code == 404
    assert err.error_type == "not_found"


def test_validation_error() -> None:
    err = ValidationError("bad input")
    assert err.code == 422


def test_chain_error() -> None:
    err = ChainError("RPC timeout")
    assert err.code == 503


def test_rate_limit_error() -> None:
    err = RateLimitError("too many requests")
    assert err.code == 429
    assert err.error_type == "rate_limit"
