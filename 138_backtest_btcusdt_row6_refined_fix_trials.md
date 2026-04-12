# 138번 연구: row6 개선안 상세 분석

- 기준 전략은 `lb4_delay8_capna_cd0`, 즉 우리가 `row6`라고 부르던 BTC case3 개선형이다.
- 비교 구간은 `2021-01-02 00:00:00` ~ `2026-03-15 05:19:00`이다.
- 이번 연구의 목적은 `136`, `137`에서 확인된 row6의 약점을 직접 겨냥하는 것이었다.

## 문제 정의
- row6는 수익 엔진 자체는 매우 강했지만, 특정 구간에서 equity가 길게 눌리고 회복이 오래 걸렸다.
- 이전 분석 기준 핵심 약점은 크게 두 가지였다.
- `급락 초입 롱 잔류`: bearish 전환 초입에서 long 노출을 너무 늦게 줄여 큰 손실을 맞는 문제
- `느린 약세장 short 공백`: short TP 후 lock이 걸린 뒤, bearish가 오래 이어져도 continuation short를 다시 못 여는 문제
- 이후에는 이 두 문제를 어느 정도 해결하면, 남는 병목이 `two-way whipsaw` 쪽으로 이동할 가능성이 높다고 봤다.

## 이번에 넣은 수정
- `bulltrim`: bullish regime 안이지만 약화 신호가 보이면 기존 long을 닫고 더 낮은 레버리지 long으로 다시 연다.
- `unlock_short_lock`: short TP 이후 잠긴 short를 prolonged bearish에서 다시 풀어준다.
- `slow_bear_short`: sweep gate가 없어도 bearish가 충분히 오래 지속되면 continuation short를 다시 허용한다.

중요한 해석 주의점:
- variant 이름의 `24h`, `36h`는 이름만 그렇게 붙었고 실제 실행 데이터는 `15분봉`이다.
- 따라서 `slow_bear_bars=1440`은 약 `24시간`이 아니라 `1440개의 15분봉`, 즉 약 `15일`이다.
- `36h`도 실제로는 약 `22.5일`에 가깝다.

## 결과표

| Variant | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Bull Trims | Unlocks | Slow Bear Shorts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `unlock_slowbear_24h_2p0` | 206.7044 | 69.9377 | 2.9555 | 15.1415 | 47.7595 | 0 | 41 | 17 |
| `combo_trim2p0_unlock24h` | 180.7641 | 63.9784 | 2.8254 | 19.1725 | 44.9550 | 65 | 41 | 17 |
| `baseline_row6` | 167.9773 | 64.5809 | 2.6010 | -11.5764 | 33.1473 | 0 | 0 | 0 |
| `bulltrim_once_2p0` | 145.3124 | 58.3019 | 2.4924 | -8.4807 | 29.5583 | 65 | 0 | 0 |
| `bulltrim_once_1p5` | 130.5106 | 57.4867 | 2.2703 | -6.7166 | 27.6624 | 65 | 0 | 0 |
| `unlock_slowbear_36h_2p0` | 133.5950 | 64.5809 | 2.0686 | -29.0759 | 47.4785 | 0 | 23 | 10 |

## baseline_row6 대비 무엇이 좋아졌나

기준선인 `baseline_row6`는 다음과 같았다.
- CAGR `167.9773%`
- MDD `64.5809%`
- Calmar `2.6010`
- 2026 수익률 `-11.5764%`
- `unlock 0`, `slow bear short 0`

여기서 가장 중요한 포인트는 수익 개선의 본체가 무엇이냐이다.

`unlock_slowbear_24h_2p0`는 baseline 대비:
- CAGR `+38.7271%p`
- MDD `+5.3569%p`
- Calmar `+0.3545`
- 2026 수익률 `+26.7178%p`

`combo_trim2p0_unlock24h`는 baseline 대비:
- CAGR `+12.7867%p`
- MDD `-0.6025%p`
- Calmar `+0.2244`
- 2026 수익률 `+30.7498%p`

즉 둘 다 baseline보다 좋아졌지만, 좋아진 방식은 다르다.
- `unlock_slowbear_24h_2p0`는 수익 엔진을 크게 키우는 방식이다.
- `combo_trim2p0_unlock24h`는 수익을 조금 덜 가져가는 대신, MDD와 최근 구간 방어를 같이 챙기는 방식이다.

## 왜 좋아졌는가

핵심은 `unlock + continuation short`다.

baseline은 bearish가 길게 이어져도:
- short TP 후 locked short를 다시 풀지 못했고
- sweep gate가 다시 안 열리면 숏 재진입을 못 했다

이번 승자 둘은 공통적으로:
- `unlock 41회`
- `slow bear short 17회`

즉 baseline에 없던 `bearish continuation` 알파를 실제로 다시 태웠다.  
이게 `136`, `137`에서 추정했던 병목과 정확히 맞아떨어진다.

정리하면:
- `unlock + slow_bear_short`는 수익 엔진
- `bulltrim`은 손실 완충 장치

## 각 변형 해석

