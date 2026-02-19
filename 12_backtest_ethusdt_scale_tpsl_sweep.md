# 12 ETHUSDT Scale + TP/SL Case Study

## 1) Objective
- Explore ETH tuning sensitivity for `entry_scale`, `TP`, and `SL` only.
- Keep hedge method fixed to `04 trend short hedge 5x` with 4h confirmed trend.
- Keep hysteresis fixed at `0.00%` to isolate parameter effects.

## 2) Sweep Grid
- Symbol: `ETHUSDT`
- Data period: `2022-01-01` to `2026-02-12`
- Confirmation policy: closed 4h state only (`shift(1)`, no look-ahead)
- Scale values: `0.30, 0.40`
- TP values (%): `0.60, 0.80`
- SL values (%): `4.00, 5.00, 6.00, 8.00`
- Total cases: `16`

## 3) Best Summary
- Best Final Equity: `s0.40_tp0.80_sl4.00` (`9785.9656 USDT`).
- Best Calmar: `s0.40_tp0.80_sl4.00` (`1.4332`).
- Lowest MDD: `s0.30_tp0.80_sl8.00` (`37.9097%`).

## 4) Top 4 Cases (Plotted)

| Rank | Case | Scale | TP % | SL % | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Win Rate % |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `s0.40_tp0.80_sl4.00` | 0.40 | 0.8000 | 4.0000 | 9785.9656 | 878.5966 | 74.1369 | 51.7268 | 1.4332 | 656 | 86.2805 |
| 2 | `s0.30_tp0.80_sl4.00` | 0.30 | 0.8000 | 4.0000 | 5906.5183 | 490.6518 | 54.0172 | 39.4287 | 1.3700 | 656 | 86.2805 |
| 3 | `s0.40_tp0.60_sl4.00` | 0.40 | 0.6000 | 4.0000 | 4877.2119 | 387.7212 | 47.0099 | 51.0602 | 0.9207 | 636 | 85.8491 |
| 4 | `s0.40_tp0.80_sl8.00` | 0.40 | 0.8000 | 8.0000 | 4853.4160 | 385.3416 | 46.8352 | 50.5419 | 0.9267 | 571 | 84.2382 |

## 5) Full Ranking Table (All Cases)

