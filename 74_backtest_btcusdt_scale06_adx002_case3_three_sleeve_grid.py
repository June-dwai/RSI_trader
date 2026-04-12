from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


CASE12_CURVES_CSV = Path("62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune_curves.csv")
CASE3_REGIME_CSV = Path("73_backtest_btcusdt_scale06_adx002_regime_hold_tune_curves.csv")
CASE3_COMPRESSION_CSV = Path("71_backtest_btcusdt_scale06_adx002_alt_mindset_archetypes_curves.csv")

OUT_BASE = "74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

CASE12_VARIANT = "shallow6_else2bull"
INITIAL_CAPITAL_TOTAL = 2000.0
REBALANCE_FEE_RATE = 0.0004

BASELINE_70 = {
    "cagr_pct": 117.745356,
    "mdd_pct": 49.150948,
    "calmar": 2.395587,
}

CANDIDATES = [
    {"case3_name": "regime_hold_case3", "path": CASE3_REGIME_CSV, "variant": "dual_stop6"},
    {"case3_name": "compression_case3", "path": CASE3_COMPRESSION_CSV, "variant": "compression_breakout_dual"},
]


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def compute_curve_stats(curve: pd.DataFrame, col: str, initial_capital: float) -> dict:
    series = curve[col].astype(float)
    final_equity = float(series.iloc[-1])
    total_return_pct = ((final_equity / float(initial_capital)) - 1.0) * 100.0

    elapsed_days = (curve["timestamp"].iloc[-1] - curve["timestamp"].iloc[0]).total_seconds() / 86400.0
    years = max(elapsed_days / 365.25, 1e-9)
    cagr_pct = ((final_equity / float(initial_capital)) ** (1.0 / years) - 1.0) * 100.0

    dd = series / series.cummax() - 1.0
    max_drawdown_pct = float(-dd.min() * 100.0)
    calmar_ratio = float(cagr_pct / max_drawdown_pct) if max_drawdown_pct > 0 else np.nan
    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "calmar_ratio": calmar_ratio,
    }


def load_case12() -> tuple[pd.DataFrame, pd.DataFrame]:
    curves = pd.read_csv(CASE12_CURVES_CSV, parse_dates=["timestamp"])
    ref = curves[curves["variant"] == CASE12_VARIANT].copy()
    if ref.empty:
        raise ValueError(f"missing case12 variant: {CASE12_VARIANT}")
    ref = ref.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)
    case1 = ref[["timestamp", "equity_case1"]].rename(columns={"equity_case1": "equity_case1"}).copy()
    case2 = ref[["timestamp", "equity_case2"]].rename(columns={"equity_case2": "equity_case2"}).copy()
    return case1, case2


def load_case3(path: Path, variant: str, case3_name: str) -> pd.DataFrame:
    curves = pd.read_csv(path, parse_dates=["timestamp"])
    ref = curves[curves["variant"] == variant].copy()
    if ref.empty:
        raise ValueError(f"missing case3 variant {variant} in {path}")
    ref = ref.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)
    return ref[["timestamp", "equity"]].rename(columns={"equity": case3_name})


def build_merged(case1: pd.DataFrame, case2: pd.DataFrame, case3: pd.DataFrame, case3_name: str) -> pd.DataFrame:
    merged = pd.merge(case1, case2, on="timestamp", how="outer")
    merged = pd.merge(merged, case3, on="timestamp", how="outer")
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged[case3_name] = merged[case3_name].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2", case3_name]).copy()
    return merged


