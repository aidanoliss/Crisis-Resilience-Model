"""Chart generation for the Crisis Resilience Market Model."""

from __future__ import annotations

import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
import seaborn as sns

from metrics import compute_cumulative_returns, compute_drawdowns


def plot_cumulative_returns_by_crisis(
    crisis_returns: dict[str, pd.DataFrame],
    output_dir: str | Path,
    benchmark_col: str = "SPY",
) -> list[Path]:
    """Create one cumulative-return chart per crisis period."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    saved_files: list[Path] = []

    for crisis_name, returns in crisis_returns.items():
        if returns.empty:
            continue

        cumulative = compute_cumulative_returns(returns)
        fig, ax = plt.subplots(figsize=(12, 7))

        for column in cumulative.columns:
            if column == benchmark_col:
                ax.plot(
                    cumulative.index,
                    cumulative[column],
                    label=column,
                    color="black",
                    linewidth=2.4,
                    zorder=5,
                )
            else:
                ax.plot(cumulative.index, cumulative[column], label=column, alpha=0.75)

        ax.axhline(0, color="gray", linewidth=0.8)
        ax.set_title(f"Cumulative Returns: {crisis_name}")
        ax.set_ylabel("Cumulative return")
        ax.set_xlabel("Date")
        ax.yaxis.set_major_formatter(FuncFormatter(_percent_formatter))
        ax.legend(ncol=3, fontsize=8)
        ax.grid(True, alpha=0.25)
        fig.tight_layout()

        file_path = output_path / f"cumulative_returns_{_slugify(crisis_name)}.png"
        fig.savefig(file_path, dpi=160)
        plt.close(fig)
        saved_files.append(file_path)

    return saved_files


def plot_drawdowns(
    returns: pd.DataFrame,
    output_file: str | Path,
    benchmark_col: str = "SPY",
) -> Path:
    """Plot crisis-window drawdowns for all assets."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    drawdowns = compute_drawdowns(returns)

    fig, ax = plt.subplots(figsize=(12, 7))
    for column in drawdowns.columns:
        if column == benchmark_col:
            ax.plot(
                drawdowns.index,
                drawdowns[column],
                label=column,
                color="black",
                linewidth=2.4,
                zorder=5,
            )
        else:
            ax.plot(drawdowns.index, drawdowns[column], label=column, alpha=0.75)

    ax.set_title("Drawdowns Across All Crisis Windows")
    ax.set_ylabel("Drawdown")
    ax.set_xlabel("Date")
    ax.yaxis.set_major_formatter(FuncFormatter(_percent_formatter))
    ax.legend(ncol=3, fontsize=8)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return output_path


def plot_correlation_heatmap(returns: pd.DataFrame, output_file: str | Path) -> Path:
    """Plot asset return correlations during crisis windows."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    corr = returns.corr()

    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(
        corr,
        ax=ax,
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
        center=0,
        annot=False,
        square=True,
        linewidths=0.4,
        cbar_kws={"label": "Correlation"},
    )
    ax.set_title("Crisis-Window Daily Return Correlations")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return output_path


def plot_resilience_score_bars(
    scores: pd.DataFrame,
    output_file: str | Path,
    top_n: int | None = None,
) -> Path:
    """Plot ranked crisis resilience scores."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    chart_data = scores.dropna(subset=["crisis_resilience_score"]).copy()
    chart_data = chart_data.sort_values("crisis_resilience_score", ascending=True)
    if top_n is not None:
        chart_data = chart_data.tail(top_n)

    fig_height = max(6, 0.4 * len(chart_data))
    fig, ax = plt.subplots(figsize=(11, fig_height))
    ax.barh(chart_data["ticker"], chart_data["crisis_resilience_score"], color="#2f6f73")
    ax.set_title("Crisis Resilience Score Ranking")
    ax.set_xlabel("Score, 0-100")
    ax.set_ylabel("Asset")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return output_path


def plot_resilience_score_decomposition(
    scores: pd.DataFrame,
    output_file: str | Path,
    top_n: int | None = None,
) -> Path:
    """Plot how each component contributes to the final resilience score."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    component_weights = {
        "return_score": 40,
        "drawdown_score": 25,
        "volatility_score": 20,
        "correlation_score": 15,
    }
    component_labels = {
        "return_score": "Crisis return",
        "drawdown_score": "Drawdown protection",
        "volatility_score": "Low volatility",
        "correlation_score": "Low SPY correlation",
    }
    component_colors = {
        "return_score": "#2563eb",
        "drawdown_score": "#16a34a",
        "volatility_score": "#f59e0b",
        "correlation_score": "#7c3aed",
    }

    required_columns = ["ticker", "crisis_resilience_score", *component_weights.keys()]
    missing = [column for column in required_columns if column not in scores.columns]
    if missing:
        raise ValueError(f"Missing score columns for decomposition chart: {missing}")

    chart_data = scores.dropna(subset=["crisis_resilience_score"]).copy()
    chart_data = chart_data.sort_values("crisis_resilience_score", ascending=True)
    if top_n is not None:
        chart_data = chart_data.tail(top_n)

    for column, weight in component_weights.items():
        chart_data[f"{column}_contribution"] = chart_data[column] * weight

    fig_height = max(6, 0.45 * len(chart_data))
    fig, ax = plt.subplots(figsize=(12, fig_height))
    left = pd.Series(0.0, index=chart_data.index)

    for column in component_weights:
        contribution_col = f"{column}_contribution"
        ax.barh(
            chart_data["ticker"],
            chart_data[contribution_col],
            left=left,
            label=component_labels[column],
            color=component_colors[column],
        )
        left = left + chart_data[contribution_col]

    ax.set_title("Crisis Resilience Score Decomposition")
    ax.set_xlabel("Weighted score contribution, 0-100")
    ax.set_ylabel("Asset")
    ax.set_xlim(0, 100)
    ax.grid(True, axis="x", alpha=0.25)
    ax.legend(loc="lower right", frameon=True, fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _percent_formatter(value: float, _position: int) -> str:
    return f"{value:.0%}"
