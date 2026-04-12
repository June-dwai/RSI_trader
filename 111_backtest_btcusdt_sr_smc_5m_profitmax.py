from __future__ import annotations

import importlib.util
import itertools
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OUT_BASE = "111_backtest_btcusdt_sr_smc_5m_profitmax"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_TRADES_CSV = Path(f"{OUT_BASE}_trades.csv")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_selected_curves.csv")

BASE_107_PATH = Path("107_backtest_btcusdt_4h_ema200_counter_gap_study.py")
BASE_109_PATH = Path("109_backtest_btcusdt_minus20_rsi15_case2_longonly_noreentry.py")
BASE_110_PATH = Path("110_backtest_btcusdt_gap_rsi15_case2_longonly_threshold_cases.py")

INITIAL_CAPITAL = 1000.0
COMMISSION = 0.0004
RESAMPLE_RULE = "5min"
CURVE_RESAMPLE_RULE = "1h"

ZONE_ANCHORS = ["white_floor", "red_floor", "overlap"]
LOOKBACK_GRID = [12, 24, 36]
RECLAIM_GRID = [1, 2, 3]
CONFIRM_MODES = ["close_above_white", "close_above_prev3bar_high", "proxy_bos"]

ENTRY_SCALE_GRID = [0.30, 0.45, 0.60]
MAX_ENTRIES_GRID = [1, 2, 3]
ADD_TRIGGER_GRID = ["none", "avg_minus_0.5ATR", "retest_red_floor", "ob_revisit"]
ADD_PROFILE_GRID = ["equal", "taper"]
COOLDOWN_GRID = [0, 2, 4]
STOP_MODE_GRID = ["sweep_low-0.2ATR", "red_floor-0.15ATR", "ob_low-0.1ATR"]
TP_MODE_GRID = ["2R_fixed", "3R_fixed", "partial_1.5R_runner_to_bearish_ob", "trail_white_avg_after_2R"]
MAX_HOLD_GRID = [24, 48, 96]

BASE_STAGE1_CFG = {
    "entry_scale": 0.45,
    "max_entries": 2,
    "add_trigger": "avg_minus_0.5ATR",
    "add_profile": "equal",
    "cooldown_bars": 2,
    "stop_mode": "sweep_low-0.2ATR",
    "tp_mode": "partial_1.5R_runner_to_bearish_ob",
    "max_hold_bars": 48,
}


@dataclass(frozen=True)
class SeedConfig:
    entry_family: str
    zone_anchor: str
    sweep_lookback: int
    reclaim_window: int
    confirm_mode: str

    def short_name(self) -> str:
        if self.entry_family == "band_bounce":
            return f"{self.entry_family}_{self.zone_anchor}"
        return (
            f"{self.entry_family}_{self.zone_anchor}"
            f"_lb{self.sweep_lookback}_rw{self.reclaim_window}_{self.confirm_mode}"
        )


@dataclass(frozen=True)
class StrategyConfig:
    seed: SeedConfig
    entry_scale: float = 0.45
    max_entries: int = 2
    add_trigger: str = "avg_minus_0.5ATR"
    add_profile: str = "equal"
    cooldown_bars: int = 2
    stop_mode: str = "sweep_low-0.2ATR"
    tp_mode: str = "partial_1.5R_runner_to_bearish_ob"
    max_hold_bars: int = 48
    smc_gate_mode: str = "none"
    stage: str = "stage1_coarse"

    def normalized(self) -> "StrategyConfig":
        if self.max_entries <= 1:
            return replace(self, max_entries=1, add_trigger="none", add_profile="equal")
        return self

    def variant(self) -> str:
        return (
            f"{self.stage}_{self.seed.short_name()}"
            f"_es{self.entry_scale:.2f}"
            f"_me{self.max_entries}"
            f"_add{self.add_trigger}"
            f"_{self.add_profile}"
            f"_cd{self.cooldown_bars}"
            f"_stop{self.stop_mode}"
            f"_tp{self.tp_mode}"
            f"_hold{self.max_hold_bars}"
            f"_gate{self.smc_gate_mode}"
        )


@dataclass
class SimulationArtifacts:
    metrics: dict
    curve: pd.DataFrame | None = None
    trades: pd.DataFrame | None = None


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


def _edge_from_bool(mask: np.ndarray) -> np.ndarray:
    mask = np.asarray(mask, dtype=bool)
    if mask.size == 0:
        return mask
    return mask & ~np.r_[False, mask[:-1]]


def _rolling_any(mask: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return np.asarray(mask, dtype=bool)
    ser = pd.Series(np.asarray(mask, dtype=int))
    return ser.rolling(window, min_periods=1).max().to_numpy(dtype=float) > 0


def _ffill_numeric(values: np.ndarray) -> np.ndarray:
    return pd.Series(values).ffill().to_numpy(dtype=float)


def _resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    return (
        df.resample(rule, label="right", closed="right")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna(subset=["open", "high", "low", "close"])
    )


def _resample_close(df: pd.DataFrame, rule: str) -> pd.Series:
    return df["close"].resample(rule, label="right", closed="right").last().dropna()


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    return pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)


