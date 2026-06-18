"""Historical narrative charts layered on top of the quantitative backtest."""

from __future__ import annotations

import os
from pathlib import Path
import textwrap

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
import pandas as pd
import seaborn as sns

from historical_context import RESOURCE_TICKERS


def plot_historical_crisis_timeline(
    context_table: pd.DataFrame,
    performance_by_crisis: pd.DataFrame,
    output_file: str | Path,
) -> Path:
    """Plot a dated crisis timeline with context labels and SPY return."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    table = context_table.copy()
    table["start"] = pd.to_datetime(
        performance_by_crisis.groupby("crisis")["crisis_start"].first()
    ).reindex(table["crisis"]).values
    table["end"] = pd.to_datetime(
        performance_by_crisis.groupby("crisis")["crisis_end"].first()
    ).reindex(table["crisis"]).values

    spy_returns = (
        performance_by_crisis.loc[performance_by_crisis["ticker"] == "SPY"]
        .set_index("crisis")["total_return"]
        .to_dict()
    )

    colors = {
        "Financial crisis": "#9b5de5",
        "Sovereign debt shock": "#577590",
        "Growth and commodity shock": "#f8961e",
        "Policy and trade shock": "#43aa8b",
        "Pandemic shock": "#f94144",
        "War and commodity shock": "#d62828",
        "Inflation and rate shock": "#277da1",
        "Banking and duration shock": "#4d908e",
    }

    fig, ax = plt.subplots(figsize=(14, 7))
    y_positions = list(range(len(table)))

    for idx, row in table.iterrows():
        start = mdates.date2num(row["start"])
        width = mdates.date2num(row["end"]) - start
        color = colors.get(row["context_type"], "#6c757d")
        ax.broken_barh([(start, width)], (idx - 0.35, 0.7), facecolors=color, alpha=0.85)

        spy_return = spy_returns.get(row["crisis"])
        spy_text = "SPY n/a" if pd.isna(spy_return) else f"SPY {spy_return:.0%}"
        label = f"{row['crisis']} ({spy_text})"
        ax.text(row["end"], idx, "  " + label, va="center", fontsize=9)

    ax.set_yticks(y_positions)
    ax.set_yticklabels([_wrap_text(value, 34) for value in table["war_or_geopolitical_context"]])
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_title("Historical Crisis Timeline: Wars, Policy Shocks, Pandemics, and Drawdowns")
    ax.set_xlabel("Calendar year")
    ax.set_ylabel("Historical context")
    ax.grid(True, axis="x", alpha=0.25)

    legend_items = [
        Patch(facecolor=color, label=context_type)
        for context_type, color in colors.items()
        if context_type in set(table["context_type"])
    ]
    ax.legend(handles=legend_items, loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_crisis_return_heatmap(
    performance_by_crisis: pd.DataFrame,
    output_file: str | Path,
    title: str,
    tickers: list[str] | None = None,
) -> Path:
    """Plot total returns by crisis and ticker as a heatmap."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = performance_by_crisis.copy()
    if tickers is not None:
        data = data[data["ticker"].isin(tickers)]

    pivot = data.pivot_table(index="crisis", columns="ticker", values="total_return")

    fig_width = max(11, 0.55 * len(pivot.columns))
    fig_height = max(6, 0.55 * len(pivot.index))
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="RdYlGn",
        center=0,
        annot=True,
        fmt=".0%",
        linewidths=0.4,
        cbar_kws={"label": "Total return"},
    )
    ax.set_title(title)
    ax.set_xlabel("Ticker")
    ax.set_ylabel("Crisis period")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_industry_winners_losers_by_crisis(
    performance_by_crisis: pd.DataFrame,
    output_file: str | Path,
    top_n: int = 3,
) -> Path:
    """Plot top and bottom sector/resource ETF returns for each crisis."""

    return _plot_top_bottom_panels(
        performance_by_crisis=performance_by_crisis,
        output_file=output_file,
        label_col="ticker",
        title="Industries and Asset Classes That Held Up or Fell During Each Crisis",
        exclude_tickers=["SPY"],
        top_n=top_n,
    )


