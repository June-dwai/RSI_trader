# Study 75: Regime-Hold Case3 Weight Tuning

## Setup
- Focus only on the promising case3 from study 74: `regime_hold_case3`.
- Search region is the small-case3 zone where study 74 already found dominance over study 70.
- Rebalance cadence and fee model are unchanged from studies 70 and 74.

## Top 12

| Variant | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Fee Paid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| regime_hold_case3_w68_24_8 | 0.68 | 0.24 | 0.08 | 115.5702 | 46.1312 | 2.5053 | 262.9705 |
| regime_hold_case3_w67_25_8 | 0.67 | 0.25 | 0.08 | 115.8086 | 46.2366 | 2.5047 | 266.6977 |
| regime_hold_case3_w66_26_8 | 0.66 | 0.26 | 0.08 | 116.0340 | 46.3424 | 2.5038 | 270.1811 |
| regime_hold_case3_w65_27_8 | 0.65 | 0.27 | 0.08 | 116.2462 | 46.4488 | 2.5027 | 273.4165 |
| regime_hold_case3_w64_28_8 | 0.64 | 0.28 | 0.08 | 116.4452 | 46.5555 | 2.5012 | 276.4031 |
| regime_hold_case3_w63_29_8 | 0.63 | 0.29 | 0.08 | 116.6310 | 46.6627 | 2.4994 | 279.1389 |
| regime_hold_case3_w62_30_8 | 0.62 | 0.30 | 0.08 | 116.8035 | 46.7703 | 2.4974 | 281.6236 |
| regime_hold_case3_w61_31_8 | 0.61 | 0.31 | 0.08 | 116.9627 | 46.8784 | 2.4950 | 283.8605 |
| regime_hold_case3_w60_32_8 | 0.60 | 0.32 | 0.08 | 117.1085 | 46.9869 | 2.4924 | 285.8487 |
| regime_hold_case3_w69_24_7 | 0.69 | 0.24 | 0.07 | 115.8314 | 46.4891 | 2.4916 | 254.9107 |
| regime_hold_case3_w68_25_7 | 0.68 | 0.25 | 0.07 | 116.0723 | 46.5938 | 2.4912 | 258.7864 |
| regime_hold_case3_w67_26_7 | 0.67 | 0.26 | 0.07 | 116.3000 | 46.6990 | 2.4904 | 262.4130 |

## Best Variant
- `regime_hold_case3_w68_24_8`: CAGR `115.5702%`, MDD `46.1312%`, Calmar `2.5053`

## Delta vs Baseline 70
- CAGR `-2.1783pp`, MDD `-3.0198pp`, Calmar `0.1096`

## Interpretation
- Multiple tuned case3 weights dominate the two-sleeve study-70 baseline on both CAGR and MDD.
- If the optimum keeps case3 small, then regime-hold works as a diversifier rather than a main return engine.

## Outputs
- Plot: `75_backtest_btcusdt_scale06_adx002_case3_regime_hold_weight_tune.png`
- Metrics CSV: `75_backtest_btcusdt_scale06_adx002_case3_regime_hold_weight_tune.csv`
- Curves CSV: `75_backtest_btcusdt_scale06_adx002_case3_regime_hold_weight_tune_curves.csv`
- Report: `75_backtest_btcusdt_scale06_adx002_case3_regime_hold_weight_tune.md`