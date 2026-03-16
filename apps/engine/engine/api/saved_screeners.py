"""CRUD endpoints for user saved screener configurations."""

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.database import get_session
from engine.core.logging import get_logger
from engine.models.saved_screener import SavedScreener
from engine.schemas.saved_screener import (
    SavedScreenerCreateSchema,
    SavedScreenerResponseSchema,
    SavedScreenerUpdateSchema,
)

log = get_logger(__name__)
router = APIRouter(prefix="/users/{user_id}/saved-screeners")

MAX_SAVED_SCREENERS_PER_USER = 20


def _screener_response(screener: SavedScreener) -> dict[str, object]:
    """Build the standard saved screener response."""
    return SavedScreenerResponseSchema(
        id=screener.id,
        name=screener.name,
        filters_json=screener.filters_json,
        created_at=screener.created_at,
        updated_at=screener.updated_at,
    ).model_dump(mode="json")


def _forbidden_response() -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "type": "forbidden",
                "message": "You can only access your own saved screeners",
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
                "message": "Saved screener not found",
                "code": 404,
            }
        },
    )


@router.get("")
async def list_saved_screeners(
    user_id: int,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    x_user_id: str = Header(...),  # noqa: B008
) -> JSONResponse:
    """List all saved screeners for a user."""
    if str(user_id) != x_user_id:
        return _forbidden_response()

    result = await session.execute(
        select(SavedScreener)
        .where(SavedScreener.user_id == user_id)
        .order_by(SavedScreener.updated_at.desc())
    )
    screeners = result.scalars().all()
    return JSONResponse(
        status_code=200,
        content={"data": [_screener_response(s) for s in screeners]},
    )


@router.post("")
async def create_saved_screener(
    user_id: int,
    body: SavedScreenerCreateSchema,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    x_user_id: str = Header(...),  # noqa: B008
) -> JSONResponse:
    """Save a new screener configuration for a user."""
    if str(user_id) != x_user_id:
        return _forbidden_response()

    # Load all screeners for this user to check duplicates and count.
    all_result = await session.execute(
        select(SavedScreener).where(SavedScreener.user_id == user_id)
    )
    existing_screeners = all_result.scalars().all()

    if any(s.name == body.name for s in existing_screeners):
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "type": "duplicate_name",
                    "message": "A saved screener with this name already exists",
                    "code": 409,
                }
            },
        )

    if len(existing_screeners) >= MAX_SAVED_SCREENERS_PER_USER:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "type": "screener_limit_reached",
                    "message": f"Maximum {MAX_SAVED_SCREENERS_PER_USER} saved screeners allowed",
                    "code": 400,
                }
            },
        )

    screener = SavedScreener(
        user_id=user_id,
        name=body.name,
        filters_json=body.filters_json,
    )
    session.add(screener)
    await session.commit()
    await session.refresh(screener)

    log.info("saved_screener_created", user_id=user_id, screener_id=screener.id)
    return JSONResponse(status_code=201, content={"data": _screener_response(screener)})


@router.put("/{screener_id}")
async def update_saved_screener(
    user_id: int,
    screener_id: int,
    body: SavedScreenerUpdateSchema,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    x_user_id: str = Header(...),  # noqa: B008
) -> JSONResponse:
    """Update a saved screener configuration."""
    if str(user_id) != x_user_id:
        return _forbidden_response()

    result = await session.execute(
        select(SavedScreener).where(
            SavedScreener.id == screener_id,
            SavedScreener.user_id == user_id,
        )
    )
    screener = result.scalar_one_or_none()
    if screener is None:
        return _not_found_response()

    if body.name is not None:
        # Check for duplicate name (excluding current screener)
        dup_result = await session.execute(
            select(SavedScreener).where(
                SavedScreener.user_id == user_id,
                SavedScreener.name == body.name,
                SavedScreener.id != screener_id,
            )
        )
        if dup_result.scalar_one_or_none() is not None:
            return JSONResponse(
                status_code=409,
                content={
                    "error": {
                        "type": "duplicate_name",
                        "message": "A saved screener with this name already exists",
                        "code": 409,
                    }
                },
            )
        screener.name = body.name

    if body.filters_json is not None:
        screener.filters_json = body.filters_json

    await session.commit()
    await session.refresh(screener)

    log.info("saved_screener_updated", user_id=user_id, screener_id=screener_id)
    return JSONResponse(status_code=200, content={"data": _screener_response(screener)})


@router.delete("/{screener_id}")
async def delete_saved_screener(
    user_id: int,
    screener_id: int,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    x_user_id: str = Header(...),  # noqa: B008
) -> JSONResponse:
    """Remove a saved screener configuration."""
    if str(user_id) != x_user_id:
        return _forbidden_response()

    result = await session.execute(
        select(SavedScreener).where(
            SavedScreener.id == screener_id,
            SavedScreener.user_id == user_id,
        )
    )
    screener = result.scalar_one_or_none()
    if screener is None:
        return _not_found_response()

    await session.delete(screener)
    await session.commit()

    log.info("saved_screener_deleted", user_id=user_id, screener_id=screener_id)
    return JSONResponse(
        status_code=200,
        content={"message": "Screener removed."},
    )
