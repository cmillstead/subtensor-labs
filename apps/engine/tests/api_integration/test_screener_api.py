"""Tests for screener API endpoint — real database, real Redis, no mocks."""

from httpx import AsyncClient


class TestScreenerQueryEndpoint:
    async def test_returns_envelope_structure(
        self,
        client: AsyncClient,
        seed_subnets,
    ) -> None:
        resp = await client.get("/engine/screener/query")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "last_updated" in body["meta"]
        assert "cache_hit" in body["meta"]
        assert "compute_ms" in body["meta"]

    async def test_data_contains_subnets(
        self,
        client: AsyncClient,
        seed_subnets,
    ) -> None:
        resp = await client.get("/engine/screener/query")
        data = resp.json()["data"]
        assert data["subnet_count"] == 2
        assert len(data["subnets"]) == 2

    async def test_subnet_data_shape(
        self,
        client: AsyncClient,
        seed_subnets,
    ) -> None:
        resp = await client.get("/engine/screener/query")
        subnets = resp.json()["data"]["subnets"]
        # Find netuid 1
        subnet1 = next(s for s in subnets if s["netuid"] == 1)
        assert subnet1["name"] == "Text Prompting"
        assert subnet1["miner_count"] == 100
        assert subnet1["validator_count"] == 50
        assert isinstance(subnet1["sparkline_emission_7d"], list)
        assert isinstance(subnet1["sparkline_price_7d"], list)
        assert "subnet_age_days" in subnet1

    async def test_computed_metrics_present(
        self,
        client: AsyncClient,
        seed_subnets,
    ) -> None:
        """New computed fields are present in the response."""
        resp = await client.get("/engine/screener/query")
        subnets = resp.json()["data"]["subnets"]
        subnet1 = next(s for s in subnets if s["netuid"] == 1)

        # Price change fields — may be None or float depending on history
        assert "alpha_price_change_24h" in subnet1
        assert "alpha_price_change_7d" in subnet1
        assert "alpha_price_change_30d" in subnet1
        # Net TAO inflow — None when no emission_records seeded
        assert "net_tao_inflow" in subnet1
        # Immunity active — boolean
        assert "immunity_active" in subnet1
        assert isinstance(subnet1["immunity_active"], bool)

    async def test_first_call_is_cache_miss(
        self,
        client: AsyncClient,
        seed_subnets,
    ) -> None:
        resp = await client.get("/engine/screener/query")
        assert resp.json()["meta"]["cache_hit"] is False

    async def test_second_call_is_cache_hit(
        self,
        client: AsyncClient,
        seed_subnets,
    ) -> None:
        # First call populates cache
        await client.get("/engine/screener/query")
        # Second call should hit cache
        resp = await client.get("/engine/screener/query")
        assert resp.json()["meta"]["cache_hit"] is True

    async def test_empty_db_returns_zero_subnets(self, client: AsyncClient) -> None:
        """No seed data — should return empty list, not error."""
        resp = await client.get("/engine/screener/query")
        assert resp.status_code == 200
        assert resp.json()["data"]["subnet_count"] == 0
        assert resp.json()["data"]["subnets"] == []
