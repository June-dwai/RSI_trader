# 39 Backtest: Live Parity (No-lookahead, Long-only + Trend Short Hedge, No Stop-loss, ADX=002)

## Setup
- Base target: study-38 logic with stop-loss/re-entry cycle removed.
- Hedge hysteresis band: `0.50%`
- Symbol: `BTCUSDT`
- Initial capital: `1000`
- Entry scale: `0.50`
- Parameters: RSI(6), oversold 18, overbought 85, TP 1.2%, stop-loss disabled, max position 5x.
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
| 6135.8494 | 513.5849 | 55.4505 | 65.0862 | 0.8520 | 224 | 158/66 | 77.6786 | 1.2932 |

## Signal Stats
- Processed bars: `2162314`
- EMA-touch bars: `162285` (`7.5052%`)
- Entry-window bars (not touch): `2000029`
- Long signal bars: `14246`
- Short signal bars: `0`
- Reverse events: `0`
- Stop-loss / re-entry: `disabled`
- Stop-loss events: `0`
- Re-entry events: `0`
- Hedge open events: `66`
- Hedge close events: `66`
- Order events (BUY/SELL): `400/224`

## Drawdown
- Worst drawdown: `65.0862%`
- Average drawdown: `26.8232%`

## Reason Breakdown
| Reason | Trades | Win Rate % | Net PnL | Avg PnL |
|---|---:|---:|---:|---:|
| `Take Profit` | 157 | 100.0000 | 12944.1781 | 82.4470 |
| `Final Hedge Close` | 1 | 100.0000 | 3979.3992 | 3979.3992 |
| `Trend Up` | 65 | 24.6154 | -1731.3685 | -26.6364 |
| `Final Close` | 1 | 0.0000 | -9384.0625 | -9384.0625 |

## Outputs
- Plot: `39_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_nosl.png`
- Report: `39_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_nosl.md`
- Metrics CSV: `39_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_nosl.csv`
- Events CSV: `39_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_nosl_events.csv`
- Trades CSV: `39_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_nosl_trades.csv`