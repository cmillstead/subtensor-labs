"""Tests for scenario engine — HHI, move application, and outcome building."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from engine.predictions.scenario_engine import _build_outcome, apply_moves, compute_hhi
from engine.schemas.predictions import (
    ScenarioCalcRequestSchema,
    ScenarioInputSchema,
    ScenarioMoveSchema,
    SubnetAllocationSchema,
)


class TestComputeHhi:
    """Test Herfindahl-Hirschman Index computation."""

    def _make_allocation(self, netuid: int, pct: float) -> SubnetAllocationSchema:
        """Helper to build a minimal SubnetAllocationSchema."""
        return SubnetAllocationSchema(
            netuid=netuid,
            stake_tao=100.0,
            allocation_pct=pct,
            projected_yield_tao=0.0,
            confidence_68_lower=0.0,
            confidence_68_upper=0.0,
        )

    def test_single_position_max_hhi(self) -> None:
        """100% in one subnet should produce HHI of 10000."""
        allocations = [self._make_allocation(1, 100.0)]
        assert compute_hhi(allocations) == 10000.0

    def test_equal_two_way_split(self) -> None:
        """50/50 split should produce HHI of 5000."""
        allocations = [self._make_allocation(1, 50.0), self._make_allocation(2, 50.0)]
        assert compute_hhi(allocations) == 5000.0

    def test_equal_four_way_split(self) -> None:
        """25% each across 4 subnets should produce HHI of 2500."""
        allocations = [self._make_allocation(i, 25.0) for i in range(4)]
        assert compute_hhi(allocations) == 2500.0

    def test_empty_allocations(self) -> None:
        """No allocations should produce HHI of 0."""
        assert compute_hhi([]) == 0.0


class TestApplyMoves:
    """Test scenario move application logic."""

    def _make_scenario(self, moves: list[ScenarioMoveSchema]) -> ScenarioInputSchema:
        """Helper to wrap moves in a ScenarioInputSchema."""
        return ScenarioInputSchema(label="test", moves=moves)

    def test_basic_move_between_subnets(self) -> None:
        """Moving 100 TAO from SN1 to SN2 should adjust both balances."""
        base = {1: 500.0, 2: 300.0}
        scenario = self._make_scenario(
            [
                ScenarioMoveSchema(source_netuid=1, dest_netuid=2, amount_tao=100.0),
            ]
        )
        result = apply_moves(base, scenario)
        assert isinstance(result, dict)
        assert result[1] == 400.0
        assert result[2] == 400.0

    def test_move_all_stake_from_subnet(self) -> None:
        """Moving all TAO from a subnet should leave it at zero."""
        base = {1: 200.0, 2: 100.0}
        scenario = self._make_scenario(
            [
                ScenarioMoveSchema(source_netuid=1, dest_netuid=2, amount_tao=200.0),
            ]
        )
        result = apply_moves(base, scenario)
        assert isinstance(result, dict)
        assert result[1] == pytest.approx(0.0, abs=1e-9)
        assert result[2] == 300.0

    def test_move_to_new_subnet(self) -> None:
        """Moving to a subnet not in current stakes should create it."""
        base = {1: 500.0}
        scenario = self._make_scenario(
            [
                ScenarioMoveSchema(source_netuid=1, dest_netuid=99, amount_tao=100.0),
            ]
        )
        result = apply_moves(base, scenario)
        assert isinstance(result, dict)
        assert result[99] == 100.0
        assert result[1] == 400.0

    def test_multiple_moves_in_scenario(self) -> None:
        """Two moves in one scenario should both be applied sequentially."""
        base = {1: 500.0, 2: 300.0, 3: 200.0}
        scenario = self._make_scenario(
            [
                ScenarioMoveSchema(source_netuid=1, dest_netuid=2, amount_tao=100.0),
                ScenarioMoveSchema(source_netuid=3, dest_netuid=1, amount_tao=50.0),
            ]
        )
        result = apply_moves(base, scenario)
        assert isinstance(result, dict)
        assert result[1] == 450.0  # 500 - 100 + 50
        assert result[2] == 400.0  # 300 + 100
        assert result[3] == 150.0  # 200 - 50

    def test_move_exceeds_stake_returns_error(self) -> None:
        """Moving more than available should return an error string."""
        base = {1: 50.0, 2: 100.0}
        scenario = self._make_scenario(
            [
                ScenarioMoveSchema(source_netuid=1, dest_netuid=2, amount_tao=100.0),
            ]
        )
        result = apply_moves(base, scenario)
        assert isinstance(result, str)
        assert "exceeds stake" in result.lower() or "Move exceeds stake" in result

    def test_move_from_zero_stake_returns_error(self) -> None:
        """Moving from a subnet with no stake should return an error string."""
        base = {2: 100.0}
        scenario = self._make_scenario(
            [
                ScenarioMoveSchema(source_netuid=1, dest_netuid=2, amount_tao=10.0),
            ]
        )
        result = apply_moves(base, scenario)
        assert isinstance(result, str)

    def test_net_zero_total_stake(self) -> None:
        """Moves should not change total staked TAO."""
        base = {1: 500.0, 2: 300.0, 3: 200.0}
        original_total = sum(base.values())
        scenario = self._make_scenario(
            [
                ScenarioMoveSchema(source_netuid=1, dest_netuid=2, amount_tao=150.0),
                ScenarioMoveSchema(source_netuid=3, dest_netuid=1, amount_tao=75.0),
            ]
        )
        result = apply_moves(base, scenario)
        assert isinstance(result, dict)
        assert sum(result.values()) == pytest.approx(original_total)


class TestBuildOutcome:
    """Test the _build_outcome algebraic computation."""

    def _make_emission_history(
        self,
        days: int = 30,
        base_emission: float = 2.0,
        daily_change: float = 0.01,
    ) -> list[tuple[datetime, float]]:
        """Helper to generate synthetic emission history."""
        base_time = datetime.now(UTC) - timedelta(days=days)
        return [
            (base_time + timedelta(days=i), base_emission + daily_change * i) for i in range(days)
        ]

    def test_baseline_with_known_emission_data(self) -> None:
        """Build outcome with synthetic emission history; verify allocations and yield."""
        stakes = {1: 500.0, 2: 500.0}
        emission_history = {
            1: self._make_emission_history(days=30, base_emission=5.0, daily_change=0.05),
            2: self._make_emission_history(days=30, base_emission=3.0, daily_change=0.02),
        }
        take_rates = {1: 0.0, 2: 0.0}
        alpha_prices = {1: 1.5, 2: 2.0}

        outcome = _build_outcome(stakes, emission_history, take_rates, alpha_prices, horizon=30)

        assert len(outcome.allocations) == 2
        assert outcome.total_staked_tao == 1000.0
        assert outcome.total_projected_yield_tao > 0

    def test_empty_stakes_produces_empty_outcome(self) -> None:
        """No stakes should produce zero everything."""
        outcome = _build_outcome(
            stakes={},
            emission_history={},
            take_rates={},
            alpha_prices={},
            horizon=30,
        )

        assert outcome.allocations == []
        assert outcome.total_staked_tao == 0.0
        assert outcome.total_projected_yield_tao == 0.0
        assert outcome.hhi == 0.0

    def test_allocation_percentages_sum_to_100(self) -> None:
        """Allocation percentages across subnets should sum to ~100."""
        stakes = {1: 300.0, 2: 500.0, 3: 200.0}
        emission_history = {n: self._make_emission_history(days=30) for n in stakes}
        take_rates = {n: 0.0 for n in stakes}
        alpha_prices = {n: 1.0 for n in stakes}

        outcome = _build_outcome(stakes, emission_history, take_rates, alpha_prices, horizon=30)

        total_pct = sum(a.allocation_pct for a in outcome.allocations)
        assert total_pct == pytest.approx(100.0, abs=0.1)

    def test_alpha_exposure_computed(self) -> None:
        """Alpha exposure should equal alpha_price * stake_tao."""
        stakes = {1: 400.0}
        emission_history = {1: self._make_emission_history(days=30)}
        take_rates = {1: 0.0}
        alpha_prices = {1: 2.5}

        outcome = _build_outcome(stakes, emission_history, take_rates, alpha_prices, horizon=30)

        alloc = outcome.allocations[0]
        assert alloc.alpha_exposure_tao == pytest.approx(400.0 * 2.5)
        assert outcome.total_alpha_exposure_tao == pytest.approx(1000.0)

    def test_yield_delta_computed_vs_baseline(self) -> None:
        """When baseline_yield is provided, yield_delta should be computed."""
        stakes = {1: 500.0}
        emission_history = {
            1: self._make_emission_history(days=30, base_emission=5.0, daily_change=0.05)
        }
        take_rates = {1: 0.0}
        alpha_prices = {1: 1.0}

        outcome = _build_outcome(
            stakes,
            emission_history,
            take_rates,
            alpha_prices,
            horizon=30,
            baseline_yield=10.0,
        )

        expected_delta = outcome.total_projected_yield_tao - 10.0
        assert outcome.yield_delta_tao == pytest.approx(expected_delta, abs=1e-5)

    def test_subnets_with_insufficient_data_get_zero_yield(self) -> None:
        """Subnet with fewer than 7 data points should get zero projected yield."""
        stakes = {1: 500.0}
        # Only 3 data points — below _MIN_DATA_POINTS (7)
        emission_history = {1: self._make_emission_history(days=3)}
        take_rates = {1: 0.0}
        alpha_prices = {1: 1.0}

        outcome = _build_outcome(stakes, emission_history, take_rates, alpha_prices, horizon=30)

        alloc = outcome.allocations[0]
        assert alloc.projected_yield_tao == 0.0
        assert outcome.total_projected_yield_tao == 0.0


class TestScenarioSchemaValidation:
    """Test Pydantic validation on scenario request schemas."""

    _VALID_ADDR = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"

    def _make_valid_scenario(self) -> ScenarioInputSchema:
        """Helper to build a valid single-move scenario."""
        return ScenarioInputSchema(
            label="Test",
            moves=[ScenarioMoveSchema(source_netuid=1, dest_netuid=2, amount_tao=100.0)],
        )

    def test_valid_scenario_request(self) -> None:
        """A well-formed request should pass validation."""
        request = ScenarioCalcRequestSchema(
            coldkey_addresses=[self._VALID_ADDR],
            scenarios=[self._make_valid_scenario()],
            horizon=90,
        )
        assert len(request.scenarios) == 1
        assert request.horizon == 90

    def test_too_many_scenarios_rejected(self) -> None:
        """More than 5 scenarios should be rejected."""
        with pytest.raises(ValidationError, match="Maximum 5 scenarios"):
            ScenarioCalcRequestSchema(
                coldkey_addresses=[self._VALID_ADDR],
                scenarios=[self._make_valid_scenario() for _ in range(6)],
                horizon=90,
            )

    def test_negative_move_amount_rejected(self) -> None:
        """Negative amount_tao should fail validation."""
        with pytest.raises(ValidationError, match="Move amount must be positive"):
            ScenarioMoveSchema(source_netuid=1, dest_netuid=2, amount_tao=-50.0)

    def test_same_source_dest_rejected(self) -> None:
        """source_netuid == dest_netuid should fail validation."""
        with pytest.raises(ValidationError, match="Source and destination subnets must differ"):
            ScenarioMoveSchema(source_netuid=1, dest_netuid=1, amount_tao=100.0)

    def test_empty_moves_rejected(self) -> None:
        """Empty moves list should fail validation."""
        with pytest.raises(ValidationError, match="At least one move is required"):
            ScenarioInputSchema(label="Empty", moves=[])
