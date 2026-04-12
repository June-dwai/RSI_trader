# 92번 연구: Case123 Regime Allocator Sweep

## 설정
- 90번에서 만든 `4시간 시장 상태 캐시`를 활용해 동적 weight allocator를 테스트한다.
- chop 구간에서는 case3 비중을 줄이거나 0으로 만들고, 강한 bear trend에서는 case3 비중을 늘린다.
- 판단 기준은 4시간 `ADX14`, `EMA200 대비 거리`, `확정 추세`다.
- baseline은 `base_static = 62/31/7` 고정 비중 + threshold 2% 구조다.
- 공통 구간: `2022-01-01 16:00:00` -> `2026-03-15 05:19:00`

## 결과

| Variant | Final Equity | Net Profit | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Avg Case3 W % | State Switches | Fee Paid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| chop18_b05_off | 345742.4175 | 293742.4175 | 109.9302 | 46.2809 | 2.3753 | 103.1738 | 5.9240 | 598 | 8862.7107 |
| chop22_b10_off | 355791.4454 | 303791.4454 | 111.3035 | 46.8662 | 2.3749 | 105.0464 | 5.0820 | 746 | 11361.3994 |
| base_static | 350890.1531 | 298890.1531 | 110.5695 | 46.7763 | 2.3638 | 104.1383 | 7.0000 | 0 | 550.8431 |
| chop22_b10_light | 347367.7431 | 295367.7431 | 109.8209 | 46.6729 | 2.3530 | 103.4795 | 5.0820 | 746 | 7659.3171 |
| chop22_b10_bear10 | 352087.2507 | 300087.2507 | 110.0825 | 47.0514 | 2.3396 | 104.3610 | 5.9090 | 1111 | 12612.3633 |
| chop22_b10_bear12 | 356865.1772 | 304865.1772 | 110.6519 | 47.3297 | 2.3379 | 105.2440 | 6.4603 | 1111 | 13675.1449 |
| chop26_b15_off | 345437.0498 | 293437.0498 | 108.9171 | 46.7093 | 2.3318 | 103.1162 | 4.1849 | 738 | 10715.0670 |

## 핵심 해석
- best variant: `chop18_b05_off`
- best vs baseline: TWR CAGR `-0.6393pp`, MDD `-0.4954pp`, XIRR `-0.9645pp`.
- 이 연구가 먹히면, 핵심은 `추세추종 성격의 case3를 언제 끄고 언제 키울지`에 있었다는 뜻이다.

## 산출물
- 플롯: `92_backtest_btcusdt_scale06_adx002_case123_regime_allocator_sweep.png`
- 성과 CSV: `92_backtest_btcusdt_scale06_adx002_case123_regime_allocator_sweep.csv`
- 곡선 CSV: `92_backtest_btcusdt_scale06_adx002_case123_regime_allocator_sweep_curves.csv`
- 보고서: `92_backtest_btcusdt_scale06_adx002_case123_regime_allocator_sweep.md`