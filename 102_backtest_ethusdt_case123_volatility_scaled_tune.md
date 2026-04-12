# 102 Study: ETH vol-scaled sleeve tuning

## Setup
- Treat ETH as higher-vol than BTC and retune case1/case3 absolute thresholds.
- case1 axes: lower entry_scale, deeper RSI, wider DCA gap, wider TP/SL, wider hedge release gap.
- case3 axes: lower leverage, wider stop, wider TP, longer gate duration.
- case2 stays unchanged because it survived best on ETH.
- Portfolio uses monthly 1000 top-up plus threshold 2% rebalance.

## Sleeves

| Sleeve | Variant | Final Equity | CAGR % | MDD % | Calmar | Trades |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| case1 | eth_v2_deep_case1 | 3737.0651 | 36.8718 | 42.2020 | 0.8737 | 162 |
| case1 | eth_v2_loose_case1 | 2522.8185 | 24.6479 | 52.3617 | 0.4707 | 159 |
| case1 | eth_v2_bal_case1 | 2382.9135 | 22.9662 | 61.3489 | 0.3744 | 162 |
| case1 | btc_ref_case1 | 1398.9818 | 8.3219 | 78.4558 | 0.1061 | 239 |
| case2 | baseline_case2 | 7125.3375 | 59.6043 | 77.7440 | 0.7667 | 1953 |
| case3 | eth_v2_deep_case3 | 4148.1210 | 40.3212 | 58.1825 | 0.6930 | 121 |
| case3 | eth_v2_slow_case3 | 3022.7039 | 30.1344 | 56.6396 | 0.5320 | 122 |
| case3 | eth_v2_bal_case3 | 2690.6188 | 26.5776 | 68.6254 | 0.3873 | 128 |
| case3 | eth_v2_wide_case3 | 2153.1871 | 20.0366 | 69.6933 | 0.2875 | 130 |
| case3 | btc_ref_case3 | 1273.0909 | 5.9179 | 82.4872 | 0.0717 | 137 |

## Portfolio

| Variant | Weights | Final Equity | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| btc_62_31_07__eth_v2_deep_case1__eth_v2_deep_case3 | `0.62/0.31/0.07` | 197285.6367 | 68.8196 | 48.3345 | 1.4238 | 68.6951 | 330 | 386.1456 |
| btc_62_31_07__eth_v2_deep_case1__eth_v2_slow_case3 | `0.62/0.31/0.07` | 193699.0123 | 67.6278 | 48.4587 | 1.3956 | 67.6335 | 327 | 378.4580 |
| btc_62_31_07__eth_v2_deep_case1__eth_v2_bal_case3 | `0.62/0.31/0.07` | 193313.8632 | 68.2763 | 49.0953 | 1.3907 | 67.5185 | 339 | 382.0653 |
| btc_62_31_07__eth_v2_deep_case1__eth_v2_wide_case3 | `0.62/0.31/0.07` | 192660.6253 | 67.3083 | 49.1764 | 1.3687 | 67.3232 | 336 | 377.5687 |
| btc_62_31_07__eth_v2_deep_case1__btc_ref_case3 | `0.62/0.31/0.07` | 194471.5602 | 66.7629 | 50.0769 | 1.3332 | 67.8635 | 339 | 383.2972 |
| eth_30_70_00__eth_v2_deep_case1__eth_v2_bal_case3 | `0.30/0.70/0.00` | 205537.8332 | 79.0848 | 64.8152 | 1.2202 | 71.0804 | 315 | 383.8765 |
| eth_30_70_00__eth_v2_deep_case1__eth_v2_wide_case3 | `0.30/0.70/0.00` | 205537.8332 | 79.0848 | 64.8152 | 1.2202 | 71.0804 | 315 | 383.8765 |
| eth_30_70_00__eth_v2_deep_case1__eth_v2_slow_case3 | `0.30/0.70/0.00` | 205537.8332 | 79.0848 | 64.8152 | 1.2202 | 71.0804 | 315 | 383.8765 |
| eth_30_70_00__eth_v2_deep_case1__eth_v2_deep_case3 | `0.30/0.70/0.00` | 205537.8332 | 79.0848 | 64.8152 | 1.2202 | 71.0804 | 315 | 383.8765 |
| eth_30_70_00__eth_v2_deep_case1__btc_ref_case3 | `0.30/0.70/0.00` | 205537.8332 | 79.0848 | 64.8152 | 1.2202 | 71.0804 | 315 | 383.8765 |
| eth_25_70_05__eth_v2_deep_case1__eth_v2_deep_case3 | `0.25/0.70/0.05` | 204529.4219 | 78.8603 | 64.9307 | 1.2145 | 70.7931 | 306 | 379.6882 |
| eth_20_70_10__eth_v2_deep_case1__eth_v2_deep_case3 | `0.20/0.70/0.10` | 202853.0674 | 78.6346 | 65.0301 | 1.2092 | 70.3129 | 291 | 360.3395 |
| eth_25_70_05__eth_v2_deep_case1__eth_v2_bal_case3 | `0.25/0.70/0.05` | 203922.5699 | 78.7766 | 65.2022 | 1.2082 | 70.6197 | 307 | 391.0901 |
| eth_25_70_05__eth_v2_deep_case1__eth_v2_slow_case3 | `0.25/0.70/0.05` | 202311.8302 | 78.0927 | 64.9883 | 1.2016 | 70.1572 | 299 | 375.0347 |
| eth_25_70_05__eth_v2_deep_case1__eth_v2_wide_case3 | `0.25/0.70/0.05` | 204517.2900 | 78.3705 | 65.2400 | 1.2013 | 70.7896 | 306 | 392.6527 |
| eth_20_70_10__eth_v2_deep_case1__eth_v2_bal_case3 | `0.20/0.70/0.10` | 198114.0182 | 77.6637 | 65.4479 | 1.1866 | 68.9382 | 289 | 349.6636 |
| eth_20_70_10__eth_v2_deep_case1__eth_v2_slow_case3 | `0.20/0.70/0.10` | 198415.6184 | 77.2131 | 65.2172 | 1.1839 | 69.0264 | 287 | 348.7981 |
| eth_25_70_05__eth_v2_deep_case1__btc_ref_case3 | `0.25/0.70/0.05` | 201655.3466 | 77.0178 | 65.7675 | 1.1711 | 69.9679 | 296 | 372.2222 |
| eth_20_70_10__eth_v2_deep_case1__eth_v2_wide_case3 | `0.20/0.70/0.10` | 197896.3288 | 76.5828 | 65.5225 | 1.1688 | 68.8744 | 282 | 345.7211 |
| eth_25_75_00__eth_v2_deep_case1__btc_ref_case3 | `0.25/0.75/0.00` | 200764.9198 | 77.8851 | 66.8623 | 1.1649 | 69.7104 | 258 | 320.0803 |

## Summary
- Best case1: `eth_v2_deep_case1` -> CAGR `36.8718`, MDD `42.2020`.
- Best case3: `eth_v2_deep_case3` -> CAGR `40.3212`, MDD `58.1825`.
- Best portfolio: `btc_62_31_07__eth_v2_deep_case1__eth_v2_deep_case3` -> vs baseline CAGR `2.4067pp`, MDD `-25.5946pp`, XIRR `10.5564pp`.