# 11 ETHUSDT Hysteresis + TP/SL Case Study

## 1) Objective
- Use ETH-specific sweep with wider hysteresis bands and TP/SL permutations.
- Keep strategy core as: `04 long-only + trend short hedge 5x` with 4h confirmed trend.
- Apply `entry_scale=0.40` for all cases.

## 2) Sweep Grid
- Symbol: `ETHUSDT`
- Data period: `2022-01-01` to `2026-02-12`
- Confirmation policy: closed 4h state only (`shift(1)`, no look-ahead)
- Hysteresis bands (%): `0.00, 0.50, 1.00, 2.00, 3.00`
- TP values (%): `0.80, 1.60`
- SL values (%): `2.00, 4.00`
- Total cases: `20`

## 3) Best Summary
- Best Final Equity: `h0.00_tp0.80_sl4.00` (`9785.9656 USDT`).
- Best Calmar: `h0.00_tp0.80_sl4.00` (`1.4332`).
- Lowest MDD: `h0.00_tp1.60_sl2.00` (`50.7421%`).

## 4) Top 4 Cases (Plotted)

| Rank | Case | Hysteresis % | TP % | SL % | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Win Rate % |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `h0.00_tp0.80_sl4.00` | 0.0000 | 0.8000 | 4.0000 | 9785.9656 | 878.5966 | 74.1369 | 51.7268 | 1.4332 | 656 | 86.2805 |
| 2 | `h0.50_tp0.80_sl4.00` | 0.5000 | 0.8000 | 4.0000 | 7389.2012 | 638.9201 | 62.6379 | 67.9724 | 0.9215 | 613 | 91.3540 |
| 3 | `h1.00_tp0.80_sl4.00` | 1.0000 | 0.8000 | 4.0000 | 5668.5442 | 466.8544 | 52.4846 | 56.0267 | 0.9368 | 596 | 92.6174 |
| 4 | `h0.00_tp0.80_sl2.00` | 0.0000 | 0.8000 | 2.0000 | 4949.6914 | 394.9691 | 47.5382 | 52.9479 | 0.8978 | 622 | 85.5305 |

## 5) Full Ranking Table (All Cases)

