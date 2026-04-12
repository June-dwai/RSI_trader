# 128 Case3 라이브봇 전략 통합 요청서

## 목적
- 현재 사용 중인 live bot에 신규 전략 1개를 추가하고 싶습니다.
- 이번에 추가하려는 전략은 연구 `126/127`에서 사용한 `best case3` 로직입니다.
- 트레이딩뷰의 ICT/SMC 전체 기능을 복제하려는 목적은 아니고, **백테스트에서 성과를 낸 실제 매매 규칙**만 live bot 전략으로 넣는 것이 목표입니다.

## 전달 파일
- 로직 모듈: [128_live_case2_case3best_logic.py](/c:/AppDev/Free_trader/128_live_case2_case3best_logic.py)
- 설명 문서: [128_live_case2_case3best_logic_ko.md](/c:/AppDev/Free_trader/128_live_case2_case3best_logic_ko.md)

## 이번에 실제로 넣고 싶은 전략
- 우선순위는 `case3best` 전략입니다.
- 파일 안 함수명 기준:
  - `prepare_case3best_features(...)`
  - `evaluate_case3best_latest(...)`
  - `Case3State`
  - `sync_case3_state_from_broker(...)`

## 전략 요약
- 실행 기준 타임프레임은 `15분봉`입니다.
- 원천 데이터는 `1분봉 + 4시간봉`을 사용합니다.
- 상위 추세는 `4시간 EMA200 confirmed trend`로 판단합니다.
- 롱은 bullish 추세일 때만 봅니다.
- 숏은 bearish 추세라고 바로 들어가는 것이 아니라, `상단 유동성 스윕 발생 후 12개 15분봉 동안만` 진입 가능합니다.
- 숏은 `20% TP`, 롱/숏 공통 `6% stop`, liquidation guard가 들어갑니다.

## 핵심 진입 규칙

### 롱
- `4시간 confirmed trend == bullish`
- `bullish_streak > 8`
- `bearish_ob_above_count <= 4`
- 위 조건을 만족할 때만 롱 진입

### 숏
- `4시간 confirmed trend == bearish`
- 최근 `24시간 high`를 wick으로 넘겼다가 다시 아래로 종가 마감하는 `short sweep event` 발생
- sweep 발생 후 `12개 15분봉` 동안만 short gate 활성화
- gate가 열려 있고 `close < ema20`일 때만 숏 진입

## 구현 요청 사항
- 기존 live bot에 이 전략을 **독립 전략 하나**로 추가해 주세요.
- 다른 전략과 상태를 섞지 말고, `Case3State`는 별도 저장/복원되게 해 주세요.
- 판단은 반드시 `닫힌 15분봉 기준`으로만 해 주세요.
- 미완성 15분봉, 미완성 4시간봉 값은 사용하지 않게 해 주세요.
- 재시작 후에도 아래 상태가 복원되어야 합니다.
  - `position_side`
  - `avg_entry_price`
  - `position_qty`
  - `locked_side`
  - `short_gate_until_ts`
  - `bullish_streak`
  - `last_short_sweep_ts`
  - `last_processed_ts`

## 주문 해석 요청
- `OPEN`
  - 신규 진입
- `CLOSE`
  - 전체 청산
- `wallet_fraction 0.98`
  - 선물 지갑 기준 98% 사용 의미
- `desired_leverage = 3.0`
  - 3배 레버리지 설정 의미
- `stop_price`, `take_profit_price`
  - 가능하면 브로커 보호주문과 연결
  - 어렵다면 봇 내부 감시로 처리

## 개발 시 주의사항
- 파일명이 `128_live_case2_case3best_logic.py`처럼 숫자로 시작해서 일반 import가 안 될 수 있습니다.
- 방법은 둘 중 하나로 처리해 주세요.
  - `importlib`로 경로 로딩
  - 파일명을 시스템 내부에서 `study128_live_case2_case3best_logic.py`처럼 바꿔서 import
- 핵심은 파일명보다 **전략 로직 보존**입니다.

## 원하는 최종 결과
- 기존 live bot 안에서 `case3best` 전략을 on/off 가능하게 추가
- 전략별 상태 저장/복원 지원
- 실시간 1분 데이터 수집 후, 닫힌 15분봉마다 신호 평가
- 브로커 포지션과 state sync 가능
- 신호 발생 시 `OPEN/CLOSE` 주문이 안정적으로 실행

## 참고
- 이 전략은 트레이딩뷰 SMC 지표 전체를 완전 복제한 것이 아닙니다.
- 하지만 연구 `126/127`에서 실제 성과를 낸 `best case3` 매매 로직은 반영되어 있습니다.
- 즉, 목적은 “SMC 화면을 똑같이 그리는 것”이 아니라 “그 연구에서 이긴 매매 규칙을 라이브봇에서 재현하는 것”입니다.

## 한 줄 요청
- 첨부한 `128_live_case2_case3best_logic.py`의 `case3best` 로직을 기준으로, 현재 운영 중인 live bot에 독립 전략 1개로 통합해 주세요.
