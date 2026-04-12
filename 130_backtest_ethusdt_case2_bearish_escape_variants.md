# Study 130: ETHUSDT case2 bearish-escape variants

## Setup
- Symbol: `ETHUSDT`
- Window: `2021-01-01 00:00:00` -> `2026-04-12 05:30:00`
- Initial capital per variant: `1000 USDT`
- Baseline engine: study-42 case2 (`dual-direction / no-hedge / prev-touch-only / max entries 4`).
- Variant goal: reduce the chance of getting stuck in a large long during a bearish transition.
- Data sources used:
  - `historical_data_mainnet\ETHUSDT_1m_2021-01-01_2021-12-31.pkl`
  - `historical_data_mainnet\ETHUSDT_1m_2022-01-01_2024-12-31.pkl`
  - `historical_data_mainnet\ETHUSDT_1m_2025-01-01_2026-04-12.pkl`

## Variant axes
- `short_rsi_overbought`: lower bearish reverse trigger from `85` to `80`.
- `allow_short_reverse_on_prev_touch`: allow long-to-short reverse even if previous 4h candle touched EMA200.
- `fix_stop_rearm`: re-arm stop logic after reentry instead of leaving `stop_loss[1] == 0`.
- `bearish_flip_trim_frac`: immediately trim an open long on the first bullish->bearish trend flip.

## Results
| Variant | Final Equity | Total Return % | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Crash Equity | First Zero TS | Reverse | Stop | Reentry | Trim |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| baseline_case2 | 0.0000 | -100.0000 | -100.0000 | 100.0000 | -1.0000 | N/A | N/A | 0.0000 | 2021-05-19 12:50:00 | 9 | 86 | 31 | 0 |
| short_rsi80 | 0.0000 | -100.0000 | -100.0000 | 100.0000 | -1.0000 | N/A | N/A | 2953.8484 | 2021-05-26 02:20:00 | 10 | 92 | 35 | 0 |
| short_rsi80_reverse_nogate | 0.0000 | -100.0000 | -100.0000 | 100.0000 | -1.0000 | N/A | N/A | 2804.5016 | 2021-05-26 02:20:00 | 10 | 92 | 35 | 0 |
| short_rsi80_reverse_nogate_stopfix | 1.1832 | -99.8817 | -72.1235 | 99.9183 | -0.7218 | -42.7800 | 70.8010 | 433.7643 | N/A | 235 | 1005 | 338 | 0 |
| short_rsi80_reverse_nogate_stopfix_trim80 | 1.2123 | -99.8788 | -71.9948 | 99.9126 | -0.7206 | -45.8094 | 70.4259 | 390.4960 | N/A | 128 | 983 | 301 | 331 |

## Takeaways
- Highest CAGR: `short_rsi80_reverse_nogate_stopfix_trim80` with CAGR `-71.9948%`, MDD `99.9126%`.
- Best Calmar: `short_rsi80_reverse_nogate_stopfix_trim80` with Calmar `-0.7206`, CAGR `-71.9948%`.
- Best May-2021 survival equity: `short_rsi80` with equity `2953.8484` at `2021-05-19 12:50:00`.

## Outputs
- Plot: `130_backtest_ethusdt_case2_bearish_escape_variants.png`
- Metrics CSV: `130_backtest_ethusdt_case2_bearish_escape_variants.csv`
- Curves CSV: `130_backtest_ethusdt_case2_bearish_escape_variants_curves.csv`
- Report: `130_backtest_ethusdt_case2_bearish_escape_variants.md`