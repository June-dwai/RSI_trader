# 90번 연구: Stress Proxy State Sweep

## 설정
- 로컬에 funding/OI 캐시가 없어서, 90번은 `가격 기반 deleveraging/stress proxy`로 대체했다.
- 공통 최신 슬리브 곡선과 4시간 상태 지표를 같이 저장해서 이후 연구(91, 92)가 재활용할 수 있게 했다.
- baseline은 `case123 + threshold 2%`의 고정 비중 구조다.
- stress state가 감지되면 case3 비중을 키우고 case1 비중을 줄이는 방식으로 동적 가중치를 건다.
- 일부 variant는 bullish impulse 구간에서 case3 비중을 0으로 줄여 squeeze 구간 노출을 낮춘다.
- 공통 구간: `2022-01-01 08:00:00` -> `2026-03-15 05:19:00`

## 결과

| Variant | Final Equity | Net Profit | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid | Avg Case3 W % | State Switches |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| stress6_w12 | 359471.1390 | 307471.1390 | 111.7142 | 46.2598 | 2.4149 | 105.7218 | 609 | 2811.1178 | 7.9267 | 414 |
| stress3_w12 | 360113.3941 | 308113.3941 | 111.2087 | 46.3433 | 2.3997 | 105.8391 | 709 | 3549.0048 | 7.5309 | 522 |
| stress3_w15 | 354889.2757 | 302889.2757 | 109.5679 | 46.1670 | 2.3733 | 104.8800 | 710 | 5329.8294 | 7.8494 | 522 |
| stress3_w10 | 350599.0532 | 298599.0532 | 110.0608 | 46.4882 | 2.3675 | 104.0841 | 708 | 2260.8169 | 7.3185 | 522 |
| base_static | 350890.1531 | 298890.1531 | 110.5695 | 46.7763 | 2.3638 | 104.1383 | 247 | 550.8431 | 7.0000 | 0 |
| stress3_w12_bullcut | 337442.0658 | 285442.0658 | 106.8415 | 47.1982 | 2.2637 | 101.5945 | 1175 | 7467.4645 | 6.8236 | 1008 |

## 핵심 해석
- best variant: `stress6_w12`
- best vs baseline: TWR CAGR `1.1447pp`, MDD `-0.5165pp`, XIRR `1.5835pp`.
- 이 연구는 진짜 perp positioning 데이터가 아니라 `가격/변동성 기반 proxy`라는 점을 반드시 감안해야 한다.

## 산출물
- 플롯: `90_backtest_btcusdt_scale06_adx002_case123_stress_proxy_sweep.png`
- 성과 CSV: `90_backtest_btcusdt_scale06_adx002_case123_stress_proxy_sweep.csv`
- 곡선 CSV: `90_backtest_btcusdt_scale06_adx002_case123_stress_proxy_sweep_curves.csv`
- 최신 슬리브 캐시: `90_backtest_btcusdt_scale06_adx002_case123_stress_proxy_sweep_latest_case_curves.csv`
- 4시간 상태 캐시: `90_backtest_btcusdt_scale06_adx002_case123_stress_proxy_sweep_market_state_4h.csv`
- 보고서: `90_backtest_btcusdt_scale06_adx002_case123_stress_proxy_sweep.md`