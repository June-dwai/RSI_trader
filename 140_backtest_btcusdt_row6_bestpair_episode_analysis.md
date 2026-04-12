# 140번 연구: row6 최상위 2개 변형의 약점 구간 상세 분석

- 비교 대상은 `unlock_slowbear_24h_2p0`와 `combo_trim2p0_unlock24h`다.
- 분석 구간은 `2021-01-02 00:00:00` ~ `2026-03-15 05:19:00`이다.
- 목적은 단순 수익률 비교가 아니라, 두 전략이 **BTC가 어떤 상태일 때 약해지는지**, 그리고 **왜 하나가 더 실전형으로 보이는지**를 구조적으로 파악하는 것이다.
- 방법은 `136`과 같은 underwater episode 분석이지만, 이번에는 `bulltrim`, `unlock`, `slow_bear_short` 이벤트가 대표 약한 구간에서 실제로 몇 번 발생했는지도 같이 집계했다.

## 먼저 결론

- 두 전략 모두 `138`에서 문제였던 `느린 bear continuation 미대응`은 상당 부분 해결했다.
- 대신 대표 약점이 `slow_bear_short_gap`에서 `two-way whipsaw`로 이동했다.
- 즉, 이제 병목은 “bearish에서 숏을 못 타는 문제”보다 “오르지도 내리지도 않게 흔드는 장세에서 long/short가 번갈아 소모되는 문제”에 더 가깝다.
- `unlock_slowbear_24h_2p0`는 더 강한 엔진이다.
- `combo_trim2p0_unlock24h`는 같은 약한 구간을 더 얕게 맞는 실전형이다.

## 전체 성과 요약

| Variant | CAGR % | MDD % | Calmar | 2026 Return % | 대표 약한 구간 평균 Depth % | 대표 약한 구간 평균 회복일수 | 대표 구간 수 | 최다 라벨 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `unlock_slowbear_24h_2p0` | 206.7044 | 69.9377 | 2.9555 | 15.1415 | 56.4573 | 166.7 | 7 | `two_way_whipsaw` |
| `combo_trim2p0_unlock24h` | 180.7641 | 63.9784 | 2.8254 | 19.1725 | 48.9744 | 142.5 | 8 | `two_way_whipsaw` |

핵심 해석:
- `unlock_slowbear_24h_2p0`는 수익 엔진 1위다.
- `combo_trim2p0_unlock24h`는 CAGR을 조금 양보하는 대신 대표 약한 구간 평균 깊이를 약 `7.48%p` 줄였고, 전체 MDD도 약 `5.96%p` 낮췄다.
- 2026 수익률도 `combo`가 더 좋았다.

## 왜 140이 중요했나

`138`에서 이미 두 best 후보가 나왔지만, 그건 “전체 기간 기준 결과”였다.
- `unlock_slowbear_24h_2p0`: 가장 강한 raw 엔진
- `combo_trim2p0_unlock24h`: 가장 균형적인 실전형

그런데 실전 관점에서는 전체 CAGR보다 더 중요한 질문이 있다.
- 어디서 크게 다치나?
- 그 약점이 trend miss인가, bear miss인가, whipsaw인가?
- `bulltrim`은 진짜로 약한 구간을 줄여주나, 아니면 그냥 수익만 깎나?

이번 140은 바로 그 질문에 대한 답이다.

## 1. `unlock_slowbear_24h_2p0`는 언제 약한가

### 대표 약점 요약

가장 깊거나 오래 걸린 대표 구간을 보면, 이 전략은 세 종류의 약점을 보인다.

1. `fast_selloff_long_stuck`
- 대표 구간: `2021-01-08 12:15:00` -> `2021-01-27 00:30:00` -> `2021-02-17 19:45:00`
- BTC peak-to-trough: `-22.4771%`
- 전략 depth: `64.5809%`
- long 비중: `62.4859%`
- short 비중: `0.1125%`
- flat 비중: `37.4016%`

해석:
- 급락 초입에 long이 너무 오래 남아 있었다.
- 이 구간에는 `bulltrim 0`, `unlock 0`, `slowbear 0`이라서, 후반부 unlock 계열 개선이 아직 개입할 수 없는 유형이다.
- 즉 이 전략의 가장 전통적인 약점은 여전히 완전히 사라지지 않았다.

2. `slow_bear_short_gap`
- 대표 구간: `2022-03-02 15:00:00` -> `2022-03-16 18:30:00` -> `2022-05-09 02:30:00`
- BTC peak-to-trough: `-12.5094%`
- bearish 4h 비중: `74.1722%`
- flat 비중: `58.5725%`
- short gate open 비중: `4.8565%`
- 전략 depth: `51.2396%`

