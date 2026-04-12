from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_107_PATH = Path("107_backtest_btcusdt_4h_ema200_counter_gap_study.py")

OUT_BASE = "107_backtest_btcusdt_4h_ema200_counter_gap_equity"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_TRADES_CSV = Path(f"{OUT_BASE}_trades.csv")

INITIAL_CAPITAL = 1000.0
FEE_RATE = 0.0004

VARIANTS = [
    {
        "variant": "dual_best",
        "mode": "rules",
        "allow_long": True,
        "allow_short": True,
        "long_threshold_pct": 8.0,
        "long_tp_pct": 2.0,
        "long_sl_pct": 6.0,
        "short_threshold_pct": 10.0,
        "short_tp_pct": 2.0,
        "short_sl_pct": 1.5,
        "max_hold_hours": 48,
    },
    {
        "variant": "long_only_best",
        "mode": "rules",
        "allow_long": True,
        "allow_short": False,
        "long_threshold_pct": 8.0,
        "long_tp_pct": 2.0,
        "long_sl_pct": 6.0,
        "short_threshold_pct": 10.0,
        "short_tp_pct": 2.0,
        "short_sl_pct": 1.5,
        "max_hold_hours": 48,
    },
    {
        "variant": "short_only_best",
        "mode": "rules",
        "allow_long": False,
        "allow_short": True,
        "long_threshold_pct": 8.0,
        "long_tp_pct": 2.0,
        "long_sl_pct": 6.0,
        "short_threshold_pct": 10.0,
        "short_tp_pct": 2.0,
        "short_sl_pct": 1.5,
        "max_hold_hours": 48,
    },
    {
        "variant": "buy_hold",
        "mode": "buy_hold",
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


def compute_curve_stats(curve: pd.DataFrame, initial_capital: float) -> dict:
    series = curve["equity"].astype(float)
    final_equity = float(series.iloc[-1])
    total_return_pct = (final_equity / float(initial_capital) - 1.0) * 100.0
    elapsed_days = (curve["timestamp"].iloc[-1] - curve["timestamp"].iloc[0]).total_seconds() / 86400.0
    years = max(elapsed_days / 365.25, 1e-9)
    cagr_pct = ((final_equity / float(initial_capital)) ** (1.0 / years) - 1.0) * 100.0
    dd = series / series.cummax() - 1.0
    max_drawdown_pct = float(-dd.min() * 100.0)
    calmar = float(cagr_pct / max_drawdown_pct) if max_drawdown_pct > 0 else np.nan
    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "calmar_ratio": calmar,
    }


def _open_position(capital: float, price: float) -> tuple[float, float]:
    entry_fee = capital * FEE_RATE
    equity_after_fee = capital - entry_fee
    qty = equity_after_fee / price if price > 0 else 0.0
    return equity_after_fee, qty


def _close_long(qty: float, price: float) -> float:
    return qty * price * (1.0 - FEE_RATE)


def _close_short(entry_equity_after_fee: float, entry_price: float, qty: float, price: float) -> float:
    pnl = (entry_price - price) * qty
    exit_fee = qty * price * FEE_RATE
    return entry_equity_after_fee + pnl - exit_fee


def _mark_long(qty: float, price: float) -> float:
    return qty * price


def _mark_short(entry_equity_after_fee: float, entry_price: float, qty: float, price: float) -> float:
    return entry_equity_after_fee + (entry_price - price) * qty


def run_buy_hold(market: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    work = market.copy()
    first_price = float(work["close"].iloc[0])
    entry_equity_after_fee, qty = _open_position(INITIAL_CAPITAL, first_price)

    curve = work[["timestamp"]].copy()
    curve["variant"] = "buy_hold"
    curve["equity"] = qty * work["close"].astype(float)
    curve.loc[curve.index[0], "equity"] = entry_equity_after_fee

    final_capital = _close_long(qty, float(work["close"].iloc[-1]))
    curve.loc[curve.index[-1], "equity"] = final_capital

    trades = pd.DataFrame(
        [
            {
                "variant": "buy_hold",
                "side": "LONG",
                "entry_time": pd.to_datetime(work["timestamp"].iloc[0]),
                "exit_time": pd.to_datetime(work["timestamp"].iloc[-1]),
                "entry_price": first_price,
                "exit_price": float(work["close"].iloc[-1]),
                "exit_reason": "final",
                "bars_held": int(len(work) - 1),
                "hours_held": float((len(work) - 1) * 0.25),
                "entry_capital": INITIAL_CAPITAL,
                "exit_capital": final_capital,
                "return_pct": (final_capital / INITIAL_CAPITAL - 1.0) * 100.0,
            }
        ]
    )

    stats = compute_curve_stats(curve, INITIAL_CAPITAL)
    stats.update(
        {
            "variant": "buy_hold",
            "mode": "buy_hold",
            "trades": 1,
            "win_rate_pct": 100.0 if final_capital > INITIAL_CAPITAL else 0.0,
            "avg_trade_return_pct": float(trades["return_pct"].mean()),
            "avg_hours_held": float(trades["hours_held"].mean()),
            "long_trades": 1,
            "short_trades": 0,
        }
    )
    return curve, trades, stats


def run_rule_variant(market: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    work = market.copy().reset_index(drop=True)
    close = work["close"].to_numpy(dtype=float)
    high = work["high"].to_numpy(dtype=float)
    low = work["low"].to_numpy(dtype=float)
    gap = work["gap_pct"].to_numpy(dtype=float)
    timestamps = pd.to_datetime(work["timestamp"]).to_numpy()

    capital = float(INITIAL_CAPITAL)
    side = 0
    qty = 0.0
    entry_price = 0.0
    entry_equity_after_fee = 0.0
    entry_capital = 0.0
    entry_idx = -1
    bars_in_trade = 0

    curve_rows = [
        {
            "timestamp": pd.Timestamp(timestamps[0]),
            "variant": cfg["variant"],
            "equity": capital,
            "position": "flat",
        }
    ]
    trade_rows: list[dict] = []

    max_hold_bars = int(cfg["max_hold_hours"] * 4)

    for i in range(1, len(work)):
        just_exited = False

        if side != 0:
            bars_in_trade += 1
            exit_reason = None
            exit_price = None

            if side > 0:
                tp_price = entry_price * (1.0 + float(cfg["long_tp_pct"]) / 100.0)
                sl_price = entry_price * (1.0 - float(cfg["long_sl_pct"]) / 100.0)
                hit_sl = low[i] <= sl_price
                hit_tp = high[i] >= tp_price
                if hit_sl and hit_tp:
                    exit_reason = "stop"
                    exit_price = sl_price
                elif hit_sl:
                    exit_reason = "stop"
                    exit_price = sl_price
                elif hit_tp:
                    exit_reason = "tp"
                    exit_price = tp_price
                elif bars_in_trade >= max_hold_bars:
                    exit_reason = "time"
                    exit_price = close[i]
            else:
                tp_price = entry_price * (1.0 - float(cfg["short_tp_pct"]) / 100.0)
                sl_price = entry_price * (1.0 + float(cfg["short_sl_pct"]) / 100.0)
                hit_sl = high[i] >= sl_price
                hit_tp = low[i] <= tp_price
                if hit_sl and hit_tp:
                    exit_reason = "stop"
                    exit_price = sl_price
                elif hit_sl:
                    exit_reason = "stop"
                    exit_price = sl_price
                elif hit_tp:
                    exit_reason = "tp"
                    exit_price = tp_price
                elif bars_in_trade >= max_hold_bars:
                    exit_reason = "time"
                    exit_price = close[i]

            if exit_reason is not None and exit_price is not None:
                if side > 0:
                    capital = _close_long(qty, float(exit_price))
                    mark_side = "LONG"
                else:
                    capital = _close_short(entry_equity_after_fee, entry_price, qty, float(exit_price))
                    mark_side = "SHORT"
                capital = max(capital, 0.0)
                trade_rows.append(
                    {
                        "variant": cfg["variant"],
                        "side": mark_side,
                        "entry_time": pd.Timestamp(timestamps[entry_idx]),
                        "exit_time": pd.Timestamp(timestamps[i]),
                        "entry_price": float(entry_price),
                        "exit_price": float(exit_price),
                        "exit_reason": exit_reason,
                        "bars_held": int(bars_in_trade),
                        "hours_held": float(bars_in_trade * 0.25),
                        "entry_capital": float(entry_capital),
                        "exit_capital": float(capital),
                        "return_pct": (capital / entry_capital - 1.0) * 100.0 if entry_capital > 0 else np.nan,
                    }
                )
                side = 0
                qty = 0.0
                entry_price = 0.0
                entry_equity_after_fee = 0.0
                entry_capital = 0.0
                entry_idx = -1
                bars_in_trade = 0
                just_exited = True

        if capital > 0 and side == 0 and not just_exited:
            long_signal = bool(cfg["allow_long"]) and gap[i] <= -float(cfg["long_threshold_pct"]) and gap[i - 1] > -float(cfg["long_threshold_pct"])
            short_signal = bool(cfg["allow_short"]) and gap[i] >= float(cfg["short_threshold_pct"]) and gap[i - 1] < float(cfg["short_threshold_pct"])

            if long_signal:
                entry_capital = capital
                entry_equity_after_fee, qty = _open_position(capital, close[i])
                side = 1
                entry_price = float(close[i])
                entry_idx = i
                bars_in_trade = 0
            elif short_signal:
                entry_capital = capital
                entry_equity_after_fee, qty = _open_position(capital, close[i])
                side = -1
                entry_price = float(close[i])
                entry_idx = i
                bars_in_trade = 0

        if side > 0:
            equity = _mark_long(qty, close[i])
            pos_label = "long"
        elif side < 0:
            equity = _mark_short(entry_equity_after_fee, entry_price, qty, close[i])
            pos_label = "short"
        else:
            equity = capital
            pos_label = "flat"

        curve_rows.append(
            {
                "timestamp": pd.Timestamp(timestamps[i]),
                "variant": cfg["variant"],
                "equity": max(float(equity), 0.0),
                "position": pos_label,
            }
        )

    if side != 0:
        final_price = float(close[-1])
        final_time = pd.Timestamp(timestamps[-1])
        if side > 0:
            capital = _close_long(qty, final_price)
            mark_side = "LONG"
        else:
            capital = _close_short(entry_equity_after_fee, entry_price, qty, final_price)
            mark_side = "SHORT"
        trade_rows.append(
            {
                "variant": cfg["variant"],
                "side": mark_side,
                "entry_time": pd.Timestamp(timestamps[entry_idx]),
                "exit_time": final_time,
                "entry_price": float(entry_price),
                "exit_price": final_price,
                "exit_reason": "final",
                "bars_held": int(max(0, len(work) - 1 - entry_idx)),
                "hours_held": float(max(0, len(work) - 1 - entry_idx) * 0.25),
                "entry_capital": float(entry_capital),
                "exit_capital": float(capital),
                "return_pct": (capital / entry_capital - 1.0) * 100.0 if entry_capital > 0 else np.nan,
            }
        )
        curve_rows[-1]["equity"] = float(capital)
        curve_rows[-1]["position"] = "flat"

    curve = pd.DataFrame(curve_rows)
    trades = pd.DataFrame(trade_rows)

    stats = compute_curve_stats(curve, INITIAL_CAPITAL)
    wins = int((trades["return_pct"] > 0).sum()) if not trades.empty else 0
    stats.update(
        {
            "variant": cfg["variant"],
            "mode": "rules",
            "trades": int(len(trades)),
            "win_rate_pct": float(wins / len(trades) * 100.0) if len(trades) else np.nan,
            "avg_trade_return_pct": float(trades["return_pct"].mean()) if len(trades) else np.nan,
            "avg_hours_held": float(trades["hours_held"].mean()) if len(trades) else np.nan,
            "long_trades": int((trades["side"] == "LONG").sum()) if len(trades) else 0,
            "short_trades": int((trades["side"] == "SHORT").sum()) if len(trades) else 0,
        }
    )
    return curve, trades, stats


def save_plot(curves_df: pd.DataFrame, metrics_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True, gridspec_kw={"height_ratios": [2.2, 1.0]})
    ax_eq, ax_dd = axes

    colors = {
        "dual_best": "#1f77b4",
        "long_only_best": "#2ca02c",
        "short_only_best": "#d62728",
        "buy_hold": "#7f7f7f",
    }

    for variant in metrics_df["variant"]:
        sub = curves_df[curves_df["variant"] == variant].copy()
        if sub.empty:
            continue
        ax_eq.plot(sub["timestamp"], sub["equity"], linewidth=1.2, color=colors.get(variant), label=variant)
        dd = sub["equity"].astype(float) / sub["equity"].astype(float).cummax() - 1.0
        ax_dd.plot(sub["timestamp"], -dd * 100.0, linewidth=1.0, color=colors.get(variant), label=variant)

    ax_eq.axhline(INITIAL_CAPITAL, color="black", linestyle="--", linewidth=0.9)
    ax_eq.set_title("107 Counter-EMA Sequential Equity Curves")
    ax_eq.set_ylabel("Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_dd.set_title("Drawdown")
    ax_dd.set_ylabel("Drawdown %")
    ax_dd.set_xlabel("Time")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=170)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, trades_df: pd.DataFrame) -> None:
    dual = metrics_df[metrics_df["variant"] == "dual_best"].iloc[0]
    long_only = metrics_df[metrics_df["variant"] == "long_only_best"].iloc[0]
    short_only = metrics_df[metrics_df["variant"] == "short_only_best"].iloc[0]
    buy_hold = metrics_df[metrics_df["variant"] == "buy_hold"].iloc[0]

    trade_summary = (
        trades_df.groupby(["variant", "exit_reason"])
        .size()
        .reset_index(name="count")
        .sort_values(["variant", "exit_reason"])
    )

    lines: list[str] = []
    lines.append("# Study 107 Equity Check")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Sequential, flat-only backtest on 15m bars")
    lines.append("- Uses the recommended 107 study thresholds directly")
    lines.append("- Entry only on threshold cross bar close")
    lines.append("- Exit via TP / SL / 48h timeout with conservative stop-first handling inside the bar")
    lines.append("- No same-bar re-entry after an exit")
    lines.append("")
    lines.append("## Performance")
    lines.append("| Variant | Final Equity | Total Return % | CAGR % | MDD % | Calmar | Trades | Win Rate % | Avg Trade % | Avg Hold h |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['total_return_pct'])} | "
            f"{_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{int(row['trades'])} | {_fmt(row['win_rate_pct'])} | {_fmt(row['avg_trade_return_pct'])} | {_fmt(row['avg_hours_held'])} |"
        )
    lines.append("")
    lines.append("## Readout")
    lines.append(
        f"- Dual curve: final equity `{_fmt(dual['final_equity'])}`, CAGR `{_fmt(dual['cagr_pct'])}%`, "
        f"MDD `{_fmt(dual['max_drawdown_pct'])}%`, win rate `{_fmt(dual['win_rate_pct'])}%`."
    )
    lines.append(
        f"- Long-only drives most of the edge: final equity `{_fmt(long_only['final_equity'])}`, "
        f"vs short-only `{_fmt(short_only['final_equity'])}`."
    )
    lines.append(
        f"- Buy-and-hold benchmark over the same sample finishes at `{_fmt(buy_hold['final_equity'])}`."
    )
    lines.append("")
    lines.append("## Exit Breakdown")
    lines.append("| Variant | Exit Reason | Count |")
    lines.append("| --- | --- | ---: |")
    for _, row in trade_summary.iterrows():
        lines.append(f"| {row['variant']} | {row['exit_reason']} | {int(row['count'])} |")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    m107 = load_module("study107_gap", BASE_107_PATH)
    df_1m, df_4h, _ = m107.load_market_data()
    market = m107.build_market_frame(df_1m, df_4h)

    curve_frames: list[pd.DataFrame] = []
    trade_frames: list[pd.DataFrame] = []
    metric_rows: list[dict] = []

    for cfg in VARIANTS:
        if cfg["mode"] == "buy_hold":
            curve, trades, stats = run_buy_hold(market)
        else:
            curve, trades, stats = run_rule_variant(market, cfg)
        curve_frames.append(curve)
        trade_frames.append(trades)
        metric_rows.append(stats)

    curves_df = pd.concat(curve_frames, ignore_index=True)
    trades_df = pd.concat(trade_frames, ignore_index=True)
    metrics_df = pd.DataFrame(metric_rows).sort_values("variant").reset_index(drop=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    trades_df.to_csv(OUT_TRADES_CSV, index=False)

    save_plot(curves_df, metrics_df)
    save_report(metrics_df, trades_df)

    dual = metrics_df[metrics_df["variant"] == "dual_best"].iloc[0]
    print(
        "study=107_equity, "
        f"dual_final={dual['final_equity']:.2f}, "
        f"dual_cagr={dual['cagr_pct']:.2f}, "
        f"dual_mdd={dual['max_drawdown_pct']:.2f}, "
        f"dual_trades={int(dual['trades'])}"
    )


if __name__ == "__main__":
    main()
