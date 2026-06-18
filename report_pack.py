"""Comprehensive report pack generation.

This module creates human-readable documentation for every generated dataset
and chart so the project can be reviewed without inspecting the code first.
"""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd


DATASET_NOTES: dict[str, str] = {
    "adjusted_close_prices.csv": "Adjusted close ETF prices downloaded from yfinance for the core ETF universe.",
    "daily_returns.csv": "Daily simple returns calculated from adjusted close prices.",
    "performance_by_crisis.csv": "Per-crisis performance metrics for each ETF and asset-class proxy.",
    "aggregate_crisis_metrics.csv": "Performance metrics across the de-duplicated union of all crisis windows.",
    "resilience_scores.csv": "Crisis Resilience Score ranking and component scores.",
    "crisis_periods.csv": "Explicit historical crisis windows used by the backtest.",
    "historical_context.csv": "Analyst-defined context for wars, shocks, resources, technologies, and companies.",
    "technology_themes.csv": "Technology themes that benefited or became more important during crisis regimes.",
    "company_adjusted_close_prices.csv": "Adjusted close prices for the company universe used in winner analysis.",
    "company_daily_returns.csv": "Daily returns for the company universe.",
    "company_performance_by_crisis.csv": "Company-level performance metrics by crisis window.",
    "company_winners_by_crisis.csv": "Top company performers inside each crisis window.",
    "industry_asset_winners_by_crisis.csv": "Top ETF and asset-class performers inside each crisis window.",
    "industry_asset_losers_by_crisis.csv": "Weakest ETF and asset-class performers inside each crisis window.",
    "scenario_exposures.csv": "Forward-looking stress assumptions by scenario, bucket, ticker/theme, and impact score.",
    "scenario_summary.csv": "Compact likely-growth, likely-pressure, and mixed buckets for each scenario.",
    "scenario_risk_matrix.csv": "Scenario-level probability weights, severity, macro impacts, and risk scores.",
    "scenario_bucket_summary.csv": "Average scenario impact by exposure bucket.",
    "macro_proxy_crisis_summary.csv": "Crisis-window returns, volatility, and drawdowns for macro proxy instruments.",
    "macro_proxy_takeaways.csv": "Strongest and weakest macro proxies by crisis window.",
    "fred_macro_series.csv": "Direct FRED macro series: CPI, Fed funds, Treasury yields, VIX, credit spreads, unemployment, and financial stress indexes.",
    "fred_macro_latest.csv": "Latest direct FRED macro readings with trend and stress-threshold scores.",
    "fred_macro_crisis_summary.csv": "Direct FRED macro changes inside each historical crisis window.",
    "fred_macro_alerts.csv": "Threshold alerts generated from direct FRED macro readings.",
    "early_warning_indicators.csv": "Current early-warning indicator readings from latest cached price history.",
    "early_warning_summary.csv": "Current regime classification and active alert summary.",
    "news_items.csv": "RSS headline items classified into crisis sentiment categories.",
    "news_sentiment_summary.csv": "Aggregated news classification counts and keyword scores.",
    "news_alerts.csv": "News-driven watch/stress and de-escalation alerts.",
    "sample_portfolio.csv": "Default sample portfolio used when no custom portfolio is supplied.",
    "active_portfolio.csv": "Portfolio actually used in the latest model run.",
    "portfolio_import_audit.csv": "Audit row describing how the portfolio CSV or sample portfolio was normalized.",
    "portfolio_scenario_stress.csv": "Portfolio-level scenario stress scores.",
    "portfolio_stress_contributions.csv": "Holding-level contributions to each portfolio scenario stress score.",
    "scenario_calibrated_weights.csv": "Scenario weights recalibrated with historical analogs and current alert signals.",
    "monte_carlo_scenario_paths.csv": "Monte Carlo sampled scenario paths and portfolio stress-return proxies.",
    "monte_carlo_summary.csv": "Summary percentiles and probabilities from Monte Carlo scenario paths.",
    "crisis_category_resilience_forecast.csv": "Future-crisis playbook showing expected resilience by category for each possible crisis scenario.",
    "crisis_forecast_summary.csv": "Compact top resilient, vulnerable, and path-dependent categories by possible future crisis.",
    "alerts.csv": "Unified alert feed combining market proxies, FRED thresholds, news sentiment, and calibrated scenarios.",
    "alerts_summary.csv": "Current overall alert level and top alert categories.",
}


