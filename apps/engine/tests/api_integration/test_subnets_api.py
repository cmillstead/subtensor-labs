"""Tests for subnet detail API endpoint — real database, real Redis, no mocks."""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def seed_subnet_detail(db_engine):
    """Seed subnet_snapshots and metagraph_entries for subnet 1."""
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        # Subnet snapshots (current + history)
        await session.execute(
            text("""
                INSERT INTO subnet_snapshots (time, netuid, miner_count, validator_count,
                    emission_share, registration_cost, alpha_price, alpha_market_cap,
                    tao_reserves, alpha_reserves, fill_rate, owner_take_rate)
                VALUES
                    (NOW(), 1, 100, 50, 0.05, 1.5, 0.12, 1200.0, 500.0, 4000.0, 0.78, 0.18),
                    (NOW() - INTERVAL '1 day', 1, 98, 49,
                     0.048, 1.5, 0.11, 1100, 490, 3900, 0.77, 0.18),
                    (NOW() - INTERVAL '2 days', 1, 96, 48,
                     0.046, 1.4, 0.10, 1000, 480, 3800, 0.76, 0.18)
            """)
        )
        # Metagraph entries (1 miner + 1 validator)
        await session.execute(
            text("""
                INSERT INTO metagraph_entries (time, netuid, uid, hotkey, coldkey,
                    stake, incentive, trust, dividends, is_active)
                VALUES
                    (NOW(), 1, 1, '5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJ',
                     '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHG', 100.0, 0.95, 0.88, 0.0, true),
                    (NOW(), 1, 2, '5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum',
                     '5FLSigC9HGRKVhB9FiEo4Y3koPsNmBmLJbpXg2mp1h', 500.0, 0.80, 0.92, 0.15, true)
            """)
        )
        await session.commit()


class TestSubnetDetailEndpoint:
    async def test_returns_envelope_structure(
        self,
        client: AsyncClient,
        seed_subnet_detail,
    ) -> None:
        resp = await client.get("/engine/subnets/1")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "last_updated" in body["meta"]
        assert "cache_hit" in body["meta"]
        assert "compute_ms" in body["meta"]

    async def test_data_contains_detail(
        self,
        client: AsyncClient,
        seed_subnet_detail,
    ) -> None:
        resp = await client.get("/engine/subnets/1")
        data = resp.json()["data"]
        assert data["detail"]["netuid"] == 1
        assert data["detail"]["name"] == "Text Prompting"
        assert data["detail"]["miner_count"] == 100
        assert "history" in data
        assert "miners" in data
        assert "validators" in data

    async def test_history_has_data(
        self,
        client: AsyncClient,
        seed_subnet_detail,
    ) -> None:
        resp = await client.get("/engine/subnets/1")
        history = resp.json()["data"]["history"]
        assert len(history) >= 1
        assert "emission_share" in history[0]
        assert "alpha_price" in history[0]

    async def test_miners_and_validators_separated(
        self,
        client: AsyncClient,
        seed_subnet_detail,
    ) -> None:
        resp = await client.get("/engine/subnets/1")
        data = resp.json()["data"]
        assert len(data["miners"]) == 1
        assert len(data["validators"]) == 1
        # Miners have dividends == 0
        assert data["miners"][0]["dividends"] == 0.0
        # Validators have dividends > 0
        assert data["validators"][0]["dividends"] > 0

    async def test_returns_404_for_unknown_subnet(self, client: AsyncClient) -> None:
        resp = await client.get("/engine/subnets/999")
        assert resp.status_code == 404

    async def test_time_range_7d_accepted(
        self,
        client: AsyncClient,
        seed_subnet_detail,
    ) -> None:
        resp = await client.get("/engine/subnets/1?time_range=7d")
        assert resp.status_code == 200

    async def test_invalid_time_range_returns_422(self, client: AsyncClient) -> None:
        resp = await client.get("/engine/subnets/1?time_range=invalid")
        assert resp.status_code == 422
        assert resp.json()["error"]["type"] == "validation_error"

    async def test_first_call_is_cache_miss(
        self,
        client: AsyncClient,
        seed_subnet_detail,
    ) -> None:
        resp = await client.get("/engine/subnets/1")
        assert resp.json()["meta"]["cache_hit"] is False

    async def test_second_call_is_cache_hit(
        self,
        client: AsyncClient,
        seed_subnet_detail,
    ) -> None:
        await client.get("/engine/subnets/1")
        resp = await client.get("/engine/subnets/1")
        assert resp.json()["meta"]["cache_hit"] is True
