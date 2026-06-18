"""Generate publishable crisis simulation case-study reports.

The simulation reports are presentation artifacts. They summarize model outputs
for a few realistic crisis families and explain what the model expects to be
resilient, vulnerable, and path-dependent. They are not investment advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class SimulationCase:
    slug: str
    title: str
    scenarios: list[str]
    thesis: str
    historical_analogs: list[str]
    key_questions: list[str]


SIMULATION_CASES: list[SimulationCase] = [
    SimulationCase(
        slug="taiwan_conflict",
        title="Taiwan Conflict / Pacific Semiconductor Shock",
        scenarios=["China attacks Taiwan", "China blockades Taiwan"],
        thesis=(
            "A Taiwan conflict is modeled as a severe supply-chain, semiconductor, "
            "liquidity, cyber, and defense-demand shock."
        ),
        historical_analogs=[
            "2022 Russia-Ukraine Invasion Shock",
            "2022 Inflation and Rate Shock",
            "2015-2016 China and Oil Growth Scare",
        ],
        key_questions=[
            "How exposed is the portfolio to advanced-chip supply chains?",
            "Does the portfolio have enough liquidity and safe-haven exposure?",
            "Are defense, cyber, and critical-mineral exposures sized deliberately?",
        ],
    ),
    SimulationCase(
        slug="middle_east_energy_shock",
        title="Middle East War / Strait of Hormuz Energy Shock",
        scenarios=["U.S. expands war in the Middle East", "Strait of Hormuz closure"],
        thesis=(
            "A Middle East escalation is modeled as an oil, inflation, shipping, "
            "defense, and consumer-margin shock."
        ),
        historical_analogs=[
            "2022 Russia-Ukraine Invasion Shock",
            "2022 Inflation and Rate Shock",
            "2018 Q4 Fed Tightening and Trade War",
        ],
        key_questions=[
            "Would energy exposure offset the consumer and rate shock?",
            "How vulnerable are travel, discretionary, and margin-sensitive holdings?",
            "Would higher inflation pressure duration and growth assets?",
        ],
    ),
    SimulationCase(
        slug="credit_liquidity_crisis",
        title="Credit / Liquidity Crisis",
        scenarios=[
            "U.S. debt or Treasury liquidity scare",
            "Regional bank and commercial real estate shock",
        ],
        thesis=(
            "A credit/liquidity crisis is modeled as a funding, bank, real estate, "
            "Treasury-market, and broad-risk-appetite shock."
        ),
        historical_analogs=[
            "2008 Global Financial Crisis",
            "2011 Debt Ceiling and Eurozone Stress",
            "2023 Regional Banking Stress",
        ],
        key_questions=[
            "How much exposure is tied to banks, credit, real estate, or leverage?",
            "Can short-duration liquidity cover volatility and drawdowns?",
            "Would long-duration Treasuries help or hurt if the stress is fiscal/rate-driven?",
        ],
    ),
]


def generate_simulation_reports(output_dir: str | Path) -> dict[str, Path]:
    """Generate Markdown simulation reports from latest model output CSVs."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    context = {
        "forecast_summary": _read_csv(output_path / "crisis_forecast_summary.csv"),
        "forecast_detail": _read_csv(output_path / "crisis_category_resilience_forecast.csv"),
        "calibrated": _read_csv(output_path / "scenario_calibrated_weights.csv"),
        "portfolio_stress": _read_csv(output_path / "portfolio_scenario_stress.csv"),
        "monte_carlo": _read_csv(output_path / "monte_carlo_summary.csv"),
        "alerts": _read_csv(output_path / "alerts_summary.csv"),
    }

    paths: dict[str, Path] = {}
    for case in SIMULATION_CASES:
        path = output_path / f"simulation_{case.slug}.md"
        path.write_text(_simulation_markdown(case, context), encoding="utf-8")
        paths[case.slug] = path

    index_path = output_path / "simulation_reports_index.md"
    index_path.write_text(_index_markdown(paths), encoding="utf-8")
    paths["index"] = index_path
    return paths


