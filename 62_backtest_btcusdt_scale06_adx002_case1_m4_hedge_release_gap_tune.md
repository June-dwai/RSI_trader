# 62 Backtest: MaxEntries=4 Hedge Release Gap Tuning

## Setup
- `case1` uses study-51 baseline: `max_entries=4`, matched hedge size, original `dca_drop=0.50%`.
- `case2` stays fixed as study-42 case2 curve.
- Variant idea: use the best 61-structure (`2 bullish bars unless the long is only shallowly underwater`) and tune the shallow-release gap itself.

## Results

| Variant | Bullish Close Bars | Shallow Gap % | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | Bullish Hold | Early Release |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `shallow6_else2bull` | 2 | 6.0000 | 37042.7061 | 103.2781 | 50.8536 | 2.0309 | 107.3780 | 61.0421 | 35 | 32 |
| `shallow5_else2bull` | 2 | 5.0000 | 36753.7386 | 102.8916 | 50.8650 | 2.0228 | 106.6480 | 60.4496 | 42 | 26 |
| `release1bull` | 1 | 0.0000 | 35703.7284 | 101.4674 | 50.3387 | 2.0157 | 103.9256 | 64.8802 | 0 | 0 |
| `shallow7_else2bull` | 2 | 7.0000 | 35675.0926 | 101.4281 | 50.8536 | 1.9945 | 103.8498 | 64.3334 | 28 | 38 |
| `shallow4_else2bull` | 2 | 4.0000 | 34624.9977 | 99.9708 | 51.4048 | 1.9448 | 101.0057 | 60.4496 | 48 | 21 |

## Best Cases
- Best total CAGR: `shallow6_else2bull` (`103.2781%`).
- Lowest total MDD: `release1bull` (`50.3387%`).
- Best total Calmar: `shallow6_else2bull` (`2.0309`).

## Delta vs release1bull
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `shallow6_else2bull` | 1338.9777 | 1.8108 | 0.5149 | 0.0152 |
| `shallow5_else2bull` | 1050.0102 | 1.4242 | 0.5262 | 0.0071 |
| `release1bull` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `shallow7_else2bull` | -28.6358 | -0.0393 | 0.5149 | -0.0212 |
| `shallow4_else2bull` | -1078.7307 | -1.4966 | 1.0661 | -0.0709 |

## Dominance Check
- No tested hedge-release-delay variant achieved both `higher total CAGR` and `lower total MDD` than `release1bull`.

## Interpretation
- If a variant helps, it means hedge losses were being realized too early on single-bucket bullish flips.
- Waiting too long to release hedge will drag rebounds, so the tradeoff is whipsaw protection versus recovery participation.
- The key metric is whether there is a shallow-gap sweet spot that preserves the 61 CAGR gain without giving back total MDD.

## Outputs
- Plot: `62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune.png`
- Metrics CSV: `62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune.csv`
- Curves CSV: `62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune_curves.csv`
- Report: `62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune.md`