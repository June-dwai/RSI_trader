# Study 119: Fine Tune Around Study-118 Winner

## Setup
- Goal is to fine-tune the study-118 winner neighborhood rather than searching a broad new family.
- Search axes are: top case3 source variants from study 118, case1 weight, case3 weight, and rebalance hours.
- Common study period is `2022-01-01 08:00:00` to `2026-02-12 00:00:00`.
- Ranking priority is `CAGR >= 130%` first, then domination over study 118, then Calmar.

## Focused Case3 Sources
- `lv3p0_g12_body25_tp20_lb5_none`
- `lv3p0_g12_body20_tp20_lb5_none`

## Baselines
- Rebuilt study-85 leader: CAGR `121.9577%`, MDD `45.1117%`, Calmar `2.7035`
- Rebuilt study-118 best: CAGR `129.5209%`, MDD `43.5679%`, Calmar `2.9728`

## Best Variant
- `lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w49_27_24` (lv3p0_g12_body25_tp20_lb5_none) -> CAGR `132.2561%`, MDD `42.8382%`, Calmar `3.0873`, weights `0.49/0.27/0.24`, rebalance `1h`
- Delta vs rebuilt 118 best: CAGR `2.7352pp`, MDD `-0.7297pp`, Calmar `0.1145`
- Delta vs rebuilt 85 leader: CAGR `10.2983pp`, MDD `-2.2735pp`, Calmar `0.3839`

## Top 12

| Variant | Case3 Source | Rebalance | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Delta CAGR vs 118 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w49_27_24 | lv3p0_g12_body25_tp20_lb5_none | 1h | 0.49 | 0.27 | 0.24 | 132.2561 | 42.8382 | 3.0873 | 2.7352 |
| lv3p0_g12_body20_tp20_lb5_none_case3_rb1h_w49_27_24 | lv3p0_g12_body20_tp20_lb5_none | 1h | 0.49 | 0.27 | 0.24 | 132.1807 | 42.8382 | 3.0856 | 2.6598 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w48_28_24 | lv3p0_g12_body25_tp20_lb5_none | 1h | 0.48 | 0.28 | 0.24 | 132.4173 | 42.9900 | 3.0802 | 2.8965 |
| lv3p0_g12_body20_tp20_lb5_none_case3_rb1h_w48_28_24 | lv3p0_g12_body20_tp20_lb5_none | 1h | 0.48 | 0.28 | 0.24 | 132.3416 | 42.9900 | 3.0784 | 2.8208 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w50_27_23 | lv3p0_g12_body25_tp20_lb5_none | 1h | 0.50 | 0.27 | 0.23 | 131.7900 | 42.9436 | 3.0689 | 2.2691 |
| lv3p0_g12_body20_tp20_lb5_none_case3_rb1h_w50_27_23 | lv3p0_g12_body20_tp20_lb5_none | 1h | 0.50 | 0.27 | 0.23 | 131.7180 | 42.9436 | 3.0672 | 2.1971 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb4h_w49_27_24 | lv3p0_g12_body25_tp20_lb5_none | 4h | 0.49 | 0.27 | 0.24 | 130.9234 | 42.7116 | 3.0653 | 1.4025 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb4h_w48_28_24 | lv3p0_g12_body25_tp20_lb5_none | 4h | 0.48 | 0.28 | 0.24 | 131.1090 | 42.7751 | 3.0651 | 1.5881 |
| lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w49_28_23 | lv3p0_g12_body25_tp20_lb5_none | 1h | 0.49 | 0.28 | 0.23 | 131.9535 | 43.0645 | 3.0641 | 2.4326 |
| lv3p0_g12_body20_tp20_lb5_none_case3_rb4h_w49_27_24 | lv3p0_g12_body20_tp20_lb5_none | 4h | 0.49 | 0.27 | 0.24 | 130.8539 | 42.7116 | 3.0637 | 1.3331 |
| lv3p0_g12_body20_tp20_lb5_none_case3_rb4h_w48_28_24 | lv3p0_g12_body20_tp20_lb5_none | 4h | 0.48 | 0.28 | 0.24 | 131.0394 | 42.7751 | 3.0635 | 1.5186 |
| lv3p0_g12_body20_tp20_lb5_none_case3_rb1h_w49_28_23 | lv3p0_g12_body20_tp20_lb5_none | 1h | 0.49 | 0.28 | 0.23 | 131.8811 | 43.0645 | 3.0624 | 2.3603 |

## Interpretation
- At least one fine-tuned portfolio exceeds the 130% CAGR target.
- At least one fine-tuned portfolio beats the rebuilt 118 best on both CAGR and MDD.
- At least one fine-tuned portfolio also beats the rebuilt 85 leader on both CAGR and MDD.
- If a non-4h rebalance wins, then part of the remaining upside came from portfolio plumbing rather than sleeve alpha alone.

## Outputs
- Plot: `119_backtest_btcusdt_case123_portfolio_fine_tune_around_118.png`
- Metrics CSV: `119_backtest_btcusdt_case123_portfolio_fine_tune_around_118.csv`
- Curves CSV: `119_backtest_btcusdt_case123_portfolio_fine_tune_around_118_curves.csv`
- Report: `119_backtest_btcusdt_case123_portfolio_fine_tune_around_118.md`