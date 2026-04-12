# 55 Backtest: MaxEntries=4 Partial Stress DCA Size Variants

## Setup
- `case1` baseline is study-51 candidate: `max_entries=4`, matched hedge size.
- `case2` stays fixed as study-42 case2 curve.
- Variant idea: keep `OPEN` and `REENTRY` intact, but scale down `LONG DCA` size when the position is already stressed under bearish or crash-like conditions.

## Results

| Variant | Mode | Min Bear Run 4h | Min Entry Count | Stress Gap % | Stress Add % | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | Scaled DCA | Brake Hits |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline_m4` | `none` | 0 | 99 | 0.0000 | 100.0000 | 35703.7284 | 101.4674 | 50.3387 | 2.0157 | 103.9256 | 64.8802 | 0 | 0 |
| `bear4_entry3_gap0_add50` | `bear_run` | 4 | 3 | 0.0000 | 50.0000 | 33366.7395 | 98.1798 | 50.3297 | 1.9507 | 97.4241 | 65.9557 | 258 | 258 |
| `bear4_entry3_gap0_add25` | `bear_run` | 4 | 3 | 0.0000 | 25.0000 | 33366.7395 | 98.1798 | 50.3297 | 1.9507 | 97.4241 | 65.9557 | 258 | 258 |
| `risk4_entry2_gap0_add50` | `risk` | 0 | 2 | 0.0000 | 50.0000 | 33366.7395 | 98.1798 | 50.3297 | 1.9507 | 97.4241 | 65.9557 | 125 | 125 |
| `risk4_entry3_gap1_add50` | `risk` | 0 | 3 | 1.0000 | 50.0000 | 33366.7395 | 98.1798 | 50.3297 | 1.9507 | 97.4241 | 65.9557 | 125 | 125 |

## Best Cases
- Best total CAGR: `baseline_m4` (`101.4674%`).
- Lowest total MDD: `bear4_entry3_gap0_add50` (`50.3297%`).
- Best total Calmar: `baseline_m4` (`2.0157`).

## Delta vs baseline_m4
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `baseline_m4` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `bear4_entry3_gap0_add50` | -2336.9889 | -3.2875 | -0.0090 | -0.0650 |
| `bear4_entry3_gap0_add25` | -2336.9889 | -3.2875 | -0.0090 | -0.0650 |
| `risk4_entry2_gap0_add50` | -2336.9889 | -3.2875 | -0.0090 | -0.0650 |
| `risk4_entry3_gap1_add50` | -2336.9889 | -3.2875 | -0.0090 | -0.0650 |

## Dominance Check
- No tested partial-size variant achieved both `higher total CAGR` and `lower total MDD` than `baseline_m4`.

## Interpretation
- If a variant helps, it means the real problem was the size of the stressed final add, not the existence of the add path itself.
- If CAGR falls more than MDD improves, even partial scaling is still too blunt or triggers too early.
- The key test is whether reducing stressed long add size can improve both CAGR and MDD over the study-51 baseline.

## Outputs
- Plot: `55_backtest_btcusdt_scale06_adx002_case1_m4_partial_dca_size_compare.png`
- Metrics CSV: `55_backtest_btcusdt_scale06_adx002_case1_m4_partial_dca_size_compare.csv`
- Curves CSV: `55_backtest_btcusdt_scale06_adx002_case1_m4_partial_dca_size_compare_curves.csv`
- Report: `55_backtest_btcusdt_scale06_adx002_case1_m4_partial_dca_size_compare.md`