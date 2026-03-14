"""Tests for alpha token price sync pipeline."""

import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.ingestion.price_tracker import (
    _compute_market_cap,
    _compute_price,
    _extract_reserves,
    _serialize_price_cache,
    run_price_sync_cycle,
    sync_single_subnet_price,
)


def _make_hyperparams(**kwargs: float) -> SimpleNamespace:
    """Create a hyperparams object with the given attributes.

    Uses SimpleNamespace instead of MagicMock so that only explicitly
    provided attributes exist — hasattr() behaves like the real SDK object.
    """
    return SimpleNamespace(**kwargs)


class TestExtractReserves:
    def test_extracts_tao_in_alpha_out(self) -> None:
        hp = _make_hyperparams(tao_in=1000.0, alpha_out=500.0)
        tao, alpha = _extract_reserves(hp)
        assert tao == 1000.0
        assert alpha == 500.0

    def test_extracts_tao_reserve_alpha_reserve(self) -> None:
        hp = _make_hyperparams(tao_reserve=2000.0, alpha_reserve=800.0)
        result = _extract_reserves(hp)
        assert result == (2000.0, 800.0)

    def test_extracts_pool_tao_pool_alpha(self) -> None:
        hp = _make_hyperparams(pool_tao=3000.0, pool_alpha=1500.0)
        result = _extract_reserves(hp)
        assert result == (3000.0, 1500.0)

    def test_raises_on_zero_alpha_reserve(self) -> None:
        hp = _make_hyperparams(tao_in=1000.0, alpha_out=0.0)
        with pytest.raises(ValueError, match="alpha_reserve is zero"):
            _extract_reserves(hp)

    def test_raises_on_missing_alpha_reserve(self) -> None:
        hp = _make_hyperparams(tao_in=1000.0)
        # no alpha attribute → defaults to 0.0
        with pytest.raises(ValueError, match="alpha_reserve is zero"):
            _extract_reserves(hp)

    def test_raises_on_missing_tao_reserve(self) -> None:
        hp = _make_hyperparams(alpha_out=500.0)
        # no tao attribute → tao_reserve stays 0.0, should raise
        with pytest.raises(ValueError, match="tao_reserve is zero"):
            _extract_reserves(hp)


class TestComputePrice:
    def test_basic_price_computation(self) -> None:
        assert _compute_price(1000.0, 500.0) == 2.0

    def test_fractional_price(self) -> None:
        assert _compute_price(100.0, 1000.0) == 0.1


class TestComputeMarketCap:
    def test_market_cap_equals_tao_reserve(self) -> None:
        # price * alpha_reserve = (tao/alpha) * alpha = tao
        price = _compute_price(1000.0, 500.0)
        cap = _compute_market_cap(price, 500.0)
        assert cap == 1000.0


class TestSerializePriceCache:
    def test_serializes_to_valid_json(self) -> None:
        now = datetime.now(UTC)
        result = _serialize_price_cache(
            netuid=1,
            price_tao=2.0,
            tao_reserve=1000.0,
            alpha_reserve=500.0,
            alpha_market_cap=1000.0,
            now=now,
        )
        data = json.loads(result)
        assert data["netuid"] == 1
        assert data["price_tao"] == 2.0
        assert data["tao_reserve"] == 1000.0
        assert data["alpha_reserve"] == 500.0
        assert data["alpha_market_cap"] == 1000.0
        assert data["synced_at"] == now.isoformat()


class TestSyncSingleSubnetPrice:
    @pytest.mark.asyncio
    async def test_writes_alpha_price_and_cache(self) -> None:
        hp = _make_hyperparams(tao_in=1000.0, alpha_out=500.0)
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        with (
            patch(
                "engine.ingestion.price_tracker.get_subnet_hyperparams",
                new_callable=AsyncMock,
                return_value=hp,
            ),
            patch(
                "engine.ingestion.price_tracker.cache_set", new_callable=AsyncMock
            ) as mock_cache_set,
        ):
            await sync_single_subnet_price(1, mock_session)

        # One execute call for AlphaPrice insert
        assert mock_session.execute.call_count == 1
        mock_session.commit.assert_called_once()
        # Two cache_set calls: price data + per-subnet sync timestamp
        assert mock_cache_set.call_count == 2
        cache_keys = [call.args[0] for call in mock_cache_set.call_args_list]
        assert "price:1" in cache_keys
        assert "price_sync_ts:1" in cache_keys

        # Verify price cache content
        for call in mock_cache_set.call_args_list:
            if call.args[0] == "price:1":
                cached = json.loads(call.args[1])
                assert cached["price_tao"] == 2.0
                assert cached["tao_reserve"] == 1000.0
                assert cached["alpha_reserve"] == 500.0

    @pytest.mark.asyncio
    async def test_handles_zero_alpha_reserve(self) -> None:
        """Division by zero (alpha_reserve == 0) raises ValueError, caught by cycle."""
        hp = _make_hyperparams(tao_in=1000.0, alpha_out=0.0)
        mock_session = AsyncMock()

        with (
            patch(
                "engine.ingestion.price_tracker.get_subnet_hyperparams",
                new_callable=AsyncMock,
                return_value=hp,
            ),
            pytest.raises(ValueError, match="alpha_reserve is zero"),
        ):
            await sync_single_subnet_price(1, mock_session)

    @pytest.mark.asyncio
    async def test_timeout_on_slow_query(self) -> None:
        async def _slow_query(netuid: int) -> None:
            await asyncio.sleep(60)

        mock_session = AsyncMock()

        with (
            patch(
                "engine.ingestion.price_tracker.get_subnet_hyperparams",
                side_effect=_slow_query,
            ),
            pytest.raises(asyncio.TimeoutError),
        ):
            await sync_single_subnet_price(1, mock_session)


