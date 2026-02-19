from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")

PLOT_FILE = Path("19_backtest_btcusdt_touch_window_next_open_sweep.png")
CSV_FILE = Path("19_backtest_btcusdt_touch_window_next_open_sweep.csv")
MD_FILE = Path("19_backtest_btcusdt_touch_window_next_open_sweep.md")

HYSTERESIS_BAND = 0.005
TOUCH_WINDOWS = [1, 2, 3, 4, 5, 6]


@dataclass(frozen=True)
class SweepCase:
    touch_window: int

    @property
    def mode(self) -> str:
        return f"touch_last_{self.touch_window}_4h"


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


def build_case_class(base_module, helper_module, touch_window: int):
    _, BaseHedgeCls = helper_module.build_mode_classes(base_module)

    class FixedBase5xHystTouchWindowNextOpen(BaseHedgeCls):
        hysteresis = float(HYSTERESIS_BAND)
        touch_window_n = int(touch_window)

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
            out_4h["ema_touch_recent"] = (
                out_4h["ema_touch_raw"].astype(int).rolling(window=self.touch_window_n, min_periods=1).max().astype(bool)
            )
            out_4h["ema_touch_confirmed"] = out_4h["ema_touch_recent"].shift(1).fillna(False)
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

            pending_long_entry_adx: float | None = None

            for i in range(200, len(out_1m)):
                row = out_1m.iloc[i]
                timestamp = row.name
                open_price = float(row["open"])
                close_price = float(row["close"])
                rsi = row["rsi"]
                adx = row["adx"]
                trend = row["trend"]
                ema_touch = bool(row["ema_touch"])
                ema_val = row["ema200"]
                confirmed_trend_4h = row["trend_4h_confirmed"]
                is_new_4h_bucket = bool(row["is_new_4h_bucket"])

                # Entry-only next-open execution: execute signal from previous bar at current open.
                if pending_long_entry_adx is not None:
                    self._process_long_entry(open_price, timestamp, pending_long_entry_adx, i)
                    pending_long_entry_adx = None

                if pd.isna(rsi) or pd.isna(adx) or pd.isna(ema_val):
                    self._record_equity(close_price, timestamp, float(ema_val) if pd.notna(ema_val) else 0.0)
                    continue

                current_time = i
                time_since_last = current_time - self.last_order_time

                self._check_trend_change(trend, close_price, timestamp, float(ema_val))
                self._check_stop_loss(close_price, timestamp)
                self._manage_trend_hedge(confirmed_trend_4h, close_price, timestamp, is_new_4h_bucket)

                if pending_long_entry_adx is None and (not ema_touch) and time_since_last >= self.cooldown_time:
                    if rsi <= self.rsi_oversold and trend == "bullish":
                        pending_long_entry_adx = float(adx)

                self._check_take_profit(close_price, timestamp)
                self._record_equity(close_price, timestamp, float(ema_val))

            if self.current_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_timestamp = out_1m.index[-1]
                self._close_position(last_price, last_timestamp, "Final Close")

            if self.hedge_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_timestamp = out_1m.index[-1]
                self._close_hedge_short(last_price, last_timestamp, "Final Hedge Close")
                self._record_equity(last_price, last_timestamp, float(out_1m["ema200"].iloc[-1]))

    return FixedBase5xHystTouchWindowNextOpen


