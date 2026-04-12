# Study 113: SR/SMC Main, RSI Confirmation

## Setup
- Base market prep reuses study 111: 5m execution from BTCUSDT 1m data with the same SR and LuxAlgo-style exact/internal structure features.
- This study flips the priority: SR + SMC define the trigger, RSI only confirms that the pullback is washed out and starting to recover.
- Signal families are `sweep_choch_ob`, `ob_revisit_bull`, and `band_reclaim_break`.
- Coarse pass sweeps structural seeds; full-stack pass only tunes position sizing, adds, stop mode, TP mode, and max hold.

## Winner
- Winner: `stage113_fullstack_ob_revisit_bull_white_floor_lb6_rw1_r8_os30_rec40_es0.60_me3_addavg_minus_0.5ATR_equal_cd0_stopsweep_low-0.2ATR_tp3R_fixed_hold72_gatenone` -> equity `1071.9743`, CAGR `1.6684%`, MDD `2.6737%`, Calmar `0.6240`, trades `8`
- Structural trigger: `ob_revisit_bull` on `white_floor`, sweep window `6`, struct window `1`, RSI confirm `r8_os30_rec40`
- vs `110 gap_12`: equity uplift `-55.9328`
- vs `111 proxy winner`: equity uplift `-23.1838`

## Benchmarks
| Variant | Stage | Final Equity | CAGR % | MDD % | Calmar | Trades |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| buy_hold | benchmark | 1548.4270 | 10.9704 | 67.8001 | 0.1618 | 1 |
| gap_12 | benchmark | 1127.9070 | 2.9069 | 35.1812 | 0.0826 | 313 |
| stage1_fullstack_choch_ob_reclaim_white_floor_lb12_rw2_close_above_white_es0.60_me3_addavg_minus_0.5ATR_equal_cd4_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gatenone | stage1_fullstack | 1095.1581 | 2.1877 | 2.2609 | 0.9676 | 6 |
| stage113_fullstack_ob_revisit_bull_white_floor_lb6_rw1_r8_os30_rec40_es0.60_me3_addavg_minus_0.5ATR_equal_cd0_stopsweep_low-0.2ATR_tp3R_fixed_hold72_gatenone | stage113_fullstack | 1071.9743 | 1.6684 | 2.6737 | 0.6240 | 8 |

## Stage 113 Full-Stack Top 10
| Variant | Entry Family | Final Equity | CAGR % | MDD % | Calmar | Trades |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| stage113_fullstack_ob_revisit_bull_white_floor_lb6_rw1_r8_os30_rec40_es0.60_me3_addavg_minus_0.5ATR_equal_cd0_stopsweep_low-0.2ATR_tp3R_fixed_hold72_gatenone | ob_revisit_bull | 1071.9743 | 1.6684 | 2.6737 | 0.6240 | 8 |
| stage113_fullstack_ob_revisit_bull_white_floor_lb6_rw2_r8_os30_rec40_es0.60_me3_addavg_minus_0.5ATR_equal_cd0_stopsweep_low-0.2ATR_tp3R_fixed_hold72_gatenone | ob_revisit_bull | 1071.9743 | 1.6684 | 2.6737 | 0.6240 | 8 |
| stage113_fullstack_ob_revisit_bull_white_floor_lb6_rw3_r8_os30_rec40_es0.60_me3_addavg_minus_0.5ATR_equal_cd0_stopsweep_low-0.2ATR_tp3R_fixed_hold72_gatenone | ob_revisit_bull | 1071.9743 | 1.6684 | 2.6737 | 0.6240 | 8 |
| stage113_fullstack_ob_revisit_bull_red_floor_lb6_rw1_r8_os30_rec40_es0.60_me3_addavg_minus_0.5ATR_equal_cd0_stopsweep_low-0.2ATR_tp3R_fixed_hold72_gatenone | ob_revisit_bull | 1071.9743 | 1.6684 | 2.6737 | 0.6240 | 8 |
| stage113_fullstack_ob_revisit_bull_red_floor_lb6_rw2_r8_os30_rec40_es0.60_me3_addavg_minus_0.5ATR_equal_cd0_stopsweep_low-0.2ATR_tp3R_fixed_hold72_gatenone | ob_revisit_bull | 1071.9743 | 1.6684 | 2.6737 | 0.6240 | 8 |
| stage113_fullstack_ob_revisit_bull_red_floor_lb6_rw3_r8_os30_rec40_es0.60_me3_addavg_minus_0.5ATR_equal_cd0_stopsweep_low-0.2ATR_tp3R_fixed_hold72_gatenone | ob_revisit_bull | 1071.9743 | 1.6684 | 2.6737 | 0.6240 | 8 |
| stage113_fullstack_ob_revisit_bull_overlap_lb6_rw1_r8_os30_rec40_es0.60_me3_addavg_minus_0.5ATR_equal_cd0_stopsweep_low-0.2ATR_tp3R_fixed_hold72_gatenone | ob_revisit_bull | 1071.9743 | 1.6684 | 2.6737 | 0.6240 | 8 |
| stage113_fullstack_ob_revisit_bull_overlap_lb6_rw2_r8_os30_rec40_es0.60_me3_addavg_minus_0.5ATR_equal_cd0_stopsweep_low-0.2ATR_tp3R_fixed_hold72_gatenone | ob_revisit_bull | 1071.9743 | 1.6684 | 2.6737 | 0.6240 | 8 |
| stage113_fullstack_ob_revisit_bull_overlap_lb6_rw3_r8_os30_rec40_es0.60_me3_addavg_minus_0.5ATR_equal_cd0_stopsweep_low-0.2ATR_tp3R_fixed_hold72_gatenone | ob_revisit_bull | 1071.9743 | 1.6684 | 2.6737 | 0.6240 | 8 |
| stage113_fullstack_ob_revisit_bull_white_floor_lb6_rw1_r6_os25_rec35_es0.60_me3_addretest_red_floor_equal_cd0_stopsweep_low-0.2ATR_tp2R_fixed_hold72_gatenone | ob_revisit_bull | 1053.3020 | 1.2440 | 2.5777 | 0.4826 | 7 |

