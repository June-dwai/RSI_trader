# 104 Study: BTC flow_combo6_thr2 with 2021 data

## Setup
- Added real 2021 BTCUSDT futures archive data to the local cache.
- Rebuilt case1/case2/case3 from 2021-01-01, then reran current BTC best candidate (`flow_combo6_thr2`).
- Common period: `2021-01-01 08:00:00` -> `2026-03-15 05:15:00`

## Results

| Variant | Final Equity | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | State Switches | Fee Paid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| flow_combo6_thr2_2021 | 469937.7647 | 71.5818 | 70.1544 | 1.0203 | 82.4334 | 380 | 58 | 1545.4072 |
| static_thr2_2021 | 459596.8758 | 70.8883 | 70.1544 | 1.0105 | 81.3893 | 326 | 0 | 748.5786 |

## Compare To Old 98 Result

- Old `flow_combo6_thr2` TWR CAGR: `112.3102%`
- Old `flow_combo6_thr2` TWR MDD: `45.1238%`
- Old `flow_combo6_thr2` XIRR: `105.6884%`
- New vs old: CAGR `-40.7284pp`, MDD `25.0307pp`, XIRR `-23.2549pp`.