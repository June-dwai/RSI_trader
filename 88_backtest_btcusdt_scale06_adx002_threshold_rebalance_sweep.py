from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_86_PATH = Path("86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.py")

OUT_BASE = "88_backtest_btcusdt_scale06_adx002_threshold_rebalance_sweep"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

MONTHLY_TOPUP = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
REBALANCE_FEE_RATE = 0.0004
THRESHOLDS = [0.00, 0.02, 0.04, 0.06, 0.08, 0.10]

CASE12_WEIGHTS = (0.74, 0.26, 0.00)
CASE123_WEIGHTS = (0.62, 0.31, 0.07)


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


def build_case12_merged(case1: pd.DataFrame, case2: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge(case1, case2, on="timestamp", how="outer").sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2"]).copy()
    merged["equity_case3"] = 1.0
    return merged


def compute_month_flags(ts: pd.Series) -> np.ndarray:
    flags = (ts.dt.to_period("M") != ts.dt.to_period("M").shift(1)).to_numpy(copy=True)
    if len(flags):
        flags[0] = False
    return flags


def run_threshold_portfolio(
    merged: pd.DataFrame,
    variant: str,
    weights: tuple[float, float, float],
    threshold: float,
) -> tuple[pd.DataFrame, dict]:
    w1, w2, w3 = weights
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret3 = merged["equity_case3"].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"].reset_index(drop=True)

    rebal_flags = (ts.dt.floor("4h") != ts.dt.floor("4h").shift(1)).to_numpy()
    topup_flags = compute_month_flags(ts)

    cap1 = np.zeros(len(merged), dtype=float)
    cap2 = np.zeros(len(merged), dtype=float)
    cap3 = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    contrib = np.zeros(len(merged), dtype=float)
    flow = np.zeros(len(merged), dtype=float)
    nav_index = np.zeros(len(merged), dtype=float)
    drift_before = np.zeros(len(merged), dtype=float)
    drift_after = np.zeros(len(merged), dtype=float)

    fee_paid = 0.0
    rebalance_count = 0
    threshold_hits = 0
    turnover_notional = 0.0

    cap1[0] = INITIAL_CAPITAL_TOTAL * w1
    cap2[0] = INITIAL_CAPITAL_TOTAL * w2
    cap3[0] = INITIAL_CAPITAL_TOTAL * w3
    total[0] = cap1[0] + cap2[0] + cap3[0]
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        c3 = cap3[i - 1] * (1.0 + float(ret3[i]))
        cur_total = c1 + c2 + c3
        cur_flow = 0.0

        if topup_flags[i]:
            cur_flow = MONTHLY_TOPUP
            c1 += cur_flow * w1
            c2 += cur_flow * w2
            c3 += cur_flow * w3
            cur_total += cur_flow

        if cur_total > 0:
            aw1 = c1 / cur_total
            aw2 = c2 / cur_total
            aw3 = c3 / cur_total
            max_drift = max(abs(aw1 - w1), abs(aw2 - w2), abs(aw3 - w3))
        else:
            aw1 = aw2 = aw3 = 0.0
            max_drift = 0.0
        drift_before[i] = max_drift

        if rebal_flags[i] and max_drift >= threshold - 1e-12:
            threshold_hits += 1
            target1 = cur_total * w1
            target2 = cur_total * w2
            target3 = cur_total * w3
            moved = abs(target1 - c1) + abs(target2 - c2) + abs(target3 - c3)
            fee = moved * REBALANCE_FEE_RATE
            cur_total -= fee
            c1 = cur_total * w1
            c2 = cur_total * w2
            c3 = cur_total * w3
            fee_paid += fee
            turnover_notional += moved
            rebalance_count += 1
            drift_after[i] = 0.0
        else:
            if cur_total > 0:
                drift_after[i] = max(abs((c1 / cur_total) - w1), abs((c2 / cur_total) - w2), abs((c3 / cur_total) - w3))
            else:
                drift_after[i] = 0.0

        prev_total = total[i - 1]
        period_return = (cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0
        nav_index[i] = nav_index[i - 1] * (1.0 + period_return)

        cap1[i] = c1
        cap2[i] = c2
        cap3[i] = c3
        total[i] = cur_total
        flow[i] = cur_flow
        contrib[i] = contrib[i - 1] + cur_flow

    out = merged[["timestamp"]].copy()
    out["variant"] = variant
    out["equity_total"] = total
    out["cap1"] = cap1
    out["cap2"] = cap2
    out["cap3"] = cap3
    out["cash_flow"] = flow
    out["cumulative_contribution"] = contrib
    out["nav_index"] = nav_index
    out["drift_before"] = drift_before
    out["drift_after"] = drift_after
    out["w1"] = w1
    out["w2"] = w2
    out["w3"] = w3

    topups_df = pd.DataFrame(
        {
            "timestamp": ts[topup_flags],
            "topup_amount": MONTHLY_TOPUP,
        }
    )
    stats = s86.compute_flow_metrics(out, topups_df)
    stats["variant"] = variant
    stats["threshold_pct"] = threshold * 100.0
    stats["rebalance_count"] = rebalance_count
    stats["threshold_hits"] = threshold_hits
    stats["fee_paid"] = fee_paid
    stats["turnover_notional"] = turnover_notional
    stats["avg_drift_before_pct"] = float(pd.Series(drift_before[1:]).mean() * 100.0)
    stats["avg_drift_after_pct"] = float(pd.Series(drift_after[1:]).mean() * 100.0)
    stats["topup_count"] = int(topup_flags.sum())
    return out, stats


def save_plot(metrics_df: pd.DataFrame, curve_map: dict[str, pd.DataFrame]):
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.0]})
    ax_eq, ax_perf, ax_cost = axes

    focus = [
        "case12_thr0",
        "case12_thr4",
        "case12_thr8",
        "case123_thr0",
        "case123_thr4",
        "case123_thr8",
    ]
    colors = {
        "case12_thr0": "#1f77b4",
        "case12_thr4": "#4c78a8",
        "case12_thr8": "#9ecae9",
        "case123_thr0": "#d62728",
        "case123_thr4": "#e45756",
        "case123_thr8": "#f28e8c",
    }
    for variant in focus:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.set_title("88번 연구: Threshold Rebalance Sweep")
    ax_eq.set_ylabel("Total Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    plot_df = metrics_df.copy()
    plot_df["family"] = plot_df["variant"].str.extract(r"^(case12|case123)")
    plot_df["threshold_label"] = plot_df["threshold_pct"].astype(int).astype(str)
    for family, family_df in plot_df.groupby("family"):
        family_df = family_df.sort_values("threshold_pct")
        ax_perf.plot(family_df["threshold_pct"], family_df["twr_cagr_pct"], marker="o", linewidth=1.2, label=f"{family} TWR CAGR")
    ax_perf_t = ax_perf.twinx()
    for family, family_df in plot_df.groupby("family"):
        family_df = family_df.sort_values("threshold_pct")
        ax_perf_t.plot(family_df["threshold_pct"], family_df["twr_mdd_pct"], marker="s", linewidth=1.0, linestyle="--", label=f"{family} TWR MDD")
    ax_perf.set_xlabel("Threshold %p")
    ax_perf.set_ylabel("TWR CAGR %")
    ax_perf_t.set_ylabel("TWR MDD %")
    ax_perf.grid(True, alpha=0.2)
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper center", ncol=2)

    for family, family_df in plot_df.groupby("family"):
        family_df = family_df.sort_values("threshold_pct")
        ax_cost.plot(family_df["threshold_pct"], family_df["rebalance_count"], marker="o", linewidth=1.2, label=f"{family} rebalance count")
    ax_cost_t = ax_cost.twinx()
    for family, family_df in plot_df.groupby("family"):
        family_df = family_df.sort_values("threshold_pct")
        ax_cost_t.plot(family_df["threshold_pct"], family_df["fee_paid"], marker="s", linewidth=1.0, linestyle="--", label=f"{family} fee")
    ax_cost.set_xlabel("Threshold %p")
    ax_cost.set_ylabel("Rebalance Count")
    ax_cost_t.set_ylabel("Fee Paid")
    ax_cost.grid(True, alpha=0.2)
    h1, l1 = ax_cost.get_legend_handles_labels()
    h2, l2 = ax_cost_t.get_legend_handles_labels()
    ax_cost.legend(h1 + h2, l1 + l2, loc="upper center", ncol=2)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, common_start: pd.Timestamp, common_end: pd.Timestamp):
    lines: list[str] = []
    lines.append("# 88번 연구: Threshold Rebalance Sweep")
    lines.append("")
    lines.append("## 설정")
    lines.append("- 비교 목적: `4시간마다 무조건 리밸런싱` 대신, 비중 괴리가 일정 수준 이상일 때만 리밸런싱해도 성과가 유지되는지 확인한다.")
    lines.append(f"- 공통 구간: `{common_start}` -> `{common_end}`")
    lines.append(f"- 월 적립금: 매월 첫 시점에 `{MONTHLY_TOPUP:.0f}` 달러")
    lines.append("- 리밸런싱 체크 시점은 4시간마다 동일하지만, 실제 거래는 `threshold`를 넘은 경우에만 실행한다.")
    lines.append("- `threshold=0%`는 기존의 `항상 4시간 리밸런싱`과 같다.")
    lines.append("- `case12`는 `74/26`, `case123`는 `62/31/7` 비중을 사용한다.")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Variant | Threshold %p | Final Equity | Net Profit | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid | Avg Drift Before %p |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['threshold_pct'])} | {_fmt(row['final_equity'])} | {_fmt(row['net_profit'])} | "
            f"{_fmt(row['twr_cagr_pct'])} | {_fmt(row['twr_mdd_pct'])} | {_fmt(row['twr_calmar_ratio'])} | {_fmt(row['xirr_pct'])} | "
            f"{int(row['rebalance_count'])} | {_fmt(row['fee_paid'])} | {_fmt(row['avg_drift_before_pct'])} |"
        )
    lines.append("")

    case12 = metrics_df[metrics_df["variant"].str.startswith("case12_")].copy()
    case123 = metrics_df[metrics_df["variant"].str.startswith("case123_")].copy()
    best12 = case12.sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).iloc[0]
    best123 = case123.sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).iloc[0]
    baseline12 = case12[case12["threshold_pct"] == 0.0].iloc[0]
    baseline123 = case123[case123["threshold_pct"] == 0.0].iloc[0]

    lines.append("## 핵심 해석")
    lines.append(f"- case12 best threshold: `{best12['variant']}` (`TWR CAGR {_fmt(best12['twr_cagr_pct'])}%`, `MDD {_fmt(best12['twr_mdd_pct'])}%`, `XIRR {_fmt(best12['xirr_pct'])}%`).")
    lines.append(f"- case123 best threshold: `{best123['variant']}` (`TWR CAGR {_fmt(best123['twr_cagr_pct'])}%`, `MDD {_fmt(best123['twr_mdd_pct'])}%`, `XIRR {_fmt(best123['xirr_pct'])}%`).")
    lines.append(
        f"- case12 best vs always-rebalance: TWR CAGR `{_fmt(best12['twr_cagr_pct'] - baseline12['twr_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best12['twr_mdd_pct'] - baseline12['twr_mdd_pct'])}pp`, fee `{_fmt(best12['fee_paid'] - baseline12['fee_paid'])}`."
    )
    lines.append(
        f"- case123 best vs always-rebalance: TWR CAGR `{_fmt(best123['twr_cagr_pct'] - baseline123['twr_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best123['twr_mdd_pct'] - baseline123['twr_mdd_pct'])}pp`, fee `{_fmt(best123['fee_paid'] - baseline123['fee_paid'])}`."
    )
    lines.append("- threshold가 커질수록 리밸런싱 횟수와 수수료는 줄지만, 너무 커지면 포트폴리오 드리프트가 커져 edge가 약해질 수 있다.")
    lines.append("- 실전적으로는 `무조건 4시간마다`보다, `비중 괴리가 어느 정도 벌어졌을 때만` 맞추는 방식이 더 자연스럽다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 성과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- 보고서: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    case1, case2 = s86._build_case12_latest()
    case3 = s86._load_case3_curve()

    common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
    common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())

    case1_clip = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)].copy()
    case2_clip = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy()
    case3_clip = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)].copy()

    merged12 = build_case12_merged(case1_clip, case2_clip)
    merged123 = s86._build_merged(case1_clip, case2_clip, case3_clip)

    rows: list[dict] = []
    curve_map: dict[str, pd.DataFrame] = {}
    curve_rows: list[pd.DataFrame] = []

    for threshold in THRESHOLDS:
        thr_label = int(round(threshold * 100))
        variant12 = f"case12_thr{thr_label}"
        curve12, stats12 = run_threshold_portfolio(merged12, variant12, CASE12_WEIGHTS, threshold)
        rows.append(stats12)
        curve_map[variant12] = curve12
        curve_rows.append(curve12)

        variant123 = f"case123_thr{thr_label}"
        curve123, stats123 = run_threshold_portfolio(merged123, variant123, CASE123_WEIGHTS, threshold)
        rows.append(stats123)
        curve_map[variant123] = curve123
        curve_rows.append(curve123)

    metrics_df = pd.DataFrame(rows).sort_values(["variant", "threshold_pct"]).reset_index(drop=True)
    curves_df = pd.concat(curve_rows, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(metrics_df, curve_map)
    save_report(metrics_df, common_start, common_end)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


s86 = load_module("s86_88", BASE_86_PATH)


if __name__ == "__main__":
    run()
