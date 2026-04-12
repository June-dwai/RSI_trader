# 50 Backtest: Study 42 Drawdown Diagnosis

## Setup
- Base curve: `42_backtest_btcusdt_scale06_adx002_equity_combo_curves.csv`
- Reproduced engines: `case1 = study-40 baseline`, `case2 = study-42 case2 exact`
- Goal: explain when large losses happened, why the losses were large, and which mitigation directions are most credible.
- Stress windows: `global_mdd_episode` + `15` forward crash windows

## Reproduction Check
| curve | final_equity | mdd_pct | cagr_pct |
| --- | --- | --- | --- |
| case1 | 28615.4276 | 76.8389 | 126.0528 |
| case2 | 16957.7677 | 74.0774 | 99.0456 |
| total | 45573.1953 | 64.7393 | 113.7793 |

## Global MDD
| start | end | total_return_pct | case1_return_pct | case2_return_pct | both_loss_rate | offset_rate | case1_loss_contribution_share |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2024-12-17 18:08:00 | 2025-04-16 17:59:00 | -64.7393 | -76.8389 | 2.9084 | 0.2017 | 0.0692 | 1.0068 |

## Selected Stress Windows
| window_id | start_timestamp | end_timestamp | total_return_pct | case1_return_pct | case2_return_pct | both_loss_rate | offset_rate | case1_loss_contribution_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| global_mdd_episode | 2024-12-17 18:08:00 | 2025-04-16 17:59:00 | -64.7393 | -76.8389 | 2.9084 | 0.2017 | 0.0692 | 1.0068 |
| worst_forward_1d_01 | 2025-10-09 21:19:00 | 2025-10-10 21:19:00 | -42.5652 | -44.5811 | -36.0900 | 0.5135 | 0.0000 | 0.7987 |
| worst_forward_1d_02 | 2023-03-12 15:31:00 | 2023-03-13 15:31:00 | -33.2077 | -25.9161 | -48.6670 | 0.0347 | 0.0902 | 0.5303 |
| worst_forward_1d_03 | 2024-12-19 12:10:00 | 2024-12-20 12:10:00 | -30.2719 | -31.2920 | -24.7886 | 0.5378 | 0.0007 | 0.8716 |
| worst_forward_1d_04 | 2025-01-07 07:02:00 | 2025-01-08 07:02:00 | -28.8343 | -33.2948 | -10.4987 | 0.5330 | 0.0000 | 0.9288 |
| worst_forward_1d_05 | 2024-08-26 22:15:00 | 2024-08-27 22:15:00 | -26.7326 | -28.1910 | -18.5545 | 0.5170 | 0.0000 | 0.8950 |
| worst_forward_4h_01 | 2025-10-10 17:19:00 | 2025-10-10 21:19:00 | -38.6192 | -40.7944 | -31.6220 | 0.5270 | 0.0000 | 0.8058 |
| worst_forward_4h_02 | 2023-03-13 11:31:00 | 2023-03-13 15:31:00 | -25.5844 | -21.2913 | -36.2277 | 0.2033 | 0.0622 | 0.5930 |
| worst_forward_4h_03 | 2024-12-05 18:28:00 | 2024-12-05 22:28:00 | -23.9765 | -24.7762 | -19.5260 | 0.5353 | 0.0000 | 0.8760 |
| worst_forward_4h_04 | 2024-01-03 08:09:00 | 2024-01-03 12:09:00 | -23.2713 | -24.2924 | -19.9104 | 0.5311 | 0.0000 | 0.8006 |
| worst_forward_4h_05 | 2024-03-05 15:56:00 | 2024-03-05 19:56:00 | -22.4400 | -23.0321 | -20.4605 | 0.5685 | 0.0000 | 0.7900 |
| worst_forward_7d_01 | 2024-12-17 20:58:00 | 2024-12-24 20:58:00 | -44.3760 | -47.5395 | -26.6896 | 0.3699 | 0.0424 | 0.9087 |
| worst_forward_7d_02 | 2025-10-03 21:19:00 | 2025-10-10 21:19:00 | -42.6611 | -44.8338 | -35.5960 | 0.4772 | 0.0001 | 0.8038 |
| worst_forward_7d_03 | 2022-03-03 13:33:00 | 2022-03-10 13:33:00 | -41.1495 | -40.0267 | -42.7709 | 0.1971 | 0.0798 | 0.5747 |
| worst_forward_7d_04 | 2023-03-07 21:16:00 | 2023-03-14 21:16:00 | -32.8020 | -30.5621 | -38.0214 | 0.0505 | 0.0130 | 0.6519 |
| worst_forward_7d_05 | 2024-09-28 03:02:00 | 2024-10-05 03:02:00 | -30.5189 | -34.1973 | -13.7494 | 0.3126 | 0.0511 | 0.9190 |

