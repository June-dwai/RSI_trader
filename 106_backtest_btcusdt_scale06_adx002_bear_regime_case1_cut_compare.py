from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


CASE_CURVES_CSV = Path("90_backtest_btcusdt_scale06_adx002_case123_stress_proxy_sweep_latest_case_curves.csv")
STATE_CSV = Path("105_backtest_btcusdt_scale06_adx002_allocator_realism_compare_sleeve_state.csv")
FLOW_MARKET_CSV = Path("96_backtest_btcusdt_scale06_adx002_case123_flow_proxy_sweep_market_state_4h.csv")
BASE_86_PATH = Path("86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.py")

OUT_BASE = "106_backtest_btcusdt_scale06_adx002_bear_regime_case1_cut_compare"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

INITIAL_CAPITAL_TOTAL = 2000.0
MONTHLY_TOPUP = 1000.0
THRESHOLD = 0.02
REBALANCE_FEE_RATE = 0.0004

BASE_WEIGHTS = (0.62, 0.31, 0.07)
SELL_WEIGHTS = (0.58, 0.30, 0.12)
SQUEEZE_WEIGHTS = (0.66, 0.31, 0.03)

VARIANTS = [
    {
        "variant": "baseline_openfloor",
        "topup_block_case1_bear": False,
        "bear_case1_factor": 1.00,
    },
    {
        "variant": "bear_topup_block_case1",
        "topup_block_case1_bear": True,
        "bear_case1_factor": 1.00,
    },
    {
        "variant": "bear_cut25_openfloor",
        "topup_block_case1_bear": True,
        "bear_case1_factor": 0.75,
    },
    {
        "variant": "bear_cut50_openfloor",
        "topup_block_case1_bear": True,
        "bear_case1_factor": 0.50,
    },
    {
        "variant": "bear_cut100_openfloor",
        "topup_block_case1_bear": True,
        "bear_case1_factor": 0.00,
    },
]


