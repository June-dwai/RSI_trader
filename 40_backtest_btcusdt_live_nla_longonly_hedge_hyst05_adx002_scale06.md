# 40 Backtest: Live Parity (No-lookahead, Long-only + Trend Short Hedge Hyst 0.5%, ADX=002)

## Setup
- Base target: study-38 logic with entry scale changed to 0.60.
- Hedge hysteresis band: `0.50%`
- Symbol: `BTCUSDT`
- Initial capital: `1000`
- Entry scale: `0.60`
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
| 28615.4276 | 2761.5428 | 126.0528 | 76.8389 | 1.6405 | 610 | 544/66 | 91.8033 | 2.2092 |

## Signal Stats
- Processed bars: `2162314`
- EMA-touch bars: `162285` (`7.5052%`)
- Entry-window bars (not touch): `2000029`
- Long signal bars: `21956`
- Short signal bars: `0`
- Reverse events: `0`
- Stop-loss events: `85`
- Re-entry events: `37`
- Hedge open events: `66`
- Hedge close events: `66`
- Order events (BUY/SELL): `1427/695`

## Drawdown
- Worst drawdown: `76.8389%`
- Average drawdown: `26.6188%`

## Reason Breakdown
| Reason | Trades | Win Rate % | Net PnL | Avg PnL |
|---|---:|---:|---:|---:|
| `Take Profit` | 543 | 100.0000 | 201769.4614 | 371.5828 |
| `Final Hedge Close` | 1 | 100.0000 | 24270.8380 | 24270.8380 |
| `Trend Up` | 65 | 24.6154 | -21973.8336 | -338.0590 |
| `Final Close` | 1 | 0.0000 | -54464.1566 | -54464.1566 |

## Outputs
- Plot: `40_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_scale06.png`
- Report: `40_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_scale06.md`
- Metrics CSV: `40_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_scale06.csv`
- Events CSV: `40_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_scale06_events.csv`
- Trades CSV: `40_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_scale06_trades.csv`