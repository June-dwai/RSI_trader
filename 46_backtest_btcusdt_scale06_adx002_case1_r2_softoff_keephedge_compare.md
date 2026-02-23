# 46 백테스트: Baseline(hedge5x) vs R2 Soft-OFF 변형 비교

## 구성
- 기본 구조: `Case1 + Case2` 합산 Total.
- 비교군에 `Case1 baseline(hedge5x)` 포함.
- Case2는 study-42 설정 그대로 고정.
- 실험군은 R2(bearish mature) Soft-OFF 2종.
  - block_hedge_open: OFF 중 hedge 신규 오픈 차단
  - keep_hedge_open: OFF 중에도 hedge 신규 오픈 허용

## OFF 동작(요청 반영)
- `Soft OFF`: 신규 진입 중지 + DCA/REENTRY 중지.
- hedge 동작은 variant별 정책으로 분리 비교.
- 기존 포지션은 TP/SL/청산 로직 유지.
- 상태 갱신은 4h 버킷에서만 수행 (no-lookahead 정렬 유지).
- OFF -> ON 전환은 최소 `4`개 4h bar 쿨다운.
- ON 조건은 `bullish and run_len_4h >= 2` (히스테리시스).

## Variant 정의
| variant | label | off_rule | on_rule | off_to_on_cooldown_4h_bars |
| --- | --- | --- | --- | --- |
| baseline_hedge5x | Baseline hedge5x | N/A (always ON) | N/A | 4 |
| r2_soft_off_block_hedgeopen | R2 soft-off (block hedge open) | bearish and run_len_4h >= 12 | bullish and run_len_4h >= 2 (after cooldown) | 4 |
| r2_soft_off_keep_hedgeopen | R2 soft-off (keep hedge open allowed) | bearish and run_len_4h >= 12 | bullish and run_len_4h >= 2 (after cooldown) | 4 |

## 성과 요약
| curve | variant | variant_label | initial_capital | final_equity | total_return_pct | cagr_pct | max_drawdown_pct | calmar_ratio | trades | long_trades | short_trades | win_rate_pct | profit_factor | case1_off_ratio_1m_pct | case1_off_ratio_4h_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| total_baseline_hedge5x_plus_case2 | baseline_hedge5x | Baseline hedge5x | 2000.0000 | 45573.1953 | 2178.6598 | 113.7793 | 64.7393 | 1.7575 | 1989 | 1235 | 754 | N/A | N/A | 0.0000 | 0.0000 |
| case1_baseline_hedge5x | baseline_hedge5x | Baseline hedge5x | 1000.0000 | 28615.4276 | 2761.5428 | 126.0528 | 76.8389 | 1.6405 | 610 | 544 | 66 | 91.8033 | 2.2092 | 0.0000 | 0.0000 |
| total_r2_soft_off_block_hedgeopen_plus_case2 | r2_soft_off_block_hedgeopen | R2 soft-off (block hedge open) | 2000.0000 | 44442.7593 | 2122.1380 | 112.4782 | 64.3197 | 1.7487 | 1924 | 1172 | 752 | N/A | N/A | 43.7651 | 43.7861 |
| case1_r2_soft_off_block_hedgeopen | r2_soft_off_block_hedgeopen | R2 soft-off (block hedge open) | 1000.0000 | 27484.9915 | 2648.4992 | 123.8480 | 76.8389 | 1.6118 | 545 | 481 | 64 | 91.1927 | 2.1961 | 43.7651 | 43.7861 |
| total_r2_soft_off_keep_hedgeopen_plus_case2 | r2_soft_off_keep_hedgeopen | R2 soft-off (keep hedge open allowed) | 2000.0000 | 40767.1332 | 1938.3567 | 108.0668 | 62.7290 | 1.7228 | 1926 | 1172 | 754 | N/A | N/A | 43.7651 | 43.7861 |
| case1_r2_soft_off_keep_hedgeopen | r2_soft_off_keep_hedgeopen | R2 soft-off (keep hedge open allowed) | 1000.0000 | 23809.3655 | 2280.9365 | 116.1681 | 76.8389 | 1.5118 | 547 | 481 | 66 | 90.8592 | 2.1908 | 43.7651 | 43.7861 |
| case2_study42_fixed | case2 | Case2 fixed | 1000.0000 | 16957.7677 | 1595.7768 | 99.0456 | 74.0774 | 1.3371 | 1379 | 691 | 688 | 99.6374 | 10373.6255 | N/A | N/A |

