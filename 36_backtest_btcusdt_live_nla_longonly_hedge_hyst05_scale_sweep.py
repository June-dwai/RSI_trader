from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
BASE_35_PATH = Path("35_backtest_btcusdt_live_nla_longonly_hedge_hyst05.py")
BASE_35_CSV = Path("35_backtest_btcusdt_live_nla_longonly_hedge_hyst05.csv")

OUT_BASE = "36_backtest_btcusdt_live_nla_longonly_hedge_hyst05_scale_sweep"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")

INITIAL_CAPITAL = 1000.0
ENTRY_SCALES = [0.60, 0.70]


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


def save_plot(equity_map: dict[float, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_ret, ax_risk = axes

    cmap = plt.get_cmap("plasma")
    scales = metrics_df["entry_scale"].astype(float).tolist()
    colors = {s: cmap(i / max(1, len(scales) - 1)) for i, s in enumerate(scales)}

    for s in scales:
        eq = equity_map.get(s)
        if eq is None or eq.empty:
            continue
        ax_eq.plot(eq["timestamp"], eq["equity"], linewidth=1.05, color=colors[s], label=f"scale={s:.2f}")
    ax_eq.axhline(INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9, label="Start 1000")
    ax_eq.set_title("36 Study: Scale Sweep on Study-35 Core (Long-only + Hyst 0.5% Hedge)")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_ret.bar(metrics_df["entry_scale"], metrics_df["final_equity"], color=[colors[s] for s in scales], alpha=0.85, label="Final Equity")
    ax_ret.set_ylabel("Final Equity")
    ax_ret.grid(True, axis="y", alpha=0.2)
    ax_ret_t = ax_ret.twinx()
    ax_ret_t.plot(metrics_df["entry_scale"], metrics_df["cagr_pct"], color="#d62728", marker="o", linewidth=1.1, label="CAGR %")
    ax_ret_t.set_ylabel("CAGR %")
    ax_ret.set_xlabel("Entry Scale")
    ax_ret.set_xticks(scales)
    h1, l1 = ax_ret.get_legend_handles_labels()
    h2, l2 = ax_ret_t.get_legend_handles_labels()
    ax_ret.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_risk.bar(metrics_df["entry_scale"], metrics_df["max_drawdown_pct"], color=[colors[s] for s in scales], alpha=0.85, label="MDD %")
    ax_risk.set_ylabel("MDD %")
    ax_risk.grid(True, axis="y", alpha=0.2)
    ax_risk_t = ax_risk.twinx()
    ax_risk_t.plot(metrics_df["entry_scale"], metrics_df["calmar_ratio"], color="#1f77b4", marker="o", linewidth=1.1, label="Calmar")
    ax_risk_t.set_ylabel("Calmar")
    ax_risk.set_xlabel("Entry Scale")
    ax_risk.set_xticks(scales)
    h1, l1 = ax_risk.get_legend_handles_labels()
    h2, l2 = ax_risk_t.get_legend_handles_labels()
    ax_risk.legend(h1 + h2, l1 + l2, loc="upper left")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    base35 = None
    if BASE_35_CSV.exists():
        t = pd.read_csv(BASE_35_CSV)
        if not t.empty:
            base35 = t.iloc[0]

    best_calmar = metrics_df.sort_values("calmar_ratio", ascending=False).iloc[0]
    best_cagr = metrics_df.sort_values("cagr_pct", ascending=False).iloc[0]
    best_mdd = metrics_df.sort_values("max_drawdown_pct", ascending=True).iloc[0]

    lines: list[str] = []
    lines.append("# 36 Backtest: Entry Scale Sweep (0.60 / 0.70) on Study-35 Core")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Base engine: study-35 (`long-only + trend short hedge`, 4h hysteresis band 0.5%).")
    lines.append("- Symbol: `BTCUSDT`")
    lines.append("- Initial capital: `1000`")
    lines.append(f"- Entry scales tested: `{', '.join(f'{s:.2f}' for s in ENTRY_SCALES)}`")
    lines.append("- No-lookahead guard: same as study-35.")
    lines.append("")
    lines.append("## Results")
    lines.append("| Entry Scale | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Hedge Open/Close |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| {_fmt(r['entry_scale'], 2)} | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | {_fmt(r['cagr_pct'])} | "
            f"{_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} | "
            f"{int(r['hedge_open_events'])}/{int(r['hedge_close_events'])} |"
        )

    lines.append("")
    lines.append("## Best Cases")
    lines.append(f"- Best CAGR: `scale={_fmt(best_cagr['entry_scale'], 2)}` ({_fmt(best_cagr['cagr_pct'])}%).")
    lines.append(f"- Lowest MDD: `scale={_fmt(best_mdd['entry_scale'], 2)}` ({_fmt(best_mdd['max_drawdown_pct'])}%).")
    lines.append(f"- Best Calmar: `scale={_fmt(best_calmar['entry_scale'], 2)}` ({_fmt(best_calmar['calmar_ratio'])}).")

    if base35 is not None:
        lines.append("")
        lines.append("## Delta vs Study-35 (Scale 0.50)")
        lines.append("| Entry Scale | Final Equity Delta | CAGR Delta (pp) | MDD Delta (pp) | Calmar Delta |")
        lines.append("|---:|---:|---:|---:|---:|")
        for _, r in metrics_df.iterrows():
            lines.append(
                f"| {_fmt(r['entry_scale'], 2)} | {_fmt(r['final_equity'] - float(base35['final_equity']))} | "
                f"{_fmt(r['cagr_pct'] - float(base35['cagr_pct']))} | "
                f"{_fmt(r['max_drawdown_pct'] - float(base35['max_drawdown_pct']))} | "
                f"{_fmt(r['calmar_ratio'] - float(base35['calmar_ratio']))} |"
            )

    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    base = load_module("m002_36", BASE_002_PATH)
    helper = load_module("m04_36", BASE_04_PATH)
    m35 = load_module("m35_36", BASE_35_PATH)

    df_1m, df_4h = m35.load_data_no_filter(base)
    df_1m = df_1m[(df_1m.index >= base.BACKTEST_START) & (df_1m.index <= base.BACKTEST_END)].copy()

    rows: list[dict] = []
    equity_map: dict[float, pd.DataFrame] = {}

    for scale in ENTRY_SCALES:
        bt = m35.LiveParityNoLookahead(
            base_module=base,
            symbol=base.SYMBOL,
            initial_capital=INITIAL_CAPITAL,
            commission=base.COMMISSION,
            entry_scale=float(scale),
        )
        helper.configure_baseline_params(bt)
        bt.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)

        metrics = helper.calculate_metrics(bt, INITIAL_CAPITAL)
        metrics["entry_scale"] = float(scale)
        metrics["hedge_open_events"] = int(bt.stats.get("hedge_open_events", 0))
        metrics["hedge_close_events"] = int(bt.stats.get("hedge_close_events", 0))
        rows.append(metrics)

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            equity_map[float(scale)] = eq[["timestamp", "equity"]].copy()
        else:
            equity_map[float(scale)] = pd.DataFrame(columns=["timestamp", "equity"])

    metrics_df = pd.DataFrame(rows).sort_values("entry_scale").reset_index(drop=True)
    cols = [
        "entry_scale",
        "final_equity",
        "total_return_pct",
        "cagr_pct",
        "max_drawdown_pct",
        "calmar_ratio",
        "trades",
        "long_trades",
        "short_trades",
        "win_rate_pct",
        "profit_factor",
        "hedge_open_events",
        "hedge_close_events",
    ]
    metrics_df[cols].to_csv(OUT_CSV, index=False)
    save_plot(equity_map, metrics_df[cols])
    save_report(metrics_df[cols])

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df[cols].to_string(index=False))


if __name__ == "__main__":
    run()
