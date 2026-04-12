# 57 Backtest: MaxEntries=4 with DCA 0.75% and RSI Entry Variants

## Setup
- `case1` baseline is the study-56 best CAGR candidate: `max_entries=4`, matched hedge size, `DCA drop = 0.75%`.
- `case2` stays fixed as study-42 case2 curve.
- Variant idea: keep DCA spacing fixed at `0.75%`, but require deeper RSI oversold before taking bullish long entries.

## Results

| Variant | RSI Oversold | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | DCA Signals | Hedge Top-up |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `rsi18_dca0p75` | 18 | 38126.1140 | 104.7073 | 52.2416 | 2.0043 | 110.0459 | 52.7733 | 3843 | 0 |
| `rsi15_dca0p75` | 15 | 28014.3585 | 89.9350 | 50.5773 | 1.7782 | 79.3359 | 57.6666 | 2952 | 0 |
| `rsi14_dca0p75` | 14 | 26804.4358 | 87.9079 | 50.8424 | 1.7290 | 74.3466 | 58.0674 | 2203 | 0 |
| `rsi16_dca0p75` | 16 | 25494.9997 | 85.6344 | 52.1768 | 1.6412 | 68.3927 | 64.4635 | 3505 | 0 |
| `rsi12_dca0p75` | 12 | 24793.3918 | 84.3797 | 51.9358 | 1.6247 | 64.9123 | 62.7025 | 1675 | 0 |

## Best Cases
- Best total CAGR: `rsi18_dca0p75` (`104.7073%`).
- Lowest total MDD: `rsi15_dca0p75` (`50.5773%`).
- Best total Calmar: `rsi18_dca0p75` (`2.0043`).

## Delta vs rsi18_dca0p75
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `rsi18_dca0p75` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `rsi15_dca0p75` | -10111.7555 | -14.7724 | -1.6643 | -0.2261 |
| `rsi14_dca0p75` | -11321.6781 | -16.7995 | -1.3993 | -0.2753 |
| `rsi16_dca0p75` | -12631.1143 | -19.0729 | -0.0648 | -0.3631 |
| `rsi12_dca0p75` | -13332.7222 | -20.3276 | -0.3058 | -0.3796 |

## Dominance Check
- No tested RSI-entry variant achieved both `higher total CAGR` and `lower total MDD` than `rsi18_dca0p75`.

## Interpretation
- If a variant helps, it means the main problem was entering too early on the first bullish oversold signal.
- If CAGR and MDD both improve, waiting for deeper RSI is filtering weak catches without losing the good ones.
- The key metric is whether delayed bullish entry can keep the study-56 CAGR gain while pulling MDD back down.

## Outputs
- Plot: `57_backtest_btcusdt_scale06_adx002_case1_m4_dca075_rsi_open_compare.png`
- Metrics CSV: `57_backtest_btcusdt_scale06_adx002_case1_m4_dca075_rsi_open_compare.csv`
- Curves CSV: `57_backtest_btcusdt_scale06_adx002_case1_m4_dca075_rsi_open_compare_curves.csv`
- Report: `57_backtest_btcusdt_scale06_adx002_case1_m4_dca075_rsi_open_compare.md`