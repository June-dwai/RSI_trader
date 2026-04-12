from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_107_PATH = Path("107_backtest_btcusdt_4h_ema200_counter_gap_study.py")

OUT_BASE = "109_backtest_btcusdt_minus20_rsi15_case2_longonly_noreentry"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_TRADES_CSV = Path(f"{OUT_BASE}_trades.csv")

INITIAL_CAPITAL = 1000.0
COMMISSION = 0.0004
ENTRY_SCALE = 0.60
MAX_ENTRIES = 4
TAKE_PROFIT_PCT = 0.012
STOP_LOSS_PCT = 0.03
RSI_PERIOD = 6
RSI_OVERSOLD = 15.0
GAP_THRESHOLD_PCT = -20.0
BASE_COOLDOWN = 5
PRICE_STEP_DCA = 0.995


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


def calculate_rsi(closes: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = closes.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi[(avg_loss == 0) & (avg_gain > 0)] = 100.0
    rsi[(avg_gain == 0) & (avg_loss > 0)] = 0.0
    rsi[(avg_gain == 0) & (avg_loss == 0)] = 50.0
    return rsi.fillna(50.0)


def build_market_1m(df_1m: pd.DataFrame, df_4h: pd.DataFrame) -> pd.DataFrame:
    out_1m = df_1m.copy().sort_index()
    out_4h = df_4h.copy().sort_index()

    out_1m["rsi"] = calculate_rsi(out_1m["close"], RSI_PERIOD)
    out_1m["bucket_4h"] = out_1m.index.floor("4h")

    out_4h["ema200"] = out_4h["close"].ewm(span=200, adjust=False).mean().shift(1)
    out_1m = out_1m.merge(out_4h[["ema200"]], left_on="bucket_4h", right_index=True, how="left")
    out_1m["ema200"] = out_1m["ema200"].ffill()
    out_1m["gap_pct"] = ((out_1m["close"] - out_1m["ema200"]) / out_1m["ema200"] * 100.0).replace([np.inf, -np.inf], np.nan)
    out_1m = out_1m.dropna(subset=["ema200", "gap_pct"]).copy()
    out_1m["timestamp"] = out_1m.index
    return out_1m.reset_index(drop=True)


def compute_curve_stats(curve: pd.DataFrame, initial_capital: float) -> dict:
    series = curve["equity"].astype(float)
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


def run_buy_hold(market: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    first_price = float(market["close"].iloc[0])
    entry_fee = INITIAL_CAPITAL * COMMISSION
    qty = (INITIAL_CAPITAL - entry_fee) / first_price if first_price > 0 else 0.0

    curve = market[["timestamp"]].copy()
    curve["variant"] = "buy_hold"
    curve["equity"] = qty * market["close"].astype(float)
    curve.loc[curve.index[0], "equity"] = INITIAL_CAPITAL - entry_fee
    final_capital = qty * float(market["close"].iloc[-1]) * (1.0 - COMMISSION)
    curve.loc[curve.index[-1], "equity"] = final_capital

    trades = pd.DataFrame(
        [
            {
                "variant": "buy_hold",
                "entry_time": pd.to_datetime(market["timestamp"].iloc[0]),
                "exit_time": pd.to_datetime(market["timestamp"].iloc[-1]),
                "avg_entry": first_price,
                "exit_price": float(market["close"].iloc[-1]),
                "quantity": float(qty),
                "num_entries": 1,
                "pnl": float(final_capital - INITIAL_CAPITAL),
                "return_pct": float((final_capital / INITIAL_CAPITAL - 1.0) * 100.0),
                "reason": "Final Close",
                "hours_held": float((len(market) - 1) / 60.0),
            }
        ]
    )

    stats = compute_curve_stats(curve, INITIAL_CAPITAL)
    stats.update(
        {
            "variant": "buy_hold",
            "trades": 1,
            "win_rate_pct": 100.0 if final_capital > INITIAL_CAPITAL else 0.0,
            "avg_trade_return_pct": float(trades["return_pct"].mean()),
            "avg_num_entries": 1.0,
            "avg_hours_held": float(trades["hours_held"].mean()),
            "signal_bars": np.nan,
            "signal_crosses": np.nan,
            "tp_exits": 0,
            "stop_exits": 0,
            "final_exits": 1,
        }
    )
    return curve, trades, stats


def run_strategy(market: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    close = market["close"].to_numpy(dtype=float)
    gap = market["gap_pct"].to_numpy(dtype=float)
    rsi = market["rsi"].to_numpy(dtype=float)
    timestamps = pd.to_datetime(market["timestamp"]).to_numpy()

    capital = float(INITIAL_CAPITAL)
    current_position: dict | None = None
    position_quantity = 0.0
    entry_count = 0
    cooldown_time = BASE_COOLDOWN
    last_order_time = -10**9
    recent_trade_price = 0.0

    curve_rows: list[dict] = []
    trade_rows: list[dict] = []

    signal_mask = (gap <= GAP_THRESHOLD_PCT) & (rsi <= RSI_OVERSOLD)
    signal_bars = int(signal_mask.sum())
    signal_crosses = int((signal_mask & np.r_[False, ~signal_mask[:-1]]).sum())
    tp_exits = 0
    stop_exits = 0
    final_exits = 0

    def update_cooldown() -> None:
        nonlocal cooldown_time
        if current_position is None:
            cooldown_time = BASE_COOLDOWN
        else:
            cooldown_time = BASE_COOLDOWN + max(1, entry_count)

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
        close_commission = qty * price * COMMISSION
        pnl = (price - float(pos["avg_entry"])) * qty - close_commission
        capital += pnl
        trade_rows.append(
            {
                "variant": "minus20_rsi15_case2_longonly_noreentry",
                "entry_time": pd.to_datetime(pos["entry_time"]),
                "exit_time": pd.to_datetime(ts),
                "avg_entry": float(pos["avg_entry"]),
                "exit_price": float(price),
                "quantity": qty,
                "num_entries": int(entry_count),
                "pnl": float(pnl),
                "return_pct": float(pnl / INITIAL_CAPITAL * 100.0),
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
        qty = (capital / price) * ENTRY_SCALE
        if qty <= 0:
            return
        commission = qty * price * COMMISSION
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
        max_position = position_quantity * MAX_ENTRIES
        cur_qty = float(current_position["quantity"])
        add_qty = min(position_quantity, max_position - cur_qty)
        if add_qty <= 0:
            return
        commission = add_qty * price * COMMISSION
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
            if price <= avg_entry * (1.0 - STOP_LOSS_PCT):
                close_position(price, ts, "Stop Loss", i)
                just_exited = True
            elif price >= avg_entry * (1.0 + TAKE_PROFIT_PCT):
                close_position(price, ts, "Take Profit", i)
                just_exited = True

        time_since_last = i - last_order_time
        if (not just_exited) and signal_mask[i] and time_since_last >= cooldown_time:
            if current_position is None:
                open_position(price, ts, i)
            elif price <= recent_trade_price * PRICE_STEP_DCA and entry_count < MAX_ENTRIES:
                add_to_position(price, i)
                last_order_time = i

        curve_rows.append(
            {
                "timestamp": ts,
                "variant": "minus20_rsi15_case2_longonly_noreentry",
                "equity": max(mark_equity(price), 0.0),
                "gap_pct": float(gap[i]),
                "rsi": float(rsi[i]),
                "position_state": "long" if current_position is not None else "flat",
            }
        )

    if current_position is not None:
        close_position(float(close[-1]), pd.Timestamp(timestamps[-1]), "Final Close", len(market) - 1)
        curve_rows[-1]["equity"] = float(capital)
        curve_rows[-1]["position_state"] = "flat"

    curve = pd.DataFrame(curve_rows)
    trades = pd.DataFrame(trade_rows)

    stats = compute_curve_stats(curve, INITIAL_CAPITAL)
    wins = int((trades["pnl"] > 0).sum()) if not trades.empty else 0
    stats.update(
        {
            "variant": "minus20_rsi15_case2_longonly_noreentry",
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


def save_plot(curves_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True, gridspec_kw={"height_ratios": [2.0, 1.0]})
    ax_eq, ax_dd = axes

    colors = {
        "minus20_rsi15_case2_longonly_noreentry": "#1f77b4",
        "buy_hold": "#7f7f7f",
    }
    labels = {
        "minus20_rsi15_case2_longonly_noreentry": "Strategy",
        "buy_hold": "Buy & Hold",
    }

    for variant in ["minus20_rsi15_case2_longonly_noreentry", "buy_hold"]:
        sub = curves_df[curves_df["variant"] == variant].copy()
        ax_eq.plot(sub["timestamp"], sub["equity"], linewidth=1.2, color=colors[variant], label=labels[variant])
        dd = sub["equity"].astype(float) / sub["equity"].astype(float).cummax() - 1.0
        ax_dd.plot(sub["timestamp"], -dd * 100.0, linewidth=1.0, color=colors[variant], label=labels[variant])

    ax_eq.axhline(INITIAL_CAPITAL, color="black", linestyle="--", linewidth=0.9)
    ax_eq.set_title("109: -20% Gap + RSI<=15 Case2-Style Long Only")
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
    strategy = metrics_df[metrics_df["variant"] == "minus20_rsi15_case2_longonly_noreentry"].iloc[0]
    buy_hold = metrics_df[metrics_df["variant"] == "buy_hold"].iloc[0]

    reason_table = (
        trades_df.groupby(["variant", "reason"])
        .size()
        .reset_index(name="count")
        .sort_values(["variant", "reason"])
    )

    lines: list[str] = []
    lines.append("# Study 109: -20% Gap + RSI15 Case2-Style Long Only")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Long only")
    lines.append("- Entry signal: confirmed 4h EMA200 gap `<= -20%` and `RSI6 <= 15` on the 1m close")
    lines.append("- DCA timing: same case2 rhythm using cooldown and `recent_trade * 0.995` trigger")
    lines.append(f"- Entry sizing: `{ENTRY_SCALE:.1f}` each, max `{ENTRY_SCALE * MAX_ENTRIES:.1f}` total (`{MAX_ENTRIES}` entries)")
    lines.append("- Take profit: case2 default `+1.2%` from average entry")
    lines.append("- Stop loss: `-3.0%` from average entry, full close, no re-entry logic")
    lines.append("")
    lines.append("## Performance")
    lines.append("| Variant | Final Equity | Total Return % | CAGR % | MDD % | Calmar | Trades | Win Rate % | Avg Trade % | Avg Entries | Avg Hold h |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['total_return_pct'])} | "
            f"{_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{int(row['trades'])} | {_fmt(row['win_rate_pct'])} | {_fmt(row['avg_trade_return_pct'])} | "
            f"{_fmt(row['avg_num_entries'])} | {_fmt(row['avg_hours_held'])} |"
        )
    lines.append("")
    lines.append("## Readout")
    lines.append(
        f"- Strategy signals: `{int(strategy['signal_crosses'])}` crosses, `{int(strategy['signal_bars'])}` total signal bars."
    )
    lines.append(
        f"- Strategy exits: TP `{int(strategy['tp_exits'])}`, Stop `{int(strategy['stop_exits'])}`, Final `{int(strategy['final_exits'])}`."
    )
    lines.append(
        f"- Strategy final equity `{_fmt(strategy['final_equity'])}` vs buy-and-hold `{_fmt(buy_hold['final_equity'])}`."
    )
    lines.append("")
    lines.append("## Exit Breakdown")
    lines.append("| Variant | Reason | Count |")
    lines.append("| --- | --- | ---: |")
    for _, row in reason_table.iterrows():
        lines.append(f"| {row['variant']} | {row['reason']} | {int(row['count'])} |")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    m107 = load_module("study107_gap", BASE_107_PATH)
    df_1m, df_4h, _ = m107.load_market_data()
    market = build_market_1m(df_1m, df_4h)

    strategy_curve, strategy_trades, strategy_stats = run_strategy(market)
    buy_curve, buy_trades, buy_stats = run_buy_hold(market)

    curves_df = pd.concat([strategy_curve, buy_curve], ignore_index=True)
    trades_df = pd.concat([strategy_trades, buy_trades], ignore_index=True)
    metrics_df = pd.DataFrame([strategy_stats, buy_stats]).sort_values("variant").reset_index(drop=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    trades_df.to_csv(OUT_TRADES_CSV, index=False)

    save_plot(curves_df)
    save_report(metrics_df, trades_df)

    print(
        "study=109, "
        f"strategy_final={strategy_stats['final_equity']:.2f}, "
        f"strategy_cagr={strategy_stats['cagr_pct']:.2f}, "
        f"strategy_mdd={strategy_stats['max_drawdown_pct']:.2f}, "
        f"strategy_trades={strategy_stats['trades']}"
    )


if __name__ == "__main__":
    main()
