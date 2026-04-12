# Study 133: ETHUSDT case3 fixed-seed overlay vs multiplier ladder overlay

## Interpretation Of The User Rule
- Previous study 132 assumed a fixed `2000 USDT` seed forever.
- New ladder interpretation uses multiplier levels: `4k -> 8k -> 16k -> 32k -> 64k -> 128k ...`.
- When active equity reaches a ladder level `T`, the system skims it down to `T/2`, sends the rest to the vault, and the new refill seed becomes `T/2`.
- When active equity later falls to half of that seed, it refills back to the current seed from the vault.

## Results
| Variant | Final Equity | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Peak Equity | Post-Peak Trough | Post-Peak Drop % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| raw_case3 | 27038.1842 | 63.8550 | 92.8406 | 0.6878 | -57.9510 | 64.4957 | 124248.9240 | 8895.4442 | -92.8406 |
| fixed_seed_overlay | 17904.7844 | 51.5356 | 31.8147 | 1.6199 | -6.3060 | 8.8940 | 20170.6647 | 17750.3772 | -11.9990 |
| multiplier_ladder_overlay | 48690.7433 | 83.1909 | 71.6547 | 1.1610 | -30.1123 | 35.7308 | 98325.4856 | 46610.5969 | -52.5956 |

## Why The New Ladder Matches Better
- Fixed-seed overlay only withdrew `24000.0000` in total because it kept resetting the operating seed back to `2000`.
- Multiplier ladder withdrew `62441.2364` in total and refilled `40145.4599`.
- Under the ladder, the last active seed reached `32000.0000` and the next withdrawal ladder became `128000.0000`.
- At the ladder wealth peak, active was `60017.5531` and vault was `38307.9325`.

## Takeaways
- Raw red line has the highest terminal equity of the un-managed sleeve (`27038.1842`) but catastrophic MDD `92.8406%`.
- Fixed seed overlay cut MDD hardest (`31.8147%`) but also suppressed the upside too much.
- Multiplier ladder sits in the middle: final wealth `48690.7433`, CAGR `83.1909%`, MDD `71.6547%`.

## Outputs
- Plot: `133_backtest_ethusdt_case3_seed_ladder_overlay.png`
- Metrics CSV: `133_backtest_ethusdt_case3_seed_ladder_overlay.csv`
- Events CSV: `133_backtest_ethusdt_case3_seed_ladder_overlay_events.csv`
- Curves CSV: `133_backtest_ethusdt_case3_seed_ladder_overlay_curves.csv`
- Report: `133_backtest_ethusdt_case3_seed_ladder_overlay.md`