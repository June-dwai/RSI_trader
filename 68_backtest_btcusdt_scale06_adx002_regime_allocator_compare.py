from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
INPUT_CURVES_CSV = Path("62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune_curves.csv")

OUT_BASE = "68_backtest_btcusdt_scale06_adx002_regime_allocator_compare"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

CASE_VARIANT = "shallow6_else2bull"
INITIAL_CAPITAL_TOTAL = 2000.0

EXPECTED_HOLD_BASELINE = {
    "final_equity": 37042.70606845802,
    "cagr_pct": 103.27812652063195,
    "mdd_pct": 50.853607894861834,
}

VARIANTS = [
    {"variant": "hold_50_50_baseline", "mode": "hold"},
    {"variant": "rebal_eq50_4h", "mode": "regime", "bull_case1_w": 0.50, "bear_case1_w": 0.50, "dd_cut_case1_w": 0.50, "dd_trigger_pct": 999.0},
    {"variant": "trend70_35", "mode": "regime", "bull_case1_w": 0.70, "bear_case1_w": 0.35, "dd_cut_case1_w": 0.35, "dd_trigger_pct": 999.0},
    {"variant": "trend80_20", "mode": "regime", "bull_case1_w": 0.80, "bear_case1_w": 0.20, "dd_cut_case1_w": 0.20, "dd_trigger_pct": 999.0},
    {"variant": "trend90_10", "mode": "regime", "bull_case1_w": 0.90, "bear_case1_w": 0.10, "dd_cut_case1_w": 0.10, "dd_trigger_pct": 999.0},
    {"variant": "trend80_10_dd20", "mode": "regime", "bull_case1_w": 0.80, "bear_case1_w": 0.20, "dd_cut_case1_w": 0.10, "dd_trigger_pct": 20.0},
    {"variant": "trend85_10_dd15", "mode": "regime", "bull_case1_w": 0.85, "bear_case1_w": 0.15, "dd_cut_case1_w": 0.10, "dd_trigger_pct": 15.0},
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
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "calmar_ratio": calmar_ratio,
    }


def load_case_curves() -> pd.DataFrame:
    curves = pd.read_csv(INPUT_CURVES_CSV, parse_dates=["timestamp"])
    curve = curves[curves["variant"] == CASE_VARIANT][["timestamp", "equity_case1", "equity_case2", "equity_total"]].copy()
    if curve.empty:
        raise ValueError(f"missing variant: {CASE_VARIANT}")
    curve = curve.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)
    return curve


def prepare_regime_series(m47, timestamps: pd.Series) -> pd.DataFrame:
    start_ts = pd.Timestamp(timestamps.iloc[0])
    end_ts = pd.Timestamp(timestamps.iloc[-1])
    _, df_4h = m47.load_data_no_filter()
    df_4h = df_4h[(df_4h.index >= start_ts.floor("4h") - pd.Timedelta(days=60)) & (df_4h.index <= end_ts.ceil("4h"))].copy()
    df_4h["ema200_closed"] = df_4h["close"].ewm(span=m47.EMA_PERIOD, adjust=False).mean()
    df_4h["ema200_prev_closed"] = df_4h["ema200_closed"].shift(1)
    df_4h["trend_4h_hyst"] = m47.LiveParityNoLookahead._compute_hysteresis_state(
        df_4h["close"], df_4h["ema200_prev_closed"], m47.HYSTERESIS_BAND
    )
    df_4h["trend_4h_confirmed"] = df_4h["trend_4h_hyst"].shift(1)

    regime = pd.DataFrame({"timestamp": timestamps.copy()})
    regime["bucket_4h"] = regime["timestamp"].dt.floor("4h")
    regime["is_new_4h_bucket"] = regime["bucket_4h"] != regime["bucket_4h"].shift(1)
    regime = regime.merge(df_4h[["trend_4h_confirmed"]], left_on="bucket_4h", right_index=True, how="left")
    regime["trend_4h_confirmed"] = regime["trend_4h_confirmed"].ffill()
    return regime[["timestamp", "is_new_4h_bucket", "trend_4h_confirmed"]]