FUTURE_IMPROVEMENTS: list[dict[str, str]] = [
    {
        "priority": "P1",
        "improvement": "Brokerage-grade portfolio import",
        "why_it_matters": "The current custom CSV supports ticker and weight. Real brokerage files usually include account, cost basis, cash, options, bonds, funds, and duplicate symbols.",
        "implementation_notes": "Add import adapters for Schwab, Fidelity, Robinhood, Vanguard, Interactive Brokers, and generic portfolio software exports.",
    },
    {
        "priority": "P1",
        "improvement": "Scheduled alerts and notifications",
        "why_it_matters": "The alert feed is useful, but it should proactively notify the user after refreshes when VIX, credit spreads, oil, dollar, rates, or news categories breach thresholds.",
        "implementation_notes": "Add cron/automation support plus email, Slack, or local macOS notification delivery with deduplication.",
    },
    {
        "priority": "P1",
        "improvement": "LLM-assisted news/event intelligence",
        "why_it_matters": "The current RSS classifier is transparent but keyword-based. LLM classification can detect context, source credibility, escalation/de-escalation nuance, and duplicate stories.",
        "implementation_notes": "Add source scoring, entity extraction, event clustering, confidence labels, and a fallback keyword model for offline use.",
    },
    {
        "priority": "P2",
        "improvement": "Factor-calibrated Monte Carlo shocks",
        "why_it_matters": "The current Monte Carlo engine converts scenario impact scores into stress-return proxies. A production model should estimate factor betas and covariance from returns.",
        "implementation_notes": "Estimate equity beta, duration beta, dollar beta, oil beta, gold beta, credit beta, and sector residual risk, then simulate correlated paths.",
    },
    {
        "priority": "P2",
        "improvement": "Macro vintage and recession validation",
        "why_it_matters": "FRED series are revised and released at different frequencies. Real-time crisis detection should avoid look-ahead bias.",
        "implementation_notes": "Use ALFRED vintage data, release calendars, recession labels, and walk-forward threshold tests.",
    },
    {
        "priority": "P2",
        "improvement": "Expanded investable hedge universe",
        "why_it_matters": "Some scenarios need more precise instruments than broad sector ETFs.",
        "implementation_notes": "Add defense ETFs, cyber ETFs, semiconductor ETFs, uranium, copper, agriculture, high-yield credit, investment-grade credit, China/Taiwan ETFs, and managed futures.",
    },
    {
        "priority": "P2",
        "improvement": "Interactive dashboard deployment",
        "why_it_matters": "The static dashboard is portable, but a Streamlit app enables user inputs and drilldowns.",
        "implementation_notes": "Finish Streamlit dependency setup, then expose scenario selectors, portfolio upload, and custom scoring weights.",
    },
    {
        "priority": "P3",
        "improvement": "Asset universe expansion",
        "why_it_matters": "Some scenarios need more precise proxies than broad sector ETFs.",
        "implementation_notes": "Add defense ETFs, cyber ETFs, semiconductor ETFs, food/fertilizer ETFs, regional banks, high yield, investment-grade credit, and China/Taiwan ETFs.",
    },
    {
        "priority": "P3",
        "improvement": "Data quality and survivorship checks",
        "why_it_matters": "ETF inception dates, ticker changes, and missing histories can distort crisis rankings.",
        "implementation_notes": "Add minimum-history filters, missing-data reports, and alternate proxy selection for pre-inception periods.",
    },
    {
        "priority": "P3",
        "improvement": "Backtest transaction costs and rebalance rules",
        "why_it_matters": "Crisis hedges often require rebalancing discipline and may be costly to hold.",
        "implementation_notes": "Add monthly/quarterly rebalance portfolios, transaction costs, and turnover metrics.",
    },
]


