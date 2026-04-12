# 96번 연구: Case123 Flow Proxy State Sweep

## 설정
- 가격-only stress proxy 대신 4시간 taker imbalance와 volume shock을 사용한다.
- bearish sell climax에서는 case3 비중을 키우고, bearish squeeze risk에서는 case3 비중을 줄인다.
- 월 1000달러 top-up, 4시간 리밸런싱, drift threshold 2%를 유지한다.

## 결과

| Variant | Final Equity | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | State Switches | Fee Paid | Avg Case3 Weight % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| flow_combo6 | 358567.9160 | 112.1950 | 45.1173 | 2.4867 | 105.5568 | 277 | 42 | 1113.3633 | 7.0516 |
| flow_sell6_w12 | 358032.2983 | 112.1176 | 45.1173 | 2.4850 | 105.4587 | 268 | 34 | 983.9055 | 7.0587 |
| flow_combo3 | 355397.9373 | 111.7441 | 45.1173 | 2.4767 | 104.9742 | 279 | 46 | 1120.2667 | 7.0228 |
| flow_sell3_w12 | 354949.1216 | 111.6785 | 45.1173 | 2.4753 | 104.8914 | 269 | 36 | 995.0954 | 7.0293 |
| flow_combo3_eup | 354464.4530 | 111.6097 | 45.1173 | 2.4738 | 104.8019 | 306 | 78 | 1365.4574 | 7.0113 |
| base_static | 351422.0317 | 111.1631 | 45.1173 | 2.4639 | 104.2377 | 241 | 0 | 532.8002 | 7.0000 |

## 해석
- best variant: `flow_combo6`
- best vs base: TWR CAGR `1.0318pp`, MDD `0.0000pp`, XIRR `1.3192pp`, fee `580.5632`.

## 산출물
- 플롯: `96_backtest_btcusdt_scale06_adx002_case123_flow_proxy_sweep.png`
- 성과 CSV: `96_backtest_btcusdt_scale06_adx002_case123_flow_proxy_sweep.csv`
- 곡선 CSV: `96_backtest_btcusdt_scale06_adx002_case123_flow_proxy_sweep_curves.csv`
- 시장 상태 CSV: `96_backtest_btcusdt_scale06_adx002_case123_flow_proxy_sweep_market_state_4h.csv`
- 보고서: `96_backtest_btcusdt_scale06_adx002_case123_flow_proxy_sweep.md`