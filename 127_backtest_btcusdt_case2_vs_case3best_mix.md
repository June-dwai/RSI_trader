# 127 연구: case2 vs 126 best case3 vs 50:50 혼합

## 설정
- 공정 비교 구간: `2021-01-02 00:00:00` ~ `2026-03-15 05:30:00`
- 로컬 최신 캐시 종료 시각: `2026-03-15 05:19:00`
- case3 후보는 126 raw-best인 `lb4_delay8_capna_cd0`를 사용했다.
- 세 번째 곡선은 `case2 50% + case3best 50%`를 시작 시점에 고정한 정적 혼합이다.
- 리밸런싱 없이 보유 비중만 고정했다.

## 결과
| Variant | Final Equity | Total Return % | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| case2_only | 130370.9573 | 6418.5479 | 123.3942 | 73.7105 | 1.6740 | 12.1671 | 35.3099 |
| lb4_delay8_capna_cd0_only | 335648.4751 | 16682.4238 | 167.9773 | 64.5809 | 2.6010 | -11.5764 | 33.1473 |
| case2_case3best_half_mix | 233009.7162 | 11550.4858 | 149.8032 | 55.5628 | 2.6961 | -6.0105 | 33.4685 |

## 해석
- 수익 극대화 기준으로는 `lb4_delay8_capna_cd0_only`가 가장 강했다. CAGR `167.9773%`, final equity `335648.4751`.
- 방어 효율까지 보면 `case2_case3best_half_mix`가 꽤 좋다. CAGR `149.8032%`, MDD `55.5628%`, Calmar `2.6961`.
- `case2_only`는 여전히 의미가 있지만, 지금 비교에선 알파의 중심이 아니라 완충재에 더 가깝다. CAGR `123.3942%`, MDD `73.7105%`.
- 2026만 보면 `case3best`가 그대로 제일 강한지는 별도로 봐야 한다. `case3best 2026 = -11.5764%`, `mix 2026 = -6.0105%`, `case2 2026 = 12.1671%`.

## 결론
- `case3best 단독`은 고CAGR 코어 후보다.
- `case2 + case3best 50:50`은 CAGR을 조금 내주고 MDD를 줄이는 타협안이다.
- 앞으로 포트폴리오화할 때는 `case3best`를 코어로 두고 `case2`를 완충 슬리브로 얹는 방향이 자연스럽다.

## 출력물
- Plot: `127_backtest_btcusdt_case2_vs_case3best_mix.png`
- Metrics CSV: `127_backtest_btcusdt_case2_vs_case3best_mix.csv`
- Curves CSV: `127_backtest_btcusdt_case2_vs_case3best_mix_curves.csv`
- Report: `127_backtest_btcusdt_case2_vs_case3best_mix.md`