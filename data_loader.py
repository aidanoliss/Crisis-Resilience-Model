"""Market data loading utilities for the Crisis Resilience Market Model."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import yfinance as yf


BENCHMARK = "SPY"

TICKER_NAMES: dict[str, str] = {
    "SPY": "S&P 500 Benchmark",
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLU": "Utilities",
    "XLV": "Healthcare",
    "XLP": "Consumer Staples",
    "XLI": "Industrials",
    "XLY": "Consumer Discretionary",
    "XLB": "Materials",
    "XLC": "Communication Services",
    "GLD": "Gold",
    "TLT": "Long-Term Treasuries",
    "SHY": "Short-Term Treasuries",
    "USO": "Oil",
    "UUP": "U.S. Dollar",
    "VNQ": "Real Estate",
}

DEFAULT_TICKERS: list[str] = list(TICKER_NAMES.keys())


def download_adjusted_close(
    tickers: Iterable[str] = DEFAULT_TICKERS,
    start: str = "2004-01-01",
    end: str | None = None,
    cache_path: str | Path | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Download adjusted close prices from Yahoo Finance via yfinance.

    Adjusted close prices account for dividends and splits, which makes them
    the right input for a total-return-style ETF backtest.
    """

    ticker_list = list(dict.fromkeys(tickers))
    if not ticker_list:
        raise ValueError("At least one ticker is required.")

    cache = Path(cache_path) if cache_path else None
    if cache and cache.exists() and not force_refresh:
        return pd.read_csv(cache, index_col=0, parse_dates=True)

    raw = yf.download(
        ticker_list,
        start=start,
        end=end,
        auto_adjust=False,
        actions=False,
        progress=False,
        group_by="column",
        threads=False,
    )

    if raw.empty:
        raise RuntimeError(
            "No data was downloaded. Check your internet connection and ticker list."
        )

    prices = _extract_adjusted_close(raw)
    prices = prices.reindex(columns=ticker_list)
    prices = prices.apply(pd.to_numeric, errors="coerce")
    prices = prices.sort_index().dropna(how="all")
    prices.index.name = "Date"
    prices = _repair_missing_tickers(
        prices=prices,
        ticker_list=ticker_list,
        start=start,
        end=end,
        cache=cache,
    )

    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        prices.to_csv(cache)

    return prices


def _repair_missing_tickers(
    prices: pd.DataFrame,
    ticker_list: list[str],
    start: str,
    end: str | None,
    cache: Path | None,
) -> pd.DataFrame:
    """Retry or backfill tickers that yfinance returned as all missing.

    Bulk Yahoo requests can occasionally return a false "possibly delisted"
    result for one ticker while the rest of the batch succeeds. Retrying those
    symbols one by one reduces silent data loss. If a prior cache has valid data,
    it is used as a last resort.
    """

    result = prices.copy()
    missing = [
        ticker
        for ticker in ticker_list
        if ticker not in result.columns or result[ticker].dropna().empty
    ]
    if not missing:
        return result

    for ticker in missing:
        try:
            retry = _download_single_adjusted_close(ticker, start=start, end=end)
        except Exception as exc:
            print(f"Retry failed for {ticker}: {exc}")
            continue
        if not retry.empty:
            result[ticker] = retry.reindex(result.index).combine_first(retry)

    still_missing = [
        ticker
        for ticker in ticker_list
        if ticker not in result.columns or result[ticker].dropna().empty
    ]
    if cache and cache.exists() and still_missing:
        cached = pd.read_csv(cache, index_col=0, parse_dates=True)
        for ticker in still_missing:
            if ticker in cached.columns and not cached[ticker].dropna().empty:
                result[ticker] = cached[ticker].reindex(result.index).combine_first(cached[ticker])

    return result.reindex(columns=ticker_list).sort_index()


def _download_single_adjusted_close(
    ticker: str,
    start: str,
    end: str | None,
) -> pd.Series:
    raw = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=False,
        actions=False,
        progress=False,
        group_by="column",
        threads=False,
    )
    if raw.empty:
        return pd.Series(dtype=float, name=ticker)
    prices = _extract_adjusted_close(raw)
    if isinstance(prices.columns, pd.MultiIndex):
        series = prices.iloc[:, 0]
    elif ticker in prices.columns:
        series = prices[ticker]
    else:
        series = prices.iloc[:, 0]
    series = pd.to_numeric(series, errors="coerce").dropna()
    series.name = ticker
    return series


def calculate_daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Convert adjusted prices into simple daily returns."""

    returns = prices.pct_change(fill_method=None)
    returns = returns.replace([float("inf"), float("-inf")], pd.NA)
    returns = returns.dropna(how="all")
    returns.index.name = "Date"
    return returns


def add_asset_names(df: pd.DataFrame, ticker_column: str = "ticker") -> pd.DataFrame:
    """Add a human-readable asset name column to a dataframe containing tickers."""

    result = df.copy()
    result.insert(1, "asset_name", result[ticker_column].map(TICKER_NAMES))
    return result


def _extract_adjusted_close(raw: pd.DataFrame) -> pd.DataFrame:
    """Handle the different column shapes yfinance can return."""

    if isinstance(raw.columns, pd.MultiIndex):
        level_0 = raw.columns.get_level_values(0)
        level_1 = raw.columns.get_level_values(1)

        if "Adj Close" in level_0:
            prices = raw.xs("Adj Close", axis=1, level=0)
        elif "Adj Close" in level_1:
            prices = raw.xs("Adj Close", axis=1, level=1)
        elif "Close" in level_0:
            prices = raw.xs("Close", axis=1, level=0)
        elif "Close" in level_1:
            prices = raw.xs("Close", axis=1, level=1)
        else:
            raise RuntimeError("Could not find adjusted close prices in yfinance output.")
    else:
        if "Adj Close" in raw.columns:
            prices = raw[["Adj Close"]].copy()
        elif "Close" in raw.columns:
            prices = raw[["Close"]].copy()
        else:
            raise RuntimeError("Could not find adjusted close prices in yfinance output.")

    if isinstance(prices, pd.Series):
        prices = prices.to_frame()

    return prices
