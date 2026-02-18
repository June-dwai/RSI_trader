# 09 Strategy Evolution Comparison

## 1) Purpose
- Compare three evolved strategies in one run with identical data and core parameters.
- Target set:
  - `02_baseline`: base strategy from `002_backtest_btcusdt.py`.
  - `04_long_only_with_trend_short_hedge_5x`: long-only + confirmed 4h trend short hedge 5x from `04_backtest_btcusdt_mode_compare.py`.
  - `08_best_hysteresis_fixed5x`: fixed-base5x + hysteresis best variant from `08_backtest_btcusdt_hysteresis_sweep.py` (band `0.50%`).

## 2) Common Test Setup
- Symbol: `BTCUSDT`
- Data period: `2022-01-01` to `2026-02-12`
- Initial capital: `1000 USDT`
- Commission: `0.04%` per side
- Entry scale: `0.50`
- Confirmation policy for hedge variants: closed 4h state only (`shift(1)`, no look-ahead)

## 3) Topline Performance

| Strategy | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `02_baseline` | 14968.8275 | 1396.8827 | 93.0977 | 64.0331 | 1.4539 | 1403 | 703/700 | 99.6436 | 4087.6954 |
| `04_long_only_with_trend_short_hedge_5x` | 20964.0793 | 1996.4079 | 109.5805 | 72.0598 | 1.5207 | 764 | 635/129 | 85.8639 | 2.6648 |
| `08_best_hysteresis_fixed5x` | 39367.8799 | 3836.7880 | 144.2867 | 67.8150 | 2.1277 | 701 | 635/66 | 92.8673 | 2.9320 |

## 4) Detailed Metrics

### `02_baseline`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `14968.8275 USDT`
- Total Return: `1396.8827%`
- CAGR: `93.0977%`
- MDD: `64.0331%` (`7816.6232 USDT`)
- Calmar: `1.4539`
- Annual Volatility: `90.6183%`
- Sharpe(365): `1.1963`
- Sortino(365): `1.4383`
- Trades: `1403` (Long `703`, Short `700`)
- Win Rate: `99.6436%` (Long `99.8578%`, Short `99.4286%`)
- Gross Profit / Gross Loss: `115682.6329` / `-28.3002`
- Net PnL Sum (trades): `115654.3327`
- Avg/Median PnL per trade: `82.4336` / `47.0376`
- Avg/Median Return per trade: `8.2434%` / `4.7038%`
- Avg/Median Holding: `18.6856h` / `7.5500h`
- Max Consecutive Wins/Losses: `547` / `1`
- Best/Worst Trade PnL: `508.4488` / `-9.9399`
- Best/Worst Trade Reason: `Take Profit` / `Reverse`
- Worst Month: `2022-03 (-31.8251%)`
- Max DD Episode: peak `2022-01-24 15:10:00`, trough `2022-04-21 13:34:00`, recovery `2022-09-06 13:55:00`, depth `64.0331%`, peak->trough `86.9333 days`
- PnL by side/reason:
- `LONG` / `Reverse`: trades=1, pnl_sum=-9.9399, pnl_avg=-9.9399
- `LONG` / `Take Profit`: trades=702, pnl_sum=58565.7752, pnl_avg=83.4270
- `SHORT` / `Reverse`: trades=4, pnl_sum=-18.3603, pnl_avg=-4.5901
- `SHORT` / `Final Close`: trades=1, pnl_sum=117.8676, pnl_avg=117.8676
- `SHORT` / `Take Profit`: trades=695, pnl_sum=56998.9901, pnl_avg=82.0129

