# Study 69: Periodic Rebalance Sweep on Case1 + Case2

## Setup
- Source combined curve: `shallow6_else2bull` from study 62
- Portfolio is rebalanced to a fixed target case1 weight on a fixed schedule
- Rebalance fee model: `2 * moved_notional * 0.0004`
- This is a capital-allocation overlay only; underlying trade paths are unchanged

## Ranking

| Variant | Total CAGR % | Total MDD % | Total Calmar | Rebalances | Fee Paid | Avg Case1 W |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| rebal_1d_w55 | 122.0592 | 51.5442 | 2.3681 | 1503 | 121.2795 | 0.5499 |
| rebal_4h_w55 | 119.8342 | 51.1384 | 2.3433 | 9013 | 235.8615 | 0.5500 |
| rebal_1d_w50 | 121.8689 | 52.0899 | 2.3396 | 1503 | 119.0939 | 0.4999 |
| rebal_4h_w50 | 119.5681 | 51.6846 | 2.3134 | 9013 | 231.3316 | 0.5000 |
| rebal_1d_w45 | 121.2901 | 52.6962 | 2.3017 | 1503 | 113.9980 | 0.4499 |
| rebal_4h_w45 | 118.9612 | 52.6503 | 2.2595 | 9013 | 221.3175 | 0.4500 |
| rebal_7d_w55 | 115.7118 | 51.5984 | 2.2425 | 215 | 44.5684 | 0.5497 |
| rebal_7d_w50 | 115.4257 | 52.1446 | 2.2136 | 215 | 43.7218 | 0.4997 |
| rebal_7d_w45 | 114.8884 | 52.6906 | 2.1804 | 215 | 41.8917 | 0.4498 |
| hold_no_rebalance | 103.2781 | 50.8536 | 2.0309 | 0 | 0.0000 | 0.6607 |

## Best Variant
- `rebal_1d_w55`: total CAGR `122.0592%`, total MDD `51.5442%`, total Calmar `2.3681`

## Delta vs hold_no_rebalance
- `rebal_1d_w55`: CAGR `18.7811pp`, MDD `0.6906pp`, Calmar `0.3372`
- `rebal_4h_w55`: CAGR `16.5561pp`, MDD `0.2848pp`, Calmar `0.3124`
- `rebal_1d_w50`: CAGR `18.5908pp`, MDD `1.2363pp`, Calmar `0.3087`
- `rebal_4h_w50`: CAGR `16.2900pp`, MDD `0.8310pp`, Calmar `0.2825`
- `rebal_1d_w45`: CAGR `18.0120pp`, MDD `1.8426pp`, Calmar `0.2708`
- `rebal_4h_w45`: CAGR `15.6831pp`, MDD `1.7967pp`, Calmar `0.2286`
- `rebal_7d_w55`: CAGR `12.4337pp`, MDD `0.7448pp`, Calmar `0.2117`
- `rebal_7d_w50`: CAGR `12.1476pp`, MDD `1.2910pp`, Calmar `0.1827`
- `rebal_7d_w45`: CAGR `11.6103pp`, MDD `1.8370pp`, Calmar `0.1495`

## Interpretation
- No periodic rebalance variant dominated the hold baseline on both CAGR and MDD.
- If rebalancing alone helps materially, then a large part of the opportunity is portfolio construction rather than entry logic.
- If only very frequent rebalancing helps, robustness to fees should be treated as the next validation step.

## Outputs
- Plot: `69_backtest_btcusdt_scale06_adx002_rebalance_schedule_sweep.png`
- Metrics CSV: `69_backtest_btcusdt_scale06_adx002_rebalance_schedule_sweep.csv`
- Curves CSV: `69_backtest_btcusdt_scale06_adx002_rebalance_schedule_sweep_curves.csv`
- Report: `69_backtest_btcusdt_scale06_adx002_rebalance_schedule_sweep.md`