"""Live news and crisis-sentiment classification.

This is intentionally simple and transparent: RSS headlines are classified with
weighted keyword dictionaries into crisis categories. It is not a large language
model and it should be treated as a triage layer, not a truth engine.
"""

from __future__ import annotations

from email.utils import parsedate_to_datetime
import html
import os
from pathlib import Path
import re
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests


NEWS_QUERIES: dict[str, str] = {
    "geopolitical_market_stress": "geopolitical escalation markets war risk",
    "taiwan_semiconductors": "China Taiwan conflict semiconductor supply chain",
    "middle_east_energy": "Middle East war oil supply shock markets",
    "inflation_rates": "inflation shock interest rates markets",
    "credit_liquidity": "liquidity stress credit spreads banking markets",
    "de_escalation": "ceasefire de-escalation sanctions relief markets",
}

CATEGORY_KEYWORDS: dict[str, dict[str, int]] = {
    "geopolitical_escalation": {
        "attack": 3,
        "invasion": 4,
        "blockade": 4,
        "missile": 3,
        "war": 2,
        "troops": 2,
        "sanctions": 2,
        "taiwan": 3,
        "iran": 2,
        "middle east": 2,
        "red sea": 2,
        "hormuz": 4,
        "escalation": 4,
    },
    "supply_shock": {
        "supply shock": 5,
        "shortage": 3,
        "disruption": 3,
        "shipping": 2,
        "semiconductor": 3,
        "chips": 3,
        "oil": 3,
        "gas": 2,
        "lng": 2,
        "fertilizer": 2,
        "critical minerals": 3,
        "rare earth": 3,
    },
    "inflation_shock": {
        "inflation": 4,
        "cpi": 3,
        "prices": 2,
        "rate hike": 3,
        "higher for longer": 4,
        "treasury yields": 3,
        "fed": 2,
        "central bank": 2,
    },
    "liquidity_stress": {
        "liquidity": 4,
        "credit spreads": 4,
        "bank": 2,
        "default": 3,
        "funding": 3,
        "treasury market": 3,
        "financial stress": 4,
        "commercial real estate": 3,
        "deposit": 2,
    },
    "cyber_shock": {
        "cyberattack": 5,
        "hack": 4,
        "ransomware": 4,
        "payment system": 3,
        "exchange outage": 3,
        "critical infrastructure": 3,
    },
    "de_escalation": {
        "ceasefire": 5,
        "truce": 4,
        "peace talks": 4,
        "de-escalation": 5,
        "deescalation": 5,
        "sanctions relief": 4,
        "diplomacy": 2,
        "withdrawal": 3,
        "deal reached": 4,
    },
}

RISK_CATEGORIES = {
    "geopolitical_escalation",
    "supply_shock",
    "inflation_shock",
    "liquidity_stress",
    "cyber_shock",
}


