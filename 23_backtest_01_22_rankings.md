# 23 Aggregated Ranking (01~22)

## Notes
- Total cases aggregated: `122`
- Source priority: `03~22` from CSV + `001/002` from MD.
- MDD column used per case is recorded in `23_backtest_01_22_rankings_all_cases.csv`.
- Rankings mix BTC/ETH and DCA/non-DCA experiments. Interpret cross-study comparisons carefully.

## Equity Ranking (Top 30)

| Rank | Study | Symbol | Source | Case | Final Equity | MDD % | Equity Rank | MDD Rank | Rank Sum | Combined Rank |
|---:|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.8` | 35,093,521 | 92.41 | 1 | 120 | 121 | 60 |
| 2 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.7` | 24,304,360 | 85.52 | 2 | 113 | 115 | 53 |
| 3 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.6` | 16,358,689 | 77.25 | 3 | 100 | 103 | 36 |
| 4 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.5` | 10,800,762 | 67.61 | 4 | 57 | 61 | 7 |
| 5 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.4` | 7,068,302 | 56.61 | 5 | 38 | 43 | 5 |
| 6 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.3` | 4,638,960 | 44.29 | 6 | 16 | 22 | 3 |
| 7 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.2` | 3,091,849 | 30.70 | 7 | 3 | 10 | 1 |
| 8 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.8` | 1,260,319 | 92.40 | 8 | 119 | 127 | 76 |
| 9 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.7` | 866,952 | 85.49 | 9 | 112 | 121 | 60 |
| 10 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.6` | 578,598 | 77.21 | 10 | 99 | 109 | 48 |
| 11 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.5` | 378,206 | 67.55 | 11 | 56 | 67 | 8 |
| 12 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.4` | 244,743 | 56.54 | 12 | 37 | 49 | 6 |
| 13 | 15 | BTCUSDT | `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.csv` | `scale_label=0.8 ; entry_scale=0.8` | 185,574 | 92.52 | 13 | 121 | 134 | 86 |
| 14 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.3` | 158,739 | 44.20 | 14 | 15 | 29 | 4 |
| 15 | 15 | BTCUSDT | `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.csv` | `scale_label=0.7 ; entry_scale=0.7` | 116,791 | 85.65 | 15 | 114 | 129 | 78 |
| 16 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=baseline_es0.8 ; entry_scale=0.8` | 107,145 | 92.63 | 16 | 122 | 138 | 92 |
| 17 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.2` | 104,594 | 30.60 | 17 | 2 | 19 | 2 |
| 18 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=baseline_es0.7 ; entry_scale=0.7` | 72,267 | 85.85 | 18 | 115 | 133 | 85 |
| 19 | 15 | BTCUSDT | `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.csv` | `scale_label=0.6 ; entry_scale=0.6` | 69,610 | 77.41 | 19 | 101 | 120 | 59 |
| 20 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=baseline_es0.6 ; entry_scale=0.6` | 46,144 | 77.68 | 20 | 102 | 122 | 62 |
| 21 | 08 | BTCUSDT | `08_backtest_btcusdt_hysteresis_sweep.csv` | `mode=hyst_0.50pct ; band_label=0.50%` | 39,368 | 67.81 | 21 | 58 | 79 | 11 |
| 22 | 14 | BTCUSDT | `14_backtest_btcusdt_best_hyst_fixed5x_sl_sweep.csv` | `sl_label=3.00%` | 39,368 | 67.81 | 21 | 58 | 79 | 11 |
| 23 | 15 | BTCUSDT | `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.csv` | `scale_label=0.5 ; entry_scale=0.5` | 39,368 | 67.81 | 21 | 58 | 79 | 11 |
| 24 | 09 | BTCUSDT | `09_backtest_btcusdt_triple_compare.csv` | `strategy=08_best_hysteresis_fixed5x` | 39,368 | 67.81 | 21 | 61 | 82 | 15 |
| 25 | 08 | BTCUSDT | `08_backtest_btcusdt_hysteresis_sweep.csv` | `mode=hyst_0.30pct ; band_label=0.30%` | 35,583 | 70.23 | 25 | 77 | 102 | 35 |
| 26 | 17 | BTCUSDT | `17_backtest_btcusdt_hysteresis_sweep_nolookahead_raw.csv` | `mode=hyst_0.50pct ; band_label=0.50%` | 27,950 | 68.14 | 26 | 63 | 89 | 21 |
| 27 | 18 | BTCUSDT | `18_backtest_btcusdt_hys05_longsl_compare.csv` | `mode=case_17_baseline ; long_sl_enabled=on` | 27,950 | 68.14 | 26 | 63 | 89 | 21 |
| 28 | 20 | BTCUSDT | `20_backtest_btcusdt_hys05_diagnostics_metrics.csv` | `row_1` | 27,950 | 68.14 | 26 | 63 | 89 | 21 |
| 29 | 21 | BTCUSDT | `21_backtest_btcusdt_dd_scale_compare.csv` | `mode=baseline_hys05` | 27,950 | 68.14 | 26 | 63 | 89 | 21 |
| 30 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=baseline_es0.5 ; entry_scale=0.5` | 27,950 | 68.14 | 26 | 63 | 89 | 21 |

