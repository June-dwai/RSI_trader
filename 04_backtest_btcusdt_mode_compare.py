from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_SCRIPT_PATH = Path("002_backtest_btcusdt.py")
PLOT_FILE = Path("04_backtest_btcusdt_modes.png")
CSV_FILE = Path("04_backtest_btcusdt_modes_metrics.csv")
MD_FILE = Path("04_backtest_btcusdt_modes_comparison.md")

MODE_BASELINE = "baseline_02"
MODE_LONG_ONLY = "long_only_no_short"
MODE_SHORT_HEDGE_5X = "long_only_with_trend_short_hedge_5x"
MODES = [MODE_BASELINE, MODE_LONG_ONLY, MODE_SHORT_HEDGE_5X]


def load_base_module(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing base script: {path}")

    spec = importlib.util.spec_from_file_location("bt002", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_mode_classes(base_module):
    class LongOnlyBacktest(base_module.FloorScaledRSIAveragingBacktest):
        """Disable all strategy short entries."""

        def _process_short_entry(self, price, timestamp, adx, current_time):
            return

    class LongOnlyWithTrendShortHedge5xBacktest(LongOnlyBacktest):
        """
        Long-only strategy + trend hedge short.

        Hedge rules:
        - Use only confirmed 4h trend (no 1m flip-flop).
        - Confirmed trend for current 4h bucket is previous closed 4h candle trend.
        - Open hedge short when confirmed 4h trend is bearish.
        - Close hedge short when confirmed 4h trend is bullish.
        - Hedge size = 5 * base_qty, where base_qty = initial long unit qty.
        """

        hedge_short_multiplier = 5.0

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.hedge_position = None
            self.hedge_base_qty = 0.0

        def _reset_hedge(self):
            self.hedge_position = None

        def _open_position(self, side, price, timestamp, quantity):
            super()._open_position(side, price, timestamp, quantity)
            if side == "LONG" and self.position_quantity:
                self.hedge_base_qty = float(self.position_quantity)

        def _open_hedge_short(self, price, timestamp):
            if self.hedge_position is not None:
                return
            if self.position_quantity:
                self.hedge_base_qty = float(self.position_quantity)
            base_qty = float(self.hedge_base_qty)
            if base_qty <= 0:
                return

            hedge_qty = base_qty * self.hedge_short_multiplier
            if hedge_qty <= 0:
                return

            open_commission = hedge_qty * price * self.commission
            self.capital -= open_commission
            self.hedge_position = {
                "side": "SHORT",
                "avg_entry": price,
                "quantity": hedge_qty,
                "entry_time": timestamp,
                "total_commission": open_commission,
            }

        def _close_hedge_short(self, price, timestamp, reason):
            if self.hedge_position is None:
                return

            pos = self.hedge_position
            close_commission = pos["quantity"] * price * self.commission
            pnl = (pos["avg_entry"] - price) * pos["quantity"]
            pnl -= (pos["total_commission"] + close_commission)
            self.capital += pnl

            self.trades.append(
                {
                    "entry_time": pos["entry_time"],
                    "exit_time": timestamp,
                    "side": "SHORT",
                    "avg_entry": pos["avg_entry"],
                    "exit_price": price,
                    "quantity": pos["quantity"],
                    "num_entries": 1,
                    "pnl": pnl,
                    "return_pct": (pnl / self.initial_capital) * 100,
                    "reason": reason,
                }
            )
            self.hedge_position = None

        def _manage_trend_hedge(self, confirmed_trend_4h, price, timestamp, is_new_4h_bucket):
            if not is_new_4h_bucket:
                return
            if confirmed_trend_4h not in ("bullish", "bearish"):
                return

            if confirmed_trend_4h == "bearish" and self.hedge_position is None:
                self._open_hedge_short(price, timestamp)

            if confirmed_trend_4h == "bullish" and self.hedge_position is not None:
                self._close_hedge_short(price, timestamp, "Hedge Close Trend Up")

        def _record_equity(self, price, timestamp, ema=0):
            if self.bankrupt:
                self.equity_curve.append({"timestamp": timestamp, "equity": 0.0, "price": price, "ema200": ema})
                return

            equity = self.capital
            if self.current_position:
                pos = self.current_position
                if pos["side"] == "LONG":
                    equity += (price - pos["avg_entry"]) * pos["quantity"]
                else:
                    equity += (pos["avg_entry"] - price) * pos["quantity"]

            if self.hedge_position:
                hedge = self.hedge_position
                equity += (hedge["avg_entry"] - price) * hedge["quantity"]

            if equity <= 0:
                self.equity_curve.append({"timestamp": timestamp, "equity": 0.0, "price": price, "ema200": ema})
                self.capital = 0.0
                self.current_position = None
                self.position_quantity = None
                self.entry_count = 0
                self.skip_count = 0
                self.stop_loss = [0, 0]
                self.hedge_position = None
                self.bankrupt = True
                return

            self.equity_curve.append(
                {
                    "timestamp": timestamp,
                    "equity": equity,
                    "price": price,
                    "ema200": ema,
                }
            )

        def run(self, df_1m: pd.DataFrame, df_4h: pd.DataFrame, backtest_start_date=None):
            self.capital = self.initial_capital
            self.current_position = None
            self.position_quantity = 0.0
            self.entry_count = 0
            self.skip_count = 0
            self.stop_loss = [0, 0]
            self.last_order_time = -10**9
            self.recent_trade = [0.0, None]
            self.cooldown_time = self.base_cooldown
            self.trades = []
            self.equity_curve = []
            self.current_trend = None
            self.bankrupt = False
            self._reset_hedge()

            out_1m = df_1m.copy()
            out_4h = df_4h.copy()

            if backtest_start_date is not None:
                out_1m = out_1m[out_1m.index >= pd.Timestamp(backtest_start_date)].copy()
            if len(out_1m) == 0:
                return

            out_1m["rsi"] = self.calculate_rsi(out_1m["close"], period=self.rsi_period)
            out_1m["adx"] = self.calculate_adx(out_1m, period=14)

            out_4h["ema200"] = out_4h["close"].ewm(span=200, adjust=False).mean().shift(1)
            out_4h["ema_touch"] = (out_4h["high"] >= out_4h["ema200"]) & (out_4h["low"] <= out_4h["ema200"])
            out_4h["trend_4h"] = np.where(out_4h["close"] > out_4h["ema200"], "bullish", "bearish")
            out_4h.loc[out_4h["ema200"].isna(), "trend_4h"] = np.nan
            # No look-ahead: use previous closed 4h trend for current 4h bucket.
            out_4h["trend_4h_confirmed"] = out_4h["trend_4h"].shift(1)

            out_1m["timestamp_4h"] = out_1m.index.floor("4h")
            out_1m["is_new_4h_bucket"] = out_1m["timestamp_4h"] != out_1m["timestamp_4h"].shift(1)
            out_1m = out_1m.merge(
                out_4h[["ema200", "ema_touch", "trend_4h_confirmed"]],
                left_on="timestamp_4h",
                right_index=True,
                how="left",
            )
            out_1m.drop("timestamp_4h", axis=1, inplace=True)
            out_1m["ema200"] = out_1m["ema200"].ffill()
            out_1m["ema_touch"] = out_1m["ema_touch"].ffill().fillna(False)
            out_1m["trend"] = np.where(out_1m["close"] > out_1m["ema200"], "bullish", "bearish")

            for i in range(200, len(out_1m)):
                row = out_1m.iloc[i]
                timestamp = row.name
                price = row["close"]
                rsi = row["rsi"]
                adx = row["adx"]
                trend = row["trend"]
                ema_touch = row["ema_touch"]
                ema_val = row["ema200"]
                confirmed_trend_4h = row["trend_4h_confirmed"]
                is_new_4h_bucket = bool(row["is_new_4h_bucket"])

                if pd.isna(rsi) or pd.isna(adx) or pd.isna(ema_val):
                    continue

                self._check_trend_change(trend, price, timestamp, ema_val)

                current_time = i
                time_since_last = current_time - self.last_order_time
                self._check_stop_loss(price, timestamp)
                self._manage_trend_hedge(confirmed_trend_4h, price, timestamp, is_new_4h_bucket)

                if (not ema_touch) and time_since_last >= self.cooldown_time:
                    if rsi <= self.rsi_oversold and trend == "bullish":
                        self._process_long_entry(price, timestamp, adx, current_time)
                    # no strategy short entry in this mode

                self._check_take_profit(price, timestamp)
                self._record_equity(price, timestamp, ema_val)

            if self.current_position:
                last_price = out_1m["close"].iloc[-1]
                last_timestamp = out_1m.index[-1]
                self._close_position(last_price, last_timestamp, "Final Close")

            if self.hedge_position:
                last_price = out_1m["close"].iloc[-1]
                last_timestamp = out_1m.index[-1]
                self._close_hedge_short(last_price, last_timestamp, "Final Hedge Close")
                self._record_equity(last_price, last_timestamp, float(out_1m["ema200"].iloc[-1]))

    return LongOnlyBacktest, LongOnlyWithTrendShortHedge5xBacktest


def configure_baseline_params(bt):
    bt.rsi_oversold = 18
    bt.rsi_overbought = 85
    bt.take_profit_pct = 0.012
    bt.stop_loss_pct = 0.03
    bt.base_cooldown = 5
    bt.cooldown_time = 5


def create_backtest(base_module, mode: str, long_only_cls, hedge_cls):
    if mode == MODE_BASELINE:
        cls = base_module.FloorScaledRSIAveragingBacktest
    elif mode == MODE_LONG_ONLY:
        cls = long_only_cls
    elif mode == MODE_SHORT_HEDGE_5X:
        cls = hedge_cls
    else:
        raise ValueError(f"Unknown mode: {mode}")

    bt = cls(
        symbol=base_module.SYMBOL,
        initial_capital=base_module.INITIAL_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=base_module.ENTRY_SCALE,
    )
    configure_baseline_params(bt)
    return bt


def calculate_metrics(bt, initial_capital: float) -> dict:
    eq = pd.DataFrame(bt.equity_curve)
    tr = pd.DataFrame(bt.trades)

    if eq.empty:
        return {
            "period_start": pd.NaT,
            "period_end": pd.NaT,
            "final_equity": 0.0,
            "total_return_pct": -100.0,
            "cagr_pct": -100.0,
            "max_drawdown_pct": 100.0,
            "calmar_ratio": np.nan,
            "trades": 0,
            "long_trades": 0,
            "short_trades": 0,
            "win_rate_pct": 0.0,
            "long_win_rate_pct": 0.0,
            "short_win_rate_pct": 0.0,
            "profit_factor": np.nan,
            "avg_holding_hours": np.nan,
        }

    eq["timestamp"] = pd.to_datetime(eq["timestamp"])
    start = eq["timestamp"].iloc[0]
    end = eq["timestamp"].iloc[-1]
    final_equity = float(eq["equity"].iloc[-1])
    total_return_pct = (final_equity - initial_capital) / initial_capital * 100.0

    years = max((end - start).days / 365.25, 1e-9)
    cagr_pct = (pow(max(final_equity, 1e-12) / initial_capital, 1 / years) - 1.0) * 100.0

    equity = eq["equity"].astype(float)
    drawdown = (equity - equity.cummax()) / equity.cummax().replace(0, np.nan)
    max_drawdown_pct = float((-drawdown.min()) * 100.0) if len(drawdown) else 0.0
    calmar_ratio = float(cagr_pct / max_drawdown_pct) if max_drawdown_pct > 0 else np.nan

    trades = len(tr)
    if trades > 0:
        tr["entry_time"] = pd.to_datetime(tr["entry_time"])
        tr["exit_time"] = pd.to_datetime(tr["exit_time"])

        long_trades = tr[tr["side"] == "LONG"]
        short_trades = tr[tr["side"] == "SHORT"]
        long_count = int(len(long_trades))
        short_count = int(len(short_trades))

        win_rate = float((tr["pnl"] > 0).mean() * 100.0)
        long_win_rate = float((long_trades["pnl"] > 0).mean() * 100.0) if long_count > 0 else 0.0
        short_win_rate = float((short_trades["pnl"] > 0).mean() * 100.0) if short_count > 0 else 0.0

        gross_profit = float(tr.loc[tr["pnl"] > 0, "pnl"].sum())
        gross_loss = float(tr.loc[tr["pnl"] < 0, "pnl"].sum())
        profit_factor = float(gross_profit / abs(gross_loss)) if gross_loss < 0 else np.inf

        avg_holding_hours = float((tr["exit_time"] - tr["entry_time"]).dt.total_seconds().mean() / 3600.0)
    else:
        long_count = 0
        short_count = 0
        win_rate = 0.0
        long_win_rate = 0.0
        short_win_rate = 0.0
        profit_factor = np.nan
        avg_holding_hours = np.nan

    return {
        "period_start": start,
        "period_end": end,
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "calmar_ratio": calmar_ratio,
        "trades": int(trades),
        "long_trades": long_count,
        "short_trades": short_count,
        "win_rate_pct": win_rate,
        "long_win_rate_pct": long_win_rate,
        "short_win_rate_pct": short_win_rate,
        "profit_factor": profit_factor,
        "avg_holding_hours": avg_holding_hours,
    }


def save_plot(equity_curves: dict[str, pd.DataFrame], metrics_df: pd.DataFrame, filename: Path) -> None:
    if not equity_curves:
        return

    color_map = {
        MODE_BASELINE: "#1f77b4",
        MODE_LONG_ONLY: "#2ca02c",
        MODE_SHORT_HEDGE_5X: "#d62728",
    }

    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("004 Mode Comparison Equity Curves (based on 002)")
    ax_eq.set_ylabel("Equity (USDT)")

    for mode in MODES:
        eq = equity_curves.get(mode)
        if eq is None or eq.empty:
            continue
        ax_eq.plot(eq["timestamp"], eq["equity"], label=mode, color=color_map[mode], linewidth=1.2)

    ax_eq.legend(loc="upper left")
    ax_eq.grid(True, alpha=0.2)

    ax_final = fig.add_subplot(gs[1, 0])
    ax_final.set_title("Final Equity")
    ax_final.bar(metrics_df["mode"], metrics_df["final_equity"], color=[color_map[m] for m in metrics_df["mode"]])
    ax_final.set_ylabel("USDT")
    ax_final.tick_params(axis="x", labelrotation=15)
    ax_final.grid(True, axis="y", alpha=0.2)

    ax_mdd = fig.add_subplot(gs[1, 1])
    ax_mdd.set_title("Max Drawdown")
    ax_mdd.bar(metrics_df["mode"], metrics_df["max_drawdown_pct"], color=[color_map[m] for m in metrics_df["mode"]])
    ax_mdd.set_ylabel("%")
    ax_mdd.tick_params(axis="x", labelrotation=15)
    ax_mdd.grid(True, axis="y", alpha=0.2)

    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close()


def _fmt(v, digits=4):
    if pd.isna(v):
        return "N/A"
    return f"{v:.{digits}f}"


def save_markdown(metrics_df: pd.DataFrame, filename: Path) -> None:
    base_row = metrics_df[metrics_df["mode"] == MODE_BASELINE].iloc[0]

    lines = []
    lines.append("# 04 Mode Comparison (Revised Hedge Logic)")
    lines.append("")
    lines.append("## Hedge Logic Used")
    lines.append("- `baseline_02`: original 002 behavior")
    lines.append("- `long_only_no_short`: strategy short entry disabled")
    lines.append("- `long_only_with_trend_short_hedge_5x`:")
    lines.append("  - strategy remains long-only")
    lines.append("  - hedge trend confirmation uses closed 4h candles only")
    lines.append("  - current 4h bucket uses previous closed 4h trend (`trend_4h_confirmed = trend_4h.shift(1)`) to avoid look-ahead")
    lines.append("  - open hedge short when confirmed 4h trend is bearish")
    lines.append("  - close hedge short when confirmed 4h trend is bullish")
    lines.append("  - hedge size: `5 * base_qty`, `base_qty = initial long unit qty`")
    lines.append("")
    lines.append("## Performance Table")
    lines.append("")
    lines.append("| Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['mode']}` | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | {_fmt(r['cagr_pct'])} | "
            f"{_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} |"
        )

    lines.append("")
    lines.append("## Delta vs Baseline")
    lines.append("")
    lines.append("| Mode | Final Equity Delta % | MDD Delta %p | Trades Delta |")
    lines.append("|---|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        if r["mode"] == MODE_BASELINE:
            continue
        eq_delta = (r["final_equity"] / base_row["final_equity"] - 1.0) * 100.0
        mdd_delta = r["max_drawdown_pct"] - base_row["max_drawdown_pct"]
        trades_delta = int(r["trades"] - base_row["trades"])
        lines.append(f"| `{r['mode']}` | {_fmt(eq_delta)} | {_fmt(mdd_delta)} | {trades_delta:+d} |")

    lines.append("")
    lines.append("## Output Files")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{CSV_FILE}`")

    filename.write_text("\n".join(lines), encoding="utf-8")


def run():
    base = load_base_module(BASE_SCRIPT_PATH)
    long_only_cls, hedge_cls = build_mode_classes(base)

    df_1m, df_4h = base.load_data()
    df_1m = df_1m[(df_1m.index >= base.BACKTEST_START) & (df_1m.index <= base.BACKTEST_END)].copy()

    metrics_rows = []
    equity_curves: dict[str, pd.DataFrame] = {}

    for mode in MODES:
        bt = create_backtest(base, mode, long_only_cls, hedge_cls)
        bt.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)

        metrics = calculate_metrics(bt, base.INITIAL_CAPITAL)
        metrics["mode"] = mode
        metrics_rows.append(metrics)

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            equity_curves[mode] = eq[["timestamp", "equity"]].copy()
        else:
            equity_curves[mode] = pd.DataFrame(columns=["timestamp", "equity"])

    order_map = {m: i for i, m in enumerate(MODES)}
    metrics_df = pd.DataFrame(metrics_rows).sort_values(by="mode", key=lambda s: s.map(order_map)).reset_index(drop=True)

    save_plot(equity_curves, metrics_df, PLOT_FILE)
    metrics_df.to_csv(CSV_FILE, index=False)
    save_markdown(metrics_df, MD_FILE)

    show_cols = [
        "mode",
        "final_equity",
        "total_return_pct",
        "cagr_pct",
        "max_drawdown_pct",
        "trades",
        "long_trades",
        "short_trades",
        "win_rate_pct",
        "profit_factor",
    ]
    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(f"saved_report={MD_FILE}")
    print(metrics_df[show_cols].to_string(index=False))


if __name__ == "__main__":
    run()
