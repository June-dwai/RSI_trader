# 122 연구: 실전형 리밸런스 검증 + 비중 재탐색

## 설정
- 로컬 최신 BTCUSDT 1분 캐시는 `2026-03-15 05:19:00`까지 존재한다.
- 이번 연구의 공통 구간은 `2021-01-02 00:00:00` ~ `2026-03-15 05:30:00` 이다.
- sleeve는 case1/case2/case3를 그대로 유지하고, 비중만 넓게 흔들었다.
- weight grid는 `5%` 단위 전체 simplex 탐색이다. 즉 `case1=0%`부터 `100%`까지 모두 열어둔다.
- 리밸런스는 포지션을 강제로 정리하지 않는다.
  주간/월간 due가 지난 뒤 `세 sleeve가 모두 flat`인 첫 시점에서만 리밸런스한다.

## Sleeve 정의
- case1: study62 `shallow6_else2bull`
- case2: study42 case2 sleeve
- case3: study117 `lv3p0_g12_body25_tp20_lb5_none`

## 최고 결과
- 최고 CAGR: `no_rebalance_w0_0_100` -> CAGR `151.3261%`, MDD `64.5809%`, Calmar `2.3432`, weights `0.00/0.00/1.00`, mode `no_rebalance`
- 최고 Calmar: `weekly_due_allflat_w0_55_45` -> CAGR `138.4891%`, MDD `54.7645%`, Calmar `2.5288`, weights `0.00/0.55/0.45`, mode `weekly_due_allflat`

## 모드별 우승
- no rebalance: `no_rebalance_w0_55_45` -> CAGR `137.6798%`, MDD `54.8647%`, Calmar `2.5094`
- weekly due + all-flat: `weekly_due_allflat_w0_55_45` -> CAGR `138.4891%`, MDD `54.7645%`, Calmar `2.5288`
- monthly due + all-flat: `monthly_due_allflat_w0_55_45` -> CAGR `137.6743%`, MDD `54.8647%`, Calmar `2.5093`

## 121 기준 참고값
- 121 study119_current_mix: CAGR `102.5839%`, MDD `65.8846%`, Calmar `1.5570`
- 121 study120_current_mix: CAGR `114.6123%`, MDD `64.4942%`, Calmar `1.7771`
- 121 case3_only: CAGR `151.0915%`, MDD `64.5809%`, Calmar `2.3396`

## 상위 15개

| Variant | Mode | W1 | W2 | W3 | Final Equity | CAGR % | MDD % | Calmar | Rebalances | Deferred Bars |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| weekly_due_allflat_w0_55_45 | weekly_due_allflat | 0.00 | 0.55 | 0.45 | 183130.1115 | 138.4891 | 54.7645 | 2.5288 | 2 | 181803 |
| weekly_due_allflat_w0_50_50 | weekly_due_allflat | 0.00 | 0.50 | 0.50 | 188668.3254 | 139.8602 | 55.4631 | 2.5217 | 2 | 181803 |
| weekly_due_allflat_w0_45_55 | weekly_due_allflat | 0.00 | 0.45 | 0.55 | 194141.7564 | 141.1838 | 56.1676 | 2.5136 | 2 | 181803 |
| no_rebalance_w0_55_45 | no_rebalance | 0.00 | 0.55 | 0.45 | 179923.3594 | 137.6798 | 54.8647 | 2.5094 | 0 | 0 |
| monthly_due_allflat_w0_55_45 | monthly_due_allflat | 0.00 | 0.55 | 0.45 | 179901.5563 | 137.6743 | 54.8647 | 2.5093 | 1 | 179339 |
| weekly_due_allflat_w0_40_60 | weekly_due_allflat | 0.00 | 0.40 | 0.60 | 199550.4046 | 142.4623 | 56.8528 | 2.5058 | 2 | 181803 |
| weekly_due_allflat_w0_60_40 | weekly_due_allflat | 0.00 | 0.60 | 0.40 | 177527.1148 | 137.0674 | 54.7633 | 2.5029 | 2 | 181803 |
| no_rebalance_w0_50_50 | no_rebalance | 0.00 | 0.50 | 0.50 | 185429.1818 | 139.0623 | 55.5628 | 2.5028 | 0 | 0 |
| monthly_due_allflat_w0_50_50 | monthly_due_allflat | 0.00 | 0.50 | 0.50 | 185407.1585 | 139.0568 | 55.5628 | 2.5027 | 1 | 179339 |
| weekly_due_allflat_w0_35_65 | weekly_due_allflat | 0.00 | 0.35 | 0.65 | 204894.2698 | 143.6984 | 57.5198 | 2.4982 | 2 | 181803 |
| no_rebalance_w0_45_55 | no_rebalance | 0.00 | 0.45 | 0.55 | 190935.0043 | 140.4121 | 56.2647 | 2.4956 | 0 | 0 |
| monthly_due_allflat_w0_45_55 | monthly_due_allflat | 0.00 | 0.45 | 0.55 | 190913.2012 | 140.4068 | 56.2647 | 2.4955 | 1 | 179339 |
| no_rebalance_w0_40_60 | no_rebalance | 0.00 | 0.40 | 0.60 | 196440.8267 | 141.7307 | 56.9457 | 2.4889 | 0 | 0 |
| monthly_due_allflat_w0_40_60 | monthly_due_allflat | 0.00 | 0.40 | 0.60 | 196419.6844 | 141.7257 | 56.9457 | 2.4888 | 1 | 179339 |
| weekly_due_allflat_w0_30_70 | weekly_due_allflat | 0.00 | 0.30 | 0.70 | 210173.3522 | 144.8942 | 58.2363 | 2.4880 | 2 | 181803 |

## 해석
- weekly/monthly flat-only가 상위에 온다면, 잦은 기계적 리밸런스 없이도 포트폴리오 구성 효과가 유지된다는 뜻이다.
- no rebalance가 계속 이긴다면, 현재는 분산보다 case3 단독 알파가 더 강하다는 뜻이다.
- case1 비중이 낮은 조합이 상위라면, 2021~현재 전체 구간에서는 기존의 높은 case1 비중이 허수였을 가능성이 크다.

## 산출물
- Plot: `122_backtest_btcusdt_practical_rebalance_weight_sweep_2021plus.png`
- Metrics CSV: `122_backtest_btcusdt_practical_rebalance_weight_sweep_2021plus.csv`
- Curves CSV: `122_backtest_btcusdt_practical_rebalance_weight_sweep_2021plus_curves.csv`
- Report: `122_backtest_btcusdt_practical_rebalance_weight_sweep_2021plus.md`