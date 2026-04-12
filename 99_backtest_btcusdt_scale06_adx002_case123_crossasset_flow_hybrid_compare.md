# 99번 연구: Cross-Asset Flow Hybrid Compare

## 설정
- 98의 best 상태 정의인 `flow_combo6_thr2`를 고정한다.
- 상태 신호의 원천만 BTC, ETH, XRP 4시간 taker flow/volume state로 바꿔 본다.
- 포트폴리오 자체는 동일한 BTC case1/case2/case3를 유지한다.

## 결과

| Source Asset | Final Equity | TWR CAGR % | TWR MDD % | Post-2025 TWR CAGR % | Post-2025 TWR MDD % | Rebalances | State Switches | Fee Paid | First Event |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BTCUSDT | 358461.7280 | 111.9987 | 45.1238 | 36.0845 | 36.2024 | 231 | 44 | 1088.8860 | 2025-01-13 08:00:00 |
| ETHUSDT | 356398.5412 | 111.7180 | 45.1238 | 35.4547 | 36.3786 | 242 | 57 | 1184.1426 | 2025-01-03 12:00:00 |
| XRPUSDT | 351586.7192 | 111.0102 | 45.1238 | 33.8763 | 36.3412 | 197 | 6 | 582.4983 | 2026-02-15 08:00:00 |

## 해석
- best source asset: `BTCUSDT`
- 전체 기간 MDD가 동일하게 보인 이유는 세 상태 소스 모두 2025년 전에는 이벤트가 거의 없어서, 2023~2024 drawdown을 동일하게 겪었기 때문이다.
- best vs BTC-state baseline: TWR CAGR `0.0000pp`, MDD `0.0000pp`, XIRR `0.0000pp`, fee `0.0000`.

## 산출물
- 플롯: `99_backtest_btcusdt_scale06_adx002_case123_crossasset_flow_hybrid_compare.png`
- 성과 CSV: `99_backtest_btcusdt_scale06_adx002_case123_crossasset_flow_hybrid_compare.csv`
- 곡선 CSV: `99_backtest_btcusdt_scale06_adx002_case123_crossasset_flow_hybrid_compare_curves.csv`
- 상태 이벤트 CSV: `99_backtest_btcusdt_scale06_adx002_case123_crossasset_flow_hybrid_compare_state_events.csv`
- 보고서: `99_backtest_btcusdt_scale06_adx002_case123_crossasset_flow_hybrid_compare.md`