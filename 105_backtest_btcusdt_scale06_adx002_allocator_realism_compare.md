# 105번 연구: Allocator Realism Compare

## 목적
- `98 flow_combo6_thr2`의 비중 조절이 실제로는 열린 포지션을 건드려야 성립하는지 확인한다.
- 같은 sleeve(`case1/case2/case3`) 위에 `upper bound / cash-only / open-floor / flat-freeze` allocator를 올려 비교한다.
- 공통 구간: `2022-01-01 16:00:00` -> `2026-03-15 05:19:00`

## 시나리오 정의
- `fullreb_flow_thr2`: 98번과 같은 upper-bound. target drift 2% 넘으면 포지션까지 같이 리사이즈된 것으로 간주.
- `cashonly_flow`: 월 입금만 underweight 쪽에 넣고, 기존 자본은 한 번도 옮기지 않음.
- `openfloor_flow_thr2`: 열린 sleeve에서는 자본을 뺄 수 없고, 추가 자본만 넣을 수 있다고 가정.
- `flatfreeze_flow_thr2`: 열린 sleeve는 자본도 아예 건드리지 않고, flat sleeve끼리만 자본 이동.

## flat 비율
- case1 flat ratio: `4.8317%`
- case2 flat ratio: `9.0586%`
- case3 flat ratio: `33.4389%`
- all three flat ratio: `0.1958%`

## 결과

| Variant | Mode | Final Equity | Net Profit | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid | Blocked Open Overweight | No Flat Checks | Partial Flat Rebal | All Flat Rebal |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fullreb_flow_thr2 | fullreb | 360096.9533 | 308096.9533 | 111.9378 | 46.7762 | 2.3930 | 105.8361 | 237 | 1098.7909 | 0 | 0 | 0 | 0 |
| openfloor_flow_thr2 | openfloor | 342002.8566 | 290002.8566 | 108.9730 | 47.1114 | 2.3131 | 102.4660 | 561 | 633.2981 | 1997 | 0 | 0 | 0 |
| flatfreeze_flow_thr2 | flatfreeze | 314976.5607 | 262976.5607 | 103.6239 | 46.2198 | 2.2420 | 97.1617 | 855 | 330.3029 | 5273 | 3321 | 851 | 4 |
| cashonly_flow | cashonly | 307462.3680 | 255462.3680 | 102.0393 | 47.4739 | 2.1494 | 95.6235 | 0 | 0.0000 | 0 | 0 | 0 | 0 |

## 해석
- `fullreb_flow_thr2` 대비 가장 실전적인 대안 중 best는 `openfloor_flow_thr2`였다. CAGR 변화 `-2.9648pp`, MDD 변화 `0.3352pp`, XIRR 변화 `-3.3701pp`.
- `blocked_open_overweight_checks`는 이상적인 리밸런싱이라면 줄였어야 할 open sleeve를 실제 제약 때문에 못 줄인 횟수다.
- `flat-freeze`가 크게 악화되면, 기존 리밸런싱 edge 상당 부분이 열린 포지션 리사이즈 가정에 의존했다는 뜻이다.

## 산출물
- 플롯: `105_backtest_btcusdt_scale06_adx002_allocator_realism_compare.png`
- 결과 CSV: `105_backtest_btcusdt_scale06_adx002_allocator_realism_compare.csv`
- 곡선 CSV: `105_backtest_btcusdt_scale06_adx002_allocator_realism_compare_curves.csv`
- 상태 CSV: `105_backtest_btcusdt_scale06_adx002_allocator_realism_compare_sleeve_state.csv`
- flat 요약 CSV: `105_backtest_btcusdt_scale06_adx002_allocator_realism_compare_flat_summary.csv`