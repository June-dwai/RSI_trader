# 87번 연구: 월 적립식 구조 비교

## 설정
- 모든 비교 대상이 완전히 같은 시장 구간을 보도록 공통 기간으로 잘라서 계산했다.
- 시작 시점: `2022-01-01 08:00:00`
- 종료 시점: `2026-03-15 05:19:00`
- 월 적립금: 매월 새로운 달의 첫 시점에 `1000` 달러를 추가한다.
- `case1/case2 only`는 70번 연구의 2-sleeve 목표 비중 `74/26`을 사용한다.
- `case1/case2/case3`는 현재 85번 연구 best 비중인 `62/31/7`을 사용한다.
- 현금 유입이 있으므로 비교 지표는 `TWR CAGR`, `TWR MDD`, `TWR Calmar`, `XIRR`를 중심으로 본다.

## 슬리브별 매매 로직

### Case1: `shallow6_else2bull`
- 기본 철학: 롱 위주의 눌림매수 엔진이고, 별도의 추세 헤지를 붙인 구조다. 대칭적인 롱/숏 전략은 아니다.
- 실행 단위: 1분봉.
- 진입 아이디어: 상위 타임프레임이 아직 bullish일 때 과매도 눌림을 롱으로 산다.
- 포지션 누적: 가격이 더 밀리면 `0.5%` 간격으로 물타기를 하고, `max_entries=4`에서 제한한다. 추가 진입 크기는 ADX 상태를 반영한다.
- 리스크 관리: 확정된 4시간 추세가 bearish로 바뀌면 기존 롱 inventory를 상대로 hedge short를 연다.
- 여기서 쓰는 62번 개선: 롱이 평균단가 대비 얕게 물려 있을 때는 가격이 평균단가의 `-6%` 안쪽으로 오면 hedge를 조기 해제하고, 깊게 물려 있으면 bullish 4시간봉이 두 번 확인될 때까지 hedge를 유지한다.
- 실전적으로는 이 슬리브가 가장 강한 수익 엔진이지만, 단독으로 돌리면 inventory drawdown이 크다.

### Case2: 42번 연구 dual-direction no-hedge 엔진
- 기본 철학: 양방향 mean-reversion이지만, case1처럼 별도의 hedge 계층은 없다.
- 실행 단위: 1분봉.
- 진입 아이디어: bullish 구간에서는 과매도 롱, bearish 구간에서는 과매수 숏을 잡는다.
- 포지션 처리: 최대 `max_entries=4`까지 누적 가능하다. 반대 신호가 나오면 기존 포지션을 `80%` 부분청산하고, 곧바로 반대 방향을 새로 연다.
- hedge 없음, hysteresis overlay 없음, case1 같은 보호 장치도 없다.
- 포트폴리오에서 이 슬리브의 가치는 단독 안정성보다, case1과 경로가 완전히 같지 않아서 분산과 리밸런싱 이득을 주는 데 있다.

### Case3: `short_gate_24h_g12_tp15`
- 기본 철학: 추세추종 슬리브인데, 숏 타이밍을 더 엄격하게 걸러서 보조 엔진으로 쓰는 구조다.
- 실행 단위: 1분봉을 15분봉으로 리샘플한 뒤 사용.
- 바이어스 엔진: 4시간 EMA200 hysteresis 확정 추세.
- 롱 측면: bullish regime이면 기본적으로 그대로 따라간다.
- 숏 측면: bearish라고 바로 숏하지 않는다. 먼저 직전 `24시간` 유동성 고점을 위로 쓸고 올라갔다가 다시 밀리는 rejection이 나와야 하고, 그 뒤 `12개 bar` 동안만 숏 진입을 허용한다.
- 청산 로직: 레버리지 `2배`, 손절 `6%`, 그리고 숏 전용 `+15%` 익절 lock을 쓴다. 숏이 목표 수익에 도달하면 익절하고, 이후 bullish flip이 나올 때까지 새 숏 재진입을 막는다.
- 이 슬리브는 비중을 작게 두는 게 전제다. 총수익의 핵심 엔진이 아니라, 하락 구간 타이밍 개선과 포트폴리오 완충 역할이 목적이다.

## 비교 시나리오 정의

