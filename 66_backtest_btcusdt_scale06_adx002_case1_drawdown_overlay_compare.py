from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT_CURVES_CSV = Path("62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune_curves.csv")

OUT_BASE = "66_backtest_btcusdt_scale06_adx002_case1_drawdown_overlay_compare"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

INITIAL_CAPITAL_CASE = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0

SOURCE_VARIANT = "shallow6_else2bull"
BASELINE_VARIANT = "release1bull"

VARIANTS = [
    {"variant": "release1bull_baseline", "mode": "baseline_release1"},
    {"variant": "shallow6_no_overlay", "mode": "source_shallow6"},
    {"variant": "dd15_to75_restore10", "mode": "overlay", "trigger_dd_pct": 15.0, "restore_dd_pct": 10.0, "reduced_weight": 0.75},
    {"variant": "dd20_to50_restore12", "mode": "overlay", "trigger_dd_pct": 20.0, "restore_dd_pct": 12.0, "reduced_weight": 0.50},
    {"variant": "dd25_to50_restore15", "mode": "overlay", "trigger_dd_pct": 25.0, "restore_dd_pct": 15.0, "reduced_weight": 0.50},
    {"variant": "dd30_to25_restore20", "mode": "overlay", "trigger_dd_pct": 30.0, "restore_dd_pct": 20.0, "reduced_weight": 0.25},
]

EXPECTED_RELEASE1_TOTAL = {
    "final_equity": 35703.728400496766,
    "cagr_pct": 101.4673658152283,
    "mdd_pct": 50.338739340819494,
}
EXPECTED_SHALLOW6_TOTAL = {
    "final_equity": 37042.70606845802,
    "cagr_pct": 103.27812652063195,
    "mdd_pct": 50.853607894861834,
}


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


def load_curves() -> tuple[pd.DataFrame, pd.DataFrame]:
    curves = pd.read_csv(INPUT_CURVES_CSV, parse_dates=["timestamp"])
    source = curves[curves["variant"] == SOURCE_VARIANT].copy().sort_values("timestamp").reset_index(drop=True)
    baseline = curves[curves["variant"] == BASELINE_VARIANT].copy().sort_values("timestamp").reset_index(drop=True)
    if source.empty or baseline.empty:
        raise ValueError("missing source or baseline variant in curves file")
    return source, baseline


