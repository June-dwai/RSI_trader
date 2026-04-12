# Study 81: Short-TP Regime-Hold as Case3

## Setup
- Baseline comparison remains the study-70 two-sleeve winner: `case1 74% / case2 26%`, 4h rebalance, fee-aware.
- New case3 candidates come from study 80, where short-only TP-lock materially improved standalone regime-hold.
- Search region focuses on small-to-moderate case3 weights (`4%~10%`) and the prior winning case1/case2 zone.

## Top 12

| Variant | Case3 | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Fee Paid |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| shorttp15_15x_case3_w61_33_6 | shorttp15_15x_case3 | 0.61 | 0.33 | 0.06 | 120.3713 | 47.3654 | 2.5413 | 293.5326 |
| shorttp15_15x_case3_w60_34_6 | shorttp15_15x_case3 | 0.60 | 0.34 | 0.06 | 120.4934 | 47.4743 | 2.5381 | 295.3398 |
| shorttp15_15x_case3_w61_34_5 | shorttp15_15x_case3 | 0.61 | 0.34 | 0.05 | 120.3105 | 47.8964 | 2.5119 | 284.0619 |
| shorttp15_15x_case3_w60_35_5 | shorttp15_15x_case3 | 0.60 | 0.35 | 0.05 | 120.4210 | 48.0049 | 2.5085 | 285.7296 |
| baseline_70_case12_only | none | 0.74 | 0.26 | 0.00 | 117.6791 | 49.1509 | 2.3942 | 196.1380 |

## Best Variant
- `shorttp15_15x_case3_w61_33_6`: CAGR `120.3713%`, MDD `47.3654%`, Calmar `2.5413`

## Delta vs Study 70 Baseline
- CAGR `2.6259pp`, MDD `-1.7855pp`, Calmar `0.1457`

## Delta vs Prior Best Case3 Mix
- Prior best from study 75: `regime_hold_case3_w61_33_6` with CAGR `117.7910%`, MDD `47.7977%`, Calmar `2.4644`
- New best delta: CAGR `2.5802pp`, MDD `-0.4323pp`, Calmar `0.0770`

## Interpretation
- At least one short-TP case3 mix dominates the study-70 two-sleeve baseline on both CAGR and MDD.
- The improved short-TP regime-hold also beats the prior study-75 case3 leader on Calmar.
- If the best weight stays small, this is still a diversifier sleeve rather than a core return engine.

## Outputs
- Plot: `81_backtest_btcusdt_scale06_adx002_case3_shorttp_portfolio_grid.png`
- Metrics CSV: `81_backtest_btcusdt_scale06_adx002_case3_shorttp_portfolio_grid.csv`
- Curves CSV: `81_backtest_btcusdt_scale06_adx002_case3_shorttp_portfolio_grid_curves.csv`
- Report: `81_backtest_btcusdt_scale06_adx002_case3_shorttp_portfolio_grid.md`