### 1. `current_run_topup_only`
- 지금처럼 `case1`과 `case2`를 별도로 굴리면서 새 돈만 넣는 상황에 가장 가까운 가정이다.
- 초기 비중은 `74/26`이다.
- 매월 들어오는 새 `1000`달러도 같은 `74/26` 비율로 넣는다.
- 기존 자산을 팔지 않고, 정기 리밸런싱도 하지 않으며, 포트폴리오 차원의 리밸런싱 수수료도 없다.

### 2. `case12_rebal4h_topup`
- 같은 두 슬리브, 같은 초기 비중, 같은 월 적립금을 쓴다.
- 다만 각 슬리브의 손익으로 비중이 틀어질 때마다 전체 포트폴리오를 `4시간마다` 다시 `74/26`으로 맞춘다.
- 즉 전략 구성은 안 바꾸고, 포트폴리오 레벨 리밸런싱의 가치만 따로 분리해서 보는 케이스다.

### 3. `case123_rebal4h_topup`
- 여기에 `case3`를 추가해서 현재 best 3-sleeve 목표 비중 `62/31/7`을 사용한다.
- 월 적립금도 그 비중대로 바로 나눠 넣는다.
- 포트폴리오는 85번 연구와 같은 방식으로 `4시간마다` 수수료를 반영해 리밸런싱한다.
- 현재까지 비교한 월 적립식 구조 중에서는 이 케이스가 가장 강한 historical 결과를 보였다.

### 추가 실전 참고: `case12_cash_only_rebalance_topup`
- 기존 자산을 팔지 않고, 정기 리밸런싱도 하지 않는다.
- 대신 매월 들어오는 새 돈만 underweight 쪽에 더 넣어서 비중 틀어짐을 일부 복구한다.
- 즉 실제 운용에서 포지션을 직접 스왑하긴 부담스럽지만, 새 자금으로만 비중을 조절하고 싶을 때 가까운 형태다.

## 결과

| Variant | Final Equity | Contributed | Net Profit | Money Multiple | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| case123_rebal4h_topup | 351282.8201 | 52000.0000 | 299282.8201 | 6.7554 | 110.5383 | 46.7127 | 2.3663 | 104.2066 | 9203 | 1931.8540 |
| case12_rebal4h_topup | 324966.2336 | 52000.0000 | 272966.2336 | 6.2494 | 108.3790 | 49.1509 | 2.2050 | 99.1580 | 9198 | 1478.1161 |
| case12_cash_only_rebalance_topup | 295027.9000 | 52000.0000 | 243027.9000 | 5.6736 | 102.1449 | 49.6391 | 2.0578 | 93.0078 | 0 | 0.0000 |
| current_run_topup_only | 278347.5244 | 52000.0000 | 226347.5244 | 5.3528 | 99.2109 | 50.4063 | 1.9682 | 89.3647 | 0 | 0.0000 |

## 해석
- TWR/Calmar 기준 최고 구조는 `case123_rebal4h_topup`다.
- 투자자 체감 수익률에 가까운 XIRR 기준 최고 구조도 `case123_rebal4h_topup`다.
- `current_run_topup_only`는 지금처럼 슬리브를 따로 돌리고 새 돈만 넣는 형태의 기준선이다.
- `case12_rebal4h_topup`는 case3 없이도 리밸런싱만으로 얼마나 좋아지는지 보여준다.
- `case123_rebal4h_topup`는 월 적립식 자금 유입이 있어도 case3 diversifier가 여전히 유효한지 보여준다.
- `case12_cash_only_rebalance_topup`는 실전에서 기존 자산을 팔지 않고 새 돈으로만 비중을 조절할 때 어느 정도 개선이 가능한지 보는 참고선이다.

## 산출물
- 플롯: `87_backtest_btcusdt_scale06_adx002_monthly_topup_structure_compare.png`
- 성과 CSV: `87_backtest_btcusdt_scale06_adx002_monthly_topup_structure_compare.csv`
- 곡선 CSV: `87_backtest_btcusdt_scale06_adx002_monthly_topup_structure_compare_curves.csv`
- 적립금 CSV: `87_backtest_btcusdt_scale06_adx002_monthly_topup_structure_compare_topups.csv`
- 보고서: `87_backtest_btcusdt_scale06_adx002_monthly_topup_structure_compare.md`
