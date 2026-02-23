# 43 Backtest: Study-42 Case2 Max Entries Sweep

## Setup
- Strategy: case2 from study-42 only.
- Engine traits: dual-direction, no short hedge, no hysteresis, ADX 002 logic, previous confirmed 4h touch only.
- Initial capital per run: `1000 USDT`
- Entry scale: `0.60`
- Sweep max entries: `3, 4, 5, 6, 7`

## Results

| Max Entries | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 9967.3172 | 896.7317 | 74.9162 | 63.1173 | 1.1869 | 1321 | 668/653 | 99.6215 | 6707.2059 |
| 4 | 16957.7677 | 1595.7768 | 99.0456 | 74.0774 | 1.3371 | 1379 | 691/688 | 99.6374 | 10373.6255 |
| 5 | 12590.8480 | 1159.0848 | 85.1428 | 80.7829 | 1.0540 | 1395 | 704/691 | 99.6416 | 12650.0613 |
| 6 | 7665.4301 | 666.5430 | 64.0959 | 83.8918 | 0.7640 | 1431 | 721/710 | 99.6506 | 14289.1010 |
| 7 | 2833.0171 | 183.3017 | 28.8178 | 94.0100 | 0.3065 | 1446 | 735/711 | 99.6542 | 14225.1119 |

## Best Cases
- Best CAGR: `max_entries=4` (CAGR `99.0456%`).
- Lowest MDD: `max_entries=3` (MDD `63.1173%`).
- Best Calmar: `max_entries=4` (Calmar `1.3371`).

## Delta vs max_entries=5
| Max Entries | Final Equity Delta | CAGR Delta (pp) | MDD Delta (pp) |
|---:|---:|---:|---:|
| 3 | -2623.5307 | -10.2265 | -17.6656 |
| 4 | 4366.9198 | 13.9029 | -6.7056 |
| 5 | 0.0000 | 0.0000 | 0.0000 |
| 6 | -4925.4179 | -21.0468 | 3.1089 |
| 7 | -9757.8308 | -56.3249 | 13.2270 |

## Outputs
- Plot: `43_backtest_btcusdt_case2_adx002_scale06_max_entries_sweep.png`
- Metrics: `43_backtest_btcusdt_case2_adx002_scale06_max_entries_sweep.csv`
- Curves: `43_backtest_btcusdt_case2_adx002_scale06_max_entries_sweep_curves.csv`
- Report: `43_backtest_btcusdt_case2_adx002_scale06_max_entries_sweep.md`