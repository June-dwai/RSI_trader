# 49 Backtest: Study-47 Case1 Max Entries Sweep (Hedge Matched)

## Setup
- Strategy: case1 from study-47 only.
- Engine traits: long-only core + 4h confirmed trend short hedge, hysteresis 0.5%, ADX 002 logic.
- Change from study-48: hedge size is matched to max entries (hedge_multiple = max_entries).
- Symbol: `BTCUSDT`
- Initial capital per run: `1000 USDT`
- Entry scale: `0.60`
- Sweep max entries / hedge multiple: `3, 4, 5, 6`

## Results

| Max Entries | Hedge Multiple | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Hedge Open/Close |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 3 | 7895.7145 | 689.5714 | 65.2813 | 52.6137 | 1.2408 | 546 | 480/66 | 90.8425 | 2.8369 | 66/66 |
| 4 | 4 | 18733.8045 | 1773.3804 | 103.9256 | 64.8802 | 1.6018 | 598 | 532/66 | 91.6388 | 2.5073 | 66/66 |
| 5 | 5 | 28615.4276 | 2761.5428 | 126.0528 | 76.8389 | 1.6405 | 610 | 544/66 | 91.8033 | 2.2092 | 66/66 |
| 6 | 6 | 5946.0998 | 494.6100 | 54.2675 | 85.4925 | 0.6348 | 427 | 361/66 | 88.2904 | 2.0969 | 66/66 |

## Best Cases
- Best CAGR: `max_entries=5` (CAGR `126.0528%`).
- Lowest MDD: `max_entries=3` (MDD `52.6137%`).
- Best Calmar: `max_entries=5` (Calmar `1.6405`).

## Delta vs max_entries=5
| Max Entries | Final Equity Delta | CAGR Delta (pp) | MDD Delta (pp) |
|---:|---:|---:|---:|
| 3 | -20719.7131 | -60.7714 | -24.2252 |
| 4 | -9881.6231 | -22.1272 | -11.9587 |
| 5 | 0.0000 | 0.0000 | 0.0000 |
| 6 | -22669.3278 | -71.7853 | 8.6536 |

## Outputs
- Plot: `49_backtest_btcusdt_scale06_adx002_case1_max_entries_hedge_matched_sweep.png`
- Metrics: `49_backtest_btcusdt_scale06_adx002_case1_max_entries_hedge_matched_sweep.csv`
- Curves: `49_backtest_btcusdt_scale06_adx002_case1_max_entries_hedge_matched_sweep_curves.csv`
- Report: `49_backtest_btcusdt_scale06_adx002_case1_max_entries_hedge_matched_sweep.md`