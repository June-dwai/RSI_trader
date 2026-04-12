# Study 131: ETHUSDT case2 leverage cut + wider TP/SL

## Setup
- Symbol: `ETHUSDT`
- Window: `2021-01-01 00:00:00` -> `2026-04-12 08:20:00`
- Initial capital per variant: `1000 USDT`
- Max entries stays `4`.
- Requested test: lower max notional from `2.4x` to `1.2x` by changing `entry_scale 0.60 -> 0.30`.
- Requested TP/SL widening: baseline `1.2% / 3.0%` -> `2.4% / 6.0%`.
- Included one extra control with `stop rearm` fix so the leverage test is not fully dominated by the known reentry bug.
- Data sources used:
  - `historical_data_mainnet\ETHUSDT_1m_2021-01-01_2021-12-31.pkl`
  - `historical_data_mainnet\ETHUSDT_1m_2022-01-01_2024-12-31.pkl`
  - `historical_data_mainnet\ETHUSDT_1m_2025-01-01_2026-04-12.pkl`

## Results
| Variant | Max Notional x | TP % | SL % | Final Equity | CAGR % | MDD % | Calmar | 2026 Return % | Crash Equity | First Zero TS | Reverse | Stop | Reentry |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| baseline_case2 | 2.40 | 1.20 | 3.00 | 0.0000 | -100.0000 | 100.0000 | -1.0000 | N/A | 0.0000 | 2021-05-19 12:50:00 | 9 | 86 | 31 |
| lev12_tp2x_sl2x | 1.20 | 2.40 | 6.00 | 4512.4692 | 33.0541 | 76.8370 | 0.4302 | 2.0680 | 1669.9967 | N/A | 183 | 233 | 60 |
| lev12_tp2x_sl2x_stopfix | 1.20 | 2.40 | 6.00 | 1423.7042 | 6.9244 | 76.3333 | 0.0907 | -7.0300 | 1642.0625 | N/A | 179 | 333 | 90 |

## Takeaways
- Highest CAGR: `lev12_tp2x_sl2x` with CAGR `33.0541%`, MDD `76.8370%`.
- Best Calmar: `lev12_tp2x_sl2x` with Calmar `0.4302`.
- Best May 19 crash survival equity: `lev12_tp2x_sl2x` with `1669.9967` at `2021-05-19 12:50:00`.

## Outputs
- Plot: `131_backtest_ethusdt_case2_lev12_wide_tpsl.png`
- Metrics CSV: `131_backtest_ethusdt_case2_lev12_wide_tpsl.csv`
- Curves CSV: `131_backtest_ethusdt_case2_lev12_wide_tpsl_curves.csv`
- Report: `131_backtest_ethusdt_case2_lev12_wide_tpsl.md`