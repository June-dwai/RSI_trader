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

PLOT_FILE = Path("22_backtest_btcusdt_dd_scale_entryscale_sweep.png")
CSV_FILE = Path("22_backtest_btcusdt_dd_scale_entryscale_sweep.csv")
MD_FILE = Path("22_backtest_btcusdt_dd_scale_entryscale_sweep.md")

HYSTERESIS_BAND = 0.005
ENTRY_SCALES = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


@dataclass(frozen=True)
class SweepCase:
    entry_scale: float
    dynamic_dd_scale: bool

    @property
    def mode(self) -> str:
        prefix = "dd_scaled" if self.dynamic_dd_scale else "baseline"
        return f"{prefix}_es{self.entry_scale:.1f}"


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


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{v:.{digits}f}"


def build_case_class(base_module, helper_module, dynamic_dd_scale: bool):
    _, BaseHedgeCls = helper_module.build_mode_classes(base_module)

    class FixedBase5xWithHysteresisDDScale(BaseHedgeCls):
        hysteresis = float(HYSTERESIS_BAND)
        use_dynamic_dd_scale = bool(dynamic_dd_scale)

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

        def _compute_live_equity(self, price: float) -> float:
            equity = float(self.capital)
            if self.current_position:
                pos = self.current_position
                if pos["side"] == "LONG":
                    equity += (price - float(pos["avg_entry"])) * float(pos["quantity"])
                else:
                    equity += (float(pos["avg_entry"]) - price) * float(pos["quantity"])
            if self.hedge_position:
                hedge = self.hedge_position
                equity += (float(hedge["avg_entry"]) - price) * float(hedge["quantity"])
            return equity

        def _get_position_scale(self, current_drawdown: float) -> float:
            if not self.use_dynamic_dd_scale:
                return 1.0
            if current_drawdown > 0.50:
                return 0.25
            if current_drawdown > 0.25:
                return 0.5
            return 1.0

        def _process_long_entry_with_scale(self, price, timestamp, adx, current_time, position_scale: float):
            if not self.current_position:
                if self.capital <= 0:
                    return
                qty = (self.capital / price) * float(position_scale)
                if qty <= 0:
                    return
                self._open_position("LONG", price, timestamp, qty)
                self.last_order_time = current_time
                self.recent_trade = [price, "LONG"]
                self._update_cooldown("LONG")

            elif self.current_position["side"] == "LONG":
                if price <= self.recent_trade[0] * 0.995:
                    mult = self._get_adx_multiplier(adx)
                    if mult > 0:
                        qty = self.position_quantity * mult
                        self._add_to_position(price, timestamp, qty, adx)
                        self.last_order_time = current_time
                        self.recent_trade = [price, "LONG"]
                        self._update_cooldown("LONG")

            elif self.current_position["side"] == "SHORT":
                close_qty = self.current_position["quantity"] * 0.8
                self._partial_close(price, timestamp, close_qty, "Reverse")
                if self.capital <= 0:
                    return
                qty = self.capital / price
                self._open_position("LONG", price, timestamp, qty)
                self.last_order_time = current_time
                self.recent_trade = [price, "LONG"]
                self._update_cooldown("LONG")

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

            self.scale_entry_log: list[dict] = []
            self._equity_peak = float(self.initial_capital)

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

                live_equity = self._compute_live_equity(price)
                if live_equity > self._equity_peak:
                    self._equity_peak = live_equity
                current_drawdown = 0.0 if self._equity_peak <= 0 else max(0.0, (self._equity_peak - live_equity) / self._equity_peak)
                position_scale = self._get_position_scale(current_drawdown)

                if (not ema_touch) and time_since_last >= self.cooldown_time:
                    if rsi <= self.rsi_oversold and trend == "bullish":
                        prev_last_order_time = self.last_order_time
                        self._process_long_entry_with_scale(price, timestamp, float(adx), current_time, position_scale)
                        if self.last_order_time != prev_last_order_time:
                            self.scale_entry_log.append(
                                {
                                    "timestamp": timestamp,
                                    "drawdown_pct": current_drawdown * 100.0,
                                    "position_scale": float(position_scale),
                                    "price": price,
                                }
                            )

                self._check_take_profit(price, timestamp)
                self._record_equity(price, timestamp, float(ema_val))
                if self.equity_curve:
                    eq_val = float(self.equity_curve[-1]["equity"])
                    if eq_val > self._equity_peak:
                        self._equity_peak = eq_val

            if self.current_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_timestamp = out_1m.index[-1]
                self._close_position(last_price, last_timestamp, "Final Close")

            if self.hedge_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_timestamp = out_1m.index[-1]
                self._close_hedge_short(last_price, last_timestamp, "Final Hedge Close")
                self._record_equity(last_price, last_timestamp, float(out_1m["ema200"].iloc[-1]))

    return FixedBase5xWithHysteresisDDScale