| Rank | Case | Hyst % | TP % | SL % | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Worst Month |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `h0.00_tp0.80_sl4.00` | 0.0000 | 0.8000 | 4.0000 | 9785.9656 | 878.5966 | 74.1369 | 51.7268 | 1.4332 | 656 | 541/115 | 86.2805 | 2.7678 | `2025-01 (-32.4929%)` |
| 2 | `h0.50_tp0.80_sl4.00` | 0.5000 | 0.8000 | 4.0000 | 7389.2012 | 638.9201 | 62.6379 | 67.9724 | 0.9215 | 613 | 541/72 | 91.3540 | 2.7411 | `2025-01 (-49.2247%)` |
| 3 | `h1.00_tp0.80_sl4.00` | 1.0000 | 0.8000 | 4.0000 | 5668.5442 | 466.8544 | 52.4846 | 56.0267 | 0.9368 | 596 | 541/55 | 92.6174 | 2.7913 | `2025-01 (-31.3668%)` |
| 4 | `h0.00_tp0.80_sl2.00` | 0.0000 | 0.8000 | 2.0000 | 4949.6914 | 394.9691 | 47.5382 | 52.9479 | 0.8978 | 622 | 507/115 | 85.5305 | 2.1663 | `2025-01 (-32.0074%)` |
| 5 | `h0.00_tp1.60_sl2.00` | 0.0000 | 1.6000 | 2.0000 | 4840.2954 | 384.0295 | 46.7386 | 50.7421 | 0.9211 | 259 | 144/115 | 65.2510 | 1.7208 | `2025-01 (-32.0074%)` |
| 6 | `h0.00_tp1.60_sl4.00` | 0.0000 | 1.6000 | 4.0000 | 4384.1375 | 338.4138 | 43.2487 | 53.8027 | 0.8038 | 232 | 117/115 | 61.2069 | 1.8179 | `2025-01 (-32.4929%)` |
| 7 | `h0.50_tp0.80_sl2.00` | 0.5000 | 0.8000 | 2.0000 | 3933.4272 | 293.3427 | 39.5192 | 68.7658 | 0.5747 | 579 | 507/72 | 90.8463 | 2.2003 | `2025-01 (-48.4006%)` |
| 8 | `h0.50_tp1.60_sl2.00` | 0.5000 | 1.6000 | 2.0000 | 3791.2077 | 279.1208 | 38.2753 | 69.5385 | 0.5504 | 216 | 144/72 | 75.4630 | 1.7276 | `2024-04 (-50.8573%)` |
| 9 | `h0.50_tp1.60_sl4.00` | 0.5000 | 1.6000 | 4.0000 | 3369.8122 | 236.9812 | 34.3696 | 72.5303 | 0.4739 | 189 | 117/72 | 71.9577 | 1.7880 | `2024-04 (-53.1121%)` |
| 10 | `h1.00_tp0.80_sl2.00` | 1.0000 | 0.8000 | 2.0000 | 2896.6169 | 189.6617 | 29.5152 | 57.5382 | 0.5130 | 562 | 507/55 | 92.1708 | 2.1288 | `2024-04 (-30.9462%)` |
| 11 | `h1.00_tp1.60_sl2.00` | 1.0000 | 1.6000 | 2.0000 | 2788.5688 | 178.8569 | 28.3234 | 70.2820 | 0.4030 | 199 | 144/55 | 77.8894 | 1.6527 | `2024-04 (-50.0249%)` |
| 12 | `h2.00_tp0.80_sl4.00` | 2.0000 | 0.8000 | 4.0000 | 2606.4652 | 160.6465 | 26.2332 | 53.7647 | 0.4879 | 583 | 541/42 | 93.9966 | 2.4148 | `2025-01 (-22.6377%)` |
| 13 | `h1.00_tp1.60_sl4.00` | 1.0000 | 1.6000 | 4.0000 | 2504.4782 | 150.4478 | 25.0139 | 73.2711 | 0.3414 | 172 | 117/55 | 74.4186 | 1.7380 | `2024-04 (-52.2428%)` |
| 14 | `h3.00_tp0.80_sl4.00` | 3.0000 | 0.8000 | 4.0000 | 1658.2585 | 65.8259 | 13.0874 | 66.5641 | 0.1966 | 577 | 541/36 | 94.9740 | 2.1658 | `2024-10 (-26.8798%)` |
| 15 | `h2.00_tp0.80_sl2.00` | 2.0000 | 0.8000 | 2.0000 | 1386.5988 | 38.6599 | 8.2727 | 57.8108 | 0.1431 | 549 | 507/42 | 93.6248 | 1.9107 | `2024-04 (-31.2980%)` |
| 16 | `h2.00_tp1.60_sl2.00` | 2.0000 | 1.6000 | 2.0000 | 1208.0005 | 20.8001 | 4.7024 | 80.4851 | 0.0584 | 186 | 144/42 | 81.1828 | 1.4478 | `2024-04 (-60.1345%)` |
| 17 | `h2.00_tp1.60_sl4.00` | 2.0000 | 1.6000 | 4.0000 | 1054.4197 | 5.4420 | 1.2969 | 83.4368 | 0.0155 | 159 | 117/42 | 77.9874 | 1.4885 | `2024-04 (-63.2777%)` |
| 18 | `h3.00_tp0.80_sl2.00` | 3.0000 | 0.8000 | 2.0000 | 990.8460 | -0.9154 | -0.2234 | 69.1755 | -0.0032 | 543 | 507/36 | 94.6593 | 1.8157 | `2024-04 (-33.8977%)` |
| 19 | `h3.00_tp1.60_sl2.00` | 3.0000 | 1.6000 | 2.0000 | 794.1058 | -20.5894 | -5.4519 | 85.0851 | -0.0641 | 180 | 144/36 | 83.8889 | 1.3467 | `2024-04 (-66.9642%)` |
| 20 | `h3.00_tp1.60_sl4.00` | 3.0000 | 1.6000 | 4.0000 | 734.0137 | -26.5986 | -7.2439 | 88.0200 | -0.0823 | 153 | 117/36 | 81.0458 | 1.3882 | `2024-04 (-70.5884%)` |

