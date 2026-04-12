from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_86_PATH = Path("86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.py")
CASE_CURVES_CSV = Path("90_backtest_btcusdt_scale06_adx002_case123_stress_proxy_sweep_latest_case_curves.csv")
FLOW_MARKET_CSV = Path("96_backtest_btcusdt_scale06_adx002_case123_flow_proxy_sweep_market_state_4h.csv")

OUT_BASE = "98_backtest_btcusdt_scale06_adx002_case123_flow_hybrid_compare"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

MONTHLY_TOPUP = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
REBALANCE_FEE_RATE = 0.0004
BASE_WEIGHTS = (0.62, 0.31, 0.07)
SELL_WEIGHTS = (0.58, 0.30, 0.12)
SQUEEZE_WEIGHTS = (0.66, 0.31, 0.03)

VARIANTS = [
    {"variant": "static_thr2", "threshold": 0.02, "mode": "static"},
    {"variant": "static_thr4", "threshold": 0.04, "mode": "static"},
    {"variant": "flow_sell6_thr2", "threshold": 0.02, "mode": "flow_sell6"},
    {"variant": "flow_sell6_thr4", "threshold": 0.04, "mode": "flow_sell6"},
    {"variant": "flow_combo6_thr2", "threshold": 0.02, "mode": "flow_combo6"},
    {"variant": "flow_combo6_thr4", "threshold": 0.04, "mode": "flow_combo6"},
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


def merge_state_to_cases(case_curves: pd.DataFrame, market_state: pd.DataFrame) -> pd.DataFrame:
    left = case_curves.copy().reset_index(drop=True)
    right = market_state.copy().reset_index(drop=True)
    left["timestamp"] = left["timestamp"].to_numpy(dtype="datetime64[ns]")
    right["timestamp"] = right["timestamp"].to_numpy(dtype="datetime64[ns]")
    return pd.merge_asof(left.sort_values("timestamp"), right.sort_values("timestamp"), on="timestamp", direction="backward").dropna(
        subset=["trend_4h_confirmed"]
    ).reset_index(drop=True)


def get_target_weights(row: pd.Series, mode: str) -> tuple[float, float, float]:
    if mode == "flow_combo6":
        if bool(row["squeeze_risk_active_3"]):
            return SQUEEZE_WEIGHTS
        if bool(row["sell_climax_active_6"]):
            return SELL_WEIGHTS
        return BASE_WEIGHTS
    if mode == "flow_sell6":
        if bool(row["sell_climax_active_6"]):
            return SELL_WEIGHTS
    return BASE_WEIGHTS


def run_hybrid(merged: pd.DataFrame, variant: str, threshold: float, mode: str) -> tuple[pd.DataFrame, dict]:
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
    state_switches = 0
    turnover_notional = 0.0

    cur_target = BASE_WEIGHTS
    cap1[0] = INITIAL_CAPITAL_TOTAL * cur_target[0]
    cap2[0] = INITIAL_CAPITAL_TOTAL * cur_target[1]
    cap3[0] = INITIAL_CAPITAL_TOTAL * cur_target[2]
    total[0] = INITIAL_CAPITAL_TOTAL
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0
    w1_series[0], w2_series[0], w3_series[0] = cur_target

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        c3 = cap3[i - 1] * (1.0 + float(ret3[i]))
        cur_total = c1 + c2 + c3
        cur_flow = 0.0

        target_w1, target_w2, target_w3 = get_target_weights(merged.iloc[i], mode)
        target_weights = (target_w1, target_w2, target_w3)
        if target_weights != cur_target:
            state_switches += 1

        if topup_flags[i]:
            cur_flow = MONTHLY_TOPUP
            target1_after = target_w1 * (cur_total + cur_flow)
            target2_after = target_w2 * (cur_total + cur_flow)
            add1 = min(max(target1_after - c1, 0.0), cur_flow)
            remaining = cur_flow - add1
            add2 = min(max(target2_after - c2, 0.0), remaining)
            add3 = cur_flow - add1 - add2
            c1 += add1
            c2 += add2
            c3 += add3
            cur_total += cur_flow

        if cur_total > 0:
            aw1, aw2, aw3 = c1 / cur_total, c2 / cur_total, c3 / cur_total
            max_drift = max(abs(aw1 - target_w1), abs(aw2 - target_w2), abs(aw3 - target_w3))
        else:
            max_drift = 0.0

        if rebal_flags[i] and max_drift >= threshold - 1e-12:
            target1 = cur_total * target_w1
            target2 = cur_total * target_w2
            target3 = cur_total * target_w3
            moved = abs(target1 - c1) + abs(target2 - c2) + abs(target3 - c3)
            fee = moved * REBALANCE_FEE_RATE
            cur_total -= fee
            c1 = cur_total * target_w1
            c2 = cur_total * target_w2
            c3 = cur_total * target_w3
            fee_paid += fee
            turnover_notional += moved
            rebalance_count += 1

        prev_total = total[i - 1]
        period_return = (cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0
        nav_index[i] = nav_index[i - 1] * (1.0 + period_return)

        cur_target = target_weights
        cap1[i], cap2[i], cap3[i] = c1, c2, c3
        total[i] = cur_total
        flow[i] = cur_flow
        contrib[i] = contrib[i - 1] + cur_flow
        w1_series[i], w2_series[i], w3_series[i] = cur_target

    out = merged[["timestamp"]].copy()
    out["variant"] = variant
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

    topups_df = pd.DataFrame({"timestamp": ts[topup_flags], "topup_amount": MONTHLY_TOPUP})
    stats = s86.compute_flow_metrics(out, topups_df)
    stats["variant"] = variant
    stats["threshold_pct"] = threshold * 100.0
    stats["mode"] = mode
    stats["rebalance_count"] = rebalance_count
    stats["state_switches"] = state_switches
    stats["fee_paid"] = fee_paid
    stats["turnover_notional"] = turnover_notional
    stats["avg_case3_weight_pct"] = float(pd.Series(w3_series[1:]).mean() * 100.0)
    return out, stats


def save_plot(metrics_df: pd.DataFrame, curve_map: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.0]})
    ax_eq, ax_perf, ax_cost = axes
    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {variant: cmap(i % 10) for i, variant in enumerate(variants)}

    for variant in variants:
        curve = curve_map[variant]
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.set_title("98번 연구: Case123 Flow Hybrid Compare")
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

    ax_cost.bar(metrics_df["variant"], metrics_df["rebalance_count"], color=[colors[v] for v in variants], alpha=0.85, label="Rebalances")
    ax_cost.set_ylabel("Rebalances")
    ax_cost.grid(True, axis="y", alpha=0.2)
    ax_cost.tick_params(axis="x", rotation=20)
    ax_cost_t = ax_cost.twinx()
    ax_cost_t.plot(metrics_df["variant"], metrics_df["fee_paid"], color="#9467bd", marker="o", linewidth=1.1, label="Fee Paid")
    ax_cost_t.set_ylabel("Fee Paid")
    h1, l1 = ax_cost.get_legend_handles_labels()
    h2, l2 = ax_cost_t.get_legend_handles_labels()
    ax_cost.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame) -> None:
    best = metrics_df.sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).iloc[0]
    baseline = metrics_df[metrics_df["variant"] == "static_thr4"].iloc[0]
    lines: list[str] = []
    lines.append("# 98번 연구: Case123 Flow Hybrid Compare")
    lines.append("")
    lines.append("## 설정")
    lines.append("- 91 hybrid 구조 위에 96의 flow-state target weights를 얹는다.")
    lines.append("- 월 top-up은 현재 target weights 기준 underweight 쪽에 먼저 넣는다.")
    lines.append("- 전체 리밸런싱은 4시간 경계에서 drift threshold를 넘을 때만 한다.")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Variant | Mode | Threshold %p | Final Equity | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | State Switches | Fee Paid |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {row['mode']} | {_fmt(row['threshold_pct'])} | {_fmt(row['final_equity'])} | {_fmt(row['twr_cagr_pct'])} | "
            f"{_fmt(row['twr_mdd_pct'])} | {_fmt(row['twr_calmar_ratio'])} | {_fmt(row['xirr_pct'])} | "
            f"{int(row['rebalance_count'])} | {int(row['state_switches'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append(f"- best variant: `{best['variant']}`")
    lines.append(
        f"- best vs static_thr4: TWR CAGR `{_fmt(best['twr_cagr_pct'] - baseline['twr_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best['twr_mdd_pct'] - baseline['twr_mdd_pct'])}pp`, "
        f"XIRR `{_fmt(best['xirr_pct'] - baseline['xirr_pct'])}pp`, "
        f"fee `{_fmt(best['fee_paid'] - baseline['fee_paid'])}`."
    )
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 성과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- 보고서: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run() -> None:
    case_curves = pd.read_csv(CASE_CURVES_CSV, parse_dates=["timestamp"])
    case_curves = case_curves.set_index("timestamp").resample("15min").last().dropna().reset_index()
    market_state = pd.read_csv(FLOW_MARKET_CSV, parse_dates=["timestamp"])
    merged = merge_state_to_cases(case_curves, market_state)

    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}
    for cfg in VARIANTS:
        curve, stats = run_hybrid(merged, cfg["variant"], float(cfg["threshold"]), str(cfg["mode"]))
        rows.append(stats)
        curve_rows.append(curve)
        curve_map[cfg["variant"]] = curve

    metrics_df = pd.DataFrame(rows).sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curve_rows, ignore_index=True)
    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(metrics_df, curve_map)
    save_report(metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


s86 = load_module("m86_98", BASE_86_PATH)


if __name__ == "__main__":
    run()
