# Study 111: 5분 SR + SMC Profit-Max

## Setup
- Data: latest local `BTCUSDT` 1m cache from `2022-01-01` onward.
- Execution: `5m` signal close -> next `1m` open fill, intrabar exits on `1m` high/low, stop-first if TP and SL touch together.
- SR follows the actual Pine code: `white = avg(EMA20[1m], EMA1800[1m])`, `red = avg(EMA20[1m], EMA1800[2m])`, floors = `avg - ATR14[1m]`.
- Stage 1 uses SR + proxy SMC. Stage 2 rechecks the best variants with Pine-near internal structure gates.
- Full-stack pass uses the declared grids with cached coordinate sweeps to keep runtime tractable.

## Winner
- Winner: `stage2_exact_choch_ob_reclaim_white_floor_lb12_rw2_close_above_white_es0.60_me3_addavg_minus_0.5ATR_equal_cd4_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gaterelaxed` -> equity `1000.6153`, CAGR `0.0146%`, MDD `0.2496%`, Calmar `0.0587`, trades `1`
- Winning entry family: `choch_ob_reclaim` with gate `relaxed`
- `110 gap_12` 대비 uplift: equity `-127.2918`
- `SR-only` 대비 uplift: equity `226.3923`
- `proxy winner vs exact winner` 차이: equity `-94.5428`
- Profit-max와 risk-profile 충돌 정도: `meaningful`

## Benchmarks
| Variant | Stage | Final Equity | Total Return % | CAGR % | MDD % | Calmar | Trades |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| buy_hold | benchmark | 1548.4270 | 54.8427 | 10.9704 | 67.8001 | 0.1618 | 1 |
| gap_12 | benchmark | 1127.9070 | 12.7907 | 2.9069 | 35.1812 | 0.0826 | 313 |
| stage1_fullstack_choch_ob_reclaim_white_floor_lb12_rw2_close_above_white_es0.60_me3_addavg_minus_0.5ATR_equal_cd4_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gatenone | stage1_fullstack | 1095.1581 | 9.5158 | 2.1877 | 2.2609 | 0.9676 | 6 |
| stage2_exact_choch_ob_reclaim_white_floor_lb12_rw2_close_above_white_es0.60_me3_addavg_minus_0.5ATR_equal_cd4_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gaterelaxed | stage2_exact | 1000.6153 | 0.0615 | 0.0146 | 0.2496 | 0.0587 | 1 |
| stage1_fullstack_band_bounce_red_floor_es0.30_me1_addnone_equal_cd2_stopob_low-0.1ATR_tp3R_fixed_hold96_gatenone | stage1_fullstack | 774.2230 | -22.5777 | -5.9104 | 24.1941 | -0.2443 | 1852 |

## Stage 2 Exact Gate Ranking
| Variant | Gate | Final Equity | CAGR % | MDD % | Calmar | Trades |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| stage2_exact_choch_ob_reclaim_white_floor_lb12_rw2_close_above_white_es0.60_me3_addavg_minus_0.5ATR_equal_cd4_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gaterelaxed | relaxed | 1000.6153 | 0.0146 | 0.2496 | 0.0587 | 1 |
| stage2_exact_choch_ob_reclaim_white_floor_lb12_rw3_close_above_white_es0.60_me3_addob_revisit_equal_cd0_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gaterelaxed | relaxed | 1000.6153 | 0.0146 | 0.2496 | 0.0587 | 1 |
| stage2_exact_choch_ob_reclaim_white_floor_lb12_rw2_close_above_white_es0.60_me3_addavg_minus_0.5ATR_equal_cd4_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gatestrict | strict | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |
| stage2_exact_choch_ob_reclaim_white_floor_lb12_rw3_close_above_white_es0.60_me3_addob_revisit_equal_cd0_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gatestrict | strict | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |
| stage2_exact_sweep_reclaim_overlap_lb12_rw2_proxy_bos_es0.60_me3_addavg_minus_0.5ATR_equal_cd2_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gatestrict | strict | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |
| stage2_exact_sweep_reclaim_overlap_lb12_rw2_proxy_bos_es0.60_me3_addavg_minus_0.5ATR_equal_cd2_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gaterelaxed | relaxed | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |
| stage2_exact_sweep_reclaim_overlap_lb12_rw3_proxy_bos_es0.60_me2_addob_revisit_equal_cd4_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gatestrict | strict | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |
| stage2_exact_sweep_reclaim_overlap_lb12_rw3_proxy_bos_es0.60_me2_addob_revisit_equal_cd4_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gaterelaxed | relaxed | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |
| stage2_exact_sweep_reclaim_overlap_lb12_rw1_proxy_bos_es0.60_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tp3R_fixed_hold48_gatestrict | strict | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |
| stage2_exact_sweep_reclaim_overlap_lb12_rw1_proxy_bos_es0.60_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tp3R_fixed_hold48_gaterelaxed | relaxed | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |
| stage2_exact_choch_ob_reclaim_white_floor_lb24_rw3_close_above_white_es0.60_me1_addnone_equal_cd2_stopsweep_low-0.2ATR_tp3R_fixed_hold24_gatestrict | strict | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |
| stage2_exact_choch_ob_reclaim_white_floor_lb24_rw3_close_above_white_es0.60_me1_addnone_equal_cd2_stopsweep_low-0.2ATR_tp3R_fixed_hold24_gaterelaxed | relaxed | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |

