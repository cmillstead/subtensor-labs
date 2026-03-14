"""Tests for version consistency."""

import tomllib
from pathlib import Path

from engine import __version__
from engine.schemas.errors import ENGINE_VERSION


def test_version_matches_pyproject() -> None:
    """Engine __version__ matches pyproject.toml version."""
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    assert __version__ == data["project"]["version"]


def test_engine_version_alias_matches() -> None:
    """ENGINE_VERSION in schemas re-exports __version__ from engine package."""
    assert __version__ == ENGINE_VERSION
