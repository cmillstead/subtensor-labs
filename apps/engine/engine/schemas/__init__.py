"""Pydantic v2 request/response schemas with snake_case enforcement."""

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema enforcing snake_case field serialization for all API schemas."""

    model_config = ConfigDict(populate_by_name=True)
