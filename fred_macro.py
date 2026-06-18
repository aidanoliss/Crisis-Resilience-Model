"""Direct FRED macro data pipeline.

FRED adds cleaner macro regime signals than ETF proxies alone. The module uses
FRED's public CSV endpoint so no API key is required. If the network is not
available, the model falls back to cached CSVs when present and otherwise
writes empty outputs so the rest of the project can still run.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns

from crisis_periods import CRISIS_PERIODS


FRED_BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


@dataclass(frozen=True)
class FredSeries:
    series_id: str
    name: str
    category: str
    unit: str
    interpretation: str


FRED_SERIES: list[FredSeries] = [
    FredSeries("CPIAUCSL", "CPI index", "Inflation", "index", "Consumer price level."),
    FredSeries("FEDFUNDS", "Effective fed funds rate", "Rates", "percent", "Policy-rate stance."),
    FredSeries("DGS2", "2-year Treasury yield", "Rates", "percent", "Front-end rate expectations."),
    FredSeries("DGS10", "10-year Treasury yield", "Rates", "percent", "Long-rate expectations."),
    FredSeries("VIXCLS", "VIX", "Volatility", "index", "Equity volatility stress."),
    FredSeries(
        "BAMLH0A0HYM2",
        "High-yield credit spread",
        "Credit",
        "percentage points",
        "Risk premium for below-investment-grade credit.",
    ),
    FredSeries(
        "BAMLC0A0CM",
        "Investment-grade credit spread",
        "Credit",
        "percentage points",
        "Risk premium for investment-grade corporate credit.",
    ),
    FredSeries("UNRATE", "Unemployment rate", "Labor", "percent", "Labor-market slack."),
    FredSeries(
        "STLFSI4",
        "St. Louis Fed Financial Stress Index",
        "Financial stress",
        "index",
        "Broad U.S. financial stress conditions.",
    ),
    FredSeries(
        "NFCI",
        "Chicago Fed National Financial Conditions Index",
        "Financial stress",
        "index",
        "Broad financial conditions and leverage stress.",
    ),
]

DERIVED_SERIES: list[FredSeries] = [
    FredSeries("CPI_YOY", "CPI year-over-year", "Inflation", "percent", "Inflation momentum."),
    FredSeries(
        "YIELD_CURVE_10Y_2Y",
        "10Y minus 2Y Treasury slope",
        "Rates",
        "percentage points",
        "Yield-curve slope and recession pressure.",
    ),
]

SERIES_METADATA = {series.series_id: series for series in [*FRED_SERIES, *DERIVED_SERIES]}


def export_fred_macro_tables(
    output_dir: str | Path,
    force_refresh: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Download, cache, summarize, and alert on direct FRED macro series."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    cache_path = output_path / "fred_macro_series.csv"

    data = load_fred_macro_data(cache_path, force_refresh=force_refresh)
    latest = build_fred_latest_summary(data)
    crisis_summary = build_fred_crisis_summary(data)
    alerts = build_fred_macro_alerts(latest)

    data.to_csv(cache_path)
    latest.to_csv(output_path / "fred_macro_latest.csv", index=False)
    crisis_summary.to_csv(output_path / "fred_macro_crisis_summary.csv", index=False)
    alerts.to_csv(output_path / "fred_macro_alerts.csv", index=False)
    return data, latest, crisis_summary, alerts


def load_fred_macro_data(cache_path: str | Path, force_refresh: bool = False) -> pd.DataFrame:
    """Load direct macro data from cache or FRED."""

    cache = Path(cache_path)
    if cache.exists() and not force_refresh:
        return _read_cached_fred(cache)

    try:
        data = download_fred_macro_data()
    except Exception as exc:
        print(f"FRED macro download unavailable: {exc}")
        if cache.exists():
            return _read_cached_fred(cache)
        return pd.DataFrame()

    if data.empty and cache.exists():
        return _read_cached_fred(cache)
    return data


def download_fred_macro_data() -> pd.DataFrame:
    """Download FRED macro series and derived indicators."""

    frames: list[pd.Series] = []
    for series in FRED_SERIES:
        try:
            frames.append(_download_single_series(series.series_id))
        except Exception as exc:
            print(f"Skipping FRED series {series.series_id}: {exc}")

    if not frames:
        return pd.DataFrame()

    data = pd.concat(frames, axis=1).sort_index()
    data.index.name = "date"
    data = add_derived_macro_series(data)
    return data


def add_derived_macro_series(data: pd.DataFrame) -> pd.DataFrame:
    """Add CPI YoY and yield-curve slope derived from raw FRED data."""

    result = data.copy()
    if "CPIAUCSL" in result.columns:
        result["CPI_YOY"] = result["CPIAUCSL"].pct_change(12, fill_method=None) * 100.0
    if {"DGS10", "DGS2"}.issubset(result.columns):
        result["YIELD_CURVE_10Y_2Y"] = result["DGS10"] - result["DGS2"]
    return result


def build_fred_latest_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Create one latest row per macro series with trend and stress scoring."""

    if data.empty:
        return _empty_latest()

    rows: list[dict[str, float | str]] = []
    for series_id in data.columns:
        series = data[series_id].dropna()
        if series.empty:
            continue

        metadata = SERIES_METADATA.get(
            series_id,
            FredSeries(series_id, series_id, "Other", "value", "No metadata configured."),
        )
        latest_date = series.index.max()
        latest_value = float(series.loc[latest_date])
        prior_3m = _latest_before(series, latest_date - pd.Timedelta(days=90))
        prior_1y = _latest_before(series, latest_date - pd.Timedelta(days=365))
        change_3m = latest_value - prior_3m if prior_3m is not None else pd.NA
        change_1y = latest_value - prior_1y if prior_1y is not None else pd.NA
        stress_score, stress_level, signal = _score_macro_latest(series_id, latest_value, change_3m)
        rows.append(
            {
                "series_id": series_id,
                "name": metadata.name,
                "category": metadata.category,
                "unit": metadata.unit,
                "latest_date": latest_date.date().isoformat(),
                "latest_value": latest_value,
                "change_3m": change_3m,
                "change_1y": change_1y,
                "stress_score": stress_score,
                "stress_level": stress_level,
                "signal": signal,
                "interpretation": metadata.interpretation,
            }
        )

    if not rows:
        return _empty_latest()
    return pd.DataFrame(rows).sort_values("stress_score", ascending=False)


