# 56 Backtest: MaxEntries=4 DCA Spacing Variants

## Setup
- `case1` baseline is study-51 candidate: `max_entries=4`, matched hedge size.
- `case2` stays fixed as study-42 case2 curve.
- Variant idea: keep hedge behavior unchanged, but widen the required drop between long adds so the strategy does not reach full size too quickly.

## Results

| Variant | DCA Drop % | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | DCA Signals | Hedge Top-up |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline_drop0p50` | 0.5000 | 35703.7284 | 101.4674 | 50.3387 | 2.0157 | 103.9256 | 64.8802 | 5408 | 0 |
| `dca_drop0p75` | 0.7500 | 38126.1140 | 104.7073 | 52.2416 | 2.0043 | 110.0459 | 52.7733 | 3843 | 0 |
| `dca_drop1p25` | 1.2500 | 24732.2596 | 84.2691 | 50.9962 | 1.6525 | 64.5980 | 63.8132 | 3022 | 0 |
| `dca_drop1p50` | 1.5000 | 23958.4569 | 82.8511 | 50.5411 | 1.6393 | 60.4480 | 48.6860 | 2215 | 0 |
| `dca_drop1p00` | 1.0000 | 22345.1823 | 79.7793 | 52.2611 | 1.5266 | 50.5274 | 64.8581 | 6255 | 0 |

## Best Cases
- Best total CAGR: `dca_drop0p75` (`104.7073%`).
- Lowest total MDD: `baseline_drop0p50` (`50.3387%`).
- Best total Calmar: `baseline_drop0p50` (`2.0157`).

## Delta vs baseline_drop0p50
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `baseline_drop0p50` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `dca_drop0p75` | 2422.3856 | 3.2400 | 1.9029 | -0.0114 |
| `dca_drop1p25` | -10971.4688 | -17.1982 | 0.6574 | -0.3632 |
| `dca_drop1p50` | -11745.2715 | -18.6163 | 0.2023 | -0.3764 |
| `dca_drop1p00` | -13358.5461 | -21.6881 | 1.9224 | -0.4891 |

## Dominance Check
- No tested DCA-spacing variant achieved both `higher total CAGR` and `lower total MDD` than `baseline_drop0p50`.

## Interpretation
- If a variant helps, it means the main problem was reaching full size too fast rather than the existence of the add path itself.
- If CAGR improves while MDD also improves, deeper spacing is buying better average prices without killing too many rebounds.
- The key metric is whether wider DCA spacing improves both total CAGR and total MDD over the `max_entries=4` baseline.

## Outputs
- Plot: `56_backtest_btcusdt_scale06_adx002_case1_m4_dca_spacing_compare.png`
- Metrics CSV: `56_backtest_btcusdt_scale06_adx002_case1_m4_dca_spacing_compare.csv`
- Curves CSV: `56_backtest_btcusdt_scale06_adx002_case1_m4_dca_spacing_compare_curves.csv`
- Report: `56_backtest_btcusdt_scale06_adx002_case1_m4_dca_spacing_compare.md`