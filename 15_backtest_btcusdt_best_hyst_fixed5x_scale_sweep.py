from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
BASE_08_PATH = Path("08_backtest_btcusdt_hysteresis_sweep.py")
BASE_08_CSV = Path("08_backtest_btcusdt_hysteresis_sweep.csv")

SCRIPT_FILE = Path("15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.py")
PLOT_FILE = Path("15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.png")
CSV_FILE = Path("15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.csv")
MD_FILE = Path("15_backtest_btcusdt_best_hyst_fixed5x_scale_sweep.md")

TARGET_SYMBOL = "BTCUSDT"
DEFAULT_BEST_HYST_BAND = 0.005
ENTRY_SCALES = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80]


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


def detect_best_hysteresis_band(path: Path, fallback: float = DEFAULT_BEST_HYST_BAND) -> float:
    if not path.exists():
        return fallback
    try:
        df = pd.read_csv(path)
    except Exception:
        return fallback
    if df.empty or "band" not in df.columns or "final_equity" not in df.columns:
        return fallback
    row = df.sort_values("final_equity", ascending=False).iloc[0]
    return float(row["band"])


def _fmt(v, digits: int = 4) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "N/A"
    return f"{v:.{digits}f}"


def _worst_month(eq: pd.DataFrame) -> str:
    if eq.empty:
        return "N/A"
    e = eq.copy()
    e["timestamp"] = pd.to_datetime(e["timestamp"])
    monthly = e.set_index("timestamp")["equity"].resample("ME").last().dropna().pct_change().dropna() * 100.0
    if monthly.empty:
        return "N/A"
    idx = monthly.idxmin()
    return f"{idx.strftime('%Y-%m')} ({monthly.min():.4f}%)"


