# 61 Backtest: MaxEntries=4 Baseline with Hedge Release Delay Variants

## Setup
- `case1` uses study-51 baseline: `max_entries=4`, matched hedge size, original `dca_drop=0.50%`.
- `case2` stays fixed as study-42 case2 curve.
- Variant idea: keep bearish hedge open longer on bullish reversals instead of closing on the first confirmed bullish 4h bucket.

## Results

| Variant | Bullish Close Bars | Shallow Gap % | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | Bullish Hold | Early Release |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `shallow5_else2bull` | 2 | 5.0000 | 36753.7386 | 102.8916 | 50.8650 | 2.0228 | 106.6480 | 60.4496 | 42 | 26 |
| `release1bull` | 1 | 0.0000 | 35703.7284 | 101.4674 | 50.3387 | 2.0157 | 103.9256 | 64.8802 | 0 | 0 |
| `release2bull` | 2 | 0.0000 | 34602.0754 | 99.9386 | 52.5963 | 1.9001 | 100.9422 | 58.4733 | 65 | 0 |
| `shallow2_else2bull` | 2 | 2.0000 | 33341.0324 | 98.1427 | 52.5963 | 1.8660 | 97.3487 | 60.4496 | 54 | 13 |

## Best Cases
- Best total CAGR: `shallow5_else2bull` (`102.8916%`).
- Lowest total MDD: `release1bull` (`50.3387%`).
- Best total Calmar: `shallow5_else2bull` (`2.0228`).

## Delta vs release1bull
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `shallow5_else2bull` | 1050.0102 | 1.4242 | 0.5262 | 0.0071 |
| `release1bull` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `release2bull` | -1101.6530 | -1.5288 | 2.2576 | -0.1156 |
| `shallow2_else2bull` | -2362.6960 | -3.3246 | 2.2576 | -0.1497 |

## Dominance Check
- No tested hedge-release-delay variant achieved both `higher total CAGR` and `lower total MDD` than `release1bull`.

## Interpretation
- If a variant helps, it means hedge losses were being realized too early on single-bucket bullish flips.
- Waiting too long to release hedge will drag rebounds, so the tradeoff is whipsaw protection versus recovery participation.
- The key metric is whether smarter hedge release can improve the original `max_entries=4` total portfolio rather than only helping the more aggressive `dca0.75` branch.

## Outputs
- Plot: `61_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_delay_compare.png`
- Metrics CSV: `61_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_delay_compare.csv`
- Curves CSV: `61_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_delay_compare_curves.csv`
- Report: `61_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_delay_compare.md`