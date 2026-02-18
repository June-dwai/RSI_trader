# `001_backtest_btcusdt.py` 백테스트 문서

## 1) 개요
- 대상 코드: `001_backtest_btcusdt.py`
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
  - RSI(`period=6`, EWMA 방식)
  - ADX(`period=14`, EWM/ATR 기반)
  - EMA 스택(`ema16`, `ema50`, `ema99`, `ema200_1m`) + `ema_status`
- `4h` 기준:
  - EMA200 (`shift(1)` 적용)
  - EMA 터치 여부(`high >= ema200` and `low <= ema200`)
- `1m`에 `4h` EMA200/터치 정보 merge + ffill

## 3.2 진입 조건
- 공통:
  - 쿨다운 충족 (`time_since_last >= cooldown_time`)
  - EMA 터치 중이면 진입 금지 (`skip_entry_when_ema_touch=True`)
- Long:
  - `rsi <= rsi_oversold`
  - `trend == bullish` (`close > 4h ema200`) 조건에서만 허용
- Short:
  - `rsi >= rsi_overbought`
  - `trend == bearish` (`close <= 4h ema200`) 조건에서만 허용

## 3.3 포지션 운영
- 첫 진입 수량:
  - `qty = (capital * initial_entry_capital_ratio) / price * entry_scale`
- 동일 방향 추가 진입:
  - Long: 직전 체결가 대비 `-0.5%` 이상 하락
  - Short: 직전 체결가 대비 `+0.5%` 이상 상승
  - ADX 기반 가중치(1~3배), 최대 진입 횟수 `max_entry_count=5`
- 반대 신호 발생:
  - 반대 포지션 즉시 오픈 없이, 기존 포지션 일부만 청산
  - 부분청산 비율은 `ema_status`에 따라 20% 또는 40%

## 3.4 청산 조건
- 익절:
  - Long: `price >= avg_entry * (1 + take_profit_pct)`
  - Short: `price <= avg_entry * (1 - take_profit_pct)`
- 손절:
  - 기본 3% 불리한 방향 이동 시 80% 부분청산
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
- 콘솔 실행: `python 001_backtest_btcusdt.py`
- 플롯 파일: `backtest_real_results.png`

## 6) 성능 결과

## 6.1 백테스트 구간
- 실측 에쿼티 구간: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`

## 6.2 핵심 수익/리스크 지표

| 항목 | 값 |
|---|---:|
| 초기 자본 | 1,000.0000 USDT |
| 최종 자본 (Final Equity) | 6,041.7178 USDT |
| 순이익 (Final Equity - Initial) | 5,041.7178 USDT |
| 총 수익률 | 504.1718% |
| CAGR | 54.8671% |
| MDD | 40.7136% |
| 최대 낙폭 금액 | 2,513.2679 USDT |
| 최대 Run-up | 634.5757% |
| Calmar Ratio | 1.3476 |
| 연환산 변동성 (365d) | 54.0130% |
| Sharpe (365d) | 1.0884 |
| Sortino (365d) | 1.3437 |

## 6.3 거래 성능 지표

| 항목 | 값 |
|---|---:|
| 총 거래 수 | 1,460 |
| Long 거래 수 | 736 |
| Short 거래 수 | 724 |
| 전체 승률 | 69.4521% |
| Long 승률 | 70.2446% |
| Short 승률 | 68.6464% |
| 총 이익 (Gross Profit) | 35,709.3592 USDT |
| 총 손실 (Gross Loss) | -27,324.6283 USDT |
| Profit Factor | 1.3069 |
| 평균 손익/거래 | 5.7430 USDT |
| 중앙값 손익/거래 | 13.9373 USDT |
| 평균 수익률/거래 | 0.5743% |
| 중앙값 수익률/거래 | 1.3937% |
| 평균 보유시간 | 2,632.3904분 (약 43.87시간) |
| 중앙값 보유시간 | 879.0000분 (약 14.65시간) |
| 최대 연속 승리 | 51 |
| 최대 연속 손실 | 18 |

## 6.4 청산 사유 분포

| 청산 사유 | 건수 |
|---|---:|
| Take Profit | 1,014 |
| Reverse Signal | 303 |
| Stop Loss | 142 |
| Final Close | 1 |

## 6.5 단일 거래 극값

| 항목 | 값 |
|---|---|
| 최고 수익 거래 | `+197.3473 USDT` (`+19.7347%`) / `LONG` / `2025-05-20 00:15:00` / `Take Profit` |
| 최대 손실 거래 | `-417.8107 USDT` (`-41.7811%`) / `LONG` / `2025-05-29 17:43:00` / `Stop Loss` |

## 6.6 월별 손익 방향성
- 수익 월: `22`
- 손실 월: `27`
- 보합 월: `0`

## 7) 해석 시 유의사항
- 수익률은 높지만 승률/손익비가 `002` 대비 보수적인 특성을 보이며, 손절/리버스 시 손실 폭이 상대적으로 큼.
- 포지션 반전 시 즉시 반대 포지션 오픈이 아니라 부분청산 중심이라 추세 급변 구간에서 대응 속도가 느릴 수 있음.
- 거래 빈도(1,460회)가 높아 실거래 시 수수료/슬리피지 민감도가 큼.
