# 121 연구: case1/case2/case3 단독 vs 현재 혼합 포트폴리오 비교

## 설정
- 현재 날짜는 `2026-04-11`이지만, 로컬 최신 BTCUSDT 1분 캐시는 `2026-03-15 05:19:00`까지 있다.
- 따라서 이번 비교는 `2021-01-01`부터 데이터를 불러오되, 실제 공정 비교 구간은 모든 곡선이 겹치는 공통 구간으로 맞췄다.
- 공통 비교 구간: `2021-01-02 00:00:00` ~ `2026-03-15 05:15:00`
- 기준 자본은 모든 비교에서 `2000 USDT`로 통일했다.

## 비교 대상
- `case1_only`: study 62의 `shallow6_else2bull` case1 sleeve 단독
- `case2_only`: study 42의 case2 sleeve 단독
- `case3_only`: 현재 혼합 포트폴리오가 쓰는 case3 source `lv3p0_g12_body25_tp20_lb5_none` 단독
- `study119_current_mix`: 현재 혼합 정의서의 `49/27/24`, `1h rebalance`
- `study120_current_mix`: 최근 CAGR winner의 `46/24/30`, `30min rebalance`

## 결과 표

| Variant | Type | Rebalance | W1 | W2 | W3 | Final Equity | CAGR % | MDD % | Calmar | Trades |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| case1_only | solo | none | 1.00 | 0.00 | 0.00 | 6658.5143 | 26.0401 | 77.9521 | 0.3341 | 505 |
| case2_only | solo | none | 0.00 | 1.00 | 0.00 | 130370.9573 | 123.3952 | 73.7137 | 1.6740 | 2057 |
| case3_only | solo | none | 0.00 | 0.00 | 1.00 | 239316.8078 | 151.0915 | 64.5809 | 2.3396 | 123 |
| study119_current_mix | mix | 1h | 0.49 | 0.27 | 0.24 | 78427.4347 | 102.5839 | 65.8846 | 1.5570 | N/A |
| study120_current_mix | mix | 30min | 0.46 | 0.24 | 0.30 | 105840.5947 | 114.6123 | 64.4942 | 1.7771 | N/A |

## 한눈에 보기
- 최고 CAGR: `case3_only` -> `151.0915%`
- 최고 Calmar: `case3_only` -> `2.3396`
- 최저 MDD: `study120_current_mix` -> `64.4942%`
- 120 mix vs 119 mix: CAGR `12.0284pp`, MDD `-1.3905pp`, Calmar `0.2201`

## 해석
- 단독 sleeve와 혼합 포트폴리오를 같은 기간에 맞춰 보면, 현재 알파의 대부분이 어느 sleeve에서 나오고 있는지 더 명확히 볼 수 있다.
- 특히 `case3_only`가 강한데도 혼합에서 더 좋아진다면, case3 자체 알파와 case1/case2 분산효과가 동시에 작동한 것으로 볼 수 있다.
- 반대로 단독 sleeve보다 혼합이 약하다면, 현재 비중이나 리밸런스가 알파를 깎고 있는지 다시 봐야 한다.

## 산출물
- Plot: `121_backtest_btcusdt_solo_vs_current_mix_2021plus.png`
- Metrics CSV: `121_backtest_btcusdt_solo_vs_current_mix_2021plus.csv`
- Curves CSV: `121_backtest_btcusdt_solo_vs_current_mix_2021plus_curves.csv`
- Report: `121_backtest_btcusdt_solo_vs_current_mix_2021plus.md`