## Case1 State Checkpoints
| checkpoint | timestamp | price | equity | capital | entry_count | hedge_qty | long_unrealized | hedge_unrealized |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mdd_start | 2024-12-17 18:08:00 | 107572.4000 | 56002.7681 | 54739.8339 | 4 | 0.0000 | 1262.9342 | 0.0000 |
| first_full_entries | 2024-12-17 22:24:00 | 105782.4000 | 53794.0782 | 54726.8580 | 5 | 0.0000 | -932.7798 | 0.0000 |
| mdd_trough | 2025-04-16 17:59:00 | 83237.5000 | 12970.8611 | 32208.1622 | 5 | 0.0000 | -19237.3011 | 0.0000 |

## Worst Daily Losses
| date | return_total_pct | return_case1_pct | return_case2_pct | loss_rank_total |
| --- | --- | --- | --- | --- |
| 2025-01-07 00:00:00 | -22.9181 | -26.2417 | -9.1056 | 1 |
| 2022-02-04 00:00:00 | -21.5467 | 0.0000 | -37.5639 | 2 |
| 2024-03-19 00:00:00 | -20.9274 | -21.6189 | -18.5186 | 3 |
| 2023-03-13 00:00:00 | -20.1099 | -19.8612 | -20.7642 | 4 |
| 2025-10-10 00:00:00 | -19.8027 | -20.4489 | -17.7342 | 5 |
| 2022-03-04 00:00:00 | -19.2933 | -19.3115 | -19.2673 | 6 |
| 2024-08-27 00:00:00 | -18.1889 | -19.6521 | -10.0361 | 7 |
| 2022-03-10 00:00:00 | -17.9845 | -24.1347 | -7.3809 | 8 |
| 2024-12-18 00:00:00 | -17.3209 | -18.0767 | -13.0891 | 9 |
| 2024-01-12 00:00:00 | -16.2987 | -16.2420 | -16.4864 | 10 |

## Why The Loss Was Large
- The largest total drawdown episode ran from `2024-12-17 18:08:00` to `2025-04-16 17:59:00` with `total -64.7393%`.
- `case1` drove the damage: `-76.8389%` vs `case2 2.9084%`, so `case1` contributed `100.6816%` of the total drop before `case2` offsets.
- During the same window, `both_loss_rate=20.1677%` and `offset_rate=6.9214%`, so `case2` was not a reliable structural hedge when the portfolio was under stress.
- `case1` spent `92.7757%` of the MDD window at full size and `28.9084%` of underwater bars without hedge protection.
- `case1` hedge behavior was asymmetric: `13` hedge opens, `13` hedge closes, and `12` closes were loss-making `Trend Up` exits.
- At the trough timestamp `2025-04-16 17:59:00`, `entry_count=5`, `hedge_qty=0.0000`, `price=83237.5000`, `position_avg_entry=102262.6360`, `long_unrealized=-19237.3011`.
- `case2` helped only partially: in the MDD window it closed `124` trades, but the total series still showed frequent same-direction minute losses.

## How To Reduce The Loss
- Priority 1: reduce `case1` size concentration. Study 49 already showed `max_entries=4` improved case1 MDD to `64.8802%` versus `76.8389%` at `max_entries=5`.
- Priority 2: keep some hedge on when the long is fully built and still deeply underwater; the current hedge often closes on `Trend Up` before the real stress is over.
- Priority 3: add an earlier stress gate that blocks new DCA/reentry once bearish stress becomes mature, instead of waiting until the position is already at full size.
- Priority 4: cap `case1` portfolio weight. Study 42 step2a showed `A_static_w1_0.30` reached `MDD 54.0159%` with `CAGR 81.4618%`, materially below the full-`case1` configuration.

## Outputs
- Plot: `50_backtest_btcusdt_scale06_adx002_study42_drawdown_diagnosis.png`
- Stress windows: `50_backtest_btcusdt_scale06_adx002_study42_drawdown_diagnosis_stress_windows.csv`
- Window summary: `50_backtest_btcusdt_scale06_adx002_study42_drawdown_diagnosis_window_summary.csv`
- State timeline: `50_backtest_btcusdt_scale06_adx002_study42_drawdown_diagnosis_state_timeline.csv`
- Event summary: `50_backtest_btcusdt_scale06_adx002_study42_drawdown_diagnosis_event_summary.csv`
- Worst daily returns: `50_backtest_btcusdt_scale06_adx002_study42_drawdown_diagnosis_worst_daily_returns.csv`
- Report: `50_backtest_btcusdt_scale06_adx002_study42_drawdown_diagnosis.md`