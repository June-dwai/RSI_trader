# Study 141: row6 whipsaw-guard trials

- Base engine: `lb4_delay8_capna_cd0` with the 138 improvements.
- Analysis window: `2021-01-02 00:00:00` ~ `2026-03-15 05:19:00`.
- This study targets the remaining weakness identified in Study 140: long, costly two-way whipsaw periods.
- Note: the inherited `slow_bear_bars=1440` setting is on 15-minute bars, so it means about 15 days, not 24 hours.

## Variant Table
| Variant | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Whipsaw Avg Return % | Whipsaw Avg MDD % | Chop Downshift | Chop Cooldown Blocks | Chop Delay Blocks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| combo_base | 180.7641 | 63.9784 | 2.8254 | 19.1725 | 44.9550 | -50.4013 | 50.4013 | 0 | 0 | 0 |
| combo_chopcool8_x6 | 173.0870 | 63.9784 | 2.7054 | 19.1725 | 44.9550 | -50.4013 | 50.4013 | 0 | 878 | 0 |
| combo_chopdelay24_x6 | 170.3293 | 64.3629 | 2.6464 | 12.3338 | 48.1407 | -50.7119 | 50.7119 | 0 | 63 | 45 |
| combo_choplev2_x6 | 158.7285 | 64.7476 | 2.4515 | 41.0079 | 35.0738 | -48.2638 | 48.2638 | 112 | 67 | 0 |
| combo_choppack_x6 | 146.5681 | 67.2489 | 2.1795 | 34.1653 | 38.2776 | -48.6448 | 48.6448 | 112 | 893 | 43 |
| unlock_choppack_x6 | 132.0048 | 67.7400 | 1.9487 | 28.6836 | 40.8236 | -49.2366 | 49.2366 | 111 | 883 | 43 |

- `combo_base`: CAGR `180.7641%`, MDD `63.9784%`, whipsaw avg return `-50.4013%`.
- Best practical balance: `combo_base`.
- Best whipsaw-window protection: `combo_choplev2_x6`.

## What Was Tested
- `combo_base`: Study 138 practical base (`combo_trim2p0_unlock24h`).
- `combo_choplev2_x6`: if the last 64 bars have at least 6 EMA20 crosses, downshift new entries to 2.0x.
- `combo_chopcool8_x6`: in the same chop state, block fresh entries for 8 bars after the last exit.
- `combo_chopdelay24_x6`: in chop, require a longer bullish confirmation delay (`24` bars) before long re-entry.
- `combo_choppack_x6`: combine downshift + cooldown + longer bullish delay.
- `unlock_choppack_x6`: apply the same guard pack to the raw 206% engine without bull trim.

## Whipsaw Windows Used
- `2022-07-05 13:00:00` -> `2022-11-08 05:30:00`
- `2024-07-08 01:15:00` -> `2024-10-13 15:30:00`
- `2024-12-17 15:00:00` -> `2025-02-21 13:45:00`
- `2025-07-14 07:45:00` -> `2025-10-13 20:00:00`

## Practical Read
- A good whipsaw guard should improve the whipsaw-window average loss first, then try to preserve CAGR.
- If a variant improves whipsaw windows but destroys CAGR too much, it is over-filtering.
- If a variant preserves CAGR but whipsaw-window losses stay large, it is not solving the real bottleneck.

## Outputs
- Plot: `141_backtest_btcusdt_row6_whipsaw_guard_trials.png`
- Metrics CSV: `141_backtest_btcusdt_row6_whipsaw_guard_trials.csv`
- Curves CSV: `141_backtest_btcusdt_row6_whipsaw_guard_trials_curves.csv`
- Whipsaw Windows CSV: `141_backtest_btcusdt_row6_whipsaw_guard_trials_whipsaw_windows.csv`
- Report: `141_backtest_btcusdt_row6_whipsaw_guard_trials.md`
