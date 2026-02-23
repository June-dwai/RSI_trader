# 38 Backtest Report: Live Parity NLA + Hedge Hyst 0.5 (ADX from 002)

## 1) Run Configuration
- Study ID: `38`
- Script: `38_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002.py`
- Symbol: `BTCUSDT`
- Initial capital: `1000.0`
- Entry scale: `0.50`
- Hedge hysteresis band: `0.005` (0.5%)
- Indicators: RSI(6), ADX(14), 4h EMA200
- Core rule set: same as study 35, with ADX calculation replaced by 002-style rolling ADX only

## 2) Data and Time Span
- Source: cached `1m` + `4h` OHLCV (same local cache pipeline as prior studies)
- Backtest window (trade records):
  - First entry time: `2022-02-05 06:44:00`
  - Last exit time: `2026-02-12 00:00:00`

## 3) No-lookahead Guards
- Trend anchor for 1m decisions uses previous closed 4h EMA: `ema200_prev_closed`
- 4h trend state for hedge uses hysteresis and then `shift(1)` confirmation
- EMA touch gate uses only information known at each 1m close:
  1. previous confirmed 4h touch
  2. current 4h touch-so-far built from cumulative 1m high/low inside the open 4h bucket
- No future 4h candle high/low is referenced

## 4) Top-line Metrics
| Metric | Value |
|---|---:|
| Final equity | 18844.8733 |
| Total return % | 1784.4873 |
| CAGR % | 104.2190 |
| Max drawdown % | 67.1408 |
| Calmar ratio | 1.5522 |
| Total trades | 610 |
| Long trades | 544 |
| Short trades (hedge leg) | 66 |
| Win rate % | 91.8033 |
| Profit factor | 2.3149 |

## 5) Signal and State Counters
| Counter | Value |
|---|---:|
| Processed bars | 2162314 |
| EMA-touch bars | 162285 |
| EMA-touch ratio % | 7.5052 |
| Entry-window bars | 2000029 |
| Long signal bars | 21939 |
| Short signal bars | 0 |
| Reverse events | 0 |
| Stop-loss events | 85 |
| Re-entry events | 37 |
| Hedge open events | 66 |
| Hedge close events | 66 |

## 6) Order Event Counts
| Event side | Count |
|---|---:|
| BUY | 1429 |
| SELL | 695 |
| Total | 2124 |

## 7) Exit Reason Breakdown (Detailed)
| Reason | Trades | Win rate % | Net PnL | Avg PnL | Median PnL | Max win | Max loss |
|---|---:|---:|---:|---:|---:|---:|---:|
| Take Profit | 543 | 100.0000 | 109551.6373 | 201.7526 | 114.0539 | 923.8509 | 6.4444 |
| Final Hedge Close | 1 | 100.0000 | 12343.8153 | 12343.8153 | 12343.8153 | 12343.8153 | 12343.8153 |
| Trend Up | 65 | 24.6154 | -10504.3291 | -161.6051 | -267.2888 | 10778.2724 | -3064.6989 |
| Final Close | 1 | 0.0000 | -27699.7231 | -27699.7231 | -27699.7231 | -27699.7231 | -27699.7231 |

## 8) Interpretation Notes
- The strategy makes many small/medium realized gains via `Take Profit`.
- Hedge short exits (`Trend Up`) are mostly cost centers by design in strong uptrend periods.
- Final bar liquidation (`Final Close`) can dominate last-trade PnL and should be interpreted as accounting close, not a live discretionary exit.
- High CAGR and high MDD coexist here because position sizing scales up in high ADX regimes.

## 9) Output Files
- Plot: `38_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002.png`
- Report: `38_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002.md`
- Metrics CSV: `38_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002.csv`
- Events CSV: `38_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_events.csv`
- Trades CSV: `38_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_trades.csv`