## 6) Detailed Per-Case Notes (All Cases)

### Rank 1 - `h0.00_tp0.80_sl4.00`
- Params: hysteresis `0.0000%`, TP `0.8000%`, SL `4.0000%`, entry_scale `0.40`
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

### Rank 2 - `h0.50_tp0.80_sl4.00`
- Params: hysteresis `0.5000%`, TP `0.8000%`, SL `4.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `7389.2012 USDT`
- Total Return / CAGR: `638.9201%` / `62.6379%`
- MDD: `67.9724%` (`2971.9427 USDT`), Calmar `0.9215`
- Vol/Sharpe/Sortino: `71.4369%` / `1.0218` / `1.3243`
- Trades: `613` (Long `541`, Short `72`), Win `91.3540%`, PF `2.7411`
- Avg/Median trade PnL: `30.0633` / `15.8191`, Avg/Median hold: `80.5104h` / `3.8167h`
- Worst Month: `2025-01 (-49.2247%)`, DD episode: peak `2024-12-17 03:45:00` -> trough `2025-04-24 08:35:00` -> recovery `2025-07-16 19:37:00`, depth `67.9724%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-6477.8111, pnl_avg=-6477.8111
- `LONG` / `Take Profit`: trades=540, pnl_sum=14144.3610, pnl_avg=26.1933
- `SHORT` / `Hedge Close Trend Up`: trades=71, pnl_sum=4798.3959, pnl_avg=67.5830
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=5963.8382, pnl_avg=5963.8382

### Rank 3 - `h1.00_tp0.80_sl4.00`
- Params: hysteresis `1.0000%`, TP `0.8000%`, SL `4.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `5668.5442 USDT`
- Total Return / CAGR: `466.8544%` / `52.4846%`
- MDD: `56.0267%` (`2402.0768 USDT`), Calmar `0.9368`
- Vol/Sharpe/Sortino: `67.0719%` / `0.9573` / `1.1934`
- Trades: `596` (Long `541`, Short `55`), Win `92.6174%`, PF `2.7913`
- Avg/Median trade PnL: `24.5632` / `14.1922`, Avg/Median hold: `82.3370h` / `3.4667h`
- Worst Month: `2025-01 (-31.3668%)`, DD episode: peak `2024-12-17 03:45:00` -> trough `2025-04-24 08:35:00` -> recovery `2025-06-11 15:36:00`, depth `56.0267%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-5007.3104, pnl_avg=-5007.3104
- `LONG` / `Take Profit`: trades=540, pnl_sum=11705.7504, pnl_avg=21.6773
- `SHORT` / `Hedge Close Trend Up`: trades=54, pnl_sum=3374.5078, pnl_avg=62.4909
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=4566.7295, pnl_avg=4566.7295

### Rank 4 - `h0.00_tp0.80_sl2.00`
- Params: hysteresis `0.0000%`, TP `0.8000%`, SL `2.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `4949.6914 USDT`
- Total Return / CAGR: `394.9691%` / `47.5382%`
- MDD: `52.9479%` (`2477.5817 USDT`), Calmar `0.8978`
- Vol/Sharpe/Sortino: `61.4725%` / `0.9309` / `1.2097`
- Trades: `622` (Long `507`, Short `115`), Win `85.5305%`, PF `2.1663`
- Avg/Median trade PnL: `22.8161` / `13.1499`, Avg/Median hold: `84.3414h` / `4.0000h`
- Worst Month: `2025-01 (-32.0074%)`, DD episode: peak `2024-12-05 22:01:00` -> trough `2025-05-06 21:30:00` -> recovery `2025-07-16 07:35:00`, depth `52.9479%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-7933.3526, pnl_avg=-7933.3526
- `LONG` / `Take Profit`: trades=506, pnl_sum=12682.5843, pnl_avg=25.0644
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=3556.5796, pnl_avg=3556.5796
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=5885.8016, pnl_avg=51.6298

