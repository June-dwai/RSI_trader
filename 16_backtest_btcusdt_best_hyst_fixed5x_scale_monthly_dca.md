# 16 BTCUSDT - Scale Sweep with Monthly 1000 USDT DCA

## 1) Objective
- Evaluate `15` strategy family under external cash flow scenario.
- Base strategy: `08_best_hysteresis_fixed5x` on BTC.
- Sweep `scale` and add fixed DCA cash inflow monthly.

## 2) DCA Assumption
- Updated by request: this report uses `monthly DCA`.
- DCA amount: `1000 USDT` each month (`frequency=monthly`).
- First-month DCA skipped: `True` (deposit starts from next month).

## 3) Test Setup
- Symbol: `BTCUSDT`
- Data period: `2022-01-01` to `2026-02-12`
- Hysteresis fixed to 08-best: `0.50%`
- TP fixed: `1.20%`
- SL fixed: `3.00%`
- Scale sweep: `0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80`

## 4) Summary Table

| Scale | Final Equity | Total Contribution | Net Profit | Account Return on Contribution % | TWR Total % | TWR CAGR % | NAV MDD % | Calmar(TWR/NAV) | Trades | Win Rate % | PF | Worst Month(Account) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `0.20` | 104594.4356 | 50000.0000 | 54594.4356 | 109.1889 | 375.3050 | 46.0909 | 30.6035 | 1.5061 | 701 | 92.8673 | 3.2505 | `2024-12 (-13.6021%)` |
| `0.30` | 158739.4224 | 50000.0000 | 108739.4224 | 217.4788 | 862.4948 | 73.4358 | 44.2037 | 1.6613 | 701 | 92.8673 | 3.1069 | `2024-12 (-21.8850%)` |
| `0.40` | 244742.8440 | 50000.0000 | 194742.8440 | 389.4857 | 1757.7379 | 103.5102 | 56.5404 | 1.8307 | 701 | 92.8673 | 2.9717 | `2024-12 (-30.3450%)` |
| `0.50` | 378205.7350 | 50000.0000 | 328205.7350 | 656.4115 | 3316.7517 | 136.0139 | 67.5545 | 2.0134 | 701 | 92.8673 | 2.8496 | `2024-12 (-39.0527%)` |
| `0.60` | 578598.3726 | 50000.0000 | 528598.3726 | 1057.1967 | 5882.0812 | 170.4503 | 77.2113 | 2.2076 | 701 | 92.8673 | 2.7429 | `2024-12 (-48.0539%)` |
| `0.70` | 866951.8324 | 50000.0000 | 816951.8324 | 1633.9037 | 9852.1999 | 206.0874 | 85.4934 | 2.4106 | 701 | 92.8673 | 2.6523 | `2024-12 (-57.3752%)` |
| `0.80` | 1260318.7943 | 50000.0000 | 1210318.7943 | 2420.6376 | 15588.4595 | 241.9101 | 92.3958 | 2.6182 | 701 | 92.8673 | 2.5772 | `2024-12 (-67.0305%)` |

## 5) Best by Objective
- Highest Final Equity: `scale=0.80` (`1260318.7943 USDT`).
- Highest Net Profit: `scale=0.80` (`1210318.7943 USDT`).
- Highest Strategy TWR CAGR: `scale=0.80` (`241.9101%`).
- Lowest Strategy NAV MDD: `scale=0.20` (`30.6035%`).

## 6) Interpretation
- Since contribution schedule is identical across scales, scale comparison remains meaningful for net profit and risk.
- Higher scale tends to increase final equity and net profit but also increases drawdown risk on strategy NAV.
- `Account Return on Contribution` reflects investor-level outcome including cash inflows.
- `TWR` and `NAV MDD` are flow-adjusted strategy metrics, useful for pure strategy quality.

## 7) Output Files
- script: `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.py`
- plot: `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.png`
- metrics: `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv`
- report: `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.md`