| Rank | Case | Scale | TP % | SL % | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Worst Month |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `s0.40_tp0.80_sl4.00` | 0.40 | 0.8000 | 4.0000 | 9785.9656 | 878.5966 | 74.1369 | 51.7268 | 1.4332 | 656 | 541/115 | 86.2805 | 2.7678 | `2025-01 (-32.4929%)` |
| 2 | `s0.30_tp0.80_sl4.00` | 0.30 | 0.8000 | 4.0000 | 5906.5183 | 490.6518 | 54.0172 | 39.4287 | 1.3700 | 656 | 541/115 | 86.2805 | 2.9219 | `2022-04 (-23.5265%)` |
| 3 | `s0.40_tp0.60_sl4.00` | 0.40 | 0.6000 | 4.0000 | 4877.2119 | 387.7212 | 47.0099 | 51.0602 | 0.9207 | 636 | 521/115 | 85.8491 | 2.3937 | `2022-04 (-35.3902%)` |
| 4 | `s0.40_tp0.80_sl8.00` | 0.40 | 0.8000 | 8.0000 | 4853.4160 | 385.3416 | 46.8352 | 50.5419 | 0.9267 | 571 | 456/115 | 84.2382 | 2.8399 | `2025-06 (-31.5316%)` |
| 5 | `s0.40_tp0.80_sl6.00` | 0.40 | 0.8000 | 6.0000 | 4084.9994 | 308.4999 | 40.8079 | 53.8955 | 0.7572 | 463 | 348/115 | 80.5616 | 2.5270 | `2022-04 (-36.0841%)` |
| 6 | `s0.40_tp0.60_sl6.00` | 0.40 | 0.6000 | 6.0000 | 3947.0724 | 294.7072 | 39.6367 | 55.9829 | 0.7080 | 815 | 700/115 | 88.9571 | 2.7916 | `2024-06 (-32.2785%)` |
| 7 | `s0.30_tp0.80_sl8.00` | 0.30 | 0.8000 | 8.0000 | 3521.3114 | 252.1311 | 35.8142 | 37.9097 | 0.9447 | 571 | 456/115 | 84.2382 | 2.8502 | `2025-06 (-24.0476%)` |
| 8 | `s0.30_tp0.60_sl4.00` | 0.30 | 0.6000 | 4.0000 | 3423.6097 | 242.3610 | 34.8881 | 39.2322 | 0.8893 | 636 | 521/115 | 85.8491 | 2.4395 | `2022-04 (-26.3463%)` |
| 9 | `s0.40_tp0.60_sl8.00` | 0.40 | 0.6000 | 8.0000 | 3062.5280 | 206.2528 | 31.2813 | 56.6246 | 0.5524 | 766 | 651/115 | 88.2507 | 2.7982 | `2025-01 (-38.0653%)` |
| 10 | `s0.30_tp0.60_sl6.00` | 0.30 | 0.6000 | 6.0000 | 3056.1673 | 205.6167 | 31.2149 | 43.6777 | 0.7147 | 815 | 700/115 | 88.9571 | 2.8130 | `2024-06 (-23.8460%)` |
| 11 | `s0.30_tp0.80_sl6.00` | 0.30 | 0.8000 | 6.0000 | 3006.0439 | 200.6044 | 30.6884 | 41.5945 | 0.7378 | 463 | 348/115 | 80.5616 | 2.5606 | `2022-04 (-26.8312%)` |
| 12 | `s0.40_tp0.80_sl5.00` | 0.40 | 0.8000 | 5.0000 | 2818.7600 | 181.8760 | 28.6599 | 52.2746 | 0.5483 | 466 | 351/115 | 80.6867 | 2.1732 | `2022-04 (-32.7816%)` |
| 13 | `s0.40_tp0.60_sl5.00` | 0.40 | 0.6000 | 5.0000 | 2621.8562 | 162.1856 | 26.4141 | 53.8490 | 0.4905 | 592 | 477/115 | 84.7973 | 2.1244 | `2025-01 (-31.7227%)` |
| 14 | `s0.30_tp0.60_sl8.00` | 0.30 | 0.6000 | 8.0000 | 2510.7433 | 151.0743 | 25.0899 | 44.3005 | 0.5664 | 766 | 651/115 | 88.2507 | 2.7949 | `2025-01 (-29.5277%)` |
| 15 | `s0.30_tp0.80_sl5.00` | 0.30 | 0.8000 | 5.0000 | 2295.8913 | 129.5891 | 22.3981 | 40.4970 | 0.5531 | 466 | 351/115 | 80.6867 | 2.2189 | `2022-04 (-24.2162%)` |
| 16 | `s0.30_tp0.60_sl5.00` | 0.30 | 0.6000 | 5.0000 | 2173.3050 | 117.3305 | 20.7757 | 41.9334 | 0.4954 | 592 | 477/115 | 84.7973 | 2.1658 | `2025-01 (-22.6507%)` |

## 6) Detailed Per-Case Notes (All Cases)

### Rank 1 - `s0.40_tp0.80_sl4.00`
- Params: scale `0.40`, TP `0.8000%`, SL `4.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `9785.9656 USDT`
- Total Return / CAGR: `878.5966%` / `74.1369%`
- MDD: `51.7268%` (`4515.1792 USDT`), Calmar `1.4332`
- Vol/Sharpe/Sortino: `67.5260%` / `1.1515` / `1.4868`
- Trades: `656` (Long `541`, Short `115`), Win `86.2805%`, PF `2.7678`
- Avg/Median trade PnL: `36.5422` / `15.3183`, Avg/Median hold: `75.1659h` / `4.0000h`
- Worst Month: `2025-01 (-32.4929%)`, DD episode: peak `2022-03-13 23:01:00` -> trough `2023-01-06 13:29:00` -> recovery `2024-01-11 11:53:00`, depth `51.7268%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-8578.9566, pnl_avg=-8578.9566
- `LONG` / `Take Profit`: trades=540, pnl_sum=17537.4449, pnl_avg=32.4767
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=7114.9194, pnl_avg=62.4116
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=7898.2713, pnl_avg=7898.2713

