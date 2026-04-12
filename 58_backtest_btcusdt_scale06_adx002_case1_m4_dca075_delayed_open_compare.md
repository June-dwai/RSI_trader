# 58 Backtest: DCA 0.75% with Delayed Initial Open Variants

## Setup
- `case1` keeps study-56 best add spacing: `max_entries=4`, matched hedge size, `dca_drop=0.75%`.
- `case2` stays fixed as study-42 case2 curve.
- Variant idea: when the first long signal appears, do not buy immediately; place a lower delayed-open anchor and allow a fallback market open only after the wait window expires.

## Results

| Variant | Open Delay % | Wait Bars | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | Limit Fill | Fallback Open | Pending Cancel |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `open_now_dca0p75` | 0.0000 | 0 | 38126.1140 | 104.7073 | 52.2416 | 2.0043 | 110.0459 | 52.7733 | 0 | 0 | 0 |
| `delay0p25_wait240` | 0.2500 | 240 | 34152.7017 | 99.3044 | 50.5531 | 1.9644 | 99.6847 | 58.8796 | 416 | 104 | 0 |
| `delay0p10_wait30` | 0.1000 | 30 | 29991.6211 | 93.1095 | 52.1955 | 1.7839 | 86.6638 | 67.8353 | 381 | 138 | 0 |
| `delay0p15_wait60` | 0.1500 | 60 | 29341.2847 | 92.0833 | 52.2784 | 1.7614 | 84.3527 | 67.0162 | 356 | 143 | 0 |
| `delay0p20_wait120` | 0.2000 | 120 | 27049.0959 | 88.3233 | 52.7069 | 1.6757 | 75.3915 | 60.4371 | 386 | 125 | 0 |

## Best Cases
- Best total CAGR: `open_now_dca0p75` (`104.7073%`).
- Lowest total MDD: `delay0p25_wait240` (`50.5531%`).
- Best total Calmar: `open_now_dca0p75` (`2.0043`).

## Delta vs open_now_dca0p75
| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |
|---|---:|---:|---:|---:|
| `open_now_dca0p75` | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `delay0p25_wait240` | -3973.4122 | -5.4029 | -1.6885 | -0.0399 |
| `delay0p10_wait30` | -8134.4928 | -11.5979 | -0.0461 | -0.2204 |
| `delay0p15_wait60` | -8784.8293 | -12.6240 | 0.0368 | -0.2429 |
| `delay0p20_wait120` | -11077.0180 | -16.3841 | 0.4652 | -0.3285 |

## Dominance Check
- No tested delayed-open variant achieved both `higher total CAGR` and `lower total MDD` than `open_now_dca0p75`.

## Interpretation
- If a variant helps, it means the first fill itself was too early and a shallow patience rule improves average entry quality.
- Strong delayed-open rules can easily miss rebounds, so the key tradeoff is limit-fill quality versus fallback-chase cost.
- The key metric is whether delayed initial entry can keep the study-56 CAGR edge while pulling MDD back down.

## Outputs
- Plot: `58_backtest_btcusdt_scale06_adx002_case1_m4_dca075_delayed_open_compare.png`
- Metrics CSV: `58_backtest_btcusdt_scale06_adx002_case1_m4_dca075_delayed_open_compare.csv`
- Curves CSV: `58_backtest_btcusdt_scale06_adx002_case1_m4_dca075_delayed_open_compare_curves.csv`
- Report: `58_backtest_btcusdt_scale06_adx002_case1_m4_dca075_delayed_open_compare.md`