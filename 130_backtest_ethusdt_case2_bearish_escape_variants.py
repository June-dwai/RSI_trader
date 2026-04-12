from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SOURCE_002 = Path("002_backtest_btcusdt.py")
SOURCE_04 = Path("04_backtest_btcusdt_mode_compare.py")
SOURCE_32 = Path("32_backtest_btcusdt_live_nla.py")
SOURCE_42 = Path("42_backtest_btcusdt_scale06_adx002_equity_combo.py")
SOURCE_129 = Path("129_backtest_ethusdt_case2_vs_case3best_mix.py")

OUT_BASE = "130_backtest_ethusdt_case2_bearish_escape_variants"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_MD = Path(f"{OUT_BASE}.md")

SYMBOL = "ETHUSDT"
INITIAL_CAPITAL = 1000.0
BACKTEST_START = pd.Timestamp("2021-01-01 00:00:00")
ANALYSIS_2026_START = pd.Timestamp("2026-01-01 00:00:00")
CRASH_TS = pd.Timestamp("2021-05-19 12:50:00")
CRASH_WINDOW_START = pd.Timestamp("2021-05-10 00:00:00")
CRASH_WINDOW_END = pd.Timestamp("2021-05-25 00:00:00")

VARIANTS: list[dict] = [
    {
        "variant": "baseline_case2",
        "label": "Baseline",
        "color": "#1f77b4",
        "short_rsi_overbought": 85,
        "allow_short_reverse_on_prev_touch": False,
        "fix_stop_rearm": False,
        "bearish_flip_trim_frac": 0.0,
    },
    {
        "variant": "short_rsi80",
        "label": "Short RSI 80",
        "color": "#ff7f0e",
        "short_rsi_overbought": 80,
        "allow_short_reverse_on_prev_touch": False,
        "fix_stop_rearm": False,
        "bearish_flip_trim_frac": 0.0,
    },
    {
        "variant": "short_rsi80_reverse_nogate",
        "label": "RSI 80 + Reverse No Gate",
        "color": "#2ca02c",
        "short_rsi_overbought": 80,
        "allow_short_reverse_on_prev_touch": True,
        "fix_stop_rearm": False,
        "bearish_flip_trim_frac": 0.0,
    },
    {
        "variant": "short_rsi80_reverse_nogate_stopfix",
        "label": "RSI 80 + No Gate + Stop Fix",
        "color": "#d62728",
        "short_rsi_overbought": 80,
        "allow_short_reverse_on_prev_touch": True,
        "fix_stop_rearm": True,
        "bearish_flip_trim_frac": 0.0,
    },
    {
        "variant": "short_rsi80_reverse_nogate_stopfix_trim80",
        "label": "Combo + Trim 80",
        "color": "#9467bd",
        "short_rsi_overbought": 80,
        "allow_short_reverse_on_prev_touch": True,
        "fix_stop_rearm": True,
        "bearish_flip_trim_frac": 0.8,
    },
]


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


def compute_curve_stats(curve: pd.DataFrame, equity_col: str, initial_capital: float) -> dict:
    series = curve[equity_col].astype(float)
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


def compute_window_stats(curve: pd.DataFrame, start_ts: pd.Timestamp, initial_capital: float | None = None) -> dict:
    seg = curve[pd.to_datetime(curve["timestamp"]) >= pd.Timestamp(start_ts)].copy()
    if seg.empty:
        return {"return_pct": np.nan, "mdd_pct": np.nan}
    start_eq = float(seg["equity"].iloc[0]) if initial_capital is None else float(initial_capital)
    end_eq = float(seg["equity"].iloc[-1])
    if start_eq <= 0:
        return {"return_pct": np.nan, "mdd_pct": np.nan}
    dd = seg["equity"].astype(float) / seg["equity"].cummax().astype(float) - 1.0
    return {
        "return_pct": (end_eq / start_eq - 1.0) * 100.0,
        "mdd_pct": -float(dd.min() * 100.0),
    }


def first_zero_ts(curve: pd.DataFrame) -> pd.Timestamp | pd.NaT:
    zero = curve[curve["equity"].astype(float) <= 0].copy()
    if zero.empty:
        return pd.NaT
    return pd.Timestamp(zero["timestamp"].iloc[0])


