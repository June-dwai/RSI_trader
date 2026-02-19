# 18 Compare: 17 Baseline vs No Long Stop-Loss

## Objective
- Compare whether long stop-loss is still useful when trend hedge short is active.
- Keep same logic as 17: no-lookahead 4h confirmation, raw data, hysteresis 0.50%.

## Cases
- `case_17_baseline`: same as 17 (long SL enabled).
- `case_no_long_sl`: long SL disabled, all other rules unchanged.

## Results

| Mode | Long SL | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `case_17_baseline` | `on` | 27950.2987 | 2695.0299 | 124.7637 | 68.1363 | 1.8311 | 664 | 598/66 | 92.4699 | 2.9327 |
| `case_no_long_sl` | `off` | 5623.9316 | 462.3932 | 52.1919 | 65.1864 | 0.8007 | 224 | 158/66 | 77.6786 | 1.2850 |

## Delta (No Long SL - Baseline)
- Final Equity Delta: `-22326.3671` USDT
- MDD Delta: `-2.9499` %pt
- Trades Delta: `-440`

## Interpretation
- This is a meaningful comparison because only one control variable changes (long stop-loss on/off).
- If no-long-SL improves return but worsens MDD materially, it means hedge does not fully replace long SL risk control.
- If no-long-SL improves both return and MDD, then long SL may be unnecessary under this specific hedge design.

## Output Files
- plot: `18_backtest_btcusdt_hys05_longsl_compare.png`
- metrics: `18_backtest_btcusdt_hys05_longsl_compare.csv`