from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_107_PATH = Path("107_backtest_btcusdt_4h_ema200_counter_gap_study.py")
BASE_109_PATH = Path("109_backtest_btcusdt_minus20_rsi15_case2_longonly_noreentry.py")

OUT_BASE = "110_backtest_btcusdt_gap_rsi15_case2_longonly_threshold_cases"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_selected_curves.csv")
OUT_TRADES_CSV = Path(f"{OUT_BASE}_trades.csv")

THRESHOLD_CASES = [10.0, 12.0, 15.0, 18.0, 20.0]
CURVE_RESAMPLE_RULE = "1h"


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


def compress_curve(curve: pd.DataFrame, rule: str = CURVE_RESAMPLE_RULE) -> pd.DataFrame:
    out = curve.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    out = (
        out.set_index("timestamp")
        .resample(rule)
        .last()
        .dropna(subset=["equity"])
        .reset_index()
    )
    return out


def run_threshold_case(market: pd.DataFrame, threshold_pct: float, m109) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    close = market["close"].to_numpy(dtype=float)
    gap = market["gap_pct"].to_numpy(dtype=float)
    rsi = market["rsi"].to_numpy(dtype=float)
    timestamps = pd.to_datetime(market["timestamp"]).to_numpy()

    capital = float(m109.INITIAL_CAPITAL)
    current_position: dict | None = None
    position_quantity = 0.0
    entry_count = 0
    cooldown_time = int(m109.BASE_COOLDOWN)
    last_order_time = -10**9
    recent_trade_price = 0.0

    variant = f"gap_{str(threshold_pct).replace('.0', '')}"
    curve_rows: list[dict] = []
    trade_rows: list[dict] = []

    signal_mask = (gap <= -float(threshold_pct)) & (rsi <= float(m109.RSI_OVERSOLD))
    signal_bars = int(signal_mask.sum())
    signal_crosses = int((signal_mask & np.r_[False, ~signal_mask[:-1]]).sum())
    tp_exits = 0
    stop_exits = 0
    final_exits = 0

    def update_cooldown() -> None:
        nonlocal cooldown_time
        if current_position is None:
            cooldown_time = int(m109.BASE_COOLDOWN)
        else:
            cooldown_time = int(m109.BASE_COOLDOWN) + max(1, entry_count)

    def mark_equity(price: float) -> float:
        if current_position is None:
            return float(capital)
        return float(capital + (price - float(current_position["avg_entry"])) * float(current_position["quantity"]))

    def close_position(price: float, ts, reason: str, current_time_idx: int) -> None:
        nonlocal capital, current_position, position_quantity, entry_count, recent_trade_price, last_order_time, tp_exits, stop_exits, final_exits
        if current_position is None:
            return
        pos = current_position
        qty = float(pos["quantity"])
        close_commission = qty * price * float(m109.COMMISSION)
        pnl = (price - float(pos["avg_entry"])) * qty - close_commission
        capital += pnl
        trade_rows.append(
            {
                "variant": variant,
                "threshold_pct": float(threshold_pct),
                "entry_time": pd.to_datetime(pos["entry_time"]),
                "exit_time": pd.to_datetime(ts),
                "avg_entry": float(pos["avg_entry"]),
                "exit_price": float(price),
                "quantity": qty,
                "num_entries": int(entry_count),
                "pnl": float(pnl),
                "return_pct": float(pnl / float(m109.INITIAL_CAPITAL) * 100.0),
                "reason": reason,
                "hours_held": float((current_time_idx - int(pos["entry_idx"])) / 60.0),
            }
        )
        if reason == "Take Profit":
            tp_exits += 1
        elif reason == "Stop Loss":
            stop_exits += 1
        elif reason == "Final Close":
            final_exits += 1
        current_position = None
        position_quantity = 0.0
        entry_count = 0
        recent_trade_price = 0.0
        last_order_time = current_time_idx
        update_cooldown()

    def open_position(price: float, ts, current_time_idx: int) -> None:
        nonlocal capital, current_position, position_quantity, entry_count, recent_trade_price, last_order_time
        qty = (capital / price) * float(m109.ENTRY_SCALE)
        if qty <= 0:
            return
        commission = qty * price * float(m109.COMMISSION)
        capital -= commission
        current_position = {
            "avg_entry": float(price),
            "quantity": float(qty),
            "entry_time": pd.to_datetime(ts),
            "entry_idx": int(current_time_idx),
        }
        position_quantity = float(qty)
        entry_count = 1
        recent_trade_price = float(price)
        last_order_time = current_time_idx
        update_cooldown()

    def add_to_position(price: float, current_time_idx: int) -> None:
        nonlocal capital, current_position, entry_count, recent_trade_price
        if current_position is None or position_quantity <= 0:
            return
        max_position = position_quantity * int(m109.MAX_ENTRIES)
        cur_qty = float(current_position["quantity"])
        add_qty = min(position_quantity, max_position - cur_qty)
        if add_qty <= 0:
            return
        commission = add_qty * price * float(m109.COMMISSION)
        total_qty = cur_qty + add_qty
        new_avg = (float(current_position["avg_entry"]) * cur_qty + price * add_qty) / total_qty
        capital -= commission
        current_position["avg_entry"] = float(new_avg)
        current_position["quantity"] = float(total_qty)
        entry_count = max(1, round(total_qty / position_quantity))
        recent_trade_price = float(price)
        update_cooldown()

    for i in range(len(market)):
        ts = pd.Timestamp(timestamps[i])
        price = float(close[i])
        just_exited = False

        if current_position is not None:
            avg_entry = float(current_position["avg_entry"])
            if price <= avg_entry * (1.0 - float(m109.STOP_LOSS_PCT)):
                close_position(price, ts, "Stop Loss", i)
                just_exited = True
            elif price >= avg_entry * (1.0 + float(m109.TAKE_PROFIT_PCT)):
                close_position(price, ts, "Take Profit", i)
                just_exited = True

        time_since_last = i - last_order_time
        if (not just_exited) and signal_mask[i] and time_since_last >= cooldown_time:
            if current_position is None:
                open_position(price, ts, i)
            elif price <= recent_trade_price * float(m109.PRICE_STEP_DCA) and entry_count < int(m109.MAX_ENTRIES):
                add_to_position(price, i)
                last_order_time = i

        curve_rows.append(
            {
                "timestamp": ts,
                "variant": variant,
                "equity": max(mark_equity(price), 0.0),
                "threshold_pct": float(threshold_pct),
            }
        )

    if current_position is not None:
        close_position(float(close[-1]), pd.Timestamp(timestamps[-1]), "Final Close", len(market) - 1)
        curve_rows[-1]["equity"] = float(capital)

    curve = pd.DataFrame(curve_rows)
    trades = pd.DataFrame(trade_rows)
    stats = m109.compute_curve_stats(curve, float(m109.INITIAL_CAPITAL))
    wins = int((trades["pnl"] > 0).sum()) if not trades.empty else 0
    stats.update(
        {
            "variant": variant,
            "threshold_pct": float(threshold_pct),
            "trades": int(len(trades)),
            "win_rate_pct": float(wins / len(trades) * 100.0) if len(trades) else np.nan,
            "avg_trade_return_pct": float(trades["return_pct"].mean()) if len(trades) else np.nan,
            "avg_num_entries": float(trades["num_entries"].mean()) if len(trades) else np.nan,
            "avg_hours_held": float(trades["hours_held"].mean()) if len(trades) else np.nan,
            "signal_bars": int(signal_bars),
            "signal_crosses": int(signal_crosses),
            "tp_exits": int(tp_exits),
            "stop_exits": int(stop_exits),
            "final_exits": int(final_exits),
        }
    )
    return curve, trades, stats


