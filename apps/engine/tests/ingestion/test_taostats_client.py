"""Tests for the Taostats API client."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from engine.ingestion.taostats_client import (
    TaostatsClient,
    TaostatsPagination,
    TaostatsResponse,
)


def _make_response(
    data: list,
    *,
    status_code: int = 200,
    current_page: int = 1,
    total_pages: int = 1,
    next_page: int | None = None,
    headers: dict | None = None,
) -> httpx.Response:
    """Create a mock httpx.Response with Taostats pagination envelope."""
    body = {
        "pagination": {
            "current_page": current_page,
            "per_page": 200,
            "total_items": len(data),
            "total_pages": total_pages,
            "next_page": next_page,
            "prev_page": None,
        },
        "data": data,
    }
    response = httpx.Response(
        status_code=status_code,
        json=body if status_code == 200 else None,
        headers=headers or {},
        request=httpx.Request("GET", "http://test/api/test"),
    )
    return response


def _make_429_response(*, retry_after: str | None = None) -> httpx.Response:
    """Create a 429 rate-limited response."""
    headers = {}
    if retry_after:
        headers["Retry-After"] = retry_after
    return httpx.Response(
        status_code=429,
        headers=headers,
        request=httpx.Request("GET", "http://test/api/test"),
    )


class TestTaostatsResponseModel:
    """Test Pydantic response models."""

    def test_pagination_model(self) -> None:
        p = TaostatsPagination(
            current_page=1, per_page=50, total_items=100, total_pages=2, next_page=2
        )
        assert p.current_page == 1
        assert p.next_page == 2

    def test_response_model(self) -> None:
        r = TaostatsResponse(
            pagination=TaostatsPagination(
                current_page=1, per_page=50, total_items=1, total_pages=1
            ),
            data=[{"subnet_id": 1, "name": "test"}],
        )
        assert len(r.data) == 1
        assert r.pagination.next_page is None


class TestTaostatsClientAuth:
    """Test authentication header."""

    async def test_auth_header_sent(self) -> None:
        """Verify Authorization header is set on requests."""
        client = TaostatsClient(
            base_url="http://test", api_key="test-key-123", timeout=5, max_retries=0
        )

        mock_response = _make_response([{"id": 1}])

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            await client.fetch_page("/api/test/v1")

        # Verify the client was created with auth header
        http_client = await client._get_client()
        assert http_client.headers["authorization"] == "test-key-123"
        await client.close()


class TestTaostatsClientPagination:
    """Test paginated fetching."""

    async def test_single_page(self) -> None:
        """Single page response returns all data."""
        client = TaostatsClient(base_url="http://test", api_key="key", timeout=5, max_retries=0)

        page1 = _make_response(
            [{"id": 1}, {"id": 2}],
            current_page=1,
            total_pages=1,
            next_page=None,
        )

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = page1
            data = await client.fetch_all_pages("/api/test/v1")

        assert len(data) == 2
        assert data[0]["id"] == 1
        await client.close()

    async def test_multi_page(self) -> None:
        """Multi-page response follows pagination.next_page."""
        client = TaostatsClient(base_url="http://test", api_key="key", timeout=5, max_retries=0)

        page1 = _make_response([{"id": 1}], current_page=1, total_pages=3, next_page=2)
        page2 = _make_response([{"id": 2}], current_page=2, total_pages=3, next_page=3)
        page3 = _make_response([{"id": 3}], current_page=3, total_pages=3, next_page=None)

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [page1, page2, page3]
            data = await client.fetch_all_pages("/api/test/v1")

        assert len(data) == 3
        assert [d["id"] for d in data] == [1, 2, 3]
        assert mock_get.call_count == 3
        await client.close()

    async def test_empty_response(self) -> None:
        """Empty data returns empty list."""
        client = TaostatsClient(base_url="http://test", api_key="key", timeout=5, max_retries=0)

        empty = _make_response([], current_page=1, total_pages=1, next_page=None)

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = empty
            data = await client.fetch_all_pages("/api/test/v1")

        assert data == []
        await client.close()


class TestTaostatsClientRateLimit:
    """Test 429 rate limit handling with exponential backoff."""

    async def test_retry_on_429(self) -> None:
        """429 response triggers retry with eventual success."""
        client = TaostatsClient(base_url="http://test", api_key="key", timeout=5, max_retries=3)

        rate_limited = _make_429_response()
        success = _make_response([{"id": 1}])

        with (
            patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get,
            patch(
                "engine.ingestion.taostats_client.asyncio.sleep", new_callable=AsyncMock
            ) as mock_sleep,
        ):
            mock_get.side_effect = [rate_limited, rate_limited, success]
            data = await client.fetch_page("/api/test/v1")

        assert len(data.data) == 1
        assert mock_sleep.call_count == 2  # Two retries before success
        await client.close()

    async def test_retry_after_header(self) -> None:
        """Retry-After header is respected for backoff delay."""
        client = TaostatsClient(base_url="http://test", api_key="key", timeout=5, max_retries=3)

        rate_limited = _make_429_response(retry_after="5")
        success = _make_response([{"id": 1}])

        with (
            patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get,
            patch(
                "engine.ingestion.taostats_client.asyncio.sleep", new_callable=AsyncMock
            ) as mock_sleep,
        ):
            mock_get.side_effect = [rate_limited, success]
            await client.fetch_page("/api/test/v1")

        mock_sleep.assert_called_once()
        delay = mock_sleep.call_args[0][0]
        assert delay == 5.0  # Respects Retry-After header
        await client.close()

    async def test_max_retries_exhausted(self) -> None:
        """Max retries exhausted raises HTTPStatusError."""
        client = TaostatsClient(base_url="http://test", api_key="key", timeout=5, max_retries=2)

        rate_limited = _make_429_response()

        with (
            patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get,
            patch("engine.ingestion.taostats_client.asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(httpx.HTTPStatusError),
        ):
            mock_get.return_value = rate_limited
            await client.fetch_page("/api/test/v1")

        await client.close()


class TestTaostatsClientEndpoints:
    """Test convenience methods for specific API endpoints."""

    async def test_fetch_subnet_emission(self) -> None:
        """fetch_subnet_emission passes correct params."""
        client = TaostatsClient(base_url="http://test", api_key="key", timeout=5, max_retries=0)

        resp = _make_response([{"emission": "0.05"}])
        since = datetime(2024, 1, 1, tzinfo=UTC)

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = resp
            data = await client.fetch_subnet_emission(subnet_id=19, since=since)

        assert len(data) == 1
        call_params = mock_get.call_args[1]["params"]
        assert call_params["subnet_id"] == 19
        assert call_params["timestamp_start"] == int(since.timestamp())
        await client.close()

    async def test_fetch_price_history(self) -> None:
        """fetch_price_history passes asset=TAO."""
        client = TaostatsClient(base_url="http://test", api_key="key", timeout=5, max_retries=0)

        resp = _make_response([{"price": "450.00"}])

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = resp
            await client.fetch_price_history()

        call_params = mock_get.call_args[1]["params"]
        assert call_params["asset"] == "TAO"
        await client.close()

    async def test_fetch_metagraph_history(self) -> None:
        """fetch_metagraph_history passes subnet_id."""
        client = TaostatsClient(base_url="http://test", api_key="key", timeout=5, max_retries=0)

        resp = _make_response([{"neuron_count": 50}])

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = resp
            await client.fetch_metagraph_history(subnet_id=1)

        call_params = mock_get.call_args[1]["params"]
        assert call_params["subnet_id"] == 1
        await client.close()
