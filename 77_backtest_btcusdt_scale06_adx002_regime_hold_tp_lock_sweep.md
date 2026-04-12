# Study 77: Regime-Hold Take-Profit Lockout Sweep

## Model
- Base engine is study-76 regime-hold with the same 4h confirmed EMA200 hysteresis trend and the same isolated-margin accounting.
- Take-profit check is `close-based` only: if marked wallet return from the current trade reaches the threshold on the current 4h close, the position is closed at that close.
- After a TP exit, the same side is locked out until the confirmed 4h regime flips to the opposite side. This is the intentional flat gap.
- Stop-loss and liquidation logic are unchanged from study 76.
- Leveraged variants tested: `1.5x, 2x`
- TP thresholds tested: `20%, 30%, 40%, 50%, 60%` wallet return per trade

## Ranking

| Variant | Lev | TP % | CAGR % | MDD % | Calmar | Final Equity | TP Exits | Locked Bars | Trades |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| base_1.5x | 1.5 | N/A | 35.9322 | 49.8715 | 0.7205 | 3629.7345 | 0 | 0 | 140 |
| tp20_lock_2x | 2.0 | 20 | 34.3546 | 50.8583 | 0.6755 | 3456.0913 | 28 | 4416 | 140 |
| base_2x | 2.0 | N/A | 38.4140 | 59.8575 | 0.6418 | 3916.2700 | 0 | 0 | 140 |
| tp60_lock_1.5x | 1.5 | 60 | 29.3767 | 49.8715 | 0.5890 | 2949.3677 | 5 | 982 | 140 |
| tp40_lock_1.5x | 1.5 | 40 | 23.1554 | 47.2546 | 0.4900 | 2398.0062 | 8 | 1756 | 140 |
| tp50_lock_2x | 2.0 | 50 | 24.5716 | 58.5574 | 0.4196 | 2515.9561 | 10 | 2127 | 140 |
| tp30_lock_1.5x | 1.5 | 30 | 19.8457 | 47.7837 | 0.4153 | 2138.7861 | 12 | 2556 | 140 |
| tp50_lock_1.5x | 1.5 | 50 | 20.6055 | 49.8715 | 0.4132 | 2196.3121 | 5 | 1171 | 140 |
| tp60_lock_2x | 2.0 | 60 | 24.4335 | 59.8575 | 0.4082 | 2504.2681 | 7 | 1446 | 140 |
| tp20_lock_1.5x | 1.5 | 20 | 16.4627 | 43.7005 | 0.3767 | 1896.4702 | 19 | 3657 | 140 |
| tp40_lock_2x | 2.0 | 40 | 20.0632 | 59.1584 | 0.3391 | 2155.1381 | 12 | 2556 | 140 |
| tp30_lock_2x | 2.0 | 30 | 14.5135 | 57.8437 | 0.2509 | 1766.7020 | 17 | 3534 | 140 |

## Best Variant
- `base_1.5x`: CAGR `35.9322%`, MDD `49.8715%`, Calmar `0.7205`, TP exits `0`

## Delta vs Same-Leverage Baseline
- `tp20_lock_2x` vs `base_2x`: CAGR `-4.0594pp`, MDD `-8.9992pp`, Calmar `0.0337`, TP exits `28`, locked bars `4416`
- `tp60_lock_1.5x` vs `base_1.5x`: CAGR `-6.5555pp`, MDD `0.0000pp`, Calmar `-0.1314`, TP exits `5`, locked bars `982`
- `tp40_lock_1.5x` vs `base_1.5x`: CAGR `-12.7768pp`, MDD `-2.6169pp`, Calmar `-0.2305`, TP exits `8`, locked bars `1756`
- `tp50_lock_2x` vs `base_2x`: CAGR `-13.8424pp`, MDD `-1.3001pp`, Calmar `-0.2221`, TP exits `10`, locked bars `2127`
- `tp30_lock_1.5x` vs `base_1.5x`: CAGR `-16.0865pp`, MDD `-2.0878pp`, Calmar `-0.3052`, TP exits `12`, locked bars `2556`
- `tp50_lock_1.5x` vs `base_1.5x`: CAGR `-15.3267pp`, MDD `0.0000pp`, Calmar `-0.3073`, TP exits `5`, locked bars `1171`
- `tp60_lock_2x` vs `base_2x`: CAGR `-13.9805pp`, MDD `0.0000pp`, Calmar `-0.2336`, TP exits `7`, locked bars `1446`
- `tp20_lock_1.5x` vs `base_1.5x`: CAGR `-19.4695pp`, MDD `-6.1711pp`, Calmar `-0.3438`, TP exits `19`, locked bars `3657`
- `tp40_lock_2x` vs `base_2x`: CAGR `-18.3508pp`, MDD `-0.6992pp`, Calmar `-0.3026`, TP exits `12`, locked bars `2556`
- `tp30_lock_2x` vs `base_2x`: CAGR `-23.9005pp`, MDD `-2.0138pp`, Calmar `-0.3908`, TP exits `17`, locked bars `3534`

## Interpretation
- If TP-lock improves both CAGR and MDD against the same leverage baseline, then the regime-hold was indeed giving back too much during late-trend chop.
- If MDD falls but CAGR falls harder, then the TP was simply cutting winners too early.
- Because TP uses current-close information only, the result is conservative versus intrabar profit-taking and avoids intrabar ordering ambiguity.

## Outputs
- Plot: `77_backtest_btcusdt_scale06_adx002_regime_hold_tp_lock_sweep.png`
- Metrics CSV: `77_backtest_btcusdt_scale06_adx002_regime_hold_tp_lock_sweep.csv`
- Curves CSV: `77_backtest_btcusdt_scale06_adx002_regime_hold_tp_lock_sweep_curves.csv`
- Report: `77_backtest_btcusdt_scale06_adx002_regime_hold_tp_lock_sweep.md`