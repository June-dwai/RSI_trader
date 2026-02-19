from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")

PLOT_FILE = Path("20_backtest_btcusdt_hys05_diagnostics.png")
MD_FILE = Path("20_backtest_btcusdt_hys05_diagnostics.md")
METRICS_FILE = Path("20_backtest_btcusdt_hys05_diagnostics_metrics.csv")
DRAWDOWN_FILE = Path("20_backtest_btcusdt_hys05_diagnostics_drawdowns.csv")
REASON_FILE = Path("20_backtest_btcusdt_hys05_diagnostics_reason_pnl.csv")
ENTRY_FILE = Path("20_backtest_btcusdt_hys05_diagnostics_entry_quality.csv")
YEARLY_FILE = Path("20_backtest_btcusdt_hys05_diagnostics_yearly.csv")
EXPOSURE_FILE = Path("20_backtest_btcusdt_hys05_diagnostics_exposure.csv")

HYSTERESIS_BAND = 0.005
TOP_DD = 5


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


def _fmt(v, d=4):
    if pd.isna(v):
        return "N/A"
    return f"{v:.{d}f}"


def build_diag_class(base_module, helper_module):
    _, BaseHedgeCls = helper_module.build_mode_classes(base_module)

    class FixedBase5xWithHysteresisDiag(BaseHedgeCls):
        hysteresis = float(HYSTERESIS_BAND)

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

            self.state_rows: list[tuple] = []
            self.entry_signals: list[dict] = []
            self.event_log: list[dict] = []
            self.signal_counters = {
                "entry_condition_true": 0,
                "blocked_by_ema_touch": 0,
                "blocked_by_cooldown": 0,
                "executed_long_entries": 0,
            }

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
                prev_sl = tuple(self.stop_loss)
                had_hedge = self.hedge_position is not None
                self._check_stop_loss(price, timestamp)
                curr_sl = tuple(self.stop_loss)
                if prev_sl != curr_sl:
                    if prev_sl == (0, 0) and curr_sl[1] != 0:
                        self.event_log.append(
                            {
                                "timestamp": timestamp,
                                "event_type": "stop_loss_trigger",
                                "price": price,
                                "stop_qty": float(curr_sl[1]),
                            }
                        )
                    elif prev_sl[1] != 0 and curr_sl[1] == 0:
                        self.event_log.append(
                            {
                                "timestamp": timestamp,
                                "event_type": "stop_loss_readd",
                                "price": price,
                                "stop_qty": float(prev_sl[1]),
                            }
                        )
                self._manage_trend_hedge(confirmed_trend_4h, price, timestamp, is_new_4h_bucket)
                has_hedge = self.hedge_position is not None
                if (not had_hedge) and has_hedge:
                    self.event_log.append({"timestamp": timestamp, "event_type": "hedge_open", "price": price, "stop_qty": 0.0})
                elif had_hedge and (not has_hedge):
                    self.event_log.append(
                        {"timestamp": timestamp, "event_type": "hedge_close", "price": price, "stop_qty": 0.0}
                    )

                long_signal = bool(rsi <= self.rsi_oversold and trend == "bullish")
                if long_signal:
                    self.signal_counters["entry_condition_true"] += 1
                    if ema_touch:
                        self.signal_counters["blocked_by_ema_touch"] += 1
                    elif time_since_last < self.cooldown_time:
                        self.signal_counters["blocked_by_cooldown"] += 1

                if (not ema_touch) and time_since_last >= self.cooldown_time:
                    if long_signal:
                        prev_last_order_time = self.last_order_time
                        self._process_long_entry(price, timestamp, float(adx), current_time)
                        if self.last_order_time != prev_last_order_time:
                            self.signal_counters["executed_long_entries"] += 1
                            self.entry_signals.append(
                                {
                                    "timestamp": timestamp,
                                    "entry_price": price,
                                    "rsi": float(rsi),
                                    "adx": float(adx),
                                    "ema200": float(ema_val),
                                    "ema_dist_pct": abs((price - float(ema_val)) / float(ema_val)) * 100.0,
                                    "trend_1m": trend,
                                    "trend_4h_confirmed": confirmed_trend_4h if pd.notna(confirmed_trend_4h) else "nan",
                                    "ema_touch": ema_touch,
                                }
                            )

                self._check_take_profit(price, timestamp)
                self._record_equity(price, timestamp, float(ema_val))

                if self.current_position and self.current_position["side"] == "LONG":
                    long_qty = float(self.current_position["quantity"])
                else:
                    long_qty = 0.0
                hedge_qty = float(self.hedge_position["quantity"]) if self.hedge_position is not None else 0.0
                net_qty = long_qty - hedge_qty
                current_equity = float(self.equity_curve[-1]["equity"])

                self.state_rows.append(
                    (
                        timestamp,
                        price,
                        current_equity,
                        long_qty,
                        hedge_qty,
                        net_qty,
                        confirmed_trend_4h if pd.notna(confirmed_trend_4h) else "nan",
                        ema_touch,
                    )
                )

            if self.current_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_timestamp = out_1m.index[-1]
                self._close_position(last_price, last_timestamp, "Final Close")

            if self.hedge_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_timestamp = out_1m.index[-1]
                self._close_hedge_short(last_price, last_timestamp, "Final Hedge Close")
                self._record_equity(last_price, last_timestamp, float(out_1m["ema200"].iloc[-1]))

    return FixedBase5xWithHysteresisDiag


