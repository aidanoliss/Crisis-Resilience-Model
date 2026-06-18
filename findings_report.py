"""Generate an executive findings report from model outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def generate_executive_findings(output_dir: str | Path) -> Path:
    """Create a concise Markdown findings report from generated CSVs."""

    output_path = Path(output_dir)
    report_path = output_path / "executive_findings.md"

    scores = _read_csv(output_path / "resilience_scores.csv")
    scenario_risk = _read_csv(output_path / "scenario_risk_matrix.csv")
    scenario_summary = _read_csv(output_path / "scenario_summary.csv")
    macro_takeaways = _read_csv(output_path / "macro_proxy_takeaways.csv")
    early_warning_summary = _read_csv(output_path / "early_warning_summary.csv")
    early_warning_indicators = _read_csv(output_path / "early_warning_indicators.csv")
    fred_latest = _read_csv(output_path / "fred_macro_latest.csv")
    fred_alerts = _read_csv(output_path / "fred_macro_alerts.csv")
    news_summary = _read_csv(output_path / "news_sentiment_summary.csv")
    news_alerts = _read_csv(output_path / "news_alerts.csv")
    portfolio_stress = _read_csv(output_path / "portfolio_scenario_stress.csv")
    calibrated_scenarios = _read_csv(output_path / "scenario_calibrated_weights.csv")
    monte_carlo_summary = _read_csv(output_path / "monte_carlo_summary.csv")
    crisis_forecast_summary = _read_csv(output_path / "crisis_forecast_summary.csv")
    crisis_forecast = _read_csv(output_path / "crisis_category_resilience_forecast.csv")
    alerts_summary = _read_csv(output_path / "alerts_summary.csv")
    unified_alerts = _read_csv(output_path / "alerts.csv")
    company_winners = _read_csv(output_path / "company_winners_by_crisis.csv")
    industry_winners = _read_csv(output_path / "industry_asset_winners_by_crisis.csv")
    industry_losers = _read_csv(output_path / "industry_asset_losers_by_crisis.csv")

    sections = [
        "# Executive Findings",
        "",
        "This report summarizes the historical backtest and scenario stress outputs. It is a decision-support artifact, not a forecast or investment recommendation.",
        "",
        "## Historical Crisis Resilience",
        _historical_resilience_section(scores),
        "",
        "## Historical Winners And Losers",
        _winner_loser_section(industry_winners, industry_losers, company_winners),
        "",
        "## Macro Proxy Findings",
        _macro_takeaway_section(macro_takeaways),
        "",
        "## Current Early Warning Monitor",
        _early_warning_section(early_warning_summary, early_warning_indicators),
        "",
        "## Direct FRED Macro Read",
        _fred_section(fred_latest, fred_alerts),
        "",
        "## News And Sentiment Read",
        _news_section(news_summary, news_alerts),
        "",
        "## Unified Alert Feed",
        _alerts_section(alerts_summary, unified_alerts),
        "",
        "## Portfolio Scenario Stress",
        _portfolio_section(portfolio_stress),
        "",
        "## Scenario Calibration And Monte Carlo",
        _calibration_section(calibrated_scenarios, monte_carlo_summary),
        "",
        "## Future Crisis Resilience Forecast",
        _forecast_section(crisis_forecast_summary, crisis_forecast),
        "",
        "## Forward-Looking Scenario Stress",
        _scenario_section(scenario_risk, scenario_summary),
        "",
        "## Expert Read",
        _expert_read_section(scores, scenario_risk),
        "",
        "## Recommended Next Builds",
        "- Improve portfolio imports for brokerage-specific exports with cost basis, account labels, cash, options, and fixed income.",
        "- Add a true LLM/ML news classifier with source quality scoring and event deduplication.",
        "- Add FRED vintage/revision handling and recession-regime validation.",
        "- Add real factor-model shocks for equity beta, rates duration, oil beta, dollar beta, credit beta, and gold beta.",
        "- Add scheduled alerts by email, Slack, or local notification after a data refresh.",
        "",
    ]

    report_path.write_text("\n".join(sections), encoding="utf-8")
    return report_path


def _historical_resilience_section(scores: pd.DataFrame) -> str:
    if scores.empty:
        return "No resilience score output is available."

    top = scores.dropna(subset=["crisis_resilience_score"]).head(6)
    bottom = scores.dropna(subset=["crisis_resilience_score"]).tail(4)
    lines = ["Top aggregate crisis-resilience assets:"]
    for row in top.itertuples():
        lines.append(
            f"- {row.ticker} ({row.asset_name}): score {row.crisis_resilience_score:.1f}, "
            f"total crisis return {row.total_return:.1%}, max drawdown {row.max_drawdown:.1%}, "
            f"SPY correlation {row.correlation_to_spy:.2f}"
        )

    lines.append("")
    lines.append("Weakest aggregate crisis-resilience assets in this universe:")
    for row in bottom.itertuples():
        lines.append(
            f"- {row.ticker} ({row.asset_name}): score {row.crisis_resilience_score:.1f}, "
            f"total crisis return {row.total_return:.1%}, max drawdown {row.max_drawdown:.1%}"
        )
    return "\n".join(lines)


def _winner_loser_section(
    industry_winners: pd.DataFrame,
    industry_losers: pd.DataFrame,
    company_winners: pd.DataFrame,
) -> str:
    lines = []

    if not industry_winners.empty:
        lines.append("Most frequent ETF winners by crisis-window rank:")
        lines.extend(_frequency_lines(industry_winners, "ticker", limit=6))

    if not industry_losers.empty:
        lines.append("")
        lines.append("Most frequent ETF losers by crisis-window rank:")
        lines.extend(_frequency_lines(industry_losers, "ticker", limit=6))

    if not company_winners.empty:
        lines.append("")
        lines.append("Most frequent company winners in the selected universe:")
        label_col = "company_name" if "company_name" in company_winners.columns else "ticker"
        lines.extend(_frequency_lines(company_winners, label_col, limit=8))

    if not lines:
        return "No winner/loser tables are available."
    return "\n".join(lines)


def _macro_takeaway_section(macro_takeaways: pd.DataFrame) -> str:
    if macro_takeaways.empty:
        return "No macro proxy output is available."

    lines = [
        "Macro proxy behavior by crisis window:",
    ]
    for row in macro_takeaways.itertuples():
        lines.append(
            f"- {row.crisis}: strongest {row.strongest_macro_proxies}; weakest {row.weakest_macro_proxies}"
        )
    return "\n".join(lines)


def _scenario_section(scenario_risk: pd.DataFrame, scenario_summary: pd.DataFrame) -> str:
    if scenario_risk.empty:
        return "No scenario risk output is available."

    lines = ["Highest modeled scenario risk scores:"]
    for row in scenario_risk.head(5).itertuples():
        lines.append(
            f"- {row.scenario}: risk score {row.scenario_risk_score:.2f}, "
            f"severity {row.severity_score}, probability weight {row.probability_weight:.0%}, "
            f"inflation {row.inflation_impact}, growth {row.growth_impact}, "
            f"liquidity {row.liquidity_impact}, supply chain {row.supply_chain_impact}"
        )

    if not scenario_summary.empty:
        lines.append("")
        lines.append("Scenario playbook summary:")
        for row in scenario_summary.itertuples():
            lines.append(f"- {row.scenario}: growth -> {row.likely_growth}; pressure -> {row.likely_pressure}")
    return "\n".join(lines)


def _early_warning_section(summary: pd.DataFrame, indicators: pd.DataFrame) -> str:
    if summary.empty:
        return "No early-warning output is available."

    row = summary.iloc[0]
    primary_alerts = row["primary_alerts"]
    if pd.isna(primary_alerts) or not str(primary_alerts).strip():
        primary_alerts = "None"
    lines = [
        f"Current regime: {row['regime']} with score {row['regime_score']:.1f}/100.",
        f"Data freshness: {row['data_freshness']} as of {row['latest_date']} ({row['data_age_days']} days old).",
        f"Active alerts: {row['active_alert_count']}. Primary alerts: {primary_alerts}.",
        f"Interpretation: {row['interpretation']}",
    ]
    if not indicators.empty:
        top = indicators.sort_values("stress_score", ascending=False).head(5)
        lines.append("")
        lines.append("Highest current warning indicators:")
        for item in top.itertuples():
            lines.append(
                f"- {item.indicator} ({item.ticker}): {item.stress_level}, "
                f"score {item.stress_score}, signal {item.signal_value:.2%}"
            )
    return "\n".join(lines)


def _fred_section(latest: pd.DataFrame, alerts: pd.DataFrame) -> str:
    if latest.empty:
        return "No direct FRED macro output is available. Re-run with network access and without --skip-fred."

    lines = ["Highest direct macro stress readings:"]
    for row in latest.sort_values("stress_score", ascending=False).head(6).itertuples():
        lines.append(
            f"- {row.name}: {row.stress_level}, score {row.stress_score}, "
            f"latest {row.latest_value:.2f} as of {row.latest_date}; {row.signal}"
        )
    if not alerts.empty:
        lines.append("")
        lines.append("Active FRED threshold alerts:")
        for row in alerts.head(6).itertuples():
            lines.append(f"- {row.category}: {row.message}")
    return "\n".join(lines)


def _news_section(summary: pd.DataFrame, alerts: pd.DataFrame) -> str:
    if summary.empty:
        return "No news sentiment output is available. Re-run with network access and without --skip-news."

    net_score = summary["net_news_risk_score"].iloc[0] if "net_news_risk_score" in summary.columns else "n/a"
    lines = [f"Net news risk score: {net_score}."]
    lines.append("Top classified categories:")
    for row in summary.sort_values("total_keyword_score", ascending=False).head(5).itertuples():
        lines.append(
            f"- {row.category}: {row.headline_count} headlines, keyword score {row.total_keyword_score}"
        )
    if not alerts.empty:
        lines.append("")
        lines.append("News alerts:")
        for row in alerts.head(5).itertuples():
            lines.append(f"- {row.category}: {row.stress_level}; {row.message}")
    return "\n".join(lines)


def _alerts_section(summary: pd.DataFrame, alerts: pd.DataFrame) -> str:
    if summary.empty:
        return "No unified alert summary is available."

    row = summary.iloc[0]
    lines = [
        f"Unified alert level: {row['highest_level']}.",
        f"Active alert count: {row['active_alert_count']}; average score {row['average_score']:.1f}.",
        f"Top categories: {row['top_categories'] or 'None'}.",
        f"Interpretation: {row['interpretation']}",
    ]
    if not alerts.empty:
        lines.append("")
        lines.append("Highest active alerts:")
        for item in alerts.head(6).itertuples():
            lines.append(f"- {item.source} / {item.category}: {item.level}, score {item.score:.1f}")
    return "\n".join(lines)


def _portfolio_section(portfolio_stress: pd.DataFrame) -> str:
    if portfolio_stress.empty:
        return "No portfolio stress output is available."

    downside = portfolio_stress.sort_values("portfolio_stress_score").head(5)
    upside = portfolio_stress.sort_values("portfolio_stress_score", ascending=False).head(3)
    lines = ["Most negative modeled portfolio scenarios:"]
    for row in downside.itertuples():
        lines.append(
            f"- {row.scenario}: score {row.portfolio_stress_score:.2f}, "
            f"{row.stress_interpretation}"
        )
    lines.append("")
    lines.append("Most positive modeled portfolio scenarios:")
    for row in upside.itertuples():
        lines.append(
            f"- {row.scenario}: score {row.portfolio_stress_score:.2f}, "
            f"{row.stress_interpretation}"
        )
    return "\n".join(lines)


def _calibration_section(calibrated: pd.DataFrame, monte_carlo_summary: pd.DataFrame) -> str:
    if calibrated.empty:
        return "No scenario calibration output is available."

    lines = ["Highest calibrated scenario risk scores:"]
    for row in calibrated.head(5).itertuples():
        lines.append(
            f"- {row.scenario}: calibrated weight {row.calibrated_probability_weight:.0%} "
            f"(base {row.base_probability_weight:.0%}), risk score {row.calibrated_scenario_risk_score:.2f}; "
            f"signals {row.active_calibration_signals or 'none'}"
        )
    if not monte_carlo_summary.empty:
        mc = monte_carlo_summary.iloc[0]
        lines.extend(
            [
                "",
                "Monte Carlo stress proxy:",
                f"- 5th percentile return proxy: {mc['p05_return_proxy']:.1%}",
                f"- 1st percentile return proxy: {mc['p01_return_proxy']:.1%}",
                f"- Severe negative proxy probability: {mc['probability_severe_negative_proxy']:.1%}",
                f"- Most common worst scenario: {mc['most_common_worst_scenario']}",
            ]
        )
    return "\n".join(lines)


def _forecast_section(summary: pd.DataFrame, forecast: pd.DataFrame) -> str:
    if summary.empty:
        return "No future crisis forecast output is available."

    lines = [
        "Category-level forecast by possible future crisis. These are planning scores, not return forecasts."
    ]
    for row in summary.head(6).itertuples():
        lines.append(
            f"- {row.scenario}: resilient -> {row.top_resilient_categories}; "
            f"vulnerable -> {row.top_vulnerable_categories}"
        )

    if not forecast.empty:
        attention = forecast.copy()
        attention["absolute_attention"] = attention["weighted_attention_score"].abs()
        top_attention = attention.sort_values("absolute_attention", ascending=False).head(5)
        lines.append("")
        lines.append("Highest attention category exposures:")
        for row in top_attention.itertuples():
            lines.append(
                f"- {row.scenario} / {row.forecast_category}: "
                f"{row.resilience_band}, score {row.expected_resilience_score:.1f}, "
                f"attention {row.weighted_attention_score:.2f}"
            )
    return "\n".join(lines)


def _expert_read_section(scores: pd.DataFrame, scenario_risk: pd.DataFrame) -> str:
    top_assets = []
    if not scores.empty:
        top_assets = scores.dropna(subset=["crisis_resilience_score"])["ticker"].head(4).tolist()
    top_scenarios = []
    if not scenario_risk.empty:
        top_scenarios = scenario_risk["scenario"].head(3).tolist()

    lines = [
        "The historical backtest strongly favors liquid defensive assets over equity sectors during the configured crisis windows.",
        f"The leading historical resilience assets are {', '.join(top_assets) if top_assets else 'not available'}, mainly reflecting dollar liquidity, Treasury duration, short-duration safety, and gold.",
        "Equity sectors can still matter, but in severe crises they generally behave as relative losers compared with dedicated safe-haven or liquidity proxies.",
        f"The highest modeled forward-looking scenario risks are {', '.join(top_scenarios) if top_scenarios else 'not available'}, because they combine market severity with inflation, liquidity, and supply-chain stress.",
        "The practical portfolio implication is not to chase a single crisis hedge. The better framework is a barbell of liquidity, inflation hedges, selective defense/cyber exposure, and strict position sizing around growth and supply-chain-sensitive assets.",
    ]
    return "\n".join(lines)


def _frequency_lines(df: pd.DataFrame, column: str, limit: int) -> list[str]:
    counts = df[column].value_counts().head(limit)
    return [f"- {name}: {count} appearances" for name, count in counts.items()]


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)
