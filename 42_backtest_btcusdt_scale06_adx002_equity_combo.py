from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
CASE1_SCRIPT_PATH = Path("40_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_scale06.py")
CASE2_BASE_SCRIPT_PATH = Path("32_backtest_btcusdt_live_nla.py")

OUT_BASE = "42_backtest_btcusdt_scale06_adx002_equity_combo"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_CURVE_CSV = Path(f"{OUT_BASE}_curves.csv")

INITIAL_CAPITAL_EACH = 1000.0
ENTRY_SCALE = 0.60
CASE2_MAX_ENTRIES = 4


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


def build_case2_class(base_mod):
    class DualDirectionNoHedgeAdx002(base_mod.LiveParityNoLookahead):
        """Study-42 case2: dual-direction, no hedge/no hysteresis, ADX=002, prev-touch-only gate, max_entries=4."""

        def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            tr1 = high - low
            tr2 = (high - close.shift(1)).abs()
            tr3 = (low - close.shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            up_move = high - high.shift(1)
            down_move = low.shift(1) - low
            pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
            neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

            atr = tr.rolling(period).mean()
            plus_di = 100 * pd.Series(pos_dm, index=df.index).rolling(period).mean() / atr
            minus_di = 100 * pd.Series(neg_dm, index=df.index).rolling(period).mean() / atr
            dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).abs()
            return dx.rolling(period).mean()

        def _add_to_position(self, price: float, timestamp, quantity: float, tag: str):
            if not self.current_position:
                return
            if not self.position_quantity or self.position_quantity == 0:
                return
            if quantity <= 0:
                return

            pos = self.current_position
            max_position = self.position_quantity * CASE2_MAX_ENTRIES
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

        def _execute_reverse_signal(self, target_side: str, price: float, timestamp, current_time_idx: int):
            """
            002-style reverse:
            - Partial close 80%
            - Immediately open opposite side with current capital*scale
            - Do not create Reverse Residual liquidation trade
            """
            if not self.current_position:
                return
            if self.current_position["side"] == target_side:
                return

            self._partial_close(price, timestamp, self.current_position["quantity"] * 0.8, "Reverse")

            if self.capital <= 0:
                self.last_order_time = current_time_idx
                self.stats["reverse_events"] += 1
                return

            # Mirror 002 semantics: replace old residual leg without explicit residual close.
            self.current_position = None
            self.position_quantity = 0.0
            self.entry_count = 0
            self.skip_count = 0
            self.stop_loss = [0.0, 0.0]
            self.pending_reentry = None
            self.recent_trade = [0.0, None]

            qty = (self.capital / price) * self.entry_scale
            if qty > 0:
                self._open_position(target_side, price, timestamp, qty, "REVERSE_OPEN")

            self.last_order_time = current_time_idx
            self.stats["reverse_events"] += 1

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
            out_1m["adx"] = self.calculate_adx(out_1m, period=base_mod.ADX_PERIOD)

            out_4h["ema200_closed"] = out_4h["close"].ewm(span=base_mod.EMA_PERIOD, adjust=False).mean()
            out_4h["ema200_prev_closed"] = out_4h["ema200_closed"].shift(1)
            out_4h["touch_closed"] = (out_4h["high"] >= out_4h["ema200_closed"]) & (out_4h["low"] <= out_4h["ema200_closed"])
            out_4h["touch_prev_closed"] = out_4h["touch_closed"].shift(1).fillna(False)

            out_1m["bucket_4h"] = out_1m.index.floor("4h")
            out_1m["run_high_4h"] = out_1m.groupby("bucket_4h")["high"].cummax()
            out_1m["run_low_4h"] = out_1m.groupby("bucket_4h")["low"].cummin()

            out_1m = out_1m.merge(
                out_4h[["ema200_prev_closed", "touch_prev_closed"]],
                left_on="bucket_4h",
                right_index=True,
                how="left",
            )
            out_1m["ema200_prev_closed"] = out_1m["ema200_prev_closed"].ffill()
            out_1m["touch_prev_closed"] = out_1m["touch_prev_closed"].fillna(False)

            alpha = 2.0 / (base_mod.EMA_PERIOD + 1.0)
            out_1m["ema200_live_current"] = alpha * out_1m["close"] + (1.0 - alpha) * out_1m["ema200_prev_closed"]
            out_1m["touch_curr_sofar"] = (
                (out_1m["run_high_4h"] >= out_1m["ema200_live_current"])
                & (out_1m["run_low_4h"] <= out_1m["ema200_live_current"])
            )
            out_1m["ema_touch_live_nla"] = out_1m["touch_prev_closed"]
            out_1m["trend_prev_ema"] = np.where(out_1m["close"] > out_1m["ema200_prev_closed"], "bullish", "bearish")
            self.signal_df = out_1m[["close", "ema200_prev_closed", "ema_touch_live_nla", "trend_prev_ema"]].copy()

            for i in range(max(base_mod.EMA_PERIOD, 200), len(out_1m)):
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

                self.stats["bars_processed"] += 1
                if ema_touch:
                    self.stats["touch_bars"] += 1
                else:
                    self.stats["entry_window_bars"] += 1

                self.current_trend = trend
                self._check_stop_loss_and_reentry(price, timestamp)

                time_since_last = i - self.last_order_time
                if (not ema_touch) and time_since_last >= self.cooldown_time:
                    if rsi <= self.rsi_oversold and trend == "bullish":
                        self.stats["long_signal_bars"] += 1
                        self._process_long_entry(price, timestamp, adx, i)
                    elif rsi >= self.rsi_overbought and trend == "bearish":
                        self.stats["short_signal_bars"] += 1
                        self._process_short_entry(price, timestamp, adx, i)

                self._check_take_profit(price, timestamp)
                self._record_equity(price, timestamp, ema_prev)

            if self.current_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_ts = out_1m.index[-1]
                self._close_position(last_price, last_ts, "Final Close")
                self._record_equity(last_price, last_ts, float(out_1m["ema200_prev_closed"].ffill().iloc[-1]))

    return DualDirectionNoHedgeAdx002


