"""Crisis early warning monitor built from liquid market proxies."""

from __future__ import annotations

import os
from pathlib import Path
from datetime import date

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


INDICATOR_CONFIG: list[dict[str, str]] = [
    {
        "indicator": "Equity drawdown",
        "ticker": "SPY",
        "signal": "drawdown_252d",
        "description": "S&P 500 drawdown from one-year high.",
    },
    {
        "indicator": "Equity volatility",
        "ticker": "SPY",
        "signal": "realized_vol_21d",
        "description": "Annualized 21-day realized equity volatility.",
    },
    {
        "indicator": "Dollar liquidity stress",
        "ticker": "UUP",
        "signal": "return_63d",
        "description": "Three-month U.S. dollar proxy momentum.",
    },
    {
        "indicator": "Oil shock",
        "ticker": "USO",
        "signal": "return_63d",
        "description": "Three-month oil proxy momentum.",
    },
    {
        "indicator": "Duration shock",
        "ticker": "TLT",
        "signal": "return_63d",
        "description": "Three-month long Treasury return.",
    },
    {
        "indicator": "Financial stress",
        "ticker": "XLF",
        "signal": "return_63d",
        "description": "Three-month financial-sector return.",
    },
    {
        "indicator": "Real estate stress",
        "ticker": "VNQ",
        "signal": "return_63d",
        "description": "Three-month real estate return.",
    },
    {
        "indicator": "Safe-haven bid",
        "ticker": "GLD",
        "signal": "return_63d",
        "description": "Three-month gold proxy momentum.",
    },
    {
        "indicator": "Growth technology stress",
        "ticker": "XLK",
        "signal": "return_63d",
        "description": "Three-month technology-sector return.",
    },
]


