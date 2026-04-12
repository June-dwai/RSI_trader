from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_74_PATH = Path("74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.py")
BASE_75_CSV = Path("75_backtest_btcusdt_scale06_adx002_case3_regime_hold_weight_tune.csv")
CASE3_SHORTTP_CSV = Path("80_backtest_btcusdt_scale06_adx002_regime_hold_short_tp_tune_curves.csv")

OUT_BASE = "81_backtest_btcusdt_scale06_adx002_case3_shorttp_portfolio_grid"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

CANDIDATES = [
    {"case3_name": "shorttp15_15x_case3", "variant": "short_tp15_lock_1.5x"},
]

W1_PCTS = [60, 61]
W3_PCTS = [5, 6]


def load_study74():
    spec = importlib.util.spec_from_file_location("study74_for_81", BASE_74_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {BASE_74_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def load_prev_best() -> pd.Series:
    df = pd.read_csv(BASE_75_CSV)
    baseline = df[df["variant"] == "baseline_70_case12_only"].iloc[0]
    dominating = df[(df["total_cagr_pct"] > baseline["total_cagr_pct"]) & (df["total_mdd_pct"] < baseline["total_mdd_pct"])]
    if dominating.empty:
        return df.iloc[0]
    return dominating.sort_values(["total_calmar_ratio", "total_cagr_pct"], ascending=[False, False]).iloc[0]


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame, initial_capital_total: float):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_w = axes

    cmap = plt.get_cmap("tab20")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 20) for i, v in enumerate(variants)}

    for variant in variants[:10]:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(initial_capital_total, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("81 Study: Short-TP Regime-Hold as Case3")
    ax_eq.set_ylabel("Total Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    top = metrics_df.head(12)
    ax_cagr.bar(top["variant"], top["total_cagr_pct"], color=[colors[v] for v in top["variant"]], alpha=0.85, label="CAGR %")
    ax_cagr.set_ylabel("CAGR %")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr.tick_params(axis="x", rotation=20)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(top["variant"], top["total_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_cagr_t.set_ylabel("MDD %")
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_w.bar(top["variant"], top["w3"], color=[colors[v] for v in top["variant"]], alpha=0.85, label="Case3 Weight")
    ax_w.set_ylabel("Case3 Weight")
    ax_w.grid(True, axis="y", alpha=0.2)
    ax_w.tick_params(axis="x", rotation=20)
    ax_w_t = ax_w.twinx()
    ax_w_t.plot(top["variant"], top["total_calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Calmar")
    ax_w_t.set_ylabel("Calmar")
    h1, l1 = ax_w.get_legend_handles_labels()
    h2, l2 = ax_w_t.get_legend_handles_labels()
    ax_w.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, baseline70: pd.Series, prev_best: pd.Series):
    best = metrics_df.iloc[0]

    lines: list[str] = []
    lines.append("# Study 81: Short-TP Regime-Hold as Case3")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Baseline comparison remains the study-70 two-sleeve winner: `case1 74% / case2 26%`, 4h rebalance, fee-aware.")
    lines.append("- New case3 candidates come from study 80, where short-only TP-lock materially improved standalone regime-hold.")
    lines.append("- Search region focuses on small-to-moderate case3 weights (`4%~10%`) and the prior winning case1/case2 zone.")
    lines.append("")
    lines.append("## Top 12")
    lines.append("")
    lines.append("| Variant | Case3 | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Fee Paid |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.head(12).iterrows():
        lines.append(
            f"| {row['variant']} | {row['case3_name']} | {_fmt(row['w1'], 2)} | {_fmt(row['w2'], 2)} | {_fmt(row['w3'], 2)} | "
            f"{_fmt(row['total_cagr_pct'])} | {_fmt(row['total_mdd_pct'])} | {_fmt(row['total_calmar_ratio'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}`: CAGR `{_fmt(best['total_cagr_pct'])}%`, MDD `{_fmt(best['total_mdd_pct'])}%`, Calmar `{_fmt(best['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Delta vs Study 70 Baseline")
    lines.append(
        f"- CAGR `{_fmt(best['total_cagr_pct'] - baseline70['total_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best['total_mdd_pct'] - baseline70['total_mdd_pct'])}pp`, "
        f"Calmar `{_fmt(best['total_calmar_ratio'] - baseline70['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Delta vs Prior Best Case3 Mix")
    lines.append(
        f"- Prior best from study 75: `{prev_best['variant']}` with CAGR `{_fmt(prev_best['total_cagr_pct'])}%`, "
        f"MDD `{_fmt(prev_best['total_mdd_pct'])}%`, Calmar `{_fmt(prev_best['total_calmar_ratio'])}`"
    )
    lines.append(
        f"- New best delta: CAGR `{_fmt(best['total_cagr_pct'] - prev_best['total_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best['total_mdd_pct'] - prev_best['total_mdd_pct'])}pp`, "
        f"Calmar `{_fmt(best['total_calmar_ratio'] - prev_best['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Interpretation")
    if ((metrics_df["total_cagr_pct"] > baseline70["total_cagr_pct"]) & (metrics_df["total_mdd_pct"] < baseline70["total_mdd_pct"])).any():
        lines.append("- At least one short-TP case3 mix dominates the study-70 two-sleeve baseline on both CAGR and MDD.")
    else:
        lines.append("- No short-TP case3 mix dominates the study-70 two-sleeve baseline on both CAGR and MDD.")
    if best["total_calmar_ratio"] > float(prev_best["total_calmar_ratio"]):
        lines.append("- The improved short-TP regime-hold also beats the prior study-75 case3 leader on Calmar.")
    else:
        lines.append("- The improved short-TP regime-hold does not beat the prior study-75 case3 leader on Calmar.")
    lines.append("- If the best weight stays small, this is still a diversifier sleeve rather than a core return engine.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    s74 = load_study74()
    case1, case2 = s74.load_case12()
    baseline70 = pd.Series(
        {
            "variant": "baseline_70_case12_only",
            "total_cagr_pct": float(s74.BASELINE_70["cagr_pct"]),
            "total_mdd_pct": float(s74.BASELINE_70["mdd_pct"]),
            "total_calmar_ratio": float(s74.BASELINE_70["calmar"]),
        }
    )
    prev_best = load_prev_best()

    rows: list[dict] = []
    curve_map: dict[str, pd.DataFrame] = {}

    baseline_case3 = s74.load_case3(CASE3_SHORTTP_CSV, CANDIDATES[0]["variant"], CANDIDATES[0]["case3_name"])
    baseline_common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), baseline_case3["timestamp"].min())
    baseline_common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), baseline_case3["timestamp"].max())
    baseline_merged = s74.build_merged(
        case1[(case1["timestamp"] >= baseline_common_start) & (case1["timestamp"] <= baseline_common_end)].copy(),
        case2[(case2["timestamp"] >= baseline_common_start) & (case2["timestamp"] <= baseline_common_end)].copy(),
        baseline_case3[(baseline_case3["timestamp"] >= baseline_common_start) & (baseline_case3["timestamp"] <= baseline_common_end)].copy(),
        CANDIDATES[0]["case3_name"],
    )
    baseline_out, baseline_run = s74.run_three_sleeve(
        baseline_merged,
        CANDIDATES[0]["case3_name"],
        0.74,
        0.26,
        0.00,
    )
    baseline_stats = s74.compute_curve_stats(baseline_out, "equity_total", s74.INITIAL_CAPITAL_TOTAL)
    rows.append(
        {
            "variant": "baseline_70_case12_only",
            "case3_name": "none",
            "w1": 0.74,
            "w2": 0.26,
            "w3": 0.00,
            "total_final_equity": baseline_stats["final_equity"],
            "total_return_pct": baseline_stats["total_return_pct"],
            "total_cagr_pct": baseline_stats["cagr_pct"],
            "total_mdd_pct": baseline_stats["max_drawdown_pct"],
            "total_calmar_ratio": baseline_stats["calmar_ratio"],
            "rebalance_count": baseline_run["rebalance_count"],
            "fee_paid": baseline_run["fee_paid"],
        }
    )
    curve_map["baseline_70_case12_only"] = baseline_out

    for candidate in CANDIDATES:
        case3_name = str(candidate["case3_name"])
        case3 = s74.load_case3(CASE3_SHORTTP_CSV, str(candidate["variant"]), case3_name)
        common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
        common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())
        case1_clip = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)].copy()
        case2_clip = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy()
        case3_clip = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)].copy()
        merged = s74.build_merged(case1_clip, case2_clip, case3_clip, case3_name)

        for w1_pct in W1_PCTS:
            for w3_pct in W3_PCTS:
                w1 = w1_pct / 100.0
                w3 = w3_pct / 100.0
                w2 = 1.0 - w1 - w3
                if w2 <= 0:
                    continue

                out, run_stats = s74.run_three_sleeve(merged, case3_name, w1, w2, w3)
                stats = s74.compute_curve_stats(out, "equity_total", s74.INITIAL_CAPITAL_TOTAL)
                variant = f"{case3_name}_w{w1_pct}_{int(round(w2 * 100))}_{w3_pct}"
                rows.append(
                    {
                        "variant": variant,
                        "case3_name": case3_name,
                        "w1": w1,
                        "w2": w2,
                        "w3": w3,
                        "total_final_equity": stats["final_equity"],
                        "total_return_pct": stats["total_return_pct"],
                        "total_cagr_pct": stats["cagr_pct"],
                        "total_mdd_pct": stats["max_drawdown_pct"],
                        "total_calmar_ratio": stats["calmar_ratio"],
                        "rebalance_count": run_stats["rebalance_count"],
                        "fee_paid": run_stats["fee_paid"],
                    }
                )
                curve_map[variant] = out

    metrics_df = pd.DataFrame(rows).sort_values(["total_calmar_ratio", "total_cagr_pct"], ascending=[False, False]).reset_index(drop=True)
    selected = ["baseline_70_case12_only"] + metrics_df.head(11)["variant"].tolist()
    curves_df = pd.concat([curve_map[v] for v in dict.fromkeys(selected)], ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df, s74.INITIAL_CAPITAL_TOTAL)
    save_report(metrics_df, baseline70, prev_best)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.head(20).to_string(index=False))


if __name__ == "__main__":
    run()
