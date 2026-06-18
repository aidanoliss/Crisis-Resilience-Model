"""Crisis resilience scoring logic."""

from __future__ import annotations

import numpy as np
import pandas as pd


DEFAULT_SCORE_WEIGHTS: dict[str, float] = {
    "return_score": 0.40,
    "drawdown_score": 0.25,
    "volatility_score": 0.20,
    "correlation_score": 0.15,
}


def score_assets(
    metrics: pd.DataFrame,
    weights: dict[str, float] | None = None,
    minimum_observations: int = 30,
) -> pd.DataFrame:
    """Rank assets with a transparent normalized crisis resilience score.

    Formula:
        100 * (
            40% normalized total return
          + 25% normalized drawdown protection
          + 20% normalized low volatility
          + 15% normalized low SPY correlation
        )

    Each component is scaled from 0 to 1 across the available assets.
    """

    if weights is None:
        weights = DEFAULT_SCORE_WEIGHTS

    scored = metrics.copy()
    eligible = scored["observations"] >= minimum_observations

    scored["return_score"] = _minmax(scored["total_return"], higher_is_better=True)
    scored["drawdown_score"] = _minmax(scored["max_drawdown"], higher_is_better=True)
    scored["volatility_score"] = _minmax(scored["volatility"], higher_is_better=False)
    scored["correlation_score"] = _minmax(
        scored["correlation_to_spy"], higher_is_better=False
    )

    weighted_sum = sum(scored[column] * weight for column, weight in weights.items())
    scored["crisis_resilience_score"] = 100.0 * weighted_sum
    scored.loc[~eligible, "crisis_resilience_score"] = np.nan

    scored = scored.sort_values(
        by="crisis_resilience_score", ascending=False, na_position="last"
    ).reset_index(drop=True)
    scored["rank"] = scored["crisis_resilience_score"].rank(
        ascending=False, method="min"
    )
    scored["rank"] = scored["rank"].astype("Int64")

    ordered_cols = [
        "rank",
        "ticker",
        "observations",
        "crisis_resilience_score",
        "return_score",
        "drawdown_score",
        "volatility_score",
        "correlation_score",
    ]
    remaining_cols = [col for col in scored.columns if col not in ordered_cols]
    return scored[ordered_cols + remaining_cols]


def _minmax(values: pd.Series, higher_is_better: bool) -> pd.Series:
    """Scale a metric to 0..1 and assign neutral 0.5 when no ranking is possible."""

    numeric = pd.to_numeric(values, errors="coerce")
    valid = numeric.dropna()
    result = pd.Series(np.nan, index=values.index, dtype=float)

    if valid.empty:
        return result.fillna(0.5)

    min_value = valid.min()
    max_value = valid.max()
    if np.isclose(max_value, min_value):
        result.loc[valid.index] = 0.5
        return result.fillna(0.5)

    scaled = (valid - min_value) / (max_value - min_value)
    if not higher_is_better:
        scaled = 1.0 - scaled

    result.loc[valid.index] = scaled
    return result.fillna(0.5)