해석:
- 이건 `136`에서 봤던 전형적인 “느린 약세장 숏 공백”이다.
- 다만 중요한 점은, 이 대표 구간에서는 `unlock 0`, `slowbear 0`이다.
- 즉 이 전략이 전체적으로는 bear continuation 문제를 꽤 해결했지만, 모든 약세 구간에서 항상 잘 작동한 것은 아니다.

3. `two_way_whipsaw`
- 대표 구간:
- `2022-07-05 13:00:00` -> `2022-11-08 05:30:00` -> `2024-01-11 14:45:00`
- `2024-07-08 01:15:00` -> `2024-10-13 15:30:00` -> `2024-11-21 04:15:00`
- `2024-12-17 15:00:00` -> `2025-02-21 13:45:00` -> `2025-05-08 21:30:00`
- `2025-07-14 07:45:00` -> `2025-10-13 20:00:00` -> `2025-11-21 03:00:00`

이 구간들의 특징:
- BTC가 꼭 많이 빠지는 것도 아니다.
- `2022-07 ~ 2022-11`은 BTC peak-to-trough가 `+1.0075%`인데 전략은 `69.9377%`를 잃었다.
- `2024-07 ~ 2024-10`은 BTC가 `+14.1135%`인데 전략은 `62.7104%`를 잃었다.
- long/short/flat이 모두 꽤 높은 비중으로 섞여 있다.

해석:
- 이건 방향성 miss가 아니라 **양방향 흔들림 비용**이다.
- `unlock 2`, `slowbear 2`가 실제로 작동한 구간도 있는데, 그럼에도 손실이 큰 이유는 “short continuation 복구”만으로는 chop 소모를 막지 못했기 때문이다.
- 즉 이 전략은 이제 bearish continuation 문제를 꽤 해결했고, 그 결과 남은 병목이 훨씬 더 순수한 `whipsaw`로 드러난 상태다.

## 2. `combo_trim2p0_unlock24h`는 어떻게 달라졌나

### 핵심 차이

이 전략은 `unlock_slowbear_24h_2p0`와 비교할 때:
- `unlock 41회`, `slow_bear_short 17회`는 동일하다.
- 차이는 거의 전부 `bulltrim 65회`에서 나온다.

즉:
- bearish continuation을 다시 태우는 구조는 동일
- 대신 bullish 약화 구간에서 long을 줄여 whipsaw나 급락 초입 손실을 완충

### 대표 약점 구간 비교

같은 유형의 구간을 나란히 보면 차이가 꽤 분명하다.

| 공통 구간 | `unlock_slowbear_24h_2p0` Depth % | `combo_trim2p0_unlock24h` Depth % | 차이 |
| --- | ---: | ---: | ---: |
| `2021-01-08 ~ 2021-01-27` 급락 초입 | 64.5809 | 58.3019 | `-6.2789%p` |
| `2022-03-02 ~ 2022-03-16` 느린 bear | 51.2396 | 41.1267 | `-10.1130%p` |
| `2022-07-05 ~ 2022-11-08` 장기 whipsaw | 69.9377 | 63.9784 | `-5.9593%p` |
| `2024-07-08 ~ 2024-10-13` 장기 whipsaw | 62.7104 | 57.0767 | `-5.6337%p` |
| `2024-12-17 ~ 2025-02-21` 장기 whipsaw | 47.0989 | 42.3305 | `-4.7684%p` |
| `2025-07-14 ~ 2025-10-13` 장기 whipsaw | 47.1834 | 38.2194 | `-8.9640%p` |

핵심 해석:
- `bulltrim`은 거의 모든 대표 약한 구간에서 손실 깊이를 줄였다.
- 특히 `2022-03` slow bear와 `2025-07 ~ 2025-10` whipsaw에서 개선폭이 컸다.
- 다만 모든 구간에서 recovery가 빨라진 것은 아니다. 예를 들어 `2022-07 ~ 2022-11`은 depth는 줄었지만 회복기간은 조금 더 길어졌다.

즉 `bulltrim`의 역할은:
- “완전히 다른 알파를 추가”한 것이 아니라
- “같은 엔진을 덜 깊게 맞게” 만든 것이다.

## 3. 약점의 종류가 어떻게 달라졌나

대표 weak window 라벨 분포를 보면 더 분명하다.

### `unlock_slowbear_24h_2p0`
- `two_way_whipsaw` 4개
- `fast_selloff_long_stuck` 1개
- `mixed_trend_whipsaw` 1개
- `slow_bear_short_gap` 1개

대표 라벨 평균:
- `two_way_whipsaw`: depth `56.7326%`, 평균 회복 `240.8일`
- `slow_bear_short_gap`: depth `51.2396%`