class TestRunPriceSyncCycle:
    @pytest.mark.asyncio
    async def test_syncs_all_subnets(self) -> None:
        hp1 = _make_hyperparams(tao_in=1000.0, alpha_out=500.0)
        hp2 = _make_hyperparams(tao_in=2000.0, alpha_out=800.0)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        call_count = 0

        async def _mock_get_hyperparams(netuid: int) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return hp1 if netuid == 1 else hp2

        with (
            patch(
                "engine.ingestion.price_tracker.get_active_subnet_netuids",
                new_callable=AsyncMock,
                return_value=[1, 3],
            ),
            patch(
                "engine.ingestion.price_tracker.get_subnet_hyperparams",
                side_effect=_mock_get_hyperparams,
            ),
            patch("engine.ingestion.price_tracker.cache_set", new_callable=AsyncMock),
            patch("engine.ingestion.price_tracker.get_session_factory", return_value=mock_factory),
        ):
            await run_price_sync_cycle()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_error_isolation_one_subnet_fails(self) -> None:
        """One subnet failure doesn't prevent others from syncing."""
        hp = _make_hyperparams(tao_in=2000.0, alpha_out=800.0)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        async def _mock_hyperparams(netuid: int) -> MagicMock:
            if netuid == 1:
                raise ConnectionError("RPC timeout")
            return hp

        with (
            patch(
                "engine.ingestion.price_tracker.get_active_subnet_netuids",
                new_callable=AsyncMock,
                return_value=[1, 3],
            ),
            patch(
                "engine.ingestion.price_tracker.get_subnet_hyperparams",
                side_effect=_mock_hyperparams,
            ),
            patch("engine.ingestion.price_tracker.cache_set", new_callable=AsyncMock),
            patch("engine.ingestion.price_tracker.get_session_factory", return_value=mock_factory),
        ):
            # Should not raise — error is isolated
            await run_price_sync_cycle()

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self) -> None:
        """Verify concurrency is bounded by settings.price_sync_workers."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        hp = _make_hyperparams(tao_in=1000.0, alpha_out=500.0)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        async def _tracked_hyperparams(netuid: int) -> MagicMock:
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.01)
            async with lock:
                current_concurrent -= 1
            return hp

        netuids = list(range(12))

        with (
            patch(
                "engine.ingestion.price_tracker.get_active_subnet_netuids",
                new_callable=AsyncMock,
                return_value=netuids,
            ),
            patch(
                "engine.ingestion.price_tracker.get_subnet_hyperparams",
                side_effect=_tracked_hyperparams,
            ),
            patch("engine.ingestion.price_tracker.cache_set", new_callable=AsyncMock),
            patch("engine.ingestion.price_tracker.get_session_factory", return_value=mock_factory),
            patch("engine.ingestion.price_tracker.settings") as mock_settings,
        ):
            mock_settings.price_sync_workers = 4
            mock_settings.cache_ttl_price = 180
            mock_settings.price_sync_timeout_seconds = 30
            await run_price_sync_cycle()

        assert max_concurrent <= 4

    @pytest.mark.asyncio
    async def test_handles_subnet_discovery_failure(self) -> None:
        """If subnet discovery fails, cycle logs error and returns."""
        with patch(
            "engine.ingestion.price_tracker.get_active_subnet_netuids",
            new_callable=AsyncMock,
            side_effect=ConnectionError("chain down"),
        ):
            # Should not raise
            await run_price_sync_cycle()
