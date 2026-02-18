# 06 Hedge Size / Hysteresis Experiment

## Tested Modes
- `hedge_fixed_base5x_04`: current 04 successful hedge (fixed `base_qty * 5`)
- `hedge_dynamic_linked_to_long_qty`: hedge size linked to current long quantity (`long_qty * 1.0`), under confirmed bearish, hedge never shrinks and only increases when needed
- `hedge_dynamic_linked_plus_4h_hysteresis`: mode 2 + 4h EMA200 hysteresis (band +/-0.20%), confirmed with previous closed 4h state

## Performance

| Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `hedge_fixed_base5x_04` | 20964.0793 | 1996.4079 | 109.5805 | 72.0598 | 1.5207 | 764 | 635/129 | 85.8639 | 2.6648 |
| `hedge_dynamic_linked_to_long_qty` | 10586.6025 | 958.6603 | 77.4990 | 72.0598 | 1.0755 | 751 | 635/116 | 86.6844 | 2.8742 |
| `hedge_dynamic_linked_plus_4h_hysteresis` | 14135.6416 | 1313.5642 | 90.4271 | 72.6146 | 1.2453 | 720 | 635/85 | 90.2778 | 3.0047 |

## Delta vs 04 Baseline

| Mode | Final Equity Delta % | MDD Delta %p | Trades Delta |
|---|---:|---:|---:|
| `hedge_dynamic_linked_to_long_qty` | -49.5012 | -0.0000 | -13 |
| `hedge_dynamic_linked_plus_4h_hysteresis` | -32.5721 | 0.5549 | -44 |

## Output Files
- plot: `06_backtest_btcusdt_hedge_size_hysteresis_compare.png`
- metrics: `06_backtest_btcusdt_hedge_size_hysteresis_compare.csv`