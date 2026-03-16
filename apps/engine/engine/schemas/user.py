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


class PasswordResetRequestSchema(BaseSchema):
    """Password reset request — email only."""

    email: EmailStr


class PasswordResetConfirmSchema(BaseSchema):
    """Password reset confirmation — token + new password."""

    token: str
    password: str = Field(min_length=8)


class UserResponseSchema(BaseSchema):
    """User data returned after registration or verification."""

    id: int
    email: str
    premium_status: str
    created_at: datetime


class AddressCreateSchema(BaseSchema):
    """Create a saved address for a user."""

    coldkey_address: str = Field(pattern=r"^[1-9A-HJ-NP-Za-km-z]{46,48}$")
    label: str | None = Field(None, max_length=100)
    is_watch_only: bool = False


class AddressUpdateSchema(BaseSchema):
    """Update label on an existing saved address."""

    label: str | None = Field(None, max_length=100)


class AddressResponseSchema(BaseSchema):
    """Saved address returned from the API."""

    id: int
    coldkey_address: str
    label: str | None
    is_watch_only: bool
    created_at: datetime
