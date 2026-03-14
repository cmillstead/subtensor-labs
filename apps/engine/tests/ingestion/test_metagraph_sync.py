"""Tests for metagraph sync pipeline."""

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from engine.ingestion.metagraph_sync import (
    _extract_metagraph_entries,
    _extract_subnet_snapshot,
    _serialize_metagraph_cache,
    run_metagraph_sync_cycle,
    sync_single_subnet,
)


def _make_mock_metagraph(netuid: int = 1, n: int = 3) -> MagicMock:
    """Create a mock metagraph with realistic numpy-like attributes."""
    mg = MagicMock()
    mg.n = np.int64(n)
    mg.block = np.int64(1000000)
    mg.uids = np.arange(n)
    mg.hotkeys = [f"5Hot{netuid}{i:045d}" for i in range(n)]
    mg.coldkeys = [f"5Col{netuid}{i:045d}" for i in range(n)]
    mg.stake = np.array([100.0, 200.0, 0.0][:n], dtype=np.float64)
    mg.incentive = np.array([0.5, 0.3, 0.2][:n], dtype=np.float64)
    mg.trust = np.array([0.9, 0.8, 0.7][:n], dtype=np.float64)
    mg.dividends = np.array([0.1, 0.05, 0.0][:n], dtype=np.float64)
    mg.active = np.array([True, True, False][:n])
    return mg


class TestExtractSubnetSnapshot:
    def test_extracts_miner_and_validator_counts(self) -> None:
        mg = _make_mock_metagraph()
        now = datetime.now(UTC)
        result = _extract_subnet_snapshot(1, mg, now)

        assert result["netuid"] == 1
        assert result["time"] == now
        assert result["miner_count"] == 2  # 2 active
        assert result["validator_count"] == 2  # 2 with stake > 0
        # Story 1.4 fields default to 0.0
        assert result["alpha_price"] == 0.0
        assert result["tao_reserves"] == 0.0


class TestExtractMetagraphEntries:
    def test_extracts_all_neurons(self) -> None:
        mg = _make_mock_metagraph(netuid=5, n=3)
        now = datetime.now(UTC)
        entries = _extract_metagraph_entries(5, mg, now)

        assert len(entries) == 3
        assert entries[0]["netuid"] == 5
        assert entries[0]["uid"] == 0
        assert entries[0]["hotkey"] == mg.hotkeys[0]
        assert entries[0]["coldkey"] == mg.coldkeys[0]
        assert entries[0]["stake"] == 100.0
        assert entries[0]["incentive"] == 0.5
        assert entries[0]["trust"] == 0.9
        assert entries[0]["dividends"] == 0.1
        assert entries[0]["is_active"] is True

    def test_last_neuron_is_inactive(self) -> None:
        mg = _make_mock_metagraph(n=3)
        now = datetime.now(UTC)
        entries = _extract_metagraph_entries(1, mg, now)

        assert entries[2]["is_active"] is False
        assert entries[2]["stake"] == 0.0


class TestSerializeMetagraphCache:
    def test_serializes_to_valid_json(self) -> None:
        mg = _make_mock_metagraph(netuid=1, n=2)
        now = datetime.now(UTC)
        result = _serialize_metagraph_cache(1, mg, now)

        data = json.loads(result)
        assert data["netuid"] == 1
        assert data["n"] == 2
        assert data["block"] == 1000000
        assert len(data["hotkeys"]) == 2
        assert len(data["stake"]) == 2
        assert data["synced_at"] == now.isoformat()


