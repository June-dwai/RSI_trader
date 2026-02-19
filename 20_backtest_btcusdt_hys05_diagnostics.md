# 20 Diagnostics for 17 Best Case (`hys=0.50%`)

## Scope
- Strategy: same core logic as 17 (no-lookahead, raw data, fixed 5x trend hedge, long SL ON).
- Goal: locate where losses cluster and identify high-impact improvement candidates.

## Overall Metrics

| Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 27950.2987 | 2695.0299 | 124.7637 | 68.1363 | 1.8311 | 664 | 598/66 | 92.4699 | 2.9327 |

## Exposure & Signal Counters

| Item | Value |
|---|---:|
| Hedge On Ratio % | 47.3169 |
| Bearish Positive Net Ratio % | 0.0000 |
| Entry Condition True | 31914 |
| Blocked by EMA Touch | 1215 |
| Blocked by Cooldown | 2365 |
| Executed Long Entries | 1819 |

## Top Drawdown Episodes

| ID | Peak Time | Trough Time | Recovery Time | MDD % | Days UW | Long PnL | Short PnL | SL Trg | SL ReAdd | HedgeOn % | Bear+NetLong % |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015 | 2024-12-17 18:08 | 2025-04-16 17:59 | 2025-11-20 17:07 | 68.1363 | 337.9576 | 26903.3829 | -14312.3442 | 15 | 8 | 47.4932 | 0.0000 |
| 889 | 2023-04-15 00:26 | 2023-10-16 04:37 | 2023-10-30 09:28 | 43.0701 | 198.3764 | 4228.9983 | -621.3207 | 9 | 5 | 53.0283 | 0.0000 |
| 756 | 2023-01-30 04:12 | 2023-03-14 21:16 | 2023-03-31 14:40 | 43.0055 | 60.4361 | 4445.0922 | -1290.5720 | 10 | 3 | 19.0281 | 0.0000 |
| 181 | 2022-03-03 14:04 | 2022-03-16 18:32 | 2022-04-11 19:27 | 41.1868 | 39.2243 | 380.2317 | -218.0490 | 4 | 3 | 39.0341 | 0.0000 |
| 1753 | 2024-07-05 04:19 | 2024-09-18 16:04 | 2024-11-13 13:41 | 39.5490 | 131.3903 | 20016.1939 | -1377.6050 | 10 | 5 | 41.2186 | 0.0000 |

## PnL by Side/Reason (Worst to Best)

| Side | Reason | Trades | PnL Sum | Avg PnL | Win Rate % |
|---|---|---:|---:|---:|---:|
| LONG | Final Close | 1 | -19533.1021 | -19533.1021 | 0.0000 |
| SHORT | Hedge Close Trend Up | 65 | -10937.5106 | -168.2694 | 24.6154 |
| SHORT | Final Hedge Close | 1 | 18966.2049 | 18966.2049 | 100.0000 |
| LONG | Take Profit | 597 | 115878.3720 | 194.1011 | 100.0000 |

## Entry Quality Buckets

| Dimension | Bucket | Trades | Win Rate % | Avg PnL | PnL Sum |
|---|---|---:|---:|---:|---:|
| RSI | 0-10 | 14 | 100.0000 | 156.8177 | 2195.4474 |
| RSI | 10-15 | 188 | 100.0000 | 213.5328 | 40144.1617 |
| RSI | 15-18 | 396 | 99.7475 | 136.3779 | 54005.6608 |
| ADX | 0-20 | 83 | 100.0000 | 199.9735 | 16597.7993 |
| ADX | 20-30 | 181 | 99.4475 | 107.1355 | 19391.5283 |
| ADX | 30-40 | 164 | 100.0000 | 194.8142 | 31949.5320 |
| ADX | 40-60 | 143 | 100.0000 | 175.9881 | 25166.3007 |
| ADX | 60+ | 27 | 100.0000 | 120.0041 | 3240.1097 |
| EMA_Distance | 0.25-0.5% | 1 | 100.0000 | 187.9888 | 187.9888 |
| EMA_Distance | 0.5-1.0% | 3 | 100.0000 | 208.3410 | 625.0229 |
| EMA_Distance | 1.0-2.0% | 10 | 100.0000 | 197.5050 | 1975.0498 |
| EMA_Distance | 2.0%+ | 584 | 99.8288 | 160.2007 | 93557.2083 |

## Yearly Stability

| Year | Return % | MDD % | Trades | Win Rate % | Long PnL | Short PnL |
|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 136.9481 | 41.1868 | 97 | 93.8144 | 2956.9477 | 1810.0614 |
| 2023 | 225.7482 | 43.0701 | 205 | 94.1463 | 18205.4924 | -1913.0448 |
| 2024 | 111.5659 | 47.0945 | 262 | 94.2748 | 63884.5264 | -11678.1048 |
| 2025 | 83.5214 | 55.2190 | 88 | 81.8182 | 26903.3829 | -8369.8373 |
| 2026 | -6.3698 | 11.8517 | 12 | 91.6667 | -15605.0795 | 28179.6197 |

## Improvement Focus (for next case study)
- Directional downside under bearish 4h appears mostly neutralized (`Bear+NetLong %` near zero).
- Largest negative bucket is `LONG / Final Close` (PnL `-19533.1021` across 1 trades).
- In worst DD window, stop-loss trigger/readd counts were 15/8.
- Add/adjust entry filters only where bucket-level expectancy is weak, then re-check yearly split.

## Output Files
- plot: `20_backtest_btcusdt_hys05_diagnostics.png`
- metrics: `20_backtest_btcusdt_hys05_diagnostics_metrics.csv`
- drawdowns: `20_backtest_btcusdt_hys05_diagnostics_drawdowns.csv`
- reason pnl: `20_backtest_btcusdt_hys05_diagnostics_reason_pnl.csv`
- entry quality: `20_backtest_btcusdt_hys05_diagnostics_entry_quality.csv`
- yearly: `20_backtest_btcusdt_hys05_diagnostics_yearly.csv`
- exposure: `20_backtest_btcusdt_hys05_diagnostics_exposure.csv`