def equity_at_or_before(curve: pd.DataFrame, ts: pd.Timestamp) -> float:
    seg = curve[pd.to_datetime(curve["timestamp"]) <= pd.Timestamp(ts)].copy()
    if seg.empty:
        return np.nan
    return float(seg["equity"].iloc[-1])


def make_variant_class(base_mod, s42_mod, cfg: dict):
    base_cls = s42_mod.build_case2_class(base_mod)

    class VariantCase2(base_cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.variant_cfg = dict(cfg)
            self.prev_trend = None
            self.stats["trend_flip_trim_events"] = 0

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
            if re["side"] == "LONG" and price <= re["reentry_price"]:
                self._add_to_position(re["reentry_price"], timestamp, re["quantity"], "REENTRY")
                self.pending_reentry = None
                self.stats["reentry_events"] += 1
                if self.variant_cfg["fix_stop_rearm"]:
                    self.stop_loss = [0.0, 0.0]
                else:
                    self.stop_loss = [float(price), 0.0]
            elif re["side"] == "SHORT" and price >= re["reentry_price"]:
                self._add_to_position(re["reentry_price"], timestamp, re["quantity"], "REENTRY")
                self.pending_reentry = None
                self.stats["reentry_events"] += 1
                if self.variant_cfg["fix_stop_rearm"]:
                    self.stop_loss = [0.0, 0.0]
                else:
                    self.stop_loss = [float(price), 0.0]

        def _maybe_trim_on_bearish_flip(self, price: float, timestamp, current_time_idx: int, trend: str):
            trim_frac = float(self.variant_cfg["bearish_flip_trim_frac"])
            if trim_frac <= 0:
                return
            if self.prev_trend != "bullish" or trend != "bearish":
                return
            if not self.current_position or self.current_position["side"] != "LONG":
                return

            trim_qty = self.current_position["quantity"] * trim_frac
            if trim_qty <= 0:
                return

            self._partial_close(price, timestamp, trim_qty, "TrendFlipTrim")
            self.last_order_time = current_time_idx
            self.stats["trend_flip_trim_events"] += 1
            if self.current_position:
                self.stop_loss = [0.0, 0.0]
                self.pending_reentry = None
                self._update_cooldown()

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
            self.prev_trend = None
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
            self.signal_df = out_1m[
                ["close", "rsi", "adx", "ema200_prev_closed", "touch_prev_closed", "ema_touch_live_nla", "trend_prev_ema"]
            ].copy()

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
                self._maybe_trim_on_bearish_flip(price, timestamp, i, trend)

                time_since_last = i - self.last_order_time
                allow_short_reverse = (
                    self.variant_cfg["allow_short_reverse_on_prev_touch"]
                    and self.current_position is not None
                    and self.current_position["side"] == "LONG"
                )
                allow_short_signal = (not ema_touch) or allow_short_reverse

                if time_since_last >= self.cooldown_time:
                    if (not ema_touch) and rsi <= self.rsi_oversold and trend == "bullish":
                        self.stats["long_signal_bars"] += 1
                        self._process_long_entry(price, timestamp, adx, i)
                    elif allow_short_signal and rsi >= self.rsi_overbought and trend == "bearish":
                        self.stats["short_signal_bars"] += 1
                        self._process_short_entry(price, timestamp, adx, i)

                self._check_take_profit(price, timestamp)
                self._record_equity(price, timestamp, ema_prev)
                self.prev_trend = trend

            if self.current_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_ts = out_1m.index[-1]
                self._close_position(last_price, last_ts, "Final Close")
                self._record_equity(last_price, last_ts, float(out_1m["ema200_prev_closed"].ffill().iloc[-1]))

    return VariantCase2


def run_variant(df_1m: pd.DataFrame, df_4h: pd.DataFrame, base, helper, m32, s42, cfg: dict) -> tuple[pd.DataFrame, dict]:
    bt_cls = make_variant_class(m32, s42, cfg)
    bt = bt_cls(
        base_module=base,
        symbol=SYMBOL,
        initial_capital=INITIAL_CAPITAL,
        commission=base.COMMISSION,
        entry_scale=0.60,
    )
    helper.configure_baseline_params(bt)
    bt.rsi_overbought = int(cfg["short_rsi_overbought"])
    bt.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)

    curve = pd.DataFrame(bt.equity_curve)[["timestamp", "equity"]].copy()
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)

    stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL)
    stats["variant"] = cfg["variant"]
    stats["short_rsi_overbought"] = int(cfg["short_rsi_overbought"])
    stats["allow_short_reverse_on_prev_touch"] = bool(cfg["allow_short_reverse_on_prev_touch"])
    stats["fix_stop_rearm"] = bool(cfg["fix_stop_rearm"])
    stats["bearish_flip_trim_frac"] = float(cfg["bearish_flip_trim_frac"])
    stats["trades"] = len(bt.trades)
    stats["reverse_events"] = int(bt.stats["reverse_events"])
    stats["stop_loss_events"] = int(bt.stats["stop_loss_events"])
    stats["reentry_events"] = int(bt.stats["reentry_events"])
    stats["trend_flip_trim_events"] = int(bt.stats["trend_flip_trim_events"])
    return curve, stats


