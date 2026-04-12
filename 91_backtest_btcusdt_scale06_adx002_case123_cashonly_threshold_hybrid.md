# 91번 연구: Case123 Cash-Only + Threshold Hybrid

## 설정
- 목표는 `월 적립금은 underweight 쪽에만 넣고`, drift가 너무 커질 때만 전체 리밸런싱하는 하이브리드 구조를 검증하는 것이다.
- 공통 슬리브는 case123 최신 곡선이다.
- baseline은 `thr2_fullreb_targettopup`: 88번의 case123 threshold 2%와 같은 풀 리밸런싱 구조다.
- `cashonly_no_fullreb`는 새 돈만 underweight 쪽에 넣고, 기존 자산은 한 번도 팔지 않는다.
- 공통 구간: `2022-01-01 08:00:00` -> `2026-03-15 05:19:00`

## 결과

| Variant | Threshold %p | Final Equity | Net Profit | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid_thr4 | 4.0000 | 347021.5772 | 295021.5772 | 109.5318 | 46.2920 | 2.3661 | 103.4097 | 52 | 269.9028 |
| thr2_fullreb_targettopup | 2.0000 | 348965.8141 | 296965.8141 | 110.4422 | 46.7762 | 2.3611 | 103.7742 | 195 | 473.5771 |
| hybrid_thr2 | 2.0000 | 348965.8141 | 296965.8141 | 110.4422 | 46.7762 | 2.3611 | 103.7742 | 195 | 473.5771 |
| hybrid_thr6 | 6.0000 | 338995.9986 | 286995.9986 | 108.9706 | 46.4085 | 2.3481 | 101.8878 | 22 | 155.4724 |
| hybrid_thr10 | 10.0000 | 323009.7831 | 271009.7831 | 105.5030 | 47.4718 | 2.2224 | 98.7700 | 5 | 98.5541 |
| hybrid_thr8 | 8.0000 | 321792.3835 | 269792.3835 | 105.0120 | 47.4724 | 2.2121 | 98.5277 | 8 | 96.2751 |
| cashonly_no_fullreb | N/A | 307408.0603 | 255408.0603 | 101.9392 | 47.4740 | 2.1473 | 95.6080 | 0 | 0.0000 |

## 핵심 해석
- best variant: `hybrid_thr4`
- best vs baseline: TWR CAGR `-0.9104pp`, MDD `-0.4842pp`, XIRR `-0.3645pp`, fee `-203.6743`.
- cash-only only vs baseline: TWR CAGR `-8.5031pp`, MDD `0.6978pp`, XIRR `-8.1662pp`.
- 이 연구가 좋게 나오면 `환전/스왑은 거의 안 하고`, 월 적립금과 드물게만 전체 리밸런싱해도 실전 성과를 많이 유지할 수 있다는 뜻이다.

## 산출물
- 플롯: `91_backtest_btcusdt_scale06_adx002_case123_cashonly_threshold_hybrid.png`
- 성과 CSV: `91_backtest_btcusdt_scale06_adx002_case123_cashonly_threshold_hybrid.csv`
- 곡선 CSV: `91_backtest_btcusdt_scale06_adx002_case123_cashonly_threshold_hybrid_curves.csv`
- 보고서: `91_backtest_btcusdt_scale06_adx002_case123_cashonly_threshold_hybrid.md`