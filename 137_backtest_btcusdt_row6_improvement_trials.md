# 137번 연구: row6 개선 실험

## 설정
- 기준 전략은 `lb4_delay8_capna_cd0`이다.
- 비교 구간은 `2021-01-02 00:00:00` ~ `2026-03-15 05:19:00` 이다.
- 이번 실험은 두 가지 개선축을 본다.
  1. bearish 전환 전조에서 롱을 먼저 접고 4시간 동안 롱 재진입을 막는 `pre-bear exit`
  2. sweep가 없어도 장시간 bearish 상태가 이어지면 숏을 허용하는 `slow bear continuation short`

## 결과 표

| Variant | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Prebear Exits | Slow Bear Shorts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| slowbear_short_24h_ob4 | 168.4456 | 64.5809 | 2.6083 | -11.5764 | 33.1473 | 0 | 1 |
| baseline_row6 | 167.9773 | 64.5809 | 2.6010 | -11.5764 | 33.1473 | 0 | 0 |
| slowbear_short_12h_ob4 | 145.2236 | 64.5809 | 2.2487 | -11.5764 | 33.1473 | 0 | 4 |
| prebear_exit_ob5_cool4h | 91.0485 | 63.1360 | 1.4421 | -0.8079 | 21.8684 | 288 | 0 |
| combo_prebear_plus_slow12h | 74.8267 | 63.1360 | 1.1852 | -0.8079 | 21.8684 | 288 | 4 |

## 읽는 법
- baseline은 CAGR `167.9773%`, MDD `64.5809%`, Calmar `2.6010`, 2026 `-11.5764%`였다.
- 전체 균형 우승은 `slowbear_short_24h_ob4`였다. Calmar `2.6083`, CAGR `168.4456%`, MDD `64.5809%`.
- 2026 방어 우승은 `combo_prebear_plus_slow12h`였다. 2026 return `-0.8079%`, 2026 MDD `21.8684%`.

## 해석
- `pre-bear exit`는 급락 초입 롱 잔류를 줄이는 쪽을 겨냥했다.
- `slow bear short`는 느린 약세장에서 숏을 못 잡는 문제를 겨냥했다.
- 둘을 합친 결과가 baseline보다 좋아졌다면, row6의 약점이 실제로 이 두 축에 있다는 뜻이다.
- 반대로 개선이 약하거나 오히려 나빠졌다면, 이 문제는 규칙 추가보다 레버리지나 엔진 구조 문제가 더 크다는 뜻에 가깝다.

## 산출물
- Plot: `137_backtest_btcusdt_row6_improvement_trials.png`
- Metrics CSV: `137_backtest_btcusdt_row6_improvement_trials.csv`
- Curves CSV: `137_backtest_btcusdt_row6_improvement_trials_curves.csv`
- Report: `137_backtest_btcusdt_row6_improvement_trials.md`
