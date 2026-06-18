# Crisis Resilience Market Model: Project Summary

## What This Is

The Crisis Resilience Market Model is a Python research project that studies how assets, sectors, macro proxies, and portfolio exposures behave during major crisis regimes.

It combines:

- Historical crisis backtesting against `SPY`
- ETF and asset-class resilience scoring
- Direct FRED macro indicators
- News/RSS crisis classification
- Forward-looking scenario stress tests
- Future crisis category resilience forecasts
- Portfolio stress testing
- Monte Carlo stress-path proxies
- Static HTML dashboard and Markdown reports

This is a decision-support and research tool. It does not predict future returns or guarantee portfolio protection.

## Why It Matters

Most market analysis treats crises as one generic risk-off event. This project separates crisis types:

- Financial crisis
- Pandemic shock
- Inflation/rate shock
- Middle East energy shock
- Taiwan/Pacific semiconductor shock
- Treasury liquidity scare
- Regional banking/CRE shock
- Cyber/market infrastructure shock
- AI/mega-cap unwind

The model shows that resilience depends on the crisis transmission channel. Gold, dollar liquidity, Treasuries, energy, defense, cybersecurity, and defensive equities behave differently depending on whether the shock is inflationary, deflationary, geopolitical, liquidity-driven, or supply-chain-driven.

## Current High-Level Findings

- `UUP`, `SHY`, `TLT`, and `GLD` rank highest historically across the configured crisis windows.
- Equity sectors usually act as relative winners or losers, not true hedges.
- Consumer staples, utilities, and healthcare are more defensive than cyclical sectors, but still have meaningful drawdown risk.
- Energy is crisis-specific: resilient in supply shocks, weaker in demand crashes.
- Taiwan conflict scenarios create high modeled pressure on semiconductors and consumer cyclicals, while lifting defense, cyber, and safe-haven liquidity.
- Middle East/Hormuz scenarios favor energy, defense, gold/dollar liquidity, and short-duration safety while pressuring travel, discretionary, and inflation-sensitive growth.
- Credit/liquidity scenarios pressure financials, real estate, and leverage-sensitive assets.

## How To Present It

Recommended positioning:

> A Python-based crisis resilience research and scenario stress-testing tool that backtests historical market behavior, scores asset resilience, and generates portfolio stress reports for possible future crises.

Avoid positioning it as:

- A trading signal engine
- A prediction model
- Investment advice
- A guaranteed crisis hedge selector

## Best Demo Flow

1. Show the dashboard executive snapshot.
2. Explain the historical resilience score.
3. Show the future crisis category forecast heatmap.
4. Open one simulation report, preferably the Taiwan conflict case study.
5. Show how the active portfolio is stress-tested.
6. Close with limitations and next build steps.

## Resume Bullet

Built a Python-based Crisis Resilience Market Model using `yfinance`, FRED macro data, scenario stress testing, Monte Carlo simulation, and static dashboard reporting to analyze asset and sector resilience across historical and hypothetical crisis regimes.
