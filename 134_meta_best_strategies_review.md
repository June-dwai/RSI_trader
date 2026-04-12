# 134번 연구: 최근 MD 전체 흐름을 다시 훑은 최고 전략 정리

## 범위와 비교 기준
- 이번 메타 리뷰는 현재 운용 후보로 이어지는 후기 연구를 중심으로 다시 읽었다. 핵심 축은 `118~133`이고, 보조 해석으로 `123`, `124`를 반영했다.
- 초기 `00~117`번대는 구조 탐색 비중이 커서 직접 우승 후보를 다시 뽑기보다는, 이후 실제로 살아남은 계보를 우선 정리했다.
- 기간이 다르면 숫자를 그대로 일대일 비교하면 안 된다.
  - BTC 포트폴리오 진화축 `118~120`: `2022-01-01 08:00:00` ~ `2026-02-12 00:00:00`
  - BTC 실전 비교축 `121~127`: `2021-01-02 00:00:00` ~ `2026-03-15 05:30:00` 전후
  - ETH 축 `129~133`: `2021-01-02 00:00:00` ~ `2026-04-12 03:15:00` 전후

## 한 줄 결론
- BTC에서 raw 엔진 최고는 study 126/127의 `lb4_delay8_capna_cd0`였다. CAGR `167.9773%`, MDD `64.5809%`, Calmar `2.6010`.
- BTC에서 실제 운용형 최고는 study 122의 `weekly_due_allflat_w0_55_45`였다. CAGR `138.4891%`, MDD `54.7645%`, Calmar `2.5288`.
- BTC 2022+ 구간에서 가장 예쁘게 다듬어진 저MDD 포트폴리오는 study 119의 `lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w49_27_24`였다. CAGR `132.2561%`, MDD `42.8382%`, Calmar `3.0873`.
- ETH에서 알파 엔진은 여전히 study 129의 raw case3였지만, 그대로 쓰면 MDD가 `92.8406%`까지 벌어진다.
- ETH 실전형은 보수적으로는 study 132 `seed_vault_overlay` , 공격적으로는 study 133 `multiplier_ladder_overlay`가 가장 납득 가능했다.

## 최고 전략 표
| Bucket | Study | Label | Variant | CAGR % | MDD % | Calmar | Verdict |
| --- | ---: | --- | --- | ---: | ---: | ---: | --- |
| BTC 포트폴리오 진화 | 118 | 첫 case3 확대형 포트폴리오 승자 | `lv3p0_g12_body25_tp20_lb5_none_case3_w52_28_20` | 129.5209 | 43.5679 | 2.9728 | 역사적 전환점 |
| BTC 포트폴리오 진화 | 119 | BTC 2022+ 저MDD 완성형 | `lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w49_27_24` | 132.2561 | 42.8382 | 3.0873 | BTC 2022+ 밸런스 우승 |
| BTC 포트폴리오 진화 | 120 | BTC 2022+ 공격형 포트폴리오 | `lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_24_30` | 138.0334 | 43.4085 | 3.1799 | BTC 2022+ 고성능, 고운영비 |
| BTC 2021+ 단독/혼합 비교 | 121 | 2021+에서 case3 우위 재확인 | `case3_only` | 151.0915 | 64.5809 | 2.3396 | 2021+ raw 우세 확인 |
| BTC 2021+ 실전형 | 122 | BTC 실전형 최고 | `weekly_due_allflat_w0_55_45` | 138.4891 | 54.7645 | 2.5288 | BTC 실전형 1순위 |
| BTC case3 엔진 | 126 | BTC raw CAGR 최고 case3 | `lb4_delay8_capna_cd0` | 167.9773 | 64.5809 | 2.6010 | BTC raw 엔진 우승 |
| BTC case3 엔진 | 127 | BTC case2+case3 완충 혼합 | `case2_case3best_half_mix` | 149.8032 | 55.5628 | 2.6961 | BTC 공격형 혼합 우승 |
| ETH raw / salvage | 129 | ETH raw case3 red line | `lb4_delay9_capna_cd0_only` | 63.8550 | 92.8406 | 0.6878 | 연구용 엔진, 실전은 비추천 |
| ETH raw / salvage | 131 | ETH case2 생존형 | `lev12_tp2x_sl2x` | 33.0541 | 76.8370 | 0.4302 | 참고용 salvage, 주력은 아님 |
| ETH 리스크 관리 | 132 | ETH 보수형 실전 후보 | `seed_vault_overlay` | 51.5356 | 31.8147 | 1.6199 | ETH 안정형 1순위 |
| ETH 리스크 관리 | 133 | ETH 공격형 실전 후보 | `multiplier_ladder_overlay` | 83.1909 | 71.6547 | 1.1610 | ETH 공격형 1순위 |

