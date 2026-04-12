# 94번 연구: 페어 스프레드 평균회귀

## 설정
- BTC/ETH/XRP 사이 비율 스프레드의 평균회귀만 먹는 시장중립 구조다.
- z-score가 entry threshold를 넘으면 스프레드 진입, mean 근처로 돌아오면 청산한다.
- 한쪽 자산을 50% 롱, 반대쪽을 50% 숏해서 gross exposure 100%를 유지한다.
- 목적은 방향성 BTC 의존도를 낮춘 low-MDD 대안을 찾는 것이다.

## 결과

| Variant | Pair | Final Equity | CAGR % | MDD % | Calmar | Trades | Fee Paid |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| xrp_btc_mr_42_e20_x05_s35 | XRPUSDT/BTCUSDT | 677.2940 | -8.8991 | 54.5924 | -0.1630 | 548 | 176.0205 |
| eth_btc_mr_84_e20_x05_s35 | ETHUSDT/BTCUSDT | 766.0050 | -6.2046 | 35.4393 | -0.1751 | 348 | 114.6150 |
| eth_btc_mr_42_e15_x03_s30 | ETHUSDT/BTCUSDT | 564.8636 | -12.7699 | 51.1371 | -0.2497 | 762 | 209.6980 |
| eth_xrp_mr_84_e20_x05_s35 | ETHUSDT/XRPUSDT | 466.6258 | -16.7365 | 66.2002 | -0.2528 | 357 | 105.2478 |
| eth_xrp_mr_42_e15_x03_s30 | ETHUSDT/XRPUSDT | 438.1007 | -17.9145 | 66.1358 | -0.2709 | 749 | 195.4601 |

## 해석
- best variant: `xrp_btc_mr_42_e20_x05_s35`
- 페어 전략은 절대 CAGR보다, 방향성 sleeve와 다른 경로를 만들어주는지가 더 중요하다.

## 산출물
- 플롯: `94_backtest_pair_spread_mean_reversion.png`
- 성과 CSV: `94_backtest_pair_spread_mean_reversion.csv`
- 곡선 CSV: `94_backtest_pair_spread_mean_reversion_curves.csv`
- 보고서: `94_backtest_pair_spread_mean_reversion.md`