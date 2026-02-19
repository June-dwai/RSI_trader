# 22 DD-Scale + Entry Scale Sweep

## Objective
- Sweep `entry_scale` values: `0.3, 0.4, 0.5, 0.6, 0.7, 0.8`.
- Compare two modes at each scale:
  1) `baseline` (no dd scale)
  2) `dd_scaled` with drawdown scaling

## DD Scale Rule
```python
if current_drawdown > 0.50:
    position_scale = 0.25
elif current_drawdown > 0.25:
    position_scale = 0.5
else:
    position_scale = 1.0
```

## Full Results

| Mode | entry_scale | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Avg Entry Scale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `baseline` | 0.3 | 8765.0120 | 776.5012 | 69.5331 | 44.9130 | 1.5482 | 664 | 598/66 | 92.4699 | 3.3201 | 1.0000 |
| `baseline` | 0.4 | 16070.5925 | 1507.0592 | 96.4616 | 57.2094 | 1.6861 | 664 | 598/66 | 92.4699 | 3.1039 | 1.0000 |
| `baseline` | 0.5 | 27950.2987 | 2695.0299 | 124.7637 | 68.1363 | 1.8311 | 664 | 598/66 | 92.4699 | 2.9327 | 1.0000 |
| `baseline` | 0.6 | 46144.2768 | 4514.4277 | 153.9061 | 77.6838 | 1.9812 | 664 | 598/66 | 92.4699 | 2.7966 | 1.0000 |
| `baseline` | 0.7 | 72266.6371 | 7126.6637 | 183.1709 | 85.8487 | 2.1336 | 664 | 598/66 | 92.4699 | 2.6883 | 1.0000 |
| `baseline` | 0.8 | 107144.6513 | 10614.4651 | 211.6303 | 92.6349 | 2.2846 | 664 | 598/66 | 92.4699 | 2.6025 | 1.0000 |
| `dd_scaled` | 0.3 | 8765.0120 | 776.5012 | 69.5331 | 44.9130 | 1.5482 | 664 | 598/66 | 92.4699 | 3.3201 | 0.9973 |
| `dd_scaled` | 0.4 | 12244.5015 | 1124.4502 | 83.8912 | 42.5726 | 1.9705 | 664 | 598/66 | 92.4699 | 3.1696 | 0.9283 |
| `dd_scaled` | 0.5 | 17790.3904 | 1679.0390 | 101.3793 | 51.4950 | 1.9687 | 664 | 598/66 | 92.4699 | 2.9633 | 0.8791 |
| `dd_scaled` | 0.6 | 19293.7573 | 1829.3757 | 105.3914 | 61.5713 | 1.7117 | 664 | 598/66 | 92.4699 | 2.8525 | 0.8003 |
| `dd_scaled` | 0.7 | 24198.3582 | 2319.8358 | 117.0217 | 71.5753 | 1.6349 | 664 | 598/66 | 92.4699 | 3.1787 | 0.7978 |
| `dd_scaled` | 0.8 | 24145.8724 | 2314.5872 | 116.9072 | 81.5078 | 1.4343 | 664 | 598/66 | 92.4699 | 3.1007 | 0.7320 |

## Delta (dd_scaled - baseline) by entry_scale

| entry_scale | Equity Delta | Equity Delta % | MDD Delta %pt | Calmar Delta |
|---:|---:|---:|---:|---:|
| 0.3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 0.4 | -3826.0909 | -23.8080 | -14.6368 | 0.2844 |
| 0.5 | -10159.9083 | -36.3499 | -16.6413 | 0.1376 |
| 0.6 | -26850.5195 | -58.1882 | -16.1124 | -0.2695 |
| 0.7 | -48068.2789 | -66.5152 | -14.2734 | -0.4987 |
| 0.8 | -82998.7789 | -77.4642 | -11.1271 | -0.8503 |

## Best Cases
- Best Final Equity: `baseline_es0.8` (entry_scale `0.8`, equity `107144.6513`)
- Best Calmar: `baseline_es0.8` (entry_scale `0.8`, calmar `2.2846`)
- Lowest MDD: `dd_scaled_es0.4` (entry_scale `0.4`, MDD `42.5726%`)

## Output Files
- plot: `22_backtest_btcusdt_dd_scale_entryscale_sweep.png`
- metrics: `22_backtest_btcusdt_dd_scale_entryscale_sweep.csv`