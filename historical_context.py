"""Historical interpretation layer for the crisis resilience model.

The price-based rankings still come from yfinance data. This file adds a
human-readable map of geopolitical context, resources, technologies, and
company groups so the charts explain what was happening around the returns.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CrisisContext:
    """Narrative context for one historical crisis window."""

    crisis: str
    context_type: str
    war_or_geopolitical_context: str
    market_pressure: str
    resources_that_mattered: str
    technologies_that_benefited: str
    company_examples: str


CRISIS_CONTEXTS: dict[str, CrisisContext] = {
    "2008 Global Financial Crisis": CrisisContext(
        crisis="2008 Global Financial Crisis",
        context_type="Financial crisis",
        war_or_geopolitical_context="Iraq/Afghanistan war era; crisis driver was credit and housing leverage.",
        market_pressure="Banks, real estate, discretionary spending, and industrial cyclicals sold off sharply.",
        resources_that_mattered="Gold and high-quality government bonds were important defensive stores of value.",
        technologies_that_benefited="Cloud infrastructure and digital advertising kept developing, but the crisis was not tech-led.",
        company_examples="Defensive staples, discount retail, gold miners, and high-quality large-cap tech are tested in the company universe.",
    ),
    "2011 Debt Ceiling and Eurozone Stress": CrisisContext(
        crisis="2011 Debt Ceiling and Eurozone Stress",
        context_type="Sovereign debt shock",
        war_or_geopolitical_context="Arab Spring and NATO Libya intervention overlapped with Eurozone sovereign stress.",
        market_pressure="Financials, exporters, cyclicals, and global growth-sensitive sectors were pressured.",
        resources_that_mattered="Gold, the U.S. dollar, and Treasuries were key safe-haven assets.",
        technologies_that_benefited="Mobile platforms, cloud software, and digital payments continued gaining strategic value.",
        company_examples="Large-cap software, consumer staples, healthcare, and defense companies are tested.",
    ),
    "2015-2016 China and Oil Growth Scare": CrisisContext(
        crisis="2015-2016 China and Oil Growth Scare",
        context_type="Growth and commodity shock",
        war_or_geopolitical_context="Middle East instability and Russia sanctions background; primary shock was China and oil.",
        market_pressure="Energy, materials, industrials, and emerging-market-sensitive companies were hit.",
        resources_that_mattered="Oil collapsed, while the U.S. dollar and Treasuries mattered as defensive assets.",
        technologies_that_benefited="Cloud computing, e-commerce scale, cybersecurity, and mobile ecosystems strengthened.",
        company_examples="Mega-cap platforms, cybersecurity, discount retail, energy producers, and miners are compared.",
    ),
    "2018 Q4 Fed Tightening and Trade War": CrisisContext(
        crisis="2018 Q4 Fed Tightening and Trade War",
        context_type="Policy and trade shock",
        war_or_geopolitical_context="U.S.-China trade war and tariff escalation dominated the geopolitical market narrative.",
        market_pressure="Semiconductors, industrials, materials, and global supply-chain stocks were pressured.",
        resources_that_mattered="Treasuries and the U.S. dollar gained importance as liquidity and safety proxies.",
        technologies_that_benefited="Cloud software and cybersecurity remained resilient strategic spending areas.",
        company_examples="Software, cybersecurity, defense, staples, semiconductors, and industrial bellwethers are tested.",
    ),
    "2020 COVID Crash": CrisisContext(
        crisis="2020 COVID Crash",
        context_type="Pandemic shock",
        war_or_geopolitical_context="Global pandemic response, supply-chain breakdowns, and emergency fiscal/monetary policy.",
        market_pressure="Travel, energy, banks, real estate, and discretionary cyclicals collapsed first.",
        resources_that_mattered="Short-term Treasuries, the U.S. dollar, gold, medical supplies, and later energy logistics mattered.",
        technologies_that_benefited="Remote work, cloud infrastructure, e-commerce, digital payments, cybersecurity, and mRNA biotech accelerated.",
        company_examples="Cloud platforms, e-commerce, digital payments, vaccine developers, staples, and logistics firms are tested.",
    ),
    "2022 Russia-Ukraine Invasion Shock": CrisisContext(
        crisis="2022 Russia-Ukraine Invasion Shock",
        context_type="War and commodity shock",
        war_or_geopolitical_context="Russia invaded Ukraine on 2022-02-24, triggering energy, food, defense, and sanctions shocks.",
        market_pressure="Europe-exposed, growth, rate-sensitive, and supply-chain-sensitive assets came under stress.",
        resources_that_mattered="Oil, natural gas, wheat, fertilizer, uranium, the U.S. dollar, and defense supply chains grew in importance.",
        technologies_that_benefited="Defense electronics, drones, satellites, cybersecurity, energy infrastructure, and semiconductor resilience gained urgency.",
        company_examples="Defense primes, energy producers, cyber firms, miners, and dollar-sensitive assets are compared.",
    ),
    "2022 Inflation and Rate Shock": CrisisContext(
        crisis="2022 Inflation and Rate Shock",
        context_type="Inflation and rate shock",
        war_or_geopolitical_context="Russia-Ukraine war amplified inflation already building from stimulus and supply-chain disruption.",
        market_pressure="Long-duration growth stocks, real estate, long bonds, and profitless technology were repriced lower.",
        resources_that_mattered="Energy, the U.S. dollar, short-duration Treasuries, and commodity-linked cash flows became more important.",
        technologies_that_benefited="Automation, energy efficiency, cybersecurity, and mission-critical enterprise software held strategic value.",
        company_examples="Energy majors, defense, cash-rich tech, staples, healthcare, and utilities are tested.",
    ),
    "2023 Regional Banking Stress": CrisisContext(
        crisis="2023 Regional Banking Stress",
        context_type="Banking and duration shock",
        war_or_geopolitical_context="War risk remained in the background; immediate driver was bank balance-sheet duration risk.",
        market_pressure="Regional banks, financials, real estate, and confidence-sensitive credit assets were pressured.",
        resources_that_mattered="Short-term Treasuries, money-market-like safety, gold, and liquidity became more valuable.",
        technologies_that_benefited="Large profitable AI/cloud platforms benefited from quality rotation and AI enthusiasm.",
        company_examples="Mega-cap AI/cloud platforms, gold, Treasuries, large banks, and regional-bank-sensitive proxies are tested.",
    ),
}


COMPANY_NAMES: dict[str, str] = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMD": "Advanced Micro Devices",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "META": "Meta Platforms",
    "ORCL": "Oracle",
    "ADBE": "Adobe",
    "CRM": "Salesforce",
    "PANW": "Palo Alto Networks",
    "FTNT": "Fortinet",
    "CRWD": "CrowdStrike",
    "LMT": "Lockheed Martin",
    "NOC": "Northrop Grumman",
    "GD": "General Dynamics",
    "RTX": "RTX",
    "XOM": "Exxon Mobil",
    "CVX": "Chevron",
    "COP": "ConocoPhillips",
    "SLB": "SLB",
    "FCX": "Freeport-McMoRan",
    "NEM": "Newmont",
    "JNJ": "Johnson & Johnson",
    "PFE": "Pfizer",
    "MRK": "Merck",
    "UNH": "UnitedHealth Group",
    "MRNA": "Moderna",
    "WMT": "Walmart",
    "COST": "Costco",
    "PG": "Procter & Gamble",
    "KO": "Coca-Cola",
    "JPM": "JPMorgan Chase",
    "BAC": "Bank of America",
    "GS": "Goldman Sachs",
    "BA": "Boeing",
    "CAT": "Caterpillar",
}


COMPANY_THEMES: dict[str, str] = {
    "AAPL": "Mega-cap technology",
    "MSFT": "Cloud and enterprise software",
    "NVDA": "Semiconductors and AI",
    "AMD": "Semiconductors",
    "GOOGL": "Digital advertising and cloud",
    "AMZN": "E-commerce and cloud",
    "META": "Digital advertising",
    "ORCL": "Enterprise software",
    "ADBE": "Creative software",
    "CRM": "Cloud software",
    "PANW": "Cybersecurity",
    "FTNT": "Cybersecurity",
    "CRWD": "Cybersecurity",
    "LMT": "Defense aerospace",
    "NOC": "Defense aerospace",
    "GD": "Defense and shipbuilding",
    "RTX": "Defense and aerospace",
    "XOM": "Integrated energy",
    "CVX": "Integrated energy",
    "COP": "Oil and gas production",
    "SLB": "Energy services",
    "FCX": "Copper and materials",
    "NEM": "Gold mining",
    "JNJ": "Healthcare defensive",
    "PFE": "Pharmaceuticals",
    "MRK": "Pharmaceuticals",
    "UNH": "Managed care",
    "MRNA": "mRNA biotechnology",
    "WMT": "Discount retail",
    "COST": "Warehouse retail",
    "PG": "Consumer staples",
    "KO": "Consumer staples",
    "JPM": "Large bank",
    "BAC": "Large bank",
    "GS": "Investment bank",
    "BA": "Aerospace cyclicals",
    "CAT": "Industrial cyclicals",
}


TECHNOLOGY_THEME_ROWS: list[dict[str, str]] = [
    {
        "theme": "Cloud infrastructure",
        "why_it_matters": "Remote work, scalable compute, enterprise resilience, and AI workloads increase demand.",
        "example_companies": "MSFT, AMZN, GOOGL, ORCL",
    },
    {
        "theme": "Cybersecurity",
        "why_it_matters": "War, sanctions, remote work, and digital infrastructure increase attack surfaces.",
        "example_companies": "PANW, FTNT, CRWD",
    },
    {
        "theme": "Semiconductors and AI",
        "why_it_matters": "Supply-chain resilience, defense electronics, data centers, and automation depend on chips.",
        "example_companies": "NVDA, AMD, AAPL",
    },
    {
        "theme": "Defense electronics and aerospace",
        "why_it_matters": "War raises demand for missiles, sensors, drones, satellites, logistics, and secure communications.",
        "example_companies": "LMT, NOC, GD, RTX",
    },
    {
        "theme": "mRNA and biotech platforms",
        "why_it_matters": "Pandemics increase the value of fast vaccine design, testing, manufacturing, and distribution.",
        "example_companies": "MRNA, PFE, MRK, JNJ",
    },
    {
        "theme": "Energy security technology",
        "why_it_matters": "Commodity shocks increase the value of production, refining, grid reliability, and efficiency.",
        "example_companies": "XOM, CVX, COP, SLB",
    },
    {
        "theme": "Digital commerce and payments",
        "why_it_matters": "Lockdowns and economic stress accelerate online ordering, fulfillment, and cashless transactions.",
        "example_companies": "AMZN, AAPL, GOOGL",
    },
]


RESOURCE_TICKERS: list[str] = ["GLD", "USO", "UUP", "TLT", "SHY", "XLE", "XLB"]


def company_universe_tickers() -> list[str]:
    """Return the company tickers used for data-driven winner analysis."""

    return list(COMPANY_NAMES.keys())


def build_context_table() -> pd.DataFrame:
    """Convert crisis context definitions into an exportable table."""

    return pd.DataFrame([context.__dict__ for context in CRISIS_CONTEXTS.values()])


def build_technology_theme_table() -> pd.DataFrame:
    """Return the technology themes used in the visual history charts."""

    return pd.DataFrame(TECHNOLOGY_THEME_ROWS)


def add_company_metadata(df: pd.DataFrame, ticker_column: str = "ticker") -> pd.DataFrame:
    """Attach company names and themes to a dataframe containing company tickers."""

    result = df.copy()
    result.insert(1, "company_name", result[ticker_column].map(COMPANY_NAMES))
    result.insert(2, "theme", result[ticker_column].map(COMPANY_THEMES))
    return result

