"""Structured logging configuration with address redaction."""

import re

import structlog

# Bittensor SS58 address pattern (starts with 5, 48 chars)
_ADDRESS_PATTERN = re.compile(r"\b5[A-HJ-NP-Za-km-z1-9]{47}\b")

# Initialize structlog early so module-level get_logger() calls use correct config.
# This runs at import time before any logger is used.
_configured = False


def _redact_addresses(
    _logger: structlog.types.WrappedLogger,
    _method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Redact Bittensor SS58 addresses from log output."""
    for key, value in event_dict.items():
        if isinstance(value, str):
            event_dict[key] = _ADDRESS_PATTERN.sub(
                lambda m: m.group()[:8] + "..." + m.group()[-4:], value
            )
    return event_dict


def setup_logging(*, debug: bool = False) -> None:
    """Configure structlog for JSON output with address redaction."""
    global _configured  # noqa: PLW0603
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            _redact_addresses,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    _configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a named logger instance."""
    if not _configured:
        setup_logging()
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
