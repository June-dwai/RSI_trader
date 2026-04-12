from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_74_PATH = Path("74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.py")
BASE_116_PATH = Path("116_backtest_btcusdt_case123_portfolio_with_115_case3.py")
BASE_117_CSV = Path("117_backtest_btcusdt_115_highcagr_push.csv")
BASE_117_CURVES_CSV = Path("117_backtest_btcusdt_115_highcagr_push_curves.csv")
BASE_84_CURVES_CSV = Path("84_backtest_btcusdt_scale06_adx002_smc_short_gate_tune_curves.csv")

OUT_BASE = "118_backtest_btcusdt_case123_portfolio_with_117_case3"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

CASE1_WEIGHT_PCTS = [50, 52, 54, 56, 58, 60, 62]
CASE3_WEIGHT_PCTS = [7, 9, 11, 13, 15, 17, 20]
TOP_117_CANDIDATES = 6


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


def load_117_candidates() -> list[dict]:
    metrics = pd.read_csv(BASE_117_CSV)
    live = metrics[~metrics["variant"].astype(str).str.startswith("reference_")].copy().reset_index(drop=True)
    picked: list[dict] = []
    for _, row in live.head(TOP_117_CANDIDATES).iterrows():
        variant = str(row["variant"])
        picked.append(
            {
                "case3_name": f"{variant}_case3",
                "source_group": "study117_live",
                "variant": variant,
            }
        )
    if not picked:
        raise RuntimeError("No live study-117 candidates found.")
    return picked


def load_case3_curves(m116, candidates: list[dict]) -> dict[str, pd.DataFrame]:
    curves117 = pd.read_csv(BASE_117_CURVES_CSV, usecols=["timestamp", "variant", "equity"], parse_dates=["timestamp"])
    curves84 = pd.read_csv(BASE_84_CURVES_CSV, usecols=["timestamp", "variant", "equity"], parse_dates=["timestamp"])

    out: dict[str, pd.DataFrame] = {}
    baseline84 = curves84[curves84["variant"] == "short_gate_24h_g12_tp15"].copy()
    if baseline84.empty:
        raise RuntimeError("Missing study-84 baseline curve.")
    out["short_gate_24h_g12_tp15_case3"] = m116._to_rule_curve(
        baseline84[["timestamp", "equity"]],
        "equity",
        "short_gate_24h_g12_tp15_case3",
    )

    for cfg in candidates:
        ref = curves117[curves117["variant"] == str(cfg["variant"])].copy()
        if ref.empty:
            raise RuntimeError(f"Missing study-117 curve for {cfg['variant']}")
        out[str(cfg["case3_name"])] = m116._to_rule_curve(ref[["timestamp", "equity"]], "equity", str(cfg["case3_name"]))
    return out


