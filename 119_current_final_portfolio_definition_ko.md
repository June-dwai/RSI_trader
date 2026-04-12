# 현재 최종 포트폴리오 정의서

## 문서 목적

이 문서는 Study 119 시점 기준으로, 현재 우리가 가장 유력한 `BTCUSDT 멀티 슬리브 포트폴리오`를 한 번에 다시 복원할 수 있도록 정리한 문서다.

연구가 100개를 넘으면서 흐름이 자주 끊기기 때문에, 이 문서는 아래 질문에 바로 답하도록 만든다.

- 현재 best 포트폴리오는 정확히 무엇인가?
- case1 / case2 / case3는 각각 어디서 왔는가?
- 비중은 얼마인가?
- 리밸런스는 어떻게 하는가?
- case3는 왜 예전보다 비중이 커졌는가?
- 85 -> 116 -> 117 -> 118 -> 119 흐름에서 무엇이 바뀌었는가?

## 현재 최종 결론 한 줄 요약

현재 기준 최종 best 포트폴리오는:

- `case1 49%`
- `case2 27%`
- `case3 24%`
- `1시간 리밸런스`
- `case3 = Study 117 best 엔진`

이다.

러프하게 말하면:

- `case1 : case2 : case3 ~= 2 : 1 : 1`

에 가깝다.  
정확한 숫자는 `49 : 27 : 24`다.

## 현재 최종 best 포트폴리오

Study 119 기준 최종 우승 variant:

- `lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w49_27_24`

핵심 성과:

- CAGR: `132.2561%`
- MDD: `42.8382%`
- Calmar: `3.0873`

비교 기준:

- rebuilt Study 85 leader 대비
  - CAGR `+10.2983%p`
  - MDD `-2.2735%p`
  - Calmar `+0.3839`
- rebuilt Study 118 best 대비
  - CAGR `+2.7352%p`
  - MDD `-0.7297%p`
  - Calmar `+0.1145`

백테스트 공통 기간:

- `2022-01-01 08:00:00` ~ `2026-02-12 00:00:00`

## 포트폴리오 구성

### 1. 전체 구조

포트폴리오는 `3-sleeve` 구조다.

- `case1`
- `case2`
- `case3`

세 개의 equity curve를 하나의 총자산 포트폴리오로 묶고, 정해진 비중으로 리밸런스한다.

### 2. 현재 최종 비중

현재 최종 best 비중은 다음과 같다.

- `case1 = 49%`
- `case2 = 27%`
- `case3 = 24%`

즉 해석상:

- case1은 여전히 가장 큰 코어
- case2는 중간 코어
- case3는 더 이상 작은 실험 sleeve가 아니라 `준-코어(quasi-core)` 역할

이다.

이건 예전 85 계열에서 case3가 `7% 내외`였던 것과 매우 다르다.

### 3. 리밸런스

현재 최종 best에서는:

- `1시간 리밸런스`

를 사용한다.

이건 매우 중요하다.  
Study 119의 핵심 메시지 중 하나는, **남아 있던 알파 일부가 case3 교체 자체가 아니라 리밸런스 주기 단축에서 나왔다**는 점이다.

즉 현재 best는:

- 좋은 case3를 쓰는 것
- 그 case3 비중을 충분히 크게 두는 것
- 그리고 `4시간`이 아니라 `1시간`으로 더 자주 리밸런스하는 것

이 세 가지 조합으로 만들어졌다.

## 각 sleeve 정의

## Case1

현재 포트폴리오의 case1은 다음 계보를 따른다.

- 직접 소스는 `62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune.py`
- 포트폴리오 통합 단계에서는 `74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.py`에서 불러온다
- 실제 사용 variant는 `shallow6_else2bull`

정리하면:

- `case1 = Study 62의 shallow6_else2bull에서 나온 equity_case1`

이다.

### Case1의 역할

case1은 오래된 코어 슬리브다.  
새로운 연구들에서도 거의 계속 살아남았고, 최종 포트폴리오에서도 가장 큰 비중을 유지하고 있다.

즉 현재 기준 해석은:

- `case1은 아직도 코어 엔진으로 유효`

다.

## Case2

현재 포트폴리오의 case2도 case1과 같은 계보 묶음에서 온다.

