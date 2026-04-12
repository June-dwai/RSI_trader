# Study 80: Short-Only Take-Profit Lock Tuning

## Model
- Reuses the study-78 short-only TP-lock logic.
- After a profitable short reaches the threshold on the current 4h close, the short is closed and re-entry on the short side stays locked until a confirmed bullish flip occurs.
- Long trades are untouched.

## Ranking

| Variant | Lev | TP % | CAGR % | MDD % | Calmar | Final Equity | TP Exits | Locked Bars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| short_tp15_lock_2x | 2.0 | 15 | 67.5300 | 50.8583 | 1.3278 | 8730.8307 | 19 | 2419 |
| short_tp15_lock_1.5x | 1.5 | 15 | 54.2930 | 41.7230 | 1.3013 | 6179.3410 | 14 | 2019 |
| short_tp20_lock_2x | 2.0 | 20 | 64.4184 | 52.5842 | 1.2251 | 8069.8245 | 14 | 2019 |
| short_tp10_lock_2x | 2.0 | 10 | 60.7376 | 50.8583 | 1.1943 | 7337.8865 | 24 | 2877 |
| short_tp10_lock_1.5x | 1.5 | 10 | 45.3744 | 41.0263 | 1.1060 | 4812.2973 | 19 | 2481 |
| short_tp20_lock_1.5x | 1.5 | 20 | 46.5933 | 47.2225 | 0.9867 | 4984.0323 | 10 | 1600 |
| short_tp30_lock_1.5x | 1.5 | 30 | 45.3253 | 47.7837 | 0.9486 | 4805.4864 | 6 | 1110 |
| short_tp25_lock_1.5x | 1.5 | 25 | 44.9199 | 51.5140 | 0.8720 | 4749.4383 | 8 | 1474 |
| short_tp25_lock_2x | 2.0 | 25 | 50.8729 | 58.3747 | 0.8715 | 5624.2064 | 10 | 1605 |
| short_tp40_lock_2x | 2.0 | 40 | 50.9918 | 59.1584 | 0.8620 | 5642.8490 | 6 | 1110 |
| short_tp40_lock_1.5x | 1.5 | 40 | 39.9793 | 47.2546 | 0.8460 | 4105.6480 | 3 | 637 |
| short_tp30_lock_2x | 2.0 | 30 | 46.4112 | 63.3725 | 0.7324 | 4958.0854 | 8 | 1489 |
| base_1.5x | 1.5 | N/A | 35.9322 | 49.8715 | 0.7205 | 3629.7345 | 0 | 0 |
| base_2x | 2.0 | N/A | 38.4140 | 59.8575 | 0.6418 | 3916.2700 | 0 | 0 |

## Best Variant
- `short_tp15_lock_2x`: CAGR `67.5300%`, MDD `50.8583%`, Calmar `1.3278`

## Delta vs Same-Leverage Baseline
- `short_tp15_lock_2x` vs `base_2x`: CAGR `29.1159pp`, MDD `-8.9992pp`, Calmar `0.6860`, TP exits `19`
- `short_tp15_lock_1.5x` vs `base_1.5x`: CAGR `18.3608pp`, MDD `-8.1485pp`, Calmar `0.5808`, TP exits `14`
- `short_tp20_lock_2x` vs `base_2x`: CAGR `26.0044pp`, MDD `-7.2733pp`, Calmar `0.5833`, TP exits `14`
- `short_tp10_lock_2x` vs `base_2x`: CAGR `22.3236pp`, MDD `-8.9992pp`, Calmar `0.5525`, TP exits `24`
- `short_tp10_lock_1.5x` vs `base_1.5x`: CAGR `9.4422pp`, MDD `-8.8452pp`, Calmar `0.3855`, TP exits `19`
- `short_tp20_lock_1.5x` vs `base_1.5x`: CAGR `10.6611pp`, MDD `-2.6490pp`, Calmar `0.2662`, TP exits `10`
- `short_tp30_lock_1.5x` vs `base_1.5x`: CAGR `9.3931pp`, MDD `-2.0878pp`, Calmar `0.2281`, TP exits `6`
- `short_tp25_lock_1.5x` vs `base_1.5x`: CAGR `8.9877pp`, MDD `1.6425pp`, Calmar `0.1515`, TP exits `8`
- `short_tp25_lock_2x` vs `base_2x`: CAGR `12.4589pp`, MDD `-1.4828pp`, Calmar `0.2297`, TP exits `10`
- `short_tp40_lock_2x` vs `base_2x`: CAGR `12.5778pp`, MDD `-0.6992pp`, Calmar `0.2202`, TP exits `6`
- `short_tp40_lock_1.5x` vs `base_1.5x`: CAGR `4.0471pp`, MDD `-2.6169pp`, Calmar `0.1255`, TP exits `3`
- `short_tp30_lock_2x` vs `base_2x`: CAGR `7.9972pp`, MDD `3.5150pp`, Calmar `0.0906`, TP exits `8`

## Interpretation
- If lower short TP thresholds dominate, short squeezes are a major source of giveback and shorts should be monetized earlier.
- If higher thresholds dominate, shorts still need room to run and only the biggest winners should be clipped.

## Outputs
- Plot: `80_backtest_btcusdt_scale06_adx002_regime_hold_short_tp_tune.png`
- Metrics CSV: `80_backtest_btcusdt_scale06_adx002_regime_hold_short_tp_tune.csv`
- Curves CSV: `80_backtest_btcusdt_scale06_adx002_regime_hold_short_tp_tune_curves.csv`
- Report: `80_backtest_btcusdt_scale06_adx002_regime_hold_short_tp_tune.md`