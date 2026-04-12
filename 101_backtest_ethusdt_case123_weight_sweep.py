from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_100_PATH = Path("100_backtest_crossasset_case123_flow_combo6_thr2.py")
BASE_86_PATH = Path("86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.py")

OUT_BASE = "101_backtest_ethusdt_case123_weight_sweep"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_CASE_CURVES_CSV = Path(f"{OUT_BASE}_eth_case_curves.csv")

SYMBOL = "ETHUSDT"
MONTHLY_TOPUP = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
REBALANCE_FEE_RATE = 0.0004
THRESHOLDS = [0.02, 0.04]
W1_CANDIDATES = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
W3_CANDIDATES = [0.00, 0.05, 0.10, 0.15, 0.20]


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


def run_weight_variant(merged: pd.DataFrame, variant: str, weights: tuple[float, float, float], threshold: float, s86) -> tuple[pd.DataFrame, dict]:
    w1, w2, w3 = weights
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

    fee_paid = 0.0
    rebalance_count = 0
    turnover_notional = 0.0

    cap1[0] = INITIAL_CAPITAL_TOTAL * w1
    cap2[0] = INITIAL_CAPITAL_TOTAL * w2
    cap3[0] = INITIAL_CAPITAL_TOTAL * w3
    total[0] = INITIAL_CAPITAL_TOTAL
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
            target1_after = w1 * (cur_total + cur_flow)
            target2_after = w2 * (cur_total + cur_flow)
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
            max_drift = max(abs(aw1 - w1), abs(aw2 - w2), abs(aw3 - w3))
        else:
            max_drift = 0.0

        if rebal_flags[i] and max_drift >= threshold - 1e-12:
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

        prev_total = total[i - 1]
        period_return = (cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0
        nav_index[i] = nav_index[i - 1] * (1.0 + period_return)

        cap1[i], cap2[i], cap3[i] = c1, c2, c3
        total[i] = cur_total
        flow[i] = cur_flow
        contrib[i] = contrib[i - 1] + cur_flow

    out = merged[["timestamp"]].copy()
    out["variant"] = variant
    out["equity_total"] = total
    out["cash_flow"] = flow
    out["cumulative_contribution"] = contrib
    out["nav_index"] = nav_index

    topups_df = pd.DataFrame({"timestamp": ts[topup_flags], "topup_amount": MONTHLY_TOPUP})
    stats = s86.compute_flow_metrics(out, topups_df)
    stats["variant"] = variant
    stats["w1"] = w1
    stats["w2"] = w2
    stats["w3"] = w3
    stats["threshold_pct"] = threshold * 100.0
    stats["rebalance_count"] = rebalance_count
    stats["fee_paid"] = fee_paid
    stats["turnover_notional"] = turnover_notional
    return out, stats


def save_plot(metrics_df: pd.DataFrame, curve_map: dict[str, pd.DataFrame]) -> None:
    top_variants = metrics_df.head(8)["variant"].tolist()
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.0]})
    ax_eq, ax_perf, ax_cost = axes
    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(top_variants)}

    for variant in top_variants:
        curve = curve_map[variant]
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.set_title("101번 연구: ETHUSDT case123 weight sweep")
    ax_eq.set_ylabel("Total Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    show = metrics_df.head(12).copy()
    ax_perf.bar(show["variant"], show["twr_cagr_pct"], color=[cmap(i % 10) for i in range(len(show))], alpha=0.85, label="TWR CAGR %")
    ax_perf.set_ylabel("TWR CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf.tick_params(axis="x", rotation=20)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(show["variant"], show["twr_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="TWR MDD %")
    ax_perf_t.set_ylabel("TWR MDD %")
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_cost.bar(show["variant"], show["rebalance_count"], color=[cmap(i % 10) for i in range(len(show))], alpha=0.85, label="Rebalances")
    ax_cost.set_ylabel("Rebalances")
    ax_cost.grid(True, axis="y", alpha=0.2)
    ax_cost.tick_params(axis="x", rotation=20)
    ax_cost_t = ax_cost.twinx()
    ax_cost_t.plot(show["variant"], show["fee_paid"], color="#9467bd", marker="o", linewidth=1.1, label="Fee Paid")
    ax_cost_t.set_ylabel("Fee Paid")
    h1, l1 = ax_cost.get_legend_handles_labels()
    h2, l2 = ax_cost_t.get_legend_handles_labels()
    ax_cost.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame) -> None:
    best = metrics_df.iloc[0]
    baseline = metrics_df[metrics_df["variant"] == "baseline_btc_62_31_7_thr2"].iloc[0]
    lines: list[str] = []
    lines.append("# 101번 연구: ETHUSDT case123 weight sweep")
    lines.append("")
    lines.append("## 설정")
    lines.append("- ETHUSDT에 대해 case1/case2/case3를 실제로 다시 생성했다.")
    lines.append("- 그 위에 월 1000달러 top-up + threshold rebalance를 적용했다.")
    lines.append("- 목적은 ETH에서 BTC용 62/31/7 비중 대신 더 맞는 조합이 있는지 확인하는 것이다.")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Variant | w1 | w2 | w3 | Thr %p | Final Equity | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.head(20).iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['w1'], 2)} | {_fmt(row['w2'], 2)} | {_fmt(row['w3'], 2)} | {_fmt(row['threshold_pct'], 0)} | "
            f"{_fmt(row['final_equity'])} | {_fmt(row['twr_cagr_pct'])} | {_fmt(row['twr_mdd_pct'])} | {_fmt(row['twr_calmar_ratio'])} | "
            f"{_fmt(row['xirr_pct'])} | {int(row['rebalance_count'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append(f"- best variant: `{best['variant']}`")
    lines.append(
        f"- best vs BTC-style baseline: TWR CAGR `{_fmt(best['twr_cagr_pct'] - baseline['twr_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best['twr_mdd_pct'] - baseline['twr_mdd_pct'])}pp`, "
        f"XIRR `{_fmt(best['xirr_pct'] - baseline['xirr_pct'])}pp`."
    )
    lines.append("- ETH에서는 case2 비중을 크게 높이고, case1/case3 비중을 줄여야 살아날 가능성이 높다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 성과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- ETH sleeve 곡선 CSV: `{OUT_CASE_CURVES_CSV}`")
    lines.append(f"- 보고서: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run() -> None:
    s100 = load_module("m100_101", BASE_100_PATH)
    s86 = load_module("m86_101", BASE_86_PATH)

    print(f"[{SYMBOL}] building case curves", flush=True)
    merged_cases, _ = s100.build_symbol_case_curves(SYMBOL)
    merged_cases = merged_cases.set_index("timestamp").resample("15min").last().dropna().reset_index()
    merged_cases.to_csv(OUT_CASE_CURVES_CSV, index=False)

    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    candidates: list[tuple[tuple[float, float, float], float, str]] = []
    candidates.append(((0.62, 0.31, 0.07), 0.02, "baseline_btc_62_31_7_thr2"))
    candidates.append(((0.62, 0.31, 0.07), 0.04, "baseline_btc_62_31_7_thr4"))
    candidates.append(((0.0, 1.0, 0.0), 0.02, "case2_only_thr2"))
    candidates.append(((0.0, 1.0, 0.0), 0.04, "case2_only_thr4"))

    for threshold in THRESHOLDS:
        for w1 in W1_CANDIDATES:
            for w3 in W3_CANDIDATES:
                w2 = round(1.0 - w1 - w3, 10)
                if w2 < 0.5 - 1e-12:
                    continue
                variant = f"eth_w{int(round(w1*100)):02d}_{int(round(w2*100)):02d}_{int(round(w3*100)):02d}_thr{int(round(threshold*100)):02d}"
                candidates.append(((w1, w2, w3), threshold, variant))

    seen: set[str] = set()
    unique_candidates: list[tuple[tuple[float, float, float], float, str]] = []
    for weights, threshold, variant in candidates:
        if variant in seen:
            continue
        seen.add(variant)
        unique_candidates.append((weights, threshold, variant))

    for weights, threshold, variant in unique_candidates:
        curve, stats = run_weight_variant(merged_cases, variant, weights, threshold, s86)
        rows.append(stats)
        curve_rows.append(curve)
        curve_map[variant] = curve

    metrics_df = pd.DataFrame(rows).sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curve_rows, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(metrics_df, curve_map)
    save_report(metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_case_curves={OUT_CASE_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.head(20).to_string(index=False))


if __name__ == "__main__":
    run()
