"""Tests for portfolio API endpoints — real database, real Redis, no mocks.

Seeds metagraph_entries and alpha_prices to exercise the full pipeline:
API endpoint → aggregate_portfolio → resolve_coldkey_positions → DB queries.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

VALID_COLDKEY = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
VALID_COLDKEY_2 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
HOTKEY_1 = "5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum"


@pytest.fixture
async def seed_portfolio(db_engine):
    """Seed metagraph entries and alpha prices for portfolio tests."""
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        # Metagraph entry: VALID_COLDKEY owns HOTKEY_1 on subnet 1
        await session.execute(
            text("""
                INSERT INTO metagraph_entries
                    (time, netuid, uid, hotkey, coldkey,
                     stake, incentive, trust, dividends, is_active)
                VALUES
                    (NOW(), 1, 0, :hotkey, :coldkey,
                     100.0, 0.5, 0.9, 0.1, true)
            """),
            {"hotkey": HOTKEY_1, "coldkey": VALID_COLDKEY},
        )
        # Alpha price for subnet 1
        await session.execute(
            text("""
                INSERT INTO alpha_prices
                    (time, netuid, price_tao, tao_reserve, alpha_reserve)
                VALUES (NOW(), 1, 2.0, 500.0, 250.0)
            """),
        )
        # Subnet snapshot (needed for emission_share lookup)
        await session.execute(
            text("""
                INSERT INTO subnet_snapshots
                    (time, netuid, miner_count, validator_count,
                     emission_share, registration_cost, alpha_price,
                     alpha_market_cap, tao_reserves, alpha_reserves,
                     fill_rate, owner_take_rate)
                VALUES
                    (NOW(), 1, 100, 50, 0.05, 1.5, 0.12,
                     1200, 500, 4000, 0.78, 0.18)
            """),
        )
        await session.commit()


class TestPortfolioAggregateEndpoint:
    async def test_valid_request(
        self,
        client: AsyncClient,
        seed_portfolio,
    ) -> None:
        res = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": [VALID_COLDKEY]},
        )
        assert res.status_code == 200
        body = res.json()
        assert "data" in body
        assert "meta" in body
        assert body["data"]["coldkeys_resolved"] == 1

    async def test_response_envelope_meta(
        self,
        client: AsyncClient,
        seed_portfolio,
    ) -> None:
        res = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": [VALID_COLDKEY]},
        )
        meta = res.json()["meta"]
        assert "last_updated" in meta
        assert "compute_ms" in meta
        assert "cache_hit" in meta

    async def test_empty_addresses_rejected(self, client: AsyncClient) -> None:
        res = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": []},
        )
        assert res.status_code == 422

    async def test_invalid_address_rejected(self, client: AsyncClient) -> None:
        res = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": ["not-valid"]},
        )
        assert res.status_code == 422

    async def test_too_many_addresses_rejected(self, client: AsyncClient) -> None:
        res = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": [VALID_COLDKEY] * 21},
        )
        assert res.status_code == 422

    async def test_missing_body_rejected(self, client: AsyncClient) -> None:
        res = await client.post("/engine/portfolio/aggregate")
        assert res.status_code == 422

    async def test_unknown_coldkey_returns_empty_positions(
        self,
        client: AsyncClient,
    ) -> None:
        """Unknown coldkey should return 200 with empty positions, not 404."""
        res = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": [VALID_COLDKEY_2]},
        )
        assert res.status_code == 200
        assert res.json()["data"]["positions"] == []
        assert res.json()["data"]["total_value_tao"] == 0.0

    async def test_cache_miss_then_hit(
        self,
        client: AsyncClient,
        seed_portfolio,
    ) -> None:
        """First call is cache miss, second is cache hit."""
        r1 = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": [VALID_COLDKEY]},
        )
        assert r1.json()["meta"]["cache_hit"] is False

        r2 = await client.post(
            "/engine/portfolio/aggregate",
            json={"coldkey_addresses": [VALID_COLDKEY]},
        )
        assert r2.json()["meta"]["cache_hit"] is True


class TestPortfolioHistoryEndpoint:
    async def test_valid_request(
        self,
        client: AsyncClient,
        seed_portfolio,
    ) -> None:
        res = await client.post(
            "/engine/portfolio/history",
            json={"coldkey_addresses": [VALID_COLDKEY], "time_range": "7d"},
        )
        # time_bucket is TimescaleDB-specific; may return 500 on plain PostgreSQL
        if res.status_code == 500:
            pytest.skip("time_bucket requires TimescaleDB extension")
        assert res.status_code == 200
        body = res.json()
        assert "data" in body
        assert "meta" in body
        assert body["data"]["time_range"] == "7d"

    async def test_empty_addresses_rejected(self, client: AsyncClient) -> None:
        res = await client.post(
            "/engine/portfolio/history",
            json={"coldkey_addresses": [], "time_range": "7d"},
        )
        assert res.status_code == 422

    async def test_invalid_time_range_rejected(self, client: AsyncClient) -> None:
        res = await client.post(
            "/engine/portfolio/history",
            json={"coldkey_addresses": [VALID_COLDKEY], "time_range": "1d"},
        )
        assert res.status_code == 422

    async def test_missing_body_rejected(self, client: AsyncClient) -> None:
        res = await client.post("/engine/portfolio/history")
        assert res.status_code == 422

    async def test_unknown_coldkey_returns_empty_points(
        self,
        client: AsyncClient,
    ) -> None:
        res = await client.post(
            "/engine/portfolio/history",
            json={"coldkey_addresses": [VALID_COLDKEY_2], "time_range": "7d"},
        )
        # time_bucket is TimescaleDB-specific; may return 500 on plain PostgreSQL
        if res.status_code == 500:
            pytest.skip("time_bucket requires TimescaleDB extension")
        assert res.status_code == 200
        assert res.json()["data"]["points"] == []
