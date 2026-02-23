# 33 Backtest: Live Parity (No-lookahead, Long-only)

## Setup
- Base target: study-32 live-parity no-lookahead engine with strategy shorts blocked.
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
| 0.0000 | -100.0000 | -99.9775 | 100.0000 | -0.9998 | 41 | 41/0 | 100.0000 | inf |

## Signal Stats
- Processed bars: `2162682`
- EMA-touch bars: `162310` (`7.5050%`)
- Entry-window bars (not touch): `2000372`
- Long signal bars: `30262`
- Short signal bars: `0`
- Reverse events: `0`
- Stop-loss events: `6`
- Re-entry events: `4`
- Order events (BUY/SELL): `120/47`

## Drawdown
- Worst drawdown: `100.0000%`
- Average drawdown: `92.6590%`

## Reason Breakdown
| Reason | Trades | Win Rate % | Net PnL | Avg PnL |
|---|---:|---:|---:|---:|
| `Take Profit` | 41 | 100.0000 | 852.2162 | 20.7858 |

## Outputs
- Plot: `33_backtest_btcusdt_live_nla_longonly.png`
- Report: `33_backtest_btcusdt_live_nla_longonly.md`
- Metrics CSV: `33_backtest_btcusdt_live_nla_longonly.csv`
- Events CSV: `33_backtest_btcusdt_live_nla_longonly_events.csv`
- Trades CSV: `33_backtest_btcusdt_live_nla_longonly_trades.csv`