### Rank 5 - `h0.00_tp1.60_sl2.00`
- Params: hysteresis `0.0000%`, TP `1.6000%`, SL `2.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `4840.2954 USDT`
- Total Return / CAGR: `384.0295%` / `46.7386%`
- MDD: `50.7421%` (`3098.7964 USDT`), Calmar `0.9211`
- Vol/Sharpe/Sortino: `70.4737%` / `0.8762` / `1.1731`
- Trades: `259` (Long `144`, Short `115`), Win `65.2510%`, PF `1.7208`
- Avg/Median trade PnL: `35.3518` / `18.2003`, Avg/Median hold: `207.5802h` / `12.0000h`
- Worst Month: `2025-01 (-32.0074%)`, DD episode: peak `2024-03-12 11:24:00` -> trough `2024-05-20 13:39:00` -> recovery `2024-07-05 09:06:00`, depth `50.7421%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-8477.6116, pnl_avg=-8477.6116
- `LONG` / `Take Profit`: trades=143, pnl_sum=8142.5053, pnl_avg=56.9406
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=3530.6302, pnl_avg=3530.6302
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=5960.5834, pnl_avg=52.2858

### Rank 6 - `h0.00_tp1.60_sl4.00`
- Params: hysteresis `0.0000%`, TP `1.6000%`, SL `4.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `4384.1375 USDT`
- Total Return / CAGR: `338.4138%` / `43.2487%`
- MDD: `53.8027%` (`2282.4861 USDT`), Calmar `0.8038`
- Vol/Sharpe/Sortino: `74.8030%` / `0.8321` / `1.0833`
- Trades: `232` (Long `117`, Short `115`), Win `61.2069%`, PF `1.8179`
- Avg/Median trade PnL: `39.5280` / `16.0527`, Avg/Median hold: `232.4505h` / `12.8750h`
- Worst Month: `2025-01 (-32.4929%)`, DD episode: peak `2024-03-12 11:24:00` -> trough `2024-05-20 13:39:00` -> recovery `2024-11-27 21:02:00`, depth `53.8027%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-6928.1034, pnl_avg=-6928.1034
- `LONG` / `Take Profit`: trades=116, pnl_sum=7284.6315, pnl_avg=62.7985
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=3171.8427, pnl_avg=3171.8427
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=5642.1187, pnl_avg=49.4923

### Rank 7 - `h0.50_tp0.80_sl2.00`
- Params: hysteresis `0.5000%`, TP `0.8000%`, SL `2.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `3933.4272 USDT`
- Total Return / CAGR: `293.3427%` / `39.5192%`
- MDD: `68.7658%` (`2455.6792 USDT`), Calmar `0.5747`
- Vol/Sharpe/Sortino: `66.0659%` / `0.8169` / `1.0549`
- Trades: `579` (Long `507`, Short `72`), Win `90.8463%`, PF `2.2003`
- Avg/Median trade PnL: `19.8742` / `13.7711`, Avg/Median hold: `90.6811h` / `3.4667h`
- Worst Month: `2025-01 (-48.4006%)`, DD episode: peak `2024-12-05 22:01:00` -> trough `2025-04-24 08:35:00` -> recovery `2025-07-17 09:29:00`, depth `68.7658%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-5985.0727, pnl_avg=-5985.0727
- `LONG` / `Take Profit`: trades=506, pnl_sum=10670.2894, pnl_avg=21.0875
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=2683.1516, pnl_avg=2683.1516
- `SHORT` / `Hedge Close Trend Up`: trades=71, pnl_sum=4138.8059, pnl_avg=58.2930

