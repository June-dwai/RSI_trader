from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_85_CSV = Path("85_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_portfolio.csv")
BASE_74_PATH = Path("74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.py")
CASE3_84_CURVES_CSV = Path("84_backtest_btcusdt_scale06_adx002_smc_short_gate_tune_curves.csv")
BASE_111_CSV = Path("111_backtest_btcusdt_sr_smc_5m_profitmax.csv")
BASE_111_CURVES_CSV = Path("111_backtest_btcusdt_sr_smc_5m_profitmax_selected_curves.csv")

OUT_BASE = "112_backtest_btcusdt_highcagr_core_srsmc_overlay"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

INITIAL_CAPITAL_TOTAL = 2000.0
REBALANCE_FEE_RATE = 0.0004
RESAMPLE_RULE = "1h"
CAGR_FLOOR_PCT = 100.0
WEIGHT_GRID_PCT = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15]
REBALANCE_HOURS_GRID = [4, 24, 168]

OVERLAY_LABELS = {
    "proxy_winner": "study111_proxy",
    "exact_winner": "study111_exact",
    "gap_12": "gap12_reference",
    "buy_hold": "buy_hold_reference",
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


def _hourly_curve(df: pd.DataFrame, equity_col: str) -> pd.DataFrame:
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    out = (
        out.set_index("timestamp")
        .sort_index()[[equity_col]]
        .resample(RESAMPLE_RULE)
        .last()
        .dropna()
        .reset_index()
        .rename(columns={equity_col: "equity"})
    )
    return out


def load_core_curve() -> tuple[pd.Series, pd.DataFrame]:
    metrics = pd.read_csv(BASE_85_CSV)
    live = metrics[metrics["variant"] != "baseline_70_case12_only"].copy()
    if live.empty:
        raise RuntimeError("No live study-85 variants found.")
    core_row = live.iloc[0].copy()

    s74 = load_module("study74_for_112", BASE_74_PATH)
    case1, case2 = s74.load_case12()
    case3_name = str(core_row["case3_name"])
    case3_variant = case3_name.removesuffix("_case3")
    case3 = s74.load_case3(CASE3_84_CURVES_CSV, case3_variant, case3_name)

    common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
    common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())
    case1_clip = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)].copy()
    case2_clip = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy()
    case3_clip = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)].copy()
    merged = s74.build_merged(case1_clip, case2_clip, case3_clip, case3_name)

    rebuilt_curve, _ = s74.run_three_sleeve(
        merged,
        case3_name,
        float(core_row["w1"]),
        float(core_row["w2"]),
        float(core_row["w3"]),
    )
    hourly = _hourly_curve(rebuilt_curve[["timestamp", "equity_total"]], "equity_total")
    return core_row, hourly


def load_overlay_curves() -> tuple[pd.DataFrame, dict[str, dict]]:
    metrics = pd.read_csv(BASE_111_CSV)
    curves = pd.read_csv(BASE_111_CURVES_CSV, parse_dates=["timestamp"])

    candidates: dict[str, dict] = {}
    for benchmark_flag, overlay_name in OVERLAY_LABELS.items():
        row = metrics[metrics["benchmark_flag"] == benchmark_flag]
        if row.empty:
            raise RuntimeError(f"Missing benchmark flag in study-111 metrics: {benchmark_flag}")
        ref = row.iloc[0].copy()
        variant = str(ref["variant"])
        curve = curves[curves["variant"] == variant].copy()
        if curve.empty:
            raise RuntimeError(f"Missing study-111 curve for variant: {variant}")
        candidates[overlay_name] = {
            "benchmark_flag": benchmark_flag,
            "variant": variant,
            "metrics": ref,
            "curve": _hourly_curve(curve[["timestamp", "equity"]], "equity"),
        }
    return metrics, candidates


def build_common_index(core_curve: pd.DataFrame, overlays: dict[str, dict]) -> pd.DatetimeIndex:
    starts = [pd.Timestamp(core_curve["timestamp"].min())]
    ends = [pd.Timestamp(core_curve["timestamp"].max())]
    for item in overlays.values():
        starts.append(pd.Timestamp(item["curve"]["timestamp"].min()))
        ends.append(pd.Timestamp(item["curve"]["timestamp"].max()))
    start = max(starts)
    end = min(ends)
    if start >= end:
        raise RuntimeError("No common study period across core and overlay curves.")
    return pd.date_range(start=start, end=end, freq=RESAMPLE_RULE)


def align_curve_to_index(curve: pd.DataFrame, target_index: pd.DatetimeIndex) -> pd.DataFrame:
    out = curve.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    out = out.set_index("timestamp").sort_index()
    out = out.reindex(target_index, method="ffill")
    if out["equity"].isna().any():
        raise RuntimeError("Curve alignment introduced missing equity values.")
    out = out.reset_index().rename(columns={"index": "timestamp"})
    return out


