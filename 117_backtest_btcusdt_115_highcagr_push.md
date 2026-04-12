# Study 117: Push Study-115 Toward 130% CAGR

## Setup
- Base idea is to keep the study-115 long-side SMC filter, but pair it with stronger short-gate settings closer to study 84.
- Backtest period is `2021-01-02` to `2026-03-15` on the 2021+ BTCUSDT cache.
- Search axes are leverage, short gate length, short TP threshold, SMC long-block threshold, and whether longs must stay above `red_avg`.
- Ranking priority is `CAGR >= 130%` first, then higher Calmar, then higher CAGR, then lower MDD.

## References
- `reference_115_best`: CAGR `109.5105%`, MDD `52.3206%`, Calmar `2.0931`
- `reference_84_best`: CAGR `111.1024%`, MDD `62.1257%`, Calmar `1.7883`

## Best Variant
- `lv2p5_g12_body20_tp20_lb5_none` -> CAGR `145.2192%`, MDD `59.0448%`, Calmar `2.4595`, Final Equity `105813.5209`
- Delta vs study-115 best: CAGR `35.7087pp`, MDD `6.7242pp`, Calmar `0.3664`
- Delta vs study-84 best reference: CAGR `34.1168pp`, MDD `-3.0809pp`, Calmar `0.6711`

## Top 12

| Variant | Leverage | Gate Bars | TP % | Long Block | SR Mode | CAGR % | MDD % | Calmar | Trades |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| lv2p5_g12_body20_tp20_lb5_none | 2.50 | 12 | 20.0 | 5 | none | 145.2192 | 59.0448 | 2.4595 | 123 |
| lv2p5_g12_body25_tp20_lb5_none | 2.50 | 12 | 20.0 | 5 | none | 144.3210 | 59.0448 | 2.4443 | 123 |
| lv3p0_g8_body20_tp20_lb5_none | 3.00 | 8 | 20.0 | 5 | none | 153.5918 | 64.5809 | 2.3783 | 123 |
| lv3p0_g8_body25_tp20_lb5_none | 3.00 | 8 | 20.0 | 5 | none | 153.3836 | 64.5809 | 2.3751 | 123 |
| lv3p0_g12_body25_tp20_lb5_none | 3.00 | 12 | 20.0 | 5 | none | 151.3261 | 64.5809 | 2.3432 | 123 |
| lv3p0_g12_body20_tp20_lb5_none | 3.00 | 12 | 20.0 | 5 | none | 151.0629 | 64.5809 | 2.3391 | 123 |
| lv2p5_g12_body20_tp20_lb5_long_above_red_avg | 2.50 | 12 | 20.0 | 5 | long_above_red_avg | 140.1293 | 60.4032 | 2.3199 | 121 |
| lv2p5_g12_body25_tp20_lb5_long_above_red_avg | 2.50 | 12 | 20.0 | 5 | long_above_red_avg | 139.2497 | 60.4032 | 2.3053 | 121 |
| lv2p5_g8_body20_tp20_lb5_none | 2.50 | 8 | 20.0 | 5 | none | 135.2286 | 59.0448 | 2.2903 | 123 |
| lv2p5_g8_body25_tp20_lb5_none | 2.50 | 8 | 20.0 | 5 | none | 134.7896 | 59.0448 | 2.2828 | 123 |
| lv3p0_g8_body20_tp20_lb5_long_above_red_avg | 3.00 | 8 | 20.0 | 5 | long_above_red_avg | 147.3224 | 66.2773 | 2.2228 | 121 |
| lv3p0_g8_body25_tp20_lb5_long_above_red_avg | 3.00 | 8 | 20.0 | 5 | long_above_red_avg | 147.1193 | 66.2773 | 2.2198 | 121 |

## Interpretation
- The search found at least one variant above the 130% CAGR target.
- If higher leverage plus the stronger short-gate family ranks near the top, then the 115 improvement is portable into the 84-style engine.
- If `long_above_red_avg` does not appear in the winners, then SR is still weaker than the SMC long-block signal for this engine family.

## Outputs
- Plot: `117_backtest_btcusdt_115_highcagr_push.png`
- Metrics CSV: `117_backtest_btcusdt_115_highcagr_push.csv`
- Curves CSV: `117_backtest_btcusdt_115_highcagr_push_curves.csv`
- Report: `117_backtest_btcusdt_115_highcagr_push.md`