# 93번 연구: 멀티코인 상대강도 시장중립

## 설정
- BTC/ETH/XRP 3개만 사용한다.
- 각 시점에서 상대적으로 강한 코인을 롱, 약한 코인을 숏하는 시장중립 구조다.
- gross exposure는 100%로 두고 롱 50% / 숏 50%를 유지한다.
- `momentum`은 강한 것을 롱, 약한 것을 숏하고 `reversal`은 반대로 간다.
- 목적은 기존 BTC 방향성 전략과 다른 low-MDD sleeve 후보가 있는지 보는 것이다.

## 결과

| Variant | Signal TF | Mode | Final Equity | CAGR % | MDD % | Calmar | Trades | Fee Paid |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| relrev_3d_14d_4h | 4h | reversal | 1340.8911 | 7.3039 | 38.9733 | 0.1874 | 2586 | 744.4710 |
| relrev_1d_7d_4h | 4h | reversal | 835.9165 | -4.1969 | 50.2149 | -0.0836 | 3586 | 780.8201 |
| relmom_3d_14d_4h | 4h | momentum | 163.0593 | -35.3291 | 88.8073 | -0.3978 | 2586 | 242.7043 |
| relmom_1d_7d_4h | 4h | momentum | 170.4168 | -34.5120 | 86.6487 | -0.3983 | 3586 | 366.4063 |
| relmom_1d_7d_1h | 1h | momentum | 129.5663 | -38.6652 | 88.3867 | -0.4375 | 3596 | 317.5790 |

## 해석
- best variant: `relrev_3d_14d_4h`
- 시장중립 구조는 높은 CAGR보다 낮은 MDD와 기존 BTC 방향성과 다른 경로가 더 중요하다.

## 산출물
- 플롯: `93_backtest_multicoin_relative_strength_market_neutral.png`
- 성과 CSV: `93_backtest_multicoin_relative_strength_market_neutral.csv`
- 곡선 CSV: `93_backtest_multicoin_relative_strength_market_neutral_curves.csv`
- 보고서: `93_backtest_multicoin_relative_strength_market_neutral.md`