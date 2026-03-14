"""Subtensor Labs Engine — data engine for Bittensor analytics."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("subtensor-labs-engine")
except PackageNotFoundError:
    __version__ = "0.1.0"