def build_early_warning_monitor(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build current regime indicators from the latest available prices."""

    if prices.empty:
        return pd.DataFrame(), pd.DataFrame()

    returns = prices.pct_change(fill_method=None)
    rows: list[dict[str, float | str]] = []
    latest_date = prices.dropna(how="all").index.max()

    for config in INDICATOR_CONFIG:
        ticker = config["ticker"]
        if ticker not in prices.columns:
            continue

        price = prices[ticker].dropna()
        ticker_returns = returns[ticker].dropna()
        if price.empty or ticker_returns.empty:
            continue

        metrics = _latest_metrics(price, ticker_returns)
        signal_value = metrics[config["signal"]]
        stress_score, level, interpretation = _score_indicator(
            config["indicator"], signal_value
        )
        rows.append(
            {
                "latest_date": latest_date.date().isoformat(),
                "indicator": config["indicator"],
                "ticker": ticker,
                "signal": config["signal"],
                "signal_value": signal_value,
                "stress_score": stress_score,
                "stress_level": level,
                "description": config["description"],
                "interpretation": interpretation,
                "price_latest": metrics["price_latest"],
                "return_21d": metrics["return_21d"],
                "return_63d": metrics["return_63d"],
                "drawdown_252d": metrics["drawdown_252d"],
                "realized_vol_21d": metrics["realized_vol_21d"],
            }
        )

    indicators = pd.DataFrame(rows)
    if indicators.empty:
        return indicators, pd.DataFrame()

    average_score = float(indicators["stress_score"].mean())
    max_score = float(indicators["stress_score"].max())
    regime_score = 0.65 * average_score + 0.35 * max_score
    regime = _regime_from_score(regime_score)
    active_alerts = indicators[indicators["stress_level"].isin(["Stress", "Crisis"])]
    latest = pd.Timestamp(indicators["latest_date"].iloc[0]).date()
    data_age_days = (date.today() - latest).days
    summary = pd.DataFrame(
        [
            {
                "latest_date": indicators["latest_date"].iloc[0],
                "data_age_days": data_age_days,
                "data_freshness": "Fresh" if data_age_days <= 3 else "Stale",
                "regime": regime,
                "regime_score": regime_score,
                "average_indicator_score": average_score,
                "max_indicator_score": max_score,
                "active_alert_count": int(active_alerts.shape[0]),
                "primary_alerts": "; ".join(active_alerts["indicator"].head(5).tolist()),
                "interpretation": _regime_interpretation(regime),
            }
        ]
    )
    return indicators, summary


def export_early_warning_monitor(
    prices: pd.DataFrame,
    output_dir: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write early-warning CSVs."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    indicators, summary = build_early_warning_monitor(prices)
    indicators.to_csv(output_path / "early_warning_indicators.csv", index=False)
    summary.to_csv(output_path / "early_warning_summary.csv", index=False)
    return indicators, summary


def plot_early_warning_scores(indicators: pd.DataFrame, output_file: str | Path) -> Path:
    """Plot current stress scores by indicator."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if indicators.empty:
        return output_path

    data = indicators.sort_values("stress_score")
    colors = data["stress_score"].map(_score_color)
    fig, ax = plt.subplots(figsize=(12, max(5, 0.45 * len(data))))
    ax.barh(data["indicator"], data["stress_score"], color=colors)
    ax.axvline(25, color="#84cc16", linewidth=0.8, linestyle="--")
    ax.axvline(50, color="#f59e0b", linewidth=0.8, linestyle="--")
    ax.axvline(75, color="#dc2626", linewidth=0.8, linestyle="--")
    ax.set_xlim(0, 100)
    ax.set_title("Crisis Early Warning Stress Scores")
    ax.set_xlabel("Stress score, 0-100")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_regime_gauge(summary: pd.DataFrame, output_file: str | Path) -> Path:
    """Plot a simple regime score gauge."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if summary.empty:
        return output_path

    score = float(summary["regime_score"].iloc[0])
    regime = str(summary["regime"].iloc[0])
    fig, ax = plt.subplots(figsize=(11, 2.8))
    ax.barh(["Regime"], [100], color="#e5e7eb")
    ax.barh(["Regime"], [score], color=_score_color(score))
    for value, label in [(25, "Watch"), (50, "Stress"), (75, "Crisis")]:
        ax.axvline(value, color="black", linewidth=0.8)
        ax.text(value, 0.25, label, ha="center", va="bottom", fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_title(f"Current Market Regime: {regime} ({score:.1f}/100)")
    ax.set_xlabel("Regime stress score")
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def _latest_metrics(price: pd.Series, returns: pd.Series) -> dict[str, float]:
    price_latest = float(price.iloc[-1])
    return_21d = _period_return(price, 21)
    return_63d = _period_return(price, 63)
    high_252d = float(price.tail(252).max())
    drawdown_252d = price_latest / high_252d - 1.0 if high_252d else 0.0
    realized_vol_21d = float(returns.tail(21).std() * (252 ** 0.5))
    return {
        "price_latest": price_latest,
        "return_21d": return_21d,
        "return_63d": return_63d,
        "drawdown_252d": drawdown_252d,
        "realized_vol_21d": realized_vol_21d,
    }


def _period_return(price: pd.Series, days: int) -> float:
    if len(price) <= days:
        return float(price.iloc[-1] / price.iloc[0] - 1.0)
    return float(price.iloc[-1] / price.iloc[-days - 1] - 1.0)


def _score_indicator(indicator: str, value: float) -> tuple[int, str, str]:
    if indicator == "Equity drawdown":
        score = _score_negative(value, [-0.05, -0.10, -0.20])
        message = "Equity drawdown is measuring broad risk appetite."
    elif indicator == "Equity volatility":
        score = _score_positive(value, [0.18, 0.28, 0.40])
        message = "Realized volatility is measuring equity market instability."
    elif indicator == "Dollar liquidity stress":
        score = _score_positive(value, [0.02, 0.05, 0.10])
        message = "Dollar strength can signal global funding stress."
    elif indicator == "Oil shock":
        score = _score_positive(value, [0.10, 0.25, 0.40])
        message = "Oil spikes can transmit into inflation and consumer stress."
    elif indicator == "Duration shock":
        score = _score_negative(value, [-0.05, -0.10, -0.20])
        message = "Long-duration Treasury losses can indicate rate shock pressure."
    elif indicator in {"Financial stress", "Real estate stress", "Growth technology stress"}:
        score = _score_negative(value, [-0.05, -0.12, -0.25])
        message = f"{indicator} is measuring sector-level stress."
    elif indicator == "Safe-haven bid":
        score = _score_positive(value, [0.05, 0.10, 0.18])
        message = "Gold strength can signal safe-haven demand."
    else:
        score = 0
        message = "No scoring rule configured."

    return score, _regime_from_score(score), message


def _score_negative(value: float, thresholds: list[float]) -> int:
    if value <= thresholds[2]:
        return 100
    if value <= thresholds[1]:
        return 70
    if value <= thresholds[0]:
        return 40
    return 10


def _score_positive(value: float, thresholds: list[float]) -> int:
    if value >= thresholds[2]:
        return 100
    if value >= thresholds[1]:
        return 70
    if value >= thresholds[0]:
        return 40
    return 10


def _regime_from_score(score: float) -> str:
    if score >= 75:
        return "Crisis"
    if score >= 50:
        return "Stress"
    if score >= 25:
        return "Watch"
    return "Normal"


def _regime_interpretation(regime: str) -> str:
    if regime == "Crisis":
        return "Multiple market proxies are flashing crisis conditions. Review liquidity, hedges, and concentrated exposures."
    if regime == "Stress":
        return "Several market proxies are stressed. Defensive positioning and scenario review are warranted."
    if regime == "Watch":
        return "Some warning signals are elevated. Monitor changes and portfolio sensitivity."
    return "Market proxies are not currently signaling broad crisis conditions."


def _score_color(score: float) -> str:
    if score >= 75:
        return "#b91c1c"
    if score >= 50:
        return "#f97316"
    if score >= 25:
        return "#facc15"
    return "#16a34a"