def summarize_scale_usage(entry_log_df: pd.DataFrame) -> dict:
    if entry_log_df.empty:
        return {
            "entries_scaled_total": 0,
            "scale_1_0_entries": 0,
            "scale_0_5_entries": 0,
            "scale_0_25_entries": 0,
            "avg_entry_scale": np.nan,
            "avg_entry_drawdown_pct": np.nan,
        }

    s = entry_log_df["position_scale"].astype(float)
    return {
        "entries_scaled_total": int(len(entry_log_df)),
        "scale_1_0_entries": int((s == 1.0).sum()),
        "scale_0_5_entries": int((s == 0.5).sum()),
        "scale_0_25_entries": int((s == 0.25).sum()),
        "avg_entry_scale": float(s.mean()),
        "avg_entry_drawdown_pct": float(entry_log_df["drawdown_pct"].astype(float).mean()),
    }


def save_plot(equity_curves: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    piv_eq = metrics_df.pivot(index="entry_scale", columns="mode_group", values="final_equity").sort_index()
    piv_mdd = metrics_df.pivot(index="entry_scale", columns="mode_group", values="max_drawdown_pct").sort_index()

    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[2.2, 1.0])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("22 Equity Curves by Mode (Time Axis)")
    ax_eq.set_ylabel("Equity (USDT)")

    cmap = plt.get_cmap("tab20")
    modes = metrics_df["mode"].tolist()
    colors = {m: cmap(i % 20) for i, m in enumerate(modes)}
    for mode in modes:
        eq = equity_curves.get(mode)
        if eq is None or eq.empty:
            continue
        ls = "--" if mode.startswith("dd_scaled") else "-"
        ax_eq.plot(eq["timestamp"], eq["equity"], linewidth=1.0, linestyle=ls, label=mode, color=colors[mode])
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2, fontsize=8)

    ax1 = fig.add_subplot(gs[1, 0])
    if "baseline" in piv_eq.columns:
        ax1.plot(piv_eq.index, piv_eq["baseline"], marker="o", label="baseline")
    if "dd_scaled" in piv_eq.columns:
        ax1.plot(piv_eq.index, piv_eq["dd_scaled"], marker="o", label="dd_scaled")
    ax1.set_title("Final Equity by entry_scale")
    ax1.set_xlabel("entry_scale")
    ax1.set_ylabel("Final Equity (USDT)")
    ax1.grid(True, alpha=0.2)
    ax1.legend(loc="best")

    ax2 = fig.add_subplot(gs[1, 1])
    if "baseline" in piv_mdd.columns:
        ax2.plot(piv_mdd.index, piv_mdd["baseline"], marker="o", label="baseline")
    if "dd_scaled" in piv_mdd.columns:
        ax2.plot(piv_mdd.index, piv_mdd["dd_scaled"], marker="o", label="dd_scaled")
    ax2.set_title("Max Drawdown by entry_scale")
    ax2.set_xlabel("entry_scale")
    ax2.set_ylabel("MDD (%)")
    ax2.grid(True, alpha=0.2)
    ax2.legend(loc="best")

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
    plt.close()


