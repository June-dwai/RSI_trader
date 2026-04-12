from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
INPUT_CASE2_CURVE_CSV = Path("42_backtest_btcusdt_scale06_adx002_equity_combo_curves.csv")

OUT_BASE = "58_backtest_btcusdt_scale06_adx002_case1_m4_dca075_delayed_open_compare"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

INITIAL_CAPITAL_CASE = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
ENTRY_SCALE = 0.60
MAX_ENTRIES = 4
VERIFY_TOL = 1e-6

DCA_DROP_PCT = 0.0075

VARIANTS = [
    {"variant": "open_now_dca0p75", "open_delay_pct": 0.0000, "open_wait_bars": 0},
    {"variant": "delay0p10_wait30", "open_delay_pct": 0.0010, "open_wait_bars": 30},
    {"variant": "delay0p15_wait60", "open_delay_pct": 0.0015, "open_wait_bars": 60},
    {"variant": "delay0p20_wait120", "open_delay_pct": 0.0020, "open_wait_bars": 120},
    {"variant": "delay0p25_wait240", "open_delay_pct": 0.0025, "open_wait_bars": 240},
]

EXPECTED_BASELINE_TOTAL = {
    "final_equity": 38126.11397467511,
    "cagr_pct": 104.70734554000711,
    "mdd_pct": 52.241617709852015,
}


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


def load_case2_curve() -> pd.DataFrame:
    case2 = pd.read_csv(INPUT_CASE2_CURVE_CSV, parse_dates=["timestamp"])[["timestamp", "equity_case2"]]
    return case2.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)


def build_total_curve(case1_curve: pd.DataFrame, case2_curve: pd.DataFrame) -> pd.DataFrame:
    c1 = case1_curve[["timestamp", "equity"]].rename(columns={"equity": "equity_case1"})
    merged = pd.merge(c1, case2_curve, on="timestamp", how="outer").sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2"]).copy()
    merged["equity_total"] = merged["equity_case1"] + merged["equity_case2"]
    return merged


def compute_curve_stats(curve: pd.DataFrame, col: str, initial_capital: float) -> dict:
    series = curve[col].astype(float)
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


