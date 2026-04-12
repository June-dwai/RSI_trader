# Study 108: Deep Gap Long with Leverage

## Setup
- Long only
- Entry when 15m close first crosses below `-20%` vs confirmed 4h EMA200
- No timeout. Exit only by TP, SL, liquidation, or final mark
- Position size = full equity * leverage
- Fees: `0.04%` on entry notional and `0.04%` on exit notional
- Intrabar order of events: liquidation first, then stop, then take-profit
- Whole-sample signal crosses at `-20%`: `46`

## Base Case
- Variant: `thr20_long_5x_tp10_sl10` = `5x`, `TP +10%`, `SL -10%`
- Final Equity `286.5654`, CAGR `-25.7353%`, MDD `95.1996%`, trades `11`, win rate `54.5455%`, avg trade `2.1114%`
- Avg / median / max hold: `229.0909h` / `128.0000h` / `878.5000h`
- Exit counts: TP `5`, Stop `5`, Liquidation `0`, Final `1`

## Best Variants
- Best final equity: `thr20_long_3x_tp15_sl15` -> equity `2170.5644`, CAGR `20.2616%`, MDD `83.4159%`
- Best Calmar: `thr20_long_2x_tp15_sl15` -> Calmar `0.2633`, equity `1966.0409`, trades `8`

## Leverage Ladder at TP10 / SL10
| Leverage | Final Equity | CAGR % | MDD % | Trades | Win Rate % | Liquidations |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1.0 | 994.7378 | -0.1255 | 37.7594 | 11 | 54.5455 | 0 |
| 2.0 | 889.3579 | -2.7529 | 63.1171 | 11 | 54.5455 | 0 |
| 3.0 | 707.3258 | -7.9128 | 79.4757 | 11 | 54.5455 | 0 |
| 5.0 | 286.5654 | -25.7353 | 95.1996 | 11 | 54.5455 | 0 |
| 7.0 | 42.8267 | -52.7659 | 99.4518 | 11 | 54.5455 | 0 |
| 10.0 | 0.0000 | -100.0000 | 100.0000 | 2 | 50.0000 | 1 |

## Top 10 by Final Equity
| Variant | Leverage | TP % | SL % | Final Equity | CAGR % | MDD % | Calmar | Trades | Win Rate % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| thr20_long_3x_tp15_sl15 | 3.0 | 15.0 | 15.0 | 2170.5644 | 20.2616 | 83.4159 | 0.2429 | 8 | 75.0000 |
| thr20_long_2x_tp15_sl15 | 2.0 | 15.0 | 15.0 | 1966.0409 | 17.4613 | 66.3053 | 0.2633 | 8 | 75.0000 |
| thr20_long_3x_tp12.5_sl15 | 3.0 | 12.5 | 15.0 | 1663.7286 | 12.8840 | 83.4159 | 0.1545 | 8 | 75.0000 |
| thr20_long_2x_tp12.5_sl15 | 2.0 | 12.5 | 15.0 | 1615.6436 | 12.0986 | 66.3053 | 0.1825 | 8 | 75.0000 |
| thr20_long_1x_tp15_sl15 | 1.0 | 15.0 | 15.0 | 1512.0518 | 10.3441 | 39.4712 | 0.2621 | 8 | 75.0000 |
| thr20_long_1x_tp12.5_sl15 | 1.0 | 12.5 | 15.0 | 1354.6381 | 7.4937 | 39.4712 | 0.1899 | 8 | 75.0000 |
| thr20_long_2x_tp15_sl10 | 2.0 | 15.0 | 10.0 | 1327.5606 | 6.9782 | 63.1171 | 0.1106 | 11 | 54.5455 |
| thr20_long_2x_tp10_sl15 | 2.0 | 10.0 | 15.0 | 1317.0879 | 6.7767 | 66.3053 | 0.1022 | 8 | 75.0000 |
| thr20_long_3x_tp10_sl15 | 3.0 | 10.0 | 15.0 | 1256.3284 | 5.5828 | 83.4159 | 0.0669 | 8 | 75.0000 |
| thr20_long_1x_tp15_sl10 | 1.0 | 15.0 | 10.0 | 1242.4209 | 5.3034 | 37.7594 | 0.1405 | 11 | 54.5455 |

## Caveat
- `-20%` is a very small sample. Most variants only trade around 8-13 times, so ranking stability is weak.