def _simulation_markdown(case: SimulationCase, context: dict[str, pd.DataFrame]) -> str:
    forecast_summary = _filter_scenarios(context["forecast_summary"], case.scenarios)
    forecast_detail = _filter_scenarios(context["forecast_detail"], case.scenarios)
    calibrated = _filter_scenarios(context["calibrated"], case.scenarios)
    portfolio = _filter_scenarios(context["portfolio_stress"], case.scenarios)
    monte_carlo = context["monte_carlo"]
    alerts = context["alerts"]

    lines = [
        f"# Simulation: {case.title}",
        "",
        case.thesis,
        "",
        "Important: this is a scenario stress simulation and decision-support artifact. It is not a prediction, price target, or investment recommendation.",
        "",
        "## Scenario Set",
        *[f"- {scenario}" for scenario in case.scenarios],
        "",
        "## Key Questions",
        *[f"- {question}" for question in case.key_questions],
        "",
        "## Historical Analogs",
        *[f"- {analog}" for analog in case.historical_analogs],
        "",
        "## Expected Category Resilience",
        _forecast_summary_table(forecast_summary),
        "",
        "## Highest Attention Categories",
        _attention_lines(forecast_detail),
        "",
        "## Calibrated Scenario Weights",
        _calibration_table(calibrated),
        "",
        "## Portfolio Stress Read",
        _portfolio_table(portfolio),
        "",
        "## Monte Carlo Context",
        _monte_carlo_lines(monte_carlo),
        "",
        "## Current Alert Context",
        _alert_lines(alerts),
        "",
        "## Relevant Dashboard Charts",
        "- [Future crisis category resilience heatmap](charts/crisis_category_resilience_forecast_heatmap.png)",
        "- [Forecast attention scores](charts/crisis_forecast_attention_scores.png)",
        "- [Scenario calibrated weights](charts/scenario_calibrated_weights.png)",
        "- [Monte Carlo stress distribution](charts/monte_carlo_portfolio_stress_distribution.png)",
        "",
        "## Interpretation",
        _interpretation(case, forecast_summary, forecast_detail),
        "",
        "## Caveats",
        "- Scenario scores are analyst-defined planning assumptions blended with historical support.",
        "- Historical analogs are imperfect; future crises can transmit through different channels.",
        "- Portfolio stress is only as accurate as the holdings and scenario mappings provided.",
        "- News and macro alerts should be refreshed and verified before presenting current-market conclusions.",
        "",
    ]
    return "\n".join(lines)


def _index_markdown(paths: dict[str, Path]) -> str:
    lines = [
        "# Crisis Simulation Reports",
        "",
        "These reports are presentation-ready case studies generated from the latest model outputs.",
        "",
    ]
    for case in SIMULATION_CASES:
        path = paths[case.slug]
        lines.append(f"- [{case.title}]({path.name})")
    lines.extend(
        [
            "",
            "Use these as examples of how to explain the model. They are not investment advice or crisis predictions.",
            "",
        ]
    )
    return "\n".join(lines)


def _forecast_summary_table(summary: pd.DataFrame) -> str:
    if summary.empty:
        return "No forecast summary rows are available."
    table = summary[
        [
            "scenario",
            "top_resilient_categories",
            "top_vulnerable_categories",
            "path_dependent_categories",
        ]
    ].copy()
    return _markdown_table(table)


def _attention_lines(forecast: pd.DataFrame) -> str:
    if forecast.empty:
        return "No forecast detail rows are available."
    data = forecast.copy()
    data["absolute_attention"] = data["weighted_attention_score"].abs()
    data = data.sort_values("absolute_attention", ascending=False).head(8)
    lines = []
    for row in data.itertuples():
        lines.append(
            f"- {row.scenario} / {row.forecast_category}: {row.resilience_band}, "
            f"score {row.expected_resilience_score:.1f}, attention {row.weighted_attention_score:.2f}"
        )
    return "\n".join(lines)