### `unlock_slowbear_24h_2p0`
- 이번 연구의 `순수 엔진 1위`
- CAGR `206.7044%`, Calmar `2.9555`로 전체 최고
- bearish continuation을 가장 공격적으로 다시 먹는다
- 대신 MDD `69.9377%`로 실전 체감은 매우 거칠다

한 줄 평가:
- "가장 강한 엔진"은 맞지만, 그대로 실전 투입하기엔 drawdown 스트레스가 크다

### `combo_trim2p0_unlock24h`
- 이번 연구의 `실전형 1위`
- CAGR `180.7641%`로 여전히 매우 높다
- MDD `63.9784%`로 baseline보다 소폭 낮다
- 2026 수익률 `19.1725%`로 전체 최고
- `bulltrim 65회`가 long 노출을 눌러주면서 worst-case를 완화한다

한 줄 평가:
- "순수 최고 수익"은 아니지만, 수익과 방어를 같이 보면 가장 균형이 좋다

### `bulltrim_once_2p0`
- bull trim만 단독으로 넣은 버전
- MDD는 `58.3019%`로 줄지만 CAGR이 `145.3124%`로 크게 깎인다
- 즉 trim만으로는 row6의 구조적 병목을 해결하지 못한다

### `bulltrim_once_1p5`
- 2.0x보다 더 강하게 줄인 버전
- MDD는 조금 더 낮지만 CAGR 훼손이 더 크다
- 과한 de-risk에 가깝다

### `unlock_slowbear_36h_2p0`
- unlock을 더 늦춘 버전
- `unlock 23회`, `slow bear short 10회`로 기회 자체가 줄었다
- CAGR `133.5950%`, 2026 `-29.0759%`로 성과가 크게 나빠졌다

의미:
- 방향은 맞았지만 timing이 중요하다
- "bearish continuation을 열어주는 것" 자체보다 "언제 열어주느냐"가 더 중요하다

## 실전 가능성은 있는가

결론부터 말하면:
- `unlock_slowbear_24h_2p0`는 연구용 최고 엔진
- `combo_trim2p0_unlock24h`는 실전형 후보

이유는 다음과 같다.

`unlock_slowbear_24h_2p0`
- CAGR은 최고지만 MDD가 70%에 가깝다
- 실전 배치 시 비중이 조금만 커져도 계좌 체감 변동성이 매우 커질 가능성이 높다
- "좋은 전략"이라기보다 "좋은 엔진" 쪽에 가깝다

`combo_trim2p0_unlock24h`
- baseline보다 CAGR, Calmar, 2026 수익률이 모두 좋다
- MDD도 baseline보다 약간 낮아졌다
- 즉 수익을 희생하면서 방어를 얻은 정도가 아니라, baseline보다 거의 전부 좋아진 개선형이다

다만 주의:
- 절대 MDD가 여전히 `63.9784%`라서, 실전형 후보라고 해도 보수적 전략은 아니다
- 단독 올인보다는 비중 제한, 포트폴리오 내 sleeve 운용, 자금관리 overlay가 같이 붙는 게 자연스럽다

## 이후 후속 연구에서 확인된 점

후속 `140` 분석으로 확인된 내용:
- 두 best 변형 모두 더 이상 주된 병목이 `slow bear short gap`만은 아니었다
- 대표 약점이 `two-way whipsaw`로 이동했다
- 즉 bearish continuation 문제를 꽤 해결한 뒤에는, 남는 문제가 chop/rotation 쪽으로 바뀐 것이다

후속 `140` 기준 대표 약한 구간 평균 깊이:
- `unlock_slowbear_24h_2p0`: 약 `56.46%`
- `combo_trim2p0_unlock24h`: 약 `48.97%`

즉 `combo`는 bull trim 덕분에 약한 구간의 깊이를 실제로 줄였다.

후속 `141` 기준:
- 추가 whipsaw guard를 넣어봤지만 아직 `combo_trim2p0_unlock24h`를 명확히 이기는 후속형은 못 찾았다
- 이건 오히려 `combo`가 현재 시점의 실전형 베이스로 꽤 괜찮다는 뜻이기도 하다

## 최종 판단

- 순수 엔진 1위: `unlock_slowbear_24h_2p0`
- 실전형 1위: `combo_trim2p0_unlock24h`

이번 `138`의 진짜 결론은 이거다.
- row6를 더 좋게 만드는 방향은 맞았다
- 핵심 개선 포인트는 `short continuation 복구`
- 그 다음 단계의 과제는 `whipsaw 방지`

즉 `138`은 row6를 살린 연구이고, 그중에서도 `combo_trim2p0_unlock24h`는 실제 운용 후보로 볼 만한 수준까지 왔다.

## 산출물
- Plot: `138_backtest_btcusdt_row6_refined_fix_trials.png`
- Metrics CSV: `138_backtest_btcusdt_row6_refined_fix_trials.csv`
- Curves CSV: `138_backtest_btcusdt_row6_refined_fix_trials_curves.csv`
- Report: `138_backtest_btcusdt_row6_refined_fix_trials.md`
