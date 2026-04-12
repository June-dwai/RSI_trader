# Study 83: SMC Sweep Filter on Regime-Hold

## Scope
- Reuse only the least-bad SMC ingredient from study 82: liquidity sweep.
- Base engine is the study-80 winner concept: regime-hold with short-only TP-lock at `15%`.
- Change only the entry timing: selected variants wait for a 15m sweep-reclaim event against 1h liquidity before entering in the 4h confirmed trend direction.
- This tests SMC as a filter rather than a standalone trading system.

## Variants
- `base15m_*`: same regime-hold/short-TP concept on the 15m execution engine, no sweep gate.
- `long_gate*`: only longs require a recent downside sweep-reclaim.
- `short_gate*`: only shorts require a recent upside sweep-reject.
- `both_gate*`: both sides require the filter.

## Ranking

| Variant | CAGR % | MDD % | Calmar | Final Equity | Trades | Gated Entries | Long Sweeps | Short Sweeps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| short_gate24h_shorttp15_2x | 85.5152 | 48.4494 | 1.7650 | 13399.2438 | 131 | 51 | 636 | 630 |
| base15m_shorttp15_1.5x | 67.2495 | 41.6855 | 1.6133 | 8670.3685 | 155 | 0 | 0 | 0 |
| base15m_shorttp15_2x | 76.3005 | 51.5201 | 1.4810 | 10818.3586 | 155 | 0 | 0 | 0 |
| long_gate8h_shorttp15_1.5x | 61.3691 | 42.1458 | 1.4561 | 7460.3334 | 127 | 52 | 1403 | 1414 |
| reference_shorttp15_2x | 67.5300 | 50.8583 | 1.3278 | 8730.8307 | N/A | N/A | N/A | N/A |
| reference_shorttp15_15x | 54.2930 | 41.7230 | 1.3013 | 6179.3410 | N/A | N/A | N/A | N/A |
| long_gate24h_shorttp15_1.5x | 48.4367 | 41.2744 | 1.1735 | 5252.9265 | 116 | 41 | 636 | 630 |
| both_gate24h_shorttp15_2x | 59.4867 | 51.8989 | 1.1462 | 7101.6187 | 92 | 92 | 636 | 630 |
| long_gate24h_shorttp15_2x | 51.5649 | 47.4079 | 1.0877 | 5733.7458 | 116 | 41 | 636 | 630 |
| short_gate8h_shorttp15_1.5x | 51.0370 | 49.6116 | 1.0287 | 5650.3324 | 144 | 64 | 1403 | 1414 |
| short_gate24h_shorttp15_1.5x | 49.2474 | 51.3133 | 0.9597 | 5374.4610 | 132 | 52 | 636 | 630 |
| both_gate24h_shorttp15_1.5x | 32.4596 | 61.7745 | 0.5255 | 3256.1072 | 93 | 93 | 636 | 630 |

## Best Live Variant
- `short_gate24h_shorttp15_2x`: CAGR `85.5152%`, MDD `48.4494%`, Calmar `1.7650`

## Interpretation
- If a gated variant beats its `base15m` sibling, then liquidity sweep works better as entry timing than as a full standalone strategy.
- If only long-gated variants work, then the noisy side was long chasing, not short chasing.
- If only short-gated variants work, then late short entries after downside extension were the real problem.
- If all gated variants underperform, then the sweep filter is overconstraining the regime-hold engine.

## Outputs
- Plot: `83_backtest_btcusdt_scale06_adx002_smc_sweep_filter_regime_hold.png`
- Metrics CSV: `83_backtest_btcusdt_scale06_adx002_smc_sweep_filter_regime_hold.csv`
- Curves CSV: `83_backtest_btcusdt_scale06_adx002_smc_sweep_filter_regime_hold_curves.csv`
- Report: `83_backtest_btcusdt_scale06_adx002_smc_sweep_filter_regime_hold.md`