def rank_metrics(metrics_df: pd.DataFrame) -> pd.DataFrame:
    ranked = metrics_df.copy()
    ranked["dominates_116"] = (
        (ranked["total_cagr_pct"] > ranked["ref116_cagr_pct"])
        & (ranked["total_mdd_pct"] < ranked["ref116_mdd_pct"])
    )
    ranked["dominates_85"] = (
        (ranked["total_cagr_pct"] > ranked["ref85_cagr_pct"])
        & (ranked["total_mdd_pct"] < ranked["ref85_mdd_pct"])
    )
    ranked["beats_116_cagr"] = ranked["total_cagr_pct"] > ranked["ref116_cagr_pct"]
    ranked = ranked.sort_values(
        ["dominates_116", "dominates_85", "total_calmar_ratio", "total_cagr_pct", "total_mdd_pct"],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)
    return ranked


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    display = ["study85_leader_reference", "study116_best_reference"]
    display.extend([v for v in metrics_df.head(8)["variant"].tolist() if v not in display])

    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_delta = axes

    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(display)}

    for variant in display:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(2000.0, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 118: Replace Case3 With Study-117 Sleeves")
    ax_eq.set_ylabel("Total Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    top = metrics_df.head(10)
    ax_cagr.bar(top["variant"], top["total_cagr_pct"], color="#1f77b4", alpha=0.85, label="CAGR %")
    ax_cagr.set_ylabel("CAGR %")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr.tick_params(axis="x", rotation=20)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(top["variant"], top["total_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_cagr_t.set_ylabel("MDD %")
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_delta.bar(top["variant"], top["delta_cagr_vs_116"], color="#2ca02c", alpha=0.85, label="Delta CAGR vs 116")
    ax_delta.set_ylabel("Delta CAGR pp")
    ax_delta.grid(True, axis="y", alpha=0.2)
    ax_delta.tick_params(axis="x", rotation=20)
    ax_delta_t = ax_delta.twinx()
    ax_delta_t.plot(top["variant"], top["delta_calmar_vs_116"], color="#9467bd", marker="o", linewidth=1.1, label="Delta Calmar vs 116")
    ax_delta_t.set_ylabel("Delta Calmar")
    h1, l1 = ax_delta.get_legend_handles_labels()
    h2, l2 = ax_delta_t.get_legend_handles_labels()
    ax_delta.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, top_candidates: list[dict], common_start: pd.Timestamp, common_end: pd.Timestamp):
    ref85 = metrics_df[metrics_df["variant"] == "study85_leader_reference"].iloc[0]
    ref116 = metrics_df[metrics_df["variant"] == "study116_best_reference"].iloc[0]
    best = metrics_df.iloc[0]
    best117 = metrics_df[metrics_df["source_group"] == "study117_live"].iloc[0]

    lines: list[str] = []
    lines.append("# Study 118: 117 Case3 Portfolio Replacement")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Goal is to test whether the stronger study-117 sleeves can replace the case3 sleeve inside the case1/case2/case3 portfolio.")
    lines.append("- Baselines are the rebuilt study-85 leader and the rebuilt study-116 winner.")
    lines.append("- Candidate case3 sleeves are the top live study-117 variants that were already saved in the study-117 selected curves file.")
    lines.append(f"- Common study period is `{common_start}` to `{common_end}`.")
    lines.append("")
    lines.append("## Candidate 117 Sleeves")
    for cfg in top_candidates:
        lines.append(f"- `{cfg['variant']}`")
    lines.append("")
    lines.append("## Baselines")
    lines.append(
        f"- Rebuilt study-85 leader: CAGR `{_fmt(ref85['total_cagr_pct'])}%`, MDD `{_fmt(ref85['total_mdd_pct'])}%`, Calmar `{_fmt(ref85['total_calmar_ratio'])}`"
    )
    lines.append(
        f"- Rebuilt study-116 best: CAGR `{_fmt(ref116['total_cagr_pct'])}%`, MDD `{_fmt(ref116['total_mdd_pct'])}%`, Calmar `{_fmt(ref116['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}` ({best['source_group']}) -> CAGR `{_fmt(best['total_cagr_pct'])}%`, MDD `{_fmt(best['total_mdd_pct'])}%`, "
        f"Calmar `{_fmt(best['total_calmar_ratio'])}`, weights `{_fmt(best['w1'], 2)}/{_fmt(best['w2'], 2)}/{_fmt(best['w3'], 2)}`"
    )
    lines.append(
        f"- Delta vs rebuilt 116 best: CAGR `{_fmt(best['delta_cagr_vs_116'])}pp`, "
        f"MDD `{_fmt(best['delta_mdd_vs_116'])}pp`, Calmar `{_fmt(best['delta_calmar_vs_116'])}`"
    )
    lines.append(
        f"- Delta vs rebuilt 85 leader: CAGR `{_fmt(best['delta_cagr_vs_85'])}pp`, "
        f"MDD `{_fmt(best['delta_mdd_vs_85'])}pp`, Calmar `{_fmt(best['delta_calmar_vs_85'])}`"
    )
    lines.append("")
    lines.append("## Best 117-Based Replacement")
    lines.append(
        f"- `{best117['variant']}` -> CAGR `{_fmt(best117['total_cagr_pct'])}%`, MDD `{_fmt(best117['total_mdd_pct'])}%`, "
        f"Calmar `{_fmt(best117['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Top 12")
    lines.append("")
    lines.append("| Variant | Source | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Delta CAGR vs 116 | Delta Calmar vs 116 |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.head(12).iterrows():
        lines.append(
            f"| {row['variant']} | {row['source_group']} | {_fmt(row['w1'], 2)} | {_fmt(row['w2'], 2)} | {_fmt(row['w3'], 2)} | "
            f"{_fmt(row['total_cagr_pct'])} | {_fmt(row['total_mdd_pct'])} | {_fmt(row['total_calmar_ratio'])} | "
            f"{_fmt(row['delta_cagr_vs_116'])} | {_fmt(row['delta_calmar_vs_116'])} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    if (metrics_df["dominates_116"]).any():
        lines.append("- At least one 117-based portfolio beats the rebuilt 116 winner on both CAGR and MDD.")
    else:
        lines.append("- No 117-based portfolio beats the rebuilt 116 winner on both CAGR and MDD.")
    if (metrics_df["dominates_85"]).any():
        lines.append("- At least one 117-based portfolio also beats the rebuilt 85 leader on both CAGR and MDD.")
    else:
        lines.append("- No 117-based portfolio beats the rebuilt 85 leader on both CAGR and MDD.")
    if (metrics_df["beats_116_cagr"]).any():
        lines.append("- At least one 117-based portfolio exceeds the rebuilt 116 CAGR even when it does not dominate on drawdown.")
    lines.append("- If 117-based sleeves only win when case3 weight is meaningfully larger, then 117 is acting more like a core sleeve than the old case3 diversifier.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run_validations(metrics_df: pd.DataFrame, curve_map: dict[str, pd.DataFrame]):
    required = {"study85_leader_reference", "study116_best_reference"}
    if not required.issubset(set(metrics_df["variant"])):
        raise AssertionError("missing baseline rows")
    if not required.issubset(set(curve_map.keys())):
        raise AssertionError("missing baseline curves")


def run():
    print("Loading helper modules...")
    m116 = load_module("study116_for_118", BASE_116_PATH)
    s74 = load_module("study74_for_118", BASE_74_PATH)

    print("Loading case1/case2 and study-117 candidates...")
    case1, case2 = m116.load_case12_resampled(s74)
    candidates = load_117_candidates()
    case3_map = load_case3_curves(m116, candidates)

    rows: list[dict] = []
    curve_map: dict[str, pd.DataFrame] = {}

    baseline_case3 = case3_map["short_gate_24h_g12_tp15_case3"]
    common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), baseline_case3["timestamp"].min())
    common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), baseline_case3["timestamp"].max())
    case1_base = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)].copy()
    case2_base = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy()
    case3_base = baseline_case3[(baseline_case3["timestamp"] >= common_start) & (baseline_case3["timestamp"] <= common_end)].copy()
    merged_base = m116.build_merged(case1_base, case2_base, case3_base, "short_gate_24h_g12_tp15_case3")

    baseline_rows = [
        ("study85_leader_reference", 0.62, 0.31, 0.07),
        ("study116_best_reference", 0.60, 0.31, 0.09),
    ]
    for variant_name, w1, w2, w3 in baseline_rows:
        curve, run_stats = m116.run_three_sleeve_15m(merged_base, "short_gate_24h_g12_tp15_case3", w1, w2, w3)
        stats = m116.compute_curve_stats(curve, "equity_total", m116.INITIAL_CAPITAL_TOTAL)
        curve["variant"] = variant_name
        curve_map[variant_name] = curve.copy()
        rows.append(
            {
                "variant": variant_name,
                "source_group": "baseline",
                "case3_name": "short_gate_24h_g12_tp15_case3",
                "case3_source_variant": "short_gate_24h_g12_tp15",
                "w1": w1,
                "w2": w2,
                "w3": w3,
                **stats,
                **run_stats,
            }
        )

    print("Running 117 case3 portfolio sweep...")
    for cfg in candidates:
        case3_name = str(cfg["case3_name"])
        case3 = case3_map[case3_name]
        common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
        common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())
        case1_clip = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)].copy()
        case2_clip = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy()
        case3_clip = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)].copy()
        merged = m116.build_merged(case1_clip, case2_clip, case3_clip, case3_name)

        for w1_pct in CASE1_WEIGHT_PCTS:
            for w3_pct in CASE3_WEIGHT_PCTS:
                w1 = w1_pct / 100.0
                w3 = w3_pct / 100.0
                w2 = 1.0 - w1 - w3
                if w2 <= 0:
                    continue

                variant = f"{case3_name}_w{w1_pct}_{int(round(w2 * 100))}_{w3_pct}"
                curve, run_stats = m116.run_three_sleeve_15m(merged, case3_name, w1, w2, w3)
                stats = m116.compute_curve_stats(curve, "equity_total", m116.INITIAL_CAPITAL_TOTAL)
                curve["variant"] = variant
                curve_map[variant] = curve.copy()
                rows.append(
                    {
                        "variant": variant,
                        "source_group": str(cfg["source_group"]),
                        "case3_name": case3_name,
                        "case3_source_variant": str(cfg["variant"]),
                        "w1": w1,
                        "w2": w2,
                        "w3": w3,
                        **stats,
                        **run_stats,
                    }
                )

    metrics_df = pd.DataFrame(rows)
    ref85 = metrics_df[metrics_df["variant"] == "study85_leader_reference"].iloc[0]
    ref116 = metrics_df[metrics_df["variant"] == "study116_best_reference"].iloc[0]
    metrics_df["ref85_cagr_pct"] = float(ref85["total_cagr_pct"])
    metrics_df["ref85_mdd_pct"] = float(ref85["total_mdd_pct"])
    metrics_df["ref116_cagr_pct"] = float(ref116["total_cagr_pct"])
    metrics_df["ref116_mdd_pct"] = float(ref116["total_mdd_pct"])
    metrics_df["delta_cagr_vs_85"] = metrics_df["total_cagr_pct"] - float(ref85["total_cagr_pct"])
    metrics_df["delta_mdd_vs_85"] = metrics_df["total_mdd_pct"] - float(ref85["total_mdd_pct"])
    metrics_df["delta_calmar_vs_85"] = metrics_df["total_calmar_ratio"] - float(ref85["total_calmar_ratio"])
    metrics_df["delta_cagr_vs_116"] = metrics_df["total_cagr_pct"] - float(ref116["total_cagr_pct"])
    metrics_df["delta_mdd_vs_116"] = metrics_df["total_mdd_pct"] - float(ref116["total_mdd_pct"])
    metrics_df["delta_calmar_vs_116"] = metrics_df["total_calmar_ratio"] - float(ref116["total_calmar_ratio"])
    metrics_df = rank_metrics(metrics_df)

    selected_variants = list(dict.fromkeys(["study85_leader_reference", "study116_best_reference"] + metrics_df.head(10)["variant"].tolist()))
    curves_df = pd.concat([curve_map[v] for v in selected_variants], ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df)
    save_report(metrics_df, candidates, pd.Timestamp(case1_base["timestamp"].min()), pd.Timestamp(case1_base["timestamp"].max()))
    run_validations(metrics_df, curve_map)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.head(12).to_string(index=False))


if __name__ == "__main__":
    run()
