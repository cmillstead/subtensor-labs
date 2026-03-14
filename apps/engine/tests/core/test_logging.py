"""Tests for logging configuration."""

import structlog

from engine.core.logging import setup_logging


def test_setup_logging_debug_uses_console_renderer() -> None:
    """Debug mode configures ConsoleRenderer for human-readable output."""
    setup_logging(debug=True)
    config = structlog.get_config()
    renderers = [p for p in config["processors"] if isinstance(p, structlog.dev.ConsoleRenderer)]
    assert len(renderers) == 1


def test_setup_logging_production_uses_json_renderer() -> None:
    """Production mode configures JSONRenderer for structured log aggregation."""
    setup_logging(debug=False)
    config = structlog.get_config()
    renderers = [
        p for p in config["processors"] if isinstance(p, structlog.processors.JSONRenderer)
    ]
    assert len(renderers) == 1
