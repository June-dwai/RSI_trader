# 45 백테스트: Case1 Regime Soft-OFF 5종 비교 (Case2 고정)

## 구성
- 기본 구조: `Case1 + Case2` 합산 Total.
- Case1은 study-40 baseline(hedge5x, scale0.60) 유지.
- Case2는 study-42 설정 그대로 고정.
- 실험 변수는 `Case1 regime ON/OFF`만 변경 (5개).

## OFF 동작(요청 반영)
- `Soft OFF`: 신규 진입 중지 + DCA/REENTRY 중지 + 신규 hedge open 중지.
- 기존 포지션은 TP/SL/청산 로직 유지.
- 상태 갱신은 4h 버킷에서만 수행 (no-lookahead 정렬 유지).
- OFF -> ON 전환은 최소 `4`개 4h bar 쿨다운.
- ON 조건은 OFF 조건보다 보수적으로 구성(히스테리시스).

## Regime 정의
| regime_id | label | off_rule | on_rule | off_to_on_cooldown_4h_bars |
| --- | --- | --- | --- | --- |
| r1_bear_only | R1 bear_only | trend_4h_confirmed == bearish | trend_4h_confirmed == bullish and run_len_4h >= 2 | 4 |
| r2_bear_mature | R2 bear_mature | trend_4h_confirmed == bearish and run_len_4h >= 12 | trend_4h_confirmed == bullish and run_len_4h >= 2 | 4 |
| r3_bear_chop | R3 bear_chop | trend_4h_confirmed == bearish and flip_count_30_4h >= 2 | (trend_4h_confirmed == bullish and run_len_4h >= 2) or flip_count_30_4h <= 1 | 4 |
| r4_bear_highvol_p80 | R4 bear_highvol(P80) | trend_4h_confirmed == bearish and vol20_confirmed >= vol20_p80_2y | trend_4h_confirmed == bullish and vol20_confirmed <= vol20_p65_2y | 4 |
| r5_risk_or_crash | R5 risk_or_crash | risk_score_24 >= 4 or (trend_4h_confirmed == bearish and dd30_confirmed <= -6) | risk_score_24 <= 2 and ((trend_4h_confirmed == bullish and run_len_4h >= 2) or dd30_confirmed >= -3) | 4 |

## 성과 요약
| curve | variant | variant_label | initial_capital | final_equity | total_return_pct | cagr_pct | max_drawdown_pct | calmar_ratio | trades | long_trades | short_trades | win_rate_pct | profit_factor | case1_off_ratio_1m_pct | case1_off_ratio_4h_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| total_r1_bear_only_plus_case2 | r1_bear_only | R1 bear_only | 2000.0000 | 16957.7677 | 747.8884 | 68.1203 | 87.4929 | 0.7786 | 1854 | 1166 | 688 | N/A | N/A | 50.4801 | 50.4993 |
| case1_r1_bear_only | r1_bear_only | R1 bear_only | 1000.0000 | 0.0000 | -100.0000 | -99.9775 | 100.0000 | -0.9998 | 475 | 475 | 0 | 100.0000 | inf | 50.4801 | 50.4993 |
| total_r2_bear_mature_plus_case2 | r2_bear_mature | R2 bear_mature | 2000.0000 | 44442.7593 | 2122.1380 | 112.4782 | 64.3197 | 1.7487 | 1924 | 1172 | 752 | N/A | N/A | 43.7651 | 43.7861 |
| case1_r2_bear_mature | r2_bear_mature | R2 bear_mature | 1000.0000 | 27484.9915 | 2648.4992 | 123.8480 | 76.8389 | 1.6118 | 545 | 481 | 64 | 91.1927 | 2.1961 | 43.7651 | 43.7861 |
| total_r3_bear_chop_plus_case2 | r3_bear_chop | R3 bear_chop | 2000.0000 | 36427.6801 | 1721.3840 | 102.4527 | 83.1631 | 1.2319 | 1969 | 1229 | 740 | N/A | N/A | 5.6939 | 5.7035 |
| case1_r3_bear_chop | r3_bear_chop | R3 bear_chop | 1000.0000 | 19469.9123 | 1846.9912 | 105.8458 | 91.0855 | 1.1620 | 590 | 538 | 52 | 93.3898 | 2.3031 | 5.6939 | 5.7035 |
| total_r4_bear_highvol_p80_plus_case2 | r4_bear_highvol_p80 | R4 bear_highvol(P80) | 2000.0000 | 16957.7677 | 747.8884 | 68.1203 | 87.7929 | 0.7759 | 1909 | 1170 | 739 | N/A | N/A | 31.9058 | 31.9241 |
| case1_r4_bear_highvol_p80 | r4_bear_highvol_p80 | R4 bear_highvol(P80) | 1000.0000 | 0.0000 | -100.0000 | -99.9775 | 100.0000 | -0.9998 | 530 | 479 | 51 | 92.8302 | 3.4541 | 31.9058 | 31.9241 |
| total_r5_risk_or_crash_plus_case2 | r5_risk_or_crash | R5 risk_or_crash | 2000.0000 | 33459.5233 | 1572.9762 | 98.3136 | 68.0238 | 1.4453 | 1905 | 1167 | 738 | N/A | N/A | 23.3396 | 23.3577 |
| case1_r5_risk_or_crash | r5_risk_or_crash | R5 risk_or_crash | 1000.0000 | 16501.7555 | 1550.1756 | 97.7306 | 83.7605 | 1.1668 | 526 | 476 | 50 | 92.2053 | 2.2315 | 23.3396 | 23.3577 |
| case2_study42_fixed | case2 | Case2 fixed | 1000.0000 | 16957.7677 | 1595.7768 | 99.0456 | 74.0774 | 1.3371 | 1379 | 691 | 688 | 99.6374 | 10373.6255 | N/A | N/A |

