"""Performance and risk metrics used by the crisis backtest."""

from __future__ import annotations

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252


def total_return(returns: pd.Series) -> float:
    """Compounded return over the observed period."""

    clean = returns.dropna()
    if clean.empty:
        return np.nan
    return float((1.0 + clean).prod() - 1.0)


def annualized_return(
    returns: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    """Annualized compounded return based on daily observations."""

    clean = returns.dropna()
    if clean.empty:
        return np.nan

    compounded = (1.0 + clean).prod()
    if compounded <= 0:
        return -1.0
    return float(compounded ** (periods_per_year / len(clean)) - 1.0)


def annualized_volatility(
    returns: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> float:
    """Annualized standard deviation of daily returns."""

    clean = returns.dropna()
    if len(clean) < 2:
        return np.nan
    return float(clean.std(ddof=1) * np.sqrt(periods_per_year))


def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Annualized Sharpe ratio using a configurable annual risk-free rate."""

    ann_return = annualized_return(returns, periods_per_year)
    ann_vol = annualized_volatility(returns, periods_per_year)
    if pd.isna(ann_return) or pd.isna(ann_vol) or ann_vol == 0:
        return np.nan
    return float((ann_return - risk_free_rate) / ann_vol)


def max_drawdown(returns: pd.Series) -> float:
    """Worst peak-to-trough loss during the period."""

    clean = returns.dropna()
    if clean.empty:
        return np.nan

    wealth = (1.0 + clean).cumprod()
    wealth = pd.concat([pd.Series([1.0]), wealth], ignore_index=True)
    running_peak = wealth.cummax()
    drawdown = wealth / running_peak - 1.0
    return float(drawdown.min())


def downside_deviation(
    returns: pd.Series,
    minimum_acceptable_return: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Annualized downside deviation below a daily return threshold.

    This measures harmful volatility only. Positive-return days contribute 0.
    """

    clean = returns.dropna()
    if clean.empty:
        return np.nan

    downside = np.minimum(clean - minimum_acceptable_return, 0.0)
    return float(np.sqrt(np.mean(np.square(downside))) * np.sqrt(periods_per_year))


def beta_to_benchmark(asset_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Slope of asset returns versus benchmark returns."""

    aligned = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return np.nan

    asset = aligned.iloc[:, 0]
    benchmark = aligned.iloc[:, 1]
    benchmark_variance = benchmark.var(ddof=1)
    if benchmark_variance == 0 or pd.isna(benchmark_variance):
        return np.nan

    covariance = asset.cov(benchmark)
    return float(covariance / benchmark_variance)


def correlation_to_benchmark(asset_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Pearson correlation of asset returns to the benchmark."""

    aligned = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return np.nan
    return float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))


def compute_drawdowns(returns: pd.DataFrame) -> pd.DataFrame:
    """Compute drawdown time series for every asset column."""

    wealth = (1.0 + returns.fillna(0.0)).cumprod()
    running_peak = wealth.cummax()
    return wealth / running_peak - 1.0


def compute_cumulative_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """Compute cumulative returns from a daily return dataframe."""

    return (1.0 + returns.fillna(0.0)).cumprod() - 1.0


def compute_performance_metrics(
    returns: pd.DataFrame,
    benchmark_col: str = "SPY",
    risk_free_rate: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> pd.DataFrame:
    """Calculate crisis performance metrics for each asset."""

    if returns.empty:
        raise ValueError("Returns dataframe is empty.")
    if benchmark_col not in returns.columns:
        raise ValueError(f"Benchmark column '{benchmark_col}' is missing.")

    benchmark_returns = returns[benchmark_col]
    rows: list[dict[str, float | str | int]] = []

    for ticker in returns.columns:
        series = returns[ticker].dropna()
        rows.append(
            {
                "ticker": ticker,
                "observations": int(series.shape[0]),
                "total_return": total_return(series),
                "annualized_return": annualized_return(series, periods_per_year),
                "volatility": annualized_volatility(series, periods_per_year),
                "sharpe_ratio": sharpe_ratio(
                    series, risk_free_rate=risk_free_rate, periods_per_year=periods_per_year
                ),
                "max_drawdown": max_drawdown(series),
                "downside_deviation": downside_deviation(
                    series, periods_per_year=periods_per_year
                ),
                "beta_to_spy": beta_to_benchmark(series, benchmark_returns),
                "correlation_to_spy": correlation_to_benchmark(series, benchmark_returns),
            }
        )

    return pd.DataFrame(rows)

