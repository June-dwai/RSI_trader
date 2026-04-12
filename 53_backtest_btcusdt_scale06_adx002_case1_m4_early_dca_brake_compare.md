# 53 Backtest: MaxEntries=4 Early Long DCA Brake Variants

## Setup
- `case1` baseline is study-51 candidate: `max_entries=4`, matched hedge size.
- `case2` stays fixed as study-42 case2 curve.
- Variant idea: keep `OPEN`/reverse logic intact, but block only `LONG DCA/REENTRY` when the position is already stressed under bearish or crash-like conditions.

## Results

| Variant | Mode | Min Bear Run 4h | Min Entry Count | Stress Gap % | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | Blocked DCA | Blocked Reentry | Brake Active Bars |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline_m4` | `none` | 0 | 99 | 0.0000 | 35703.7284 | 101.4674 | 50.3387 | 2.0157 | 103.9256 | 64.8802 | 0 | 0 | 0 |
| `bear4_entry3_gap0` | `bear_run` | 4 | 3 | 0.0000 | 33366.7395 | 98.1798 | 50.3297 | 1.9507 | 97.4241 | 65.9557 | 258 | 456122 | 456380 |
| `bear6_entry3_gap1` | `bear_run` | 6 | 3 | 1.0000 | 33366.7395 | 98.1798 | 50.3297 | 1.9507 | 97.4241 | 65.9557 | 258 | 443069 | 443327 |
| `risk4_entry2_gap0` | `risk` | 0 | 2 | 0.0000 | 33265.0445 | 98.0329 | 50.3297 | 1.9478 | 97.1256 | 65.9557 | 125 | 164096 | 164221 |
| `risk4_entry3_gap1` | `risk` | 0 | 3 | 1.0000 | 33265.0445 | 98.0329 | 50.3297 | 1.9478 | 97.1256 | 65.9557 | 125 | 158500 | 158625 |
| `bear2_entry2_gap0` | `bear_run` | 2 | 2 | 0.0000 | 32841.0063 | 97.4164 | 50.3297 | 1.9356 | 95.8657 | 65.9557 | 258 | 499234 | 499492 |
| `bear4_entry2_gap0` | `bear_run` | 4 | 2 | 0.0000 | 32841.0063 | 97.4164 | 50.3297 | 1.9356 | 95.8657 | 65.9557 | 258 | 457449 | 457707 |
| `bear6_entry2_gap0` | `bear_run` | 6 | 2 | 0.0000 | 32841.0063 | 97.4164 | 50.3297 | 1.9356 | 95.8657 | 65.9557 | 258 | 444396 | 444654 |

## Best Cases
- Best total CAGR: `baseline_m4` (`101.4674%`).
- Lowest total MDD: `bear4_entry3_gap0` (`50.3297%`).
- Best total Calmar: `baseline_m4` (`2.0157`).

## Delta vs baseline_m4
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `baseline_m4` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `bear4_entry3_gap0` | -2336.9889 | -3.2875 | -0.0090 | -0.0650 |
| `bear6_entry3_gap1` | -2336.9889 | -3.2875 | -0.0090 | -0.0650 |
| `risk4_entry2_gap0` | -2438.6839 | -3.4345 | -0.0090 | -0.0679 |
| `risk4_entry3_gap1` | -2438.6839 | -3.4345 | -0.0090 | -0.0679 |
| `bear2_entry2_gap0` | -2862.7221 | -4.0510 | -0.0090 | -0.0801 |
| `bear4_entry2_gap0` | -2862.7221 | -4.0510 | -0.0090 | -0.0801 |
| `bear6_entry2_gap0` | -2862.7221 | -4.0510 | -0.0090 | -0.0801 |

## Dominance Check
- No tested early-brake variant achieved both `higher total CAGR` and `lower total MDD` than `baseline_m4`.

## Interpretation
- If a variant helps, it means the real problem was long inventory build-up rather than hedge-close timing.
- If CAGR falls more than MDD improves, the brake is firing too early and is cutting profitable averaging paths.
- The key test is whether narrowing the intervention to stressed long adds can improve both CAGR and MDD over the study-51 baseline.

## Outputs
- Plot: `53_backtest_btcusdt_scale06_adx002_case1_m4_early_dca_brake_compare.png`
- Metrics CSV: `53_backtest_btcusdt_scale06_adx002_case1_m4_early_dca_brake_compare.csv`
- Curves CSV: `53_backtest_btcusdt_scale06_adx002_case1_m4_early_dca_brake_compare_curves.csv`
- Report: `53_backtest_btcusdt_scale06_adx002_case1_m4_early_dca_brake_compare.md`