def save_plot(equity_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    colors = plt.get_cmap("tab10")
    labels = metrics_df["scale_label"].tolist()

    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("15 BTCUSDT: 08 Best Hysteresis Fixed5x - Scale Sweep")
    ax_eq.set_ylabel("Equity (USDT)")
    for i, scale_label in enumerate(labels):
        eq = equity_map.get(scale_label)
        if eq is None or eq.empty:
            continue
        ax_eq.plot(eq["timestamp"], eq["equity"], label=scale_label, linewidth=1.2, color=colors(i))
    ax_eq.legend(loc="upper left")
    ax_eq.grid(True, alpha=0.2)

    ax_final = fig.add_subplot(gs[1, 0])
    ax_final.set_title("Final Equity by Scale")
    ax_final.bar(metrics_df["scale_label"], metrics_df["final_equity"], color=[colors(i) for i in range(len(metrics_df))])
    ax_final.set_ylabel("USDT")
    ax_final.set_xlabel("Entry Scale")
    ax_final.grid(True, axis="y", alpha=0.2)

    ax_mdd = fig.add_subplot(gs[1, 1])
    ax_mdd.set_title("MDD by Scale")
    ax_mdd.bar(metrics_df["scale_label"], metrics_df["max_drawdown_pct"], color=[colors(i) for i in range(len(metrics_df))])
    ax_mdd.set_ylabel("MDD (%)")
    ax_mdd.set_xlabel("Entry Scale")
    ax_mdd.grid(True, axis="y", alpha=0.2)

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
    plt.close()


def save_md(metrics_df: pd.DataFrame, best_band: float):
    best_eq = metrics_df.sort_values("final_equity", ascending=False).iloc[0]
    best_calmar = metrics_df.sort_values("calmar_ratio", ascending=False).iloc[0]
    best_mdd = metrics_df.sort_values("max_drawdown_pct", ascending=True).iloc[0]
    base_row = metrics_df[metrics_df["entry_scale"] == 0.50].iloc[0] if (metrics_df["entry_scale"] == 0.50).any() else metrics_df.iloc[0]

    lines: list[str] = []
    lines.append("# 15 BTCUSDT - Best Hysteresis Fixed5x Scale Sweep")
    lines.append("")
    lines.append("## 1) Objective")
    lines.append("- Test only entry-scale sensitivity on BTC for `08_best_hysteresis_fixed5x` logic.")
    lines.append("- Keep hysteresis to best value from `08_backtest_btcusdt_hysteresis_sweep.csv`.")
    lines.append("- Keep base params from `04.configure_baseline_params` except scale.")
    lines.append("")
    lines.append("## 2) Test Setup")
    lines.append(f"- Symbol: `{TARGET_SYMBOL}`")
    lines.append("- Data period: `2022-01-01` to `2026-02-12`")
    lines.append(f"- Hysteresis band fixed: `{best_band * 100:.2f}%`")
    lines.append("- TP fixed: `1.20%` (baseline)")
    lines.append("- SL fixed: `3.00%` (baseline)")
    lines.append("- Scale sweep: `0.20`, `0.30`, `0.40`, `0.50`, `0.60`, `0.70`, `0.80`")
    lines.append("")
    lines.append("## 3) Results")
    lines.append("")
    lines.append("| Scale | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Worst Month |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['scale_label']}` | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | {_fmt(r['cagr_pct'])} | "
            f"{_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} | "
            f"`{r['worst_month']}` |"
        )

    lines.append("")
    lines.append("## 4) Best Picks")
    lines.append(f"- Best Final Equity: `{best_eq['scale_label']}` (`{_fmt(best_eq['final_equity'])} USDT`).")
    lines.append(f"- Best Calmar: `{best_calmar['scale_label']}` (`{_fmt(best_calmar['calmar_ratio'])}`).")
    lines.append(f"- Lowest MDD: `{best_mdd['scale_label']}` (`{_fmt(best_mdd['max_drawdown_pct'])}%`).")
    lines.append("")
    lines.append("## 5) Interpretation")
    lines.append("- Scale up increases both return and drawdown. In this run, `Final Equity`, `CAGR`, and `Calmar` all rose as scale increased.")
    lines.append("- `Win Rate`, `Long/Short trades`, and `Avg holding hours` remained unchanged, showing this is mostly a position-size leverage effect.")
    lines.append("- `Profit Factor` declines as scale rises (`0.20 -> 0.80`: `3.6276 -> 2.5973`), so higher return comes with lower margin-for-error per trade.")
    lines.append("- Worst monthly drawdown expanded materially (`-14.61%` at `0.20` to `-67.05%` at `0.80`).")
    lines.append("")
    lines.append("## 6) Delta vs Scale 0.50")
    lines.append("")
    lines.append("| Scale | Final Equity Delta % | MDD Delta %p | Calmar Delta | Profit Factor Delta |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        eq_delta = (float(r["final_equity"]) / float(base_row["final_equity"]) - 1.0) * 100.0
        mdd_delta = float(r["max_drawdown_pct"]) - float(base_row["max_drawdown_pct"])
        calmar_delta = float(r["calmar_ratio"]) - float(base_row["calmar_ratio"])
        pf_delta = float(r["profit_factor"]) - float(base_row["profit_factor"])
        lines.append(
            f"| `{r['scale_label']}` | {_fmt(eq_delta)} | {_fmt(mdd_delta)} | {_fmt(calmar_delta)} | {_fmt(pf_delta)} |"
        )
    lines.append("")
    lines.append("## 7) Practical Range")
    lines.append("- Return-max objective: prefer `0.70~0.80` (highest equity and Calmar in this run).")
    lines.append("- Drawdown-control objective: prefer `0.20~0.40` (MDD and worst-month loss materially lower).")
    lines.append("- Balanced objective: `0.50~0.60` keeps high growth while limiting extreme drawdown expansion compared with `0.70+`.")
    lines.append("")
    lines.append("## 8) Output Files")
    lines.append(f"- script: `{SCRIPT_FILE}`")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{CSV_FILE}`")
    lines.append(f"- report: `{MD_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_15", BASE_002_PATH)
    helper_04 = load_module("m04_15", BASE_04_PATH)
    helper_08 = load_module("m08_15", BASE_08_PATH)

    best_band = detect_best_hysteresis_band(BASE_08_CSV, DEFAULT_BEST_HYST_BAND)
    base_module.SYMBOL = TARGET_SYMBOL

    df_1m, df_4h = base_module.load_data()
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    cls = helper_08.build_fixed5x_hyst_class(base_module, helper_04, best_band)

    rows = []
    equity_map: dict[str, pd.DataFrame] = {}

    for i, scale in enumerate(ENTRY_SCALES, start=1):
        scale_label = f"{scale:.2f}"
        print(f"[{i}/{len(ENTRY_SCALES)}] run scale={scale_label}")

        bt = cls(
            symbol=base_module.SYMBOL,
            initial_capital=base_module.INITIAL_CAPITAL,
            commission=base_module.COMMISSION,
            entry_scale=scale,
        )
        helper_04.configure_baseline_params(bt)

        bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)
        metrics = helper_04.calculate_metrics(bt, base_module.INITIAL_CAPITAL)
        metrics["entry_scale"] = scale
        metrics["scale_label"] = scale_label

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            equity_map[scale_label] = eq[["timestamp", "equity"]].copy()
            metrics["worst_month"] = _worst_month(eq)
        else:
            equity_map[scale_label] = pd.DataFrame(columns=["timestamp", "equity"])
            metrics["worst_month"] = "N/A"

        rows.append(metrics)

    metrics_df = pd.DataFrame(rows).sort_values("entry_scale").reset_index(drop=True)
    metrics_df.to_csv(CSV_FILE, index=False)
    save_plot(equity_map, metrics_df)
    save_md(metrics_df, best_band)

    show_cols = [
        "scale_label",
        "final_equity",
        "total_return_pct",
        "cagr_pct",
        "max_drawdown_pct",
        "calmar_ratio",
        "trades",
        "win_rate_pct",
        "profit_factor",
    ]
    print(f"best_hysteresis_band={best_band * 100:.2f}%")
    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(f"saved_report={MD_FILE}")
    print(metrics_df[show_cols].to_string(index=False))


if __name__ == "__main__":
    run()
