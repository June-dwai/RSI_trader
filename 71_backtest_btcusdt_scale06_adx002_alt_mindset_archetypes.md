# Study 71: Alternative Strategy Mindsets

## Purpose
- This study intentionally avoids the `inventory averaging + hedge management` mindset.
- Tested families are: `turtle trend-follow`, `bull breakout`, `pullback then reclaim`, `compression breakout`, and `hard-stop mean reversion`.
- All entries use only closed-bar information; breakout levels are shifted by one bar, and 4h regime uses confirmed hysteresis state.

## Ranking

| Variant | CAGR % | MDD % | Calmar | Final Equity | Trades | Longs | Shorts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| reference_case1 | 107.2913 | 61.0421 | 1.7577 | 20072.7821 | N/A | N/A | N/A |
| reference_case2 | 99.0018 | 74.0774 | 1.3365 | 16969.9239 | N/A | N/A | N/A |
| compression_breakout_dual | 15.8960 | 23.5408 | 0.6753 | 1834.9175 | 450 | 267 | 183 |
| breakout_long_96 | 12.1170 | 28.5958 | 0.4237 | 1600.9554 | 451 | 451 | 0 |
| pullback_reclaim_dual | -9.8457 | 58.4837 | -0.1683 | 652.8096 | 1791 | 812 | 979 |
| turtle_dual_144_48 | -22.1459 | 71.8860 | -0.3081 | 356.9982 | 1316 | 669 | 647 |
| hard_stop_meanrev_dual | -29.7869 | 78.1827 | -0.3810 | 233.3839 | 1614 | 861 | 753 |

## Best New Archetype
- `compression_breakout_dual`: CAGR `15.8960%`, MDD `23.5408%`, Calmar `0.6753`

## Interpretation
- If a live archetype beats `reference_case2`, it is a plausible replacement candidate for the current second sleeve.
- If a live archetype approaches `reference_case1` with much lower MDD, it is a candidate for a fundamentally different primary engine.
- This study is about identifying promising mindsets first, not yet about perfect parameter tuning.

## Outputs
- Plot: `71_backtest_btcusdt_scale06_adx002_alt_mindset_archetypes.png`
- Metrics CSV: `71_backtest_btcusdt_scale06_adx002_alt_mindset_archetypes.csv`
- Curves CSV: `71_backtest_btcusdt_scale06_adx002_alt_mindset_archetypes_curves.csv`
- Report: `71_backtest_btcusdt_scale06_adx002_alt_mindset_archetypes.md`