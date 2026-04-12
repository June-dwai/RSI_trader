# Study 78: Side-Selective Take-Profit Lock

## Model
- Uses the study-76 regime-hold leverage engine with the same no-lookahead confirmed 4h regime signal.
- A TP exit is allowed only on the configured side (`long` or `short`), and it uses current 4h close wallet return from the active trade.
- After TP, the same side is locked out until the confirmed regime flips to the opposite side.
- This isolates whether the late-trend giveback problem is mainly in longs or shorts.

## Ranking

| Variant | Lev | TP Side | TP % | CAGR % | MDD % | Calmar | Final Equity | TP Exits | Locked Bars |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| short_tp20_lock_2x | 2.0 | short | 20 | 64.4184 | 52.5842 | 1.2251 | 8069.8245 | 14 | 2019 |
| short_tp20_lock_1.5x | 1.5 | short | 20 | 46.5933 | 47.2225 | 0.9867 | 4984.0323 | 10 | 1600 |
| short_tp30_lock_1.5x | 1.5 | short | 30 | 45.3253 | 47.7837 | 0.9486 | 4805.4864 | 6 | 1110 |
| short_tp30_lock_2x | 2.0 | short | 30 | 46.4112 | 63.3725 | 0.7324 | 4958.0854 | 8 | 1489 |
| base_1.5x | 1.5 | none | N/A | 35.9322 | 49.8715 | 0.7205 | 3629.7345 | 0 | 0 |
| base_2x | 2.0 | none | N/A | 38.4140 | 59.8575 | 0.6418 | 3916.2700 | 0 | 0 |
| long_tp30_lock_1.5x | 1.5 | long | 30 | 12.0994 | 50.1890 | 0.2411 | 1615.4921 | 6 | 1446 |
| long_tp20_lock_2x | 2.0 | long | 20 | 13.1051 | 62.5340 | 0.2096 | 1677.2343 | 14 | 2397 |
| long_tp20_lock_1.5x | 1.5 | long | 20 | 7.9929 | 53.8202 | 0.1485 | 1381.1474 | 9 | 2057 |
| long_tp30_lock_2x | 2.0 | long | 30 | 8.2586 | 64.6347 | 0.1278 | 1395.4745 | 9 | 2045 |

## Best Variant
- `short_tp20_lock_2x`: CAGR `64.4184%`, MDD `52.5842%`, Calmar `1.2251`

## Delta vs Same-Leverage Baseline
- `short_tp20_lock_2x` vs `base_2x`: CAGR `26.0044pp`, MDD `-7.2733pp`, Calmar `0.5833`, TP exits `14`
- `short_tp20_lock_1.5x` vs `base_1.5x`: CAGR `10.6611pp`, MDD `-2.6490pp`, Calmar `0.2662`, TP exits `10`
- `short_tp30_lock_1.5x` vs `base_1.5x`: CAGR `9.3931pp`, MDD `-2.0878pp`, Calmar `0.2281`, TP exits `6`
- `short_tp30_lock_2x` vs `base_2x`: CAGR `7.9972pp`, MDD `3.5150pp`, Calmar `0.0906`, TP exits `8`
- `long_tp30_lock_1.5x` vs `base_1.5x`: CAGR `-23.8328pp`, MDD `0.3175pp`, Calmar `-0.4794`, TP exits `6`
- `long_tp20_lock_2x` vs `base_2x`: CAGR `-25.3089pp`, MDD `2.6765pp`, Calmar `-0.4322`, TP exits `14`
- `long_tp20_lock_1.5x` vs `base_1.5x`: CAGR `-27.9393pp`, MDD `3.9487pp`, Calmar `-0.5720`, TP exits `9`
- `long_tp30_lock_2x` vs `base_2x`: CAGR `-30.1554pp`, MDD `4.7772pp`, Calmar `-0.5140`, TP exits `9`

## Interpretation
- If long-only TP works materially better than short-only TP, the regime-hold pain is mostly long giveback after extended bullish phases.
- If short-only TP works better, the problem is the opposite: short squeezes are giving back too much.
- If neither side-selective version improves enough, full TP-lock was not too blunt by accident; the issue is more structural.

## Outputs
- Plot: `78_backtest_btcusdt_scale06_adx002_regime_hold_side_tp_lock.png`
- Metrics CSV: `78_backtest_btcusdt_scale06_adx002_regime_hold_side_tp_lock.csv`
- Curves CSV: `78_backtest_btcusdt_scale06_adx002_regime_hold_side_tp_lock_curves.csv`
- Report: `78_backtest_btcusdt_scale06_adx002_regime_hold_side_tp_lock.md`