# `backtest_btcusdt_ema200_standalone.py` 매매 로직 상세 설명

본 문서는 현재 백테스트 코드(`backtest_btcusdt_ema200_standalone.py`)가 실제로 어떤 규칙으로 매매를 수행하는지, 실행 순서와 상태 전이를 기준으로 정리한 것이다.

## 1) 실행 진입점

- 엔트리 포인트: `main()`
  - `run_baseline_ema200()` 실행
  - `summarize(bt)`로 수익 지표 계산
  - `save_backtest_plot(bt)`로 그래프 저장

## 2) 사용 데이터 및 기간

- 거래 종목: `SYMBOL = "BTCUSDT"`
- 시작/종료:
  - `BACKTEST_START = "2022-01-01"`
  - `BACKTEST_END = "2026-02-12"`
- 데이터 로딩:
  - 1분봉(`1m`) 구간:
    - `2022-01-01 ~ 2024-12-31`
    - `2025-01-01 ~ 2026-02-12`
  - 4시간봉(`4h`) 구간:
    - `2021-07-01 ~ 2021-12-31`
    - `2022-01-01 ~ 2024-12-31`
    - `2025-01-01 ~ 2026-02-12`
- 캐시 파일:
  - `historical_data_mainnet/{SYMBOL}_{timeframe}_{start}_{end}.pkl`

## 3) 전처리(`_clean_data`)

전처리는 두 단계로 수행된다.

### 3.1 IQR 기반 이상치 필터
- `close/high/low`를 IQR(25%, 75%) 기준으로:
  - `lower = Q1 - 1.5*IQR`
  - `upper = Q3 + 1.5*IQR`
  - 이 범위를 벗어난 값 제거

### 3.2 1분봉 급등락 제거
- `open_gap, close_gap, body_gap, range_gap, high_gap, low_gap`를 직전 종가 대비 퍼센트 변화로 계산
- 어떤 항목이든 10% 초과면 jump로 간주하고 제거

## 4) 지표 계산

`run(df_1m, df_4h)` 안에서 1분봉 기준으로 지표 계산.

- RSI: `period=6` (EWMA 평활 사용)
  - 상승/하락 폭 분리 후 `avg_gain`, `avg_loss` EWM
  - 양쪽이 0이면 RSI=50, 손실은 0 / 이익은 100 처리
- ADX: `period=14` (커스텀 구현)
  - True Range(TR), +DM, -DM 기반
- EMA:
  - 1분봉: `ema16, ema50, ema99, ema200_1m`
  - 4시간봉: `ema200` (shift(1) 적용하여 다음 바를 미리 보지 않도록 설계)
- EMA 상태(`ema_status`)
  - `bullish`: `ema16 > ema50 > ema99 > ema200_1m`
  - `bearish`: 반대
  - 아니면 `mixed`
- 4시간봉 EMA 터치 플래그(`ema_touch`)
  - 봉의 `high >= ema200` & `low <= ema200`
  - 1분봉 행으로 forward-fill 후 사용

## 5) 추세/진입 방향 결정

- `trend = close > ema200 ? bullish : bearish`
- `require_ema_trend_for_entry = True` 이므로:
  - 추세가 `bullish`면 `allow_short = False`
  - 추세가 `bearish`면 `allow_long = False`
- 또한 `skip_entry_when_ema_touch = True`일 때 EMA 터치 구간(`ema_touch_now`)에서는 진입 금지

## 6) 매매 반복 로직(메인 루프)

매 루프(`i`)에서 1분봉 데이터 기준으로 다음을 수행.

1. NaN 체크 (`rsi`, `adx`, `ema200`)가 있으면 스킵
2. `_check_trend_change(...)`
3. `_check_stop_loss(...)`
4. 진입 판단
   - 트레이딩 HALT 조건은 항상 False
   - `time_since_last >= cooldown_time` (기본 5분)에만 진입 시도
   - 진입 금지(EMA 터치) 조건 만족 시 스킵
   - RSI 임계값 충족 시
     - `rsi <= rsi_oversold`면 LONG
     - `rsi >= rsi_overbought`면 SHORT
5. `_check_take_profit(...)`
6. `_record_equity(...)`

루프 종료 후 마지막 시점에서 미청산 포지션은 `Final Close`로 청산한다.

## 7) 매수/매도 규칙

### 7.1 기본 진입(_process_long_entry / _process_short_entry)

- 현재 비포지션일 때
  - 매수/매도 수량:
    - `qty = (capital * initial_entry_capital_ratio) / price * entry_scale`
    - 기본값: `initial_entry_capital_ratio = 1.0`, `entry_scale = 0.50`
  - `_open_position` 후 `cooldown_time` 갱신

