# 25 Backtest: Risk-Score Scaling Case Study (entry_scale=0.6 fixed)

## Why This Study
- `00_1` showed higher DD in short run-length / higher flip / higher near-EMA regimes.
- This study tests how to map that risk score into position scaling, while keeping base entry_scale fixed at `0.6`.

## Risk Score Definition
- score +1 if run_len_4h <= 8
- score +1 if run_len_4h <= 3
- score +1 if flip_count_30_4h >= 2
- score +1 if flip_count_30_4h >= 4
- score +1 if near_ema_ratio_30_4h >= 20
- score +1 if near_ema_ratio_30_4h >= 40

## Case Definitions
| Case | Rule (min score -> scale) | Description |
|---|---|---|
| `baseline_no_scale` | `s>=0:1.00` | No regime scaling |
| `mild_s2_0p90` | `s>=0:1.00, s>=2:0.90` | Reduce lightly at score>=2 |
| `mild_s2_0p85` | `s>=0:1.00, s>=2:0.85` | Reduce lightly at score>=2 (stronger) |
| `two_step_90_75` | `s>=0:1.00, s>=2:0.90, s>=4:0.75` | Two-step mild reduction |
| `two_step_85_65` | `s>=0:1.00, s>=2:0.85, s>=4:0.65` | Two-step medium reduction |
| `high_only_s4_0p70` | `s>=0:1.00, s>=4:0.70` | Scale only in very high-risk regime |
| `aggressive_24_style` | `s>=0:1.00, s>=2:0.50, s>=4:0.25` | Same aggressive style as 24 |

## Metrics
| Case | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Win Rate % | Avg Entry Scale | Entries(<1.0) | Avg Risk Score | Scale Usage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `baseline_no_scale` | 46144.2768 | 4514.4277 | 153.9061 | 77.6838 | 1.9812 | 664 | 92.4699 | 1.0000 | 0 | 0.2457 | `1.00:1819` |
| `high_only_s4_0p70` | 45665.6360 | 4466.5636 | 153.2631 | 77.6838 | 1.9729 | 664 | 92.4699 | 0.9985 | 9 | 0.2457 | `0.70:9|1.00:1810` |
| `mild_s2_0p90` | 45088.8437 | 4408.8844 | 152.4815 | 77.8221 | 1.9594 | 664 | 92.4699 | 0.9936 | 116 | 0.2457 | `0.90:116|1.00:1703` |
| `two_step_90_75` | 44854.3157 | 4385.4316 | 152.1615 | 77.8221 | 1.9552 | 664 | 92.4699 | 0.9929 | 116 | 0.2457 | `0.75:9|0.90:107|1.00:1703` |
| `mild_s2_0p85` | 44558.8069 | 4355.8807 | 151.7565 | 77.8912 | 1.9483 | 664 | 92.4699 | 0.9904 | 116 | 0.2457 | `0.85:116|1.00:1703` |
| `two_step_85_65` | 44249.7627 | 4324.9763 | 151.3308 | 77.8912 | 1.9428 | 664 | 92.4699 | 0.9894 | 116 | 0.2457 | `0.65:9|0.85:107|1.00:1703` |
| `aggressive_24_style` | 40473.7677 | 3947.3768 | 145.9380 | 78.3718 | 1.8621 | 664 | 92.4699 | 0.9669 | 116 | 0.2457 | `0.25:9|0.50:107|1.00:1703` |

## Delta vs Baseline
| Case | Equity Delta | Equity Delta % | MDD Delta %pt | Calmar Delta |
|---|---:|---:|---:|---:|
| `mild_s2_0p90` | -1055.4331 | -2.2872 | 0.1384 | -0.0218 |
| `mild_s2_0p85` | -1585.4699 | -3.4359 | 0.2074 | -0.0329 |
| `two_step_90_75` | -1289.9611 | -2.7955 | 0.1384 | -0.0259 |
| `two_step_85_65` | -1894.5141 | -4.1056 | 0.2074 | -0.0383 |
| `high_only_s4_0p70` | -478.6408 | -1.0373 | 0.0000 | -0.0083 |
| `aggressive_24_style` | -5670.5091 | -12.2887 | 0.6881 | -0.1191 |

## Highlights
- Best Final Equity: `baseline_no_scale` (46144.2768)
- Lowest MDD: `baseline_no_scale` (77.6838%)
- Best Calmar: `baseline_no_scale` (1.9812)

## Outputs
- Plot: `25_backtest_btcusdt_risk_score_scale06_case_study.png`
- Metrics: `25_backtest_btcusdt_risk_score_scale06_case_study.csv`
- Report: `25_backtest_btcusdt_risk_score_scale06_case_study.md`