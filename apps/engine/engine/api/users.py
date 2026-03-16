"""User registration, credential verification, and password reset endpoints."""

import asyncio
import contextlib
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.config import settings
from engine.core.database import get_session
from engine.core.email import send_password_reset_email
from engine.core.logging import get_logger
from engine.models.password_reset_token import PasswordResetToken
from engine.models.user import User
from engine.schemas.user import (
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    UserRegisterSchema,
    UserResponseSchema,
    UserVerifySchema,
)

log = get_logger(__name__)
router = APIRouter(prefix="/users")
ph = PasswordHasher()

# Pre-computed dummy hash for constant-time comparison when user doesn't exist.
# Prevents timing side-channel that leaks email existence.
_DUMMY_HASH = ph.hash("dummy-password-for-timing-safety")


def _invalid_credentials_response() -> JSONResponse:
    """Standard 401 response for invalid credentials — no email enumeration."""
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "type": "invalid_credentials",
                "message": "Invalid email or password",
                "code": 401,
            }
        },
    )


def _user_response(user: User) -> dict[str, object]:
    """Build the standard user response envelope."""
    return {
        "data": UserResponseSchema(
            id=user.id,
            email=user.email,
            premium_status=user.premium_status,
            created_at=user.created_at,
        ).model_dump(mode="json")
    }


@router.post("/register")
async def register(
    body: UserRegisterSchema,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> JSONResponse:
    """Create a new user account with email and password."""
    existing = await session.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "type": "duplicate_email",
                    "message": "An account with this email already exists",
                    "code": 409,
                }
            },
        )

    user = User(
        email=body.email,
        password_hash=ph.hash(body.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    log.info("user_registered", user_id=user.id)
    return JSONResponse(status_code=201, content=_user_response(user))


@router.post("/verify")
async def verify(
    body: UserVerifySchema,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> JSONResponse:
    """Verify user credentials for login."""
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None:
        # Perform dummy verify to prevent timing side-channel that leaks email existence
        with contextlib.suppress(VerifyMismatchError):
            ph.verify(_DUMMY_HASH, body.password)
        return _invalid_credentials_response()

    try:
        ph.verify(user.password_hash, body.password)
    except VerifyMismatchError:
        return _invalid_credentials_response()

    # Rehash if argon2 parameters have changed
    if ph.check_needs_rehash(user.password_hash):
        user.password_hash = ph.hash(body.password)
        await session.commit()

    return JSONResponse(status_code=200, content=_user_response(user))


def _hash_token(raw_token: str) -> str:
    """SHA-256 hash a raw reset token for storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


_RESET_REQUEST_MESSAGE = "If an account exists with this email, a reset link has been sent."


@router.post("/reset-password/request")
async def request_password_reset(
    body: PasswordResetRequestSchema,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> JSONResponse:
    """Request a password reset email. Always returns 200 to prevent email enumeration."""
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None:
        # Simulate work to prevent timing side-channel that leaks email existence.
        # Without this, requests for nonexistent emails return ~instantly while valid
        # emails take longer (DB writes + email send), revealing which emails exist.
        await asyncio.sleep(0.1 + secrets.randbelow(100) / 1000)  # 100-200ms jitter
        log.info("password_reset_requested_unknown_email")
        return JSONResponse(status_code=200, content={"message": _RESET_REQUEST_MESSAGE})

    # Invalidate any previous unused tokens for this user
    now = datetime.now(UTC)
    await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    # Generate and store new token
    raw_token = secrets.token_urlsafe(32)
    token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=now + timedelta(hours=1),
    )
    session.add(token_record)
    await session.commit()

    # Send reset email
    reset_url = f"{settings.password_reset_base_url}/auth/reset-password/confirm?token={raw_token}"
    try:
        send_password_reset_email(to=user.email, reset_url=reset_url)
    except Exception:
        log.exception("password_reset_email_failed", user_id=user.id)
        # Still return 200 — don't leak failure to the user

    return JSONResponse(status_code=200, content={"message": _RESET_REQUEST_MESSAGE})


@router.post("/reset-password/confirm")
async def confirm_password_reset(
    body: PasswordResetConfirmSchema,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> JSONResponse:
    """Confirm a password reset with token and new password."""
    token_hash = _hash_token(body.token)
    result = await session.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    token_record = result.scalar_one_or_none()

    if token_record is None or token_record.used_at is not None:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "type": "invalid_token",
                    "message": "This reset link is invalid or has already been used.",
                    "code": 400,
                }
            },
        )

    now = datetime.now(UTC)
    if token_record.expires_at < now:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "type": "token_expired",
                    "message": "This reset link has expired. Please request a new one.",
                    "code": 400,
                }
            },
        )

    # Update password and mark token as used
    user_result = await session.execute(select(User).where(User.id == token_record.user_id))
    user = user_result.scalar_one()
    user.password_hash = ph.hash(body.password)
    token_record.used_at = now
    await session.commit()

    log.info("password_reset_confirmed", user_id=user.id)
    return JSONResponse(
        status_code=200,
        content={"message": "Password has been reset successfully."},
    )