- 동일 방향 추가 진입(추세 내 평균 단가 조정)
  - LONG: 최근 체결가가 최근 진입가 대비 0.5% 하락 (`<= 0.995`)일 때
  - SHORT: 최근 체결가가 최근 진입가 대비 0.5% 상승 (`>= 1.005`)일 때
  - 추가량 = `position_quantity * _get_adx_multiplier(adx)`를 현재 잔여 추가 가능 수량과 비교 후 적용

- 반대 진입이 들어오면 부분 반전 청산
  - LONG 보유 중 SHORT 조건 발생 시:
    - `close_ratio = 0.2` (ema_status == bearish) 또는 `0.4` (기타)
  - SHORT 보유 중 LONG 조건도 동일 비율 적용
  - `_partial_close`로 해당 수량만큼 닫음

### 7.2 ADX 가중 추가 진입 배수

- `_get_adx_multiplier(adx)`
  - `adx >= 50` → 3
  - `40 <= adx < 50` → 2
  - `adx < 40` → 1
  - `entry_count`가 `max_entry_count(=5)` 초과면 0 반환

### 7.3 청산 조건

#### Take Profit
- LONG: `price >= avg_entry * (1 + take_profit_pct)`
- SHORT: `price <= avg_entry * (1 - take_profit_pct)`
- 기본값: `take_profit_pct = 0.012` (1.2%)

#### Stop Loss
- 기본 손절 라인:
  - LONG: `entry * (1 - stop_loss_pct)` = 3% 하락
  - SHORT: `entry * (1 + stop_loss_pct)` = 3% 상승
- `stop_partial_close_ratio = 0.8` 이면 80%만 먼저 부분 청산 후 잔량 추적
- `enable_stop_reentry = True`이지만, 실제 재진입 로직은 현재 구현에서 사용 안 함(별도 함수가 존재만 함)

#### 최종 정리
- 백테스트 종료 시점에 잔여 포지션은 무조건 `Final Close` 처리

## 8) 포지션/자금 상태 업데이트

### 8.1 주문/수수료
- `_open_position`, `_add_to_position`, `_partial_close`, `_close_position`에서 모두
  - 거래 금액의 `commission`(기본 0.04%)를 차감
- `initial_capital` 대비 누적 손익률(`return_pct`)을 거래별로 기록

### 8.2 미실현손익 반영
- `self.capital`은 현금(실현손익 반영 계정)
- `equity`는 매 분마다:
  - 현금 + 현재 포지션의 미실현손익
- 거래일지는 `self.trades`에 사유(reason), 진입/청산시간, 수량, pnl 등 저장

## 9) 요약 지표 (`summarize`)

- `final_equity`
- `total_return_pct`
- `cagr_pct` (연환산 수익률)
- `max_dd_pct` (max drawdown)
- `trades` 개수
- `win_rate_pct` (승률)

## 10) 현재 설정 값(상단 파라미터 + 실행에서 override)

- 글로벌 기본값
  - `INITIAL_CAPITAL=1000`
  - `COMMISSION=0.0004`
  - `ENTRY_SCALE=0.50`
  - `rsi_period=6`, `rsi_oversold=15`, `rsi_overbought=85`
  - `stop_loss_pct=0.03`, `take_profit_pct=0.01`(기본), `ENTRY` 계열 등
- `run_baseline_ema200()`에서 덮어쓰기
  - `rsi_oversold = 18`
  - `rsi_overbought = 85`
  - `take_profit_pct = 0.012`
  - `stop_loss_pct = 0.03`
  - `base_cooldown = 5`

## 11) 활성화/비활성화된 옵션

다음 값은 코드에 존재하지만 현재 실행 루프에서 기본적으로는 비활성 상태다.

- `enable_trend_break_close = False`(추세 반전 시 강제 청산 비활성)
- `enable_adx_regime_filter = False`
- `enable_ema_stack_filter = False`
- `use_margin_pct_stop = False`(별도 마진 손절 계산 함수는 있으나 미사용)
- `_try_stop_reentry_by_rsi(...)`는 별도 구현되었으나 현재 호출되지 않음

## 12) 핵심 한줄 요약

- 이 백테스트는 **1분봉 RSI 신호를 중심으로, 4시간 EMA200 추세 필터와 진입/추가 진입 규칙, 부분 손절 + 고정 익절 구조**를 결합한 단일 전략이다.
- 현재 기본 동작은 과감한 멀티엔트리/부분청산 대신, 방향성 필터링 + 가격 조건 기반 추가 진입 + 자동 익절/손절으로 구조화되어 있다.
