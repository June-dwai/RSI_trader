# 37 Backtest: 35 Variants (Touch/Reentry Rules)

## Setup
- Base template: study-35 (`scale=0.50`, long-only + trend short hedge, hysteresis 0.5%).
- Case A: baseline 35 logic.
- Case B: same as A but `ema_touch` uses previous confirmed 4h touch only.
- Case C: same as B plus reentry only if `price > 4h EMA200` (long-side gate).

## Results
| Case | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Reentry EMA Blocks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `A_baseline_35` | 5984.1433 | 498.4143 | 54.5070 | 49.5386 | 1.1003 | 430 | 364/66 | 88.3721 | 2.0561 | 0 |
| `B_touch_prev_only` | 6051.8852 | 505.1885 | 54.9305 | 49.5386 | 1.1088 | 430 | 364/66 | 88.3721 | 2.0543 | 0 |
| `C_B_plus_reentry_above_ema` | 4968.6204 | 396.8620 | 47.6752 | 61.5049 | 0.7751 | 409 | 343/66 | 87.7751 | 2.0755 | 117630 |

## Delta vs A (Baseline)
| Case | Final Equity Delta | CAGR Delta (pp) | MDD Delta (pp) | Calmar Delta |
|---|---:|---:|---:|---:|
| `A_baseline_35` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `B_touch_prev_only` | 67.7419 | 0.4235 | 0.0000 | 0.0085 |
| `C_B_plus_reentry_above_ema` | -1015.5229 | -6.8317 | 11.9663 | -0.3251 |

## Outputs
- Plot: `37_backtest_btcusdt_35_touch_reentry_variants.png`
- Metrics CSV: `37_backtest_btcusdt_35_touch_reentry_variants.csv`
- Report: `37_backtest_btcusdt_35_touch_reentry_variants.md`