from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")

PLOT_FILE = Path("06_backtest_btcusdt_hedge_size_hysteresis_compare.png")
CSV_FILE = Path("06_backtest_btcusdt_hedge_size_hysteresis_compare.csv")
MD_FILE = Path("06_backtest_btcusdt_hedge_size_hysteresis_compare.md")

MODE_BASE_04 = "hedge_fixed_base5x_04"
MODE_DYNAMIC = "hedge_dynamic_linked_to_long_qty"
MODE_DYNAMIC_HYST = "hedge_dynamic_linked_plus_4h_hysteresis"
MODES = [MODE_BASE_04, MODE_DYNAMIC, MODE_DYNAMIC_HYST]

HYSTERESIS_PCT = 0.002  # 0.2%
HEDGE_RATIO_TO_LONG = 1.0


def load_module(alias: str, path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing script: {path}")
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_classes(base_module, helper_module):
    _, BaseHedgeCls = helper_module.build_mode_classes(base_module)

    class DynamicLinkedHedge(BaseHedgeCls):
        """
        Hedge quantity follows current long quantity without forced downsizing.

        Rules under confirmed bearish:
        - If hedge < target(long_qty * ratio): increase hedge.
        - If hedge >= target: keep hedge as is (do not reduce).
        Hedge is reduced only when confirmed trend flips bullish (original close logic).
        """

        hedge_size_ratio = HEDGE_RATIO_TO_LONG
        rebalance_tol = 1e-12

        def _open_hedge_short(self, price, timestamp, hedge_qty: float | None = None):
            if self.hedge_position is not None:
                return
            if hedge_qty is None:
                if not self.current_position or self.current_position["side"] != "LONG":
                    return
                long_qty = float(self.current_position["quantity"])
                hedge_qty = long_qty * self.hedge_size_ratio
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

        def _increase_hedge_short(self, price, add_qty: float):
            if self.hedge_position is None or add_qty <= self.rebalance_tol:
                return

            pos = self.hedge_position
            position_value = add_qty * price
            commission = position_value * self.commission
            total_qty = pos["quantity"] + add_qty
            new_avg = (pos["avg_entry"] * pos["quantity"] + price * add_qty) / total_qty

            pos["avg_entry"] = new_avg
            pos["quantity"] = total_qty
            pos["total_commission"] += commission
            self.capital -= commission

        def _manage_trend_hedge(self, confirmed_trend_4h, price, timestamp, is_new_4h_bucket):
            has_long = bool(self.current_position and self.current_position["side"] == "LONG")
            target_qty = float(self.current_position["quantity"] * self.hedge_size_ratio) if has_long else 0.0
            current_qty = float(self.hedge_position["quantity"]) if self.hedge_position is not None else 0.0

            if confirmed_trend_4h == "bullish":
                if self.hedge_position is not None:
                    self._close_hedge_short(price, timestamp, "Hedge Close Trend Up")
                return

            if confirmed_trend_4h != "bearish":
                return

            if target_qty <= self.rebalance_tol:
                # Do not shrink hedge in bearish regime when long reduces/disappears.
                return

            if self.hedge_position is None:
                self._open_hedge_short(price, timestamp, hedge_qty=target_qty)
                return

            if target_qty > current_qty + self.rebalance_tol:
                add_qty = target_qty - current_qty
                self._increase_hedge_short(price, add_qty)

    class DynamicLinkedHedgeWithHysteresis(DynamicLinkedHedge):
        """
        Dynamic long-linked hedge + 4h hysteresis confirmation.
        No look-ahead: use previous closed 4h state for current 4h bucket.
        """

        hysteresis_pct = HYSTERESIS_PCT

        @staticmethod
        def _compute_hysteresis_state(df_4h: pd.DataFrame, hysteresis_pct: float) -> pd.Series:
            state: list[str | float] = []
            prev_state: str | None = None

            for _, row in df_4h.iterrows():
                ema = row["ema200"]
                close = row["close"]

                if pd.isna(ema) or pd.isna(close):
                    state.append(np.nan)
                    continue

                upper = ema * (1.0 + hysteresis_pct)
                lower = ema * (1.0 - hysteresis_pct)

                if close > upper:
                    current = "bullish"
                elif close < lower:
                    current = "bearish"
                else:
                    # Inside band: keep previous state to avoid flip-flop.
                    if prev_state is None:
                        current = "bullish" if close > ema else "bearish"
                    else:
                        current = prev_state

                state.append(current)
                prev_state = current

            return pd.Series(state, index=df_4h.index)

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
            out_4h["trend_4h_hyst"] = self._compute_hysteresis_state(out_4h, self.hysteresis_pct)
            # no look-ahead: current bucket uses prior closed 4h state
            out_4h["trend_4h_confirmed"] = out_4h["trend_4h_hyst"].shift(1)

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

    return BaseHedgeCls, DynamicLinkedHedge, DynamicLinkedHedgeWithHysteresis


def create_bt(base_module, helper_module, mode, cls_base, cls_dynamic, cls_hyst):
    if mode == MODE_BASE_04:
        cls = cls_base
    elif mode == MODE_DYNAMIC:
        cls = cls_dynamic
    elif mode == MODE_DYNAMIC_HYST:
        cls = cls_hyst
    else:
        raise ValueError(mode)

    bt = cls(
        symbol=base_module.SYMBOL,
        initial_capital=base_module.INITIAL_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=base_module.ENTRY_SCALE,
    )
    helper_module.configure_baseline_params(bt)
    return bt


def save_plot(equity_curves: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    color_map = {
        MODE_BASE_04: "#1f77b4",
        MODE_DYNAMIC: "#ff7f0e",
        MODE_DYNAMIC_HYST: "#2ca02c",
    }

    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("06 Hedge Variant Comparison")
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
    ax_final.tick_params(axis="x", rotation=15)
    ax_final.set_ylabel("USDT")
    ax_final.grid(True, axis="y", alpha=0.2)

    ax_mdd = fig.add_subplot(gs[1, 1])
    ax_mdd.set_title("Max Drawdown")
    ax_mdd.bar(metrics_df["mode"], metrics_df["max_drawdown_pct"], color=[color_map[m] for m in metrics_df["mode"]])
    ax_mdd.tick_params(axis="x", rotation=15)
    ax_mdd.set_ylabel("%")
    ax_mdd.grid(True, axis="y", alpha=0.2)

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
    plt.close()


def _fmt(v, digits=4):
    if pd.isna(v):
        return "N/A"
    return f"{v:.{digits}f}"


def save_report(metrics_df: pd.DataFrame):
    base = metrics_df[metrics_df["mode"] == MODE_BASE_04].iloc[0]
    d1 = metrics_df[metrics_df["mode"] == MODE_DYNAMIC].iloc[0]
    d2 = metrics_df[metrics_df["mode"] == MODE_DYNAMIC_HYST].iloc[0]

    def delta_row(r):
        return (
            (r["final_equity"] / base["final_equity"] - 1.0) * 100.0,
            r["max_drawdown_pct"] - base["max_drawdown_pct"],
            int(r["trades"] - base["trades"]),
        )

    d1_eq, d1_mdd, d1_tr = delta_row(d1)
    d2_eq, d2_mdd, d2_tr = delta_row(d2)

    lines = []
    lines.append("# 06 Hedge Size / Hysteresis Experiment")
    lines.append("")
    lines.append("## Tested Modes")
    lines.append(f"- `{MODE_BASE_04}`: current 04 successful hedge (fixed `base_qty * 5`)")
    lines.append(
        f"- `{MODE_DYNAMIC}`: hedge size linked to current long quantity (`long_qty * {HEDGE_RATIO_TO_LONG:.1f}`), "
        "under confirmed bearish, hedge never shrinks and only increases when needed"
    )
    lines.append(
        f"- `{MODE_DYNAMIC_HYST}`: mode 2 + 4h EMA200 hysteresis (band +/-{HYSTERESIS_PCT * 100:.2f}%), "
        "confirmed with previous closed 4h state"
    )
    lines.append("")
    lines.append("## Performance")
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
    lines.append("## Delta vs 04 Baseline")
    lines.append("")
    lines.append("| Mode | Final Equity Delta % | MDD Delta %p | Trades Delta |")
    lines.append("|---|---:|---:|---:|")
    lines.append(f"| `{MODE_DYNAMIC}` | {_fmt(d1_eq)} | {_fmt(d1_mdd)} | {d1_tr:+d} |")
    lines.append(f"| `{MODE_DYNAMIC_HYST}` | {_fmt(d2_eq)} | {_fmt(d2_mdd)} | {d2_tr:+d} |")
    lines.append("")
    lines.append("## Output Files")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{CSV_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002", BASE_002_PATH)
    helper_module = load_module("m04", BASE_04_PATH)
    cls_base, cls_dynamic, cls_hyst = build_classes(base_module, helper_module)

    df_1m, df_4h = base_module.load_data()
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    rows = []
    eq_map: dict[str, pd.DataFrame] = {}

    for mode in MODES:
        bt = create_bt(base_module, helper_module, mode, cls_base, cls_dynamic, cls_hyst)
        bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

        m = helper_module.calculate_metrics(bt, base_module.INITIAL_CAPITAL)
        m["mode"] = mode
        rows.append(m)

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            eq_map[mode] = eq[["timestamp", "equity"]].copy()
        else:
            eq_map[mode] = pd.DataFrame(columns=["timestamp", "equity"])

    order = {m: i for i, m in enumerate(MODES)}
    metrics_df = pd.DataFrame(rows).sort_values(by="mode", key=lambda s: s.map(order)).reset_index(drop=True)

    save_plot(eq_map, metrics_df)
    metrics_df.to_csv(CSV_FILE, index=False)
    save_report(metrics_df)

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
