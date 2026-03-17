"""Tests for emission forecaster — EMA computation and projection math."""

import pytest

from engine.predictions.emission_forecaster import (
    BLOCKS_PER_DAY,
    GENESIS_EMISSION_PER_BLOCK,
    HALVING_INTERVAL_BLOCKS,
    classify_trend,
    compute_ema,
    compute_halving_impact,
    project_emission_trajectory,
)


class TestComputeEma:
    """Test exponential moving average computation."""

    def test_single_value(self) -> None:
        """EMA of a single value is the value itself."""
        result = compute_ema([5.0], span=14)
        assert result == [5.0]

    def test_constant_values(self) -> None:
        """EMA of constant values should remain constant."""
        values = [3.0] * 20
        result = compute_ema(values, span=14)
        for v in result:
            assert v == pytest.approx(3.0)

    def test_increasing_values_ema_follows(self) -> None:
        """EMA of increasing values should lag behind but trend upward."""
        values = [float(i) for i in range(20)]
        result = compute_ema(values, span=14)
        # EMA lags — last EMA should be less than last value
        assert result[-1] < values[-1]
        # But should be increasing
        assert result[-1] > result[-5]

    def test_span_affects_smoothing(self) -> None:
        """Shorter span = more responsive to recent values."""
        values = [1.0] * 10 + [10.0] * 5
        short_ema = compute_ema(values, span=3)
        long_ema = compute_ema(values, span=14)
        # Short span reacts faster to the jump
        assert short_ema[-1] > long_ema[-1]


class TestProjectEmissionTrajectory:
    """Test EMA-based emission trajectory projection."""

    def test_stable_trend_projects_flat(self) -> None:
        """Constant emission should project roughly flat."""
        values = [5.0] * 30
        result = project_emission_trajectory(values, horizon_days=30)
        predicted = result["predicted"]
        # All projected values should be close to 5.0
        for v in predicted:
            assert v == pytest.approx(5.0, abs=0.1)

    def test_increasing_trend_projects_upward(self) -> None:
        """Increasing emission should project upward initially."""
        values = [2.0 + 0.1 * i for i in range(30)]
        result = project_emission_trajectory(values, horizon_days=30)
        # EMA lags behind raw values, but day 5 should be above day 1 (upward trend)
        assert result["predicted"][4] > result["predicted"][0]
        # Momentum should be positive
        assert result["momentum"] > 0

    def test_confidence_bands_widen(self) -> None:
        """Confidence bands should widen over time."""
        values = [2.0 + 0.1 * i for i in range(30)]
        result = project_emission_trajectory(values, horizon_days=30)
        # Day 30 bands should be wider than day 1
        width_day1 = result["upper_95"][0] - result["lower_95"][0]
        width_day30 = result["upper_95"][-1] - result["lower_95"][-1]
        assert width_day30 > width_day1

    def test_band_ordering(self) -> None:
        """68% band should be within 95% band at all points."""
        values = [5.0 + 0.05 * i for i in range(30)]
        result = project_emission_trajectory(values, horizon_days=30)
        for i in range(30):
            assert result["lower_95"][i] <= result["lower_68"][i]
            assert result["upper_68"][i] <= result["upper_95"][i]

    def test_predicted_never_negative(self) -> None:
        """Projected emission share should never go below zero."""
        # Sharply declining emission
        values = [10.0 - 0.5 * i for i in range(30)]
        result = project_emission_trajectory(values, horizon_days=60)
        for v in result["predicted"]:
            assert v >= 0.0

    def test_momentum_returned(self) -> None:
        """Momentum value should be returned in result."""
        values = [2.0 + 0.1 * i for i in range(30)]
        result = project_emission_trajectory(values, horizon_days=30)
        assert "momentum" in result
        # Increasing emission should have positive momentum
        assert result["momentum"] > 0

    def test_output_length_matches_horizon(self) -> None:
        """Output lists should have exactly horizon_days entries."""
        values = [5.0] * 30
        result = project_emission_trajectory(values, horizon_days=45)
        assert len(result["predicted"]) == 45
        assert len(result["lower_68"]) == 45
        assert len(result["upper_68"]) == 45
        assert len(result["lower_95"]) == 45
        assert len(result["upper_95"]) == 45


