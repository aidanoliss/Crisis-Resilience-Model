from __future__ import annotations

import unittest

import pandas as pd

from forecast_playbook import build_crisis_category_forecast


class ForecastPlaybookTests(unittest.TestCase):
    def test_forecast_maps_semiconductor_shock_to_vulnerability(self) -> None:
        exposures = pd.DataFrame(
            [
                {
                    "scenario": "China attacks Taiwan",
                    "bucket": "Sector/ETF",
                    "ticker_or_theme": "SOXX/SMH",
                    "name": "Semiconductor ETFs",
                    "impact_score": -5,
                    "rationale": "Advanced chip supply interruption.",
                    "severity_score": 5,
                },
                {
                    "scenario": "China attacks Taiwan",
                    "bucket": "Resource",
                    "ticker_or_theme": "GLD",
                    "name": "Gold",
                    "impact_score": 4,
                    "rationale": "Safe-haven demand.",
                    "severity_score": 5,
                },
            ]
        )
        calibrated = pd.DataFrame(
            [
                {
                    "scenario": "China attacks Taiwan",
                    "base_probability_weight": 0.12,
                    "calibrated_probability_weight": 0.20,
                    "severity_score": 5,
                }
            ]
        )
        resilience = pd.DataFrame(
            [
                {"ticker": "XLK", "crisis_resilience_score": 15},
                {"ticker": "GLD", "crisis_resilience_score": 80},
                {"ticker": "UUP", "crisis_resilience_score": 90},
                {"ticker": "SHY", "crisis_resilience_score": 88},
                {"ticker": "TLT", "crisis_resilience_score": 85},
            ]
        )

        forecast = build_crisis_category_forecast(exposures, calibrated, resilience)
        semi = forecast[forecast["forecast_category"] == "Semiconductors and hardware"].iloc[0]
        haven = forecast[forecast["forecast_category"] == "Safe-haven liquidity"].iloc[0]

        self.assertLess(semi["expected_resilience_score"], 0)
        self.assertGreater(haven["expected_resilience_score"], 0)


if __name__ == "__main__":
    unittest.main()
