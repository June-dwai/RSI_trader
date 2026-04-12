# 143번 연구: 134 메타 정리 최신판

## 목적
- 134에서 정리했던 method/전략 표를 135~142까지 확장해서 다시 묶는다.
- 이번 버전은 `좋았던 전략`만이 아니라 `실패한 개선 line`도 같이 남겨서, 지금 어디까지 유효했고 어디서 막혔는지 한 번에 보이게 하는 데 목적이 있다.

## 비교 시 주의
- 기간이 다르면 숫자를 그대로 일대일 비교하면 안 된다.
- 특히 row6 계열은 `2021`이 CAGR을 크게 끌어올린다. 142에서 same-family 전략을 `2022-01-01`부터 다시 보면 CAGR이 `109% ~ 114%` 수준으로 내려온다.
- 따라서 `2021 포함 CAGR`은 최대 잠재력, `2022+`는 지금 시장 기준의 실전 체감이라고 보는 게 맞다.

## 현재 살아남은 핵심 후보
| Bucket | Study | Label | Variant | CAGR % | MDD % | Calmar | 2026 % | 2022+ CAGR % | Verdict |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| BTC core candidates | 119 | BTC 2022+ 저MDD 포트폴리오 | `lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w49_27_24` | 132.2561 | 42.8382 | 3.0873 |  |  | BTC 2022+ 저MDD 1순위 |
| BTC core candidates | 120 | BTC 2022+ 공격형 포트폴리오 | `lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_24_30` | 138.0334 | 43.4085 | 3.1799 |  |  | BTC 2022+ 공격형 포트폴리오 |
| BTC core candidates | 122 | BTC 단순 실전형 | `weekly_due_allflat_w0_55_45` | 138.4891 | 54.7645 | 2.5288 |  |  | BTC 단순 배치 1순위 |
| BTC core candidates | 126 | BTC raw case3 엔진 | `lb4_delay8_capna_cd0` | 167.9773 | 64.5809 | 2.6010 | -11.5764 |  | BTC raw 엔진 기준점 |
| BTC core candidates | 127 | BTC case2+case3 절충안 | `case2_case3best_half_mix` | 149.8032 | 55.5628 | 2.6961 | -6.0105 |  | BTC 공격형 절충안 |
| BTC refined engine | 138 | BTC 최고 엔진형 | `unlock_slowbear_24h_2p0` | 206.7044 | 69.9377 | 2.9555 | 15.1415 |  | BTC 최고 CAGR 엔진 |
| BTC refined engine | 138 | BTC 실전형 개선 엔진 | `combo_trim2p0_unlock24h` | 180.7641 | 63.9784 | 2.8254 | 19.1725 | 114.3598 | BTC 현 시점 실전형 알파 1순위 |
| ETH candidates | 129 | ETH raw case3 red line | `lb4_delay9_capna_cd0_only` | 63.8550 | 92.8406 | 0.6878 | -57.9510 |  | 엔진 연구용, 실전 배치 부적합 |
| ETH candidates | 132 | ETH 보수형 오버레이 | `seed_vault_overlay` | 51.5356 | 31.8147 | 1.6199 | -6.3060 |  | ETH 보수형 1순위 |
| ETH candidates | 133 | ETH 공격형 오버레이 | `multiplier_ladder_overlay` | 83.1909 | 71.6547 | 1.1610 | -30.1123 |  | ETH 공격형 1순위 |

