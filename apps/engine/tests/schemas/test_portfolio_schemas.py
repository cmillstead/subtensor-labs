"""Tests for portfolio request/response schemas."""

import pytest
from pydantic import ValidationError

from engine.schemas.portfolio import (
    ColdkeyPortfolioSchema,
    PortfolioRequestSchema,
    PortfolioResponseSchema,
    SubnetPositionSchema,
)

# Valid SS58 address (48 chars, base58)
VALID_COLDKEY = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
VALID_COLDKEY_2 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"


class TestSubnetPositionSchema:
    def test_valid_position(self) -> None:
        pos = SubnetPositionSchema(
            netuid=1,
            hotkey="5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
            staked_tao=100.5,
            alpha_value_tao=50.25,
            emission_share=0.05,
            incentive=0.8,
            trust=0.9,
            dividends=0.1,
            is_active=True,
            is_miner=False,
        )
        assert pos.netuid == 1
        assert pos.staked_tao == 100.5
        assert pos.is_miner is False

    def test_zero_values(self) -> None:
        pos = SubnetPositionSchema(
            netuid=0,
            hotkey="5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
            staked_tao=0.0,
            alpha_value_tao=0.0,
            emission_share=0.0,
            incentive=0.0,
            trust=0.0,
            dividends=0.0,
            is_active=False,
            is_miner=True,
        )
        assert pos.staked_tao == 0.0


class TestPortfolioResponseSchema:
    def test_valid_response(self) -> None:
        resp = PortfolioResponseSchema(
            total_value_tao=150.75,
            total_staked_tao=100.5,
            total_alpha_value_tao=50.25,
            positions=[],
            subnets_exposed=0,
            coldkeys_resolved=1,
            last_updated="2026-03-14T14:30:00Z",
        )
        assert resp.total_value_tao == 150.75
        assert resp.subnets_exposed == 0
        assert resp.coldkeys_resolved == 1

    def test_with_positions(self) -> None:
        pos = SubnetPositionSchema(
            netuid=1,
            hotkey=VALID_COLDKEY,
            staked_tao=100.0,
            alpha_value_tao=50.0,
            emission_share=0.05,
            incentive=0.8,
            trust=0.9,
            dividends=0.1,
            is_active=True,
            is_miner=False,
        )
        resp = PortfolioResponseSchema(
            total_value_tao=150.0,
            total_staked_tao=100.0,
            total_alpha_value_tao=50.0,
            positions=[pos],
            subnets_exposed=1,
            coldkeys_resolved=1,
            last_updated="2026-03-14T14:30:00Z",
        )
        assert len(resp.positions) == 1
        assert resp.positions[0].netuid == 1


class TestColdkeyPortfolioSchema:
    def test_valid(self) -> None:
        schema = ColdkeyPortfolioSchema(
            coldkey=VALID_COLDKEY,
            total_value_tao=100.0,
            total_staked_tao=80.0,
            total_alpha_value_tao=20.0,
            positions=[],
            subnets_exposed=0,
        )
        assert schema.coldkey == VALID_COLDKEY


class TestPortfolioRequestSchema:
    def test_valid_single_address(self) -> None:
        req = PortfolioRequestSchema(coldkey_addresses=[VALID_COLDKEY])
        assert len(req.coldkey_addresses) == 1

    def test_valid_multiple_addresses(self) -> None:
        req = PortfolioRequestSchema(
            coldkey_addresses=[VALID_COLDKEY, VALID_COLDKEY_2]
        )
        assert len(req.coldkey_addresses) == 2

    def test_empty_addresses_rejected(self) -> None:
        with pytest.raises(ValidationError, match="At least one coldkey"):
            PortfolioRequestSchema(coldkey_addresses=[])

    def test_too_many_addresses_rejected(self) -> None:
        addresses = [VALID_COLDKEY] * 21
        with pytest.raises(ValidationError, match="Maximum 20"):
            PortfolioRequestSchema(coldkey_addresses=addresses)

    def test_invalid_ss58_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Invalid SS58"):
            PortfolioRequestSchema(coldkey_addresses=["not-a-valid-address"])

    def test_short_address_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Invalid SS58"):
            PortfolioRequestSchema(coldkey_addresses=["5FHne"])

    def test_max_addresses_accepted(self) -> None:
        addresses = [VALID_COLDKEY] * 20
        req = PortfolioRequestSchema(coldkey_addresses=addresses)
        assert len(req.coldkey_addresses) == 20
