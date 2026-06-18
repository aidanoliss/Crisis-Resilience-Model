"""Unified crisis alert layer.

This module combines market-proxy warnings, direct FRED macro thresholds,
headline classifications, and calibrated scenario weights into one audit-friendly
alert feed.
"""

from __future__ import annotations

from datetime import date
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


LEVEL_ORDER = {
    "De-escalation": -1,
    "Normal": 0,
    "Watch": 1,
    "Stress": 2,
    "Crisis": 3,
}


def export_unified_alerts(
    output_dir: str | Path,
    early_warning_indicators: pd.DataFrame,
    fred_alerts: pd.DataFrame,
    news_alerts: pd.DataFrame,
    calibrated_scenarios: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build and export unified alert feed and summary."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    alerts = build_unified_alerts(
        early_warning_indicators=early_warning_indicators,
        fred_alerts=fred_alerts,
        news_alerts=news_alerts,
        calibrated_scenarios=calibrated_scenarios,
    )
    summary = build_alert_summary(alerts)
    alerts.to_csv(output_path / "alerts.csv", index=False)
    summary.to_csv(output_path / "alerts_summary.csv", index=False)
    return alerts, summary


def build_unified_alerts(
    early_warning_indicators: pd.DataFrame,
    fred_alerts: pd.DataFrame,
    news_alerts: pd.DataFrame,
    calibrated_scenarios: pd.DataFrame,
) -> pd.DataFrame:
    """Combine current alerts from all available model layers."""

    rows: list[dict[str, str | float | int]] = []
    today = date.today().isoformat()

    if not early_warning_indicators.empty:
        active = early_warning_indicators[
            early_warning_indicators["stress_level"].isin(["Watch", "Stress", "Crisis"])
        ]
        for row in active.itertuples():
            rows.append(
                {
                    "as_of": today,
                    "source": "Market proxies",
                    "category": row.indicator,
                    "level": row.stress_level,
                    "score": float(row.stress_score),
                    "signal": row.signal,
                    "evidence": f"{row.ticker} signal value {float(row.signal_value):.4f}",
                    "message": row.interpretation,
                    "recommended_review": _review_action(str(row.indicator)),
                }
            )

    if not fred_alerts.empty:
        for row in fred_alerts.itertuples():
            rows.append(
                {
                    "as_of": today,
                    "source": "FRED macro",
                    "category": row.category,
                    "level": row.stress_level,
                    "score": float(row.stress_score),
                    "signal": row.signal,
                    "evidence": f"{row.series_id} latest {float(row.latest_value):.2f}",
                    "message": row.message,
                    "recommended_review": _review_action(str(row.category)),
                }
            )

    if not news_alerts.empty:
        for row in news_alerts.itertuples():
            rows.append(
                {
                    "as_of": today,
                    "source": "News sentiment",
                    "category": row.category,
                    "level": row.stress_level,
                    "score": float(row.stress_score),
                    "signal": f"{int(row.headline_count)} classified headlines",
                    "evidence": row.top_titles,
                    "message": row.message,
                    "recommended_review": _review_action(str(row.category)),
                }
            )

    if not calibrated_scenarios.empty:
        active_scenarios = calibrated_scenarios[
            calibrated_scenarios["calibrated_probability_weight"] >= 0.35
        ]
        for row in active_scenarios.itertuples():
            level = "Stress" if float(row.calibrated_probability_weight) >= 0.50 else "Watch"
            rows.append(
                {
                    "as_of": today,
                    "source": "Scenario calibration",
                    "category": row.scenario,
                    "level": level,
                    "score": float(row.calibrated_probability_weight) * 100.0,
                    "signal": "Calibrated scenario weight threshold",
                    "evidence": row.active_calibration_signals,
                    "message": (
                        f"{row.scenario} calibrated weight is "
                        f"{float(row.calibrated_probability_weight):.0%}."
                    ),
                    "recommended_review": "Review portfolio exposure, scenario playbook, and hedge sizing.",
                }
            )

    if not rows:
        return _empty_alerts()

    alerts = pd.DataFrame(rows)
    alerts["level_rank"] = alerts["level"].map(LEVEL_ORDER).fillna(0).astype(int)
    return alerts.sort_values(["level_rank", "score"], ascending=False).drop(columns=["level_rank"])


