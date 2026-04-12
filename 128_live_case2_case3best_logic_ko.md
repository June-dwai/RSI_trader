# 128 전략 로직 정의서

## 목적
- 이 파일 세트는 `case2`와 `126 best case3`를 기존 라이브 시스템에 붙이기 쉽게 `전략 로직 모듈` 형태로 분리한 것이다.
- 실거래 주문 실행, 브로커 연결, 포지션 조회, 상태 저장은 포함하지 않는다.
- 대신 `닫힌 봉 데이터 -> 액션 제안 -> 브로커 체결 -> 상태 sync` 흐름에 바로 꽂을 수 있게 설계했다.

대상 파일:
- 로직 모듈: [128_live_case2_case3best_logic.py](/c:/AppDev/Free_trader/128_live_case2_case3best_logic.py)
- 설명 문서: [128_live_case2_case3best_logic_ko.md](/c:/AppDev/Free_trader/128_live_case2_case3best_logic_ko.md)

## 포함된 두 전략

### 1. `case2`
- 연구 계보: `32 -> 42 -> 122/125/127`
- 성격: `1분봉 RSI/ADX 기반 양방향 DCA + reverse`
- 핵심:
  - `RSI <= 18` and `bullish trend`면 롱
  - `RSI >= 85` and `bearish trend`면 숏
  - 같은 방향이면 ADX에 따라 DCA
  - 반대 방향 신호면 `80% partial close + reverse open`
  - TP `1.2%`
  - SL `3.0%`에서 `80% partial close`, 이후 한 번 더 불리하게 가면 reentry

### 2. `case3best`
- 연구 계보: `117 -> 126 -> 127`
- 실제 사용 버전: `lb4_delay8_capna_cd0`
- 성격: `15분봉 4h trend + short gate + SMC OB 필터`
- 핵심:
  - 4시간 confirmed trend가 bullish면 롱, bearish면 숏 후보
  - 숏은 `24h 상단 유동성 스윕` 이후 `12개 15분봉` 동안만 허용
  - 숏 TP `20%`
  - stop `6%`
  - leverage는 전략 의미상 `3x`
  - 롱은 `bearish_ob_above_count <= 4`일 때만 허용
  - 롱은 bullish 전환 직후 바로 진입하지 않고 `8개 15분봉`을 기다린 뒤 허용

## 모듈 구조

### 공통 액션 객체
- `TradeAction`
- 라이브 시스템은 이 객체를 보고 주문을 만들면 된다.

주요 필드:
- `action`
  - `OPEN`
  - `ADD`
  - `PARTIAL_CLOSE`
  - `CLOSE`
- `side`
  - `LONG`
  - `SHORT`
  - close 계열이면 현재 포지션 방향
- `quantity_mode`
  - `capital_fraction`
  - `wallet_fraction`
  - `base_qty_multiple`
  - `position_fraction`
  - `absolute_qty`
- `quantity_value`
  - 수량 모드에 따라 해석이 달라진다
- `reduce_only`
  - close 계열 주문이면 `True`
- `desired_leverage`
  - case3에서 `3.0`
- `reference_price`
  - 전략 판단 기준 가격
- `stop_price`, `take_profit_price`
  - 라이브 시스템에서 보호주문 생성 시 참고
- `meta`
  - 보조 진단 정보

## 상태 객체

### `Case2State`
- `last_processed_ts`
- `last_order_ts`
- `position_side`
- `avg_entry_price`
- `position_qty`
- `base_entry_qty`
- `entry_count`
- `recent_trade_price`
- `stop_trigger_price`
- `stop_reentry_signed_qty`
- `pending_reentry_side`
- `pending_reentry_price`
- `pending_reentry_qty`

### `Case3State`
- `last_processed_ts`
- `position_side`
- `avg_entry_price`
- `position_qty`
- `locked_side`
- `short_gate_until_ts`
- `bullish_streak`
- `last_short_sweep_ts`

두 상태 객체 모두:
- `to_dict()`
- `from_dict()`

를 제공하므로 JSON/DB/파일로 저장하기 쉽다.

## 브로커 상태 sync

전략 로직은 내부 상태를 들고 가지만, 실거래에서는 반드시 브로커 상태로 덮어써주는 게 안전하다.

사용 함수:
- `sync_case2_state_from_broker(...)`
- `sync_case3_state_from_broker(...)`

권장 순서:
1. 거래소에서 현재 포지션 조회
2. state를 broker 정보로 sync
3. 최신 닫힌 봉 데이터로 평가
4. 액션 실행
5. 체결 후 state 저장

## 입력 데이터 요구사항

### `case2`
입력:
- `df_1m`
  - index 또는 컬럼 기준 시계열
  - 최소 컬럼: `open`, `high`, `low`, `close`
- `df_4h`
  - 최소 컬럼: `open`, `high`, `low`, `close`

전처리 함수:
- `prepare_case2_features(df_1m, df_4h)`

평가 함수:
- `evaluate_case2_latest(df_1m, df_4h, state)`

### `case3best`
입력:
- `df_1m`
- `df_4h`

전처리 함수:
- `prepare_case3best_features(df_1m, df_4h)`

평가 함수:
- `evaluate_case3best_latest(df_1m, df_4h, state)`

## 리턴 형식

두 평가 함수 모두 아래를 리턴한다.

1. `actions: list[TradeAction]`
2. `updated_state`
3. `diagnostics: dict`

`diagnostics`는 디버깅용이다.

