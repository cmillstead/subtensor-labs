"""CRUD endpoints for user saved addresses."""

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.database import get_session
from engine.core.logging import get_logger
from engine.models.user_address import UserAddress
from engine.schemas.user import (
    AddressCreateSchema,
    AddressResponseSchema,
    AddressUpdateSchema,
)

log = get_logger(__name__)
router = APIRouter(prefix="/users/{user_id}/addresses")

MAX_ADDRESSES_PER_USER = 20


def _address_response(addr: UserAddress) -> dict[str, object]:
    """Build the standard address response."""
    return AddressResponseSchema(
        id=addr.id,
        coldkey_address=addr.coldkey_address,
        label=addr.label,
        is_watch_only=addr.is_watch_only,
        created_at=addr.created_at,
    ).model_dump(mode="json")


def _forbidden_response() -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "type": "forbidden",
                "message": "You can only access your own addresses",
                "code": 403,
            }
        },
    )


def _not_found_response() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "type": "not_found",
                "message": "Address not found",
                "code": 404,
            }
        },
    )


@router.get("")
async def list_addresses(
    user_id: int,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    x_user_id: str = Header(...),  # noqa: B008
) -> JSONResponse:
    """List all saved addresses for a user."""
    if str(user_id) != x_user_id:
        return _forbidden_response()

    result = await session.execute(
        select(UserAddress).where(UserAddress.user_id == user_id).order_by(UserAddress.created_at)
    )
    addresses = result.scalars().all()
    return JSONResponse(
        status_code=200,
        content={"data": [_address_response(a) for a in addresses]},
    )


@router.post("")
async def create_address(
    user_id: int,
    body: AddressCreateSchema,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    x_user_id: str = Header(...),  # noqa: B008
) -> JSONResponse:
    """Save a new coldkey address for a user."""
    if str(user_id) != x_user_id:
        return _forbidden_response()

    # Load all addresses for this user (max 20) to check duplicates and count.
    # SQL equality won't work on EncryptedString (AES-256-GCM random nonce),
    # so we compare decrypted values in Python.
    all_result = await session.execute(select(UserAddress).where(UserAddress.user_id == user_id))
    existing_addresses = all_result.scalars().all()

    if any(a.coldkey_address == body.coldkey_address for a in existing_addresses):
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "type": "duplicate_address",
                    "message": "This address is already saved",
                    "code": 409,
                }
            },
        )

    if len(existing_addresses) >= MAX_ADDRESSES_PER_USER:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "type": "address_limit_reached",
                    "message": f"Maximum {MAX_ADDRESSES_PER_USER} addresses allowed",
                    "code": 400,
                }
            },
        )

    addr = UserAddress(
        user_id=user_id,
        coldkey_address=body.coldkey_address,
        label=body.label,
        is_watch_only=body.is_watch_only,
    )
    session.add(addr)
    await session.commit()
    await session.refresh(addr)

    log.info("address_created", user_id=user_id, address_id=addr.id)
    return JSONResponse(status_code=201, content={"data": _address_response(addr)})


@router.patch("/{address_id}")
async def update_address(
    user_id: int,
    address_id: int,
    body: AddressUpdateSchema,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    x_user_id: str = Header(...),  # noqa: B008
) -> JSONResponse:
    """Update the label on a saved address."""
    if str(user_id) != x_user_id:
        return _forbidden_response()

    result = await session.execute(
        select(UserAddress).where(
            UserAddress.id == address_id,
            UserAddress.user_id == user_id,
        )
    )
    addr = result.scalar_one_or_none()
    if addr is None:
        return _not_found_response()

    addr.label = body.label
    await session.commit()
    await session.refresh(addr)

    log.info("address_updated", user_id=user_id, address_id=address_id)
    return JSONResponse(status_code=200, content={"data": _address_response(addr)})


@router.delete("/{address_id}")
async def delete_address(
    user_id: int,
    address_id: int,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    x_user_id: str = Header(...),  # noqa: B008
) -> JSONResponse:
    """Remove a saved address."""
    if str(user_id) != x_user_id:
        return _forbidden_response()

    result = await session.execute(
        select(UserAddress).where(
            UserAddress.id == address_id,
            UserAddress.user_id == user_id,
        )
    )
    addr = result.scalar_one_or_none()
    if addr is None:
        return _not_found_response()

    await session.delete(addr)
    await session.commit()

    log.info("address_deleted", user_id=user_id, address_id=address_id)
    return JSONResponse(
        status_code=200,
        content={"message": "Address removed."},
    )
