"""Integration tests for prediction API endpoints — real database, no mocks."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def seed_emission_data(db_engine):
    """Seed emission_records, metagraph_entries, and subnet_snapshots with
    30 days of data for netuids 1 and 3, plus a user with stake.
    """
    base_time = datetime.now(UTC) - timedelta(days=30)

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        # Emission records — 30 days of increasing emission for SN1
        for i in range(30):
            t = base_time + timedelta(days=i)
            await session.execute(
                text(
                    "INSERT INTO emission_records"
                    " (time, netuid, emission_tao,"
                    " emission_share_pct, net_tao_inflow,"
                    " cumulative_stake)"
                    " VALUES (:t, :netuid, :emission_tao,"
                    " :emission_share_pct, :net_tao_inflow,"
                    " :cumulative_stake)"
                ),
                {
                    "t": t,
                    "netuid": 1,
                    "emission_tao": 10.0 + i * 0.1,
                    "emission_share_pct": 5.0 + i * 0.05,
                    "net_tao_inflow": 50.0 + i,
                    "cumulative_stake": 1000.0 + i * 10,
                },
            )

        # Subnet snapshots — latest for SN1 (owner_take_rate)
        await session.execute(
            text("""
                INSERT INTO subnet_snapshots
                    (time, netuid, miner_count, validator_count, emission_share,
                     registration_cost, alpha_price, alpha_market_cap,
                     tao_reserves, alpha_reserves, fill_rate, owner_take_rate)
                VALUES (NOW(), 1, 100, 50, 0.065, 1.5, 0.12, 1200.0, 500.0, 4000.0, 0.78, 0.10)
            """)
        )

        # Metagraph entries — user's stake on SN1
        await session.execute(
            text(
                "INSERT INTO metagraph_entries"
                " (time, netuid, uid, hotkey, coldkey,"
                " stake, incentive, trust, dividends,"
                " is_active)"
                " VALUES"
                " (NOW(), 1, 0,"
                " '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY',"
                " '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY',"
                " 200.0, 0.5, 0.8, 0.3, true)"
            )
        )

        await session.commit()

    return {
        "address": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
        "netuid": 1,
        "stake": 200.0,
    }


class TestYieldProjectionEndpoint:
    """Integration tests for POST /engine/predictions/yield."""

    async def test_returns_200_with_projection_data(
        self, client: AsyncClient, seed_emission_data: dict
    ) -> None:
        """Should compute real projections from seeded emission data."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": [seed_emission_data["address"]],
                "horizons": [30],
            },
        )
        assert response.status_code == 200
        body = response.json()

        assert "data" in body
        assert "meta" in body
        assert body["meta"]["compute_ms"] >= 0

        data = body["data"]
        assert data["subnets_analyzed"] == 1
        assert data["total_staked_tao"] == pytest.approx(200.0)
        assert len(data["projections"]) == 1
        assert data["projections"][0]["horizon_days"] == 30
        assert data["projections"][0]["total_projected_yield_tao"] > 0

    async def test_returns_chart_data(self, client: AsyncClient, seed_emission_data: dict) -> None:
        """Should return daily chart data points up to the max horizon."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": [seed_emission_data["address"]],
                "horizons": [30, 60],
            },
        )
        body = response.json()
        chart_data = body["data"]["chart_data"]

        assert len(chart_data) == 60  # max horizon
        assert chart_data[0]["day"] == 1
        assert chart_data[-1]["day"] == 60
        # Confidence bands should exist
        assert "confidence_68_lower" in chart_data[0]
        assert "confidence_95_upper" in chart_data[0]

    async def test_returns_caveat(self, client: AsyncClient, seed_emission_data: dict) -> None:
        """Response always includes the caveat text."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": [seed_emission_data["address"]],
                "horizons": [30],
            },
        )
        body = response.json()
        assert "Not financial advice" in body["data"]["caveat"]

    async def test_envelope_format(self, client: AsyncClient, seed_emission_data: dict) -> None:
        """Response follows {data, meta} envelope format."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": [seed_emission_data["address"]],
                "horizons": [30],
            },
        )
        body = response.json()

        data = body["data"]
        assert "projections" in data
        assert "chart_data" in data
        assert "last_computed" in data
        assert "total_staked_tao" in data
        assert "subnets_analyzed" in data
        assert "subnets_skipped" in data

        meta = body["meta"]
        assert "last_updated" in meta
        assert "compute_ms" in meta
        assert "cache_hit" in meta

    async def test_validates_invalid_addresses(self, client: AsyncClient) -> None:
        """Should reject invalid SS58 addresses."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": ["not-a-valid-address"],
                "horizons": [30],
            },
        )
        assert response.status_code == 422

    async def test_validates_empty_addresses(self, client: AsyncClient) -> None:
        """Should reject empty address list."""
        response = await client.post(
            "/engine/predictions/yield",
            json={"coldkey_addresses": [], "horizons": [30]},
        )
        assert response.status_code == 422

    async def test_validates_invalid_horizons(self, client: AsyncClient) -> None:
        """Should reject invalid horizon values."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": ["5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"],
                "horizons": [15],
            },
        )
        assert response.status_code == 422

    async def test_empty_portfolio_returns_zero(self, client: AsyncClient) -> None:
        """Address with no stake returns zero projections."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": ["5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"],
                "horizons": [30],
            },
        )
        body = response.json()
        assert body["data"]["total_staked_tao"] == 0.0
        assert body["data"]["subnets_analyzed"] == 0

    async def test_default_horizons(self, client: AsyncClient, seed_emission_data: dict) -> None:
        """Should use default horizons [30, 60, 90] if not specified."""
        response = await client.post(
            "/engine/predictions/yield",
            json={"coldkey_addresses": [seed_emission_data["address"]]},
        )
        body = response.json()
        horizons = [p["horizon_days"] for p in body["data"]["projections"]]
        assert horizons == [30, 60, 90]

    async def test_subnet_projection_details(
        self, client: AsyncClient, seed_emission_data: dict
    ) -> None:
        """Subnet projections include all expected fields."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": [seed_emission_data["address"]],
                "horizons": [30],
            },
        )
        body = response.json()
        subnet_proj = body["data"]["projections"][0]["subnet_projections"][0]

        assert subnet_proj["netuid"] == 1
        assert subnet_proj["current_stake_tao"] == pytest.approx(200.0)
        assert subnet_proj["projected_yield_tao"] > 0
        assert subnet_proj["r_squared"] > 0
        assert subnet_proj["confidence_68_lower"] < subnet_proj["confidence_68_upper"]
        assert subnet_proj["confidence_95_lower"] < subnet_proj["confidence_95_upper"]
        # 30 days of data → volatility warning (< 60 days)
        assert subnet_proj["has_volatility_warning"] is True

    async def test_cache_hit_on_second_request(
        self, client: AsyncClient, seed_emission_data: dict
    ) -> None:
        """Second identical request should be a cache hit."""
        payload = {
            "coldkey_addresses": [seed_emission_data["address"]],
            "horizons": [30],
        }

        # First request — cache miss
        response1 = await client.post("/engine/predictions/yield", json=payload)
        assert response1.json()["meta"]["cache_hit"] is False

        # Second request — should be cache hit
        response2 = await client.post("/engine/predictions/yield", json=payload)
        assert response2.json()["meta"]["cache_hit"] is True