def save_plot(equity_curves: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    cmap = plt.get_cmap("viridis")
    modes = metrics_df["mode"].tolist()
    colors = {mode: cmap(i / max(1, len(modes) - 1)) for i, mode in enumerate(modes)}

    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("19 Touch Window Sweep (Entry Next-Open Only, hys=0.50%)")
    ax_eq.set_ylabel("Equity (USDT)")
    for mode in modes:
        eq = equity_curves.get(mode)
        if eq is None or eq.empty:
            continue
        ax_eq.plot(eq["timestamp"], eq["equity"], linewidth=1.1, label=mode, color=colors[mode])
    ax_eq.legend(loc="upper left", ncol=2)
    ax_eq.grid(True, alpha=0.2)

    ax_final = fig.add_subplot(gs[1, 0])
    ax_final.set_title("Final Equity by Touch Window")
    ax_final.bar(metrics_df["touch_window"], metrics_df["final_equity"], color=[colors[m] for m in modes])
    ax_final.set_xlabel("N (lookback 4h candles)")
    ax_final.set_ylabel("USDT")
    ax_final.grid(True, axis="y", alpha=0.2)

    ax_mdd = fig.add_subplot(gs[1, 1])
    ax_mdd.set_title("MDD by Touch Window")
    ax_mdd.bar(metrics_df["touch_window"], metrics_df["max_drawdown_pct"], color=[colors[m] for m in modes])
    ax_mdd.set_xlabel("N (lookback 4h candles)")
    ax_mdd.set_ylabel("MDD (%)")
    ax_mdd.grid(True, axis="y", alpha=0.2)

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
    plt.close()


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{v:.{digits}f}"


def save_report(metrics_df: pd.DataFrame):
    best_equity = metrics_df.sort_values("final_equity", ascending=False).iloc[0]
    best_calmar = metrics_df.sort_values("calmar_ratio", ascending=False).iloc[0]
    best_mdd = metrics_df.sort_values("max_drawdown_pct", ascending=True).iloc[0]

    lines: list[str] = []
    lines.append("# 19 Touch Window Case Study (`-1` to `-6`) with Entry-Only Next-Open")
    lines.append("")
    lines.append("## Objective")
    lines.append("- Compare entry filter variants: block long entry if any of last N confirmed 4h candles touched 4h EMA200.")
    lines.append("- N sweep: `1, 2, 3, 4, 5, 6`.")
    lines.append("- Keep long stop-loss ON.")
    lines.append("- Execute long entries at next 1m open.")
    lines.append("- Keep stop-loss / take-profit / trend-close / hedge open-close on signal close.")
    lines.append("- Keep fixed hedge strategy from 17 (hysteresis `0.50%`, 4h confirmed trend hedge).")
    lines.append("")
    lines.append("## Logic")
    lines.append("- `ema_touch_raw`: `high >= ema200 and low <= ema200` on 4h.")
    lines.append("- `ema_touch_recent_n`: rolling-any over last `N` 4h candles.")
    lines.append("- `ema_touch_confirmed`: `ema_touch_recent_n.shift(1)` for no look-ahead.")
    lines.append("- 1m long entry condition uses `not ema_touch_confirmed` as gate.")
    lines.append("- Entry timing only: signal at close `t`, execution at open `t+1`.")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| N | Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| {int(r['touch_window'])} | `{r['mode']}` | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | "
            f"{_fmt(r['cagr_pct'])} | {_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} |"
        )

    lines.append("")
    lines.append("## Best Cases")
    lines.append(
        f"- Best Final Equity: `N={int(best_equity['touch_window'])}` (`{_fmt(best_equity['final_equity'])}` USDT, "
        f"return `{_fmt(best_equity['total_return_pct'])}%`)."
    )
    lines.append(
        f"- Best Calmar: `N={int(best_calmar['touch_window'])}` (Calmar `{_fmt(best_calmar['calmar_ratio'])}`, "
        f"MDD `{_fmt(best_calmar['max_drawdown_pct'])}%`)."
    )
    lines.append(
        f"- Lowest MDD: `N={int(best_mdd['touch_window'])}` (MDD `{_fmt(best_mdd['max_drawdown_pct'])}%`, "
        f"Final Equity `{_fmt(best_mdd['final_equity'])}` USDT)."
    )
    lines.append("")
    lines.append("## Output Files")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{CSV_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_19", BASE_002_PATH)
    helper_module = load_module("m04_19", BASE_04_PATH)

    df_1m, df_4h = load_data_no_filter(base_module)
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    rows = []
    equity_map: dict[str, pd.DataFrame] = {}

    cases = [SweepCase(touch_window=n) for n in TOUCH_WINDOWS]
    for case in cases:
        cls = build_case_class(base_module, helper_module, case.touch_window)
        bt = cls(
            symbol=base_module.SYMBOL,
            initial_capital=base_module.INITIAL_CAPITAL,
            commission=base_module.COMMISSION,
            entry_scale=base_module.ENTRY_SCALE,
        )
        helper_module.configure_baseline_params(bt)
        bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

        metrics = helper_module.calculate_metrics(bt, base_module.INITIAL_CAPITAL)
        metrics["touch_window"] = case.touch_window
        metrics["mode"] = case.mode
        rows.append(metrics)

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            equity_map[case.mode] = eq[["timestamp", "equity"]].copy()
        else:
            equity_map[case.mode] = pd.DataFrame(columns=["timestamp", "equity"])

    metrics_df = pd.DataFrame(rows).sort_values("touch_window").reset_index(drop=True)
    save_plot(equity_map, metrics_df)
    metrics_df.to_csv(CSV_FILE, index=False)
    save_report(metrics_df)

    show_cols = [
        "touch_window",
        "mode",
        "final_equity",
        "total_return_pct",
        "cagr_pct",
        "max_drawdown_pct",
        "calmar_ratio",
        "trades",
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