## MDD Ranking (Top 30, lower is better)

| Rank | Study | Symbol | Source | Case | Final Equity | MDD % | Equity Rank | MDD Rank | Rank Sum | Combined Rank |
|---:|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 03 | BTCUSDT | `03_backtest_btcusdt_scale_metrics.csv` | `entry_scale=0.2` | 3,765 | 29.72 | 99 | 1 | 100 | 33 |
| 2 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.2` | 104,594 | 30.60 | 17 | 2 | 19 | 2 |
| 3 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.2` | 3,091,849 | 30.70 | 7 | 3 | 10 | 1 |
| 4 | 15 | BTCUSDT | `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.csv` | `scale_label=0.2 ; entry_scale=0.2` | 5,190 | 30.98 | 81 | 4 | 85 | 19 |
| 5 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.30_tp0.80_sl8.00` | 3,521 | 37.91 | 100 | 5 | 105 | 37 |
| 6 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.30_tp0.60_sl4.00` | 3,424 | 39.23 | 101 | 6 | 107 | 40 |
| 7 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.30_tp0.80_sl4.00` | 5,907 | 39.43 | 76 | 7 | 83 | 17 |
| 8 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.30_tp0.80_sl5.00` | 2,296 | 40.50 | 114 | 8 | 122 | 62 |
| 9 | 01 | BTCUSDT | `001_backtest_btcusdt.md` | `single_run` | 6,042 | 40.71 | 75 | 9 | 84 | 18 |
| 10 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.30_tp0.80_sl6.00` | 3,006 | 41.59 | 106 | 10 | 116 | 55 |
| 11 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.30_tp0.60_sl5.00` | 2,173 | 41.93 | 115 | 11 | 126 | 75 |
| 12 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=dd_scaled_es0.4 ; entry_scale=0.4` | 12,245 | 42.57 | 63 | 12 | 75 | 9 |
| 13 | 03 | BTCUSDT | `03_backtest_btcusdt_scale_metrics.csv` | `entry_scale=0.3` | 6,505 | 42.58 | 74 | 13 | 87 | 20 |
| 14 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.30_tp0.60_sl6.00` | 3,056 | 43.68 | 105 | 14 | 119 | 57 |
| 15 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.3` | 158,739 | 44.20 | 14 | 15 | 29 | 4 |
| 16 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.3` | 4,638,960 | 44.29 | 6 | 16 | 22 | 3 |
| 17 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.30_tp0.60_sl8.00` | 2,511 | 44.30 | 112 | 17 | 129 | 78 |
| 18 | 15 | BTCUSDT | `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.csv` | `scale_label=0.3 ; entry_scale=0.3` | 10,767 | 44.58 | 64 | 18 | 82 | 15 |
| 19 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=baseline_es0.3 ; entry_scale=0.3` | 8,765 | 44.91 | 70 | 19 | 89 | 21 |
| 20 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=dd_scaled_es0.3 ; entry_scale=0.3` | 8,765 | 44.91 | 70 | 19 | 89 | 21 |
| 21 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.40_tp0.80_sl8.00` | 4,853 | 50.54 | 85 | 21 | 106 | 39 |
| 22 | 11 | ETHUSDT | `11_backtest_ethusdt_hyst_tpsl_sweep.csv` | `h0.00_tp1.60_sl2.00` | 4,840 | 50.74 | 86 | 22 | 108 | 46 |
| 23 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.40_tp0.60_sl4.00` | 4,877 | 51.06 | 84 | 23 | 107 | 40 |
| 24 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=dd_scaled_es0.5 ; entry_scale=0.5` | 17,790 | 51.49 | 53 | 24 | 77 | 10 |
| 25 | 11 | ETHUSDT | `11_backtest_ethusdt_hyst_tpsl_sweep.csv` | `h0.00_tp0.80_sl4.00` | 9,786 | 51.73 | 67 | 25 | 92 | 29 |
| 26 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.40_tp0.80_sl4.00` | 9,786 | 51.73 | 67 | 25 | 92 | 29 |
| 27 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.40_tp0.80_sl5.00` | 2,819 | 52.27 | 108 | 27 | 135 | 89 |
| 28 | 11 | ETHUSDT | `11_backtest_ethusdt_hyst_tpsl_sweep.csv` | `h0.00_tp0.80_sl2.00` | 4,950 | 52.95 | 83 | 28 | 111 | 50 |
| 29 | 11 | ETHUSDT | `11_backtest_ethusdt_hyst_tpsl_sweep.csv` | `h2.00_tp0.80_sl4.00` | 2,606 | 53.76 | 111 | 29 | 140 | 93 |
| 30 | 11 | ETHUSDT | `11_backtest_ethusdt_hyst_tpsl_sweep.csv` | `h0.00_tp1.60_sl4.00` | 4,384 | 53.80 | 89 | 30 | 119 | 57 |

