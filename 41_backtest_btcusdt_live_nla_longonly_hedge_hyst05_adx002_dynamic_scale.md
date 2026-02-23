# 41 Backtest Report: Dynamic Scale Loop (0.40 -> +0.04 -> cap 0.60, reset on hedge)

## Setup
- Base target: study-38 logic with no-lookahead guards preserved.
- Hedge hysteresis band: `0.50%`
- Symbol: `BTCUSDT`
- Initial capital: `1000`
- Dynamic scale start/step/max: `0.40` / `0.04` / `0.60`
- Parameters: RSI(6), oversold 18, overbought 85, TP 1.2%, SL 3.0%, max position 5x.
- Data: raw cached 1m + 4h (no jump/IQR filtering).

## Dynamic Scale Rule (Study-41)
- Rule-1: first long open uses scale `0.40`.
- Rule-2: consecutive long opens increase scale by `0.04` (cap `0.60`).
- Rule-3: if short hedge opens while long regime is active, next long open resets to `0.40`.
- Rule-4: short hedge size stays `5x` of base long quantity at the time of hedge open.
- Rule-5: rules repeat indefinitely.

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
| 23434.2935 | 2243.4294 | 115.3351 | 74.8951 | 1.5400 | 610 | 544/66 | 91.8033 | 2.2693 |

## Dynamic Scale State Summary
- Long open events: `544`
- Scale reset trigger events (hedge open): `66`
- Scale reset applied events (next long open): `25`
- End-of-backtest next scale state: `0.60`

## Long Open Count By Scale (Raw Opens)
| Entry Scale | Open Count | Reset Applied Count |
|---:|---:|---:|
| 0.40 | 26 | 25 |
| 0.44 | 25 | 0 |
| 0.48 | 25 | 0 |
| 0.52 | 23 | 0 |
| 0.56 | 22 | 0 |
| 0.60 | 423 | 0 |

## Scale-Wise Trade Stats (LONG Trades)
| Entry Scale | Trades | Win Rate % | Net PnL | Avg PnL | Median PnL |
|---:|---:|---:|---:|---:|---:|
| 0.40 | 26 | 100.0000 | 4770.2147 | 183.4698 | 107.4677 |
| 0.44 | 25 | 100.0000 | 5244.3516 | 209.7741 | 56.5870 |
| 0.48 | 25 | 100.0000 | 4748.1335 | 189.9253 | 115.5221 |
| 0.52 | 23 | 100.0000 | 6932.3568 | 301.4068 | 130.6932 |
| 0.56 | 22 | 95.4545 | -33265.0397 | -1512.0473 | 148.5171 |
| 0.60 | 423 | 100.0000 | 137440.4695 | 324.9184 | 175.5584 |

## Scale-Wise Trade Stats (Hedge SHORT Trades)
| Entry Scale | Trades | Win Rate % | Net PnL | Avg PnL | Median PnL |
|---:|---:|---:|---:|---:|---:|
| 0.40 | 1 | 0.0000 | -289.1927 | -289.1927 | -289.1927 |
| 0.48 | 4 | 25.0000 | -1213.1355 | -303.2839 | -563.7073 |
| 0.52 | 1 | 0.0000 | -170.9858 | -170.9858 | -170.9858 |
| 0.56 | 14 | 35.7143 | 30510.6236 | 2179.3303 | -940.5494 |
| 0.60 | 46 | 23.9130 | -30833.7528 | -670.2990 | -322.9470 |

## Signal Stats
- Processed bars: `2162314`
- EMA-touch bars: `162285` (`7.5052%`)
- Entry-window bars (not touch): `2000029`
- Long signal bars: `22003`
- Short signal bars: `0`
- Reverse events: `0`
- Stop-loss events: `85`
- Re-entry events: `37`
- Hedge open events: `66`
- Hedge close events: `66`
- Pending reset flag at end: `True`
- Order events (BUY/SELL): `1423/695`

## Drawdown
- Worst drawdown: `74.8951%`
- Average drawdown: `27.1198%`

## Reason Breakdown
| Reason | Trades | Win Rate % | Net PnL | Avg PnL |
|---|---:|---:|---:|---:|
| `Take Profit` | 543 | 100.0000 | 166223.6066 | 306.1208 |
| `Final Hedge Close` | 1 | 100.0000 | 17982.5431 | 17982.5431 |
| `Trend Up` | 65 | 24.6154 | -19978.9862 | -307.3690 |
| `Final Close` | 1 | 0.0000 | -40353.1202 | -40353.1202 |

## Outputs
- Plot: `41_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_dynamic_scale.png`
- Report: `41_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_dynamic_scale.md`
- Metrics CSV: `41_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_dynamic_scale.csv`
- Events CSV: `41_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_dynamic_scale_events.csv`
- Trades CSV: `41_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_dynamic_scale_trades.csv`
- Scale stats CSV: `41_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_dynamic_scale_scale_stats.csv`