# 59 Backtest: DCA 0.75% with Add Cooldown Variants

## Setup
- `case1` keeps study-56 best add spacing: `max_entries=4`, matched hedge size, `dca_drop=0.75%`.
- `case2` stays fixed as study-42 case2 curve.
- Variant idea: keep the same price trigger for adds, but require extra time between long add events so full size cannot be built too quickly during one selloff.

## Results

| Variant | Add Cooldown Bars | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | DCA Signals | DCA Blocked | Hedge Top-up |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline_cool0` | 0 | 38126.1140 | 104.7073 | 52.2416 | 2.0043 | 110.0459 | 52.7733 | 3843 | 0 | 0 |
| `addcool30` | 30 | 36870.9451 | 103.0486 | 53.5070 | 1.9259 | 106.9450 | 53.1441 | 3750 | 254 | 0 |
| `addcool120` | 120 | 22556.2086 | 80.1904 | 52.3146 | 1.5329 | 51.9435 | 53.1441 | 6492 | 493 | 0 |
| `addcool60` | 60 | 23554.6135 | 82.0972 | 53.9046 | 1.5230 | 58.1423 | 53.1441 | 6617 | 272 | 0 |
| `addcool240` | 240 | 19583.1590 | 74.1058 | 54.0857 | 1.3702 | 26.3129 | 63.1213 | 7092 | 951 | 0 |

## Best Cases
- Best total CAGR: `baseline_cool0` (`104.7073%`).
- Lowest total MDD: `baseline_cool0` (`52.2416%`).
- Best total Calmar: `baseline_cool0` (`2.0043`).

## Delta vs baseline_cool0
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `baseline_cool0` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `addcool30` | -1255.1689 | -1.6587 | 1.2654 | -0.0784 |
| `addcool120` | -15569.9053 | -24.5169 | 0.0729 | -0.4714 |
| `addcool60` | -14571.5005 | -22.6102 | 1.6630 | -0.4813 |
| `addcool240` | -18542.9550 | -30.6015 | 1.8441 | -0.6341 |

## Dominance Check
- No tested add-cooldown variant achieved both `higher total CAGR` and `lower total MDD` than `baseline_cool0`.

## Interpretation
- If a variant helps, it means position size is building too quickly in clock time, not just at the wrong price gaps.
- Add cooldown is a softer structural brake than hard DCA blocking because it delays clustering without deleting the add path entirely.
- The key metric is whether slower inventory pacing can keep the study-56 CAGR gain while reducing total MDD.

## Outputs
- Plot: `59_backtest_btcusdt_scale06_adx002_case1_m4_dca075_add_cooldown_compare.png`
- Metrics CSV: `59_backtest_btcusdt_scale06_adx002_case1_m4_dca075_add_cooldown_compare.csv`
- Curves CSV: `59_backtest_btcusdt_scale06_adx002_case1_m4_dca075_add_cooldown_compare_curves.csv`
- Report: `59_backtest_btcusdt_scale06_adx002_case1_m4_dca075_add_cooldown_compare.md`