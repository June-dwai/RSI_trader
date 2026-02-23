# 44 백테스트: Case1 3-Variant 비교

## 구성
- 기준 구조는 42와 동일: Case1 + Case2 합산 Total
- Case1만 아래 3가지로 비교
  - baseline (기존 40: hedge 5x)
  - baseline + hedge6x
  - baseline + debt relief + hedge6x
- Case2는 42와 동일 설정 유지

## 성과 요약
| curve | variant | initial_capital | final_equity | total_return_pct | cagr_pct | max_drawdown_pct | calmar_ratio | trades | long_trades | short_trades | win_rate_pct | profit_factor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| total_baseline_plus_case2 | baseline | 2000.0000 | 45573.1953 | 2178.6598 | 113.7793 | 64.7393 | 1.7575 | 1989 | 1235 | 754 | N/A | N/A |
| case1_baseline | baseline | 1000.0000 | 28615.4276 | 2761.5428 | 126.0528 | 76.8389 | 1.6405 | 610 | 544 | 66 | 91.8033 | 2.2092 |
| total_baseline_plus_hedge6x_plus_case2 | baseline_plus_hedge6x | 2000.0000 | 42914.1076 | 2045.7054 | 110.6784 | 65.5211 | 1.6892 | 1989 | 1235 | 754 | N/A | N/A |
| case1_baseline_plus_hedge6x | baseline_plus_hedge6x | 1000.0000 | 25956.3398 | 2495.6340 | 120.7546 | 79.8348 | 1.5126 | 610 | 544 | 66 | 91.8033 | 2.2027 |
| total_baseline_plus_debtrelief_hedge6x_plus_case2 | baseline_plus_debtrelief_hedge6x | 2000.0000 | 39587.8157 | 1879.3908 | 106.5877 | 64.7201 | 1.6469 | 1748 | 994 | 754 | N/A | N/A |
| case1_baseline_plus_debtrelief_hedge6x | baseline_plus_debtrelief_hedge6x | 1000.0000 | 22630.0479 | 2163.0048 | 113.5142 | 74.0666 | 1.5326 | 369 | 303 | 66 | 84.8238 | 1.7006 |
| case2_study42 | case2 | 1000.0000 | 16957.7677 | 1595.7768 | 99.0456 | 74.0774 | 1.3371 | 1379 | 691 | 688 | 99.6374 | 10373.6255 |

## Case1 전용 비교
| case1_variant | final_equity | total_return_pct | cagr_pct | max_drawdown_pct | calmar_ratio | trades | long_trades | short_trades | win_rate_pct | profit_factor | hedge_profit_applied_events | hedge_profit_applied_usd | campaign_count | campaign_residual_debt_sum | campaign_residual_credit_sum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 28615.4276 | 2761.5428 | 126.0528 | 76.8389 | 1.6405 | 610 | 544 | 66 | 91.8033 | 2.2092 | 0 | 0.0000 | 0 | 0.0000 | 0.0000 |
| baseline_plus_hedge6x | 25956.3398 | 2495.6340 | 120.7546 | 79.8348 | 1.5126 | 610 | 544 | 66 | 91.8033 | 2.2027 | 0 | 0.0000 | 0 | 0.0000 | 0.0000 |
| baseline_plus_debtrelief_hedge6x | 22630.0479 | 2163.0048 | 113.5142 | 74.0666 | 1.5326 | 369 | 303 | 66 | 84.8238 | 1.7006 | 16 | 36311.2203 | 303 | 19481.3434 | 79023.5523 |

## 장기 물림 구간 변화(기준 baseline long-window)
- baseline의 2024년 10월 이후 LONG 중 최장 보유 구간을 기준 윈도우로 사용
| variant | baseline_entry | baseline_exit | baseline_duration_days | baseline_num_entries | baseline_pnl | baseline_reason | overlap_long_trades | overlap_total_pnl | overlap_max_duration_days | overlap_mean_duration_days | relief_events_in_window | relief_applied_usd_in_window | relief_avg_bep_drop | relief_max_bep_drop |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 2025-10-06 17:36:00 | 2026-02-12 00:00:00 | 128.2667 | 5 | -54464.1566 | Final Close | 1 | -54464.1566 | 128.2667 | 128.2667 | 0 | 0.0000 | N/A | N/A |
| baseline_plus_hedge6x | 2025-10-06 17:36:00 | 2026-02-12 00:00:00 | 128.2667 | 5 | -54464.1566 | Final Close | 1 | -37767.5223 | 128.2667 | 128.2667 | 0 | 0.0000 | N/A | N/A |
| baseline_plus_debtrelief_hedge6x | 2025-10-06 17:36:00 | 2026-02-12 00:00:00 | 128.2667 | 5 | -54464.1566 | Final Close | 1 | -32927.6333 | 128.2667 | 128.2667 | 1 | 15375.0130 | 25161.8660 | 25161.8660 |

## 산출물
- Plot: `44_backtest_btcusdt_scale06_adx002_case1_debt_relief.png`
- Metrics CSV: `44_backtest_btcusdt_scale06_adx002_case1_debt_relief.csv`
- Curves CSV: `44_backtest_btcusdt_scale06_adx002_case1_debt_relief_curves.csv`
- Case1 compare CSV: `44_backtest_btcusdt_scale06_adx002_case1_debt_relief_case1_compare.csv`
- Debt events CSV: `44_backtest_btcusdt_scale06_adx002_case1_debt_relief_case1_debt_events.csv`
- Stuck compare CSV: `44_backtest_btcusdt_scale06_adx002_case1_debt_relief_late2024_stuck_compare.csv`
- Report: `44_backtest_btcusdt_scale06_adx002_case1_debt_relief.md`