# Study 107 Equity Check

## Setup
- Sequential, flat-only backtest on 15m bars
- Uses the recommended 107 study thresholds directly
- Entry only on threshold cross bar close
- Exit via TP / SL / 48h timeout with conservative stop-first handling inside the bar
- No same-bar re-entry after an exit

## Performance
| Variant | Final Equity | Total Return % | CAGR % | MDD % | Calmar | Trades | Win Rate % | Avg Trade % | Avg Hold h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| buy_hold | 1548.4270 | 54.8427 | 10.9703 | 67.5771 | 0.1623 | 1 | 100.0000 | 54.8427 | 36797.7500 |
| dual_best | 1201.9041 | 20.1904 | 4.4755 | 27.6859 | 0.1617 | 179 | 59.2179 | 0.1306 | 15.8240 |
| long_only_best | 1288.6557 | 28.8656 | 6.2234 | 16.3112 | 0.3815 | 90 | 74.4444 | 0.3227 | 20.8306 |
| short_only_best | 932.6806 | -6.7319 | -1.6455 | 25.5046 | -0.0645 | 89 | 43.8202 | -0.0638 | 10.7612 |

## Readout
- Dual curve: final equity `1201.9041`, CAGR `4.4755%`, MDD `27.6859%`, win rate `59.2179%`.
- Long-only drives most of the edge: final equity `1288.6557`, vs short-only `932.6806`.
- Buy-and-hold benchmark over the same sample finishes at `1548.4270`.

## Exit Breakdown
| Variant | Exit Reason | Count |
| --- | --- | ---: |
| buy_hold | final | 1 |
| dual_best | stop | 61 |
| dual_best | time | 19 |
| dual_best | tp | 99 |
| long_only_best | stop | 12 |
| long_only_best | time | 16 |
| long_only_best | tp | 62 |
| short_only_best | stop | 49 |
| short_only_best | time | 3 |
| short_only_best | tp | 37 |
