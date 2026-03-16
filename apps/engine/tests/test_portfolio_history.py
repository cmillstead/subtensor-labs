"""Tests for portfolio history schemas — pure unit tests only.

Integration tests for the history endpoint and get_portfolio_history
are in tests/api_integration/test_portfolio_api.py (real DB + Redis).
"""

import pytest
from pydantic import ValidationError

from engine.schemas.portfolio_history import (
    PortfolioHistoryRequestSchema,
    PortfolioHistoryResponseSchema,
)

VALID_COLDKEY = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"


class TestPortfolioHistoryRequestSchema:
    def test_valid_request(self) -> None:
        req = PortfolioHistoryRequestSchema(
            coldkey_addresses=[VALID_COLDKEY],
            time_range="7d",
        )
        assert req.time_range == "7d"

    def test_all_time_ranges(self) -> None:
        for tr in ("7d", "30d", "90d"):
            req = PortfolioHistoryRequestSchema(
                coldkey_addresses=[VALID_COLDKEY],
                time_range=tr,
            )
            assert req.time_range == tr

    def test_invalid_time_range(self) -> None:
        with pytest.raises(ValidationError):
            PortfolioHistoryRequestSchema(
                coldkey_addresses=[VALID_COLDKEY],
                time_range="1d",
            )

    def test_empty_addresses_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PortfolioHistoryRequestSchema(
                coldkey_addresses=[],
                time_range="7d",
            )

    def test_invalid_address_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PortfolioHistoryRequestSchema(
                coldkey_addresses=["not-valid"],
                time_range="7d",
            )

    def test_too_many_addresses_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PortfolioHistoryRequestSchema(
                coldkey_addresses=[VALID_COLDKEY] * 21,
                time_range="7d",
            )


class TestPortfolioHistoryResponseSchema:
    def test_empty_points(self) -> None:
        resp = PortfolioHistoryResponseSchema(points=[], data_start=None, time_range="7d")
        assert resp.points == []
        assert resp.data_start is None

    def test_with_points(self) -> None:
        resp = PortfolioHistoryResponseSchema(
            points=[{"time": "2026-03-14T00:00:00Z", "total_value_tao": 100.0}],
            data_start=None,
            time_range="30d",
        )
        assert len(resp.points) == 1
        assert resp.points[0].total_value_tao == 100.0
