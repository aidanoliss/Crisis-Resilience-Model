"""Streamlit dashboard for the Crisis Resilience Market Model."""

from __future__ import annotations

from pathlib import Path
import re

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


OUTPUT_DIR = Path("outputs")
CHART_DIR = OUTPUT_DIR / "charts"


st.set_page_config(
    page_title="Crisis Resilience Market Model",
    layout="wide",
)


@st.cache_data
def load_csv(path: str) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    return pd.read_csv(file_path)


def main() -> None:
    st.title("Crisis Resilience Market Model")
    st.caption("Historical backtesting plus forward-looking scenario stress tests. Not investment advice.")

    scores = load_csv(str(OUTPUT_DIR / "resilience_scores.csv"))
    performance = load_csv(str(OUTPUT_DIR / "performance_by_crisis.csv"))
    scenario_exposures = load_csv(str(OUTPUT_DIR / "scenario_exposures.csv"))
    scenario_summary = load_csv(str(OUTPUT_DIR / "scenario_summary.csv"))
    scenario_risk = load_csv(str(OUTPUT_DIR / "scenario_risk_matrix.csv"))
    scenario_buckets = load_csv(str(OUTPUT_DIR / "scenario_bucket_summary.csv"))
    early_warning = load_csv(str(OUTPUT_DIR / "early_warning_indicators.csv"))
    early_warning_summary = load_csv(str(OUTPUT_DIR / "early_warning_summary.csv"))
    saved_portfolio = load_csv(str(OUTPUT_DIR / "active_portfolio.csv"))
    saved_portfolio_stress = load_csv(str(OUTPUT_DIR / "portfolio_scenario_stress.csv"))

    tabs = st.tabs(
        [
            "Overview",
            "Early Warning",
            "Historical Resilience",
            "Scenario Engine",
            "Portfolio Stress",
            "Data Tables",
        ]
    )

    with tabs[0]:
        render_overview(scores, scenario_risk, early_warning_summary)

    with tabs[1]:
        render_early_warning(early_warning, early_warning_summary)

    with tabs[2]:
        render_historical(scores, performance)

    with tabs[3]:
        render_scenarios(scenario_exposures, scenario_summary, scenario_risk, scenario_buckets)

    with tabs[4]:
        render_portfolio_stress(scenario_exposures, saved_portfolio, saved_portfolio_stress)

    with tabs[5]:
        render_tables(scores, performance, scenario_exposures, scenario_risk)


def render_overview(
    scores: pd.DataFrame,
    scenario_risk: pd.DataFrame,
    early_warning_summary: pd.DataFrame,
) -> None:
    col1, col2, col3, col4 = st.columns(4)
    if not early_warning_summary.empty:
        current = early_warning_summary.iloc[0]
        col1.metric("Current Regime", current["regime"])
        col2.metric("Regime Score", f"{current['regime_score']:.1f}/100")
        st.caption(
            f"Early-warning data freshness: {current.get('data_freshness', 'Unknown')} "
            f"as of {current.get('latest_date', 'n/a')}"
        )
    if not scores.empty:
        top_asset = scores.dropna(subset=["crisis_resilience_score"]).iloc[0]
        col3.metric("Top Crisis Asset", top_asset["ticker"])
    if not scenario_risk.empty:
        highest_risk = scenario_risk.sort_values("scenario_risk_score", ascending=False).iloc[0]
        col4.metric("Highest Scenario Risk", highest_risk["scenario"])

    show_chart("early_warning_regime_gauge.png", "Current Regime Gauge")
    show_chart("scenario_risk_map.png", "Scenario Risk Map")
    show_chart("resilience_score_ranking.png", "Historical Resilience Ranking")


def render_early_warning(indicators: pd.DataFrame, summary: pd.DataFrame) -> None:
    st.subheader("Crisis Early Warning Monitor")
    if summary.empty:
        st.warning("Run `python main.py` to generate early-warning outputs.")
        return

    current = summary.iloc[0]
    cols = st.columns(4)
    cols[0].metric("Regime", current["regime"])
    cols[1].metric("Regime Score", f"{current['regime_score']:.1f}/100")
    cols[2].metric("Active Alerts", int(current["active_alert_count"]))
    cols[3].metric("Latest Date", current["latest_date"])
    st.caption(
        f"Data freshness: {current.get('data_freshness', 'Unknown')} "
        f"({current.get('data_age_days', 'n/a')} days old)"
    )

    show_chart("early_warning_scores.png", "Early Warning Scores")
    show_chart("early_warning_regime_gauge.png", "Regime Gauge")
    if not indicators.empty:
        st.dataframe(format_percent_columns(indicators), use_container_width=True)