## 134 이후 추가된 핵심 method line 요약
- `135`: 같은 2022+ 구간으로 row3와 row6를 붙여보면 row6가 CAGR `151.4721%`로 row3 `137.9606%`보다 강했다. 대신 MDD는 row6 `55.5493%`, row3 `43.4085%`라 row3가 더 얕았다.
- `135_1`: 2021+로 창을 늘리면 row6 CAGR이 `167.7272%`, row3는 `114.6123%`가 되어 격차가 더 벌어진다. 즉 row6는 엔진, row3는 완충형 성격이 더 뚜렷해졌다.
- `136`: baseline row6의 대표 약점이 `급락 초입 롱 잔류`, `느린 약세장에서 숏 기회 부족`, `양방향 whipsaw`라는 점을 구조적으로 확인했다.
- `137`: 첫 개선 시도는 대부분 실패했다. slow bear short 24h는 CAGR을 `167.9773% -> 168.4456%`로 아주 약간 올렸지만 실질적 구조 개선은 약했고, pre-bear exit는 CAGR이 `91.0485%`까지 무너져 과필터링이었다.
- `138`: 진짜 개선은 여기서 나왔다. baseline `167.9773% / 64.5809%`에서 `unlock_slowbear_24h_2p0`는 `206.7044% / 69.9377%`, `combo_trim2p0_unlock24h`는 `180.7641% / 63.9784%`가 나왔다.
- `139`: 138 combo를 ETH에 같은 구간으로 옮기면 CAGR `29.3369%`, MDD `97.4863%`에 그쳤다. 즉 이 개선 line은 BTC 전용 성격이 강하다.
- `140`: 138의 best 2개를 다시 뜯어보니 남은 병목은 `slow_bear_short_gap`보다 `two_way_whipsaw`였다. 대표 약한 구간 평균 depth가 `unlock`은 `56.4573%`, `combo`는 `48.9744%`로 줄었다.
- `141`: generic chop filter는 거의 실패했다. 가장 나았던 `combo_choplev2_x6`도 whipsaw 평균 손실을 `-50.4013% -> -48.2638%`로만 줄였고, CAGR은 `158.7285%`로 크게 내려갔다.
- `142`: bulltrim 이후 재레버리지 제한은 숫자는 약간 좋아 보여도 구조 효과가 거의 없었다. best 수치가 `181.1938% / 63.9784%`였지만 `posttrim capped long`이 3회뿐이었고, 2022+ CAGR도 `111.2160%`였다.

## 현재 해석
- BTC는 이제 크게 세 줄기로 정리된다.
  1. 단순 실전 포트폴리오 줄기: `122`
  2. raw case3 / 공격형 절충 줄기: `126`, `127`
  3. row6 개선 엔진 줄기: `138`, `140`, `141`, `142`
- 이 중 현재 가장 의미 있는 신규 성과는 `138`이다. `137`까지의 미세 수정과 달리, `unlock short lock + slow bear continuation short + bulltrim` 조합은 숫자와 상태 분석 양쪽에서 개선 흔적이 분명하다.
- 반대로 `141`, `142`는 다음 길을 알려준 연구다. generic chop filter나 posttrim re-entry cap은 핵심 병목을 못 찔렀다. 즉 다음 개선은 `재진입 제한`보다 `open long 관리` 쪽으로 가야 한다.
- ETH는 여전히 `엔진 개선`보다 `오버레이`가 더 유효하다. 현재까지는 `132`, `133`이 `129 raw`보다 실전성이 훨씬 높다.

## 최종 판정
- BTC 최고 엔진: `138 / unlock_slowbear_24h_2p0`. CAGR `206.7044%`, MDD `69.9377%`.
- BTC 현 시점 실전형 알파: `138 / combo_trim2p0_unlock24h`. CAGR `180.7641%`, MDD `63.9784%`, 2026 `19.1725%`.
- BTC 단순 배치형: `122 / weekly_due_allflat_w0_55_45`. CAGR `138.4891%`, MDD `54.7645%`.
- BTC 2022+ 저MDD 포트폴리오: `119 / lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w49_27_24`. CAGR `132.2561%`, MDD `42.8382%`.
- ETH 보수형: `132 / seed_vault_overlay`. CAGR `51.5356%`, MDD `31.8147%`.
- ETH 공격형: `133 / multiplier_ladder_overlay`. CAGR `83.1909%`, MDD `71.6547%`.
- 보류 또는 탈락 라인: `129 raw ETH case3`, `130 ETH case2 bearish escape`, `139 BTC->ETH 이식`, `141 generic chop guard`, `142 posttrim re-leverage`.

## 산출물
- Summary CSV: `143_meta_method_lines_review.csv`
- Report: `143_meta_method_lines_review.md`