def to_df(bt) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eq = pd.DataFrame(bt.equity_curve)
    tr = pd.DataFrame(bt.trades)
    ev = pd.DataFrame(bt.event_log)
    st = pd.DataFrame(
        bt.state_rows,
        columns=[
            "timestamp",
            "price",
            "equity",
            "long_qty",
            "hedge_qty",
            "net_qty",
            "trend_4h_confirmed",
            "ema_touch",
        ],
    )

    if not eq.empty:
        eq["timestamp"] = pd.to_datetime(eq["timestamp"])
        eq["equity"] = eq["equity"].astype(float)
    if not tr.empty:
        tr["entry_time"] = pd.to_datetime(tr["entry_time"])
        tr["exit_time"] = pd.to_datetime(tr["exit_time"])
        tr["pnl"] = tr["pnl"].astype(float)
    if not ev.empty:
        ev["timestamp"] = pd.to_datetime(ev["timestamp"])
        ev["price"] = ev["price"].astype(float)
        ev["stop_qty"] = ev["stop_qty"].astype(float)
    if not st.empty:
        st["timestamp"] = pd.to_datetime(st["timestamp"])
        st["equity"] = st["equity"].astype(float)
        st["price"] = st["price"].astype(float)
        st["long_qty"] = st["long_qty"].astype(float)
        st["hedge_qty"] = st["hedge_qty"].astype(float)
        st["net_qty"] = st["net_qty"].astype(float)
        st["ema_touch"] = st["ema_touch"].astype(bool)
        run_max = st["equity"].cummax().replace(0, np.nan)
        st["drawdown_pct"] = (st["equity"] / run_max - 1.0) * 100.0
        st["net_notional"] = st["net_qty"] * st["price"]
        st["net_notional_over_equity"] = st["net_notional"] / st["equity"].replace(0, np.nan)

    return eq, tr, st, ev


