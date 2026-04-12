# Study 110: Threshold Case Studies

## Setup
- Reused the 109 structure
- Long only
- Entry signal: gap threshold vs confirmed 4h EMA200 plus `RSI6 <= 15`
- DCA / cooldown / max 2.4 total size follow the same case2-style long-only rule as 109
- TP = `+1.2%`, SL = `-3.0%`, no re-entry logic
- Threshold cases: `-10%, -12%, -15%, -18%, -20%`

## Performance
| Variant | Threshold % | Final Equity | Total Return % | CAGR % | MDD % | Calmar | Trades | Win Rate % | Avg Entries | Avg Hold h | Signal Crosses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| buy_hold | N/A | 1548.4270 | 54.8427 | 10.9704 | 67.8001 | 0.1618 | 1 | 100.0000 | 1.0000 | 36797.3333 | N/A |
| gap_10 | 10.0 | 734.1219 | -26.5878 | -7.0940 | 50.8718 | -0.1394 | 386 | 83.4197 | 2.1010 | 7.0382 | 1785 |
| gap_12 | 12.0 | 1127.9070 | 12.7907 | 2.9069 | 35.1812 | 0.0826 | 313 | 84.3450 | 2.0256 | 5.5075 | 1208 |
| gap_15 | 15.0 | 1065.6908 | 6.5691 | 1.5262 | 36.1991 | 0.0422 | 208 | 84.6154 | 1.9615 | 4.2759 | 679 |
| gap_18 | 18.0 | 980.3383 | -1.9662 | -0.4716 | 30.2606 | -0.0156 | 125 | 82.4000 | 2.0080 | 3.6947 | 380 |
| gap_20 | 20.0 | 1096.8183 | 9.6818 | 2.2245 | 28.6925 | 0.0775 | 96 | 85.4167 | 1.9375 | 2.6955 | 238 |

## Best Cases
- Best final equity: `gap_12` (`-12%`) -> equity `1127.9070`, CAGR `2.9069%`, MDD `35.1812%`
- Best Calmar: `gap_12` (`-12%`) -> Calmar `0.0826`, equity `1127.9070`
- Buy-and-hold reference: equity `1548.4270`, CAGR `10.9704%`, MDD `67.8001%`

## Exit Breakdown
| Variant | Reason | Count |
| --- | --- | ---: |
| gap_10 | Stop Loss | 64 |
| gap_10 | Take Profit | 322 |
| gap_12 | Stop Loss | 49 |
| gap_12 | Take Profit | 264 |
| gap_15 | Stop Loss | 32 |
| gap_15 | Take Profit | 176 |
| gap_18 | Stop Loss | 22 |
| gap_18 | Take Profit | 103 |
| gap_20 | Stop Loss | 14 |
| gap_20 | Take Profit | 82 |