def save_plot(metrics_df: pd.DataFrame, curves_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), gridspec_kw={"height_ratios": [2.0, 1.0, 1.0]})
    ax_eq, ax_final, ax_risk = axes

    cmap = plt.get_cmap("viridis")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i / max(1, len(variants) - 1)) for i, v in enumerate(variants)}

    for variant in variants:
        sub = curves_df[curves_df["variant"] == variant]
        if sub.empty:
            continue
        lw = 1.4 if variant.startswith("gap_") else 1.0
        ax_eq.plot(sub["timestamp"], sub["equity"], linewidth=lw, color=colors[variant], label=variant)
    ax_eq.axhline(1000.0, color="black", linestyle="--", linewidth=0.9)
    ax_eq.set_title("110: Threshold Case Studies (-10% to -20%)")
    ax_eq.set_ylabel("Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=3, fontsize=8)

    live = metrics_df[metrics_df["variant"] != "buy_hold"].sort_values("threshold_pct")
    ax_final.bar(live["threshold_pct"].astype(str), live["final_equity"], color=[colors[v] for v in live["variant"]], alpha=0.9)
    ax_final.axhline(1000.0, color="black", linestyle="--", linewidth=0.9)
    ax_final.set_ylabel("Final Equity")
    ax_final.set_xlabel("Threshold %")
    ax_final.grid(True, axis="y", alpha=0.2)

    ax_risk.bar(live["threshold_pct"].astype(str), live["cagr_pct"], color=[colors[v] for v in live["variant"]], alpha=0.85, label="CAGR %")
    ax_risk_t = ax_risk.twinx()
    ax_risk_t.plot(live["threshold_pct"].astype(str), live["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_risk.set_ylabel("CAGR %")
    ax_risk_t.set_ylabel("MDD %")
    ax_risk.set_xlabel("Threshold %")
    ax_risk.grid(True, axis="y", alpha=0.2)
    h1, l1 = ax_risk.get_legend_handles_labels()
    h2, l2 = ax_risk_t.get_legend_handles_labels()
    ax_risk.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=170)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, trades_df: pd.DataFrame) -> None:
    live = metrics_df[metrics_df["variant"] != "buy_hold"].copy().sort_values("threshold_pct")
    best_final = live.sort_values(["final_equity", "calmar_ratio"], ascending=[False, False]).iloc[0]
    best_calmar = live.sort_values(["calmar_ratio", "final_equity"], ascending=[False, False]).iloc[0]
    buy_hold = metrics_df[metrics_df["variant"] == "buy_hold"].iloc[0]

    reason_df = (
        trades_df[trades_df["variant"] != "buy_hold"]
        .groupby(["variant", "reason"])
        .size()
        .reset_index(name="count")
        .sort_values(["variant", "reason"])
    )

    lines: list[str] = []
    lines.append("# Study 110: Threshold Case Studies")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Reused the 109 structure")
    lines.append("- Long only")
    lines.append("- Entry signal: gap threshold vs confirmed 4h EMA200 plus `RSI6 <= 15`")
    lines.append("- DCA / cooldown / max 2.4 total size follow the same case2-style long-only rule as 109")
    lines.append("- TP = `+1.2%`, SL = `-3.0%`, no re-entry logic")
    lines.append(f"- Threshold cases: `{', '.join(f'-{int(x)}%' for x in THRESHOLD_CASES)}`")
    lines.append("")
    lines.append("## Performance")
    lines.append("| Variant | Threshold % | Final Equity | Total Return % | CAGR % | MDD % | Calmar | Trades | Win Rate % | Avg Entries | Avg Hold h | Signal Crosses |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.sort_values(["variant"]).iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row.get('threshold_pct', np.nan), 1)} | {_fmt(row['final_equity'])} | "
            f"{_fmt(row['total_return_pct'])} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | "
            f"{_fmt(row['calmar_ratio'])} | {int(row['trades'])} | {_fmt(row['win_rate_pct'])} | "
            f"{_fmt(row.get('avg_num_entries', np.nan))} | {_fmt(row.get('avg_hours_held', np.nan))} | "
            f"{_fmt(row.get('signal_crosses', np.nan), 0)} |"
        )
    lines.append("")
    lines.append("## Best Cases")
    lines.append(
        f"- Best final equity: `{best_final['variant']}` (`-{int(best_final['threshold_pct'])}%`) -> "
        f"equity `{_fmt(best_final['final_equity'])}`, CAGR `{_fmt(best_final['cagr_pct'])}%`, "
        f"MDD `{_fmt(best_final['max_drawdown_pct'])}%`"
    )
    lines.append(
        f"- Best Calmar: `{best_calmar['variant']}` (`-{int(best_calmar['threshold_pct'])}%`) -> "
        f"Calmar `{_fmt(best_calmar['calmar_ratio'])}`, equity `{_fmt(best_calmar['final_equity'])}`"
    )
    lines.append(
        f"- Buy-and-hold reference: equity `{_fmt(buy_hold['final_equity'])}`, CAGR `{_fmt(buy_hold['cagr_pct'])}%`, "
        f"MDD `{_fmt(buy_hold['max_drawdown_pct'])}%`"
    )
    lines.append("")
    lines.append("## Exit Breakdown")
    lines.append("| Variant | Reason | Count |")
    lines.append("| --- | --- | ---: |")
    for _, row in reason_df.iterrows():
        lines.append(f"| {row['variant']} | {row['reason']} | {int(row['count'])} |")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    m107 = load_module("study107_gap", BASE_107_PATH)
    m109 = load_module("study109_case", BASE_109_PATH)
    df_1m, df_4h, _ = m107.load_market_data()
    market = m109.build_market_1m(df_1m, df_4h)

    metrics_rows: list[dict] = []
    trade_frames: list[pd.DataFrame] = []
    compressed_curves: list[pd.DataFrame] = []

    buy_curve, buy_trades, buy_stats = m109.run_buy_hold(market)
    metrics_rows.append(buy_stats)
    trade_frames.append(buy_trades)
    compressed_curves.append(compress_curve(buy_curve))

    for threshold_pct in THRESHOLD_CASES:
        curve, trades, stats = run_threshold_case(market, threshold_pct, m109)
        metrics_rows.append(stats)
        trade_frames.append(trades)
        compressed_curves.append(compress_curve(curve))

    metrics_df = pd.DataFrame(metrics_rows).sort_values(["variant"]).reset_index(drop=True)
    trades_df = pd.concat(trade_frames, ignore_index=True)
    curves_df = pd.concat(compressed_curves, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    trades_df.to_csv(OUT_TRADES_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)

    save_plot(metrics_df, curves_df)
    save_report(metrics_df, trades_df)

    best = metrics_df[metrics_df["variant"] != "buy_hold"].sort_values(["final_equity", "calmar_ratio"], ascending=[False, False]).iloc[0]
    print(
        "study=110, "
        f"best_variant={best['variant']}, "
        f"best_threshold=-{best['threshold_pct']:.0f}%, "
        f"best_final={best['final_equity']:.2f}, "
        f"best_cagr={best['cagr_pct']:.2f}"
    )


if __name__ == "__main__":
    main()
