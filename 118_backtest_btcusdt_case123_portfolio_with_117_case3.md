# Study 118: 117 Case3 Portfolio Replacement

## Setup
- Goal is to test whether the stronger study-117 sleeves can replace the case3 sleeve inside the case1/case2/case3 portfolio.
- Baselines are the rebuilt study-85 leader and the rebuilt study-116 winner.
- Candidate case3 sleeves are the top live study-117 variants that were already saved in the study-117 selected curves file.
- Common study period is `2022-01-01 08:00:00` to `2026-02-12 00:00:00`.

## Candidate 117 Sleeves
- `lv2p5_g12_body20_tp20_lb5_none`
- `lv2p5_g12_body25_tp20_lb5_none`
- `lv3p0_g8_body20_tp20_lb5_none`
- `lv3p0_g8_body25_tp20_lb5_none`
- `lv3p0_g12_body25_tp20_lb5_none`
- `lv3p0_g12_body20_tp20_lb5_none`

## Baselines
- Rebuilt study-85 leader: CAGR `121.9577%`, MDD `45.1117%`, Calmar `2.7035`
- Rebuilt study-116 best: CAGR `122.5595%`, MDD `44.2220%`, Calmar `2.7715`

## Best Variant
- `lv3p0_g12_body25_tp20_lb5_none_case3_w52_28_20` (study117_live) -> CAGR `129.5209%`, MDD `43.5679%`, Calmar `2.9728`, weights `0.52/0.28/0.20`
- Delta vs rebuilt 116 best: CAGR `6.9614pp`, MDD `-0.6541pp`, Calmar `0.2014`
- Delta vs rebuilt 85 leader: CAGR `7.5631pp`, MDD `-1.5437pp`, Calmar `0.2694`

## Best 117-Based Replacement
- `lv3p0_g12_body25_tp20_lb5_none_case3_w52_28_20` -> CAGR `129.5209%`, MDD `43.5679%`, Calmar `2.9728`

## Top 12

| Variant | Source | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Delta CAGR vs 116 | Delta Calmar vs 116 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| lv3p0_g12_body25_tp20_lb5_none_case3_w52_28_20 | study117_live | 0.52 | 0.28 | 0.20 | 129.5209 | 43.5679 | 2.9728 | 6.9614 | 0.2014 |
| lv3p0_g12_body20_tp20_lb5_none_case3_w52_28_20 | study117_live | 0.52 | 0.28 | 0.20 | 129.4634 | 43.5679 | 2.9715 | 6.9040 | 0.2001 |
| lv3p0_g12_body25_tp20_lb5_none_case3_w50_30_20 | study117_live | 0.50 | 0.30 | 0.20 | 129.8664 | 43.7935 | 2.9654 | 7.3069 | 0.1940 |
| lv3p0_g12_body20_tp20_lb5_none_case3_w50_30_20 | study117_live | 0.50 | 0.30 | 0.20 | 129.8088 | 43.7935 | 2.9641 | 7.2493 | 0.1927 |
| lv3p0_g12_body25_tp20_lb5_none_case3_w54_26_20 | study117_live | 0.54 | 0.26 | 0.20 | 129.1152 | 43.6877 | 2.9554 | 6.5557 | 0.1840 |
| lv3p0_g12_body20_tp20_lb5_none_case3_w54_26_20 | study117_live | 0.54 | 0.26 | 0.20 | 129.0579 | 43.6877 | 2.9541 | 6.4984 | 0.1826 |
| lv3p0_g12_body25_tp20_lb5_none_case3_w56_27_17 | study117_live | 0.56 | 0.27 | 0.17 | 128.0142 | 44.0918 | 2.9034 | 5.4547 | 0.1319 |
| lv3p0_g12_body20_tp20_lb5_none_case3_w56_27_17 | study117_live | 0.56 | 0.27 | 0.17 | 127.9658 | 44.0918 | 2.9023 | 5.4063 | 0.1308 |
| lv3p0_g8_body20_tp20_lb5_none_case3_w52_28_20 | study117_live | 0.52 | 0.28 | 0.20 | 125.9848 | 43.5679 | 2.8917 | 3.4253 | 0.1202 |
| lv3p0_g8_body25_tp20_lb5_none_case3_w52_28_20 | study117_live | 0.52 | 0.28 | 0.20 | 125.9240 | 43.5679 | 2.8903 | 3.3645 | 0.1188 |
| lv3p0_g8_body20_tp20_lb5_none_case3_w50_30_20 | study117_live | 0.50 | 0.30 | 0.20 | 126.3194 | 43.7935 | 2.8844 | 3.7600 | 0.1130 |
| lv3p0_g8_body25_tp20_lb5_none_case3_w50_30_20 | study117_live | 0.50 | 0.30 | 0.20 | 126.2586 | 43.7935 | 2.8830 | 3.6991 | 0.1116 |

## Interpretation
- At least one 117-based portfolio beats the rebuilt 116 winner on both CAGR and MDD.
- At least one 117-based portfolio also beats the rebuilt 85 leader on both CAGR and MDD.
- At least one 117-based portfolio exceeds the rebuilt 116 CAGR even when it does not dominate on drawdown.
- If 117-based sleeves only win when case3 weight is meaningfully larger, then 117 is acting more like a core sleeve than the old case3 diversifier.

## Outputs
- Plot: `118_backtest_btcusdt_case123_portfolio_with_117_case3.png`
- Metrics CSV: `118_backtest_btcusdt_case123_portfolio_with_117_case3.csv`
- Curves CSV: `118_backtest_btcusdt_case123_portfolio_with_117_case3_curves.csv`
- Report: `118_backtest_btcusdt_case123_portfolio_with_117_case3.md`