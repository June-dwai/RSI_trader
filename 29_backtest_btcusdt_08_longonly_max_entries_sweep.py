from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
BASE_28_PATH = Path("28_backtest_btcusdt_08_02_split500.py")

OUT_BASE = "29_backtest_btcusdt_08_longonly_max_entries_sweep"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")

ENTRY_SCALE = 0.50
LEG_CAPITAL = 500.0
MAX_ENTRIES_LIST = [2, 3, 4, 5, 6, 7]


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


def build_max_entries_class(base_cls, max_entries: int):
    class MaxEntriesCase(base_cls):
        max_entries_cap = int(max_entries)

        def _add_to_position(self, price, timestamp, quantity, adx):
            if not self.current_position:
                return
            if not self.position_quantity or self.position_quantity == 0:
                return
            if quantity <= 0:
                return

            pos = self.current_position
            max_position = self.position_quantity * self.max_entries_cap
            add_qty = min(quantity, max_position - pos["quantity"])
            if add_qty <= 0:
                return

            position_value = add_qty * price
            commission = position_value * self.commission
            total_qty = pos["quantity"] + add_qty
            new_avg = (pos["avg_entry"] * pos["quantity"] + price * add_qty) / total_qty

            pos["avg_entry"] = new_avg
            pos["quantity"] = total_qty
            pos["total_commission"] += commission
            self.capital -= commission
            self.entry_count = round(total_qty / self.position_quantity)

    return MaxEntriesCase


def save_plot(equity_map: dict[int, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_mdd = axes

    cmap = plt.get_cmap("viridis")
    entries = metrics_df["max_entries"].astype(int).tolist()
    colors = {e: cmap(i / max(1, len(entries) - 1)) for i, e in enumerate(entries)}

    for e in entries:
        eq = equity_map.get(e)
        if eq is None or eq.empty:
            continue
        ax_eq.plot(eq["timestamp"], eq["equity"], linewidth=1.0, color=colors[e], label=f"max_entries={e}")
    ax_eq.axhline(LEG_CAPITAL, color="#777777", linestyle="--", linewidth=0.9, label="Start 500")
    ax_eq.set_title("29 Study: 08 Long-only Sweep by Max Entry Count")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_cagr.bar(metrics_df["max_entries"], metrics_df["final_equity"], color=[colors[e] for e in entries], alpha=0.8, label="Final Equity")
    ax_cagr.set_ylabel("Final Equity")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(metrics_df["max_entries"], metrics_df["cagr_pct"], color="#d62728", marker="o", linewidth=1.1, label="CAGR %")
    ax_cagr_t.set_ylabel("CAGR %")
    ax_cagr.set_xlabel("Max Entries")
    ax_cagr.set_xticks(entries)

    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_mdd.bar(metrics_df["max_entries"], metrics_df["max_drawdown_pct"], color=[colors[e] for e in entries], alpha=0.8, label="MDD %")
    ax_mdd.set_ylabel("MDD %")
    ax_mdd.grid(True, axis="y", alpha=0.2)
    ax_mdd_t = ax_mdd.twinx()
    ax_mdd_t.plot(metrics_df["max_entries"], metrics_df["calmar_ratio"], color="#1f77b4", marker="o", linewidth=1.1, label="Calmar")
    ax_mdd_t.set_ylabel("Calmar")
    ax_mdd.set_xlabel("Max Entries")
    ax_mdd.set_xticks(entries)

    h1, l1 = ax_mdd.get_legend_handles_labels()
    h2, l2 = ax_mdd_t.get_legend_handles_labels()
    ax_mdd.legend(h1 + h2, l1 + l2, loc="upper left")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    best_cagr = metrics_df.sort_values("cagr_pct", ascending=False).iloc[0]
    best_mdd = metrics_df.sort_values("max_drawdown_pct", ascending=True).iloc[0]
    best_calmar = metrics_df.sort_values("calmar_ratio", ascending=False).iloc[0]
    base5 = metrics_df[metrics_df["max_entries"] == 5]
    base5_row = base5.iloc[0] if not base5.empty else None

    lines: list[str] = []
    lines.append("# 29 Backtest: 08 Long-only Max Entries Sweep")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Base: 08 long-only (hysteresis 0.5%, no-lookahead confirmed 4h touch/trend)")
    lines.append("- Initial capital per run: `500 USDT`")
    lines.append("- Entry scale: `0.50`")
    lines.append(f"- Sweep max entries: `{', '.join(str(x) for x in MAX_ENTRIES_LIST)}`")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Max Entries | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| {int(r['max_entries'])} | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | "
            f"{_fmt(r['cagr_pct'])} | {_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | "
            f"{int(r['trades'])} | {int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} |"
        )
    lines.append("")
    lines.append("## Best Cases")
    lines.append(f"- Best CAGR: `max_entries={int(best_cagr['max_entries'])}` (CAGR `{_fmt(best_cagr['cagr_pct'])}%`).")
    lines.append(f"- Lowest MDD: `max_entries={int(best_mdd['max_entries'])}` (MDD `{_fmt(best_mdd['max_drawdown_pct'])}%`).")
    lines.append(f"- Best Calmar: `max_entries={int(best_calmar['max_entries'])}` (Calmar `{_fmt(best_calmar['calmar_ratio'])}`).")
    if base5_row is not None:
        lines.append("")
        lines.append("## Delta vs max_entries=5")
        lines.append("| Max Entries | Final Equity Delta | CAGR Delta (pp) | MDD Delta (pp) |")
        lines.append("|---:|---:|---:|---:|")
        for _, r in metrics_df.iterrows():
            lines.append(
                f"| {int(r['max_entries'])} | {_fmt(r['final_equity'] - float(base5_row['final_equity']))} | "
                f"{_fmt(r['cagr_pct'] - float(base5_row['cagr_pct']))} | "
                f"{_fmt(r['max_drawdown_pct'] - float(base5_row['max_drawdown_pct']))} |"
            )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics: `{OUT_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    base = load_module("m002_29", BASE_002_PATH)
    helper = load_module("m04_29", BASE_04_PATH)
    m28 = load_module("m28_29", BASE_28_PATH)

    df_1m, df_4h = m28.load_data_no_filter(base)
    df_1m = df_1m[(df_1m.index >= base.BACKTEST_START) & (df_1m.index <= base.BACKTEST_END)].copy()

    base_08_cls = m28.build_08_no_lookahead_class(base, helper)

    rows: list[dict] = []
    equity_map: dict[int, pd.DataFrame] = {}

    for max_entries in MAX_ENTRIES_LIST:
        cls = build_max_entries_class(base_08_cls, max_entries)
        bt = cls(
            symbol=base.SYMBOL,
            initial_capital=LEG_CAPITAL,
            commission=base.COMMISSION,
            entry_scale=ENTRY_SCALE,
        )
        helper.configure_baseline_params(bt)
        bt.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)

        metrics = helper.calculate_metrics(bt, LEG_CAPITAL)
        metrics["max_entries"] = int(max_entries)
        rows.append(metrics)

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            equity_map[int(max_entries)] = eq[["timestamp", "equity"]].copy()
        else:
            equity_map[int(max_entries)] = pd.DataFrame(columns=["timestamp", "equity"])

    metrics_df = pd.DataFrame(rows).sort_values("max_entries").reset_index(drop=True)
    cols = [
        "max_entries",
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
    ]
    metrics_df[cols].to_csv(OUT_CSV, index=False)
    save_plot(equity_map, metrics_df)
    save_report(metrics_df[cols])

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df[cols].to_string(index=False))


if __name__ == "__main__":
    run()