def build_drawdown_episodes(state_df: pd.DataFrame) -> pd.DataFrame:
    if state_df.empty:
        return pd.DataFrame()

    s = state_df.reset_index(drop=True).copy()
    s["run_max"] = s["equity"].cummax()
    s["dd"] = s["equity"] / s["run_max"].replace(0, np.nan) - 1.0

    episodes = []
    in_dd = False
    peak_idx = 0
    start_peak_idx = 0
    trough_idx = 0
    trough_dd = 0.0

    for i in range(len(s)):
        if s.loc[i, "equity"] >= s.loc[i, "run_max"] - 1e-12:
            peak_idx = i

        dd = float(s.loc[i, "dd"])
        if not in_dd and dd < 0:
            in_dd = True
            start_peak_idx = peak_idx
            trough_idx = i
            trough_dd = dd

        if in_dd:
            if dd < trough_dd:
                trough_dd = dd
                trough_idx = i
            if dd >= 0:
                episodes.append((start_peak_idx, trough_idx, i, True, trough_dd))
                in_dd = False

    if in_dd:
        episodes.append((start_peak_idx, trough_idx, len(s) - 1, False, trough_dd))

    rows = []
    for idx, (peak_i, trough_i, end_i, recovered, trough_dd) in enumerate(episodes, start=1):
        peak_ts = s.loc[peak_i, "timestamp"]
        trough_ts = s.loc[trough_i, "timestamp"]
        end_ts = s.loc[end_i, "timestamp"]
        rows.append(
            {
                "episode_id": idx,
                "peak_time": peak_ts,
                "peak_equity": float(s.loc[peak_i, "equity"]),
                "trough_time": trough_ts,
                "trough_equity": float(s.loc[trough_i, "equity"]),
                "recovery_time": end_ts if recovered else pd.NaT,
                "recovered": recovered,
                "max_drawdown_pct": float(-trough_dd * 100.0),
                "bars_peak_to_trough": int(trough_i - peak_i),
                "bars_underwater": int(end_i - peak_i),
                "days_underwater": float((end_ts - peak_ts).total_seconds() / 86400.0),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values("max_drawdown_pct", ascending=False).reset_index(drop=True)


def annotate_drawdown_episodes(
    episodes: pd.DataFrame, trades_df: pd.DataFrame, state_df: pd.DataFrame, event_df: pd.DataFrame
) -> pd.DataFrame:
    if episodes.empty:
        return episodes

    rows = []
    state_end = state_df["timestamp"].max()

    for _, ep in episodes.iterrows():
        start_ts = ep["peak_time"]
        end_ts = ep["recovery_time"] if pd.notna(ep["recovery_time"]) else state_end

        seg_state = state_df[(state_df["timestamp"] >= start_ts) & (state_df["timestamp"] <= end_ts)].copy()
        seg_trades = trades_df[(trades_df["exit_time"] >= start_ts) & (trades_df["exit_time"] <= end_ts)].copy()
        seg_events = event_df[(event_df["timestamp"] >= start_ts) & (event_df["timestamp"] <= end_ts)].copy()

        if seg_state.empty:
            hedge_on_ratio = np.nan
            bearish_ratio = np.nan
            bearish_pos_net_ratio = np.nan
            avg_net_qty = np.nan
            avg_net_over_eq = np.nan
        else:
            bearish = seg_state["trend_4h_confirmed"] == "bearish"
            hedge_on_ratio = float((seg_state["hedge_qty"] > 0).mean() * 100.0)
            bearish_ratio = float(bearish.mean() * 100.0)
            bearish_pos_net_ratio = float(((bearish) & (seg_state["net_qty"] > 0)).mean() * 100.0)
            avg_net_qty = float(seg_state["net_qty"].mean())
            avg_net_over_eq = float(seg_state["net_notional_over_equity"].replace([np.inf, -np.inf], np.nan).mean())

        if seg_trades.empty:
            long_trades = 0
            short_trades = 0
            long_pnl = 0.0
            short_pnl = 0.0
            trend_change_trades = 0
            hedge_close_trades = 0
        else:
            long_trades = int((seg_trades["side"] == "LONG").sum())
            short_trades = int((seg_trades["side"] == "SHORT").sum())
            long_pnl = float(seg_trades.loc[seg_trades["side"] == "LONG", "pnl"].sum())
            short_pnl = float(seg_trades.loc[seg_trades["side"] == "SHORT", "pnl"].sum())
            trend_change_trades = int((seg_trades["reason"] == "Trend Change").sum())
            hedge_close_trades = int((seg_trades["reason"] == "Hedge Close Trend Up").sum())

        if seg_events.empty:
            stop_loss_trigger_events = 0
            stop_loss_readd_events = 0
            hedge_open_events = 0
            hedge_close_events = 0
        else:
            stop_loss_trigger_events = int((seg_events["event_type"] == "stop_loss_trigger").sum())
            stop_loss_readd_events = int((seg_events["event_type"] == "stop_loss_readd").sum())
            hedge_open_events = int((seg_events["event_type"] == "hedge_open").sum())
            hedge_close_events = int((seg_events["event_type"] == "hedge_close").sum())

        row = ep.to_dict()
        row.update(
            {
                "seg_long_trades": long_trades,
                "seg_short_trades": short_trades,
                "seg_long_pnl": long_pnl,
                "seg_short_pnl": short_pnl,
                "seg_stop_loss_trigger_events": stop_loss_trigger_events,
                "seg_stop_loss_readd_events": stop_loss_readd_events,
                "seg_trend_change_trades": trend_change_trades,
                "seg_hedge_close_trades": hedge_close_trades,
                "seg_hedge_open_events": hedge_open_events,
                "seg_hedge_close_events": hedge_close_events,
                "seg_hedge_on_ratio_pct": hedge_on_ratio,
                "seg_bearish_ratio_pct": bearish_ratio,
                "seg_bearish_positive_net_ratio_pct": bearish_pos_net_ratio,
                "seg_avg_net_qty": avg_net_qty,
                "seg_avg_net_notional_over_equity": avg_net_over_eq,
            }
        )
        rows.append(row)

    return pd.DataFrame(rows)


def build_reason_pnl(trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return pd.DataFrame()

    g = (
        trades_df.groupby(["side", "reason"], dropna=False)
        .agg(
            trades=("pnl", "count"),
            pnl_sum=("pnl", "sum"),
            avg_pnl=("pnl", "mean"),
            win_rate_pct=("pnl", lambda x: (x > 0).mean() * 100.0),
        )
        .reset_index()
    )
    return g.sort_values("pnl_sum", ascending=True).reset_index(drop=True)


def build_entry_quality(bt, trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return pd.DataFrame()
    if len(bt.entry_signals) == 0:
        return pd.DataFrame()

    entry_ctx = pd.DataFrame(bt.entry_signals).copy()
    entry_ctx["timestamp"] = pd.to_datetime(entry_ctx["timestamp"])
    entry_ctx = entry_ctx.sort_values("timestamp").drop_duplicates("timestamp", keep="last")

    long_trades = trades_df[trades_df["side"] == "LONG"][["entry_time", "pnl"]].copy()
    if long_trades.empty:
        return pd.DataFrame()

    merged = long_trades.merge(entry_ctx, left_on="entry_time", right_on="timestamp", how="left")
    merged["win"] = merged["pnl"] > 0

    out_rows = []

    def bucket_stats(df: pd.DataFrame, col: str, bins: list[float], labels: list[str], name: str):
        x = df.copy()
        x["bucket"] = pd.cut(x[col], bins=bins, labels=labels, include_lowest=True, right=False)
        g = (
            x.dropna(subset=["bucket"])
            .groupby("bucket", observed=True)
            .agg(
                trades=("pnl", "count"),
                win_rate_pct=("win", "mean"),
                avg_pnl=("pnl", "mean"),
                median_pnl=("pnl", "median"),
                pnl_sum=("pnl", "sum"),
            )
            .reset_index()
        )
        if g.empty:
            return
        g["win_rate_pct"] = g["win_rate_pct"] * 100.0
        g["dimension"] = name
        out_rows.append(g[["dimension", "bucket", "trades", "win_rate_pct", "avg_pnl", "median_pnl", "pnl_sum"]])

    bucket_stats(
        merged,
        "rsi",
        [0, 10, 15, 18, 22, 100],
        ["0-10", "10-15", "15-18", "18-22", "22+"],
        "RSI",
    )
    bucket_stats(
        merged,
        "adx",
        [0, 20, 30, 40, 60, 1e9],
        ["0-20", "20-30", "30-40", "40-60", "60+"],
        "ADX",
    )
    bucket_stats(
        merged,
        "ema_dist_pct",
        [0, 0.25, 0.5, 1.0, 2.0, 100],
        ["0-0.25%", "0.25-0.5%", "0.5-1.0%", "1.0-2.0%", "2.0%+"],
        "EMA_Distance",
    )

    if not out_rows:
        return pd.DataFrame()
    return pd.concat(out_rows, ignore_index=True)


def build_yearly_table(state_df: pd.DataFrame, trades_df: pd.DataFrame) -> pd.DataFrame:
    if state_df.empty:
        return pd.DataFrame()

    s = state_df.copy()
    s["year"] = s["timestamp"].dt.year
    rows = []
    for year, g in s.groupby("year"):
        eq = g["equity"].astype(float)
        start_eq = float(eq.iloc[0])
        end_eq = float(eq.iloc[-1])
        ret_pct = (end_eq / start_eq - 1.0) * 100.0 if start_eq != 0 else np.nan
        run_max = eq.cummax().replace(0, np.nan)
        dd_pct = (eq / run_max - 1.0) * 100.0
        mdd_pct = float(-dd_pct.min()) if len(dd_pct) else np.nan

        if trades_df.empty:
            t = pd.DataFrame()
        else:
            t = trades_df[trades_df["exit_time"].dt.year == year]

        if t.empty:
            trade_count = 0
            win_rate = np.nan
            long_pnl = 0.0
            short_pnl = 0.0
        else:
            trade_count = int(len(t))
            win_rate = float((t["pnl"] > 0).mean() * 100.0)
            long_pnl = float(t.loc[t["side"] == "LONG", "pnl"].sum())
            short_pnl = float(t.loc[t["side"] == "SHORT", "pnl"].sum())

        rows.append(
            {
                "year": int(year),
                "start_equity": start_eq,
                "end_equity": end_eq,
                "return_pct": ret_pct,
                "max_drawdown_pct": mdd_pct,
                "trades": trade_count,
                "win_rate_pct": win_rate,
                "long_pnl": long_pnl,
                "short_pnl": short_pnl,
            }
        )
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def build_exposure_summary(bt, state_df: pd.DataFrame) -> pd.DataFrame:
    if state_df.empty:
        return pd.DataFrame()

    bearish = state_df["trend_4h_confirmed"] == "bearish"
    bull = state_df["trend_4h_confirmed"] == "bullish"
    out = {
        "bars_total": int(len(state_df)),
        "hedge_on_ratio_pct": float((state_df["hedge_qty"] > 0).mean() * 100.0),
        "net_long_ratio_pct": float((state_df["net_qty"] > 0).mean() * 100.0),
        "net_short_ratio_pct": float((state_df["net_qty"] < 0).mean() * 100.0),
        "bearish_bars": int(bearish.sum()),
        "bullish_bars": int(bull.sum()),
        "bearish_hedge_on_ratio_pct": float(((state_df["hedge_qty"] > 0) & bearish).sum() / max(1, bearish.sum()) * 100.0),
        "bearish_positive_net_ratio_pct": float(((state_df["net_qty"] > 0) & bearish).sum() / max(1, bearish.sum()) * 100.0),
        "entry_condition_true": int(bt.signal_counters.get("entry_condition_true", 0)),
        "blocked_by_ema_touch": int(bt.signal_counters.get("blocked_by_ema_touch", 0)),
        "blocked_by_cooldown": int(bt.signal_counters.get("blocked_by_cooldown", 0)),
        "executed_long_entries": int(bt.signal_counters.get("executed_long_entries", 0)),
    }
    return pd.DataFrame([out])


def save_plot(state_df: pd.DataFrame, drawdowns_df: pd.DataFrame, yearly_df: pd.DataFrame):
    if state_df.empty:
        return

    plot_state = (
        state_df.set_index("timestamp")[["equity", "drawdown_pct", "net_notional_over_equity"]]
        .resample("1h")
        .last()
        .dropna()
        .reset_index()
    )

    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1.3])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("20 Diagnostics: Equity Curve with Top Drawdown Windows")
    ax_eq.plot(plot_state["timestamp"], plot_state["equity"], color="#1f77b4", linewidth=1.1, label="equity")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)

    for i, (_, row) in enumerate(drawdowns_df.head(3).iterrows(), start=1):
        start = row["peak_time"]
        end = row["recovery_time"] if pd.notna(row["recovery_time"]) else plot_state["timestamp"].iloc[-1]
        ax_eq.axvspan(start, end, color="#d62728", alpha=0.10)
        ax_eq.text(start, plot_state["equity"].max() * (0.98 - i * 0.03), f"DD#{int(row['episode_id'])}", fontsize=8)

    ax_dd = fig.add_subplot(gs[1, 0])
    ax_dd.set_title("Drawdown % (hourly sampled)")
    ax_dd.plot(plot_state["timestamp"], plot_state["drawdown_pct"], color="#d62728", linewidth=1.0)
    ax_dd.set_ylabel("Drawdown (%)")
    ax_dd.grid(True, alpha=0.2)

    ax_exp = fig.add_subplot(gs[1, 1])
    ax_exp.set_title("Net Notional / Equity (hourly sampled)")
    y = plot_state["net_notional_over_equity"].clip(-5, 5)
    ax_exp.plot(plot_state["timestamp"], y, color="#2ca02c", linewidth=1.0)
    ax_exp.set_ylabel("Net Notional / Equity")
    ax_exp.grid(True, alpha=0.2)

    if not yearly_df.empty:
        ax_yr = ax_exp.twinx()
        years = yearly_df["year"].astype(int).astype(str).tolist()
        ret = yearly_df["return_pct"].tolist()
        xpos = np.linspace(0.05, 0.95, len(years))
        for x, r, ylbl in zip(xpos, ret, years):
            ax_yr.text(x, 0.05, f"{ylbl}:{r:.1f}%", transform=ax_yr.transAxes, fontsize=8, ha="center", va="bottom")
        ax_yr.set_yticks([])

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
    plt.close()


def save_report(
    metrics: dict,
    drawdowns_df: pd.DataFrame,
    reason_df: pd.DataFrame,
    entry_df: pd.DataFrame,
    yearly_df: pd.DataFrame,
    exposure_df: pd.DataFrame,
):
    lines: list[str] = []
    lines.append("# 20 Diagnostics for 17 Best Case (`hys=0.50%`)")
    lines.append("")
    lines.append("## Scope")
    lines.append("- Strategy: same core logic as 17 (no-lookahead, raw data, fixed 5x trend hedge, long SL ON).")
    lines.append("- Goal: locate where losses cluster and identify high-impact improvement candidates.")
    lines.append("")
    lines.append("## Overall Metrics")
    lines.append("")
    lines.append("| Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {_fmt(metrics['final_equity'])} | {_fmt(metrics['total_return_pct'])} | {_fmt(metrics['cagr_pct'])} | "
        f"{_fmt(metrics['max_drawdown_pct'])} | {_fmt(metrics['calmar_ratio'])} | {int(metrics['trades'])} | "
        f"{int(metrics['long_trades'])}/{int(metrics['short_trades'])} | {_fmt(metrics['win_rate_pct'])} | {_fmt(metrics['profit_factor'])} |"
    )

    if not exposure_df.empty:
        ex = exposure_df.iloc[0]
        lines.append("")
        lines.append("## Exposure & Signal Counters")
        lines.append("")
        lines.append("| Item | Value |")
        lines.append("|---|---:|")
        lines.append(f"| Hedge On Ratio % | {_fmt(ex['hedge_on_ratio_pct'])} |")
        lines.append(f"| Bearish Positive Net Ratio % | {_fmt(ex['bearish_positive_net_ratio_pct'])} |")
        lines.append(f"| Entry Condition True | {int(ex['entry_condition_true'])} |")
        lines.append(f"| Blocked by EMA Touch | {int(ex['blocked_by_ema_touch'])} |")
        lines.append(f"| Blocked by Cooldown | {int(ex['blocked_by_cooldown'])} |")
        lines.append(f"| Executed Long Entries | {int(ex['executed_long_entries'])} |")

    if not drawdowns_df.empty:
        lines.append("")
        lines.append("## Top Drawdown Episodes")
        lines.append("")
        lines.append(
            "| ID | Peak Time | Trough Time | Recovery Time | MDD % | Days UW | Long PnL | Short PnL | SL Trg | SL ReAdd | HedgeOn % | Bear+NetLong % |"
        )
        lines.append("|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for _, r in drawdowns_df.head(TOP_DD).iterrows():
            rec = r["recovery_time"].strftime("%Y-%m-%d %H:%M") if pd.notna(r["recovery_time"]) else "N/A"
            lines.append(
                f"| {int(r['episode_id'])} | {r['peak_time'].strftime('%Y-%m-%d %H:%M')} | "
                f"{r['trough_time'].strftime('%Y-%m-%d %H:%M')} | {rec} | {_fmt(r['max_drawdown_pct'])} | "
                f"{_fmt(r['days_underwater'])} | {_fmt(r['seg_long_pnl'])} | {_fmt(r['seg_short_pnl'])} | "
                f"{int(r['seg_stop_loss_trigger_events'])} | {int(r['seg_stop_loss_readd_events'])} | "
                f"{_fmt(r['seg_hedge_on_ratio_pct'])} | {_fmt(r['seg_bearish_positive_net_ratio_pct'])} |"
            )

    if not reason_df.empty:
        lines.append("")
        lines.append("## PnL by Side/Reason (Worst to Best)")
        lines.append("")
        lines.append("| Side | Reason | Trades | PnL Sum | Avg PnL | Win Rate % |")
        lines.append("|---|---|---:|---:|---:|---:|")
        for _, r in reason_df.head(12).iterrows():
            lines.append(
                f"| {r['side']} | {r['reason']} | {int(r['trades'])} | {_fmt(r['pnl_sum'])} | {_fmt(r['avg_pnl'])} | {_fmt(r['win_rate_pct'])} |"
            )

    if not entry_df.empty:
        lines.append("")
        lines.append("## Entry Quality Buckets")
        lines.append("")
        lines.append("| Dimension | Bucket | Trades | Win Rate % | Avg PnL | PnL Sum |")
        lines.append("|---|---|---:|---:|---:|---:|")
        for _, r in entry_df.iterrows():
            lines.append(
                f"| {r['dimension']} | {r['bucket']} | {int(r['trades'])} | {_fmt(r['win_rate_pct'])} | "
                f"{_fmt(r['avg_pnl'])} | {_fmt(r['pnl_sum'])} |"
            )

    if not yearly_df.empty:
        lines.append("")
        lines.append("## Yearly Stability")
        lines.append("")
        lines.append("| Year | Return % | MDD % | Trades | Win Rate % | Long PnL | Short PnL |")
        lines.append("|---:|---:|---:|---:|---:|---:|---:|")
        for _, r in yearly_df.iterrows():
            lines.append(
                f"| {int(r['year'])} | {_fmt(r['return_pct'])} | {_fmt(r['max_drawdown_pct'])} | "
                f"{int(r['trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['long_pnl'])} | {_fmt(r['short_pnl'])} |"
            )

    lines.append("")
    lines.append("## Improvement Focus (for next case study)")
    if not exposure_df.empty and float(exposure_df.iloc[0]["bearish_positive_net_ratio_pct"]) <= 1.0:
        lines.append("- Directional downside under bearish 4h appears mostly neutralized (`Bear+NetLong %` near zero).")
    else:
        lines.append("- First priority: reduce bullish net exposure while `trend_4h_confirmed` is bearish.")
    if not reason_df.empty:
        worst = reason_df.iloc[0]
        lines.append(
            f"- Largest negative bucket is `{worst['side']} / {worst['reason']}` "
            f"(PnL `{_fmt(worst['pnl_sum'])}` across {int(worst['trades'])} trades)."
        )
    if not drawdowns_df.empty:
        top_ep = drawdowns_df.iloc[0]
        lines.append(
            f"- In worst DD window, stop-loss trigger/readd counts were "
            f"{int(top_ep['seg_stop_loss_trigger_events'])}/{int(top_ep['seg_stop_loss_readd_events'])}."
        )
    lines.append("- Add/adjust entry filters only where bucket-level expectancy is weak, then re-check yearly split.")
    lines.append("")
    lines.append("## Output Files")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{METRICS_FILE}`")
    lines.append(f"- drawdowns: `{DRAWDOWN_FILE}`")
    lines.append(f"- reason pnl: `{REASON_FILE}`")
    lines.append(f"- entry quality: `{ENTRY_FILE}`")
    lines.append(f"- yearly: `{YEARLY_FILE}`")
    lines.append(f"- exposure: `{EXPOSURE_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_20", BASE_002_PATH)
    helper_module = load_module("m04_20", BASE_04_PATH)

    bt_cls = build_diag_class(base_module, helper_module)
    bt = bt_cls(
        symbol=base_module.SYMBOL,
        initial_capital=base_module.INITIAL_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=base_module.ENTRY_SCALE,
    )
    helper_module.configure_baseline_params(bt)

    df_1m, df_4h = load_data_no_filter(base_module)
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()
    bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

    metrics = helper_module.calculate_metrics(bt, base_module.INITIAL_CAPITAL)
    metrics_df = pd.DataFrame([metrics])
    metrics_df.to_csv(METRICS_FILE, index=False)

    _, trades_df, state_df, event_df = to_df(bt)
    dd_df = build_drawdown_episodes(state_df)
    dd_annot_df = annotate_drawdown_episodes(dd_df, trades_df, state_df, event_df)
    reason_df = build_reason_pnl(trades_df)
    entry_df = build_entry_quality(bt, trades_df)
    yearly_df = build_yearly_table(state_df, trades_df)
    exposure_df = build_exposure_summary(bt, state_df)

    dd_annot_df.to_csv(DRAWDOWN_FILE, index=False)
    reason_df.to_csv(REASON_FILE, index=False)
    entry_df.to_csv(ENTRY_FILE, index=False)
    yearly_df.to_csv(YEARLY_FILE, index=False)
    exposure_df.to_csv(EXPOSURE_FILE, index=False)

    save_plot(state_df, dd_annot_df, yearly_df)
    save_report(metrics, dd_annot_df, reason_df, entry_df, yearly_df, exposure_df)

    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_report={MD_FILE}")
    print(f"saved_metrics={METRICS_FILE}")
    print(f"saved_drawdowns={DRAWDOWN_FILE}")
    print(f"saved_reason={REASON_FILE}")
    print(f"saved_entry={ENTRY_FILE}")
    print(f"saved_yearly={YEARLY_FILE}")
    print(f"saved_exposure={EXPOSURE_FILE}")
    print(metrics_df.to_string(index=False))
    if not dd_annot_df.empty:
        show_cols = [
            "episode_id",
            "max_drawdown_pct",
            "peak_time",
            "trough_time",
            "recovery_time",
            "seg_long_pnl",
            "seg_short_pnl",
            "seg_stop_loss_trigger_events",
            "seg_stop_loss_readd_events",
        ]
        print(dd_annot_df[show_cols].head(TOP_DD).to_string(index=False))


if __name__ == "__main__":
    run()
