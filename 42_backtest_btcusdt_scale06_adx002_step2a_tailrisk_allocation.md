# Step2-A: Joint Tail Risk 최소화 목적의 Allocation 정책 탐색 (Study42)

## 분석 설정
- 입력 곡선: `42_backtest_btcusdt_scale06_adx002_equity_combo_curves.csv`
- 상승후급락 이벤트: `42_backtest_btcusdt_scale06_adx002_structural_offset_step1_rise_crash_events.csv`
- 포트폴리오 수익률: `r_p(t) = w1(t)*r1(t) + (1-w1(t))*r2(t)`
- 워크포워드: 앞 70% train, 뒤 30% validation
- 정책군:
  - A) Static weight grid (`w1=0.00~1.00`, step 0.02)
  - B) Risk parity (`vol window=30/60/120`)
  - C) Regime dynamic (`dd1`, `vol ratio`, `hysteresis=EWM`, `quantized weights`) + `tc 5bps` 페널티 버전

## 우선순위 목적함수 반영
- 1순위/2순위 지표(`strategy tail joint`, `both-loss bar`)는 정의상 전략 수익률 기반이라 정책 간 값이 거의 동일합니다.
- 따라서 실질 순위는 동일 1/2순위 동률 하에서, `joint-tail 구간의 포트폴리오 손실 강도`와 `MDD`를 중심으로 갈립니다.
- CAGR 제약은 별도로 적용: `>=80%`, `>=100%` 두 버전 보고.

## Validation Top10 (CAGR >= 80%)
| policy_name | family | tc_bps | joint_p_q1 | joint_lift_q1 | joint_p_q5 | joint_lift_q5 | rise_crash_both_loss_ratio | rise_crash_event_joint_loss_freq | mdd_pct | cagr_pct | calmar | turnover_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_static_w1_0.00 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 55.505223 | 117.316053 | 2.113604 | 0.000000 |
| A_static_w1_0.02 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 55.361108 | 115.276922 | 2.082273 | 0.000000 |
| A_static_w1_0.04 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 55.244017 | 113.183807 | 2.048798 | 0.000000 |
| A_static_w1_0.06 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 55.140501 | 111.038664 | 2.013741 | 0.000000 |
| A_static_w1_0.08 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 55.038454 | 108.843481 | 1.977590 | 0.000000 |
| A_static_w1_0.10 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 54.937885 | 106.600280 | 1.940378 | 0.000000 |
| A_static_w1_0.12 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 54.838806 | 104.311108 | 1.902140 | 0.000000 |
| A_static_w1_0.14 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 54.741228 | 101.978037 | 1.862911 | 0.000000 |
| A_static_w1_0.16 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 54.645162 | 99.603161 | 1.822726 | 0.000000 |
| A_static_w1_0.18 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 54.550619 | 97.188592 | 1.781622 | 0.000000 |

- CAGR>=80% feasible 여부: `True`

## Validation Top10 (CAGR >= 100%)
| policy_name | family | tc_bps | joint_p_q1 | joint_lift_q1 | joint_p_q5 | joint_lift_q5 | rise_crash_both_loss_ratio | rise_crash_event_joint_loss_freq | mdd_pct | cagr_pct | calmar | turnover_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A_static_w1_0.00 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 55.505223 | 117.316053 | 2.113604 | 0.000000 |
| A_static_w1_0.02 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 55.361108 | 115.276922 | 2.082273 | 0.000000 |
| A_static_w1_0.04 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 55.244017 | 113.183807 | 2.048798 | 0.000000 |
| A_static_w1_0.06 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 55.140501 | 111.038664 | 2.013741 | 0.000000 |
| A_static_w1_0.08 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 55.038454 | 108.843481 | 1.977590 | 0.000000 |
| A_static_w1_0.10 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 54.937885 | 106.600280 | 1.940378 | 0.000000 |
| A_static_w1_0.12 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 54.838806 | 104.311108 | 1.902140 | 0.000000 |
| A_static_w1_0.14 | A_static | 0.000000 | 0.000996 | 86.505030 | 0.006697 | 22.058783 | 0.443232 | 0.965318 | 54.741228 | 101.978037 | 1.862911 | 0.000000 |

- CAGR>=100% feasible 여부: `True`

## Best 정책
- 선택 기준: `CAGR>=80%` 제약 하 우선순위 정렬 1위
- Best policy: `A_static_w1_0.00`
- Family: `A_static`, tc_bps=`0.000000`
- Validation CAGR: `117.316053%`
- Validation MDD: `55.505223%`
- Validation Calmar: `2.113604`
- Weight 시계열: `42_backtest_btcusdt_scale06_adx002_step2a_tailrisk_allocation_best_policy_weights.csv`

### 규칙 설명
- 고정 비중: `w1=0.00`, `w2=1.00`

## 다음 정책 제안 (Step2-B)
- 현재 정의(`w2=1-w1`, long-only)에서는 1/2순위 확률 지표가 정책에 거의 불변입니다.
- 따라서 다음 단계는 `cash/risk-off` 허용(예: `w1+w2<1`) 또는 `hedge(음수 가중)` 허용 정책을 추가해,
  동일한 tail joint 사건에서 포트폴리오 손실 자체를 줄이는 방향으로 확장하는 것을 권장합니다.
- 우선 시도안: `DD+Vol gating` 기반으로 `총 익스포저 cap`을 레짐별로 1.0/0.7/0.4로 조절.

## 산출물
- Dynamic train ranking: `42_backtest_btcusdt_scale06_adx002_step2a_tailrisk_allocation_dynamic_train.csv`
- Validation all policies: `42_backtest_btcusdt_scale06_adx002_step2a_tailrisk_allocation_all_policies_val.csv`
- Top10 (CAGR>=80): `42_backtest_btcusdt_scale06_adx002_step2a_tailrisk_allocation_top10_cagr80.csv`
- Top10 (CAGR>=100): `42_backtest_btcusdt_scale06_adx002_step2a_tailrisk_allocation_top10_cagr100.csv`
- Best weights: `42_backtest_btcusdt_scale06_adx002_step2a_tailrisk_allocation_best_policy_weights.csv`
- Report: `42_backtest_btcusdt_scale06_adx002_step2a_tailrisk_allocation.md`