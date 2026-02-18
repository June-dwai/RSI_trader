# 07 Fixed Base5x + Hysteresis-Only Test

## Tested Modes
- `hedge_fixed_base5x_04`: current 04 successful hedge (fixed `base_qty * 5`)
- `hedge_fixed_base5x_plus_4h_hysteresis`: fixed `base_qty * 5` hedge unchanged, only 4h EMA200 hysteresis added (band +/-0.20%)

## Performance

| Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `hedge_fixed_base5x_04` | 20964.0793 | 1996.4079 | 109.5805 | 72.0598 | 1.5207 | 764 | 635/129 | 85.8639 | 2.6648 |
| `hedge_fixed_base5x_plus_4h_hysteresis` | 27843.5216 | 2684.3522 | 124.5546 | 72.6146 | 1.7153 | 732 | 635/97 | 89.4809 | 2.7989 |

## Delta vs Baseline

- Final Equity Delta: 32.8154%
- MDD Delta: 0.5549%p
- Trades Delta: -32

## Output Files
- plot: `07_backtest_btcusdt_fixed5x_hysteresis_compare.png`
- metrics: `07_backtest_btcusdt_fixed5x_hysteresis_compare.csv`