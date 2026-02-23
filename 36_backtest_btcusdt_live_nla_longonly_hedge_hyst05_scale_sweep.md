# 36 Backtest: Entry Scale Sweep (0.60 / 0.70) on Study-35 Core

## Setup
- Base engine: study-35 (`long-only + trend short hedge`, 4h hysteresis band 0.5%).
- Symbol: `BTCUSDT`
- Initial capital: `1000`
- Entry scales tested: `0.60, 0.70`
- No-lookahead guard: same as study-35.

## Results
| Entry Scale | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Hedge Open/Close |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.60 | 7495.0711 | 649.5071 | 63.2015 | 59.3620 | 1.0647 | 430 | 364/66 | 88.3721 | 1.9936 | 66/66 |
| 0.70 | 8935.3779 | 793.5378 | 70.3286 | 69.1576 | 1.0169 | 430 | 364/66 | 88.3721 | 1.9465 | 66/66 |

## Best Cases
- Best CAGR: `scale=0.70` (70.3286%).
- Lowest MDD: `scale=0.60` (59.3620%).
- Best Calmar: `scale=0.60` (1.0647).

## Delta vs Study-35 (Scale 0.50)
| Entry Scale | Final Equity Delta | CAGR Delta (pp) | MDD Delta (pp) | Calmar Delta |
|---:|---:|---:|---:|---:|
| 0.60 | 1510.9277 | 8.6946 | 9.8234 | -0.0356 |
| 0.70 | 2951.2346 | 15.8217 | 19.6190 | -0.0834 |

## Outputs
- Plot: `36_backtest_btcusdt_live_nla_longonly_hedge_hyst05_scale_sweep.png`
- Metrics CSV: `36_backtest_btcusdt_live_nla_longonly_hedge_hyst05_scale_sweep.csv`
- Report: `36_backtest_btcusdt_live_nla_longonly_hedge_hyst05_scale_sweep.md`