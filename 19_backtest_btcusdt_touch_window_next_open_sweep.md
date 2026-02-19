# 19 Touch Window Case Study (`-1` to `-6`) with Entry-Only Next-Open

## Objective
- Compare entry filter variants: block long entry if any of last N confirmed 4h candles touched 4h EMA200.
- N sweep: `1, 2, 3, 4, 5, 6`.
- Keep long stop-loss ON.
- Execute long entries at next 1m open.
- Keep stop-loss / take-profit / trend-close / hedge open-close on signal close.
- Keep fixed hedge strategy from 17 (hysteresis `0.50%`, 4h confirmed trend hedge).

## Logic
- `ema_touch_raw`: `high >= ema200 and low <= ema200` on 4h.
- `ema_touch_recent_n`: rolling-any over last `N` 4h candles.
- `ema_touch_confirmed`: `ema_touch_recent_n.shift(1)` for no look-ahead.
- 1m long entry condition uses `not ema_touch_confirmed` as gate.
- Entry timing only: signal at close `t`, execution at open `t+1`.

## Results

| N | Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `touch_last_1_4h` | 23033.2161 | 2203.3216 | 114.4330 | 69.0819 | 1.6565 | 663 | 597/66 | 92.4585 | 2.9799 |
| 2 | `touch_last_2_4h` | 21465.9608 | 2046.5961 | 110.7897 | 68.9519 | 1.6068 | 660 | 594/66 | 92.4242 | 2.9807 |
| 3 | `touch_last_3_4h` | 21271.5477 | 2027.1548 | 110.3239 | 69.0490 | 1.5978 | 655 | 589/66 | 92.3664 | 2.9813 |
| 4 | `touch_last_4_4h` | 18672.4693 | 1767.2469 | 103.7631 | 69.3146 | 1.4970 | 645 | 579/66 | 92.2481 | 2.9970 |
| 5 | `touch_last_5_4h` | 17826.2208 | 1682.6221 | 101.4778 | 69.1188 | 1.4682 | 638 | 572/66 | 92.1630 | 2.9899 |
| 6 | `touch_last_6_4h` | 15753.8572 | 1475.3857 | 95.5129 | 69.8056 | 1.3683 | 630 | 564/66 | 92.0635 | 2.9944 |

## Best Cases
- Best Final Equity: `N=1` (`23033.2161` USDT, return `2203.3216%`).
- Best Calmar: `N=1` (Calmar `1.6565`, MDD `69.0819%`).
- Lowest MDD: `N=2` (MDD `68.9519%`, Final Equity `21465.9608` USDT).

## Output Files
- plot: `19_backtest_btcusdt_touch_window_next_open_sweep.png`
- metrics: `19_backtest_btcusdt_touch_window_next_open_sweep.csv`