## 흐름 해석
- study 118은 `case3를 20%대까지 키워도 된다`는 첫 증거였다. 승자 `lv3p0_g12_body25_tp20_lb5_none_case3_w52_28_20`가 CAGR `129.5209%` / MDD `43.5679%` / Calmar `2.9728`를 만들었다.
- study 119는 이 흐름을 `1시간 리밸런스`로 정리해 `49/27/24`를 현재형 포트폴리오로 굳혔다. 2022+ 기준 가장 낮은 MDD 축에 속하면서도 Calmar가 `3.0873`까지 올라갔다.
- study 120은 `30분 리밸런스 + case3 30%`까지 밀어붙여 CAGR `138.0334%`, Calmar `3.1799`를 만들었다. 다만 리밸런스 횟수가 매우 많아 실전 단순성은 떨어진다.
- study 121과 122에서 `2021`을 포함해 보니, case1 비중이 큰 구형 포트폴리오보다 `case2/case3` 중심 구성이 더 강했다. 그 정리본이 `weekly_due_allflat_w0_55_45`다.
- study 126과 127은 BTC 알파의 중심이 사실상 case3라는 점을 확인했다. raw는 `167.9773%` CAGR까지 갔고, 반면 50:50 혼합은 `149.8032%` CAGR / `55.5628%` MDD로 완충 효과를 보여줬다.
- study 123과 124의 해석도 중요하다. BTC case3 drawdown의 주원인은 미세한 타이밍보다 `3.0x 레버리지 자체`에 더 가까웠고, 2026 손실도 `빠른 역행 + 시그널 뒤집힘`에서 나왔다.
- ETH에 이걸 옮긴 study 129에서는 case3가 여전히 엔진이었지만, CAGR `63.8550%` 대비 MDD가 `92.8406%`로 너무 크다. 여기서는 `청산`보다 `수익 재복리 후 대규모 반환`이 문제였다.
- ETH case2를 억지로 살리려 한 130은 대부분 실패했고, study 131의 `lev12_tp2x_sl2x`가 최대 1.2배 노출과 넓은 TP/SL로 겨우 생존한 수준이었다. CAGR `33.0541%`라 주력 채택감은 약하다.
- ETH 실전형 해법은 엔진 수정이 아니라 `자금관리 오버레이`에서 나왔다. study 132는 MDD를 `92.8406% -> 31.8147%`로 크게 줄였고, study 133은 CAGR을 `83.1909%`까지 올리면서도 raw보단 훨씬 나은 형태로 만들었다.

## 카테고리별 최종 판단
- BTC 순수 수익 극대화: study 126 `lb4_delay8_capna_cd0`. 숫자는 가장 세지만, drawdown을 견딜 수 있어야 한다.
- BTC 공격형 타협안: study 127 `case2_case3best_half_mix`. raw case3보다 CAGR을 조금 내주고 MDD와 2026 손실을 줄인다.
- BTC 실전형 기본안: study 122 `weekly_due_allflat_w0_55_45`. 이유는 `운영 단순성`, `2021 포함`, `Calmar 균형` 세 가지가 동시에 좋기 때문이다.
- BTC 2022+ 저MDD 포트폴리오: study 119 `lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w49_27_24`. 다만 이건 기간이 `2022-01-01` 시작이라 2021+ 연구와 직접 우열 비교는 조심해야 한다.
- ETH 보수형: study 132 `seed_vault_overlay`. CAGR `51.5356%` / MDD `31.8147%` / Calmar `1.6199`로 가장 실전적이다.
- ETH 공격형: study 133 `multiplier_ladder_overlay`. CAGR `83.1909%`로 ETH 계열 중 업사이드가 가장 매력적이지만, MDD `71.6547%`는 여전히 크다.
- ETH raw 엔진 참고용: study 129 `lb4_delay9_capna_cd0_only`. 엔진 연구에는 가치가 있지만 그대로 쓰기엔 너무 거칠다.

## 내가 지금 고른다면
1. BTC를 실제로 굴린다면 1순위는 study 122 `weekly_due_allflat_w0_55_45`다.
2. BTC에서 연구용 최고 엔진을 계속 밀고 싶다면 study 126 raw case3와 study 127 half-mix를 같이 본다.
3. ETH는 case2를 주력으로 보기보다 case3 엔진 위에 오버레이를 얹는 방향이 맞다. 안정형은 study 132, 공격형은 study 133이다.
4. study 129 raw red line과 study 130 계열 case2 변형은 그대로 실전 배치하기엔 메리트가 약하다.

## 산출물
- Summary CSV: `134_meta_best_strategies_review.csv`
- Report: `134_meta_best_strategies_review.md`
