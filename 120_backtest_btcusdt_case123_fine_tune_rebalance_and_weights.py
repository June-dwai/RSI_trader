from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_74_PATH = Path("74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.py")
BASE_116_PATH = Path("116_backtest_btcusdt_case123_portfolio_with_115_case3.py")
BASE_117_CURVES_CSV = Path("117_backtest_btcusdt_115_highcagr_push_curves.csv")
BASE_84_CURVES_CSV = Path("84_backtest_btcusdt_scale06_adx002_smc_short_gate_tune_curves.csv")

OUT_BASE = "120_backtest_btcusdt_case123_fine_tune_rebalance_and_weights"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

CASE3_SOURCE_VARIANT = "lv3p0_g12_body25_tp20_lb5_none"
CASE3_NAME = f"{CASE3_SOURCE_VARIANT}_case3"

TARGET_CAGR_PCT = 133.0
CASE1_WEIGHT_PCTS = list(range(46, 53))
CASE3_WEIGHT_PCTS = list(range(22, 31))
REBALANCE_RULES = ["30min", "45min", "1h", "90min", "2h", "3h", "4h"]


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


def _fmt_count(v: float) -> str:
    if pd.isna(v):
        return "N/A"
    return str(int(v))


def load_case3_curves(m116) -> dict[str, pd.DataFrame]:
    curves117 = pd.read_csv(BASE_117_CURVES_CSV, usecols=["timestamp", "variant", "equity"], parse_dates=["timestamp"])
    curves84 = pd.read_csv(BASE_84_CURVES_CSV, usecols=["timestamp", "variant", "equity"], parse_dates=["timestamp"])

    out: dict[str, pd.DataFrame] = {}
    baseline84 = curves84[curves84["variant"] == "short_gate_24h_g12_tp15"].copy()
    if baseline84.empty:
        raise RuntimeError("Missing study-84 baseline case3 curve.")
    out["short_gate_24h_g12_tp15_case3"] = m116._to_rule_curve(
        baseline84[["timestamp", "equity"]],
        "equity",
        "short_gate_24h_g12_tp15_case3",
    )

    ref117 = curves117[curves117["variant"] == CASE3_SOURCE_VARIANT].copy()
    if ref117.empty:
        raise RuntimeError(f"Missing study-117 curve for {CASE3_SOURCE_VARIANT}")
    out[CASE3_NAME] = m116._to_rule_curve(ref117[["timestamp", "equity"]], "equity", CASE3_NAME)
    return out


def run_three_sleeve_custom_rebalance(
    merged: pd.DataFrame,
    case3_name: str,
    w1: float,
    w2: float,
    w3: float,
    rebalance_rule: str,
    initial_capital_total: float,
    fee_rate: float,
) -> tuple[pd.DataFrame, dict]:
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret3 = merged[case3_name].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"]
    rebal_flags = (ts.dt.floor(rebalance_rule) != ts.dt.floor(rebalance_rule).shift(1)).to_numpy()

    cap1 = np.zeros(len(merged), dtype=float)
    cap2 = np.zeros(len(merged), dtype=float)
    cap3 = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    fee_paid = 0.0
    rebalance_count = 0

    cap1[0] = initial_capital_total * w1
    cap2[0] = initial_capital_total * w2
    cap3[0] = initial_capital_total * w3
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
            fee = (abs(target1 - c1) + abs(target2 - c2) + abs(target3 - c3)) * fee_rate
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
    out["rebalance_rule"] = rebalance_rule
    return out, {"rebalance_count": rebalance_count, "fee_paid": fee_paid}


