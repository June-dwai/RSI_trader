from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
BASE_35_PATH = Path("35_backtest_btcusdt_live_nla_longonly_hedge_hyst05.py")

OUT_BASE = "37_backtest_btcusdt_35_touch_reentry_variants"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")

INITIAL_CAPITAL = 1000.0
ENTRY_SCALE = 0.50


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


def save_plot(curves: dict[str, pd.DataFrame]):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    order = [
        "A_baseline_35",
        "B_touch_prev_only",
        "C_B_plus_reentry_above_ema",
    ]
    titles = {
        "A_baseline_35": "A) 35 baseline (touch_prev OR current-touch-so-far)",
        "B_touch_prev_only": "B) A + touch uses previous confirmed 4h touch only",
        "C_B_plus_reentry_above_ema": "C) B + reentry requires price > 4h EMA200",
    }

    for ax, key in zip(axes, order):
        eq = curves.get(key, pd.DataFrame())
        if not eq.empty:
            ax.plot(eq["timestamp"], eq["equity"], color="#111111", linewidth=1.05)
        ax.axhline(INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9, label="Start 1000")
        ax.set_title(titles[key])
        ax.set_ylabel("Equity (USDT)")
        ax.grid(True, alpha=0.2)
        ax.legend(loc="upper left")

    axes[-1].set_xlabel("Time")
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    base = metrics_df.loc[metrics_df["case_id"] == "A_baseline_35"].iloc[0]

    lines: list[str] = []
    lines.append("# 37 Backtest: 35 Variants (Touch/Reentry Rules)")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Base template: study-35 (`scale=0.50`, long-only + trend short hedge, hysteresis 0.5%).")
    lines.append("- Case A: baseline 35 logic.")
    lines.append("- Case B: same as A but `ema_touch` uses previous confirmed 4h touch only.")
    lines.append("- Case C: same as B plus reentry only if `price > 4h EMA200` (long-side gate).")
    lines.append("")
    lines.append("## Results")
    lines.append("| Case | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Reentry EMA Blocks |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['case_id']}` | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | {_fmt(r['cagr_pct'])} | "
            f"{_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} | "
            f"{int(r['reentry_ema_block_count'])} |"
        )
    lines.append("")
    lines.append("## Delta vs A (Baseline)")
    lines.append("| Case | Final Equity Delta | CAGR Delta (pp) | MDD Delta (pp) | Calmar Delta |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['case_id']}` | {_fmt(r['final_equity'] - float(base['final_equity']))} | "
            f"{_fmt(r['cagr_pct'] - float(base['cagr_pct']))} | "
            f"{_fmt(r['max_drawdown_pct'] - float(base['max_drawdown_pct']))} | "
            f"{_fmt(r['calmar_ratio'] - float(base['calmar_ratio']))} |"
        )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    base = load_module("m002_37", BASE_002_PATH)
    helper = load_module("m04_37", BASE_04_PATH)
    m35 = load_module("m35_37", BASE_35_PATH)

    df_1m, df_4h = m35.load_data_no_filter(base)
    df_1m = df_1m[(df_1m.index >= base.BACKTEST_START) & (df_1m.index <= base.BACKTEST_END)].copy()

    class Variant(m35.LiveParityNoLookahead):
        def __init__(self, *args, use_prev_touch_only: bool, reentry_need_above_ema: bool, **kwargs):
            super().__init__(*args, **kwargs)
            self.use_prev_touch_only = bool(use_prev_touch_only)
            self.reentry_need_above_ema = bool(reentry_need_above_ema)
            self.reentry_ema_block_count = 0
            self._ema_prev_now = np.nan

        def _check_stop_loss_and_reentry(self, price: float, timestamp):
            if not self.current_position:
                if self.stop_loss != [0.0, 0.0]:
                    self.stop_loss = [0.0, 0.0]
                self.pending_reentry = None
                return

            pos = self.current_position
            side = pos["side"]
            entry_price = pos["avg_entry"]
            qty = pos["quantity"]

            if self.stop_loss == [0.0, 0.0]:
                if side == "LONG":
                    stop_price = entry_price * (1 - self.stop_loss_pct)
                    if price <= stop_price:
                        close_qty = qty * 0.8
                        self._partial_close(price, timestamp, close_qty, "Stop Loss")
                        self.stop_loss = [float(price), float(close_qty)]
                        self.pending_reentry = {
                            "side": "LONG",
                            "quantity": float(close_qty),
                            "trigger_price": float(price),
                            "reentry_price": float(price * (1 - self.stop_loss_pct)),
                        }
                        self.stats["stop_loss_events"] += 1
                else:
                    stop_price = entry_price * (1 + self.stop_loss_pct)
                    if price >= stop_price:
                        close_qty = qty * 0.8
                        self._partial_close(price, timestamp, close_qty, "Stop Loss")
                        self.stop_loss = [float(price), -float(close_qty)]
                        self.pending_reentry = {
                            "side": "SHORT",
                            "quantity": float(close_qty),
                            "trigger_price": float(price),
                            "reentry_price": float(price * (1 + self.stop_loss_pct)),
                        }
                        self.stats["stop_loss_events"] += 1
                return

            if self.stop_loss[1] == 0:
                return

            if self.pending_reentry is None:
                signed_qty = float(self.stop_loss[1])
                trigger = float(self.stop_loss[0])
                side_re = "LONG" if signed_qty > 0 else "SHORT"
                qty_re = abs(signed_qty)
                re_price = trigger * (1 - self.stop_loss_pct) if side_re == "LONG" else trigger * (1 + self.stop_loss_pct)
                self.pending_reentry = {
                    "side": side_re,
                    "quantity": qty_re,
                    "trigger_price": trigger,
                    "reentry_price": re_price,
                }

            re = self.pending_reentry
            ema_prev = float(self._ema_prev_now) if pd.notna(self._ema_prev_now) else np.nan

            if re["side"] == "LONG" and price <= re["reentry_price"]:
                if self.reentry_need_above_ema and not pd.isna(ema_prev) and not (price > ema_prev):
                    self.reentry_ema_block_count += 1
                    return
                self._add_to_position(re["reentry_price"], timestamp, re["quantity"], "REENTRY")
                self.stop_loss = [float(price), 0.0]
                self.pending_reentry = None
                self.stats["reentry_events"] += 1
            elif re["side"] == "SHORT" and price >= re["reentry_price"]:
                if self.reentry_need_above_ema and not pd.isna(ema_prev) and not (price < ema_prev):
                    self.reentry_ema_block_count += 1
                    return
                self._add_to_position(re["reentry_price"], timestamp, re["quantity"], "REENTRY")
                self.stop_loss = [float(price), 0.0]
                self.pending_reentry = None
                self.stats["reentry_events"] += 1

        def run(self, df_1m: pd.DataFrame, df_4h: pd.DataFrame, backtest_start_date=None):
            self.capital = self.initial_capital
            self.current_position = None
            self.position_quantity = 0.0
            self.entry_count = 0
            self.skip_count = 0
            self.stop_loss = [0.0, 0.0]
            self.pending_reentry = None
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
            self.reentry_ema_block_count = 0
            for k in self.stats:
                self.stats[k] = 0

            out_1m = df_1m.copy()
            out_4h = df_4h.copy()
            if backtest_start_date is not None:
                out_1m = out_1m[out_1m.index >= pd.Timestamp(backtest_start_date)].copy()
            if len(out_1m) == 0:
                return

            out_1m["rsi"] = self.calculate_rsi(out_1m["close"], period=self.rsi_period)
            out_1m["adx"] = self.calculate_adx(out_1m, period=m35.ADX_PERIOD)

            out_4h["ema200_closed"] = out_4h["close"].ewm(span=m35.EMA_PERIOD, adjust=False).mean()
            out_4h["ema200_prev_closed"] = out_4h["ema200_closed"].shift(1)
            out_4h["touch_closed"] = (out_4h["high"] >= out_4h["ema200_closed"]) & (out_4h["low"] <= out_4h["ema200_closed"])
            out_4h["touch_prev_closed"] = out_4h["touch_closed"].shift(1).fillna(False)
            out_4h["trend_4h_hyst"] = self._compute_hysteresis_state(
                out_4h["close"], out_4h["ema200_prev_closed"], m35.HYSTERESIS_BAND
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

            alpha = 2.0 / (m35.EMA_PERIOD + 1.0)
            out_1m["ema200_live_current"] = alpha * out_1m["close"] + (1.0 - alpha) * out_1m["ema200_prev_closed"]
            out_1m["touch_curr_sofar"] = (
                (out_1m["run_high_4h"] >= out_1m["ema200_live_current"])
                & (out_1m["run_low_4h"] <= out_1m["ema200_live_current"])
            )
            if self.use_prev_touch_only:
                out_1m["ema_touch_case"] = out_1m["touch_prev_closed"]
            else:
                out_1m["ema_touch_case"] = out_1m["touch_prev_closed"] | out_1m["touch_curr_sofar"]

            out_1m["trend_prev_ema"] = np.where(out_1m["close"] > out_1m["ema200_prev_closed"], "bullish", "bearish")

            for i in range(max(m35.EMA_PERIOD, 200), len(out_1m)):
                row = out_1m.iloc[i]
                timestamp = row.name
                price = float(row["close"])
                rsi = float(row["rsi"])
                adx = float(row["adx"])
                ema_prev = float(row["ema200_prev_closed"]) if pd.notna(row["ema200_prev_closed"]) else np.nan
                if pd.isna(rsi) or pd.isna(adx) or pd.isna(ema_prev):
                    continue

                trend = row["trend_prev_ema"]
                ema_touch = bool(row["ema_touch_case"])
                confirmed_trend_4h = row["trend_4h_confirmed"]
                is_new_4h_bucket = bool(row["is_new_4h_bucket"])

                self.stats["bars_processed"] += 1
                if ema_touch:
                    self.stats["touch_bars"] += 1
                else:
                    self.stats["entry_window_bars"] += 1

                self.current_trend = trend
                self._ema_prev_now = ema_prev
                self._check_stop_loss_and_reentry(price, timestamp)
                self._manage_trend_hedge(confirmed_trend_4h, price, timestamp, is_new_4h_bucket)

                time_since_last = i - self.last_order_time
                if (not ema_touch) and time_since_last >= self.cooldown_time:
                    if rsi <= self.rsi_oversold and trend == "bullish":
                        self.stats["long_signal_bars"] += 1
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

    cases = [
        ("A_baseline_35", False, False),
        ("B_touch_prev_only", True, False),
        ("C_B_plus_reentry_above_ema", True, True),
    ]

    rows: list[dict] = []
    curves: dict[str, pd.DataFrame] = {}

    for case_id, use_prev_touch_only, reentry_need_above_ema in cases:
        bt = Variant(
            base_module=base,
            symbol=base.SYMBOL,
            initial_capital=INITIAL_CAPITAL,
            commission=base.COMMISSION,
            entry_scale=ENTRY_SCALE,
            use_prev_touch_only=use_prev_touch_only,
            reentry_need_above_ema=reentry_need_above_ema,
        )
        helper.configure_baseline_params(bt)
        bt.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)

        metrics = helper.calculate_metrics(bt, INITIAL_CAPITAL)
        metrics["case_id"] = case_id
        metrics["reentry_ema_block_count"] = int(bt.reentry_ema_block_count)
        rows.append(metrics)

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            curves[case_id] = eq[["timestamp", "equity"]].copy()
        else:
            curves[case_id] = pd.DataFrame(columns=["timestamp", "equity"])

    metrics_df = pd.DataFrame(rows)
    order = ["A_baseline_35", "B_touch_prev_only", "C_B_plus_reentry_above_ema"]
    metrics_df["case_order"] = metrics_df["case_id"].map({k: i for i, k in enumerate(order)})
    metrics_df = metrics_df.sort_values("case_order").drop(columns=["case_order"]).reset_index(drop=True)

    cols = [
        "case_id",
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
        "reentry_ema_block_count",
    ]
    metrics_df[cols].to_csv(OUT_CSV, index=False)
    save_plot(curves)
    save_report(metrics_df[cols])

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df[cols].to_string(index=False))


if __name__ == "__main__":
    run()
