# Publishing Checklist

Use this checklist before posting the project publicly.

## Required Before Publishing

- [ ] Run `python main.py --monte-carlo-runs 1000` successfully.
- [ ] Open `outputs/crisis_resilience_dashboard.html` and confirm charts load.
- [ ] Review `outputs/executive_findings.md` for current-market language.
- [ ] Review `outputs/simulation_taiwan_conflict.md` as the primary case study.
- [ ] Confirm the README says this is not investment advice and not a prediction engine.
- [ ] Remove or ignore large generated cache files if publishing to GitHub.
- [ ] Do not publish personal brokerage exports or account data.
- [ ] Do not publish API keys, credentials, or private notes.

## Recommended GitHub Contents

Commit:

- Source code files
- `README.md`
- `PROJECT_SUMMARY.md`
- `PUBLISHING_CHECKLIST.md`
- `NEXT_STEPS.md`
- `requirements.txt`
- `run_model.sh`
- `tests/`
- A small set of demo images under `docs/demo_assets/`

Usually do not commit:

- Full `outputs/*.csv`
- Full `outputs/charts/*.png`
- `.venv/`
- `__pycache__/`
- Private portfolio files

## Suggested LinkedIn Post

I built a Python-based Crisis Resilience Market Model that backtests how sector ETFs, asset classes, macro proxies, and portfolio exposures behaved during major crisis windows, then stress-tests possible future scenarios such as Taiwan conflict, Middle East escalation, inflation shocks, and credit/liquidity crises.

The model uses `yfinance`, FRED macro data, scenario calibration, Monte Carlo stress paths, and a static dashboard to compare historical resilience versus `SPY`.

This is not a prediction engine or investment advice. It is a research and decision-support tool for understanding how crisis transmission channels can affect different asset categories.

## Demo Script

1. “This dashboard summarizes historical crisis resilience and current alert conditions.”
2. “The backtest ranks assets by return, drawdown, volatility, and correlation to `SPY` during crisis windows.”
3. “The scenario layer translates specific crises into expected beneficiaries and vulnerabilities.”
4. “The forecast playbook summarizes resilience by category for each possible crisis.”
5. “The simulation reports turn the model into presentation-ready case studies.”
6. “The limitations are explicit: this is not a forecast or investment recommendation.”

## Version Tag

Suggested first release name:

```text
v0.1-crisis-resilience-research
```
