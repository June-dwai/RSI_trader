# Study 79: Partial Take-Profit Runner

## Model
- Uses the study-76 regime-hold engine and its no-lookahead 4h confirmed regime signal.
- When current-close wallet return from the active trade reaches the TP threshold, only a fraction of the position is closed.
- The remaining runner stays active until stop or regime flip. Some variants move the runner stop to breakeven after the partial TP.
- TP is checked only once per trade, on the current 4h close, to avoid intrabar ambiguity.

## Ranking

| Variant | Lev | TP % | Cut % | BE Stop | CAGR % | MDD % | Calmar | Final Equity | TP Partials |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| ptp20_cut50_nobe_2x | 2.0 | 20 | 50 | no | 42.7753 | 50.8583 | 0.8411 | 4461.1903 | 28 |
| ptp20_cut50_be_2x | 2.0 | 20 | 50 | yes | 40.9863 | 50.8583 | 0.8059 | 4231.1181 | 28 |
| ptp20_cut25_be_2x | 2.0 | 20 | 25 | yes | 41.4004 | 52.8369 | 0.7836 | 4283.5500 | 28 |
| ptp20_cut25_be_1.5x | 1.5 | 20 | 25 | yes | 33.3091 | 43.7005 | 0.7622 | 3344.5491 | 19 |
| base_1.5x | 1.5 | N/A | 0 | no | 35.9322 | 49.8715 | 0.7205 | 3629.7345 | 0 |
| ptp20_cut50_be_1.5x | 1.5 | 20 | 50 | yes | 28.7125 | 43.7005 | 0.6570 | 2886.3037 | 19 |
| base_2x | 2.0 | N/A | 0 | no | 38.4140 | 59.8575 | 0.6418 | 3916.2700 | 0 |
| ptp30_cut50_be_2x | 2.0 | 30 | 50 | yes | 29.2274 | 57.4688 | 0.5086 | 2935.0995 | 17 |

## Best Variant
- `ptp20_cut50_nobe_2x`: CAGR `42.7753%`, MDD `50.8583%`, Calmar `0.8411`

## Delta vs Same-Leverage Baseline
- `ptp20_cut50_nobe_2x` vs `base_2x`: CAGR `4.3612pp`, MDD `-8.9992pp`, Calmar `0.1993`, TP partials `28`
- `ptp20_cut50_be_2x` vs `base_2x`: CAGR `2.5723pp`, MDD `-8.9992pp`, Calmar `0.1641`, TP partials `28`
- `ptp20_cut25_be_2x` vs `base_2x`: CAGR `2.9864pp`, MDD `-7.0206pp`, Calmar `0.1418`, TP partials `28`
- `ptp20_cut25_be_1.5x` vs `base_1.5x`: CAGR `-2.6231pp`, MDD `-6.1711pp`, Calmar `0.0417`, TP partials `19`
- `ptp20_cut50_be_1.5x` vs `base_1.5x`: CAGR `-7.2197pp`, MDD `-6.1711pp`, Calmar `-0.0635`, TP partials `19`
- `ptp30_cut50_be_2x` vs `base_2x`: CAGR `-9.1867pp`, MDD `-2.3887pp`, Calmar `-0.1332`, TP partials `17`

## Interpretation
- If a partial TP runner beats the same-leverage baseline, then full-trend holding was too greedy but full TP-lock was too blunt.
- If breakeven-stop variants outperform no-breakeven variants, then the main value is in protecting the runner rather than just de-risking notional.
- If cut-25 works better than cut-50, the strategy still needs a large runner to monetize long trends.

## Outputs
- Plot: `79_backtest_btcusdt_scale06_adx002_regime_hold_partial_tp_runner.png`
- Metrics CSV: `79_backtest_btcusdt_scale06_adx002_regime_hold_partial_tp_runner.csv`
- Curves CSV: `79_backtest_btcusdt_scale06_adx002_regime_hold_partial_tp_runner_curves.csv`
- Report: `79_backtest_btcusdt_scale06_adx002_regime_hold_partial_tp_runner.md`