"""Pydantic v2 schemas for saved screener CRUD operations."""

from datetime import datetime
from typing import Any

from pydantic import Field

from engine.schemas import BaseSchema


class SavedScreenerCreateSchema(BaseSchema):
    """Create a saved screener configuration."""

    name: str = Field(min_length=1, max_length=100)
    filters_json: dict[str, Any]


class SavedScreenerUpdateSchema(BaseSchema):
    """Update an existing saved screener configuration."""

    name: str | None = Field(None, min_length=1, max_length=100)
    filters_json: dict[str, Any] | None = None


class SavedScreenerResponseSchema(BaseSchema):
    """Saved screener returned from the API."""

    id: int
    name: str
    filters_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
