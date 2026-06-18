from __future__ import annotations

import unittest

import pandas as pd

from scoring import score_assets


class ScoringTests(unittest.TestCase):
    def test_score_assets_ranks_more_resilient_asset_first(self) -> None:
        metrics = pd.DataFrame(
            [
                {
                    "ticker": "WEAK",
                    "observations": 100,
                    "total_return": -0.30,
                    "max_drawdown": -0.45,
                    "volatility": 0.30,
                    "correlation_to_spy": 0.95,
                },
                {
                    "ticker": "STRONG",
                    "observations": 100,
                    "total_return": 0.08,
                    "max_drawdown": -0.04,
                    "volatility": 0.05,
                    "correlation_to_spy": -0.20,
                },
            ]
        )

        scored = score_assets(metrics)
        self.assertEqual(scored.iloc[0]["ticker"], "STRONG")
        self.assertGreater(
            scored.iloc[0]["crisis_resilience_score"],
            scored.iloc[1]["crisis_resilience_score"],
        )

    def test_score_assets_marks_low_observation_assets_unranked(self) -> None:
        metrics = pd.DataFrame(
            [
                {
                    "ticker": "SHORT",
                    "observations": 5,
                    "total_return": 1.0,
                    "max_drawdown": 0.0,
                    "volatility": 0.01,
                    "correlation_to_spy": -1.0,
                }
            ]
        )

        scored = score_assets(metrics, minimum_observations=30)
        self.assertTrue(pd.isna(scored.iloc[0]["crisis_resilience_score"]))


if __name__ == "__main__":
    unittest.main()
