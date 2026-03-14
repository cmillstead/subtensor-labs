"""Bittensor SDK initialization and metagraph sync helpers."""

import asyncio
import threading
from typing import Any

import bittensor as bt

from engine.core.config import settings
from engine.core.logging import get_logger

log = get_logger(__name__)

# Module-level subtensor instance (reused across sync cycles)
_subtensor: bt.Subtensor | None = None
_init_lock = threading.Lock()


def get_subtensor() -> bt.Subtensor:
    """Get or create a Subtensor connection (thread-safe).

    Uses settings.subtensor_endpoint if set (Dwellir commercial RPC),
    otherwise falls back to settings.subtensor_network ("finney").
    """
    global _subtensor  # noqa: PLW0603
    if _subtensor is None:
        with _init_lock:
            if _subtensor is None:
                if settings.subtensor_endpoint:
                    _subtensor = bt.Subtensor(network=settings.subtensor_endpoint)
                    log.info(
                        "subtensor_connected",
                        endpoint=settings.subtensor_endpoint,
                        worker="bittensor",
                    )
                else:
                    _subtensor = bt.Subtensor(network=settings.subtensor_network)
                    log.info(
                        "subtensor_connected",
                        network=settings.subtensor_network,
                        worker="bittensor",
                    )
    return _subtensor


async def sync_subnet_metagraph(netuid: int) -> Any:
    """Sync metagraph for a single subnet.

    The Bittensor SDK metagraph sync is synchronous, so we run it in a
    thread to avoid blocking the async event loop.

    Returns the metagraph object with attributes: uids, hotkeys, coldkeys,
    stake, incentive, trust, dividends, active, n, block.
    """
    subtensor = get_subtensor()

    def _sync() -> Any:
        return subtensor.metagraph(netuid=netuid)

    return await asyncio.to_thread(_sync)


async def get_active_subnet_netuids() -> list[int]:
    """Discover all active subnet netuids from the chain.

    Runs in a thread since the SDK call is synchronous.
    """
    subtensor = get_subtensor()

    def _get_netuids() -> list[int]:
        result: list[int] = subtensor.get_subnets()
        return result

    return await asyncio.to_thread(_get_netuids)


async def get_subnet_hyperparams(netuid: int) -> Any:
    """Fetch subnet hyperparameters including AMM pool reserves.

    Wraps the synchronous SDK call in asyncio.to_thread().
    Returns the SubnetHyperparams object (or equivalent) for the given subnet.
    """
    subtensor = get_subtensor()

    def _get_hyperparams() -> Any:
        return subtensor.get_subnet_hyperparameters(netuid=netuid)

    return await asyncio.to_thread(_get_hyperparams)


async def dispose_subtensor() -> None:
    """Clean up the subtensor connection on shutdown."""
    global _subtensor  # noqa: PLW0603
    if _subtensor is not None:
        try:
            _subtensor.close()
        except Exception:
            log.warning("subtensor_close_failed", exc_info=True)
        _subtensor = None
