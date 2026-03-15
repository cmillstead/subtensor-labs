"""Tests for subnet detail query engine."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from engine.schemas.subnet import (
    SubnetDetailResponseSchema,
    SubnetDetailSchema,
    SubnetHistoryPointSchema,
    SubnetNeuronSchema,
)
from engine.subnets.engine import VALID_TIME_RANGES, _cache_key, get_subnet_detail


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
            SubnetHistoryPointSchema(
                time="2026-03-11T00:00:00+00:00",
                emission_share=0.05,
                alpha_price=0.12,
                miner_count=100,
            ),
        ],
        miners=[
            SubnetNeuronSchema(
                uid=1,
                hotkey="5FHneW46xGXg5",
                coldkey="5GrwvaEF5zXb",
                stake=100.0,
                incentive=0.95,
                trust=0.88,
                dividends=0.0,
                is_active=True,
            ),
        ],
        validators=[
            SubnetNeuronSchema(
                uid=2,
                hotkey="5DAAnrj7VHTzD",
                coldkey="5FLSigC9HGR",
                stake=500.0,
                incentive=0.80,
                trust=0.92,
                dividends=0.15,
                is_active=True,
            ),
        ],
    )


class TestGetSubnetDetail:
    @pytest.mark.anyio
    async def test_returns_cached_data_on_cache_hit(self) -> None:
        mock_response = _mock_detail_response()
        cached_json = mock_response.model_dump_json()

        with patch(
            "engine.subnets.engine.cache_get",
            new_callable=AsyncMock,
            return_value=cached_json,
        ):
            result, cache_hit = await get_subnet_detail(1, "30d")

        assert cache_hit is True
        assert result.detail.netuid == 1
        assert result.detail.name == "Text Prompting"

    @pytest.mark.anyio
    async def test_queries_db_on_cache_miss(self) -> None:
        mock_response = _mock_detail_response()

        with (
            patch(
                "engine.subnets.engine.cache_get",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "engine.subnets.engine._query_subnet_detail",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
            patch(
                "engine.subnets.engine.cache_set",
                new_callable=AsyncMock,
            ) as mock_cache_set,
        ):
            result, cache_hit = await get_subnet_detail(1, "30d")

        assert cache_hit is False
        assert result.detail.netuid == 1
        mock_cache_set.assert_called_once()

    @pytest.mark.anyio
    async def test_invalid_time_range_defaults_to_30d(self) -> None:
        mock_response = _mock_detail_response()
        cached_json = mock_response.model_dump_json()

        with patch(
            "engine.subnets.engine.cache_get",
            new_callable=AsyncMock,
            return_value=cached_json,
        ) as mock_get:
            await get_subnet_detail(1, "invalid")

        # Should have used 30d default in cache key
        mock_get.assert_called_once_with(_cache_key(1, "30d"))

    @pytest.mark.anyio
    async def test_history_sorted_chronologically(self) -> None:
        mock_response = _mock_detail_response()
        cached_json = mock_response.model_dump_json()

        with patch(
            "engine.subnets.engine.cache_get",
            new_callable=AsyncMock,
            return_value=cached_json,
        ):
            result, _ = await get_subnet_detail(1, "30d")

        times = [h.time for h in result.history]
        assert times == sorted(times)

    @pytest.mark.anyio
    async def test_miners_and_validators_separated(self) -> None:
        mock_response = _mock_detail_response()
        cached_json = mock_response.model_dump_json()

        with patch(
            "engine.subnets.engine.cache_get",
            new_callable=AsyncMock,
            return_value=cached_json,
        ):
            result, _ = await get_subnet_detail(1, "30d")

        # Miners have dividends == 0
        for miner in result.miners:
            assert miner.dividends == 0.0

        # Validators have dividends > 0
        for validator in result.validators:
            assert validator.dividends > 0


class TestValidTimeRanges:
    def test_valid_ranges_defined(self) -> None:
        assert "7d" in VALID_TIME_RANGES
        assert "30d" in VALID_TIME_RANGES
        assert "90d" in VALID_TIME_RANGES
        assert VALID_TIME_RANGES["7d"] == 7
        assert VALID_TIME_RANGES["30d"] == 30
        assert VALID_TIME_RANGES["90d"] == 90


class TestCacheKey:
    def test_cache_key_format(self) -> None:
        assert _cache_key(1, "30d") == "subnet:1:30d"
        assert _cache_key(42, "7d") == "subnet:42:7d"


class TestSubnetSchemas:
    def test_detail_schema_serialization(self) -> None:
        detail = _mock_detail_response().detail
        data = detail.model_dump()
        assert data["netuid"] == 1
        assert data["subnet_age_days"] == 120
        assert data["description"] is None

    def test_response_schema_json_roundtrip(self) -> None:
        response = _mock_detail_response()
        json_str = response.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["detail"]["netuid"] == 1
        assert len(parsed["history"]) == 2
        assert len(parsed["miners"]) == 1
        assert len(parsed["validators"]) == 1

    def test_neuron_schema_fields(self) -> None:
        neuron = SubnetNeuronSchema(
            uid=5,
            hotkey="5abc",
            coldkey="5def",
            stake=200.0,
            incentive=0.5,
            trust=0.8,
            dividends=0.1,
            is_active=False,
        )
        data = neuron.model_dump()
        assert data["uid"] == 5
        assert data["is_active"] is False