def run_regime_allocator(curve: pd.DataFrame, regime: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    merged = curve.merge(regime, on="timestamp", how="left")
    merged["trend_4h_confirmed"] = merged["trend_4h_confirmed"].ffill().fillna("bullish")
    merged["is_new_4h_bucket"] = merged["is_new_4h_bucket"].fillna(False)

    case1_ret = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    case2_ret = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    trend = merged["trend_4h_confirmed"].astype(str).to_numpy()
    is_new_4h = merged["is_new_4h_bucket"].astype(bool).to_numpy()
    timestamps = merged["timestamp"].to_numpy()

    case1_dd = ((merged["equity_case1"].astype(float) / merged["equity_case1"].astype(float).cummax()) - 1.0).fillna(0.0) * -100.0
    case1_dd = case1_dd.to_numpy()

    bull_case1_w = float(cfg["bull_case1_w"])
    bear_case1_w = float(cfg["bear_case1_w"])
    dd_cut_case1_w = float(cfg["dd_cut_case1_w"])
    dd_trigger_pct = float(cfg["dd_trigger_pct"])

    total_eq = np.zeros(len(merged), dtype=float)
    case1_w = np.zeros(len(merged), dtype=float)
    case2_w = np.zeros(len(merged), dtype=float)
    total_eq[0] = INITIAL_CAPITAL_TOTAL
    case1_w[0] = 0.50
    case2_w[0] = 0.50

    for i in range(1, len(merged)):
        w1 = case1_w[i - 1]
        if is_new_4h[i]:
            if trend[i] == "bearish":
                w1 = bear_case1_w
                if float(case1_dd[i - 1]) >= dd_trigger_pct:
                    w1 = dd_cut_case1_w
            else:
                w1 = bull_case1_w
        w2 = 1.0 - w1
        total_eq[i] = total_eq[i - 1] * (1.0 + w1 * float(case1_ret[i]) + w2 * float(case2_ret[i]))
        case1_w[i] = w1
        case2_w[i] = w2

    out = merged[["timestamp", "equity_case1", "equity_case2"]].copy()
    out["case1_weight"] = case1_w
    out["case2_weight"] = case2_w
    out["equity_total"] = total_eq
    return out


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
    ax_eq.set_title("68 Study: Dynamic Regime Allocation Between Case1 and Case2")
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

    ax_mdd.bar(metrics_df["variant"], metrics_df["avg_case1_weight"], color=[colors[v] for v in variants], alpha=0.85, label="Avg Case1 Weight")
    ax_mdd.set_ylabel("Avg Case1 Weight")
    ax_mdd.grid(True, axis="y", alpha=0.2)
    ax_mdd.tick_params(axis="x", rotation=20)
    ax_mdd_t = ax_mdd.twinx()
    ax_mdd_t.plot(metrics_df["variant"], metrics_df["bear_case1_weight_realized"], color="#9467bd", marker="o", linewidth=1.1, label="Bear Case1 Weight")
    ax_mdd_t.set_ylabel("Bear Case1 Weight")
    h1, l1 = ax_mdd.get_legend_handles_labels()
    h2, l2 = ax_mdd_t.get_legend_handles_labels()
    ax_mdd.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    baseline = metrics_df[metrics_df["variant"] == "hold_50_50_baseline"].iloc[0]
    best = metrics_df.iloc[0]

    lines: list[str] = []
    lines.append("# Study 68: Dynamic Regime Allocation Between Case1 and Case2")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Source combined curve: `{CASE_VARIANT}` from study 62")
    lines.append("- Allocation logic uses only confirmed 4h trend and lagged case1 drawdown")
    lines.append("- Rebalance happens only on 4h bucket transitions, so there is no future leak from same-bucket information")
    lines.append("- This changes capital allocation, not the underlying trade path of either sleeve")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | Total CAGR % | Total MDD % | Total Calmar | Avg Case1 W | Bear Case1 W |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['total_cagr_pct'])} | {_fmt(row['total_mdd_pct'])} | {_fmt(row['total_calmar_ratio'])} | "
            f"{_fmt(row['avg_case1_weight'])} | {_fmt(row['bear_case1_weight_realized'])} |"
        )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}`: total CAGR `{_fmt(best['total_cagr_pct'])}%`, total MDD `{_fmt(best['total_mdd_pct'])}%`, total Calmar `{_fmt(best['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Delta vs hold_50_50_baseline")
    for _, row in metrics_df.iterrows():
        if row["variant"] == "hold_50_50_baseline":
            continue
        lines.append(
            f"- `{row['variant']}`: CAGR `{_fmt(row['total_cagr_pct'] - baseline['total_cagr_pct'])}pp`, "
            f"MDD `{_fmt(row['total_mdd_pct'] - baseline['total_mdd_pct'])}pp`, "
            f"Calmar `{_fmt(row['total_calmar_ratio'] - baseline['total_calmar_ratio'])}`"
        )
    lines.append("")
    lines.append("## Interpretation")
    if ((metrics_df["total_cagr_pct"] > baseline["total_cagr_pct"]) & (metrics_df["total_mdd_pct"] < baseline["total_mdd_pct"])).any():
        lines.append("- At least one regime allocator dominated the existing hold baseline on both CAGR and MDD.")
    else:
        lines.append("- No tested regime allocator dominated the existing hold baseline on both CAGR and MDD.")
    lines.append("- If trend allocators help, then the next structural lever is capital routing, not more micro-edits inside case1.")
    lines.append("- If trend allocators still fail, then the core return streams themselves need replacement rather than redistribution.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    curve = load_case_curves()
    hold_stats = compute_curve_stats(curve, "equity_total", INITIAL_CAPITAL_TOTAL)
    if abs(hold_stats["final_equity"] - EXPECTED_HOLD_BASELINE["final_equity"]) > 1e-6:
        raise ValueError("hold baseline final equity mismatch")
    if abs(hold_stats["cagr_pct"] - EXPECTED_HOLD_BASELINE["cagr_pct"]) > 1e-6:
        raise ValueError("hold baseline cagr mismatch")
    if abs(hold_stats["max_drawdown_pct"] - EXPECTED_HOLD_BASELINE["mdd_pct"]) > 1e-6:
        raise ValueError("hold baseline mdd mismatch")

    m47 = load_module("study47_for_68", BASE_47_PATH)
    regime = prepare_regime_series(m47, curve["timestamp"])

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        variant = str(cfg["variant"])
        if cfg["mode"] == "hold":
            out = curve.copy()
            out["case1_weight"] = out["equity_case1"] / out["equity_total"]
            out["case2_weight"] = out["equity_case2"] / out["equity_total"]
        else:
            out = run_regime_allocator(curve, regime, cfg)
        out["variant"] = variant
        stats = compute_curve_stats(out, "equity_total", INITIAL_CAPITAL_TOTAL)
        bear_weight = float(out.loc[regime["trend_4h_confirmed"].astype(str).eq("bearish"), "case1_weight"].mean())
        rows.append(
            {
                "variant": variant,
                "mode": cfg["mode"],
                "total_final_equity": stats["final_equity"],
                "total_return_pct": stats["total_return_pct"],
                "total_cagr_pct": stats["cagr_pct"],
                "total_mdd_pct": stats["max_drawdown_pct"],
                "total_calmar_ratio": stats["calmar_ratio"],
                "avg_case1_weight": float(out["case1_weight"].mean()),
                "bear_case1_weight_realized": bear_weight,
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
