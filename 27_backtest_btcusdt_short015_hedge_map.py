from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")

OUT_BASE = "27_backtest_btcusdt_short015_hedge_map"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_METRICS_CSV = Path(f"{OUT_BASE}_metrics.csv")
OUT_EVENTS_CSV = Path(f"{OUT_BASE}_events.csv")
OUT_POSITION_CSV = Path(f"{OUT_BASE}_position.csv")

INITIAL_CAPITAL = 500.0
ENTRY_SCALE_SHORT = 0.15
HYSTERESIS_BAND = 0.005


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


def load_data_no_filter(base_module) -> tuple[pd.DataFrame, pd.DataFrame]:
    periods_1m = [("2022-01-01", "2024-12-31"), ("2025-01-01", base_module.BACKTEST_END)]
    periods_4h = [
        ("2021-07-01", "2021-12-31"),
        ("2022-01-01", "2024-12-31"),
        ("2025-01-01", base_module.BACKTEST_END),
    ]
    df_1m = base_module._load_cached_df(base_module.SYMBOL, "1m", periods_1m).sort_index()
    df_4h = base_module._load_cached_df(base_module.SYMBOL, "4h", periods_4h).sort_index()
    return df_1m, df_4h


def build_short_visual_class(base_module, helper_module):
    _, BaseHedgeCls = helper_module.build_mode_classes(base_module)

    class ShortOnlyWithLongHedgeVisual(BaseHedgeCls):
        hysteresis = float(HYSTERESIS_BAND)
        hedge_long_multiplier = 5.0

        @staticmethod
        def _compute_hysteresis_state(df_4h: pd.DataFrame, hysteresis: float) -> pd.Series:
            states: list[str | float] = []
            prev_state: str | None = None
            for _, row in df_4h.iterrows():
                ema = row["ema200"]
                close = row["close"]
                if pd.isna(ema) or pd.isna(close):
                    states.append(np.nan)
                    continue
                upper = ema * (1.0 + hysteresis)
                lower = ema * (1.0 - hysteresis)
                if close > upper:
                    state = "bullish"
                elif close < lower:
                    state = "bearish"
                else:
                    if prev_state is None:
                        state = "bullish" if close > ema else "bearish"
                    else:
                        state = prev_state
                states.append(state)
                prev_state = state
            return pd.Series(states, index=df_4h.index)

        def _reset_visual_logs(self):
            self.event_log: list[dict] = []
            self.position_state_log: list[dict] = []
            self.hedge_interval_log: list[dict] = []
            self._hedge_open_time = None

        def _append_event(self, timestamp, side: str, event: str, price: float, quantity: float):
            self.event_log.append(
                {
                    "timestamp": pd.to_datetime(timestamp),
                    "side": side,
                    "event": event,
                    "price": float(price),
                    "quantity": float(quantity),
                }
            )

        def _process_short_entry(self, price, timestamp, adx, current_time):
            # BaseHedgeCls originates from LongOnlyBacktest, so explicitly
            # restore the original short-entry logic.
            return base_module.RSIAveragingBacktestStandalone._process_short_entry(self, price, timestamp, adx, current_time)

        def _open_position(self, side, price, timestamp, quantity):
            super()._open_position(side, price, timestamp, quantity)
            if side == "SHORT" and self.position_quantity:
                self.hedge_base_qty = float(self.position_quantity)
                self._append_event(timestamp, "SHORT", "open", float(price), float(self.current_position["quantity"]))

        def _add_to_position(self, price, timestamp, quantity, adx):
            prev_side = None
            prev_qty = 0.0
            if self.current_position:
                prev_side = self.current_position["side"]
                prev_qty = float(self.current_position["quantity"])
            super()._add_to_position(price, timestamp, quantity, adx)
            if self.current_position and prev_side == self.current_position["side"]:
                post_qty = float(self.current_position["quantity"])
                add_qty = post_qty - prev_qty
                if add_qty > 1e-12 and prev_side == "SHORT":
                    self._append_event(timestamp, "SHORT", "add", float(price), float(add_qty))

        def _open_hedge_long(self, price, timestamp):
            if self.hedge_position is not None:
                return
            if self.position_quantity:
                self.hedge_base_qty = float(self.position_quantity)
            base_qty = float(self.hedge_base_qty)
            if base_qty <= 0:
                return

            hedge_qty = base_qty * self.hedge_long_multiplier
            if hedge_qty <= 0:
                return

            open_commission = hedge_qty * price * self.commission
            self.capital -= open_commission
            self.hedge_position = {
                "side": "LONG",
                "avg_entry": float(price),
                "quantity": float(hedge_qty),
                "entry_time": timestamp,
                "total_commission": float(open_commission),
            }
            self._hedge_open_time = pd.to_datetime(timestamp)
            self._append_event(timestamp, "LONG", "hedge_open", float(price), float(hedge_qty))

        def _close_hedge_long(self, price, timestamp, reason):
            if self.hedge_position is None:
                return

            pos = self.hedge_position
            close_commission = pos["quantity"] * price * self.commission
            pnl = (price - pos["avg_entry"]) * pos["quantity"]
            pnl -= (pos["total_commission"] + close_commission)
            self.capital += pnl

            self.trades.append(
                {
                    "entry_time": pos["entry_time"],
                    "exit_time": timestamp,
                    "side": "LONG",
                    "avg_entry": pos["avg_entry"],
                    "exit_price": float(price),
                    "quantity": pos["quantity"],
                    "num_entries": 1,
                    "pnl": float(pnl),
                    "return_pct": float((pnl / self.initial_capital) * 100.0),
                    "reason": reason,
                }
            )
            self._append_event(timestamp, "LONG", "hedge_close", float(price), float(pos["quantity"]))
            if self._hedge_open_time is not None:
                self.hedge_interval_log.append(
                    {
                        "start": self._hedge_open_time,
                        "end": pd.to_datetime(timestamp),
                        "reason": reason,
                    }
                )
            self._hedge_open_time = None
            self.hedge_position = None

        def _manage_trend_hedge(self, confirmed_trend_4h, price, timestamp, is_new_4h_bucket):
            if not is_new_4h_bucket:
                return
            if confirmed_trend_4h not in ("bullish", "bearish"):
                return

            if confirmed_trend_4h == "bullish" and self.hedge_position is None:
                self._open_hedge_long(price, timestamp)
            if confirmed_trend_4h == "bearish" and self.hedge_position is not None:
                self._close_hedge_long(price, timestamp, "Hedge Close Trend Down")

        def _compute_position_multipliers(self) -> tuple[float, float, float, float]:
            short_qty = 0.0
            if self.current_position and self.current_position["side"] == "SHORT":
                short_qty = float(self.current_position["quantity"])

            hedge_long_qty = 0.0
            if self.hedge_position and self.hedge_position["side"] == "LONG":
                hedge_long_qty = float(self.hedge_position["quantity"])

            base_qty = float(getattr(self, "hedge_base_qty", 0.0) or 0.0)
            if base_qty <= 0:
                if short_qty > 0:
                    base_qty = short_qty
                elif hedge_long_qty > 0:
                    base_qty = hedge_long_qty / self.hedge_long_multiplier

            if base_qty <= 0:
                return 0.0, 0.0, 0.0, 0.0

            short_mult = short_qty / base_qty
            hedge_long_mult = hedge_long_qty / base_qty
            # sign convention: short positive, long hedge negative
            net_mult = short_mult - hedge_long_mult
            return float(base_qty), float(short_mult), float(hedge_long_mult), float(net_mult)

        def _log_position_state(self, timestamp, price, ema):
            base_qty, short_mult, hedge_long_mult, net_mult = self._compute_position_multipliers()
            self.position_state_log.append(
                {
                    "timestamp": pd.to_datetime(timestamp),
                    "price": float(price),
                    "ema200": float(ema) if pd.notna(ema) else np.nan,
                    "base_qty": base_qty,
                    "short_mult": short_mult,
                    "hedge_long_mult": hedge_long_mult,
                    "net_mult": net_mult,
                    "hedge_active": float(hedge_long_mult > 0.0),
                }
            )

        def _record_equity(self, price, timestamp, ema=0):
            if self.bankrupt:
                self.equity_curve.append({"timestamp": timestamp, "equity": 0.0, "price": price, "ema200": ema})
                return

            equity = float(self.capital)
            if self.current_position:
                pos = self.current_position
                if pos["side"] == "LONG":
                    equity += (price - pos["avg_entry"]) * pos["quantity"]
                else:
                    equity += (pos["avg_entry"] - price) * pos["quantity"]

            if self.hedge_position:
                hedge = self.hedge_position
                equity += (price - hedge["avg_entry"]) * hedge["quantity"]

            if equity <= 0:
                self.equity_curve.append({"timestamp": timestamp, "equity": 0.0, "price": price, "ema200": ema})
                self._append_event(timestamp, "SYSTEM", "bankrupt", float(price), 0.0)
                if self._hedge_open_time is not None:
                    self.hedge_interval_log.append(
                        {
                            "start": self._hedge_open_time,
                            "end": pd.to_datetime(timestamp),
                            "reason": "bankruptcy_reset",
                        }
                    )
                    self._hedge_open_time = None
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
                    "equity": float(equity),
                    "price": float(price),
                    "ema200": float(ema),
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
            self._reset_visual_logs()
            self.hedge_base_qty = 0.0

            out_1m = df_1m.copy()
            out_4h = df_4h.copy()

            if backtest_start_date is not None:
                out_1m = out_1m[out_1m.index >= pd.Timestamp(backtest_start_date)].copy()
            if len(out_1m) == 0:
                return

            out_1m["rsi"] = self.calculate_rsi(out_1m["close"], period=self.rsi_period)
            out_1m["adx"] = self.calculate_adx(out_1m, period=14)

            out_4h["ema200"] = out_4h["close"].ewm(span=200, adjust=False).mean().shift(1)
            out_4h["ema_touch_raw"] = (out_4h["high"] >= out_4h["ema200"]) & (out_4h["low"] <= out_4h["ema200"])
            out_4h["ema_touch_confirmed"] = out_4h["ema_touch_raw"].shift(1).fillna(False)
            out_4h["trend_4h_hyst"] = self._compute_hysteresis_state(out_4h, self.hysteresis)
            out_4h["trend_4h_confirmed"] = out_4h["trend_4h_hyst"].shift(1)

            out_1m["timestamp_4h"] = out_1m.index.floor("4h")
            out_1m["is_new_4h_bucket"] = out_1m["timestamp_4h"] != out_1m["timestamp_4h"].shift(1)
            out_1m = out_1m.merge(
                out_4h[["ema200", "ema_touch_confirmed", "trend_4h_confirmed"]],
                left_on="timestamp_4h",
                right_index=True,
                how="left",
            )
            out_1m.drop("timestamp_4h", axis=1, inplace=True)
            out_1m["ema200"] = out_1m["ema200"].ffill()
            out_1m["ema_touch"] = out_1m["ema_touch_confirmed"].ffill().fillna(False)
            out_1m.drop("ema_touch_confirmed", axis=1, inplace=True)
            out_1m["trend"] = np.where(out_1m["close"] > out_1m["ema200"], "bullish", "bearish")

            for i in range(200, len(out_1m)):
                row = out_1m.iloc[i]
                timestamp = row.name
                price = float(row["close"])
                rsi = row["rsi"]
                adx = row["adx"]
                trend = row["trend"]
                ema_touch = bool(row["ema_touch"])
                ema_val = row["ema200"]
                confirmed_trend_4h = row["trend_4h_confirmed"]
                is_new_4h_bucket = bool(row["is_new_4h_bucket"])

                if pd.isna(rsi) or pd.isna(adx) or pd.isna(ema_val):
                    continue

                self._check_trend_change(trend, price, timestamp, float(ema_val))
                current_time = i
                time_since_last = current_time - self.last_order_time
                self._check_stop_loss(price, timestamp)
                self._manage_trend_hedge(confirmed_trend_4h, price, timestamp, is_new_4h_bucket)

                if (not ema_touch) and time_since_last >= self.cooldown_time:
                    if rsi >= self.rsi_overbought and trend == "bearish":
                        self._process_short_entry(price, timestamp, float(adx), current_time)

                self._check_take_profit(price, timestamp)
                self._record_equity(price, timestamp, float(ema_val))
                self._log_position_state(timestamp, price, float(ema_val))

            if self.current_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_timestamp = out_1m.index[-1]
                self._close_position(last_price, last_timestamp, "Final Close")
                self._append_event(last_timestamp, "SHORT", "final_close", last_price, 0.0)

            if self.hedge_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_timestamp = out_1m.index[-1]
                self._close_hedge_long(last_price, last_timestamp, "Final Hedge Close")
                self._record_equity(last_price, last_timestamp, float(out_1m["ema200"].iloc[-1]))
                self._log_position_state(last_timestamp, last_price, float(out_1m["ema200"].iloc[-1]))

    return ShortOnlyWithLongHedgeVisual


