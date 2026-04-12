# Study 114: Current Best + SR / SMC Filters

## Setup
- Baseline is the current best near-90 CAGR family: `short_gate24h_shorttp15_2x` from study 83.
- Backtest period is `2021-01-02` to `2026-03-15` using local BTCUSDT caches.
- Engine remains the same 15m regime-hold + 24h short sweep gate + short TP lock 15%.
- SR filters are layered directly onto the current-best engine rather than compared against unrelated studies.
- Important assumption: the current-best engine has no DCA/add logic, so the SR rule is applied to all openings and direction flips.
- SMC stack filter counts active internal order blocks on 15m bars and blocks longs when bearish boxes fully above price reach `5`, blocks shorts when bullish boxes fully below price reach `5`.

## Baseline
- `baseline_short_gate24h_shorttp15_2x_2021plus`: CAGR `102.9351%`, MDD `62.1257%`, Calmar `1.6569`, Final Equity `39569.0574`

## Best Variant
- `baseline_short_gate24h_shorttp15_2x_smc5_2021plus`: CAGR `95.0432%`, MDD `52.3536%`, Calmar `1.8154`, Final Equity `32198.0501`
- Delta vs baseline: CAGR `-7.8919pp`, MDD `-9.7721pp`, Calmar `0.1585`

## Ranking

| Variant | SR Mode | SMC Filter | CAGR % | MDD % | Calmar | Delta Calmar | Trades | Blocked by SMC | Flat Due SR |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_short_gate24h_shorttp15_2x_smc5_2021plus | none | opp5 | 95.0432 | 52.3536 | 1.8154 | 0.1585 | 109 | 3911 | 0 |
| baseline_short_gate24h_shorttp15_2x_2021plus | none | none | 102.9351 | 62.1257 | 1.6569 | 0.0000 | 145 | 0 | 0 |
| redavg_align_smc5_2021plus | redavg_align | opp5 | 16.8122 | 54.0577 | 0.3110 | -1.3459 | 1091 | 13828 | 64584 |
| redfloor_align_smc5_2021plus | redfloor_align | opp5 | 13.2548 | 54.6230 | 0.2427 | -1.4142 | 1017 | 13077 | 64788 |
| redavg_align_2021plus | redavg_align | none | -25.1433 | 88.6349 | -0.2837 | -1.9406 | 2800 | 0 | 64584 |
| redfloor_align_2021plus | redfloor_align | none | -26.0094 | 88.7285 | -0.2931 | -1.9500 | 2643 | 0 | 64788 |
| band_switch_smc5_2021plus | band_switch | opp5 | -44.6821 | 97.7942 | -0.4569 | -2.1138 | 2280 | 27777 | 29006 |
| band_switch_2021plus | band_switch | none | -86.6115 | 99.9983 | -0.8661 | -2.5230 | 6667 | 0 | 29006 |

## Interpretation
- At least one SR / SMC filtered variant improved on the current-best baseline.
- `redavg_align` is the most direct test of 'long only above SR / short only below SR' while keeping the 4h trend-follow logic.
- `band_switch` is the stronger test of 'if price is below the SR band, only short side is allowed'.
- If SMC-5 variants barely differ from their no-SMC twins, then the active 5-box stack condition is too rare or too loose on this engine.

## Outputs
- Plot: `114_backtest_btcusdt_best_with_sr_smc_filters.png`
- Metrics CSV: `114_backtest_btcusdt_best_with_sr_smc_filters.csv`
- Curves CSV: `114_backtest_btcusdt_best_with_sr_smc_filters_curves.csv`
- Report: `114_backtest_btcusdt_best_with_sr_smc_filters.md`