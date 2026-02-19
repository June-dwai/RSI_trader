# 10 Strategy Evolution Comparison (ETHUSDT)

## 1) Purpose
- Compare three evolved strategies in one run with identical data and core parameters.
- Target set:
  - `02_baseline`: base strategy from `002_backtest_btcusdt.py`.
  - `04_long_only_with_trend_short_hedge_5x`: long-only + confirmed 4h trend short hedge 5x from `04_backtest_btcusdt_mode_compare.py`.
  - `08_best_hysteresis_fixed5x`: fixed-base5x + hysteresis best variant from `08_backtest_btcusdt_hysteresis_sweep.py` (band `0.50%`).

## 2) Common Test Setup
- Symbol: `ETHUSDT`
- Data period: `2022-01-01` to `2026-02-12`
- Initial capital: `1000 USDT`
- Commission: `0.04%` per side
- Entry scale: `0.50`
- Confirmation policy for hedge variants: closed 4h state only (`shift(1)`, no look-ahead)

## 3) Topline Performance

| Strategy | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `02_baseline` | 5670.0320 | 467.0032 | 52.4943 | 65.9247 | 0.7963 | 1980 | 843/1137 | 99.7475 | 6912.7612 |
| `04_long_only_with_trend_short_hedge_5x` | 5129.8017 | 412.9802 | 48.8262 | 62.9875 | 0.7752 | 318 | 203/115 | 71.6981 | 1.8544 |
| `08_best_hysteresis_fixed5x` | 3839.6961 | 283.9696 | 38.7033 | 83.7689 | 0.4620 | 275 | 203/72 | 80.7273 | 1.8884 |

## 4) Detailed Metrics

### `02_baseline`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `5670.0320 USDT`
- Total Return: `467.0032%`
- CAGR: `52.4943%`
- MDD: `65.9247%` (`3381.6506 USDT`)
- Calmar: `0.7963`
- Annual Volatility: `109.9441%`
- Sharpe(365): `0.9464`
- Sortino(365): `1.2477`
- Trades: `1980` (Long `843`, Short `1137`)
- Win Rate: `99.7475%` (Long `99.6441%`, Short `99.8241%`)
- Gross Profit / Gross Loss: `83267.5569` / `-12.0455`
- Net PnL Sum (trades): `83255.5114`
- Avg/Median PnL per trade: `42.0482` / `29.0439`
- Avg/Median Return per trade: `4.2048%` / `2.9044%`
- Avg/Median Holding: `13.0546h` / `4.6500h`
- Max Consecutive Wins/Losses: `779` / `1`
- Best/Worst Trade PnL: `229.3748` / `-4.0146`
- Best/Worst Trade Reason: `Take Profit` / `Reverse`
- Worst Month: `2025-12 (-35.4242%)`
- Max DD Episode: peak `2022-07-04 07:05:00`, trough `2022-07-16 16:14:00`, recovery `2023-04-05 19:21:00`, depth `65.9247%`, peak->trough `12.3812 days`
- PnL by side/reason:
- `LONG` / `Reverse`: trades=3, pnl_sum=-6.5143, pnl_avg=-2.1714
- `LONG` / `Take Profit`: trades=840, pnl_sum=38623.3925, pnl_avg=45.9802
- `SHORT` / `Reverse`: trades=2, pnl_sum=-5.5312, pnl_avg=-2.7656
- `SHORT` / `Take Profit`: trades=1135, pnl_sum=44644.1644, pnl_avg=39.3341

### `04_long_only_with_trend_short_hedge_5x`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `5129.8017 USDT`
- Total Return: `412.9802%`
- CAGR: `48.8262%`
- MDD: `62.9875%` (`4045.4868 USDT`)
- Calmar: `0.7752`
- Annual Volatility: `90.3300%`
- Sharpe(365): `0.8714`
- Sortino(365): `1.1139`
- Trades: `318` (Long `203`, Short `115`)
- Win Rate: `71.6981%` (Long `99.5074%`, Short `22.6087%`)
- Gross Profit / Gross Loss: `33933.3533` / `-18299.0247`
- Net PnL Sum (trades): `15634.3286`
- Avg/Median PnL per trade: `49.1646` / `24.0885`
- Avg/Median Return per trade: `4.9165%` / `2.4088%`
- Avg/Median Holding: `169.0358h` / `8.8833h`
- Max Consecutive Wins/Losses: `47` / `22`
- Best/Worst Trade PnL: `5211.3577` / `-11546.3598`
- Best/Worst Trade Reason: `Final Hedge Close` / `Final Close`
- Worst Month: `2025-01 (-42.5120%)`
- Max DD Episode: peak `2024-12-01 15:34:00`, trough `2025-05-06 21:30:00`, recovery `2025-06-11 15:30:00`, depth `62.9875%`, peak->trough `156.2472 days`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-11546.3598, pnl_avg=-11546.3598
- `LONG` / `Take Profit`: trades=202, pnl_sum=12890.7485, pnl_avg=63.8156
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=5211.3577, pnl_avg=5211.3577
- `SHORT` / `Hedge Close Trend Up`: trades=114, pnl_sum=9078.5821, pnl_avg=79.6367

### `08_best_hysteresis_fixed5x`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `3839.6961 USDT`
- Total Return: `283.9696%`
- CAGR: `38.7033%`
- MDD: `83.7689%` (`3333.9235 USDT`)
- Calmar: `0.4620`
- Annual Volatility: `108.0221%`
- Sharpe(365): `0.7581`
- Sortino(365): `1.0485`
- Trades: `275` (Long `203`, Short `72`)
- Win Rate: `80.7273%` (Long `99.5074%`, Short `27.7778%`)
- Gross Profit / Gross Loss: `25816.5668` / `-13671.3799`
- Net PnL Sum (trades): `12145.1869`
- Avg/Median PnL per trade: `44.1643` / `30.3090`
- Avg/Median Return per trade: `4.4164%` / `3.0309%`
- Avg/Median Holding: `195.6268h` / `11.2500h`
- Max Consecutive Wins/Losses: `49` / `9`
- Best/Worst Trade PnL: `3627.0659` / `-8036.1797`
- Best/Worst Trade Reason: `Final Hedge Close` / `Final Close`
- Worst Month: `2025-01 (-66.9313%)`
- Max DD Episode: peak `2024-03-10 16:31:00`, trough `2025-04-24 08:35:00`, recovery `2025-07-16 19:59:00`, depth `83.7689%`, peak->trough `409.6694 days`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-8036.1797, pnl_avg=-8036.1797
- `LONG` / `Take Profit`: trades=202, pnl_sum=10656.2612, pnl_avg=52.7538
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=3627.0659, pnl_avg=3627.0659
- `SHORT` / `Hedge Close Trend Up`: trades=71, pnl_sum=5898.0395, pnl_avg=83.0710

## 5) Comparative Interpretation
- Best Final Equity: `02_baseline` (`5670.0320 USDT`).
- Best Calmar: `02_baseline` (`0.7963`).
- Lowest MDD: `04_long_only_with_trend_short_hedge_5x` (`62.9875%`).
- Hysteresis best variant in this test uses a wider band to reduce unnecessary hedge flips.

## 6) Output Files
- script: `10_backtest_ethusdt_triple_compare.py`
- plot: `10_backtest_ethusdt_triple_compare.png`
- metrics: `10_backtest_ethusdt_triple_compare.csv`
- report: `10_backtest_ethusdt_triple_compare.md`