def render_historical(scores: pd.DataFrame, performance: pd.DataFrame) -> None:
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Historical Resilience Ranking")
        if not scores.empty:
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
            st.dataframe(format_percent_columns(scores[cols]), use_container_width=True)
    with right:
        st.subheader("Crisis Return Heatmap")
        show_chart("crisis_sector_asset_return_heatmap.png", "Sector and Asset Returns")

    st.subheader("Historical Context")
    show_chart("historical_crisis_timeline.png", "Historical Crisis Timeline")
    show_chart("company_winners_by_crisis.png", "Company Winners by Crisis")

    if not performance.empty:
        selected_crisis = st.selectbox(
            "Crisis period",
            list(dict.fromkeys(performance["crisis"])),
        )
        crisis_data = performance[performance["crisis"] == selected_crisis].copy()
        crisis_data = crisis_data.sort_values("total_return", ascending=False)
        st.dataframe(
            format_percent_columns(
                crisis_data[
                    [
                        "ticker",
                        "asset_name",
                        "total_return",
                        "max_drawdown",
                        "volatility",
                        "beta_to_spy",
                        "correlation_to_spy",
                    ]
                ]
            ),
            use_container_width=True,
        )


def render_scenarios(
    exposures: pd.DataFrame,
    summary: pd.DataFrame,
    risk: pd.DataFrame,
    bucket_summary: pd.DataFrame,
) -> None:
    if exposures.empty:
        st.warning("Run `python main.py` to generate scenario outputs.")
        return

    selected = st.selectbox("Scenario", list(dict.fromkeys(exposures["scenario"])))
    scenario_rows = exposures[exposures["scenario"] == selected].sort_values("impact_score")
    scenario_summary = summary[summary["scenario"] == selected]

    if not scenario_summary.empty:
        st.dataframe(scenario_summary, use_container_width=True, hide_index=True)

    render_impact_bar(scenario_rows, title=selected)

    st.subheader("Scenario Assumptions")
    assumption_cols = [
        "bucket",
        "ticker_or_theme",
        "name",
        "expected_direction",
        "impact_score",
        "confidence",
        "rationale",
        "key_risk_to_view",
    ]
    st.dataframe(scenario_rows[assumption_cols], use_container_width=True, hide_index=True)

    left, right = st.columns(2)
    with left:
        show_chart("scenario_macro_impact_matrix.png", "Macro Impact Matrix")
    with right:
        show_chart("scenario_bucket_impact_heatmap.png", "Bucket Impact Heatmap")

    if not risk.empty:
        st.subheader("Scenario Risk Matrix")
        st.dataframe(risk, use_container_width=True, hide_index=True)

    if not bucket_summary.empty:
        st.subheader("Bucket Summary")
        st.dataframe(bucket_summary, use_container_width=True, hide_index=True)


def render_portfolio_stress(
    exposures: pd.DataFrame,
    saved_portfolio: pd.DataFrame,
    saved_portfolio_stress: pd.DataFrame,
) -> None:
    if exposures.empty:
        st.warning("Run `python main.py` to generate scenario outputs.")
        return

    st.subheader("Portfolio Stress Test")
    if not saved_portfolio.empty:
        st.caption("Saved active portfolio from the last model run")
        st.dataframe(saved_portfolio, use_container_width=True, hide_index=True)
    if not saved_portfolio_stress.empty:
        st.caption("Saved portfolio scenario stress from the last model run")
        st.dataframe(saved_portfolio_stress, use_container_width=True, hide_index=True)
        show_chart("portfolio_scenario_stress.png", "Saved Portfolio Scenario Stress")
        show_chart("portfolio_contribution_heatmap.png", "Saved Portfolio Contribution Heatmap")

    sample = "SPY,0.30\nQQQ,0.20\nNVDA,0.10\nXLE,0.10\nGLD,0.10\nSHY,0.20"
    raw = st.text_area("Ticker, weight", value=sample, height=150)
    portfolio = parse_portfolio(raw)
    if portfolio.empty:
        st.warning("Enter rows like `SPY,0.30`.")
        return

    st.dataframe(portfolio, use_container_width=True, hide_index=True)
    stress = score_portfolio_against_scenarios(portfolio, exposures)
    if stress.empty:
        st.warning("No scenario exposure matches found for those tickers.")
        return

    st.subheader("Portfolio Scenario Scores")
    st.dataframe(stress, use_container_width=True, hide_index=True)
    render_portfolio_bar(stress)