### Rank 8 - `h0.50_tp1.60_sl2.00`
- Params: hysteresis `0.5000%`, TP `1.6000%`, SL `2.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `3791.2077 USDT`
- Total Return / CAGR: `279.1208%` / `38.2753%`
- MDD: `69.5385%` (`2377.2897 USDT`), Calmar `0.5504`
- Vol/Sharpe/Sortino: `82.9361%` / `0.7573` / `1.0338`
- Trades: `216` (Long `144`, Short `72`), Win `75.4630%`, PF `1.7276`
- Avg/Median trade PnL: `33.5003` / `21.0311`, Avg/Median hold: `249.1077h` / `16.0000h`
- Worst Month: `2024-04 (-50.8573%)`, DD episode: peak `2024-03-12 11:24:00` -> trough `2024-05-20 16:15:00` -> recovery `2024-11-18 15:42:00`, depth `69.5385%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-6298.9173, pnl_avg=-6298.9173
- `LONG` / `Take Profit`: trades=143, pnl_sum=6909.2153, pnl_avg=48.3162
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=2623.2799, pnl_avg=2623.2799
- `SHORT` / `Hedge Close Trend Up`: trades=71, pnl_sum=4002.4791, pnl_avg=56.3729

### Rank 9 - `h0.50_tp1.60_sl4.00`
- Params: hysteresis `0.5000%`, TP `1.6000%`, SL `4.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `3369.8122 USDT`
- Total Return / CAGR: `236.9812%` / `34.3696%`
- MDD: `72.5303%` (`2367.9573 USDT`), Calmar `0.4739`
- Vol/Sharpe/Sortino: `88.5671%` / `0.7200` / `0.9720`
- Trades: `189` (Long `117`, Short `72`), Win `71.9577%`, PF `1.7880`
- Avg/Median trade PnL: `36.7645` / `27.0448`, Avg/Median hold: `285.5689h` / `21.2333h`
- Worst Month: `2024-04 (-53.1121%)`, DD episode: peak `2024-03-12 11:24:00` -> trough `2024-05-20 16:15:00` -> recovery `2025-07-17 07:37:00`, depth `72.5303%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-5053.6419, pnl_avg=-5053.6419
- `LONG` / `Take Profit`: trades=116, pnl_sum=6047.6802, pnl_avg=52.1352
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=2313.6718, pnl_avg=2313.6718
- `SHORT` / `Hedge Close Trend Up`: trades=71, pnl_sum=3640.7800, pnl_avg=51.2786

### Rank 10 - `h1.00_tp0.80_sl2.00`
- Params: hysteresis `1.0000%`, TP `0.8000%`, SL `2.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `2896.6169 USDT`
- Total Return / CAGR: `189.6617%` / `29.5152%`
- MDD: `57.5382%` (`1791.5821 USDT`), Calmar `0.5130`
- Vol/Sharpe/Sortino: `62.9354%` / `0.7166` / `0.8769`
- Trades: `562` (Long `507`, Short `55`), Win `92.1708%`, PF `2.1288`
- Avg/Median trade PnL: `16.0625` / `12.0382`, Avg/Median hold: `92.9259h` / `3.2500h`
- Worst Month: `2024-04 (-30.9462%)`, DD episode: peak `2024-12-05 22:01:00` -> trough `2025-04-24 08:35:00` -> recovery `2025-07-16 00:40:00`, depth `57.5382%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-5099.9374, pnl_avg=-5099.9374
- `LONG` / `Take Profit`: trades=506, pnl_sum=8913.2074, pnl_avg=17.6150
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=2264.8729, pnl_avg=2264.8729
- `SHORT` / `Hedge Close Trend Up`: trades=54, pnl_sum=2948.9648, pnl_avg=54.6105

### Rank 11 - `h1.00_tp1.60_sl2.00`
- Params: hysteresis `1.0000%`, TP `1.6000%`, SL `2.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `2788.5688 USDT`
- Total Return / CAGR: `178.8569%` / `28.3234%`
- MDD: `70.2820%` (`2270.0209 USDT`), Calmar `0.4030`
- Vol/Sharpe/Sortino: `82.2164%` / `0.6634` / `0.8950`
- Trades: `199` (Long `144`, Short `55`), Win `77.8894%`, PF `1.6527`
- Avg/Median trade PnL: `27.5301` / `21.6279`, Avg/Median hold: `268.9812h` / `14.9333h`
- Worst Month: `2024-04 (-50.0249%)`, DD episode: peak `2024-03-12 11:24:00` -> trough `2024-05-20 01:36:00` -> recovery `2024-11-29 14:54:00`, depth `70.2820%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-5494.0589, pnl_avg=-5494.0589
- `LONG` / `Take Profit`: trades=143, pnl_sum=5769.0352, pnl_avg=40.3429
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=2266.6018, pnl_avg=2266.6018
- `SHORT` / `Hedge Close Trend Up`: trades=54, pnl_sum=2936.9041, pnl_avg=54.3871