def apply_drawdown_overlay(source_curve: pd.DataFrame, trigger_dd_pct: float, restore_dd_pct: float, reduced_weight: float) -> pd.DataFrame:
    curve = source_curve[["timestamp", "equity_case1", "equity_case2"]].copy().reset_index(drop=True)
    source_case1 = curve["equity_case1"].astype(float)
    source_ret = source_case1.pct_change().fillna(0.0)
    source_dd = (source_case1 / source_case1.cummax() - 1.0).fillna(0.0) * -100.0

    overlay_eq = np.zeros(len(curve), dtype=float)
    weights = np.zeros(len(curve), dtype=float)
    reduced_state = False
    overlay_eq[0] = INITIAL_CAPITAL_CASE
    weights[0] = 1.0

    for i in range(1, len(curve)):
        dd_prev = float(source_dd.iloc[i - 1])
        if reduced_state:
            if dd_prev <= restore_dd_pct:
                reduced_state = False
        else:
            if dd_prev >= trigger_dd_pct:
                reduced_state = True
        weight = reduced_weight if reduced_state else 1.0
        overlay_eq[i] = overlay_eq[i - 1] * (1.0 + weight * float(source_ret.iloc[i]))
        weights[i] = weight

    out = curve.copy()
    out["equity_case1_overlay"] = overlay_eq
    out["overlay_weight"] = weights
    out["equity_total_overlay"] = out["equity_case1_overlay"] + out["equity_case2"].astype(float)
    return out


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_mdd = axes

    cmap = plt.get_cmap("viridis")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i / max(1, len(variants) - 1)) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(INITIAL_CAPITAL_TOTAL, color="#777777", linestyle="--", linewidth=0.9, label=f"Start {INITIAL_CAPITAL_TOTAL:.0f}")
    ax_eq.set_title("66 Study: Case1 Drawdown Overlay Variants + Fixed Case2")
    ax_eq.set_ylabel("Total Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_cagr.bar(metrics_df["variant"], metrics_df["total_final_equity"], color=[colors[v] for v in variants], alpha=0.85, label="Total Final Equity")
    ax_cagr.set_ylabel("Total Final Equity")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr.tick_params(axis="x", rotation=20)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(metrics_df["variant"], metrics_df["total_cagr_pct"], color="#d62728", marker="o", linewidth=1.1, label="Total CAGR %")
    ax_cagr_t.set_ylabel("Total CAGR %")
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_mdd.bar(metrics_df["variant"], metrics_df["total_mdd_pct"], color=[colors[v] for v in variants], alpha=0.85, label="Total MDD %")
    ax_mdd.set_ylabel("Total MDD %")
    ax_mdd.grid(True, axis="y", alpha=0.2)
    ax_mdd.tick_params(axis="x", rotation=20)
    ax_mdd_t = ax_mdd.twinx()
    ax_mdd_t.plot(metrics_df["variant"], metrics_df["total_calmar_ratio"], color="#1f77b4", marker="o", linewidth=1.1, label="Total Calmar")
    ax_mdd_t.set_ylabel("Total Calmar")
    h3, l3 = ax_mdd.get_legend_handles_labels()
    h4, l4 = ax_mdd_t.get_legend_handles_labels()
    ax_mdd.legend(h3 + h4, l3 + l4, loc="upper left")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    best_cagr = metrics_df.sort_values("total_cagr_pct", ascending=False).iloc[0]
    best_mdd = metrics_df.sort_values("total_mdd_pct", ascending=True).iloc[0]
    best_calmar = metrics_df.sort_values("total_calmar_ratio", ascending=False).iloc[0]
    baseline = metrics_df[metrics_df["variant"] == "release1bull_baseline"].iloc[0]
    improved = metrics_df[
        (metrics_df["total_cagr_pct"] > baseline["total_cagr_pct"])
        & (metrics_df["total_mdd_pct"] < baseline["total_mdd_pct"])
    ].copy()

    lines: list[str] = []
    lines.append("# 66 Backtest: Case1 Drawdown Overlay Variants")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Baseline reference is `release1bull` from study 62.")
    lines.append("- Overlay source is `shallow6_else2bull` from study 62, which had the best total Calmar among the pure case1 logic variants.")
    lines.append("- Overlay rule uses only lagged case1 drawdown from the source curve. If case1 drawdown breaches the trigger, the next-minute case1 exposure is reduced to the configured weight until drawdown recovers below the restore level.")
    lines.append("- `case2` remains fully invested and unchanged.")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Variant | Mode | Trigger DD % | Restore DD % | Reduced Weight | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['variant']}` | `{r['mode']}` | {_fmt(r['trigger_dd_pct'])} | {_fmt(r['restore_dd_pct'])} | {_fmt(r['reduced_weight'] * 100.0)} | "
            f"{_fmt(r['total_final_equity'])} | {_fmt(r['total_cagr_pct'])} | {_fmt(r['total_mdd_pct'])} | {_fmt(r['total_calmar_ratio'])} |"
        )
    lines.append("")
    lines.append("## Best Cases")
    lines.append(f"- Best total CAGR: `{best_cagr['variant']}` (`{_fmt(best_cagr['total_cagr_pct'])}%`).")
    lines.append(f"- Lowest total MDD: `{best_mdd['variant']}` (`{_fmt(best_mdd['total_mdd_pct'])}%`).")
    lines.append(f"- Best total Calmar: `{best_calmar['variant']}` (`{_fmt(best_calmar['total_calmar_ratio'])}`).")
    lines.append("")
    lines.append("## Delta vs release1bull_baseline")
    lines.append("| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['variant']}` | {_fmt(r['total_final_equity'] - baseline['total_final_equity'])} | "
            f"{_fmt(r['total_cagr_pct'] - baseline['total_cagr_pct'])} | "
            f"{_fmt(r['total_mdd_pct'] - baseline['total_mdd_pct'])} | "
            f"{_fmt(r['total_calmar_ratio'] - baseline['total_calmar_ratio'])} |"
        )
    lines.append("")
    lines.append("## Dominance Check")
    if improved.empty:
        lines.append("- No tested overlay achieved both `higher total CAGR` and `lower total MDD` than `release1bull_baseline`.")
    else:
        for _, r in improved.iterrows():
            lines.append(
                f"- `{r['variant']}` dominates baseline: CAGR `{_fmt(r['total_cagr_pct'])}%` vs `{_fmt(baseline['total_cagr_pct'])}%`, "
                f"MDD `{_fmt(r['total_mdd_pct'])}%` vs `{_fmt(baseline['total_mdd_pct'])}%`."
            )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If an overlay helps, it means the alpha engine is still useful but should not be fully invested through its own deep drawdowns.")
    lines.append("- If all overlays fail, then the remaining problem is not allocation but the underlying case1 alpha quality under stress.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    source_curve, baseline_curve = load_curves()

    release1_stats = compute_curve_stats(baseline_curve, "equity_total", INITIAL_CAPITAL_TOTAL)
    if abs(release1_stats["final_equity"] - EXPECTED_RELEASE1_TOTAL["final_equity"]) > 1e-6:
        raise ValueError("release1 baseline final equity mismatch")
    if abs(release1_stats["cagr_pct"] - EXPECTED_RELEASE1_TOTAL["cagr_pct"]) > 1e-6:
        raise ValueError("release1 baseline cagr mismatch")
    if abs(release1_stats["max_drawdown_pct"] - EXPECTED_RELEASE1_TOTAL["mdd_pct"]) > 1e-6:
        raise ValueError("release1 baseline mdd mismatch")

    shallow6_stats = compute_curve_stats(source_curve, "equity_total", INITIAL_CAPITAL_TOTAL)
    if abs(shallow6_stats["final_equity"] - EXPECTED_SHALLOW6_TOTAL["final_equity"]) > 1e-6:
        raise ValueError("shallow6 final equity mismatch")
    if abs(shallow6_stats["cagr_pct"] - EXPECTED_SHALLOW6_TOTAL["cagr_pct"]) > 1e-6:
        raise ValueError("shallow6 cagr mismatch")
    if abs(shallow6_stats["max_drawdown_pct"] - EXPECTED_SHALLOW6_TOTAL["mdd_pct"]) > 1e-6:
        raise ValueError("shallow6 mdd mismatch")

    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        variant = str(cfg["variant"])
        mode = str(cfg["mode"])

        if mode == "baseline_release1":
            curve = baseline_curve[["timestamp", "equity_case1", "equity_case2", "equity_total"]].copy()
            curve["overlay_weight"] = 1.0
            stats = compute_curve_stats(curve, "equity_total", INITIAL_CAPITAL_TOTAL)
        elif mode == "source_shallow6":
            curve = source_curve[["timestamp", "equity_case1", "equity_case2", "equity_total"]].copy()
            curve["overlay_weight"] = 1.0
            stats = compute_curve_stats(curve, "equity_total", INITIAL_CAPITAL_TOTAL)
        else:
            overlay_curve = apply_drawdown_overlay(
                source_curve,
                trigger_dd_pct=float(cfg["trigger_dd_pct"]),
                restore_dd_pct=float(cfg["restore_dd_pct"]),
                reduced_weight=float(cfg["reduced_weight"]),
            )
            curve = overlay_curve[["timestamp", "equity_case1_overlay", "equity_case2", "equity_total_overlay", "overlay_weight"]].rename(
                columns={"equity_case1_overlay": "equity_case1", "equity_total_overlay": "equity_total"}
            )[
                ["timestamp", "equity_case1", "equity_case2", "equity_total", "overlay_weight"]
            ].copy()
            stats = compute_curve_stats(curve, "equity_total", INITIAL_CAPITAL_TOTAL)

        curve["variant"] = variant
        curve_rows.append(curve)
        curve_map[variant] = curve.copy()
        rows.append(
            {
                "variant": variant,
                "mode": mode,
                "trigger_dd_pct": float(cfg.get("trigger_dd_pct", 0.0)),
                "restore_dd_pct": float(cfg.get("restore_dd_pct", 0.0)),
                "reduced_weight": float(cfg.get("reduced_weight", 1.0)),
                "total_final_equity": stats["final_equity"],
                "total_return_pct": stats["total_return_pct"],
                "total_cagr_pct": stats["cagr_pct"],
                "total_mdd_pct": stats["max_drawdown_pct"],
                "total_calmar_ratio": stats["calmar_ratio"],
            }
        )

    metrics_df = pd.DataFrame(rows).sort_values(["total_calmar_ratio", "total_cagr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curve_rows, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df)
    save_report(metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    run()
