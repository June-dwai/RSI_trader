# 32 Backtest: Live Parity (No-lookahead Strict)

## Setup
- Base target: `live_rsi_bot.py` signal family (entry/DCA/reverse/stop-loss cycle).
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
| 3591.6938 | 259.1694 | 36.4694 | 76.2307 | 0.4784 | 1501 | 738/763 | 93.6043 | 18.6443 |

## Signal Stats
- Processed bars: `2162682`
- EMA-touch bars: `162310` (`7.5050%`)
- Entry-window bars (not touch): `2000372`
- Long signal bars: `26514`
- Short signal bars: `15140`
- Reverse events: `98`
- Stop-loss events: `213`
- Re-entry events: `65`
- Order events (BUY/SELL): `2822/2767`

## Drawdown
- Worst drawdown: `76.2307%`
- Average drawdown: `32.4644%`

## Reason Breakdown
| Reason | Trades | Win Rate % | Net PnL | Avg PnL |
|---|---:|---:|---:|---:|
| `Take Profit` | 1402 | 100.0000 | 33511.2989 | 23.9025 |
| `Final Close` | 1 | 100.0000 | 30.4607 | 30.4607 |
| `Reverse` | 7 | 0.0000 | -10.4428 | -1.4918 |
| `Reverse Residual` | 91 | 2.1978 | -1788.3467 | -19.6522 |

## Outputs
- Plot: `32_backtest_btcusdt_live_nla.png`
- Report: `32_backtest_btcusdt_live_nla.md`
- Metrics CSV: `32_backtest_btcusdt_live_nla.csv`
- Events CSV: `32_backtest_btcusdt_live_nla_events.csv`
- Trades CSV: `32_backtest_btcusdt_live_nla_trades.csv`