def plot_company_winners_by_crisis(
    company_performance_by_crisis: pd.DataFrame,
    output_file: str | Path,
    top_n: int = 5,
    minimum_observations: int = 10,
) -> Path:
    """Plot the highest-returning companies in the defined company universe."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = company_performance_by_crisis[
        company_performance_by_crisis["observations"] >= minimum_observations
    ].copy()
    crises = list(dict.fromkeys(data["crisis"]))
    ncols = 2
    nrows = (len(crises) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(14, max(7, 3.5 * nrows)))
    axes_list = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for ax, crisis in zip(axes_list, crises):
        crisis_data = data[data["crisis"] == crisis].nlargest(top_n, "total_return")
        labels = crisis_data.apply(
            lambda row: f"{row['ticker']} - {row.get('company_name', '')}", axis=1
        )
        ax.barh(labels, crisis_data["total_return"], color="#2a9d8f")
        ax.invert_yaxis()
        ax.xaxis.set_major_formatter(FuncFormatter(_percent_formatter))
        ax.set_title(_wrap_text(crisis, 34))
        ax.set_xlabel("Total return")
        ax.grid(True, axis="x", alpha=0.25)

    for ax in axes_list[len(crises) :]:
        ax.axis("off")

    fig.suptitle("Companies That Succeeded Inside Each Crisis Window", fontsize=14, y=0.995)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_resource_importance_heatmap(
    performance_by_crisis: pd.DataFrame,
    output_file: str | Path,
    resource_tickers: list[str] = RESOURCE_TICKERS,
) -> Path:
    """Plot crisis returns for resource and defensive proxy ETFs."""

    return plot_crisis_return_heatmap(
        performance_by_crisis=performance_by_crisis,
        output_file=output_file,
        title="Resources and Defensive Assets That Grew in Importance",
        tickers=resource_tickers,
    )


def plot_context_table(
    context_table: pd.DataFrame,
    output_file: str | Path,
) -> Path:
    """Render a compact crisis context table as a PNG."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    columns = [
        "crisis",
        "resources_that_mattered",
        "technologies_that_benefited",
    ]
    table = context_table[columns].copy()
    for column in columns:
        table[column] = table[column].map(lambda value: _wrap_text(str(value), 42))

    fig_height = max(7, 0.85 * len(table))
    fig, ax = plt.subplots(figsize=(16, fig_height))
    ax.axis("off")
    mpl_table = ax.table(
        cellText=table.values,
        colLabels=["Crisis", "Resources That Mattered", "Technology That Benefited"],
        loc="center",
        cellLoc="left",
        colLoc="left",
        colWidths=[0.24, 0.35, 0.41],
    )
    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(8)
    mpl_table.scale(1, 2.0)

    for (row, _col), cell in mpl_table.get_celld().items():
        cell.set_edgecolor("#d0d7de")
        if row == 0:
            cell.set_facecolor("#1f2937")
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor("#f8fafc" if row % 2 else "white")

    ax.set_title("Historical Context: Resources and Technology Themes", pad=18)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_technology_theme_table(
    technology_theme_table: pd.DataFrame,
    output_file: str | Path,
) -> Path:
    """Render technology themes and example companies as a PNG table."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    table = technology_theme_table.copy()
    for column in table.columns:
        table[column] = table[column].map(lambda value: _wrap_text(str(value), 48))

    fig, ax = plt.subplots(figsize=(15, max(6, 0.85 * len(table))))
    ax.axis("off")
    mpl_table = ax.table(
        cellText=table.values,
        colLabels=["Technology Theme", "Why It Mattered", "Example Companies"],
        loc="center",
        cellLoc="left",
        colLoc="left",
        colWidths=[0.23, 0.52, 0.25],
    )
    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(8)
    mpl_table.scale(1, 2.0)

    for (row, _col), cell in mpl_table.get_celld().items():
        cell.set_edgecolor("#d0d7de")
        if row == 0:
            cell.set_facecolor("#0f766e")
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor("#f8fafc" if row % 2 else "white")

    ax.set_title("Technology That Benefited or Improved During Crisis Regimes", pad=18)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def build_winner_loser_tables(
    performance_by_crisis: pd.DataFrame,
    company_performance_by_crisis: pd.DataFrame,
    top_n: int = 5,
    minimum_observations: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return exportable tables for ETF winners, ETF losers, and company winners."""

    etf_data = performance_by_crisis[performance_by_crisis["ticker"] != "SPY"].copy()
    company_data = company_performance_by_crisis[
        company_performance_by_crisis["observations"] >= minimum_observations
    ].copy()

    etf_winners = _rank_within_crisis(etf_data, top_n, ascending=False)
    etf_losers = _rank_within_crisis(etf_data, top_n, ascending=True)
    company_winners = _rank_within_crisis(company_data, top_n, ascending=False)
    return etf_winners, etf_losers, company_winners


def _plot_top_bottom_panels(
    performance_by_crisis: pd.DataFrame,
    output_file: str | Path,
    label_col: str,
    title: str,
    exclude_tickers: list[str] | None,
    top_n: int,
) -> Path:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = performance_by_crisis.copy()
    if exclude_tickers:
        data = data[~data["ticker"].isin(exclude_tickers)]

    crises = list(dict.fromkeys(data["crisis"]))
    ncols = 2
    nrows = (len(crises) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(14, max(7, 3.8 * nrows)))
    axes_list = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for ax, crisis in zip(axes_list, crises):
        crisis_data = data[data["crisis"] == crisis].dropna(subset=["total_return"])
        top = crisis_data.nlargest(top_n, "total_return")
        bottom = crisis_data.nsmallest(top_n, "total_return")
        panel = pd.concat([top, bottom]).drop_duplicates(subset=["ticker"])
        panel = panel.sort_values("total_return")
        colors = ["#c1121f" if value < 0 else "#2a9d8f" for value in panel["total_return"]]

        ax.barh(panel[label_col], panel["total_return"], color=colors)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.xaxis.set_major_formatter(FuncFormatter(_percent_formatter))
        ax.set_title(_wrap_text(crisis, 34))
        ax.set_xlabel("Total return")
        ax.grid(True, axis="x", alpha=0.25)

    for ax in axes_list[len(crises) :]:
        ax.axis("off")

    fig.suptitle(title, fontsize=14, y=0.995)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def _rank_within_crisis(
    data: pd.DataFrame,
    top_n: int,
    ascending: bool,
) -> pd.DataFrame:
    ranked_frames: list[pd.DataFrame] = []
    for crisis, group in data.groupby("crisis", sort=False):
        ranked = group.sort_values("total_return", ascending=ascending).head(top_n).copy()
        ranked.insert(0, "within_crisis_rank", range(1, len(ranked) + 1))
        ranked_frames.append(ranked)
    if not ranked_frames:
        return pd.DataFrame()
    return pd.concat(ranked_frames, ignore_index=True)


def _wrap_text(value: str, width: int) -> str:
    return "\n".join(textwrap.wrap(value, width=width, break_long_words=False))


def _percent_formatter(value: float, _position: int) -> str:
    return f"{value:.0%}"