### Rank 12 - `h2.00_tp0.80_sl4.00`
- Params: hysteresis `2.0000%`, TP `0.8000%`, SL `4.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `2606.4652 USDT`
- Total Return / CAGR: `160.6465%` / `26.2332%`
- MDD: `53.7647%` (`1432.6011 USDT`), Calmar `0.4879`
- Vol/Sharpe/Sortino: `67.5522%` / `0.6785` / `0.8036`
- Trades: `583` (Long `541`, Short `42`), Win `93.9966%`, PF `2.4148`
- Avg/Median trade PnL: `12.6462` / `8.2199`, Avg/Median hold: `84.9895h` / `3.3667h`
- Worst Month: `2025-01 (-22.6377%)`, DD episode: peak `2024-03-13 11:46:00` -> trough `2024-05-22 12:52:00` -> recovery `2024-12-16 14:47:00`, depth `53.7647%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-2432.3431, pnl_avg=-2432.3431
- `LONG` / `Take Profit`: trades=540, pnl_sum=6889.6395, pnl_avg=12.7586
- `SHORT` / `Hedge Close Trend Up`: trades=41, pnl_sum=844.2490, pnl_avg=20.5914
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=2071.1906, pnl_avg=2071.1906

### Rank 13 - `h1.00_tp1.60_sl4.00`
- Params: hysteresis `1.0000%`, TP `1.6000%`, SL `4.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `2504.4782 USDT`
- Total Return / CAGR: `150.4478%` / `25.0139%`
- MDD: `73.2711%` (`2009.6456 USDT`), Calmar `0.3414`
- Vol/Sharpe/Sortino: `89.0713%` / `0.6350` / `0.8615`
- Trades: `172` (Long `117`, Short `55`), Win `74.4186%`, PF `1.7380`
- Avg/Median trade PnL: `31.6675` / `24.8229`, Avg/Median hold: `312.1658h` / `22.1083h`
- Worst Month: `2024-04 (-52.2428%)`, DD episode: peak `2024-03-12 11:24:00` -> trough `2024-05-20 01:36:00` -> recovery `2025-07-16 17:02:00`, depth `73.2711%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-4350.4734, pnl_avg=-4350.4734
- `LONG` / `Take Profit`: trades=116, pnl_sum=5198.9395, pnl_avg=44.8184
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1973.0451, pnl_avg=1973.0451
- `SHORT` / `Hedge Close Trend Up`: trades=54, pnl_sum=2625.2926, pnl_avg=48.6165

### Rank 14 - `h3.00_tp0.80_sl4.00`
- Params: hysteresis `3.0000%`, TP `0.8000%`, SL `4.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `1658.2585 USDT`
- Total Return / CAGR: `65.8259%` / `13.0874%`
- MDD: `66.5641%` (`1013.2484 USDT`), Calmar `0.1966`
- Vol/Sharpe/Sortino: `71.8034%` / `0.5242` / `0.6378`
- Trades: `577` (Long `541`, Short `36`), Win `94.9740%`, PF `2.1658`
- Avg/Median trade PnL: `8.3759` / `5.7274`, Avg/Median hold: `84.6601h` / `3.2500h`
- Worst Month: `2024-10 (-26.8798%)`, DD episode: peak `2022-02-06 15:01:00` -> trough `2023-10-23 00:25:00` -> recovery `2024-02-27 12:33:00`, depth `66.5641%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-1547.4804, pnl_avg=-1547.4804
- `LONG` / `Take Profit`: trades=540, pnl_sum=5049.9732, pnl_avg=9.3518
- `SHORT` / `Hedge Close Trend Up`: trades=35, pnl_sum=12.6949, pnl_avg=0.3627
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1317.7116, pnl_avg=1317.7116

