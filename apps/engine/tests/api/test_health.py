"""Tests for the health endpoint."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from engine.api.health import BackfillStatus, PriceSyncStatus, SyncStatus


def _mock_sync_status(
    last_sync_at: datetime | None = None,
    subnets_synced: int | None = None,
    subnets_failed: int | None = None,
    subnets_stale: list[int] | None = None,
    sync_healthy: bool = True,
) -> SyncStatus:
    return SyncStatus(
        last_sync_completed_at=last_sync_at.isoformat() if last_sync_at else None,
        subnets_synced=subnets_synced,
        subnets_failed=subnets_failed,
        subnets_stale=subnets_stale or [],
        sync_healthy=sync_healthy,
    )


def _mock_price_sync_status(
    last_price_sync_at: datetime | None = None,
    subnets_priced: int | None = None,
    subnets_price_failed: int | None = None,
    subnets_price_stale: list[int] | None = None,
    price_sync_healthy: bool = True,
) -> PriceSyncStatus:
    return PriceSyncStatus(
        last_price_sync_at=last_price_sync_at.isoformat() if last_price_sync_at else None,
        subnets_priced=subnets_priced,
        subnets_price_failed=subnets_price_failed,
        subnets_price_stale=subnets_price_stale or [],
        price_sync_healthy=price_sync_healthy,
    )


def _mock_backfill_status(
    last_backfill_at: datetime | None = None,
    subnets_backfilled: int | None = None,
    subnets_failed: int | None = None,
    total_records_written: int | None = None,
    backfill_healthy: bool = True,
) -> BackfillStatus:
    return BackfillStatus(
        last_backfill_at=last_backfill_at.isoformat() if last_backfill_at else None,
        subnets_backfilled=subnets_backfilled,
        subnets_failed=subnets_failed,
        total_records_written=total_records_written,
        backfill_healthy=backfill_healthy,
    )


@pytest.fixture
def _fresh_backfill() -> BackfillStatus:
    return _mock_backfill_status(backfill_healthy=True)


@pytest.fixture
def _fresh_sync() -> SyncStatus:
    return _mock_sync_status(
        last_sync_at=datetime.now(UTC),
        subnets_synced=10,
        subnets_failed=0,
    )


@pytest.fixture
def _fresh_price_sync() -> PriceSyncStatus:
    return _mock_price_sync_status(
        last_price_sync_at=datetime.now(UTC),
        subnets_priced=10,
        subnets_price_failed=0,
    )


@pytest.mark.asyncio
async def test_health_endpoint_healthy(
    client: AsyncClient, _fresh_sync: SyncStatus, _fresh_price_sync: PriceSyncStatus
) -> None:
    """Health endpoint returns 200 with healthy status when all services are up."""
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
        patch(
            "engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=_fresh_sync
        ),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=_fresh_price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=_mock_backfill_status(),
        ),
    ):
        response = await client.get("/engine/health")

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "healthy"
    assert data["data"]["engine"] == "running"
    assert data["data"]["database"] == "connected"
    assert data["data"]["redis"] == "connected"
    assert data["data"]["sync"]["sync_healthy"] is True
    assert data["data"]["price_sync"]["price_sync_healthy"] is True
    assert data["meta"]["service"] == "subtensor-labs-engine"


@pytest.mark.asyncio
async def test_health_endpoint_degraded_no_db(
    client: AsyncClient, _fresh_sync: SyncStatus, _fresh_price_sync: PriceSyncStatus
) -> None:
    """Health endpoint returns 503 with degraded status when database is down."""
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=False),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
        patch(
            "engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=_fresh_sync
        ),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=_fresh_price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=_mock_backfill_status(),
        ),
    ):
        response = await client.get("/engine/health")

    assert response.status_code == 503
    data = response.json()
    assert data["data"]["status"] == "degraded"
    assert data["data"]["database"] == "disconnected"
    assert data["data"]["redis"] == "connected"


@pytest.mark.asyncio
async def test_health_endpoint_degraded_no_redis(
    client: AsyncClient, _fresh_sync: SyncStatus, _fresh_price_sync: PriceSyncStatus
) -> None:
    """Health endpoint returns 503 with degraded status when Redis is down."""
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=False),
        patch(
            "engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=_fresh_sync
        ),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=_fresh_price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=_mock_backfill_status(),
        ),
    ):
        response = await client.get("/engine/health")

    assert response.status_code == 503
    data = response.json()
    assert data["data"]["status"] == "degraded"
    assert data["data"]["database"] == "connected"
    assert data["data"]["redis"] == "disconnected"


@pytest.mark.asyncio
async def test_health_endpoint_degraded_both_down(
    client: AsyncClient, _fresh_sync: SyncStatus, _fresh_price_sync: PriceSyncStatus
) -> None:
    """Health endpoint returns 503 with degraded status when both services are down."""
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=False),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=False),
        patch(
            "engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=_fresh_sync
        ),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=_fresh_price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=_mock_backfill_status(),
        ),
    ):
        response = await client.get("/engine/health")

    assert response.status_code == 503
    data = response.json()
    assert data["data"]["status"] == "degraded"
    assert data["data"]["database"] == "disconnected"
    assert data["data"]["redis"] == "disconnected"


@pytest.mark.asyncio
async def test_health_response_matches_schema(
    client: AsyncClient, _fresh_sync: SyncStatus, _fresh_price_sync: PriceSyncStatus
) -> None:
    """Health endpoint response matches the documented envelope format."""
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
        patch(
            "engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=_fresh_sync
        ),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=_fresh_price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=_mock_backfill_status(),
        ),
    ):
        response = await client.get("/engine/health")

    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert set(data["data"].keys()) == {
        "status",
        "engine",
        "database",
        "redis",
        "sync",
        "price_sync",
        "backfill",
    }
    assert set(data["meta"].keys()) == {"service"}


@pytest.mark.asyncio
async def test_health_sync_status_included(
    client: AsyncClient, _fresh_price_sync: PriceSyncStatus
) -> None:
    """Health response includes sync status details."""
    now = datetime.now(UTC)
    sync = _mock_sync_status(last_sync_at=now, subnets_synced=5, subnets_failed=1)
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=sync),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=_fresh_price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=_mock_backfill_status(),
        ),
    ):
        response = await client.get("/engine/health")

    data = response.json()
    sync_data = data["data"]["sync"]
    assert sync_data["last_sync_completed_at"] == now.isoformat()
    assert sync_data["subnets_synced"] == 5
    assert sync_data["subnets_failed"] == 1
    assert sync_data["subnets_stale"] == []
    assert sync_data["sync_healthy"] is True


@pytest.mark.asyncio
async def test_health_sync_never_ran(
    client: AsyncClient, _fresh_price_sync: PriceSyncStatus
) -> None:
    """Health shows sync_healthy=False when sync has never run."""
    sync = _mock_sync_status(sync_healthy=False)
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=sync),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=_fresh_price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=_mock_backfill_status(),
        ),
    ):
        response = await client.get("/engine/health")

    data = response.json()
    assert data["data"]["sync"]["last_sync_completed_at"] is None
    assert data["data"]["sync"]["sync_healthy"] is False
    # Still 200 because DB and Redis are healthy and no stale timestamp
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_sync_critically_stale(
    client: AsyncClient, _fresh_price_sync: PriceSyncStatus
) -> None:
    """Health returns 503 when sync is critically stale (> 10 min)."""
    stale_time = datetime.now(UTC) - timedelta(minutes=15)
    sync = _mock_sync_status(
        last_sync_at=stale_time, subnets_synced=10, subnets_failed=0, sync_healthy=False
    )
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=sync),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=_fresh_price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=_mock_backfill_status(),
        ),
    ):
        response = await client.get("/engine/health")

    assert response.status_code == 503
    data = response.json()
    assert data["data"]["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_reports_stale_subnets(
    client: AsyncClient, _fresh_price_sync: PriceSyncStatus
) -> None:
    """Health response includes stale subnet netuids."""
    now = datetime.now(UTC)
    sync = _mock_sync_status(
        last_sync_at=now,
        subnets_synced=10,
        subnets_failed=0,
        subnets_stale=[3, 19],
    )
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=sync),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=_fresh_price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=_mock_backfill_status(),
        ),
    ):
        response = await client.get("/engine/health")

    data = response.json()
    assert data["data"]["sync"]["subnets_stale"] == [3, 19]


@pytest.mark.asyncio
async def test_health_price_sync_status_included(
    client: AsyncClient, _fresh_sync: SyncStatus
) -> None:
    """Health response includes price sync status details."""
    now = datetime.now(UTC)
    price_sync = _mock_price_sync_status(
        last_price_sync_at=now, subnets_priced=8, subnets_price_failed=2
    )
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
        patch(
            "engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=_fresh_sync
        ),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=_mock_backfill_status(),
        ),
    ):
        response = await client.get("/engine/health")

    data = response.json()
    ps = data["data"]["price_sync"]
    assert ps["last_price_sync_at"] == now.isoformat()
    assert ps["subnets_priced"] == 8
    assert ps["subnets_price_failed"] == 2
    assert ps["subnets_price_stale"] == []
    assert ps["price_sync_healthy"] is True


@pytest.mark.asyncio
async def test_health_price_sync_critically_stale(
    client: AsyncClient, _fresh_sync: SyncStatus
) -> None:
    """Health returns 503 when price sync is critically stale (> 10 min)."""
    stale_time = datetime.now(UTC) - timedelta(minutes=15)
    price_sync = _mock_price_sync_status(
        last_price_sync_at=stale_time,
        subnets_priced=10,
        subnets_price_failed=0,
        price_sync_healthy=False,
    )
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
        patch(
            "engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=_fresh_sync
        ),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=_mock_backfill_status(),
        ),
    ):
        response = await client.get("/engine/health")

    assert response.status_code == 503
    data = response.json()
    assert data["data"]["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_backfill_status_included(
    client: AsyncClient, _fresh_sync: SyncStatus, _fresh_price_sync: PriceSyncStatus
) -> None:
    """Health response includes backfill status details."""
    now = datetime.now(UTC)
    backfill = _mock_backfill_status(
        last_backfill_at=now,
        subnets_backfilled=10,
        subnets_failed=1,
        total_records_written=5000,
        backfill_healthy=True,
    )
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
        patch(
            "engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=_fresh_sync
        ),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=_fresh_price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=backfill,
        ),
    ):
        response = await client.get("/engine/health")

    data = response.json()
    bf = data["data"]["backfill"]
    assert bf["last_backfill_at"] == now.isoformat()
    assert bf["subnets_backfilled"] == 10
    assert bf["subnets_failed"] == 1
    assert bf["total_records_written"] == 5000
    assert bf["backfill_healthy"] is True


@pytest.mark.asyncio
async def test_health_backfill_never_ran(
    client: AsyncClient, _fresh_sync: SyncStatus, _fresh_price_sync: PriceSyncStatus
) -> None:
    """Health shows backfill_healthy=True even when backfill has never run."""
    backfill = _mock_backfill_status(backfill_healthy=True)
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
        patch(
            "engine.api.health._get_sync_status", new_callable=AsyncMock, return_value=_fresh_sync
        ),
        patch(
            "engine.api.health._get_price_sync_status",
            new_callable=AsyncMock,
            return_value=_fresh_price_sync,
        ),
        patch(
            "engine.api.health._get_backfill_status",
            new_callable=AsyncMock,
            return_value=backfill,
        ),
    ):
        response = await client.get("/engine/health")

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["backfill"]["backfill_healthy"] is True
    assert data["data"]["backfill"]["last_backfill_at"] is None
