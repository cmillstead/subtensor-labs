"""Tests for yield projector — projection math with known emission data."""

from datetime import UTC, datetime, timedelta

from engine.predictions.yield_projector import _project_subnet_yield
from engine.schemas.predictions import YieldProjectionResponseSchema


class TestProjectSubnetYield:
    """Test the per-subnet yield projection math."""

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

    def test_basic_projection_returns_correct_horizons(self) -> None:
        """Should return projections for each requested horizon."""
        history = self._make_emission_history(days=30)
        projections, chart_data, has_warning = _project_subnet_yield(
            emission_history=history,
            stake_tao=100.0,
            take_rate=0.1,
            horizons=[30, 60, 90],
        )

        assert len(projections) == 3
        assert projections[0].netuid == 0  # Placeholder, set by caller
        assert len(chart_data) == 90  # Max horizon

    def test_increasing_emission_yields_positive_projection(self) -> None:
        """Increasing emission trend should produce positive yield projections."""
        history = self._make_emission_history(days=30, base_emission=5.0, daily_change=0.1)
        projections, _, _ = _project_subnet_yield(
            emission_history=history,
            stake_tao=100.0,
            take_rate=0.0,
            horizons=[30],
        )

        assert projections[0].projected_yield_tao > 0
        assert projections[0].emission_trend_slope > 0

    def test_take_rate_reduces_yield(self) -> None:
        """Higher validator take rate should reduce yield."""
        history = self._make_emission_history(days=30, base_emission=5.0, daily_change=0.05)

        proj_no_take, _, _ = _project_subnet_yield(
            emission_history=history, stake_tao=100.0, take_rate=0.0, horizons=[30]
        )
        proj_with_take, _, _ = _project_subnet_yield(
            emission_history=history, stake_tao=100.0, take_rate=0.2, horizons=[30]
        )

        assert proj_with_take[0].projected_yield_tao < proj_no_take[0].projected_yield_tao

    def test_more_stake_increases_yield(self) -> None:
        """More staked TAO should increase yield proportionally."""
        history = self._make_emission_history(days=30, base_emission=5.0, daily_change=0.05)

        proj_100, _, _ = _project_subnet_yield(
            emission_history=history, stake_tao=100.0, take_rate=0.0, horizons=[30]
        )
        proj_200, _, _ = _project_subnet_yield(
            emission_history=history, stake_tao=200.0, take_rate=0.0, horizons=[30]
        )

        ratio = proj_200[0].projected_yield_tao / proj_100[0].projected_yield_tao
        assert abs(ratio - 2.0) < 0.01

    def test_volatility_warning_for_young_subnet(self) -> None:
        """Subnets with <60 days data should have volatility warning."""
        history = self._make_emission_history(days=30)  # Less than 60
        projections, _, has_warning = _project_subnet_yield(
            emission_history=history, stake_tao=100.0, take_rate=0.0, horizons=[30]
        )

        assert has_warning is True
        assert projections[0].has_volatility_warning is True

    def test_no_volatility_warning_for_mature_subnet(self) -> None:
        """Subnets with >=60 days data should not have volatility warning."""
        history = self._make_emission_history(days=70)  # More than 60
        projections, _, has_warning = _project_subnet_yield(
            emission_history=history, stake_tao=100.0, take_rate=0.0, horizons=[30]
        )

        assert has_warning is False
        assert projections[0].has_volatility_warning is False

    def test_longer_horizon_yields_more(self) -> None:
        """Longer projection horizon should generally project more yield."""
        history = self._make_emission_history(days=30, base_emission=5.0, daily_change=0.05)
        projections, _, _ = _project_subnet_yield(
            emission_history=history, stake_tao=100.0, take_rate=0.0, horizons=[30, 60, 90]
        )

        assert projections[2].projected_yield_tao > projections[1].projected_yield_tao
        assert projections[1].projected_yield_tao > projections[0].projected_yield_tao

    def test_confidence_bands_ordered(self) -> None:
        """68% band should be within 95% band."""
        history = self._make_emission_history(days=30, base_emission=5.0, daily_change=0.05)
        projections, _, _ = _project_subnet_yield(
            emission_history=history, stake_tao=100.0, take_rate=0.0, horizons=[30]
        )

        proj = projections[0]
        assert proj.confidence_95_lower <= proj.confidence_68_lower
        assert proj.confidence_68_upper <= proj.confidence_95_upper

    def test_chart_data_length_matches_max_horizon(self) -> None:
        """Chart data should have one point per day up to max horizon."""
        history = self._make_emission_history(days=30)
        _, chart_data, _ = _project_subnet_yield(
            emission_history=history, stake_tao=100.0, take_rate=0.0, horizons=[30, 60]
        )

        assert len(chart_data) == 60
        assert chart_data[0].day == 1
        assert chart_data[-1].day == 60

    def test_r_squared_close_to_one_for_linear_data(self) -> None:
        """Perfect linear emission should produce R² ≈ 1."""
        history = self._make_emission_history(days=30, base_emission=2.0, daily_change=0.1)
        projections, _, _ = _project_subnet_yield(
            emission_history=history, stake_tao=100.0, take_rate=0.0, horizons=[30]
        )

        assert projections[0].r_squared > 0.99


class TestYieldProjectionResponseSchema:
    """Test response schema serialization."""

    def test_roundtrip_serialization(self) -> None:
        """Response should serialize and deserialize correctly."""
        from engine.schemas.predictions import (
            HorizonProjectionSchema,
            SubnetYieldProjectionSchema,
            YieldChartPointSchema,
        )

        response = YieldProjectionResponseSchema(
            projections=[
                HorizonProjectionSchema(
                    horizon_days=30,
                    total_projected_yield_tao=10.5,
                    total_confidence_68_lower=8.0,
                    total_confidence_68_upper=13.0,
                    total_confidence_95_lower=5.0,
                    total_confidence_95_upper=16.0,
                    subnet_projections=[
                        SubnetYieldProjectionSchema(
                            netuid=1,
                            subnet_name="alpha",
                            current_stake_tao=100.0,
                            projected_yield_tao=10.5,
                            emission_trend_slope=0.01,
                            r_squared=0.95,
                            confidence_68_lower=8.0,
                            confidence_68_upper=13.0,
                            confidence_95_lower=5.0,
                            confidence_95_upper=16.0,
                            has_volatility_warning=False,
                        )
                    ],
                )
            ],
            chart_data=[
                YieldChartPointSchema(
                    day=1,
                    projected_yield_tao=0.35,
                    confidence_68_lower=0.27,
                    confidence_68_upper=0.43,
                    confidence_95_lower=0.17,
                    confidence_95_upper=0.53,
                )
            ],
            last_computed="2026-03-16T00:00:00Z",
            total_staked_tao=100.0,
            subnets_analyzed=1,
            subnets_skipped=0,
        )

        json_str = response.model_dump_json()
        restored = YieldProjectionResponseSchema.model_validate_json(json_str)

        assert restored.projections[0].horizon_days == 30
        assert restored.total_staked_tao == 100.0
        assert restored.subnets_analyzed == 1
