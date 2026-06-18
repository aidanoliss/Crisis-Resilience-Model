"""Portfolio stress testing against scenario exposures."""

from __future__ import annotations

import os
from pathlib import Path
import re

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


DEFAULT_PORTFOLIO = pd.DataFrame(
    [
        {"ticker": "SPY", "weight": 0.30},
        {"ticker": "QQQ", "weight": 0.20},
        {"ticker": "NVDA", "weight": 0.10},
        {"ticker": "XLE", "weight": 0.10},
        {"ticker": "GLD", "weight": 0.10},
        {"ticker": "SHY", "weight": 0.20},
    ]
)


def load_or_create_portfolio(
    portfolio_file: str | Path | None,
    output_dir: str | Path,
) -> tuple[pd.DataFrame, Path]:
    """Load a portfolio CSV, or create a sample portfolio if none is supplied.

    Accepted real-export formats:
    - ticker/symbol plus weight/allocation/percent
    - ticker/symbol plus market value/current value/value/amount

    If dollar values are provided, they are normalized into weights.
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sample_path = output_path / "sample_portfolio.csv"
    if not sample_path.exists():
        DEFAULT_PORTFOLIO.to_csv(sample_path, index=False)

    path = Path(portfolio_file) if portfolio_file else sample_path
    if not path.exists():
        raise FileNotFoundError(f"Portfolio file not found: {path}")

    raw = pd.read_csv(path)
    portfolio = normalize_portfolio_export(raw)
    total = portfolio["weight"].sum()
    if total == 0:
        raise ValueError("Portfolio weights sum to zero.")
    portfolio["weight"] = portfolio["weight"] / total
    portfolio.to_csv(output_path / "active_portfolio.csv", index=False)
    build_portfolio_import_audit(raw, portfolio, path).to_csv(
        output_path / "portfolio_import_audit.csv",
        index=False,
    )
    return portfolio, path


def normalize_portfolio_export(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize brokerage-style holdings exports into ticker and weight."""

    if raw.empty:
        raise ValueError("Portfolio CSV is empty.")

    column_map = {_normalize_column(column): column for column in raw.columns}
    ticker_column = _first_matching_column(
        column_map,
        ["ticker", "symbol", "securitysymbol", "underlyingsymbol"],
    )
    if ticker_column is None:
        raise ValueError("Portfolio CSV must include a ticker or symbol column.")

    weight_column = _first_matching_column(
        column_map,
        ["weight", "allocation", "allocationpercent", "percent", "percentage", "portfolio_percent"],
    )
    value_column = _first_matching_column(
        column_map,
        [
            "marketvalue",
            "currentvalue",
            "value",
            "amount",
            "positionvalue",
            "totalvalue",
            "market_value",
            "current_value",
        ],
    )

    portfolio = pd.DataFrame()
    portfolio["ticker"] = raw[ticker_column].astype(str).str.upper().str.strip()
    portfolio["ticker"] = portfolio["ticker"].replace({"": pd.NA, "NAN": pd.NA})

    if weight_column is not None:
        weights = _clean_numeric(raw[weight_column])
        if weights.dropna().max() > 1.5:
            weights = weights / 100.0
        portfolio["weight"] = weights
        source_column = weight_column
    elif value_column is not None:
        values = _clean_numeric(raw[value_column])
        portfolio["weight"] = values
        source_column = value_column
    else:
        raise ValueError(
            "Portfolio CSV must include a weight/allocation column or a market value/current value column."
        )

    portfolio = portfolio.dropna(subset=["ticker", "weight"])
    portfolio = portfolio[portfolio["weight"] > 0].copy()
    if portfolio.empty:
        raise ValueError("No positive portfolio holdings found after normalization.")

    portfolio = portfolio.groupby("ticker", as_index=False)["weight"].sum()
    portfolio["import_weight_source"] = source_column
    return portfolio


def build_portfolio_import_audit(
    raw: pd.DataFrame,
    portfolio: pd.DataFrame,
    path: Path,
) -> pd.DataFrame:
    """Document how a portfolio export was interpreted."""

    return pd.DataFrame(
        [
            {
                "source_file": str(path),
                "raw_rows": int(raw.shape[0]),
                "normalized_holdings": int(portfolio.shape[0]),
                "normalized_columns": ", ".join(portfolio.columns.astype(str).tolist()),
                "import_note": "Weights were normalized to sum to 1.0. Unmapped holdings remain in active_portfolio.csv but may not match scenario exposure rows.",
            }
        ]
    )


