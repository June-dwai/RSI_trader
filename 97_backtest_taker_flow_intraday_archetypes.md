# 97번 연구: Taker Flow Intraday Archetypes

## 설정
- BTC 1시간봉 taker flow와 4시간 confirmed trend를 결합한 standalone 구조다.
- reclaim은 liquidity sweep 후 aggressive taker flow를 확인하고 되돌림을 먹는다.
- follow는 aggressive taker flow가 돌파를 동반할 때 추세를 따라간다.

## 결과

| Variant | Entry Type | Final Equity | CAGR % | MDD % | Calmar | Trades | Fee Paid |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| flow_follow_dual_48h_x100 | follow | 996.2330 | -0.0901 | 21.2372 | -0.0042 | 430 | 163.9398 |
| flow_follow_dual_24h_x100 | follow | 912.3680 | -2.1641 | 26.0724 | -0.0830 | 596 | 206.6155 |
| flow_reclaim_dual_24h_x100 | reclaim | 705.5988 | -7.9823 | 32.0630 | -0.2490 | 570 | 187.8865 |
| flow_reclaim_dual_24h_x125 | reclaim | 642.6197 | -10.0119 | 38.6987 | -0.2587 | 570 | 223.2304 |

## 해석
- best variant: `flow_follow_dual_48h_x100`
- 이 연구는 taker-flow 자체만으로 standalone 알파가 있는지 확인하는 목적이다.

## 산출물
- 플롯: `97_backtest_taker_flow_intraday_archetypes.png`
- 성과 CSV: `97_backtest_taker_flow_intraday_archetypes.csv`
- 곡선 CSV: `97_backtest_taker_flow_intraday_archetypes_curves.csv`
- 보고서: `97_backtest_taker_flow_intraday_archetypes.md`