def _atr_series(high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
    return _true_range(high, low, close).rolling(length, min_periods=length).mean()


def _atr_array(high: np.ndarray, low: np.ndarray, close: np.ndarray, length: int) -> np.ndarray:
    ser = _true_range(pd.Series(high), pd.Series(low), pd.Series(close))
    return ser.rolling(length, min_periods=length).mean().to_numpy(dtype=float)


def _map_series_to_target(series: pd.Series, target_index: pd.DatetimeIndex) -> pd.Series:
    mapped = series.reindex(target_index, method="ffill")
    mapped.index = target_index
    return mapped


def _zone_bounds(df: pd.DataFrame, anchor: str) -> tuple[np.ndarray, np.ndarray]:
    white = df["white_floor"].to_numpy(dtype=float)
    red = df["red_floor"].to_numpy(dtype=float)
    if anchor == "white_floor":
        return white.copy(), white.copy()
    if anchor == "red_floor":
        return red.copy(), red.copy()
    return np.minimum(white, red), np.maximum(white, red)


def _better_metrics(a: dict, b: dict | None) -> bool:
    if b is None:
        return True
    key_a = (float(a["final_equity"]), float(a["cagr_pct"]), -float(a["max_drawdown_pct"]))
    key_b = (float(b["final_equity"]), float(b["cagr_pct"]), -float(b["max_drawdown_pct"]))
    return key_a > key_b


def _order_scales(entry_scale: float, max_entries: int, add_profile: str) -> list[float]:
    if max_entries <= 1:
        return [entry_scale]
    if add_profile == "taper":
        tail = [0.70 * entry_scale, 0.50 * entry_scale]
    else:
        tail = [entry_scale, entry_scale]
    return [entry_scale] + tail[: max_entries - 1]


def _close_position(capital: float, avg_entry: float, qty: float, price: float) -> tuple[float, float]:
    close_commission = qty * price * COMMISSION
    pnl = (price - avg_entry) * qty - close_commission
    return capital + pnl, pnl


def _realize_partial(capital: float, avg_entry: float, qty: float, price: float) -> tuple[float, float]:
    close_commission = qty * price * COMMISSION
    pnl = (price - avg_entry) * qty - close_commission
    return capital + pnl, pnl


def compute_curve_stats(curve: pd.DataFrame, initial_capital: float) -> dict:
    series = curve["equity"].astype(float)
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


def _compress_curve(curve: pd.DataFrame, rule: str = CURVE_RESAMPLE_RULE) -> pd.DataFrame:
    out = curve.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    return (
        out.set_index("timestamp")
        .resample(rule)
        .last()
        .dropna(subset=["equity"])
        .reset_index()
    )


def compute_exact_smc_features(bars: pd.DataFrame) -> pd.DataFrame:
    high = bars["high"].to_numpy(dtype=float)
    low = bars["low"].to_numpy(dtype=float)
    close = bars["close"].to_numpy(dtype=float)
    n = len(bars)

    atr200 = _atr_array(high, low, close, 200)
    high_volatility = (high - low) >= (2.0 * atr200)
    parsed_high = np.where(high_volatility, low, high)
    parsed_low = np.where(high_volatility, high, low)

    internal_bullish_choch = np.zeros(n, dtype=bool)
    internal_bullish_bos = np.zeros(n, dtype=bool)
    weak_low_active = np.zeros(n, dtype=bool)
    strong_high_active = np.zeros(n, dtype=bool)
    weak_low_sweep = np.zeros(n, dtype=bool)
    bullish_internal_ob_revisit = np.zeros(n, dtype=bool)
    active_bullish_internal_ob = np.zeros(n, dtype=bool)

    exact_bullish_internal_ob_top = np.full(n, np.nan, dtype=float)
    exact_bullish_internal_ob_bottom = np.full(n, np.nan, dtype=float)
    exact_bearish_internal_ob_top = np.full(n, np.nan, dtype=float)
    exact_bearish_internal_ob_bottom = np.full(n, np.nan, dtype=float)
    strong_high_level = np.full(n, np.nan, dtype=float)
    weak_low_level = np.full(n, np.nan, dtype=float)

    def new_pivot() -> dict[str, float | int | bool]:
        return {"current": np.nan, "crossed": False, "idx": -1}

    internal_high = new_pivot()
    internal_low = new_pivot()
    swing_high = new_pivot()
    swing_low = new_pivot()

    internal_leg = 0
    swing_leg = 0
    internal_trend = 0
    swing_trend = 0

    trailing_top = high[0]
    trailing_bottom = low[0]
    bullish_blocks: list[dict[str, float]] = []
    bearish_blocks: list[dict[str, float]] = []

    def update_pivot(pivot: dict[str, float | int | bool], level: float, idx: int) -> None:
        pivot["current"] = float(level)
        pivot["crossed"] = False
        pivot["idx"] = int(idx)

    def store_order_block(start_idx: int, current_idx: int, bullish: bool) -> None:
        nonlocal bullish_blocks, bearish_blocks
        if start_idx < 0:
            return
        left = max(0, min(start_idx, current_idx - 1))
        right = max(left + 1, current_idx)
        if bullish:
            rel_idx = int(np.nanargmin(parsed_low[left:right]))
            source_idx = left + rel_idx
            bullish_blocks.insert(0, {"top": float(parsed_high[source_idx]), "bottom": float(parsed_low[source_idx])})
            bullish_blocks = bullish_blocks[:20]
        else:
            rel_idx = int(np.nanargmax(parsed_high[left:right]))
            source_idx = left + rel_idx
            bearish_blocks.insert(0, {"top": float(parsed_high[source_idx]), "bottom": float(parsed_low[source_idx])})
            bearish_blocks = bearish_blocks[:20]

    for i in range(n):
        prior_trailing_bottom = trailing_bottom
        if swing_trend == -1 and np.isfinite(prior_trailing_bottom) and low[i] < prior_trailing_bottom:
            weak_low_sweep[i] = True

        trailing_top = max(trailing_top, float(high[i]))
        trailing_bottom = min(trailing_bottom, float(low[i]))

        if i >= 5:
            ref_idx = i - 5
            new_leg = internal_leg
            if high[ref_idx] > np.nanmax(high[ref_idx + 1 : i + 1]):
                new_leg = 0
            elif low[ref_idx] < np.nanmin(low[ref_idx + 1 : i + 1]):
                new_leg = 1
            if new_leg != internal_leg:
                internal_leg = new_leg
                if new_leg == 1:
                    update_pivot(internal_low, low[ref_idx], ref_idx)
                else:
                    update_pivot(internal_high, high[ref_idx], ref_idx)

        if i >= 50:
            ref_idx = i - 50
            new_leg = swing_leg
            if high[ref_idx] > np.nanmax(high[ref_idx + 1 : i + 1]):
                new_leg = 0
            elif low[ref_idx] < np.nanmin(low[ref_idx + 1 : i + 1]):
                new_leg = 1
            if new_leg != swing_leg:
                swing_leg = new_leg
                if new_leg == 1:
                    update_pivot(swing_low, low[ref_idx], ref_idx)
                    trailing_bottom = float(low[ref_idx])
                else:
                    update_pivot(swing_high, high[ref_idx], ref_idx)
                    trailing_top = float(high[ref_idx])

        if i > 0:
            internal_high_level = float(internal_high["current"]) if np.isfinite(internal_high["current"]) else np.nan
            internal_low_level = float(internal_low["current"]) if np.isfinite(internal_low["current"]) else np.nan
            swing_high_level_value = float(swing_high["current"]) if np.isfinite(swing_high["current"]) else np.nan
            swing_low_level_value = float(swing_low["current"]) if np.isfinite(swing_low["current"]) else np.nan

            if (
                np.isfinite(internal_high_level)
                and not bool(internal_high["crossed"])
                and close[i - 1] <= internal_high_level
                and close[i] > internal_high_level
                and (not np.isfinite(swing_high_level_value) or not np.isclose(internal_high_level, swing_high_level_value))
            ):
                internal_bullish_choch[i] = internal_trend == -1
                internal_bullish_bos[i] = internal_trend != -1
                internal_high["crossed"] = True
                internal_trend = 1
                store_order_block(int(internal_high["idx"]), i, bullish=True)

            if (
                np.isfinite(internal_low_level)
                and not bool(internal_low["crossed"])
                and close[i - 1] >= internal_low_level
                and close[i] < internal_low_level
                and (not np.isfinite(swing_low_level_value) or not np.isclose(internal_low_level, swing_low_level_value))
            ):
                internal_low["crossed"] = True
                internal_trend = -1
                store_order_block(int(internal_low["idx"]), i, bullish=False)

            if (
                np.isfinite(swing_high_level_value)
                and not bool(swing_high["crossed"])
                and close[i - 1] <= swing_high_level_value
                and close[i] > swing_high_level_value
            ):
                swing_high["crossed"] = True
                swing_trend = 1

            if (
                np.isfinite(swing_low_level_value)
                and not bool(swing_low["crossed"])
                and close[i - 1] >= swing_low_level_value
                and close[i] < swing_low_level_value
            ):
                swing_low["crossed"] = True
                swing_trend = -1

        bullish_blocks = [ob for ob in bullish_blocks if not (low[i] < ob["bottom"])]
        bearish_blocks = [ob for ob in bearish_blocks if not (high[i] > ob["top"])]

        weak_low_active[i] = swing_trend == -1
        strong_high_active[i] = swing_trend == -1
        strong_high_level[i] = trailing_top
        weak_low_level[i] = trailing_bottom

        if bullish_blocks:
            latest = bullish_blocks[0]
            active_bullish_internal_ob[i] = True
            exact_bullish_internal_ob_top[i] = latest["top"]
            exact_bullish_internal_ob_bottom[i] = latest["bottom"]
            bullish_internal_ob_revisit[i] = low[i] <= latest["top"] and high[i] >= latest["bottom"]

        if bearish_blocks:
            latest = bearish_blocks[0]
            exact_bearish_internal_ob_top[i] = latest["top"]
            exact_bearish_internal_ob_bottom[i] = latest["bottom"]

    return pd.DataFrame(
        {
            "internal_bullish_choch": internal_bullish_choch,
            "internal_bullish_bos": internal_bullish_bos,
            "active_bullish_internal_ob": active_bullish_internal_ob,
            "bullish_internal_ob_revisit": bullish_internal_ob_revisit,
            "exact_bullish_internal_ob_top": exact_bullish_internal_ob_top,
            "exact_bullish_internal_ob_bottom": exact_bullish_internal_ob_bottom,
            "exact_bearish_internal_ob_top": exact_bearish_internal_ob_top,
            "exact_bearish_internal_ob_bottom": exact_bearish_internal_ob_bottom,
            "weak_low_active": weak_low_active,
            "strong_high_active": strong_high_active,
            "weak_low_sweep": weak_low_sweep,
            "strong_high_level": strong_high_level,
            "weak_low_level": weak_low_level,
        },
        index=bars.index,
    )


def prepare_market_111(df_1m: pd.DataFrame) -> pd.DataFrame:
    out_1m = df_1m.copy().sort_index()
    if not isinstance(out_1m.index, pd.DatetimeIndex):
        out_1m.index = pd.to_datetime(out_1m.index)

    bars_5m = _resample_ohlc(out_1m, RESAMPLE_RULE)
    target_index = bars_5m.index

    ema_fast_1m = out_1m["close"].ewm(span=20, adjust=False).mean()
    ema_slow_1m = out_1m["close"].ewm(span=1800, adjust=False).mean()
    atr_1m = _atr_series(out_1m["high"], out_1m["low"], out_1m["close"], 14)

    ema_slow_2m = _resample_close(out_1m, "2min").ewm(span=1800, adjust=False).mean()
    ema_slow_3m = _resample_close(out_1m, "3min").ewm(span=1800, adjust=False).mean()
    ema_slow_5m = _resample_close(out_1m, "5min").ewm(span=1800, adjust=False).mean()

    fast_5m = _map_series_to_target(ema_fast_1m, target_index)
    slow_1m_5m = _map_series_to_target(ema_slow_1m, target_index)
    slow_2m_5m = _map_series_to_target(ema_slow_2m, target_index)
    slow_3m_5m = _map_series_to_target(ema_slow_3m, target_index)
    slow_5m_5m = _map_series_to_target(ema_slow_5m, target_index)
    atr_1m_5m = _map_series_to_target(atr_1m, target_index)

    bars_5m["white_avg"] = (fast_5m + slow_1m_5m) * 0.5
    bars_5m["red_avg"] = (fast_5m + slow_2m_5m) * 0.5
    bars_5m["yellow_avg"] = (fast_5m + slow_3m_5m) * 0.5
    bars_5m["green_avg"] = (fast_5m + slow_5m_5m) * 0.5

    bars_5m["white_floor"] = bars_5m["white_avg"] - atr_1m_5m
    bars_5m["red_floor"] = bars_5m["red_avg"] - atr_1m_5m
    bars_5m["yellow_floor"] = bars_5m["yellow_avg"] - atr_1m_5m
    bars_5m["green_floor"] = bars_5m["green_avg"] - atr_1m_5m

    bars_5m["overlap_low"] = np.minimum(bars_5m["white_floor"], bars_5m["red_floor"])
    bars_5m["overlap_high"] = np.maximum(bars_5m["white_floor"], bars_5m["red_floor"])
    bars_5m["atr_5m"] = _atr_series(bars_5m["high"], bars_5m["low"], bars_5m["close"], 14)
    bars_5m["long_regime"] = (
        (bars_5m["white_avg"] > bars_5m["white_avg"].shift(6))
        & (bars_5m["red_avg"] > bars_5m["red_avg"].shift(6))
        & (bars_5m["close"] > bars_5m["red_floor"])
    )

    bars_5m["prev3_high"] = bars_5m["high"].rolling(3, min_periods=3).max().shift(1)
    bars_5m["proxy_bos_level"] = bars_5m["high"].rolling(5, min_periods=5).max().shift(1)
    bars_5m["proxy_bos_up"] = (
        (bars_5m["close"] > bars_5m["proxy_bos_level"])
        & ~(bars_5m["close"].shift(1) > bars_5m["proxy_bos_level"].shift(1))
    )

    bearish_top = np.where(bars_5m["close"] < bars_5m["open"], bars_5m["open"], np.nan)
    bearish_bottom = np.where(bars_5m["close"] < bars_5m["open"], bars_5m["close"], np.nan)
    bullish_supply_top = np.where(bars_5m["close"] > bars_5m["open"], bars_5m["high"], np.nan)
    bullish_supply_bottom = np.where(bars_5m["close"] > bars_5m["open"], bars_5m["open"], np.nan)
    bars_5m["proxy_ob_top"] = _ffill_numeric(bearish_top)
    bars_5m["proxy_ob_bottom"] = _ffill_numeric(bearish_bottom)
    bars_5m["proxy_bearish_supply_top"] = _ffill_numeric(bullish_supply_top)
    bars_5m["proxy_bearish_supply_bottom"] = _ffill_numeric(bullish_supply_bottom)

    exact = compute_exact_smc_features(bars_5m)
    bars_5m = pd.concat([bars_5m, exact], axis=1)

    recent_high_20_prev = bars_5m["high"].rolling(20, min_periods=20).max().shift(1).to_numpy(dtype=float)
    bars_5m["runner_target_proxy"] = np.nanmax(
        np.column_stack(
            [
                recent_high_20_prev,
                bars_5m["strong_high_level"].to_numpy(dtype=float),
                bars_5m["proxy_bearish_supply_top"].to_numpy(dtype=float),
            ]
        ),
        axis=1,
    )
    bars_5m["band_touch_overlap"] = (
        (bars_5m["low"] <= bars_5m["overlap_high"])
        & (bars_5m["high"] >= bars_5m["overlap_low"])
    )
    recent_24_low = bars_5m["low"].rolling(24, min_periods=24).min().shift(1)
    bars_5m["proxy_sweep_low"] = (
        bars_5m["long_regime"]
        & (bars_5m["low"] < recent_24_low)
        & (bars_5m["low"] < bars_5m["overlap_low"])
    )

    bars_5m["timestamp"] = bars_5m.index
    bars_5m = bars_5m.dropna(subset=["white_avg", "red_avg", "white_floor", "red_floor", "atr_5m"]).copy()
    return bars_5m.reset_index(drop=True)


def build_stage1_signal_cache(market: pd.DataFrame) -> dict[SeedConfig, dict[str, np.ndarray | int]]:
    cache: dict[SeedConfig, dict[str, np.ndarray | int]] = {}
    n = len(market)
    bar_idx = np.arange(n, dtype=float)

    close = market["close"].to_numpy(dtype=float)
    high = market["high"].to_numpy(dtype=float)
    low = market["low"].to_numpy(dtype=float)
    long_regime = market["long_regime"].to_numpy(dtype=bool)
    white_avg = market["white_avg"].to_numpy(dtype=float)
    prev3_high = market["prev3_high"].to_numpy(dtype=float)
    proxy_bos_up = market["proxy_bos_up"].to_numpy(dtype=bool)
    proxy_ob_top = market["proxy_ob_top"].to_numpy(dtype=float)
    proxy_ob_bottom = market["proxy_ob_bottom"].to_numpy(dtype=float)

    confirm_cache = {
        "close_above_white": close > white_avg,
        "close_above_prev3bar_high": close > prev3_high,
        "proxy_bos": proxy_bos_up,
    }
    zone_cache = {anchor: _zone_bounds(market, anchor) for anchor in ZONE_ANCHORS}
    recent_low_cache = {
        lookback: market["low"].rolling(lookback, min_periods=lookback).min().shift(1).to_numpy(dtype=float)
        for lookback in LOOKBACK_GRID
    }

    def build_pack(mask: np.ndarray, stop_ref: np.ndarray, ob_low: np.ndarray, ob_high: np.ndarray) -> dict[str, np.ndarray | int]:
        signal_idx = np.flatnonzero(mask)
        return {
            "signal_mask": mask,
            "signal_idx": signal_idx.astype(int),
            "signal_stop_ref": stop_ref[signal_idx].astype(float),
            "signal_ob_low": ob_low[signal_idx].astype(float),
            "signal_ob_high": ob_high[signal_idx].astype(float),
            "signal_count": int(signal_idx.size),
        }

    for anchor in ZONE_ANCHORS:
        zone_low, zone_high = zone_cache[anchor]
        band_raw = long_regime & (low <= zone_high) & (high >= zone_low) & (close > white_avg)
        cache[SeedConfig("band_bounce", anchor, 12, 1, "close_above_white")] = build_pack(
            _edge_from_bool(band_raw),
            low.copy(),
            proxy_ob_bottom,
            proxy_ob_top,
        )

        for lookback in LOOKBACK_GRID:
            recent_low = recent_low_cache[lookback]
            sweep_event = long_regime & np.isfinite(recent_low) & (low < recent_low) & (low < zone_low)
            sweep_low_ff = _ffill_numeric(np.where(sweep_event, low, np.nan))
            sweep_idx_ff = _ffill_numeric(np.where(sweep_event, bar_idx, np.nan))

            for reclaim_window in RECLAIM_GRID:
                within = np.isfinite(sweep_idx_ff) & ((bar_idx - sweep_idx_ff) >= 1.0) & ((bar_idx - sweep_idx_ff) <= float(reclaim_window))
                for confirm_mode in CONFIRM_MODES:
                    reclaim_raw = within & confirm_cache[confirm_mode] & (close > zone_low)
                    reclaim_event = _edge_from_bool(reclaim_raw)
                    cache[SeedConfig("sweep_reclaim", anchor, lookback, reclaim_window, confirm_mode)] = build_pack(
                        reclaim_event,
                        sweep_low_ff,
                        proxy_ob_bottom,
                        proxy_ob_top,
                    )

                    reclaim_idx_ff = _ffill_numeric(np.where(reclaim_event, bar_idx, np.nan))
                    bos_window = np.isfinite(reclaim_idx_ff) & ((bar_idx - reclaim_idx_ff) >= 1.0) & ((bar_idx - reclaim_idx_ff) <= float(reclaim_window + 3))
                    bos_event = bos_window & proxy_bos_up
                    ob_overlap = np.isfinite(proxy_ob_top) & np.isfinite(proxy_ob_bottom) & (proxy_ob_top >= zone_low) & (proxy_ob_bottom <= zone_high)
                    bos_idx_ff = _ffill_numeric(np.where(bos_event & ob_overlap, bar_idx, np.nan))
                    active_ob_low = _ffill_numeric(np.where(bos_event & ob_overlap, proxy_ob_bottom, np.nan))
                    active_ob_high = _ffill_numeric(np.where(bos_event & ob_overlap, proxy_ob_top, np.nan))
                    revisit_window = np.isfinite(bos_idx_ff) & ((bar_idx - bos_idx_ff) >= 1.0) & ((bar_idx - bos_idx_ff) <= float(reclaim_window + 3))
                    revisit_raw = long_regime & revisit_window & np.isfinite(active_ob_low) & (low <= active_ob_high) & (high >= active_ob_low) & (close >= active_ob_low)
                    cache[SeedConfig("choch_ob_reclaim", anchor, lookback, reclaim_window, confirm_mode)] = build_pack(
                        _edge_from_bool(revisit_raw),
                        np.minimum(sweep_low_ff, active_ob_low),
                        active_ob_low,
                        active_ob_high,
                    )

    return cache


def build_market_bundle(market: pd.DataFrame, df_1m: pd.DataFrame) -> dict:
    out_1m = df_1m.copy().sort_index()
    if not isinstance(out_1m.index, pd.DatetimeIndex):
        out_1m.index = pd.to_datetime(out_1m.index)

    ts1 = pd.to_datetime(out_1m.index).to_numpy(dtype="datetime64[ns]")
    ts5 = pd.to_datetime(market["timestamp"]).to_numpy(dtype="datetime64[ns]")
    minute_to_five_close_idx = pd.Index(ts5).get_indexer(ts1)
    minute_to_container_5_idx = np.searchsorted(ts5, ts1, side="left")
    five_next_minute_idx = np.searchsorted(ts1, ts5, side="right")

    return {
        "ts5": ts5,
        "open5": market["open"].to_numpy(dtype=float),
        "high5": market["high"].to_numpy(dtype=float),
        "low5": market["low"].to_numpy(dtype=float),
        "close5": market["close"].to_numpy(dtype=float),
        "white_avg": market["white_avg"].to_numpy(dtype=float),
        "red_floor": market["red_floor"].to_numpy(dtype=float),
        "atr5": market["atr_5m"].to_numpy(dtype=float),
        "proxy_ob_top": market["proxy_ob_top"].to_numpy(dtype=float),
        "proxy_ob_bottom": market["proxy_ob_bottom"].to_numpy(dtype=float),
        "runner_target_proxy": market["runner_target_proxy"].to_numpy(dtype=float),
        "exact_bearish_ob_bottom": market["exact_bearish_internal_ob_bottom"].to_numpy(dtype=float),
        "open1": out_1m["open"].to_numpy(dtype=float),
        "high1": out_1m["high"].to_numpy(dtype=float),
        "low1": out_1m["low"].to_numpy(dtype=float),
        "close1": out_1m["close"].to_numpy(dtype=float),
        "ts1": ts1,
        "minute_to_five_close_idx": minute_to_five_close_idx,
        "minute_to_container_5_idx": minute_to_container_5_idx,
        "five_next_minute_idx": five_next_minute_idx,
    }


def _resolve_stop_reference(cfg: StrategyConfig, bundle: dict, bar_idx: int, signal_stop_ref: float, signal_ob_low: float) -> float:
    atr = float(bundle["atr5"][bar_idx])
    if cfg.stop_mode == "sweep_low-0.2ATR":
        ref = signal_stop_ref if np.isfinite(signal_stop_ref) else bundle["low5"][bar_idx]
        return float(ref - 0.2 * atr)
    if cfg.stop_mode == "red_floor-0.15ATR":
        return float(bundle["red_floor"][bar_idx] - 0.15 * atr)
    ob_ref = signal_ob_low if np.isfinite(signal_ob_low) else bundle["proxy_ob_bottom"][bar_idx]
    return float(ob_ref - 0.1 * atr)


def _runner_target(bundle: dict, bar_idx: int, avg_entry: float, risk_r: float) -> float:
    proxy_target = bundle["runner_target_proxy"][bar_idx]
    exact_target = bundle["exact_bearish_ob_bottom"][bar_idx]
    target = exact_target if np.isfinite(exact_target) and exact_target > avg_entry else proxy_target
    if not np.isfinite(target):
        target = avg_entry + 3.0 * risk_r
    return float(max(target, avg_entry + 2.0 * risk_r))


def _should_add(cfg: StrategyConfig, bundle: dict, bar_idx: int, avg_entry: float, signal_ob_low: float, signal_ob_high: float) -> bool:
    if cfg.add_trigger == "none":
        return False
    if cfg.add_trigger == "avg_minus_0.5ATR":
        return bool(bundle["low5"][bar_idx] <= avg_entry - 0.5 * bundle["atr5"][bar_idx])
    if cfg.add_trigger == "retest_red_floor":
        return bool(bundle["low5"][bar_idx] <= bundle["red_floor"][bar_idx] and bundle["close5"][bar_idx] >= bundle["red_floor"][bar_idx])
    ob_low = signal_ob_low if np.isfinite(signal_ob_low) else bundle["proxy_ob_bottom"][bar_idx]
    ob_high = signal_ob_high if np.isfinite(signal_ob_high) else bundle["proxy_ob_top"][bar_idx]
    return bool(np.isfinite(ob_low) and np.isfinite(ob_high) and bundle["low5"][bar_idx] <= ob_high and bundle["high5"][bar_idx] >= ob_low)


def filter_signal_pack(pack: dict[str, np.ndarray | int], market: pd.DataFrame, gate_mode: str) -> dict[str, np.ndarray | int]:
    if gate_mode == "none":
        return pack

    signal_mask = np.asarray(pack["signal_mask"], dtype=bool)
    if gate_mode == "strict":
        allow = (
            _rolling_any(market["weak_low_sweep"].to_numpy(dtype=bool), 3)
            & _rolling_any(market["internal_bullish_choch"].to_numpy(dtype=bool), 3)
            & market["bullish_internal_ob_revisit"].to_numpy(dtype=bool)
        )
    else:
        allow = (
            _rolling_any(
                market["internal_bullish_choch"].to_numpy(dtype=bool) | market["internal_bullish_bos"].to_numpy(dtype=bool),
                3,
            )
            & (market["band_touch_overlap"].to_numpy(dtype=bool) | market["proxy_sweep_low"].to_numpy(dtype=bool))
        )

    filtered_mask = signal_mask & allow
    signal_idx = np.flatnonzero(filtered_mask)
    source_idx = np.flatnonzero(signal_mask)
    source_pos = {idx: pos for pos, idx in enumerate(source_idx.tolist())}
    take_pos = np.array([source_pos[int(idx)] for idx in signal_idx], dtype=int)
    return {
        "signal_mask": filtered_mask,
        "signal_idx": signal_idx.astype(int),
        "signal_stop_ref": np.asarray(pack["signal_stop_ref"], dtype=float)[take_pos],
        "signal_ob_low": np.asarray(pack["signal_ob_low"], dtype=float)[take_pos],
        "signal_ob_high": np.asarray(pack["signal_ob_high"], dtype=float)[take_pos],
        "signal_count": int(signal_idx.size),
    }


def simulate_strategy(
    bundle: dict,
    pack: dict[str, np.ndarray | int],
    cfg: StrategyConfig,
    benchmark_flag: str = "",
    keep_curve: bool = False,
    keep_trades: bool = False,
) -> SimulationArtifacts:
    signal_idx = np.asarray(pack["signal_idx"], dtype=int)
    signal_stop_refs = np.asarray(pack["signal_stop_ref"], dtype=float)
    signal_ob_lows = np.asarray(pack["signal_ob_low"], dtype=float)
    signal_ob_highs = np.asarray(pack["signal_ob_high"], dtype=float)
    signal_count = int(pack["signal_count"])

    ts5 = bundle["ts5"]
    ts1 = bundle["ts1"]
    n5 = len(ts5)
    n1 = len(ts1)
    equity = np.empty(n5, dtype=float)

    capital = float(INITIAL_CAPITAL)
    cursor5 = 0
    sig_ptr = 0
    exposure_minutes = 0
    trade_rows: list[dict] = []

    while sig_ptr < signal_idx.size:
        sig5 = int(signal_idx[sig_ptr])
        if sig5 < cursor5:
            sig_ptr += 1
            continue

        fill1 = int(bundle["five_next_minute_idx"][sig5])
        if fill1 >= n1:
            break
        fill5 = int(bundle["minute_to_container_5_idx"][fill1])
        if fill5 >= n5:
            break

        if cursor5 < fill5:
            equity[cursor5:fill5] = capital

        entry_price = float(bundle["open1"][fill1])
        order_scales = _order_scales(cfg.entry_scale, cfg.max_entries, cfg.add_profile)
        entry_qty = (capital / entry_price) * float(order_scales[0])
        raw_stop = _resolve_stop_reference(cfg, bundle, sig5, signal_stop_refs[sig_ptr], signal_ob_lows[sig_ptr])
        if entry_qty <= 0 or (not np.isfinite(raw_stop)) or raw_stop >= entry_price:
            cursor5 = fill5
            sig_ptr += 1
            continue

        trade_capital_start = capital
        capital -= entry_qty * entry_price * COMMISSION
        avg_entry = entry_price
        qty = entry_qty
        stop_price = float(raw_stop)
        risk_r = max(avg_entry - stop_price, 1e-9)
        size_path = [float(order_scales[0])]
        entries = 1
        last_order_bar = sig5
        partial_taken = False
        trail_armed = False
        partial_target = avg_entry + 1.5 * risk_r
        full_target = avg_entry + (2.0 if cfg.tp_mode == "2R_fixed" else 3.0) * risk_r
        runner_target = _runner_target(bundle, sig5, avg_entry, risk_r)

        pending_add_fill = -1
        pending_add_bar = -1
        pending_add_stop = np.nan
        trade_equity: dict[int, float] = {}

        exit_min_idx = fill1
        exit_reason = "Final Close"
        exit_price = float(bundle["close1"][-1])

        max_exit_bar = min(n5 - 1, fill5 + cfg.max_hold_bars - 1)
        max_exit_time = ts5[max_exit_bar]
        current_min = fill1

        while current_min < n1 and ts1[current_min] <= max_exit_time:
            if pending_add_fill == current_min and qty > 0 and entries < cfg.max_entries:
                add_scale = float(order_scales[entries])
                add_price = float(bundle["open1"][current_min])
                add_qty = (capital / add_price) * add_scale
                if add_qty > 0:
                    capital -= add_qty * add_price * COMMISSION
                    total_qty = qty + add_qty
                    avg_entry = (avg_entry * qty + add_price * add_qty) / total_qty
                    qty = total_qty
                    entries += 1
                    size_path.append(add_scale)
                    if np.isfinite(pending_add_stop):
                        stop_price = min(stop_price, float(pending_add_stop))
                    risk_r = max(avg_entry - stop_price, 1e-9)
                    partial_target = avg_entry + 1.5 * risk_r
                    full_target = avg_entry + (2.0 if cfg.tp_mode == "2R_fixed" else 3.0) * risk_r
                    runner_target = _runner_target(bundle, min(pending_add_bar, n5 - 1), avg_entry, risk_r)
                    last_order_bar = pending_add_bar
                pending_add_fill = -1
                pending_add_bar = -1
                pending_add_stop = np.nan

            high_m = float(bundle["high1"][current_min])
            low_m = float(bundle["low1"][current_min])
            cur5 = min(int(bundle["minute_to_container_5_idx"][current_min]), n5 - 1)

            reason: str | None = None
            price_out = np.nan
            if qty > 0 and low_m <= stop_price:
                reason = "Trail Stop" if trail_armed else "Stop Loss"
                price_out = float(stop_price)
            elif qty > 0:
                if cfg.tp_mode in {"2R_fixed", "3R_fixed"} and high_m >= full_target:
                    reason = "Take Profit"
                    price_out = float(full_target)
                elif cfg.tp_mode == "partial_1.5R_runner_to_bearish_ob":
                    if (not partial_taken) and high_m >= partial_target:
                        partial_qty = qty * 0.5
                        capital, _ = _realize_partial(capital, avg_entry, partial_qty, partial_target)
                        qty -= partial_qty
                        partial_taken = True
                        runner_target = _runner_target(bundle, cur5, avg_entry, risk_r)
                    if partial_taken and qty > 0 and high_m >= runner_target:
                        reason = "Runner Target"
                        price_out = float(runner_target)
                elif cfg.tp_mode == "trail_white_avg_after_2R":
                    if (not trail_armed) and high_m >= avg_entry + 2.0 * risk_r:
                        trail_armed = True
                    if trail_armed:
                        stop_price = max(stop_price, float(bundle["white_avg"][cur5]))
                        if low_m <= stop_price:
                            reason = "Trail Stop"
                            price_out = float(stop_price)

            if reason is not None:
                capital, _ = _close_position(capital, avg_entry, qty, float(price_out))
                qty = 0.0
                exit_min_idx = current_min
                exit_reason = reason
                exit_price = float(price_out)
                exit_bar = min(int(bundle["minute_to_container_5_idx"][current_min]), n5 - 1)
                trade_equity[exit_bar] = capital
                break

            close5_idx = int(bundle["minute_to_five_close_idx"][current_min])
            if close5_idx >= 0:
                if qty > 0:
                    trade_equity[close5_idx] = capital + (float(bundle["close5"][close5_idx]) - avg_entry) * qty
                if qty > 0 and close5_idx >= max_exit_bar:
                    capital, _ = _close_position(capital, avg_entry, qty, float(bundle["close5"][close5_idx]))
                    qty = 0.0
                    exit_min_idx = current_min
                    exit_reason = "Time Exit"
                    exit_price = float(bundle["close5"][close5_idx])
                    trade_equity[close5_idx] = capital
                    break
                if (
                    qty > 0
                    and pending_add_fill < 0
                    and entries < cfg.max_entries
                    and close5_idx - last_order_bar >= cfg.cooldown_bars
                    and _should_add(cfg, bundle, close5_idx, avg_entry, signal_ob_lows[sig_ptr], signal_ob_highs[sig_ptr])
                ):
                    pending_add_fill = int(bundle["five_next_minute_idx"][close5_idx])
                    pending_add_bar = close5_idx
                    pending_add_stop = _resolve_stop_reference(
                        cfg,
                        bundle,
                        close5_idx,
                        min(signal_stop_refs[sig_ptr], bundle["low5"][close5_idx]),
                        signal_ob_lows[sig_ptr],
                    )

            current_min += 1

        if qty > 0:
            final_min = min(current_min, n1 - 1)
            final_bar = min(int(bundle["minute_to_container_5_idx"][final_min]), n5 - 1)
            capital, _ = _close_position(capital, avg_entry, qty, float(bundle["close1"][final_min]))
            exit_min_idx = final_min
            exit_reason = "Final Close"
            exit_price = float(bundle["close1"][final_min])
            trade_equity[final_bar] = capital

        exit_bar = min(int(bundle["minute_to_container_5_idx"][exit_min_idx]), n5 - 1)
        for bar_fill in range(fill5, exit_bar + 1):
            equity[bar_fill] = trade_equity.get(bar_fill, capital)

        hold_minutes = max(1, exit_min_idx - fill1 + 1)
        exposure_minutes += hold_minutes
        trade_pnl = capital - trade_capital_start
        trade_rows.append(
            {
                "variant": cfg.variant(),
                "stage": cfg.stage,
                "entry_family": cfg.seed.entry_family,
                "gate": cfg.smc_gate_mode,
                "signal_time": pd.Timestamp(ts5[sig5]),
                "entry_time": pd.Timestamp(ts1[fill1]),
                "exit_time": pd.Timestamp(ts1[exit_min_idx]),
                "avg_entry": float(entry_price),
                "exit_price": float(exit_price),
                "size_path": "+".join(f"{x:.2f}" for x in size_path),
                "num_entries": int(entries),
                "exit_reason": exit_reason,
                "realized_r": float(trade_pnl / max((entry_price - raw_stop) * entry_qty, 1e-9)),
                "pnl": float(trade_pnl),
                "hold_minutes": float(hold_minutes),
                "max_entries_allowed": int(cfg.max_entries),
            }
        )

        cursor5 = exit_bar + 1
        sig_ptr = int(np.searchsorted(signal_idx, cursor5, side="left"))

    if cursor5 < n5:
        equity[cursor5:] = capital

    curve = pd.DataFrame({"timestamp": pd.to_datetime(ts5), "variant": cfg.variant(), "equity": equity})
    metrics = compute_curve_stats(curve, INITIAL_CAPITAL)
    trades_df = pd.DataFrame(trade_rows)
    metrics.update(
        {
            "variant": cfg.variant(),
            "stage": cfg.stage,
            "gate": cfg.smc_gate_mode,
            "entry_family": cfg.seed.entry_family,
            "zone_anchor": cfg.seed.zone_anchor,
            "sweep_lookback": cfg.seed.sweep_lookback,
            "reclaim_window": cfg.seed.reclaim_window,
            "confirm_mode": cfg.seed.confirm_mode,
            "entry_scale": cfg.entry_scale,
            "max_entries": cfg.max_entries,
            "add_trigger": cfg.add_trigger,
            "add_profile": cfg.add_profile,
            "cooldown_bars": cfg.cooldown_bars,
            "stop_mode": cfg.stop_mode,
            "tp_mode": cfg.tp_mode,
            "max_hold_bars": cfg.max_hold_bars,
            "signal_count": signal_count,
            "trades": int(len(trades_df)),
            "win_rate_pct": float((trades_df["pnl"] > 0).mean() * 100.0) if not trades_df.empty else np.nan,
            "avg_entries": float(trades_df["num_entries"].mean()) if not trades_df.empty else np.nan,
            "avg_hold_minutes": float(trades_df["hold_minutes"].mean()) if not trades_df.empty else np.nan,
            "add_count": int(max(0, trades_df["num_entries"].sum() - len(trades_df))) if not trades_df.empty else 0,
            "exposure_pct": float(exposure_minutes / max(1, len(bundle["ts1"])) * 100.0),
            "benchmark_flag": benchmark_flag,
        }
    )
    return SimulationArtifacts(metrics=metrics, curve=curve if keep_curve else None, trades=trades_df if keep_trades else None)


def strategy_from_seed(seed: SeedConfig, stage: str) -> StrategyConfig:
    return StrategyConfig(seed=seed, stage=stage, **BASE_STAGE1_CFG).normalized()


def benchmark_to_row(stats: dict, benchmark_flag: str) -> dict:
    return {
        "variant": str(stats["variant"]),
        "stage": "benchmark",
        "gate": "none",
        "entry_family": benchmark_flag,
        "zone_anchor": "",
        "sweep_lookback": np.nan,
        "reclaim_window": np.nan,
        "confirm_mode": "",
        "entry_scale": np.nan,
        "max_entries": np.nan,
        "add_trigger": "",
        "add_profile": "",
        "cooldown_bars": np.nan,
        "stop_mode": "",
        "tp_mode": "",
        "max_hold_bars": np.nan,
        "signal_count": float(stats.get("signal_crosses", stats.get("signal_count", np.nan))),
        "trades": float(stats.get("trades", np.nan)),
        "win_rate_pct": float(stats.get("win_rate_pct", np.nan)),
        "avg_entries": float(stats.get("avg_num_entries", np.nan)),
        "avg_hold_minutes": float(stats.get("avg_hours_held", np.nan) * 60.0) if pd.notna(stats.get("avg_hours_held", np.nan)) else np.nan,
        "add_count": 0,
        "exposure_pct": np.nan,
        "benchmark_flag": benchmark_flag,
        "final_equity": float(stats["final_equity"]),
        "total_return_pct": float(stats["total_return_pct"]),
        "cagr_pct": float(stats["cagr_pct"]),
        "max_drawdown_pct": float(stats["max_drawdown_pct"]),
        "calmar_ratio": float(stats["calmar_ratio"]),
    }


def coordinate_optimize_seed(seed: SeedConfig, evaluate) -> tuple[StrategyConfig, dict]:
    current = strategy_from_seed(seed, "stage1_fullstack")
    best_metrics = evaluate(current).metrics
    fields = [
        ("entry_scale", ENTRY_SCALE_GRID),
        ("max_entries", MAX_ENTRIES_GRID),
        ("add_trigger", ADD_TRIGGER_GRID),
        ("add_profile", ADD_PROFILE_GRID),
        ("cooldown_bars", COOLDOWN_GRID),
        ("stop_mode", STOP_MODE_GRID),
        ("tp_mode", TP_MODE_GRID),
        ("max_hold_bars", MAX_HOLD_GRID),
    ]
    for _ in range(2):
        improved = False
        for field_name, values in fields:
            local_best_cfg = current
            local_best_metrics = best_metrics
            for value in values:
                candidate = replace(current, **{field_name: value}, stage="stage1_fullstack").normalized()
                if field_name in {"add_trigger", "add_profile"} and candidate.max_entries == 1:
                    continue
                artifacts = evaluate(candidate)
                if _better_metrics(artifacts.metrics, local_best_metrics):
                    local_best_cfg = candidate
                    local_best_metrics = artifacts.metrics
            if local_best_cfg != current:
                current = local_best_cfg
                best_metrics = local_best_metrics
                improved = True
        if not improved:
            break
    return current, best_metrics


def save_plot(curve_map: dict[str, pd.DataFrame], summary_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=False, gridspec_kw={"height_ratios": [2.4, 1.0, 1.0]})
    ax_eq, ax_final, ax_risk = axes

    variants = summary_df["variant"].tolist()
    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.1, label=variant, color=colors[variant])
    ax_eq.axhline(INITIAL_CAPITAL, color="#666666", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 111: 5m SR + SMC Profit-Max")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_final.bar(summary_df["variant"], summary_df["final_equity"], color=[colors[v] for v in variants], alpha=0.9)
    ax_final.set_ylabel("Final Equity")
    ax_final.grid(True, axis="y", alpha=0.2)
    ax_final.tick_params(axis="x", rotation=20)

    ax_risk.bar(summary_df["variant"], summary_df["cagr_pct"], color=[colors[v] for v in variants], alpha=0.85, label="CAGR %")
    ax_risk_t = ax_risk.twinx()
    ax_risk_t.plot(summary_df["variant"], summary_df["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_risk.set_ylabel("CAGR %")
    ax_risk_t.set_ylabel("MDD %")
    ax_risk.grid(True, axis="y", alpha=0.2)
    ax_risk.tick_params(axis="x", rotation=20)
    h1, l1 = ax_risk.get_legend_handles_labels()
    h2, l2 = ax_risk_t.get_legend_handles_labels()
    ax_risk.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def build_report(
    winner: dict,
    proxy_winner: dict,
    sr_only: dict,
    gap12: dict,
    exact_results: pd.DataFrame,
    fullstack_results: pd.DataFrame,
    sanity_df: pd.DataFrame,
    benchmark_summary: pd.DataFrame,
) -> str:
    uplift_gap = float(winner["final_equity"] - gap12["final_equity"])
    uplift_sr = float(winner["final_equity"] - sr_only["final_equity"])
    proxy_delta = float(winner["final_equity"] - proxy_winner["final_equity"])
    risk_conflict = "mild" if winner["max_drawdown_pct"] <= 60.0 and winner["trades"] >= 40 else "meaningful"

    lines: list[str] = []
    lines.append("# Study 111: 5분 SR + SMC Profit-Max")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Data: latest local `BTCUSDT` 1m cache from `2022-01-01` onward.")
    lines.append("- Execution: `5m` signal close -> next `1m` open fill, intrabar exits on `1m` high/low, stop-first if TP and SL touch together.")
    lines.append("- SR follows the actual Pine code: `white = avg(EMA20[1m], EMA1800[1m])`, `red = avg(EMA20[1m], EMA1800[2m])`, floors = `avg - ATR14[1m]`.")
    lines.append("- Stage 1 uses SR + proxy SMC. Stage 2 rechecks the best variants with Pine-near internal structure gates.")
    lines.append("- Full-stack pass uses the declared grids with cached coordinate sweeps to keep runtime tractable.")
    lines.append("")
    lines.append("## Winner")
    lines.append(
        f"- Winner: `{winner['variant']}` -> equity `{_fmt(winner['final_equity'])}`, CAGR `{_fmt(winner['cagr_pct'])}%`, "
        f"MDD `{_fmt(winner['max_drawdown_pct'])}%`, Calmar `{_fmt(winner['calmar_ratio'])}`, trades `{int(winner['trades'])}`"
    )
    lines.append(f"- Winning entry family: `{winner['entry_family']}` with gate `{winner['gate']}`")
    lines.append(f"- `110 gap_12` 대비 uplift: equity `{_fmt(uplift_gap)}`")
    lines.append(f"- `SR-only` 대비 uplift: equity `{_fmt(uplift_sr)}`")
    lines.append(f"- `proxy winner vs exact winner` 차이: equity `{_fmt(proxy_delta)}`")
    lines.append(f"- Profit-max와 risk-profile 충돌 정도: `{risk_conflict}`")
    lines.append("")
    lines.append("## Benchmarks")
    lines.append("| Variant | Stage | Final Equity | Total Return % | CAGR % | MDD % | Calmar | Trades |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in benchmark_summary.iterrows():
        lines.append(
            f"| {row['variant']} | {row['stage']} | {_fmt(row['final_equity'])} | {_fmt(row['total_return_pct'])} | "
            f"{_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{int(row['trades']) if pd.notna(row['trades']) else 'N/A'} |"
        )
    lines.append("")
    lines.append("## Stage 2 Exact Gate Ranking")
    lines.append("| Variant | Gate | Final Equity | CAGR % | MDD % | Calmar | Trades |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for _, row in exact_results.sort_values(["final_equity", "cagr_pct", "max_drawdown_pct"], ascending=[False, False, True]).iterrows():
        lines.append(
            f"| {row['variant']} | {row['gate']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {int(row['trades'])} |"
        )
    lines.append("")
    lines.append("## Stage 1 Full-Stack Top 10")
    lines.append("| Variant | Entry Family | Final Equity | CAGR % | MDD % | Calmar | Trades |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for _, row in fullstack_results.sort_values(["final_equity", "cagr_pct", "max_drawdown_pct"], ascending=[False, False, True]).head(10).iterrows():
        lines.append(
            f"| {row['variant']} | {row['entry_family']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {int(row['trades'])} |"
        )
    lines.append("")
    lines.append("## Sanity Leaderboard")
    lines.append("| Variant | Stage | Final Equity | CAGR % | MDD % | Trades |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
    if sanity_df.empty:
        lines.append("| none | N/A | N/A | N/A | N/A | N/A |")
    else:
        for _, row in sanity_df.iterrows():
            lines.append(
                f"| {row['variant']} | {row['stage']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | "
                f"{_fmt(row['max_drawdown_pct'])} | {int(row['trades'])} |"
            )
    lines.append("")
    lines.append("## Notes")
    lines.append("- `SR-only` is the best fully optimized `band_bounce` strategy.")
    lines.append("- `SR+proxy SMC` is the best fully optimized Stage 1 strategy from `sweep_reclaim` or `choch_ob_reclaim`.")
    lines.append("- `SR+exact SMC` is the best Stage 2 gated strategy.")
    return "\n".join(lines) + "\n"


def run_validations(market: pd.DataFrame, trade_df: pd.DataFrame, metrics_df: pd.DataFrame):
    idx_candidates = [200, len(market) // 2, len(market) - 200]
    idx_candidates = [idx for idx in idx_candidates if 0 <= idx < len(market)]
    for idx in idx_candidates[:3]:
        row = market.iloc[idx]
        white_gap = row["white_avg"] - row["white_floor"]
        red_gap = row["red_avg"] - row["red_floor"]
        if not np.isfinite(white_gap) or not np.isfinite(red_gap):
            raise AssertionError("white/red floor validation hit NaN")
        if abs(white_gap - red_gap) > 1e-8:
            raise AssertionError("white/red floor validation mismatch")

    if not trade_df.empty:
        strategy_trades = trade_df[trade_df["stage"] != "benchmark"].copy()
        if not strategy_trades.empty and not (pd.to_datetime(strategy_trades["entry_time"]) > pd.to_datetime(strategy_trades["signal_time"])).all():
            raise AssertionError("same-bar entry detected")
        if not strategy_trades.empty and not (strategy_trades["num_entries"] <= strategy_trades["max_entries_allowed"]).all():
            raise AssertionError("max entries violation detected")

    benchmark_flags = set(metrics_df["benchmark_flag"].fillna("").astype(str))
    required = {"buy_hold", "gap_12", "sr_only", "proxy_winner", "exact_winner"}
    if not required.issubset(benchmark_flags):
        raise AssertionError("missing required benchmark rows")


def main():
    print("Loading modules and market data...")
    m107 = load_module("_m107_111", BASE_107_PATH)
    m109 = load_module("_m109_111", BASE_109_PATH)
    m110 = load_module("_m110_111", BASE_110_PATH)

    df_1m, df_4h, _ = m107.load_market_data()
    market = prepare_market_111(df_1m)
    bundle = build_market_bundle(market, df_1m)
    signal_cache = build_stage1_signal_cache(market)

    eval_cache: dict[str, SimulationArtifacts] = {}

    def evaluate(cfg: StrategyConfig, benchmark_flag: str = "", keep_curve: bool = False, keep_trades: bool = False) -> SimulationArtifacts:
        cfg = cfg.normalized()
        cache_key = cfg.variant()
        if cache_key in eval_cache and not keep_curve and not keep_trades:
            return eval_cache[cache_key]
        pack = signal_cache[cfg.seed]
        if cfg.smc_gate_mode != "none":
            pack = filter_signal_pack(pack, market, cfg.smc_gate_mode)
        artifacts = simulate_strategy(bundle, pack, cfg, benchmark_flag=benchmark_flag, keep_curve=keep_curve, keep_trades=keep_trades)
        if not keep_curve and not keep_trades:
            eval_cache[cache_key] = artifacts
        return artifacts

    print("Stage 1 coarse pass...")
    seeds: list[SeedConfig] = [SeedConfig("band_bounce", anchor, 12, 1, "close_above_white") for anchor in ZONE_ANCHORS]
    for family in ["sweep_reclaim", "choch_ob_reclaim"]:
        seeds.extend(
            SeedConfig(family, anchor, lookback, reclaim_window, confirm_mode)
            for anchor, lookback, reclaim_window, confirm_mode in itertools.product(
                ZONE_ANCHORS, LOOKBACK_GRID, RECLAIM_GRID, CONFIRM_MODES
            )
        )

    coarse_rows: list[dict] = []
    for idx, seed in enumerate(seeds, start=1):
        if idx % 25 == 0 or idx == len(seeds):
            print(f"  coarse {idx}/{len(seeds)}")
        coarse_rows.append(evaluate(strategy_from_seed(seed, "stage1_coarse")).metrics)
    coarse_df = pd.DataFrame(coarse_rows).sort_values(["final_equity", "cagr_pct", "max_drawdown_pct"], ascending=[False, False, True]).reset_index(drop=True)

    top12 = coarse_df.head(12)
    best_band_seed = coarse_df[coarse_df["entry_family"] == "band_bounce"].iloc[0]
    best_proxy_seed = coarse_df[coarse_df["entry_family"] != "band_bounce"].iloc[0]
    seed_rows = pd.concat([top12, pd.DataFrame([best_band_seed, best_proxy_seed])], ignore_index=True)
    unique_seed_map: dict[tuple, SeedConfig] = {}
    for _, row in seed_rows.iterrows():
        seed = SeedConfig(str(row["entry_family"]), str(row["zone_anchor"]), int(row["sweep_lookback"]), int(row["reclaim_window"]), str(row["confirm_mode"]))
        unique_seed_map[(seed.entry_family, seed.zone_anchor, seed.sweep_lookback, seed.reclaim_window, seed.confirm_mode)] = seed

    print("Stage 1 full-stack pass...")
    fullstack_rows: list[dict] = []
    for idx, seed in enumerate(unique_seed_map.values(), start=1):
        print(f"  full-stack {idx}/{len(unique_seed_map)} -> {seed.short_name()}")
        _, best_metrics = coordinate_optimize_seed(seed, evaluate)
        fullstack_rows.append(best_metrics)
    fullstack_df = pd.DataFrame(fullstack_rows).sort_values(["final_equity", "cagr_pct", "max_drawdown_pct"], ascending=[False, False, True]).reset_index(drop=True)

    print("Stage 2 exact recheck...")
    exact_rows: list[dict] = []
    for _, row in fullstack_df.head(6).iterrows():
        base_cfg = StrategyConfig(
            seed=SeedConfig(str(row["entry_family"]), str(row["zone_anchor"]), int(row["sweep_lookback"]), int(row["reclaim_window"]), str(row["confirm_mode"])),
            entry_scale=float(row["entry_scale"]),
            max_entries=int(row["max_entries"]),
            add_trigger=str(row["add_trigger"]),
            add_profile=str(row["add_profile"]),
            cooldown_bars=int(row["cooldown_bars"]),
            stop_mode=str(row["stop_mode"]),
            tp_mode=str(row["tp_mode"]),
            max_hold_bars=int(row["max_hold_bars"]),
            stage="stage2_exact",
        ).normalized()
        for gate in ["strict", "relaxed"]:
            exact_rows.append(evaluate(replace(base_cfg, smc_gate_mode=gate)).metrics)
    exact_df = pd.DataFrame(exact_rows).sort_values(["final_equity", "cagr_pct", "max_drawdown_pct"], ascending=[False, False, True]).reset_index(drop=True)

    print("Benchmarks...")
    benchmark_market_1m = m109.build_market_1m(df_1m, df_4h)
    buy_hold_curve, buy_hold_trades, buy_hold_stats = m109.run_buy_hold(benchmark_market_1m)
    gap12_curve, gap12_trades, gap12_stats = m110.run_threshold_case(benchmark_market_1m, 12.0, m109)

    sr_only_row = fullstack_df[fullstack_df["entry_family"] == "band_bounce"].iloc[0].to_dict()
    proxy_winner_row = fullstack_df[fullstack_df["entry_family"] != "band_bounce"].iloc[0].to_dict()
    exact_winner_row = exact_df.iloc[0].to_dict()

    summary_rows = [benchmark_to_row(buy_hold_stats, "buy_hold"), benchmark_to_row(gap12_stats, "gap_12")]
    sr_only_benchmark = dict(sr_only_row)
    sr_only_benchmark["benchmark_flag"] = "sr_only"
    proxy_benchmark = dict(proxy_winner_row)
    proxy_benchmark["benchmark_flag"] = "proxy_winner"
    exact_benchmark = dict(exact_winner_row)
    exact_benchmark["benchmark_flag"] = "exact_winner"

    metrics_df = pd.concat(
        [
            coarse_df.assign(benchmark_flag=""),
            fullstack_df.assign(benchmark_flag=""),
            exact_df.assign(benchmark_flag=""),
            pd.DataFrame(summary_rows),
        ],
        ignore_index=True,
        sort=False,
    )
    metrics_df.loc[metrics_df["variant"] == sr_only_benchmark["variant"], "benchmark_flag"] = "sr_only"
    metrics_df.loc[metrics_df["variant"] == proxy_benchmark["variant"], "benchmark_flag"] = "proxy_winner"
    metrics_df.loc[metrics_df["variant"] == exact_benchmark["variant"], "benchmark_flag"] = "exact_winner"
    metrics_df.to_csv(OUT_CSV, index=False)

    print("Collecting selected curves and trades...")
    selected_curves: dict[str, pd.DataFrame] = {
        "buy_hold": _compress_curve(buy_hold_curve[["timestamp", "variant", "equity"]]),
        "gap_12": _compress_curve(gap12_curve[["timestamp", "variant", "equity"]]),
    }
    selected_trade_frames = [
        buy_hold_trades.assign(stage="benchmark", gate="none", signal_time=buy_hold_trades["entry_time"], max_entries_allowed=1, entry_family="buy_hold", exit_reason="Final Close", realized_r=buy_hold_trades["return_pct"], hold_minutes=buy_hold_trades["hours_held"] * 60.0, size_path="1.00"),
        gap12_trades.assign(stage="benchmark", gate="none", signal_time=gap12_trades["entry_time"], max_entries_allowed=4, entry_family="gap_12", size_path="benchmark").rename(columns={"reason": "exit_reason", "return_pct": "realized_r", "hours_held": "hold_minutes"}),
    ]
    if "hold_minutes" in selected_trade_frames[1].columns:
        selected_trade_frames[1]["hold_minutes"] = selected_trade_frames[1]["hold_minutes"] * 60.0

    selected_cfgs = []
    for row in [sr_only_row, proxy_winner_row, exact_winner_row]:
        selected_cfgs.append(
            StrategyConfig(
                seed=SeedConfig(str(row["entry_family"]), str(row["zone_anchor"]), int(row["sweep_lookback"]), int(row["reclaim_window"]), str(row["confirm_mode"])),
                entry_scale=float(row["entry_scale"]),
                max_entries=int(row["max_entries"]),
                add_trigger=str(row["add_trigger"]),
                add_profile=str(row["add_profile"]),
                cooldown_bars=int(row["cooldown_bars"]),
                stop_mode=str(row["stop_mode"]),
                tp_mode=str(row["tp_mode"]),
                max_hold_bars=int(row["max_hold_bars"]),
                smc_gate_mode=str(row["gate"]),
                stage=str(row["stage"]),
            ).normalized()
        )

    for cfg in {cfg.variant(): cfg for cfg in selected_cfgs}.values():
        artifacts = evaluate(cfg, keep_curve=True, keep_trades=True)
        if artifacts.curve is not None:
            selected_curves[cfg.variant()] = _compress_curve(artifacts.curve[["timestamp", "variant", "equity"]])
        if artifacts.trades is not None and not artifacts.trades.empty:
            selected_trade_frames.append(artifacts.trades)

    pd.concat(selected_curves.values(), ignore_index=True).to_csv(OUT_CURVES_CSV, index=False)
    selected_trade_df = pd.concat(selected_trade_frames, ignore_index=True, sort=False)
    selected_trade_df.to_csv(OUT_TRADES_CSV, index=False)

    benchmark_summary = pd.DataFrame(
        [
            benchmark_to_row(buy_hold_stats, "buy_hold"),
            benchmark_to_row(gap12_stats, "gap_12"),
            sr_only_benchmark,
            proxy_benchmark,
            exact_benchmark,
        ]
    ).sort_values(["final_equity", "cagr_pct", "max_drawdown_pct"], ascending=[False, False, True]).reset_index(drop=True)
    save_plot(selected_curves, benchmark_summary[["variant", "final_equity", "cagr_pct", "max_drawdown_pct"]])

    sanity_df = metrics_df[
        (metrics_df["stage"] != "benchmark")
        & (metrics_df["max_drawdown_pct"] <= 60.0)
        & (metrics_df["trades"] >= 40)
    ].sort_values(["final_equity", "cagr_pct", "max_drawdown_pct"], ascending=[False, False, True]).head(10)
    report = build_report(exact_winner_row, proxy_winner_row, sr_only_row, benchmark_to_row(gap12_stats, "gap_12"), exact_df, fullstack_df, sanity_df, benchmark_summary)
    OUT_MD.write_text(report, encoding="utf-8")

    run_validations(market, selected_trade_df, pd.concat([metrics_df, benchmark_summary], ignore_index=True, sort=False))
    print("Done.")
    print(f"- metrics: {OUT_CSV}")
    print(f"- trades: {OUT_TRADES_CSV}")
    print(f"- curves: {OUT_CURVES_CSV}")
    print(f"- report: {OUT_MD}")
    print(f"- plot: {OUT_PNG}")


if __name__ == "__main__":
    main()
