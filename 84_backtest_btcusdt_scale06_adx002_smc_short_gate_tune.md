# Study 84: Short-Side Sweep Gate Tuning

## Scope
- Focus only on the promising idea from study 83: `short-side liquidity sweep gate` on the 15m regime-hold + short-TP engine.
- Leverage is fixed at `2x` because that was the strongest configuration in study 83.
- Search dimensions: sweep lookback hours, gate duration bars, short TP threshold, and body-strength filter.

## Ranking

| Variant | CAGR % | MDD % | Calmar | Final Equity | TP Exits | Short Sweeps | Gated Entries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| short_gate_24h_g12_tp15 | 98.7654 | 48.4494 | 2.0385 | 17902.1759 | 20 | 630 | 53 |
| short_gate_24h_g12_tp10 | 80.3649 | 40.7166 | 1.9738 | 11905.0145 | 23 | 630 | 53 |
| short_gate_24h_g8_tp15_body20 | 85.7116 | 48.4494 | 1.7691 | 13458.9311 | 20 | 666 | 52 |
| reference_short_gate24h_shorttp15_2x | 85.5152 | 48.4494 | 1.7650 | 13399.2438 | N/A | N/A | N/A |
| short_gate_24h_g8_tp15 | 85.5152 | 48.4494 | 1.7650 | 13399.2438 | 20 | 630 | 51 |
| short_gate_24h_g8_tp15_body25 | 85.5152 | 48.4494 | 1.7650 | 13399.2438 | 20 | 630 | 51 |
| short_gate_24h_g8_tp15_body10 | 85.4006 | 48.4494 | 1.7627 | 13364.5311 | 20 | 731 | 53 |
| short_gate_24h_g8_tp15_body35 | 82.1128 | 48.4494 | 1.6948 | 12397.0982 | 20 | 551 | 51 |
| short_gate_36h_g12_tp15 | 80.1389 | 50.6362 | 1.5826 | 11842.4971 | 17 | 478 | 46 |
| short_gate_12h_g8_tp15 | 85.2267 | 56.4188 | 1.5106 | 13311.9572 | 20 | 1074 | 58 |
| base15m_shorttp15_2x | 76.3005 | 51.5201 | 1.4810 | 10818.3586 | 19 | 0 | 0 |
| short_gate_12h_g4_tp10 | 68.8981 | 49.2477 | 1.3990 | 9034.9997 | 24 | 1074 | 53 |
| short_gate_12h_g8_tp10 | 67.1850 | 49.0506 | 1.3697 | 8656.3501 | 24 | 1074 | 58 |
| short_gate_12h_g8_tp20 | 72.8012 | 54.2546 | 1.3418 | 9944.7993 | 14 | 1074 | 58 |
| short_gate_36h_g12_tp10 | 67.3733 | 50.4873 | 1.3345 | 8697.3711 | 20 | 478 | 46 |
| reference_shorttp15_2x | 67.5300 | 50.8583 | 1.3278 | 8730.8307 | N/A | N/A | N/A |
| short_gate_36h_g8_tp15 | 70.4149 | 53.4763 | 1.3167 | 9380.6684 | 17 | 478 | 46 |
| short_gate_12h_g12_tp15 | 80.1888 | 61.6144 | 1.3015 | 11856.2980 | 20 | 1074 | 62 |
| short_gate_24h_g8_tp10 | 61.8479 | 48.3710 | 1.2786 | 7553.7363 | 22 | 630 | 51 |
| short_gate_12h_g4_tp20 | 67.4776 | 53.7400 | 1.2556 | 8720.1449 | 14 | 1074 | 53 |
| short_gate_12h_g4_tp15 | 68.7438 | 57.1464 | 1.2029 | 9000.3887 | 18 | 1074 | 53 |
| short_gate_12h_g12_tp20 | 67.0708 | 57.0900 | 1.1748 | 8631.5421 | 14 | 1074 | 62 |
| short_gate_36h_g12_tp20 | 65.0093 | 56.6797 | 1.1470 | 8193.0133 | 11 | 478 | 46 |
| short_gate_12h_g12_tp10 | 62.9205 | 55.0772 | 1.1424 | 7766.2024 | 24 | 1074 | 62 |
| short_gate_24h_g12_tp20 | 68.3394 | 61.1246 | 1.1180 | 8910.1418 | 13 | 630 | 54 |
| short_gate_36h_g4_tp15 | 59.2433 | 53.3700 | 1.1100 | 7056.2141 | 15 | 478 | 41 |
| short_gate_36h_g4_tp20 | 63.5753 | 58.6240 | 1.0845 | 7898.1282 | 12 | 478 | 41 |
| short_gate_24h_g4_tp10 | 52.5352 | 50.2671 | 1.0451 | 5889.4737 | 21 | 630 | 47 |
| short_gate_24h_g4_tp20 | 59.3991 | 59.9691 | 0.9905 | 7085.2465 | 14 | 630 | 47 |
| short_gate_36h_g8_tp20 | 56.6771 | 59.1721 | 0.9578 | 6590.8488 | 11 | 478 | 46 |
| short_gate_24h_g8_tp15_body50 | 62.2092 | 65.7640 | 0.9459 | 7624.8030 | 18 | 440 | 51 |
| short_gate_36h_g8_tp10 | 52.4986 | 55.8966 | 0.9392 | 5883.5395 | 19 | 478 | 46 |
| short_gate_24h_g8_tp20 | 57.8237 | 61.9892 | 0.9328 | 6795.7831 | 13 | 630 | 52 |
| short_gate_24h_g4_tp15 | 54.2939 | 58.5758 | 0.9269 | 6179.9591 | 17 | 630 | 47 |
| short_gate_36h_g4_tp10 | 46.0021 | 49.6513 | 0.9265 | 4900.4810 | 17 | 478 | 41 |

## Best Live Variant
- `short_gate_24h_g12_tp15`: CAGR `98.7654%`, MDD `48.4494%`, Calmar `2.0385`

## Delta vs References
- vs study-80 `short_tp15_lock_2x`: CAGR `31.2355pp`, MDD `-2.4089pp`, Calmar `0.7107`
- vs study-83 `short_gate24h_shorttp15_2x`: CAGR `13.2503pp`, MDD `-0.0000pp`, Calmar `0.2735`

## Interpretation
- If lower TP thresholds dominate, the short edge needs faster monetization once the sweep-confirmed move starts working.
- If longer lookback windows dominate, the market is respecting larger liquidity pools rather than intraday ones.
- If very short gate windows dominate, the sweep timing edge decays quickly and should be used only as a narrow entry window.

## Outputs
- Plot: `84_backtest_btcusdt_scale06_adx002_smc_short_gate_tune.png`
- Metrics CSV: `84_backtest_btcusdt_scale06_adx002_smc_short_gate_tune.csv`
- Curves CSV: `84_backtest_btcusdt_scale06_adx002_smc_short_gate_tune_curves.csv`
- Report: `84_backtest_btcusdt_scale06_adx002_smc_short_gate_tune.md`