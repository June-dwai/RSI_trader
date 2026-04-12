# Study 109: -20% Gap + RSI15 Case2-Style Long Only

## Setup
- Long only
- Entry signal: confirmed 4h EMA200 gap `<= -20%` and `RSI6 <= 15` on the 1m close
- DCA timing: same case2 rhythm using cooldown and `recent_trade * 0.995` trigger
- Entry sizing: `0.6` each, max `2.4` total (`4` entries)
- Take profit: case2 default `+1.2%` from average entry
- Stop loss: `-3.0%` from average entry, full close, no re-entry logic

## Performance
| Variant | Final Equity | Total Return % | CAGR % | MDD % | Calmar | Trades | Win Rate % | Avg Trade % | Avg Entries | Avg Hold h |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| buy_hold | 1548.4270 | 54.8427 | 10.9704 | 67.8001 | 0.1618 | 1 | 100.0000 | 54.8427 | 1.0000 | 36797.3333 |
| minus20_rsi15_case2_longonly_noreentry | 1096.8183 | 9.6818 | 2.2245 | 28.6925 | 0.0775 | 96 | 85.4167 | 0.1500 | 1.9375 | 2.6955 |

## Readout
- Strategy signals: `238` crosses, `563` total signal bars.
- Strategy exits: TP `82`, Stop `14`, Final `0`.
- Strategy final equity `1096.8183` vs buy-and-hold `1548.4270`.

## Exit Breakdown
| Variant | Reason | Count |
| --- | --- | ---: |
| buy_hold | Final Close | 1 |
| minus20_rsi15_case2_longonly_noreentry | Stop Loss | 14 |
| minus20_rsi15_case2_longonly_noreentry | Take Profit | 82 |
