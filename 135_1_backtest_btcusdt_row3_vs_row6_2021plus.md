# 135_1번 연구: 134 최고전략표 3행 vs 6행을 2021~로컬최신까지 다시 비교

## 비교 대상
- 3행 2021+ 복원본: `study120_current_mix` from study 121
- 6행 2021+ raw engine: `lb4_delay8_capna_cd0` from study 126
- 이번 비교는 두 전략을 모두 `2000 USDT` 기준으로 맞췄다.
- 6행은 원본 126 curve가 `1000 USDT` 시작이라, 같은 비교를 위해 equity를 `x2` 스케일링했다.
- 공통 비교 구간은 `2021-01-02 00:00:00` ~ `2026-03-15 05:15:00` 이다.
- 참고로 오늘 날짜는 `2026-04-12`이지만, 로컬 최신 BTC 1분 캐시는 `2026-03-15`까지만 있다.

## 결과 표

| Strategy | Final Equity | Total Return % | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| row3_2021plus_study120_mix | 105840.5947 | 5192.0297 | 114.6123 | 64.4942 | 1.7771 | -1.2406 | 23.7556 |
| row6_2021plus_study126_case3 | 334014.3555 | 16600.7178 | 167.7272 | 64.5809 | 2.5972 | -12.0069 | 33.1473 |

## 핵심 해석
- CAGR 우위는 `row6_2021plus_study126_case3`였다. `167.7272%`로 더 높았다.
- MDD 방어 우위는 `row3_2021plus_study120_mix`였다. MDD `64.4942%`로 더 낮았다.
- Calmar 우위는 `row6_2021plus_study126_case3`였다. 위험조정 효율은 이쪽이 더 좋았다.
- 2026 구간 수익 우위는 `row3_2021plus_study120_mix`였다. 2026 return `-1.2406%`.

## 읽는 방법
- 3행은 `case1/case2/case3`를 섞은 포트폴리오라 변동을 깎는 대신 최고 수익을 일부 포기한다.
- 6행은 단일 case3 엔진이라 방향이 맞을 때 더 강하지만, drawdown도 더 크게 받는다.
- 따라서 2021+ 전체 구간에서도 핵심 구도는 그대로다. `6행 = 고수익 엔진`, `3행 = 실전형 완충 포트폴리오`.

## 산출물
- Metrics CSV: `135_1_backtest_btcusdt_row3_vs_row6_2021plus.csv`
- Curves CSV: `135_1_backtest_btcusdt_row3_vs_row6_2021plus_curves.csv`
- Plot: `135_1_backtest_btcusdt_row3_vs_row6_2021plus.png`
- Report: `135_1_backtest_btcusdt_row3_vs_row6_2021plus.md`
