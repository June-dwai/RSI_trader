# Study 120: Fine Tune Weights + Rebalance Around 119

## Setup
- Goal is to hold the study-119 winning case3 source fixed and only fine-tune weights plus rebalance cadence.
- Fixed case3 source is `lv3p0_g12_body25_tp20_lb5_none`.
- Search axes are case1 weight `46%~52%`, case3 weight `22%~30%`, and rebalance rule from `30min` to `4h`.
- Common study period is `2022-01-01 08:00:00` to `2026-02-12 00:00:00`.
- Ranking priority is `CAGR >= 133%` first, then domination over study 119, then Calmar.

## Baselines
- Rebuilt study-85 leader: CAGR `121.9577%`, MDD `45.1117%`, Calmar `2.7035`
- Rebuilt study-119 best: CAGR `132.2561%`, MDD `42.8382%`, Calmar `3.0873`

## Best Variant
- `lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_24_30` -> CAGR `138.0334%`, MDD `43.4085%`, Calmar `3.1799`, weights `0.46/0.24/0.30`, rebalance `30min`
- Delta vs rebuilt 119 best: CAGR `5.7774pp`, MDD `0.5703pp`, Calmar `0.0925`
- Delta vs rebuilt 85 leader: CAGR `16.0757pp`, MDD `-1.7032pp`, Calmar `0.4764`

## Top 12

| Variant | Rebalance | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Delta CAGR vs 119 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_24_30 | 30min | 0.46 | 0.24 | 0.30 | 138.0334 | 43.4085 | 3.1799 | 5.7774 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_25_29 | 30min | 0.46 | 0.25 | 0.29 | 137.7467 | 43.3541 | 3.1772 | 5.4907 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w47_25_28 | 30min | 0.47 | 0.25 | 0.28 | 137.2544 | 43.2381 | 3.1744 | 4.9983 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_26_28 | 30min | 0.46 | 0.26 | 0.28 | 137.4327 | 43.3001 | 3.1740 | 5.1766 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w47_24_29 | 30min | 0.47 | 0.24 | 0.29 | 137.5565 | 43.3402 | 3.1739 | 5.3005 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w48_25_27 | 30min | 0.48 | 0.25 | 0.27 | 136.7445 | 43.1224 | 3.1711 | 4.4885 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w47_26_27 | 30min | 0.47 | 0.26 | 0.27 | 136.9250 | 43.1843 | 3.1707 | 4.6689 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_27_27 | 30min | 0.46 | 0.27 | 0.27 | 137.0915 | 43.2466 | 3.1700 | 4.8354 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w48_26_26 | 30min | 0.48 | 0.26 | 0.26 | 136.3998 | 43.0687 | 3.1670 | 4.1438 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w47_27_26 | 30min | 0.47 | 0.27 | 0.26 | 136.5685 | 43.1309 | 3.1664 | 4.3124 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_28_26 | 30min | 0.46 | 0.28 | 0.26 | 136.7231 | 43.1935 | 3.1654 | 4.4670 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w49_26_25 | 30min | 0.49 | 0.26 | 0.25 | 135.8573 | 42.9534 | 3.1629 | 3.6013 |

## Interpretation
- At least one fine-tuned portfolio exceeds the 133% CAGR target.
- No fine-tuned portfolio beats the rebuilt 119 best on both CAGR and MDD.
- At least one fine-tuned portfolio also beats the rebuilt 85 leader on both CAGR and MDD.
- If sub-hour rebalance wins, then more of the remaining alpha still lives in portfolio plumbing.

## Outputs
- Plot: `120_backtest_btcusdt_case123_fine_tune_rebalance_and_weights.png`
- Metrics CSV: `120_backtest_btcusdt_case123_fine_tune_rebalance_and_weights.csv`
- Curves CSV: `120_backtest_btcusdt_case123_fine_tune_rebalance_and_weights_curves.csv`
- Report: `120_backtest_btcusdt_case123_fine_tune_rebalance_and_weights.md`