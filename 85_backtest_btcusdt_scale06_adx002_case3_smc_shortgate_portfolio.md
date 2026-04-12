# Study 85: SMC Short-Gate Case3 Portfolio

## Setup
- Case3 candidates are selected automatically from the top live performers in study 84.
- Baseline remains the study-70 two-sleeve winner under the same common-period clipping used in this study.
- Search region stays near the prior winning case1/case2 ridge and keeps case3 small.

## Top 12

| Variant | Case3 | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Fee Paid |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| short_gate_24h_g12_tp15_case3_w62_31_7 | short_gate_24h_g12_tp15_case3 | 0.62 | 0.31 | 0.07 | 120.6837 | 46.7127 | 2.5835 | 248.4122 |
| short_gate_24h_g12_tp15_case3_w61_32_7 | short_gate_24h_g12_tp15_case3 | 0.61 | 0.32 | 0.07 | 120.8314 | 46.8192 | 2.5808 | 250.8631 |
| short_gate_24h_g12_tp15_case3_w60_33_7 | short_gate_24h_g12_tp15_case3 | 0.60 | 0.33 | 0.07 | 120.9655 | 46.9262 | 2.5778 | 253.0516 |
| short_gate_24h_g12_tp15_case3_w59_34_7 | short_gate_24h_g12_tp15_case3 | 0.59 | 0.34 | 0.07 | 121.0860 | 47.0336 | 2.5745 | 254.9781 |
| short_gate_24h_g12_tp15_case3_w62_32_6 | short_gate_24h_g12_tp15_case3 | 0.62 | 0.32 | 0.06 | 120.5671 | 47.2477 | 2.5518 | 246.6871 |
| short_gate_24h_g12_tp15_case3_w61_33_6 | short_gate_24h_g12_tp15_case3 | 0.61 | 0.33 | 0.06 | 120.7031 | 47.3541 | 2.5489 | 248.9637 |
| short_gate_24h_g12_tp15_case3_w60_34_6 | short_gate_24h_g12_tp15_case3 | 0.60 | 0.34 | 0.06 | 120.8256 | 47.4610 | 2.5458 | 250.9779 |
| short_gate_24h_g12_tp15_case3_w59_35_6 | short_gate_24h_g12_tp15_case3 | 0.59 | 0.35 | 0.06 | 120.9344 | 47.5683 | 2.5423 | 252.7324 |
| short_gate_24h_g12_tp10_case3_w62_31_7 | short_gate_24h_g12_tp10_case3 | 0.62 | 0.31 | 0.07 | 119.0867 | 46.9032 | 2.5390 | 243.0003 |
| short_gate_24h_g12_tp10_case3_w61_32_7 | short_gate_24h_g12_tp10_case3 | 0.61 | 0.32 | 0.07 | 119.2368 | 47.0094 | 2.5364 | 245.4707 |
| short_gate_24h_g12_tp10_case3_w60_33_7 | short_gate_24h_g12_tp10_case3 | 0.60 | 0.33 | 0.07 | 119.3735 | 47.1159 | 2.5336 | 247.6833 |
| short_gate_24h_g12_tp10_case3_w59_34_7 | short_gate_24h_g12_tp10_case3 | 0.59 | 0.34 | 0.07 | 119.4966 | 47.2229 | 2.5305 | 249.6383 |

## Best Variant
- `short_gate_24h_g12_tp15_case3_w62_31_7`: CAGR `120.6837%`, MDD `46.7127%`, Calmar `2.5835`

## Delta vs Baselines
- vs study-70 baseline: CAGR `2.9383pp`, MDD `-2.4382pp`, Calmar `0.1879`
- vs study-81 best: CAGR `0.3124pp`, MDD `-0.6527pp`, Calmar `0.0422`

## Interpretation
- At least one study-84 case3 mix dominates the two-sleeve study-70 baseline on both CAGR and MDD.
- At least one study-84 case3 mix also dominates the prior study-81 best case3 mix.
- If the best case3 weight stays around `5%~7%`, this sleeve is still acting as a diversifier rather than a core engine.

## Outputs
- Plot: `85_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_portfolio.png`
- Metrics CSV: `85_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_portfolio.csv`
- Curves CSV: `85_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_portfolio_curves.csv`
- Report: `85_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_portfolio.md`