def build_total_curve(eq1: pd.DataFrame, eq2: pd.DataFrame) -> pd.DataFrame:
    c1 = eq1[["timestamp", "equity"]].rename(columns={"equity": "equity_case1"})
    c2 = eq2[["timestamp", "equity"]].rename(columns={"equity": "equity_case2"})
    merged = pd.merge(c1, c2, on="timestamp", how="outer").sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2"]).copy()
    merged["equity_total"] = merged["equity_case1"] + merged["equity_case2"]
    return merged


def compute_curve_stats(curve: pd.DataFrame, col: str, initial_capital: float) -> dict:
    series = curve[col].astype(float)
    final_equity = float(series.iloc[-1])
    total_return_pct = ((final_equity / float(initial_capital)) - 1.0) * 100.0

    if len(curve) > 1:
        elapsed_days = (curve["timestamp"].iloc[-1] - curve["timestamp"].iloc[0]).total_seconds() / 86400.0
        years = max(elapsed_days / 365.25, 1e-9)
        cagr_pct = ((final_equity / float(initial_capital)) ** (1.0 / years) - 1.0) * 100.0
    else:
        cagr_pct = np.nan

    dd = (series - series.cummax()) / series.cummax().replace(0, np.nan) * 100.0
    mdd_pct = float(dd.min()) if len(dd) else np.nan
    calmar = (cagr_pct / abs(mdd_pct)) if (pd.notna(cagr_pct) and pd.notna(mdd_pct) and mdd_pct != 0) else np.nan
    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": abs(mdd_pct) if pd.notna(mdd_pct) else np.nan,
        "calmar_ratio": calmar,
    }