## Combined Ranking (Top 30 by Equity Rank + MDD Rank)

| Rank | Study | Symbol | Source | Case | Final Equity | MDD % | Equity Rank | MDD Rank | Rank Sum | Combined Rank |
|---:|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.2` | 3,091,849 | 30.70 | 7 | 3 | 10 | 1 |
| 2 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.2` | 104,594 | 30.60 | 17 | 2 | 19 | 2 |
| 3 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.3` | 4,638,960 | 44.29 | 6 | 16 | 22 | 3 |
| 4 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.3` | 158,739 | 44.20 | 14 | 15 | 29 | 4 |
| 5 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.4` | 7,068,302 | 56.61 | 5 | 38 | 43 | 5 |
| 6 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.4` | 244,743 | 56.54 | 12 | 37 | 49 | 6 |
| 7 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_daily_dca.csv` | `entry_scale=0.5` | 10,800,762 | 67.61 | 4 | 57 | 61 | 7 |
| 8 | 16 | BTCUSDT | `16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv` | `entry_scale=0.5` | 378,206 | 67.55 | 11 | 56 | 67 | 8 |
| 9 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=dd_scaled_es0.4 ; entry_scale=0.4` | 12,245 | 42.57 | 63 | 12 | 75 | 9 |
| 10 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=dd_scaled_es0.5 ; entry_scale=0.5` | 17,790 | 51.49 | 53 | 24 | 77 | 10 |
| 11 | 08 | BTCUSDT | `08_backtest_btcusdt_hysteresis_sweep.csv` | `mode=hyst_0.50pct ; band_label=0.50%` | 39,368 | 67.81 | 21 | 58 | 79 | 11 |
| 12 | 14 | BTCUSDT | `14_backtest_btcusdt_best_hyst_fixed5x_sl_sweep.csv` | `sl_label=3.00%` | 39,368 | 67.81 | 21 | 58 | 79 | 11 |
| 13 | 15 | BTCUSDT | `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.csv` | `scale_label=0.5 ; entry_scale=0.5` | 39,368 | 67.81 | 21 | 58 | 79 | 11 |
| 14 | 15 | BTCUSDT | `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.csv` | `scale_label=0.4 ; entry_scale=0.4` | 21,138 | 56.86 | 40 | 40 | 80 | 14 |
| 15 | 09 | BTCUSDT | `09_backtest_btcusdt_triple_compare.csv` | `strategy=08_best_hysteresis_fixed5x` | 39,368 | 67.81 | 21 | 61 | 82 | 15 |
| 16 | 15 | BTCUSDT | `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.csv` | `scale_label=0.3 ; entry_scale=0.3` | 10,767 | 44.58 | 64 | 18 | 82 | 15 |
| 17 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.30_tp0.80_sl4.00` | 5,907 | 39.43 | 76 | 7 | 83 | 17 |
| 18 | 01 | BTCUSDT | `001_backtest_btcusdt.md` | `single_run` | 6,042 | 40.71 | 75 | 9 | 84 | 18 |
| 19 | 15 | BTCUSDT | `15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.csv` | `scale_label=0.2 ; entry_scale=0.2` | 5,190 | 30.98 | 81 | 4 | 85 | 19 |
| 20 | 03 | BTCUSDT | `03_backtest_btcusdt_scale_metrics.csv` | `entry_scale=0.3` | 6,505 | 42.58 | 74 | 13 | 87 | 20 |
| 21 | 17 | BTCUSDT | `17_backtest_btcusdt_hysteresis_sweep_nolookahead_raw.csv` | `mode=hyst_0.50pct ; band_label=0.50%` | 27,950 | 68.14 | 26 | 63 | 89 | 21 |
| 22 | 18 | BTCUSDT | `18_backtest_btcusdt_hys05_longsl_compare.csv` | `mode=case_17_baseline ; long_sl_enabled=on` | 27,950 | 68.14 | 26 | 63 | 89 | 21 |
| 23 | 20 | BTCUSDT | `20_backtest_btcusdt_hys05_diagnostics_metrics.csv` | `row_1` | 27,950 | 68.14 | 26 | 63 | 89 | 21 |
| 24 | 21 | BTCUSDT | `21_backtest_btcusdt_dd_scale_compare.csv` | `mode=baseline_hys05` | 27,950 | 68.14 | 26 | 63 | 89 | 21 |
| 25 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=baseline_es0.5 ; entry_scale=0.5` | 27,950 | 68.14 | 26 | 63 | 89 | 21 |
| 26 | 21 | BTCUSDT | `21_backtest_btcusdt_dd_scale_compare.csv` | `mode=dd_scaled_hys05` | 19,795 | 57.46 | 47 | 42 | 89 | 21 |
| 27 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=baseline_es0.3 ; entry_scale=0.3` | 8,765 | 44.91 | 70 | 19 | 89 | 21 |
| 28 | 22 | BTCUSDT | `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv` | `mode=dd_scaled_es0.3 ; entry_scale=0.3` | 8,765 | 44.91 | 70 | 19 | 89 | 21 |
| 29 | 11 | ETHUSDT | `11_backtest_ethusdt_hyst_tpsl_sweep.csv` | `h0.00_tp0.80_sl4.00` | 9,786 | 51.73 | 67 | 25 | 92 | 29 |
| 30 | 12 | ETHUSDT | `12_backtest_ethusdt_scale_tpsl_sweep.csv` | `s0.40_tp0.80_sl4.00` | 9,786 | 51.73 | 67 | 25 | 92 | 29 |

## Output Files
- all cases: `23_backtest_01_22_rankings_all_cases.csv`
- equity sorted: `23_backtest_01_22_rankings_by_equity.csv`
- mdd sorted: `23_backtest_01_22_rankings_by_mdd.csv`
- combined sorted: `23_backtest_01_22_rankings_by_combined.csv`