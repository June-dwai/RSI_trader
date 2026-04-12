# Study 76: Regime-Hold Leverage Sweep With Liquidation Model

## Model
- Base signal is the study-73 `dual_stop6` idea: confirmed 4h trend decides long versus short.
- Start capital: `1000` USDT
- Margin posted per trade: `98.0%` of wallet
- Margin mode assumption: `isolated`, no auto-add
- Maintenance margin rate assumption: `0.50%`
- Stop loss: `6.0%` from entry
- Liquidation check uses bar extremes (`low` for long, `high` for short) before stop-loss, which is intentionally conservative.

## Ranking

| Variant | CAGR % | MDD % | Calmar | Final Equity | Liquidations | First Liq | Trades |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| lev_1x | 28.8257 | 37.2472 | 0.7739 | 2896.9742 | 0 | N/A | 140 |
| lev_1.5x | 35.9322 | 49.8715 | 0.7205 | 3629.7345 | 0 | N/A | 140 |
| lev_2x | 38.4140 | 59.8575 | 0.6418 | 3916.2700 | 0 | N/A | 140 |
| lev_2.5x | 36.7667 | 67.8295 | 0.5420 | 3724.2300 | 0 | N/A | 140 |
| lev_3x | 31.6374 | 74.2340 | 0.4262 | 3171.9204 | 0 | N/A | 140 |
| lev_4x | 13.8551 | 84.6980 | 0.1636 | 1724.4388 | 0 | N/A | 140 |
| lev_5x | -9.1953 | 93.0176 | -0.0989 | 666.9297 | 0 | N/A | 140 |

## Best Variant
- `lev_1x`: CAGR `28.8257%`, MDD `37.2472%`, Calmar `0.7739`

## Delta vs 1x
- `lev_1.5x`: CAGR `7.1066pp`, MDD `12.6243pp`, Calmar `-0.0534`, liquidations `0`
- `lev_2x`: CAGR `9.5884pp`, MDD `22.6103pp`, Calmar `-0.1321`, liquidations `0`
- `lev_2.5x`: CAGR `7.9410pp`, MDD `30.5822pp`, Calmar `-0.2319`, liquidations `0`
- `lev_3x`: CAGR `2.8118pp`, MDD `36.9868pp`, Calmar `-0.3477`, liquidations `0`
- `lev_4x`: CAGR `-14.9705pp`, MDD `47.4507pp`, Calmar `-0.6103`, liquidations `0`
- `lev_5x`: CAGR `-38.0209pp`, MDD `55.7704pp`, Calmar `-0.8728`, liquidations `0`

## Interpretation
- If leverage improves CAGR faster than it increases MDD without triggering many liquidations, then regime-hold may support modest leverage as a sleeve.
- If high-leverage variants suffer frequent liquidations, they are not suitable as case3 diversifiers even if their CAGR looks attractive.
- This study is still a simplified margin model; funding, slippage, and Binance risk-tier changes are not included.

## Outputs
- Plot: `76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.png`
- Metrics CSV: `76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.csv`
- Curves CSV: `76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep_curves.csv`
- Report: `76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.md`