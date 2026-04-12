# Study 73: Regime-Hold Tuning

## Purpose
- Tune the `regime_hold_dual` idea from study 72 instead of abandoning it after the first pass.
- Tested levers: stop width, neutral EMA band, and `dual` versus `long-flat` regime handling.
- Band variants delay entry by one 4h bar after signal formation to avoid same-bar lookahead.

## Ranking

| Variant | CAGR % | MDD % | Calmar | Final Equity | Trades | Longs | Shorts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| reference_case1 | 107.2913 | 61.0421 | 1.7577 | 20072.7821 | N/A | N/A | N/A |
| reference_case2 | 99.0018 | 74.0774 | 1.3365 | 16969.9239 | N/A | N/A | N/A |
| dual_stop6 | 41.1892 | 34.0157 | 1.2109 | 4133.9256 | 135 | 68 | 67 |
| dual_stop5 | 41.0484 | 33.9660 | 1.2085 | 4116.9905 | 138 | 69 | 69 |
| dual_stop4 | 41.0214 | 33.9660 | 1.2077 | 4113.7514 | 139 | 70 | 69 |
| dual_band1_stop5 | 34.9286 | 37.7909 | 0.9243 | 3430.1871 | 260 | 121 | 139 |
| longflat_stop5 | 30.4151 | 33.7569 | 0.9010 | 2982.0833 | 69 | 69 | 0 |
| longflat_band1_stop5 | 27.5699 | 37.7334 | 0.7306 | 2723.3582 | 121 | 121 | 0 |
| longflat_band2_stop5 | 20.0274 | 35.8640 | 0.5584 | 2119.3470 | 147 | 147 | 0 |
| dual_band2_stop5 | 4.1258 | 52.9057 | 0.0780 | 1180.9866 | 329 | 147 | 182 |

## Best Tuned Variant
- `dual_stop6`: CAGR `41.1892%`, MDD `34.0157%`, Calmar `1.2109`

## Interpretation
- If the best tuned variant still cannot clear the original references, this logic is more plausible as a low-risk third sleeve than as a primary engine.
- If `long-flat` beats `dual`, then bearish short exposure is not carrying its weight inside this slow regime framework.
- If the EMA band helps, then avoiding ambiguous regime transitions is the main missing ingredient.

## Outputs
- Plot: `73_backtest_btcusdt_scale06_adx002_regime_hold_tune.png`
- Metrics CSV: `73_backtest_btcusdt_scale06_adx002_regime_hold_tune.csv`
- Curves CSV: `73_backtest_btcusdt_scale06_adx002_regime_hold_tune_curves.csv`
- Report: `73_backtest_btcusdt_scale06_adx002_regime_hold_tune.md`