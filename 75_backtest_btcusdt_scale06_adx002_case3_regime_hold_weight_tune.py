from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_74_PATH = Path("74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.py")

OUT_BASE = "75_backtest_btcusdt_scale06_adx002_case3_regime_hold_weight_tune"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")


def load_study74():
    spec = importlib.util.spec_from_file_location("study74_for_75", BASE_74_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {BASE_74_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame, initial_capital_total: float):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_mdd = axes

    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant in variants[:8]:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(initial_capital_total, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("75 Study: Regime-Hold Case3 Weight Tuning")
    ax_eq.set_ylabel("Total Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    top10 = metrics_df.head(10)
    ax_cagr.bar(top10["variant"], top10["total_cagr_pct"], color=[colors[v] for v in top10["variant"]], alpha=0.85, label="CAGR %")
    ax_cagr.set_ylabel("CAGR %")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr.tick_params(axis="x", rotation=20)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(top10["variant"], top10["total_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_cagr_t.set_ylabel("MDD %")
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_mdd.bar(top10["variant"], top10["w3"], color=[colors[v] for v in top10["variant"]], alpha=0.85, label="Case3 Weight")
    ax_mdd.set_ylabel("Case3 Weight")
    ax_mdd.grid(True, axis="y", alpha=0.2)
    ax_mdd.tick_params(axis="x", rotation=20)
    ax_mdd_t = ax_mdd.twinx()
    ax_mdd_t.plot(top10["variant"], top10["total_calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Calmar")
    ax_mdd_t.set_ylabel("Calmar")
    h1, l1 = ax_mdd.get_legend_handles_labels()
    h2, l2 = ax_mdd_t.get_legend_handles_labels()
    ax_mdd.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    baseline = metrics_df[metrics_df["variant"] == "baseline_70_case12_only"].iloc[0]
    best = metrics_df.iloc[0]

    lines: list[str] = []
    lines.append("# Study 75: Regime-Hold Case3 Weight Tuning")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Focus only on the promising case3 from study 74: `regime_hold_case3`.")
    lines.append("- Search region is the small-case3 zone where study 74 already found dominance over study 70.")
    lines.append("- Rebalance cadence and fee model are unchanged from studies 70 and 74.")
    lines.append("")
    lines.append("## Top 12")
    lines.append("")
    lines.append("| Variant | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Fee Paid |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.head(12).iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['w1'], 2)} | {_fmt(row['w2'], 2)} | {_fmt(row['w3'], 2)} | "
            f"{_fmt(row['total_cagr_pct'])} | {_fmt(row['total_mdd_pct'])} | {_fmt(row['total_calmar_ratio'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}`: CAGR `{_fmt(best['total_cagr_pct'])}%`, MDD `{_fmt(best['total_mdd_pct'])}%`, Calmar `{_fmt(best['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Delta vs Baseline 70")
    lines.append(
        f"- CAGR `{_fmt(best['total_cagr_pct'] - baseline['total_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best['total_mdd_pct'] - baseline['total_mdd_pct'])}pp`, "
        f"Calmar `{_fmt(best['total_calmar_ratio'] - baseline['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Interpretation")
    if ((metrics_df["total_cagr_pct"] > baseline["total_cagr_pct"]) & (metrics_df["total_mdd_pct"] < baseline["total_mdd_pct"])).any():
        lines.append("- Multiple tuned case3 weights dominate the two-sleeve study-70 baseline on both CAGR and MDD.")
    else:
        lines.append("- No tuned case3 weight dominates the two-sleeve study-70 baseline on both CAGR and MDD.")
    lines.append("- If the optimum keeps case3 small, then regime-hold works as a diversifier rather than a main return engine.")
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
    case3 = s74.load_case3(s74.CASE3_REGIME_CSV, "dual_stop6", "regime_hold_case3")
    merged = s74.build_merged(case1, case2, case3, "regime_hold_case3")

    rows: list[dict] = []
    curve_map: dict[str, pd.DataFrame] = {}

    baseline_out, baseline_run = s74.run_three_sleeve(merged, "regime_hold_case3", 0.74, 0.26, 0.00)
    baseline_out["variant"] = "baseline_70_case12_only"
    baseline_stats = s74.compute_curve_stats(baseline_out, "equity_total", s74.INITIAL_CAPITAL_TOTAL)
    rows.append(
        {
            "variant": "baseline_70_case12_only",
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

    for w1_pct in range(60, 75):
        for w3_pct in range(1, 9):
            w1 = w1_pct / 100.0
            w3 = w3_pct / 100.0
            w2 = 1.0 - w1 - w3
            if w2 < 0.20:
                continue
            out, run_stats = s74.run_three_sleeve(merged, "regime_hold_case3", w1, w2, w3)
            stats = s74.compute_curve_stats(out, "equity_total", s74.INITIAL_CAPITAL_TOTAL)
            variant = f"regime_hold_case3_w{w1_pct}_{int(round(w2*100))}_{w3_pct}"
            out["variant"] = variant
            rows.append(
                {
                    "variant": variant,
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
    selected = ["baseline_70_case12_only"] + [v for v in metrics_df.head(12)["variant"].tolist() if v != "baseline_70_case12_only"]
    curves_df = pd.concat([curve_map[v] for v in selected], ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df, s74.INITIAL_CAPITAL_TOTAL)
    save_report(metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.head(20).to_string(index=False))


if __name__ == "__main__":
    run()
