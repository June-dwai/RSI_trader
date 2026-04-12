# 142번 연구: row6 bulltrim 이후 재레버리지 제한 실험

- 기준 엔진은 `138`의 실전형 베이스인 `combo_trim2p0_unlock24h`입니다.
- 비교 구간은 `2021-01-02 00:00:00` ~ `2026-03-15 05:19:00`입니다.
- `141`에서 generic chop filter가 잘 안 먹혔기 때문에, 이번엔 문제를 더 좁혀서 `bulltrim 이후 long이 너무 빨리 다시 3.0x로 복귀하는가`를 직접 테스트했습니다.
- 해석 주의: inherited `slow_bear_bars=1440`은 15분봉 기준이므로 약 15일 지속 bearish 조건입니다.

## 실험 아이디어
- `bulltrim`은 bullish regime 안에서 이상 징후가 잡히면 기존 long을 닫고 `2.0x` long으로 다시 여는 완충 장치입니다.
- 이번 연구는 그 이후 long 재진입이 다시 발생할 때, 곧바로 `3.0x`로 복귀시키지 말고 일정 조건이 충족될 때까지 낮은 레버리지를 유지하면 whipsaw를 줄일 수 있는지 보는 실험입니다.
- 즉 `141`의 chop 전역 필터가 아니라, `trim 이후 long 쪽 재가속만 제어`하는 훨씬 국소적인 수정입니다.

## Variant Table
| Variant | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Whipsaw Avg Return % | Whipsaw Avg MDD % | Bull Trims | Unlocks | Slow Bear Shorts | Posttrim Capped Longs | Posttrim Releases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| combo_posttrim_same_regime_2p0 | 181.1938 | 63.9784 | 2.8321 | 19.1725 | 44.9550 | -50.4013 | 50.4013 | 65 | 41 | 17 | 3 | 0 |
| combo_posttrim_confirm32_2p0 | 181.1938 | 63.9784 | 2.8321 | 19.1725 | 44.9550 | -50.4013 | 50.4013 | 65 | 41 | 17 | 3 | 0 |
| combo_posttrim_stage16_64 | 181.0878 | 63.9784 | 2.8305 | 19.1725 | 44.9550 | -50.4013 | 50.4013 | 65 | 41 | 17 | 3 | 0 |
| combo_posttrim_stage16_96_strict | 181.0878 | 63.9784 | 2.8305 | 19.1725 | 44.9550 | -50.4013 | 50.4013 | 65 | 41 | 17 | 3 | 0 |
| combo_base | 180.7641 | 63.9784 | 2.8254 | 19.1725 | 44.9550 | -50.4013 | 50.4013 | 65 | 41 | 17 | 0 | 0 |
| combo_posttrim_wait32_2p0 | 175.4544 | 64.7056 | 2.7116 | 19.1725 | 44.9550 | -50.4013 | 50.4013 | 65 | 41 | 17 | 1 | 2 |

## Variant Meaning
- `combo_base`: `138` 실전형 그대로. trim 이후에도 다음 long 재진입은 바로 원래 레버리지로 복귀합니다.
- `combo_posttrim_same_regime_2p0`: trim이 한 번 나오면 같은 bullish regime이 끝날 때까지 long은 계속 `2.0x`로 제한합니다.
- `combo_posttrim_wait32_2p0`: trim 후 32개 15분봉 동안만 `2.0x` 유지하고 그 뒤엔 자동 해제합니다.
- `combo_posttrim_confirm32_2p0`: 32개 봉 경과 + `red_avg` 위 회복 + 위쪽 bearish OB 완화가 동시에 확인될 때만 해제합니다.
- `combo_posttrim_stage16_64`: 처음 16개 봉은 `2.0x`, 그다음은 `2.5x`로 완화하고 64개 봉 이후 조건이 좋아지면 풀레버리지 복귀를 허용합니다.
- `combo_posttrim_stage16_96_strict`: 더 오래, 더 엄격하게 `2.0x -> 2.5x -> 3.0x` 단계 복귀를 강제하는 버전입니다.

## 기준 대비 읽는 법
- 기준 `combo_base`: CAGR `180.7641%`, MDD `63.9784%`, Calmar `2.8254`, 2026 `19.1725%`, whipsaw 평균 수익률 `-50.4013%`입니다.
- 전체 균형 최상위: `combo_posttrim_same_regime_2p0` -> Calmar `2.8321`, CAGR `181.1938%`, MDD `63.9784%`.
- whipsaw 방어 최상위: `combo_posttrim_same_regime_2p0` -> whipsaw 평균 수익률 `-50.4013%`, whipsaw 평균 MDD `50.4013%`.

## 해석 포인트
- 좋은 수정이라면 `whipsaw 평균 손실`이 먼저 개선되고, 그 다음에 CAGR 손상이 얼마나 작은지를 봐야 합니다.
- `posttrim_capped_long_entries`가 많다는 건 trim 이후 long 재가속을 실제로 자주 눌렀다는 뜻입니다.
- 그런데도 whipsaw가 개선되지 않으면, 문제는 `bulltrim 이후 재레버리지`보다 더 앞단의 진입/방향 판별에 있을 가능성이 큽니다.
- 반대로 whipsaw가 좋아지는데 CAGR 훼손이 작다면, `141`보다 훨씬 실전적인 개선으로 볼 수 있습니다.

## Whipsaw Windows Used
- `2022-07-05 13:00:00` -> `2022-11-08 05:30:00`
- `2024-07-08 01:15:00` -> `2024-10-13 15:30:00`
- `2024-12-17 15:00:00` -> `2025-02-21 13:45:00`
- `2025-07-14 07:45:00` -> `2025-10-13 20:00:00`

## 실전성 판단 체크리스트
- baseline 대비 CAGR을 지키면서 MDD 또는 whipsaw 손실을 줄였는가
- 2026 방어가 유지되거나 좋아졌는가
- 수정 효과가 `한두 번의 우연`이 아니라 `capped_long_entries`, `release_count` 같은 구조적 흔적으로 확인되는가
- 너무 오래 `2.0x`에 묶여서 장기 상승장의 엔진을 망치지는 않는가

## 산출물
- Plot: `142_backtest_btcusdt_row6_posttrim_releverage_trials.png`
- Metrics CSV: `142_backtest_btcusdt_row6_posttrim_releverage_trials.csv`
- Curves CSV: `142_backtest_btcusdt_row6_posttrim_releverage_trials_curves.csv`
- Whipsaw Windows CSV: `142_backtest_btcusdt_row6_posttrim_releverage_trials_whipsaw_windows.csv`
- Report: `142_backtest_btcusdt_row6_posttrim_releverage_trials.md`