def rank_metrics(metrics_df: pd.DataFrame) -> pd.DataFrame:
    ranked = metrics_df.copy()
    ranked["meets_target"] = ranked["total_cagr_pct"] >= TARGET_CAGR_PCT
    ranked["dominates_119"] = (
        (ranked["total_cagr_pct"] > ranked["ref119_cagr_pct"])
        & (ranked["total_mdd_pct"] < ranked["ref119_mdd_pct"])
    )
    ranked["dominates_85"] = (
        (ranked["total_cagr_pct"] > ranked["ref85_cagr_pct"])
        & (ranked["total_mdd_pct"] < ranked["ref85_mdd_pct"])
    )
    ranked = ranked.sort_values(
        ["meets_target", "dominates_119", "dominates_85", "total_calmar_ratio", "total_cagr_pct", "total_mdd_pct"],
        ascending=[False, False, False, False, False, True],
    ).reset_index(drop=True)
    return ranked


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    display = ["study85_leader_reference", "study119_best_reference"]
    display.extend([v for v in metrics_df.head(8)["variant"].tolist() if v not in display])

    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_perf, ax_delta = axes

    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(display)}

    for variant in display:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(2000.0, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 120: Fine Tune Weights + Rebalance Around 119")
    ax_eq.set_ylabel("Total Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    top = metrics_df.head(10)
    ax_perf.bar(top["variant"], top["total_cagr_pct"], color="#1f77b4", alpha=0.85, label="CAGR %")
    ax_perf.set_ylabel("CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf.tick_params(axis="x", rotation=20)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(top["variant"], top["total_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_perf_t.set_ylabel("MDD %")
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_delta.bar(top["variant"], top["delta_cagr_vs_119"], color="#2ca02c", alpha=0.85, label="Delta CAGR vs 119")
    ax_delta.set_ylabel("Delta CAGR pp")
    ax_delta.grid(True, axis="y", alpha=0.2)
    ax_delta.tick_params(axis="x", rotation=20)
    ax_delta_t = ax_delta.twinx()
    ax_delta_t.plot(top["variant"], top["delta_calmar_vs_119"], color="#9467bd", marker="o", linewidth=1.1, label="Delta Calmar vs 119")
    ax_delta_t.set_ylabel("Delta Calmar")
    h1, l1 = ax_delta.get_legend_handles_labels()
    h2, l2 = ax_delta_t.get_legend_handles_labels()
    ax_delta.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, common_start: pd.Timestamp, common_end: pd.Timestamp):
    ref85 = metrics_df[metrics_df["variant"] == "study85_leader_reference"].iloc[0]
    ref119 = metrics_df[metrics_df["variant"] == "study119_best_reference"].iloc[0]
    best = metrics_df.iloc[0]

    lines: list[str] = []
    lines.append("# Study 120: Fine Tune Weights + Rebalance Around 119")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Goal is to hold the study-119 winning case3 source fixed and only fine-tune weights plus rebalance cadence.")
    lines.append(f"- Fixed case3 source is `{CASE3_SOURCE_VARIANT}`.")
    lines.append("- Search axes are case1 weight `46%~52%`, case3 weight `22%~30%`, and rebalance rule from `30min` to `4h`.")
    lines.append(f"- Common study period is `{common_start}` to `{common_end}`.")
    lines.append(f"- Ranking priority is `CAGR >= {TARGET_CAGR_PCT:.0f}%` first, then domination over study 119, then Calmar.")
    lines.append("")
    lines.append("## Baselines")
    lines.append(
        f"- Rebuilt study-85 leader: CAGR `{_fmt(ref85['total_cagr_pct'])}%`, MDD `{_fmt(ref85['total_mdd_pct'])}%`, Calmar `{_fmt(ref85['total_calmar_ratio'])}`"
    )
    lines.append(
        f"- Rebuilt study-119 best: CAGR `{_fmt(ref119['total_cagr_pct'])}%`, MDD `{_fmt(ref119['total_mdd_pct'])}%`, Calmar `{_fmt(ref119['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}` -> CAGR `{_fmt(best['total_cagr_pct'])}%`, MDD `{_fmt(best['total_mdd_pct'])}%`, "
        f"Calmar `{_fmt(best['total_calmar_ratio'])}`, weights `{_fmt(best['w1'], 2)}/{_fmt(best['w2'], 2)}/{_fmt(best['w3'], 2)}`, "
        f"rebalance `{best['rebalance_rule']}`"
    )
    lines.append(
        f"- Delta vs rebuilt 119 best: CAGR `{_fmt(best['delta_cagr_vs_119'])}pp`, "
        f"MDD `{_fmt(best['delta_mdd_vs_119'])}pp`, Calmar `{_fmt(best['delta_calmar_vs_119'])}`"
    )
    lines.append(
        f"- Delta vs rebuilt 85 leader: CAGR `{_fmt(best['delta_cagr_vs_85'])}pp`, "
        f"MDD `{_fmt(best['delta_mdd_vs_85'])}pp`, Calmar `{_fmt(best['delta_calmar_vs_85'])}`"
    )
    lines.append("")
    lines.append("## Top 12")
    lines.append("")
    lines.append("| Variant | Rebalance | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Delta CAGR vs 119 |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.head(12).iterrows():
        lines.append(
            f"| {row['variant']} | {row['rebalance_rule']} | {_fmt(row['w1'], 2)} | {_fmt(row['w2'], 2)} | {_fmt(row['w3'], 2)} | "
            f"{_fmt(row['total_cagr_pct'])} | {_fmt(row['total_mdd_pct'])} | {_fmt(row['total_calmar_ratio'])} | {_fmt(row['delta_cagr_vs_119'])} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    if (metrics_df["meets_target"]).any():
        lines.append("- At least one fine-tuned portfolio exceeds the 133% CAGR target.")
    else:
        lines.append("- The fine-tune sweep did not exceed the 133% CAGR target.")
    if (metrics_df["dominates_119"]).any():
        lines.append("- At least one fine-tuned portfolio beats the rebuilt 119 best on both CAGR and MDD.")
    else:
        lines.append("- No fine-tuned portfolio beats the rebuilt 119 best on both CAGR and MDD.")
    if (metrics_df["dominates_85"]).any():
        lines.append("- At least one fine-tuned portfolio also beats the rebuilt 85 leader on both CAGR and MDD.")
    lines.append("- If sub-hour rebalance wins, then more of the remaining alpha still lives in portfolio plumbing.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run_validations(metrics_df: pd.DataFrame, curve_map: dict[str, pd.DataFrame]):
    required = {"study85_leader_reference", "study119_best_reference"}
    if not required.issubset(set(metrics_df["variant"])):
        raise AssertionError("missing baseline rows")
    if not required.issubset(set(curve_map.keys())):
        raise AssertionError("missing baseline curves")


def run():
    print("Loading helper modules...")
    m116 = load_module("study116_for_120", BASE_116_PATH)
    s74 = load_module("study74_for_120", BASE_74_PATH)

    print("Loading case1/case2/case3 curves...")
    case1, case2 = m116.load_case12_resampled(s74)
    case3_map = load_case3_curves(m116)

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
        ("study85_leader_reference", "short_gate_24h_g12_tp15_case3", 0.62, 0.31, 0.07, "4h"),
        ("study119_best_reference", CASE3_NAME, 0.49, 0.27, 0.24, "1h"),
    ]
    for variant_name, case3_name, w1, w2, w3, rebalance_rule in baseline_rows:
        case3 = case3_map[case3_name]
        common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
        common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())
        merged = m116.build_merged(
            case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)].copy(),
            case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy(),
            case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)].copy(),
            case3_name,
        )
        curve, run_stats = run_three_sleeve_custom_rebalance(
            merged,
            case3_name,
            w1,
            w2,
            w3,
            rebalance_rule,
            m116.INITIAL_CAPITAL_TOTAL,
            m116.REBALANCE_FEE_RATE,
        )
        stats = m116.compute_curve_stats(curve, "equity_total", m116.INITIAL_CAPITAL_TOTAL)
        curve["variant"] = variant_name
        curve_map[variant_name] = curve.copy()
        rows.append(
            {
                "variant": variant_name,
                "source_group": "baseline",
                "case3_name": case3_name,
                "case3_source_variant": "short_gate_24h_g12_tp15" if case3_name == "short_gate_24h_g12_tp15_case3" else CASE3_SOURCE_VARIANT,
                "w1": w1,
                "w2": w2,
                "w3": w3,
                "rebalance_rule": rebalance_rule,
                **stats,
                **run_stats,
            }
        )

    print("Running focused sweep...")
    case3 = case3_map[CASE3_NAME]
    common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
    common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())
    case1_clip = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)].copy()
    case2_clip = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy()
    case3_clip = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)].copy()
    merged = m116.build_merged(case1_clip, case2_clip, case3_clip, CASE3_NAME)

    for rebalance_rule in REBALANCE_RULES:
        for w1_pct in CASE1_WEIGHT_PCTS:
            for w3_pct in CASE3_WEIGHT_PCTS:
                w1 = w1_pct / 100.0
                w3 = w3_pct / 100.0
                w2 = 1.0 - w1 - w3
                if w2 <= 0:
                    continue

                variant = f"{CASE3_NAME}_rb{rebalance_rule}_w{w1_pct}_{int(round(w2 * 100))}_{w3_pct}"
                curve, run_stats = run_three_sleeve_custom_rebalance(
                    merged,
                    CASE3_NAME,
                    w1,
                    w2,
                    w3,
                    rebalance_rule,
                    m116.INITIAL_CAPITAL_TOTAL,
                    m116.REBALANCE_FEE_RATE,
                )
                stats = m116.compute_curve_stats(curve, "equity_total", m116.INITIAL_CAPITAL_TOTAL)
                curve["variant"] = variant
                curve_map[variant] = curve.copy()
                rows.append(
                    {
                        "variant": variant,
                        "source_group": "study120_live",
                        "case3_name": CASE3_NAME,
                        "case3_source_variant": CASE3_SOURCE_VARIANT,
                        "w1": w1,
                        "w2": w2,
                        "w3": w3,
                        "rebalance_rule": rebalance_rule,
                        **stats,
                        **run_stats,
                    }
                )

    metrics_df = pd.DataFrame(rows)
    ref85 = metrics_df[metrics_df["variant"] == "study85_leader_reference"].iloc[0]
    ref119 = metrics_df[metrics_df["variant"] == "study119_best_reference"].iloc[0]
    metrics_df["ref85_cagr_pct"] = float(ref85["total_cagr_pct"])
    metrics_df["ref85_mdd_pct"] = float(ref85["total_mdd_pct"])
    metrics_df["ref119_cagr_pct"] = float(ref119["total_cagr_pct"])
    metrics_df["ref119_mdd_pct"] = float(ref119["total_mdd_pct"])
    metrics_df["delta_cagr_vs_85"] = metrics_df["total_cagr_pct"] - float(ref85["total_cagr_pct"])
    metrics_df["delta_mdd_vs_85"] = metrics_df["total_mdd_pct"] - float(ref85["total_mdd_pct"])
    metrics_df["delta_calmar_vs_85"] = metrics_df["total_calmar_ratio"] - float(ref85["total_calmar_ratio"])
    metrics_df["delta_cagr_vs_119"] = metrics_df["total_cagr_pct"] - float(ref119["total_cagr_pct"])
    metrics_df["delta_mdd_vs_119"] = metrics_df["total_mdd_pct"] - float(ref119["total_mdd_pct"])
    metrics_df["delta_calmar_vs_119"] = metrics_df["total_calmar_ratio"] - float(ref119["total_calmar_ratio"])
    metrics_df = rank_metrics(metrics_df)

    selected_variants = list(dict.fromkeys(["study85_leader_reference", "study119_best_reference"] + metrics_df.head(10)["variant"].tolist()))
    curves_df = pd.concat([curve_map[v] for v in selected_variants], ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df)
    save_report(metrics_df, pd.Timestamp(case1_base["timestamp"].min()), pd.Timestamp(case1_base["timestamp"].max()))
    run_validations(metrics_df, curve_map)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.head(12).to_string(index=False))


if __name__ == "__main__":
    run()
