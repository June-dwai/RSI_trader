# 60 Backtest: DCA 0.75% with Hedge Release Delay Variants

## Setup
- `case1` keeps study-56 best add spacing: `max_entries=4`, matched hedge size, `dca_drop=0.75%`.
- `case2` stays fixed as study-42 case2 curve.
- Variant idea: keep bearish hedge open longer on bullish reversals instead of closing on the first confirmed bullish 4h bucket.

## Results

| Variant | Bullish Close Bars | Shallow Gap % | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | Bullish Hold | Early Release |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `shallow5_else2bull` | 2 | 5.0000 | 40373.3822 | 107.5766 | 52.2416 | 2.0592 | 115.2661 | 47.2925 | 38 | 30 |
| `release1bull` | 1 | 0.0000 | 38126.1140 | 104.7073 | 52.2416 | 2.0043 | 110.0459 | 52.7733 | 0 | 0 |
| `release2bull` | 2 | 0.0000 | 36872.0861 | 103.0502 | 54.3703 | 1.8953 | 106.9479 | 45.8081 | 65 | 0 |
| `shallow2_else2bull` | 2 | 2.0000 | 36187.0670 | 102.1268 | 54.3703 | 1.8784 | 105.1928 | 47.2925 | 54 | 15 |
| `release3bull` | 3 | 0.0000 | 37255.1981 | 103.5609 | 56.8068 | 1.8230 | 107.9097 | 49.6614 | 127 | 0 |

## Best Cases
- Best total CAGR: `shallow5_else2bull` (`107.5766%`).
- Lowest total MDD: `shallow5_else2bull` (`52.2416%`).
- Best total Calmar: `shallow5_else2bull` (`2.0592`).

## Delta vs release1bull
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `shallow5_else2bull` | 2247.2682 | 2.8692 | 0.0000 | 0.0549 |
| `release1bull` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `release2bull` | -1254.0278 | -1.6572 | 2.1287 | -0.1089 |
| `shallow2_else2bull` | -1939.0470 | -2.5805 | 2.1287 | -0.1259 |
| `release3bull` | -870.9159 | -1.1464 | 4.5652 | -0.1813 |

## Dominance Check
- No tested hedge-release-delay variant achieved both `higher total CAGR` and `lower total MDD` than `release1bull`.

## Interpretation
- If a variant helps, it means hedge losses were being realized too early on single-bucket bullish flips.
- Waiting too long to release hedge will drag rebounds, so the tradeoff is whipsaw protection versus recovery participation.
- The key metric is whether smarter hedge release can preserve the study-56 CAGR boost while reducing its extra MDD.

## Outputs
- Plot: `60_backtest_btcusdt_scale06_adx002_case1_m4_dca075_hedge_release_delay_compare.png`
- Metrics CSV: `60_backtest_btcusdt_scale06_adx002_case1_m4_dca075_hedge_release_delay_compare.csv`
- Curves CSV: `60_backtest_btcusdt_scale06_adx002_case1_m4_dca075_hedge_release_delay_compare_curves.csv`
- Report: `60_backtest_btcusdt_scale06_adx002_case1_m4_dca075_hedge_release_delay_compare.md`