- `62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune.py`에서 포트폴리오용으로 불러온 `equity_case2`
- 내부적으로는 `42_backtest_btcusdt_scale06_adx002_equity_combo_curves.csv`에서 가져온다

정리하면:

- `case2 = Study 62를 통해 불러오는 기존 고정 sleeve`

다.

### Case2의 역할

case2는 case1보다 비중은 낮지만 여전히 살아남았고, 최종 best에서도 `27%`를 차지한다.

즉 현재 해석은:

- `case2도 아직 교체 대상이 아니라 유효한 중간 코어`

다.

## Case3

현재 포트폴리오의 case3는 예전 85 시절의 case3가 아니다.  
현재 final best에서는 **Study 117 winner**를 case3 sleeve로 사용한다.

현재 채택된 case3 source:

- `lv3p0_g12_body25_tp20_lb5_none`

즉:

- `case3 = Study 117 best 계열 단일 엔진`

이다.

## 현재 case3의 단일 전략 정의

case3 source인 `lv3p0_g12_body25_tp20_lb5_none`의 핵심 설정은 아래와 같다.

- 레버리지: `3.0x`
- short gate bars: `12`
- short sweep body 기준: `0.25 * ATR20`
- short TP: `20%`
- SR 진입 필터: `none`
- long block threshold: `5`

이 전략의 standalone 성과는:

- CAGR: `151.3261%`
- MDD: `64.5809%`
- Calmar: `2.3432`

였다.

즉 standalone으로는 공격적이고 MDD도 큰 편이지만,  
포트폴리오에 `24%` 비중으로 넣고 나머지를 case1/case2가 받쳐주면 오히려 전체 성과가 더 좋아졌다.

## 현재 case3의 매매 아이디어 요약

case3를 짧게 설명하면:

- 상위 방향은 `4시간 추세`
- 롱은 `위쪽 bearish OB 5개 이상 쌓이면 금지`
- 숏은 `24시간 고점 유동성 스윕`이 나온 뒤 `12개 15분봉` 안에서만 허용
- 숏 수익은 `20%`까지 길게 끌고 감

즉 이 전략은:

- 롱은 무리한 자리 진입을 적극 차단하고
- 숏은 좋은 이벤트가 발생했을 때 강하게 먹는 구조

다.

더 자세한 내용은 별도 문서:

- [117_best_condition_trade_logic_ko.md](/c:/AppDev/Free_trader/117_best_condition_trade_logic_ko.md)

를 보면 된다.

## 현재 최종 포트폴리오를 문장으로 풀어 쓰면

현재 final best 포트폴리오는 이렇게 이해하면 된다.

1. 예전부터 살아남아 온 `case1`, `case2` 코어 슬리브는 유지한다.
2. 기존 85/116의 case3 대신, 더 강한 `117 best 계열` 전략을 case3로 교체한다.
3. case3를 예전처럼 7~9% 수준의 작은 보조 슬리브로 두지 않고, `24%`까지 크게 올린다.
4. 포트폴리오는 `1시간마다` 목표 비중으로 리밸런스한다.
5. 그 결과 전체 포트폴리오가 `132.2561% CAGR`과 `42.8382% MDD`를 달성한다.

## 연구 계보 요약

지금 current best가 어떤 흐름으로 왔는지 헷갈리지 않게, 최소한의 계보를 남긴다.

### Study 85

- case1 + case2 + 기존 case3를 합친 고성장 포트폴리오
- 대략 `120% CAGR` 구간을 형성
- 오랫동안 기준선 역할

### Study 116

- `115 스타일 case3`를 85 포트폴리오에 넣어보는 실험
- 결론: direct replacement로는 부족
- 기존 84/85 case3가 더 강했음

### Study 117

- 115의 핵심 아이디어를 살리되, 숏 엔진을 강화한 단일 전략 연구
- `145%+ CAGR`이 가능함을 확인
- case3 대체 후보로 가치가 생김

### Study 118

- 117 상위 전략들을 case3로 넣어 case1/case2/case3 포트폴리오 재구성
- 결론: 117 case3가 실제 포트폴리오에서도 먹힘
- best가 약 `129.52% CAGR`

### Study 119

- 118 winner 근처를 미세조정
- `case3 비중 확대 + 1시간 리밸런스`
- 최종적으로 `132.2561% CAGR / 42.8382% MDD / 3.0873 Calmar`

즉 최종 흐름은:

