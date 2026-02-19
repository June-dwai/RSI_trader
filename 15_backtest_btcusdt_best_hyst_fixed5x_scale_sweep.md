# 15 BTCUSDT - Best Hysteresis Fixed5x Scale Sweep

## 1) Objective
- Test only entry-scale sensitivity on BTC for `08_best_hysteresis_fixed5x` logic.
- Keep hysteresis to best value from `08_backtest_btcusdt_hysteresis_sweep.csv`.
- Keep base params from `04.configure_baseline_params` except scale.

## 2) Test Setup
- Symbol: `BTCUSDT`
- Data period: `2022-01-01` to `2026-02-12`
- Hysteresis band fixed: `0.50%`
- TP fixed: `1.20%` (baseline)
- SL fixed: `3.00%` (baseline)
- Scale sweep: `0.20`, `0.30`, `0.40`, `0.50`, `0.60`, `0.70`, `0.80`

## 3) Results

| Scale | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Worst Month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `0.2` | 5189.9609 | 418.9961 | 49.2487 | 30.9848 | 1.5894 | 701 | 635/66 | 92.8673 | 3.6276 | `2024-12 (-14.6087%)` |
| `0.3` | 10766.5779 | 976.6578 | 78.2281 | 44.5787 | 1.7548 | 701 | 635/66 | 92.8673 | 3.3346 | `2024-12 (-22.4521%)` |
| `0.4` | 21137.6862 | 2013.7686 | 110.0012 | 56.8637 | 1.9345 | 701 | 635/66 | 92.8673 | 3.1084 | `2024-12 (-30.6556%)` |
| `0.5` | 39367.8799 | 3836.7880 | 144.2867 | 67.8150 | 2.1277 | 701 | 635/66 | 92.8673 | 2.9320 | `2024-12 (-39.2188%)` |
| `0.6` | 69610.3757 | 6861.0376 | 180.6039 | 77.4141 | 2.3330 | 701 | 635/66 | 92.8673 | 2.7932 | `2024-12 (-48.1405%)` |
| `0.7` | 116790.7638 | 11579.0764 | 218.2319 | 85.6496 | 2.5480 | 701 | 635/66 | 92.8673 | 2.6836 | `2024-12 (-57.4190%)` |
| `0.8` | 185573.8038 | 18457.3804 | 256.1626 | 92.5167 | 2.7688 | 701 | 635/66 | 92.8673 | 2.5973 | `2024-12 (-67.0517%)` |

## 4) Best Picks
- Best Final Equity: `0.8` (`185573.8038 USDT`).
- Best Calmar: `0.8` (`2.7688`).
- Lowest MDD: `0.2` (`30.9848%`).

## 5) Interpretation
- Scale up increases both return and drawdown. In this run, `Final Equity`, `CAGR`, and `Calmar` all rose as scale increased.
- `Win Rate`, `Long/Short trades`, and `Avg holding hours` remained unchanged, showing this is mostly a position-size leverage effect.
- `Profit Factor` declines as scale rises (`0.20 -> 0.80`: `3.6276 -> 2.5973`), so higher return comes with lower margin-for-error per trade.
- Worst monthly drawdown expanded materially (`-14.61%` at `0.20` to `-67.05%` at `0.80`).

## 6) Delta vs Scale 0.50

| Scale | Final Equity Delta % | MDD Delta %p | Calmar Delta | Profit Factor Delta |
|---|---:|---:|---:|---:|
| `0.2` | -86.8168 | -36.8302 | -0.5382 | 0.6956 |
| `0.3` | -72.6514 | -23.2363 | -0.3728 | 0.4027 |
| `0.4` | -46.3073 | -10.9513 | -0.1932 | 0.1765 |
| `0.5` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `0.6` | 76.8202 | 9.5992 | 0.2053 | -0.1388 |
| `0.7` | 196.6651 | 17.8346 | 0.4203 | -0.2484 |
| `0.8` | 371.3838 | 24.7017 | 0.6412 | -0.3347 |

## 7) Practical Range
- Return-max objective: prefer `0.70~0.80` (highest equity and Calmar in this run).
- Drawdown-control objective: prefer `0.20~0.40` (MDD and worst-month loss materially lower).
- Balanced objective: `0.50~0.60` keeps high growth while limiting extreme drawdown expansion compared with `0.70+`.

## 8) Output Files
- script: `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.py`
- plot: `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.png`
- metrics: `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.csv`
- report: `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.md`