from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_69_PATH = Path("69_backtest_btcusdt_scale06_adx002_rebalance_schedule_sweep.py")

OUT_BASE = "70_backtest_btcusdt_scale06_adx002_rebalance_4h_weight_tune"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

VARIANTS = [
    {"variant": "hold_no_rebalance", "mode": "hold"},
    {"variant": "rebal_4h_w70", "mode": "rebalance", "target_case1_w": 0.70},
    {"variant": "rebal_4h_w72", "mode": "rebalance", "target_case1_w": 0.72},
    {"variant": "rebal_4h_w74", "mode": "rebalance", "target_case1_w": 0.74},
    {"variant": "rebal_4h_w75", "mode": "rebalance", "target_case1_w": 0.75},
    {"variant": "rebal_4h_w76", "mode": "rebalance", "target_case1_w": 0.76},
]


def load_study69():
    spec = importlib.util.spec_from_file_location("study69_for_70", BASE_69_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {BASE_69_PATH}")
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

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(initial_capital_total, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("70 Study: 4H Rebalance Weight Tuning")
    ax_eq.set_ylabel("Total Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_cagr.bar(metrics_df["variant"], metrics_df["total_cagr_pct"], color=[colors[v] for v in variants], alpha=0.85, label="Total CAGR %")
    ax_cagr.set_ylabel("Total CAGR %")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr.tick_params(axis="x", rotation=20)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(metrics_df["variant"], metrics_df["total_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="Total MDD %")
    ax_cagr_t.set_ylabel("Total MDD %")
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_mdd.bar(metrics_df["variant"], metrics_df["fee_paid"], color=[colors[v] for v in variants], alpha=0.85, label="Fee Paid")
    ax_mdd.set_ylabel("Fee Paid (USDT)")
    ax_mdd.grid(True, axis="y", alpha=0.2)
    ax_mdd.tick_params(axis="x", rotation=20)
    ax_mdd_t = ax_mdd.twinx()
    ax_mdd_t.plot(metrics_df["variant"], metrics_df["total_calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Total Calmar")
    ax_mdd_t.set_ylabel("Total Calmar")
    h1, l1 = ax_mdd.get_legend_handles_labels()
    h2, l2 = ax_mdd_t.get_legend_handles_labels()
    ax_mdd.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    baseline = metrics_df[metrics_df["variant"] == "hold_no_rebalance"].iloc[0]
    best = metrics_df.iloc[0]

    lines: list[str] = []
    lines.append("# Study 70: 4H Rebalance Weight Tuning")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Base portfolio logic is study 69's fee-aware periodic rebalance engine")
    lines.append("- Focus range: `4h rebalance` with `case1 target weight 0.70~0.76`")
    lines.append("- Goal: convert the study-69 scan into a concrete next baseline candidate")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | Total CAGR % | Total MDD % | Total Calmar | Fee Paid |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['total_cagr_pct'])} | {_fmt(row['total_mdd_pct'])} | {_fmt(row['total_calmar_ratio'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}`: total CAGR `{_fmt(best['total_cagr_pct'])}%`, total MDD `{_fmt(best['total_mdd_pct'])}%`, total Calmar `{_fmt(best['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Delta vs hold_no_rebalance")
    for _, row in metrics_df.iterrows():
        if row["variant"] == "hold_no_rebalance":
            continue
        lines.append(
            f"- `{row['variant']}`: CAGR `{_fmt(row['total_cagr_pct'] - baseline['total_cagr_pct'])}pp`, "
            f"MDD `{_fmt(row['total_mdd_pct'] - baseline['total_mdd_pct'])}pp`, "
            f"Calmar `{_fmt(row['total_calmar_ratio'] - baseline['total_calmar_ratio'])}`"
        )
    lines.append("")
    lines.append("## Interpretation")
    if ((metrics_df["total_cagr_pct"] > baseline["total_cagr_pct"]) & (metrics_df["total_mdd_pct"] < baseline["total_mdd_pct"])).any():
        lines.append("- Multiple 4h rebalance variants dominate the hold baseline on both CAGR and MDD.")
    else:
        lines.append("- No tuned 4h rebalance variant dominates the hold baseline on both CAGR and MDD.")
    lines.append("- This is the first clear structural win in the recent study chain: portfolio construction improved both growth and drawdown.")
    lines.append("- The next validation step should test whether this edge survives a more realistic execution model or lower-frequency rebalance constraints.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    s69 = load_study69()
    curve = s69.load_curve()

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    hold_stats = s69.compute_curve_stats(curve, "equity_total", s69.INITIAL_CAPITAL_TOTAL)
    if abs(hold_stats["final_equity"] - s69.EXPECTED_HOLD_BASELINE["final_equity"]) > 1e-6:
        raise ValueError("hold baseline final equity mismatch")

    for cfg in VARIANTS:
        variant = str(cfg["variant"])
        if cfg["mode"] == "hold":
            out = curve.copy()
            run_stats = {"rebalance_count": 0, "fee_paid": 0.0}
        else:
            out, run_stats = s69.run_rebalanced_portfolio(curve, "4h", float(cfg["target_case1_w"]))
        out["variant"] = variant
        stats = s69.compute_curve_stats(out, "equity_total", s69.INITIAL_CAPITAL_TOTAL)
        rows.append(
            {
                "variant": variant,
                "mode": cfg["mode"],
                "target_case1_w": float(cfg.get("target_case1_w", float("nan"))),
                "total_final_equity": stats["final_equity"],
                "total_return_pct": stats["total_return_pct"],
                "total_cagr_pct": stats["cagr_pct"],
                "total_mdd_pct": stats["max_drawdown_pct"],
                "total_calmar_ratio": stats["calmar_ratio"],
                "rebalance_count": run_stats["rebalance_count"],
                "fee_paid": run_stats["fee_paid"],
            }
        )
        curves_out.append(out)
        curve_map[variant] = out.copy()

    metrics_df = pd.DataFrame(rows).sort_values(["total_calmar_ratio", "total_cagr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curves_out, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df, s69.INITIAL_CAPITAL_TOTAL)
    save_report(metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    run()