예:
- `case2`
  - `rsi`
  - `adx`
  - `trend`
  - `ema_touch_live_nla`
  - `bars_since_last_order`
- `case3best`
  - `trend_4h_confirmed`
  - `short_sweep_event`
  - `short_gate_open`
  - `bullish_streak`
  - `bearish_ob_above_count`
  - `long_quality_ok`

## 주문 해석 규칙

### `case2`
- `OPEN + capital_fraction 0.60`
  - 현재 사용 가능한 전략 자본의 60%를 새 진입 기준으로 쓴다
- `ADD + base_qty_multiple`
  - 최초 base qty 기준 배수만큼 추가
  - ADX가 높을수록 배수가 커진다
- `PARTIAL_CLOSE + position_fraction 0.80`
  - 현재 포지션의 80%만 줄인다
- `CLOSE + position_fraction 1.00`
  - 전체 청산

### `case3best`
- `OPEN + wallet_fraction 0.98 + desired_leverage 3.0`
  - 선물 계좌 기준 margin fraction `98%`, leverage `3x` 의미
- `CLOSE + position_fraction 1.00`
  - 전체 청산

## 실제 라이브 루프 예시

주의:
- 파일명이 `128_live_case2_case3best_logic.py`처럼 숫자로 시작하므로 일반 `import 128_live_case2_case3best_logic` 문법은 사용할 수 없다.
- 기존 시스템에 붙일 때는 아래처럼 `importlib`로 경로 로딩하거나, 시스템 안으로 옮기면서 파일명을 `study128_live_case2_case3best_logic.py`처럼 바꿔서 써도 된다.

```python
import importlib.util
import sys
from pathlib import Path

module_path = Path("128_live_case2_case3best_logic.py").resolve()
spec = importlib.util.spec_from_file_location("study128_live_logic", module_path)
study128 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = study128
spec.loader.exec_module(study128)

Case2State = study128.Case2State
Case3State = study128.Case3State
evaluate_case2_latest = study128.evaluate_case2_latest
evaluate_case3best_latest = study128.evaluate_case3best_latest
sync_case2_state_from_broker = study128.sync_case2_state_from_broker
sync_case3_state_from_broker = study128.sync_case3_state_from_broker

# 1. 상태 복원
case2_state = Case2State()
case3_state = Case3State()

# 2. 브로커 포지션 sync
case2_state = sync_case2_state_from_broker(
    case2_state,
    position_side=broker_case2_side,
    avg_entry_price=broker_case2_avg,
    position_qty=broker_case2_qty,
    base_entry_qty=broker_case2_base_qty,
)
case3_state = sync_case3_state_from_broker(
    case3_state,
    position_side=broker_case3_side,
    avg_entry_price=broker_case3_avg,
    position_qty=broker_case3_qty,
)

# 3. 액션 평가
case2_actions, case2_state, case2_diag = evaluate_case2_latest(df_1m, df_4h, case2_state)
case3_actions, case3_state, case3_diag = evaluate_case3best_latest(df_1m, df_4h, case3_state)

# 4. 액션 실행
for action in case2_actions + case3_actions:
    execute_order(action)

# 5. 상태 저장
save_json(case2_state.to_dict())
save_json(case3_state.to_dict())
```

## 주의점

### 1. 닫힌 봉 기준으로만 호출
- `case2`는 `1분봉 close`
- `case3best`는 `15분봉 close`
- 미완성 봉으로 평가하면 백테스트와 달라진다.

### 2. 중복 바 평가 금지
- 내부에 `last_processed_ts`가 있어 같은 바를 중복 평가하면 `duplicate_bar`로 돌려준다.

### 3. 수량 계산 책임
- 모듈은 `신호와 수량 모드`를 제안한다.
- 실제 주문 수량 계산은 현재 계좌 잔고, 심볼 step size, hedge mode 여부를 반영해 라이브 시스템이 해야 한다.

### 4. case2 reverse
- 원본 의미는 `80% 줄이고 반대방향 오픈`이다.
- 실제 시스템에서 더 단순하게 `전량 close 후 반대방향 open`으로 바꾸면 성과가 조금 달라질 수 있다.

### 5. case3best는 2026 방어가 아직 약함
- 126/127 기준으로 장기 CAGR은 강하지만 2026만 보면 약점이 있었다.
- 따라서 라이브 적용 시:
  - 별도 daily loss cap
  - 계정 단위 max exposure
  - order failure fallback
  - stale state 감지
를 꼭 같이 두는 게 좋다.

## 추천 적용 방식

초기 적용 우선순위:
- 1순위: `case2`와 `case3best`를 각각 독립 슬리브로 분리 운용
- 2순위: 시스템 레벨에서 sleeve별 자본 배분
- 3순위: 포트폴리오 비중 조정

실전 감각 기준 추천:
- `case3best`는 고CAGR 코어
- `case2`는 완충 슬리브
- 둘을 같은 계좌에 넣더라도 내부 상태는 반드시 분리해서 저장

## 한 줄 결론
- `128_live_case2_case3best_logic.py`는 바로 live bot에 꽂을 수 있는 전략 모듈이다.
- 단, 파일명이 숫자로 시작하므로 `importlib` 경로 로딩 또는 파일명 변경 후 import 방식으로 연결하는 것을 권장한다.
- 브로커 연결부만 기존 시스템에 맞게 붙이면 `case2`와 `126 best case3`를 각각 독립적으로 운용할 수 있다.