def export_news_sentiment_tables(
    output_dir: str | Path,
    force_refresh: bool = False,
    max_items_per_query: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch RSS news, classify crisis categories, and export CSVs."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    cache_path = output_path / "news_items.csv"

    items = load_news_items(cache_path, force_refresh=force_refresh, max_items=max_items_per_query)
    summary = build_news_sentiment_summary(items)
    alerts = build_news_alerts(summary)

    items.to_csv(cache_path, index=False)
    summary.to_csv(output_path / "news_sentiment_summary.csv", index=False)
    alerts.to_csv(output_path / "news_alerts.csv", index=False)
    return items, summary, alerts


def load_news_items(
    cache_path: str | Path,
    force_refresh: bool,
    max_items: int,
) -> pd.DataFrame:
    """Load cached news unless a live refresh is requested."""

    cache = Path(cache_path)
    if cache.exists() and not force_refresh:
        return pd.read_csv(cache)

    try:
        items = fetch_and_classify_news(max_items_per_query=max_items)
    except Exception as exc:
        print(f"News RSS fetch unavailable: {exc}")
        if cache.exists():
            return pd.read_csv(cache)
        return _empty_news_items()

    if items.empty and cache.exists():
        return pd.read_csv(cache)
    return items


def fetch_and_classify_news(max_items_per_query: int = 30) -> pd.DataFrame:
    """Fetch Google News RSS query results and classify each headline."""

    rows: list[dict[str, str | int | float]] = []
    seen_links: set[str] = set()
    for query_name, query in NEWS_QUERIES.items():
        url = _google_news_rss_url(query)
        try:
            response = requests.get(
                url,
                timeout=5,
                headers={"User-Agent": "crisis-resilience-market-model/1.0"},
            )
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except Exception as exc:
            print(f"Skipping news query {query_name}: {exc}")
            continue
        for item in root.findall(".//item")[:max_items_per_query]:
            title = _clean_text(item.findtext("title", default=""))
            description = _clean_text(item.findtext("description", default=""))
            link = item.findtext("link", default="")
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            published = _parse_pubdate(item.findtext("pubDate", default=""))
            text = f"{title} {description}"
            scores = classify_text(text)
            top_category = max(scores, key=scores.get) if scores else "unclassified"
            top_score = int(scores.get(top_category, 0))
            risk_score = sum(scores.get(category, 0) for category in RISK_CATEGORIES)
            deescalation_score = scores.get("de_escalation", 0)
            rows.append(
                {
                    "query_name": query_name,
                    "published": published,
                    "title": title,
                    "link": link,
                    "top_category": top_category if top_score > 0 else "unclassified",
                    "top_category_score": top_score,
                    "risk_sentiment_score": int(risk_score - deescalation_score),
                    "geopolitical_escalation": scores.get("geopolitical_escalation", 0),
                    "supply_shock": scores.get("supply_shock", 0),
                    "inflation_shock": scores.get("inflation_shock", 0),
                    "liquidity_stress": scores.get("liquidity_stress", 0),
                    "cyber_shock": scores.get("cyber_shock", 0),
                    "de_escalation": deescalation_score,
                }
            )

    if not rows:
        return _empty_news_items()
    return pd.DataFrame(rows).sort_values(
        ["risk_sentiment_score", "top_category_score"], ascending=False
    )


def classify_text(text: str) -> dict[str, int]:
    """Classify a headline/summary into weighted crisis categories."""

    normalized = _normalize_text(text)
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword, weight in keywords.items():
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
            if re.search(pattern, normalized):
                score += weight
        scores[category] = score
    return scores


def build_news_sentiment_summary(items: pd.DataFrame) -> pd.DataFrame:
    """Aggregate headline classifications by category."""

    if items.empty:
        return _empty_summary()

    rows: list[dict[str, str | int | float]] = []
    for category in CATEGORY_KEYWORDS:
        category_scores = pd.to_numeric(items[category], errors="coerce").fillna(0)
        matching = items[category_scores > 0]
        if matching.empty:
            top_titles = ""
        else:
            top_titles = " | ".join(matching.head(5)["title"].astype(str).tolist())
        rows.append(
            {
                "category": category,
                "headline_count": int((category_scores > 0).sum()),
                "total_keyword_score": int(category_scores.sum()),
                "average_keyword_score": float(category_scores.mean()),
                "top_titles": top_titles,
            }
        )

    summary = pd.DataFrame(rows)
    risk_score = int(
        summary.loc[summary["category"].isin(RISK_CATEGORIES), "total_keyword_score"].sum()
        - summary.loc[summary["category"] == "de_escalation", "total_keyword_score"].sum()
    )
    summary["net_news_risk_score"] = risk_score
    return summary.sort_values("total_keyword_score", ascending=False)


def build_news_alerts(summary: pd.DataFrame) -> pd.DataFrame:
    """Convert category counts into alert rows."""

    if summary.empty:
        return _empty_alerts()

    rows: list[dict[str, str | int | float]] = []
    for row in summary.itertuples():
        if row.category == "de_escalation":
            if row.total_keyword_score >= 12:
                rows.append(
                    {
                        "source": "News RSS",
                        "category": row.category,
                        "stress_level": "De-escalation",
                        "stress_score": -min(100, int(row.total_keyword_score * 4)),
                        "headline_count": row.headline_count,
                        "message": "News flow contains de-escalation language.",
                        "top_titles": row.top_titles,
                    }
                )
            continue

        if row.total_keyword_score >= 35:
            level = "Stress"
        elif row.total_keyword_score >= 18 or row.headline_count >= 4:
            level = "Watch"
        else:
            continue
        rows.append(
            {
                "source": "News RSS",
                "category": row.category,
                "stress_level": level,
                "stress_score": min(100, int(row.total_keyword_score * 3)),
                "headline_count": row.headline_count,
                "message": f"News flow is clustering around {row.category.replace('_', ' ')}.",
                "top_titles": row.top_titles,
            }
        )

    if not rows:
        return _empty_alerts()
    return pd.DataFrame(rows).sort_values("stress_score", ascending=False)


def plot_news_sentiment_counts(summary: pd.DataFrame, output_file: str | Path) -> Path:
    """Plot classified headline counts by crisis category."""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if summary.empty:
        return output_path

    data = summary.sort_values("headline_count")
    colors = ["#0f766e" if category == "de_escalation" else "#b91c1c" for category in data["category"]]
    fig, ax = plt.subplots(figsize=(12, max(5, 0.5 * len(data))))
    ax.barh(data["category"].str.replace("_", " ").str.title(), data["headline_count"], color=colors)
    ax.set_title("Live News Classification by Crisis Category")
    ax.set_xlabel("Classified headline count")
    ax.grid(True, axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)
    return output_path


def _google_news_rss_url(query: str) -> str:
    encoded = quote_plus(f"{query} when:14d")
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"


def _clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _normalize_text(value: str) -> str:
    value = _clean_text(value).lower()
    value = value.replace("-", " ")
    value = re.sub(r"\s+", " ", value)
    return value


def _parse_pubdate(value: str) -> str:
    try:
        return parsedate_to_datetime(value).isoformat()
    except Exception:
        return ""


def _empty_news_items() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "query_name",
            "published",
            "title",
            "link",
            "top_category",
            "top_category_score",
            "risk_sentiment_score",
            "geopolitical_escalation",
            "supply_shock",
            "inflation_shock",
            "liquidity_stress",
            "cyber_shock",
            "de_escalation",
        ]
    )


def _empty_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "category",
            "headline_count",
            "total_keyword_score",
            "average_keyword_score",
            "top_titles",
            "net_news_risk_score",
        ]
    )


def _empty_alerts() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "source",
            "category",
            "stress_level",
            "stress_score",
            "headline_count",
            "message",
            "top_titles",
        ]
    )
