# 00 Study: EMA Distance vs Drawdown (22 baseline scale=0.6)

## Setup
- Strategy base: `22_backtest_btcusdt_dd_scale_entryscale_sweep.py`
- Case: `baseline_es0.6` (`dynamic_dd_scale=False`) with 4h hysteresis + fixed 5x trend hedge
- Data: BTCUSDT 1m + 4h cached data (raw, no extra IQR/jump filtering)
- DD threshold analyzed: `20%`

## Core Metrics
- Final Equity: `46144.2768` USDT
- Total Return: `4514.4277%`
- CAGR: `153.9061%`
- MDD: `77.6838%`
- Trades: `664` (Long `598`, Short `66`)

## EMA Distance vs Drawdown
- Pearson corr (`drawdown_pct`, `ema_below_pct`): `-0.1800`
- Spearman corr (`drawdown_pct`, `ema_below_pct`): `-0.0359`
- Time in DD>=20%: `51.45%`
- Avg EMA-below% when DD>=20: `1.7711`
- Avg EMA-below% when DD<20: `3.9001`
- 90th pct EMA-below% (DD>=20 / DD<20): `5.3146` / `12.3821`

## DD>=20% Episodes
- Episode count: `1129`
- Total duration: `773.04` days
- Longest episode: `ID 1102` (2024-12-19 19:15:00 ~ 2025-11-14 04:38:00, 329.3910 days, max DD 77.6838%)
- Worst DD episode: `ID 1102` (2024-12-19 19:15:00 ~ 2025-11-14 04:38:00, max DD 77.6838%, max EMA-below 18.0550%)

## Threshold Table (ema_below_pct >= threshold)
| Threshold % | Bars | DD>=20 Bars | P(DD>=20 | gap) % | DD>=20 Coverage % | Time Coverage % |
|---:|---:|---:|---:|---:|---:|
| 0.0 | 2162314 | 1112611 | 51.4546 | 100.0000 | 100.0000 |
| 0.5 | 1022318 | 539564 | 52.7785 | 48.4953 | 47.2789 |
| 1.0 | 961955 | 489389 | 50.8744 | 43.9856 | 44.4873 |
| 2.0 | 812644 | 368842 | 45.3879 | 33.1510 | 37.5821 |
| 3.0 | 656955 | 258880 | 39.4060 | 23.2678 | 30.3820 |
| 5.0 | 448081 | 124421 | 27.7675 | 11.1828 | 20.7223 |
| 8.0 | 247818 | 45294 | 18.2771 | 4.0710 | 11.4608 |
| 10.0 | 177816 | 19473 | 10.9512 | 1.7502 | 8.2234 |

## Outputs
- Plot: `00_backtest_btcusdt_ema_distance_dd20_scale06.png`
- Episodes CSV: `00_backtest_btcusdt_ema_distance_dd20_scale06_episodes.csv`
- Threshold CSV: `00_backtest_btcusdt_ema_distance_dd20_scale06_thresholds.csv`