# 08 Hysteresis Band Sweep

## Objective
- Test only hysteresis impact on fixed `base_qty * 5` hedge strategy.
- Keep all other 04 strategy rules unchanged.
- Use confirmed 4h trend only (`shift(1)`) to avoid look-ahead.

## Sweep Setup
- Bands tested: `0.00%`, `0.10%`, `0.20%`, `0.30%`, `0.50%`
- Mode naming: `hyst_XXpct` where `XX` is hysteresis band in percent.

## Results

| Band | Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `0.00%` | `hyst_0.00pct` | 20964.0793 | 1996.4079 | 109.5805 | 72.0598 | 1.5207 | 764 | 635/129 | 85.8639 | 2.6648 |
| `0.10%` | `hyst_0.10pct` | 24428.7896 | 2342.8790 | 117.5225 | 70.7236 | 1.6617 | 744 | 635/109 | 88.0376 | 2.7556 |
| `0.20%` | `hyst_0.20pct` | 27843.5216 | 2684.3522 | 124.5546 | 72.6146 | 1.7153 | 732 | 635/97 | 89.4809 | 2.7989 |
| `0.30%` | `hyst_0.30pct` | 35583.4562 | 3458.3456 | 138.3559 | 70.2339 | 1.9699 | 718 | 635/83 | 91.0864 | 2.9361 |
| `0.50%` | `hyst_0.50pct` | 39367.8799 | 3836.7880 | 144.2867 | 67.8150 | 2.1277 | 701 | 635/66 | 92.8673 | 2.9320 |

## Best Bands
- Best Final Equity: `0.50%` (`39367.8799` USDT, return `3836.7880%`).
- Best Calmar: `0.50%` (Calmar `2.1277`, MDD `67.8150%`).
- Lowest MDD: `0.50%` (MDD `67.8150%`, Final Equity `39367.8799` USDT).

## Output Files
- plot: `08_backtest_btcusdt_hysteresis_sweep.png`
- metrics: `08_backtest_btcusdt_hysteresis_sweep.csv`