class TestClassifyTrend:
    """Test trend classification from momentum."""

    def test_rising(self) -> None:
        assert classify_trend(0.05) == "rising"

    def test_falling(self) -> None:
        assert classify_trend(-0.05) == "falling"

    def test_stable_zero(self) -> None:
        assert classify_trend(0.0) == "stable"

    def test_stable_small_positive(self) -> None:
        assert classify_trend(0.005) == "stable"

    def test_stable_small_negative(self) -> None:
        assert classify_trend(-0.005) == "stable"


class TestComputeHalvingImpact:
    """Test halving countdown and network-level yield impact computation."""

    def test_blocks_remaining_positive(self) -> None:
        """Should compute positive blocks remaining when before halving."""
        result = compute_halving_impact(
            current_block=5_000_000,
            horizon_days=90,
        )
        assert result.blocks_remaining == HALVING_INTERVAL_BLOCKS - 5_000_000
        assert result.estimated_days_remaining > 0

    def test_post_halving_emission_is_half(self) -> None:
        """Post-halving daily emission should be half of current."""
        result = compute_halving_impact(
            current_block=5_000_000,
            horizon_days=90,
        )
        assert result.post_halving_emission_per_day_tao == pytest.approx(
            result.current_emission_per_day_tao / 2.0
        )

    def test_yield_impact_negative(self) -> None:
        """Halving should always have negative yield impact."""
        result = compute_halving_impact(
            current_block=5_000_000,
            horizon_days=90,
        )
        assert result.estimated_yield_impact_pct == -50.0
        assert result.estimated_yield_impact_tao < 0

    def test_yield_impact_is_network_level(self) -> None:
        """Yield impact TAO should equal half of daily emission * horizon."""
        result = compute_halving_impact(
            current_block=5_000_000,
            horizon_days=90,
        )
        current_daily = result.current_emission_per_day_tao
        expected = -(current_daily / 2.0) * 90
        assert result.estimated_yield_impact_tao == pytest.approx(expected, rel=1e-4)

    def test_days_remaining_calculation(self) -> None:
        """Days remaining should be blocks_remaining * 12 / 86400."""
        result = compute_halving_impact(
            current_block=5_000_000,
            horizon_days=90,
        )
        expected_days = (HALVING_INTERVAL_BLOCKS - 5_000_000) * 12 / 86400.0
        assert result.estimated_days_remaining == pytest.approx(expected_days, rel=0.01)

    def test_current_emission_per_day_pre_first_halving(self) -> None:
        """Before first halving, emission should be genesis rate."""
        result = compute_halving_impact(
            current_block=5_000_000,
            horizon_days=90,
        )
        # Block 5M is before first halving (10.5M), so 0 halvings passed
        assert result.current_emission_per_day_tao == pytest.approx(
            GENESIS_EMISSION_PER_BLOCK * BLOCKS_PER_DAY
        )

    def test_current_emission_per_day_post_first_halving(self) -> None:
        """After first halving, emission should be half of genesis rate."""
        result = compute_halving_impact(
            current_block=15_000_000,
            horizon_days=90,
        )
        # Block 15M is after first halving, so 1 halving passed
        assert result.current_emission_per_day_tao == pytest.approx(
            GENESIS_EMISSION_PER_BLOCK / 2 * BLOCKS_PER_DAY
        )

    def test_no_double_counting_halvings(self) -> None:
        """Emission rate after N halvings should be genesis / 2^N."""
        # After 2 halvings (block 25M)
        result = compute_halving_impact(
            current_block=25_000_000,
            horizon_days=90,
        )
        assert result.current_emission_per_day_tao == pytest.approx(
            GENESIS_EMISSION_PER_BLOCK / 4 * BLOCKS_PER_DAY
        )
