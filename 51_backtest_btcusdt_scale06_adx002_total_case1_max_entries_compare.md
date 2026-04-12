# 51 Backtest: Total Portfolio with Case1 Max Entries Sweep

## Setup
- Total portfolio = `case1` from study-49 variant + fixed `case2` from study-42.
- `case1` uses matched hedge size (`hedge_multiple = max_entries`).
- `case2` is fixed as study-42 case2 (`dual-direction, no hedge/no hysteresis, ADX002, scale0.60, prev-touch-only, max_entries=4`).
- Capital allocation: `1000 USDT` each, total start `2000 USDT`.

## Results

| Case1 Max Entries | Total Final Equity | Total Return % | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 24865.6384 | 1143.2819 | 84.5102 | 49.0016 | 1.7246 | 65.2813 | 52.6137 |
| 4 | 35703.7284 | 1685.1864 | 101.4674 | 50.3387 | 2.0157 | 103.9256 | 64.8802 |
| 5 | 45585.3515 | 2179.2676 | 113.7931 | 64.7393 | 1.7577 | 126.0528 | 76.8389 |
| 6 | 22916.0238 | 1045.8012 | 80.8848 | 59.3523 | 1.3628 | 54.2675 | 85.4925 |

## Best Cases
- Best total CAGR: `max_entries=5` (`113.7931%`).
- Lowest total MDD: `max_entries=3` (`49.0016%`).
- Best total Calmar: `max_entries=4` (`2.0157`).

## Delta vs max_entries=5
| Max Entries | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---:|---:|---:|---:|---:|
| 3 | -20719.7131 | -29.2830 | -15.7377 | -0.0331 |
| 4 | -9881.6231 | -12.3258 | -14.4005 | 0.2580 |
| 5 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 6 | -22669.3278 | -32.9083 | -5.3870 | -0.3949 |

## Interpretation
- `max_entries=5` still gives the highest total CAGR, but the drawdown cost is large.
- `max_entries=4` is the best risk-adjusted total portfolio in this sweep because it materially lowers total MDD while keeping CAGR above 100%.
- This makes `max_entries=4` the natural baseline for the next hedge-close experiment.

## Outputs
- Plot: `51_backtest_btcusdt_scale06_adx002_total_case1_max_entries_compare.png`
- Metrics CSV: `51_backtest_btcusdt_scale06_adx002_total_case1_max_entries_compare.csv`
- Curves CSV: `51_backtest_btcusdt_scale06_adx002_total_case1_max_entries_compare_curves.csv`
- Report: `51_backtest_btcusdt_scale06_adx002_total_case1_max_entries_compare.md`