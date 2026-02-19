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

PLOT_FILE = Path("21_backtest_btcusdt_dd_scale_compare.png")
CSV_FILE = Path("21_backtest_btcusdt_dd_scale_compare.csv")
MD_FILE = Path("21_backtest_btcusdt_dd_scale_compare.md")

HYSTERESIS_BAND = 0.005


@dataclass(frozen=True)
class CompareCase:
    mode: str
    dynamic_dd_scale: bool


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
            if current_drawdown > 0.35:
                return 0.5
            if current_drawdown > 0.20:
                return 0.7
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
            "scale_0_7_entries": 0,
            "scale_0_5_entries": 0,
            "avg_entry_scale": np.nan,
            "avg_entry_drawdown_pct": np.nan,
        }

    s = entry_log_df["position_scale"].astype(float)
    return {
        "entries_scaled_total": int(len(entry_log_df)),
        "scale_1_0_entries": int((s == 1.0).sum()),
        "scale_0_7_entries": int((s == 0.7).sum()),
        "scale_0_5_entries": int((s == 0.5).sum()),
        "avg_entry_scale": float(s.mean()),
        "avg_entry_drawdown_pct": float(entry_log_df["drawdown_pct"].astype(float).mean()),
    }


def save_plot(equity_curves: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("21 Compare: Baseline vs Drawdown-Based Entry Scale")
    ax_eq.set_ylabel("Equity (USDT)")
    for mode in metrics_df["mode"].tolist():
        eq = equity_curves.get(mode)
        if eq is None or eq.empty:
            continue
        ax_eq.plot(eq["timestamp"], eq["equity"], linewidth=1.2, label=mode)
    ax_eq.legend(loc="upper left")
    ax_eq.grid(True, alpha=0.2)

    ax_final = fig.add_subplot(gs[1, 0])
    ax_final.set_title("Final Equity")
    ax_final.bar(metrics_df["mode"], metrics_df["final_equity"])
    ax_final.set_ylabel("USDT")
    ax_final.tick_params(axis="x", labelrotation=15)
    ax_final.grid(True, axis="y", alpha=0.2)

    ax_mdd = fig.add_subplot(gs[1, 1])
    ax_mdd.set_title("Max Drawdown (%)")
    ax_mdd.bar(metrics_df["mode"], metrics_df["max_drawdown_pct"])
    ax_mdd.set_ylabel("%")
    ax_mdd.tick_params(axis="x", labelrotation=15)
    ax_mdd.grid(True, axis="y", alpha=0.2)

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
    plt.close()


def save_report(metrics_df: pd.DataFrame):
    baseline = metrics_df[metrics_df["mode"] == "baseline_hys05"].iloc[0]
    scaled = metrics_df[metrics_df["mode"] == "dd_scaled_hys05"].iloc[0]

    lines: list[str] = []
    lines.append("# 21 Drawdown-Based Position Scale Compare")
    lines.append("")
    lines.append("## Objective")
    lines.append("- Compare 17 baseline (`hys=0.50%`) vs drawdown-based entry scale control.")
    lines.append("- Keep all existing rules unchanged (long SL ON, fixed 5x hedge, no-lookahead, raw data).")
    lines.append("")
    lines.append("## DD Scale Rule")
    lines.append("```python")
    lines.append("if current_drawdown > 0.35:")
    lines.append("    position_scale = 0.5")
    lines.append("elif current_drawdown > 0.20:")
    lines.append("    position_scale = 0.7")
    lines.append("else:")
    lines.append("    position_scale = 1.0")
    lines.append("```")
    lines.append("- Scale is applied to new long base quantity (`base_qty`) at entry open.")
    lines.append("- Subsequent averaging follows original logic using scaled base quantity.")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append(
        "| Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Avg Entry Scale |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['mode']}` | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | {_fmt(r['cagr_pct'])} | "
            f"{_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} | "
            f"{_fmt(r['avg_entry_scale'])} |"
        )

    lines.append("")
    lines.append("## Entry Scale Usage")
    lines.append("")
    lines.append("| Mode | Total Entries | scale=1.0 | scale=0.7 | scale=0.5 | Avg Drawdown at Entry % |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['mode']}` | {int(r['entries_scaled_total'])} | {int(r['scale_1_0_entries'])} | "
            f"{int(r['scale_0_7_entries'])} | {int(r['scale_0_5_entries'])} | {_fmt(r['avg_entry_drawdown_pct'])} |"
        )

    eq_delta = float(scaled["final_equity"] - baseline["final_equity"])
    eq_delta_pct = (float(scaled["final_equity"]) / float(baseline["final_equity"]) - 1.0) * 100.0
    mdd_delta = float(scaled["max_drawdown_pct"] - baseline["max_drawdown_pct"])

    lines.append("")
    lines.append("## Delta vs Baseline")
    lines.append(f"- Final Equity Delta: `{_fmt(eq_delta)}` USDT (`{_fmt(eq_delta_pct)}%`).")
    lines.append(f"- MDD Delta: `{_fmt(mdd_delta)}` %pt.")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If MDD decreases with small equity loss, this can be a risk-control improvement.")
    lines.append("- If equity drops sharply while MDD barely improves, DD scaling is too conservative for this strategy.")
    lines.append("")
    lines.append("## Output Files")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{CSV_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_21", BASE_002_PATH)
    helper_module = load_module("m04_21", BASE_04_PATH)

    df_1m, df_4h = load_data_no_filter(base_module)
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    cases = [
        CompareCase(mode="baseline_hys05", dynamic_dd_scale=False),
        CompareCase(mode="dd_scaled_hys05", dynamic_dd_scale=True),
    ]

    rows = []
    equity_map: dict[str, pd.DataFrame] = {}

    for case in cases:
        cls = build_case_class(base_module, helper_module, case.dynamic_dd_scale)
        bt = cls(
            symbol=base_module.SYMBOL,
            initial_capital=base_module.INITIAL_CAPITAL,
            commission=base_module.COMMISSION,
            entry_scale=base_module.ENTRY_SCALE,
        )
        helper_module.configure_baseline_params(bt)
        bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

        metrics = helper_module.calculate_metrics(bt, base_module.INITIAL_CAPITAL)
        metrics["mode"] = case.mode

        entry_log_df = pd.DataFrame(bt.scale_entry_log)
        metrics.update(summarize_scale_usage(entry_log_df))
        rows.append(metrics)

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            equity_map[case.mode] = eq[["timestamp", "equity"]].copy()
        else:
            equity_map[case.mode] = pd.DataFrame(columns=["timestamp", "equity"])

    metrics_df = pd.DataFrame(rows)
    mode_order = ["baseline_hys05", "dd_scaled_hys05"]
    metrics_df["mode"] = pd.Categorical(metrics_df["mode"], categories=mode_order, ordered=True)
    metrics_df = metrics_df.sort_values("mode").reset_index(drop=True)
    metrics_df["mode"] = metrics_df["mode"].astype(str)

    save_plot(equity_map, metrics_df)
    metrics_df.to_csv(CSV_FILE, index=False)
    save_report(metrics_df)

    show_cols = [
        "mode",
        "final_equity",
        "total_return_pct",
        "cagr_pct",
        "max_drawdown_pct",
        "calmar_ratio",
        "trades",
        "long_trades",
        "short_trades",
        "win_rate_pct",
        "profit_factor",
        "avg_entry_scale",
        "entries_scaled_total",
        "scale_0_7_entries",
        "scale_0_5_entries",
    ]
    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(f"saved_report={MD_FILE}")
    print(metrics_df[show_cols].to_string(index=False))


if __name__ == "__main__":
    run()
