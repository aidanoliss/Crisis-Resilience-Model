# Next Steps Roadmap

## v0.1: Publishable Research Demo

Status: ready after final review.

Scope:

- Historical crisis backtest
- Scenario stress engine
- FRED macro layer
- News sentiment triage
- Portfolio stress testing
- Future crisis forecast playbook
- Simulation case studies
- Static dashboard

Goal: publish as a portfolio-quality quantitative research project.

## v0.2: Validation And Testing

Add:

- More unit tests for scoring, data loading, forecast mapping, and report generation.
- Data-quality report for missing values, stale data, and ETF inception limitations.
- Walk-forward validation for crisis thresholds.
- Sensitivity analysis for Crisis Resilience Score weights.
- Alternative crisis-window definitions.

Goal: make the results more defensible.

## v0.3: Real Portfolio Analytics

Add:

- Brokerage-specific import adapters.
- Cash, options, fixed income, mutual funds, and duplicate account handling.
- Holding classification for unmapped securities.
- Position-level factor exposure: equity beta, duration, credit, oil, dollar, gold, sector.
- Portfolio optimization with constraints.

Goal: make the model useful with real holdings.

## v0.4: Better Forecasting And Simulation

Add:

- Factor-calibrated Monte Carlo instead of stress-score scaling.
- Historical crisis analog matching by volatility, VIX, credit spreads, rates, oil, and dollar.
- Bayesian or regime-switching scenario weights.
- Shock path simulation across multiple horizons.
- Scenario confidence intervals.

Goal: improve the simulation engine without pretending it predicts the future.

## v0.5: AI And News Intelligence

Add:

- LLM headline classification.
- Source quality scoring.
- Duplicate event clustering.
- Entity extraction: countries, companies, commodities, shipping lanes, cyber actors.
- Escalation/de-escalation timeline.

Goal: turn news triage into structured crisis intelligence.

## v0.6: Productization

Add:

- Streamlit or web app deployment.
- Portfolio upload in the UI.
- Scenario selector and custom crisis builder.
- Scheduled refreshes.
- Email/Slack/local alert delivery.
- PDF report export.

Goal: turn the research project into an interactive decision-support product.
