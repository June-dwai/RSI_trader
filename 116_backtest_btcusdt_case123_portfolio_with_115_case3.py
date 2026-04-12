from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_74_PATH = Path("74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.py")
BASE_85_CSV = Path("85_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_portfolio.csv")
BASE_84_CURVES_CSV = Path("84_backtest_btcusdt_scale06_adx002_smc_short_gate_tune_curves.csv")
BASE_115_CURVES_CSV = Path("115_backtest_btcusdt_currentbest_soft_sr_filters_curves.csv")

OUT_BASE = "116_backtest_btcusdt_case123_portfolio_with_115_case3"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

INITIAL_CAPITAL_TOTAL = 2000.0
REBALANCE_FEE_RATE = 0.0004
RESAMPLE_RULE = "15min"
CASE3_WEIGHT_PCTS = [5, 6, 7, 8, 9]
CASE1_WEIGHT_PCTS = [58, 59, 60, 61, 62]

CASE3_CANDIDATES = [
    {
        "case3_name": "short_gate_24h_g12_tp15_case3",
        "source_group": "study84_best",
        "curve_source": "84",
        "variant": "short_gate_24h_g12_tp15",
    },
    {
        "case3_name": "smc5_longonly_case3",
        "source_group": "study115_best",
        "curve_source": "115",
        "variant": "smc5_longonly_2021plus",
    },
    {
        "case3_name": "smc5_longonly_redavg_case3",
        "source_group": "study115_redavg",
        "curve_source": "115",
        "variant": "smc5_longonly_long_above_redavg_2021plus",
    },
    {
        "case3_name": "currentbest114_smc5_both_case3",
        "source_group": "study114_best",
        "curve_source": "115",
        "variant": "currentbest_114_smc5_both_2021plus",
    },
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
        "total_cagr_pct": cagr_pct,
        "total_mdd_pct": max_drawdown_pct,
        "total_calmar_ratio": calmar_ratio,
    }


def _to_rule_curve(df: pd.DataFrame, equity_col: str, out_col: str) -> pd.DataFrame:
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    out = (
        out.set_index("timestamp")
        .sort_index()[[equity_col]]
        .resample(RESAMPLE_RULE)
        .last()
        .dropna()
        .reset_index()
        .rename(columns={equity_col: out_col})
    )
    return out


def load_case12_resampled(s74) -> tuple[pd.DataFrame, pd.DataFrame]:
    case1, case2 = s74.load_case12()
    case1_15m = _to_rule_curve(case1, "equity_case1", "equity_case1")
    case2_15m = _to_rule_curve(case2, "equity_case2", "equity_case2")
    return case1_15m, case2_15m


def load_case3_curves() -> dict[str, pd.DataFrame]:
    curves84 = pd.read_csv(BASE_84_CURVES_CSV, usecols=["timestamp", "variant", "equity"], parse_dates=["timestamp"])
    curves115 = pd.read_csv(BASE_115_CURVES_CSV, usecols=["timestamp", "variant", "equity"], parse_dates=["timestamp"])

    out: dict[str, pd.DataFrame] = {}
    for cfg in CASE3_CANDIDATES:
        base = curves84 if cfg["curve_source"] == "84" else curves115
        ref = base[base["variant"] == str(cfg["variant"])].copy()
        if ref.empty:
            raise RuntimeError(f"Missing case3 curve for {cfg['variant']}")
        case3 = _to_rule_curve(ref[["timestamp", "equity"]], "equity", str(cfg["case3_name"]))
        out[str(cfg["case3_name"])] = case3
    return out


def build_merged(case1: pd.DataFrame, case2: pd.DataFrame, case3: pd.DataFrame, case3_name: str) -> pd.DataFrame:
    merged = pd.merge(case1, case2, on="timestamp", how="outer")
    merged = pd.merge(merged, case3, on="timestamp", how="outer")
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged[case3_name] = merged[case3_name].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2", case3_name]).copy()
    return merged


def run_three_sleeve_15m(merged: pd.DataFrame, case3_name: str, w1: float, w2: float, w3: float) -> tuple[pd.DataFrame, dict]:
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
            fee = (abs(target1 - c1) + abs(target2 - c2) + abs(target3 - c3)) * REBALANCE_FEE_RATE
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


