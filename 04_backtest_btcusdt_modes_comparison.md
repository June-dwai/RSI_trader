# 04 Mode Comparison (Revised Hedge Logic)

## Hedge Logic Used
- `baseline_02`: original 002 behavior
- `long_only_no_short`: strategy short entry disabled
- `long_only_with_trend_short_hedge_5x`:
  - strategy remains long-only
  - hedge trend confirmation uses closed 4h candles only
  - current 4h bucket uses previous closed 4h trend (`trend_4h_confirmed = trend_4h.shift(1)`) to avoid look-ahead
  - open hedge short when confirmed 4h trend is bearish
  - close hedge short when confirmed 4h trend is bullish
  - hedge size: `5 * base_qty`, `base_qty = initial long unit qty`

## Performance Table

| Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline_02` | 14968.8275 | 1396.8827 | 93.0977 | 64.0331 | 1.4539 | 1403 | 703/700 | 99.6436 | 4087.6954 |
| `long_only_no_short` | 18237.8124 | 1723.7812 | 102.5993 | 89.4832 | 1.1466 | 635 | 635/0 | 99.8425 | 4.5289 |
| `long_only_with_trend_short_hedge_5x` | 20964.0793 | 1996.4079 | 109.5805 | 72.0598 | 1.5207 | 764 | 635/129 | 85.8639 | 2.6648 |

## Delta vs Baseline

| Mode | Final Equity Delta % | MDD Delta %p | Trades Delta |
|---|---:|---:|---:|
| `long_only_no_short` | 21.8386 | 25.4500 | -768 |
| `long_only_with_trend_short_hedge_5x` | 40.0516 | 8.0266 | -639 |

## Output Files
- plot: `04_backtest_btcusdt_modes.png`
- metrics: `04_backtest_btcusdt_modes_metrics.csv`