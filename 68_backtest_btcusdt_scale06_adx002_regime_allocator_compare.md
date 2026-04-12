# Study 68: Dynamic Regime Allocation Between Case1 and Case2

## Setup
- Source combined curve: `shallow6_else2bull` from study 62
- Allocation logic uses only confirmed 4h trend and lagged case1 drawdown
- Rebalance happens only on 4h bucket transitions, so there is no future leak from same-bucket information
- This changes capital allocation, not the underlying trade path of either sleeve

## Ranking

| Variant | Total CAGR % | Total MDD % | Total Calmar | Avg Case1 W | Bear Case1 W |
| --- | ---: | ---: | ---: | ---: | ---: |
| rebal_eq50_4h | 120.8035 | 52.0320 | 2.3217 | 0.5000 | 0.5000 |
| trend70_35 | 121.2816 | 56.2581 | 2.1558 | 0.5263 | 0.3500 |
| hold_50_50_baseline | 103.2781 | 50.8536 | 2.0309 | 0.6607 | 0.6450 |
| trend80_20 | 117.9424 | 61.4916 | 1.9180 | 0.5022 | 0.2000 |
| trend80_10_dd20 | 117.4438 | 62.3916 | 1.8824 | 0.4688 | 0.1327 |
| trend85_10_dd15 | 116.1612 | 64.1434 | 1.8110 | 0.4834 | 0.1114 |
| trend90_10 | 114.1126 | 65.5288 | 1.7414 | 0.5029 | 0.1000 |

## Best Variant
- `rebal_eq50_4h`: total CAGR `120.8035%`, total MDD `52.0320%`, total Calmar `2.3217`

## Delta vs hold_50_50_baseline
- `rebal_eq50_4h`: CAGR `17.5254pp`, MDD `1.1784pp`, Calmar `0.2908`
- `trend70_35`: CAGR `18.0034pp`, MDD `5.4044pp`, Calmar `0.1249`
- `trend80_20`: CAGR `14.6643pp`, MDD `10.6380pp`, Calmar `-0.1129`
- `trend80_10_dd20`: CAGR `14.1656pp`, MDD `11.5380pp`, Calmar `-0.1485`
- `trend85_10_dd15`: CAGR `12.8831pp`, MDD `13.2898pp`, Calmar `-0.2199`
- `trend90_10`: CAGR `10.8344pp`, MDD `14.6752pp`, Calmar `-0.2895`

## Interpretation
- No tested regime allocator dominated the existing hold baseline on both CAGR and MDD.
- If trend allocators help, then the next structural lever is capital routing, not more micro-edits inside case1.
- If trend allocators still fail, then the core return streams themselves need replacement rather than redistribution.

## Outputs
- Plot: `68_backtest_btcusdt_scale06_adx002_regime_allocator_compare.png`
- Metrics CSV: `68_backtest_btcusdt_scale06_adx002_regime_allocator_compare.csv`
- Curves CSV: `68_backtest_btcusdt_scale06_adx002_regime_allocator_compare_curves.csv`
- Report: `68_backtest_btcusdt_scale06_adx002_regime_allocator_compare.md`