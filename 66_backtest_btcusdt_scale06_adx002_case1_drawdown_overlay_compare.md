# 66 Backtest: Case1 Drawdown Overlay Variants

## Setup
- Baseline reference is `release1bull` from study 62.
- Overlay source is `shallow6_else2bull` from study 62, which had the best total Calmar among the pure case1 logic variants.
- Overlay rule uses only lagged case1 drawdown from the source curve. If case1 drawdown breaches the trigger, the next-minute case1 exposure is reduced to the configured weight until drawdown recovers below the restore level.
- `case2` remains fully invested and unchanged.

## Results

| Variant | Mode | Trigger DD % | Restore DD % | Reduced Weight | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `shallow6_no_overlay` | `source_shallow6` | 0.0000 | 0.0000 | 100.0000 | 37042.7061 | 103.2781 | 50.8536 | 2.0309 |
| `release1bull_baseline` | `baseline_release1` | 0.0000 | 0.0000 | 100.0000 | 35703.7284 | 101.4674 | 50.3387 | 2.0157 |
| `dd15_to75_restore10` | `overlay` | 15.0000 | 10.0000 | 75.0000 | 28262.3389 | 90.3422 | 48.7829 | 1.8519 |
| `dd25_to50_restore15` | `overlay` | 25.0000 | 15.0000 | 50.0000 | 24614.2278 | 84.0550 | 51.1729 | 1.6426 |
| `dd30_to25_restore20` | `overlay` | 30.0000 | 20.0000 | 25.0000 | 22407.0893 | 79.9002 | 49.3614 | 1.6187 |
| `dd20_to50_restore12` | `overlay` | 20.0000 | 12.0000 | 50.0000 | 22360.4272 | 79.8091 | 51.7952 | 1.5409 |

## Best Cases
- Best total CAGR: `shallow6_no_overlay` (`103.2781%`).
- Lowest total MDD: `dd15_to75_restore10` (`48.7829%`).
- Best total Calmar: `shallow6_no_overlay` (`2.0309`).

## Delta vs release1bull_baseline
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `shallow6_no_overlay` | 1338.9777 | 1.8108 | 0.5149 | 0.0152 |
| `release1bull_baseline` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `dd15_to75_restore10` | -7441.3895 | -11.1251 | -1.5558 | -0.1638 |
| `dd25_to50_restore15` | -11089.5006 | -17.4123 | 0.8342 | -0.3731 |
| `dd30_to25_restore20` | -13296.6391 | -21.5672 | -0.9773 | -0.3970 |
| `dd20_to50_restore12` | -13343.3012 | -21.6583 | 1.4565 | -0.4748 |

## Dominance Check
- No tested overlay achieved both `higher total CAGR` and `lower total MDD` than `release1bull_baseline`.

## Interpretation
- If an overlay helps, it means the alpha engine is still useful but should not be fully invested through its own deep drawdowns.
- If all overlays fail, then the remaining problem is not allocation but the underlying case1 alpha quality under stress.

## Outputs
- Plot: `66_backtest_btcusdt_scale06_adx002_case1_drawdown_overlay_compare.png`
- Metrics CSV: `66_backtest_btcusdt_scale06_adx002_case1_drawdown_overlay_compare.csv`
- Curves CSV: `66_backtest_btcusdt_scale06_adx002_case1_drawdown_overlay_compare_curves.csv`
- Report: `66_backtest_btcusdt_scale06_adx002_case1_drawdown_overlay_compare.md`