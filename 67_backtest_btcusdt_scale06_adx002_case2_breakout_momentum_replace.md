# Study 67: Replace Case2 With Regime-Aware Breakout Momentum

## Setup
- Fixed case1 variant: `shallow6_else2bull` from study 62
- New case2 family: no-lookahead 1m breakout momentum gated by confirmed 4h hysteresis trend
- Entry uses prior rolling breakout levels only (`shift(1)`), so no future bars are referenced
- Goal: improve total CAGR / MDD frontier by making case2 more orthogonal to case1

## Ranking

| Variant | Total CAGR % | Total MDD % | Total Calmar | Case2 CAGR % | Case2 MDD % | Trades | Winner Adds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_case2 | 103.2781 | 50.8536 | 2.0309 | 99.0018 | 74.0774 | N/A | N/A |
| short_720_slow | 76.0334 | 60.1453 | 1.2642 | -19.1043 | 64.1415 | 619 | 324 |
| dual_720_slow | 75.8923 | 60.4542 | 1.2554 | -22.4941 | 69.9489 | 1164 | 615 |
| short_240_fast | 75.8185 | 60.5710 | 1.2517 | -24.4637 | 84.0704 | 1133 | 616 |
| dual_240_fast | 75.6640 | 60.7805 | 1.2449 | -29.1918 | 86.8380 | 2108 | 1145 |
| dual_240_aggr | 75.3451 | 60.8996 | 1.2372 | -44.2577 | 94.9011 | 2266 | 2026 |

## Best Variant
- `baseline_case2`: total CAGR `103.2781%`, total MDD `50.8536%`, total Calmar `2.0309`

## Delta vs baseline_case2
- `short_720_slow`: CAGR `-27.2447pp`, MDD `9.2917pp`, Calmar `-0.7667`
- `dual_720_slow`: CAGR `-27.3858pp`, MDD `9.6006pp`, Calmar `-0.7755`
- `short_240_fast`: CAGR `-27.4596pp`, MDD `9.7174pp`, Calmar `-0.7792`
- `dual_240_fast`: CAGR `-27.6141pp`, MDD `9.9269pp`, Calmar `-0.7860`
- `dual_240_aggr`: CAGR `-27.9331pp`, MDD `10.0460pp`, Calmar `-0.7937`

## Interpretation
- No replacement case2 dominated the current baseline on both total CAGR and total MDD.
- If dual breakout variants outperform short-only variants, case2 should remain a full orthogonal alpha engine instead of a pure hedge sleeve.
- If short-only variants reduce MDD but crush CAGR, then protection is being bought too expensively and case2 needs a better bull-side alpha component.

## Outputs
- Plot: `67_backtest_btcusdt_scale06_adx002_case2_breakout_momentum_replace.png`
- Metrics CSV: `67_backtest_btcusdt_scale06_adx002_case2_breakout_momentum_replace.csv`
- Curves CSV: `67_backtest_btcusdt_scale06_adx002_case2_breakout_momentum_replace_curves.csv`
- Report: `67_backtest_btcusdt_scale06_adx002_case2_breakout_momentum_replace.md`