### `04_long_only_with_trend_short_hedge_5x`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `20964.0793 USDT`
- Total Return: `1996.4079%`
- CAGR: `109.5805%`
- MDD: `72.0598%` (`21830.4651 USDT`)
- Calmar: `1.5207`
- Annual Volatility: `79.0330%`
- Sharpe(365): `1.3262`
- Sortino(365): `1.7654`
- Trades: `764` (Long `635`, Short `129`)
- Win Rate: `85.8639%` (Long `99.8425%`, Short `17.0543%`)
- Gross Profit / Gross Loss: `164682.0213` / `-61799.3097`
- Net PnL Sum (trades): `102882.7116`
- Avg/Median PnL per trade: `134.6632` / `105.1607`
- Avg/Median Return per trade: `13.4663%` / `10.5161%`
- Avg/Median Holding: `57.6146h` / `9.7500h`
- Max Consecutive Wins/Losses: `88` / `7`
- Best/Worst Trade PnL: `14238.8831` / `-14684.0879`
- Best/Worst Trade Reason: `Final Hedge Close` / `Final Close`
- Worst Month: `2024-12 (-41.5992%)`
- Max DD Episode: peak `2024-12-17 18:08:00`, trough `2025-04-17 14:38:00`, recovery `NaT`, depth `72.0598%`, peak->trough `120.8542 days`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-14684.0879, pnl_avg=-14684.0879
- `LONG` / `Take Profit`: trades=634, pnl_sum=126028.3117, pnl_avg=198.7828
- `SHORT` / `Hedge Close Trend Up`: trades=128, pnl_sum=-22700.3953, pnl_avg=-177.3468
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=14238.8831, pnl_avg=14238.8831

### `08_best_hysteresis_fixed5x`
- Period: `2022-01-01 03:20:00` ~ `2026-02-12 00:00:00`
- Final Equity: `39367.8799 USDT`
- Total Return: `3836.7880%`
- CAGR: `144.2867%`
- MDD: `67.8150%` (`29357.2462 USDT`)
- Calmar: `2.1277`
- Annual Volatility: `77.5927%`
- Sharpe(365): `1.5350`
- Sortino(365): `2.0065`
- Trades: `701` (Long `635`, Short `66`)
- Win Rate: `92.8673%` (Long `99.8425%`, Short `25.7576%`)
- Gross Profit / Gross Loss: `222083.5197` / `-75745.8498`
- Net PnL Sum (trades): `146337.6699`
- Avg/Median PnL per trade: `208.7556` / `134.6752`
- Avg/Median Return per trade: `20.8756%` / `13.4675%`
- Avg/Median Holding: `62.6555h` / `10.2833h`
- Max Consecutive Wins/Losses: `90` / `5`
- Best/Worst Trade PnL: `26738.8150` / `-27574.8531`
- Best/Worst Trade Reason: `Final Hedge Close` / `Final Close`
- Worst Month: `2024-12 (-39.2188%)`
- Max DD Episode: peak `2024-12-17 18:08:00`, trough `2025-04-16 17:59:00`, recovery `2025-11-18 03:34:00`, depth `67.8150%`, peak->trough `119.9938 days`
- PnL by side/reason:
- `LONG` / `Final Close`: trades=1, pnl_sum=-27574.8531, pnl_avg=-27574.8531
- `LONG` / `Take Profit`: trades=634, pnl_sum=162387.2201, pnl_avg=256.1313
- `SHORT` / `Hedge Close Trend Up`: trades=65, pnl_sum=-15213.5121, pnl_avg=-234.0540
- `SHORT` / `Final Hedge Close`: trades=1, pnl_sum=26738.8150, pnl_avg=26738.8150

## 5) Comparative Interpretation
- Best Final Equity: `08_best_hysteresis_fixed5x` (`39367.8799 USDT`).
- Best Calmar: `08_best_hysteresis_fixed5x` (`2.1277`).
- Lowest MDD: `02_baseline` (`64.0331%`).
- Hysteresis best variant in this test uses a wider band to reduce unnecessary hedge flips.

## 6) Output Files
- script: `09_backtest_btcusdt_triple_compare.py`
- plot: `09_backtest_btcusdt_triple_compare.png`
- metrics: `09_backtest_btcusdt_triple_compare.csv`
- report: `09_backtest_btcusdt_triple_compare.md`