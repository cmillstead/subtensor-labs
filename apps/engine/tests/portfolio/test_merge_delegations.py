"""Tests for delegation merging in _merge_positions (Story 2.2)."""

import sys
from unittest.mock import MagicMock

# Stub bittensor before importing aggregator (avoids ModuleNotFoundError)
if "bittensor" not in sys.modules:
    sys.modules["bittensor"] = MagicMock()

from engine.portfolio.aggregator import _merge_positions  # noqa: E402
from engine.schemas.portfolio import (  # noqa: E402
    ColdkeyPortfolioSchema,
    DelegationDetailSchema,
    SubnetPositionSchema,
)

COLDKEY_1 = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
COLDKEY_2 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
HOTKEY_1 = "5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy"
HOTKEY_2 = "5HGjWAeFDfFCWPsjFQdVV2Msvz2XtMktvgocEZcCj68kUMaw"
HOTKEY_3 = "5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSneWj6VRz28"


def _delegation(
    hotkey: str = HOTKEY_1,
    name: str | None = None,
    amount: float = 100.0,
    take_rate: float = 0.1,
) -> DelegationDetailSchema:
    return DelegationDetailSchema(
        validator_hotkey=hotkey,
        validator_name=name,
        delegated_amount=amount,
        take_rate=take_rate,
    )


def _pos(
    netuid: int = 1,
    hotkey: str = HOTKEY_1,
    staked: float = 100.0,
    delegations: list[DelegationDetailSchema] | None = None,
) -> SubnetPositionSchema:
    return SubnetPositionSchema(
        netuid=netuid,
        hotkey=hotkey,
        staked_tao=staked,
        alpha_value_tao=50.0,
        emission_share=0.05,
        incentive=0.0,
        trust=0.9,
        dividends=0.1,
        is_active=True,
        is_miner=False,
        delegations=delegations or [],
    )


def _coldkey_portfolio(
    coldkey: str = COLDKEY_1,
    positions: list[SubnetPositionSchema] | None = None,
) -> ColdkeyPortfolioSchema:
    if positions is None:
        positions = [_pos()]
    staked = sum(p.staked_tao for p in positions)
    alpha = sum(p.alpha_value_tao for p in positions)
    netuids = {p.netuid for p in positions}
    return ColdkeyPortfolioSchema(
        coldkey=coldkey,
        total_value_tao=staked + alpha,
        total_staked_tao=staked,
        total_alpha_value_tao=alpha,
        positions=positions,
        subnets_exposed=len(netuids),
    )


class TestMergeDelegations:
    def test_single_coldkey_preserves_delegations(self) -> None:
        d = _delegation(hotkey=HOTKEY_1, name="ValidatorA")
        result = _coldkey_portfolio(positions=[_pos(delegations=[d])])
        merged = _merge_positions([result])
        assert len(merged) == 1
        assert len(merged[0].delegations) == 1
        assert merged[0].delegations[0].validator_name == "ValidatorA"

    def test_two_coldkeys_same_subnet_different_validators_merged(self) -> None:
        """Different hotkeys in same subnet → delegations should merge."""
        d1 = _delegation(hotkey=HOTKEY_1, name="ValidatorA")
        d2 = _delegation(hotkey=HOTKEY_2, name="ValidatorB")
        result1 = _coldkey_portfolio(
            coldkey=COLDKEY_1,
            positions=[_pos(netuid=1, hotkey=HOTKEY_1, delegations=[d1])],
        )
        result2 = _coldkey_portfolio(
            coldkey=COLDKEY_2,
            positions=[_pos(netuid=1, hotkey=HOTKEY_2, delegations=[d2])],
        )
        merged = _merge_positions([result1, result2])
        # Both positions kept (different hotkeys)
        assert len(merged) == 2
        # First position in subnet 1 should have merged delegations
        subnet1_pos = merged[0]
        assert len(subnet1_pos.delegations) == 2
        validator_names = {d.validator_name for d in subnet1_pos.delegations}
        assert validator_names == {"ValidatorA", "ValidatorB"}

    def test_duplicate_validator_not_duplicated(self) -> None:
        """Same validator hotkey across coldkeys → only kept once."""
        d1 = _delegation(hotkey=HOTKEY_1, name="SameValidator")
        d2 = _delegation(hotkey=HOTKEY_1, name="SameValidator")
        result1 = _coldkey_portfolio(
            coldkey=COLDKEY_1,
            positions=[_pos(netuid=1, hotkey=HOTKEY_1, delegations=[d1])],
        )
        result2 = _coldkey_portfolio(
            coldkey=COLDKEY_2,
            positions=[_pos(netuid=1, hotkey=HOTKEY_2, delegations=[d2])],
        )
        merged = _merge_positions([result1, result2])
        subnet1_pos = merged[0]
        assert len(subnet1_pos.delegations) == 1

    def test_three_coldkeys_same_subnet_accumulates(self) -> None:
        """Three coldkeys with positions in the same subnet, each with
        a unique validator — all 3 delegations should be merged."""
        d1 = _delegation(hotkey=HOTKEY_1, name="V1")
        d2 = _delegation(hotkey=HOTKEY_2, name="V2")
        d3 = _delegation(hotkey=HOTKEY_3, name="V3")
        results = [
            _coldkey_portfolio(
                coldkey=COLDKEY_1,
                positions=[_pos(netuid=1, hotkey=HOTKEY_1, delegations=[d1])],
            ),
            _coldkey_portfolio(
                coldkey=COLDKEY_2,
                positions=[_pos(netuid=1, hotkey=HOTKEY_2, delegations=[d2])],
            ),
            _coldkey_portfolio(
                coldkey="5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSneWj6VRz28",
                positions=[_pos(netuid=1, hotkey=HOTKEY_3, delegations=[d3])],
            ),
        ]
        merged = _merge_positions(results)
        subnet1_pos = merged[0]
        assert len(subnet1_pos.delegations) == 3
        names = {d.validator_name for d in subnet1_pos.delegations}
        assert names == {"V1", "V2", "V3"}

    def test_different_subnets_not_merged(self) -> None:
        """Positions in different subnets keep separate delegation lists."""
        d1 = _delegation(hotkey=HOTKEY_1, name="V1")
        d2 = _delegation(hotkey=HOTKEY_2, name="V2")
        result = _coldkey_portfolio(
            positions=[
                _pos(netuid=1, hotkey=HOTKEY_1, delegations=[d1]),
                _pos(netuid=2, hotkey=HOTKEY_2, delegations=[d2]),
            ],
        )
        merged = _merge_positions([result])
        assert len(merged) == 2
        assert len(merged[0].delegations) == 1
        assert len(merged[1].delegations) == 1

    def test_empty_delegations_no_crash(self) -> None:
        result = _coldkey_portfolio(positions=[_pos(delegations=[])])
        merged = _merge_positions([result])
        assert len(merged[0].delegations) == 0
