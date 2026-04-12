# 48 Backtest: Study-47 Case1 Max Entries Sweep

## Setup
- Strategy: case1 from study-47 only.
- Engine traits: long-only core + 4h confirmed trend short hedge, hysteresis 0.5%, ADX 002 logic.
- Symbol: `BTCUSDT`
- Initial capital per run: `1000 USDT`
- Entry scale: `0.60`
- Sweep max entries: `3, 4, 5, 6`

## Results

| Max Entries | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Hedge Open/Close |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 6921.3777 | 592.1378 | 60.0717 | 62.3051 | 0.9642 | 546 | 480/66 | 90.8425 | 2.4972 | 66/66 |
| 4 | 17551.8580 | 1655.1858 | 100.7193 | 68.9323 | 1.4611 | 598 | 532/66 | 91.6388 | 2.4524 | 66/66 |
| 5 | 28615.4276 | 2761.5428 | 126.0528 | 76.8389 | 1.6405 | 610 | 544/66 | 91.8033 | 2.2092 | 66/66 |
| 6 | 5168.7607 | 416.8761 | 49.1002 | 83.2126 | 0.5901 | 427 | 361/66 | 88.2904 | 2.0745 | 66/66 |

## Best Cases
- Best CAGR: `max_entries=5` (CAGR `126.0528%`).
- Lowest MDD: `max_entries=3` (MDD `62.3051%`).
- Best Calmar: `max_entries=5` (Calmar `1.6405`).

## Delta vs max_entries=5
| Max Entries | Final Equity Delta | CAGR Delta (pp) | MDD Delta (pp) |
|---:|---:|---:|---:|
| 3 | -21694.0499 | -65.9811 | -14.5337 |
| 4 | -11063.5696 | -25.3335 | -7.9066 |
| 5 | 0.0000 | 0.0000 | 0.0000 |
| 6 | -23446.6669 | -76.9526 | 6.3737 |

## Outputs
- Plot: `48_backtest_btcusdt_scale06_adx002_case1_max_entries_sweep.png`
- Metrics: `48_backtest_btcusdt_scale06_adx002_case1_max_entries_sweep.csv`
- Curves: `48_backtest_btcusdt_scale06_adx002_case1_max_entries_sweep_curves.csv`
- Report: `48_backtest_btcusdt_scale06_adx002_case1_max_entries_sweep.md`