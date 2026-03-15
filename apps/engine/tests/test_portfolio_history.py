"""Tests for portfolio history feature."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from engine.schemas.portfolio import (
    PortfolioResponseSchema,
    SubnetPositionSchema,
)
from engine.schemas.portfolio_history import (
    PortfolioHistoryRequestSchema,
    PortfolioHistoryResponseSchema,
)

VALID_COLDKEY = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
VALID_COLDKEY_2 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
HOTKEY_1 = "5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy"


def _make_portfolio(
    positions: list[SubnetPositionSchema] | None = None,
) -> PortfolioResponseSchema:
    positions = positions or []
    return PortfolioResponseSchema(
        total_value_tao=sum(p.staked_tao + p.alpha_value_tao for p in positions),
        total_staked_tao=sum(p.staked_tao for p in positions),
        total_alpha_value_tao=sum(p.alpha_value_tao for p in positions),
        positions=positions,
        subnets_exposed=len({p.netuid for p in positions}),
        coldkeys_resolved=1,
        last_updated="2026-03-14T14:30:00Z",
    )


def _make_position(
    netuid: int = 1,
    staked_tao: float = 100.0,
    alpha_holdings: float = 50.0,
    alpha_value_tao: float = 25.0,
) -> SubnetPositionSchema:
    return SubnetPositionSchema(
        netuid=netuid,
        hotkey=HOTKEY_1,
        staked_tao=staked_tao,
        alpha_holdings=alpha_holdings,
        alpha_value_tao=alpha_value_tao,
        emission_share=0.05,
        incentive=0.0,
        trust=0.9,
        dividends=0.1,
        is_active=True,
        is_miner=False,
    )


class TestPortfolioHistoryRequestSchema:
    def test_valid_request(self) -> None:
        req = PortfolioHistoryRequestSchema(
            coldkey_addresses=[VALID_COLDKEY],
            time_range="7d",
        )
        assert req.time_range == "7d"

    def test_all_time_ranges(self) -> None:
        for tr in ("7d", "30d", "90d"):
            req = PortfolioHistoryRequestSchema(
                coldkey_addresses=[VALID_COLDKEY],
                time_range=tr,
            )
            assert req.time_range == tr

    def test_invalid_time_range(self) -> None:
        with pytest.raises(ValidationError):
            PortfolioHistoryRequestSchema(
                coldkey_addresses=[VALID_COLDKEY],
                time_range="1d",
            )

    def test_empty_addresses_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PortfolioHistoryRequestSchema(
                coldkey_addresses=[],
                time_range="7d",
            )

    def test_invalid_address_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PortfolioHistoryRequestSchema(
                coldkey_addresses=["not-valid"],
                time_range="7d",
            )

    def test_too_many_addresses_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PortfolioHistoryRequestSchema(
                coldkey_addresses=[VALID_COLDKEY] * 21,
                time_range="7d",
            )


class TestPortfolioHistoryResponseSchema:
    def test_empty_points(self) -> None:
        resp = PortfolioHistoryResponseSchema(points=[], data_start=None, time_range="7d")
        assert resp.points == []
        assert resp.data_start is None

    def test_with_points(self) -> None:
        resp = PortfolioHistoryResponseSchema(
            points=[{"time": "2026-03-14T00:00:00Z", "total_value_tao": 100.0}],
            data_start=None,
            time_range="30d",
        )
        assert len(resp.points) == 1
        assert resp.points[0].total_value_tao == 100.0


class TestGetPortfolioHistory:
    @patch("engine.portfolio.history.cache_set", new_callable=AsyncMock)
    @patch("engine.portfolio.history.cache_get", new_callable=AsyncMock)
    @patch("engine.portfolio.history.get_session_factory")
    @patch("engine.portfolio.history.aggregate_portfolio", new_callable=AsyncMock)
    async def test_with_positions(
        self,
        mock_agg: AsyncMock,
        mock_session_factory: MagicMock,
        mock_cache_get: AsyncMock,
        mock_cache_set: AsyncMock,
    ) -> None:
        from engine.portfolio.history import get_portfolio_history

        pos = _make_position(netuid=1, staked_tao=100.0, alpha_holdings=50.0)
        mock_agg.return_value = (_make_portfolio([pos]), False)
        mock_cache_get.return_value = None

        now = datetime.now(UTC)
        t1 = now - timedelta(hours=6)
        t2 = now - timedelta(hours=3)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (t1, 1, 0.5),
            (t2, 1, 0.6),
        ]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_factory = MagicMock()
        mock_factory.return_value = mock_session
        mock_session_factory.return_value = mock_factory

        points, data_start = await get_portfolio_history([VALID_COLDKEY], "7d")

        assert len(points) == 2
        assert points[0]["total_value_tao"] == round(100.0 + 50.0 * 0.5, 4)
        assert points[1]["total_value_tao"] == round(100.0 + 50.0 * 0.6, 4)
        mock_cache_set.assert_called_once()

    @patch("engine.portfolio.history.cache_set", new_callable=AsyncMock)
    @patch("engine.portfolio.history.cache_get", new_callable=AsyncMock)
    @patch("engine.portfolio.history.aggregate_portfolio", new_callable=AsyncMock)
    async def test_empty_positions(
        self,
        mock_agg: AsyncMock,
        mock_cache_get: AsyncMock,
        mock_cache_set: AsyncMock,
    ) -> None:
        from engine.portfolio.history import get_portfolio_history

        mock_agg.return_value = (_make_portfolio([]), False)
        mock_cache_get.return_value = None

        points, data_start = await get_portfolio_history([VALID_COLDKEY], "7d")

        assert points == []
        assert data_start is None

    @patch("engine.portfolio.history.cache_set", new_callable=AsyncMock)
    @patch("engine.portfolio.history.cache_get", new_callable=AsyncMock)
    @patch("engine.portfolio.history.get_session_factory")
    @patch("engine.portfolio.history.aggregate_portfolio", new_callable=AsyncMock)
    async def test_sparse_data_sets_data_start(
        self,
        mock_agg: AsyncMock,
        mock_session_factory: MagicMock,
        mock_cache_get: AsyncMock,
        mock_cache_set: AsyncMock,
    ) -> None:
        from engine.portfolio.history import get_portfolio_history

        pos = _make_position(netuid=1)
        mock_agg.return_value = (_make_portfolio([pos]), False)
        mock_cache_get.return_value = None

        # Data starts only 2 days ago, not 7
        first_data_time = datetime.now(UTC) - timedelta(days=2)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (first_data_time, 1, 0.5),
        ]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_factory = MagicMock()
        mock_factory.return_value = mock_session
        mock_session_factory.return_value = mock_factory

        points, data_start = await get_portfolio_history([VALID_COLDKEY], "7d")

        assert len(points) == 1
        assert data_start is not None

    @patch("engine.portfolio.history.cache_get", new_callable=AsyncMock)
    async def test_cache_hit(self, mock_cache_get: AsyncMock) -> None:
        from engine.portfolio.history import get_portfolio_history

        cached_data = {
            "points": [{"time": "2026-03-14T00:00:00Z", "total_value_tao": 150.0}],
            "data_start": None,
        }
        mock_cache_get.return_value = json.dumps(cached_data)

        points, data_start = await get_portfolio_history([VALID_COLDKEY], "7d")

        assert len(points) == 1
        assert points[0]["total_value_tao"] == 150.0
        assert data_start is None

    @patch("engine.portfolio.history.cache_set", new_callable=AsyncMock)
    @patch("engine.portfolio.history.cache_get", new_callable=AsyncMock)
    @patch("engine.portfolio.history.get_session_factory")
    @patch("engine.portfolio.history.aggregate_portfolio", new_callable=AsyncMock)
    async def test_no_db_rows_returns_empty(
        self,
        mock_agg: AsyncMock,
        mock_session_factory: MagicMock,
        mock_cache_get: AsyncMock,
        mock_cache_set: AsyncMock,
    ) -> None:
        from engine.portfolio.history import get_portfolio_history

        pos = _make_position(netuid=1)
        mock_agg.return_value = (_make_portfolio([pos]), False)
        mock_cache_get.return_value = None

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_factory = MagicMock()
        mock_factory.return_value = mock_session
        mock_session_factory.return_value = mock_factory

        points, data_start = await get_portfolio_history([VALID_COLDKEY], "7d")

        assert points == []
        assert data_start is None


class TestPortfolioHistoryEndpoint:
    @patch("engine.api.portfolio.get_portfolio_history", new_callable=AsyncMock)
    async def test_valid_request(self, mock_history: AsyncMock, client: AsyncMock) -> None:
        mock_history.return_value = (
            [{"time": "2026-03-14T00:00:00Z", "total_value_tao": 150.0}],
            None,
        )

        response = await client.post(
            "/engine/portfolio/history",
            json={"coldkey_addresses": [VALID_COLDKEY], "time_range": "7d"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert body["data"]["time_range"] == "7d"
        assert len(body["data"]["points"]) == 1

    @patch("engine.api.portfolio.get_portfolio_history", new_callable=AsyncMock)
    async def test_response_envelope_meta(self, mock_history: AsyncMock, client: AsyncMock) -> None:
        mock_history.return_value = ([], None)

        response = await client.post(
            "/engine/portfolio/history",
            json={"coldkey_addresses": [VALID_COLDKEY], "time_range": "30d"},
        )
        body = response.json()
        meta = body["meta"]
        assert "last_updated" in meta
        assert "compute_ms" in meta

    async def test_invalid_time_range_rejected(self, client: AsyncMock) -> None:
        response = await client.post(
            "/engine/portfolio/history",
            json={"coldkey_addresses": [VALID_COLDKEY], "time_range": "1d"},
        )
        assert response.status_code == 422

    async def test_empty_addresses_rejected(self, client: AsyncMock) -> None:
        response = await client.post(
            "/engine/portfolio/history",
            json={"coldkey_addresses": [], "time_range": "7d"},
        )
        assert response.status_code == 422

    async def test_invalid_address_rejected(self, client: AsyncMock) -> None:
        response = await client.post(
            "/engine/portfolio/history",
            json={"coldkey_addresses": ["not-valid"], "time_range": "7d"},
        )
        assert response.status_code == 422

    async def test_missing_body_rejected(self, client: AsyncMock) -> None:
        response = await client.post("/engine/portfolio/history")
        assert response.status_code == 422

    @patch("engine.api.portfolio.get_portfolio_history", new_callable=AsyncMock)
    async def test_empty_points_returns_200(
        self, mock_history: AsyncMock, client: AsyncMock
    ) -> None:
        mock_history.return_value = ([], None)

        response = await client.post(
            "/engine/portfolio/history",
            json={"coldkey_addresses": [VALID_COLDKEY], "time_range": "7d"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["points"] == []
        assert body["data"]["data_start"] is None

    @patch("engine.api.portfolio.get_portfolio_history", new_callable=AsyncMock)
    async def test_sparse_data_includes_data_start(
        self, mock_history: AsyncMock, client: AsyncMock
    ) -> None:
        mock_history.return_value = (
            [{"time": "2026-03-12T00:00:00Z", "total_value_tao": 100.0}],
            "2026-03-12T00:00:00Z",
        )

        response = await client.post(
            "/engine/portfolio/history",
            json={"coldkey_addresses": [VALID_COLDKEY], "time_range": "7d"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["data_start"] == "2026-03-12T00:00:00Z"
