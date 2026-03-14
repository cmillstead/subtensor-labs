"""Error response envelope schema."""

from pydantic import BaseModel

ENGINE_VERSION = "0.1.0"


class ErrorDetail(BaseModel):
    """Error detail within the error envelope."""

    type: str
    message: str
    code: int


class ErrorResponseSchema(BaseModel):
    """Standard error response envelope."""

    error: ErrorDetail
