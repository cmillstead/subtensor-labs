"""Tests for confidence interval computation."""

import numpy as np
import pytest

from engine.predictions.confidence import compute_confidence_bands


class TestComputeConfidenceBands:
    """Tests for compute_confidence_bands."""

    def test_linear_data_returns_correct_slope(self) -> None:
        """Perfect linear data should produce exact slope and intercept."""
        x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        y = np.array([1.0, 3.0, 5.0, 7.0, 9.0])  # y = 2x + 1
        x_pred = np.array([5.0, 6.0])

        result = compute_confidence_bands(x, y, x_pred)

        assert abs(result["slope"][0] - 2.0) < 1e-10
        assert abs(result["intercept"][0] - 1.0) < 1e-10
        assert abs(result["r_squared"][0] - 1.0) < 1e-10

    def test_predictions_are_correct_for_linear_data(self) -> None:
        """Predicted values should match the linear equation."""
        x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        y = np.array([1.0, 3.0, 5.0, 7.0, 9.0])
        x_pred = np.array([5.0, 10.0])

        result = compute_confidence_bands(x, y, x_pred)

        np.testing.assert_allclose(result["predicted"], [11.0, 21.0], atol=1e-10)

    def test_confidence_bands_widen_with_distance(self) -> None:
        """Confidence bands should be wider for predictions further from the data."""
        x = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
        rng = np.random.default_rng(42)
        y = 2.0 * x + 1.0 + rng.normal(0, 0.5, size=len(x))
        x_pred = np.array([8.0, 20.0])

        result = compute_confidence_bands(x, y, x_pred, confidence_levels=[0.95])

        width_near = result["upper_0.95"][0] - result["lower_0.95"][0]
        width_far = result["upper_0.95"][1] - result["lower_0.95"][1]
        assert width_far > width_near

    def test_95_band_wider_than_68_band(self) -> None:
        """95% confidence band should be wider than 68% band."""
        x = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
        rng = np.random.default_rng(42)
        y = 2.0 * x + 1.0 + rng.normal(0, 0.5, size=len(x))
        x_pred = np.array([10.0])

        result = compute_confidence_bands(x, y, x_pred, confidence_levels=[0.68, 0.95])

        width_68 = result["upper_0.68"][0] - result["lower_0.68"][0]
        width_95 = result["upper_0.95"][0] - result["lower_0.95"][0]
        assert width_95 > width_68

    def test_raises_on_insufficient_data(self) -> None:
        """Should raise ValueError with fewer than 3 data points."""
        x = np.array([0.0, 1.0])
        y = np.array([1.0, 2.0])
        x_pred = np.array([3.0])

        with pytest.raises(ValueError, match="at least 3"):
            compute_confidence_bands(x, y, x_pred)

    def test_raises_on_identical_x_values(self) -> None:
        """Should raise ValueError when all x values are the same."""
        x = np.array([1.0, 1.0, 1.0])
        y = np.array([2.0, 3.0, 4.0])
        x_pred = np.array([2.0])

        with pytest.raises(ValueError, match="identical"):
            compute_confidence_bands(x, y, x_pred)

    def test_custom_confidence_levels(self) -> None:
        """Should compute bands for custom confidence levels."""
        x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        rng = np.random.default_rng(42)
        y = x + rng.normal(0, 0.1, size=len(x))
        x_pred = np.array([5.0])

        result = compute_confidence_bands(x, y, x_pred, confidence_levels=[0.50, 0.99])

        assert "lower_0.5" in result
        assert "upper_0.5" in result
        assert "lower_0.99" in result
        assert "upper_0.99" in result

    def test_prediction_contains_within_confidence(self) -> None:
        """Predicted value should be within all confidence bands."""
        x = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        rng = np.random.default_rng(42)
        y = 3.0 * x + 2.0 + rng.normal(0, 0.3, size=len(x))
        x_pred = np.array([8.0])

        result = compute_confidence_bands(x, y, x_pred, confidence_levels=[0.68, 0.95])

        pred = result["predicted"][0]
        assert result["lower_0.68"][0] <= pred <= result["upper_0.68"][0]
        assert result["lower_0.95"][0] <= pred <= result["upper_0.95"][0]