### `combo_trim2p0_unlock24h`
- `two_way_whipsaw` 4개
- `slow_bear_short_gap` 2개
- `fast_selloff_long_stuck` 1개
- `mixed_trend_whipsaw` 1개

대표 라벨 평균:
- `two_way_whipsaw`: depth `50.4013%`, 평균 회복 `253.5일`
- `slow_bear_short_gap`: depth `43.0408%`

해석:
- 두 전략 모두 이미 주된 병목은 `two_way_whipsaw`다.
- `combo`는 같은 `two_way_whipsaw`에서도 depth를 `56.73% -> 50.40%`로 낮췄다.
- `slow_bear_short_gap`도 `51.24% -> 43.04%`로 줄였다.

즉 `combo`는 “새 약점이 없는 전략”은 아니지만, **기존 약점 유형 대부분을 조금씩 더 얕게 맞는 전략**이다.

## 4. 이벤트 카운트 관점에서 본 차이

두 전략의 전체 구조를 보면:

### `unlock_slowbear_24h_2p0`
- trades `171`
- long entries `67`
- short entries `104`
- `unlock 41`
- `slow bear short 17`
- `bulltrim 0`

### `combo_trim2p0_unlock24h`
- trades `238`
- long entries `134`
- short entries `104`
- `unlock 41`
- `slow bear short 17`
- `bulltrim 65`

이 숫자가 의미하는 바:
- short 쪽 개선은 완전히 동일하다.
- `combo`의 차이는 long을 더 자주 재조정한다는 점이다.
- 즉 더 많은 trade를 감수하면서도, long exposure를 적극적으로 관리해 약한 구간을 눌렀다.

이건 장단점이 같이 있다.
- 장점: 손실 깊이를 줄임
- 단점: trade가 늘어나고, 일부 구간에선 recovery가 조금 늦어질 수 있음

그래도 이번 결과에서는 그 trade-off가 충분히 가치 있었다고 볼 수 있다.

## 5. 실전적으로 누가 더 낫나

### `unlock_slowbear_24h_2p0`
- raw 엔진으로는 더 좋다
- CAGR `206.70%`
- Calmar `2.9555`
- 그러나 MDD `69.94%`는 상당히 거칠다
- 대표 약한 구간 평균 depth도 `56.46%`로 크다

실전 해석:
- 계좌 체감이 매우 강할 가능성이 높다
- 공격형 sleeve나 연구용 benchmark로는 좋다
- 하지만 단독 주력으로는 부담스럽다

### `combo_trim2p0_unlock24h`
- CAGR `180.76%`로 여전히 매우 높다
- MDD `63.98%`
- 2026 수익률 `19.17%`로 오히려 더 좋다
- 대표 약한 구간 평균 depth와 전체 MDD가 모두 낮다

실전 해석:
- 두 전략 중에서는 확실히 더 실전형이다
- 다만 절대 MDD가 여전히 높아서 “안전형”이라고 부를 수는 없다
- 실전 투입 시에는 비중 제한, 분할 운용, 자금관리 overlay가 여전히 필요하다

## 6. 이번 연구의 진짜 결론

이번 140에서 가장 중요한 결론은 이거다.

1. `138`의 short continuation 복구 방향은 맞았다  
   `slow bear short gap`만 보던 시기에서, 이제는 주된 병목이 `two_way_whipsaw`로 이동했다.

2. `bulltrim`은 실제로 의미가 있었다  
   같은 weak window를 비교했을 때 손실 깊이를 거의 일관되게 줄였다.

3. 남은 과제는 whipsaw 방지다  
   즉 다음 단계는 bear continuation을 더 늘리는 게 아니라, chop 구간에서 long/short 소모를 줄이는 쪽이 맞다.

## 최종 평가

- 순수 엔진 1위: `unlock_slowbear_24h_2p0`
- 실전형 1위: `combo_trim2p0_unlock24h`

이 보고서를 한 줄로 요약하면:
- `unlock_slowbear_24h_2p0`는 더 강한 엔진
- `combo_trim2p0_unlock24h`는 같은 약점을 덜 깊게 맞는 전략
- 둘 다 이제 주된 약점은 `whipsaw`

## 산출물

- Plot: `140_backtest_btcusdt_row6_bestpair_episode_analysis.png`
- Episodes CSV: `140_backtest_btcusdt_row6_bestpair_episode_analysis_episodes.csv`
- Label Summary CSV: `140_backtest_btcusdt_row6_bestpair_episode_analysis_label_summary.csv`
- Variant Summary CSV: `140_backtest_btcusdt_row6_bestpair_episode_analysis_variant_summary.csv`
- Curves CSV: `140_backtest_btcusdt_row6_bestpair_episode_analysis_curves.csv`
- Report: `140_backtest_btcusdt_row6_bestpair_episode_analysis.md`
