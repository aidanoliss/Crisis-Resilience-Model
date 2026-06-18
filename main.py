"""Command-line entrypoint for the Crisis Resilience Market Model."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from alerts import export_unified_alerts, plot_unified_alerts
from crisis_periods import CRISIS_PERIODS, crisis_union_mask, filter_returns_for_period
from data_loader import (
    BENCHMARK,
    DEFAULT_TICKERS,
    add_asset_names,
    calculate_daily_returns,
    download_adjusted_close,
)
from early_warning import (
    export_early_warning_monitor,
    plot_early_warning_scores,
    plot_regime_gauge,
)
from fred_macro import (
    export_fred_macro_tables,
    plot_fred_macro_crisis_heatmap,
    plot_fred_macro_stress_scores,
)
from forecast_playbook import (
    export_crisis_forecast_playbook,
    plot_crisis_forecast_attention,
    plot_crisis_forecast_heatmap,
)
from news_sentiment import (
    export_news_sentiment_tables,
    plot_news_sentiment_counts,
)
from portfolio_analysis import (
    export_portfolio_stress,
    plot_portfolio_contribution_heatmap,
    plot_portfolio_scenario_stress,
)
from historical_context import (
    add_company_metadata,
    build_context_table,
    build_technology_theme_table,
    company_universe_tickers,
)
from historical_visualizations import (
    build_winner_loser_tables,
    plot_company_winners_by_crisis,
    plot_context_table,
    plot_crisis_return_heatmap,
    plot_historical_crisis_timeline,
    plot_industry_winners_losers_by_crisis,
    plot_resource_importance_heatmap,
    plot_technology_theme_table,
)
from findings_report import generate_executive_findings
from macro_indicators import (
    export_macro_proxy_tables,
    plot_macro_proxy_cumulative_history,
    plot_macro_proxy_drawdown_heatmap,
    plot_macro_proxy_heatmap,
)
from metrics import compute_performance_metrics
from report_pack import generate_report_pack
from reporting import generate_static_dashboard
from scenario_analysis import export_scenario_tables
from scenario_calibration import (
    export_scenario_calibration,
    plot_calibrated_scenario_weights,
    plot_monte_carlo_distribution,
)
from scenario_visualizations import (
    plot_scenario_bars,
    plot_scenario_bucket_heatmap,
    plot_scenario_dimension_heatmap,
    plot_scenario_impact_heatmap,
    plot_scenario_risk_scatter,
    plot_scenario_summary_table,
)
from scoring import score_assets
from simulation_reports import generate_simulation_reports
from visualizations import (
    plot_correlation_heatmap,
    plot_cumulative_returns_by_crisis,
    plot_drawdowns,
    plot_resilience_score_decomposition,
    plot_resilience_score_bars,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest ETF resilience across historical crisis windows."
    )
    parser.add_argument(
        "--start",
        default="2004-01-01",
        help="First date to request from yfinance. Default: 2004-01-01.",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Optional yfinance end date in YYYY-MM-DD format. Default: latest available.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for CSV and chart outputs. Default: outputs.",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore cached prices and download fresh yfinance data.",
    )
    parser.add_argument(
        "--risk-free-rate",
        type=float,
        default=0.0,
        help="Annual risk-free rate used for Sharpe ratio. Default: 0.0.",
    )
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Skip PNG chart generation.",
    )
    parser.add_argument(
        "--skip-company-history",
        action="store_true",
        help="Skip company-level historical winner analysis.",
    )
    parser.add_argument(
        "--skip-scenarios",
        action="store_true",
        help="Skip forward-looking scenario stress tables and charts.",
    )
    parser.add_argument(
        "--skip-macro",
        action="store_true",
        help="Skip macro proxy tables and charts.",
    )
    parser.add_argument(
        "--skip-fred",
        action="store_true",
        help="Skip direct FRED macro data, alerts, and charts.",
    )
    parser.add_argument(
        "--skip-news",
        action="store_true",
        help="Skip live news/RSS sentiment classification.",
    )
    parser.add_argument(
        "--skip-early-warning",
        action="store_true",
        help="Skip crisis early-warning monitor outputs.",
    )
    parser.add_argument(
        "--skip-portfolio",
        action="store_true",
        help="Skip portfolio scenario stress outputs.",
    )
    parser.add_argument(
        "--portfolio-file",
        default=None,
        help="Optional CSV with ticker,weight columns. Default: generated sample portfolio.",
    )
    parser.add_argument(
        "--skip-calibration",
        action="store_true",
        help="Skip historical-analog scenario calibration and Monte Carlo paths.",
    )
    parser.add_argument(
        "--skip-alerts",
        action="store_true",
        help="Skip unified alert feed generation.",
    )
    parser.add_argument(
        "--skip-forecast-playbook",
        action="store_true",
        help="Skip future-crisis category resilience forecast outputs.",
    )
    parser.add_argument(
        "--skip-simulation-reports",
        action="store_true",
        help="Skip publishable crisis simulation case-study Markdown reports.",
    )
    parser.add_argument(
        "--monte-carlo-runs",
        type=int,
        default=10000,
        help="Number of Monte Carlo scenario paths. Default: 10000.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Downloading adjusted close prices...")
    prices = download_adjusted_close(
        tickers=DEFAULT_TICKERS,
        start=args.start,
        end=args.end,
        cache_path=output_dir / "adjusted_close_prices.csv",
        force_refresh=args.force_refresh,
    )
    prices.to_csv(output_dir / "adjusted_close_prices.csv")

    returns = calculate_daily_returns(prices)
    returns.to_csv(output_dir / "daily_returns.csv")

    print("Computing metrics for each crisis window...")
    crisis_returns: dict[str, pd.DataFrame] = {}
    per_crisis_frames: list[pd.DataFrame] = []

    for period in CRISIS_PERIODS:
        period_returns = filter_returns_for_period(returns, period)
        if period_returns.empty:
            print(f"Skipping {period.name}: no return data available.")
            continue

        crisis_returns[period.name] = period_returns
        metrics = compute_performance_metrics(
            period_returns,
            benchmark_col=BENCHMARK,
            risk_free_rate=args.risk_free_rate,
        )
        metrics.insert(0, "crisis", period.name)
        metrics.insert(1, "crisis_start", period.start)
        metrics.insert(2, "crisis_end", period.end)
        metrics.insert(3, "crisis_description", period.description)
        per_crisis_frames.append(metrics)

    if not per_crisis_frames:
        raise RuntimeError("No crisis windows had enough market data to analyze.")

    performance_by_crisis = pd.concat(per_crisis_frames, ignore_index=True)
    performance_by_crisis = add_asset_names(performance_by_crisis)
    performance_by_crisis.to_csv(output_dir / "performance_by_crisis.csv", index=False)

    aggregate_returns = returns.loc[crisis_union_mask(returns.index)].copy()
    aggregate_returns.to_csv(output_dir / "aggregate_crisis_returns.csv")

    print("Computing aggregate crisis metrics and resilience ranking...")
    aggregate_metrics = compute_performance_metrics(
        aggregate_returns,
        benchmark_col=BENCHMARK,
        risk_free_rate=args.risk_free_rate,
    )
    aggregate_metrics = add_asset_names(aggregate_metrics)
    aggregate_metrics.to_csv(output_dir / "aggregate_crisis_metrics.csv", index=False)

    scores = score_assets(aggregate_metrics)
    scores.to_csv(output_dir / "resilience_scores.csv", index=False)

    crisis_table = build_crisis_table()
    crisis_table.to_csv(output_dir / "crisis_periods.csv", index=False)

    context_table = build_context_table()
    context_table.to_csv(output_dir / "historical_context.csv", index=False)

    technology_theme_table = build_technology_theme_table()
    technology_theme_table.to_csv(output_dir / "technology_themes.csv", index=False)

    company_performance_by_crisis = pd.DataFrame()
    if not args.skip_company_history:
        company_performance_by_crisis = run_company_history_analysis(
            args=args,
            output_dir=output_dir,
        )

        if not company_performance_by_crisis.empty:
            etf_winners, etf_losers, company_winners = build_winner_loser_tables(
                performance_by_crisis=performance_by_crisis,
                company_performance_by_crisis=company_performance_by_crisis,
            )
            etf_winners.to_csv(output_dir / "industry_asset_winners_by_crisis.csv", index=False)
            etf_losers.to_csv(output_dir / "industry_asset_losers_by_crisis.csv", index=False)
            company_winners.to_csv(output_dir / "company_winners_by_crisis.csv", index=False)

    scenario_exposures = pd.DataFrame()
    scenario_summary = pd.DataFrame()
    scenario_risk_matrix = pd.DataFrame()
    scenario_bucket_summary = pd.DataFrame()
    if not args.skip_scenarios:
        (
            scenario_exposures,
            scenario_summary,
            scenario_risk_matrix,
            scenario_bucket_summary,
        ) = export_scenario_tables(output_dir)

    macro_summary = pd.DataFrame()
    macro_takeaways = pd.DataFrame()
    if not args.skip_macro:
        macro_summary, macro_takeaways = export_macro_proxy_tables(prices, output_dir)

    early_warning_indicators = pd.DataFrame()
    early_warning_summary = pd.DataFrame()
    if not args.skip_early_warning:
        early_warning_indicators, early_warning_summary = export_early_warning_monitor(
            prices, output_dir
        )

    fred_macro_data = pd.DataFrame()
    fred_latest = pd.DataFrame()
    fred_crisis_summary = pd.DataFrame()
    fred_alerts = pd.DataFrame()
    if not args.skip_fred:
        print("Pulling direct FRED macro series...")
        fred_macro_data, fred_latest, fred_crisis_summary, fred_alerts = export_fred_macro_tables(
            output_dir,
            force_refresh=args.force_refresh,
        )

    news_items = pd.DataFrame()
    news_summary = pd.DataFrame()
    news_alerts = pd.DataFrame()
    if not args.skip_news:
        print("Classifying live news sentiment...")
        news_items, news_summary, news_alerts = export_news_sentiment_tables(
            output_dir,
            force_refresh=args.force_refresh,
        )

    portfolio = pd.DataFrame()
    portfolio_stress = pd.DataFrame()
    portfolio_contributions = pd.DataFrame()
    if not args.skip_portfolio and not scenario_exposures.empty:
        portfolio, portfolio_stress, portfolio_contributions = export_portfolio_stress(
            args.portfolio_file,
            output_dir,
            scenario_exposures,
        )

    calibrated_scenarios = pd.DataFrame()
    monte_carlo_paths = pd.DataFrame()
    monte_carlo_summary = pd.DataFrame()
    if not args.skip_calibration and not scenario_risk_matrix.empty:
        print("Calibrating scenario weights and running Monte Carlo paths...")
        calibrated_scenarios, monte_carlo_paths, monte_carlo_summary = export_scenario_calibration(
            output_dir=output_dir,
            scenario_risk_matrix=scenario_risk_matrix,
            performance_by_crisis=performance_by_crisis,
            portfolio_stress=portfolio_stress,
            early_warning_indicators=early_warning_indicators,
            fred_alerts=fred_alerts,
            news_summary=news_summary,
            runs=args.monte_carlo_runs,
        )

    unified_alerts = pd.DataFrame()
    alerts_summary = pd.DataFrame()
    if not args.skip_alerts:
        print("Building unified crisis alert feed...")
        unified_alerts, alerts_summary = export_unified_alerts(
            output_dir=output_dir,
            early_warning_indicators=early_warning_indicators,
            fred_alerts=fred_alerts,
            news_alerts=news_alerts,
            calibrated_scenarios=calibrated_scenarios,
        )

    crisis_forecast = pd.DataFrame()
    crisis_forecast_summary = pd.DataFrame()
    if (
        not args.skip_forecast_playbook
        and not scenario_exposures.empty
        and not scores.empty
    ):
        print("Building future-crisis category resilience forecast...")
        crisis_forecast, crisis_forecast_summary = export_crisis_forecast_playbook(
            output_dir=output_dir,
            scenario_exposures=scenario_exposures,
            calibrated_scenarios=calibrated_scenarios,
            resilience_scores=scores,
        )

    if not args.no_charts:
        print("Generating charts...")
        plot_cumulative_returns_by_crisis(
            crisis_returns,
            output_dir / "charts",
            benchmark_col=BENCHMARK,
        )
        plot_drawdowns(
            aggregate_returns,
            output_dir / "charts" / "drawdowns_all_crises.png",
            benchmark_col=BENCHMARK,
        )
        plot_correlation_heatmap(
            aggregate_returns,
            output_dir / "charts" / "correlation_heatmap.png",
        )
        plot_resilience_score_bars(
            scores,
            output_dir / "charts" / "resilience_score_ranking.png",
        )
        plot_resilience_score_decomposition(
            scores,
            output_dir / "charts" / "resilience_score_decomposition.png",
        )
        print("Generating historical narrative charts...")
        plot_historical_crisis_timeline(
            context_table,
            performance_by_crisis,
            output_dir / "charts" / "historical_crisis_timeline.png",
        )
        plot_crisis_return_heatmap(
            performance_by_crisis,
            output_dir / "charts" / "crisis_sector_asset_return_heatmap.png",
            title="Sector and Asset-Class Returns by Crisis",
        )
        plot_industry_winners_losers_by_crisis(
            performance_by_crisis,
            output_dir / "charts" / "industry_winners_losers_by_crisis.png",
        )
        plot_resource_importance_heatmap(
            performance_by_crisis,
            output_dir / "charts" / "resource_importance_by_crisis.png",
        )
        plot_context_table(
            context_table,
            output_dir / "charts" / "historical_context_table.png",
        )
        plot_technology_theme_table(
            technology_theme_table,
            output_dir / "charts" / "technology_themes_table.png",
        )
        if not company_performance_by_crisis.empty:
            plot_company_winners_by_crisis(
                company_performance_by_crisis,
                output_dir / "charts" / "company_winners_by_crisis.png",
            )
        if not scenario_exposures.empty:
            print("Generating forward-looking scenario charts...")
            plot_scenario_impact_heatmap(
                scenario_exposures,
                output_dir / "charts" / "scenario_impact_heatmap.png",
            )
            plot_scenario_bars(
                scenario_exposures,
                output_dir / "charts",
            )
            plot_scenario_summary_table(
                scenario_summary,
                output_dir / "charts" / "scenario_summary_table.png",
            )
            plot_scenario_dimension_heatmap(
                scenario_risk_matrix,
                output_dir / "charts" / "scenario_macro_impact_matrix.png",
            )
            plot_scenario_risk_scatter(
                scenario_risk_matrix,
                output_dir / "charts" / "scenario_risk_map.png",
            )
            plot_scenario_bucket_heatmap(
                scenario_bucket_summary,
                output_dir / "charts" / "scenario_bucket_impact_heatmap.png",
            )
        if not macro_summary.empty:
            print("Generating macro proxy charts...")
            plot_macro_proxy_heatmap(
                macro_summary,
                output_dir / "charts" / "macro_proxy_return_heatmap.png",
            )
            plot_macro_proxy_drawdown_heatmap(
                macro_summary,
                output_dir / "charts" / "macro_proxy_drawdown_heatmap.png",
            )
            plot_macro_proxy_cumulative_history(
                prices,
                output_dir / "charts" / "macro_proxy_normalized_history.png",
            )
        if not early_warning_indicators.empty:
            print("Generating early-warning charts...")
            plot_early_warning_scores(
                early_warning_indicators,
                output_dir / "charts" / "early_warning_scores.png",
            )
            plot_regime_gauge(
                early_warning_summary,
                output_dir / "charts" / "early_warning_regime_gauge.png",
            )
        if not fred_latest.empty:
            print("Generating direct FRED macro charts...")
            plot_fred_macro_stress_scores(
                fred_latest,
                output_dir / "charts" / "fred_macro_stress_scores.png",
            )
            plot_fred_macro_crisis_heatmap(
                fred_crisis_summary,
                output_dir / "charts" / "fred_macro_crisis_heatmap.png",
            )
        if not news_summary.empty:
            print("Generating news sentiment charts...")
            plot_news_sentiment_counts(
                news_summary,
                output_dir / "charts" / "news_sentiment_category_counts.png",
            )
        if not portfolio_stress.empty:
            print("Generating portfolio stress charts...")
            plot_portfolio_scenario_stress(
                portfolio_stress,
                output_dir / "charts" / "portfolio_scenario_stress.png",
            )
            plot_portfolio_contribution_heatmap(
                portfolio_contributions,
                output_dir / "charts" / "portfolio_contribution_heatmap.png",
            )
        if not calibrated_scenarios.empty:
            print("Generating scenario calibration charts...")
            plot_calibrated_scenario_weights(
                calibrated_scenarios,
                output_dir / "charts" / "scenario_calibrated_weights.png",
            )
            plot_monte_carlo_distribution(
                monte_carlo_paths,
                output_dir / "charts" / "monte_carlo_portfolio_stress_distribution.png",
            )
        if not unified_alerts.empty:
            print("Generating unified alert chart...")
            plot_unified_alerts(
                unified_alerts,
                output_dir / "charts" / "unified_alert_scores.png",
            )
        if not crisis_forecast.empty:
            print("Generating future-crisis forecast charts...")
            plot_crisis_forecast_heatmap(
                crisis_forecast,
                output_dir / "charts" / "crisis_category_resilience_forecast_heatmap.png",
            )
            plot_crisis_forecast_attention(
                crisis_forecast,
                output_dir / "charts" / "crisis_forecast_attention_scores.png",
            )

    simulation_report_paths: dict[str, Path] = {}
    if not args.skip_simulation_reports:
        print("Generating publishable simulation case studies...")
        simulation_report_paths = generate_simulation_reports(output_dir)

    findings_path = generate_executive_findings(output_dir)
    report_pack_paths = generate_report_pack(output_dir)
    report_path = generate_static_dashboard(output_dir)
    print(f"Executive findings saved to: {findings_path.resolve()}")
    print(f"Full report saved to: {report_pack_paths['full_report'].resolve()}")
    if "index" in simulation_report_paths:
        print(f"Simulation reports saved to: {simulation_report_paths['index'].resolve()}")
    print(f"Static dashboard saved to: {report_path.resolve()}")
    print_summary(scores, output_dir)


def build_crisis_table() -> pd.DataFrame:
    """Build an exportable table of crisis windows."""

    return pd.DataFrame(
        [
            {
                "crisis": period.name,
                "start": period.start,
                "end": period.end,
                "description": period.description,
            }
            for period in CRISIS_PERIODS
        ]
    )


def run_company_history_analysis(args: argparse.Namespace, output_dir: Path) -> pd.DataFrame:
    """Download company prices and calculate winners inside each crisis window."""

    print("Downloading company prices for historical winner analysis...")
    company_tickers = company_universe_tickers()
    company_prices = download_adjusted_close(
        tickers=[BENCHMARK] + company_tickers,
        start=args.start,
        end=args.end,
        cache_path=output_dir / "company_adjusted_close_prices.csv",
        force_refresh=args.force_refresh,
    )
    company_prices.to_csv(output_dir / "company_adjusted_close_prices.csv")

    company_returns = calculate_daily_returns(company_prices)
    company_returns.to_csv(output_dir / "company_daily_returns.csv")

    frames: list[pd.DataFrame] = []
    for period in CRISIS_PERIODS:
        period_returns = filter_returns_for_period(company_returns, period)
        if period_returns.empty:
            continue

        available_columns = [
            column for column in period_returns.columns if period_returns[column].notna().any()
        ]
        if BENCHMARK not in available_columns or len(available_columns) < 2:
            continue

        metrics = compute_performance_metrics(
            period_returns[available_columns],
            benchmark_col=BENCHMARK,
            risk_free_rate=args.risk_free_rate,
        )
        metrics = metrics[metrics["ticker"].isin(company_tickers)].copy()
        metrics.insert(0, "crisis", period.name)
        metrics.insert(1, "crisis_start", period.start)
        metrics.insert(2, "crisis_end", period.end)
        metrics.insert(3, "crisis_description", period.description)
        frames.append(metrics)

    if not frames:
        print("Company history analysis skipped: no usable company return data.")
        return pd.DataFrame()

    company_performance = pd.concat(frames, ignore_index=True)
    company_performance = add_company_metadata(company_performance)
    company_performance.to_csv(output_dir / "company_performance_by_crisis.csv", index=False)
    return company_performance


def print_summary(scores: pd.DataFrame, output_dir: Path) -> None:
    """Print a compact terminal summary after the run finishes."""

    columns = [
        "rank",
        "ticker",
        "asset_name",
        "crisis_resilience_score",
        "total_return",
        "max_drawdown",
        "volatility",
        "correlation_to_spy",
    ]
    top = scores.loc[:, columns].head(10).copy()

    percent_cols = ["total_return", "max_drawdown", "volatility"]
    for column in percent_cols:
        top[column] = top[column].map(lambda value: f"{value:.2%}")
    top["correlation_to_spy"] = top["correlation_to_spy"].map(lambda value: f"{value:.2f}")
    top["crisis_resilience_score"] = top["crisis_resilience_score"].map(
        lambda value: f"{value:.1f}"
    )

    print("\nTop crisis resilience rankings:")
    print(top.to_string(index=False))
    print(f"\nSaved results to: {output_dir.resolve()}")
    print("This is a historical decision-support backtest, not a forecast.")


if __name__ == "__main__":
    main()