def build_alert_summary(alerts: pd.DataFrame) -> pd.DataFrame:
    """Summarize alert state for the dashboard and reports."""

    if alerts.empty:
        return pd.DataFrame(
            [
                {
                    "as_of": date.today().isoformat(),
                    "highest_level": "Normal",
                    "active_alert_count": 0,
                    "average_score": 0.0,
                    "top_categories": "",
                    "interpretation": "No active alert rows were generated from available data.",
                }
            ]
        )

    level_rank = alerts["level"].map(LEVEL_ORDER).fillna(0)
    highest_level = alerts.loc[level_rank.idxmax(), "level"]
    top_categories = "; ".join(alerts.head(6)["category"].astype(str).tolist())
    average_score = float(pd.to_numeric(alerts["score"], errors="coerce").fillna(0).mean())
    return pd.DataFrame(
        [
            {
                "as_of": date.today().isoformat(),
                "highest_level": highest_level,
                "active_alert_count": int(alerts.shape[0]),
                "average_score": average_score,
                "top_categories": top_categories,
                "interpretation": _summary_interpretation(str(highest_level)),
            }
        ]
    )


def plot_unified_alerts(alerts: pd.DataFrame, output_file: str | Path) -> Path:
    """Plot strongest current alerts by category."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if alerts.empty:
        return output_path

    data = (
        alerts.assign(score_numeric=pd.to_numeric(alerts["score"], errors="coerce").fillna(0))
        .groupby("category", as_index=False)["score_numeric"]
        .max()
        .sort_values("score_numeric")
    )
    colors = data["score_numeric"].map(_score_color)
    fig, ax = plt.subplots(figsize=(12, max(5, 0.45 * len(data))))
    ax.barh(data["category"], data["score_numeric"], color=colors)
    for value in [40, 70, 90]:
        ax.axvline(value, color="#111827", linewidth=0.8, linestyle="--", alpha=0.75)
    ax.set_title("Unified Crisis Alert Scores")
    ax.set_xlabel("Alert score")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def _review_action(category: str) -> str:
    normalized = category.lower()
    if "oil" in normalized or "supply" in normalized or "inflation" in normalized:
        return "Review energy, commodities, consumer-margin exposure, and inflation hedges."
    if "credit" in normalized or "liquidity" in normalized or "financial" in normalized:
        return "Review cash, Treasury duration, credit exposure, banks, and funding-sensitive holdings."
    if "rate" in normalized or "duration" in normalized:
        return "Review duration exposure, rate-sensitive equities, real estate, and leverage."
    if "geopolitical" in normalized or "taiwan" in normalized or "middle east" in normalized:
        return "Review defense, energy, semiconductor, shipping, and geopolitical concentration exposures."
    if "cyber" in normalized:
        return "Review cybersecurity exposure and operational continuity assumptions."
    if "technology" in normalized or "ai" in normalized:
        return "Review mega-cap technology concentration and semiconductor supply-chain exposure."
    return "Review related portfolio exposure and scenario assumptions."


def _summary_interpretation(level: str) -> str:
    if level == "Crisis":
        return "One or more indicators are in crisis territory; run portfolio stress and review liquidity immediately."
    if level == "Stress":
        return "Stress conditions are present across at least one model layer; review active scenario exposures."
    if level == "Watch":
        return "Some indicators are elevated; monitor changes and refresh data frequently."
    if level == "De-escalation":
        return "News flow contains de-escalation language; verify whether market stress indicators are confirming."
    return "No active alert rows were generated from available data."


def _score_color(score: float) -> str:
    if score >= 90:
        return "#b91c1c"
    if score >= 70:
        return "#f97316"
    if score >= 40:
        return "#facc15"
    return "#16a34a"


def _empty_alerts() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "as_of",
            "source",
            "category",
            "level",
            "score",
            "signal",
            "evidence",
            "message",
            "recommended_review",
        ]
    )
