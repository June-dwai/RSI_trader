# 13 ETHUSDT - Best Hysteresis Fixed5x SL Sweep

## 1) Objective
- Test only stop-loss sensitivity on ETH for `08_best_hysteresis_fixed5x` logic.
- Keep hysteresis to best value from `08_backtest_btcusdt_hysteresis_sweep.csv`.
- Keep base params from `04.configure_baseline_params` except SL.

## 2) Test Setup
- Symbol: `ETHUSDT`
- Data period: `2022-01-01` to `2026-02-12`
- Hysteresis band fixed: `0.50%`
- Entry scale: `0.50` (base default)
- TP fixed: `1.20%` (baseline)
- SL sweep (%): `2.00`, `3.00`, `4.00`, `5.00`, `6.00`

## 3) Results

| SL | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Worst Month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `2.00%` | 4124.0419 | 312.4042 | 41.1340 | 86.6139 | 0.4749 | 298 | 226/72 | 82.2148 | 1.8974 | `2024-04 (-71.4481%)` |
| `3.00%` | 3839.6961 | 283.9696 | 38.7033 | 83.7689 | 0.4620 | 275 | 203/72 | 80.7273 | 1.8884 | `2025-01 (-66.9313%)` |
| `4.00%` | 4803.4398 | 380.3440 | 46.4661 | 84.7307 | 0.5484 | 306 | 234/72 | 82.6797 | 1.9806 | `2025-01 (-68.3359%)` |
| `5.00%` | 3861.5420 | 286.1542 | 38.8948 | 84.6175 | 0.4597 | 292 | 220/72 | 81.8493 | 2.1220 | `2025-01 (-65.9448%)` |
| `6.00%` | 5765.8367 | 476.5837 | 53.1170 | 84.4079 | 0.6293 | 287 | 215/72 | 81.5331 | 2.5039 | `2025-01 (-66.1715%)` |

## 4) Best Picks
- Best Final Equity: `6.00%` (`5765.8367 USDT`).
- Best Calmar: `6.00%` (`0.6293`).
- Lowest MDD: `3.00%` (`83.7689%`).

## 5) Output Files
- script: `13_backtest_ethusdt_best_hyst_fixed5x_sl_sweep.py`
- plot: `13_backtest_ethusdt_best_hyst_fixed5x_sl_sweep.png`
- metrics: `13_backtest_ethusdt_best_hyst_fixed5x_sl_sweep.csv`
- report: `13_backtest_ethusdt_best_hyst_fixed5x_sl_sweep.md`