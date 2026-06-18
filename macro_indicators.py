"""Macro proxy analysis using market instruments already in the backtest.

This module intentionally starts with ETF proxies available in the core data
pipeline. That keeps the macro layer reliable without requiring another API.
Later, these proxies can be supplemented with FRED series and direct VIX/yield
data.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
import seaborn as sns

from crisis_periods import CRISIS_PERIODS, CrisisPeriod
from metrics import annualized_volatility, max_drawdown, total_return


MACRO_PROXY_MAP: dict[str, str] = {
    "SPY": "Equity risk appetite",
    "GLD": "Gold / safe haven",
    "USO": "Oil / energy inflation",
    "UUP": "Dollar liquidity",
    "TLT": "Long-duration Treasuries",
    "SHY": "Short-duration Treasuries",
    "XLE": "Energy equities",
    "XLF": "Financial conditions",
    "VNQ": "Rate-sensitive real estate",
    "XLP": "Defensive staples",
    "XLK": "Growth technology",
}


def build_macro_proxy_summary(
    prices: pd.DataFrame,
    periods: list[CrisisPeriod] = CRISIS_PERIODS,
) -> pd.DataFrame:
    """Calculate crisis-window behavior for macro proxies."""

    available = [ticker for ticker in MACRO_PROXY_MAP if ticker in prices.columns]
    if not available:
        return pd.DataFrame()

    returns = prices[available].pct_change(fill_method=None)
    rows: list[dict[str, float | str | int]] = []

    for period in periods:
        period_prices = prices.loc[
            (prices.index >= period.start_ts) & (prices.index <= period.end_ts), available
        ]
        period_returns = returns.loc[
            (returns.index >= period.start_ts) & (returns.index <= period.end_ts), available
        ]
        if period_returns.empty:
            continue

        for ticker in available:
            series = period_returns[ticker].dropna()
            price_series = period_prices[ticker].dropna()
            if series.empty or price_series.empty:
                continue

            rows.append(
                {
                    "crisis": period.name,
                    "ticker": ticker,
                    "macro_proxy": MACRO_PROXY_MAP[ticker],
                    "observations": int(series.shape[0]),
                    "total_return": total_return(series),
                    "annualized_volatility": annualized_volatility(series),
                    "max_drawdown": max_drawdown(series),
                    "start_level": float(price_series.iloc[0]),
                    "end_level": float(price_series.iloc[-1]),
                    "min_level": float(price_series.min()),
                    "max_level": float(price_series.max()),
                }
            )

    return pd.DataFrame(rows)


def build_macro_takeaways(summary: pd.DataFrame) -> pd.DataFrame:
    """Identify best and worst macro proxies in each crisis window."""

    if summary.empty:
        return pd.DataFrame()

    rows: list[dict[str, str | float]] = []
    for crisis, group in summary.groupby("crisis", sort=False):
        best = group.sort_values("total_return", ascending=False).head(3)
        worst = group.sort_values("total_return", ascending=True).head(3)
        rows.append(
            {
                "crisis": crisis,
                "strongest_macro_proxies": "; ".join(
                    f"{row.ticker} ({row.total_return:.0%})" for row in best.itertuples()
                ),
                "weakest_macro_proxies": "; ".join(
                    f"{row.ticker} ({row.total_return:.0%})" for row in worst.itertuples()
                ),
            }
        )
    return pd.DataFrame(rows)


def export_macro_proxy_tables(
    prices: pd.DataFrame,
    output_dir: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write macro proxy CSVs."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    summary = build_macro_proxy_summary(prices)
    takeaways = build_macro_takeaways(summary)
    summary.to_csv(output_path / "macro_proxy_crisis_summary.csv", index=False)
    takeaways.to_csv(output_path / "macro_proxy_takeaways.csv", index=False)
    return summary, takeaways


def plot_macro_proxy_heatmap(summary: pd.DataFrame, output_file: str | Path) -> Path:
    """Plot macro proxy returns by crisis."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if summary.empty:
        return output_path

    pivot = summary.pivot_table(index="crisis", columns="ticker", values="total_return")
    fig, ax = plt.subplots(figsize=(12, max(6, 0.55 * len(pivot))))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="RdYlGn",
        center=0,
        annot=True,
        fmt=".0%",
        linewidths=0.4,
        cbar_kws={"label": "Total return"},
    )
    ax.set_title("Macro Proxy Returns by Crisis Window")
    ax.set_xlabel("Macro proxy ticker")
    ax.set_ylabel("Crisis")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_macro_proxy_drawdown_heatmap(summary: pd.DataFrame, output_file: str | Path) -> Path:
    """Plot macro proxy max drawdowns by crisis."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if summary.empty:
        return output_path

    pivot = summary.pivot_table(index="crisis", columns="ticker", values="max_drawdown")
    fig, ax = plt.subplots(figsize=(12, max(6, 0.55 * len(pivot))))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="RdYlGn",
        center=0,
        annot=True,
        fmt=".0%",
        linewidths=0.4,
        cbar_kws={"label": "Max drawdown"},
    )
    ax.set_title("Macro Proxy Max Drawdowns by Crisis Window")
    ax.set_xlabel("Macro proxy ticker")
    ax.set_ylabel("Crisis")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_macro_proxy_cumulative_history(
    prices: pd.DataFrame,
    output_file: str | Path,
) -> Path:
    """Plot normalized history for macro proxies."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    available = [ticker for ticker in MACRO_PROXY_MAP if ticker in prices.columns]
    if not available:
        return output_path

    normalized = prices[available].dropna(how="all").copy()
    normalized = normalized / normalized.ffill().bfill().iloc[0] * 100.0

    fig, ax = plt.subplots(figsize=(13, 7))
    for column in normalized.columns:
        ax.plot(normalized.index, normalized[column], label=column, alpha=0.85)

    ax.set_title("Macro Proxy History, Normalized to 100")
    ax.set_xlabel("Date")
    ax.set_ylabel("Normalized level")
    ax.legend(ncol=3, fontsize=8)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def _percent_formatter(value: float, _position: int) -> str:
    return f"{value:.0%}"

