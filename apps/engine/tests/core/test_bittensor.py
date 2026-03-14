"""Tests for Bittensor SDK helpers."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from engine.core import bittensor


@pytest.fixture(autouse=True)
def _reset_subtensor() -> None:
    """Reset module-level subtensor before each test."""
    bittensor._subtensor = None
    yield  # type: ignore[misc]
    bittensor._subtensor = None


class TestGetSubtensor:
    def test_creates_subtensor_with_network(self) -> None:
        with patch("engine.core.bittensor.bt.Subtensor") as mock_cls:
            mock_cls.return_value = MagicMock()
            result = bittensor.get_subtensor()
            mock_cls.assert_called_once_with(network="finney")
            assert result is mock_cls.return_value

    def test_creates_subtensor_with_endpoint(self) -> None:
        with (
            patch("engine.core.bittensor.bt.Subtensor") as mock_cls,
            patch("engine.core.bittensor.settings") as mock_settings,
        ):
            mock_settings.subtensor_endpoint = "wss://custom-endpoint.com"
            mock_settings.subtensor_network = "finney"
            mock_cls.return_value = MagicMock()
            result = bittensor.get_subtensor()
            mock_cls.assert_called_once_with(network="wss://custom-endpoint.com")
            assert result is mock_cls.return_value

    def test_reuses_existing_subtensor(self) -> None:
        mock_sub = MagicMock()
        bittensor._subtensor = mock_sub
        result = bittensor.get_subtensor()
        assert result is mock_sub


class TestSyncSubnetMetagraph:
    @pytest.mark.asyncio
    async def test_calls_metagraph_in_thread(self) -> None:
        mock_metagraph = MagicMock()
        mock_sub = MagicMock()
        mock_sub.metagraph.return_value = mock_metagraph
        bittensor._subtensor = mock_sub

        result = await bittensor.sync_subnet_metagraph(netuid=1)

        mock_sub.metagraph.assert_called_once_with(netuid=1)
        assert result is mock_metagraph

    @pytest.mark.asyncio
    async def test_runs_in_thread_not_blocking(self) -> None:
        """Verify sync call is wrapped in asyncio.to_thread."""
        mock_sub = MagicMock()
        mock_sub.metagraph.return_value = MagicMock()
        bittensor._subtensor = mock_sub

        with patch(
            "engine.core.bittensor.asyncio.to_thread", wraps=asyncio.to_thread
        ) as mock_thread:
            await bittensor.sync_subnet_metagraph(netuid=5)
            mock_thread.assert_called_once()


class TestGetActiveSubnetNetuids:
    @pytest.mark.asyncio
    async def test_returns_subnet_list(self) -> None:
        mock_sub = MagicMock()
        mock_sub.get_subnets.return_value = [0, 1, 3, 18, 19]
        bittensor._subtensor = mock_sub

        result = await bittensor.get_active_subnet_netuids()

        mock_sub.get_subnets.assert_called_once()
        assert result == [0, 1, 3, 18, 19]

    @pytest.mark.asyncio
    async def test_runs_in_thread(self) -> None:
        mock_sub = MagicMock()
        mock_sub.get_subnets.return_value = [1]
        bittensor._subtensor = mock_sub

        with patch(
            "engine.core.bittensor.asyncio.to_thread", wraps=asyncio.to_thread
        ) as mock_thread:
            await bittensor.get_active_subnet_netuids()
            mock_thread.assert_called_once()


class TestDisposeSubtensor:
    @pytest.mark.asyncio
    async def test_closes_subtensor(self) -> None:
        mock_sub = MagicMock()
        bittensor._subtensor = mock_sub

        await bittensor.dispose_subtensor()

        mock_sub.close.assert_called_once()
        assert bittensor._subtensor is None

    @pytest.mark.asyncio
    async def test_noop_when_no_subtensor(self) -> None:
        await bittensor.dispose_subtensor()
        assert bittensor._subtensor is None

    @pytest.mark.asyncio
    async def test_handles_close_error(self) -> None:
        mock_sub = MagicMock()
        mock_sub.close.side_effect = RuntimeError("close failed")
        bittensor._subtensor = mock_sub

        await bittensor.dispose_subtensor()

        assert bittensor._subtensor is None
