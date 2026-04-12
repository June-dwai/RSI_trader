from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd


EMA_PERIOD_4H = 200
HYSTERESIS_BAND = 0.005
COMMISSION = 0.0004

CASE2_ENTRY_SCALE = 0.60
CASE2_MAX_ENTRIES = 4
CASE2_RSI_PERIOD = 6
CASE2_RSI_OVERSOLD = 18
CASE2_RSI_OVERBOUGHT = 85
CASE2_ADX_PERIOD = 14
CASE2_TP_PCT = 0.012
CASE2_STOP_PCT = 0.03
CASE2_BASE_COOLDOWN_BARS = 5

CASE3_LEVERAGE = 3.0
CASE3_MARGIN_FRACTION = 0.98
CASE3_STOP_PCT = 0.06
CASE3_SHORT_TP_PCT = 0.20
CASE3_GATE_BARS = 12
CASE3_BODY_ATR_MULT = 0.25
CASE3_LONG_MAX_BEARISH_OB_ABOVE = 4
CASE3_LONG_DELAY_BARS = 8
CASE3_MAINTENANCE_MARGIN_RATE = 0.005


def _safe_timestamp(value: Any) -> pd.Timestamp | None:
    if value is None or value == "":
        return None
    ts = pd.Timestamp(value)
    return None if pd.isna(ts) else ts


def _bars_since(last_ts: pd.Timestamp | None, timestamps: pd.Series) -> int:
    if last_ts is None:
        return 10**9
    return int((timestamps > last_ts).sum())


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    return pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)


