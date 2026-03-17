"""Tests for portfolio position detail computation."""

from engine.portfolio.positions import compute_position_details, compute_totals
from engine.schemas.portfolio import SubnetPositionSchema

from .conftest import HOTKEY_1, HOTKEY_2
from .conftest import make_position_entry as _entry


class TestComputePositionDetails:
    def test_single_entry_with_price(self) -> None:
        entries = [_entry(stake=100.0)]
        prices = {1: 2.0}
        positions = compute_position_details(entries, prices)
        assert len(positions) == 1
        assert positions[0].staked_tao == 100.0
        assert positions[0].alpha_value_tao == 200.0  # 100 * 2.0

    def test_single_entry_no_price(self) -> None:
        entries = [_entry(stake=100.0)]
        prices: dict[int, float] = {}
        positions = compute_position_details(entries, prices)
        assert positions[0].alpha_value_tao == 0.0

    def test_miner_detection(self) -> None:
        entries = [_entry(incentive=0.5)]
        positions = compute_position_details(entries, {})
        assert positions[0].is_miner is True

    def test_non_miner_detection(self) -> None:
        entries = [_entry(incentive=0.0)]
        positions = compute_position_details(entries, {})
        assert positions[0].is_miner is False

    def test_multiple_subnets(self) -> None:
        entries = [
            _entry(netuid=1, stake=100.0),
            _entry(netuid=2, stake=200.0, hotkey=HOTKEY_2),
        ]
        prices = {1: 1.0, 2: 0.5}
        positions = compute_position_details(entries, prices)
        assert len(positions) == 2
        assert positions[0].alpha_value_tao == 100.0
        assert positions[1].alpha_value_tao == 100.0

    def test_zero_stake(self) -> None:
        entries = [_entry(stake=0.0)]
        prices = {1: 10.0}
        positions = compute_position_details(entries, prices)
        assert positions[0].staked_tao == 0.0
        assert positions[0].alpha_value_tao == 0.0

    def test_none_values_default_to_zero(self) -> None:
        entry = {
            "netuid": 1,
            "hotkey": HOTKEY_1,
            "stake": None,
            "incentive": None,
            "trust": None,
            "dividends": None,
            "is_active": False,
            "emission_share": None,
        }
        positions = compute_position_details([entry], {})
        assert positions[0].staked_tao == 0.0
        assert positions[0].incentive == 0.0
        assert positions[0].trust == 0.0
        assert positions[0].dividends == 0.0

    def test_empty_entries(self) -> None:
        positions = compute_position_details([], {})
        assert positions == []

    def test_inactive_neuron(self) -> None:
        entries = [_entry(is_active=False)]
        positions = compute_position_details(entries, {})
        assert positions[0].is_active is False


class TestComputeTotals:
    def test_single_position(self) -> None:
        pos = SubnetPositionSchema(
            netuid=1,
            hotkey=HOTKEY_1,
            staked_tao=100.0,
            alpha_value_tao=50.0,
            emission_share=0.05,
            incentive=0.0,
            trust=0.9,
            dividends=0.1,
            is_active=True,
            is_miner=False,
        )
        staked, alpha, total = compute_totals([pos])
        assert staked == 100.0
        assert alpha == 50.0
        assert total == 150.0

    def test_multiple_positions(self) -> None:
        positions = [
            SubnetPositionSchema(
                netuid=1,
                hotkey=HOTKEY_1,
                staked_tao=100.0,
                alpha_value_tao=50.0,
                emission_share=0.0,
                incentive=0.0,
                trust=0.0,
                dividends=0.0,
                is_active=True,
                is_miner=False,
            ),
            SubnetPositionSchema(
                netuid=2,
                hotkey=HOTKEY_2,
                staked_tao=200.0,
                alpha_value_tao=30.0,
                emission_share=0.0,
                incentive=0.0,
                trust=0.0,
                dividends=0.0,
                is_active=True,
                is_miner=False,
            ),
        ]
        staked, alpha, total = compute_totals(positions)
        assert staked == 300.0
        assert alpha == 80.0
        assert total == 380.0

    def test_empty_positions(self) -> None:
        staked, alpha, total = compute_totals([])
        assert staked == 0.0
        assert alpha == 0.0
        assert total == 0.0
