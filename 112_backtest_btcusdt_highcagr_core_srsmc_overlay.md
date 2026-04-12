# Study 112: High-CAGR Core + SR/SMC Overlay

## Setup
- Core engine is the study-85 leader: `short_gate_24h_g12_tp15_case3_w62_31_7`.
- Overlay candidates come from study 111 (`proxy_winner`, `exact_winner`) plus reference long sleeves (`gap_12`, `buy_hold`).
- All curves are aligned to a common hourly period and rebalanced fee-aware.
- Ranking priority is `CAGR >= 100%` first, then higher Calmar, then higher CAGR, then lower MDD.

## Winner
- Best live overlay under the CAGR floor: `buy_hold_reference_w6_rb4h` -> CAGR `115.0422%`, MDD `41.6316%`, Calmar `2.7633`, overlay `buy_hold_reference` at `6.00%`, rebalance `4h`.
- Delta vs core85-only: CAGR `-5.5941pp`, MDD `-2.2242pp`, Calmar `0.0126`.
- Raw CAGR champion regardless of overlay requirement: `core85_only` with `120.6364%` CAGR.

## Candidate Comparison
- Best study111 overlay: `study111_proxy_w1_rb24h` -> CAGR `119.4965%`, MDD `43.4964%`, Calmar `2.7473`
- Best gap12 overlay: `gap12_reference_w1_rb24h` -> CAGR `119.5609%`, MDD `43.4758%`, Calmar `2.7501`
- Best buy-and-hold overlay: `buy_hold_reference_w6_rb4h` -> CAGR `115.0422%`, MDD `41.6316%`, Calmar `2.7633`

## Overlay Inputs
- `study111_proxy` from `stage1_fullstack_choch_ob_reclaim_white_floor_lb12_rw2_close_above_white_es0.60_me3_addavg_minus_0.5ATR_equal_cd4_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gatenone`: standalone CAGR `2.1877%`, MDD `2.2609%`, Final Equity `1095.1581`
- `study111_exact` from `stage2_exact_choch_ob_reclaim_white_floor_lb12_rw2_close_above_white_es0.60_me3_addavg_minus_0.5ATR_equal_cd4_stopred_floor-0.15ATR_tptrail_white_avg_after_2R_hold96_gaterelaxed`: standalone CAGR `0.0146%`, MDD `0.2496%`, Final Equity `1000.6153`
- `gap12_reference` from `gap_12`: standalone CAGR `2.9069%`, MDD `35.1812%`, Final Equity `1127.9070`
- `buy_hold_reference` from `buy_hold`: standalone CAGR `10.9704%`, MDD `67.8001%`, Final Equity `1548.4270`

## Top 12

| Variant | Overlay | Weight % | Rebalance | CAGR % | MDD % | Calmar | Fee Paid |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| buy_hold_reference_w6_rb4h | buy_hold_reference | 6.00 | 4h | 115.0422 | 41.6316 | 2.7633 | 69.2096 |
| buy_hold_reference_w7_rb4h | buy_hold_reference | 7.00 | 4h | 114.0795 | 41.2832 | 2.7633 | 78.8065 |
| buy_hold_reference_w5_rb4h | buy_hold_reference | 5.00 | 4h | 115.9966 | 41.9799 | 2.7631 | 59.0752 |
| buy_hold_reference_w8_rb4h | buy_hold_reference | 8.00 | 4h | 113.1084 | 40.9350 | 2.7631 | 87.8763 |
| buy_hold_reference_w6_rb24h | buy_hold_reference | 6.00 | 24h | 115.0166 | 41.6365 | 2.7624 | 31.2455 |
| buy_hold_reference_w5_rb24h | buy_hold_reference | 5.00 | 24h | 115.9748 | 41.9840 | 2.7624 | 26.6739 |
| buy_hold_reference_w7_rb24h | buy_hold_reference | 7.00 | 24h | 114.0501 | 41.2891 | 2.7622 | 35.5734 |
| buy_hold_reference_w4_rb24h | buy_hold_reference | 4.00 | 24h | 116.9246 | 42.3315 | 2.7621 | 21.8539 |
| buy_hold_reference_w10_rb4h | buy_hold_reference | 10.00 | 4h | 111.1420 | 40.2387 | 2.7621 | 104.4767 |
| buy_hold_reference_w8_rb24h | buy_hold_reference | 8.00 | 24h | 113.0755 | 40.9417 | 2.7619 | 39.6624 |
| buy_hold_reference_w4_rb4h | buy_hold_reference | 4.00 | 4h | 116.9423 | 42.3505 | 2.7613 | 48.3934 |
| buy_hold_reference_w10_rb24h | buy_hold_reference | 10.00 | 24h | 111.1026 | 40.2474 | 2.7605 | 47.1435 |

## Interpretation
- The new study-111 sleeve does not yet beat the simpler long references once the triple-digit CAGR constraint is enforced.
- The winning overlay weight is large enough to matter, so the added sleeve is doing more than cosmetic smoothing.
- If core85-only still wins on both CAGR and Calmar, then 112 says the safest move is to keep study 111 in the idea queue rather than the live mix.

## Outputs
- Plot: `112_backtest_btcusdt_highcagr_core_srsmc_overlay.png`
- Metrics CSV: `112_backtest_btcusdt_highcagr_core_srsmc_overlay.csv`
- Curves CSV: `112_backtest_btcusdt_highcagr_core_srsmc_overlay_curves.csv`
- Report: `112_backtest_btcusdt_highcagr_core_srsmc_overlay.md`