# Study 82: ICT/SMC-Inspired Archetypes

## Scope
- This study is not a canonical ICT/SMC implementation. It uses machine-testable proxies inspired by common SMC ideas.
- Execution timeframe: `15m` bars rebuilt from `1m` data.
- Context timeframes: `1h` liquidity pools and `4h` confirmed EMA200 hysteresis bias.
- All entries are based on information available at the current completed bar; no future bars are read.

## Archetypes
- `smc_sweep8h_reversal_15m`: sweep of the previous 8h liquidity pool, reclaim, trade back in 4h bias direction.
- `smc_sweep24h_reversal_15m`: same idea using a wider 24h liquidity pool.
- `smc_fvg_reclaim_15m`: displacement + break of structure + fair value gap, then wait for gap reclaim.
- `smc_orderblock_reclaim_15m`: displacement + break of structure, then revisit the last opposite candle zone as an order block proxy.
- References are the current regime-hold case3 winners from study 80.

## Ranking

| Variant | CAGR % | MDD % | Calmar | Final Equity | Trades | Setup Created | Setup Triggered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| reference_shorttp15_2x | 67.5300 | 50.8583 | 1.3278 | 8730.8307 | N/A | N/A | N/A |
| reference_shorttp15_15x | 54.2930 | 41.7230 | 1.3013 | 6179.3410 | N/A | N/A | N/A |
| smc_sweep24h_reversal_15m | -2.6080 | 12.5487 | -0.2078 | 894.9587 | 66 | 0 | 0 |
| smc_sweep8h_reversal_15m | -7.7467 | 31.9984 | -0.2421 | 712.7525 | 237 | 0 | 0 |
| smc_fvg_reclaim_15m | -15.4893 | 51.3140 | -0.3019 | 493.2421 | 547 | 1165 | 547 |
| smc_orderblock_reclaim_15m | -19.8233 | 62.4585 | -0.3174 | 395.4048 | 1143 | 2102 | 1143 |

## Best Live Variant
- `smc_sweep24h_reversal_15m`: CAGR `-2.6080%`, MDD `12.5487%`, Calmar `-0.2078`

## Interpretation
- If a sweep-reversal variant wins, then the SMC idea that matters here is liquidity-taking plus reclaim, not continuation chasing.
- If FVG or order-block reclaim wins, then delayed pullback entries after displacement are the more machine-tractable edge.
- If none of the SMC-inspired variants beat the regime-hold references, then this concept remains ideation rather than portfolio-ready.

## Outputs
- Plot: `82_backtest_btcusdt_scale06_adx002_ict_smc_archetypes.png`
- Metrics CSV: `82_backtest_btcusdt_scale06_adx002_ict_smc_archetypes.csv`
- Curves CSV: `82_backtest_btcusdt_scale06_adx002_ict_smc_archetypes_curves.csv`
- Report: `82_backtest_btcusdt_scale06_adx002_ict_smc_archetypes.md`