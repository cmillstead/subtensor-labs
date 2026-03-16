"""User registration and credential verification endpoints."""

import contextlib

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.database import get_session
from engine.core.logging import get_logger
from engine.models.user import User
from engine.schemas.user import UserRegisterSchema, UserResponseSchema, UserVerifySchema

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
