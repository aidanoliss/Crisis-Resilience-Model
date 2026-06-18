from __future__ import annotations

import unittest

import pandas as pd

from metrics import (
    beta_to_benchmark,
    correlation_to_benchmark,
    max_drawdown,
    total_return,
)


class MetricsTests(unittest.TestCase):
    def test_total_return_compounds_daily_returns(self) -> None:
        returns = pd.Series([0.10, -0.10, 0.05])
        self.assertAlmostEqual(total_return(returns), (1.10 * 0.90 * 1.05) - 1.0)

    def test_max_drawdown_includes_starting_wealth(self) -> None:
        returns = pd.Series([0.10, -0.20, 0.05])
        self.assertAlmostEqual(max_drawdown(returns), -0.20)

    def test_beta_and_correlation_to_benchmark(self) -> None:
        benchmark = pd.Series([0.01, 0.02, -0.01, -0.02])
        asset = benchmark * 2.0
        self.assertAlmostEqual(beta_to_benchmark(asset, benchmark), 2.0)
        self.assertAlmostEqual(correlation_to_benchmark(asset, benchmark), 1.0)


if __name__ == "__main__":
    unittest.main()