### Rank 15 - `h2.00_tp0.80_sl2.00`
- Params: hysteresis `2.0000%`, TP `0.8000%`, SL `2.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `1386.5988 USDT`
- Total Return / CAGR: `38.6599%` / `8.2727%`
- MDD: `57.8108%` (`1237.1732 USDT`), Calmar `0.1431`
- Vol/Sharpe/Sortino: `61.3317%` / `0.4321` / `0.4884`
- Trades: `549` (Long `507`, Short `42`), Win `93.6248%`, PF `1.9107`
- Avg/Median trade PnL: `8.9916` / `7.4035`, Avg/Median hold: `95.9934h` / `3.1000h`
- Worst Month: `2024-04 (-31.2980%)`, DD episode: peak `2024-03-12 15:11:00` -> trough `2025-04-24 08:35:00` -> recovery `2025-07-16 20:23:00`, depth `57.8108%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-2877.7372, pnl_avg=-2877.7372
- `LONG` / `Take Profit`: trades=506, pnl_sum=5703.8338, pnl_avg=11.2724
- `SHORT` / `Hedge Close Trend Up`: trades=41, pnl_sum=917.0691, pnl_avg=22.3675
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1193.2311, pnl_avg=1193.2311

### Rank 16 - `h2.00_tp1.60_sl2.00`
- Params: hysteresis `2.0000%`, TP `1.6000%`, SL `2.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `1208.0005 USDT`
- Total Return / CAGR: `20.8001%` / `4.7024%`
- MDD: `80.4851%` (`1515.2634 USDT`), Calmar `0.0584`
- Vol/Sharpe/Sortino: `73.7146%` / `0.4299` / `0.4644`
- Trades: `186` (Long `144`, Short `42`), Win `81.1828%`, PF `1.4478`
- Avg/Median trade PnL: `13.3970` / `15.9452`, Avg/Median hold: `290.3401h` / `13.3417h`
- Worst Month: `2024-04 (-60.1345%)`, DD episode: peak `2024-03-12 11:24:00` -> trough `2024-04-12 18:35:00` -> recovery `2025-07-18 01:18:00`, depth `80.4851%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-2932.7400, pnl_avg=-2932.7400
- `LONG` / `Take Profit`: trades=143, pnl_sum=3627.3200, pnl_avg=25.3659
- `SHORT` / `Hedge Close Trend Up`: trades=41, pnl_sum=667.5990, pnl_avg=16.2829
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=1129.6657, pnl_avg=1129.6657

### Rank 17 - `h2.00_tp1.60_sl4.00`
- Params: hysteresis `2.0000%`, TP `1.6000%`, SL `4.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `1054.4197 USDT`
- Total Return / CAGR: `5.4420%` / `1.2969%`
- MDD: `83.4368%` (`1844.2885 USDT`), Calmar `0.0155`
- Vol/Sharpe/Sortino: `78.0880%` / `0.4047` / `0.4306`
- Trades: `159` (Long `117`, Short `42`), Win `77.9874%`, PF `1.4885`
- Avg/Median trade PnL: `15.0579` / `19.1662`, Avg/Median hold: `340.6825h` / `16.9500h`
- Worst Month: `2024-04 (-63.2777%)`, DD episode: peak `2024-03-12 11:24:00` -> trough `2024-04-12 18:35:00` -> recovery `NaT`, depth `83.4368%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-2161.9514, pnl_avg=-2161.9514
- `LONG` / `Take Profit`: trades=116, pnl_sum=3297.3120, pnl_avg=28.4251
- `SHORT` / `Hedge Close Trend Up`: trades=41, pnl_sum=343.3753, pnl_avg=8.3750
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=915.4631, pnl_avg=915.4631

