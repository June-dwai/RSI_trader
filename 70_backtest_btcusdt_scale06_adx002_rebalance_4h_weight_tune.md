# Study 70: 4H Rebalance Weight Tuning

## Setup
- Base portfolio logic is study 69's fee-aware periodic rebalance engine
- Focus range: `4h rebalance` with `case1 target weight 0.70~0.76`
- Goal: convert the study-69 scan into a concrete next baseline candidate

## Ranking

| Variant | Total CAGR % | Total MDD % | Total Calmar | Fee Paid |
| --- | ---: | ---: | ---: | ---: |
| rebal_4h_w74 | 117.7454 | 49.1509 | 2.3956 | 196.4671 |
| rebal_4h_w75 | 117.5013 | 49.0504 | 2.3955 | 191.8060 |
| rebal_4h_w72 | 118.1938 | 49.3532 | 2.3949 | 205.0147 |
| rebal_4h_w70 | 118.5892 | 49.5572 | 2.3930 | 212.5225 |
| rebal_4h_w76 | 117.2441 | 49.0129 | 2.3921 | 186.8885 |
| hold_no_rebalance | 103.2781 | 50.8536 | 2.0309 | 0.0000 |

## Best Variant
- `rebal_4h_w74`: total CAGR `117.7454%`, total MDD `49.1509%`, total Calmar `2.3956`

## Delta vs hold_no_rebalance
- `rebal_4h_w74`: CAGR `14.4672pp`, MDD `-1.7027pp`, Calmar `0.3647`
- `rebal_4h_w75`: CAGR `14.2232pp`, MDD `-1.8032pp`, Calmar `0.3646`
- `rebal_4h_w72`: CAGR `14.9157pp`, MDD `-1.5004pp`, Calmar `0.3640`
- `rebal_4h_w70`: CAGR `15.3110pp`, MDD `-1.2964pp`, Calmar `0.3621`
- `rebal_4h_w76`: CAGR `13.9660pp`, MDD `-1.8407pp`, Calmar `0.3612`

## Interpretation
- Multiple 4h rebalance variants dominate the hold baseline on both CAGR and MDD.
- This is the first clear structural win in the recent study chain: portfolio construction improved both growth and drawdown.
- The next validation step should test whether this edge survives a more realistic execution model or lower-frequency rebalance constraints.

## Outputs
- Plot: `70_backtest_btcusdt_scale06_adx002_rebalance_4h_weight_tune.png`
- Metrics CSV: `70_backtest_btcusdt_scale06_adx002_rebalance_4h_weight_tune.csv`
- Curves CSV: `70_backtest_btcusdt_scale06_adx002_rebalance_4h_weight_tune_curves.csv`
- Report: `70_backtest_btcusdt_scale06_adx002_rebalance_4h_weight_tune.md`