- `85의 포트폴리오 구조는 유지`
- `case3만 117 계열로 진화`
- `비중과 리밸런스까지 재최적화`

라고 보면 된다.

## 현재 포트폴리오의 핵심 해석

현재 최종 포트폴리오가 의미하는 것은 꽤 분명하다.

### 1. case1과 case2는 아직 교체 대상이 아니다

새로운 실험을 여러 번 했지만:

- case1은 여전히 가장 큰 비중
- case2도 계속 살아남음

즉 기존 코어 구조는 여전히 유효하다.

### 2. case3는 더 이상 작은 실험 sleeve가 아니다

예전에는:

- case3가 `5%~9%` 수준의 분산용 sleeve

에 가까웠다.

지금은:

- case3가 `24%`

로 올라왔다.

즉 현재 case3는:

- “있어도 되고 없어도 되는 보조 아이디어”

가 아니라

- `실질적으로 전체 포트폴리오를 끌어올리는 핵심 성장 sleeve`

가 되었다.

### 3. 남은 알파는 포트폴리오 구조에서도 나왔다

119의 중요한 메시지는:

- 좋은 case3를 넣는 것만으로 끝나지 않았고
- `1시간 리밸런스`가 추가 알파를 만들었다

는 점이다.

즉 지금 current best는 전략 알파와 포트폴리오 플러밍이 같이 만든 결과다.

## 현재 최종 포트폴리오 정의

실무적으로 가장 짧게 적으면 현재 정의는 아래다.

### 포트폴리오 이름

- `Study 119 current final portfolio`

### 슬리브 구성

- `case1 = Study 62 / variant shallow6_else2bull 의 equity_case1`
- `case2 = Study 62 를 통해 불러오는 기존 equity_case2`
- `case3 = Study 117 / variant lv3p0_g12_body25_tp20_lb5_none`

### 비중

- `case1 49%`
- `case2 27%`
- `case3 24%`

### 리밸런스

- `1시간`

### 공통 기간

- `2022-01-01 08:00:00` ~ `2026-02-12 00:00:00`

### 성과

- CAGR `132.2561%`
- MDD `42.8382%`
- Calmar `3.0873`

## 관련 파일 맵

현재 포트폴리오를 다시 추적할 때 가장 중요한 파일은 아래다.

- 현재 최종 포트폴리오 튜닝 결과:
  - [119_backtest_btcusdt_case123_portfolio_fine_tune_around_118.py](/c:/AppDev/Free_trader/119_backtest_btcusdt_case123_portfolio_fine_tune_around_118.py)
  - [119_backtest_btcusdt_case123_portfolio_fine_tune_around_118.md](/c:/AppDev/Free_trader/119_backtest_btcusdt_case123_portfolio_fine_tune_around_118.md)
- 117 기반 case3를 포트폴리오에 처음 넣어본 결과:
  - [118_backtest_btcusdt_case123_portfolio_with_117_case3.py](/c:/AppDev/Free_trader/118_backtest_btcusdt_case123_portfolio_with_117_case3.py)
  - [118_backtest_btcusdt_case123_portfolio_with_117_case3.md](/c:/AppDev/Free_trader/118_backtest_btcusdt_case123_portfolio_with_117_case3.md)
- 현재 case3 단일 전략 설명:
  - [117_best_condition_trade_logic_ko.md](/c:/AppDev/Free_trader/117_best_condition_trade_logic_ko.md)
  - [117_backtest_btcusdt_115_highcagr_push.md](/c:/AppDev/Free_trader/117_backtest_btcusdt_115_highcagr_push.md)
- case1/case2를 불러오는 포트폴리오 원형:
  - [74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.py](/c:/AppDev/Free_trader/74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.py)
  - [62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune.py](/c:/AppDev/Free_trader/62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune.py)

## 최종 메모

지금 시점의 가장 중요한 결론은 이거다.

- `85의 골격은 여전히 맞다`
- `case1, case2는 유지해도 된다`
- `case3는 117 계열로 교체하는 게 맞다`
- `case3는 이제 24% 수준의 큰 비중을 받을 자격이 있다`
- `1시간 리밸런스가 실제로 성과를 더 좋게 만들었다`

즉 현재 final best는:

- `기존 코어 2개 + 진화한 case3 1개`
- `대략 2:1:1`
- `1시간 리밸런스`

로 이해하면 가장 정확하다.
