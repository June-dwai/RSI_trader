# Study 132: ETHUSDT 129 red-line case3 drawdown check + seed vault overlay

## Assumption
- Base strategy is the existing red line: `lb4_delay9_capna_cd0_only` from study 129.
- Starting seed: `2000` USDT.
- Overlay rule: when active equity reaches `2.0x seed` (`4000`), withdraw `2000` into a vault.
- Refill rule: when active equity falls to `0.5x seed` (`1000`) or lower, deposit from the vault only enough to restore active equity back to `2000`.
- Deposits are funded only from prior withdrawals; no outside capital is added.

## Why The Red Line Whipsaws So Hard
- It is a `3.0x` leverage regime-hold engine with `98%` of wallet posted as margin on each new position.
- Effective full-wallet notional per new trade is about `2.94x` wallet (`0.98 * 3.0`).
- Profits are not skimmed out, so every big gain gets recycled into the next trade size.
- This ETH run had `0` liquidations, so the giant drawdown is not a margin-call story; it is a compounding give-back story.
- Trade stats on the matched window: trades `159`, longs `84`, shorts `75`, stops `30`, signal exits `101`, short TP exits `27`.
- Side mix by bar: long `45.64%`, short `12.14%`, flat `42.22%`.
- Peak-to-trough on the raw curve: `2024-03-12 00:15:00` `124248.9240` -> `2024-11-06 15:00:00` `8895.4442` (`-92.8406%`).
- Worst raw months were:
  - `2024-10`: `-54.2266%` (`24359.3724` -> `11150.1041`)
  - `2026-03`: `-48.8139%` (`69052.8979` -> `35345.4661`)
  - `2024-04`: `-45.4973%` (`65107.3115` -> `35485.2498`)
  - `2025-06`: `-39.4419%` (`50656.2869` -> `30676.4939`)
  - `2024-01`: `-35.1213%` (`65497.6864` -> `42494.0683`)
  - `2022-04`: `-26.9815%` (`46453.9727` -> `33919.9985`)
  - `2024-03`: `-25.4866%` (`87539.9258` -> `65228.9918`)
  - `2022-08`: `-23.9412%` (`62254.3120` -> `47349.8691`)

## Results
| Variant | Final Equity | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Peak Equity | Post-Peak Trough | Post-Peak Drop % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| raw_case3 | 27038.1842 | 63.8550 | 92.8406 | 0.6878 | -57.9510 | 64.4957 | 124248.9240 | 8895.4442 | -92.8406 |
| seed_vault_overlay | 17904.7844 | 51.5356 | 31.8147 | 1.6199 | -6.3060 | 8.8940 | 20170.6647 | 17750.3772 | -11.9990 |

## Overlay Event Summary
- Withdrawals: `12` events, cumulative `24000.0000`.
- Deposits: `8` events, cumulative `8054.4879`.
- Final split: active `1959.2723`, vault `15945.5121`, total `17904.7844`.
- First withdrawals:
  - `2021-01-04 05:30:00` withdraw `2000.0000` -> active `2177.4712`, vault `2000.0000`
  - `2021-02-02 21:00:00` withdraw `2000.0000` -> active `2021.2154`, vault `4000.0000`
  - `2021-05-03 17:15:00` withdraw `2000.0000` -> active `2011.7875`, vault `6000.0000`
  - `2021-08-06 17:30:00` withdraw `2000.0000` -> active `2020.7541`, vault `8000.0000`
  - `2021-10-21 09:45:00` withdraw `2000.0000` -> active `2027.6244`, vault `10000.0000`
- First deposits:
  - `2021-12-09 15:30:00` deposit `1019.9077` -> active `2000.0000`, vault `8980.0923`
  - `2022-11-02 19:30:00` deposit `1013.9280` -> active `2000.0000`, vault `9966.1643`
  - `2024-03-24 23:00:00` deposit `1000.6615` -> active `2000.0000`, vault `12965.5028`
  - `2024-05-10 07:00:00` deposit `1000.8215` -> active `2000.0000`, vault `11964.6812`
  - `2024-10-23 16:15:00` deposit `1007.8030` -> active `2000.0000`, vault `10956.8783`

## Interpretation
- Raw red line finished higher (`27038.1842`) but with extreme MDD `92.8406%` and a post-peak collapse of `-92.8406%`.
- The seed-vault overlay finished lower (`17904.7844`) but cut MDD to `31.8147%` and reduced the post-peak drop to `-11.9990%`.
- In 2026 the overlay changed return from `-57.9510%` to `-6.3060%` and MDD from `64.4957%` to `8.8940%`.

## Outputs
- Plot: `132_backtest_ethusdt_case3_seed_vault_overlay.png`
- Metrics CSV: `132_backtest_ethusdt_case3_seed_vault_overlay.csv`
- Events CSV: `132_backtest_ethusdt_case3_seed_vault_overlay_events.csv`
- Curves CSV: `132_backtest_ethusdt_case3_seed_vault_overlay_curves.csv`
- Report: `132_backtest_ethusdt_case3_seed_vault_overlay.md`