## Stage 1 Full-Stack Top 10
| Variant | Entry Family | Final Equity | CAGR % | MDD % | Calmar | Trades |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| stage1_fullstack_choch_ob_reclaim_white_floor_lb12_rw2_close_above_white_es0.60_me3_addavg_minus_0.5ATR_equal_cd4_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gatenone | choch_ob_reclaim | 1095.1581 | 2.1877 | 2.2609 | 0.9676 | 6 |
| stage1_fullstack_choch_ob_reclaim_white_floor_lb12_rw3_close_above_white_es0.60_me3_addob_revisit_equal_cd0_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gatenone | choch_ob_reclaim | 1078.4757 | 1.8149 | 4.0030 | 0.4534 | 9 |
| stage1_fullstack_sweep_reclaim_overlap_lb12_rw2_proxy_bos_es0.60_me3_addavg_minus_0.5ATR_equal_cd2_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gatenone | sweep_reclaim | 1046.1626 | 1.0802 | 1.3839 | 0.7805 | 6 |
| stage1_fullstack_sweep_reclaim_overlap_lb12_rw3_proxy_bos_es0.60_me2_addob_revisit_equal_cd4_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gatenone | sweep_reclaim | 1045.0658 | 1.0550 | 1.1608 | 0.9088 | 8 |
| stage1_fullstack_sweep_reclaim_overlap_lb12_rw1_proxy_bos_es0.60_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tp3R_fixed_hold48_gatenone | sweep_reclaim | 1010.6726 | 0.2531 | 0.3186 | 0.7944 | 1 |
| stage1_fullstack_choch_ob_reclaim_white_floor_lb24_rw3_close_above_white_es0.60_me1_addnone_equal_cd2_stopsweep_low-0.2ATR_tp3R_fixed_hold24_gatenone | choch_ob_reclaim | 1004.3180 | 0.1026 | 0.0521 | 1.9715 | 2 |
| stage1_fullstack_choch_ob_reclaim_white_floor_lb36_rw3_close_above_white_es0.60_me1_addnone_equal_cd2_stopsweep_low-0.2ATR_tp3R_fixed_hold24_gatenone | choch_ob_reclaim | 1004.3180 | 0.1026 | 0.0521 | 1.9715 | 2 |
| stage1_fullstack_sweep_reclaim_red_floor_lb36_rw1_close_above_prev3bar_high_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | sweep_reclaim | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |
| stage1_fullstack_sweep_reclaim_red_floor_lb36_rw1_proxy_bos_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | sweep_reclaim | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |
| stage1_fullstack_sweep_reclaim_overlap_lb24_rw1_close_above_prev3bar_high_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | sweep_reclaim | 1000.0000 | 0.0000 | -0.0000 | N/A | 0 |

## Sanity Leaderboard
| Variant | Stage | Final Equity | CAGR % | MDD % | Trades |
| --- | --- | ---: | ---: | ---: | ---: |
| stage1_coarse_sweep_reclaim_red_floor_lb24_rw2_close_above_white_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | stage1_coarse | 973.2068 | -0.6445 | 6.3672 | 45 |
| stage1_coarse_sweep_reclaim_red_floor_lb24_rw3_close_above_white_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | stage1_coarse | 972.7212 | -0.6563 | 6.4139 | 47 |
| stage1_coarse_sweep_reclaim_overlap_lb12_rw1_close_above_white_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | stage1_coarse | 961.4770 | -0.9309 | 5.6204 | 44 |
| stage1_coarse_sweep_reclaim_overlap_lb12_rw2_close_above_white_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | stage1_coarse | 958.9812 | -0.9922 | 6.6312 | 60 |
| stage1_coarse_sweep_reclaim_overlap_lb12_rw3_close_above_white_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | stage1_coarse | 958.5027 | -1.0040 | 6.6778 | 62 |
| stage1_coarse_sweep_reclaim_red_floor_lb12_rw1_close_above_white_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | stage1_coarse | 955.3318 | -1.0820 | 7.8762 | 66 |
| stage1_coarse_sweep_reclaim_red_floor_lb12_rw2_close_above_white_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | stage1_coarse | 949.6074 | -1.2235 | 9.1732 | 85 |
| stage1_coarse_sweep_reclaim_red_floor_lb12_rw3_close_above_white_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | stage1_coarse | 949.1337 | -1.2352 | 9.2185 | 87 |
| stage1_coarse_sweep_reclaim_white_floor_lb12_rw3_close_above_prev3bar_high_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | stage1_coarse | 906.4321 | -2.3117 | 10.1723 | 47 |
| stage1_coarse_sweep_reclaim_white_floor_lb36_rw3_close_above_white_es0.45_me2_addavg_minus_0.5ATR_equal_cd2_stopsweep_low-0.2ATR_tppartial_1.5R_runner_to_bearish_ob_hold48_gatenone | stage1_coarse | 893.8204 | -2.6370 | 11.1034 | 71 |

## Notes
- `SR-only` is the best fully optimized `band_bounce` strategy.
- `SR+proxy SMC` is the best fully optimized Stage 1 strategy from `sweep_reclaim` or `choch_ob_reclaim`.
- `SR+exact SMC` is the best Stage 2 gated strategy.
