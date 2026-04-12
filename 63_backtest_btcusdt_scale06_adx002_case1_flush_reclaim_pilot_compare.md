# 63 Backtest: Flush/Reclaim Pilot Entry + Winner Pyramid Variants

## Setup
- Baseline row is study-51 `case1 max_entries=4` with matched hedge and original lower-price DCA path.
- `case2` stays fixed as study-42 case2 curve.
- Structural rows replace loser averaging with: `flush -> reclaim -> pilot fill`, then `winner pyramid` adds, plus `hard stop without lower reentry`.
- No lookahead rule: structural setup state uses only sequential 1-minute `close` observations. It does not infer low-before-high order inside the same bar.

## Results

| Variant | Mode | Flush % | Reclaim % | Pilot Scale | Pyramid Step % | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | Setups Filled | Pyramid Adds | Hard Stops |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline_m4` | `baseline` | 0.0000 | 0.0000 | 60.0000 | 0.0000 | 35703.7284 | 101.4674 | 50.3387 | 2.0157 | 103.9256 | 64.8802 | 0 | 0 | 0 |
| `flush1p00_reclaim0p25_p15_step0p75` | `structural` | 1.0000 | 0.2500 | 15.0000 | 0.7500 | 18358.2139 | 71.3940 | 52.4421 | 1.3614 | 8.3048 | 27.2097 | 312 | 460 | 115 |
| `flush0p75_reclaim0p25_p20_step0p75` | `structural` | 0.7500 | 0.2500 | 20.0000 | 0.7500 | 18418.0098 | 71.5295 | 52.6268 | 1.3592 | 9.4212 | 39.0174 | 375 | 548 | 144 |
| `flush0p75_reclaim0p25_p15_step0p75` | `structural` | 0.7500 | 0.2500 | 15.0000 | 0.7500 | 18316.0883 | 71.2983 | 52.5357 | 1.3571 | 7.4963 | 30.6608 | 375 | 548 | 144 |
| `flush1p00_reclaim0p50_p15_step1p00` | `structural` | 1.0000 | 0.5000 | 15.0000 | 1.0000 | 18271.3296 | 71.1965 | 52.6630 | 1.3519 | 6.6160 | 30.2651 | 294 | 232 | 100 |

## Best Cases
- Best total CAGR: `baseline_m4` (`101.4674%`).
- Lowest total MDD: `baseline_m4` (`50.3387%`).
- Best total Calmar: `baseline_m4` (`2.0157`).

## Delta vs baseline_m4
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `baseline_m4` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `flush1p00_reclaim0p25_p15_step0p75` | -17345.5145 | -30.0734 | 2.1034 | -0.6543 |
| `flush0p75_reclaim0p25_p20_step0p75` | -17285.7186 | -29.9379 | 2.2881 | -0.6565 |
| `flush0p75_reclaim0p25_p15_step0p75` | -17387.6401 | -30.1690 | 2.1970 | -0.6586 |
| `flush1p00_reclaim0p50_p15_step1p00` | -17432.3988 | -30.2709 | 2.3243 | -0.6638 |

## Dominance Check
- No tested structural variant achieved both `higher total CAGR` and `lower total MDD` than `baseline_m4`.

## Interpretation
- If a structural row helps, it means the main damage came from building size into weakness rather than from the long idea itself.
- If a structural row fails badly, it means this market still needs loser-side inventory accumulation to monetize rebounds, so a full rewrite must pair entry logic with a new hedge/allocator layer.
- The key metric is whether `flush/reclaim + pilot fill` moves the frontier, not just whether it lowers MDD by destroying exposure.

## Outputs
- Plot: `63_backtest_btcusdt_scale06_adx002_case1_flush_reclaim_pilot_compare.png`
- Metrics CSV: `63_backtest_btcusdt_scale06_adx002_case1_flush_reclaim_pilot_compare.csv`
- Curves CSV: `63_backtest_btcusdt_scale06_adx002_case1_flush_reclaim_pilot_compare_curves.csv`
- Report: `63_backtest_btcusdt_scale06_adx002_case1_flush_reclaim_pilot_compare.md`