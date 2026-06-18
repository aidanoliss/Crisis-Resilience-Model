"""Scenario calibration and Monte Carlo stress paths.

The base scenario engine is intentionally transparent and analyst-defined. This
module keeps that transparency while adding an evidence layer: historical
analogs, live alerts, and Monte Carlo sampling. Outputs remain decision-support
inputs, not event probabilities or return forecasts.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ANALOG_MAP: dict[str, list[str]] = {
    "China attacks Taiwan": [
        "2022 Russia-Ukraine Invasion Shock",
        "2022 Inflation and Rate Shock",
        "2015-2016 China and Oil Growth Scare",
    ],
    "China blockades Taiwan": [
        "2022 Russia-Ukraine Invasion Shock",
        "2015-2016 China and Oil Growth Scare",
        "2018 Q4 Fed Tightening and Trade War",
    ],
    "U.S. expands war in the Middle East": [
        "2022 Russia-Ukraine Invasion Shock",
        "2022 Inflation and Rate Shock",
    ],
    "Strait of Hormuz closure": [
        "2022 Russia-Ukraine Invasion Shock",
        "2022 Inflation and Rate Shock",
    ],
    "U.S. debt or Treasury liquidity scare": [
        "2011 Debt Ceiling and Eurozone Stress",
        "2023 Regional Banking Stress",
        "2008 Global Financial Crisis",
    ],
    "Regional bank and commercial real estate shock": [
        "2023 Regional Banking Stress",
        "2008 Global Financial Crisis",
    ],
    "Pandemic 2.0": [
        "2020 COVID Crash",
        "2008 Global Financial Crisis",
    ],
    "Inflation resurgence and second rate shock": [
        "2022 Inflation and Rate Shock",
        "2018 Q4 Fed Tightening and Trade War",
    ],
    "Cyberattack on U.S. financial infrastructure": [
        "2008 Global Financial Crisis",
        "2023 Regional Banking Stress",
    ],
    "AI mega-cap unwind": [
        "2018 Q4 Fed Tightening and Trade War",
        "2022 Inflation and Rate Shock",
    ],
}

SCENARIO_SIGNAL_MAP: dict[str, list[str]] = {
    "China attacks Taiwan": [
        "geopolitical_escalation",
        "supply_shock",
        "cyber_shock",
        "Volatility",
        "Dollar liquidity stress",
    ],
    "China blockades Taiwan": [
        "geopolitical_escalation",
        "supply_shock",
        "Volatility",
        "Dollar liquidity stress",
    ],
    "U.S. expands war in the Middle East": [
        "geopolitical_escalation",
        "supply_shock",
        "inflation_shock",
        "Oil shock",
    ],
    "Strait of Hormuz closure": [
        "geopolitical_escalation",
        "supply_shock",
        "inflation_shock",
        "Oil shock",
    ],
    "U.S. debt or Treasury liquidity scare": [
        "liquidity_stress",
        "Credit",
        "Rates",
        "Financial stress",
        "Dollar liquidity stress",
    ],
    "Regional bank and commercial real estate shock": [
        "liquidity_stress",
        "Credit",
        "Financial stress",
        "Real estate stress",
    ],
    "Pandemic 2.0": [
        "geopolitical_escalation",
        "supply_shock",
        "Volatility",
        "Equity volatility",
    ],
    "Inflation resurgence and second rate shock": [
        "inflation_shock",
        "Inflation",
        "Rates",
        "Duration shock",
    ],
    "Cyberattack on U.S. financial infrastructure": [
        "cyber_shock",
        "liquidity_stress",
        "Financial stress",
        "Volatility",
    ],
    "AI mega-cap unwind": [
        "Equity volatility",
        "Growth technology stress",
        "Volatility",
    ],
}


def export_scenario_calibration(
    output_dir: str | Path,
    scenario_risk_matrix: pd.DataFrame,
    performance_by_crisis: pd.DataFrame,
    portfolio_stress: pd.DataFrame,
    early_warning_indicators: pd.DataFrame,
    fred_alerts: pd.DataFrame,
    news_summary: pd.DataFrame,
    runs: int = 10000,
    random_seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Export calibrated scenario weights and Monte Carlo stress summaries."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    calibrated = calibrate_scenario_weights(
        scenario_risk_matrix=scenario_risk_matrix,
        performance_by_crisis=performance_by_crisis,
        early_warning_indicators=early_warning_indicators,
        fred_alerts=fred_alerts,
        news_summary=news_summary,
    )
    paths, summary = run_monte_carlo_scenarios(
        calibrated=calibrated,
        portfolio_stress=portfolio_stress,
        runs=runs,
        random_seed=random_seed,
    )

    calibrated.to_csv(output_path / "scenario_calibrated_weights.csv", index=False)
    paths.to_csv(output_path / "monte_carlo_scenario_paths.csv", index=False)
    summary.to_csv(output_path / "monte_carlo_summary.csv", index=False)
    return calibrated, paths, summary


def calibrate_scenario_weights(
    scenario_risk_matrix: pd.DataFrame,
    performance_by_crisis: pd.DataFrame,
    early_warning_indicators: pd.DataFrame,
    fred_alerts: pd.DataFrame,
    news_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Blend base scenario weights with historical analogs and current alerts."""

    if scenario_risk_matrix.empty:
        return _empty_calibrated()

    historical = _historical_analog_scores(performance_by_crisis)
    alert_scores = _current_alert_scores(
        early_warning_indicators=early_warning_indicators,
        fred_alerts=fred_alerts,
        news_summary=news_summary,
    )

    rows: list[dict[str, float | str | int]] = []
    for row in scenario_risk_matrix.itertuples():
        scenario = str(row.scenario)
        analog_score = _scenario_analog_score(scenario, historical)
        signal_score, active_signals = _scenario_alert_score(scenario, alert_scores)
        base_weight = float(row.probability_weight)
        calibrated_weight = base_weight * (1.0 + 0.50 * analog_score + 0.75 * signal_score)
        calibrated_weight = float(np.clip(calibrated_weight, 0.02, 0.65))
        macro_abs = float(
            np.mean(
                [
                    abs(float(row.inflation_impact)),
                    abs(float(row.growth_impact)),
                    abs(float(row.liquidity_impact)),
                    abs(float(row.supply_chain_impact)),
                ]
            )
        )
        calibrated_risk_score = calibrated_weight * float(row.severity_score) * macro_abs
        rows.append(
            {
                "scenario": scenario,
                "base_probability_weight": base_weight,
                "calibrated_probability_weight": calibrated_weight,
                "probability_change": calibrated_weight - base_weight,
                "severity_score": row.severity_score,
                "historical_analog_score": analog_score,
                "current_alert_score": signal_score,
                "active_calibration_signals": "; ".join(active_signals),
                "calibrated_scenario_risk_score": calibrated_risk_score,
                "trigger_definition": row.trigger_definition,
                "calibration_method": "base_weight * (1 + 0.50*historical_analog_score + 0.75*current_alert_score), clipped to 2%-65%",
            }
        )

    return pd.DataFrame(rows).sort_values("calibrated_scenario_risk_score", ascending=False)


