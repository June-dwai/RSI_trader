# 128 Case2 vs 현재 `rsi_adx` 라이브 전략 비교 요청서

## 목적
- 현재 운영 중인 `rsi_adx` 라이브 전략이 연구용 `case2`와 실제로 동일한지 확인하고 싶습니다.
- 신규 전략을 바로 추가해 달라는 요청이 아니라, **현재 돌고 있는 전략과 연구 기준 로직의 차이점이 있는지 점검**해 달라는 요청입니다.

## 비교 기준 파일
- 연구 기준 로직:
  - [128_live_case2_case3best_logic.py](/c:/AppDev/Free_trader/128_live_case2_case3best_logic.py)
  - 이 중 `case2` 관련 함수/상태만 비교 대상
- 현재 라이브 후보 파일:
  - [live_rsi_bot.py](/c:/AppDev/Free_trader/live_rsi_bot.py)
  - [live_rsi_bot_2.py](/c:/AppDev/Free_trader/live_rsi_bot_2.py)

## 요청 내용
- 현재 운영 중인 `rsi_adx` 전략이 위 `128`의 `case2`와 같은 계보인지 확인해 주세요.
- 같다면 그대로 유지해도 되는지 알려 주세요.
- 다르다면 **정확히 어떤 부분이 다른지 항목별로 정리**해 주세요.
- 가능하면 아래 형식으로 비교 결과를 주시면 좋겠습니다.

## 확인해 달라는 항목

### 1. 지표 계산
- RSI period가 같은지
- ADX 계산식이 같은지
- 4시간 EMA200 기준이 같은지
- `직전 완성 4h EMA`를 쓰는지

### 2. EMA touch gate
- `case2`는 기본적으로 `previous closed 4h touch` 기준입니다.
- 현재 `rsi_adx`가
  - 직전 완성 4h touch만 보는지
  - 아니면 현재 진행 중 4h의 touch-so-far도 섞는지
확인해 주세요.

### 3. 진입 조건
- 롱: `RSI <= oversold` + `bullish trend`
- 숏: `RSI >= overbought` + `bearish trend`
- 이 진입 조건이 현재 라이브 코드와 동일한지 확인해 주세요.

### 4. DCA 규칙
- DCA 기준 가격이 무엇인지
  - `recent_trade_price`
  - `last_entry_price`
  - `avg_entry_price`
- DCA 간격이 같은지
  - 연구 기준은 대략 `0.5%`
- ADX multiplier 규칙이 같은지
- 최대 추가 진입 수가 같은지

### 5. cooldown 규칙
- 연구 기준 `128 case2`는 `bars_since_last_order` 기반입니다.
- 현재 `rsi_adx`는 실제 시간 초(`seconds`) 기반일 가능성이 있습니다.
- 이 차이가 있는지 확인해 주세요.

### 6. stop / partial close / reentry
- `3% stop`
- `80% partial close`
- 이후 `3% 추가 이동 시 reentry`
- 위 사이클이 현재 코드와 동일한지 확인해 주세요.

### 7. reverse signal
- 반대 신호가 왔을 때
  - `80% partial close + 반대 방향 신규 open`
이 구조가 현재 코드와 동일한지 확인해 주세요.

### 8. take profit
- `1.2% TP`
- 라이브 코드가 동일하게 쓰는지 확인해 주세요.

## 제가 보기엔 특히 체크가 필요한 부분

### A. `live_rsi_bot.py`
- [live_rsi_bot.py](/c:/AppDev/Free_trader/live_rsi_bot.py:519) 에서는 `previous closed 4h touch`만 보는 것으로 보입니다.
- [live_rsi_bot.py](/c:/AppDev/Free_trader/live_rsi_bot.py:473) 의 ADX 계산은 단순 rolling ADX처럼 보입니다.
- [live_rsi_bot.py](/c:/AppDev/Free_trader/live_rsi_bot.py:1973) 이후 DCA는 초 단위 cooldown과 `last_entry_price` 기준처럼 보입니다.
- [live_rsi_bot.py](/c:/AppDev/Free_trader/live_rsi_bot.py:2017) 진입은 현재 가격 vs EMA200으로 바로 판정하는 구조처럼 보입니다.

### B. `live_rsi_bot_2.py`
- [live_rsi_bot_2.py](/c:/AppDev/Free_trader/live_rsi_bot_2.py:375) 를 보면 `touch_prev_closed OR current touch-so-far`가 들어가 있어 보입니다.
- 이 부분은 연구 기준 `128 case2`와 다를 수 있습니다.
- 대신 [live_rsi_bot_2.py](/c:/AppDev/Free_trader/live_rsi_bot_2.py:656) 쪽은 연구용 case2 롱 로직에 더 가까워 보입니다.

## 원하는 답변 형태
- `현재 운영 중인 rsi_adx는 어느 파일 기준인지`
- `128 case2와 완전히 같은지 / 부분적으로 다른지`
- `다르다면 어떤 부분이 다르고, 실전 결과에 어떤 영향을 줄 수 있는지`
- `그 차이를 유지하는 게 나은지, case2 쪽으로 맞추는 게 나은지`

## 한 줄 요청
- 현재 운영 중인 `rsi_adx` 전략이 `128 case2`와 실제로 같은 전략인지 코드 기준으로 비교해 주시고, 다르면 차이점을 항목별로 정리해 주세요.
