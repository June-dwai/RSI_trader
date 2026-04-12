# Study 72: Slow 4H Alternative Archetypes

## Purpose
- This study tests slower, lower-turnover, 4h-bar alternative mindsets.
- Families: `regime hold`, `donchian breakout`, `EMA reclaim`, `RSI regime momentum`.
- Signals use only closed 4h bars and confirmed regime state.

## Ranking

| Variant | CAGR % | MDD % | Calmar | Final Equity | Trades | Longs | Shorts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| reference_case1 | 107.2913 | 61.0421 | 1.7577 | 20072.7821 | N/A | N/A | N/A |
| reference_case2 | 99.0018 | 74.0774 | 1.3365 | 16969.9239 | N/A | N/A | N/A |
| regime_hold_dual | 41.0484 | 33.9660 | 1.2085 | 4116.9905 | 138 | 69 | 69 |
| donchian_20_10_dual | 21.8926 | 30.6950 | 0.7132 | 2258.1674 | 155 | 77 | 78 |
| rsi_regime_dual | 13.0048 | 55.3125 | 0.2351 | 1653.7455 | 391 | 178 | 213 |
| ema_reclaim_dual | 3.1356 | 52.7109 | 0.0595 | 1135.4538 | 323 | 163 | 160 |

## Best New Archetype
- `regime_hold_dual`: CAGR `41.0484%`, MDD `33.9660%`, Calmar `1.2085`

## Interpretation
- If slower archetypes beat the fast 5m variants, then the alternate mindset is more plausible at swing horizon than intraday.
- If they still fail badly versus `reference_case1`, then the current edge is likely coming more from the existing research stack than from generic trend systems.

## Outputs
- Plot: `72_backtest_btcusdt_scale06_adx002_slow_archetypes_4h.png`
- Metrics CSV: `72_backtest_btcusdt_scale06_adx002_slow_archetypes_4h.csv`
- Curves CSV: `72_backtest_btcusdt_scale06_adx002_slow_archetypes_4h_curves.csv`
- Report: `72_backtest_btcusdt_scale06_adx002_slow_archetypes_4h.md`