## Case1 + 상태 통계
| case1_variant | variant_label | off_switches | on_switches | off_ratio_1m_pct | off_ratio_4h_pct | blocked_open_signals | blocked_add_signals | blocked_hedge_open_signals | stress_off_ratio_1m_pct | final_equity | total_return_pct | cagr_pct | max_drawdown_pct | calmar_ratio | trades | win_rate_pct | profit_factor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_hedge5x | Baseline hedge5x | 0 | 0 | 0.0000 | 0.0000 | 0 | 0 | 0 | 0.0000 | 28615.4276 | 2761.5428 | 126.0528 | 76.8389 | 1.6405 | 610 | 91.8033 | 2.2092 |
| r2_soft_off_block_hedgeopen | R2 soft-off (block hedge open) | 45 | 44 | 43.7651 | 43.7861 | 342 | 1 | 216 | 73.6351 | 27484.9915 | 2648.4992 | 123.8480 | 76.8389 | 1.6118 | 545 | 91.1927 | 2.1961 |
| r2_soft_off_keep_hedgeopen | R2 soft-off (keep hedge open allowed) | 45 | 44 | 43.7651 | 43.7861 | 342 | 1 | 0 | 73.6351 | 23809.3655 | 2280.9365 | 116.1681 | 76.8389 | 1.5118 | 547 | 90.8592 | 2.1908 |

## 스트레스 윈도우 비교 (2025-10-01 ~ 2026-02-12)
| variant | variant_label | case1_window_return_pct | case1_window_mdd_pct | total_window_return_pct | total_window_mdd_pct | stress_off_ratio_1m_pct | window_start_equity_case1 | window_end_equity_case1 | window_start_equity_total | window_end_equity_total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_hedge5x | Baseline hedge5x | -9.9241 | 49.8196 | 6.1818 | 47.5104 | 0.0000 | 31768.1296 | 28615.4276 | 42919.9747 | 45573.1953 |
| r2_soft_off_block_hedgeopen | R2 soft-off (block hedge open) | -9.9241 | 49.8196 | 6.6669 | 47.4405 | 73.6351 | 30513.1479 | 27484.9915 | 41664.9929 | 44442.7593 |
| r2_soft_off_keep_hedgeopen | R2 soft-off (keep hedge open allowed) | -9.9241 | 49.8196 | 8.4682 | 47.1794 | 73.6351 | 26432.5601 | 23809.3655 | 37584.4052 | 40767.1332 |

## 산출물
- Plot: `46_backtest_btcusdt_scale06_adx002_case1_r2_softoff_keephedge_compare.png`
- Metrics CSV: `46_backtest_btcusdt_scale06_adx002_case1_r2_softoff_keephedge_compare.csv`
- Curves CSV: `46_backtest_btcusdt_scale06_adx002_case1_r2_softoff_keephedge_compare_curves.csv`
- Case1 regime stats CSV: `46_backtest_btcusdt_scale06_adx002_case1_r2_softoff_keephedge_compare_case1_regime_stats.csv`
- Regime events CSV: `46_backtest_btcusdt_scale06_adx002_case1_r2_softoff_keephedge_compare_regime_events.csv`
- Stress window CSV: `46_backtest_btcusdt_scale06_adx002_case1_r2_softoff_keephedge_compare_stress_window.csv`
- Report: `46_backtest_btcusdt_scale06_adx002_case1_r2_softoff_keephedge_compare.md`