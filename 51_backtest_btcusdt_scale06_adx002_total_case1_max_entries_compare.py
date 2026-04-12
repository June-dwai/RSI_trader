from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT_CASE1_METRICS_CSV = Path("49_backtest_btcusdt_scale06_adx002_case1_max_entries_hedge_matched_sweep.csv")
INPUT_CASE1_CURVES_CSV = Path("49_backtest_btcusdt_scale06_adx002_case1_max_entries_hedge_matched_sweep_curves.csv")
INPUT_CASE2_CURVE_CSV = Path("42_backtest_btcusdt_scale06_adx002_equity_combo_curves.csv")

OUT_BASE = "51_backtest_btcusdt_scale06_adx002_total_case1_max_entries_compare"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

INITIAL_CAPITAL_CASE = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    case1_metrics = pd.read_csv(INPUT_CASE1_METRICS_CSV)
    case1_curves = pd.read_csv(INPUT_CASE1_CURVES_CSV, parse_dates=["timestamp"])
    case2_curve = pd.read_csv(INPUT_CASE2_CURVE_CSV, parse_dates=["timestamp"])[["timestamp", "equity_case2"]]

    case1_metrics = case1_metrics.sort_values("max_entries").reset_index(drop=True)
    case1_curves = case1_curves.sort_values(["max_entries", "timestamp"]).reset_index(drop=True)
    case2_curve = case2_curve.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    return case1_metrics, case1_curves, case2_curve


def build_total_curve(case1_curve: pd.DataFrame, case2_curve: pd.DataFrame) -> pd.DataFrame:
    c1 = case1_curve[["timestamp", "equity"]].rename(columns={"equity": "equity_case1"})
    merged = pd.merge(c1, case2_curve, on="timestamp", how="outer").sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2"]).copy()
    merged["equity_total"] = merged["equity_case1"] + merged["equity_case2"]
    return merged


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


