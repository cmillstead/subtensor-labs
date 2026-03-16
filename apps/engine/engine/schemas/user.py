"""Pydantic v2 schemas for user registration and authentication."""

from datetime import datetime

from pydantic import EmailStr, Field

from engine.schemas import BaseSchema


class UserRegisterSchema(BaseSchema):
    """User registration request."""

    email: EmailStr
    password: str = Field(min_length=8)


class UserVerifySchema(BaseSchema):
    """User credential verification request."""

    email: EmailStr
    password: str


class UserResponseSchema(BaseSchema):
    """User data returned after registration or verification."""

    id: int
    email: str
    premium_status: str
    created_at: datetime
