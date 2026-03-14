"""Exception hierarchy for the engine."""


class EngineError(Exception):
    """Base exception for all engine errors."""

    def __init__(self, message: str, error_type: str = "engine_error", code: int = 500) -> None:
        self.message = message
        self.error_type = error_type
        self.code = code
        super().__init__(message)


class NotFoundError(EngineError):
    """Resource not found."""

    def __init__(self, message: str, error_type: str = "not_found") -> None:
        super().__init__(message=message, error_type=error_type, code=404)


class ValidationError(EngineError):
    """Input validation failed."""

    def __init__(self, message: str, error_type: str = "validation_error") -> None:
        super().__init__(message=message, error_type=error_type, code=422)


class ChainError(EngineError):
    """Error communicating with the Bittensor chain."""

    def __init__(self, message: str, error_type: str = "chain_error") -> None:
        super().__init__(message=message, error_type=error_type, code=503)


class RateLimitError(EngineError):
    """External API rate limit hit."""

    def __init__(self, message: str, error_type: str = "rate_limit") -> None:
        super().__init__(message=message, error_type=error_type, code=429)
