# 106번 연구: Bear-Regime Case1 Cut Compare

## 목적
- `openfloor` allocator를 유지한 채, bear regime에서 `case1`로 새 돈을 안 보내거나 기존 목표 비중을 줄였을 때 개선되는지 확인한다.
- bear regime 판정은 `trend_4h_confirmed == bearish`로 둔다.

## bear regime 빈도
- bear regime time ratio: `50.2325%`
- bear regime top-up ratio: `46.0000%`

## 결과

| Variant | Bear Case1 Factor | Bear Topup Block | Final Equity | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid | Avg W1 % | Avg W2 % | Blocked Open Overweight |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_openfloor | 1.00 | False | 339792.4788 | 108.5642 | 46.9869 | 2.3105 | 102.0448 | 563 | 633.5259 | 61.9600 | 30.9884 | 2022 |
| bear_topup_block_case1 | 1.00 | True | 340899.3203 | 107.6281 | 46.9870 | 2.2906 | 102.2560 | 574 | 645.8142 | 61.9600 | 30.9884 | 2214 |
| bear_cut25_openfloor | 0.75 | True | 355148.4087 | 108.4918 | 49.6201 | 2.1864 | 104.9278 | 1070 | 1305.6375 | 54.1844 | 38.7640 | 5085 |
| bear_cut50_openfloor | 0.50 | True | 350881.9321 | 107.9092 | 50.3087 | 2.1449 | 104.1368 | 428 | 821.1429 | 46.4088 | 46.5396 | 5314 |
| bear_cut100_openfloor | 0.00 | True | 346498.8400 | 106.6348 | 57.1879 | 1.8646 | 103.3162 | 298 | 792.8432 | 30.8576 | 62.0908 | 5285 |

## 해석
- best variant: `baseline_openfloor`. baseline 대비 CAGR `0.0000pp`, MDD `0.0000pp`, XIRR `0.0000pp`.
- `bear_topup_block_case1`은 새 돈만 막는 효과를 보여준다.
- `bear_cut25/50/100`은 기존 목표 비중 자체를 바꾸기 때문에, 월 입금 영향이 작아져도 계속 작동한다.

## 산출물
- 플롯: `106_backtest_btcusdt_scale06_adx002_bear_regime_case1_cut_compare.png`
- 결과 CSV: `106_backtest_btcusdt_scale06_adx002_bear_regime_case1_cut_compare.csv`
- 곡선 CSV: `106_backtest_btcusdt_scale06_adx002_bear_regime_case1_cut_compare_curves.csv`
- 보고서: `106_backtest_btcusdt_scale06_adx002_bear_regime_case1_cut_compare.md`