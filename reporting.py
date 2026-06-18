"""Static HTML reporting for the crisis resilience project."""

from __future__ import annotations

from pathlib import Path
import html

import pandas as pd


def generate_static_dashboard(output_dir: str | Path) -> Path:
    """Generate a dependency-free HTML dashboard from existing CSVs and charts."""

    output_path = Path(output_dir)
    chart_path = output_path / "charts"
    report_path = output_path / "crisis_resilience_dashboard.html"

    scores = _read_csv(output_path / "resilience_scores.csv")
    scenario_risk = _read_csv(output_path / "scenario_risk_matrix.csv")
    scenario_summary = _read_csv(output_path / "scenario_summary.csv")
    bucket_summary = _read_csv(output_path / "scenario_bucket_summary.csv")
    macro_takeaways = _read_csv(output_path / "macro_proxy_takeaways.csv")
    early_warning_summary = _read_csv(output_path / "early_warning_summary.csv")
    early_warning_indicators = _read_csv(output_path / "early_warning_indicators.csv")
    fred_latest = _read_csv(output_path / "fred_macro_latest.csv")
    fred_alerts = _read_csv(output_path / "fred_macro_alerts.csv")
    news_summary = _read_csv(output_path / "news_sentiment_summary.csv")
    news_alerts = _read_csv(output_path / "news_alerts.csv")
    portfolio = _read_csv(output_path / "active_portfolio.csv")
    portfolio_stress = _read_csv(output_path / "portfolio_scenario_stress.csv")
    calibrated_scenarios = _read_csv(output_path / "scenario_calibrated_weights.csv")
    monte_carlo_summary = _read_csv(output_path / "monte_carlo_summary.csv")
    crisis_forecast = _read_csv(output_path / "crisis_category_resilience_forecast.csv")
    crisis_forecast_summary = _read_csv(output_path / "crisis_forecast_summary.csv")
    unified_alerts = _read_csv(output_path / "alerts.csv")
    alerts_summary = _read_csv(output_path / "alerts_summary.csv")
    chart_synopses = _read_csv(output_path / "chart_synopses.csv")
    data_dictionary = _read_csv(output_path / "data_dictionary.csv")

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Crisis Resilience Market Model</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #17202a;
      --muted: #5b6773;
      --line: #d9dee5;
      --accent: #0f766e;
      --danger: #b91c1c;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    header {{
      padding: 28px 36px 18px;
      background: #111827;
      color: white;
    }}
    header p {{
      margin: 8px 0 0;
      color: #d1d5db;
      max-width: 920px;
    }}
    main {{
      padding: 24px 36px 40px;
      max-width: 1500px;
      margin: 0 auto;
    }}
    section {{
      margin: 0 0 28px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px;
    }}
    h1, h2, h3 {{
      margin: 0 0 12px;
      line-height: 1.15;
    }}
    h2 {{
      font-size: 22px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 18px;
      align-items: start;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}
    .metric {{
      background: #f8fafc;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .metric .label {{
      color: var(--muted);
      font-size: 13px;
    }}
    .metric .value {{
      margin-top: 4px;
      font-size: 22px;
      font-weight: 700;
    }}
    figure {{
      margin: 0;
    }}
    img {{
      display: block;
      max-width: 100%;
      height: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
    }}
    figcaption {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      background: white;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 8px 10px;
      vertical-align: top;
      text-align: left;
    }}
    th {{
      background: #f1f5f9;
      font-weight: 700;
    }}
    .note {{
      color: var(--muted);
      font-size: 14px;
    }}
    .wide {{
      overflow-x: auto;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Crisis Resilience Market Model</h1>
    <p>Historical crisis backtesting, scenario stress scoring, and visual decision support. This is not a prediction engine or investment advice.</p>
  </header>
  <main>
    <section>
      <h2>Executive Snapshot</h2>
      <p class="note">
        <a href="executive_findings.md">Executive findings</a> |
        <a href="full_report.md">Full report</a> |
        <a href="simulation_reports_index.md">Simulation reports</a> |
        <a href="future_improvements.md">Future improvements</a> |
        <a href="chart_synopses.csv">Chart synopses CSV</a> |
        <a href="data_dictionary.csv">Data dictionary CSV</a>
      </p>
      {build_metric_grid(scores, scenario_risk, early_warning_summary, alerts_summary, monte_carlo_summary)}
      <div class="grid">
        {chart_figure(chart_path, "unified_alert_scores.png", "Unified crisis alert scores")}
        {chart_figure(chart_path, "early_warning_regime_gauge.png", "Current early-warning regime")}
        {chart_figure(chart_path, "scenario_risk_map.png", "Scenario risk map")}
        {chart_figure(chart_path, "resilience_score_ranking.png", "Historical resilience ranking")}
        {chart_figure(chart_path, "resilience_score_decomposition.png", "Resilience score decomposition")}
      </div>
    </section>

    <section>
      <h2>Crisis Early Warning Monitor</h2>
      <p class="note">This monitor uses the latest available cached market data to classify current market stress. Re-run with --force-refresh to update prices.</p>
      <div class="grid">
        {chart_figure(chart_path, "early_warning_scores.png", "Early-warning stress scores")}
        {chart_figure(chart_path, "early_warning_regime_gauge.png", "Regime gauge")}
      </div>
      <h3>Indicator Table</h3>
      <div class="wide">{dataframe_to_html(format_early_warning_table(early_warning_indicators))}</div>
    </section>

    <section>
      <h2>Unified Alert Layer</h2>
      <p class="note">Combines VIX, credit spreads, rates, oil/dollar proxy signals, FRED stress indicators, news classification, and calibrated scenario weights.</p>
      <div class="grid">
        {chart_figure(chart_path, "unified_alert_scores.png", "Unified alert scores")}
        {chart_figure(chart_path, "fred_macro_stress_scores.png", "Direct FRED macro stress scores")}
      </div>
      <h3>Alert Summary</h3>
      <div class="wide">{dataframe_to_html(alerts_summary)}</div>
      <h3>Active Alerts</h3>
      <div class="wide">{dataframe_to_html(unified_alerts)}</div>
    </section>

    <section>
      <h2>Direct FRED Macro Layer</h2>
      <p class="note">Direct macro series include CPI, Fed funds, 2Y/10Y yields, VIX, credit spreads, unemployment, and financial stress indexes.</p>
      <div class="grid">
        {chart_figure(chart_path, "fred_macro_stress_scores.png", "FRED macro stress scores")}
        {chart_figure(chart_path, "fred_macro_crisis_heatmap.png", "FRED macro crisis heatmap")}
      </div>
      <h3>Latest Macro Readings</h3>
      <div class="wide">{dataframe_to_html(fred_latest)}</div>
      <h3>Macro Threshold Alerts</h3>
      <div class="wide">{dataframe_to_html(fred_alerts)}</div>
    </section>

    <section>
      <h2>Live News Classification</h2>
      <p class="note">RSS headlines are classified into geopolitical escalation, supply shock, inflation shock, liquidity stress, cyber shock, and de-escalation buckets.</p>
      <div class="grid">
        {chart_figure(chart_path, "news_sentiment_category_counts.png", "News classification counts")}
      </div>
      <h3>News Sentiment Summary</h3>
      <div class="wide">{dataframe_to_html(news_summary)}</div>
      <h3>News Alerts</h3>
      <div class="wide">{dataframe_to_html(news_alerts)}</div>
    </section>

    <section>
      <h2>Portfolio Stress Test</h2>
      <p class="note">Default output uses sample_portfolio.csv unless a custom --portfolio-file is supplied.</p>
      <div class="grid">
        {chart_figure(chart_path, "portfolio_scenario_stress.png", "Portfolio scenario stress")}
        {chart_figure(chart_path, "portfolio_contribution_heatmap.png", "Portfolio contribution heatmap")}
      </div>
      <h3>Active Portfolio</h3>
      <div class="wide">{dataframe_to_html(portfolio)}</div>
      <h3>Scenario Scores</h3>
      <div class="wide">{dataframe_to_html(portfolio_stress)}</div>
    </section>

    <section>
      <h2>Scenario Calibration And Monte Carlo</h2>
      <p class="note">Base scenario weights are adjusted with historical analog severity and current alert signals, then sampled through Monte Carlo paths. Return proxies are stress-scale estimates, not forecasts.</p>
      <div class="grid">
        {chart_figure(chart_path, "scenario_calibrated_weights.png", "Base vs calibrated scenario weights")}
        {chart_figure(chart_path, "monte_carlo_portfolio_stress_distribution.png", "Monte Carlo stress distribution")}
      </div>
      <h3>Calibrated Scenario Weights</h3>
      <div class="wide">{dataframe_to_html(calibrated_scenarios)}</div>
      <h3>Monte Carlo Summary</h3>
      <div class="wide">{dataframe_to_html(monte_carlo_summary)}</div>
    </section>

    <section>
      <h2>Future Crisis Resilience Forecast</h2>
      <p class="note">This playbook translates possible future crises into expected category resilience. Scores combine scenario assumptions, calibrated scenario weights, and historical crisis behavior. They are planning scores, not return forecasts.</p>
      <p class="note">
        Case studies:
        <a href="simulation_taiwan_conflict.md">Taiwan conflict</a> |
        <a href="simulation_middle_east_energy_shock.md">Middle East energy shock</a> |
        <a href="simulation_credit_liquidity_crisis.md">Credit/liquidity crisis</a>
      </p>
      <div class="grid">
        {chart_figure(chart_path, "crisis_category_resilience_forecast_heatmap.png", "Future crisis category resilience heatmap")}
        {chart_figure(chart_path, "crisis_forecast_attention_scores.png", "Highest attention forecast category exposures")}
      </div>
      <h3>Forecast Summary</h3>
      <div class="wide">{dataframe_to_html(crisis_forecast_summary)}</div>
      <h3>Category Forecast Detail</h3>
      <div class="wide">{dataframe_to_html(crisis_forecast)}</div>
    </section>


    <section>
      <h2>Macro Proxy Layer</h2>
      <p class="note">Macro proxies use liquid instruments already in the model: gold, oil, dollar, Treasuries, equities, financials, energy, real estate, staples, and technology.</p>
      <div class="grid">
        {chart_figure(chart_path, "macro_proxy_return_heatmap.png", "Macro proxy crisis returns")}
        {chart_figure(chart_path, "macro_proxy_drawdown_heatmap.png", "Macro proxy crisis drawdowns")}
        {chart_figure(chart_path, "macro_proxy_normalized_history.png", "Macro proxy normalized history")}
      </div>
      <h3>Macro Takeaways</h3>
      <div class="wide">{dataframe_to_html(macro_takeaways)}</div>
    </section>

    <section>
      <h2>Forward-Looking Scenario Engine</h2>
      <p class="note">Stress scores are analyst-defined assumptions from -5 pressure to +5 beneficiary.</p>
      <div class="grid">
        {chart_figure(chart_path, "scenario_impact_heatmap.png", "Scenario impact heatmap")}
        {chart_figure(chart_path, "scenario_macro_impact_matrix.png", "Macro impact matrix")}
        {chart_figure(chart_path, "scenario_bucket_impact_heatmap.png", "Bucket impact heatmap")}
        {chart_figure(chart_path, "scenario_summary_table.png", "Scenario summary table")}
      </div>
      <h3>Scenario Summary</h3>
      <div class="wide">{dataframe_to_html(scenario_summary)}</div>
    </section>

    <section>
      <h2>Scenario Playbooks</h2>
      <div class="grid">
        {scenario_chart_grid(chart_path)}
      </div>
    </section>

    <section>
      <h2>Historical Crisis Evidence</h2>
      <div class="grid">
        {chart_figure(chart_path, "historical_crisis_timeline.png", "Historical crisis timeline")}
        {chart_figure(chart_path, "crisis_sector_asset_return_heatmap.png", "Sector and asset-class crisis returns")}
        {chart_figure(chart_path, "resource_importance_by_crisis.png", "Resources and defensive assets")}
        {chart_figure(chart_path, "company_winners_by_crisis.png", "Company winners by crisis")}
      </div>
    </section>

    <section>
      <h2>Chart Synopses</h2>
      <p class="note">Every generated chart is documented with a synopsis, reading guide, and caveat.</p>
      <div class="wide">{dataframe_to_html(chart_synopses)}</div>
    </section>

    <section>
      <h2>Data Dictionary</h2>
      <p class="note">Every generated CSV is documented with row counts, columns, and purpose.</p>
      <div class="wide">{dataframe_to_html(data_dictionary)}</div>
    </section>

    <section>
      <h2>Top Historical Crisis Scores</h2>
      <div class="wide">{dataframe_to_html(format_score_table(scores))}</div>
    </section>

    <section>
      <h2>Scenario Risk Matrix</h2>
      <div class="wide">{dataframe_to_html(format_risk_table(scenario_risk))}</div>
      <h3>Bucket Summary</h3>
      <div class="wide">{dataframe_to_html(bucket_summary)}</div>
    </section>
  </main>
</body>
</html>
"""
    report_path.write_text(html_doc, encoding="utf-8")
    return report_path


def build_metric_grid(
    scores: pd.DataFrame,
    scenario_risk: pd.DataFrame,
    early_warning_summary: pd.DataFrame,
    alerts_summary: pd.DataFrame,
    monte_carlo_summary: pd.DataFrame,
) -> str:
    metrics: list[tuple[str, str]] = []
    if not alerts_summary.empty:
        current_alerts = alerts_summary.iloc[0]
        metrics.append(("Unified alert level", str(current_alerts["highest_level"])))
        metrics.append(("Active alert count", str(current_alerts["active_alert_count"])))
    if not early_warning_summary.empty:
        current = early_warning_summary.iloc[0]
        metrics.append(("Current market regime", str(current["regime"])))
        metrics.append(("Regime score", f"{current['regime_score']:.1f}/100"))
        metrics.append(("Data freshness", f"{current['data_freshness']} ({current['latest_date']})"))
    if not scores.empty:
        top = scores.dropna(subset=["crisis_resilience_score"]).iloc[0]
        metrics.append(("Top historical crisis asset", str(top["ticker"])))
        metrics.append(("Top historical score", f"{top['crisis_resilience_score']:.1f}"))
    if not scenario_risk.empty:
        highest = scenario_risk.iloc[0]
        metrics.append(("Highest modeled scenario risk", str(highest["scenario"])))
        metrics.append(("Scenario risk score", f"{highest['scenario_risk_score']:.2f}"))
    if not monte_carlo_summary.empty:
        mc = monte_carlo_summary.iloc[0]
        metrics.append(("Monte Carlo 5th pct proxy", f"{mc['p05_return_proxy']:.1%}"))
        metrics.append(("Severe downside proxy", f"{mc['probability_severe_negative_proxy']:.1%}"))

    cards = "\n".join(
        f"""<div class="metric"><div class="label">{html.escape(label)}</div><div class="value">{html.escape(value)}</div></div>"""
        for label, value in metrics
    )
    return f'<div class="metric-grid">{cards}</div>'


def chart_figure(chart_dir: Path, filename: str, caption: str) -> str:
    path = chart_dir / filename
    if not path.exists():
        return f"<p class=\"note\">Missing chart: {html.escape(filename)}</p>"
    rel_path = Path("charts") / filename
    return (
        "<figure>"
        f'<img src="{html.escape(str(rel_path))}" alt="{html.escape(caption)}">'
        f"<figcaption>{html.escape(caption)}</figcaption>"
        "</figure>"
    )


def scenario_chart_grid(chart_dir: Path) -> str:
    scenario_charts = sorted(chart_dir.glob("scenario_*_impact_bars.png"))
    return "\n".join(
        chart_figure(chart_dir, path.name, path.stem.replace("_", " ").title())
        for path in scenario_charts
    )


def dataframe_to_html(df: pd.DataFrame) -> str:
    if df.empty:
        return '<p class="note">No data available.</p>'
    return df.to_html(index=False, escape=True)


def format_score_table(scores: pd.DataFrame) -> pd.DataFrame:
    if scores.empty:
        return scores
    cols = [
        "rank",
        "ticker",
        "asset_name",
        "crisis_resilience_score",
        "total_return",
        "max_drawdown",
        "volatility",
        "correlation_to_spy",
    ]
    table = scores[cols].head(12).copy()
    for col in ["total_return", "max_drawdown", "volatility"]:
        table[col] = table[col].map(lambda value: f"{value:.2%}")
    table["crisis_resilience_score"] = table["crisis_resilience_score"].map(
        lambda value: f"{value:.1f}"
    )
    table["correlation_to_spy"] = table["correlation_to_spy"].map(lambda value: f"{value:.2f}")
    return table


def format_risk_table(risk: pd.DataFrame) -> pd.DataFrame:
    if risk.empty:
        return risk
    cols = [
        "scenario",
        "probability_weight",
        "severity_score",
        "inflation_impact",
        "growth_impact",
        "liquidity_impact",
        "supply_chain_impact",
        "scenario_risk_score",
        "trigger_definition",
    ]
    return risk[cols].copy()


def format_early_warning_table(indicators: pd.DataFrame) -> pd.DataFrame:
    if indicators.empty:
        return indicators
    table = indicators[
        [
            "indicator",
            "ticker",
            "stress_level",
            "stress_score",
            "signal",
            "signal_value",
            "return_21d",
            "return_63d",
            "drawdown_252d",
            "realized_vol_21d",
            "interpretation",
        ]
    ].copy()
    for col in ["signal_value", "return_21d", "return_63d", "drawdown_252d", "realized_vol_21d"]:
        table[col] = table[col].map(lambda value: f"{value:.2%}")
    return table


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)