def rank_metrics(metrics_df: pd.DataFrame) -> pd.DataFrame:
    ranked = metrics_df.copy()
    ranked["dominates_leader"] = (
        (ranked["total_cagr_pct"] > ranked["leader_cagr_pct"])
        & (ranked["total_mdd_pct"] < ranked["leader_mdd_pct"])
    )
    ranked["beats_cagr_peak"] = ranked["total_cagr_pct"] > ranked["cagr_peak_pct"]
    ranked = ranked.sort_values(
        ["dominates_leader", "beats_cagr_peak", "total_calmar_ratio", "total_cagr_pct", "total_mdd_pct"],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)
    return ranked


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    display = ["study85_leader_reference", "study85_cagr_peak_reference"]
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
    ax_eq.axhline(INITIAL_CAPITAL_TOTAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 116: Replace Case3 With Study-115 Style Sleeve")
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

    ax_delta.bar(top["variant"], top["delta_cagr_vs_leader"], color="#2ca02c", alpha=0.85, label="Delta CAGR vs 85 Leader")
    ax_delta.set_ylabel("Delta CAGR pp")
    ax_delta.grid(True, axis="y", alpha=0.2)
    ax_delta.tick_params(axis="x", rotation=20)
    ax_delta_t = ax_delta.twinx()
    ax_delta_t.plot(top["variant"], top["delta_calmar_vs_leader"], color="#9467bd", marker="o", linewidth=1.1, label="Delta Calmar")
    ax_delta_t.set_ylabel("Delta Calmar")
    h1, l1 = ax_delta.get_legend_handles_labels()
    h2, l2 = ax_delta_t.get_legend_handles_labels()
    ax_delta.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, reported_leader: pd.Series, reported_cagr_peak: pd.Series, start_ts: pd.Timestamp, end_ts: pd.Timestamp):
    rebuilt_leader = metrics_df[metrics_df["variant"] == "study85_leader_reference"].iloc[0]
    rebuilt_peak = metrics_df[metrics_df["variant"] == "study85_cagr_peak_reference"].iloc[0]
    best = metrics_df.iloc[0]
    best_115 = metrics_df[metrics_df["source_group"].str.startswith("study115")].iloc[0]

    lines: list[str] = []
    lines.append("# Study 116: 85 Portfolio + 115 Case3 Replacement")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Goal is to test whether the study-115 style sleeve can replace the study-84 case3 sleeve inside the case1/case2/case3 portfolio.")
    lines.append("- To keep the sweep tractable, all sleeves are reconstructed on a common `15m` grid and still rebalanced every `4h`.")
    lines.append(f"- Common study period is `{start_ts}` to `{end_ts}`.")
    lines.append("- The 85 leader and the 85 CAGR-peak row are both rebuilt on the same 15m engine for apples-to-apples comparison.")
    lines.append("")
    lines.append("## Reported 85 References")
    lines.append(
        f"- Reported leader used in study 112: `{reported_leader['variant']}` -> CAGR `{_fmt(reported_leader['total_cagr_pct'])}%`, "
        f"MDD `{_fmt(reported_leader['total_mdd_pct'])}%`, Calmar `{_fmt(reported_leader['total_calmar_ratio'])}`"
    )
    lines.append(
        f"- Reported 85 CAGR peak: `{reported_cagr_peak['variant']}` -> CAGR `{_fmt(reported_cagr_peak['total_cagr_pct'])}%`, "
        f"MDD `{_fmt(reported_cagr_peak['total_mdd_pct'])}%`, Calmar `{_fmt(reported_cagr_peak['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Rebuilt References")
    lines.append(
        f"- Rebuilt 85 leader: CAGR `{_fmt(rebuilt_leader['total_cagr_pct'])}%`, MDD `{_fmt(rebuilt_leader['total_mdd_pct'])}%`, "
        f"Calmar `{_fmt(rebuilt_leader['total_calmar_ratio'])}`"
    )
    lines.append(
        f"- Rebuilt 85 CAGR peak: CAGR `{_fmt(rebuilt_peak['total_cagr_pct'])}%`, MDD `{_fmt(rebuilt_peak['total_mdd_pct'])}%`, "
        f"Calmar `{_fmt(rebuilt_peak['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}` ({best['source_group']}) -> CAGR `{_fmt(best['total_cagr_pct'])}%`, "
        f"MDD `{_fmt(best['total_mdd_pct'])}%`, Calmar `{_fmt(best['total_calmar_ratio'])}`, "
        f"weights `{_fmt(best['w1'], 2)}/{_fmt(best['w2'], 2)}/{_fmt(best['w3'], 2)}`"
    )
    lines.append(
        f"- Delta vs rebuilt 85 leader: CAGR `{_fmt(best['delta_cagr_vs_leader'])}pp`, "
        f"MDD `{_fmt(best['delta_mdd_vs_leader'])}pp`, Calmar `{_fmt(best['delta_calmar_vs_leader'])}`"
    )
    lines.append(
        f"- Delta vs rebuilt 85 CAGR peak: CAGR `{_fmt(best['delta_cagr_vs_cagr_peak'])}pp`, "
        f"MDD `{_fmt(best['delta_mdd_vs_cagr_peak'])}pp`, Calmar `{_fmt(best['delta_calmar_vs_cagr_peak'])}`"
    )
    lines.append("")
    lines.append("## Best 115-Based Replacement")
    lines.append(
        f"- `{best_115['variant']}` ({best_115['source_group']}) -> CAGR `{_fmt(best_115['total_cagr_pct'])}%`, "
        f"MDD `{_fmt(best_115['total_mdd_pct'])}%`, Calmar `{_fmt(best_115['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Top 12")
    lines.append("")
    lines.append("| Variant | Source | W1 | W2 | W3 | CAGR % | MDD % | Calmar | Delta CAGR vs 85 | Delta Calmar vs 85 |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.head(12).iterrows():
        lines.append(
            f"| {row['variant']} | {row['source_group']} | {_fmt(row['w1'], 2)} | {_fmt(row['w2'], 2)} | {_fmt(row['w3'], 2)} | "
            f"{_fmt(row['total_cagr_pct'])} | {_fmt(row['total_mdd_pct'])} | {_fmt(row['total_calmar_ratio'])} | "
            f"{_fmt(row['delta_cagr_vs_leader'])} | {_fmt(row['delta_calmar_vs_leader'])} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    if (metrics_df["dominates_leader"]).any():
        lines.append("- At least one rebuilt variant beats the rebuilt 85 leader on both CAGR and MDD.")
    else:
        lines.append("- No rebuilt variant beats the rebuilt 85 leader on both CAGR and MDD.")
    if (metrics_df["beats_cagr_peak"]).any():
        lines.append("- At least one variant exceeds the rebuilt 85 CAGR peak.")
    else:
        lines.append("- No variant exceeds the rebuilt 85 CAGR peak.")
    lines.append("- If the best 115-based case3 still trails the rebuilt 85 leader, then 115 works better as a single-engine refinement than as a direct case3 replacement.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run_validations(metrics_df: pd.DataFrame, curve_map: dict[str, pd.DataFrame]):
    required = {"study85_leader_reference", "study85_cagr_peak_reference"}
    if not required.issubset(set(metrics_df["variant"])):
        raise AssertionError("missing rebuilt baseline rows")
    if not required.issubset(set(curve_map.keys())):
        raise AssertionError("missing rebuilt baseline curves")


def run():
    print("Loading study-74 module...")
    s74 = load_module("study74_for_116", BASE_74_PATH)

    print("Loading and resampling sleeves...")
    case1, case2 = load_case12_resampled(s74)
    case3_map = load_case3_curves()
    metrics85 = pd.read_csv(BASE_85_CSV)
    reported_leader = metrics85.iloc[0].copy()
    reported_cagr_peak = metrics85.sort_values("total_cagr_pct", ascending=False).iloc[0].copy()

    rows: list[dict] = []
    curve_map: dict[str, pd.DataFrame] = {}

    leader_w = (float(reported_leader["w1"]), float(reported_leader["w2"]), float(reported_leader["w3"]))
    peak_w = (float(reported_cagr_peak["w1"]), float(reported_cagr_peak["w2"]), float(reported_cagr_peak["w3"]))

    baseline_case3 = case3_map["short_gate_24h_g12_tp15_case3"]
    base_start = max(case1["timestamp"].min(), case2["timestamp"].min(), baseline_case3["timestamp"].min())
    base_end = min(case1["timestamp"].max(), case2["timestamp"].max(), baseline_case3["timestamp"].max())
    case1_base = case1[(case1["timestamp"] >= base_start) & (case1["timestamp"] <= base_end)].copy()
    case2_base = case2[(case2["timestamp"] >= base_start) & (case2["timestamp"] <= base_end)].copy()
    case3_base = baseline_case3[(baseline_case3["timestamp"] >= base_start) & (baseline_case3["timestamp"] <= base_end)].copy()
    merged_base = build_merged(case1_base, case2_base, case3_base, "short_gate_24h_g12_tp15_case3")

    for variant_name, weights in [
        ("study85_leader_reference", leader_w),
        ("study85_cagr_peak_reference", peak_w),
    ]:
        curve, run_stats = run_three_sleeve_15m(merged_base, "short_gate_24h_g12_tp15_case3", weights[0], weights[1], weights[2])
        stats = compute_curve_stats(curve, "equity_total", INITIAL_CAPITAL_TOTAL)
        curve["variant"] = variant_name
        curve_map[variant_name] = curve.copy()
        rows.append(
            {
                "variant": variant_name,
                "source_group": "study85_reference",
                "case3_name": "short_gate_24h_g12_tp15_case3",
                "case3_source_variant": "short_gate_24h_g12_tp15",
                "w1": weights[0],
                "w2": weights[1],
                "w3": weights[2],
                **stats,
                **run_stats,
            }
        )

    print("Running case3 replacement sweep...")
    for cfg in CASE3_CANDIDATES:
        case3_name = str(cfg["case3_name"])
        case3 = case3_map[case3_name]
        common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
        common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())
        case1_clip = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)].copy()
        case2_clip = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy()
        case3_clip = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)].copy()
        merged = build_merged(case1_clip, case2_clip, case3_clip, case3_name)

        for w1_pct in CASE1_WEIGHT_PCTS:
            for w3_pct in CASE3_WEIGHT_PCTS:
                w1 = w1_pct / 100.0
                w3 = w3_pct / 100.0
                w2 = 1.0 - w1 - w3
                if w2 <= 0:
                    continue

                variant = f"{case3_name}_w{w1_pct}_{int(round(w2 * 100))}_{w3_pct}"
                curve, run_stats = run_three_sleeve_15m(merged, case3_name, w1, w2, w3)
                stats = compute_curve_stats(curve, "equity_total", INITIAL_CAPITAL_TOTAL)
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
    leader_row = metrics_df[metrics_df["variant"] == "study85_leader_reference"].iloc[0]
    cagr_peak_row = metrics_df[metrics_df["variant"] == "study85_cagr_peak_reference"].iloc[0]
    metrics_df["leader_cagr_pct"] = float(leader_row["total_cagr_pct"])
    metrics_df["leader_mdd_pct"] = float(leader_row["total_mdd_pct"])
    metrics_df["cagr_peak_pct"] = float(cagr_peak_row["total_cagr_pct"])
    metrics_df["delta_cagr_vs_leader"] = metrics_df["total_cagr_pct"] - float(leader_row["total_cagr_pct"])
    metrics_df["delta_mdd_vs_leader"] = metrics_df["total_mdd_pct"] - float(leader_row["total_mdd_pct"])
    metrics_df["delta_calmar_vs_leader"] = metrics_df["total_calmar_ratio"] - float(leader_row["total_calmar_ratio"])
    metrics_df["delta_cagr_vs_cagr_peak"] = metrics_df["total_cagr_pct"] - float(cagr_peak_row["total_cagr_pct"])
    metrics_df["delta_mdd_vs_cagr_peak"] = metrics_df["total_mdd_pct"] - float(cagr_peak_row["total_mdd_pct"])
    metrics_df["delta_calmar_vs_cagr_peak"] = metrics_df["total_calmar_ratio"] - float(cagr_peak_row["total_calmar_ratio"])
    metrics_df = rank_metrics(metrics_df)

    selected_variants = list(dict.fromkeys(["study85_leader_reference", "study85_cagr_peak_reference"] + metrics_df.head(10)["variant"].tolist()))
    curves_df = pd.concat([curve_map[v] for v in selected_variants], ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df)
    save_report(metrics_df, reported_leader, reported_cagr_peak, pd.Timestamp(base_start), pd.Timestamp(base_end))
    run_validations(metrics_df, curve_map)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.head(12).to_string(index=False))


if __name__ == "__main__":
    run()
