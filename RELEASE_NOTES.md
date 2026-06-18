# Release Notes

## v0.1: Crisis Resilience Research Demo

This release is a publishable research/demo version of the Crisis Resilience Market Model.

### Added

- Historical crisis backtesting versus `SPY`
- Sector ETF and asset-class resilience ranking
- Crisis Resilience Score
- Historical context layer for wars, macro shocks, resources, companies, and technologies
- Forward-looking geopolitical and macro scenario engine
- Direct FRED macro integration
- News/RSS crisis sentiment classification
- Early-warning alert layer
- Portfolio stress testing
- Historical-analog scenario calibration
- Monte Carlo stress-path proxy
- Future crisis category resilience forecast
- Three publishable simulation reports:
  - Taiwan conflict / Pacific semiconductor shock
  - Middle East war / Strait of Hormuz energy shock
  - Credit / liquidity crisis
- Static HTML dashboard
- Executive findings report
- Full report pack
- Lightweight unit tests
- Publishing checklist and next-steps roadmap

### Current Positioning

This project is ready to publish as a quantitative research and scenario stress-testing demo.

It should not be presented as:

- Investment advice
- A prediction engine
- A trading signal
- A guarantee of crisis protection

### Recommended Demo

Use the Taiwan conflict simulation as the primary showcase because it ties together:

- Semiconductors
- Defense
- Cybersecurity
- Safe-haven liquidity
- Critical minerals
- Supply-chain risk
- Consumer cyclicals
- Portfolio stress testing

### Validation

Latest verification:

- Unit tests pass with `python -m unittest discover -s tests`
- Model run completes with `python main.py --skip-company-history --monte-carlo-runs 1000`
- Dashboard has no missing chart image references