def save_plot(curves: list[tuple[dict, pd.DataFrame]]) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.2]})
    ax_eq, ax_dd, ax_crash = axes

    for cfg, curve in curves:
        color = cfg["color"]
        label = cfg["variant"]
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.05, label=label, color=color)
        dd = curve["equity"].astype(float) / curve["equity"].cummax().astype(float) - 1.0
        ax_dd.plot(curve["timestamp"], -dd * 100.0, linewidth=1.0, label=label, color=color)

        seg = curve[(curve["timestamp"] >= CRASH_WINDOW_START) & (curve["timestamp"] <= CRASH_WINDOW_END)].copy()
        if not seg.empty:
            ax_crash.plot(seg["timestamp"], seg["equity"], linewidth=1.1, label=label, color=color)

    ax_eq.axhline(INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 130: ETHUSDT Case2 Bearish-Escape Variants (2021-latest)")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", fontsize=8)

    ax_dd.set_ylabel("Drawdown %")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="upper left", fontsize=8)

    ax_crash.axvline(CRASH_TS, color="#444444", linestyle="--", linewidth=0.9)
    ax_crash.set_title("May 2021 Crash Zoom")
    ax_crash.set_ylabel("Equity (USDT)")
    ax_crash.set_xlabel("Time")
    ax_crash.grid(True, alpha=0.2)
    ax_crash.legend(loc="upper left", fontsize=8)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, latest_closed_ts: pd.Timestamp, used_paths: list[Path]) -> None:
    top_cagr = metrics_df.sort_values("cagr_pct", ascending=False).iloc[0]
    top_calmar = metrics_df.sort_values("calmar_ratio", ascending=False).iloc[0]
    crash_best = metrics_df.sort_values("equity_at_2021_05_19_1250", ascending=False).iloc[0]

    lines: list[str] = []
    lines.append("# Study 130: ETHUSDT case2 bearish-escape variants")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Symbol: `{SYMBOL}`")
    lines.append(f"- Window: `{BACKTEST_START}` -> `{latest_closed_ts}`")
    lines.append("- Initial capital per variant: `1000 USDT`")
    lines.append("- Baseline engine: study-42 case2 (`dual-direction / no-hedge / prev-touch-only / max entries 4`).")
    lines.append("- Variant goal: reduce the chance of getting stuck in a large long during a bearish transition.")
    lines.append("- Data sources used:")
    for path in used_paths:
        lines.append(f"  - `{path}`")
    lines.append("")
    lines.append("## Variant axes")
    lines.append("- `short_rsi_overbought`: lower bearish reverse trigger from `85` to `80`.")
    lines.append("- `allow_short_reverse_on_prev_touch`: allow long-to-short reverse even if previous 4h candle touched EMA200.")
    lines.append("- `fix_stop_rearm`: re-arm stop logic after reentry instead of leaving `stop_loss[1] == 0`.")
    lines.append("- `bearish_flip_trim_frac`: immediately trim an open long on the first bullish->bearish trend flip.")
    lines.append("")
    lines.append("## Results")
    lines.append("| Variant | Final Equity | Total Return % | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Crash Equity | First Zero TS | Reverse | Stop | Reentry | Trim |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        zero_ts = "N/A" if pd.isna(row["first_zero_ts"]) else str(pd.Timestamp(row["first_zero_ts"]))
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['total_return_pct'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {_fmt(row['return_2026_pct'])} | "
            f"{_fmt(row['mdd_2026_pct'])} | {_fmt(row['equity_at_2021_05_19_1250'])} | {zero_ts} | "
            f"{int(row['reverse_events'])} | {int(row['stop_loss_events'])} | {int(row['reentry_events'])} | {int(row['trend_flip_trim_events'])} |"
        )
    lines.append("")
    lines.append("## Takeaways")
    lines.append(
        f"- Highest CAGR: `{top_cagr['variant']}` with CAGR `{_fmt(top_cagr['cagr_pct'])}%`, MDD `{_fmt(top_cagr['max_drawdown_pct'])}%`."
    )
    lines.append(
        f"- Best Calmar: `{top_calmar['variant']}` with Calmar `{_fmt(top_calmar['calmar_ratio'])}`, CAGR `{_fmt(top_calmar['cagr_pct'])}%`."
    )
    lines.append(
        f"- Best May-2021 survival equity: `{crash_best['variant']}` with equity `{_fmt(crash_best['equity_at_2021_05_19_1250'])}` at `{CRASH_TS}`."
    )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    study129 = load_module("study129_for_130", SOURCE_129)
    base = load_module("m002_for_130", SOURCE_002)
    helper = load_module("m04_for_130", SOURCE_04)
    m32 = load_module("m32_for_130", SOURCE_32)
    s42 = load_module("s42_for_130", SOURCE_42)

    print("[130] Loading ETH 2021+ market...", flush=True)
    df_1m, df_4h, latest_closed_ts, used_paths = study129.load_eth_market_2021plus()
    print(f"[130] ETH 1m span: {df_1m.index.min()} -> {df_1m.index.max()} ({len(df_1m)} rows)", flush=True)
    print(f"[130] ETH 4h span: {df_4h.index.min()} -> {df_4h.index.max()} ({len(df_4h)} rows)", flush=True)

    base.SYMBOL = SYMBOL
    base.BACKTEST_START = str(BACKTEST_START.date())
    base.BACKTEST_END = str(pd.Timestamp(latest_closed_ts).date())

    metrics_rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    plot_curves: list[tuple[dict, pd.DataFrame]] = []

    for cfg in VARIANTS:
        print(f"[130] Running {cfg['variant']}...", flush=True)
        curve, stats = run_variant(df_1m.copy(), df_4h.copy(), base, helper, m32, s42, cfg)
        stats_2026 = compute_window_stats(curve, ANALYSIS_2026_START)
        zero_ts = first_zero_ts(curve)
        crash_equity = equity_at_or_before(curve, CRASH_TS)
        metrics_rows.append(
            {
                **stats,
                "return_2026_pct": stats_2026["return_pct"],
                "mdd_2026_pct": stats_2026["mdd_pct"],
                "equity_at_2021_05_19_1250": crash_equity,
                "first_zero_ts": zero_ts,
                "survived_2021_05_19": bool(pd.notna(crash_equity) and crash_equity > 0),
            }
        )
        curve_out = curve.copy()
        curve_out["variant"] = cfg["variant"]
        curve_rows.append(curve_out)
        plot_curves.append((cfg, curve))

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    pd.concat(curve_rows, ignore_index=True).to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")
    save_plot(plot_curves)
    save_report(metrics_df, latest_closed_ts, used_paths)

    print(f"[130] Crash timestamp reference: {CRASH_TS}", flush=True)
    for _, row in metrics_df.iterrows():
        zero_ts = "N/A" if pd.isna(row["first_zero_ts"]) else str(pd.Timestamp(row["first_zero_ts"]))
        print(
            f"[130] {row['variant']}: CAGR={_fmt(row['cagr_pct'])}% "
            f"MDD={_fmt(row['max_drawdown_pct'])}% Calmar={_fmt(row['calmar_ratio'])} "
            f"CrashEq={_fmt(row['equity_at_2021_05_19_1250'])} Zero={zero_ts}",
            flush=True,
        )
    print(f"[130] Outputs: {OUT_PNG}, {OUT_CSV}, {OUT_CURVES_CSV}, {OUT_MD}", flush=True)


if __name__ == "__main__":
    main()
