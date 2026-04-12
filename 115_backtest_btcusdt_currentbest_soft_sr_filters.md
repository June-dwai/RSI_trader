# Study 115: Current Best + Soft SR Entry Filters

## Setup
- Baseline is the study-114 winner: `currentbest_114_smc5_both_2021plus`.
- Backtest period is `2021-01-02` to `2026-03-15` on the same 2021+ BTCUSDT cache.
- Unlike study 114, SR is now entry-only. It does not force flat or reverse while a trade is already open.
- SMC blocking can be `both`, `long_only`, or `short_only` to test whether the improvement mainly came from filtering longs or shorts.
- Ranking priority is `CAGR >= 90%` first, then higher Calmar, then higher CAGR, then lower MDD.

## Baselines
- Current-best baseline: `currentbest_114_smc5_both_2021plus` -> CAGR `95.0432%`, MDD `52.3536%`, Calmar `1.8154`
- Original 83 reference: `reference_original_83_2021plus` -> CAGR `102.9351%`, MDD `62.1257%`, Calmar `1.6569`

## Best Variant
- `smc5_longonly_2021plus` -> CAGR `109.5105%`, MDD `52.3206%`, Calmar `2.0931`, Final Equity `46701.2954`
- Delta vs current-best baseline: CAGR `14.4674pp`, MDD `-0.0330pp`, Calmar `0.2777`

## Ranking

| Variant | SR Entry Mode | SMC Mode | CAGR % | MDD % | Calmar | Delta Calmar | Trades | SR Blocks | SMC Blocks |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| smc5_longonly_2021plus | none | long_only | 109.5105 | 52.3206 | 2.0931 | 0.2777 | 123 | 0 | 3649 |
| smc5_longonly_long_above_redavg_2021plus | long_above_red_avg | long_only | 106.0033 | 53.2597 | 1.9903 | 0.1749 | 121 | 936 | 3156 |
| smc5_longonly_long_above_redfloor_2021plus | long_above_red_floor | long_only | 104.4006 | 53.2597 | 1.9602 | 0.1448 | 122 | 795 | 3228 |
| smc5_longonly_long_above_whiteavg_2021plus | long_above_white_avg | long_only | 99.6492 | 54.8221 | 1.8177 | 0.0023 | 124 | 838 | 3025 |
| currentbest_114_smc5_both_2021plus | none | both | 95.0432 | 52.3536 | 1.8154 | 0.0000 | 109 | 0 | 3911 |
| smc5_both_long_above_redavg_2021plus | long_above_red_avg | both | 91.7781 | 53.2597 | 1.7232 | -0.0922 | 107 | 936 | 3418 |
| smc5_both_long_above_redfloor_2021plus | long_above_red_floor | both | 90.2861 | 53.2597 | 1.6952 | -0.1202 | 108 | 795 | 3490 |
| reference_original_83_2021plus | none | none | 102.9351 | 62.1257 | 1.6569 | -0.1585 | 145 | 0 | 0 |
| smc5_both_long_above_whiteavg_2021plus | long_above_white_avg | both | 85.8628 | 54.8221 | 1.5662 | -0.2492 | 110 | 838 | 3287 |
| smc5_shortonly_2021plus | none | short_only | 88.9218 | 62.1257 | 1.4313 | -0.3841 | 131 | 0 | 263 |
| smc5_both_both_soft_2021plus | both_soft | both | 62.3850 | 59.6735 | 1.0454 | -0.7700 | 101 | 1083 | 3446 |

## Interpretation
- At least one softer SR entry permission improved on the current-best 114 winner.
- If a `long_only` SMC mode wins, then the main value of the 5-box filter was preventing bad longs rather than screening both sides symmetrically.
- If a soft SR entry filter wins, then the issue in study 114 was not the SR idea itself but the fact that SR was used too aggressively as a side-switch rule.

## Outputs
- Plot: `115_backtest_btcusdt_currentbest_soft_sr_filters.png`
- Metrics CSV: `115_backtest_btcusdt_currentbest_soft_sr_filters.csv`
- Curves CSV: `115_backtest_btcusdt_currentbest_soft_sr_filters_curves.csv`
- Report: `115_backtest_btcusdt_currentbest_soft_sr_filters.md`