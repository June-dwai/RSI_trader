# Study 74: Three-Sleeve Grid With Case3 Candidates

## Setup
- Baseline is the study-70 winner: `case1 74% / case2 26%`, 4h rebalance, fee-aware.
- Candidate case3 sleeves are:
  regime-hold tuned winner from study 73 (`dual_stop6`)
  compression-breakout candidate from study 71 (`compression_breakout_dual`)
- Total capital is fixed; weights are reallocated across three sleeves rather than adding new capital.

## Top 12

| Variant | Case3 | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Fee Paid |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| regime_hold_case3_w60_24_16 | regime_hold_case3 | 0.60 | 0.24 | 0.16 | 112.9641 | 43.2107 | 2.6143 | 312.0775 |
| regime_hold_case3_w60_22_18 | regime_hold_case3 | 0.60 | 0.22 | 0.18 | 111.7057 | 43.1128 | 2.5910 | 314.6023 |
| regime_hold_case3_w62_24_14 | regime_hold_case3 | 0.62 | 0.24 | 0.14 | 113.7004 | 43.9504 | 2.5870 | 302.3921 |
| regime_hold_case3_w60_26_14 | regime_hold_case3 | 0.60 | 0.26 | 0.14 | 114.1353 | 44.1699 | 2.5840 | 307.9378 |
| regime_hold_case3_w62_22_16 | regime_hold_case3 | 0.62 | 0.22 | 0.16 | 112.4872 | 43.8894 | 2.5630 | 306.1230 |
| regime_hold_case3_w64_24_12 | regime_hold_case3 | 0.64 | 0.24 | 0.12 | 114.3806 | 44.6836 | 2.5598 | 290.9859 |
| regime_hold_case3_w62_26_12 | regime_hold_case3 | 0.62 | 0.26 | 0.12 | 114.8252 | 44.9004 | 2.5573 | 297.0553 |
| regime_hold_case3_w60_28_12 | regime_hold_case3 | 0.60 | 0.28 | 0.12 | 115.2174 | 45.1190 | 2.5536 | 302.1748 |
| regime_hold_case3_w60_20_20 | regime_hold_case3 | 0.60 | 0.20 | 0.20 | 110.3615 | 43.4951 | 2.5373 | 315.5866 |
| regime_hold_case3_w64_22_14 | regime_hold_case3 | 0.64 | 0.22 | 0.14 | 113.2135 | 44.6743 | 2.5342 | 295.9208 |
| regime_hold_case3_w66_24_10 | regime_hold_case3 | 0.66 | 0.24 | 0.10 | 115.0041 | 45.4106 | 2.5325 | 277.8396 |
| regime_hold_case3_w64_26_10 | regime_hold_case3 | 0.64 | 0.26 | 0.10 | 115.4584 | 45.6246 | 2.5306 | 284.4605 |

## Best Variant
- `regime_hold_case3_w60_24_16`: CAGR `112.9641%`, MDD `43.2107%`, Calmar `2.6143`

## Delta vs Baseline 70
- CAGR `-4.7844pp`, MDD `-5.9402pp`, Calmar `0.2186`

## Interpretation
- At least one three-sleeve mix dominated the two-sleeve study-70 baseline on both CAGR and MDD.
- If small case3 weights rank well, then these alternate mindsets are portfolio diversifiers rather than standalone engines.
- If even tiny case3 allocations hurt, then they should stay in the idea backlog rather than entering the live mix.

## Outputs
- Plot: `74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.png`
- Metrics CSV: `74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.csv`
- Curves CSV: `74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid_curves.csv`
- Report: `74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.md`