### Rank 18 - `h3.00_tp0.80_sl2.00`
- Params: hysteresis `3.0000%`, TP `0.8000%`, SL `2.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `990.8460 USDT`
- Total Return / CAGR: `-0.9154%` / `-0.2234%`
- MDD: `69.1755%` (`1062.1462 USDT`), Calmar `-0.0032`
- Vol/Sharpe/Sortino: `65.2415%` / `0.3166` / `0.3690`
- Trades: `543` (Long `507`, Short `36`), Win `94.6593%`, PF `1.8157`
- Avg/Median trade PnL: `6.4570` / `5.4955`, Avg/Median hold: `95.7649h` / `3.0500h`
- Worst Month: `2024-04 (-33.8977%)`, DD episode: peak `2024-03-12 15:11:00` -> trough `2025-04-30 13:59:00` -> recovery `2025-08-08 10:05:00`, depth `69.1755%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-1881.5561, pnl_avg=-1881.5561
- `LONG` / `Take Profit`: trades=506, pnl_sum=4426.0634, pnl_avg=8.7472
- `SHORT` / `Hedge Close Trend Up`: trades=35, pnl_sum=181.4861, pnl_avg=5.1853
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=780.1724, pnl_avg=780.1724

### Rank 19 - `h3.00_tp1.60_sl2.00`
- Params: hysteresis `3.0000%`, TP `1.6000%`, SL `2.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `794.1058 USDT`
- Total Return / CAGR: `-20.5894%` / `-5.4519%`
- MDD: `85.0851%` (`1388.7717 USDT`), Calmar `-0.0641`
- Vol/Sharpe/Sortino: `80.9409%` / `0.3328` / `0.3703`
- Trades: `180` (Long `144`, Short `36`), Win `83.8889%`, PF `1.3467`
- Avg/Median trade PnL: `8.6964` / `11.9472`, Avg/Median hold: `296.1293h` / `12.6583h`
- Worst Month: `2024-04 (-66.9642%)`, DD episode: peak `2024-03-12 11:24:00` -> trough `2024-04-12 18:35:00` -> recovery `2025-08-11 04:05:00`, depth `85.0851%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-2018.7432, pnl_avg=-2018.7432
- `LONG` / `Take Profit`: trades=143, pnl_sum=2827.9599, pnl_avg=19.7759
- `SHORT` / `Hedge Close Trend Up`: trades=35, pnl_sum=-21.4696, pnl_avg=-0.6134
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=777.6021, pnl_avg=777.6021

### Rank 20 - `h3.00_tp1.60_sl4.00`
- Params: hysteresis `3.0000%`, TP `1.6000%`, SL `4.0000%`, entry_scale `0.40`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `734.0137 USDT`
- Total Return / CAGR: `-26.5986%` / `-7.2439%`
- MDD: `88.0200%` (`1686.0675 USDT`), Calmar `-0.0823`
- Vol/Sharpe/Sortino: `87.0885%` / `0.3428` / `0.3824`
- Trades: `153` (Long `117`, Short `36`), Win `81.0458%`, PF `1.3882`
- Avg/Median trade PnL: `10.1305` / `17.4697`, Avg/Median hold: `349.4674h` / `15.2500h`
- Worst Month: `2024-04 (-70.5884%)`, DD episode: peak `2024-03-12 11:24:00` -> trough `2024-04-12 18:35:00` -> recovery `NaT`, depth `88.0200%`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-1375.9995, pnl_avg=-1375.9995
- `LONG` / `Take Profit`: trades=116, pnl_sum=2638.4132, pnl_avg=22.7449
- `SHORT` / `Hedge Close Trend Up`: trades=35, pnl_sum=-295.0988, pnl_avg=-8.4314
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=582.6573, pnl_avg=582.6573

## 7) Output Files
- script: `11_backtest_ethusdt_hyst_tpsl_sweep.py`
- plot (top 4 only): `11_backtest_ethusdt_hyst_tpsl_sweep.png`
- metrics (all cases): `11_backtest_ethusdt_hyst_tpsl_sweep.csv`
- report (all cases detailed): `11_backtest_ethusdt_hyst_tpsl_sweep.md`