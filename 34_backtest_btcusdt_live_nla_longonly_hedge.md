# 34 Backtest: Live Parity (No-lookahead, Long-only + Trend Short Hedge)

## Setup
- Base target: study-33 long-only no-lookahead + existing trend short hedge logic (5x base qty).
- Symbol: `BTCUSDT`
- Initial capital: `1000`
- Entry scale: `0.50`
- Parameters: RSI(6), oversold 18, overbought 85, TP 1.2%, SL 3.0%, max position 5x.
- Data: raw cached 1m + 4h (no jump/IQR filtering).

## No-lookahead Guard
- Trend anchor uses previous closed 4h EMA200 only: `ema200_prev_closed`.
- `ema_touch` gate uses only known info at each 1m close:
  1) previous closed 4h touch, plus
  2) current 4h touch-so-far from 1m cumulative high/low up to current bar.
- No future 4h high/low or future 1m bars are referenced.

## Metrics
| Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3459.5452 | 245.9545 | 35.2310 | 62.1523 | 0.5668 | 493 | 364/129 | 78.0933 | 1.9544 |

## Signal Stats
- Processed bars: `2162682`
- EMA-touch bars: `162310` (`7.5050%`)
- Entry-window bars (not touch): `2000372`
- Long signal bars: `20393`
- Short signal bars: `0`
- Reverse events: `0`
- Stop-loss events: `47`
- Re-entry events: `23`
- Hedge open events: `129`
- Hedge close events: `129`
- Order events (BUY/SELL): `1100/540`

## Drawdown
- Worst drawdown: `62.1523%`
- Average drawdown: `25.1549%`

## Reason Breakdown
| Reason | Trades | Win Rate % | Net PnL | Avg PnL |
|---|---:|---:|---:|---:|
| `Take Profit` | 363 | 100.0000 | 21722.6351 | 59.8420 |
| `Final Hedge Close` | 1 | 100.0000 | 2154.7030 | 2154.7030 |
| `Trend Up` | 128 | 16.4062 | -4135.3095 | -32.3071 |
| `Final Close` | 1 | 0.0000 | -4837.8669 | -4837.8669 |

## Outputs
- Plot: `34_backtest_btcusdt_live_nla_longonly_hedge.png`
- Report: `34_backtest_btcusdt_live_nla_longonly_hedge.md`
- Metrics CSV: `34_backtest_btcusdt_live_nla_longonly_hedge.csv`
- Events CSV: `34_backtest_btcusdt_live_nla_longonly_hedge_events.csv`
- Trades CSV: `34_backtest_btcusdt_live_nla_longonly_hedge_trades.csv`