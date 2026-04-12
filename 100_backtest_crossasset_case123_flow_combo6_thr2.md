# 100번 연구: BTC/ETH/XRP 실제 case123 + flow_combo6_thr2 비교

## 설정
- 상태 센서만 바꾸는 것이 아니라, case1/case2/case3 매매 자체를 BTC/ETH/XRP 각각에 실제로 적용한다.
- case1: `shallow6_else2bull`
- case2: study-42 baseline case2
- case3: `short_gate_24h_g12_tp15`
- 포트폴리오 운용은 98 best와 동일한 `flow_combo6_thr2`이다.

## 포트폴리오 결과

| Symbol | Final Equity | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid | Avg Case3 Weight % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | 334129.3707 | 108.1206 | 46.3452 | 2.3329 | 100.9514 | 231 | 1017.4494 | 7.0516 |
| ETHUSDT | 123409.6086 | 43.8071 | 73.6627 | 0.5947 | 42.6976 | 374 | 465.9142 | 7.0425 |
| XRPUSDT | 25119.7053 | -60.2753 | 98.6559 | -0.6110 | -32.3543 | 330 | 88.7937 | 7.0098 |

## Sleeve Standalone

| Symbol | Sleeve | Final Equity | CAGR % | MDD % | Calmar |
| --- | --- | ---: | ---: | ---: | ---: |
| BTCUSDT | case1 | 18280.9355 | 99.7598 | 61.0421 | 1.6343 |
| BTCUSDT | case2 | 13639.7373 | 86.3034 | 74.0774 | 1.1650 |
| BTCUSDT | case3 | 7215.4602 | 60.0923 | 56.5941 | 1.0618 |
| ETHUSDT | case1 | 1402.5636 | 8.3890 | 78.4558 | 0.1069 |
| ETHUSDT | case2 | 7190.8259 | 59.9620 | 77.7440 | 0.7713 |
| ETHUSDT | case3 | 1273.0909 | 5.9179 | 82.4872 | 0.0717 |
| XRPUSDT | case1 | 0.0000 | -100.0000 | 100.0000 | -1.0000 |
| XRPUSDT | case2 | 0.0000 | -100.0000 | 100.0000 | -1.0000 |
| XRPUSDT | case3 | 137.3710 | -37.6675 | 98.0986 | -0.3840 |

## 해석
- best symbol: `BTCUSDT`
- 이번 비교는 진짜로 심볼별 매매를 다시 돌린 결과라, curve가 거의 같아 보이면 안 된다. 실제로 심볼별 sleeve와 포트폴리오 결과가 모두 따로 계산된다.

## 산출물
- 플롯: `100_backtest_crossasset_case123_flow_combo6_thr2.png`
- 성과 CSV: `100_backtest_crossasset_case123_flow_combo6_thr2.csv`
- 곡선 CSV: `100_backtest_crossasset_case123_flow_combo6_thr2_curves.csv`
- sleeve CSV: `100_backtest_crossasset_case123_flow_combo6_thr2_components.csv`
- 보고서: `100_backtest_crossasset_case123_flow_combo6_thr2.md`