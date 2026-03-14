"""Tests for schema base class usage."""

import pytest

from engine.schemas import BaseSchema
from engine.schemas.errors import ErrorDetail, ErrorResponseSchema


@pytest.mark.parametrize(
    "cls",
    [ErrorDetail, ErrorResponseSchema],
    ids=lambda c: c.__name__,
)
def test_schema_classes_extend_base_schema(cls: type) -> None:
    """All API schema classes should extend BaseSchema for consistent config."""
    assert issubclass(cls, BaseSchema)
