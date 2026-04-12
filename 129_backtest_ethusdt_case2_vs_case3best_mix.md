# 129번 연구: ETHUSDT case2 vs delay9 case3 vs 50:50 혼합

## 설정
- case3는 더 이상 102 ETH best를 쓰지 않고, 127 계열 long-quality case3를 ETH에 이식했다.
- 이번 연구의 case3 정의: `lb4_delay9_capna_cd0`
- 파라미터는 `lb4 / delay9 / capna / cd0`, leverage `3.0`, short TP `20%`, gate `12`, body ATR `0.25`다.
- 비교 구간: `2021-01-02 00:00:00` ~ `2026-04-12 03:15:00`
- Binance 기준 최신 닫힌 1m 바 시각: `2026-04-12 03:15:00`
- 2021 ETH 1m은 Binance public archive에서 보강했고, 최근 부족 구간은 Binance futures API로 이어 붙였다.
- 사용한 로컬 캐시:
  - `historical_data_mainnet\ETHUSDT_1m_2021-01-01_2021-12-31.pkl`
  - `historical_data_mainnet\ETHUSDT_1m_2022-01-01_2024-12-31.pkl`
  - `historical_data_mainnet\ETHUSDT_1m_2025-01-01_2026-04-12.pkl`

## 결과
| Variant | Final Equity | Total Return % | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| case2_only | 0.0000 | -100.0000 | -100.0000 | 100.0000 | -1.0000 | N/A | N/A |
| lb4_delay9_capna_cd0_only | 27038.1842 | 1251.9092 | 63.8550 | 92.8406 | 0.6878 | -57.9510 | 64.4957 |
| case2_case3best_half_mix | 13519.0921 | 575.9546 | 43.6733 | 92.8406 | 0.4704 | -57.9510 | 64.4957 |

## 해석
- `case2_only`: CAGR `-100.0000%`, MDD `100.0000%`, 2026 `N/A%`.
- `lb4_delay9_capna_cd0_only`: CAGR `63.8550%`, MDD `92.8406%`, 2026 `-57.9510%`.
- `case2_case3best_half_mix`: CAGR `43.6733%`, MDD `92.8406%`, 2026 `-57.9510%`.

## 출력물
- Plot: `129_backtest_ethusdt_case2_vs_case3best_mix.png`
- Metrics CSV: `129_backtest_ethusdt_case2_vs_case3best_mix.csv`
- Curves CSV: `129_backtest_ethusdt_case2_vs_case3best_mix_curves.csv`
- Report: `129_backtest_ethusdt_case2_vs_case3best_mix.md`