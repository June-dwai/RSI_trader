from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT_CURVES_CSV = Path("62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune_curves.csv")

OUT_BASE = "69_backtest_btcusdt_scale06_adx002_rebalance_schedule_sweep"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

CASE_VARIANT = "shallow6_else2bull"
INITIAL_CAPITAL_CASE = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
REBALANCE_FEE_RATE = 0.0004

EXPECTED_HOLD_BASELINE = {
    "final_equity": 37042.70606845802,
    "cagr_pct": 103.27812652063195,
    "mdd_pct": 50.853607894861834,
}

VARIANTS = [
    {"variant": "hold_no_rebalance", "mode": "hold"},
    {"variant": "rebal_4h_w45", "mode": "rebalance", "freq": "4h", "target_case1_w": 0.45},
    {"variant": "rebal_4h_w50", "mode": "rebalance", "freq": "4h", "target_case1_w": 0.50},
    {"variant": "rebal_4h_w55", "mode": "rebalance", "freq": "4h", "target_case1_w": 0.55},
    {"variant": "rebal_1d_w45", "mode": "rebalance", "freq": "1d", "target_case1_w": 0.45},
    {"variant": "rebal_1d_w50", "mode": "rebalance", "freq": "1d", "target_case1_w": 0.50},
    {"variant": "rebal_1d_w55", "mode": "rebalance", "freq": "1d", "target_case1_w": 0.55},
    {"variant": "rebal_7d_w45", "mode": "rebalance", "freq": "7d", "target_case1_w": 0.45},
    {"variant": "rebal_7d_w50", "mode": "rebalance", "freq": "7d", "target_case1_w": 0.50},
    {"variant": "rebal_7d_w55", "mode": "rebalance", "freq": "7d", "target_case1_w": 0.55},
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


def load_curve() -> pd.DataFrame:
    curves = pd.read_csv(INPUT_CURVES_CSV, parse_dates=["timestamp"])
    curve = curves[curves["variant"] == CASE_VARIANT][["timestamp", "equity_case1", "equity_case2", "equity_total"]].copy()
    if curve.empty:
        raise ValueError(f"missing variant: {CASE_VARIANT}")
    return curve.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)


def build_rebalance_flags(timestamps: pd.Series, freq: str) -> pd.Series:
    if freq == "4h":
        bucket = timestamps.dt.floor("4h")
    elif freq == "1d":
        bucket = timestamps.dt.floor("1d")
    elif freq == "7d":
        bucket = timestamps.dt.floor("7d")
    else:
        raise ValueError(f"unsupported freq: {freq}")
    return bucket != bucket.shift(1)