def run_three_sleeve(merged: pd.DataFrame, case3_name: str, w1: float, w2: float, w3: float) -> tuple[pd.DataFrame, dict]:
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret3 = merged[case3_name].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"]
    rebal_flags = (ts.dt.floor("4h") != ts.dt.floor("4h").shift(1)).to_numpy()

    cap1 = np.zeros(len(merged), dtype=float)
    cap2 = np.zeros(len(merged), dtype=float)
    cap3 = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    fee_paid = 0.0
    rebalance_count = 0

    cap1[0] = INITIAL_CAPITAL_TOTAL * w1
    cap2[0] = INITIAL_CAPITAL_TOTAL * w2
    cap3[0] = INITIAL_CAPITAL_TOTAL * w3
    total[0] = cap1[0] + cap2[0] + cap3[0]

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        c3 = cap3[i - 1] * (1.0 + float(ret3[i]))
        cur_total = c1 + c2 + c3

        if rebal_flags[i]:
            target1 = cur_total * w1
            target2 = cur_total * w2
            target3 = cur_total * w3
            fee = (
                abs(target1 - c1)
                + abs(target2 - c2)
                + abs(target3 - c3)
            ) * REBALANCE_FEE_RATE
            cur_total -= fee
            c1 = cur_total * w1
            c2 = cur_total * w2
            c3 = cur_total * w3
            fee_paid += fee
            rebalance_count += 1

        cap1[i] = c1
        cap2[i] = c2
        cap3[i] = c3
        total[i] = cur_total

    out = merged[["timestamp"]].copy()
    out["equity_total"] = total
    out["cap1"] = cap1
    out["cap2"] = cap2
    out["cap3"] = cap3
    out["w1"] = w1
    out["w2"] = w2
    out["w3"] = w3
    return out, {"rebalance_count": rebalance_count, "fee_paid": fee_paid}


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
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
    ax_eq.axhline(INITIAL_CAPITAL_TOTAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("74 Study: Three-Sleeve Grid With Case3 Candidates")
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
    lines.append("# Study 74: Three-Sleeve Grid With Case3 Candidates")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Baseline is the study-70 winner: `case1 74% / case2 26%`, 4h rebalance, fee-aware.")
    lines.append("- Candidate case3 sleeves are:")
    lines.append("  regime-hold tuned winner from study 73 (`dual_stop6`)")
    lines.append("  compression-breakout candidate from study 71 (`compression_breakout_dual`)")
    lines.append("- Total capital is fixed; weights are reallocated across three sleeves rather than adding new capital.")
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
    lines.append("## Delta vs Baseline 70")
    lines.append(
        f"- CAGR `{_fmt(best['total_cagr_pct'] - baseline['total_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best['total_mdd_pct'] - baseline['total_mdd_pct'])}pp`, "
        f"Calmar `{_fmt(best['total_calmar_ratio'] - baseline['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Interpretation")
    if ((metrics_df["total_cagr_pct"] > baseline["total_cagr_pct"]) & (metrics_df["total_mdd_pct"] < baseline["total_mdd_pct"])).any():
        lines.append("- At least one three-sleeve mix dominated the two-sleeve study-70 baseline on both CAGR and MDD.")
    else:
        lines.append("- No three-sleeve mix dominated the two-sleeve study-70 baseline on both CAGR and MDD.")
    lines.append("- If small case3 weights rank well, then these alternate mindsets are portfolio diversifiers rather than standalone engines.")
    lines.append("- If even tiny case3 allocations hurt, then they should stay in the idea backlog rather than entering the live mix.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    case1, case2 = load_case12()
    all_rows: list[dict] = []
    top_curves: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for candidate in CANDIDATES:
        case3_name = str(candidate["case3_name"])
        case3 = load_case3(Path(candidate["path"]), str(candidate["variant"]), case3_name)
        merged = build_merged(case1, case2, case3, case3_name)

        weight_grid = []
        for w1 in np.arange(0.60, 0.81, 0.02):
            for w3 in np.arange(0.00, 0.21, 0.02):
                w2 = 1.0 - float(w1) - float(w3)
                if w2 < 0.08:
                    continue
                weight_grid.append((round(float(w1), 2), round(float(w2), 2), round(float(w3), 2)))

        for w1, w2, w3 in weight_grid:
            out, run_stats = run_three_sleeve(merged, case3_name, w1, w2, w3)
            stats = compute_curve_stats(out, "equity_total", INITIAL_CAPITAL_TOTAL)
            variant = f"{case3_name}_w{int(round(w1*100))}_{int(round(w2*100))}_{int(round(w3*100))}"
            out["variant"] = variant
            all_rows.append(
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

    baseline_variant = "baseline_70_case12_only"
    baseline_merged = build_merged(case1, case2, load_case3(CASE3_REGIME_CSV, "dual_stop6", "regime_hold_case3"), "regime_hold_case3")
    baseline_out, baseline_stats_run = run_three_sleeve(baseline_merged, "regime_hold_case3", 0.74, 0.26, 0.00)
    baseline_out["variant"] = baseline_variant
    baseline_stats = compute_curve_stats(baseline_out, "equity_total", INITIAL_CAPITAL_TOTAL)
    all_rows.append(
        {
            "variant": baseline_variant,
            "case3_name": "none",
            "w1": 0.74,
            "w2": 0.26,
            "w3": 0.00,
            "total_final_equity": baseline_stats["final_equity"],
            "total_return_pct": baseline_stats["total_return_pct"],
            "total_cagr_pct": baseline_stats["cagr_pct"],
            "total_mdd_pct": baseline_stats["max_drawdown_pct"],
            "total_calmar_ratio": baseline_stats["calmar_ratio"],
            "rebalance_count": baseline_stats_run["rebalance_count"],
            "fee_paid": baseline_stats_run["fee_paid"],
        }
    )
    curve_map[baseline_variant] = baseline_out

    metrics_df = pd.DataFrame(all_rows).sort_values(["total_calmar_ratio", "total_cagr_pct"], ascending=[False, False]).reset_index(drop=True)
    selected_variants = [baseline_variant] + [v for v in metrics_df.head(12)["variant"].tolist() if v != baseline_variant]
    for variant in selected_variants:
        top_curves.append(curve_map[variant])
    curves_df = pd.concat(top_curves, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df)
    save_report(metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.head(20).to_string(index=False))


if __name__ == "__main__":
    run()
