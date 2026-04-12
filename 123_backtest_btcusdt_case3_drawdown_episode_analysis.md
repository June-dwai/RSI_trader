# 123 연구: case3 주요 MDD 구간 해부

## 대상
- 분석 대상 case3: `lv3p0_g12_body25_tp20_lb5_none`
- 구간: `2021-01-02 00:00:00` ~ `2026-03-15 05:19:00`
- 목적: 가장 깊은 drawdown 5개가 어떤 경우에 발생했는지 읽고, CAGR 훼손을 최소화하면서 줄일 수 있는 방법을 찾는다.

## 전체 성적
- 현재 case3: CAGR `151.3261%`, MDD `64.5809%`, Calmar `2.3432`
- 근처 완화 후보 1: `lv2p5_g12_body20_tp20_lb5_none` -> CAGR `145.2192%`, MDD `59.0448%`, Calmar `2.4595`
- 근처 완화 후보 2: `lv2p0_g12_body20_tp15_lb5_none` -> CAGR `118.7930%`, MDD `52.3206%`, Calmar `2.2705`

## Top 5 Drawdown Episodes

| Episode | Peak | Trough | Recovery | Depth % | Days To Trough | BTC Peak->Trough % | Long % | Short % | Flat % | Label |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| E1 | 2021-01-08 12:15:00 | 2021-01-27 00:30:00 | 2021-02-17 19:45:00 | 64.5809 | 18.5 | -22.4771 | 62.4859 | 0.1125 | 37.4016 | 하락장에서 레버리지 롱 노출 |
| E2 | 2023-04-14 07:00:00 | 2023-06-07 00:45:00 | 2023-12-03 22:15:00 | 55.5493 | 53.7 | -11.5150 | 31.2984 | 45.3876 | 23.3140 | 양방향 휩쏘 누적 |
| E3 | 2024-12-17 15:00:00 | 2025-04-04 18:00:00 | 2025-05-22 03:45:00 | 54.4515 | 108.1 | -21.8959 | 29.3710 | 24.7375 | 45.8915 | 혼합형 추세/휩쏘 drawdown |
| E4 | 2021-04-14 12:00:00 | 2021-05-14 17:15:00 | 2021-07-26 06:30:00 | 52.7660 | 30.2 | -21.3560 | 42.1089 | 11.5093 | 46.3818 | 혼합형 추세/휩쏘 drawdown |
| E5 | 2022-03-02 15:00:00 | 2022-03-16 18:30:00 | 2023-01-13 20:15:00 | 51.2396 | 14.1 | -12.5094 | 16.9978 | 24.4297 | 58.5725 | flat 구간이 길었지만 회복이 지연 |

## Episode Notes
### E1
- 기간: `2021-01-08 12:15:00` -> `2021-01-27 00:30:00`
- 낙폭: `64.5809%`, BTC 변화: `-22.4771%`
- 노출 구성: long `62.4859%`, short `0.1125%`, flat `37.4016%`
- 추세/미스매치: bullish4h `69.2351%`, bearish4h `30.7649%`, long-in-bearish `0.0000%`, short-in-bullish `0.0000%`
- 구조 환경: bearish OB above avg `4.6265`, bullish OB below avg `3.5984`, short gate open `0.3375%`
- 해석: 하락장에서 레버리지 롱 노출

### E2
- 기간: `2023-04-14 07:00:00` -> `2023-06-07 00:45:00`
- 낙폭: `55.5493%`, BTC 변화: `-11.5150%`
- 노출 구성: long `31.2984%`, short `45.3876%`, flat `23.3140%`
- 추세/미스매치: bullish4h `38.8372%`, bearish4h `61.1628%`, long-in-bearish `0.0000%`, short-in-bullish `0.0000%`
- 구조 환경: bearish OB above avg `4.9227`, bullish OB below avg `4.9537`, short gate open `4.3411%`
- 해석: 양방향 휩쏘 누적

### E3
- 기간: `2024-12-17 15:00:00` -> `2025-04-04 18:00:00`
- 낙폭: `54.4515%`, BTC 변화: `-21.8959%`
- 노출 구성: long `29.3710%`, short `24.7375%`, flat `45.8915%`
- 추세/미스매치: bullish4h `32.0971%`, bearish4h `67.9029%`, long-in-bearish `0.0000%`, short-in-bullish `0.0000%`
- 구조 환경: bearish OB above avg `4.7299`, bullish OB below avg `4.9176`, short gate open `6.3674%`
- 해석: 혼합형 추세/휩쏘 drawdown

