# 95번 연구: 조건부 인트라데이 구조

## 설정
- BTC 15분봉 기반으로만 운용한다.
- 4시간 confirmed trend를 상위 필터로 사용한다.
- breakout은 추세 방향 돌파를 따라가고, reclaim은 유동성 sweep 후 range 복귀를 역추세로 먹는다.
- 진입/청산은 모두 bar close 기준으로 처리해 미래시를 피한다.

## 결과

| Variant | Entry Type | Final Equity | CAGR % | MDD % | Calmar | Trades | Fee Paid |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| reclaim24_dual_h12_x100 | reclaim | 545.5130 | -13.4467 | 49.3114 | -0.2727 | 1364 | 409.7017 |
| breakout48_dual_h12_x100 | breakout | 527.1406 | -14.1590 | 48.7504 | -0.2904 | 1704 | 473.3201 |
| breakout24_dual_h8_x100 | breakout | 380.6115 | -20.5611 | 64.2829 | -0.3199 | 2484 | 609.6524 |
| reclaim12_dual_h8_x100 | reclaim | 341.3086 | -22.5912 | 67.4987 | -0.3347 | 2370 | 610.0104 |
| breakout24_dual_h8_x125 | breakout | 292.4309 | -25.3965 | 72.9781 | -0.3480 | 2484 | 674.0747 |

## 해석
- best variant: `reclaim24_dual_h12_x100`
- 이 구조는 저빈도 포트폴리오 sleeve와 다른 짧은 holding-period 알파 후보를 찾는 목적이다.

## 산출물
- 플롯: `95_backtest_conditional_intraday_structures.png`
- 성과 CSV: `95_backtest_conditional_intraday_structures.csv`
- 곡선 CSV: `95_backtest_conditional_intraday_structures_curves.csv`
- 보고서: `95_backtest_conditional_intraday_structures.md`