from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")

PLOT_FILE = Path("07_backtest_btcusdt_fixed5x_hysteresis_compare.png")
CSV_FILE = Path("07_backtest_btcusdt_fixed5x_hysteresis_compare.csv")
MD_FILE = Path("07_backtest_btcusdt_fixed5x_hysteresis_compare.md")

MODE_BASE_04 = "hedge_fixed_base5x_04"
MODE_HYST_ONLY = "hedge_fixed_base5x_plus_4h_hysteresis"
MODES = [MODE_BASE_04, MODE_HYST_ONLY]

HYSTERESIS_PCT = 0.002  # 0.2%


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

    class FixedBase5xWithHysteresis(BaseHedgeCls):
        """
        Keep 04 fixed-base5x hedge sizing, but use 4h hysteresis for hedge trend confirmation.
        No look-ahead: use previous closed 4h state via shift(1).
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
                    # Keep previous state within band to reduce flip-flop.
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

    return BaseHedgeCls, FixedBase5xWithHysteresis


def create_bt(base_module, helper_module, mode, cls_base, cls_hyst):
    if mode == MODE_BASE_04:
        cls = cls_base
    elif mode == MODE_HYST_ONLY:
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
        MODE_HYST_ONLY: "#2ca02c",
    }

    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("07 Fixed Base5x Hedge vs Hysteresis-Only")
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
    hyst = metrics_df[metrics_df["mode"] == MODE_HYST_ONLY].iloc[0]

    eq_delta = (hyst["final_equity"] / base["final_equity"] - 1.0) * 100.0
    mdd_delta = hyst["max_drawdown_pct"] - base["max_drawdown_pct"]
    trades_delta = int(hyst["trades"] - base["trades"])

    lines = []
    lines.append("# 07 Fixed Base5x + Hysteresis-Only Test")
    lines.append("")
    lines.append("## Tested Modes")
    lines.append(f"- `{MODE_BASE_04}`: current 04 successful hedge (fixed `base_qty * 5`)")
    lines.append(
        f"- `{MODE_HYST_ONLY}`: fixed `base_qty * 5` hedge unchanged, "
        f"only 4h EMA200 hysteresis added (band +/-{HYSTERESIS_PCT * 100:.2f}%)"
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
    lines.append("## Delta vs Baseline")
    lines.append("")
    lines.append(f"- Final Equity Delta: {_fmt(eq_delta)}%")
    lines.append(f"- MDD Delta: {_fmt(mdd_delta)}%p")
    lines.append(f"- Trades Delta: {trades_delta:+d}")
    lines.append("")
    lines.append("## Output Files")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{CSV_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002", BASE_002_PATH)
    helper_module = load_module("m04", BASE_04_PATH)
    cls_base, cls_hyst = build_classes(base_module, helper_module)

    df_1m, df_4h = base_module.load_data()
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    rows = []
    eq_map: dict[str, pd.DataFrame] = {}

    for mode in MODES:
        bt = create_bt(base_module, helper_module, mode, cls_base, cls_hyst)
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
