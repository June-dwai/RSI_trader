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
CASE1_BASE_PATH = Path("40_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_scale06.py")
CASE2_BASE_PATH = Path("32_backtest_btcusdt_live_nla.py")
CASE2_WRAPPER_PATH = Path("42_backtest_btcusdt_scale06_adx002_equity_combo.py")

OUT_BASE = "46_backtest_btcusdt_scale06_adx002_case1_r2_softoff_keephedge_compare"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_CURVE_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_CASE1_REGIME_CSV = Path(f"{OUT_BASE}_case1_regime_stats.csv")
OUT_REGIME_EVENTS_CSV = Path(f"{OUT_BASE}_regime_events.csv")
OUT_STRESS_CSV = Path(f"{OUT_BASE}_stress_window.csv")

INITIAL_CAPITAL_EACH = 1000.0
ENTRY_SCALE = 0.60

OFF_MIN_BARS_4H = 4
VOL_LOOKBACK_4H = 4380  # 2-year window in 4h bars
VOL_P80_FALLBACK = 1.20
VOL_P65_FALLBACK = 1.00
DD_CRASH_OFF = -6.0
DD_CRASH_ON = -3.0

STRESS_START = pd.Timestamp("2025-10-01 00:00:00")
STRESS_END = pd.Timestamp("2026-02-12 00:00:00")


@dataclass(frozen=True)
class VariantCase:
    variant_id: str
    label: str
    off_rule: str
    on_rule: str


VARIANT_CASES = [
    VariantCase(
        variant_id="baseline_hedge5x",
        label="Baseline hedge5x",
        off_rule="N/A (always ON)",
        on_rule="N/A",
    ),
    VariantCase(
        variant_id="r2_soft_off_block_hedgeopen",
        label="R2 soft-off (block hedge open)",
        off_rule="bearish and run_len_4h >= 12",
        on_rule="bullish and run_len_4h >= 2 (after cooldown)",
    ),
    VariantCase(
        variant_id="r2_soft_off_keep_hedgeopen",
        label="R2 soft-off (keep hedge open allowed)",
        off_rule="bearish and run_len_4h >= 12",
        on_rule="bullish and run_len_4h >= 2 (after cooldown)",
    ),
]

VARIANT_ORDER = [x.variant_id for x in VARIANT_CASES]
VARIANT_LABELS = {x.variant_id: x.label for x in VARIANT_CASES}
VARIANT_OFF_RULE = {x.variant_id: x.off_rule for x in VARIANT_CASES}
VARIANT_ON_RULE = {x.variant_id: x.on_rule for x in VARIANT_CASES}


