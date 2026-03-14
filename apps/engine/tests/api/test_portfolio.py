"""Tests for portfolio API endpoint."""

from unittest.mock import AsyncMock, patch

from engine.schemas.portfolio import (
    PortfolioResponseSchema,
    SubnetPositionSchema,
)

VALID_COLDKEY = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
VALID_COLDKEY_2 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
HOTKEY_1 = "5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy"


def _portfolio_response(
    positions: list[SubnetPositionSchema] | None = None,
    total_value: float = 150.0,
) -> PortfolioResponseSchema:
    positions = positions or []
    return PortfolioResponseSchema(
        total_value_tao=total_value,
        total_staked_tao=100.0,
        total_alpha_value_tao=50.0,
        positions=positions,
        subnets_exposed=len({p.netuid for p in positions}),
        coldkeys_resolved=1,
        last_updated="2026-03-14T14:30:00Z",
    )


class TestPortfolioAggregateEndpoint:
    @patch("engine.api.portfolio.aggregate_portfolio", new_callable=AsyncMock)
    async def test_valid_request(self, mock_agg: AsyncMock, client: AsyncMock) -> None:
        mock_agg.return_value = (_portfolio_response(), False)

        response = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": [VALID_COLDKEY]},
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert body["data"]["total_value_tao"] == 150.0
        assert body["data"]["coldkeys_resolved"] == 1

    @patch("engine.api.portfolio.aggregate_portfolio", new_callable=AsyncMock)
    async def test_response_envelope_meta(self, mock_agg: AsyncMock, client: AsyncMock) -> None:
        mock_agg.return_value = (_portfolio_response(), True)

        response = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": [VALID_COLDKEY]},
        )
        body = response.json()
        meta = body["meta"]
        assert "last_updated" in meta
        assert meta["cache_hit"] is True
        assert "compute_ms" in meta

    async def test_empty_addresses_rejected(self, client: AsyncMock) -> None:
        response = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": []},
        )
        assert response.status_code == 422

    async def test_invalid_address_rejected(self, client: AsyncMock) -> None:
        response = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": ["not-valid"]},
        )
        assert response.status_code == 422

    async def test_too_many_addresses_rejected(self, client: AsyncMock) -> None:
        addresses = [VALID_COLDKEY] * 21
        response = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": addresses},
        )
        assert response.status_code == 422

    @patch("engine.api.portfolio.aggregate_portfolio", new_callable=AsyncMock)
    async def test_empty_positions_returns_200(
        self, mock_agg: AsyncMock, client: AsyncMock
    ) -> None:
        """Empty positions should return 200, not 404 (AC #5)."""
        mock_agg.return_value = (_portfolio_response(positions=[], total_value=0.0), False)

        response = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": [VALID_COLDKEY]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["positions"] == []
        assert body["data"]["total_value_tao"] == 0.0

    @patch("engine.api.portfolio.aggregate_portfolio", new_callable=AsyncMock)
    async def test_multi_address_request(self, mock_agg: AsyncMock, client: AsyncMock) -> None:
        pos = SubnetPositionSchema(
            netuid=1, hotkey=HOTKEY_1, staked_tao=100.0, alpha_value_tao=50.0,
            emission_share=0.05, incentive=0.0, trust=0.9, dividends=0.1,
            is_active=True, is_miner=False,
        )
        resp = PortfolioResponseSchema(
            total_value_tao=150.0, total_staked_tao=100.0, total_alpha_value_tao=50.0,
            positions=[pos], subnets_exposed=1, coldkeys_resolved=2,
            last_updated="2026-03-14T14:30:00Z",
        )
        mock_agg.return_value = (resp, False)

        response = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": [VALID_COLDKEY, VALID_COLDKEY_2]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["coldkeys_resolved"] == 2

    async def test_missing_body_rejected(self, client: AsyncMock) -> None:
        response = await client.post("/engine/portfolio/aggregate")
        assert response.status_code == 422