def run_rebalanced_portfolio(curve: pd.DataFrame, freq: str, target_case1_w: float) -> tuple[pd.DataFrame, dict]:
    out = curve[["timestamp", "equity_case1", "equity_case2"]].copy()
    rebal_flags = build_rebalance_flags(out["timestamp"], freq).to_numpy()
    case1_ret = out["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    case2_ret = out["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()

    cap1 = np.zeros(len(out), dtype=float)
    cap2 = np.zeros(len(out), dtype=float)
    total = np.zeros(len(out), dtype=float)
    case1_w = np.zeros(len(out), dtype=float)
    fee_paid = 0.0
    rebalance_count = 0

    cap1[0] = INITIAL_CAPITAL_TOTAL * target_case1_w
    cap2[0] = INITIAL_CAPITAL_TOTAL * (1.0 - target_case1_w)
    total[0] = cap1[0] + cap2[0]
    case1_w[0] = target_case1_w

    for i in range(1, len(out)):
        prev_cap1 = cap1[i - 1] * (1.0 + float(case1_ret[i]))
        prev_cap2 = cap2[i - 1] * (1.0 + float(case2_ret[i]))
        prev_total = prev_cap1 + prev_cap2

        if rebal_flags[i]:
            target_cap1 = prev_total * target_case1_w
            delta = abs(target_cap1 - prev_cap1)
            fee = 2.0 * delta * REBALANCE_FEE_RATE
            post_total = prev_total - fee
            prev_cap1 = post_total * target_case1_w
            prev_cap2 = post_total * (1.0 - target_case1_w)
            prev_total = post_total
            fee_paid += fee
            rebalance_count += 1

        cap1[i] = prev_cap1
        cap2[i] = prev_cap2
        total[i] = prev_total
        case1_w[i] = prev_cap1 / prev_total if prev_total > 0 else np.nan

    out["cap1_rebalanced"] = cap1
    out["cap2_rebalanced"] = cap2
    out["case1_weight"] = case1_w
    out["equity_total"] = total
    return out, {"rebalance_count": rebalance_count, "fee_paid": fee_paid}


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
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
    ax_eq.axhline(INITIAL_CAPITAL_TOTAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("69 Study: Periodic Rebalance Sweep on Case1 + Case2")
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

    ax_mdd.bar(metrics_df["variant"], metrics_df["rebalance_count"], color=[colors[v] for v in variants], alpha=0.85, label="Rebalances")
    ax_mdd.set_ylabel("Rebalances")
    ax_mdd.grid(True, axis="y", alpha=0.2)
    ax_mdd.tick_params(axis="x", rotation=20)
    ax_mdd_t = ax_mdd.twinx()
    ax_mdd_t.plot(metrics_df["variant"], metrics_df["fee_paid"], color="#9467bd", marker="o", linewidth=1.1, label="Fee Paid")
    ax_mdd_t.set_ylabel("Fee Paid (USDT)")
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
    lines.append("# Study 69: Periodic Rebalance Sweep on Case1 + Case2")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Source combined curve: `{CASE_VARIANT}` from study 62")
    lines.append("- Portfolio is rebalanced to a fixed target case1 weight on a fixed schedule")
    lines.append(f"- Rebalance fee model: `2 * moved_notional * {REBALANCE_FEE_RATE:.4f}`")
    lines.append("- This is a capital-allocation overlay only; underlying trade paths are unchanged")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | Total CAGR % | Total MDD % | Total Calmar | Rebalances | Fee Paid | Avg Case1 W |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['total_cagr_pct'])} | {_fmt(row['total_mdd_pct'])} | {_fmt(row['total_calmar_ratio'])} | "
            f"{int(row['rebalance_count'])} | {_fmt(row['fee_paid'])} | {_fmt(row['avg_case1_weight'])} |"
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
        lines.append("- At least one periodic rebalance variant dominated the hold baseline on both CAGR and MDD.")
    else:
        lines.append("- No periodic rebalance variant dominated the hold baseline on both CAGR and MDD.")
    lines.append("- If rebalancing alone helps materially, then a large part of the opportunity is portfolio construction rather than entry logic.")
    lines.append("- If only very frequent rebalancing helps, robustness to fees should be treated as the next validation step.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    curve = load_curve()
    hold_stats = compute_curve_stats(curve, "equity_total", INITIAL_CAPITAL_TOTAL)
    if abs(hold_stats["final_equity"] - EXPECTED_HOLD_BASELINE["final_equity"]) > 1e-6:
        raise ValueError("hold baseline final equity mismatch")
    if abs(hold_stats["cagr_pct"] - EXPECTED_HOLD_BASELINE["cagr_pct"]) > 1e-6:
        raise ValueError("hold baseline cagr mismatch")
    if abs(hold_stats["max_drawdown_pct"] - EXPECTED_HOLD_BASELINE["mdd_pct"]) > 1e-6:
        raise ValueError("hold baseline mdd mismatch")

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        variant = str(cfg["variant"])
        if cfg["mode"] == "hold":
            out = curve.copy()
            out["case1_weight"] = out["equity_case1"] / out["equity_total"]
            run_stats = {"rebalance_count": 0, "fee_paid": 0.0}
        else:
            out, run_stats = run_rebalanced_portfolio(curve, str(cfg["freq"]), float(cfg["target_case1_w"]))
        out["variant"] = variant
        stats = compute_curve_stats(out, "equity_total", INITIAL_CAPITAL_TOTAL)
        rows.append(
            {
                "variant": variant,
                "mode": cfg["mode"],
                "freq": cfg.get("freq", "hold"),
                "target_case1_w": float(cfg.get("target_case1_w", np.nan)),
                "total_final_equity": stats["final_equity"],
                "total_return_pct": stats["total_return_pct"],
                "total_cagr_pct": stats["cagr_pct"],
                "total_mdd_pct": stats["max_drawdown_pct"],
                "total_calmar_ratio": stats["calmar_ratio"],
                "rebalance_count": run_stats["rebalance_count"],
                "fee_paid": run_stats["fee_paid"],
                "avg_case1_weight": float(out["case1_weight"].mean()),
            }
        )
        curves_out.append(out)
        curve_map[variant] = out.copy()

    metrics_df = pd.DataFrame(rows).sort_values(["total_calmar_ratio", "total_cagr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curves_out, ignore_index=True)

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
