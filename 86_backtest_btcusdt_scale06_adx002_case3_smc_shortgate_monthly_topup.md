# Study 86: 85-Best Mix With Monthly 1000 Top-Up

## Setup
- Fixed weights from study 85 best mix: `case1 62% / case2 31% / case3 7%`.
- `case1` is rerun latest as `shallow6_else2bull` using the cached file ending on `2026-03-15` and keeps the last available minute in that cache.
- `case2` is rerun latest with study-42 case2 logic using the same latest cached minute range.
- `case3` uses study-84 winner `short_gate_24h_g12_tp15`.
- Portfolio keeps the same `4h rebalance` logic and fee model as studies 70/81/85.
- Top-up assumption: add `1000` USDT on the first available timestamp of each new month, starting after the initial month, and split it directly at target weights.
- Because cash flows distort plain CAGR, this report uses `TWR CAGR/MDD/Calmar` and also reports `final equity`, `total contributed`, and `XIRR`.

## Common Period
- Start: `2022-01-01 08:00:00`
- End: `2026-03-15 05:19:00`
- Rows: `2207113`

## Results

| Variant | Final Equity | Total Contributed | Net Profit | Money Multiple | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid | Topups |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_topup | 45590.8682 | 2000.0000 | 43590.8682 | 22.7954 | 110.5383 | 46.7127 | 2.3663 | 110.5383 | 9203 | 269.8968 | 0 |
| monthly_topup_1000 | 351282.8201 | 52000.0000 | 299282.8201 | 6.7554 | 110.5383 | 46.7127 | 2.3663 | 104.2066 | 9203 | 1931.8540 | 50 |

## Delta: Monthly Top-Up vs No Top-Up
- Final equity delta: `305691.9519`
- Total contributed delta: `50000.0000`
- Net profit delta: `255691.9519`
- TWR CAGR delta: `-0.0000pp`
- TWR MDD delta: `0.0000pp`
- XIRR delta: `-6.3318pp`

## Interpretation
- If `TWR CAGR/MDD` stay close to the no-topup run, then monthly cash injection is mostly scaling notional rather than changing the strategy edge.
- If `XIRR` stays strong while `money multiple` compresses, that means the portfolio is still compounding well but the later deposits had less time to work.
- Deposit-on-target-weights is the cleanest analogue to adding capital into a portfolio that is already maintained by scheduled rebalancing.

## Outputs
- Plot: `86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.png`
- Metrics CSV: `86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.csv`
- Curves CSV: `86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup_curves.csv`
- Topups CSV: `86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup_topups.csv`
- Report: `86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.md`