# 16 BTCUSDT - Scale Sweep with Daily 1000 USDT DCA

## 1) Objective
- Evaluate `15` strategy family under external cash flow scenario.
- Base strategy: `08_best_hysteresis_fixed5x` on BTC.
- Sweep `scale` and add fixed DCA cash inflow daily.

## 2) DCA Assumption
- User text included both monthly and daily wording; this report follows the explicit intent: `daily DCA`.
- DCA amount: `1000 USDT` each day (`frequency=daily`).
- First-day DCA skipped: `True` (deposit starts from next date).

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
| `0.20` | 3091849.1982 | 1504000.0000 | 1587849.1982 | 105.5751 | 362.2455 | 45.1045 | 30.6958 | 1.4694 | 701 | 92.8673 | 3.2362 | `2024-12 (-13.4574%)` |
| `0.30` | 4638959.6404 | 1504000.0000 | 3134959.6404 | 208.4415 | 824.9428 | 71.7654 | 44.2891 | 1.6204 | 701 | 92.8673 | 3.0958 | `2024-12 (-21.7574%)` |
| `0.40` | 7068301.7630 | 1504000.0000 | 5564301.7630 | 369.9669 | 1664.9910 | 100.9914 | 56.6090 | 1.7840 | 701 | 92.8673 | 2.9636 | `2024-12 (-30.2439%)` |
| `0.50` | 10800761.7559 | 1504000.0000 | 9296761.7559 | 618.1358 | 3109.8489 | 132.4559 | 67.6056 | 1.9592 | 701 | 92.8673 | 2.8438 | `2024-12 (-38.9775%)` |
| `0.60` | 16358688.9331 | 1504000.0000 | 14854688.9331 | 987.6788 | 5455.6264 | 165.6298 | 77.2477 | 2.1441 | 701 | 92.8673 | 2.7389 | `2024-12 (-47.9998%)` |
| `0.70` | 24304359.7616 | 1504000.0000 | 22800359.7616 | 1515.9814 | 9030.2818 | 199.7383 | 85.5188 | 2.3356 | 701 | 92.8673 | 2.6495 | `2024-12 (-57.3370%)` |
| `0.80` | 35093521.0788 | 1504000.0000 | 33589521.0788 | 2233.3458 | 14096.8861 | 233.7038 | 92.4129 | 2.5289 | 701 | 92.8673 | 2.5753 | `2024-12 (-67.0037%)` |

## 5) Best by Objective
- Highest Final Equity: `scale=0.80` (`35093521.0788 USDT`).
- Highest Net Profit: `scale=0.80` (`33589521.0788 USDT`).
- Highest Strategy TWR CAGR: `scale=0.80` (`233.7038%`).
- Lowest Strategy NAV MDD: `scale=0.20` (`30.6958%`).

## 6) Interpretation
- Since contribution schedule is identical across scales, scale comparison remains meaningful for net profit and risk.
- Higher scale tends to increase final equity and net profit but also increases drawdown risk on strategy NAV.
- `Account Return on Contribution` reflects investor-level outcome including cash inflows.
- `TWR` and `NAV MDD` are flow-adjusted strategy metrics, useful for pure strategy quality.

## 7) Output Files
- script: `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.py`
- plot: `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.png`
- metrics: `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv`
- report: `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.md`