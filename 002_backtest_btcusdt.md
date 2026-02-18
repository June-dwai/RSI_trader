# `002_backtest_btcusdt.py` 백테스트 문서

## 1) 개요
- 대상 코드: `002_backtest_btcusdt.py`
- 전략 타입: RSI Averaging + 4h EMA200 추세 필터
- 심볼: `BTCUSDT`
- 백테스트 설정 기간: `2022-01-01` ~ `2026-02-12`
- 시작 자본: `1000 USDT`
- 수수료: `0.04%` (`COMMISSION = 0.0004`)
- 진입 스케일: `0.50` (`ENTRY_SCALE = 0.50`)

## 2) 데이터 로드 및 전처리
- 캐시 경로: `historical_data_mainnet/{SYMBOL}_{timeframe}_{start}_{end}.pkl`
- 사용 데이터:
  - `1m`: `2022-01-01 ~ 2024-12-31`, `2025-01-01 ~ 2026-02-12`
  - `4h`: `2021-07-01 ~ 2021-12-31`, `2022-01-01 ~ 2024-12-31`, `2025-01-01 ~ 2026-02-12`
- 전처리:
  - IQR 기반 이상치 제거 (`close/high/low` 범위 필터)
  - `1m` 데이터에서 10% 이상 급격 점프 캔들 제거

## 3) 전략 로직 요약

## 3.1 신호 계산
- `1m` 기준:
  - RSI(`period=6`)
  - ADX(`period=14`)
- `4h` 기준:
  - EMA200 (`shift(1)` 적용)
  - EMA 터치 여부(`high >= ema200` and `low <= ema200`)
- `1m`에 `4h` EMA200/터치 정보 merge + ffill

## 3.2 진입 조건
- 공통:
  - 쿨다운 충족 (`time_since_last >= cooldown_time`)
  - EMA 터치 중이면 진입 금지 (`not ema_touch`)
- Long:
  - `rsi <= rsi_oversold`
  - `trend == bullish` (`close > 4h ema200`)
- Short:
  - `rsi >= rsi_overbought`
  - `trend == bearish` (`close <= 4h ema200`)

## 3.3 포지션 운영
- 첫 진입 수량:
  - 기본 `capital / price`
  - `FloorScaledRSIAveragingBacktest`에서 `ENTRY_SCALE` 반영 (`* 0.5`)
- 동일 방향 추가 진입:
  - Long: 직전 체결가 대비 `-0.5%` 이상 하락
  - Short: 직전 체결가 대비 `+0.5%` 이상 상승
  - ADX 기반 가중치(1~3배) 적용
  - 최대 포지션: 초기 수량의 5배
- 반대 신호 발생:
  - 기존 포지션 80% 부분청산 후 반대 포지션 오픈

## 3.4 청산 조건
- 익절:
  - Long: `price >= avg_entry * (1 + take_profit_pct)`
  - Short: `price <= avg_entry * (1 - take_profit_pct)`
- 손절:
  - Long: 진입가 대비 `-3%` 도달 시 80% 부분청산
  - Short: 진입가 대비 `+3%` 도달 시 80% 부분청산
  - 이후 동일 방향 추가 조건 만족 시 재진입
- 종료 시점:
  - 백테스트 마지막 캔들에서 잔여 포지션 `Final Close`

## 4) 실험 파라미터 (`run_baseline_ema200`)
- `rsi_oversold = 18`
- `rsi_overbought = 85`
- `take_profit_pct = 0.012`
- `stop_loss_pct = 0.03`
- `base_cooldown = 5`
- `cooldown_time = 5`

## 5) 결과 아티팩트
- 콘솔 실행: `python 002_backtest_btcusdt.py`
- 플롯 파일: `002_backtest_btcusdt.png`

## 6) 성능 결과

## 6.1 백테스트 구간
- 실측 에쿼티 구간: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`

## 6.2 핵심 수익/리스크 지표

| 항목 | 값 |
|---|---:|
| 초기 자본 | 1,000.0000 USDT |
| 최종 자본 (Final Equity) | 14,968.8275 USDT |
| 순이익 (Net Profit) | 13,968.8275 USDT |
| 총 수익률 | 1,396.8827% |
| CAGR | 93.0977% |
| MDD | 64.0331% |
| 최대 낙폭 금액 | 7,816.6232 USDT |
| 최대 Run-up | 2,764.1327% |
| Calmar Ratio | 1.4539 |
| 연환산 변동성 (365d) | 90.6183% |
| Sharpe (365d) | 1.1963 |
| Sortino (365d) | 1.4383 |

## 6.3 거래 성능 지표

| 항목 | 값 |
|---|---:|
| 총 거래 수 | 1,403 |
| Long 거래 수 | 703 |
| Short 거래 수 | 700 |
| 전체 승률 | 99.6436% |
| Long 승률 | 99.8578% |
| Short 승률 | 99.4286% |
| 총 이익 (Gross Profit) | 115,682.6329 USDT |
| 총 손실 (Gross Loss) | -28.3002 USDT |
| Profit Factor | 4,087.6954 |
| 평균 손익/거래 | 82.4336 USDT |
| 중앙값 손익/거래 | 47.0376 USDT |
| 평균 수익률/거래 | 8.2434% |
| 중앙값 수익률/거래 | 4.7038% |
| 평균 보유시간 | 1,121.1361분 (약 18.69시간) |
| 중앙값 보유시간 | 453.0000분 (약 7.55시간) |
| 최대 연속 승리 | 547 |
| 최대 연속 손실 | 1 |

## 6.4 청산 사유 분포

| 청산 사유 | 건수 |
|---|---:|
| Take Profit | 1,397 |
| Reverse | 5 |
| Final Close | 1 |

## 6.5 단일 거래 극값

| 항목 | 값 |
|---|---|
| 최고 수익 거래 | `+508.4488 USDT` (`+50.8449%`) / `SHORT` / `2026-02-07 07:14:00` / `Take Profit` |
| 최대 손실 거래 | `-9.9399 USDT` (`-0.9940%`) / `LONG` / `2025-02-04 09:06:00` / `Reverse` |

## 6.6 월별 손익 방향성
- 수익 월: `24`
- 손실 월: `25`
- 보합 월: `0`

## 7) 해석 시 유의사항
- 승률과 Profit Factor가 매우 높게 측정되어 과최적화 가능성, 체결 슬리피지/수수료 확장 반영 필요성을 함께 점검해야 함.
- `MDD 64%`로 낙폭이 크므로, 실전 적용 시 포지션 크기/리스크 한도 조정이 필수.
- 거래 빈도(1,403회)가 높아 거래소 수수료 체계 변화 및 실제 체결 비용에 민감함.