def run_monte_carlo_scenarios(
    calibrated: pd.DataFrame,
    portfolio_stress: pd.DataFrame,
    runs: int = 10000,
    random_seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sample scenario occurrence paths and portfolio/market stress outcomes."""

    if calibrated.empty:
        return _empty_paths(), _empty_mc_summary()

    rng = np.random.default_rng(random_seed)
    runs = int(max(runs, 100))
    portfolio_map = _portfolio_stress_map(portfolio_stress)
    scenarios = calibrated["scenario"].tolist()
    probabilities = calibrated["calibrated_probability_weight"].astype(float).clip(0.0, 0.80).to_numpy()
    severity = calibrated["severity_score"].astype(float).to_numpy()
    risk_scores = calibrated["calibrated_scenario_risk_score"].astype(float).to_numpy()

    path_rows: list[dict[str, float | int | str]] = []
    simulated_returns: list[float] = []
    event_counts: list[int] = []
    worst_scenarios: list[str] = []

    for run_id in range(1, runs + 1):
        occurred = rng.random(len(scenarios)) < probabilities
        event_count = int(occurred.sum())
        event_counts.append(event_count)

        if event_count == 0:
            simulated = float(rng.normal(0.0, 0.01))
            worst = "No modeled scenario triggered"
        else:
            scenario_impacts = []
            for index, scenario in enumerate(scenarios):
                if not occurred[index]:
                    scenario_impacts.append(0.0)
                    continue
                if scenario in portfolio_map:
                    # One portfolio impact-score point maps to about 4% return
                    # proxy. This is an explainable stress scale, not a forecast.
                    impact = portfolio_map[scenario] * 0.04
                else:
                    impact = -0.025 * risk_scores[index]
                impact *= severity[index] / 4.0
                impact += float(rng.normal(0.0, 0.012))
                scenario_impacts.append(impact)
            simulated = float(np.sum(scenario_impacts))
            worst = scenarios[int(np.argmin(scenario_impacts))]

        simulated_returns.append(simulated)
        worst_scenarios.append(worst)
        path_rows.append(
            {
                "run_id": run_id,
                "triggered_scenario_count": event_count,
                "simulated_portfolio_return_proxy": simulated,
                "worst_triggered_scenario": worst,
            }
        )

    paths = pd.DataFrame(path_rows)
    returns = pd.Series(simulated_returns)
    summary = pd.DataFrame(
        [
            {
                "runs": runs,
                "mean_return_proxy": float(returns.mean()),
                "median_return_proxy": float(returns.median()),
                "p05_return_proxy": float(returns.quantile(0.05)),
                "p01_return_proxy": float(returns.quantile(0.01)),
                "p95_return_proxy": float(returns.quantile(0.95)),
                "probability_negative_proxy": float((returns < 0).mean()),
                "probability_severe_negative_proxy": float((returns <= -0.10).mean()),
                "average_triggered_scenario_count": float(np.mean(event_counts)),
                "most_common_worst_scenario": pd.Series(worst_scenarios).mode().iloc[0],
                "model_scale_note": "Portfolio stress scores are converted with 1 impact-score point = about 4% return proxy; not a return forecast.",
            }
        ]
    )
    return paths, summary


def plot_calibrated_scenario_weights(calibrated: pd.DataFrame, output_file: str | Path) -> Path:
    """Compare base and calibrated scenario weights."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if calibrated.empty:
        return output_path

    data = calibrated.sort_values("calibrated_probability_weight")
    fig, ax = plt.subplots(figsize=(12, max(5, 0.45 * len(data))))
    y = np.arange(len(data))
    ax.barh(y - 0.18, data["base_probability_weight"], height=0.34, label="Base", color="#94a3b8")
    ax.barh(
        y + 0.18,
        data["calibrated_probability_weight"],
        height=0.34,
        label="Calibrated",
        color="#0f766e",
    )
    ax.set_yticks(y)
    ax.set_yticklabels(data["scenario"])
    ax.set_title("Scenario Weights: Base vs Calibrated")
    ax.set_xlabel("Scenario weight")
    ax.legend()
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_monte_carlo_distribution(paths: pd.DataFrame, output_file: str | Path) -> Path:
    """Plot Monte Carlo stress-return proxy distribution."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if paths.empty:
        return output_path

    values = pd.to_numeric(paths["simulated_portfolio_return_proxy"], errors="coerce").dropna()
    if values.empty:
        return output_path

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.hist(values, bins=60, color="#2563eb", alpha=0.78)
    ax.axvline(values.quantile(0.05), color="#b91c1c", linewidth=1.5, label="5th percentile")
    ax.axvline(values.median(), color="#111827", linewidth=1.3, label="Median")
    ax.set_title("Monte Carlo Scenario Stress Distribution")
    ax.set_xlabel("Simulated portfolio return proxy")
    ax.set_ylabel("Run count")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def _historical_analog_scores(performance_by_crisis: pd.DataFrame) -> dict[str, float]:
    if performance_by_crisis.empty:
        return {}

    frame = performance_by_crisis.copy()
    if "ticker" in frame.columns:
        frame = frame[frame["ticker"] == "SPY"]
    if frame.empty:
        return {}

    raw: dict[str, float] = {}
    for row in frame.itertuples():
        drawdown = abs(float(getattr(row, "max_drawdown", 0.0)))
        loss = max(0.0, -float(getattr(row, "total_return", 0.0)))
        volatility = max(0.0, float(getattr(row, "volatility", 0.0)))
        raw[str(row.crisis)] = drawdown + loss + 0.35 * volatility

    if not raw:
        return {}
    max_score = max(raw.values()) or 1.0
    return {crisis: score / max_score for crisis, score in raw.items()}


def _scenario_analog_score(scenario: str, historical: dict[str, float]) -> float:
    analogs = ANALOG_MAP.get(scenario, [])
    scores = [historical[analog] for analog in analogs if analog in historical]
    if not scores:
        return 0.35
    return float(np.mean(scores))


def _current_alert_scores(
    early_warning_indicators: pd.DataFrame,
    fred_alerts: pd.DataFrame,
    news_summary: pd.DataFrame,
) -> dict[str, float]:
    scores: dict[str, float] = {}
    if not early_warning_indicators.empty:
        for row in early_warning_indicators.itertuples():
            scores[str(row.indicator)] = max(
                scores.get(str(row.indicator), 0.0),
                min(1.0, float(row.stress_score) / 100.0),
            )

    if not fred_alerts.empty:
        for row in fred_alerts.itertuples():
            scores[str(row.category)] = max(
                scores.get(str(row.category), 0.0),
                min(1.0, float(row.stress_score) / 100.0),
            )

    if not news_summary.empty:
        max_news = max(float(news_summary["total_keyword_score"].max()), 1.0)
        for row in news_summary.itertuples():
            scores[str(row.category)] = max(
                scores.get(str(row.category), 0.0),
                min(1.0, float(row.total_keyword_score) / max_news),
            )
    return scores


def _scenario_alert_score(scenario: str, alert_scores: dict[str, float]) -> tuple[float, list[str]]:
    signals = SCENARIO_SIGNAL_MAP.get(scenario, [])
    active: list[str] = []
    values: list[float] = []
    for signal in signals:
        value = alert_scores.get(signal, 0.0)
        values.append(value)
        if value >= 0.40:
            active.append(f"{signal} ({value:.2f})")
    if not values:
        return 0.0, active
    return float(np.mean(values)), active


def _portfolio_stress_map(portfolio_stress: pd.DataFrame) -> dict[str, float]:
    if portfolio_stress.empty or "scenario" not in portfolio_stress.columns:
        return {}
    return {
        str(row.scenario): float(row.portfolio_stress_score)
        for row in portfolio_stress.itertuples()
        if pd.notna(row.portfolio_stress_score)
    }


def _empty_calibrated() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "scenario",
            "base_probability_weight",
            "calibrated_probability_weight",
            "probability_change",
            "severity_score",
            "historical_analog_score",
            "current_alert_score",
            "active_calibration_signals",
            "calibrated_scenario_risk_score",
            "trigger_definition",
            "calibration_method",
        ]
    )


def _empty_paths() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "run_id",
            "triggered_scenario_count",
            "simulated_portfolio_return_proxy",
            "worst_triggered_scenario",
        ]
    )


def _empty_mc_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "runs",
            "mean_return_proxy",
            "median_return_proxy",
            "p05_return_proxy",
            "p01_return_proxy",
            "p95_return_proxy",
            "probability_negative_proxy",
            "probability_severe_negative_proxy",
            "average_triggered_scenario_count",
            "most_common_worst_scenario",
            "model_scale_note",
        ]
    )
