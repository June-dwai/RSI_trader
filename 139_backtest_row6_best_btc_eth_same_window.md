# 139번 연구: 138 best 사례 BTC vs ETH 동일 구간 비교

- 적용 전략은 `138`에서 실전형으로 가장 좋아 보였던 `combo_trim2p0_unlock24h`이다.
- 공통 비교 구간은 `2021-01-02 00:00:00` ~ `2026-03-15 05:30:00`이다.
- BTC는 `138`과 같은 로컬 `4h` 캐시 파이프라인을 유지했다: `native_4h_cache`.
- ETH는 `2021-01-01 ~ 2021-12-31` 전체 `4h` 캐시가 없어 `resampled_4h_from_1m` 방식으로 만들었다.
- 로컬 원시 캐시 최신 시각은 BTC `2026-03-15 05:19:00`, ETH `2026-03-15 05:19:00`였고, 공통 종료 시점은 BTC 기준에 맞춰 잘렸다.

| Symbol | Final Equity | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Bull Trims | Unlocks | Slow Bear Shorts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTCUSDT | 213826.4261 | 180.7641 | 63.9784 | 2.8254 | 19.1725 | 44.9550 | 65 | 41 | 17 |
| ETHUSDT | 3807.4085 | 29.3369 | 97.4863 | 0.3009 | -1.1575 | 55.3218 | 72 | 41 | 13 |

- BTC: CAGR `180.7641%`, MDD `63.9784%`, 2026 `19.1725%`.
- ETH: CAGR `29.3369%`, MDD `97.4863%`, 2026 `-1.1575%`.
- ETH/BTC CAGR 비율은 `0.1623`배, MDD 차이는 `33.5079`%p다.

## 해석
- 이 비교는 자산만 바꾸고 로직은 그대로 유지한 크로스-애셋 적합성 체크다.
- `unlock + slow bear short`가 ETH에서도 작동하면 row6 개선이 자산 공통 구조일 가능성이 높고, 아니면 BTC 특화 성격이 강하다고 볼 수 있다.

## 산출물
- Plot: `139_backtest_row6_best_btc_eth_same_window.png`
- Metrics CSV: `139_backtest_row6_best_btc_eth_same_window.csv`
- Curves CSV: `139_backtest_row6_best_btc_eth_same_window_curves.csv`
- Report: `139_backtest_row6_best_btc_eth_same_window.md`
