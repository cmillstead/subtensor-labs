"""Shared confidence interval computation for prediction models."""

import numpy as np
from numpy.typing import NDArray
from scipy.stats import t as t_dist


def compute_confidence_bands(
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    x_pred: NDArray[np.float64],
    confidence_levels: list[float] | None = None,
) -> dict[str, NDArray[np.float64]]:
    """Compute linear regression prediction with confidence bands.

    Args:
        x: Historical time values (e.g., day indices).
        y: Historical observed values (e.g., emission_share_pct).
        x_pred: Future time values to predict.
        confidence_levels: Confidence levels for bands (default [0.68, 0.95]).

    Returns:
        Dictionary with keys:
          - "predicted": predicted values at x_pred
          - "slope": regression slope
          - "intercept": regression intercept
          - "r_squared": coefficient of determination
          - For each confidence level (e.g., "lower_0.68", "upper_0.68"):
              lower and upper bounds at x_pred
    """
    if confidence_levels is None:
        confidence_levels = [0.68, 0.95]

    n = len(x)
    if n < 3:
        raise ValueError(f"Need at least 3 data points for regression, got {n}")

    # Linear regression via least squares
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    ss_x = np.sum((x - x_mean) ** 2)

    if ss_x == 0:
        raise ValueError("All x values are identical — cannot fit regression")

    slope = np.sum((x - x_mean) * (y - y_mean)) / ss_x
    intercept = y_mean - slope * x_mean

    # Predicted values
    y_hat = intercept + slope * x
    predicted = intercept + slope * x_pred

    # Residual standard error
    residuals = y - y_hat
    mse = np.sum(residuals**2) / (n - 2)
    se_residual = np.sqrt(mse)

    # R-squared
    ss_tot = np.sum((y - y_mean) ** 2)
    r_squared = float(1.0 - np.sum(residuals**2) / ss_tot) if ss_tot > 0 else 0.0

    result: dict[str, NDArray[np.float64]] = {
        "predicted": predicted,
        "slope": np.array([float(slope)]),
        "intercept": np.array([float(intercept)]),
        "r_squared": np.array([r_squared]),
    }

    # Prediction interval standard error for each x_pred point
    for level in confidence_levels:
        se_pred = se_residual * np.sqrt(1 + 1 / n + (x_pred - x_mean) ** 2 / ss_x)
        t_val = t_dist.ppf((1 + level) / 2, df=n - 2)
        margin = t_val * se_pred

        key_lower = f"lower_{level}"
        key_upper = f"upper_{level}"
        result[key_lower] = predicted - margin
        result[key_upper] = predicted + margin

    return result
