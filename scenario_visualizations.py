"""Visualizations for forward-looking geopolitical stress scenarios."""

from __future__ import annotations

import os
from pathlib import Path
import textwrap

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def plot_scenario_impact_heatmap(
    exposures: pd.DataFrame,
    output_file: str | Path,
    top_n: int = 60,
) -> Path:
    """Plot scenario impact scores by item."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pivot = exposures.pivot_table(
        index="name",
        columns="scenario",
        values="impact_score",
        aggfunc="first",
    ).fillna(0)
    pivot = pivot.loc[pivot.abs().max(axis=1).sort_values(ascending=False).index]
    if len(pivot) > top_n:
        pivot = pivot.head(top_n)

    fig_width = max(12, 1.2 * len(pivot.columns))
    fig_height = max(9, 0.32 * len(pivot))
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="RdYlGn",
        center=0,
        vmin=-5,
        vmax=5,
        annot=True,
        fmt=".0f",
        linewidths=0.4,
        cbar_kws={"label": "Expected impact score (-5 to +5)"},
    )
    ax.set_title("Scenario Stress Scores: Expected Relative Winners and Losers")
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Resource, sector, company group, or technology")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_scenario_dimension_heatmap(
    risk_matrix: pd.DataFrame,
    output_file: str | Path,
) -> Path:
    """Plot macro impact dimensions by scenario."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dimension_cols = [
        "inflation_impact",
        "growth_impact",
        "liquidity_impact",
        "supply_chain_impact",
    ]
    heatmap_data = risk_matrix.set_index("scenario")[dimension_cols]

    fig, ax = plt.subplots(figsize=(11, max(6, 0.45 * len(heatmap_data))))
    sns.heatmap(
        heatmap_data,
        ax=ax,
        cmap="RdYlGn",
        center=0,
        vmin=-5,
        vmax=5,
        annot=True,
        fmt=".0f",
        linewidths=0.4,
        cbar_kws={"label": "Macro impact score (-5 to +5)"},
    )
    ax.set_title("Scenario Macro Impact Matrix")
    ax.set_xlabel("Stress dimension")
    ax.set_ylabel("Scenario")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_scenario_risk_scatter(
    risk_matrix: pd.DataFrame,
    output_file: str | Path,
) -> Path:
    """Plot probability versus severity for each scenario."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = risk_matrix.copy()

    fig, ax = plt.subplots(figsize=(12, 8))
    sizes = 600 * data["scenario_risk_score"] / data["scenario_risk_score"].max()
    scatter = ax.scatter(
        data["probability_weight"],
        data["severity_score"],
        s=sizes,
        c=data["liquidity_impact"],
        cmap="RdYlGn",
        vmin=-5,
        vmax=5,
        edgecolor="black",
        linewidth=0.8,
        alpha=0.82,
    )
    for _, row in data.iterrows():
        ax.annotate(
            _wrap_text(row["scenario"], 22),
            (row["probability_weight"], row["severity_score"]),
            xytext=(8, 5),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_title("Scenario Risk Map: Probability Weight vs Severity")
    ax.set_xlabel("Subjective probability weight")
    ax.set_ylabel("Severity score")
    ax.set_xlim(0, max(0.35, data["probability_weight"].max() + 0.05))
    ax.set_ylim(2.5, 5.5)
    ax.grid(True, alpha=0.25)
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Liquidity impact score")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_scenario_bucket_heatmap(
    bucket_summary: pd.DataFrame,
    output_file: str | Path,
) -> Path:
    """Plot average impact score by scenario and exposure bucket."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pivot = bucket_summary.pivot_table(
        index="scenario",
        columns="bucket",
        values="average_impact_score",
        aggfunc="mean",
    ).fillna(0)

    fig, ax = plt.subplots(figsize=(11, max(6, 0.45 * len(pivot))))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="RdYlGn",
        center=0,
        vmin=-5,
        vmax=5,
        annot=True,
        fmt=".1f",
        linewidths=0.4,
        cbar_kws={"label": "Average impact score"},
    )
    ax.set_title("Scenario Impact by Exposure Bucket")
    ax.set_xlabel("Bucket")
    ax.set_ylabel("Scenario")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_scenario_bars(
    exposures: pd.DataFrame,
    output_dir: str | Path,
) -> list[Path]:
    """Create one bar chart per scenario."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    saved_files: list[Path] = []

    for scenario, group in exposures.groupby("scenario", sort=False):
        chart_data = group.sort_values("impact_score")
        colors = [
            "#c1121f" if score < 0 else "#2a9d8f" if score > 0 else "#6c757d"
            for score in chart_data["impact_score"]
        ]

        fig_height = max(8, 0.35 * len(chart_data))
        fig, ax = plt.subplots(figsize=(13, fig_height))
        labels = chart_data.apply(
            lambda row: f"{row['ticker_or_theme']} - {row['name']}", axis=1
        )
        ax.barh(labels, chart_data["impact_score"], color=colors)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_xlim(-5.5, 5.5)
        ax.set_title(f"Scenario Playbook: {scenario}")
        ax.set_xlabel("Expected impact score (-5 pressure, +5 beneficiary)")
        ax.grid(True, axis="x", alpha=0.25)
        fig.tight_layout()

        file_path = output_path / f"scenario_{_slugify(scenario)}_impact_bars.png"
        fig.savefig(file_path, dpi=170)
        plt.close(fig)
        saved_files.append(file_path)

    return saved_files


def plot_scenario_summary_table(
    summary: pd.DataFrame,
    output_file: str | Path,
) -> Path:
    """Render likely growth, pressure, and path-dependent buckets as a table."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    table = summary.copy()
    for column in table.columns:
        table[column] = table[column].map(lambda value: _wrap_text(str(value), 42))

    fig, ax = plt.subplots(figsize=(16, max(5, 1.4 * len(table))))
    ax.axis("off")
    mpl_table = ax.table(
        cellText=table.values,
        colLabels=[
            "Scenario",
            "Likely Growth",
            "Likely Pressure",
            "Mixed or Path-Dependent",
        ],
        loc="center",
        cellLoc="left",
        colLoc="left",
        colWidths=[0.18, 0.28, 0.28, 0.26],
    )
    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(8)
    mpl_table.scale(1, 2.6)

    for (row, _col), cell in mpl_table.get_celld().items():
        cell.set_edgecolor("#d0d7de")
        if row == 0:
            cell.set_facecolor("#1f2937")
            cell.set_text_props(color="white", weight="bold")
        else:
            cell.set_facecolor("#f8fafc" if row % 2 else "white")

    ax.set_title("Geopolitical Crisis Scenario Summary", pad=18)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def _wrap_text(value: str, width: int) -> str:
    return "\n".join(textwrap.wrap(value, width=width, break_long_words=False))


def _slugify(value: str) -> str:
    return (
        value.lower()
        .replace(".", "")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("-", "_")
    )
