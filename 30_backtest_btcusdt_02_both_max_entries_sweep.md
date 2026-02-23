# 30 Backtest: 02 Both-sides Max Entries Sweep

## Setup
- Base: 02 both-sides (long/short entries active), no-lookahead confirmed 4h touch
- Initial capital per run: `500 USDT`
- Entry scale: `0.50`
- Sweep max entries: `3, 4, 5, 6, 7`

## Results

| Max Entries | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 1997.5302 | 299.5060 | 40.0477 | 56.9281 | 0.7035 | 1304 | 655/649 | 99.6166 | 3918.4357 |
| 4 | 3850.4172 | 670.0834 | 64.2799 | 66.1941 | 0.9711 | 1362 | 675/687 | 99.6329 | 5808.1990 |
| 5 | 2567.0863 | 413.4173 | 48.8570 | 73.9728 | 0.6605 | 1385 | 699/686 | 99.6390 | 7063.7565 |
| 6 | 1343.2513 | 168.6503 | 27.1651 | 80.5492 | 0.3372 | 1422 | 717/705 | 99.6484 | 7781.3454 |
| 7 | 800.9110 | 60.1822 | 12.1391 | 89.6389 | 0.1354 | 1434 | 734/700 | 99.6513 | 8319.8380 |

## Best Cases
- Best CAGR: `max_entries=4` (CAGR `64.2799%`).
- Lowest MDD: `max_entries=3` (MDD `56.9281%`).
- Best Calmar: `max_entries=4` (Calmar `0.9711`).

## Delta vs max_entries=5
| Max Entries | Final Equity Delta | CAGR Delta (pp) | MDD Delta (pp) |
|---:|---:|---:|---:|
| 3 | -569.5562 | -8.8093 | -17.0447 |
| 4 | 1283.3308 | 15.4229 | -7.7787 |
| 5 | 0.0000 | 0.0000 | 0.0000 |
| 6 | -1223.8351 | -21.6919 | 6.5764 |
| 7 | -1766.1754 | -36.7178 | 15.6661 |

## Outputs
- Plot: `30_backtest_btcusdt_02_both_max_entries_sweep.png`
- Metrics: `30_backtest_btcusdt_02_both_max_entries_sweep.csv`
- Report: `30_backtest_btcusdt_02_both_max_entries_sweep.md`