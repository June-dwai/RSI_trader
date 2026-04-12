# Study 116: 85 Portfolio + 115 Case3 Replacement

## Setup
- Goal is to test whether the study-115 style sleeve can replace the study-84 case3 sleeve inside the case1/case2/case3 portfolio.
- To keep the sweep tractable, all sleeves are reconstructed on a common `15m` grid and still rebalanced every `4h`.
- Common study period is `2022-01-01 08:00:00` to `2026-02-12 00:00:00`.
- The 85 leader and the 85 CAGR-peak row are both rebuilt on the same 15m engine for apples-to-apples comparison.

## Reported 85 References
- Reported leader used in study 112: `short_gate_24h_g12_tp15_case3_w62_31_7` -> CAGR `120.6837%`, MDD `46.7127%`, Calmar `2.5835`
- Reported 85 CAGR peak: `short_gate_24h_g12_tp15_case3_w59_34_7` -> CAGR `121.0860%`, MDD `47.0336%`, Calmar `2.5745`

## Rebuilt References
- Rebuilt 85 leader: CAGR `121.9577%`, MDD `45.1117%`, Calmar `2.7035`
- Rebuilt 85 CAGR peak: CAGR `122.4032%`, MDD `45.4447%`, Calmar `2.6935`

## Best Variant
- `short_gate_24h_g12_tp15_case3_w60_31_9` (study84_best) -> CAGR `122.5595%`, MDD `44.2220%`, Calmar `2.7715`, weights `0.60/0.31/0.09`
- Delta vs rebuilt 85 leader: CAGR `0.6018pp`, MDD `-0.8896pp`, Calmar `0.0680`
- Delta vs rebuilt 85 CAGR peak: CAGR `0.1563pp`, MDD `-1.2227pp`, Calmar `0.0780`

## Best 115-Based Replacement
- `smc5_longonly_case3_w62_29_9` (study115_best) -> CAGR `119.6035%`, MDD `45.6542%`, Calmar `2.6198`

## Top 12

| Variant | Source | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Delta CAGR vs 85 | Delta Calmar vs 85 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| short_gate_24h_g12_tp15_case3_w60_31_9 | study84_best | 0.60 | 0.31 | 0.09 | 122.5595 | 44.2220 | 2.7715 | 0.6018 | 0.0680 |
| short_gate_24h_g12_tp15_case3_w59_32_9 | study84_best | 0.59 | 0.32 | 0.09 | 122.7184 | 44.3337 | 2.7681 | 0.7606 | 0.0646 |
| short_gate_24h_g12_tp15_case3_w58_33_9 | study84_best | 0.58 | 0.33 | 0.09 | 122.8627 | 44.4458 | 2.7643 | 0.9049 | 0.0609 |
| short_gate_24h_g12_tp15_case3_w60_32_8 | study84_best | 0.60 | 0.32 | 0.08 | 122.4234 | 44.7794 | 2.7339 | 0.4657 | 0.0305 |
| short_gate_24h_g12_tp15_case3_w59_33_8 | study84_best | 0.59 | 0.33 | 0.08 | 122.5698 | 44.8909 | 2.7304 | 0.6121 | 0.0269 |
| short_gate_24h_g12_tp15_case3_w58_34_8 | study84_best | 0.58 | 0.34 | 0.08 | 122.7017 | 45.0028 | 2.7265 | 0.7439 | 0.0231 |
| short_gate_24h_g12_tp15_case3_w62_29_9 | study84_best | 0.62 | 0.29 | 0.09 | 122.1981 | 43.9998 | 2.7772 | 0.2404 | 0.0738 |
| short_gate_24h_g12_tp15_case3_w61_30_9 | study84_best | 0.61 | 0.30 | 0.09 | 122.3861 | 44.1107 | 2.7745 | 0.4283 | 0.0711 |
| short_gate_24h_g12_tp15_case3_w62_30_8 | study84_best | 0.62 | 0.30 | 0.08 | 122.0870 | 44.5574 | 2.7400 | 0.1292 | 0.0365 |
| short_gate_24h_g12_tp15_case3_w61_31_8 | study84_best | 0.61 | 0.31 | 0.08 | 122.2625 | 44.6682 | 2.7371 | 0.3047 | 0.0337 |
| short_gate_24h_g12_tp15_case3_w58_35_7 | study84_best | 0.58 | 0.35 | 0.07 | 122.5225 | 45.5565 | 2.6895 | 0.5648 | -0.0140 |
| study85_leader_reference | study85_reference | 0.62 | 0.31 | 0.07 | 121.9577 | 45.1117 | 2.7035 | 0.0000 | 0.0000 |

## Interpretation
- At least one rebuilt variant beats the rebuilt 85 leader on both CAGR and MDD.
- At least one variant exceeds the rebuilt 85 CAGR peak.
- If the best 115-based case3 still trails the rebuilt 85 leader, then 115 works better as a single-engine refinement than as a direct case3 replacement.

## Outputs
- Plot: `116_backtest_btcusdt_case123_portfolio_with_115_case3.png`
- Metrics CSV: `116_backtest_btcusdt_case123_portfolio_with_115_case3.csv`
- Curves CSV: `116_backtest_btcusdt_case123_portfolio_with_115_case3_curves.csv`
- Report: `116_backtest_btcusdt_case123_portfolio_with_115_case3.md`