def _extract_true_intervals(mask: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    if mask.empty:
        return []
    grp = (mask != mask.shift(1)).cumsum()
    out: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for _, seg in mask.groupby(grp):
        if not bool(seg.iloc[0]):
            continue
        out.append((pd.to_datetime(seg.index[0]), pd.to_datetime(seg.index[-1])))
    return out


def build_reason_breakdown(trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return pd.DataFrame(columns=["reason", "trades", "win_rate_pct", "net_pnl", "avg_pnl"])
    g = (
        trades_df.groupby("reason", dropna=False)
        .agg(
            trades=("pnl", "size"),
            win_rate_pct=("pnl", lambda x: float((x > 0).mean() * 100.0)),
            net_pnl=("pnl", "sum"),
            avg_pnl=("pnl", "mean"),
        )
        .reset_index()
        .sort_values("net_pnl", ascending=False)
    )
    return g


def save_plot(eq_df: pd.DataFrame, event_df: pd.DataFrame, pos_df: pd.DataFrame):
    plot_eq = eq_df.copy()
    plot_eq["timestamp"] = pd.to_datetime(plot_eq["timestamp"])
    plot_eq = plot_eq.sort_values("timestamp")
    plot_eq = plot_eq.drop_duplicates(subset=["timestamp"]).set_index("timestamp")

    plot_pos = pos_df.copy()
    plot_pos["timestamp"] = pd.to_datetime(plot_pos["timestamp"])
    plot_pos = plot_pos.sort_values("timestamp")
    plot_pos = plot_pos.drop_duplicates(subset=["timestamp"]).set_index("timestamp")

    hedge_intervals = _extract_true_intervals(plot_pos["hedge_active"].astype(bool))

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(16, 12),
        sharex=True,
        gridspec_kw={"height_ratios": [1.45, 1.3, 1.0]},
    )
    ax_eq, ax_px, ax_net = axes

    ax_eq.plot(plot_eq.index, plot_eq["equity"], color="#111111", linewidth=1.1, label="Equity (short-only, scale 0.15)")
    ax_eq.axhline(INITIAL_CAPITAL, color="#666666", linestyle="--", linewidth=0.9, label="Start 500")
    ax_eq.set_title("27 Study: Short-only 0.15 with Long Hedge State Map")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_px.plot(plot_eq.index, plot_eq["price"], color="#1f77b4", linewidth=0.9, label="BTC Close")
    ax_px.plot(plot_eq.index, plot_eq["ema200"], color="#d95f02", linewidth=0.9, label="4h EMA200 (confirmed)")
    for s, e in hedge_intervals:
        ax_px.axvspan(s, e, color="#8ccf9e", alpha=0.18, linewidth=0)

    if not event_df.empty:
        ev = event_df.copy()
        ev["timestamp"] = pd.to_datetime(ev["timestamp"])
        short_ev = ev[(ev["side"] == "SHORT") & (ev["event"].isin(["open", "add"]))]
        long_ev = ev[(ev["side"] == "LONG") & (ev["event"] == "hedge_open")]
        if not short_ev.empty:
            ax_px.scatter(
                short_ev["timestamp"],
                short_ev["price"],
                marker="v",
                s=26,
                color="#d62728",
                edgecolors="#5a1010",
                linewidths=0.8,
                alpha=0.9,
                label="SHORT entry",
                zorder=6,
            )
        if not long_ev.empty:
            ax_px.scatter(
                long_ev["timestamp"],
                long_ev["price"],
                marker="^",
                s=26,
                color="#2ca02c",
                edgecolors="#124d1f",
                linewidths=0.8,
                alpha=0.9,
                label="LONG hedge open",
                zorder=6,
            )

    ax_px.set_ylabel("Price (USDT)")
    ax_px.set_title("Entries (01-style markers) + Hedge Active Shading")
    ax_px.grid(True, alpha=0.2)
    ax_px.legend(loc="upper left")

    for s, e in hedge_intervals:
        ax_net.axvspan(s, e, color="#8ccf9e", alpha=0.18, linewidth=0)
    ax_net.plot(plot_pos.index, plot_pos["net_mult"], color="#111111", linewidth=1.0, label="Net mult = short - hedge_long")
    ax_net.plot(plot_pos.index, plot_pos["short_mult"], color="#d62728", linewidth=0.8, alpha=0.8, label="Short mult")
    ax_net.plot(plot_pos.index, -plot_pos["hedge_long_mult"], color="#2ca02c", linewidth=0.8, alpha=0.8, label="-Hedge long mult")
    ax_net.axhline(0.0, color="#333333", linestyle="--", linewidth=0.9)
    ax_net.axhline(-5.0, color="#2ca02c", linestyle=":", linewidth=0.9, alpha=0.8, label="Long hedge only ~ -5x")
    ax_net.set_ylabel("x base_qty")
    ax_net.set_xlabel("Time")
    ax_net.set_title("Net Position Multiple (base_qty normalized)")
    ax_net.grid(True, alpha=0.2)
    ax_net.legend(loc="upper left")

    ax_net.xaxis.set_major_locator(mdates.YearLocator())
    ax_net.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(metrics: dict, trades_df: pd.DataFrame, event_df: pd.DataFrame, pos_df: pd.DataFrame):
    reason_df = build_reason_breakdown(trades_df)

    hedge_active_ratio = float(pos_df["hedge_active"].mean() * 100.0) if not pos_df.empty else np.nan
    max_short_mult = float(pos_df["short_mult"].max()) if not pos_df.empty else np.nan
    max_hedge_mult = float(pos_df["hedge_long_mult"].max()) if not pos_df.empty else np.nan
    max_net_mult = float(pos_df["net_mult"].max()) if not pos_df.empty else np.nan
    min_net_mult = float(pos_df["net_mult"].min()) if not pos_df.empty else np.nan

    short_open = int(((event_df["side"] == "SHORT") & (event_df["event"] == "open")).sum()) if not event_df.empty else 0
    short_add = int(((event_df["side"] == "SHORT") & (event_df["event"] == "add")).sum()) if not event_df.empty else 0
    hedge_open = int(((event_df["side"] == "LONG") & (event_df["event"] == "hedge_open")).sum()) if not event_df.empty else 0
    bankrupt_events = event_df[event_df["event"] == "bankrupt"] if not event_df.empty else pd.DataFrame()
    bankrupt_ts = pd.to_datetime(bankrupt_events["timestamp"].iloc[0]) if not bankrupt_events.empty else pd.NaT

    lines: list[str] = []
    lines.append("# 27 Study: Short-only 0.15 Trade Map")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Strategy: short-only entries + long hedge by 4h confirmed trend")
    lines.append(f"- Initial capital: `{_fmt(INITIAL_CAPITAL)}`")
    lines.append(f"- Entry scale (short): `{_fmt(ENTRY_SCALE_SHORT, 2)}`")
    lines.append(f"- Hysteresis: `{_fmt(HYSTERESIS_BAND * 100.0, 2)}%`")
    lines.append("- Net position convention: `net_mult = short_mult - hedge_long_mult`")
    lines.append("- Therefore, hedge-only state is around `-5`.")
    lines.append("")
    lines.append("## Core Metrics")
    lines.append(f"- Final Equity: `{_fmt(metrics.get('final_equity', np.nan))}`")
    lines.append(f"- Return %: `{_fmt(metrics.get('total_return_pct', np.nan))}`")
    lines.append(f"- CAGR %: `{_fmt(metrics.get('cagr_pct', np.nan))}`")
    lines.append(f"- MDD %: `{_fmt(metrics.get('max_drawdown_pct', np.nan))}`")
    lines.append(f"- Calmar: `{_fmt(metrics.get('calmar_ratio', np.nan))}`")
    lines.append(f"- Trades: `{int(metrics.get('trades', 0))}` (Long `{int(metrics.get('long_trades', 0))}`, Short `{int(metrics.get('short_trades', 0))}`)")
    lines.append(f"- Win rate %: `{_fmt(metrics.get('win_rate_pct', np.nan))}`")
    lines.append(f"- Profit factor: `{_fmt(metrics.get('profit_factor', np.nan))}`")
    lines.append("")
    lines.append("## Position Dynamics")
    lines.append(f"- Hedge active ratio: `{_fmt(hedge_active_ratio)}`%")
    lines.append(f"- Max short mult: `{_fmt(max_short_mult)}`")
    lines.append(f"- Max hedge long mult: `{_fmt(max_hedge_mult)}`")
    lines.append(f"- Net mult max/min: `{_fmt(max_net_mult)}` / `{_fmt(min_net_mult)}`")
    lines.append(f"- Event counts: short open `{short_open}`, short add `{short_add}`, hedge open `{hedge_open}`")
    lines.append(f"- Bankruptcy timestamp: `{bankrupt_ts if pd.notna(bankrupt_ts) else 'None'}`")
    lines.append("")
    lines.append("## Reason Breakdown")
    lines.append("| Reason | Trades | Win Rate % | Net PnL | Avg PnL |")
    lines.append("|---|---:|---:|---:|---:|")
    if reason_df.empty:
        lines.append("| `N/A` | 0 | N/A | N/A | N/A |")
    else:
        for _, r in reason_df.iterrows():
            lines.append(
                f"| `{r['reason']}` | {int(r['trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['net_pnl'])} | {_fmt(r['avg_pnl'])} |"
            )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics: `{OUT_METRICS_CSV}`")
    lines.append(f"- Events: `{OUT_EVENTS_CSV}`")
    lines.append(f"- Position: `{OUT_POSITION_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_27", BASE_002_PATH)
    helper_module = load_module("m04_27", BASE_04_PATH)

    df_1m, df_4h = load_data_no_filter(base_module)
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    cls = build_short_visual_class(base_module, helper_module)
    bt = cls(
        symbol=base_module.SYMBOL,
        initial_capital=INITIAL_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=ENTRY_SCALE_SHORT,
    )
    helper_module.configure_baseline_params(bt)
    bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

    metrics = helper_module.calculate_metrics(bt, INITIAL_CAPITAL)
    eq_df = pd.DataFrame(bt.equity_curve)
    trades_df = pd.DataFrame(bt.trades)
    event_df = pd.DataFrame(bt.event_log)
    pos_df = pd.DataFrame(bt.position_state_log)

    if eq_df.empty:
        raise RuntimeError("Empty equity curve in 27 study.")

    eq_df["timestamp"] = pd.to_datetime(eq_df["timestamp"])
    if not trades_df.empty:
        trades_df["entry_time"] = pd.to_datetime(trades_df["entry_time"])
        trades_df["exit_time"] = pd.to_datetime(trades_df["exit_time"])
    if not event_df.empty:
        event_df["timestamp"] = pd.to_datetime(event_df["timestamp"])
    if not pos_df.empty:
        pos_df["timestamp"] = pd.to_datetime(pos_df["timestamp"])

    metrics_row = {
        **metrics,
        "initial_capital": float(INITIAL_CAPITAL),
        "entry_scale_short": float(ENTRY_SCALE_SHORT),
        "hysteresis_band": float(HYSTERESIS_BAND),
    }
    pd.DataFrame([metrics_row]).to_csv(OUT_METRICS_CSV, index=False)
    event_df.to_csv(OUT_EVENTS_CSV, index=False)
    pos_df.to_csv(OUT_POSITION_CSV, index=False)

    save_plot(eq_df, event_df, pos_df)
    save_report(metrics, trades_df, event_df, pos_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_report={OUT_MD}")
    print(f"saved_metrics={OUT_METRICS_CSV}")
    print(f"saved_events={OUT_EVENTS_CSV}")
    print(f"saved_position={OUT_POSITION_CSV}")
    print(
        "summary="
        f"final_equity:{_fmt(metrics.get('final_equity', np.nan))},"
        f"mdd:{_fmt(metrics.get('max_drawdown_pct', np.nan))},"
        f"trades:{int(metrics.get('trades', 0))}"
    )


if __name__ == "__main__":
    run()
