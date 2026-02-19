# 17 Hysteresis Band Sweep (No-lookahead + Raw Data)

## Objective
- Re-run 08 hysteresis study with two corrections:
  1) `ema_touch` uses previous closed 4h candle only (`shift(1)`) to remove look-ahead.
  2) Data filtering disabled (no IQR filter, no 1m 10% jump-candle removal).
- Keep core strategy as fixed `base_qty * 5` hedge with 4h confirmed trend state.

## Sweep Setup
- Bands tested: `0.00%`, `0.10%`, `0.20%`, `0.30%`, `0.50%`
- Mode naming: `hyst_XXpct` where `XX` is hysteresis band in percent.

## Results

| Band | Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `0.00%` | `hyst_0.00pct` | 14849.2916 | 1384.9292 | 92.7216 | 72.3374 | 1.2818 | 727 | 598/129 | 85.1444 | 2.6619 |
| `0.10%` | `hyst_0.10pct` | 17289.4485 | 1628.9448 | 99.9854 | 71.0145 | 1.4080 | 707 | 598/109 | 87.4116 | 2.7503 |
| `0.20%` | `hyst_0.20pct` | 19650.4452 | 1865.0445 | 106.3084 | 72.8867 | 1.4585 | 695 | 598/97 | 88.9209 | 2.7947 |
| `0.30%` | `hyst_0.30pct` | 25143.7670 | 2414.3767 | 119.0538 | 70.5310 | 1.6880 | 681 | 598/83 | 90.6021 | 2.9351 |
| `0.50%` | `hyst_0.50pct` | 27950.2987 | 2695.0299 | 124.7637 | 68.1363 | 1.8311 | 664 | 598/66 | 92.4699 | 2.9327 |

## Best Bands
- Best Final Equity: `0.50%` (`27950.2987` USDT, return `2695.0299%`).
- Best Calmar: `0.50%` (Calmar `1.8311`, MDD `68.1363%`).
- Lowest MDD: `0.50%` (MDD `68.1363%`, Final Equity `27950.2987` USDT).

## Output Files
- plot: `17_backtest_btcusdt_hysteresis_sweep_nolookahead_raw.png`
- metrics: `17_backtest_btcusdt_hysteresis_sweep_nolookahead_raw.csv`