def run_overlay(
    core_curve: pd.DataFrame,
    overlay_curve: pd.DataFrame,
    overlay_name: str,
    overlay_weight: float,
    rebalance_hours: int,
) -> tuple[pd.DataFrame, dict]:
    merged = pd.merge(
        core_curve.rename(columns={"equity": "equity_core"}),
        overlay_curve.rename(columns={"equity": "equity_overlay"}),
        on="timestamp",
        how="inner",
    ).sort_values("timestamp")

    ret_core = merged["equity_core"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret_overlay = merged["equity_overlay"].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"]
    rebal_flags = (ts.dt.floor(f"{rebalance_hours}h") != ts.dt.floor(f"{rebalance_hours}h").shift(1)).to_numpy()

    core_weight = 1.0 - overlay_weight
    cap_core = np.zeros(len(merged), dtype=float)
    cap_overlay = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    fee_paid = 0.0
    rebalance_count = 0

    cap_core[0] = INITIAL_CAPITAL_TOTAL * core_weight
    cap_overlay[0] = INITIAL_CAPITAL_TOTAL * overlay_weight
    total[0] = cap_core[0] + cap_overlay[0]

    for i in range(1, len(merged)):
        c_core = cap_core[i - 1] * (1.0 + float(ret_core[i]))
        c_overlay = cap_overlay[i - 1] * (1.0 + float(ret_overlay[i]))
        cur_total = c_core + c_overlay

        if rebal_flags[i]:
            target_core = cur_total * core_weight
            target_overlay = cur_total * overlay_weight
            fee = (abs(target_core - c_core) + abs(target_overlay - c_overlay)) * REBALANCE_FEE_RATE
            cur_total -= fee
            c_core = cur_total * core_weight
            c_overlay = cur_total * overlay_weight
            fee_paid += fee
            rebalance_count += 1

        cap_core[i] = c_core
        cap_overlay[i] = c_overlay
        total[i] = cur_total

    out = merged[["timestamp"]].copy()
    out["equity_total"] = total
    out["cap_core85"] = cap_core
    out["cap_overlay"] = cap_overlay
    out["overlay_name"] = overlay_name
    out["overlay_weight"] = overlay_weight
    out["rebalance_hours"] = rebalance_hours
    return out, {"fee_paid": fee_paid, "rebalance_count": rebalance_count}


def rank_metrics(metrics_df: pd.DataFrame) -> pd.DataFrame:
    ranked = metrics_df.copy()
    ranked["meets_cagr_floor"] = ranked["total_cagr_pct"] >= CAGR_FLOOR_PCT
    ranked["is_live_overlay"] = ranked["overlay_weight"] > 0.0
    ranked = ranked.sort_values(
        ["meets_cagr_floor", "is_live_overlay", "total_calmar_ratio", "total_cagr_pct", "total_mdd_pct"],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)
    return ranked


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    display_variants = ["core85_only"]
    display_variants.extend(
        [v for v in metrics_df[metrics_df["overlay_weight"] > 0.0].head(7)["variant"].tolist() if v != "core85_only"]
    )

    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_overlay = axes

    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(display_variants)}

    for variant in display_variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.axhline(INITIAL_CAPITAL_TOTAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 112: High-CAGR Core + SR/SMC Overlay")
    ax_eq.set_ylabel("Total Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    top = metrics_df.head(12)
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

    ax_overlay.bar(top["variant"], top["overlay_weight"] * 100.0, color="#2ca02c", alpha=0.85, label="Overlay Weight %")
    ax_overlay.set_ylabel("Overlay Weight %")
    ax_overlay.grid(True, axis="y", alpha=0.2)
    ax_overlay.tick_params(axis="x", rotation=20)
    ax_overlay_t = ax_overlay.twinx()
    ax_overlay_t.plot(top["variant"], top["total_calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Calmar")
    ax_overlay_t.set_ylabel("Calmar")
    h1, l1 = ax_overlay.get_legend_handles_labels()
    h2, l2 = ax_overlay_t.get_legend_handles_labels()
    ax_overlay.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(
    metrics_df: pd.DataFrame,
    core_row: pd.Series,
    overlay_candidates: dict[str, dict],
    winner: pd.Series,
    best_111: pd.Series,
    best_gap12: pd.Series,
    best_buy_hold: pd.Series,
):
    core_ref = metrics_df[metrics_df["variant"] == "core85_only"].iloc[0]
    raw_cagr_best = metrics_df.sort_values(["total_cagr_pct", "total_calmar_ratio"], ascending=[False, False]).iloc[0]

    lines: list[str] = []
    lines.append("# Study 112: High-CAGR Core + SR/SMC Overlay")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Core engine is the study-85 leader: `{core_row['variant']}`.")
    lines.append("- Overlay candidates come from study 111 (`proxy_winner`, `exact_winner`) plus reference long sleeves (`gap_12`, `buy_hold`).")
    lines.append("- All curves are aligned to a common hourly period and rebalanced fee-aware.")
    lines.append(f"- Ranking priority is `CAGR >= {CAGR_FLOOR_PCT:.0f}%` first, then higher Calmar, then higher CAGR, then lower MDD.")
    lines.append("")
    lines.append("## Winner")
    lines.append(
        f"- Best live overlay under the CAGR floor: `{winner['variant']}` -> CAGR `{_fmt(winner['total_cagr_pct'])}%`, "
        f"MDD `{_fmt(winner['total_mdd_pct'])}%`, Calmar `{_fmt(winner['total_calmar_ratio'])}`, "
        f"overlay `{winner['overlay_name']}` at `{_fmt(winner['overlay_weight'] * 100.0, 2)}%`, rebalance `{int(winner['rebalance_hours'])}h`."
    )
    lines.append(
        f"- Delta vs core85-only: CAGR `{_fmt(winner['total_cagr_pct'] - core_ref['total_cagr_pct'])}pp`, "
        f"MDD `{_fmt(winner['total_mdd_pct'] - core_ref['total_mdd_pct'])}pp`, "
        f"Calmar `{_fmt(winner['total_calmar_ratio'] - core_ref['total_calmar_ratio'])}`."
    )
    lines.append(
        f"- Raw CAGR champion regardless of overlay requirement: `{raw_cagr_best['variant']}` "
        f"with `{_fmt(raw_cagr_best['total_cagr_pct'])}%` CAGR."
    )
    lines.append("")
    lines.append("## Candidate Comparison")
    lines.append(
        f"- Best study111 overlay: `{best_111['variant']}` -> CAGR `{_fmt(best_111['total_cagr_pct'])}%`, "
        f"MDD `{_fmt(best_111['total_mdd_pct'])}%`, Calmar `{_fmt(best_111['total_calmar_ratio'])}`"
    )
    lines.append(
        f"- Best gap12 overlay: `{best_gap12['variant']}` -> CAGR `{_fmt(best_gap12['total_cagr_pct'])}%`, "
        f"MDD `{_fmt(best_gap12['total_mdd_pct'])}%`, Calmar `{_fmt(best_gap12['total_calmar_ratio'])}`"
    )
    lines.append(
        f"- Best buy-and-hold overlay: `{best_buy_hold['variant']}` -> CAGR `{_fmt(best_buy_hold['total_cagr_pct'])}%`, "
        f"MDD `{_fmt(best_buy_hold['total_mdd_pct'])}%`, Calmar `{_fmt(best_buy_hold['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Overlay Inputs")
    for overlay_name, item in overlay_candidates.items():
        ref = item["metrics"]
        lines.append(
            f"- `{overlay_name}` from `{ref['variant']}`: standalone CAGR `{_fmt(ref['cagr_pct'])}%`, "
            f"MDD `{_fmt(ref['max_drawdown_pct'])}%`, Final Equity `{_fmt(ref['final_equity'])}`"
        )
    lines.append("")
    lines.append("## Top 12")
    lines.append("")
    lines.append("| Variant | Overlay | Weight % | Rebalance | CAGR % | MDD % | Calmar | Fee Paid |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.head(12).iterrows():
        lines.append(
            f"| {row['variant']} | {row['overlay_name']} | {_fmt(row['overlay_weight'] * 100.0, 2)} | "
            f"{int(row['rebalance_hours'])}h | {_fmt(row['total_cagr_pct'])} | {_fmt(row['total_mdd_pct'])} | "
            f"{_fmt(row['total_calmar_ratio'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    if winner["overlay_name"] in {"study111_proxy", "study111_exact"}:
        lines.append("- Study 111 does contribute as an overlay candidate when the goal is to preserve triple-digit CAGR and improve risk-adjusted shape.")
    else:
        lines.append("- The new study-111 sleeve does not yet beat the simpler long references once the triple-digit CAGR constraint is enforced.")
    if winner["overlay_weight"] <= 0.04:
        lines.append("- The winning overlay weight is tiny, so this behaves as a micro-diversifier rather than a new core engine.")
    else:
        lines.append("- The winning overlay weight is large enough to matter, so the added sleeve is doing more than cosmetic smoothing.")
    lines.append("- If core85-only still wins on both CAGR and Calmar, then 112 says the safest move is to keep study 111 in the idea queue rather than the live mix.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    core_row, core_curve_raw = load_core_curve()
    _, overlays = load_overlay_curves()
    common_index = build_common_index(core_curve_raw, overlays)

    core_curve = align_curve_to_index(core_curve_raw, common_index)
    overlay_curves = {
        name: {**item, "curve": align_curve_to_index(item["curve"], common_index)}
        for name, item in overlays.items()
    }

    rows: list[dict] = []
    curve_map: dict[str, pd.DataFrame] = {}

    core_only_curve, core_only_run = run_overlay(core_curve, next(iter(overlay_curves.values()))["curve"], "none", 0.0, 24)
    core_only_curve["variant"] = "core85_only"
    core_only_stats = compute_curve_stats(core_only_curve, "equity_total", INITIAL_CAPITAL_TOTAL)
    rows.append(
        {
            "variant": "core85_only",
            "overlay_name": "none",
            "core_weight": 1.0,
            "overlay_weight": 0.0,
            "rebalance_hours": 24,
            "total_final_equity": core_only_stats["final_equity"],
            "total_return_pct": core_only_stats["total_return_pct"],
            "total_cagr_pct": core_only_stats["cagr_pct"],
            "total_mdd_pct": core_only_stats["max_drawdown_pct"],
            "total_calmar_ratio": core_only_stats["calmar_ratio"],
            "fee_paid": core_only_run["fee_paid"],
            "rebalance_count": core_only_run["rebalance_count"],
        }
    )
    curve_map["core85_only"] = core_only_curve

    for overlay_name, item in overlay_curves.items():
        for rebalance_hours in REBALANCE_HOURS_GRID:
            for overlay_weight_pct in WEIGHT_GRID_PCT:
                overlay_weight = overlay_weight_pct / 100.0
                core_weight = 1.0 - overlay_weight
                if core_weight <= 0.0:
                    continue

                curve, run_stats = run_overlay(core_curve, item["curve"], overlay_name, overlay_weight, rebalance_hours)
                variant = f"{overlay_name}_w{overlay_weight_pct}_rb{rebalance_hours}h"
                curve["variant"] = variant
                stats = compute_curve_stats(curve, "equity_total", INITIAL_CAPITAL_TOTAL)
                rows.append(
                    {
                        "variant": variant,
                        "overlay_name": overlay_name,
                        "core_weight": core_weight,
                        "overlay_weight": overlay_weight,
                        "rebalance_hours": rebalance_hours,
                        "total_final_equity": stats["final_equity"],
                        "total_return_pct": stats["total_return_pct"],
                        "total_cagr_pct": stats["cagr_pct"],
                        "total_mdd_pct": stats["max_drawdown_pct"],
                        "total_calmar_ratio": stats["calmar_ratio"],
                        "fee_paid": run_stats["fee_paid"],
                        "rebalance_count": run_stats["rebalance_count"],
                    }
                )
                curve_map[variant] = curve

    metrics_df = pd.DataFrame(rows)
    core_ref = metrics_df[metrics_df["variant"] == "core85_only"].iloc[0]
    metrics_df["delta_cagr_vs_core85"] = metrics_df["total_cagr_pct"] - float(core_ref["total_cagr_pct"])
    metrics_df["delta_mdd_vs_core85"] = metrics_df["total_mdd_pct"] - float(core_ref["total_mdd_pct"])
    metrics_df["delta_calmar_vs_core85"] = metrics_df["total_calmar_ratio"] - float(core_ref["total_calmar_ratio"])
    metrics_df = rank_metrics(metrics_df)

    live_meeting_floor = metrics_df[(metrics_df["overlay_weight"] > 0.0) & (metrics_df["total_cagr_pct"] >= CAGR_FLOOR_PCT)].copy()
    if live_meeting_floor.empty:
        winner = metrics_df[metrics_df["overlay_weight"] > 0.0].sort_values(
            ["total_calmar_ratio", "total_cagr_pct"], ascending=[False, False]
        ).iloc[0]
    else:
        winner = live_meeting_floor.iloc[0]

    best_111 = metrics_df[
        (metrics_df["overlay_name"].isin(["study111_proxy", "study111_exact"])) & (metrics_df["overlay_weight"] > 0.0)
    ].iloc[0]
    best_gap12 = metrics_df[(metrics_df["overlay_name"] == "gap12_reference") & (metrics_df["overlay_weight"] > 0.0)].iloc[0]
    best_buy_hold = metrics_df[
        (metrics_df["overlay_name"] == "buy_hold_reference") & (metrics_df["overlay_weight"] > 0.0)
    ].iloc[0]

    selected_variants = ["core85_only"]
    selected_variants.extend([v for v in metrics_df.head(11)["variant"].tolist() if v != "core85_only"])
    curves_df = pd.concat([curve_map[v] for v in dict.fromkeys(selected_variants)], ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df)
    save_report(metrics_df, core_row, overlay_curves, winner, best_111, best_gap12, best_buy_hold)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.head(20).to_string(index=False))


if __name__ == "__main__":
    run()