### Rank 2 - `s0.30_tp0.80_sl4.00`
- Params: scale `0.30`, TP `0.8000%`, SL `4.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `5906.5183 USDT`
- Total Return / CAGR: `490.6518%` / `54.0172%`
- MDD: `39.4287%` (`2054.7175 USDT`), Calmar `1.3700`
- Vol/Sharpe/Sortino: `48.4951%` / `1.1298` / `1.4166`
- Trades: `656` (Long `541`, Short `115`), Win `86.2805%`, PF `2.9219`
- Avg/Median trade PnL: `19.2356` / `9.2015`, Avg/Median hold: `75.1659h` / `4.0000h`
- Worst Month: `2022-04 (-23.5265%)`, DD episode: peak `2022-03-13 23:01:00` -> trough `2023-01-06 13:29:00` -> recovery `2024-01-11 11:54:00`, depth `39.4287%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-3738.5643, pnl_avg=-3738.5643
- `LONG` / `Take Profit`: trades=540, pnl_sum=9180.9938, pnl_avg=17.0018
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=3441.9331, pnl_avg=3441.9331
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=3734.1900, pnl_avg=32.7561

### Rank 3 - `s0.40_tp0.60_sl4.00`
- Params: scale `0.40`, TP `0.6000%`, SL `4.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `4877.2119 USDT`
- Total Return / CAGR: `387.7212%` / `47.0099%`
- MDD: `51.0602%` (`1583.3689 USDT`), Calmar `0.9207`
- Vol/Sharpe/Sortino: `66.0597%` / `0.9065` / `1.1270`
- Trades: `636` (Long `521`, Short `115`), Win `85.8491%`, PF `2.3937`
- Avg/Median trade PnL: `18.3584` / `9.7264`, Avg/Median hold: `81.8193h` / `2.8000h`
- Worst Month: `2022-04 (-35.3902%)`, DD episode: peak `2022-02-24 07:34:00` -> trough `2023-01-06 13:29:00` -> recovery `2024-01-11 10:42:00`, depth `51.0602%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-4499.7073, pnl_avg=-4499.7073
- `LONG` / `Take Profit`: trades=520, pnl_sum=8243.7954, pnl_avg=15.8535
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=2863.1375, pnl_avg=2863.1375
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=5068.7076, pnl_avg=44.4623