def render_tables(
    scores: pd.DataFrame,
    performance: pd.DataFrame,
    scenario_exposures: pd.DataFrame,
    scenario_risk: pd.DataFrame,
) -> None:
    table_name = st.selectbox(
        "Table",
        [
            "Resilience Scores",
            "Performance by Crisis",
            "Scenario Exposures",
            "Scenario Risk Matrix",
        ],
    )
    tables = {
        "Resilience Scores": scores,
        "Performance by Crisis": performance,
        "Scenario Exposures": scenario_exposures,
        "Scenario Risk Matrix": scenario_risk,
    }
    st.dataframe(tables[table_name], use_container_width=True)


def show_chart(filename: str, title: str) -> None:
    path = CHART_DIR / filename
    if path.exists():
        st.image(str(path), caption=title, use_container_width=True)
    else:
        st.info(f"Missing chart: {filename}. Run `python main.py` to generate it.")


def render_impact_bar(rows: pd.DataFrame, title: str) -> None:
    colors = ["#c1121f" if value < 0 else "#2a9d8f" for value in rows["impact_score"]]
    labels = rows.apply(lambda row: f"{row['ticker_or_theme']} - {row['name']}", axis=1)

    fig_height = max(5, 0.35 * len(rows))
    fig, ax = plt.subplots(figsize=(12, fig_height))
    ax.barh(labels, rows["impact_score"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlim(-5.5, 5.5)
    ax.set_title(title)
    ax.set_xlabel("Expected impact score")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    st.pyplot(fig)


def render_portfolio_bar(stress: pd.DataFrame) -> None:
    data = stress.sort_values("portfolio_stress_score")
    colors = ["#c1121f" if value < 0 else "#2a9d8f" for value in data["portfolio_stress_score"]]

    fig, ax = plt.subplots(figsize=(12, max(5, 0.45 * len(data))))
    ax.barh(data["scenario"], data["portfolio_stress_score"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title("Portfolio Scenario Exposure")
    ax.set_xlabel("Weighted scenario score")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    st.pyplot(fig)


def parse_portfolio(raw: str) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2:
            continue
        try:
            rows.append({"ticker": parts[0].upper(), "weight": float(parts[1])})
        except ValueError:
            continue

    portfolio = pd.DataFrame(rows)
    if portfolio.empty:
        return portfolio
    total = portfolio["weight"].sum()
    if total != 0:
        portfolio["weight"] = portfolio["weight"] / total
    return portfolio


def score_portfolio_against_scenarios(
    portfolio: pd.DataFrame,
    exposures: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, float | str | int]] = []
    for scenario, group in exposures.groupby("scenario", sort=False):
        score = 0.0
        matches = 0
        matched_items: list[str] = []
        for _, holding in portfolio.iterrows():
            ticker = str(holding["ticker"]).upper()
            hit_rows = group[group["ticker_or_theme"].map(lambda value: ticker in tokenize(value))]
            if hit_rows.empty:
                continue
            holding_score = hit_rows["impact_score"].mean() * float(holding["weight"])
            score += holding_score
            matches += len(hit_rows)
            matched_items.extend(hit_rows["name"].tolist())

        rows.append(
            {
                "scenario": scenario,
                "portfolio_stress_score": score,
                "matched_exposures": matches,
                "matched_items": "; ".join(dict.fromkeys(matched_items)),
            }
        )
    return pd.DataFrame(rows).sort_values("portfolio_stress_score")


def tokenize(value: str) -> set[str]:
    return {token.upper() for token in re.split(r"[^A-Za-z0-9]+", str(value)) if token}


def format_percent_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    percent_cols = [
        "total_return",
        "annualized_return",
        "volatility",
        "max_drawdown",
        "downside_deviation",
    ]
    for column in percent_cols:
        if column in result:
            result[column] = result[column].map(
                lambda value: "" if pd.isna(value) else f"{value:.2%}"
            )
    return result


if __name__ == "__main__":
    main()
