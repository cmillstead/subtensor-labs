"""Tests for enhanced position detail computation (Story 2.2 fields)."""

from engine.portfolio.positions import _BLOCKS_PER_YEAR, compute_position_details

HOTKEY = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"


def _entry(
    netuid: int = 1,
    hotkey: str = HOTKEY,
    stake: float = 100.0,
    incentive: float = 0.0,
    trust: float = 0.9,
    dividends: float = 0.1,
    is_active: bool = True,
    emission_share: float = 0.05,
    subnet_name: str | None = None,
    take_rate: float = 0.0,
    validator_name: str | None = None,
) -> dict:
    return {
        "netuid": netuid,
        "hotkey": hotkey,
        "stake": stake,
        "incentive": incentive,
        "trust": trust,
        "dividends": dividends,
        "is_active": is_active,
        "emission_share": emission_share,
        "subnet_name": subnet_name,
        "take_rate": take_rate,
        "validator_name": validator_name,
    }


class TestAlphaHoldings:
    def test_alpha_holdings_with_price(self) -> None:
        positions = compute_position_details([_entry(stake=100.0)], {1: 0.5})
        # alpha_holdings = stake / price = 100 / 0.5 = 200
        assert positions[0].alpha_holdings == 200.0

    def test_alpha_holdings_no_price(self) -> None:
        positions = compute_position_details([_entry(stake=100.0)], {})
        assert positions[0].alpha_holdings == 0.0

    def test_alpha_holdings_zero_price(self) -> None:
        positions = compute_position_details([_entry(stake=100.0)], {1: 0.0})
        assert positions[0].alpha_holdings == 0.0

    def test_alpha_holdings_zero_stake(self) -> None:
        positions = compute_position_details([_entry(stake=0.0)], {1: 2.0})
        assert positions[0].alpha_holdings == 0.0


class TestSubnetName:
    def test_subnet_name_populated(self) -> None:
        positions = compute_position_details(
            [_entry(subnet_name="Templar")], {}
        )
        assert positions[0].subnet_name == "Templar"

    def test_subnet_name_none_by_default(self) -> None:
        positions = compute_position_details([_entry()], {})
        assert positions[0].subnet_name is None


class TestDelegationComputation:
    def test_delegation_created_per_position(self) -> None:
        positions = compute_position_details([_entry(stake=100.0)], {})
        assert len(positions[0].delegations) == 1
        assert positions[0].delegations[0].validator_hotkey == HOTKEY
        assert positions[0].delegations[0].delegated_amount == 100.0

    def test_delegation_apy_computed(self) -> None:
        positions = compute_position_details(
            [_entry(stake=100.0, dividends=0.01)], {}
        )
        d = positions[0].delegations[0]
        expected_apy = round((0.01 / 100.0) * _BLOCKS_PER_YEAR * 100, 2)
        assert d.estimated_apy == expected_apy

    def test_delegation_apy_none_when_no_dividends(self) -> None:
        positions = compute_position_details(
            [_entry(stake=100.0, dividends=0.0)], {}
        )
        assert positions[0].delegations[0].estimated_apy is None

    def test_delegation_apy_none_when_zero_stake(self) -> None:
        positions = compute_position_details(
            [_entry(stake=0.0, dividends=0.1)], {}
        )
        assert positions[0].delegations[0].estimated_apy is None

    def test_delegation_take_rate(self) -> None:
        positions = compute_position_details(
            [_entry(take_rate=0.18)], {}
        )
        assert positions[0].delegations[0].take_rate == 0.18

    def test_delegation_validator_name(self) -> None:
        positions = compute_position_details(
            [_entry(validator_name="MyValidator")], {}
        )
        assert positions[0].delegations[0].validator_name == "MyValidator"

    def test_delegation_validator_name_none(self) -> None:
        positions = compute_position_details([_entry()], {})
        assert positions[0].delegations[0].validator_name is None
