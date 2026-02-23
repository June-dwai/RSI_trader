# 27 Study: Short-only 0.15 Trade Map

## Setup
- Strategy: short-only entries + long hedge by 4h confirmed trend
- Initial capital: `500.0000`
- Entry scale (short): `0.15`
- Hysteresis: `0.50%`
- Net position convention: `net_mult = short_mult - hedge_long_mult`
- Therefore, hedge-only state is around `-5`.

## Core Metrics
- Final Equity: `0.0000`
- Return %: `-100.0000`
- CAGR %: `-99.9734`
- MDD %: `100.0000`
- Calmar: `-0.9997`
- Trades: `498` (Long `66`, Short `432`)
- Win rate %: `89.9598`
- Profit factor: `2.8242`

## Position Dynamics
- Hedge active ratio: `50.3616`%
- Max short mult: `5.0000`
- Max hedge long mult: `5.2768`
- Net mult max/min: `5.0000` / `-5.2740`
- Event counts: short open `433`, short add `548`, hedge open `66`
- Bankruptcy timestamp: `2024-12-27 09:05:00`

## Reason Breakdown
| Reason | Trades | Win Rate % | Net PnL | Avg PnL |
|---|---:|---:|---:|---:|
| `Hedge Close Trend Down` | 66 | 24.2424 | 2036.0247 | 30.8489 |
| `Take Profit` | 431 | 100.0000 | 1053.0330 | 2.4432 |
| `Final Close` | 1 | 100.0000 | 0.4469 | 0.4469 |

## Outputs
- Plot: `27_backtest_btcusdt_short015_hedge_map.png`
- Metrics: `27_backtest_btcusdt_short015_hedge_map_metrics.csv`
- Events: `27_backtest_btcusdt_short015_hedge_map_events.csv`
- Position: `27_backtest_btcusdt_short015_hedge_map_position.csv`
- Report: `27_backtest_btcusdt_short015_hedge_map.md`