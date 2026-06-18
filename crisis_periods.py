"""Definitions and helpers for historical crisis windows.

The dates below are intentionally explicit. This project is a historical
backtest, so changing a window changes the question being tested.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class CrisisPeriod:
    """A named market stress window with inclusive start and end dates."""

    name: str
    start: str
    end: str
    description: str

    @property
    def start_ts(self) -> pd.Timestamp:
        return pd.Timestamp(self.start)

    @property
    def end_ts(self) -> pd.Timestamp:
        return pd.Timestamp(self.end)


CRISIS_PERIODS: list[CrisisPeriod] = [
    CrisisPeriod(
        name="2008 Global Financial Crisis",
        start="2007-10-09",
        end="2009-03-09",
        description="S&P 500 peak-to-trough period around the global credit crisis.",
    ),
    CrisisPeriod(
        name="2011 Debt Ceiling and Eurozone Stress",
        start="2011-07-22",
        end="2011-10-03",
        description="U.S. debt-ceiling downgrade shock and Eurozone sovereign stress.",
    ),
    CrisisPeriod(
        name="2015-2016 China and Oil Growth Scare",
        start="2015-08-18",
        end="2016-02-11",
        description="Global growth scare tied to China devaluation concerns and oil weakness.",
    ),
    CrisisPeriod(
        name="2018 Q4 Fed Tightening and Trade War",
        start="2018-09-20",
        end="2018-12-24",
        description="Equity drawdown during Fed tightening and U.S.-China trade-war fears.",
    ),
    CrisisPeriod(
        name="2020 COVID Crash",
        start="2020-02-19",
        end="2020-03-23",
        description="Fast pandemic-driven market crash from S&P 500 peak to low.",
    ),
    CrisisPeriod(
        name="2022 Russia-Ukraine Invasion Shock",
        start="2022-02-24",
        end="2022-06-16",
        description="Initial invasion shock and commodity/inflation repricing period.",
    ),
    CrisisPeriod(
        name="2022 Inflation and Rate Shock",
        start="2022-01-03",
        end="2022-10-12",
        description="Rising inflation and aggressive Fed hiking cycle during the 2022 bear market.",
    ),
    CrisisPeriod(
        name="2023 Regional Banking Stress",
        start="2023-03-08",
        end="2023-05-04",
        description="U.S. regional-bank stress around Silicon Valley Bank, Signature, and First Republic.",
    ),
]


def filter_returns_for_period(
    returns: pd.DataFrame, period: CrisisPeriod
) -> pd.DataFrame:
    """Return daily returns inside a crisis period, inclusive of both dates."""

    index = pd.to_datetime(returns.index)
    mask = (index >= period.start_ts) & (index <= period.end_ts)
    return returns.loc[mask].copy()


def crisis_union_mask(
    index: pd.Index, periods: Iterable[CrisisPeriod] = CRISIS_PERIODS
) -> pd.Series:
    """Build one de-duplicated mask covering all configured crisis windows."""

    dt_index = pd.to_datetime(index)
    mask = pd.Series(False, index=index)
    for period in periods:
        mask |= (dt_index >= period.start_ts) & (dt_index <= period.end_ts)
    return mask


def earliest_crisis_start(periods: Iterable[CrisisPeriod] = CRISIS_PERIODS) -> pd.Timestamp:
    """Return the earliest crisis start date."""

    return min(period.start_ts for period in periods)