## Case1 + Regime 상태 통계
| case1_variant | variant_label | off_switches | on_switches | off_ratio_1m_pct | off_ratio_4h_pct | blocked_open_signals | blocked_add_signals | blocked_hedge_open_signals | stress_off_ratio_1m_pct | final_equity | total_return_pct | cagr_pct | max_drawdown_pct | calmar_ratio | trades | win_rate_pct | profit_factor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| r1_bear_only | R1 bear_only | 64 | 63 | 50.4801 | 50.4993 | 367 | 7 | 4475 | 77.7402 | 0.0000 | -100.0000 | -99.9775 | 100.0000 | -0.9998 | 475 | 100.0000 | inf |
| r2_bear_mature | R2 bear_mature | 45 | 44 | 43.7651 | 43.7861 | 342 | 1 | 216 | 73.6351 | 27484.9915 | 2648.4992 | 123.8480 | 76.8389 | 1.6118 | 545 | 91.1927 | 2.1961 |
| r3_bear_chop | R3 bear_chop | 35 | 35 | 5.6939 | 5.7035 | 41 | 3 | 493 | 1.4928 | 19469.9123 | 1846.9912 | 105.8458 | 91.0855 | 1.1620 | 590 | 93.3898 | 2.3031 |
| r4_bear_highvol_p80 | R4 bear_highvol(P80) | 24 | 23 | 31.9058 | 31.9241 | 991 | 1 | 1030 | 63.3185 | 0.0000 | -100.0000 | -99.9775 | 100.0000 | -0.9998 | 530 | 92.8302 | 3.4541 |
| r5_risk_or_crash | R5 risk_or_crash | 92 | 91 | 23.3396 | 23.3577 | 501 | 5 | 976 | 37.1869 | 16501.7555 | 1550.1756 | 97.7306 | 83.7605 | 1.1668 | 526 | 92.2053 | 2.2315 |

## 스트레스 윈도우 비교 (2025-10-01 ~ 2026-02-12)
| variant | variant_label | case1_window_return_pct | case1_window_mdd_pct | total_window_return_pct | total_window_mdd_pct | stress_off_ratio_1m_pct | window_start_equity_case1 | window_end_equity_case1 | window_start_equity_total | window_end_equity_total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| r1_bear_only | R1 bear_only | -100.0000 | 100.0000 | -74.4037 | 87.4929 | 77.7402 | 55098.9163 | 0.0000 | 66250.7614 | 16957.7677 |
| r2_bear_mature | R2 bear_mature | -9.9241 | 49.8196 | 6.6669 | 47.4405 | 73.6351 | 30513.1479 | 27484.9915 | 41664.9929 | 44442.7593 |
| r3_bear_chop | R3 bear_chop | -12.3048 | 49.8196 | 9.2165 | 46.8745 | 1.4928 | 22201.7982 | 19469.9123 | 33353.6433 | 36427.6801 |
| r4_bear_highvol_p80 | R4 bear_highvol(P80) | N/A | N/A | 52.0624 | 40.0970 | 63.3185 | 0.0000 | 0.0000 | 11151.8451 | 16957.7677 |
| r5_risk_or_crash | R5 risk_or_crash | -17.2111 | 49.8196 | 7.6417 | 46.6139 | 37.1869 | 19932.3276 | 16501.7555 | 31084.1727 | 33459.5233 |

## 산출물
- Plot: `45_backtest_btcusdt_scale06_adx002_case1_regime_soft_off.png`
- Metrics CSV: `45_backtest_btcusdt_scale06_adx002_case1_regime_soft_off.csv`
- Curves CSV: `45_backtest_btcusdt_scale06_adx002_case1_regime_soft_off_curves.csv`
- Case1 regime stats CSV: `45_backtest_btcusdt_scale06_adx002_case1_regime_soft_off_case1_regime_stats.csv`
- Regime events CSV: `45_backtest_btcusdt_scale06_adx002_case1_regime_soft_off_regime_events.csv`
- Stress window CSV: `45_backtest_btcusdt_scale06_adx002_case1_regime_soft_off_stress_window.csv`
- Report: `45_backtest_btcusdt_scale06_adx002_case1_regime_soft_off.md`