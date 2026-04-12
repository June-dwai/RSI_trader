# 126 연구: case3 롱 품질 강화 실험

## 설정
- 공정 비교 구간: `2021-01-02 00:00:00` ~ `2026-03-15 05:30:00`
- 로컬 최신 캐시 종료 시각: `2026-03-15 05:19:00`
- 기준 엔진은 study117 best인 `3.0x / gate12 / body25 / TP20 / long_block_threshold=5`다.
- 숏 로직은 그대로 두고, 롱 진입 품질만 강화했다.
- 실험한 롱 필터는 네 가지다.
  1. 상단 bearish OB 허용 개수 축소
  2. bullish 추세가 몇 바 유지된 뒤에만 롱 허용
  3. red_avg 대비 과열 추격 롱 금지
  4. short_sweep 직후 일정 바 동안 롱 금지

## 기준선
- `baseline_case3_117`: CAGR `151.3261%`, MDD `64.5809%`, Calmar `2.3432`, 2026 수익률 `-10.6926%`, long entries `70`

## 승자
- 고CAGR 유지 + Calmar 우승: `lb4_delay8_capna_cd0` -> CAGR `167.9773%`, MDD `64.5809%`, Calmar `2.6010`, 2026 `-11.5764%`
- raw CAGR 우승: `lb4_delay8_capna_cd0` -> CAGR `167.9773%`, MDD `64.5809%`, Calmar `2.6010`
- 균형형 추천(기준선보다 CAGR도 높고 2026도 덜 나쁨): `lb4_delay8_cap2p5_cd0` -> CAGR `156.9846%`, MDD `64.5809%`, Calmar `2.4308`, 2026 `-7.3492%`
- 2026 방어형 우승(cagr>=140): `lb4_delay0_cap1p5_cd16` -> 2026 `-7.2855%`, 2026 MDD `31.5709%`, CAGR `142.3657%`

## 상위 15개

| Variant | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Long Entries | Short Entries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| lb4_delay8_capna_cd0 | 167.9773 | 64.5809 | 2.6010 | -11.5764 | 33.1473 | 67 | 53 |
| lb4_delay8_capna_cd8 | 167.9773 | 64.5809 | 2.6010 | -11.5764 | 33.1473 | 67 | 53 |
| lb4_delay8_capna_cd16 | 165.2804 | 64.5809 | 2.5593 | -11.7147 | 33.1578 | 67 | 53 |
| lb4_delay16_capna_cd0 | 161.8902 | 64.5809 | 2.5068 | -11.5906 | 32.7115 | 66 | 53 |
| lb4_delay16_capna_cd8 | 161.8902 | 64.5809 | 2.5068 | -11.5906 | 32.7115 | 66 | 53 |
| lb4_delay16_capna_cd16 | 161.8902 | 64.5809 | 2.5068 | -11.5906 | 32.7115 | 66 | 53 |
| lb4_delay4_capna_cd16 | 159.6571 | 64.5809 | 2.4722 | -11.6890 | 33.1376 | 69 | 53 |
| lb4_delay8_cap2p5_cd0 | 156.9846 | 64.5809 | 2.4308 | -7.3492 | 31.5938 | 68 | 53 |
| lb4_delay8_cap2p5_cd8 | 156.9846 | 64.5809 | 2.4308 | -7.3492 | 31.5938 | 68 | 53 |
| lb4_delay0_capna_cd16 | 156.5145 | 64.5809 | 2.4235 | -11.6890 | 33.1376 | 69 | 53 |
| lb4_delay16_cap2p5_cd0 | 156.0667 | 64.5809 | 2.4166 | -7.4906 | 31.7018 | 67 | 53 |
| lb4_delay16_cap2p5_cd8 | 156.0667 | 64.5809 | 2.4166 | -7.4906 | 31.7018 | 67 | 53 |
| lb4_delay16_cap2p5_cd16 | 156.0667 | 64.5809 | 2.4166 | -7.4906 | 31.7018 | 67 | 53 |
| lb4_delay0_cap2p5_cd16 | 155.8950 | 64.5809 | 2.4140 | -7.3222 | 31.5732 | 70 | 53 |
| lb4_delay4_capna_cd0 | 154.7333 | 64.5809 | 2.3960 | -10.0048 | 33.0117 | 70 | 53 |

## 해석
- baseline보다 좋아졌다면, 개선의 핵심은 숏을 더 잘한 게 아니라 저품질 롱을 얼마나 잘 잘라냈느냐에 있다.
- `long_entries`가 너무 급감하는데 CAGR도 꺾이면 필터가 너무 과한 것이다.
- 2026 손실 구간을 줄이려면 `상단 bearish OB 4개 근처 롱`과 `bullish 전환 직후 롱`을 특히 잘라내는 조합이 유력하다.

## 출력물
- Plot: `126_backtest_btcusdt_case3_long_quality_push.png`
- Metrics CSV: `126_backtest_btcusdt_case3_long_quality_push.csv`
- Curves CSV: `126_backtest_btcusdt_case3_long_quality_push_curves.csv`
- Report: `126_backtest_btcusdt_case3_long_quality_push.md`