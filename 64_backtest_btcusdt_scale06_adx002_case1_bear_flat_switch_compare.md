# 64 Backtest: Bear-Flat Regime Switch Variants

## Setup
- Baseline row is study-51 `case1 max_entries=4` with matched hedge and original lower-price DCA path.
- `case2` stays fixed as study-42 case2 curve.
- Structural rows force `flat` on confirmed bearish 4h regime, then re-arm long entries only after the configured number of confirmed bullish 4h buckets.
- No lookahead rule: regime transitions use the already-confirmed previous 4h bucket only, applied at the next 1-minute bar.

## Results

| Variant | Mode | Rearm Bull Bars | Rearm Open Scale | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | Bear Flat | Rearm Open | Blocked Signals |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline_m4` | `baseline` | 0 | 0.0000 | 35703.7284 | 101.4674 | 50.3387 | 2.0157 | 103.9256 | 64.8802 | 0 | 0 | 0 |
| `bearflat_wait2bull` | `structural` | 2 | 0.0000 | 20021.8387 | 75.0458 | 55.0270 | 1.3638 | 31.1705 | 51.6701 | 57 | 0 | 354 |
| `bearflat_wait1bull` | `structural` | 1 | 0.0000 | 19974.7306 | 74.9456 | 55.0270 | 1.3620 | 30.6753 | 52.1760 | 57 | 0 | 258 |
| `bearflat_pilot20_wait1bull` | `structural` | 1 | 20.0000 | 19354.2981 | 73.6091 | 55.3118 | 1.3308 | 23.5288 | 53.8343 | 64 | 66 | 258 |
| `bearflat_pilot15_wait2bull` | `structural` | 2 | 15.0000 | 19414.0304 | 73.7392 | 56.3439 | 1.3087 | 24.2743 | 52.2661 | 60 | 63 | 354 |

## Best Cases
- Best total CAGR: `baseline_m4` (`101.4674%`).
- Lowest total MDD: `baseline_m4` (`50.3387%`).
- Best total Calmar: `baseline_m4` (`2.0157`).

## Delta vs baseline_m4
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `baseline_m4` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `bearflat_wait2bull` | -15681.8897 | -26.4216 | 4.6883 | -0.6519 |
| `bearflat_wait1bull` | -15728.9978 | -26.5218 | 4.6883 | -0.6537 |
| `bearflat_pilot20_wait1bull` | -16349.4303 | -27.8582 | 4.9730 | -0.6849 |
| `bearflat_pilot15_wait2bull` | -16289.6980 | -27.7282 | 6.0052 | -0.7070 |

## Dominance Check
- No tested bear-flat variant achieved both `higher total CAGR` and `lower total MDD` than `baseline_m4`.

## Interpretation
- If a structural row helps, it means the biggest problem was holding long inventory through confirmed bearish regimes, not just hedge release timing.
- If a structural row fails badly, it means the strategy needs bearish-period participation rather than bearish-period avoidance, so the next rewrite should be breakout-short or net-exposure overlay instead of flat.
- The key metric is whether bearish flat-switching can compress drawdown without destroying too much of the long-side CAGR engine.

## Outputs
- Plot: `64_backtest_btcusdt_scale06_adx002_case1_bear_flat_switch_compare.png`
- Metrics CSV: `64_backtest_btcusdt_scale06_adx002_case1_bear_flat_switch_compare.csv`
- Curves CSV: `64_backtest_btcusdt_scale06_adx002_case1_bear_flat_switch_compare_curves.csv`
- Report: `64_backtest_btcusdt_scale06_adx002_case1_bear_flat_switch_compare.md`