def save_plot(total_curve: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True, gridspec_kw={"height_ratios": [1.2, 1.0, 1.0]})
    ax0, ax1, ax2 = axes

    ax0.plot(total_curve["timestamp"], total_curve["equity_total"], color="#111111", linewidth=1.2, label="Total Equity (Case1+Case2)")
    ax0.axhline(INITIAL_CAPITAL_EACH * 2.0, color="#777777", linestyle="--", linewidth=0.9, label="Start 2000")
    ax0.set_title("42 Study: Total Equity Curve (Each Strategy Starts with 1000)")
    ax0.set_ylabel("Total Equity (USDT)")
    ax0.grid(True, alpha=0.2)
    ax0.legend(loc="upper left")

    ax1.plot(
        total_curve["timestamp"],
        total_curve["equity_case1"],
        color="#1f77b4",
        linewidth=1.1,
        label="Case1: Study-40 (Long-only + Trend Short Hedge + Hyst 0.5 + ADX002 + Scale0.60)",
    )
    ax1.axhline(INITIAL_CAPITAL_EACH, color="#777777", linestyle="--", linewidth=0.9, label="Start 1000")
    ax1.set_ylabel("Case1 Equity")
    ax1.grid(True, alpha=0.2)
    ax1.legend(loc="upper left")

    ax2.plot(
        total_curve["timestamp"],
        total_curve["equity_case2"],
        color="#d62728",
        linewidth=1.1,
        label=f"Case2: Dual-dir, No Hedge/No Hyst, ADX002, Scale0.60, Prev-touch-only, MaxEntries={CASE2_MAX_ENTRIES}",
    )
    ax2.axhline(INITIAL_CAPITAL_EACH, color="#777777", linestyle="--", linewidth=0.9, label="Start 1000")
    ax2.set_ylabel("Case2 Equity")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.2)
    ax2.legend(loc="upper left")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(metrics_rows: list[dict]):
    df = pd.DataFrame(metrics_rows)
    lines: list[str] = []
    lines.append("# 42 Backtest: Total Equity + Two Scale0.60 ADX002 Curves")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Capital allocation: each strategy starts with `1000` USDT.")
    lines.append("- Top curve: `Total Equity = Case1 + Case2`.")
    lines.append("- Case1: study-40 logic (`long-only + trend short hedge + hysteresis 0.5% + ADX 002 + scale 0.60`).")
    lines.append(
        f"- Case2: dual-direction engine (`no short hedge`, `no hysteresis`, `ADX 002`, `scale 0.60`, `prev-touch-only`, `max entries {CASE2_MAX_ENTRIES}`)."
    )
    lines.append("")
    lines.append("## Metrics")
    lines.append("| Curve | Initial Capital | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in df.iterrows():
        lines.append(
            f"| `{r['curve']}` | {_fmt(r['initial_capital'])} | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | "
            f"{_fmt(r['cagr_pct'])} | {_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | "
            f"{int(r.get('trades', 0))} | {int(r.get('long_trades', 0))}/{int(r.get('short_trades', 0))} | "
            f"{_fmt(r.get('win_rate_pct', np.nan))} | {_fmt(r.get('profit_factor', np.nan))} |"
        )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curve CSV: `{OUT_CURVE_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    base = load_module("m002_42", BASE_002_PATH)
    helper = load_module("m04_42", BASE_04_PATH)
    m40 = load_module("m40_42", CASE1_SCRIPT_PATH)
    m32 = load_module("m32_42", CASE2_BASE_SCRIPT_PATH)

    df_1m, df_4h = m40.load_data_no_filter(base)
    df_1m = df_1m[(df_1m.index >= base.BACKTEST_START) & (df_1m.index <= base.BACKTEST_END)].copy()

    bt1 = m40.LiveParityNoLookahead(
        base_module=base,
        symbol=base.SYMBOL,
        initial_capital=INITIAL_CAPITAL_EACH,
        commission=base.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    helper.configure_baseline_params(bt1)
    bt1.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)
    eq1 = pd.DataFrame(bt1.equity_curve)
    eq1["timestamp"] = pd.to_datetime(eq1["timestamp"])
    eq1 = eq1.sort_values("timestamp").reset_index(drop=True)

    Case2Class = build_case2_class(m32)
    bt2 = Case2Class(
        base_module=base,
        symbol=base.SYMBOL,
        initial_capital=INITIAL_CAPITAL_EACH,
        commission=base.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    helper.configure_baseline_params(bt2)
    bt2.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)
    eq2 = pd.DataFrame(bt2.equity_curve)
    eq2["timestamp"] = pd.to_datetime(eq2["timestamp"])
    eq2 = eq2.sort_values("timestamp").reset_index(drop=True)

    total_curve = build_total_curve(eq1, eq2)
    total_curve.to_csv(OUT_CURVE_CSV, index=False)
    save_plot(total_curve)

    m1 = helper.calculate_metrics(bt1, INITIAL_CAPITAL_EACH)
    m2 = helper.calculate_metrics(bt2, INITIAL_CAPITAL_EACH)
    mt = compute_curve_stats(total_curve, "equity_total", INITIAL_CAPITAL_EACH * 2.0)

    metrics_rows = [
        {
            "curve": "total_case1_plus_case2",
            "initial_capital": INITIAL_CAPITAL_EACH * 2.0,
            **mt,
            "trades": int(m1.get("trades", 0)) + int(m2.get("trades", 0)),
            "long_trades": int(m1.get("long_trades", 0)) + int(m2.get("long_trades", 0)),
            "short_trades": int(m1.get("short_trades", 0)) + int(m2.get("short_trades", 0)),
            "win_rate_pct": np.nan,
            "profit_factor": np.nan,
        },
        {
            "curve": "case1_study40_longonly_hedge_hyst05_adx002_scale06",
            "initial_capital": INITIAL_CAPITAL_EACH,
            **{k: m1.get(k, np.nan) for k in ["final_equity", "total_return_pct", "cagr_pct", "max_drawdown_pct", "calmar_ratio"]},
            "trades": m1.get("trades", 0),
            "long_trades": m1.get("long_trades", 0),
            "short_trades": m1.get("short_trades", 0),
            "win_rate_pct": m1.get("win_rate_pct", np.nan),
            "profit_factor": m1.get("profit_factor", np.nan),
        },
        {
            "curve": f"case2_dual_nohedge_nohyst_adx002_scale06_prevtouch_maxentries{CASE2_MAX_ENTRIES}",
            "initial_capital": INITIAL_CAPITAL_EACH,
            **{k: m2.get(k, np.nan) for k in ["final_equity", "total_return_pct", "cagr_pct", "max_drawdown_pct", "calmar_ratio"]},
            "trades": m2.get("trades", 0),
            "long_trades": m2.get("long_trades", 0),
            "short_trades": m2.get("short_trades", 0),
            "win_rate_pct": m2.get("win_rate_pct", np.nan),
            "profit_factor": m2.get("profit_factor", np.nan),
        },
    ]

    pd.DataFrame(metrics_rows).to_csv(OUT_CSV, index=False)
    save_report(metrics_rows)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVE_CSV}")
    print(f"saved_report={OUT_MD}")
    print(
        f"total_final_equity={_fmt(mt.get('final_equity'))}, "
        f"case1_final_equity={_fmt(m1.get('final_equity'))}, "
        f"case2_final_equity={_fmt(m2.get('final_equity'))}"
    )


if __name__ == "__main__":
    run()
