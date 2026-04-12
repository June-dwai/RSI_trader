from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DATA_DIR = Path("historical_data_mainnet")
BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
BASE_76_PATH = Path("76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py")
BASE_111_PATH = Path("111_backtest_btcusdt_sr_smc_5m_profitmax.py")

OUT_BASE = "114_backtest_btcusdt_best_with_sr_smc_filters"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

SHORT_TP_RETURN_PCT = 15.0
SMC_BLOCK_COUNT = 5

BASELINE_CFG = {
    "variant": "baseline_short_gate24h_shorttp15_2x_2021plus",
    "leverage": 2.0,
    "gate_side": "short",
    "liq_window": "24h",
    "gate_bars": 8,
    "body_atr_mult": 0.25,
    "sr_mode": "none",
    "smc_block_mode": "none",
}

VARIANTS = [
    BASELINE_CFG,
    {**BASELINE_CFG, "variant": "baseline_short_gate24h_shorttp15_2x_smc5_2021plus", "smc_block_mode": "opp5"},
    {**BASELINE_CFG, "variant": "redavg_align_2021plus", "sr_mode": "redavg_align"},
    {**BASELINE_CFG, "variant": "redavg_align_smc5_2021plus", "sr_mode": "redavg_align", "smc_block_mode": "opp5"},
    {**BASELINE_CFG, "variant": "redfloor_align_2021plus", "sr_mode": "redfloor_align"},
    {**BASELINE_CFG, "variant": "redfloor_align_smc5_2021plus", "sr_mode": "redfloor_align", "smc_block_mode": "opp5"},
    {**BASELINE_CFG, "variant": "band_switch_2021plus", "sr_mode": "band_switch"},
    {**BASELINE_CFG, "variant": "band_switch_smc5_2021plus", "sr_mode": "band_switch", "smc_block_mode": "opp5"},
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


def _fmt_count(v: float) -> str:
    if pd.isna(v):
        return "N/A"
    return str(int(v))


def _parse_cache_end(path: Path) -> pd.Timestamp:
    return pd.Timestamp(path.stem.split("_")[-1])


def _pick_latest_cache(symbol: str, timeframe: str, start_date: str) -> Path:
    matches = list(DATA_DIR.glob(f"{symbol}_{timeframe}_{start_date}_*.pkl"))
    if not matches:
        raise FileNotFoundError(f"No cache files for {symbol} {timeframe} {start_date}")
    return max(matches, key=_parse_cache_end)


def _load_cache(paths: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_pickle(path)
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        frames.append(df)
    merged = pd.concat(frames)
    merged = merged[~merged.index.duplicated(keep="first")].sort_index()
    return merged


def load_market_data_2021plus() -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    latest_1m = _pick_latest_cache("BTCUSDT", "1m", "2022-01-01")
    latest_4h = _pick_latest_cache("BTCUSDT", "4h", "2022-01-01")

    df_1m = _load_cache(
        [
            DATA_DIR / "BTCUSDT_1m_2021-01-01_2021-12-31.pkl",
            latest_1m,
        ]
    )
    df_4h = _load_cache(
        [
            DATA_DIR / "BTCUSDT_4h_2021-01-01_2021-12-31.pkl",
            latest_4h,
        ]
    )

    start = pd.Timestamp("2021-01-01")
    end_ts = min(df_1m.index.max(), _parse_cache_end(latest_1m) + pd.Timedelta(days=1) - pd.Timedelta(minutes=1))
    df_1m = df_1m[(df_1m.index >= start) & (df_1m.index <= end_ts)].copy()
    df_4h = df_4h[(df_4h.index >= start) & (df_4h.index <= end_ts.ceil("4h"))].copy()
    return df_1m, df_4h, end_ts


def _resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    cols = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in df.columns:
        cols["volume"] = "sum"
    return (
        df.resample(rule, label="right", closed="right")
        .agg(cols)
        .dropna(subset=["open", "high", "low", "close"])
    )


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


def compute_internal_ob_stack_features(bars: pd.DataFrame, m111, pivot_size: int = 5, max_display_boxes: int = 5) -> pd.DataFrame:
    high = bars["high"].to_numpy(dtype=float)
    low = bars["low"].to_numpy(dtype=float)
    close = bars["close"].to_numpy(dtype=float)
    n = len(bars)

    atr200 = m111._atr_array(high, low, close, 200)
    high_volatility = (high - low) >= (2.0 * atr200)
    parsed_high = np.where(high_volatility, low, high)
    parsed_low = np.where(high_volatility, high, low)

    bearish_above_count = np.zeros(n, dtype=int)
    bullish_below_count = np.zeros(n, dtype=int)
    active_bearish_count = np.zeros(n, dtype=int)
    active_bullish_count = np.zeros(n, dtype=int)

    def new_pivot() -> dict[str, float | int | bool]:
        return {"current": np.nan, "crossed": False, "idx": -1}

    internal_high = new_pivot()
    internal_low = new_pivot()
    internal_leg = 0
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
            bullish_blocks = bullish_blocks[:100]
        else:
            rel_idx = int(np.nanargmax(parsed_high[left:right]))
            source_idx = left + rel_idx
            bearish_blocks.insert(0, {"top": float(parsed_high[source_idx]), "bottom": float(parsed_low[source_idx])})
            bearish_blocks = bearish_blocks[:100]

    for i in range(n):
        if i >= pivot_size:
            ref_idx = i - pivot_size
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

        if i > 0:
            high_level = float(internal_high["current"]) if np.isfinite(internal_high["current"]) else np.nan
            low_level = float(internal_low["current"]) if np.isfinite(internal_low["current"]) else np.nan

            if np.isfinite(high_level) and not bool(internal_high["crossed"]) and close[i - 1] <= high_level and close[i] > high_level:
                internal_high["crossed"] = True
                store_order_block(int(internal_high["idx"]), i, bullish=True)

            if np.isfinite(low_level) and not bool(internal_low["crossed"]) and close[i - 1] >= low_level and close[i] < low_level:
                internal_low["crossed"] = True
                store_order_block(int(internal_low["idx"]), i, bullish=False)

        bullish_blocks = [ob for ob in bullish_blocks if not (low[i] < ob["bottom"])]
        bearish_blocks = [ob for ob in bearish_blocks if not (high[i] > ob["top"])]

        shown_bullish = bullish_blocks[:max_display_boxes]
        shown_bearish = bearish_blocks[:max_display_boxes]
        active_bullish_count[i] = int(min(max_display_boxes, len(shown_bullish)))
        active_bearish_count[i] = int(min(max_display_boxes, len(shown_bearish)))
        bullish_below_count[i] = int(min(max_display_boxes, sum(1 for ob in shown_bullish if ob["top"] < close[i])))
        bearish_above_count[i] = int(min(max_display_boxes, sum(1 for ob in shown_bearish if ob["bottom"] > close[i])))

    return pd.DataFrame(
        {
            "active_bullish_ob_count": active_bullish_count,
            "active_bearish_ob_count": active_bearish_count,
            "bullish_ob_below_count": bullish_below_count,
            "bearish_ob_above_count": bearish_above_count,
            "bullish_stack_5_below": bullish_below_count >= max_display_boxes,
            "bearish_stack_5_above": bearish_above_count >= max_display_boxes,
        },
        index=bars.index,
    )


def prepare_market_114(df_1m: pd.DataFrame, df_4h: pd.DataFrame, m47, m111) -> pd.DataFrame:
    out_1m = df_1m.copy().sort_index()
    out_4h = df_4h.copy().sort_index()
    if not isinstance(out_1m.index, pd.DatetimeIndex):
        out_1m.index = pd.to_datetime(out_1m.index)
    if not isinstance(out_4h.index, pd.DatetimeIndex):
        out_4h.index = pd.to_datetime(out_4h.index)

    bars_15m = _resample_ohlc(out_1m, "15min")
    bars_1h = _resample_ohlc(out_1m, "1h")

    out_4h["ema200_closed"] = out_4h["close"].ewm(span=m47.EMA_PERIOD, adjust=False).mean()
    out_4h["ema200_prev_closed"] = out_4h["ema200_closed"].shift(1)
    out_4h["trend_4h_hyst"] = m47.LiveParityNoLookahead._compute_hysteresis_state(
        out_4h["close"], out_4h["ema200_prev_closed"], m47.HYSTERESIS_BAND
    )
    out_4h["trend_4h_confirmed"] = out_4h["trend_4h_hyst"].shift(1)
    out_4h = out_4h.reset_index().rename(columns={"index": "timestamp"})

    bars_1h["liq_high_8h_prev"] = bars_1h["high"].rolling(8).max().shift(1)
    bars_1h["liq_low_8h_prev"] = bars_1h["low"].rolling(8).min().shift(1)
    bars_1h["liq_high_24h_prev"] = bars_1h["high"].rolling(24).max().shift(1)
    bars_1h["liq_low_24h_prev"] = bars_1h["low"].rolling(24).min().shift(1)
    bars_1h = bars_1h.reset_index().rename(columns={"index": "timestamp"})

    out = bars_15m.reset_index().rename(columns={"index": "timestamp"})
    out["body"] = (out["close"] - out["open"]).abs()
    tr = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - out["close"].shift(1)).abs(),
            (out["low"] - out["close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr20"] = tr.rolling(20).mean()
    out["ema20"] = out["close"].ewm(span=20, adjust=False).mean()

    out = pd.merge_asof(
        out.sort_values("timestamp"),
        bars_1h.sort_values("timestamp")[["timestamp", "liq_high_8h_prev", "liq_low_8h_prev", "liq_high_24h_prev", "liq_low_24h_prev"]],
        on="timestamp",
        direction="backward",
    )
    out = pd.merge_asof(
        out.sort_values("timestamp"),
        out_4h.sort_values("timestamp")[["timestamp", "trend_4h_confirmed", "ema200_prev_closed"]],
        on="timestamp",
        direction="backward",
    )

    target_index = pd.DatetimeIndex(out["timestamp"])
    ema_fast_1m = out_1m["close"].ewm(span=20, adjust=False).mean()
    ema_slow_1m = out_1m["close"].ewm(span=1800, adjust=False).mean()
    ema_slow_2m = out_1m["close"].resample("2min", label="right", closed="right").last().dropna().ewm(span=1800, adjust=False).mean()
    atr_1m = m111._atr_series(out_1m["high"], out_1m["low"], out_1m["close"], 14)

    fast_15m = m111._map_series_to_target(ema_fast_1m, target_index)
    slow_1m_15m = m111._map_series_to_target(ema_slow_1m, target_index)
    slow_2m_15m = m111._map_series_to_target(ema_slow_2m, target_index)
    atr_1m_15m = m111._map_series_to_target(atr_1m, target_index)

    out["white_avg"] = (fast_15m.to_numpy(dtype=float) + slow_1m_15m.to_numpy(dtype=float)) * 0.5
    out["red_avg"] = (fast_15m.to_numpy(dtype=float) + slow_2m_15m.to_numpy(dtype=float)) * 0.5
    out["white_floor"] = out["white_avg"] - atr_1m_15m.to_numpy(dtype=float)
    out["red_floor"] = out["red_avg"] - atr_1m_15m.to_numpy(dtype=float)
    out["band_floor_low"] = np.minimum(out["white_floor"], out["red_floor"])
    out["band_avg_high"] = np.maximum(out["white_avg"], out["red_avg"])

    smc = compute_internal_ob_stack_features(out[["open", "high", "low", "close"]].copy(), m111, pivot_size=5, max_display_boxes=SMC_BLOCK_COUNT)
    out = pd.concat([out, smc.reset_index(drop=True)], axis=1)

    out["timestamp"] = pd.to_datetime(out["timestamp"])
    out = out.dropna(
        subset=[
            "atr20",
            "ema20",
            "liq_high_24h_prev",
            "liq_low_24h_prev",
            "trend_4h_confirmed",
            "red_avg",
            "red_floor",
            "white_avg",
            "white_floor",
        ]
    ).reset_index(drop=True)
    return out


def resolve_desired_side(cur_trend: str, price_close: float, row: pd.Series, sr_mode: str) -> int:
    trend_side = 1 if cur_trend == "bullish" else -1

    if sr_mode == "none":
        return trend_side
    if sr_mode == "redavg_align":
        if trend_side > 0 and price_close > float(row["red_avg"]):
            return 1
        if trend_side < 0 and price_close < float(row["red_avg"]):
            return -1
        return 0
    if sr_mode == "redfloor_align":
        if trend_side > 0 and price_close > float(row["red_floor"]):
            return 1
        if trend_side < 0 and price_close < float(row["red_floor"]):
            return -1
        return 0
    if sr_mode == "band_switch":
        if price_close > float(row["band_avg_high"]):
            return 1
        if price_close < float(row["band_floor_low"]):
            return -1
        return 0
    raise ValueError(f"Unsupported sr_mode: {sr_mode}")


def run_variant_114(df: pd.DataFrame, cfg: dict, s76) -> tuple[pd.DataFrame, dict]:
    leverage = float(cfg["leverage"])
    gate_side = str(cfg["gate_side"])
    liq_window = str(cfg["liq_window"])
    gate_bars = int(cfg["gate_bars"])
    body_atr_mult = float(cfg["body_atr_mult"])
    sr_mode = str(cfg["sr_mode"])
    smc_block_mode = str(cfg["smc_block_mode"])
    tp_threshold = SHORT_TP_RETURN_PCT / 100.0

    timestamps = df["timestamp"].to_numpy()
    open_np = df["open"].to_numpy(dtype=float)
    high_np = df["high"].to_numpy(dtype=float)
    low_np = df["low"].to_numpy(dtype=float)
    close_np = df["close"].to_numpy(dtype=float)
    atr20 = df["atr20"].to_numpy(dtype=float)
    ema20 = df["ema20"].to_numpy(dtype=float)
    trend = df["trend_4h_confirmed"].astype(str).to_numpy()
    body = df["body"].to_numpy(dtype=float)
    bearish_stack = df["bearish_stack_5_above"].to_numpy(dtype=bool)
    bullish_stack = df["bullish_stack_5_below"].to_numpy(dtype=bool)

    liq_high_col = "liq_high_8h_prev" if liq_window == "8h" else "liq_high_24h_prev"
    liq_low_col = "liq_low_8h_prev" if liq_window == "8h" else "liq_low_24h_prev"
    liq_high = df[liq_high_col].to_numpy(dtype=float) if liq_window != "none" else np.full(len(df), np.nan)
    liq_low = df[liq_low_col].to_numpy(dtype=float) if liq_window != "none" else np.full(len(df), np.nan)

    wallet = s76.INITIAL_CAPITAL
    reserve = s76.INITIAL_CAPITAL
    margin = 0.0
    qty = 0.0
    entry = 0.0
    side = 0
    entry_wallet = np.nan
    locked_side = 0

    long_gate_until = -10**9
    short_gate_until = -10**9
    prev_trend = None

    rows: list[dict] = []
    stats = {
        "trades": 0,
        "long_entries": 0,
        "short_entries": 0,
        "stop_exits": 0,
        "signal_exits": 0,
        "tp_exits": 0,
        "liquidations": 0,
        "lock_releases": 0,
        "locked_signal_bars": 0,
        "long_sweep_events": 0,
        "short_sweep_events": 0,
        "gated_entries": 0,
        "blocked_long_gate": 0,
        "blocked_short_gate": 0,
        "blocked_long_smc": 0,
        "blocked_short_smc": 0,
        "flat_due_sr": 0,
        "sr_short_override_bars": 0,
        "survived_to_end": 1,
    }
    first_liq_ts = None

    for i in range(len(df)):
        row = df.iloc[i]
        price_open = float(open_np[i])
        price_high = float(high_np[i])
        price_low = float(low_np[i])
        price_close = float(close_np[i])
        cur_trend = str(trend[i])
        blocked_reentry = False

        if prev_trend is not None and cur_trend != prev_trend:
            if cur_trend == "bullish":
                short_gate_until = -10**9
            elif cur_trend == "bearish":
                long_gate_until = -10**9
        prev_trend = cur_trend

        if liq_window != "none":
            strong_body = bool(pd.notna(atr20[i]) and body[i] >= atr20[i] * body_atr_mult)
            long_sweep_event = bool(
                cur_trend == "bullish"
                and strong_body
                and pd.notna(liq_low[i])
                and price_low < liq_low[i]
                and price_close > liq_low[i]
                and price_close > price_open
            )
            short_sweep_event = bool(
                cur_trend == "bearish"
                and strong_body
                and pd.notna(liq_high[i])
                and price_high > liq_high[i]
                and price_close < liq_high[i]
                and price_close < price_open
            )
            if long_sweep_event:
                long_gate_until = max(long_gate_until, i + gate_bars)
                stats["long_sweep_events"] += 1
            if short_sweep_event:
                short_gate_until = max(short_gate_until, i + gate_bars)
                stats["short_sweep_events"] += 1

        if side != 0:
            liq_price = s76._liq_price(entry, leverage, side)
            stop_price = entry * (1.0 - s76.STOP_PCT) if side > 0 else entry * (1.0 + s76.STOP_PCT)

            if side > 0 and leverage > 1.0 and price_low <= liq_price:
                wallet = max(reserve, 0.0)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                entry_wallet = np.nan
                blocked_reentry = True
                stats["trades"] += 1
                stats["liquidations"] += 1
                stats["survived_to_end"] = 0
                if first_liq_ts is None:
                    first_liq_ts = pd.Timestamp(timestamps[i])
            elif side < 0 and leverage > 1.0 and price_high >= liq_price:
                wallet = max(reserve, 0.0)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                entry_wallet = np.nan
                blocked_reentry = True
                stats["trades"] += 1
                stats["liquidations"] += 1
                stats["survived_to_end"] = 0
                if first_liq_ts is None:
                    first_liq_ts = pd.Timestamp(timestamps[i])
            elif side > 0 and price_low <= stop_price:
                wallet = s76._realize_close(reserve, margin, qty, entry, stop_price, side)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                entry_wallet = np.nan
                blocked_reentry = True
                stats["trades"] += 1
                stats["stop_exits"] += 1
            elif side < 0 and price_high >= stop_price:
                wallet = s76._realize_close(reserve, margin, qty, entry, stop_price, side)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                entry_wallet = np.nan
                blocked_reentry = True
                stats["trades"] += 1
                stats["stop_exits"] += 1
            elif side < 0 and entry_wallet > 0:
                marked_wallet = s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
                trade_return = marked_wallet / entry_wallet - 1.0
                if trade_return >= tp_threshold:
                    wallet = s76._realize_close(reserve, margin, qty, entry, price_close, side)
                    reserve = wallet
                    margin = 0.0
                    qty = 0.0
                    entry = 0.0
                    locked_side = side
                    side = 0
                    entry_wallet = np.nan
                    stats["trades"] += 1
                    stats["tp_exits"] += 1

        trend_side = 1 if cur_trend == "bullish" else -1
        desired_side = resolve_desired_side(cur_trend, price_close, row, sr_mode)
        if sr_mode == "band_switch" and desired_side != 0 and desired_side != trend_side:
            stats["sr_short_override_bars"] += 1
        elif desired_side == 0:
            stats["flat_due_sr"] += 1

        if locked_side != 0:
            if desired_side == locked_side:
                desired_side = 0
                stats["locked_signal_bars"] += 1
            elif desired_side == -locked_side:
                locked_side = 0
                stats["lock_releases"] += 1

        if not blocked_reentry and side != desired_side:
            if side != 0:
                wallet = s76._realize_close(reserve, margin, qty, entry, price_close, side)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                entry_wallet = np.nan
                stats["trades"] += 1
                stats["signal_exits"] += 1

            if desired_side != 0 and wallet > 0:
                allow_entry = True
                used_gate = False
                if gate_side in ("long", "both") and desired_side > 0:
                    allow_entry = i <= long_gate_until and price_close > ema20[i]
                    used_gate = allow_entry
                    if not allow_entry:
                        stats["blocked_long_gate"] += 1
                elif gate_side in ("short", "both") and desired_side < 0:
                    allow_entry = i <= short_gate_until and price_close < ema20[i]
                    used_gate = allow_entry
                    if not allow_entry:
                        stats["blocked_short_gate"] += 1

                if allow_entry and smc_block_mode == "opp5":
                    if desired_side > 0 and bool(bearish_stack[i]):
                        allow_entry = False
                        stats["blocked_long_smc"] += 1
                    elif desired_side < 0 and bool(bullish_stack[i]):
                        allow_entry = False
                        stats["blocked_short_smc"] += 1

                if allow_entry:
                    reserve, margin, qty, entry = s76._open_position(wallet, price_close, leverage, desired_side)
                    wallet = reserve + margin
                    side = desired_side
                    entry_wallet = wallet
                    if desired_side > 0:
                        stats["long_entries"] += 1
                    else:
                        stats["short_entries"] += 1
                    if used_gate:
                        stats["gated_entries"] += 1

        equity = wallet if side == 0 else s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
        rows.append(
            {
                "timestamp": timestamps[i],
                "equity": equity,
                "wallet": wallet,
                "reserve": reserve,
                "margin": margin,
                "side": side,
                "locked_side": locked_side,
                "long_gate_open": int(i <= long_gate_until),
                "short_gate_open": int(i <= short_gate_until),
                "variant": str(cfg["variant"]),
            }
        )

    if side != 0 and len(df):
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close_np[-1]), side)
        rows[-1]["equity"] = wallet
        rows[-1]["wallet"] = wallet
        rows[-1]["reserve"] = wallet
        rows[-1]["margin"] = 0.0
        rows[-1]["side"] = 0
        stats["trades"] += 1

    curve = pd.DataFrame(rows)
    stats["first_liquidation_ts"] = first_liq_ts
    return curve, stats


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_block = axes

    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(1000.0, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 114: Current Best + SR / SMC Filters")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_cagr.bar(metrics_df["variant"], metrics_df["cagr_pct"], color=[colors[v] for v in variants], alpha=0.85, label="CAGR %")
    ax_cagr.set_ylabel("CAGR %")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr.tick_params(axis="x", rotation=20)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(metrics_df["variant"], metrics_df["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_cagr_t.set_ylabel("MDD %")
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    block_total = metrics_df["blocked_long_smc"].fillna(0.0) + metrics_df["blocked_short_smc"].fillna(0.0)
    ax_block.bar(metrics_df["variant"], block_total, color=[colors[v] for v in variants], alpha=0.85, label="SMC Blocks")
    ax_block.set_ylabel("SMC Blocks")
    ax_block.grid(True, axis="y", alpha=0.2)
    ax_block.tick_params(axis="x", rotation=20)
    ax_block_t = ax_block.twinx()
    ax_block_t.plot(metrics_df["variant"], metrics_df["delta_calmar_vs_baseline"], color="#9467bd", marker="o", linewidth=1.1, label="Delta Calmar vs Baseline")
    ax_block_t.set_ylabel("Delta Calmar")
    h1, l1 = ax_block.get_legend_handles_labels()
    h2, l2 = ax_block_t.get_legend_handles_labels()
    ax_block.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp):
    baseline = metrics_df[metrics_df["variant"] == BASELINE_CFG["variant"]].iloc[0]
    best = metrics_df.iloc[0]

    lines: list[str] = []
    lines.append("# Study 114: Current Best + SR / SMC Filters")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Baseline is the current best near-90 CAGR family: `short_gate24h_shorttp15_2x` from study 83.")
    lines.append(f"- Backtest period is `{start_ts.date()}` to `{end_ts.date()}` using local BTCUSDT caches.")
    lines.append("- Engine remains the same 15m regime-hold + 24h short sweep gate + short TP lock 15%.")
    lines.append("- SR filters are layered directly onto the current-best engine rather than compared against unrelated studies.")
    lines.append("- Important assumption: the current-best engine has no DCA/add logic, so the SR rule is applied to all openings and direction flips.")
    lines.append(f"- SMC stack filter counts active internal order blocks on 15m bars and blocks longs when bearish boxes fully above price reach `{SMC_BLOCK_COUNT}`, blocks shorts when bullish boxes fully below price reach `{SMC_BLOCK_COUNT}`.")
    lines.append("")
    lines.append("## Baseline")
    lines.append(
        f"- `{baseline['variant']}`: CAGR `{_fmt(baseline['cagr_pct'])}%`, MDD `{_fmt(baseline['max_drawdown_pct'])}%`, "
        f"Calmar `{_fmt(baseline['calmar_ratio'])}`, Final Equity `{_fmt(baseline['final_equity'])}`"
    )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}`: CAGR `{_fmt(best['cagr_pct'])}%`, MDD `{_fmt(best['max_drawdown_pct'])}%`, "
        f"Calmar `{_fmt(best['calmar_ratio'])}`, Final Equity `{_fmt(best['final_equity'])}`"
    )
    lines.append(
        f"- Delta vs baseline: CAGR `{_fmt(best['delta_cagr_vs_baseline'])}pp`, "
        f"MDD `{_fmt(best['delta_mdd_vs_baseline'])}pp`, "
        f"Calmar `{_fmt(best['delta_calmar_vs_baseline'])}`"
    )
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | SR Mode | SMC Filter | CAGR % | MDD % | Calmar | Delta Calmar | Trades | Blocked by SMC | Flat Due SR |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        smc_blocks = float(row.get("blocked_long_smc", 0.0)) + float(row.get("blocked_short_smc", 0.0))
        lines.append(
            f"| {row['variant']} | {row['sr_mode']} | {row['smc_block_mode']} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {_fmt(row['delta_calmar_vs_baseline'])} | "
            f"{_fmt_count(row.get('trades', np.nan))} | {_fmt_count(smc_blocks)} | {_fmt_count(row.get('flat_due_sr', np.nan))} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    if best["variant"] == baseline["variant"]:
        lines.append("- None of the new SR / SMC filters beat the current-best baseline on the chosen ranking.")
    else:
        lines.append("- At least one SR / SMC filtered variant improved on the current-best baseline.")
    lines.append("- `redavg_align` is the most direct test of 'long only above SR / short only below SR' while keeping the 4h trend-follow logic.")
    lines.append("- `band_switch` is the stronger test of 'if price is below the SR band, only short side is allowed'.")
    lines.append("- If SMC-5 variants barely differ from their no-SMC twins, then the active 5-box stack condition is too rare or too loose on this engine.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run_validations(market: pd.DataFrame, metrics_df: pd.DataFrame):
    if pd.to_datetime(market["timestamp"].min()).year != 2021:
        raise AssertionError("backtest did not start in 2021")
    if BASELINE_CFG["variant"] not in set(metrics_df["variant"]):
        raise AssertionError("missing baseline variant")
    if (market["bearish_ob_above_count"] < 0).any() or (market["bullish_ob_below_count"] < 0).any():
        raise AssertionError("negative SMC counts detected")


def run():
    print("Loading modules...")
    m47 = load_module("study47_for_114", BASE_47_PATH)
    s76 = load_module("study76_for_114", BASE_76_PATH)
    m111 = load_module("study111_for_114", BASE_111_PATH)

    print("Loading 2021+ market data...")
    df_1m, df_4h, end_ts = load_market_data_2021plus()
    market = prepare_market_114(df_1m, df_4h, m47, m111)

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    print("Running variants...")
    for idx, cfg in enumerate(VARIANTS, start=1):
        print(f"  variant {idx}/{len(VARIANTS)} -> {cfg['variant']}")
        curve, run_stats = run_variant_114(market, cfg, s76)
        stats = compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL)
        row = {"variant": str(cfg["variant"]), "sr_mode": str(cfg["sr_mode"]), "smc_block_mode": str(cfg["smc_block_mode"]), **stats, **run_stats}
        rows.append(row)
        curves_out.append(curve.copy())
        curve_map[str(cfg["variant"])] = curve.copy()

    metrics_df = pd.DataFrame(rows)
    baseline_row = metrics_df[metrics_df["variant"] == BASELINE_CFG["variant"]].iloc[0]
    metrics_df["delta_cagr_vs_baseline"] = metrics_df["cagr_pct"] - float(baseline_row["cagr_pct"])
    metrics_df["delta_mdd_vs_baseline"] = metrics_df["max_drawdown_pct"] - float(baseline_row["max_drawdown_pct"])
    metrics_df["delta_calmar_vs_baseline"] = metrics_df["calmar_ratio"] - float(baseline_row["calmar_ratio"])
    metrics_df = metrics_df.sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curves_out, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df)
    save_report(metrics_df, pd.Timestamp(market["timestamp"].min()), end_ts)
    run_validations(market, metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    run()
