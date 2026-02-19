# 14 BTCUSDT - Best Hysteresis Fixed5x SL Sweep

## 1) Objective
- Test only stop-loss sensitivity on BTC for `08_best_hysteresis_fixed5x` logic.
- Keep hysteresis to best value from `08_backtest_btcusdt_hysteresis_sweep.csv`.
- Keep base params from `04.configure_baseline_params` except SL.

## 2) Test Setup
- Symbol: `BTCUSDT`
- Data period: `2022-01-01` to `2026-02-12`
- Hysteresis band fixed: `0.50%`
- Entry scale: `0.50` (base default)
- TP fixed: `1.20%` (baseline)
- SL sweep (%): `2.00`, `3.00`, `4.00`, `5.00`, `6.00`

## 3) Results

| SL | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Worst Month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `2.00%` | 4773.3527 | 377.3353 | 46.2424 | 62.9031 | 0.7351 | 427 | 361/66 | 88.2904 | 2.1919 | `2024-12 (-36.8054%)` |
| `3.00%` | 39367.8799 | 3836.7880 | 144.2867 | 67.8150 | 2.1277 | 701 | 635/66 | 92.8673 | 2.9320 | `2024-12 (-39.2188%)` |
| `4.00%` | 3365.6146 | 236.5615 | 34.3288 | 53.9964 | 0.6358 | 447 | 381/66 | 88.8143 | 2.6712 | `2024-08 (-22.4542%)` |
| `5.00%` | 9215.2417 | 821.5242 | 71.6108 | 65.4405 | 1.0943 | 619 | 553/66 | 92.0840 | 4.5895 | `2024-12 (-35.1464%)` |
| `6.00%` | 3875.1964 | 287.5196 | 39.0141 | 75.1832 | 0.5189 | 609 | 543/66 | 91.7898 | 3.6358 | `2024-12 (-43.0792%)` |

## 4) Best Picks
- Best Final Equity: `3.00%` (`39367.8799 USDT`).
- Best Calmar: `3.00%` (`2.1277`).
- Lowest MDD: `4.00%` (`53.9964%`).

## 5) Output Files
- script: `14_backtest_btcusdt_best_hyst_fixed5x_sl_sweep.py`
- plot: `14_backtest_btcusdt_best_hyst_fixed5x_sl_sweep.png`
- metrics: `14_backtest_btcusdt_best_hyst_fixed5x_sl_sweep.csv`
- report: `14_backtest_btcusdt_best_hyst_fixed5x_sl_sweep.md`