def _calibration_table(calibrated: pd.DataFrame) -> str:
    if calibrated.empty:
        return "No calibrated scenario rows are available."
    table = calibrated[
        [
            "scenario",
            "base_probability_weight",
            "calibrated_probability_weight",
            "severity_score",
            "calibrated_scenario_risk_score",
            "active_calibration_signals",
        ]
    ].copy()
    for column in ["base_probability_weight", "calibrated_probability_weight"]:
        table[column] = table[column].map(lambda value: f"{value:.0%}")
    table["calibrated_scenario_risk_score"] = table["calibrated_scenario_risk_score"].map(
        lambda value: f"{value:.2f}"
    )
    return _markdown_table(table)


def _portfolio_table(portfolio: pd.DataFrame) -> str:
    if portfolio.empty:
        return "No portfolio stress rows are available."
    table = portfolio[["scenario", "portfolio_stress_score", "stress_interpretation"]].copy()
    table["portfolio_stress_score"] = table["portfolio_stress_score"].map(lambda value: f"{value:.2f}")
    return _markdown_table(table)


def _monte_carlo_lines(monte_carlo: pd.DataFrame) -> str:
    if monte_carlo.empty:
        return "No Monte Carlo summary is available."
    row = monte_carlo.iloc[0]
    return "\n".join(
        [
            f"- 5th percentile stress-return proxy: {row['p05_return_proxy']:.1%}",
            f"- 1st percentile stress-return proxy: {row['p01_return_proxy']:.1%}",
            f"- Probability of negative proxy outcome: {row['probability_negative_proxy']:.1%}",
            f"- Probability of severe negative proxy outcome: {row['probability_severe_negative_proxy']:.1%}",
            f"- Most common worst scenario: {row['most_common_worst_scenario']}",
        ]
    )


def _alert_lines(alerts: pd.DataFrame) -> str:
    if alerts.empty:
        return "No alert summary is available."
    row = alerts.iloc[0]
    return "\n".join(
        [
            f"- Unified alert level: {row['highest_level']}",
            f"- Active alert count: {row['active_alert_count']}",
            f"- Top alert categories: {row['top_categories']}",
            f"- Interpretation: {row['interpretation']}",
        ]
    )


def _interpretation(
    case: SimulationCase,
    summary: pd.DataFrame,
    forecast: pd.DataFrame,
) -> str:
    if summary.empty or forecast.empty:
        return "The model did not have enough output data to generate a case interpretation."

    resilient = (
        forecast[forecast["expected_resilience_score"] >= 1.25]
        .sort_values("expected_resilience_score", ascending=False)
        .head(4)["forecast_category"]
        .drop_duplicates()
        .tolist()
    )
    vulnerable = (
        forecast[forecast["expected_resilience_score"] <= -1.25]
        .sort_values("expected_resilience_score")
        .head(4)["forecast_category"]
        .drop_duplicates()
        .tolist()
    )
    return (
        f"For {case.title}, the model points to {', '.join(resilient) or 'no clear resilient categories'} "
        f"as the main resilience candidates and {', '.join(vulnerable) or 'no clear vulnerable categories'} "
        "as the areas requiring the most risk review. This should be presented as a structured stress test, "
        "not as a forecast of actual market returns."
    )


def _filter_scenarios(df: pd.DataFrame, scenarios: list[str]) -> pd.DataFrame:
    if df.empty or "scenario" not in df.columns:
        return pd.DataFrame()
    return df[df["scenario"].isin(scenarios)].copy()


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "No rows available."
    safe = df.fillna("").astype(str)
    headers = safe.columns.tolist()
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in safe.itertuples(index=False):
        values = [str(value).replace("\n", " ").replace("|", "\\|") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)
