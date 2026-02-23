# 35 Backtest: Live Parity (No-lookahead, Long-only + Trend Short Hedge Hyst 0.5%)

## Setup
- Base target: study-33 long-only no-lookahead + existing trend short hedge logic (5x base qty).
- Hedge hysteresis band: `0.50%`
- Symbol: `BTCUSDT`
- Initial capital: `1000`
- Entry scale: `0.50`
- Parameters: RSI(6), oversold 18, overbought 85, TP 1.2%, SL 3.0%, max position 5x.
- Data: raw cached 1m + 4h (no jump/IQR filtering).

## No-lookahead Guard
- Trend anchor uses previous closed 4h EMA200 only: `ema200_prev_closed`.
- Hedge trend state uses hysteresis around EMA200 (0.5%) and then `shift(1)` confirmation.
- `ema_touch` gate uses only known info at each 1m close:
  1) previous closed 4h touch, plus
  2) current 4h touch-so-far from 1m cumulative high/low up to current bar.
- No future 4h high/low or future 1m bars are referenced.

## Metrics
| Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5984.1433 | 498.4143 | 54.5070 | 49.5386 | 1.1003 | 430 | 364/66 | 88.3721 | 2.0561 |

## Signal Stats
- Processed bars: `2162682`
- EMA-touch bars: `162310` (`7.5050%`)
- Entry-window bars (not touch): `2000372`
- Long signal bars: `20375`
- Short signal bars: `0`
- Reverse events: `0`
- Stop-loss events: `47`
- Re-entry events: `23`
- Hedge open events: `66`
- Hedge close events: `66`
- Order events (BUY/SELL): `1035/477`

## Drawdown
- Worst drawdown: `49.5386%`
- Average drawdown: `20.0116%`

## Reason Breakdown
| Reason | Trades | Win Rate % | Net PnL | Avg PnL |
|---|---:|---:|---:|---:|
| `Take Profit` | 363 | 100.0000 | 27269.0661 | 75.1214 |
| `Final Hedge Close` | 1 | 100.0000 | 3935.7764 | 3935.7764 |
| `Trend Up` | 65 | 24.6154 | -2131.1328 | -32.7867 |
| `Final Close` | 1 | 0.0000 | -8836.8385 | -8836.8385 |

## Outputs
- Plot: `35_backtest_btcusdt_live_nla_longonly_hedge_hyst05.png`
- Report: `35_backtest_btcusdt_live_nla_longonly_hedge_hyst05.md`
- Metrics CSV: `35_backtest_btcusdt_live_nla_longonly_hedge_hyst05.csv`
- Events CSV: `35_backtest_btcusdt_live_nla_longonly_hedge_hyst05_events.csv`
- Trades CSV: `35_backtest_btcusdt_live_nla_longonly_hedge_hyst05_trades.csv`