def score_portfolio_against_scenarios(
    portfolio: pd.DataFrame,
    scenario_exposures: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score portfolio holdings against scenario exposure assumptions."""

    rows: list[dict[str, float | str | int]] = []
    contributions: list[dict[str, float | str]] = []

    for scenario, group in scenario_exposures.groupby("scenario", sort=False):
        score = 0.0
        matched_count = 0
        matched_items: list[str] = []
        for holding in portfolio.itertuples():
            ticker = str(holding.ticker).upper()
            matches = group[group["ticker_or_theme"].map(lambda value: ticker in _tokens(value))]
            if matches.empty:
                continue

            avg_impact = float(matches["impact_score"].mean())
            contribution = avg_impact * float(holding.weight)
            score += contribution
            matched_count += int(matches.shape[0])
            matched_items.extend(matches["name"].tolist())
            contributions.append(
                {
                    "scenario": scenario,
                    "ticker": ticker,
                    "weight": float(holding.weight),
                    "matched_items": "; ".join(matches["name"].tolist()),
                    "average_impact_score": avg_impact,
                    "weighted_contribution": contribution,
                }
            )

        rows.append(
            {
                "scenario": scenario,
                "portfolio_stress_score": score,
                "matched_exposure_count": matched_count,
                "matched_items": "; ".join(dict.fromkeys(matched_items)),
                "stress_interpretation": _interpret_portfolio_score(score),
            }
        )

    stress = pd.DataFrame(rows).sort_values("portfolio_stress_score")
    contribution_table = pd.DataFrame(contributions)
    return stress, contribution_table


def export_portfolio_stress(
    portfolio_file: str | Path | None,
    output_dir: str | Path,
    scenario_exposures: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Write portfolio stress CSV outputs."""

    portfolio, _path = load_or_create_portfolio(portfolio_file, output_dir)
    stress, contributions = score_portfolio_against_scenarios(portfolio, scenario_exposures)
    output_path = Path(output_dir)
    stress.to_csv(output_path / "portfolio_scenario_stress.csv", index=False)
    contributions.to_csv(output_path / "portfolio_stress_contributions.csv", index=False)
    return portfolio, stress, contributions


def plot_portfolio_scenario_stress(
    stress: pd.DataFrame,
    output_file: str | Path,
) -> Path:
    """Plot portfolio stress score by scenario."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if stress.empty:
        return output_path

    data = stress.sort_values("portfolio_stress_score")
    colors = ["#b91c1c" if value < 0 else "#16a34a" for value in data["portfolio_stress_score"]]
    fig, ax = plt.subplots(figsize=(12, max(5, 0.45 * len(data))))
    ax.barh(data["scenario"], data["portfolio_stress_score"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title("Portfolio Stress Score by Scenario")
    ax.set_xlabel("Weighted impact score")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_portfolio_contribution_heatmap(
    contributions: pd.DataFrame,
    output_file: str | Path,
) -> Path:
    """Plot holding-level contribution by scenario."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if contributions.empty:
        return output_path

    pivot = contributions.pivot_table(
        index="scenario",
        columns="ticker",
        values="weighted_contribution",
        aggfunc="sum",
    ).fillna(0)

    fig, ax = plt.subplots(figsize=(12, max(6, 0.48 * len(pivot))))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="RdYlGn",
        center=0,
        annot=True,
        fmt=".2f",
        linewidths=0.4,
        cbar_kws={"label": "Weighted contribution"},
    )
    ax.set_title("Portfolio Scenario Contribution Heatmap")
    ax.set_xlabel("Holding")
    ax.set_ylabel("Scenario")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def _tokens(value: str) -> set[str]:
    return {token.upper() for token in re.split(r"[^A-Za-z0-9]+", str(value)) if token}


def _normalize_column(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _first_matching_column(column_map: dict[str, str], candidates: list[str]) -> str | None:
    normalized_candidates = {_normalize_column(candidate) for candidate in candidates}
    for normalized, original in column_map.items():
        if normalized in normalized_candidates:
            return original
    return None


def _clean_numeric(values: pd.Series) -> pd.Series:
    cleaned = (
        values.astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("(", "-", regex=False)
        .str.replace(")", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _interpret_portfolio_score(score: float) -> str:
    if score <= -1.5:
        return "Meaningful modeled downside exposure."
    if score < -0.25:
        return "Mild modeled downside exposure."
    if score <= 0.25:
        return "Roughly neutral or unmapped exposure."
    if score < 1.5:
        return "Mild modeled beneficiary exposure."
    return "Meaningful modeled beneficiary exposure."
