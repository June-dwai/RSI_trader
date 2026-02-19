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

SCRIPT_FILE = Path("14_backtest_btcusdt_best_hyst_fixed5x_sl_sweep.py")
PLOT_FILE = Path("14_backtest_btcusdt_best_hyst_fixed5x_sl_sweep.png")
CSV_FILE = Path("14_backtest_btcusdt_best_hyst_fixed5x_sl_sweep.csv")
MD_FILE = Path("14_backtest_btcusdt_best_hyst_fixed5x_sl_sweep.md")

TARGET_SYMBOL = "BTCUSDT"
DEFAULT_BEST_HYST_BAND = 0.005
STOP_LOSS_VALUES = [0.02, 0.03, 0.04, 0.05, 0.06]  # 2%, 3%, 4%, 5%, 6%


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
    labels = metrics_df["sl_label"].tolist()

    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("14 BTCUSDT: 08 Best Hysteresis Fixed5x - SL Sweep")
    ax_eq.set_ylabel("Equity (USDT)")
    for i, sl_label in enumerate(labels):
        eq = equity_map.get(sl_label)
        if eq is None or eq.empty:
            continue
        ax_eq.plot(eq["timestamp"], eq["equity"], label=sl_label, linewidth=1.2, color=colors(i))
    ax_eq.legend(loc="upper left")
    ax_eq.grid(True, alpha=0.2)

    ax_final = fig.add_subplot(gs[1, 0])
    ax_final.set_title("Final Equity by SL")
    ax_final.bar(metrics_df["sl_label"], metrics_df["final_equity"], color=[colors(i) for i in range(len(metrics_df))])
    ax_final.set_ylabel("USDT")
    ax_final.set_xlabel("Stop Loss")
    ax_final.grid(True, axis="y", alpha=0.2)

    ax_mdd = fig.add_subplot(gs[1, 1])
    ax_mdd.set_title("MDD by SL")
    ax_mdd.bar(metrics_df["sl_label"], metrics_df["max_drawdown_pct"], color=[colors(i) for i in range(len(metrics_df))])
    ax_mdd.set_ylabel("MDD (%)")
    ax_mdd.set_xlabel("Stop Loss")
    ax_mdd.grid(True, axis="y", alpha=0.2)

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
    plt.close()


def save_md(metrics_df: pd.DataFrame, best_band: float):
    best_eq = metrics_df.sort_values("final_equity", ascending=False).iloc[0]
    best_calmar = metrics_df.sort_values("calmar_ratio", ascending=False).iloc[0]
    best_mdd = metrics_df.sort_values("max_drawdown_pct", ascending=True).iloc[0]

    lines: list[str] = []
    lines.append("# 14 BTCUSDT - Best Hysteresis Fixed5x SL Sweep")
    lines.append("")
    lines.append("## 1) Objective")
    lines.append("- Test only stop-loss sensitivity on BTC for `08_best_hysteresis_fixed5x` logic.")
    lines.append("- Keep hysteresis to best value from `08_backtest_btcusdt_hysteresis_sweep.csv`.")
    lines.append("- Keep base params from `04.configure_baseline_params` except SL.")
    lines.append("")
    lines.append("## 2) Test Setup")
    lines.append(f"- Symbol: `{TARGET_SYMBOL}`")
    lines.append("- Data period: `2022-01-01` to `2026-02-12`")
    lines.append(f"- Hysteresis band fixed: `{best_band * 100:.2f}%`")
    lines.append("- Entry scale: `0.50` (base default)")
    lines.append("- TP fixed: `1.20%` (baseline)")
    lines.append("- SL sweep (%): `2.00`, `3.00`, `4.00`, `5.00`, `6.00`")
    lines.append("")
    lines.append("## 3) Results")
    lines.append("")
    lines.append("| SL | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Worst Month |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['sl_label']}` | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | {_fmt(r['cagr_pct'])} | "
            f"{_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} | "
            f"`{r['worst_month']}` |"
        )

    lines.append("")
    lines.append("## 4) Best Picks")
    lines.append(f"- Best Final Equity: `{best_eq['sl_label']}` (`{_fmt(best_eq['final_equity'])} USDT`).")
    lines.append(f"- Best Calmar: `{best_calmar['sl_label']}` (`{_fmt(best_calmar['calmar_ratio'])}`).")
    lines.append(f"- Lowest MDD: `{best_mdd['sl_label']}` (`{_fmt(best_mdd['max_drawdown_pct'])}%`).")
    lines.append("")
    lines.append("## 5) Output Files")
    lines.append(f"- script: `{SCRIPT_FILE}`")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{CSV_FILE}`")
    lines.append(f"- report: `{MD_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_13", BASE_002_PATH)
    helper_04 = load_module("m04_13", BASE_04_PATH)
    helper_08 = load_module("m08_13", BASE_08_PATH)

    best_band = detect_best_hysteresis_band(BASE_08_CSV, DEFAULT_BEST_HYST_BAND)
    base_module.SYMBOL = TARGET_SYMBOL

    df_1m, df_4h = base_module.load_data()
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    cls = helper_08.build_fixed5x_hyst_class(base_module, helper_04, best_band)

    rows = []
    equity_map: dict[str, pd.DataFrame] = {}

    for i, sl in enumerate(STOP_LOSS_VALUES, start=1):
        sl_label = f"{sl * 100:.2f}%"
        print(f"[{i}/{len(STOP_LOSS_VALUES)}] run sl={sl_label}")

        bt = cls(
            symbol=base_module.SYMBOL,
            initial_capital=base_module.INITIAL_CAPITAL,
            commission=base_module.COMMISSION,
            entry_scale=base_module.ENTRY_SCALE,
        )
        helper_04.configure_baseline_params(bt)
        bt.stop_loss_pct = sl

        bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)
        metrics = helper_04.calculate_metrics(bt, base_module.INITIAL_CAPITAL)
        metrics["stop_loss_pct"] = sl
        metrics["sl_label"] = sl_label

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            equity_map[sl_label] = eq[["timestamp", "equity"]].copy()
            metrics["worst_month"] = _worst_month(eq)
        else:
            equity_map[sl_label] = pd.DataFrame(columns=["timestamp", "equity"])
            metrics["worst_month"] = "N/A"

        rows.append(metrics)

    metrics_df = pd.DataFrame(rows).sort_values("stop_loss_pct").reset_index(drop=True)
    metrics_df.to_csv(CSV_FILE, index=False)
    save_plot(equity_map, metrics_df)
    save_md(metrics_df, best_band)

    show_cols = [
        "sl_label",
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
