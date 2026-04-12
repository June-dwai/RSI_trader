# 125 연구: case2 / case3 / 50:50 정적 혼합 비교

## 구간
- 공정 비교 구간: `2021-01-02 00:00:00` ~ `2026-03-15 05:30:00`
- 로컬 최신 캐시 종료 시각: `2026-03-15 05:19:00`
- 리밸런싱 없이 시작 시점에 `case2 50% + case3 50%`로 고정한 정적 혼합을 함께 비교했다.

## 결과
| Variant | Final Equity | Total Return % | CAGR % | MDD % | Calmar |
| --- | ---: | ---: | ---: | ---: | ---: |
| case2_only | 130370.9573 | 6418.5479 | 123.3942 | 73.7105 | 1.6740 |
| case3_only | 240487.4064 | 11924.3703 | 151.3261 | 64.5809 | 2.3432 |
| case2_case3_half_mix | 185429.1818 | 9171.4591 | 139.0623 | 55.5628 | 2.5028 |

## 해석
- CAGR 기준으로는 `case3_only (151.3261%)`가 `case2_only (123.3942%)`와 `50:50 mix (139.0623%)`를 모두 앞섰다.
- MDD도 `case3_only (64.5809%)`가 `case2_only (73.7105%)`보다 낮았다.
- `50:50 mix`는 `case2`보다 훨씬 좋아졌지만, 결국 `case3`의 알파를 희석해서 CAGR이 `12.2638%p` 낮아졌다.
- 정리하면 현재 2021~최신 구간에서는 `case3가 메인 엔진`, `case2는 완충재`, `반반 혼합은 중간 성격`으로 보는 게 맞다.

## 출력물
- Plot: `125_backtest_btcusdt_case2_case3_half_mix_plot.png`
- Metrics CSV: `125_backtest_btcusdt_case2_case3_half_mix_plot.csv`
- Report: `125_backtest_btcusdt_case2_case3_half_mix_plot.md`