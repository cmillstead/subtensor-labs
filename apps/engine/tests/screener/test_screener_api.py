"""Tests for screener API endpoints."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from engine.schemas.screener import ScreenerResponseSchema, ScreenerSubnetSchema


def _mock_subnet(netuid: int = 1, name: str | None = "Text Prompting") -> ScreenerSubnetSchema:
    return ScreenerSubnetSchema(
        netuid=netuid,
        name=name,
        miner_count=100,
        validator_count=50,
        registration_cost=1.5,
        emission_share=0.05,
        alpha_price=0.12,
        alpha_market_cap=1200.0,
        fill_rate=0.78,
        owner_take_rate=0.18,
        tao_reserves=500.0,
        alpha_reserves=4000.0,
        subnet_age_days=120,
        sparkline_emission_7d=[0.04, 0.045, 0.05, 0.048, 0.05, 0.052, 0.05],
        sparkline_price_7d=[0.10, 0.11, 0.115, 0.12, 0.118, 0.12, 0.12],
    )


def _mock_response() -> ScreenerResponseSchema:
    subnets = [_mock_subnet(1, "Text Prompting"), _mock_subnet(3, "Data Scraping")]
    return ScreenerResponseSchema(subnets=subnets, subnet_count=2)


class TestScreenerQueryEndpoint:
    @pytest.mark.anyio
    async def test_returns_envelope_structure(self, client: AsyncClient) -> None:
        mock_result = _mock_response()
        with patch(
            "engine.api.screener.get_all_subnets",
            new_callable=AsyncMock,
            return_value=(mock_result, False),
        ):
            resp = await client.get("/engine/screener/query")

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "last_updated" in body["meta"]
        assert "cache_hit" in body["meta"]
        assert "compute_ms" in body["meta"]

    @pytest.mark.anyio
    async def test_data_contains_subnets(self, client: AsyncClient) -> None:
        mock_result = _mock_response()
        with patch(
            "engine.api.screener.get_all_subnets",
            new_callable=AsyncMock,
            return_value=(mock_result, True),
        ):
            resp = await client.get("/engine/screener/query")

        data = resp.json()["data"]
        assert data["subnet_count"] == 2
        assert len(data["subnets"]) == 2

    @pytest.mark.anyio
    async def test_subnet_data_shape(self, client: AsyncClient) -> None:
        mock_result = _mock_response()
        with patch(
            "engine.api.screener.get_all_subnets",
            new_callable=AsyncMock,
            return_value=(mock_result, False),
        ):
            resp = await client.get("/engine/screener/query")

        subnet = resp.json()["data"]["subnets"][0]
        assert subnet["netuid"] == 1
        assert subnet["name"] == "Text Prompting"
        assert subnet["miner_count"] == 100
        assert subnet["validator_count"] == 50
        assert isinstance(subnet["sparkline_emission_7d"], list)
        assert isinstance(subnet["sparkline_price_7d"], list)
        assert len(subnet["sparkline_emission_7d"]) == 7
        assert "subnet_age_days" in subnet

    @pytest.mark.anyio
    async def test_cache_hit_reported(self, client: AsyncClient) -> None:
        mock_result = _mock_response()
        with patch(
            "engine.api.screener.get_all_subnets",
            new_callable=AsyncMock,
            return_value=(mock_result, True),
        ):
            resp = await client.get("/engine/screener/query")

        assert resp.json()["meta"]["cache_hit"] is True

    @pytest.mark.anyio
    async def test_cache_miss_reported(self, client: AsyncClient) -> None:
        mock_result = _mock_response()
        with patch(
            "engine.api.screener.get_all_subnets",
            new_callable=AsyncMock,
            return_value=(mock_result, False),
        ):
            resp = await client.get("/engine/screener/query")

        assert resp.json()["meta"]["cache_hit"] is False


class TestScreenerSchemas:
    def test_subnet_schema_serialization(self) -> None:
        subnet = _mock_subnet()
        data = subnet.model_dump()
        assert data["netuid"] == 1
        assert data["sparkline_emission_7d"] == [0.04, 0.045, 0.05, 0.048, 0.05, 0.052, 0.05]

    def test_response_schema_serialization(self) -> None:
        response = _mock_response()
        json_str = response.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["subnet_count"] == 2
        assert len(parsed["subnets"]) == 2

    def test_subnet_with_null_name(self) -> None:
        subnet = _mock_subnet(netuid=99, name=None)
        assert subnet.name is None
        data = subnet.model_dump()
        assert data["name"] is None