### Rank 4 - `s0.40_tp0.80_sl8.00`
- Params: scale `0.40`, TP `0.8000%`, SL `8.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `4853.4160 USDT`
- Total Return / CAGR: `385.3416%` / `46.8352%`
- MDD: `50.5419%` (`2534.4286 USDT`), Calmar `0.9267`
- Vol/Sharpe/Sortino: `76.4097%` / `0.8694` / `1.1507`
- Trades: `571` (Long `456`, Short `115`), Win `84.2382%`, PF `2.8399`
- Avg/Median trade PnL: `24.3077` / `14.3419`, Avg/Median hold: `88.3839h` / `4.0000h`
- Worst Month: `2025-06 (-31.5316%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-05-20 13:39:00` -> recovery `2024-11-23 13:56:00`, depth `50.5419%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-3491.2272, pnl_avg=-3491.2272
- `LONG` / `Take Profit`: trades=455, pnl_sum=11267.9705, pnl_avg=24.7648
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=2587.2568, pnl_avg=2587.2568
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=3515.7134, pnl_avg=30.8396

### Rank 5 - `s0.40_tp0.80_sl6.00`
- Params: scale `0.40`, TP `0.8000%`, SL `6.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `4084.9994 USDT`
- Total Return / CAGR: `308.4999%` / `40.8079%`
- MDD: `53.8955%` (`1313.4920 USDT`), Calmar `0.7572`
- Vol/Sharpe/Sortino: `68.2346%` / `0.8350` / `1.0528`
- Trades: `463` (Long `348`, Short `115`), Win `80.5616%`, PF `2.5270`
- Avg/Median trade PnL: `20.3181` / `10.1986`, Avg/Median hold: `113.7088h` / `4.2833h`
- Worst Month: `2022-04 (-36.0841%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-11-06 05:03:00` -> recovery `2024-12-05 14:29:00`, depth `53.8955%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-3053.6650, pnl_avg=-3053.6650
- `LONG` / `Take Profit`: trades=347, pnl_sum=6310.7673, pnl_avg=18.1866
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=2201.3447, pnl_avg=2201.3447
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=3948.8143, pnl_avg=34.6387

### Rank 6 - `s0.40_tp0.60_sl6.00`
- Params: scale `0.40`, TP `0.6000%`, SL `6.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `3947.0724 USDT`
- Total Return / CAGR: `294.7072%` / `39.6367%`
- MDD: `55.9829%` (`1482.0766 USDT`), Calmar `0.7080`
- Vol/Sharpe/Sortino: `68.0242%` / `0.8283` / `1.0167`
- Trades: `815` (Long `700`, Short `115`), Win `88.9571%`, PF `2.7916`
- Avg/Median trade PnL: `15.8644` / `9.2134`, Avg/Median hold: `60.7270h` / `2.4500h`
- Worst Month: `2024-06 (-32.2785%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-11-06 05:03:00` -> recovery `2024-12-06 14:27:00`, depth `55.9829%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-3314.6700, pnl_avg=-3314.6700
- `LONG` / `Take Profit`: trades=699, pnl_sum=11005.5301, pnl_avg=15.7447
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=2249.9647, pnl_avg=2249.9647
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=2988.6345, pnl_avg=26.2161

### Rank 7 - `s0.30_tp0.80_sl8.00`
- Params: scale `0.30`, TP `0.8000%`, SL `8.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `3521.3114 USDT`
- Total Return / CAGR: `252.1311%` / `35.8142%`
- MDD: `37.9097%` (`1367.3631 USDT`), Calmar `0.9447`
- Vol/Sharpe/Sortino: `54.2392%` / `0.8296` / `1.0648`
- Trades: `571` (Long `456`, Short `115`), Win `84.2382%`, PF `2.8502`
- Avg/Median trade PnL: `14.4197` / `8.0440`, Avg/Median hold: `88.3839h` / `4.0000h`
- Worst Month: `2025-06 (-24.0476%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-05-20 13:39:00` -> recovery `2024-11-12 09:01:00`, depth `37.9097%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-1922.7038, pnl_avg=-1922.7038
- `LONG` / `Take Profit`: trades=455, pnl_sum=6479.6192, pnl_avg=14.2409
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1424.8652, pnl_avg=1424.8652
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=2251.8935, pnl_avg=19.7535

### Rank 8 - `s0.30_tp0.60_sl4.00`
- Params: scale `0.30`, TP `0.6000%`, SL `4.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `3423.6097 USDT`
- Total Return / CAGR: `242.3610%` / `34.8881%`
- MDD: `39.2322%` (`897.8786 USDT`), Calmar `0.8893`
- Vol/Sharpe/Sortino: `46.9992%` / `0.8686` / `1.0492`
- Trades: `636` (Long `521`, Short `115`), Win `85.8491%`, PF `2.4395`
- Avg/Median trade PnL: `10.6618` / `5.4841`, Avg/Median hold: `81.8193h` / `2.8000h`
- Worst Month: `2022-04 (-26.3463%)`, DD episode: peak `2022-02-24 07:34:00` -> trough `2023-01-06 13:29:00` -> recovery `2024-01-11 11:44:00`, depth `39.2322%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-2338.6297, pnl_avg=-2338.6297
- `LONG` / `Take Profit`: trades=520, pnl_sum=4709.5641, pnl_avg=9.0569
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1488.0564, pnl_avg=1488.0564
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=2921.9301, pnl_avg=25.6310

### Rank 9 - `s0.40_tp0.60_sl8.00`
- Params: scale `0.40`, TP `0.6000%`, SL `8.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `3062.5280 USDT`
- Total Return / CAGR: `206.2528%` / `31.2813%`
- MDD: `56.6246%` (`1988.7417 USDT`), Calmar `0.5524`
- Vol/Sharpe/Sortino: `70.8136%` / `0.7356` / `0.9231`
- Trades: `766` (Long `651`, Short `115`), Win `88.2507%`, PF `2.7982`
- Avg/Median trade PnL: `13.8551` / `7.5965`, Avg/Median hold: `64.4575h` / `2.5333h`
- Worst Month: `2025-01 (-38.0653%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-11-06 05:03:00` -> recovery `2024-12-06 14:27:00`, depth `56.6246%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-2410.8133, pnl_avg=-2410.8133
- `LONG` / `Take Profit`: trades=650, pnl_sum=8539.4551, pnl_avg=13.1376
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1718.1748, pnl_avg=1718.1748
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=2766.1844, pnl_avg=24.2648

### Rank 10 - `s0.30_tp0.60_sl6.00`
- Params: scale `0.30`, TP `0.6000%`, SL `6.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `3056.1673 USDT`
- Total Return / CAGR: `205.6167%` / `31.2149%`
- MDD: `43.6777%` (`854.4489 USDT`), Calmar `0.7147`
- Vol/Sharpe/Sortino: `49.1535%` / `0.7970` / `0.9618`
- Trades: `815` (Long `700`, Short `115`), Win `88.9571%`, PF `2.8130`
- Avg/Median trade PnL: `9.7770` / `5.3513`, Avg/Median hold: `60.7270h` / `2.4500h`
- Worst Month: `2024-06 (-23.8460%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-11-06 05:03:00` -> recovery `2024-12-06 01:27:00`, depth `43.6777%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-1914.6355, pnl_avg=-1914.6355
- `LONG` / `Take Profit`: trades=699, pnl_sum=6570.4868, pnl_avg=9.3998
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1299.6353, pnl_avg=1299.6353
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=2012.7291, pnl_avg=17.6555

### Rank 11 - `s0.30_tp0.80_sl6.00`
- Params: scale `0.30`, TP `0.8000%`, SL `6.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `3006.0439 USDT`
- Total Return / CAGR: `200.6044%` / `30.6884%`
- MDD: `41.5945%` (`796.5011 USDT`), Calmar `0.7378`
- Vol/Sharpe/Sortino: `48.1359%` / `0.7933` / `0.9718`
- Trades: `463` (Long `348`, Short `115`), Win `80.5616%`, PF `2.5606`
- Avg/Median trade PnL: `12.5381` / `5.9795`, Avg/Median hold: `113.7088h` / `4.2833h`
- Worst Month: `2022-04 (-26.8312%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-11-06 05:03:00` -> recovery `2024-12-05 02:33:00`, depth `41.5945%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-1701.2338, pnl_avg=-1701.2338
- `LONG` / `Take Profit`: trades=347, pnl_sum=3847.8192, pnl_avg=11.0888
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1226.3959, pnl_avg=1226.3959
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=2432.1543, pnl_avg=21.3347

### Rank 12 - `s0.40_tp0.80_sl5.00`
- Params: scale `0.40`, TP `0.8000%`, SL `5.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `2818.7600 USDT`
- Total Return / CAGR: `181.8760%` / `28.6599%`
- MDD: `52.2746%` (`1731.4404 USDT`), Calmar `0.5483`
- Vol/Sharpe/Sortino: `67.0223%` / `0.7035` / `0.8736`
- Trades: `466` (Long `351`, Short `115`), Win `80.6867%`, PF `2.1732`
- Avg/Median trade PnL: `17.8087` / `9.9986`, Avg/Median hold: `112.4411h` / `4.2750h`
- Worst Month: `2022-04 (-32.7816%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-11-06 05:03:00` -> recovery `2024-12-16 21:47:00`, depth `52.2746%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-3826.3165, pnl_avg=-3826.3165
- `LONG` / `Take Profit`: trades=350, pnl_sum=6407.7380, pnl_avg=18.3078
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1878.1035, pnl_avg=1878.1035
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=3839.3086, pnl_avg=33.6781

### Rank 13 - `s0.40_tp0.60_sl5.00`
- Params: scale `0.40`, TP `0.6000%`, SL `5.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `2621.8562 USDT`
- Total Return / CAGR: `162.1856%` / `26.4141%`
- MDD: `53.8490%` (`1445.2582 USDT`), Calmar `0.4905`
- Vol/Sharpe/Sortino: `66.7730%` / `0.6774` / `0.8426`
- Trades: `592` (Long `477`, Short `115`), Win `84.7973%`, PF `2.1244`
- Avg/Median trade PnL: `13.0048` / `7.2165`, Avg/Median hold: `87.9848h` / `2.9083h`
- Worst Month: `2025-01 (-31.7227%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-11-06 05:03:00` -> recovery `2025-07-16 13:10:00`, depth `53.8490%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-3559.0302, pnl_avg=-3559.0302
- `LONG` / `Take Profit`: trades=476, pnl_sum=5762.6180, pnl_avg=12.1063
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1746.9091, pnl_avg=1746.9091
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=3748.3634, pnl_avg=32.8804

### Rank 14 - `s0.30_tp0.60_sl8.00`
- Params: scale `0.30`, TP `0.6000%`, SL `8.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `2510.7433 USDT`
- Total Return / CAGR: `151.0743%` / `25.0899%`
- MDD: `44.3005%` (`1148.0924 USDT`), Calmar `0.5664`
- Vol/Sharpe/Sortino: `51.6183%` / `0.6902` / `0.8498`
- Trades: `766` (Long `651`, Short `115`), Win `88.2507%`, PF `2.7949`
- Avg/Median trade PnL: `8.8556` / `4.6134`, Avg/Median hold: `64.4575h` / `2.5333h`
- Worst Month: `2025-01 (-29.5277%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-11-06 05:03:00` -> recovery `2024-12-06 00:41:00`, depth `44.3005%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-1480.3865, pnl_avg=-1480.3865
- `LONG` / `Take Profit`: trades=650, pnl_sum=5293.3784, pnl_avg=8.1437
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1055.0642, pnl_avg=1055.0642
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=1915.3105, pnl_avg=16.8010

### Rank 15 - `s0.30_tp0.80_sl5.00`
- Params: scale `0.30`, TP `0.8000%`, SL `5.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `2295.8913 USDT`
- Total Return / CAGR: `129.5891%` / `22.3981%`
- MDD: `40.4970%` (`954.6572 USDT`), Calmar `0.5531`
- Vol/Sharpe/Sortino: `47.4518%` / `0.6599` / `0.7904`
- Trades: `466` (Long `351`, Short `115`), Win `80.6867%`, PF `2.2189`
- Avg/Median trade PnL: `11.1050` / `5.9680`, Avg/Median hold: `112.4411h` / `4.2750h`
- Worst Month: `2022-04 (-24.2162%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-11-06 05:03:00` -> recovery `2024-12-16 05:42:00`, depth `40.4970%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-2156.6073, pnl_avg=-2156.6073
- `LONG` / `Take Profit`: trades=350, pnl_sum=3894.3647, pnl_avg=11.1268
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1058.5459, pnl_avg=1058.5459
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=2378.6233, pnl_avg=20.8651

### Rank 16 - `s0.30_tp0.60_sl5.00`
- Params: scale `0.30`, TP `0.6000%`, SL `5.0000%`, hysteresis `0.0000%`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `2173.3050 USDT`
- Total Return / CAGR: `117.3305%` / `20.7757%`
- MDD: `41.9334%` (`892.3401 USDT`), Calmar `0.4954`
- Vol/Sharpe/Sortino: `47.3048%` / `0.6323` / `0.7584`
- Trades: `592` (Long `477`, Short `115`), Win `84.7973%`, PF `2.1658`
- Avg/Median trade PnL: `8.1911` / `4.2479`, Avg/Median hold: `87.9848h` / `2.9083h`
- Worst Month: `2025-01 (-22.6507%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-11-06 05:03:00` -> recovery `2025-07-15 23:08:00`, depth `41.9334%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-2041.4579, pnl_avg=-2041.4579
- `LONG` / `Take Profit`: trades=476, pnl_sum=3540.6677, pnl_avg=7.4384
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1002.0262, pnl_avg=1002.0262
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=2347.8906, pnl_avg=20.5955

## 7) Output Files
- script: `12_backtest_ethusdt_scale_tpsl_sweep.py`
- plot (top 4 only): `12_backtest_ethusdt_scale_tpsl_sweep.png`
- metrics (all cases): `12_backtest_ethusdt_scale_tpsl_sweep.csv`
- report (all cases detailed): `12_backtest_ethusdt_scale_tpsl_sweep.md`