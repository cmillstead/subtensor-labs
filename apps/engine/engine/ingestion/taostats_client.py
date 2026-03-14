"""Async HTTP client for the Taostats REST API."""

import asyncio
import random
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel

from engine.core.config import settings
from engine.core.logging import get_logger

log = get_logger(__name__)

# Exponential backoff parameters
_BACKOFF_BASE_S = 2.0
_BACKOFF_MAX_S = 120.0


class TaostatsPagination(BaseModel):
    """Pagination envelope from Taostats API responses."""

    current_page: int
    per_page: int
    total_items: int
    total_pages: int
    next_page: int | None = None
    prev_page: int | None = None


class TaostatsResponse(BaseModel):
    """Standard Taostats API response wrapper."""

    pagination: TaostatsPagination
    data: list[dict[str, Any]]


class TaostatsClient:
    """Async HTTP client for Taostats API with pagination and rate limit handling."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._base_url = base_url or settings.taostats_api_url
        self._api_key = api_key or settings.taostats_api_key
        self._timeout = timeout or settings.taostats_request_timeout_seconds
        self._max_retries = max_retries or settings.taostats_rate_limit_max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx async client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"Authorization": self._api_key},
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request_with_retry(self, path: str, params: dict[str, Any]) -> httpx.Response:
        """Make a GET request with exponential backoff on 429 responses."""
        client = await self._get_client()

        for attempt in range(self._max_retries + 1):
            response = await client.get(path, params=params)

            if response.status_code != 429:
                response.raise_for_status()
                return response

            if attempt == self._max_retries:
                log.error(
                    "taostats_rate_limit_exhausted",
                    path=path,
                    attempts=attempt + 1,
                    worker="taostats_client",
                )
                response.raise_for_status()

            # Exponential backoff with jitter
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                delay = float(retry_after)
            else:
                delay = min(_BACKOFF_BASE_S * (2**attempt), _BACKOFF_MAX_S)
                delay += random.uniform(0, delay * 0.25)  # noqa: S311

            log.warning(
                "taostats_rate_limited",
                path=path,
                attempt=attempt + 1,
                retry_after_s=round(delay, 1),
                worker="taostats_client",
            )
            await asyncio.sleep(delay)

        # Unreachable but satisfies type checker
        raise httpx.HTTPStatusError(  # pragma: no cover
            "Max retries exhausted",
            request=httpx.Request("GET", path),
            response=httpx.Response(429),
        )

    async def fetch_page(self, path: str, params: dict[str, Any] | None = None) -> TaostatsResponse:
        """Fetch a single page from a Taostats API endpoint."""
        params = dict(params) if params else {}
        response = await self._request_with_retry(path, params)
        data = response.json()
        return TaostatsResponse(**data)

    async def fetch_all_pages(
        self, path: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all pages from a paginated Taostats API endpoint.

        Auto-follows pagination.next_page until all data is consumed.
        """
        params = dict(params) if params else {}
        params.setdefault("limit", settings.taostats_backfill_batch_size)
        params.setdefault("order", "timestamp_asc")

        all_data: list[dict[str, Any]] = []
        page = params.get("page", 1)

        while True:
            params["page"] = page
            result = await self.fetch_page(path, params)
            all_data.extend(result.data)

            if result.pagination.next_page is None:
                break

            page = result.pagination.next_page

        return all_data

    async def fetch_subnet_latest(self) -> list[dict[str, Any]]:
        """Fetch current subnet metadata."""
        return await self.fetch_all_pages("/api/subnet/latest/v1")

    async def fetch_subnet_emission(
        self,
        *,
        subnet_id: int | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch subnet emission history."""
        params: dict[str, Any] = {}
        if subnet_id is not None:
            params["subnet_id"] = subnet_id
        if since is not None:
            params["timestamp_start"] = int(since.timestamp())
        if until is not None:
            params["timestamp_end"] = int(until.timestamp())
        return await self.fetch_all_pages("/api/dtao/subnet_emission/v1", params)

    async def fetch_metagraph_history(
        self,
        *,
        subnet_id: int,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch metagraph history for a subnet."""
        params: dict[str, Any] = {"subnet_id": subnet_id}
        if since is not None:
            params["timestamp_start"] = int(since.timestamp())
        if until is not None:
            params["timestamp_end"] = int(until.timestamp())
        return await self.fetch_all_pages("/api/metagraph/history/v1", params)

    async def fetch_price_history(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch TAO price history."""
        params: dict[str, Any] = {"asset": "TAO"}
        if since is not None:
            params["timestamp_start"] = int(since.timestamp())
        if until is not None:
            params["timestamp_end"] = int(until.timestamp())
        return await self.fetch_all_pages("/api/price/history/v1", params)
