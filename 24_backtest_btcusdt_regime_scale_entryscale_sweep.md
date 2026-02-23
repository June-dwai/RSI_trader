# 24 Backtest: Regime-Based Scaling (from 00_1 findings)

## Regime Scaling Rule
- Use confirmed 4h features only (no look-ahead).
- Risk score components:
  - run_len_4h <= 8: +1
  - run_len_4h <= 3: +1
  - flip_count_30_4h >= 2: +1
  - flip_count_30_4h >= 4: +1
  - near_ema_ratio_30_4h >= 20: +1
  - near_ema_ratio_30_4h >= 40: +1
- Position scale:
  - score >= 4 -> 0.25
  - score >= 2 -> 0.5
  - else -> 1.0

## Sweep
- entry_scale: `0.3, 0.4, 0.5, 0.6, 0.7, 0.8`
- modes: `baseline` vs `regime_scaled`

## Metrics Table
| Mode | entry_scale | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Avg Entry Scale | Avg Risk Score |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| `baseline` | 0.3 | 8765.0120 | 776.5012 | 69.5331 | 44.9130 | 1.5482 | 664 | 598/66 | 92.4699 | 3.3201 | 1.0000 | 0.0000 |
| `baseline` | 0.4 | 16070.5925 | 1507.0592 | 96.4616 | 57.2094 | 1.6861 | 664 | 598/66 | 92.4699 | 3.1039 | 1.0000 | 0.0000 |
| `baseline` | 0.5 | 27950.2987 | 2695.0299 | 124.7637 | 68.1363 | 1.8311 | 664 | 598/66 | 92.4699 | 2.9327 | 1.0000 | 0.0000 |
| `baseline` | 0.6 | 46144.2768 | 4514.4277 | 153.9061 | 77.6838 | 1.9812 | 664 | 598/66 | 92.4699 | 2.7966 | 1.0000 | 0.0000 |
| `baseline` | 0.7 | 72266.6371 | 7126.6637 | 183.1709 | 85.8487 | 2.1336 | 664 | 598/66 | 92.4699 | 2.6883 | 1.0000 | 0.0000 |
| `baseline` | 0.8 | 107144.6513 | 10614.4651 | 211.6303 | 92.6349 | 2.2846 | 664 | 598/66 | 92.4699 | 2.6025 | 1.0000 | 0.0000 |
| `regime_scaled` | 0.3 | 8159.5328 | 715.9533 | 66.6076 | 45.7801 | 1.4549 | 664 | 598/66 | 92.4699 | 3.7507 | 0.9669 | 0.2457 |
| `regime_scaled` | 0.4 | 14646.0224 | 1364.6022 | 92.0767 | 58.1012 | 1.5848 | 664 | 598/66 | 92.4699 | 3.5355 | 0.9669 | 0.2457 |
| `regime_scaled` | 0.5 | 24971.7197 | 2397.1720 | 118.6883 | 68.9606 | 1.7211 | 664 | 598/66 | 92.4699 | 3.3615 | 0.9669 | 0.2457 |
| `regime_scaled` | 0.6 | 40473.7677 | 3947.3768 | 145.9380 | 78.3718 | 1.8621 | 664 | 598/66 | 92.4699 | 3.2192 | 0.9669 | 0.2457 |
| `regime_scaled` | 0.7 | 62320.2396 | 6132.0240 | 173.1557 | 86.3543 | 2.0052 | 664 | 598/66 | 92.4699 | 3.1018 | 0.9669 | 0.2457 |
| `regime_scaled` | 0.8 | 90983.5370 | 8998.3537 | 199.4831 | 92.9336 | 2.1465 | 664 | 598/66 | 92.4699 | 3.0044 | 0.9669 | 0.2457 |

## Delta (regime_scaled - baseline) by entry_scale
| entry_scale | Equity Delta | Equity Delta % | MDD Delta %pt | Calmar Delta |
|---:|---:|---:|---:|---:|
| 0.3 | -605.4792 | -6.9079 | 0.8671 | -0.0932 |
| 0.4 | -1424.5701 | -8.8645 | 0.8918 | -0.1014 |
| 0.5 | -2978.5790 | -10.6567 | 0.8244 | -0.1100 |
| 0.6 | -5670.5091 | -12.2887 | 0.6881 | -0.1191 |
| 0.7 | -9946.3975 | -13.7635 | 0.5056 | -0.1285 |
| 0.8 | -16161.1143 | -15.0835 | 0.2987 | -0.1381 |

## Highlights
- Best Final Equity: `baseline_es0.8` (entry_scale `0.8`, equity `107144.6513`)
- Best Calmar: `baseline_es0.8` (entry_scale `0.8`, calmar `2.2846`)
- Lowest MDD: `baseline_es0.3` (entry_scale `0.3`, MDD `44.9130%`)

## Outputs
- Plot: `24_backtest_btcusdt_regime_scale_entryscale_sweep.png`
- Metrics: `24_backtest_btcusdt_regime_scale_entryscale_sweep.csv`
- Report: `24_backtest_btcusdt_regime_scale_entryscale_sweep.md`