def _atr_series(high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
    return _true_range(high, low, close).rolling(length, min_periods=length).mean()


def _atr_array(high: np.ndarray, low: np.ndarray, close: np.ndarray, length: int) -> np.ndarray:
    return _true_range(pd.Series(high), pd.Series(low), pd.Series(close)).rolling(length, min_periods=length).mean().to_numpy(dtype=float)


def _resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in df.columns:
        agg["volume"] = "sum"
    return (
        df.resample(rule, label="right", closed="right")
        .agg(agg)
        .dropna(subset=["open", "high", "low", "close"])
    )


def _map_series_to_target(series: pd.Series, target_index: pd.DatetimeIndex) -> pd.Series:
    mapped = series.reindex(target_index, method="ffill")
    mapped.index = target_index
    return mapped


def calculate_rsi(closes: pd.Series, period: int) -> pd.Series:
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi[(avg_loss == 0) & (avg_gain > 0)] = 100
    rsi[(avg_gain == 0) & (avg_loss > 0)] = 0
    rsi[(avg_gain == 0) & (avg_loss == 0)] = 50
    return rsi.fillna(50)


def calculate_adx_case2(df: pd.DataFrame, period: int = CASE2_ADX_PERIOD) -> pd.Series:
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


def _compute_hysteresis_state(close_series: pd.Series, ema_series: pd.Series, hysteresis: float) -> pd.Series:
    states: list[str | float] = []
    prev_state: str | None = None
    for close, ema in zip(close_series, ema_series):
        if pd.isna(close) or pd.isna(ema):
            states.append(np.nan)
            continue
        upper = ema * (1.0 + hysteresis)
        lower = ema * (1.0 - hysteresis)
        if close > upper:
            state = "bullish"
        elif close < lower:
            state = "bearish"
        else:
            state = ("bullish" if close > ema else "bearish") if prev_state is None else prev_state
        states.append(state)
        prev_state = state
    return pd.Series(states, index=close_series.index)


def _get_adx_multiplier(adx: float) -> int:
    if adx >= 50:
        return 3
    if adx >= 40:
        return 2
    return 1


@dataclass
class TradeAction:
    action: str
    side: str | None
    reason: str
    quantity_mode: str
    quantity_value: float
    reduce_only: bool = False
    reference_price: float | None = None
    desired_leverage: float | None = None
    stop_price: float | None = None
    take_profit_price: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Case2State:
    last_processed_ts: pd.Timestamp | None = None
    last_order_ts: pd.Timestamp | None = None
    position_side: str | None = None
    avg_entry_price: float = 0.0
    position_qty: float = 0.0
    base_entry_qty: float = 0.0
    entry_count: int = 0
    recent_trade_price: float = 0.0
    stop_trigger_price: float = 0.0
    stop_reentry_signed_qty: float = 0.0
    pending_reentry_side: str | None = None
    pending_reentry_price: float = 0.0
    pending_reentry_qty: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        for key in ("last_processed_ts", "last_order_ts"):
            out[key] = out[key].isoformat() if out[key] is not None else None
        return out

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Case2State":
        data = dict(raw)
        data["last_processed_ts"] = _safe_timestamp(data.get("last_processed_ts"))
        data["last_order_ts"] = _safe_timestamp(data.get("last_order_ts"))
        return cls(**data)


@dataclass
class Case3State:
    last_processed_ts: pd.Timestamp | None = None
    position_side: str | None = None
    avg_entry_price: float = 0.0
    position_qty: float = 0.0
    locked_side: str | None = None
    short_gate_until_ts: pd.Timestamp | None = None
    bullish_streak: int = 0
    last_short_sweep_ts: pd.Timestamp | None = None

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        for key in ("last_processed_ts", "short_gate_until_ts", "last_short_sweep_ts"):
            out[key] = out[key].isoformat() if out[key] is not None else None
        return out

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Case3State":
        data = dict(raw)
        data["last_processed_ts"] = _safe_timestamp(data.get("last_processed_ts"))
        data["short_gate_until_ts"] = _safe_timestamp(data.get("short_gate_until_ts"))
        data["last_short_sweep_ts"] = _safe_timestamp(data.get("last_short_sweep_ts"))
        return cls(**data)


def sync_case2_state_from_broker(
    state: Case2State,
    position_side: str | None,
    avg_entry_price: float,
    position_qty: float,
    *,
    base_entry_qty: float | None = None,
    recent_trade_price: float | None = None,
) -> Case2State:
    state.position_side = position_side
    state.avg_entry_price = float(avg_entry_price or 0.0)
    state.position_qty = float(position_qty or 0.0)
    if position_side is None or position_qty <= 0:
        state.position_side = None
        state.avg_entry_price = 0.0
        state.position_qty = 0.0
        state.entry_count = 0
        state.base_entry_qty = 0.0
        state.recent_trade_price = 0.0
        return state

    if base_entry_qty is not None and base_entry_qty > 0:
        state.base_entry_qty = float(base_entry_qty)
    elif state.base_entry_qty <= 0:
        state.base_entry_qty = float(position_qty)
    state.entry_count = max(1, int(round(state.position_qty / max(state.base_entry_qty, 1e-12))))
    if recent_trade_price is not None and recent_trade_price > 0:
        state.recent_trade_price = float(recent_trade_price)
    elif state.recent_trade_price <= 0:
        state.recent_trade_price = state.avg_entry_price
    return state


def sync_case3_state_from_broker(
    state: Case3State,
    position_side: str | None,
    avg_entry_price: float,
    position_qty: float,
) -> Case3State:
    state.position_side = position_side
    state.avg_entry_price = float(avg_entry_price or 0.0)
    state.position_qty = float(position_qty or 0.0)
    if position_side is None or position_qty <= 0:
        state.position_side = None
        state.avg_entry_price = 0.0
        state.position_qty = 0.0
    return state


def prepare_case2_features(df_1m: pd.DataFrame, df_4h: pd.DataFrame) -> pd.DataFrame:
    out_1m = df_1m.copy().sort_index()
    out_4h = df_4h.copy().sort_index()
    if not isinstance(out_1m.index, pd.DatetimeIndex):
        out_1m.index = pd.to_datetime(out_1m.index)
    if not isinstance(out_4h.index, pd.DatetimeIndex):
        out_4h.index = pd.to_datetime(out_4h.index)

    out_1m["rsi"] = calculate_rsi(out_1m["close"], period=CASE2_RSI_PERIOD)
    out_1m["adx"] = calculate_adx_case2(out_1m, period=CASE2_ADX_PERIOD)

    out_4h["ema200_closed"] = out_4h["close"].ewm(span=EMA_PERIOD_4H, adjust=False).mean()
    out_4h["ema200_prev_closed"] = out_4h["ema200_closed"].shift(1)
    out_4h["touch_closed"] = (out_4h["high"] >= out_4h["ema200_closed"]) & (out_4h["low"] <= out_4h["ema200_closed"])
    out_4h["touch_prev_closed"] = out_4h["touch_closed"].shift(1).fillna(False)

    out_1m["bucket_4h"] = out_1m.index.floor("4h")
    out_1m = out_1m.merge(
        out_4h[["ema200_prev_closed", "touch_prev_closed"]],
        left_on="bucket_4h",
        right_index=True,
        how="left",
    )
    out_1m["ema200_prev_closed"] = out_1m["ema200_prev_closed"].ffill()
    out_1m["touch_prev_closed"] = out_1m["touch_prev_closed"].fillna(False)
    out_1m["ema_touch_live_nla"] = out_1m["touch_prev_closed"]
    out_1m["trend_prev_ema"] = np.where(out_1m["close"] > out_1m["ema200_prev_closed"], "bullish", "bearish")
    out_1m["timestamp"] = pd.to_datetime(out_1m.index)
    return out_1m.dropna(subset=["rsi", "adx", "ema200_prev_closed"]).reset_index(drop=True)


def compute_internal_ob_stack_features(bars: pd.DataFrame, pivot_size: int = 5, max_display_boxes: int = 5) -> pd.DataFrame:
    high = bars["high"].to_numpy(dtype=float)
    low = bars["low"].to_numpy(dtype=float)
    close = bars["close"].to_numpy(dtype=float)
    n = len(bars)

    atr200 = _atr_array(high, low, close, 200)
    high_volatility = (high - low) >= (2.0 * atr200)
    parsed_high = np.where(high_volatility, low, high)
    parsed_low = np.where(high_volatility, high, low)

    bearish_above_count = np.zeros(n, dtype=int)
    bullish_below_count = np.zeros(n, dtype=int)

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
        bullish_below_count[i] = int(min(max_display_boxes, sum(1 for ob in shown_bullish if ob["top"] < close[i])))
        bearish_above_count[i] = int(min(max_display_boxes, sum(1 for ob in shown_bearish if ob["bottom"] > close[i])))

    return pd.DataFrame(
        {
            "bullish_ob_below_count": bullish_below_count,
            "bearish_ob_above_count": bearish_above_count,
        },
        index=bars.index,
    )


def prepare_case3best_features(df_1m: pd.DataFrame, df_4h: pd.DataFrame) -> pd.DataFrame:
    out_1m = df_1m.copy().sort_index()
    out_4h = df_4h.copy().sort_index()
    if not isinstance(out_1m.index, pd.DatetimeIndex):
        out_1m.index = pd.to_datetime(out_1m.index)
    if not isinstance(out_4h.index, pd.DatetimeIndex):
        out_4h.index = pd.to_datetime(out_4h.index)

    bars_15m = _resample_ohlc(out_1m, "15min")
    bars_1h = _resample_ohlc(out_1m, "1h")

    out_4h["ema200_closed"] = out_4h["close"].ewm(span=EMA_PERIOD_4H, adjust=False).mean()
    out_4h["ema200_prev_closed"] = out_4h["ema200_closed"].shift(1)
    out_4h["trend_4h_hyst"] = _compute_hysteresis_state(out_4h["close"], out_4h["ema200_prev_closed"], HYSTERESIS_BAND)
    out_4h["trend_4h_confirmed"] = out_4h["trend_4h_hyst"].shift(1)
    out_4h = out_4h.reset_index().rename(columns={"index": "timestamp"})

    bars_1h["liq_high_24h_prev"] = bars_1h["high"].rolling(24).max().shift(1)
    bars_1h = bars_1h.reset_index().rename(columns={"index": "timestamp"})

    out = bars_15m.reset_index().rename(columns={"index": "timestamp"})
    out["body"] = (out["close"] - out["open"]).abs()
    out["atr20"] = _true_range(out["high"], out["low"], out["close"]).rolling(20).mean()
    out["ema20"] = out["close"].ewm(span=20, adjust=False).mean()

    out = pd.merge_asof(
        out.sort_values("timestamp"),
        bars_1h.sort_values("timestamp")[["timestamp", "liq_high_24h_prev"]],
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
    atr_1m = _atr_series(out_1m["high"], out_1m["low"], out_1m["close"], 14)

    fast_15m = _map_series_to_target(ema_fast_1m, target_index)
    slow_1m_15m = _map_series_to_target(ema_slow_1m, target_index)
    slow_2m_15m = _map_series_to_target(ema_slow_2m, target_index)
    atr_1m_15m = _map_series_to_target(atr_1m, target_index)

    out["white_avg"] = (fast_15m.to_numpy(dtype=float) + slow_1m_15m.to_numpy(dtype=float)) * 0.5
    out["red_avg"] = (fast_15m.to_numpy(dtype=float) + slow_2m_15m.to_numpy(dtype=float)) * 0.5
    out["white_floor"] = out["white_avg"] - atr_1m_15m.to_numpy(dtype=float)
    out["red_floor"] = out["red_avg"] - atr_1m_15m.to_numpy(dtype=float)

    smc = compute_internal_ob_stack_features(out[["open", "high", "low", "close"]].copy(), pivot_size=5, max_display_boxes=5)
    out = pd.concat([out, smc.reset_index(drop=True)], axis=1)
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    return out.dropna(
        subset=["atr20", "ema20", "liq_high_24h_prev", "trend_4h_confirmed", "white_avg", "red_avg", "red_floor"]
    ).reset_index(drop=True)


def evaluate_case2_latest(
    df_1m: pd.DataFrame,
    df_4h: pd.DataFrame,
    state: Case2State,
) -> tuple[list[TradeAction], Case2State, dict[str, Any]]:
    features = prepare_case2_features(df_1m, df_4h)
    if features.empty:
        return [], state, {"status": "not_ready"}

    row = features.iloc[-1]
    ts = pd.Timestamp(row["timestamp"])
    if state.last_processed_ts is not None and ts <= state.last_processed_ts:
        return [], state, {"status": "duplicate_bar", "timestamp": ts}

    actions: list[TradeAction] = []
    price = float(row["close"])
    rsi = float(row["rsi"])
    adx = float(row["adx"])
    trend = str(row["trend_prev_ema"])
    ema_touch = bool(row["ema_touch_live_nla"])
    cooldown_bars = CASE2_BASE_COOLDOWN_BARS + (state.entry_count if state.position_side else 0)
    bars_since_last = _bars_since(state.last_order_ts, features["timestamp"])

    if state.position_side and state.position_qty > 0:
        if state.stop_reentry_signed_qty == 0:
            if state.position_side == "LONG" and price <= state.avg_entry_price * (1.0 - CASE2_STOP_PCT):
                close_qty = state.position_qty * 0.8
                actions.append(
                    TradeAction(
                        action="PARTIAL_CLOSE",
                        side="LONG",
                        reason="case2_stop_loss",
                        quantity_mode="position_fraction",
                        quantity_value=0.80,
                        reduce_only=True,
                        reference_price=price,
                    )
                )
                state.stop_trigger_price = price
                state.stop_reentry_signed_qty = close_qty
                state.pending_reentry_side = "LONG"
                state.pending_reentry_qty = close_qty
                state.pending_reentry_price = price * (1.0 - CASE2_STOP_PCT)
            elif state.position_side == "SHORT" and price >= state.avg_entry_price * (1.0 + CASE2_STOP_PCT):
                close_qty = state.position_qty * 0.8
                actions.append(
                    TradeAction(
                        action="PARTIAL_CLOSE",
                        side="SHORT",
                        reason="case2_stop_loss",
                        quantity_mode="position_fraction",
                        quantity_value=0.80,
                        reduce_only=True,
                        reference_price=price,
                    )
                )
                state.stop_trigger_price = price
                state.stop_reentry_signed_qty = -close_qty
                state.pending_reentry_side = "SHORT"
                state.pending_reentry_qty = close_qty
                state.pending_reentry_price = price * (1.0 + CASE2_STOP_PCT)
        elif state.pending_reentry_side == "LONG" and price <= state.pending_reentry_price:
            actions.append(
                TradeAction(
                    action="ADD",
                    side="LONG",
                    reason="case2_reentry",
                    quantity_mode="absolute_qty",
                    quantity_value=state.pending_reentry_qty,
                    reference_price=state.pending_reentry_price,
                )
            )
            state.stop_trigger_price = price
            state.stop_reentry_signed_qty = 0.0
            state.pending_reentry_side = None
            state.pending_reentry_price = 0.0
            state.pending_reentry_qty = 0.0
        elif state.pending_reentry_side == "SHORT" and price >= state.pending_reentry_price:
            actions.append(
                TradeAction(
                    action="ADD",
                    side="SHORT",
                    reason="case2_reentry",
                    quantity_mode="absolute_qty",
                    quantity_value=state.pending_reentry_qty,
                    reference_price=state.pending_reentry_price,
                )
            )
            state.stop_trigger_price = price
            state.stop_reentry_signed_qty = 0.0
            state.pending_reentry_side = None
            state.pending_reentry_price = 0.0
            state.pending_reentry_qty = 0.0

    if (not ema_touch) and bars_since_last >= cooldown_bars:
        if rsi <= CASE2_RSI_OVERSOLD and trend == "bullish":
            if not state.position_side:
                actions.append(
                    TradeAction(
                        action="OPEN",
                        side="LONG",
                        reason="case2_open_long",
                        quantity_mode="capital_fraction",
                        quantity_value=CASE2_ENTRY_SCALE,
                        reference_price=price,
                    )
                )
            elif state.position_side == "LONG" and state.recent_trade_price > 0 and price <= state.recent_trade_price * 0.995:
                mult = _get_adx_multiplier(adx)
                if state.entry_count < CASE2_MAX_ENTRIES:
                    actions.append(
                        TradeAction(
                            action="ADD",
                            side="LONG",
                            reason="case2_dca_long",
                            quantity_mode="base_qty_multiple",
                            quantity_value=float(mult),
                            reference_price=price,
                            meta={"adx": adx},
                        )
                    )
            elif state.position_side == "SHORT":
                actions.extend(
                    [
                        TradeAction(
                            action="PARTIAL_CLOSE",
                            side="SHORT",
                            reason="case2_reverse_close",
                            quantity_mode="position_fraction",
                            quantity_value=0.80,
                            reduce_only=True,
                            reference_price=price,
                        ),
                        TradeAction(
                            action="OPEN",
                            side="LONG",
                            reason="case2_reverse_open",
                            quantity_mode="capital_fraction",
                            quantity_value=CASE2_ENTRY_SCALE,
                            reference_price=price,
                        ),
                    ]
                )
        elif rsi >= CASE2_RSI_OVERBOUGHT and trend == "bearish":
            if not state.position_side:
                actions.append(
                    TradeAction(
                        action="OPEN",
                        side="SHORT",
                        reason="case2_open_short",
                        quantity_mode="capital_fraction",
                        quantity_value=CASE2_ENTRY_SCALE,
                        reference_price=price,
                    )
                )
            elif state.position_side == "SHORT" and state.recent_trade_price > 0 and price >= state.recent_trade_price * 1.005:
                mult = _get_adx_multiplier(adx)
                if state.entry_count < CASE2_MAX_ENTRIES:
                    actions.append(
                        TradeAction(
                            action="ADD",
                            side="SHORT",
                            reason="case2_dca_short",
                            quantity_mode="base_qty_multiple",
                            quantity_value=float(mult),
                            reference_price=price,
                            meta={"adx": adx},
                        )
                    )
            elif state.position_side == "LONG":
                actions.extend(
                    [
                        TradeAction(
                            action="PARTIAL_CLOSE",
                            side="LONG",
                            reason="case2_reverse_close",
                            quantity_mode="position_fraction",
                            quantity_value=0.80,
                            reduce_only=True,
                            reference_price=price,
                        ),
                        TradeAction(
                            action="OPEN",
                            side="SHORT",
                            reason="case2_reverse_open",
                            quantity_mode="capital_fraction",
                            quantity_value=CASE2_ENTRY_SCALE,
                            reference_price=price,
                        ),
                    ]
                )

    if state.position_side == "LONG" and state.avg_entry_price > 0 and price >= state.avg_entry_price * (1.0 + CASE2_TP_PCT):
        actions.append(
            TradeAction(
                action="CLOSE",
                side="LONG",
                reason="case2_take_profit",
                quantity_mode="position_fraction",
                quantity_value=1.0,
                reduce_only=True,
                reference_price=price,
            )
        )
    elif state.position_side == "SHORT" and state.avg_entry_price > 0 and price <= state.avg_entry_price * (1.0 - CASE2_TP_PCT):
        actions.append(
            TradeAction(
                action="CLOSE",
                side="SHORT",
                reason="case2_take_profit",
                quantity_mode="position_fraction",
                quantity_value=1.0,
                reduce_only=True,
                reference_price=price,
            )
        )

    state.last_processed_ts = ts
    diagnostics = {
        "timestamp": ts,
        "price": price,
        "trend": trend,
        "ema_touch_live_nla": ema_touch,
        "rsi": rsi,
        "adx": adx,
        "bars_since_last_order": bars_since_last,
        "cooldown_bars": cooldown_bars,
    }
    return actions, state, diagnostics


def _case3_liq_price(entry: float, leverage: float, side: str) -> float:
    if leverage <= 1.0:
        return 0.0 if side == "LONG" else float("inf")
    if side == "LONG":
        return entry * (1.0 - 1.0 / leverage) / (1.0 - CASE3_MAINTENANCE_MARGIN_RATE)
    return entry * (1.0 + 1.0 / leverage) / (1.0 + CASE3_MAINTENANCE_MARGIN_RATE)


def evaluate_case3best_latest(
    df_1m: pd.DataFrame,
    df_4h: pd.DataFrame,
    state: Case3State,
) -> tuple[list[TradeAction], Case3State, dict[str, Any]]:
    features = prepare_case3best_features(df_1m, df_4h)
    if features.empty:
        return [], state, {"status": "not_ready"}

    row = features.iloc[-1]
    ts = pd.Timestamp(row["timestamp"])
    if state.last_processed_ts is not None and ts <= state.last_processed_ts:
        return [], state, {"status": "duplicate_bar", "timestamp": ts}

    price_open = float(row["open"])
    price_high = float(row["high"])
    price_low = float(row["low"])
    price_close = float(row["close"])
    cur_trend = str(row["trend_4h_confirmed"])
    actions: list[TradeAction] = []

    if cur_trend == "bullish":
        state.bullish_streak += 1
    else:
        state.bullish_streak = 0

    if cur_trend == "bullish":
        state.short_gate_until_ts = None

    short_sweep_event = bool(
        cur_trend == "bearish"
        and pd.notna(row["liq_high_24h_prev"])
        and pd.notna(row["atr20"])
        and abs(price_close - price_open) >= float(row["atr20"]) * CASE3_BODY_ATR_MULT
        and price_high > float(row["liq_high_24h_prev"])
        and price_close < float(row["liq_high_24h_prev"])
        and price_close < price_open
    )
    if short_sweep_event:
        state.last_short_sweep_ts = ts
        state.short_gate_until_ts = ts + pd.Timedelta(minutes=15 * CASE3_GATE_BARS)

    if state.position_side and state.avg_entry_price > 0:
        stop_price = state.avg_entry_price * (1.0 - CASE3_STOP_PCT) if state.position_side == "LONG" else state.avg_entry_price * (1.0 + CASE3_STOP_PCT)
        liq_price = _case3_liq_price(state.avg_entry_price, CASE3_LEVERAGE, state.position_side)

        if state.position_side == "LONG" and price_low <= liq_price:
            actions.append(
                TradeAction(
                    action="CLOSE",
                    side="LONG",
                    reason="case3_liquidation_guard",
                    quantity_mode="position_fraction",
                    quantity_value=1.0,
                    reduce_only=True,
                    reference_price=liq_price,
                )
            )
        elif state.position_side == "SHORT" and price_high >= liq_price:
            actions.append(
                TradeAction(
                    action="CLOSE",
                    side="SHORT",
                    reason="case3_liquidation_guard",
                    quantity_mode="position_fraction",
                    quantity_value=1.0,
                    reduce_only=True,
                    reference_price=liq_price,
                )
            )
        elif state.position_side == "LONG" and price_low <= stop_price:
            actions.append(
                TradeAction(
                    action="CLOSE",
                    side="LONG",
                    reason="case3_stop_loss",
                    quantity_mode="position_fraction",
                    quantity_value=1.0,
                    reduce_only=True,
                    reference_price=stop_price,
                )
            )
        elif state.position_side == "SHORT" and price_high >= stop_price:
            actions.append(
                TradeAction(
                    action="CLOSE",
                    side="SHORT",
                    reason="case3_stop_loss",
                    quantity_mode="position_fraction",
                    quantity_value=1.0,
                    reduce_only=True,
                    reference_price=stop_price,
                )
            )
        elif state.position_side == "SHORT":
            short_return = state.avg_entry_price / price_close - 1.0
            if short_return >= CASE3_SHORT_TP_PCT:
                actions.append(
                    TradeAction(
                        action="CLOSE",
                        side="SHORT",
                        reason="case3_short_tp",
                        quantity_mode="position_fraction",
                        quantity_value=1.0,
                        reduce_only=True,
                        reference_price=price_close,
                    )
                )
                state.locked_side = "SHORT"

    desired_side = "LONG" if cur_trend == "bullish" else "SHORT"
    if state.locked_side is not None:
        if desired_side == state.locked_side:
            desired_side = None
        else:
            state.locked_side = None

    gate_open = state.short_gate_until_ts is not None and ts <= state.short_gate_until_ts
    bullish_delay_ok = state.bullish_streak > CASE3_LONG_DELAY_BARS
    long_quality_ok = int(row["bearish_ob_above_count"]) <= CASE3_LONG_MAX_BEARISH_OB_ABOVE and bullish_delay_ok
    short_gate_ok = gate_open and price_close < float(row["ema20"])

    if state.position_side is not None and desired_side is not None and state.position_side != desired_side:
        actions.append(
            TradeAction(
                action="CLOSE",
                side=state.position_side,
                reason="case3_signal_flip",
                quantity_mode="position_fraction",
                quantity_value=1.0,
                reduce_only=True,
                reference_price=price_close,
            )
        )

    if desired_side == "LONG" and (state.position_side is None or state.position_side != "LONG") and long_quality_ok:
        actions.append(
            TradeAction(
                action="OPEN",
                side="LONG",
                reason="case3_open_long",
                quantity_mode="wallet_fraction",
                quantity_value=CASE3_MARGIN_FRACTION,
                desired_leverage=CASE3_LEVERAGE,
                reference_price=price_close,
                stop_price=price_close * (1.0 - CASE3_STOP_PCT),
                meta={"bullish_streak": state.bullish_streak, "bearish_ob_above_count": int(row["bearish_ob_above_count"])},
            )
        )
    elif desired_side == "SHORT" and (state.position_side is None or state.position_side != "SHORT") and short_gate_ok:
        actions.append(
            TradeAction(
                action="OPEN",
                side="SHORT",
                reason="case3_open_short",
                quantity_mode="wallet_fraction",
                quantity_value=CASE3_MARGIN_FRACTION,
                desired_leverage=CASE3_LEVERAGE,
                reference_price=price_close,
                stop_price=price_close * (1.0 + CASE3_STOP_PCT),
                take_profit_price=price_close * (1.0 - CASE3_SHORT_TP_PCT),
                meta={"short_gate_open": True, "short_sweep_event": short_sweep_event},
            )
        )

    state.last_processed_ts = ts
    diagnostics = {
        "timestamp": ts,
        "price": price_close,
        "trend_4h_confirmed": cur_trend,
        "short_sweep_event": short_sweep_event,
        "short_gate_open": gate_open,
        "bullish_streak": state.bullish_streak,
        "bearish_ob_above_count": int(row["bearish_ob_above_count"]),
        "bullish_ob_below_count": int(row["bullish_ob_below_count"]),
        "bullish_delay_ok": bullish_delay_ok,
        "long_quality_ok": long_quality_ok,
        "short_gate_ok": short_gate_ok,
    }
    return actions, state, diagnostics


def example_strategy_names() -> dict[str, str]:
    return {
        "case2": "Study 42 case2 live logic",
        "case3best": "Study 126 raw-best case3 live logic (lb4_delay8_capna_cd0)",
    }
