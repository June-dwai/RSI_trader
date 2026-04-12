# Study 107: Counter-EMA Gap Reversal

## Setup
- Symbol: `BTCUSDT`
- Sample: `2022-01-01 00:00:00` to `2026-03-15 05:30:00`
- Working bars: `15min` built from cached 1m data
- EMA anchor: confirmed 4h EMA200 (`ewm(span=200).mean().shift(1)`) mapped into the current 15m bar
- Entry event: first 15m close that crosses below `-threshold%` for long, or above `+threshold%` for short
- Exit sweep: fixed TP/SL, `24h` and `48h` max hold, round-trip fee `0.08%`, and conservative stop-first handling if TP and SL are both touched inside one 15m bar
- Important: this is an independent event study, not a flat-only sequential portfolio backtest

## Whole-Period Gap Distribution
- Bars analyzed: `147192`
- Time below / above EMA200: `50.60%` / `49.40%`
- Signed gap quantiles (5 / 25 / 50 / 75 / 95): `-12.6342%`, `-4.0776%`, `-0.1179%`, `5.3304%`, `13.8879%`

| Threshold % | Below Coverage % | Above Coverage % | Inside Band % |
| ---: | ---: | ---: | ---: |
| 1.0 | 45.21 | 44.57 | 10.22 |
| 2.0 | 38.37 | 39.17 | 22.46 |
| 3.0 | 31.27 | 34.03 | 34.70 |
| 4.0 | 25.39 | 29.98 | 44.64 |
| 5.0 | 21.60 | 26.28 | 52.12 |
| 6.0 | 18.18 | 22.49 | 59.33 |
| 8.0 | 12.23 | 15.44 | 72.34 |
| 10.0 | 8.81 | 10.31 | 80.88 |
| 12.0 | 5.78 | 6.87 | 87.35 |
| 15.0 | 3.23 | 4.26 | 92.51 |

## 48h Reversion Path Stats
| Side | Threshold % | Events | Median Entry Gap % | Half-Reclaim Hit % | EMA Touch % | Median MFE % | Median Adverse % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| long | 4.0 | 610 | 4.13 | 53.4 | 14.9 | 2.30 | 1.97 |
| long | 6.0 | 393 | 6.14 | 40.5 | 10.9 | 2.43 | 2.41 |
| long | 8.0 | 282 | 8.13 | 30.1 | 4.6 | 3.27 | 2.53 |
| long | 10.0 | 205 | 10.16 | 27.8 | 4.4 | 2.91 | 2.81 |
| long | 12.0 | 239 | 12.14 | 17.2 | 2.1 | 2.74 | 2.83 |
| long | 15.0 | 89 | 15.24 | 5.6 | 0.0 | 3.77 | 3.33 |
| short | 4.0 | 460 | 4.12 | 53.9 | 22.6 | 2.28 | 2.16 |
| short | 6.0 | 453 | 6.12 | 41.1 | 12.1 | 2.36 | 1.92 |
| short | 8.0 | 497 | 8.12 | 24.3 | 5.0 | 2.04 | 2.06 |
| short | 10.0 | 237 | 10.15 | 20.7 | 3.4 | 2.52 | 1.81 |
| short | 12.0 | 201 | 12.15 | 9.5 | 0.5 | 2.25 | 1.91 |
| short | 15.0 | 85 | 15.14 | 9.4 | 0.0 | 1.22 | 2.78 |

## Best TP/SL per Threshold
| Side | Hold h | Threshold % | TP % | SL % | Events | Expectancy % | Win Rate % | Profit Factor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| long | 24 | 4.0 | 3.0 | 8.0 | 610 | 0.200 | 61.0 | 1.229 |
| long | 24 | 6.0 | 4.0 | 8.0 | 393 | 0.121 | 51.9 | 1.111 |
| long | 24 | 8.0 | 3.0 | 6.0 | 282 | 0.493 | 62.4 | 1.558 |
| long | 24 | 10.0 | 6.0 | 4.0 | 205 | 0.263 | 51.7 | 1.224 |
| long | 24 | 12.0 | 2.0 | 8.0 | 239 | 0.389 | 68.6 | 1.495 |
| long | 24 | 15.0 | 5.0 | 1.0 | 89 | 0.279 | 27.0 | 1.354 |
| long | 48 | 4.0 | 3.0 | 2.0 | 610 | 0.024 | 48.2 | 1.024 |
| long | 48 | 6.0 | 4.0 | 8.0 | 393 | 0.231 | 56.2 | 1.173 |
| long | 48 | 8.0 | 2.0 | 6.0 | 282 | 0.618 | 77.3 | 1.809 |
| long | 48 | 10.0 | 5.0 | 4.0 | 205 | 0.211 | 49.8 | 1.133 |
| long | 48 | 12.0 | 6.0 | 8.0 | 239 | 0.657 | 58.6 | 1.478 |
| long | 48 | 15.0 | 5.0 | 1.0 | 89 | 0.324 | 24.7 | 1.398 |
| short | 24 | 4.0 | 6.0 | 1.5 | 460 | 0.106 | 43.0 | 1.131 |
| short | 24 | 6.0 | 6.0 | 8.0 | 453 | 0.131 | 53.0 | 1.142 |
| short | 24 | 8.0 | 1.0 | 3.0 | 497 | 0.042 | 69.6 | 1.075 |
| short | 24 | 10.0 | 4.0 | 4.0 | 237 | 0.277 | 55.7 | 1.353 |
| short | 24 | 12.0 | 2.0 | 8.0 | 201 | 0.084 | 59.2 | 1.114 |
| short | 24 | 15.0 | 6.0 | 1.5 | 85 | -0.269 | 35.3 | 0.728 |
| short | 48 | 4.0 | 6.0 | 1.5 | 460 | 0.114 | 35.4 | 1.116 |
| short | 48 | 6.0 | 6.0 | 8.0 | 453 | 0.555 | 53.9 | 1.571 |
| short | 48 | 8.0 | 1.0 | 3.0 | 497 | -0.009 | 72.6 | 0.986 |
| short | 48 | 10.0 | 2.0 | 1.5 | 237 | 0.283 | 54.0 | 1.405 |
| short | 48 | 12.0 | 3.0 | 5.0 | 201 | 0.176 | 55.2 | 1.159 |
| short | 48 | 15.0 | 5.0 | 1.0 | 85 | -0.243 | 21.2 | 0.711 |

## Recommendation
- Long candidate: below `-8.0%` with `48h` hold, `TP 2.0%` / `SL 6.0%`. Expectancy `0.618%`, win rate `77.3%`, events `282`.
- Short candidate: above `+10.0%` with `48h` hold, `TP 2.0%` / `SL 1.5%`. Expectancy `0.283%`, win rate `54.0%`, events `237`.
- EMA-touch take profit is too ambitious for this setup. Even after 48h, full EMA touch stays rare once the entry gap is deep.
- Practical implication: treat this as a short-horizon snapback study. Fixed TP works better than waiting for full reversion to EMA200.