def load_module(alias: str, path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing script: {path}")
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def compute_month_flags(ts: pd.Series) -> np.ndarray:
    flags = (ts.dt.to_period("M") != ts.dt.to_period("M").shift(1)).to_numpy(copy=True)
    if len(flags):
        flags[0] = False
    return flags


def project_to_simplex(values: np.ndarray, target_sum: float) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return values.copy()
    if target_sum <= 0:
        return np.zeros_like(values)
    u = np.sort(values)[::-1]
    cssv = np.cumsum(u) - target_sum
    idx = np.arange(1, len(values) + 1, dtype=float)
    cond = u - cssv / idx > 0
    if not np.any(cond):
        return np.full_like(values, target_sum / len(values))
    rho = int(np.nonzero(cond)[0][-1])
    theta = cssv[rho] / float(rho + 1)
    return np.maximum(values - theta, 0.0)


def allocate_openfloor(current_caps: np.ndarray, target_caps: np.ndarray, flat_mask: np.ndarray) -> np.ndarray:
    lower_bounds = np.where(flat_mask, 0.0, current_caps)
    remainder = float(current_caps.sum() - lower_bounds.sum())
    add = project_to_simplex(target_caps - lower_bounds, remainder)
    return lower_bounds + add


def load_merged() -> pd.DataFrame:
    curves = pd.read_csv(CASE_CURVES_CSV, parse_dates=["timestamp"])
    state = pd.read_csv(STATE_CSV, parse_dates=["timestamp"], low_memory=False)
    market = pd.read_csv(FLOW_MARKET_CSV, parse_dates=["timestamp"])

    for col in ["case1_flat", "case2_flat", "case3_flat", "case1_has_hedge", "sell_climax_active_6", "squeeze_risk_active_3"]:
        state[col] = state[col].astype(str).str.lower().eq("true")
    market["sell_climax_active_6"] = market["sell_climax_active_6"].astype(str).str.lower().eq("true")
    market["squeeze_risk_active_3"] = market["squeeze_risk_active_3"].astype(str).str.lower().eq("true")
    market = market[["timestamp", "trend_4h_confirmed"]].copy()

    common_start = pd.Timestamp(state["timestamp"].min())
    curves = curves[curves["timestamp"] >= common_start].copy()

    merged = pd.merge(curves, state, on="timestamp", how="inner").sort_values("timestamp").reset_index(drop=True)
    merged["timestamp"] = merged["timestamp"].to_numpy(dtype="datetime64[ns]")
    market["timestamp"] = market["timestamp"].to_numpy(dtype="datetime64[ns]")
    merged = pd.merge_asof(merged.sort_values("timestamp"), market.sort_values("timestamp"), on="timestamp", direction="backward")
    return merged


def get_flow_weights(row: pd.Series) -> tuple[float, float, float]:
    if bool(row["squeeze_risk_active_3"]):
        return SQUEEZE_WEIGHTS
    if bool(row["sell_climax_active_6"]):
        return SELL_WEIGHTS
    return BASE_WEIGHTS


def get_target_weights(row: pd.Series, bear_case1_factor: float) -> tuple[float, float, float]:
    w1, w2, w3 = get_flow_weights(row)
    if str(row["trend_4h_confirmed"]) == "bearish" and bear_case1_factor < 1.0:
        removed = w1 * (1.0 - bear_case1_factor)
        w1 = w1 * bear_case1_factor
        w2 = w2 + removed
    return float(w1), float(w2), float(w3)


def get_topup_weights(target_weights: tuple[float, float, float], is_bear: bool, block_case1: bool) -> tuple[float, float, float]:
    w1, w2, w3 = target_weights
    if is_bear and block_case1:
        total = w2 + w3
        if total <= 0:
            return 0.0, 1.0, 0.0
        return 0.0, w2 / total, w3 / total
    return w1, w2, w3


def run_variant(merged: pd.DataFrame, cfg: dict, s86) -> tuple[pd.DataFrame, dict]:
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret3 = merged["equity_case3"].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"].reset_index(drop=True)
    topup_flags = compute_month_flags(ts)
    rebal_flags = (ts.dt.floor("4h") != ts.dt.floor("4h").shift(1)).to_numpy()

    cap1 = np.zeros(len(merged), dtype=float)
    cap2 = np.zeros(len(merged), dtype=float)
    cap3 = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    contrib = np.zeros(len(merged), dtype=float)
    flow = np.zeros(len(merged), dtype=float)
    nav_index = np.zeros(len(merged), dtype=float)
    w1_series = np.zeros(len(merged), dtype=float)
    w2_series = np.zeros(len(merged), dtype=float)
    w3_series = np.zeros(len(merged), dtype=float)

    fee_paid = 0.0
    rebalance_count = 0
    turnover_notional = 0.0
    blocked_open_overweight_checks = 0
    bear_topup_count = 0
    bear_topup_case1_blocked_count = 0

    start_weights = get_target_weights(merged.iloc[0], float(cfg["bear_case1_factor"]))
    cap1[0] = INITIAL_CAPITAL_TOTAL * start_weights[0]
    cap2[0] = INITIAL_CAPITAL_TOTAL * start_weights[1]
    cap3[0] = INITIAL_CAPITAL_TOTAL * start_weights[2]
    total[0] = INITIAL_CAPITAL_TOTAL
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0
    w1_series[0], w2_series[0], w3_series[0] = start_weights

    topup_rows: list[dict] = []

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        c3 = cap3[i - 1] * (1.0 + float(ret3[i]))
        cur_total = c1 + c2 + c3
        cur_flow = 0.0

        target_weights = get_target_weights(merged.iloc[i], float(cfg["bear_case1_factor"]))
        is_bear = str(merged.iloc[i]["trend_4h_confirmed"]) == "bearish"
        topup_weights = get_topup_weights(target_weights, is_bear, bool(cfg["topup_block_case1_bear"]))

        if topup_flags[i]:
            cur_flow = MONTHLY_TOPUP
            if is_bear:
                bear_topup_count += 1
                if bool(cfg["topup_block_case1_bear"]):
                    bear_topup_case1_blocked_count += 1

            dep1, dep2, dep3 = topup_weights
            c1 += cur_flow * dep1
            c2 += cur_flow * dep2
            c3 += cur_flow * dep3
            cur_total += cur_flow
            topup_rows.append(
                {
                    "timestamp": ts.iloc[i],
                    "topup_amount": cur_flow,
                }
            )

        current_caps = np.array([c1, c2, c3], dtype=float)
        target_caps = np.array([cur_total * target_weights[0], cur_total * target_weights[1], cur_total * target_weights[2]], dtype=float)

        if cur_total > 0:
            actual_weights = current_caps / cur_total
            max_drift = float(np.max(np.abs(actual_weights - np.array(target_weights, dtype=float))))
        else:
            max_drift = 0.0

        if rebal_flags[i] and max_drift >= THRESHOLD - 1e-12:
            flat_mask = np.array(
                [
                    bool(merged.iloc[i]["case1_flat"]),
                    bool(merged.iloc[i]["case2_flat"]),
                    bool(merged.iloc[i]["case3_flat"]),
                ],
                dtype=bool,
            )
            if np.any((~flat_mask) & (current_caps > target_caps + 1e-12)):
                blocked_open_overweight_checks += 1

            new_caps = allocate_openfloor(current_caps, target_caps, flat_mask)
            moved = float(np.abs(new_caps - current_caps).sum())
            if moved > 1e-12:
                fee = moved * REBALANCE_FEE_RATE
                cur_total_after = max(cur_total - fee, 0.0)
                scaled_target = np.array(
                    [
                        cur_total_after * target_weights[0],
                        cur_total_after * target_weights[1],
                        cur_total_after * target_weights[2],
                    ],
                    dtype=float,
                )
                new_caps = allocate_openfloor(current_caps, scaled_target, flat_mask)
                moved = float(np.abs(new_caps - current_caps).sum())
                fee = moved * REBALANCE_FEE_RATE
                current_caps = new_caps
                cur_total = float(current_caps.sum())
                fee_paid += fee
                turnover_notional += moved
                rebalance_count += 1

        c1, c2, c3 = [float(v) for v in current_caps]
        cur_total = c1 + c2 + c3
        prev_total = total[i - 1]
        period_return = (cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0
        nav_index[i] = nav_index[i - 1] * (1.0 + period_return)

        cap1[i], cap2[i], cap3[i] = c1, c2, c3
        total[i] = cur_total
        contrib[i] = contrib[i - 1] + cur_flow
        flow[i] = cur_flow
        w1_series[i], w2_series[i], w3_series[i] = target_weights

    out = merged[["timestamp"]].copy()
    out["variant"] = str(cfg["variant"])
    out["equity_total"] = total
    out["cap1"] = cap1
    out["cap2"] = cap2
    out["cap3"] = cap3
    out["cash_flow"] = flow
    out["cumulative_contribution"] = contrib
    out["nav_index"] = nav_index
    out["w1"] = w1_series
    out["w2"] = w2_series
    out["w3"] = w3_series

    topups_df = pd.DataFrame(topup_rows)
    stats = s86.compute_flow_metrics(out, topups_df)
    stats["variant"] = str(cfg["variant"])
    stats["bear_case1_factor"] = float(cfg["bear_case1_factor"])
    stats["topup_block_case1_bear"] = bool(cfg["topup_block_case1_bear"])
    stats["rebalance_count"] = rebalance_count
    stats["fee_paid"] = fee_paid
    stats["turnover_notional"] = turnover_notional
    stats["blocked_open_overweight_checks"] = blocked_open_overweight_checks
    stats["bear_topup_count"] = bear_topup_count
    stats["bear_topup_case1_blocked_count"] = bear_topup_case1_blocked_count
    stats["avg_case1_weight_pct"] = float(pd.Series(w1_series[1:]).mean() * 100.0)
    stats["avg_case2_weight_pct"] = float(pd.Series(w2_series[1:]).mean() * 100.0)
    stats["avg_case3_weight_pct"] = float(pd.Series(w3_series[1:]).mean() * 100.0)
    return out, stats


def save_plot(metrics_df: pd.DataFrame, curves_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_perf, ax_weight = axes
    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curves_df[curves_df["variant"] == variant]
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.set_title("106 Study: Bear-Regime Case1 Cut Compare")
    ax_eq.set_ylabel("Total Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_perf.bar(metrics_df["variant"], metrics_df["twr_cagr_pct"], color=[colors[v] for v in variants], alpha=0.85, label="TWR CAGR %")
    ax_perf.set_ylabel("TWR CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf.tick_params(axis="x", rotation=20)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(metrics_df["variant"], metrics_df["twr_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="TWR MDD %")
    ax_perf_t.set_ylabel("TWR MDD %")
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_weight.bar(metrics_df["variant"], metrics_df["avg_case1_weight_pct"], color="#1f77b4", alpha=0.85, label="Avg Case1 Weight %")
    ax_weight.set_ylabel("Avg Case1 Weight %")
    ax_weight.grid(True, axis="y", alpha=0.2)
    ax_weight.tick_params(axis="x", rotation=20)
    ax_weight_t = ax_weight.twinx()
    ax_weight_t.plot(metrics_df["variant"], metrics_df["xirr_pct"], color="#2ca02c", marker="o", linewidth=1.1, label="XIRR %")
    ax_weight_t.set_ylabel("XIRR %")
    h1, l1 = ax_weight.get_legend_handles_labels()
    h2, l2 = ax_weight_t.get_legend_handles_labels()
    ax_weight.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, bear_ratio_pct: float, bear_topup_ratio_pct: float) -> None:
    baseline = metrics_df[metrics_df["variant"] == "baseline_openfloor"].iloc[0]
    best = metrics_df.sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).iloc[0]

    lines: list[str] = []
    lines.append("# 106번 연구: Bear-Regime Case1 Cut Compare")
    lines.append("")
    lines.append("## 목적")
    lines.append("- `openfloor` allocator를 유지한 채, bear regime에서 `case1`로 새 돈을 안 보내거나 기존 목표 비중을 줄였을 때 개선되는지 확인한다.")
    lines.append("- bear regime 판정은 `trend_4h_confirmed == bearish`로 둔다.")
    lines.append("")
    lines.append("## bear regime 빈도")
    lines.append(f"- bear regime time ratio: `{_fmt(bear_ratio_pct)}%`")
    lines.append(f"- bear regime top-up ratio: `{_fmt(bear_topup_ratio_pct)}%`")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Variant | Bear Case1 Factor | Bear Topup Block | Final Equity | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid | Avg W1 % | Avg W2 % | Blocked Open Overweight |")
    lines.append("| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['bear_case1_factor'], 2)} | {bool(row['topup_block_case1_bear'])} | "
            f"{_fmt(row['final_equity'])} | {_fmt(row['twr_cagr_pct'])} | {_fmt(row['twr_mdd_pct'])} | {_fmt(row['twr_calmar_ratio'])} | "
            f"{_fmt(row['xirr_pct'])} | {int(row['rebalance_count'])} | {_fmt(row['fee_paid'])} | "
            f"{_fmt(row['avg_case1_weight_pct'])} | {_fmt(row['avg_case2_weight_pct'])} | {int(row['blocked_open_overweight_checks'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append(
        f"- best variant: `{best['variant']}`. baseline 대비 "
        f"CAGR `{_fmt(best['twr_cagr_pct'] - baseline['twr_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best['twr_mdd_pct'] - baseline['twr_mdd_pct'])}pp`, "
        f"XIRR `{_fmt(best['xirr_pct'] - baseline['xirr_pct'])}pp`."
    )
    lines.append("- `bear_topup_block_case1`은 새 돈만 막는 효과를 보여준다.")
    lines.append("- `bear_cut25/50/100`은 기존 목표 비중 자체를 바꾸기 때문에, 월 입금 영향이 작아져도 계속 작동한다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 결과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- 보고서: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    s86 = load_module("s86_106", BASE_86_PATH)
    merged = load_merged()
    bear_ratio_pct = float((merged["trend_4h_confirmed"].astype(str) == "bearish").mean() * 100.0)
    topup_flags = compute_month_flags(merged["timestamp"])
    bear_topup_ratio_pct = float(
        (merged.loc[topup_flags, "trend_4h_confirmed"].astype(str) == "bearish").mean() * 100.0
    )

    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    for cfg in VARIANTS:
        curve, stats = run_variant(merged, cfg, s86)
        rows.append(stats)
        curve_rows.append(curve)

    metrics_df = pd.DataFrame(rows).sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curve_rows, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(metrics_df, curves_df)
    save_report(metrics_df, bear_ratio_pct, bear_topup_ratio_pct)

    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(f"saved_plot={OUT_PNG}")


if __name__ == "__main__":
    run()
