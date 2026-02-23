# 31 Backtest: Best Cases from 29 and 30 (No-lookahead)

## Selected Cases
- Selection rule: highest `Calmar`, tie-breaker `CAGR`, then `Final Equity`.
| Source Study | Strategy | Selected max entries | Source Final Equity | Source CAGR % | Source MDD % | Source Calmar |
|---|---|---:|---:|---:|---:|---:|
| `29` | `08 long-only + trend short hedge` | 5 | 13975.1494 | 124.7637 | 68.1363 | 1.8311 |
| `30` | `02 both-sides` | 4 | 3850.4172 | 64.2799 | 66.1941 | 0.9711 |

## Common Strategy Layer
- Symbol/data: BTCUSDT, cached 1m + 4h raw data (same universe as studies 29/30).
- Risk baseline params (same in both legs): `RSI oversold=18`, `RSI overbought=85`, `TP=1.2%`, `SL=3.0%`, `cooldown=5 bars`.
- Position sizing: floor-scaled averaging with `entry_scale=0.50` and max entries cap from selected case.
- No-lookahead guard (same in both): `ema200_4h = EWM(close_4h, 200).shift(1)`.
- No-lookahead guard (same in both): `ema_touch_confirmed = ema_touch_raw.shift(1)`.
- Time consistency: current 1m bar only sees already-closed 4h states.

## Execution Flow Comparison
| Step | Shared Logic | 08 leg behavior | 02 leg behavior |
|---|---|---|---|
| 1. Regime base | Build confirmed 4h EMA200/touch state | Same | Same |
| 2. Entry filter | Respect cooldown + no-touch gate | Long entry only when bullish + RSI<=oversold | Long entry in bullish + short entry in bearish |
| 3. Position scaling | Add units up to selected `max_entries` cap | Cap=`5` from study 29 best case | Cap=`4` from study 30 best case |
| 4. Short handling | Strategy-specific | No strategy short; separate 4h trend hedge short (`5x`) | Strategy short entries are native side of core logic |
| 5. Exit accounting | TP/SL/reverse/final close | Includes hedge open/close effects | No hedge events |

## Different Strategy Layer
| Item | 08 leg (from 29) | 02 leg (from 30) |
|---|---|---|
| Core mode | Long-only entries + trend short hedge | Both long + short strategy entries |
| Entry direction | Only long entries allowed | Long in bullish + short in bearish |
| 4h trend usage | Hysteresis 4h trend state, then confirmed with `shift(1)` | No hysteresis trend state; uses 1m close vs 4h EMA200 for bullish/bearish |
| Short exposure source | Hedge short (size = `5x` base long qty) when confirmed 4h bearish | Native short entries from strategy logic |
| Expected behavior | Captures uptrend growth, uses hedge in bearish phases | More symmetric direction coverage, usually more trades |

## Re-run Metrics (31)
| Portfolio | Initial | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `combined_1000` | 1000.0000 | 17825.5665 | 1682.5567 | 101.4760 | 58.0511 | 1.7480 | 2026 | 1273/753 | N/A | N/A |
| `08_best_500_me5` | 500.0000 | 13975.1494 | 2695.0299 | 124.7637 | 68.1363 | 1.8311 | 664 | 598/66 | 92.4699 | 2.9327 |
| `02_best_500_me4` | 500.0000 | 3850.4172 | 670.0834 | 64.2799 | 66.1941 | 0.9711 | 1362 | 675/687 | 99.6329 | 5808.1990 |
- Daily return correlation between selected 08 and 02 legs: `0.5566`.

## Interpretation
- 08 best case is the dominant profit contributor in this pair; growth is concentrated on long-trend capture.
- 02 best case adds directional coverage via native short entries, but drawdown reduction is limited here.
- Positive daily-return correlation means the two legs are not consistently offsetting each other.
- Combined profile stays high-growth/high-drawdown rather than low-volatility.

## Reason Breakdown (31 Re-run)
### 08 Leg
| Reason | Trades | Win Rate % | Net PnL | Avg PnL |
|---|---:|---:|---:|---:|
| `Take Profit` | 597 | 100.0000 | 57939.1860 | 97.0506 |
| `Final Hedge Close` | 1 | 100.0000 | 9483.1025 | 9483.1025 |
| `Hedge Close Trend Up` | 65 | 24.6154 | -5468.7553 | -84.1347 |
| `Final Close` | 1 | 0.0000 | -9766.5511 | -9766.5511 |

### 02 Leg
| Reason | Trades | Win Rate % | Net PnL | Avg PnL |
|---|---:|---:|---:|---:|
| `Take Profit` | 1356 | 100.0000 | 27377.5664 | 20.1899 |
| `Final Close` | 1 | 100.0000 | 30.3190 | 30.3190 |
| `Reverse` | 5 | 0.0000 | -4.7188 | -0.9438 |

## Outputs
- Plot: `31_backtest_btcusdt_bestcase_29_30.png`
- Metrics: `31_backtest_btcusdt_bestcase_29_30.csv`
- Equity series: `31_backtest_btcusdt_bestcase_29_30_equity.csv`
- Report: `31_backtest_btcusdt_bestcase_29_30.md`