def build_variant_class(base_module, base_cls, open_delay_pct: float, open_wait_bars: int):
    open_delay_pct_value = float(open_delay_pct)
    open_wait_bars_value = int(open_wait_bars)
    adx_period_value = int(base_module.ADX_PERIOD)
    ema_period_value = int(base_module.EMA_PERIOD)
    hysteresis_band_value = float(base_module.HYSTERESIS_BAND)

    class DelayedOpenCase(base_cls):
        max_entries_cap = MAX_ENTRIES
        dca_drop_pct = DCA_DROP_PCT
        open_delay_pct = open_delay_pct_value
        open_wait_bars = open_wait_bars_value

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.stats["hedge_topup_events"] = 0
            self.stats["dca_signal_events"] = 0
            self.stats["pending_open_placed"] = 0
            self.stats["pending_open_limit_fill"] = 0
            self.stats["pending_open_fallback_open"] = 0
            self.stats["pending_open_cancel"] = 0
            self.pending_long_open: dict | None = None

        def _desired_full_hedge_qty(self) -> float:
            if self.position_quantity > 0:
                self.hedge_base_qty = float(self.position_quantity)
            base_qty = float(self.hedge_base_qty)
            if base_qty <= 0:
                return 0.0
            return base_qty * float(self.max_entries_cap)

        def _add_to_position(self, price: float, timestamp, quantity: float, tag: str):
            if not self.current_position or quantity <= 0 or self.position_quantity <= 0:
                return

            pos = self.current_position
            max_position = self.position_quantity * self.max_entries_cap
            add_qty = min(quantity, max_position - pos["quantity"])
            if add_qty <= 0:
                return

            value = add_qty * price
            commission = value * self.commission
            total_qty = pos["quantity"] + add_qty
            new_avg = (pos["avg_entry"] * pos["quantity"] + price * add_qty) / total_qty

            self.capital -= commission
            pos["avg_entry"] = float(new_avg)
            pos["quantity"] = float(total_qty)
            pos["total_commission"] += float(commission)
            self.entry_count = max(1, round(total_qty / self.position_quantity))
            self.recent_trade = [float(price), pos["side"]]
            self._update_cooldown()

            exec_side = "BUY" if pos["side"] == "LONG" else "SELL"
            self._mark_order(timestamp, price, exec_side, add_qty, tag)

        def _open_hedge_short(self, price: float, timestamp):
            desired_qty = self._desired_full_hedge_qty()
            if desired_qty <= 0:
                return

            if self.hedge_position is None:
                open_commission = desired_qty * price * self.commission
                self.capital -= open_commission
                self.hedge_position = {
                    "side": "SHORT",
                    "avg_entry": float(price),
                    "quantity": float(desired_qty),
                    "entry_time": pd.to_datetime(timestamp),
                    "total_commission": float(open_commission),
                }
                self._mark_order(timestamp, price, "SELL", desired_qty, "HEDGE_OPEN")
                self.stats["hedge_open_events"] += 1
                return

            current_qty = float(self.hedge_position["quantity"])
            add_qty = desired_qty - current_qty
            if add_qty <= 1e-12:
                return
            self._topup_hedge_short(price, timestamp, add_qty)

        def _topup_hedge_short(self, price: float, timestamp, add_qty: float):
            if self.hedge_position is None or add_qty <= 0:
                return
            pos = self.hedge_position
            value = add_qty * price
            commission = value * self.commission
            total_qty = pos["quantity"] + add_qty
            new_avg = (pos["avg_entry"] * pos["quantity"] + price * add_qty) / total_qty

            self.capital -= commission
            pos["avg_entry"] = float(new_avg)
            pos["quantity"] = float(total_qty)
            pos["total_commission"] += float(commission)
            self._mark_order(timestamp, price, "SELL", add_qty, "HEDGE_TOPUP")
            self.stats["hedge_topup_events"] = int(self.stats.get("hedge_topup_events", 0)) + 1

        def _queue_delayed_open(self, price: float, timestamp, current_time: int):
            if self.open_delay_pct <= 0 or self.open_wait_bars <= 0:
                return
            self.pending_long_open = {
                "created_time": pd.to_datetime(timestamp),
                "signal_price": float(price),
                "limit_price": float(price * (1.0 - self.open_delay_pct)),
                "expire_idx": int(current_time + self.open_wait_bars),
            }
            self.stats["pending_open_placed"] = int(self.stats.get("pending_open_placed", 0)) + 1

        def _clear_pending_open(self):
            self.pending_long_open = None

        def _process_pending_long_open(self, row: pd.Series, price: float, timestamp, trend: str, ema_touch: bool, current_time: int):
            if self.pending_long_open is None or self.current_position is not None:
                return False

            pending = self.pending_long_open
            if ema_touch or trend != "bullish":
                self.stats["pending_open_cancel"] = int(self.stats.get("pending_open_cancel", 0)) + 1
                self._clear_pending_open()
                return False

            bar_low = float(row["low"])
            limit_price = float(pending["limit_price"])
            if bar_low <= limit_price:
                if self.capital > 0:
                    qty = (self.capital / limit_price) * self.entry_scale
                    self._open_position("LONG", limit_price, timestamp, qty, "OPEN_DELAY_LIMIT")
                    self.last_order_time = current_time
                    self.stats["pending_open_limit_fill"] = int(self.stats.get("pending_open_limit_fill", 0)) + 1
                self._clear_pending_open()
                return True

            if current_time >= int(pending["expire_idx"]):
                if self.capital > 0:
                    qty = (self.capital / price) * self.entry_scale
                    self._open_position("LONG", price, timestamp, qty, "OPEN_DELAY_FALLBACK")
                    self.last_order_time = current_time
                    self.stats["pending_open_fallback_open"] = int(self.stats.get("pending_open_fallback_open", 0)) + 1
                else:
                    self.stats["pending_open_cancel"] = int(self.stats.get("pending_open_cancel", 0)) + 1
                self._clear_pending_open()
                return True

            return False

        def _process_long_entry(self, price: float, timestamp, adx: float, current_time: int):
            if not self.current_position:
                if self.capital <= 0:
                    return
                qty = (self.capital / price) * self.entry_scale
                self._open_position("LONG", price, timestamp, qty, "OPEN")
                self.last_order_time = current_time
                return

            if self.current_position["side"] == "LONG":
                trigger_price = self.recent_trade[0] * (1.0 - self.dca_drop_pct)
                if price <= trigger_price:
                    mult = self._get_adx_multiplier(adx)
                    if mult > 0:
                        self.stats["dca_signal_events"] = int(self.stats.get("dca_signal_events", 0)) + 1
                        self._add_to_position(price, timestamp, self.position_quantity * mult, f"DCA_x{mult}")
                        self.last_order_time = current_time
                return

            self._execute_reverse_signal("LONG", price, timestamp, current_time)

        def _manage_trend_hedge(self, confirmed_trend_4h, price: float, timestamp, is_new_4h_bucket: bool):
            if not is_new_4h_bucket:
                return
            if confirmed_trend_4h not in ("bullish", "bearish"):
                return

            if confirmed_trend_4h == "bearish":
                self._open_hedge_short(price, timestamp)
                return

            if self.hedge_position is None:
                return

            self._close_hedge_short(price, timestamp, "Trend Up")

        def run(self, df_1m: pd.DataFrame, df_4h: pd.DataFrame, backtest_start_date=None):
            self.capital = self.initial_capital
            self.current_position = None
            self.position_quantity = 0.0
            self.entry_count = 0
            self.skip_count = 0
            self.stop_loss = [0.0, 0.0]
            self.pending_reentry = None
            self.pending_long_open = None
            self.last_order_time = -10**9
            self.recent_trade = [0.0, None]
            self.cooldown_time = self.base_cooldown
            self.trades = []
            self.equity_curve = []
            self.order_events = []
            self.current_trend = None
            self.hedge_position = None
            self.hedge_base_qty = 0.0
            self.bankrupt = False
            for k in self.stats:
                self.stats[k] = 0

            out_1m = df_1m.copy()
            out_4h = df_4h.copy()

            if backtest_start_date is not None:
                out_1m = out_1m[out_1m.index >= pd.Timestamp(backtest_start_date)].copy()
            if len(out_1m) == 0:
                return

            out_1m["rsi"] = self.calculate_rsi(out_1m["close"], period=self.rsi_period)
            out_1m["adx"] = self.calculate_adx(out_1m, period=adx_period_value)

            out_4h["ema200_closed"] = out_4h["close"].ewm(span=ema_period_value, adjust=False).mean()
            out_4h["ema200_prev_closed"] = out_4h["ema200_closed"].shift(1)
            out_4h["touch_closed"] = (out_4h["high"] >= out_4h["ema200_closed"]) & (out_4h["low"] <= out_4h["ema200_closed"])
            out_4h["touch_prev_closed"] = out_4h["touch_closed"].shift(1).fillna(False)
            out_4h["trend_4h_hyst"] = self._compute_hysteresis_state(
                out_4h["close"], out_4h["ema200_prev_closed"], hysteresis_band_value
            )
            out_4h["trend_4h_confirmed"] = out_4h["trend_4h_hyst"].shift(1)

            out_1m["bucket_4h"] = out_1m.index.floor("4h")
            out_1m["is_new_4h_bucket"] = out_1m["bucket_4h"] != out_1m["bucket_4h"].shift(1)
            out_1m["run_high_4h"] = out_1m.groupby("bucket_4h")["high"].cummax()
            out_1m["run_low_4h"] = out_1m.groupby("bucket_4h")["low"].cummin()

            out_1m = out_1m.merge(
                out_4h[["ema200_prev_closed", "touch_prev_closed", "trend_4h_confirmed"]],
                left_on="bucket_4h",
                right_index=True,
                how="left",
            )
            out_1m["ema200_prev_closed"] = out_1m["ema200_prev_closed"].ffill()
            out_1m["touch_prev_closed"] = out_1m["touch_prev_closed"].fillna(False)

            alpha = 2.0 / (ema_period_value + 1.0)
            out_1m["ema200_live_current"] = alpha * out_1m["close"] + (1.0 - alpha) * out_1m["ema200_prev_closed"]
            out_1m["touch_curr_sofar"] = (
                (out_1m["run_high_4h"] >= out_1m["ema200_live_current"])
                & (out_1m["run_low_4h"] <= out_1m["ema200_live_current"])
            )
            out_1m["ema_touch_live_nla"] = out_1m["touch_prev_closed"] | out_1m["touch_curr_sofar"]
            out_1m["trend_prev_ema"] = np.where(
                out_1m["close"] > out_1m["ema200_prev_closed"], "bullish", "bearish"
            )
            self.signal_df = out_1m[["close", "ema200_prev_closed", "ema_touch_live_nla", "trend_prev_ema"]].copy()

            for i in range(max(ema_period_value, 200), len(out_1m)):
                row = out_1m.iloc[i]
                timestamp = row.name
                price = float(row["close"])
                rsi = float(row["rsi"])
                adx = float(row["adx"])
                ema_prev = float(row["ema200_prev_closed"]) if pd.notna(row["ema200_prev_closed"]) else np.nan
                if pd.isna(rsi) or pd.isna(adx) or pd.isna(ema_prev):
                    continue

                trend = row["trend_prev_ema"]
                ema_touch = bool(row["ema_touch_live_nla"])
                confirmed_trend_4h = row["trend_4h_confirmed"]
                is_new_4h_bucket = bool(row["is_new_4h_bucket"])

                self.stats["bars_processed"] += 1
                if ema_touch:
                    self.stats["touch_bars"] += 1
                else:
                    self.stats["entry_window_bars"] += 1

                self.current_trend = trend
                self._check_stop_loss_and_reentry(price, timestamp)
                self._manage_trend_hedge(confirmed_trend_4h, price, timestamp, is_new_4h_bucket)
                self._process_pending_long_open(row, price, timestamp, trend, ema_touch, i)

                time_since_last = i - self.last_order_time
                if (not ema_touch) and time_since_last >= self.cooldown_time:
                    if rsi <= self.rsi_oversold and trend == "bullish":
                        self.stats["long_signal_bars"] += 1
                        if self.current_position is None and self.pending_long_open is None and self.open_delay_pct > 0:
                            self._queue_delayed_open(price, timestamp, i)
                        elif self.pending_long_open is None:
                            self._process_long_entry(price, timestamp, adx, i)

                self._check_take_profit(price, timestamp)
                self._record_equity(price, timestamp, ema_prev)

            if self.current_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_ts = out_1m.index[-1]
                self._close_position(last_price, last_ts, "Final Close")
                self._record_equity(last_price, last_ts, float(out_1m["ema200_prev_closed"].ffill().iloc[-1]))

            if self.hedge_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_ts = out_1m.index[-1]
                self._close_hedge_short(last_price, last_ts, "Final Hedge Close")
                self._record_equity(last_price, last_ts, float(out_1m["ema200_prev_closed"].ffill().iloc[-1]))

    return DelayedOpenCase


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_mdd = axes

    cmap = plt.get_cmap("viridis")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i / max(1, len(variants) - 1)) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(INITIAL_CAPITAL_TOTAL, color="#777777", linestyle="--", linewidth=0.9, label=f"Start {INITIAL_CAPITAL_TOTAL:.0f}")
    ax_eq.set_title("58 Study: DCA 0.75% + Delayed Initial Open Variants + Fixed Case2")
    ax_eq.set_ylabel("Total Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_cagr.bar(metrics_df["variant"], metrics_df["total_final_equity"], color=[colors[v] for v in variants], alpha=0.85, label="Total Final Equity")
    ax_cagr.set_ylabel("Total Final Equity")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr.tick_params(axis="x", rotation=20)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(metrics_df["variant"], metrics_df["total_cagr_pct"], color="#d62728", marker="o", linewidth=1.1, label="Total CAGR %")
    ax_cagr_t.set_ylabel("Total CAGR %")
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_mdd.bar(metrics_df["variant"], metrics_df["total_mdd_pct"], color=[colors[v] for v in variants], alpha=0.85, label="Total MDD %")
    ax_mdd.set_ylabel("Total MDD %")
    ax_mdd.grid(True, axis="y", alpha=0.2)
    ax_mdd.tick_params(axis="x", rotation=20)
    ax_mdd_t = ax_mdd.twinx()
    ax_mdd_t.plot(metrics_df["variant"], metrics_df["total_calmar_ratio"], color="#1f77b4", marker="o", linewidth=1.1, label="Total Calmar")
    ax_mdd_t.set_ylabel("Total Calmar")
    h3, l3 = ax_mdd.get_legend_handles_labels()
    h4, l4 = ax_mdd_t.get_legend_handles_labels()
    ax_mdd.legend(h3 + h4, l3 + l4, loc="upper left")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    best_cagr = metrics_df.sort_values("total_cagr_pct", ascending=False).iloc[0]
    best_mdd = metrics_df.sort_values("total_mdd_pct", ascending=True).iloc[0]
    best_calmar = metrics_df.sort_values("total_calmar_ratio", ascending=False).iloc[0]
    baseline = metrics_df[metrics_df["variant"] == "open_now_dca0p75"].iloc[0]
    improved = metrics_df[
        (metrics_df["total_cagr_pct"] > baseline["total_cagr_pct"])
        & (metrics_df["total_mdd_pct"] < baseline["total_mdd_pct"])
    ].copy()

    lines: list[str] = []
    lines.append("# 58 Backtest: DCA 0.75% with Delayed Initial Open Variants")
    lines.append("")
    lines.append("## Setup")
    lines.append("- `case1` keeps study-56 best add spacing: `max_entries=4`, matched hedge size, `dca_drop=0.75%`.")
    lines.append("- `case2` stays fixed as study-42 case2 curve.")
    lines.append("- Variant idea: when the first long signal appears, do not buy immediately; place a lower delayed-open anchor and allow a fallback market open only after the wait window expires.")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Variant | Open Delay % | Wait Bars | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | Limit Fill | Fallback Open | Pending Cancel |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['variant']}` | {_fmt(r['open_delay_pct'] * 100.0)} | {int(r['open_wait_bars'])} | "
            f"{_fmt(r['total_final_equity'])} | {_fmt(r['total_cagr_pct'])} | {_fmt(r['total_mdd_pct'])} | "
            f"{_fmt(r['total_calmar_ratio'])} | {_fmt(r['case1_cagr_pct'])} | {_fmt(r['case1_mdd_pct'])} | "
            f"{int(r['pending_open_limit_fill'])} | {int(r['pending_open_fallback_open'])} | {int(r['pending_open_cancel'])} |"
        )
    lines.append("")
    lines.append("## Best Cases")
    lines.append(f"- Best total CAGR: `{best_cagr['variant']}` (`{_fmt(best_cagr['total_cagr_pct'])}%`).")
    lines.append(f"- Lowest total MDD: `{best_mdd['variant']}` (`{_fmt(best_mdd['total_mdd_pct'])}%`).")
    lines.append(f"- Best total Calmar: `{best_calmar['variant']}` (`{_fmt(best_calmar['total_calmar_ratio'])}`).")
    lines.append("")
    lines.append("## Delta vs open_now_dca0p75")
    lines.append("| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['variant']}` | {_fmt(r['total_final_equity'] - baseline['total_final_equity'])} | "
            f"{_fmt(r['total_cagr_pct'] - baseline['total_cagr_pct'])} | "
            f"{_fmt(r['total_mdd_pct'] - baseline['total_mdd_pct'])} | "
            f"{_fmt(r['total_calmar_ratio'] - baseline['total_calmar_ratio'])} |"
        )
    lines.append("")
    lines.append("## Dominance Check")
    if improved.empty:
        lines.append("- No tested delayed-open variant achieved both `higher total CAGR` and `lower total MDD` than `open_now_dca0p75`.")
    else:
        for _, r in improved.iterrows():
            lines.append(
                f"- `{r['variant']}` dominates baseline: CAGR `{_fmt(r['total_cagr_pct'])}%` vs `{_fmt(baseline['total_cagr_pct'])}%`, "
                f"MDD `{_fmt(r['total_mdd_pct'])}%` vs `{_fmt(baseline['total_mdd_pct'])}%`."
            )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If a variant helps, it means the first fill itself was too early and a shallow patience rule improves average entry quality.")
    lines.append("- Strong delayed-open rules can easily miss rebounds, so the key tradeoff is limit-fill quality versus fallback-chase cost.")
    lines.append("- The key metric is whether delayed initial entry can keep the study-56 CAGR edge while pulling MDD back down.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    m47 = load_module("m47_52", BASE_47_PATH)
    case2_curve = load_case2_curve()

    df_1m, df_4h = m47.load_data_no_filter()
    df_1m = df_1m[(df_1m.index >= m47.BACKTEST_START) & (df_1m.index <= m47.BACKTEST_END)].copy()

    rows: list[dict] = []
    total_curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        cls = build_variant_class(m47, m47.LiveParityNoLookahead, cfg["open_delay_pct"], cfg["open_wait_bars"])
        bt = cls(
            symbol=m47.SYMBOL,
            initial_capital=INITIAL_CAPITAL_CASE,
            commission=m47.COMMISSION,
            entry_scale=ENTRY_SCALE,
        )
        m47.configure_baseline_params(bt)
        bt.run(df_1m, df_4h, backtest_start_date=m47.BACKTEST_START)

        case1_metrics = m47.calculate_metrics(bt, INITIAL_CAPITAL_CASE)
        eq_case1 = pd.DataFrame(bt.equity_curve)
        eq_case1["timestamp"] = pd.to_datetime(eq_case1["timestamp"])
        total_curve = build_total_curve(eq_case1[["timestamp", "equity"]], case2_curve)
        total_stats = compute_curve_stats(total_curve, "equity_total", INITIAL_CAPITAL_TOTAL)

        total_curve["variant"] = cfg["variant"]
        total_curve_rows.append(total_curve)
        curve_map[cfg["variant"]] = total_curve.copy()

        rows.append(
            {
                "variant": cfg["variant"],
                "open_delay_pct": cfg["open_delay_pct"],
                "open_wait_bars": cfg["open_wait_bars"],
                "case1_final_equity": float(case1_metrics["final_equity"]),
                "case1_cagr_pct": float(case1_metrics["cagr_pct"]),
                "case1_mdd_pct": float(case1_metrics["max_drawdown_pct"]),
                "case1_calmar_ratio": float(case1_metrics["calmar_ratio"]),
                "total_final_equity": total_stats["final_equity"],
                "total_return_pct": total_stats["total_return_pct"],
                "total_cagr_pct": total_stats["cagr_pct"],
                "total_mdd_pct": total_stats["max_drawdown_pct"],
                "total_calmar_ratio": total_stats["calmar_ratio"],
                "dca_signal_events": int(bt.stats.get("dca_signal_events", 0)),
                "hedge_open_events": int(bt.stats.get("hedge_open_events", 0)),
                "hedge_close_events": int(bt.stats.get("hedge_close_events", 0)),
                "hedge_topup_events": int(bt.stats.get("hedge_topup_events", 0)),
                "pending_open_placed": int(bt.stats.get("pending_open_placed", 0)),
                "pending_open_limit_fill": int(bt.stats.get("pending_open_limit_fill", 0)),
                "pending_open_fallback_open": int(bt.stats.get("pending_open_fallback_open", 0)),
                "pending_open_cancel": int(bt.stats.get("pending_open_cancel", 0)),
            }
        )

    metrics_df = pd.DataFrame(rows)
    curves_df = pd.concat(total_curve_rows, ignore_index=True)

    baseline = metrics_df[metrics_df["variant"] == "open_now_dca0p75"].iloc[0]
    if abs(float(baseline["total_final_equity"]) - EXPECTED_BASELINE_TOTAL["final_equity"]) > VERIFY_TOL:
        raise ValueError("baseline total final equity mismatch")
    if abs(float(baseline["total_cagr_pct"]) - EXPECTED_BASELINE_TOTAL["cagr_pct"]) > 1e-6:
        raise ValueError("baseline total cagr mismatch")
    if abs(float(baseline["total_mdd_pct"]) - EXPECTED_BASELINE_TOTAL["mdd_pct"]) > 1e-6:
        raise ValueError("baseline total mdd mismatch")

    metrics_df = metrics_df.sort_values(["total_calmar_ratio", "total_cagr_pct"], ascending=[False, False]).reset_index(drop=True)
    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df)
    save_report(metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    run()
