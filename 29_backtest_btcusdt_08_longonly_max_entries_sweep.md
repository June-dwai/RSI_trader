# 29 Backtest: 08 Long-only Max Entries Sweep

## Setup
- Base: 08 long-only (hysteresis 0.5%, no-lookahead confirmed 4h touch/trend)
- Initial capital per run: `500 USDT`
- Entry scale: `0.50`
- Sweep max entries: `2, 3, 4, 5, 6, 7`

## Results

| Max Entries | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 1098.8549 | 119.7710 | 21.1041 | 50.9364 | 0.4143 | 349 | 283/66 | 85.6734 | 2.1000 |
| 3 | 1543.7225 | 208.7445 | 31.5403 | 53.0095 | 0.5950 | 408 | 342/66 | 87.7451 | 2.4102 |
| 4 | 3292.4002 | 558.4800 | 58.1429 | 47.7807 | 1.2169 | 443 | 377/66 | 88.7133 | 2.8158 |
| 5 | 13975.1494 | 2695.0299 | 124.7637 | 68.1363 | 1.8311 | 664 | 598/66 | 92.4699 | 2.9327 |
| 6 | 2096.5200 | 319.3040 | 41.7046 | 61.4386 | 0.6788 | 467 | 401/66 | 89.2934 | 2.2239 |
| 7 | 2002.5848 | 300.5170 | 40.1338 | 86.8821 | 0.4619 | 477 | 411/66 | 89.5178 | 2.0418 |

## Best Cases
- Best CAGR: `max_entries=5` (CAGR `124.7637%`).
- Lowest MDD: `max_entries=4` (MDD `47.7807%`).
- Best Calmar: `max_entries=5` (Calmar `1.8311`).

## Delta vs max_entries=5
| Max Entries | Final Equity Delta | CAGR Delta (pp) | MDD Delta (pp) |
|---:|---:|---:|---:|
| 2 | -12876.2944 | -103.6596 | -17.1999 |
| 3 | -12431.4268 | -93.2234 | -15.1268 |
| 4 | -10682.7492 | -66.6208 | -20.3555 |
| 5 | 0.0000 | 0.0000 | 0.0000 |
| 6 | -11878.6294 | -83.0591 | -6.6977 |
| 7 | -11972.5646 | -84.6299 | 18.7458 |

## Outputs
- Plot: `29_backtest_btcusdt_08_longonly_max_entries_sweep.png`
- Metrics: `29_backtest_btcusdt_08_longonly_max_entries_sweep.csv`
- Report: `29_backtest_btcusdt_08_longonly_max_entries_sweep.md`