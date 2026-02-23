# 00_2 Study: EMA Order State + Risk Line vs DD

## Setup
- Base strategy/case: `22` baseline with `entry_scale=0.6` (no DD scaling)
- 4h EMA order state: `1` ordered bull (`16>50>99>200`), `0` mixed, `-1` ordered bear
- Risk line: `highest high(12) - 2.2 * ATR(14)` on 4h confirmed bars
- Shading in chart: only `EMA order state == 0` (mixed)
- DD threshold reference: `20%`

## Core Metrics
- Final Equity: `46144.2768` USDT
- MDD: `77.6838%`
- Trades: `664` (Long `598`, Short `66`)

## Regime Correlations (Spearman)
- Drawdown vs EMA order state (1/0/-1): `-0.0998`
- Drawdown vs mixed flag (state==0): `0.2243`
- Drawdown vs risk gap %: `-0.1319`
- Drawdown vs retrace from recent high %: `-0.0254`

## DD>=20 vs DD<20 Conditioned Means
- Time in DD>=20: `51.4546`%
- Avg EMA state (DD>=20 / DD<20): `-0.0364` / `0.0682`
- Mixed ratio % (DD>=20 / DD<20): `44.1614` / `24.5548`
- Risk breach ratio % (DD>=20 / DD<20): `32.6521` / `26.7574`
- Long-trap risk ratio % (DD>=20 / DD<20): `10.7718` / `9.5689`
- Avg risk gap % (DD>=20 / DD<20): `0.4556` / `0.7451`
- Avg retrace % (DD>=20 / DD<20): `1.8140` / `2.1122`

## DD>=20 Episodes (4h aggregated)
- Episode count: `78`
- Longest: `ID 78` (2024-12-19 16:00:00 ~ 2025-11-14 00:00:00, 329.3333 days)
- Worst DD: `ID 78` (max DD `76.4385%`, avg risk gap `0.5519%`, trap ratio `10.0406%`)

## Regime Bucket Stats
| Dimension | Bucket | Bars | DD>=20 Rate % | Avg DD % | P90 DD % | Avg EMA State | Mixed % | Avg Risk Gap % | Avg Retrace % | Trap % |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ema_order_state_bin | mixed | 749097 | 65.5916 | 27.8790 | 48.9229 | 0.0000 | 100.0000 | 0.4082 | 1.9854 | 8.0690 |
| ema_order_state_bin | ordered_bear | 691071 | 47.8773 | 23.0313 | 55.2610 | -1.0000 | 0.0000 | 0.4734 | 2.4779 | 0.0000 |
| ema_order_state_bin | ordered_bull | 722146 | 40.2135 | 18.6188 | 39.9305 | 1.0000 | 0.0000 | 0.9086 | 1.4342 | 22.1351 |
| risk_gap_bin | risk_below_line | 644164 | 56.3973 | 24.8357 | 46.5657 | -0.0928 | 38.4713 | -1.9724 | 4.2465 | 34.1983 |
| risk_gap_bin | risk_0_2 | 1030944 | 53.7048 | 24.0487 | 46.5657 | 0.1074 | 34.5153 | 1.0285 | 1.1683 | 0.0000 |
| risk_gap_bin | risk_2_5 | 459185 | 40.8143 | 19.6136 | 42.0661 | -0.0100 | 30.6182 | 2.8857 | 0.6113 | 0.0000 |
| risk_gap_bin | risk_5_plus | 28021 | 29.4101 | 15.9980 | 34.5805 | -0.5451 | 17.3156 | 6.2141 | 0.5280 | 0.0000 |
| retrace_bin | ret_0_3 | 1668874 | 52.1262 | 23.4374 | 46.5657 | 0.0842 | 33.9856 | 1.3682 | 0.9649 | 6.6128 |
| retrace_bin | ret_3_6 | 364560 | 52.2819 | 23.5834 | 46.5657 | -0.1336 | 37.7880 | -1.0222 | 4.1321 | 26.6656 |
| retrace_bin | ret_6_9 | 87360 | 45.0973 | 21.7046 | 48.9135 | -0.3956 | 35.7143 | -3.5741 | 7.2400 | 13.4146 |
| retrace_bin | ret_9_plus | 41520 | 30.5732 | 15.3654 | 37.2116 | -0.6301 | 31.2139 | -7.4532 | 11.7116 | 2.4157 |
| long_trap_bin | trap_off | 1942021 | 51.1201 | 23.2248 | 46.5657 | -0.0663 | 35.4606 | 0.7992 | 1.8185 | 0.0000 |
| long_trap_bin | trap_on | 220293 | 54.4039 | 23.3449 | 40.9835 | 0.7256 | 27.4385 | -1.1941 | 3.1951 | 100.0000 |

## Outputs
- Plot: `00_2_backtest_btcusdt_ema_order_riskline_scale06.png`
- Episodes: `00_2_backtest_btcusdt_ema_order_riskline_scale06_episodes.csv`
- Regime stats: `00_2_backtest_btcusdt_ema_order_riskline_scale06_regime_stats.csv`