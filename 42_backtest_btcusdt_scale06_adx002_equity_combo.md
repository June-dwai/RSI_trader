# 42 Backtest: Total Equity + Two Scale0.60 ADX002 Curves

## Setup
- Capital allocation: each strategy starts with `1000` USDT.
- Top curve: `Total Equity = Case1 + Case2`.
- Case1: study-40 logic (`long-only + trend short hedge + hysteresis 0.5% + ADX 002 + scale 0.60`).
- Case2: dual-direction engine (`no short hedge`, `no hysteresis`, `ADX 002`, `scale 0.60`, `prev-touch-only`, `max entries 4`).

## Metrics
| Curve | Initial Capital | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `total_case1_plus_case2` | 2000.0000 | 45573.1953 | 2178.6598 | 113.7793 | 64.7393 | 1.7575 | 1989 | 1235/754 | N/A | N/A |
| `case1_study40_longonly_hedge_hyst05_adx002_scale06` | 1000.0000 | 28615.4276 | 2761.5428 | 126.0528 | 76.8389 | 1.6405 | 610 | 544/66 | 91.8033 | 2.2092 |
| `case2_dual_nohedge_nohyst_adx002_scale06_prevtouch_maxentries4` | 1000.0000 | 16957.7677 | 1595.7768 | 99.0456 | 74.0774 | 1.3371 | 1379 | 691/688 | 99.6374 | 10373.6255 |

## Outputs
- Plot: `42_backtest_btcusdt_scale06_adx002_equity_combo.png`
- Metrics CSV: `42_backtest_btcusdt_scale06_adx002_equity_combo.csv`
- Curve CSV: `42_backtest_btcusdt_scale06_adx002_equity_combo_curves.csv`
- Report: `42_backtest_btcusdt_scale06_adx002_equity_combo.md`