def generate_report_pack(output_dir: str | Path) -> dict[str, Path]:
    """Generate all supplemental report artifacts."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    chart_synopses = build_chart_synopses(output_path)
    data_dictionary = build_data_dictionary(output_path)
    improvements = pd.DataFrame(FUTURE_IMPROVEMENTS)

    chart_synopses_path = output_path / "chart_synopses.csv"
    data_dictionary_path = output_path / "data_dictionary.csv"
    improvements_path = output_path / "future_improvements.md"
    full_report_path = output_path / "full_report.md"

    chart_synopses.to_csv(chart_synopses_path, index=False)
    data_dictionary.to_csv(data_dictionary_path, index=False)
    improvements_path.write_text(_future_improvements_markdown(improvements), encoding="utf-8")
    full_report_path.write_text(
        _full_report_markdown(output_path, chart_synopses, data_dictionary, improvements),
        encoding="utf-8",
    )

    return {
        "chart_synopses": chart_synopses_path,
        "data_dictionary": data_dictionary_path,
        "future_improvements": improvements_path,
        "full_report": full_report_path,
    }


def build_chart_synopses(output_dir: Path) -> pd.DataFrame:
    """Create a synopsis row for every generated PNG chart."""

    chart_dir = output_dir / "charts"
    rows: list[dict[str, str]] = []
    for chart in sorted(chart_dir.glob("*.png")):
        title, section, synopsis, how_to_read, caveat = _chart_synopsis(chart.name)
        rows.append(
            {
                "chart_file": f"charts/{chart.name}",
                "title": title,
                "section": section,
                "synopsis": synopsis,
                "how_to_read": how_to_read,
                "caveat": caveat,
            }
        )
    return pd.DataFrame(rows)


def build_data_dictionary(output_dir: Path) -> pd.DataFrame:
    """Create a data dictionary row for every generated CSV."""

    rows: list[dict[str, str | int]] = []
    for csv_path in sorted(output_dir.glob("*.csv")):
        try:
            sample = pd.read_csv(csv_path, nrows=5)
            row_count = sum(1 for _ in csv_path.open("r", encoding="utf-8", errors="ignore")) - 1
            columns = ", ".join(sample.columns.astype(str).tolist())
        except Exception as exc:
            row_count = 0
            columns = ""
            note = f"Could not inspect file: {exc}"
        else:
            note = DATASET_NOTES.get(csv_path.name, "Generated project output.")

        rows.append(
            {
                "file": csv_path.name,
                "rows": max(row_count, 0),
                "columns": columns,
                "purpose": note,
            }
        )
    return pd.DataFrame(rows)


def _chart_synopsis(filename: str) -> tuple[str, str, str, str, str]:
    stem = filename.removesuffix(".png")
    title = stem.replace("_", " ").title()
    caveat = "Read this as historical evidence or scenario stress output, not as a guaranteed forecast."

    if filename.startswith("cumulative_returns_"):
        crisis = stem.replace("cumulative_returns_", "").replace("_", " ").title()
        return (
            f"Cumulative Returns: {crisis}",
            "Historical Crisis Charts",
            "Shows how each asset compounded through one crisis window relative to SPY.",
            "Lines above zero preserved or grew capital during the window; steeper declines indicate weaker crisis behavior.",
            "The result depends on the exact start and end dates of the crisis window.",
        )

    exact: dict[str, tuple[str, str, str, str, str]] = {
        "resilience_score_ranking.png": (
            "Crisis Resilience Score Ranking",
            "Historical Scoring",
            "Ranks assets using the transparent composite score that rewards crisis returns, lower drawdowns, lower volatility, and lower SPY correlation.",
            "Higher bars are better historical crisis-resilience scores.",
            "The scoring weights are explicit but subjective and can be changed.",
        ),
        "resilience_score_decomposition.png": (
            "Crisis Resilience Score Decomposition",
            "Historical Scoring",
            "Breaks the final resilience score into weighted contributions from return, drawdown protection, low volatility, and low SPY correlation.",
            "Longer stacked bars are stronger total scores; the color mix shows why each asset ranked where it did.",
            "The decomposition explains the scoring formula, but it still inherits the subjective score weights.",
        ),
        "drawdowns_all_crises.png": (
            "Drawdowns Across All Crisis Windows",
            "Historical Risk",
            "Shows peak-to-trough losses during the combined crisis windows.",
            "Deeper negative values indicate larger capital impairment during stress.",
            "Overlapping crisis periods are de-duplicated in the aggregate crisis return set.",
        ),
        "correlation_heatmap.png": (
            "Crisis Correlation Heatmap",
            "Historical Risk",
            "Shows return correlations among assets during crisis windows.",
            "Lower or negative correlations to SPY are more useful for diversification.",
            "Correlation can change quickly across crisis types.",
        ),
        "historical_crisis_timeline.png": (
            "Historical Crisis Timeline",
            "Historical Context",
            "Connects each modeled crisis window to its geopolitical, policy, pandemic, or financial context.",
            "Use it to understand why each window was included and how long it lasted.",
            "The context labels are analyst-defined summaries.",
        ),
        "crisis_sector_asset_return_heatmap.png": (
            "Sector And Asset-Class Returns By Crisis",
            "Historical Crisis Charts",
            "Compares total returns across sectors and assets for every crisis window.",
            "Green cells are relative winners; red cells are crisis losers.",
            "Some ETFs have shorter histories due to inception dates.",
        ),
        "industry_winners_losers_by_crisis.png": (
            "Industry Winners And Losers By Crisis",
            "Historical Crisis Charts",
            "Shows top and bottom ETF performers inside each crisis window.",
            "Use this to identify which sectors or assets repeatedly held up or failed.",
            "A top performer can still be negative if the entire market fell.",
        ),
        "resource_importance_by_crisis.png": (
            "Resources And Defensive Assets By Crisis",
            "Macro Proxy Layer",
            "Focuses on gold, oil, dollar, Treasuries, materials, and energy during crisis regimes.",
            "Green shows resources that appreciated during that stress type.",
            "ETF proxies are imperfect representations of underlying commodities.",
        ),
        "company_winners_by_crisis.png": (
            "Company Winners By Crisis",
            "Company Analysis",
            "Ranks the strongest companies in the selected universe during each crisis window.",
            "Use it to see recurring resilient business models and crisis-specific winners.",
            "The company universe is curated and not exhaustive.",
        ),
        "historical_context_table.png": (
            "Historical Context Table",
            "Historical Context",
            "Summarizes resources and technologies that mattered during each crisis.",
            "Use it as a narrative bridge between price action and real-world drivers.",
            "This is qualitative context, not a statistical model.",
        ),
        "technology_themes_table.png": (
            "Technology Themes Table",
            "Technology Themes",
            "Lists crisis-relevant technology themes such as cloud, cybersecurity, semiconductors, defense electronics, and biotech.",
            "Use it to map market stress to technology demand shifts.",
            "The examples are representative rather than exhaustive.",
        ),
        "macro_proxy_return_heatmap.png": (
            "Macro Proxy Crisis Returns",
            "Macro Proxy Layer",
            "Shows how macro proxies performed during each historical crisis.",
            "Green identifies macro assets that benefited from the stress regime.",
            "ETF proxy performance includes fund structure and tracking effects.",
        ),
        "macro_proxy_drawdown_heatmap.png": (
            "Macro Proxy Crisis Drawdowns",
            "Macro Proxy Layer",
            "Shows worst drawdowns for macro proxies inside each crisis window.",
            "Less negative drawdowns indicate better capital preservation.",
            "Drawdown is path-dependent and not captured by endpoint return alone.",
        ),
        "macro_proxy_normalized_history.png": (
            "Macro Proxy Normalized History",
            "Macro Proxy Layer",
            "Normalizes macro proxy prices to show long-run relative movement.",
            "Use it to compare broad paths across oil, dollar, gold, Treasuries, equities, financials, and real estate.",
            "Normalized charts do not adjust for portfolio weights or risk.",
        ),
        "early_warning_scores.png": (
            "Early Warning Stress Scores",
            "Early Warning Monitor",
            "Ranks current stress indicators using the latest cached prices.",
            "Scores near 100 are more stressed; scores near 0 are calmer.",
            "Refresh market data with --force-refresh before using this for current monitoring.",
        ),
        "early_warning_regime_gauge.png": (
            "Early Warning Regime Gauge",
            "Early Warning Monitor",
            "Summarizes the current market regime as Normal, Watch, Stress, or Crisis.",
            "The gauge combines average and maximum indicator stress.",
            "This is a rules-based monitor, not a probability forecast.",
        ),
        "fred_macro_stress_scores.png": (
            "Direct FRED Macro Stress Scores",
            "Direct Macro Layer",
            "Scores CPI, Fed funds, Treasury yields, VIX, credit spreads, unemployment, and financial stress indexes against transparent thresholds.",
            "Scores near 100 indicate more severe macro stress; scores near 0 indicate normal conditions.",
            "FRED series have different release frequencies and may be revised after initial publication.",
        ),
        "fred_macro_crisis_heatmap.png": (
            "Direct FRED Macro Changes By Crisis",
            "Direct Macro Layer",
            "Shows how macro indicators moved inside each historical crisis window.",
            "Positive and negative cells show directional change in each macro series over the crisis window.",
            "Levels and changes are not directly comparable across all series because units differ.",
        ),
        "news_sentiment_category_counts.png": (
            "Live News Classification Counts",
            "News Sentiment",
            "Counts RSS headlines classified into geopolitical escalation, supply shock, inflation shock, liquidity stress, cyber shock, and de-escalation.",
            "Higher bars indicate more headline clustering around that crisis category.",
            "This is keyword triage and should be verified against primary sources.",
        ),
        "portfolio_scenario_stress.png": (
            "Portfolio Scenario Stress",
            "Portfolio Stress",
            "Scores the active or sample portfolio against each modeled scenario.",
            "Negative bars indicate modeled vulnerability; positive bars indicate modeled beneficiary exposure.",
            "Unmapped holdings are not fully represented until classified.",
        ),
        "portfolio_contribution_heatmap.png": (
            "Portfolio Contribution Heatmap",
            "Portfolio Stress",
            "Shows which holdings contribute to scenario vulnerability or benefit.",
            "Rows are scenarios; columns are holdings; color shows weighted contribution.",
            "Results depend on the scenario exposure map and portfolio weights.",
        ),
        "scenario_impact_heatmap.png": (
            "Scenario Impact Heatmap",
            "Scenario Engine",
            "Compares expected impact scores across all scenarios and exposure groups.",
            "Green means expected beneficiary; red means expected pressure.",
            "Impact scores are analyst assumptions, not price targets.",
        ),
        "scenario_macro_impact_matrix.png": (
            "Scenario Macro Impact Matrix",
            "Scenario Engine",
            "Scores each scenario by inflation, growth, liquidity, and supply-chain impact.",
            "Negative growth/liquidity/supply-chain scores imply stress; positive inflation scores imply inflationary pressure.",
            "Macro dimensions are simplified to keep the stress model explainable.",
        ),
        "scenario_risk_map.png": (
            "Scenario Risk Map",
            "Scenario Engine",
            "Plots subjective probability weight versus severity for each scenario.",
            "Larger or higher-positioned points deserve more planning attention.",
            "Probability weights are subjective planning inputs, not actual event probabilities.",
        ),
        "scenario_bucket_impact_heatmap.png": (
            "Scenario Bucket Impact Heatmap",
            "Scenario Engine",
            "Aggregates scenario impacts by resource, sector, company, and technology bucket.",
            "Use it to see which type of exposure matters most in each scenario.",
            "Averages can hide dispersion inside each bucket.",
        ),
        "scenario_summary_table.png": (
            "Scenario Summary Table",
            "Scenario Engine",
            "Summarizes likely growth, likely pressure, and path-dependent exposures for each scenario.",
            "Use it as the quick playbook before reading detailed exposure rows.",
            "It is intentionally concise and should be checked against the detailed CSV.",
        ),
        "scenario_calibrated_weights.png": (
            "Scenario Weights: Base Vs Calibrated",
            "Scenario Calibration",
            "Compares original scenario weights with weights adjusted by historical analogs and current alerts.",
            "Bigger calibrated bars mean that historical severity and current signals lifted planning attention.",
            "These are planning weights, not event probabilities.",
        ),
        "monte_carlo_portfolio_stress_distribution.png": (
            "Monte Carlo Scenario Stress Distribution",
            "Scenario Calibration",
            "Shows the distribution of portfolio stress-return proxies across sampled scenario paths.",
            "The left tail summarizes adverse combinations of modeled scenarios.",
            "Return proxies are stress-scale estimates, not actual return forecasts.",
        ),
        "unified_alert_scores.png": (
            "Unified Crisis Alert Scores",
            "Unified Alerts",
            "Combines market proxies, FRED thresholds, news sentiment, and calibrated scenario weights into one alert chart.",
            "Higher bars show categories with stronger current warning signals.",
            "Alerts depend on data freshness and should be checked after refreshing market and macro inputs.",
        ),
        "crisis_category_resilience_forecast_heatmap.png": (
            "Future Crisis Category Resilience Forecast",
            "Future Crisis Forecast",
            "Shows expected resilience by category for each possible future crisis scenario.",
            "Green cells are categories expected to be more resilient or beneficiary-like; red cells are expected vulnerabilities.",
            "Scores are planning estimates derived from scenario assumptions and historical support, not return forecasts.",
        ),
        "crisis_forecast_attention_scores.png": (
            "Future Crisis Forecast Attention Scores",
            "Future Crisis Forecast",
            "Ranks the largest category exposures after combining expected resilience, calibrated scenario weight, and severity.",
            "Positive bars show categories worth watching as likely beneficiaries; negative bars show major vulnerability areas.",
            "Attention scores prioritize review; they do not imply trade sizing.",
        ),
    }
    if filename in exact:
        return exact[filename]

    if filename.startswith("scenario_") and filename.endswith("_impact_bars.png"):
        scenario = stem.replace("scenario_", "").replace("_impact_bars", "").replace("_", " ").title()
        return (
            f"Scenario Playbook: {scenario}",
            "Scenario Playbooks",
            "Shows expected beneficiaries and pressure points for one forward-looking scenario.",
            "Positive bars are expected beneficiaries; negative bars are expected losers or vulnerable areas.",
            "The scenario assumptions should be reviewed and adjusted as facts change.",
        )

    return (
        title,
        "Other",
        "Generated chart from the model output.",
        "Read the axis labels and compare relative values.",
        caveat,
    )


def _future_improvements_markdown(improvements: pd.DataFrame) -> str:
    lines = [
        "# Future Improvements Roadmap",
        "",
        "These additions would move the project from a static research model toward a live crisis decision-support system.",
        "",
    ]
    for row in improvements.itertuples():
        lines.extend(
            [
                f"## {row.priority}: {row.improvement}",
                "",
                f"Why it matters: {row.why_it_matters}",
                "",
                f"Implementation notes: {row.implementation_notes}",
                "",
            ]
        )
    return "\n".join(lines)


def _full_report_markdown(
    output_dir: Path,
    chart_synopses: pd.DataFrame,
    data_dictionary: pd.DataFrame,
    improvements: pd.DataFrame,
) -> str:
    executive = _read_text(output_dir / "executive_findings.md")
    early_warning = _read_csv(output_dir / "early_warning_summary.csv")
    alerts_summary = _read_csv(output_dir / "alerts_summary.csv")
    scenario_risk = _read_csv(output_dir / "scenario_risk_matrix.csv")
    portfolio_stress = _read_csv(output_dir / "portfolio_scenario_stress.csv")
    monte_carlo_summary = _read_csv(output_dir / "monte_carlo_summary.csv")

    lines = [
        "# Crisis Resilience Market Model: Full Report",
        "",
        "This report consolidates the historical backtest, scenario stress engine, early-warning monitor, portfolio stress test, chart synopses, data dictionary, and recommended next steps.",
        "",
        "Important: this is a historical backtesting and decision-support tool. It does not predict future returns or guarantee protection.",
        "",
        "## Current Snapshot",
        _current_snapshot(early_warning, alerts_summary, scenario_risk, portfolio_stress, monte_carlo_summary),
        "",
        "## Executive Findings",
        executive.replace("# Executive Findings", "").strip(),
        "",
        "## Data Dictionary",
        _markdown_table(data_dictionary),
        "",
        "## Chart Synopses",
        _chart_synopses_markdown(chart_synopses),
        "",
        "## Future Improvements",
        _markdown_table(improvements),
        "",
        "## Operating Notes",
        "- Use `./run_model.sh --force-refresh` to refresh yfinance data and regenerate outputs.",
        "- Use `python main.py --portfolio-file /path/to/portfolio.csv` to score real holdings.",
        "- Use `outputs/crisis_resilience_dashboard.html` for a portable dashboard preview.",
        "- Use `outputs/executive_findings.md` for a compact summary and this file for the full audit trail.",
        "- Use `outputs/simulation_reports_index.md` for presentation-ready crisis simulation case studies.",
        "",
    ]
    return "\n".join(lines)


def _current_snapshot(
    early_warning: pd.DataFrame,
    alerts_summary: pd.DataFrame,
    scenario_risk: pd.DataFrame,
    portfolio_stress: pd.DataFrame,
    monte_carlo_summary: pd.DataFrame,
) -> str:
    lines: list[str] = []
    if not alerts_summary.empty:
        row = alerts_summary.iloc[0]
        lines.append(
            f"- Unified alert level: {row['highest_level']} with "
            f"{row['active_alert_count']} active alert rows."
        )
    if not early_warning.empty:
        row = early_warning.iloc[0]
        lines.append(
            f"- Current regime: {row['regime']} ({row['regime_score']:.1f}/100), "
            f"data freshness {row['data_freshness']} as of {row['latest_date']}."
        )
        lines.append(f"- Active alerts: {row['active_alert_count']}; primary alerts: {row['primary_alerts'] or 'None'}.")
    if not scenario_risk.empty:
        top = scenario_risk.iloc[0]
        lines.append(
            f"- Highest modeled scenario risk: {top['scenario']} "
            f"(risk score {top['scenario_risk_score']:.2f})."
        )
    if not portfolio_stress.empty:
        worst = portfolio_stress.sort_values("portfolio_stress_score").iloc[0]
        lines.append(
            f"- Most negative modeled portfolio scenario: {worst['scenario']} "
            f"(score {worst['portfolio_stress_score']:.2f})."
        )
    if not monte_carlo_summary.empty:
        row = monte_carlo_summary.iloc[0]
        lines.append(
            f"- Monte Carlo 5th percentile stress-return proxy: {row['p05_return_proxy']:.1%}; "
            f"severe downside proxy probability {row['probability_severe_negative_proxy']:.1%}."
        )
    return "\n".join(lines) if lines else "No current snapshot outputs are available."


def _chart_synopses_markdown(chart_synopses: pd.DataFrame) -> str:
    if chart_synopses.empty:
        return "No chart synopses are available."

    lines: list[str] = []
    for section, group in chart_synopses.groupby("section", sort=False):
        lines.extend([f"### {section}", ""])
        for row in group.itertuples():
            lines.extend(
                [
                    f"#### {row.title}",
                    "",
                    f"![{row.title}]({row.chart_file})",
                    "",
                    f"Synopsis: {row.synopsis}",
                    "",
                    f"How to read: {row.how_to_read}",
                    "",
                    f"Caveat: {row.caveat}",
                    "",
                ]
            )
    return "\n".join(lines)


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "No rows available."
    safe = df.copy()
    safe = safe.astype(str)
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


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
