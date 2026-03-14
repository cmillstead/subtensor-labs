"""Error response envelope schema."""

from engine import __version__
from engine.schemas import BaseSchema

ENGINE_VERSION: str = __version__


class ErrorDetail(BaseSchema):
    """Error detail within the error envelope."""

    type: str
    message: str
    code: int


class ErrorResponseSchema(BaseSchema):
    """Standard error response envelope."""

    error: ErrorDetail
