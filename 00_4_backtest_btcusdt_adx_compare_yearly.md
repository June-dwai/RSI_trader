# 00_4 ADX Comparison (Yearly)

## Setup
- Symbol: `BTCUSDT`
- Timeframe for ADX: `1m`
- ADX period: `14`
- Compared methods:
  1) `35-style`: mixed EWM smoothing ADX
  2) `002-style`: rolling mean ADX
- Plot resample: `30min`

## Yearly Stats
| Year | Bars | ADX35 Mean | ADX002 Mean | ADX35>=40 % | ADX002>=40 % | ADX35>=50 % | ADX002>=50 % | Mult disagree % | |ADX diff| mean | |ADX diff| p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 525508 | 24.4869 | 35.7452 | 9.0903 | 34.7974 | 2.8945 | 18.4595 | 32.3879 | 12.9983 | 30.4734 |
| 2023 | 525404 | 24.7395 | 36.3820 | 9.4630 | 36.1075 | 2.8898 | 19.8750 | 33.5685 | 13.3957 | 31.8949 |
| 2024 | 525567 | 23.7946 | 35.0853 | 7.2756 | 33.3493 | 1.8475 | 17.3285 | 31.4883 | 12.8316 | 30.3525 |
| 2025 | 525558 | 24.1455 | 35.5392 | 7.3746 | 34.4626 | 1.8017 | 18.4004 | 32.6282 | 12.9936 | 31.1551 |
| 2026 | 60451 | 24.6173 | 36.8390 | 8.2000 | 37.2450 | 1.8991 | 20.3222 | 35.3443 | 13.7462 | 32.4185 |

## Outputs
- Plot: `00_4_backtest_btcusdt_adx_compare_yearly.png`
- Report: `00_4_backtest_btcusdt_adx_compare_yearly.md`
- Yearly CSV: `00_4_backtest_btcusdt_adx_compare_yearly_yearly.csv`