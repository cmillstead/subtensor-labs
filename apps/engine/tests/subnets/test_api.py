"""Tests for subnet detail API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from engine.schemas.subnet import (
    SubnetDetailResponseSchema,
    SubnetDetailSchema,
    SubnetHistoryPointSchema,
)


def _mock_detail_response() -> SubnetDetailResponseSchema:
    return SubnetDetailResponseSchema(
        detail=SubnetDetailSchema(
            netuid=1,
            name="Text Prompting",
            miner_count=100,
            validator_count=50,
            registration_cost=1.5,
            emission_share=0.05,
            alpha_price=0.12,
            alpha_market_cap=1200.0,
            tao_reserves=500.0,
            alpha_reserves=4000.0,
            fill_rate=0.78,
            owner_take_rate=0.18,
            subnet_age_days=120,
            description=None,
        ),
        history=[
            SubnetHistoryPointSchema(
                time="2026-03-10T00:00:00+00:00",
                emission_share=0.048,
                alpha_price=0.11,
                miner_count=98,
            ),
        ],
        miners=[],
        validators=[],
    )


class TestSubnetDetailEndpoint:
    @pytest.mark.anyio
    async def test_returns_envelope_structure(self, client: AsyncClient) -> None:
        mock_result = _mock_detail_response()
        with patch(
            "engine.api.subnets.get_subnet_detail",
            new_callable=AsyncMock,
            return_value=(mock_result, False),
        ):
            resp = await client.get("/engine/subnets/1")

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        assert "last_updated" in body["meta"]
        assert "cache_hit" in body["meta"]
        assert "compute_ms" in body["meta"]

    @pytest.mark.anyio
    async def test_data_contains_detail(self, client: AsyncClient) -> None:
        mock_result = _mock_detail_response()
        with patch(
            "engine.api.subnets.get_subnet_detail",
            new_callable=AsyncMock,
            return_value=(mock_result, True),
        ):
            resp = await client.get("/engine/subnets/1")

        data = resp.json()["data"]
        assert data["detail"]["netuid"] == 1
        assert data["detail"]["name"] == "Text Prompting"
        assert data["detail"]["miner_count"] == 100
        assert "history" in data
        assert "miners" in data
        assert "validators" in data

    @pytest.mark.anyio
    async def test_returns_404_for_unknown_subnet(self, client: AsyncClient) -> None:
        with patch(
            "engine.api.subnets.get_subnet_detail",
            new_callable=AsyncMock,
            side_effect=HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "type": "subnet_not_found",
                        "message": "No data found for subnet 999",
                        "code": 404,
                    }
                },
            ),
        ):
            resp = await client.get("/engine/subnets/999")

        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_time_range_defaults_to_30d(self, client: AsyncClient) -> None:
        mock_result = _mock_detail_response()
        with patch(
            "engine.api.subnets.get_subnet_detail",
            new_callable=AsyncMock,
            return_value=(mock_result, False),
        ) as mock_fn:
            resp = await client.get("/engine/subnets/1")

        assert resp.status_code == 200
        mock_fn.assert_called_once_with(1, "30d")

    @pytest.mark.anyio
    async def test_time_range_7d_accepted(self, client: AsyncClient) -> None:
        mock_result = _mock_detail_response()
        with patch(
            "engine.api.subnets.get_subnet_detail",
            new_callable=AsyncMock,
            return_value=(mock_result, False),
        ) as mock_fn:
            resp = await client.get("/engine/subnets/1?time_range=7d")

        assert resp.status_code == 200
        mock_fn.assert_called_once_with(1, "7d")

    @pytest.mark.anyio
    async def test_invalid_time_range_returns_422(self, client: AsyncClient) -> None:
        resp = await client.get("/engine/subnets/1?time_range=invalid")

        assert resp.status_code == 422
        body = resp.json()
        assert "error" in body
        assert body["error"]["type"] == "validation_error"

    @pytest.mark.anyio
    async def test_cache_hit_reported(self, client: AsyncClient) -> None:
        mock_result = _mock_detail_response()
        with patch(
            "engine.api.subnets.get_subnet_detail",
            new_callable=AsyncMock,
            return_value=(mock_result, True),
        ):
            resp = await client.get("/engine/subnets/1")

        assert resp.json()["meta"]["cache_hit"] is True

    @pytest.mark.anyio
    async def test_cache_miss_reported(self, client: AsyncClient) -> None:
        mock_result = _mock_detail_response()
        with patch(
            "engine.api.subnets.get_subnet_detail",
            new_callable=AsyncMock,
            return_value=(mock_result, False),
        ):
            resp = await client.get("/engine/subnets/1")

        assert resp.json()["meta"]["cache_hit"] is False