## Stage 113 Coarse Top 10
| Variant | Entry Family | Final Equity | CAGR % | MDD % | Trades |
| --- | --- | ---: | ---: | ---: | ---: |
| stage113_coarse_ob_revisit_bull_white_floor_lb6_rw1_r8_os30_rec40_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | ob_revisit_bull | 1021.5916 | 0.5099 | 1.1853 | 8 |
| stage113_coarse_ob_revisit_bull_white_floor_lb6_rw2_r8_os30_rec40_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | ob_revisit_bull | 1021.5916 | 0.5099 | 1.1853 | 8 |
| stage113_coarse_ob_revisit_bull_white_floor_lb6_rw3_r8_os30_rec40_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | ob_revisit_bull | 1021.5916 | 0.5099 | 1.1853 | 8 |
| stage113_coarse_ob_revisit_bull_red_floor_lb6_rw1_r8_os30_rec40_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | ob_revisit_bull | 1021.5916 | 0.5099 | 1.1853 | 8 |
| stage113_coarse_ob_revisit_bull_red_floor_lb6_rw2_r8_os30_rec40_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | ob_revisit_bull | 1021.5916 | 0.5099 | 1.1853 | 8 |
| stage113_coarse_ob_revisit_bull_red_floor_lb6_rw3_r8_os30_rec40_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | ob_revisit_bull | 1021.5916 | 0.5099 | 1.1853 | 8 |
| stage113_coarse_ob_revisit_bull_overlap_lb6_rw1_r8_os30_rec40_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | ob_revisit_bull | 1021.5916 | 0.5099 | 1.1853 | 8 |
| stage113_coarse_ob_revisit_bull_overlap_lb6_rw2_r8_os30_rec40_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | ob_revisit_bull | 1021.5916 | 0.5099 | 1.1853 | 8 |
| stage113_coarse_ob_revisit_bull_overlap_lb6_rw3_r8_os30_rec40_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | ob_revisit_bull | 1021.5916 | 0.5099 | 1.1853 | 8 |
| stage113_coarse_ob_revisit_bull_white_floor_lb6_rw1_r6_os25_rec35_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | ob_revisit_bull | 1017.4792 | 0.4134 | 1.4770 | 7 |

## Sanity Leaderboard
| Variant | Stage | Final Equity | CAGR % | MDD % | Trades |
| --- | --- | ---: | ---: | ---: | ---: |
| stage113_coarse_ob_revisit_bull_white_floor_lb12_rw1_r6_os25_rec35_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | stage113_coarse | 990.7566 | -0.2208 | 4.6780 | 30 |
| stage113_coarse_ob_revisit_bull_white_floor_lb12_rw1_r6_os25_upturn_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | stage113_coarse | 990.7566 | -0.2208 | 4.6780 | 30 |
| stage113_coarse_ob_revisit_bull_white_floor_lb12_rw2_r6_os25_rec35_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | stage113_coarse | 990.7566 | -0.2208 | 4.6780 | 30 |
| stage113_coarse_ob_revisit_bull_white_floor_lb12_rw2_r6_os25_upturn_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | stage113_coarse | 990.7566 | -0.2208 | 4.6780 | 30 |
| stage113_coarse_ob_revisit_bull_white_floor_lb12_rw3_r6_os25_rec35_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | stage113_coarse | 990.7566 | -0.2208 | 4.6780 | 30 |
| stage113_coarse_ob_revisit_bull_white_floor_lb12_rw3_r6_os25_upturn_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | stage113_coarse | 990.7566 | -0.2208 | 4.6780 | 30 |
| stage113_coarse_ob_revisit_bull_overlap_lb12_rw1_r6_os20_rec30_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | stage113_coarse | 982.5188 | -0.4190 | 3.8688 | 23 |
| stage113_coarse_ob_revisit_bull_overlap_lb12_rw2_r6_os20_rec30_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | stage113_coarse | 982.5188 | -0.4190 | 3.8688 | 23 |
| stage113_coarse_ob_revisit_bull_overlap_lb12_rw3_r6_os20_rec30_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | stage113_coarse | 982.5188 | -0.4190 | 3.8688 | 23 |
| stage113_coarse_ob_revisit_bull_white_floor_lb12_rw1_r8_os30_rec40_es0.60_me2_addob_revisit_taper_cd2_stopob_low-0.1ATR_tppartial_1.5R_runner_to_bearish_ob_hold72_gatenone | stage113_coarse | 978.2381 | -0.5224 | 4.6318 | 35 |

## Notes
- RSI is never used as the standalone trigger here; every entry starts from SR touch + SMC structure alignment.
- If this still loses to `gap_12` or `111 proxy`, the next step is likely to improve the exit logic rather than add more RSI conditions.
