# 89번 연구: Case123 Drawdown Governor Sweep

## 설정
- 기준 포트폴리오는 88번 연구에서 가장 강했던 `case123 + threshold 2%` 구조다.
- 월 적립금은 기존과 동일하게 매월 첫 시점에 `1000` 달러를 넣는다.
- drawdown governor는 포트폴리오의 flow-adjusted NAV drawdown이 커질수록 위험자산 비중을 줄이고, 남는 비중은 현금으로 둔다.
- 리스크 슬리브 비중은 줄어들지만, `case1:case2:case3 = 62:31:7`의 내부 비율은 유지한다.
- 공통 구간: `2022-01-01 08:00:00` -> `2026-03-15 05:19:00`

## 결과

| Variant | Final Equity | Net Profit | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Avg Exposure % | Min Exposure % | Rebalances | Fee Paid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| base_thr2_nogov | 350830.0220 | 298830.0220 | 110.6127 | 46.7783 | 2.3646 | 104.1222 | 100.0000 | 100.0000 | 250 | 577.8687 |
| twostep_15_25 | 226592.1149 | 174592.1149 | 81.3429 | 40.7014 | 1.9985 | 76.8368 | 80.1203 | 65.0000 | 349 | 1737.0361 |
| ultrasoft_15_25_35 | 226953.5021 | 174953.5021 | 84.6216 | 44.5373 | 1.9000 | 76.9318 | 89.6304 | 70.0000 | 360 | 1393.5020 |
| soft_12_20_30 | 187231.6109 | 135231.6109 | 71.5897 | 40.8295 | 1.7534 | 65.6784 | 78.8698 | 60.0000 | 417 | 1966.1945 |
| mid_10_18_26 | 178037.9714 | 126037.9714 | 66.7329 | 38.9691 | 1.7125 | 62.8040 | 72.6501 | 55.0000 | 401 | 1845.2541 |
| hard_8_15_22 | 145763.8328 | 93763.8328 | 54.8690 | 32.4487 | 1.6909 | 51.6591 | 57.2083 | 40.0000 | 379 | 1733.2210 |

## 핵심 해석
- best governor: `base_thr2_nogov` (`TWR CAGR 110.6127%`, `MDD 46.7783%`, `XIRR 104.1222%`).
- best vs base: TWR CAGR `0.0000pp`, MDD `0.0000pp`, XIRR `0.0000pp`, fee `0.0000`.
- governor가 잘 먹히면 `대형 손실 구간에서 현금 비중을 늘려 MDD를 줄이면서`, 회복 구간에서는 다시 위험자산 비중을 복구한다.
- 너무 공격적인 governor는 MDD는 줄여도 상승 구간 노출을 너무 많이 잃어서 CAGR/XIRR이 꺾일 수 있다.

## 산출물
- 플롯: `89_backtest_btcusdt_scale06_adx002_case123_drawdown_governor_sweep.png`
- 성과 CSV: `89_backtest_btcusdt_scale06_adx002_case123_drawdown_governor_sweep.csv`
- 곡선 CSV: `89_backtest_btcusdt_scale06_adx002_case123_drawdown_governor_sweep_curves.csv`
- 보고서: `89_backtest_btcusdt_scale06_adx002_case123_drawdown_governor_sweep.md`