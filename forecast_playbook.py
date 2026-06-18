"""Forward crisis category resilience forecast playbook.

This module converts the detailed scenario assumptions into a higher-level
forecast matrix: for each possible future crisis, which categories are expected
to be resilient, vulnerable, or path-dependent.

The scores are not predictions of returns. They are planning scores derived from
scenario impacts, calibrated scenario weights, and historical crisis resilience.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


CATEGORY_TICKERS: dict[str, list[str]] = {
    "Safe-haven liquidity": ["UUP", "SHY", "TLT", "GLD"],
    "Energy and resource security": ["USO", "XLE", "XLB", "GLD"],
    "Defense and aerospace": [],
    "Cybersecurity and infrastructure": [],
    "Semiconductors and hardware": ["XLK"],
    "Broad technology and AI": ["XLK", "XLC"],
    "Financials and credit": ["XLF"],
    "Real estate and rate-sensitive assets": ["VNQ", "XLU"],
    "Defensive equity sectors": ["XLP", "XLU", "XLV"],
    "Consumer cyclicals and travel": ["XLY"],
    "Industrials and logistics": ["XLI"],
}


CRISIS_FAMILY_MAP: dict[str, str] = {
    "China attacks Taiwan": "Pacific war / semiconductor shock",
    "China blockades Taiwan": "Pacific blockade / supply-chain shock",
    "U.S. expands war in the Middle East": "Middle East war / oil shock",
    "Strait of Hormuz closure": "Energy chokepoint / oil shock",
    "U.S. debt or Treasury liquidity scare": "Sovereign liquidity / rates shock",
    "Regional bank and commercial real estate shock": "Banking / credit shock",
    "Pandemic 2.0": "Pandemic / growth shock",
    "Inflation resurgence and second rate shock": "Inflation / rates shock",
    "Cyberattack on U.S. financial infrastructure": "Cyber / market plumbing shock",
    "AI mega-cap unwind": "Tech valuation / concentration shock",
}


def export_crisis_forecast_playbook(
    output_dir: str | Path,
    scenario_exposures: pd.DataFrame,
    calibrated_scenarios: pd.DataFrame,
    resilience_scores: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create future-crisis resilience forecast CSVs."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    forecast = build_crisis_category_forecast(
        scenario_exposures=scenario_exposures,
        calibrated_scenarios=calibrated_scenarios,
        resilience_scores=resilience_scores,
    )
    summary = build_crisis_forecast_summary(forecast)
    forecast.to_csv(output_path / "crisis_category_resilience_forecast.csv", index=False)
    summary.to_csv(output_path / "crisis_forecast_summary.csv", index=False)
    return forecast, summary


def build_crisis_category_forecast(
    scenario_exposures: pd.DataFrame,
    calibrated_scenarios: pd.DataFrame,
    resilience_scores: pd.DataFrame,
) -> pd.DataFrame:
    """Build category-level expected resilience by possible future crisis."""

    if scenario_exposures.empty:
        return _empty_forecast()

    exposure_rows = scenario_exposures.copy()
    exposure_rows["forecast_category"] = exposure_rows.apply(_forecast_category, axis=1)
    historical = _historical_category_scores(resilience_scores)
    calibration = _calibration_map(calibrated_scenarios)

    grouped = (
        exposure_rows.groupby(["scenario", "forecast_category"], sort=False)
        .agg(
            scenario_impact_score=("impact_score", "mean"),
            strongest_positive=("impact_score", "max"),
            strongest_negative=("impact_score", "min"),
            exposure_count=("impact_score", "size"),
            key_beneficiaries=("name", lambda values: _joined_unique(values, limit=4)),
            tickers_and_themes=("ticker_or_theme", lambda values: _joined_unique(values, limit=6)),
            main_rationales=("rationale", lambda values: _joined_unique(values, limit=2)),
        )
        .reset_index()
    )

    rows: list[dict[str, float | int | str]] = []
    for row in grouped.itertuples():
        scenario = str(row.scenario)
        category = str(row.forecast_category)
        calibration_row = calibration.get(scenario, {})
        historical_score = historical.get(category, 0.0)
        scenario_score = float(row.scenario_impact_score)
        expected_score = 0.72 * scenario_score + 0.28 * historical_score
        expected_score = max(-5.0, min(5.0, expected_score))
        probability_weight = float(
            calibration_row.get("calibrated_probability_weight")
            or calibration_row.get("base_probability_weight")
            or 0.0
        )
        severity = float(calibration_row.get("severity_score") or _scenario_severity(exposure_rows, scenario))
        weighted_attention = expected_score * probability_weight * severity
        rows.append(
            {
                "scenario": scenario,
                "crisis_family": CRISIS_FAMILY_MAP.get(scenario, "Other future crisis"),
                "forecast_category": category,
                "expected_resilience_score": expected_score,
                "resilience_band": _resilience_band(expected_score),
                "scenario_impact_score": scenario_score,
                "historical_support_score": historical_score,
                "calibrated_probability_weight": probability_weight,
                "severity_score": severity,
                "weighted_attention_score": weighted_attention,
                "exposure_count": int(row.exposure_count),
                "strongest_positive": float(row.strongest_positive),
                "strongest_negative": float(row.strongest_negative),
                "key_beneficiaries_or_exposures": row.key_beneficiaries,
                "tickers_and_themes": row.tickers_and_themes,
                "forecast_thesis": _forecast_thesis(
                    scenario=scenario,
                    category=category,
                    score=expected_score,
                    rationale=row.main_rationales,
                ),
            }
        )

    if not rows:
        return _empty_forecast()
    return pd.DataFrame(rows).sort_values(
        ["scenario", "expected_resilience_score"], ascending=[True, False]
    )


def build_crisis_forecast_summary(forecast: pd.DataFrame) -> pd.DataFrame:
    """Summarize top resilient, vulnerable, and mixed categories per scenario."""

    if forecast.empty:
        return _empty_summary()

    rows: list[dict[str, str | float]] = []
    for scenario, group in forecast.groupby("scenario", sort=False):
        resilient = group[group["expected_resilience_score"] >= 1.25].sort_values(
            "expected_resilience_score", ascending=False
        )
        vulnerable = group[group["expected_resilience_score"] <= -1.25].sort_values(
            "expected_resilience_score"
        )
        mixed = group[
            (group["expected_resilience_score"] > -1.25)
            & (group["expected_resilience_score"] < 1.25)
        ].sort_values("weighted_attention_score", key=lambda s: s.abs(), ascending=False)
        rows.append(
            {
                "scenario": scenario,
                "crisis_family": CRISIS_FAMILY_MAP.get(scenario, "Other future crisis"),
                "top_resilient_categories": _format_category_list(resilient.head(4)),
                "top_vulnerable_categories": _format_category_list(vulnerable.head(4)),
                "path_dependent_categories": _format_category_list(mixed.head(4)),
                "highest_attention_category": group.iloc[
                    group["weighted_attention_score"].abs().argmax()
                ]["forecast_category"],
                "summary_thesis": _summary_thesis(scenario, resilient, vulnerable),
            }
        )
    return pd.DataFrame(rows)


def plot_crisis_forecast_heatmap(forecast: pd.DataFrame, output_file: str | Path) -> Path:
    """Plot expected category resilience by future crisis scenario."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if forecast.empty:
        return output_path

    pivot = forecast.pivot_table(
        index="scenario",
        columns="forecast_category",
        values="expected_resilience_score",
        aggfunc="mean",
    ).fillna(0.0)
    ordered_columns = sorted(pivot.columns)
    pivot = pivot.loc[:, ordered_columns]
    fig, ax = plt.subplots(figsize=(15, max(7, 0.58 * len(pivot))))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="RdYlGn",
        vmin=-5,
        vmax=5,
        center=0,
        annot=True,
        fmt=".1f",
        linewidths=0.4,
        cbar_kws={"label": "Expected resilience score (-5 vulnerable, +5 resilient)"},
    )
    ax.set_title("Future Crisis Forecast: Expected Resilience by Category")
    ax.set_xlabel("Category")
    ax.set_ylabel("Possible future crisis")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_crisis_forecast_attention(forecast: pd.DataFrame, output_file: str | Path) -> Path:
    """Plot categories with the largest weighted attention scores."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if forecast.empty:
        return output_path

    data = forecast.copy()
    data["absolute_attention"] = data["weighted_attention_score"].abs()
    data["label"] = data["scenario"] + " | " + data["forecast_category"]
    data = data.sort_values("absolute_attention", ascending=False).head(16).sort_values(
        "weighted_attention_score"
    )
    colors = ["#b91c1c" if value < 0 else "#16a34a" for value in data["weighted_attention_score"]]
    fig, ax = plt.subplots(figsize=(13, max(6, 0.44 * len(data))))
    ax.barh(data["label"], data["weighted_attention_score"], color=colors)
    ax.axvline(0, color="#111827", linewidth=0.8)
    ax.set_title("Highest Attention Future Crisis Category Exposures")
    ax.set_xlabel("Weighted attention score")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def _forecast_category(row: pd.Series) -> str:
    text = f"{row.get('bucket', '')} {row.get('ticker_or_theme', '')} {row.get('name', '')}".lower()
    if any(token in text for token in ["gld", "gold", "uup", "dollar", "treasur", "shy", "tlt"]):
        return "Safe-haven liquidity"
    if any(
        token in text
        for token in [
            "uso",
            "xle",
            "oil",
            "energy",
            "lng",
            "fertilizer",
            "rare earth",
            "critical mineral",
            "copper",
            "uranium",
            "refined product",
        ]
    ):
        return "Energy and resource security"
    if any(token in text for token in ["defense", "aerospace", "ita", "xar", "lmt", "noc", "gd", "rtx", "missile", "munitions", "drones", "satellites", "isr"]):
        return "Defense and aerospace"
    if any(token in text for token in ["cyber", "panw", "ftnt", "crwd", "hack", "cibr", "payment system"]):
        return "Cybersecurity and infrastructure"
    if any(token in text for token in ["semiconductor", "chip", "soxx", "smh", "tsm", "nvda", "amd", "intc", "amat", "lrcx", "aapl"]):
        return "Semiconductors and hardware"
    if any(token in text for token in ["ai", "cloud", "xlk", "software", "data-center", "data center", "mega-cap technology"]):
        return "Broad technology and AI"
    if any(token in text for token in ["xlf", "financial", "bank", "credit", "regional lender"]):
        return "Financials and credit"
    if any(token in text for token in ["vnq", "real estate", "utilities", "xlu", "duration", "rate-sensitive"]):
        return "Real estate and rate-sensitive assets"
    if any(token in text for token in ["xlp", "xlv", "staples", "healthcare", "defensive"]):
        return "Defensive equity sectors"
    if any(token in text for token in ["xly", "travel", "airlines", "cruise", "retail", "consumer discretionary"]):
        return "Consumer cyclicals and travel"
    if any(token in text for token in ["xli", "shipping", "logistics", "industrials", "supply-chain", "supply chain"]):
        return "Industrials and logistics"
    return "Other / idiosyncratic"


def _historical_category_scores(resilience_scores: pd.DataFrame) -> dict[str, float]:
    if resilience_scores.empty:
        return {}

    score_map = {
        str(row.ticker): float(row.crisis_resilience_score)
        for row in resilience_scores.itertuples()
        if pd.notna(row.crisis_resilience_score)
    }
    results: dict[str, float] = {}
    for category, tickers in CATEGORY_TICKERS.items():
        scores = [score_map[ticker] for ticker in tickers if ticker in score_map]
        if not scores:
            results[category] = 0.0
            continue
        # Convert 0-100 historical score to roughly -5 to +5 support.
        results[category] = max(-5.0, min(5.0, (sum(scores) / len(scores) - 50.0) / 10.0))
    return results


def _calibration_map(calibrated_scenarios: pd.DataFrame) -> dict[str, dict[str, float]]:
    if calibrated_scenarios.empty:
        return {}
    result: dict[str, dict[str, float]] = {}
    for row in calibrated_scenarios.itertuples():
        result[str(row.scenario)] = {
            "calibrated_probability_weight": float(row.calibrated_probability_weight),
            "base_probability_weight": float(row.base_probability_weight),
            "severity_score": float(row.severity_score),
        }
    return result


def _scenario_severity(exposures: pd.DataFrame, scenario: str) -> float:
    group = exposures[exposures["scenario"] == scenario]
    if group.empty or "severity_score" not in group.columns:
        return 3.0
    return float(group["severity_score"].dropna().iloc[0])


def _joined_unique(values: pd.Series, limit: int) -> str:
    seen: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in seen:
            seen.append(text)
        if len(seen) >= limit:
            break
    return "; ".join(seen)


def _resilience_band(score: float) -> str:
    if score >= 3.0:
        return "High resilience / likely beneficiary"
    if score >= 1.25:
        return "Moderate resilience"
    if score > -1.25:
        return "Mixed / path-dependent"
    if score > -3.0:
        return "Moderate vulnerability"
    return "High vulnerability"


def _forecast_thesis(scenario: str, category: str, score: float, rationale: str) -> str:
    band = _resilience_band(score).lower()
    return (
        f"In {scenario}, {category} screens as {band}. "
        f"The expected score blends scenario exposure assumptions with historical crisis support. "
        f"Key rationale: {rationale}"
    )


def _format_category_list(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "None"
    return "; ".join(
        f"{row.forecast_category} ({row.expected_resilience_score:.1f})"
        for row in frame.itertuples()
    )


def _summary_thesis(
    scenario: str,
    resilient: pd.DataFrame,
    vulnerable: pd.DataFrame,
) -> str:
    resilient_text = _format_category_list(resilient.head(2))
    vulnerable_text = _format_category_list(vulnerable.head(2))
    return (
        f"For {scenario}, expected resilience concentrates in {resilient_text}; "
        f"expected vulnerability concentrates in {vulnerable_text}. "
        "Use this as a scenario playbook, not as a guaranteed return forecast."
    )


def _empty_forecast() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "scenario",
            "crisis_family",
            "forecast_category",
            "expected_resilience_score",
            "resilience_band",
            "scenario_impact_score",
            "historical_support_score",
            "calibrated_probability_weight",
            "severity_score",
            "weighted_attention_score",
            "exposure_count",
            "strongest_positive",
            "strongest_negative",
            "key_beneficiaries_or_exposures",
            "tickers_and_themes",
            "forecast_thesis",
        ]
    )


def _empty_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "scenario",
            "crisis_family",
            "top_resilient_categories",
            "top_vulnerable_categories",
            "path_dependent_categories",
            "highest_attention_category",
            "summary_thesis",
        ]
    )
