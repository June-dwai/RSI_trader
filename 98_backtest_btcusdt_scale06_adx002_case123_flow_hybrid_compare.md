# 98번 연구: Case123 Flow Hybrid Compare

## 설정
- 91 hybrid 구조 위에 96의 flow-state target weights를 얹는다.
- 월 top-up은 현재 target weights 기준 underweight 쪽에 먼저 넣는다.
- 전체 리밸런싱은 4시간 경계에서 drift threshold를 넘을 때만 한다.

## 결과

| Variant | Mode | Threshold %p | Final Equity | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | State Switches | Fee Paid |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| flow_combo6_thr2 | flow_combo6 | 2.0000 | 359286.5619 | 112.3102 | 45.1238 | 2.4889 | 105.6884 | 228 | 42 | 1072.1702 |
| flow_sell6_thr2 | flow_sell6 | 2.0000 | 358356.7208 | 112.1764 | 45.1238 | 2.4860 | 105.5182 | 218 | 34 | 933.7289 |
| static_thr2 | static | 2.0000 | 351459.8005 | 111.1843 | 45.1238 | 2.4640 | 104.2447 | 190 | 0 | 487.5090 |
| flow_combo6_thr4 | flow_combo6 | 4.0000 | 355960.8486 | 111.3878 | 45.3316 | 2.4572 | 105.0780 | 92 | 42 | 831.5183 |
| flow_sell6_thr4 | flow_sell6 | 4.0000 | 355253.8848 | 111.2864 | 45.3316 | 2.4549 | 104.9476 | 84 | 34 | 703.8977 |
| static_thr4 | static | 4.0000 | 351553.9997 | 110.7474 | 45.3316 | 2.4431 | 104.2622 | 55 | 0 | 286.2287 |

## 해석
- best variant: `flow_combo6_thr2`
- best vs static_thr4: TWR CAGR `1.5628pp`, MDD `-0.2078pp`, XIRR `1.4261pp`, fee `785.9415`.

## 산출물
- 플롯: `98_backtest_btcusdt_scale06_adx002_case123_flow_hybrid_compare.png`
- 성과 CSV: `98_backtest_btcusdt_scale06_adx002_case123_flow_hybrid_compare.csv`
- 곡선 CSV: `98_backtest_btcusdt_scale06_adx002_case123_flow_hybrid_compare_curves.csv`
- 보고서: `98_backtest_btcusdt_scale06_adx002_case123_flow_hybrid_compare.md`