### E4
- 기간: `2021-04-14 12:00:00` -> `2021-05-14 17:15:00`
- 낙폭: `52.7660%`, BTC 변화: `-21.3560%`
- 노출 구성: long `42.1089%`, short `11.5093%`, flat `46.3818%`
- 추세/미스매치: bullish4h `43.5562%`, bearish4h `56.4438%`, long-in-bearish `0.0000%`, short-in-bullish `0.0000%`
- 구조 환경: bearish OB above avg `4.7467`, bullish OB below avg `4.9442`, short gate open `5.8580%`
- 해석: 혼합형 추세/휩쏘 drawdown

### E5
- 기간: `2022-03-02 15:00:00` -> `2022-03-16 18:30:00`
- 낙폭: `51.2396%`, BTC 변화: `-12.5094%`
- 노출 구성: long `16.9978%`, short `24.4297%`, flat `58.5725%`
- 추세/미스매치: bullish4h `25.8278%`, bearish4h `74.1722%`, long-in-bearish `0.0000%`, short-in-bullish `0.0000%`
- 구조 환경: bearish OB above avg `4.9330`, bullish OB below avg `4.9455`, short gate open `4.8565%`
- 해석: flat 구간이 길었지만 회복이 지연

## Drawdown Window Variant Compare

| Variant | Overall CAGR % | Overall MDD % | Avg Peak->Trough % | Worst Peak->Trough % | Avg Window MDD % |
| --- | ---: | ---: | ---: | ---: | ---: |
| lv2p0_g12_body20_tp15_lb5_none | 118.7930 | 52.3206 | -42.9396 | -52.3206 | 42.9396 |
| lv2p25_g8_body20_tp15_lb5_none | 123.7811 | 55.8538 | -46.5617 | -55.8538 | 46.5617 |
| lv2p5_g12_body20_tp20_lb5_none | 145.2192 | 59.0448 | -49.2865 | -59.0448 | 49.2865 |
| lv3p0_g12_body25_tp20_lb5_none | 151.3261 | 64.5809 | -55.7175 | -64.5809 | 55.7175 |
| lv3p0_g8_body20_tp20_lb5_none | 153.5918 | 64.5809 | -55.6462 | -64.5809 | 55.6462 |

## 핵심 해석
- `g8/body20`처럼 진입 타이밍만 건드린 3.0x 변형은 전체 MDD를 거의 줄이지 못했다. 즉 주원인은 타이밍보다 `레버리지 자체`에 더 가깝다.
- `2.5x + g12 + TP20`은 CAGR 손실을 비교적 작게 유지하면서 MDD를 가장 현실적으로 낮추는 후보였다.
- `2.0x/2.25x + TP15` 계열은 MDD는 더 낮추지만 CAGR 훼손이 커서 'CAGR을 크게 해치지 않는다'는 조건엔 덜 맞는다.
- 상위 5개 drawdown 대부분은 한 방향 추세 구간에서 반대 포지션이 길게 물리거나, 3.0x 레버리지 long/short 노출이 변동성 구간에서 크게 흔들린 경우로 읽힌다.

## 제안
- 1차 완화안: `lv2p5_g12_body20_tp20_lb5_none` 재검증. 전체 CAGR은 `151.33 -> 145.22`로 약 `-6.11pp`, MDD는 `64.58 -> 59.04`로 약 `-5.54pp` 개선된다.
- 2차 완화안: `2.5x`는 유지하고 `body_atr_mult`를 `0.20`으로 낮춰 short gate를 조금 더 일찍 여는 방향을 우선 검토한다.
- 보류안: `long_above_red_avg` 같은 SR 필터는 drawdown 완화 대비 CAGR 훼손이 더 커서 우선순위가 낮다.
- 공격형 유지안: case3 100%를 계속 쓸 거면, 포트폴리오가 아니라 sleeve 내부에서 `3.0x -> 2.5x` 다운시프트가 가장 덜 아픈 방어책이다.

## 산출물
- Plot: `123_backtest_btcusdt_case3_drawdown_episode_analysis.png`
- Episodes CSV: `123_backtest_btcusdt_case3_drawdown_episode_analysis.csv`
- Variant Compare CSV: `123_backtest_btcusdt_case3_drawdown_episode_analysis_variant_compare.csv`
- Curves CSV: `123_backtest_btcusdt_case3_drawdown_episode_analysis_curves.csv`
- Report: `123_backtest_btcusdt_case3_drawdown_episode_analysis.md`