# 135번 연구: 134 최고전략표 3행 vs 6행 같은 구간 정면 비교

## 비교 대상
- 3행: study 120 포트폴리오 `lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_24_30`
- 6행: study 126 raw case3 `lb4_delay8_capna_cd0`
- 목적은 서로 다른 기간에서 뽑힌 숫자를 그대로 보지 말고, 완전히 같은 창에서 다시 비교하는 것이다.
- 공통 비교 구간: `2022-01-01 08:00:00` ~ `2026-02-12 00:00:00`
- 시작 자본은 둘 다 `2000` USDT로 맞췄다.

## 결과 표

| Strategy | Final Equity | Total Return % | CAGR % | MDD % | Calmar | 2026 YTD Return % | 2026 YTD MDD % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| row3_study120_portfolio | 70794.6987 | 3439.7349 | 137.9606 | 43.4085 | 3.1782 | 18.8276 | 15.7545 |
| row6_study126_case3 | 88853.7400 | 4342.6870 | 151.4721 | 55.5493 | 2.7268 | 24.8257 | 22.4049 |

## 핵심 해석
- CAGR 우위는 `row6_study126_case3`였다. `151.4721%`로 다른 쪽 대비 `13.5115pp` 차이가 났다.
- MDD 방어 우위는 `row3_study120_portfolio`였다. MDD `43.4085%`로 더 낮았다.
- Calmar 우위는 `row3_study120_portfolio`였다. 즉 이 구간에선 단순 CAGR뿐 아니라 위험 대비 효율도 `row3_study120_portfolio` 쪽이 더 좋았다.
- 2026 YTD 방어는 `row6_study126_case3`가 더 나았다. 2026 수익률 `24.8257%`, 2026 MDD `22.4049%`였다.

## 전략 성격 차이
- `lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_24_30`는 case1/case2/case3를 `46/24/30`으로 섞고 `30분`마다 리밸런스하는 포트폴리오라, 하나의 강한 엔진을 밀기보다 여러 슬리브가 서로의 drawdown을 상쇄하는 구조다.
- `lb4_delay8_capna_cd0`는 3배 regime-hold 성격의 단일 case3 엔진이라, 포트폴리오 완충 없이 방향성이 맞을 때 강하게 치고 나가지만 흔들릴 때 낙폭도 더 크게 받는다.

## 내가 읽는 결론
- 6행은 여전히 더 공격적인 수익 엔진이고, 3행은 그 수익을 일부 덜어내는 대신 MDD를 낮춘 실전형이라고 보는 게 맞다.
- 그래서 실제 배치라면 3행을 기본형으로 보고, 6행은 더 공격적인 별도 엔진 혹은 포트폴리오의 고알파 코어로 보는 해석이 자연스럽다.

## 산출물
- Metrics CSV: `135_backtest_btcusdt_row3_vs_row6_same_window.csv`
- Curves CSV: `135_backtest_btcusdt_row3_vs_row6_same_window_curves.csv`
- Plot: `135_backtest_btcusdt_row3_vs_row6_same_window.png`
- Report: `135_backtest_btcusdt_row3_vs_row6_same_window.md`