def build_fred_crisis_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Summarize how direct macro indicators moved inside crisis windows."""

    if data.empty:
        return _empty_crisis_summary()

    filled = data.sort_index().ffill()
    rows: list[dict[str, float | str | int]] = []
    for period in CRISIS_PERIODS:
        period_data = filled.loc[
            (filled.index >= period.start_ts) & (filled.index <= period.end_ts)
        ]
        if period_data.empty:
            continue

        for series_id in filled.columns:
            series = period_data[series_id].dropna()
            if series.empty:
                continue
            metadata = SERIES_METADATA.get(
                series_id,
                FredSeries(series_id, series_id, "Other", "value", "No metadata configured."),
            )
            start_value = float(series.iloc[0])
            end_value = float(series.iloc[-1])
            rows.append(
                {
                    "crisis": period.name,
                    "series_id": series_id,
                    "name": metadata.name,
                    "category": metadata.category,
                    "unit": metadata.unit,
                    "observations": int(series.shape[0]),
                    "start_value": start_value,
                    "end_value": end_value,
                    "change": end_value - start_value,
                    "min_value": float(series.min()),
                    "max_value": float(series.max()),
                }
            )

    if not rows:
        return _empty_crisis_summary()
    return pd.DataFrame(rows)


def build_fred_macro_alerts(latest: pd.DataFrame) -> pd.DataFrame:
    """Build threshold alerts from direct macro readings."""

    if latest.empty:
        return _empty_alerts()

    rows: list[dict[str, float | str]] = []
    for row in latest.itertuples():
        level = str(row.stress_level)
        if level == "Normal":
            continue
        rows.append(
            {
                "source": "FRED",
                "series_id": row.series_id,
                "name": row.name,
                "category": row.category,
                "latest_date": row.latest_date,
                "latest_value": row.latest_value,
                "change_3m": row.change_3m,
                "stress_score": row.stress_score,
                "stress_level": level,
                "signal": row.signal,
                "message": _fred_alert_message(row.series_id, row.name, row.latest_value, row.signal),
            }
        )
    if not rows:
        return _empty_alerts()
    return pd.DataFrame(rows).sort_values("stress_score", ascending=False)


def plot_fred_macro_stress_scores(latest: pd.DataFrame, output_file: str | Path) -> Path:
    """Plot stress scores for direct FRED macro indicators."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if latest.empty:
        return output_path

    data = latest.sort_values("stress_score")
    colors = data["stress_score"].map(_score_color)
    fig, ax = plt.subplots(figsize=(12, max(5, 0.42 * len(data))))
    ax.barh(data["name"], data["stress_score"], color=colors)
    for value in [25, 50, 75]:
        ax.axvline(value, color="#111827", linewidth=0.8, linestyle="--", alpha=0.75)
    ax.set_xlim(0, 100)
    ax.set_title("Direct FRED Macro Stress Scores")
    ax.set_xlabel("Stress score, 0-100")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def plot_fred_macro_crisis_heatmap(summary: pd.DataFrame, output_file: str | Path) -> Path:
    """Plot macro indicator changes inside each historical crisis window."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if summary.empty:
        return output_path

    preferred = [
        "CPI_YOY",
        "FEDFUNDS",
        "DGS2",
        "DGS10",
        "YIELD_CURVE_10Y_2Y",
        "VIXCLS",
        "BAMLH0A0HYM2",
        "BAMLC0A0CM",
        "UNRATE",
        "STLFSI4",
        "NFCI",
    ]
    filtered = summary[summary["series_id"].isin(preferred)].copy()
    if filtered.empty:
        return output_path

    pivot = filtered.pivot_table(index="crisis", columns="series_id", values="change")
    pivot = pivot.reindex(columns=[column for column in preferred if column in pivot.columns])
    fig, ax = plt.subplots(figsize=(13, max(6, 0.55 * len(pivot))))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="RdYlGn_r",
        center=0,
        annot=True,
        fmt=".2f",
        linewidths=0.4,
        cbar_kws={"label": "Change during crisis window"},
    )
    ax.set_title("Direct FRED Macro Changes by Crisis Window")
    ax.set_xlabel("FRED series")
    ax.set_ylabel("Crisis")
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def _download_single_series(series_id: str) -> pd.Series:
    response = requests.get(
        FRED_BASE_URL,
        params={"id": series_id},
        timeout=5,
        headers={"User-Agent": "crisis-resilience-market-model/1.0"},
    )
    response.raise_for_status()
    frame = pd.read_csv(StringIO(response.text))
    if "observation_date" not in frame.columns or series_id not in frame.columns:
        raise ValueError("Unexpected FRED CSV format.")
    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
    values = pd.to_numeric(frame[series_id].replace(".", pd.NA), errors="coerce")
    values.index = frame["observation_date"]
    values.name = series_id
    return values.dropna()


def _read_cached_fred(cache: Path) -> pd.DataFrame:
    data = pd.read_csv(cache, index_col=0, parse_dates=True)
    data.index.name = "date"
    return data


def _latest_before(series: pd.Series, date_value: pd.Timestamp) -> float | None:
    prior = series.loc[series.index <= date_value]
    if prior.empty:
        return None
    return float(prior.iloc[-1])


def _score_macro_latest(
    series_id: str,
    latest_value: float,
    change_3m: float | pd._libs.missing.NAType,
) -> tuple[int, str, str]:
    """Rules-based macro stress score.

    Thresholds are deliberately transparent and easy to modify. They are not
    estimated probabilities.
    """

    change = None if pd.isna(change_3m) else float(change_3m)
    if series_id == "VIXCLS":
        score = _score_high(latest_value, [25.0, 35.0, 50.0])
        signal = "VIX volatility threshold."
    elif series_id == "BAMLH0A0HYM2":
        score = _score_high(latest_value, [4.5, 6.5, 9.0])
        signal = "High-yield credit-spread threshold."
    elif series_id == "BAMLC0A0CM":
        score = _score_high(latest_value, [1.5, 2.25, 3.5])
        signal = "Investment-grade credit-spread threshold."
    elif series_id == "STLFSI4":
        score = _score_high(latest_value, [0.5, 1.5, 2.5])
        signal = "Financial stress index threshold."
    elif series_id == "NFCI":
        score = _score_high(latest_value, [0.0, 0.75, 1.5])
        signal = "Financial conditions threshold."
    elif series_id == "CPI_YOY":
        score = _score_high(latest_value, [3.5, 5.0, 7.0])
        signal = "Inflation threshold."
    elif series_id in {"DGS2", "DGS10", "FEDFUNDS"} and change is not None:
        score = _score_high(change, [0.50, 1.00, 1.75])
        signal = "Three-month rate-change threshold."
    elif series_id == "YIELD_CURVE_10Y_2Y":
        score = _score_low(latest_value, [-0.25, -0.75, -1.25])
        signal = "Yield-curve inversion threshold."
    elif series_id == "UNRATE" and change is not None:
        score = _score_high(change, [0.30, 0.60, 1.00])
        signal = "Three-month unemployment-change threshold."
    else:
        score = 10
        signal = "No elevated threshold."
    return score, _level_from_score(score), signal


def _score_high(value: float, thresholds: list[float]) -> int:
    if value >= thresholds[2]:
        return 100
    if value >= thresholds[1]:
        return 75
    if value >= thresholds[0]:
        return 45
    return 10


def _score_low(value: float, thresholds: list[float]) -> int:
    if value <= thresholds[2]:
        return 100
    if value <= thresholds[1]:
        return 75
    if value <= thresholds[0]:
        return 45
    return 10


def _level_from_score(score: int) -> str:
    if score >= 90:
        return "Crisis"
    if score >= 70:
        return "Stress"
    if score >= 40:
        return "Watch"
    return "Normal"


def _score_color(score: float) -> str:
    if score >= 90:
        return "#b91c1c"
    if score >= 70:
        return "#f97316"
    if score >= 40:
        return "#facc15"
    return "#16a34a"


def _fred_alert_message(series_id: str, name: str, value: float, signal: str) -> str:
    return f"{name} is elevated under the {signal} Current value: {value:.2f}."


def _empty_latest() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "series_id",
            "name",
            "category",
            "unit",
            "latest_date",
            "latest_value",
            "change_3m",
            "change_1y",
            "stress_score",
            "stress_level",
            "signal",
            "interpretation",
        ]
    )


def _empty_crisis_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "crisis",
            "series_id",
            "name",
            "category",
            "unit",
            "observations",
            "start_value",
            "end_value",
            "change",
            "min_value",
            "max_value",
        ]
    )


def _empty_alerts() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "source",
            "series_id",
            "name",
            "category",
            "latest_date",
            "latest_value",
            "change_3m",
            "stress_score",
            "stress_level",
            "signal",
            "message",
        ]
    )