def save_report(metrics_df: pd.DataFrame):
    lines: list[str] = []
    lines.append("# 22 DD-Scale + Entry Scale Sweep")
    lines.append("")
    lines.append("## Objective")
    lines.append("- Sweep `entry_scale` values: `0.3, 0.4, 0.5, 0.6, 0.7, 0.8`.")
    lines.append("- Compare two modes at each scale:")
    lines.append("  1) `baseline` (no dd scale)")
    lines.append("  2) `dd_scaled` with drawdown scaling")
    lines.append("")
    lines.append("## DD Scale Rule")
    lines.append("```python")
    lines.append("if current_drawdown > 0.50:")
    lines.append("    position_scale = 0.25")
    lines.append("elif current_drawdown > 0.25:")
    lines.append("    position_scale = 0.5")
    lines.append("else:")
    lines.append("    position_scale = 1.0")
    lines.append("```")
    lines.append("")
    lines.append("## Full Results")
    lines.append("")
    lines.append(
        "| Mode | entry_scale | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Avg Entry Scale |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.sort_values(["mode_group", "entry_scale"]).iterrows():
        lines.append(
            f"| `{r['mode_group']}` | {_fmt(r['entry_scale'], 1)} | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | "
            f"{_fmt(r['cagr_pct'])} | {_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} | "
            f"{_fmt(r['avg_entry_scale'])} |"
        )

    lines.append("")
    lines.append("## Delta (dd_scaled - baseline) by entry_scale")
    lines.append("")
    lines.append("| entry_scale | Equity Delta | Equity Delta % | MDD Delta %pt | Calmar Delta |")
    lines.append("|---:|---:|---:|---:|---:|")
    for es in ENTRY_SCALES:
        b = metrics_df[(metrics_df["entry_scale"] == es) & (metrics_df["mode_group"] == "baseline")]
        d = metrics_df[(metrics_df["entry_scale"] == es) & (metrics_df["mode_group"] == "dd_scaled")]
        if b.empty or d.empty:
            continue
        b = b.iloc[0]
        d = d.iloc[0]
        eq_delta = float(d["final_equity"] - b["final_equity"])
        eq_delta_pct = (float(d["final_equity"]) / float(b["final_equity"]) - 1.0) * 100.0 if b["final_equity"] != 0 else np.nan
        mdd_delta = float(d["max_drawdown_pct"] - b["max_drawdown_pct"])
        calmar_delta = float(d["calmar_ratio"] - b["calmar_ratio"])
        lines.append(
            f"| {_fmt(es, 1)} | {_fmt(eq_delta)} | {_fmt(eq_delta_pct)} | {_fmt(mdd_delta)} | {_fmt(calmar_delta)} |"
        )

    best_eq = metrics_df.sort_values("final_equity", ascending=False).iloc[0]
    best_calmar = metrics_df.sort_values("calmar_ratio", ascending=False).iloc[0]
    best_mdd = metrics_df.sort_values("max_drawdown_pct", ascending=True).iloc[0]
    lines.append("")
    lines.append("## Best Cases")
    lines.append(
        f"- Best Final Equity: `{best_eq['mode']}` (entry_scale `{_fmt(best_eq['entry_scale'], 1)}`, "
        f"equity `{_fmt(best_eq['final_equity'])}`)"
    )
    lines.append(
        f"- Best Calmar: `{best_calmar['mode']}` (entry_scale `{_fmt(best_calmar['entry_scale'], 1)}`, "
        f"calmar `{_fmt(best_calmar['calmar_ratio'])}`)"
    )
    lines.append(
        f"- Lowest MDD: `{best_mdd['mode']}` (entry_scale `{_fmt(best_mdd['entry_scale'], 1)}`, "
        f"MDD `{_fmt(best_mdd['max_drawdown_pct'])}%`)"
    )
    lines.append("")
    lines.append("## Output Files")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{CSV_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_22", BASE_002_PATH)
    helper_module = load_module("m04_22", BASE_04_PATH)

    df_1m, df_4h = load_data_no_filter(base_module)
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    cases: list[SweepCase] = []
    for es in ENTRY_SCALES:
        cases.append(SweepCase(entry_scale=es, dynamic_dd_scale=False))
        cases.append(SweepCase(entry_scale=es, dynamic_dd_scale=True))

    rows: list[dict] = []
    equity_map: dict[str, pd.DataFrame] = {}

    for case in cases:
        cls = build_case_class(base_module, helper_module, case.dynamic_dd_scale)
        bt = cls(
            symbol=base_module.SYMBOL,
            initial_capital=base_module.INITIAL_CAPITAL,
            commission=base_module.COMMISSION,
            entry_scale=case.entry_scale,
        )
        helper_module.configure_baseline_params(bt)
        bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

        metrics = helper_module.calculate_metrics(bt, base_module.INITIAL_CAPITAL)
        metrics["mode"] = case.mode
        metrics["mode_group"] = "dd_scaled" if case.dynamic_dd_scale else "baseline"
        metrics["entry_scale"] = float(case.entry_scale)
        metrics.update(summarize_scale_usage(pd.DataFrame(bt.scale_entry_log)))
        rows.append(metrics)

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            equity_map[case.mode] = eq[["timestamp", "equity"]].copy()
        else:
            equity_map[case.mode] = pd.DataFrame(columns=["timestamp", "equity"])

    metrics_df = pd.DataFrame(rows).sort_values(["entry_scale", "mode_group"]).reset_index(drop=True)
    metrics_df.to_csv(CSV_FILE, index=False)
    save_plot(equity_map, metrics_df)
    save_report(metrics_df)

    show_cols = [
        "mode",
        "entry_scale",
        "final_equity",
        "max_drawdown_pct",
        "calmar_ratio",
        "avg_entry_scale",
        "scale_0_5_entries",
        "scale_0_25_entries",
    ]
    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(f"saved_report={MD_FILE}")
    print(metrics_df[show_cols].to_string(index=False))


if __name__ == "__main__":
    run()
