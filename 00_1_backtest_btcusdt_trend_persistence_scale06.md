# 00_1 Study: Trend Persistence / Choppiness vs DD

## Setup
- Base strategy/case: `22` baseline with `entry_scale=0.6` (no DD scaling)
- Regime features from confirmed 4h EMA200 + hysteresis trend (`0.5%`)
- DD threshold for highlighting: `20%`

## Core Metrics
- Final Equity: `46144.2768` USDT
- MDD: `77.6838%`
- Trades: `664` (Long `598`, Short `66`)

## Regime Correlations (Spearman)
- Drawdown vs active run length (4h bars): `-0.4723`
- Drawdown vs flip count (last 30x4h): `0.3423`
- Drawdown vs near-EMA ratio (last 30x4h): `0.3375`

## DD>=20 vs DD<20 Conditioned Means
- Time in DD>=20: `51.4546`%
- Avg run len (DD>=20 / DD<20): `62.4545` / `168.0091`
- Avg flip count (DD>=20 / DD<20): `0.6796` / `0.1842`
- Avg near-EMA ratio (DD>=20 / DD<20): `7.5769` / `2.0524`

## DD>=20 Episodes (4h aggregated)
- Episode count: `78`
- Longest: `ID 78` (2024-12-19 16:00:00 ~ 2025-11-14 00:00:00, 329.3333 days)
- Worst DD: `ID 78` (max DD `76.4385%`, avg run len `76.9108`, avg flip `0.6542`)

## Regime Bucket Stats
| Dimension | Bucket | Bars | DD>=20 Rate % | Avg DD % | P90 DD % | Avg Run Len | Avg Flip(30x4h) | Avg Near EMA % |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| run_bin | run_1_3 | 89520 | 85.1597 | 34.2039 | 55.2610 | 1.9598 | 1.7882 | 13.4138 |
| run_bin | run_4_8 | 121440 | 81.6033 | 32.6557 | 52.2858 | 5.9091 | 1.7095 | 14.0580 |
| run_bin | run_9_16 | 167280 | 74.6335 | 31.2264 | 50.5273 | 12.4161 | 1.5567 | 13.2233 |
| run_bin | run_17_plus | 1784074 | 45.5379 | 21.2965 | 43.0305 | 136.1363 | 0.1802 | 3.0630 |
| flip_bin | flip_0_1 | 1931433 | 47.6705 | 21.8061 | 43.6975 | 125.9352 | 0.2020 | 3.9783 |
| flip_bin | flip_2_3 | 218401 | 82.1457 | 34.2565 | 55.2610 | 11.6660 | 2.3011 | 11.9048 |
| flip_bin | flip_4_5 | 10800 | 100.0000 | 49.9480 | 64.0237 | 5.3111 | 4.3333 | 21.7778 |
| flip_bin | flip_6_plus | 1680 | 100.0000 | 64.0237 | 64.0237 | 4.0000 | 6.0000 | 39.0476 |
| near_ema_bin | near_0_20 | 2016802 | 49.3978 | 22.4916 | 46.5657 | 119.3031 | 0.3785 | 2.4381 |
| near_ema_bin | near_20_40 | 99826 | 77.8424 | 34.9119 | 69.5606 | 31.0098 | 1.5459 | 30.2470 |
| near_ema_bin | near_40_60 | 35040 | 79.9572 | 30.2895 | 43.0305 | 49.6575 | 0.7329 | 51.2100 |
| near_ema_bin | near_60_100 | 10646 | 99.8591 | 31.7619 | 37.2116 | 37.6568 | 0.5751 | 80.1710 |

## Outputs
- Plot: `00_1_backtest_btcusdt_trend_persistence_scale06.png`
- Episodes: `00_1_backtest_btcusdt_trend_persistence_scale06_episodes.csv`
- Regime stats: `00_1_backtest_btcusdt_trend_persistence_scale06_regime_stats.csv`