def load_module(alias: str, path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing script: {path}")
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def _safe_float(v) -> float:
    if pd.isna(v):
        return np.nan
    return float(v)


def build_case1_regime_class(case1_base_mod, variant_id: str):
    BaseCls = case1_base_mod.LiveParityNoLookahead

    class Case1RegimeSoftOff(BaseCls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.variant_id = str(variant_id)
            self._reset_regime_state()

        @staticmethod
        def _compute_run_length(series: pd.Series) -> pd.Series:
            valid = series.isin(["bullish", "bearish"])
            grp = (series != series.shift(1)).cumsum()
            run_len = series.groupby(grp).cumcount() + 1
            run_len = run_len.astype(float)
            run_len.loc[~valid] = np.nan
            return run_len

        @staticmethod
        def _compute_flip(series: pd.Series) -> pd.Series:
            prev = series.shift(1)
            flip = (series != prev) & series.isin(["bullish", "bearish"]) & prev.isin(["bullish", "bearish"])
            return flip.astype(float)

        @staticmethod
        def _risk_score_24(run_len_4h: float, flip_count_30_4h: float, near_ema_ratio_30_4h: float) -> int:
            if pd.isna(run_len_4h) or pd.isna(flip_count_30_4h) or pd.isna(near_ema_ratio_30_4h):
                return 0
            score = 0
            if run_len_4h <= 8:
                score += 1
            if run_len_4h <= 3:
                score += 1
            if flip_count_30_4h >= 2:
                score += 1
            if flip_count_30_4h >= 4:
                score += 1
            if near_ema_ratio_30_4h >= 20:
                score += 1
            if near_ema_ratio_30_4h >= 40:
                score += 1
            return int(score)

        def _reset_regime_state(self):
            self.case1_enabled = True
            self.case1_off_bars_4h = 0
            self.regime_events: list[dict] = []
            self.regime_stats = {
                "off_switches": 0,
                "on_switches": 0,
                "on_bars_1m": 0,
                "off_bars_1m": 0,
                "on_bars_4h": 0,
                "off_bars_4h": 0,
                "blocked_open_signals": 0,
                "blocked_add_signals": 0,
                "blocked_hedge_open_signals": 0,
                "stress_on_bars_1m": 0,
                "stress_off_bars_1m": 0,
            }

        def _record_regime_transition(self, timestamp, action: str, reason: str, row: pd.Series):
            self.regime_events.append(
                {
                    "timestamp": pd.to_datetime(timestamp),
                    "variant_id": self.variant_id,
                    "action": action,
                    "reason": reason,
                    "enabled_after": int(self.case1_enabled),
                    "off_bars_4h_counter": int(self.case1_off_bars_4h),
                    "trend_4h_confirmed": row.get("trend_4h_confirmed", np.nan),
                    "run_len_4h": _safe_float(row.get("run_len_4h", np.nan)),
                    "flip_count_30_4h": _safe_float(row.get("flip_count_30_4h", np.nan)),
                    "near_ema_ratio_30_4h": _safe_float(row.get("near_ema_ratio_30_4h", np.nan)),
                    "vol20_confirmed": _safe_float(row.get("vol20_confirmed", np.nan)),
                    "vol20_p80_2y": _safe_float(row.get("vol20_p80_2y", np.nan)),
                    "vol20_p65_2y": _safe_float(row.get("vol20_p65_2y", np.nan)),
                    "risk_score_24": int(row.get("risk_score_24", 0)) if pd.notna(row.get("risk_score_24", np.nan)) else 0,
                    "dd30_confirmed": _safe_float(row.get("dd30_confirmed", np.nan)),
                }
            )

        def _off_condition(self, row: pd.Series) -> tuple[bool, str]:
            trend = str(row.get("trend_4h_confirmed", "")) if pd.notna(row.get("trend_4h_confirmed", np.nan)) else ""
            run_len = _safe_float(row.get("run_len_4h", np.nan))
            if self.variant_id == "baseline_hedge5x":
                return False, "always_on_baseline"

            cond = (trend == "bearish") and pd.notna(run_len) and run_len >= 12
            return bool(cond), "bearish mature run (>=12)"

        def _on_condition(self, row: pd.Series) -> tuple[bool, str]:
            trend = str(row.get("trend_4h_confirmed", "")) if pd.notna(row.get("trend_4h_confirmed", np.nan)) else ""
            run_len = _safe_float(row.get("run_len_4h", np.nan))
            if self.variant_id == "baseline_hedge5x":
                return True, "always_on_baseline"

            cond = (trend == "bullish") and pd.notna(run_len) and run_len >= 2
            return bool(cond), "bullish trend re-confirmed (>=2 bars)"

        def _update_regime_state(self, row: pd.Series, timestamp, is_new_4h_bucket: bool):
            if not is_new_4h_bucket:
                return

            if self.variant_id == "baseline_hedge5x":
                self.case1_enabled = True
                self.case1_off_bars_4h = 0
                self.regime_stats["on_bars_4h"] += 1
                return

            off_cond, off_reason = self._off_condition(row)
            on_cond, on_reason = self._on_condition(row)

            if self.case1_enabled:
                if off_cond:
                    self.case1_enabled = False
                    self.case1_off_bars_4h = 0
                    self.regime_stats["off_switches"] += 1
                    self._record_regime_transition(timestamp, "OFF", off_reason, row)
            else:
                self.case1_off_bars_4h += 1
                if self.case1_off_bars_4h >= OFF_MIN_BARS_4H and on_cond and (not off_cond):
                    self.case1_enabled = True
                    self.case1_off_bars_4h = 0
                    self.regime_stats["on_switches"] += 1
                    self._record_regime_transition(timestamp, "ON", on_reason, row)

            if self.case1_enabled:
                self.regime_stats["on_bars_4h"] += 1
            else:
                self.regime_stats["off_bars_4h"] += 1

        def _add_to_position(self, price: float, timestamp, quantity: float, tag: str):
            if not self.case1_enabled:
                self.regime_stats["blocked_add_signals"] += 1
                return
            super()._add_to_position(price, timestamp, quantity, tag)

        def _manage_trend_hedge(self, confirmed_trend_4h, price: float, timestamp, is_new_4h_bucket: bool):
            if not is_new_4h_bucket:
                return
            if confirmed_trend_4h not in ("bullish", "bearish"):
                return

            allow_open_while_off = self.variant_id == "r2_soft_off_keep_hedgeopen"
            if confirmed_trend_4h == "bearish" and self.hedge_position is None:
                if self.case1_enabled or allow_open_while_off:
                    self._open_hedge_short(price, timestamp)
                else:
                    self.regime_stats["blocked_hedge_open_signals"] += 1
            elif confirmed_trend_4h == "bullish" and self.hedge_position is not None:
                self._close_hedge_short(price, timestamp, "Trend Up")

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
            self._reset_regime_state()
            for k in self.stats:
                self.stats[k] = 0

            out_1m = df_1m.copy()
            out_4h = df_4h.copy()

            if backtest_start_date is not None:
                out_1m = out_1m[out_1m.index >= pd.Timestamp(backtest_start_date)].copy()
            if len(out_1m) == 0:
                return

            out_1m["rsi"] = self.calculate_rsi(out_1m["close"], period=self.rsi_period)
            out_1m["adx"] = self.calculate_adx(out_1m, period=14)

            out_4h["ema200_closed"] = out_4h["close"].ewm(span=200, adjust=False).mean()
            out_4h["ema200_prev_closed"] = out_4h["ema200_closed"].shift(1)
            out_4h["touch_closed"] = (out_4h["high"] >= out_4h["ema200_closed"]) & (out_4h["low"] <= out_4h["ema200_closed"])
            out_4h["touch_prev_closed"] = out_4h["touch_closed"].shift(1).fillna(False)
            out_4h["trend_4h_hyst"] = self._compute_hysteresis_state(
                out_4h["close"], out_4h["ema200_prev_closed"], 0.005
            )
            out_4h["trend_4h_confirmed"] = out_4h["trend_4h_hyst"].shift(1)

            out_4h["run_len_4h"] = self._compute_run_length(out_4h["trend_4h_confirmed"])
            out_4h["flip_4h"] = self._compute_flip(out_4h["trend_4h_confirmed"])
            out_4h["flip_count_30_4h"] = out_4h["flip_4h"].rolling(30, min_periods=1).sum()

            out_4h["abs_gap_pct_4h"] = (
                (out_4h["close"] - out_4h["ema200_prev_closed"]).abs() / out_4h["ema200_prev_closed"] * 100.0
            ).replace([np.inf, -np.inf], np.nan)
            out_4h["abs_gap_pct_confirmed"] = out_4h["abs_gap_pct_4h"].shift(1)
            out_4h["near_ema_0p5_4h"] = (out_4h["abs_gap_pct_confirmed"] <= 0.5).astype(float)
            out_4h["near_ema_ratio_30_4h"] = out_4h["near_ema_0p5_4h"].rolling(30, min_periods=1).mean() * 100.0

            out_4h["ret_4h"] = out_4h["close"].pct_change()
            out_4h["vol20_4h"] = out_4h["ret_4h"].rolling(20, min_periods=5).std() * 100.0
            out_4h["vol20_confirmed"] = out_4h["vol20_4h"].shift(1)
            out_4h["vol20_p80_2y"] = out_4h["vol20_confirmed"].rolling(VOL_LOOKBACK_4H, min_periods=300).quantile(0.80)
            out_4h["vol20_p65_2y"] = out_4h["vol20_confirmed"].rolling(VOL_LOOKBACK_4H, min_periods=300).quantile(0.65)

            out_4h["dd30_4h"] = (out_4h["close"] / out_4h["close"].rolling(30, min_periods=5).max() - 1.0) * 100.0
            out_4h["dd30_confirmed"] = out_4h["dd30_4h"].shift(1)

            out_4h["risk_score_24"] = (
                (out_4h["run_len_4h"] <= 8).astype(int)
                + (out_4h["run_len_4h"] <= 3).astype(int)
                + (out_4h["flip_count_30_4h"] >= 2).astype(int)
                + (out_4h["flip_count_30_4h"] >= 4).astype(int)
                + (out_4h["near_ema_ratio_30_4h"] >= 20).astype(int)
                + (out_4h["near_ema_ratio_30_4h"] >= 40).astype(int)
            )

            out_1m["bucket_4h"] = out_1m.index.floor("4h")
            out_1m["is_new_4h_bucket"] = out_1m["bucket_4h"] != out_1m["bucket_4h"].shift(1)
            out_1m["run_high_4h"] = out_1m.groupby("bucket_4h")["high"].cummax()
            out_1m["run_low_4h"] = out_1m.groupby("bucket_4h")["low"].cummin()

            merge_cols = [
                "ema200_prev_closed",
                "touch_prev_closed",
                "trend_4h_confirmed",
                "run_len_4h",
                "flip_count_30_4h",
                "near_ema_ratio_30_4h",
                "abs_gap_pct_confirmed",
                "vol20_confirmed",
                "vol20_p80_2y",
                "vol20_p65_2y",
                "dd30_confirmed",
                "risk_score_24",
            ]
            out_1m = out_1m.merge(out_4h[merge_cols], left_on="bucket_4h", right_index=True, how="left")

            out_1m["ema200_prev_closed"] = out_1m["ema200_prev_closed"].ffill()
            out_1m["touch_prev_closed"] = out_1m["touch_prev_closed"].fillna(False)
            out_1m["run_len_4h"] = out_1m["run_len_4h"].ffill()
            out_1m["flip_count_30_4h"] = out_1m["flip_count_30_4h"].ffill()
            out_1m["near_ema_ratio_30_4h"] = out_1m["near_ema_ratio_30_4h"].ffill()
            out_1m["vol20_confirmed"] = out_1m["vol20_confirmed"].ffill()
            out_1m["vol20_p80_2y"] = out_1m["vol20_p80_2y"].ffill()
            out_1m["vol20_p65_2y"] = out_1m["vol20_p65_2y"].ffill()
            out_1m["dd30_confirmed"] = out_1m["dd30_confirmed"].ffill()
            out_1m["risk_score_24"] = out_1m["risk_score_24"].ffill().fillna(0)

            alpha = 2.0 / (200 + 1.0)
            out_1m["ema200_live_current"] = alpha * out_1m["close"] + (1.0 - alpha) * out_1m["ema200_prev_closed"]
            out_1m["touch_curr_sofar"] = (
                (out_1m["run_high_4h"] >= out_1m["ema200_live_current"])
                & (out_1m["run_low_4h"] <= out_1m["ema200_live_current"])
            )
            out_1m["ema_touch_live_nla"] = out_1m["touch_prev_closed"] | out_1m["touch_curr_sofar"]
            out_1m["trend_prev_ema"] = np.where(out_1m["close"] > out_1m["ema200_prev_closed"], "bullish", "bearish")
            self.signal_df = out_1m[["close", "ema200_prev_closed", "ema_touch_live_nla", "trend_prev_ema"]].copy()
            for i in range(max(200, 200), len(out_1m)):
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
                self._update_regime_state(row, timestamp, is_new_4h_bucket)

                if self.case1_enabled:
                    self.regime_stats["on_bars_1m"] += 1
                else:
                    self.regime_stats["off_bars_1m"] += 1

                if STRESS_START <= pd.to_datetime(timestamp) <= STRESS_END:
                    if self.case1_enabled:
                        self.regime_stats["stress_on_bars_1m"] += 1
                    else:
                        self.regime_stats["stress_off_bars_1m"] += 1

                self._check_stop_loss_and_reentry(price, timestamp)
                self._manage_trend_hedge(confirmed_trend_4h, price, timestamp, is_new_4h_bucket)

                time_since_last = i - self.last_order_time
                if (not ema_touch) and time_since_last >= self.cooldown_time:
                    if rsi <= self.rsi_oversold and trend == "bullish":
                        self.stats["long_signal_bars"] += 1
                        if self.case1_enabled:
                            self._process_long_entry(price, timestamp, adx, i)
                        else:
                            self.regime_stats["blocked_open_signals"] += 1

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

    return Case1RegimeSoftOff


def prepare_equity_df(bt) -> pd.DataFrame:
    eq = pd.DataFrame(bt.equity_curve)
    if eq.empty:
        return eq
    eq["timestamp"] = pd.to_datetime(eq["timestamp"])
    return eq.sort_values("timestamp").reset_index(drop=True)


def prepare_trades_df(bt) -> pd.DataFrame:
    t = pd.DataFrame(bt.trades)
    if t.empty:
        return t
    t["entry_time"] = pd.to_datetime(t["entry_time"])
    t["exit_time"] = pd.to_datetime(t["exit_time"])
    t["duration_days"] = (t["exit_time"] - t["entry_time"]).dt.total_seconds() / 86400.0
    return t


def summarize_regime_stats(regime_stats: dict) -> dict:
    out = dict(regime_stats)
    total_1m = float(out.get("on_bars_1m", 0) + out.get("off_bars_1m", 0))
    total_4h = float(out.get("on_bars_4h", 0) + out.get("off_bars_4h", 0))
    stress_total = float(out.get("stress_on_bars_1m", 0) + out.get("stress_off_bars_1m", 0))

    out["off_ratio_1m_pct"] = (out.get("off_bars_1m", 0) / total_1m * 100.0) if total_1m > 0 else np.nan
    out["off_ratio_4h_pct"] = (out.get("off_bars_4h", 0) / total_4h * 100.0) if total_4h > 0 else np.nan
    out["stress_off_ratio_1m_pct"] = (out.get("stress_off_bars_1m", 0) / stress_total * 100.0) if stress_total > 0 else np.nan
    return out


def run_case1_variant(variant: str, cls, base_mod, helper_mod, df_1m: pd.DataFrame, df_4h: pd.DataFrame) -> dict:
    bt = cls(
        base_module=base_mod,
        symbol=base_mod.SYMBOL,
        initial_capital=INITIAL_CAPITAL_EACH,
        commission=base_mod.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    helper_mod.configure_baseline_params(bt)
    bt.run(df_1m, df_4h, backtest_start_date=base_mod.BACKTEST_START)

    metrics = helper_mod.calculate_metrics(bt, INITIAL_CAPITAL_EACH)
    eq = prepare_equity_df(bt)
    trades = prepare_trades_df(bt)

    events = pd.DataFrame(getattr(bt, "regime_events", []))
    if not events.empty:
        events["timestamp"] = pd.to_datetime(events["timestamp"])
        events = events.sort_values("timestamp").reset_index(drop=True)

    regime_stats = summarize_regime_stats(getattr(bt, "regime_stats", {}))
    return {
        "variant": variant,
        "bt": bt,
        "metrics": metrics,
        "eq": eq,
        "trades": trades,
        "regime_events": events,
        "regime_stats": regime_stats,
    }


def build_total_curve(eq_case1: pd.DataFrame, eq_case2: pd.DataFrame) -> pd.DataFrame:
    c1 = eq_case1[["timestamp", "equity"]].rename(columns={"equity": "equity_case1"})
    c2 = eq_case2[["timestamp", "equity"]].rename(columns={"equity": "equity_case2"})
    out = pd.merge(c1, c2, on="timestamp", how="outer").sort_values("timestamp").reset_index(drop=True)
    out["equity_case1"] = out["equity_case1"].ffill()
    out["equity_case2"] = out["equity_case2"].ffill()
    out = out.dropna(subset=["equity_case1", "equity_case2"]).copy()
    out["equity_total"] = out["equity_case1"] + out["equity_case2"]
    return out


def compute_curve_stats(curve: pd.DataFrame, col: str, initial_capital: float) -> dict:
    s = curve[col].astype(float)
    final_equity = float(s.iloc[-1])
    total_return_pct = ((final_equity / float(initial_capital)) - 1.0) * 100.0

    if len(curve) > 1:
        elapsed_days = (curve["timestamp"].iloc[-1] - curve["timestamp"].iloc[0]).total_seconds() / 86400.0
        years = max(elapsed_days / 365.25, 1e-9)
        cagr_pct = ((final_equity / float(initial_capital)) ** (1.0 / years) - 1.0) * 100.0
    else:
        cagr_pct = np.nan

    dd = (s - s.cummax()) / s.cummax().replace(0, np.nan) * 100.0
    mdd = float(dd.min()) if len(dd) else np.nan
    calmar = (cagr_pct / abs(mdd)) if (pd.notna(cagr_pct) and pd.notna(mdd) and mdd != 0) else np.nan
    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": abs(mdd) if pd.notna(mdd) else np.nan,
        "calmar_ratio": calmar,
    }


def compute_window_stats(curve: pd.DataFrame, col: str, window_start: pd.Timestamp, window_end: pd.Timestamp) -> dict:
    if curve.empty:
        return {
            "window_start": window_start,
            "window_end": window_end,
            "window_start_equity": np.nan,
            "window_end_equity": np.nan,
            "window_return_pct": np.nan,
            "window_mdd_pct": np.nan,
        }

    c = curve.copy()
    c["timestamp"] = pd.to_datetime(c["timestamp"])
    c = c[(c["timestamp"] >= window_start) & (c["timestamp"] <= window_end)].copy()
    if len(c) < 2:
        return {
            "window_start": window_start,
            "window_end": window_end,
            "window_start_equity": np.nan,
            "window_end_equity": np.nan,
            "window_return_pct": np.nan,
            "window_mdd_pct": np.nan,
        }

    s = c[col].astype(float)
    st = float(s.iloc[0])
    en = float(s.iloc[-1])
    ret = ((en / st) - 1.0) * 100.0 if st > 0 else np.nan
    dd = (s - s.cummax()) / s.cummax().replace(0, np.nan) * 100.0
    mdd = abs(float(dd.min())) if len(dd) else np.nan
    return {
        "window_start": window_start,
        "window_end": window_end,
        "window_start_equity": st,
        "window_end_equity": en,
        "window_return_pct": ret,
        "window_mdd_pct": mdd,
    }

def save_plot(total_map: dict[str, pd.DataFrame], case1_map: dict[str, pd.DataFrame], eq_case2: pd.DataFrame):
    palette = {
        "baseline_hedge5x": "#1f77b4",
        "r2_soft_off_block_hedgeopen": "#ff7f0e",
        "r2_soft_off_keep_hedgeopen": "#2ca02c",
    }

    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True, gridspec_kw={"height_ratios": [1.2, 1.0, 1.0]})
    ax0, ax1, ax2 = axes

    for v in VARIANT_ORDER:
        tc = total_map[v]
        ax0.plot(tc["timestamp"], tc["equity_total"], linewidth=1.05, color=palette[v], label=f"Total ({VARIANT_LABELS[v]})")
    ax0.axhline(INITIAL_CAPITAL_EACH * 2.0, color="#777777", linestyle="--", linewidth=0.9, label="Start 2000")
    ax0.set_title("46 Study: Baseline vs R2 Soft-OFF (hedge-open policy) + Fixed Case2")
    ax0.set_ylabel("Total Equity")
    ax0.grid(True, alpha=0.2)
    ax0.legend(loc="upper left", ncol=2)

    for v in VARIANT_ORDER:
        eq = case1_map[v]
        ax1.plot(eq["timestamp"], eq["equity"], linewidth=1.05, color=palette[v], label=VARIANT_LABELS[v])
    ax1.axhline(INITIAL_CAPITAL_EACH, color="#777777", linestyle="--", linewidth=0.9)
    ax1.set_ylabel("Case1 Equity")
    ax1.grid(True, alpha=0.2)
    ax1.legend(loc="upper left", ncol=2)

    ax2.plot(eq_case2["timestamp"], eq_case2["equity"], color="#111111", linewidth=1.05, label="Case2 (fixed, study42)")
    ax2.axhline(INITIAL_CAPITAL_EACH, color="#777777", linestyle="--", linewidth=0.9)
    ax2.set_ylabel("Case2 Equity")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.2)
    ax2.legend(loc="upper left")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def df_to_md_table(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["(empty)"]
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in df.iterrows():
        vals = []
        for c in df.columns:
            v = r[c]
            if isinstance(v, float):
                vals.append(_fmt(v, 4))
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def save_report(metrics_df: pd.DataFrame, case1_df: pd.DataFrame, stress_df: pd.DataFrame):
    regime_def_df = pd.DataFrame(
        {
            "variant": VARIANT_ORDER,
            "label": [VARIANT_LABELS[x] for x in VARIANT_ORDER],
            "off_rule": [VARIANT_OFF_RULE[x] for x in VARIANT_ORDER],
            "on_rule": [VARIANT_ON_RULE[x] for x in VARIANT_ORDER],
            "off_to_on_cooldown_4h_bars": OFF_MIN_BARS_4H,
        }
    )

    lines: list[str] = []
    lines.append("# 46 백테스트: Baseline(hedge5x) vs R2 Soft-OFF 변형 비교")
    lines.append("")
    lines.append("## 구성")
    lines.append("- 기본 구조: `Case1 + Case2` 합산 Total.")
    lines.append("- 비교군에 `Case1 baseline(hedge5x)` 포함.")
    lines.append("- Case2는 study-42 설정 그대로 고정.")
    lines.append("- 실험군은 R2(bearish mature) Soft-OFF 2종.")
    lines.append("  - block_hedge_open: OFF 중 hedge 신규 오픈 차단")
    lines.append("  - keep_hedge_open: OFF 중에도 hedge 신규 오픈 허용")
    lines.append("")
    lines.append("## OFF 동작(요청 반영)")
    lines.append("- `Soft OFF`: 신규 진입 중지 + DCA/REENTRY 중지.")
    lines.append("- hedge 동작은 variant별 정책으로 분리 비교.")
    lines.append("- 기존 포지션은 TP/SL/청산 로직 유지.")
    lines.append("- 상태 갱신은 4h 버킷에서만 수행 (no-lookahead 정렬 유지).")
    lines.append(f"- OFF -> ON 전환은 최소 `{OFF_MIN_BARS_4H}`개 4h bar 쿨다운.")
    lines.append("- ON 조건은 `bullish and run_len_4h >= 2` (히스테리시스).")
    lines.append("")
    lines.append("## Variant 정의")
    lines.extend(df_to_md_table(regime_def_df))
    lines.append("")
    lines.append("## 성과 요약")
    lines.extend(df_to_md_table(metrics_df))
    lines.append("")
    lines.append("## Case1 + 상태 통계")
    lines.extend(df_to_md_table(case1_df))
    lines.append("")
    lines.append("## 스트레스 윈도우 비교 (2025-10-01 ~ 2026-02-12)")
    lines.extend(df_to_md_table(stress_df))
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVE_CSV}`")
    lines.append(f"- Case1 regime stats CSV: `{OUT_CASE1_REGIME_CSV}`")
    lines.append(f"- Regime events CSV: `{OUT_REGIME_EVENTS_CSV}`")
    lines.append(f"- Stress window CSV: `{OUT_STRESS_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8-sig")


def run():
    base = load_module("m002_46", BASE_002_PATH)
    helper = load_module("m04_46", BASE_04_PATH)
    m40 = load_module("m40_46", CASE1_BASE_PATH)
    m32 = load_module("m32_46", CASE2_BASE_PATH)
    m42 = load_module("m42_46", CASE2_WRAPPER_PATH)

    df_1m, df_4h = m40.load_data_no_filter(base)
    df_1m = df_1m[(df_1m.index >= base.BACKTEST_START) & (df_1m.index <= base.BACKTEST_END)].copy()

    # Case2 fixed (same as study42)
    Case2Class = m42.build_case2_class(m32)
    bt_case2 = Case2Class(
        base_module=base,
        symbol=base.SYMBOL,
        initial_capital=INITIAL_CAPITAL_EACH,
        commission=base.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    helper.configure_baseline_params(bt_case2)
    bt_case2.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)
    eq_case2 = prepare_equity_df(bt_case2)
    m_case2 = helper.calculate_metrics(bt_case2, INITIAL_CAPITAL_EACH)

    # Case1 variants
    runs: dict[str, dict] = {}
    for v in VARIANT_ORDER:
        cls = build_case1_regime_class(m40, v)
        runs[v] = run_case1_variant(v, cls, base, helper, df_1m, df_4h)

    total_map: dict[str, pd.DataFrame] = {}
    case1_map: dict[str, pd.DataFrame] = {}

    metric_rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    case1_rows: list[dict] = []
    stress_rows: list[dict] = []
    regime_event_rows: list[pd.DataFrame] = []

    for v in VARIANT_ORDER:
        eq1 = runs[v]["eq"]
        case1_map[v] = eq1
        total_curve = build_total_curve(eq1, eq_case2)
        total_map[v] = total_curve

        tc = total_curve.copy()
        tc["variant"] = v
        curve_rows.append(tc)

        m1 = runs[v]["metrics"]
        mt = compute_curve_stats(total_curve, "equity_total", INITIAL_CAPITAL_EACH * 2.0)
        rs = runs[v]["regime_stats"]

        metric_rows.append(
            {
                "curve": f"total_{v}_plus_case2",
                "variant": v,
                "variant_label": VARIANT_LABELS[v],
                "initial_capital": INITIAL_CAPITAL_EACH * 2.0,
                **mt,
                "trades": int(m1.get("trades", 0)) + int(m_case2.get("trades", 0)),
                "long_trades": int(m1.get("long_trades", 0)) + int(m_case2.get("long_trades", 0)),
                "short_trades": int(m1.get("short_trades", 0)) + int(m_case2.get("short_trades", 0)),
                "win_rate_pct": np.nan,
                "profit_factor": np.nan,
                "case1_off_ratio_1m_pct": rs.get("off_ratio_1m_pct", np.nan),
                "case1_off_ratio_4h_pct": rs.get("off_ratio_4h_pct", np.nan),
            }
        )
        metric_rows.append(
            {
                "curve": f"case1_{v}",
                "variant": v,
                "variant_label": VARIANT_LABELS[v],
                "initial_capital": INITIAL_CAPITAL_EACH,
                **{k: m1.get(k, np.nan) for k in ["final_equity", "total_return_pct", "cagr_pct", "max_drawdown_pct", "calmar_ratio"]},
                "trades": m1.get("trades", 0),
                "long_trades": m1.get("long_trades", 0),
                "short_trades": m1.get("short_trades", 0),
                "win_rate_pct": m1.get("win_rate_pct", np.nan),
                "profit_factor": m1.get("profit_factor", np.nan),
                "case1_off_ratio_1m_pct": rs.get("off_ratio_1m_pct", np.nan),
                "case1_off_ratio_4h_pct": rs.get("off_ratio_4h_pct", np.nan),
            }
        )

        case1_rows.append(
            {
                "case1_variant": v,
                "variant_label": VARIANT_LABELS[v],
                "off_switches": rs.get("off_switches", 0),
                "on_switches": rs.get("on_switches", 0),
                "off_ratio_1m_pct": rs.get("off_ratio_1m_pct", np.nan),
                "off_ratio_4h_pct": rs.get("off_ratio_4h_pct", np.nan),
                "blocked_open_signals": rs.get("blocked_open_signals", 0),
                "blocked_add_signals": rs.get("blocked_add_signals", 0),
                "blocked_hedge_open_signals": rs.get("blocked_hedge_open_signals", 0),
                "stress_off_ratio_1m_pct": rs.get("stress_off_ratio_1m_pct", np.nan),
                "final_equity": m1.get("final_equity", np.nan),
                "total_return_pct": m1.get("total_return_pct", np.nan),
                "cagr_pct": m1.get("cagr_pct", np.nan),
                "max_drawdown_pct": m1.get("max_drawdown_pct", np.nan),
                "calmar_ratio": m1.get("calmar_ratio", np.nan),
                "trades": m1.get("trades", 0),
                "win_rate_pct": m1.get("win_rate_pct", np.nan),
                "profit_factor": m1.get("profit_factor", np.nan),
            }
        )

        w_case1 = compute_window_stats(eq1, "equity", STRESS_START, STRESS_END)
        w_total = compute_window_stats(total_curve, "equity_total", STRESS_START, STRESS_END)
        stress_rows.append(
            {
                "variant": v,
                "variant_label": VARIANT_LABELS[v],
                "case1_window_return_pct": w_case1["window_return_pct"],
                "case1_window_mdd_pct": w_case1["window_mdd_pct"],
                "total_window_return_pct": w_total["window_return_pct"],
                "total_window_mdd_pct": w_total["window_mdd_pct"],
                "stress_off_ratio_1m_pct": rs.get("stress_off_ratio_1m_pct", np.nan),
                "window_start_equity_case1": w_case1["window_start_equity"],
                "window_end_equity_case1": w_case1["window_end_equity"],
                "window_start_equity_total": w_total["window_start_equity"],
                "window_end_equity_total": w_total["window_end_equity"],
            }
        )

        ev = runs[v]["regime_events"]
        if not ev.empty:
            e2 = ev.copy()
            e2["variant"] = v
            regime_event_rows.append(e2)

    metric_rows.append(
        {
            "curve": "case2_study42_fixed",
            "variant": "case2",
            "variant_label": "Case2 fixed",
            "initial_capital": INITIAL_CAPITAL_EACH,
            **{k: m_case2.get(k, np.nan) for k in ["final_equity", "total_return_pct", "cagr_pct", "max_drawdown_pct", "calmar_ratio"]},
            "trades": m_case2.get("trades", 0),
            "long_trades": m_case2.get("long_trades", 0),
            "short_trades": m_case2.get("short_trades", 0),
            "win_rate_pct": m_case2.get("win_rate_pct", np.nan),
            "profit_factor": m_case2.get("profit_factor", np.nan),
            "case1_off_ratio_1m_pct": np.nan,
            "case1_off_ratio_4h_pct": np.nan,
        }
    )

    metrics_df = pd.DataFrame(metric_rows)
    metrics_df.to_csv(OUT_CSV, index=False)

    pd.concat(curve_rows, ignore_index=True).to_csv(OUT_CURVE_CSV, index=False)

    case1_df = pd.DataFrame(case1_rows)
    case1_df.to_csv(OUT_CASE1_REGIME_CSV, index=False)

    stress_df = pd.DataFrame(stress_rows)
    stress_df.to_csv(OUT_STRESS_CSV, index=False)

    if regime_event_rows:
        pd.concat(regime_event_rows, ignore_index=True).to_csv(OUT_REGIME_EVENTS_CSV, index=False)
    else:
        pd.DataFrame(
            columns=[
                "timestamp",
                "variant",
                "variant_id",
                "action",
                "reason",
                "enabled_after",
                "off_bars_4h_counter",
                "trend_4h_confirmed",
                "run_len_4h",
                "flip_count_30_4h",
                "near_ema_ratio_30_4h",
                "vol20_confirmed",
                "vol20_p80_2y",
                "vol20_p65_2y",
                "risk_score_24",
                "dd30_confirmed",
            ]
        ).to_csv(OUT_REGIME_EVENTS_CSV, index=False)

    save_plot(total_map, case1_map, eq_case2)
    save_report(metrics_df, case1_df, stress_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVE_CSV}")
    print(f"saved_case1_stats={OUT_CASE1_REGIME_CSV}")
    print(f"saved_variant_events={OUT_REGIME_EVENTS_CSV}")
    print(f"saved_stress_window={OUT_STRESS_CSV}")
    print(f"saved_report={OUT_MD}")

    for v in VARIANT_ORDER:
        m = runs[v]["metrics"]
        rs = runs[v]["regime_stats"]
        print(
            f"case1_{v}_final={_fmt(m.get('final_equity'))}, "
            f"cagr={_fmt(m.get('cagr_pct'))}%, mdd={_fmt(m.get('max_drawdown_pct'))}%, "
            f"off1m={_fmt(rs.get('off_ratio_1m_pct'))}%"
        )
    print(f"case2_final={_fmt(m_case2.get('final_equity'))}, cagr={_fmt(m_case2.get('cagr_pct'))}%, mdd={_fmt(m_case2.get('max_drawdown_pct'))}%")


if __name__ == "__main__":
    run()