def save_plot(curve_map: dict[int, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_mdd = axes

    cmap = plt.get_cmap("viridis")
    entries = metrics_df["max_entries"].astype(int).tolist()
    colors = {e: cmap(i / max(1, len(entries) - 1)) for i, e in enumerate(entries)}

    for e in entries:
        curve = curve_map.get(e)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.0, color=colors[e], label=f"max_entries={e}")
    ax_eq.axhline(INITIAL_CAPITAL_TOTAL, color="#777777", linestyle="--", linewidth=0.9, label=f"Start {INITIAL_CAPITAL_TOTAL:.0f}")
    ax_eq.set_title("51 Study: Total Portfolio with Case1 Max Entries Sweep + Fixed Case2")
    ax_eq.set_ylabel("Total Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_cagr.bar(metrics_df["max_entries"], metrics_df["total_final_equity"], color=[colors[e] for e in entries], alpha=0.85, label="Total Final Equity")
    ax_cagr.set_ylabel("Total Final Equity")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(metrics_df["max_entries"], metrics_df["total_cagr_pct"], color="#d62728", marker="o", linewidth=1.1, label="Total CAGR %")
    ax_cagr_t.set_ylabel("Total CAGR %")
    ax_cagr.set_xlabel("Case1 Max Entries")
    ax_cagr.set_xticks(entries)
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_mdd.bar(metrics_df["max_entries"], metrics_df["total_mdd_pct"], color=[colors[e] for e in entries], alpha=0.85, label="Total MDD %")
    ax_mdd.set_ylabel("Total MDD %")
    ax_mdd.grid(True, axis="y", alpha=0.2)
    ax_mdd_t = ax_mdd.twinx()
    ax_mdd_t.plot(metrics_df["max_entries"], metrics_df["total_calmar_ratio"], color="#1f77b4", marker="o", linewidth=1.1, label="Total Calmar")
    ax_mdd_t.set_ylabel("Total Calmar")
    ax_mdd.set_xlabel("Case1 Max Entries")
    ax_mdd.set_xticks(entries)
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
    base5 = metrics_df[metrics_df["max_entries"] == 5]
    base5_row = base5.iloc[0] if not base5.empty else None

    lines: list[str] = []
    lines.append("# 51 Backtest: Total Portfolio with Case1 Max Entries Sweep")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Total portfolio = `case1` from study-49 variant + fixed `case2` from study-42.")
    lines.append("- `case1` uses matched hedge size (`hedge_multiple = max_entries`).")
    lines.append("- `case2` is fixed as study-42 case2 (`dual-direction, no hedge/no hysteresis, ADX002, scale0.60, prev-touch-only, max_entries=4`).")
    lines.append("- Capital allocation: `1000 USDT` each, total start `2000 USDT`.")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Case1 Max Entries | Total Final Equity | Total Return % | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| {int(r['max_entries'])} | {_fmt(r['total_final_equity'])} | {_fmt(r['total_return_pct'])} | "
            f"{_fmt(r['total_cagr_pct'])} | {_fmt(r['total_mdd_pct'])} | {_fmt(r['total_calmar_ratio'])} | "
            f"{_fmt(r['case1_cagr_pct'])} | {_fmt(r['case1_mdd_pct'])} |"
        )
    lines.append("")
    lines.append("## Best Cases")
    lines.append(f"- Best total CAGR: `max_entries={int(best_cagr['max_entries'])}` (`{_fmt(best_cagr['total_cagr_pct'])}%`).")
    lines.append(f"- Lowest total MDD: `max_entries={int(best_mdd['max_entries'])}` (`{_fmt(best_mdd['total_mdd_pct'])}%`).")
    lines.append(f"- Best total Calmar: `max_entries={int(best_calmar['max_entries'])}` (`{_fmt(best_calmar['total_calmar_ratio'])}`).")
    if base5_row is not None:
        lines.append("")
        lines.append("## Delta vs max_entries=5")
        lines.append("| Max Entries | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |")
        lines.append("|---:|---:|---:|---:|---:|")
        for _, r in metrics_df.iterrows():
            lines.append(
                f"| {int(r['max_entries'])} | {_fmt(r['total_final_equity'] - float(base5_row['total_final_equity']))} | "
                f"{_fmt(r['total_cagr_pct'] - float(base5_row['total_cagr_pct']))} | "
                f"{_fmt(r['total_mdd_pct'] - float(base5_row['total_mdd_pct']))} | "
                f"{_fmt(r['total_calmar_ratio'] - float(base5_row['total_calmar_ratio']))} |"
            )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- `max_entries=5` still gives the highest total CAGR, but the drawdown cost is large.")
    lines.append("- `max_entries=4` is the best risk-adjusted total portfolio in this sweep because it materially lowers total MDD while keeping CAGR above 100%.")
    lines.append("- This makes `max_entries=4` the natural baseline for the next hedge-close experiment.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    case1_metrics, case1_curves, case2_curve = load_inputs()

    rows: list[dict] = []
    total_curve_rows: list[pd.DataFrame] = []
    curve_map: dict[int, pd.DataFrame] = {}

    for _, metric_row in case1_metrics.iterrows():
        max_entries = int(metric_row["max_entries"])
        case1_curve = case1_curves[case1_curves["max_entries"] == max_entries].copy()
        total_curve = build_total_curve(case1_curve, case2_curve)
        total_stats = compute_curve_stats(total_curve, "equity_total", INITIAL_CAPITAL_TOTAL)

        total_curve["max_entries"] = max_entries
        total_curve_rows.append(total_curve)
        curve_map[max_entries] = total_curve.copy()

        rows.append(
            {
                "max_entries": max_entries,
                "hedge_multiple": int(metric_row["hedge_multiple"]),
                "case1_final_equity": float(metric_row["final_equity"]),
                "case1_cagr_pct": float(metric_row["cagr_pct"]),
                "case1_mdd_pct": float(metric_row["max_drawdown_pct"]),
                "total_final_equity": total_stats["final_equity"],
                "total_return_pct": total_stats["total_return_pct"],
                "total_cagr_pct": total_stats["cagr_pct"],
                "total_mdd_pct": total_stats["max_drawdown_pct"],
                "total_calmar_ratio": total_stats["calmar_ratio"],
            }
        )

    metrics_df = pd.DataFrame(rows).sort_values("max_entries").reset_index(drop=True)
    curves_df = pd.concat(total_curve_rows, ignore_index=True)

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
