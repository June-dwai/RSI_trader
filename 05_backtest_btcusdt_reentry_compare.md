# 05 Re-entry Strategy Comparison

## Compared Modes
- `hedge_04_confirmed_4h`
  - 04 successful hedge strategy (confirmed 4h trend hedge)
  - original 002 stop-loss/reentry handling
- `hedge_04_plus_infinite_stop_reentry_hybrid_tp`
  - same 4h-confirmed hedge
  - long stop-loss/reentry loop enabled indefinitely
  - after each re-entry, next stop anchor = re-entry price
  - long TP hybrid rule
    - before first stop in cycle: BEP-based target (`bep * (1 + take_profit_pct)`)
    - after any stop in cycle: avg-entry target (`avg_entry * (1 + take_profit_pct)`)

## Performance

| Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `hedge_04_confirmed_4h` | 20964.0793 | 1996.4079 | 109.5805 | 72.0598 | 1.5207 | 764 | 635/129 | 85.8639 | 2.6648 |
| `hedge_04_plus_infinite_stop_reentry_hybrid_tp` | 6860.2057 | 586.0206 | 59.7265 | 75.3019 | 0.7932 | 758 | 629/129 | 85.8839 | 3.9487 |

## Delta (Modified vs 04 Hedge)

- Final Equity Delta: -67.2764%
- MDD Delta: 3.2421%p
- Trades Delta: -6

## Notes
- This update removes the one-time stop/reentry lock state and allows repeated stop/reentry cycles.
- BEP-based TP is designed to avoid locking losses from repeated stop/reentry on long positions.
- Profit is not mathematically guaranteed in all paths due to fees, whipsaw, and hedge timing effects.

## Outputs
- plot: `05_backtest_btcusdt_reentry_compare.png`
- metrics: `05_backtest_btcusdt_reentry_compare_metrics.csv`