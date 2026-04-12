# 65 Backtest: MaxEntries=4 Net Exposure Governor Variants

## Setup
- `case1` uses study-51 baseline: `max_entries=4`, matched hedge size, original `dca_drop=0.50%`.
- `case2` stays fixed as study-42 case2 curve.
- Base candidate is `shallow6_else2bull`: wait `2` bullish 4h buckets unless the long is already within `6%` of average entry.
- Governor variants keep that release logic, but if the long is still deeply underwater they only reduce hedge to a target net-long size instead of closing hedge fully.

## Results

| Variant | Bullish Close Bars | Shallow Gap % | Target Net Entries | Governor Gap % | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | Governor Reduce | Governor Close |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `shallow6_else2bull` | 2 | 6.0000 | 4.0000 | 0.0000 | 37042.7061 | 103.2781 | 50.8536 | 2.0309 | 107.3780 | 61.0421 | 0 | 0 |
| `release1bull` | 1 | 0.0000 | 4.0000 | 0.0000 | 35703.7284 | 101.4674 | 50.3387 | 2.0157 | 103.9256 | 64.8802 | 0 | 0 |
| `gov_net2p5_gap3` | 2 | 6.0000 | 2.5000 | 3.0000 | 33028.5116 | 97.6897 | 51.1820 | 1.9087 | 96.4259 | 55.0981 | 23 | 0 |
| `gov_net2p0_gap3` | 2 | 6.0000 | 2.0000 | 3.0000 | 31807.6792 | 95.8884 | 51.3033 | 1.8691 | 92.6852 | 53.3065 | 23 | 0 |
| `gov_net2p0_gap5` | 2 | 6.0000 | 2.0000 | 5.0000 | 31807.6792 | 95.8884 | 51.3033 | 1.8691 | 92.6852 | 53.3065 | 23 | 0 |
| `gov_net1p5_gap5` | 2 | 6.0000 | 1.5000 | 5.0000 | 30643.0996 | 94.1206 | 51.4313 | 1.8300 | 88.8930 | 52.8552 | 23 | 0 |

## Best Cases
- Best total CAGR: `shallow6_else2bull` (`103.2781%`).
- Lowest total MDD: `release1bull` (`50.3387%`).
- Best total Calmar: `shallow6_else2bull` (`2.0309`).

## Delta vs release1bull
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `shallow6_else2bull` | 1338.9777 | 1.8108 | 0.5149 | 0.0152 |
| `release1bull` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `gov_net2p5_gap3` | -2675.2168 | -3.7776 | 0.8433 | -0.1070 |
| `gov_net2p0_gap3` | -3896.0492 | -5.5790 | 0.9645 | -0.1466 |
| `gov_net2p0_gap5` | -3896.0492 | -5.5790 | 0.9645 | -0.1466 |
| `gov_net1p5_gap5` | -5060.6288 | -7.3467 | 1.0925 | -0.1857 |

## Dominance Check
- No tested hedge-release-delay variant achieved both `higher total CAGR` and `lower total MDD` than `release1bull`.

## Interpretation
- If a variant helps, it means the remaining issue after study 62 is not hedge timing alone but over-restoring net-long exposure while still deeply underwater.
- If governor variants fail, it means keeping residual hedge into recovery is choking the same rebound engine that makes case1 profitable.
- The key metric is whether target net exposure can preserve the study-62 CAGR gain while pulling MDD back toward the original baseline.

## Outputs
- Plot: `65_backtest_btcusdt_scale06_adx002_case1_m4_net_exposure_governor_compare.png`
- Metrics CSV: `65_backtest_btcusdt_scale06_adx002_case1_m4_net_exposure_governor_compare.csv`
- Curves CSV: `65_backtest_btcusdt_scale06_adx002_case1_m4_net_exposure_governor_compare_curves.csv`
- Report: `65_backtest_btcusdt_scale06_adx002_case1_m4_net_exposure_governor_compare.md`