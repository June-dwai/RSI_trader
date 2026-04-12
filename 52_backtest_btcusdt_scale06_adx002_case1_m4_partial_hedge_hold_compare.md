# 52 Backtest: MaxEntries=4 Partial Hedge Hold Variants

## Setup
- `case1` baseline is study-51 candidate: `max_entries=4`, matched hedge size.
- `case2` stays fixed as study-42 case2 curve.
- Variant idea: on bullish hedge-close signal, keep part of the hedge only when the long is still full-size and underwater beyond the selected gap threshold.

## Results

| Variant | Retain Fraction | Stress Gap % | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | Hedge Reduce | Hedge Top-up | Bullish Hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline_close_all` | 0.0000 | 0.0000 | 35703.7284 | 101.4674 | 50.3387 | 2.0157 | 103.9256 | 64.8802 | 0 | 0 | 0 |
| `hold10_gap5pct` | 10.0000 | 5.0000 | 34104.3625 | 99.2358 | 50.3534 | 1.9708 | 99.5479 | 63.3223 | 34 | 17 | 34 |
| `hold10_gap3pct` | 10.0000 | 3.0000 | 33554.5537 | 98.4504 | 50.2562 | 1.9590 | 97.9716 | 63.1395 | 43 | 23 | 43 |
| `hold15_gap5pct` | 15.0000 | 5.0000 | 33342.6942 | 98.1451 | 50.3608 | 1.9488 | 97.3536 | 62.5661 | 34 | 17 | 34 |
| `hold20_gap5pct` | 20.0000 | 5.0000 | 32605.6134 | 97.0715 | 50.5403 | 1.9207 | 95.1553 | 61.8250 | 34 | 17 | 34 |
| `hold25_gap3pct` | 25.0000 | 3.0000 | 30716.9011 | 94.2342 | 50.9080 | 1.8511 | 89.1404 | 60.6035 | 43 | 23 | 43 |
| `hold25_gap1pct` | 25.0000 | 1.0000 | 30489.6097 | 93.8839 | 51.4509 | 1.8247 | 88.3752 | 59.6430 | 52 | 32 | 52 |
| `hold25_gap2pct` | 25.0000 | 2.0000 | 29724.8454 | 92.6906 | 51.1324 | 1.8128 | 85.7266 | 60.9566 | 45 | 25 | 45 |
| `hold50_gap3pct` | 50.0000 | 3.0000 | 26879.8546 | 88.0362 | 51.9654 | 1.6941 | 74.6708 | 56.8267 | 43 | 23 | 43 |

## Best Cases
- Best total CAGR: `baseline_close_all` (`101.4674%`).
- Lowest total MDD: `hold10_gap3pct` (`50.2562%`).
- Best total Calmar: `baseline_close_all` (`2.0157`).

## Delta vs baseline_close_all
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `baseline_close_all` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `hold10_gap5pct` | -1599.3659 | -2.2316 | 0.0147 | -0.0449 |
| `hold10_gap3pct` | -2149.1747 | -3.0170 | -0.0826 | -0.0567 |
| `hold15_gap5pct` | -2361.0342 | -3.3222 | 0.0221 | -0.0669 |
| `hold20_gap5pct` | -3098.1150 | -4.3958 | 0.2016 | -0.0950 |
| `hold25_gap3pct` | -4986.8273 | -7.2332 | 0.5693 | -0.1646 |
| `hold25_gap1pct` | -5214.1187 | -7.5835 | 1.1122 | -0.1910 |
| `hold25_gap2pct` | -5978.8830 | -8.7768 | 0.7936 | -0.2029 |
| `hold50_gap3pct` | -8823.8738 | -13.4311 | 1.6266 | -0.3216 |

## Dominance Check
- No tested partial-hold variant achieved both `higher total CAGR` and `lower total MDD` than `baseline_close_all`.

## Interpretation
- Mild residual hedge can help only if it protects deep stress without choking rebounds too early.
- Stronger residual hedge is expected to cut drawdown but can reduce CAGR if it stays on through recovery.
- The key metric is whether any variant improves both total CAGR and total MDD over the `max_entries=4` baseline.

## Outputs
- Plot: `52_backtest_btcusdt_scale06_adx002_case1_m4_partial_hedge_hold_compare.png`
- Metrics CSV: `52_backtest_btcusdt_scale06_adx002_case1_m4_partial_hedge_hold_compare.csv`
- Curves CSV: `52_backtest_btcusdt_scale06_adx002_case1_m4_partial_hedge_hold_compare_curves.csv`
- Report: `52_backtest_btcusdt_scale06_adx002_case1_m4_partial_hedge_hold_compare.md`