# 21 Drawdown-Based Position Scale Compare

## Objective
- Compare 17 baseline (`hys=0.50%`) vs drawdown-based entry scale control.
- Keep all existing rules unchanged (long SL ON, fixed 5x hedge, no-lookahead, raw data).

## DD Scale Rule
```python
if current_drawdown > 0.35:
    position_scale = 0.5
elif current_drawdown > 0.20:
    position_scale = 0.7
else:
    position_scale = 1.0
```
- Scale is applied to new long base quantity (`base_qty`) at entry open.
- Subsequent averaging follows original logic using scaled base quantity.

## Results

| Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Avg Entry Scale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline_hys05` | 27950.2987 | 2695.0299 | 124.7637 | 68.1363 | 1.8311 | 664 | 598/66 | 92.4699 | 2.9327 | 1.0000 |
| `dd_scaled_hys05` | 19794.6326 | 1879.4633 | 106.6755 | 57.4623 | 1.8564 | 664 | 598/66 | 92.4699 | 2.9541 | 0.9009 |

## Entry Scale Usage

| Mode | Total Entries | scale=1.0 | scale=0.7 | scale=0.5 | Avg Drawdown at Entry % |
|---|---:|---:|---:|---:|---:|
| `baseline_hys05` | 1819 | 1819 | 0 | 0 | 13.6609 |
| `dd_scaled_hys05` | 1819 | 1248 | 526 | 45 | 14.7259 |

## Delta vs Baseline
- Final Equity Delta: `-8155.6662` USDT (`-29.1792%`).
- MDD Delta: `-10.6740` %pt.

## Interpretation
- If MDD decreases with small equity loss, this can be a risk-control improvement.
- If equity drops sharply while MDD barely improves, DD scaling is too conservative for this strategy.

## Output Files
- plot: `21_backtest_btcusdt_dd_scale_compare.png`
- metrics: `21_backtest_btcusdt_dd_scale_compare.csv`