class TestSyncSingleSubnet:
    @pytest.mark.asyncio
    async def test_writes_snapshot_and_entries(self) -> None:
        mg = _make_mock_metagraph(netuid=1, n=3)
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        with (
            patch(
                "engine.ingestion.metagraph_sync.sync_subnet_metagraph",
                new_callable=AsyncMock,
                return_value=mg,
            ),
            patch(
                "engine.ingestion.metagraph_sync.cache_set", new_callable=AsyncMock
            ) as mock_cache_set,
        ):
            await sync_single_subnet(1, mock_session)

        # Three execute calls: SubnetSnapshot + MetagraphEntry bulk + per-subnet ts
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()
        # Two cache_set calls: metagraph data + per-subnet sync timestamp
        assert mock_cache_set.call_count == 2
        cache_keys = [call.args[0] for call in mock_cache_set.call_args_list]
        assert "metagraph:1" in cache_keys
        assert "metagraph_sync_ts:1" in cache_keys

        # Verify SubnetSnapshot data in first execute call
        first_call_args = mock_session.execute.call_args_list[0]
        snapshot_stmt = first_call_args[0][0]
        # The insert statement contains the values
        compiled = snapshot_stmt.compile()
        params = compiled.params
        assert params["netuid"] == 1
        assert params["miner_count"] == 2
        assert params["validator_count"] == 2

        # Verify MetagraphEntry bulk insert has 3 entries (second call)
        second_call_args = mock_session.execute.call_args_list[1]
        entries = second_call_args[0][1]  # list of dicts
        assert len(entries) == 3
        assert entries[0]["netuid"] == 1
        assert entries[0]["uid"] == 0
        assert entries[0]["stake"] == 100.0
        assert entries[2]["is_active"] is False

    @pytest.mark.asyncio
    async def test_timeout_on_slow_sync(self) -> None:
        async def _slow_sync(netuid: int) -> None:
            await asyncio.sleep(60)

        mock_session = AsyncMock()

        with (
            patch(
                "engine.ingestion.metagraph_sync.sync_subnet_metagraph",
                side_effect=_slow_sync,
            ),
            pytest.raises(asyncio.TimeoutError),
        ):
            await sync_single_subnet(1, mock_session)


class TestRunMetagraphSyncCycle:
    @pytest.mark.asyncio
    async def test_syncs_all_subnets(self) -> None:
        mg1 = _make_mock_metagraph(netuid=1, n=2)
        mg2 = _make_mock_metagraph(netuid=3, n=2)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        call_count = 0

        async def _mock_sync_metagraph(netuid: int) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return mg1 if netuid == 1 else mg2

        with (
            patch(
                "engine.ingestion.metagraph_sync.get_active_subnet_netuids",
                new_callable=AsyncMock,
                return_value=[1, 3],
            ),
            patch(
                "engine.ingestion.metagraph_sync.sync_subnet_metagraph",
                side_effect=_mock_sync_metagraph,
            ),
            patch("engine.ingestion.metagraph_sync.cache_set", new_callable=AsyncMock),
            patch("engine.ingestion.metagraph_sync.get_session_factory", return_value=mock_factory),
        ):
            await run_metagraph_sync_cycle()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_error_isolation_one_subnet_fails(self) -> None:
        """One subnet failure doesn't prevent others from syncing."""
        mg = _make_mock_metagraph(netuid=3, n=2)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        async def _mock_sync(netuid: int) -> MagicMock:
            if netuid == 1:
                raise ConnectionError("RPC timeout")
            return mg

        with (
            patch(
                "engine.ingestion.metagraph_sync.get_active_subnet_netuids",
                new_callable=AsyncMock,
                return_value=[1, 3],
            ),
            patch(
                "engine.ingestion.metagraph_sync.sync_subnet_metagraph",
                side_effect=_mock_sync,
            ),
            patch("engine.ingestion.metagraph_sync.cache_set", new_callable=AsyncMock),
            patch("engine.ingestion.metagraph_sync.get_session_factory", return_value=mock_factory),
        ):
            # Should not raise — error is isolated
            await run_metagraph_sync_cycle()

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self) -> None:
        """Verify concurrency is bounded by settings.metagraph_sync_workers."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        mg = _make_mock_metagraph(netuid=1, n=1)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        async def _tracked_sync(netuid: int) -> MagicMock:
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.01)
            async with lock:
                current_concurrent -= 1
            return mg

        # Create 12 subnets but limit workers to 4
        netuids = list(range(12))

        with (
            patch(
                "engine.ingestion.metagraph_sync.get_active_subnet_netuids",
                new_callable=AsyncMock,
                return_value=netuids,
            ),
            patch(
                "engine.ingestion.metagraph_sync.sync_subnet_metagraph",
                side_effect=_tracked_sync,
            ),
            patch("engine.ingestion.metagraph_sync.cache_set", new_callable=AsyncMock),
            patch("engine.ingestion.metagraph_sync.get_session_factory", return_value=mock_factory),
            patch("engine.ingestion.metagraph_sync.settings") as mock_settings,
        ):
            mock_settings.metagraph_sync_workers = 4
            mock_settings.cache_ttl_metagraph = 180
            await run_metagraph_sync_cycle()

        assert max_concurrent <= 4

    @pytest.mark.asyncio
    async def test_handles_subnet_discovery_failure(self) -> None:
        """If subnet discovery fails, cycle logs error and returns."""
        with patch(
            "engine.ingestion.metagraph_sync.get_active_subnet_netuids",
            new_callable=AsyncMock,
            side_effect=ConnectionError("chain down"),
        ):
            # Should not raise
            await run_metagraph_sync_cycle()
