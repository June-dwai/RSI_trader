from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
BASE_32_PATH = Path("32_backtest_btcusdt_live_nla.py")
BASE_42_PATH = Path("42_backtest_btcusdt_scale06_adx002_equity_combo.py")
BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
BASE_62_PATH = Path("62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune.py")
BASE_76_PATH = Path("76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py")
BASE_82_PATH = Path("82_backtest_btcusdt_scale06_adx002_ict_smc_archetypes.py")
BASE_84_PATH = Path("84_backtest_btcusdt_scale06_adx002_smc_short_gate_tune.py")
BASE_86_PATH = Path("86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.py")
FLOW_MARKET_CSV = Path("96_backtest_btcusdt_scale06_adx002_case123_flow_proxy_sweep_market_state_4h.csv")

OUT_BASE = "105_backtest_btcusdt_scale06_adx002_allocator_realism_compare"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_STATE_CSV = Path(f"{OUT_BASE}_sleeve_state.csv")
OUT_FLAT_SUMMARY_CSV = Path(f"{OUT_BASE}_flat_summary.csv")

LATEST_END_DATE = "2026-03-15"
INITIAL_CAPITAL_TOTAL = 2000.0
INITIAL_CAPITAL_CASE = 1000.0
ENTRY_SCALE = 0.60
MONTHLY_TOPUP = 1000.0
THRESHOLD = 0.02
REBALANCE_FEE_RATE = 0.0004

BASE_WEIGHTS = (0.62, 0.31, 0.07)
SELL_WEIGHTS = (0.58, 0.30, 0.12)
SQUEEZE_WEIGHTS = (0.66, 0.31, 0.03)

CASE3_CFG = {
    "variant": "short_gate_24h_g12_tp15",
    "liq_hours": 24,
    "gate_bars": 12,
    "body_atr_mult": 0.25,
    "tp_return_pct": 15.0,
}
CASE3_LEVERAGE = 2.0

SCENARIOS = [
    {
        "variant": "fullreb_flow_thr2",
        "mode": "fullreb",
        "description": "98번과 같은 upper-bound. target drift 2% 넘으면 포지션까지 같이 리사이즈된 것으로 간주.",
    },
    {
        "variant": "cashonly_flow",
        "mode": "cashonly",
        "description": "월 입금만 underweight 쪽에 넣고, 기존 자본은 한 번도 옮기지 않음.",
    },
    {
        "variant": "openfloor_flow_thr2",
        "mode": "openfloor",
        "description": "열린 sleeve에서는 자본을 뺄 수 없고, 추가 자본만 넣을 수 있다고 가정.",
    },
    {
        "variant": "flatfreeze_flow_thr2",
        "mode": "flatfreeze",
        "description": "열린 sleeve는 자본도 아예 건드리지 않고, flat sleeve끼리만 자본 이동.",
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


def compute_month_flags(ts: pd.Series) -> np.ndarray:
    flags = (ts.dt.to_period("M") != ts.dt.to_period("M").shift(1)).to_numpy(copy=True)
    if len(flags):
        flags[0] = False
    return flags


def project_to_simplex(values: np.ndarray, target_sum: float) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return values.copy()
    if target_sum <= 0:
        return np.zeros_like(values)
    u = np.sort(values)[::-1]
    cssv = np.cumsum(u) - target_sum
    idx = np.arange(1, len(values) + 1, dtype=float)
    cond = u - cssv / idx > 0
    if not np.any(cond):
        return np.full_like(values, target_sum / len(values))
    rho = int(np.nonzero(cond)[0][-1])
    theta = cssv[rho] / float(rho + 1)
    return np.maximum(values - theta, 0.0)


def get_target_weights(row: pd.Series) -> tuple[float, float, float]:
    if bool(row["squeeze_risk_active_3"]):
        return SQUEEZE_WEIGHTS
    if bool(row["sell_climax_active_6"]):
        return SELL_WEIGHTS
    return BASE_WEIGHTS


def merge_state_to_curve(curve: pd.DataFrame, state_df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    left = curve.copy().sort_values("timestamp").reset_index(drop=True)
    right = state_df.copy().sort_values("timestamp").reset_index(drop=True)
    left["timestamp"] = left["timestamp"].to_numpy(dtype="datetime64[ns]")
    right["timestamp"] = right["timestamp"].to_numpy(dtype="datetime64[ns]")
    return pd.merge_asof(left, right[["timestamp"] + cols], on="timestamp", direction="backward")


def load_flow_market_state() -> pd.DataFrame:
    market = pd.read_csv(FLOW_MARKET_CSV, parse_dates=["timestamp"])
    market["sell_climax_active_6"] = market["sell_climax_active_6"].astype(str).str.lower().eq("true")
    market["squeeze_risk_active_3"] = market["squeeze_risk_active_3"].astype(str).str.lower().eq("true")
    market = market[["timestamp", "trend_4h_confirmed", "sell_climax_active_6", "squeeze_risk_active_3"]].copy()
    return market.sort_values("timestamp").reset_index(drop=True)


def build_case1_probe(m47, s62, df_1m: pd.DataFrame, df_4h: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base_cls = s62.build_variant_class(m47.LiveParityNoLookahead, bullish_close_bars=2, shallow_gap_pct=0.06)

    class Case1Probe(base_cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.state_rows: list[dict] = []

        def _record_equity(self, price, timestamp, ema):
            super()._record_equity(price, timestamp, ema)
            self.state_rows.append(
                {
                    "timestamp": pd.to_datetime(timestamp),
                    "case1_flat": self.current_position is None and self.hedge_position is None,
                    "case1_side": "" if self.current_position is None else str(self.current_position["side"]),
                    "case1_has_hedge": self.hedge_position is not None,
                    "case1_entry_count": int(self.entry_count),
                }
            )

    bt = Case1Probe(
        symbol=m47.SYMBOL,
        initial_capital=INITIAL_CAPITAL_CASE,
        commission=m47.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    m47.configure_baseline_params(bt)
    bt.run(df_1m, df_4h, backtest_start_date=m47.BACKTEST_START)

    curve = pd.DataFrame(bt.equity_curve)[["timestamp", "equity"]].rename(columns={"equity": "equity_case1"})
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)

    state = pd.DataFrame(bt.state_rows)
    state["timestamp"] = pd.to_datetime(state["timestamp"])
    state = state.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    return curve, state


def build_case2_probe(m47, base002, helper04, m32, s42, df_1m: pd.DataFrame, df_4h: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base002.BACKTEST_END = LATEST_END_DATE
    base_cls = s42.build_case2_class(m32)

    class Case2Probe(base_cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.state_rows: list[dict] = []

        def _record_equity(self, price, timestamp, ema):
            super()._record_equity(price, timestamp, ema)
            self.state_rows.append(
                {
                    "timestamp": pd.to_datetime(timestamp),
                    "case2_flat": self.current_position is None,
                    "case2_side": "" if self.current_position is None else str(self.current_position["side"]),
                    "case2_entry_count": int(self.entry_count),
                }
            )

    bt = Case2Probe(
        base_module=base002,
        symbol=base002.SYMBOL,
        initial_capital=INITIAL_CAPITAL_CASE,
        commission=base002.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    helper04.configure_baseline_params(bt)
    bt.run(df_1m, df_4h, backtest_start_date=base002.BACKTEST_START)

    curve = pd.DataFrame(bt.equity_curve)[["timestamp", "equity"]].rename(columns={"equity": "equity_case2"})
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)

    state = pd.DataFrame(bt.state_rows)
    state["timestamp"] = pd.to_datetime(state["timestamp"])
    state = state.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    return curve, state


def build_case3_probe(m47, s76, s84) -> tuple[pd.DataFrame, pd.DataFrame]:
    market = s84.prepare_market_extended(m47)
    liq_hours = int(CASE3_CFG["liq_hours"])
    gate_bars = int(CASE3_CFG["gate_bars"])
    body_atr_mult = float(CASE3_CFG["body_atr_mult"])
    tp_threshold = float(CASE3_CFG["tp_return_pct"]) / 100.0

    timestamps = market["timestamp"].to_numpy()
    open_np = market["open"].to_numpy(dtype=float)
    high_np = market["high"].to_numpy(dtype=float)
    low_np = market["low"].to_numpy(dtype=float)
    close_np = market["close"].to_numpy(dtype=float)
    atr20 = market["atr20"].to_numpy(dtype=float)
    ema20 = market["ema20"].to_numpy(dtype=float)
    trend = market["trend_4h_confirmed"].astype(str).to_numpy()
    body = market["body"].to_numpy(dtype=float)
    liq_high = market[f"liq_high_{liq_hours}h_prev"].to_numpy(dtype=float)

    wallet = s76.INITIAL_CAPITAL
    reserve = s76.INITIAL_CAPITAL
    margin = 0.0
    qty = 0.0
    entry = 0.0
    side = 0
    entry_wallet = np.nan
    locked_side = 0
    short_gate_until = -10**9
    prev_trend = None

    rows: list[dict] = []
    states: list[dict] = []

    for i in range(len(market)):
        price_open = float(open_np[i])
        price_high = float(high_np[i])
        price_low = float(low_np[i])
        price_close = float(close_np[i])
        cur_trend = str(trend[i])
        blocked_reentry = False

        if prev_trend is not None and cur_trend != prev_trend and cur_trend == "bullish":
            short_gate_until = -10**9
        prev_trend = cur_trend

        short_sweep_event = bool(
            cur_trend == "bearish"
            and pd.notna(liq_high[i])
            and pd.notna(atr20[i])
            and body[i] >= atr20[i] * body_atr_mult
            and price_high > liq_high[i]
            and price_close < liq_high[i]
            and price_close < price_open
        )
        if short_sweep_event:
            short_gate_until = max(short_gate_until, i + gate_bars)

        if side != 0:
            liq_price = s76._liq_price(entry, CASE3_LEVERAGE, side)
            stop_price = entry * (1.0 - s76.STOP_PCT) if side > 0 else entry * (1.0 + s76.STOP_PCT)

            if side > 0 and CASE3_LEVERAGE > 1.0 and price_low <= liq_price:
                wallet = max(reserve, 0.0)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                entry_wallet = np.nan
                blocked_reentry = True
            elif side < 0 and CASE3_LEVERAGE > 1.0 and price_high >= liq_price:
                wallet = max(reserve, 0.0)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                entry_wallet = np.nan
                blocked_reentry = True
            elif side > 0 and price_low <= stop_price:
                wallet = s76._realize_close(reserve, margin, qty, entry, stop_price, side)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                entry_wallet = np.nan
                blocked_reentry = True
            elif side < 0 and price_high >= stop_price:
                wallet = s76._realize_close(reserve, margin, qty, entry, stop_price, side)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                entry_wallet = np.nan
                blocked_reentry = True
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

        desired_side = 1 if cur_trend == "bullish" else -1
        if locked_side != 0:
            if desired_side == locked_side:
                desired_side = 0
            elif desired_side == -locked_side:
                locked_side = 0

        if not blocked_reentry and side != desired_side:
            if side != 0:
                wallet = s76._realize_close(reserve, margin, qty, entry, price_close, side)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                entry_wallet = np.nan

            if desired_side != 0 and wallet > 0:
                allow_entry = True
                if desired_side < 0:
                    allow_entry = i <= short_gate_until and price_close < ema20[i]
                if allow_entry:
                    reserve, margin, qty, entry = s76._open_position(wallet, price_close, CASE3_LEVERAGE, desired_side)
                    wallet = reserve + margin
                    side = desired_side
                    entry_wallet = wallet

        equity = wallet if side == 0 else s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
        rows.append({"timestamp": timestamps[i], "equity_case3": equity})
        states.append(
            {
                "timestamp": timestamps[i],
                "case3_flat": side == 0,
                "case3_side": "LONG" if side > 0 else ("SHORT" if side < 0 else ""),
            }
        )

    if side != 0 and rows:
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close_np[-1]), side)
        rows[-1]["equity_case3"] = wallet
        states[-1]["case3_flat"] = True
        states[-1]["case3_side"] = ""

    curve = pd.DataFrame(rows)
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)

    state = pd.DataFrame(states)
    state["timestamp"] = pd.to_datetime(state["timestamp"])
    state = state.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    return curve, state


def build_latest_merged() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    m47 = load_module("m47_105", BASE_47_PATH)
    s62 = load_module("s62_105", BASE_62_PATH)
    base002 = load_module("m002_105", BASE_002_PATH)
    helper04 = load_module("m04_105", BASE_04_PATH)
    m32 = load_module("m32_105", BASE_32_PATH)
    s42 = load_module("s42_105", BASE_42_PATH)
    s76 = load_module("s76_105", BASE_76_PATH)
    s84 = load_module("s84_105", BASE_84_PATH)

    m47.BACKTEST_END = LATEST_END_DATE
    base002.BACKTEST_END = LATEST_END_DATE

    df_1m, df_4h = m47.load_data_no_filter()
    latest_ts = df_1m.index.max()
    df_1m = df_1m[(df_1m.index >= m47.BACKTEST_START) & (df_1m.index <= latest_ts)].copy()

    case1_curve, case1_state = build_case1_probe(m47, s62, df_1m, df_4h)
    case2_curve, case2_state = build_case2_probe(m47, base002, helper04, m32, s42, df_1m, df_4h)
    case3_curve, case3_state = build_case3_probe(m47, s76, s84)

    common_start = max(
        case1_curve["timestamp"].min(),
        case2_curve["timestamp"].min(),
        case3_curve["timestamp"].min(),
    )
    common_end = min(
        case1_curve["timestamp"].max(),
        case2_curve["timestamp"].max(),
        case3_curve["timestamp"].max(),
    )

    curve_parts = []
    for curve in [case1_curve, case2_curve, case3_curve]:
        curve_parts.append(curve[(curve["timestamp"] >= common_start) & (curve["timestamp"] <= common_end)].copy())
    case1_curve, case2_curve, case3_curve = curve_parts

    state_parts = []
    for state in [case1_state, case2_state, case3_state]:
        state_parts.append(state[(state["timestamp"] >= common_start) & (state["timestamp"] <= common_end)].copy())
    case1_state, case2_state, case3_state = state_parts

    merged = pd.merge(case1_curve, case2_curve, on="timestamp", how="outer")
    merged = pd.merge(merged, case3_curve, on="timestamp", how="outer")
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    for col in ["equity_case1", "equity_case2", "equity_case3"]:
        merged[col] = merged[col].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2", "equity_case3"]).copy()

    merged = merge_state_to_curve(merged, case1_state, ["case1_flat", "case1_side", "case1_has_hedge", "case1_entry_count"])
    merged = merge_state_to_curve(merged, case2_state, ["case2_flat", "case2_side", "case2_entry_count"])
    merged = merge_state_to_curve(merged, case3_state, ["case3_flat", "case3_side"])

    market = load_flow_market_state()
    market = market[(market["timestamp"] >= merged["timestamp"].min()) & (market["timestamp"] <= merged["timestamp"].max())].copy()
    merged["timestamp"] = merged["timestamp"].to_numpy(dtype="datetime64[ns]")
    market["timestamp"] = market["timestamp"].to_numpy(dtype="datetime64[ns]")
    merged = pd.merge_asof(merged.sort_values("timestamp"), market.sort_values("timestamp"), on="timestamp", direction="backward")
    merged = merged.dropna(subset=["trend_4h_confirmed"]).reset_index(drop=True)

    state_out = merged[
        [
            "timestamp",
            "case1_flat",
            "case2_flat",
            "case3_flat",
            "case1_side",
            "case2_side",
            "case3_side",
            "case1_has_hedge",
            "case1_entry_count",
            "case2_entry_count",
            "sell_climax_active_6",
            "squeeze_risk_active_3",
        ]
    ].copy()

    flat_summary = pd.DataFrame(
        [
            {"metric": "case1_flat_ratio_pct", "value": float(merged["case1_flat"].mean() * 100.0)},
            {"metric": "case2_flat_ratio_pct", "value": float(merged["case2_flat"].mean() * 100.0)},
            {"metric": "case3_flat_ratio_pct", "value": float(merged["case3_flat"].mean() * 100.0)},
            {
                "metric": "all_three_flat_ratio_pct",
                "value": float((merged["case1_flat"] & merged["case2_flat"] & merged["case3_flat"]).mean() * 100.0),
            },
        ]
    )
    return merged, state_out, flat_summary


def allocate_openfloor(current_caps: np.ndarray, target_caps: np.ndarray, flat_mask: np.ndarray) -> np.ndarray:
    lower_bounds = np.where(flat_mask, 0.0, current_caps)
    remainder = float(current_caps.sum() - lower_bounds.sum())
    add = project_to_simplex(target_caps - lower_bounds, remainder)
    return lower_bounds + add


def allocate_flatfreeze(current_caps: np.ndarray, target_caps: np.ndarray, flat_mask: np.ndarray) -> np.ndarray:
    new_caps = current_caps.copy()
    flat_idx = np.flatnonzero(flat_mask)
    if len(flat_idx) == 0:
        return new_caps
    fixed_open = float(current_caps[~flat_mask].sum())
    remainder = float(current_caps.sum() - fixed_open)
    new_caps[flat_idx] = project_to_simplex(target_caps[flat_idx], remainder)
    return new_caps


def run_allocator(merged: pd.DataFrame, variant: str, mode: str, s86) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret3 = merged["equity_case3"].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"].reset_index(drop=True)
    topup_flags = compute_month_flags(ts)
    rebal_flags = (ts.dt.floor("4h") != ts.dt.floor("4h").shift(1)).to_numpy()

    cap1 = np.zeros(len(merged), dtype=float)
    cap2 = np.zeros(len(merged), dtype=float)
    cap3 = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    contrib = np.zeros(len(merged), dtype=float)
    flow = np.zeros(len(merged), dtype=float)
    nav_index = np.zeros(len(merged), dtype=float)
    w1_series = np.zeros(len(merged), dtype=float)
    w2_series = np.zeros(len(merged), dtype=float)
    w3_series = np.zeros(len(merged), dtype=float)

    fee_paid = 0.0
    rebalance_count = 0
    turnover_notional = 0.0
    state_switches = 0
    blocked_open_overweight_checks = 0
    no_flat_available_checks = 0
    partial_flat_rebalance_count = 0
    all_flat_rebalance_count = 0

    cur_target = BASE_WEIGHTS
    cap1[0] = INITIAL_CAPITAL_TOTAL * cur_target[0]
    cap2[0] = INITIAL_CAPITAL_TOTAL * cur_target[1]
    cap3[0] = INITIAL_CAPITAL_TOTAL * cur_target[2]
    total[0] = INITIAL_CAPITAL_TOTAL
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0
    w1_series[0], w2_series[0], w3_series[0] = cur_target

    topup_rows: list[dict] = []

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        c3 = cap3[i - 1] * (1.0 + float(ret3[i]))
        cur_total = c1 + c2 + c3
        cur_flow = 0.0

        target_w1, target_w2, target_w3 = get_target_weights(merged.iloc[i])
        target_weights = (target_w1, target_w2, target_w3)
        if target_weights != cur_target:
            state_switches += 1

        if topup_flags[i]:
            cur_flow = MONTHLY_TOPUP
            target1_after = target_w1 * (cur_total + cur_flow)
            target2_after = target_w2 * (cur_total + cur_flow)
            add1 = min(max(target1_after - c1, 0.0), cur_flow)
            remaining = cur_flow - add1
            add2 = min(max(target2_after - c2, 0.0), remaining)
            add3 = cur_flow - add1 - add2
            c1 += add1
            c2 += add2
            c3 += add3
            cur_total += cur_flow
            topup_rows.append(
                {
                    "variant": variant,
                    "timestamp": ts.iloc[i],
                    "topup_amount": cur_flow,
                    "topup_case1": add1,
                    "topup_case2": add2,
                    "topup_case3": add3,
                    "equity_after_topup": cur_total,
                }
            )

        current_caps = np.array([c1, c2, c3], dtype=float)
        target_caps = np.array([cur_total * target_w1, cur_total * target_w2, cur_total * target_w3], dtype=float)
        if cur_total > 0:
            actual_weights = current_caps / cur_total
            max_drift = float(np.max(np.abs(actual_weights - np.array(target_weights, dtype=float))))
        else:
            max_drift = 0.0

        if mode == "fullreb":
            if rebal_flags[i] and max_drift >= THRESHOLD - 1e-12:
                moved = float(np.abs(target_caps - current_caps).sum())
                fee = moved * REBALANCE_FEE_RATE
                cur_total -= fee
                current_caps = np.array([cur_total * target_w1, cur_total * target_w2, cur_total * target_w3], dtype=float)
                fee_paid += fee
                turnover_notional += moved
                rebalance_count += 1
        elif mode == "openfloor":
            if rebal_flags[i] and max_drift >= THRESHOLD - 1e-12:
                flat_mask = np.array(
                    [
                        bool(merged.iloc[i]["case1_flat"]),
                        bool(merged.iloc[i]["case2_flat"]),
                        bool(merged.iloc[i]["case3_flat"]),
                    ],
                    dtype=bool,
                )
                if np.any((~flat_mask) & (current_caps > target_caps + 1e-12)):
                    blocked_open_overweight_checks += 1
                new_caps = allocate_openfloor(current_caps, target_caps, flat_mask)
                moved = float(np.abs(new_caps - current_caps).sum())
                if moved > 1e-12:
                    fee = moved * REBALANCE_FEE_RATE
                    cur_total_after = max(cur_total - fee, 0.0)
                    scaled_target = np.array([cur_total_after * target_w1, cur_total_after * target_w2, cur_total_after * target_w3], dtype=float)
                    new_caps = allocate_openfloor(current_caps, scaled_target, flat_mask)
                    moved = float(np.abs(new_caps - current_caps).sum())
                    fee = moved * REBALANCE_FEE_RATE
                    current_caps = new_caps
                    cur_total = float(current_caps.sum())
                    fee_paid += fee
                    turnover_notional += moved
                    rebalance_count += 1
        elif mode == "flatfreeze":
            if rebal_flags[i] and max_drift >= THRESHOLD - 1e-12:
                flat_mask = np.array(
                    [
                        bool(merged.iloc[i]["case1_flat"]),
                        bool(merged.iloc[i]["case2_flat"]),
                        bool(merged.iloc[i]["case3_flat"]),
                    ],
                    dtype=bool,
                )
                flat_count = int(flat_mask.sum())
                if np.any((~flat_mask) & (current_caps > target_caps + 1e-12)):
                    blocked_open_overweight_checks += 1
                if flat_count == 0:
                    no_flat_available_checks += 1
                else:
                    new_caps = allocate_flatfreeze(current_caps, target_caps, flat_mask)
                    moved = float(np.abs(new_caps - current_caps).sum())
                    if moved > 1e-12:
                        fee = moved * REBALANCE_FEE_RATE
                        current_caps = new_caps
                        current_caps[flat_mask] = project_to_simplex(
                            current_caps[flat_mask],
                            max(float(current_caps.sum() - fee - current_caps[~flat_mask].sum()), 0.0),
                        )
                        moved = float(np.abs(new_caps - np.array([c1, c2, c3], dtype=float)).sum())
                        fee = moved * REBALANCE_FEE_RATE
                        cur_total = float(current_caps.sum())
                        fee_paid += fee
                        turnover_notional += moved
                        rebalance_count += 1
                        if flat_count == 3:
                            all_flat_rebalance_count += 1
                        else:
                            partial_flat_rebalance_count += 1
        elif mode != "cashonly":
            raise ValueError(f"Unknown mode: {mode}")

        cur_target = target_weights
        c1, c2, c3 = [float(v) for v in current_caps]
        cur_total = c1 + c2 + c3
        prev_total = total[i - 1]
        period_return = (cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0
        nav_index[i] = nav_index[i - 1] * (1.0 + period_return)

        cap1[i], cap2[i], cap3[i] = c1, c2, c3
        total[i] = cur_total
        contrib[i] = contrib[i - 1] + cur_flow
        flow[i] = cur_flow
        w1_series[i], w2_series[i], w3_series[i] = cur_target

    out = merged[["timestamp"]].copy()
    out["variant"] = variant
    out["equity_total"] = total
    out["cap1"] = cap1
    out["cap2"] = cap2
    out["cap3"] = cap3
    out["cash_flow"] = flow
    out["cumulative_contribution"] = contrib
    out["nav_index"] = nav_index
    out["w1"] = w1_series
    out["w2"] = w2_series
    out["w3"] = w3_series

    topups_df = pd.DataFrame(topup_rows)
    if topups_df.empty:
        topups_df = pd.DataFrame(columns=["timestamp", "topup_amount"])
    else:
        topups_df = topups_df[["timestamp", "topup_amount"]]
    stats = s86.compute_flow_metrics(out, topups_df)
    stats["variant"] = variant
    stats["mode"] = mode
    stats["rebalance_count"] = rebalance_count
    stats["fee_paid"] = fee_paid
    stats["turnover_notional"] = turnover_notional
    stats["state_switches"] = state_switches
    stats["threshold_pct"] = THRESHOLD * 100.0
    stats["blocked_open_overweight_checks"] = blocked_open_overweight_checks
    stats["no_flat_available_checks"] = no_flat_available_checks
    stats["partial_flat_rebalance_count"] = partial_flat_rebalance_count
    stats["all_flat_rebalance_count"] = all_flat_rebalance_count
    stats["avg_case3_weight_pct"] = float(pd.Series(w3_series[1:]).mean() * 100.0)
    return out, topups_df, stats


def save_plot(metrics_df: pd.DataFrame, curves_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_perf, ax_cost = axes
    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curves_df[curves_df["variant"] == variant]
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.set_title("105 Study: Allocator Realism Compare")
    ax_eq.set_ylabel("Total Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_perf.bar(metrics_df["variant"], metrics_df["twr_cagr_pct"], color=[colors[v] for v in variants], alpha=0.85, label="TWR CAGR %")
    ax_perf.set_ylabel("TWR CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf.tick_params(axis="x", rotation=20)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(metrics_df["variant"], metrics_df["twr_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="TWR MDD %")
    ax_perf_t.set_ylabel("TWR MDD %")
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_cost.bar(metrics_df["variant"], metrics_df["rebalance_count"], color=[colors[v] for v in variants], alpha=0.85, label="Rebalances")
    ax_cost.set_ylabel("Rebalances")
    ax_cost.grid(True, axis="y", alpha=0.2)
    ax_cost.tick_params(axis="x", rotation=20)
    ax_cost_t = ax_cost.twinx()
    ax_cost_t.plot(metrics_df["variant"], metrics_df["fee_paid"], color="#9467bd", marker="o", linewidth=1.1, label="Fee Paid")
    ax_cost_t.set_ylabel("Fee Paid")
    h1, l1 = ax_cost.get_legend_handles_labels()
    h2, l2 = ax_cost_t.get_legend_handles_labels()
    ax_cost.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, flat_summary: pd.DataFrame, common_start: pd.Timestamp, common_end: pd.Timestamp) -> None:
    baseline = metrics_df[metrics_df["variant"] == "fullreb_flow_thr2"].iloc[0]
    best_practical = metrics_df[metrics_df["variant"] != "fullreb_flow_thr2"].sort_values(
        ["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]
    ).iloc[0]
    flat_map = {row["metric"]: float(row["value"]) for _, row in flat_summary.iterrows()}

    lines: list[str] = []
    lines.append("# 105번 연구: Allocator Realism Compare")
    lines.append("")
    lines.append("## 목적")
    lines.append("- `98 flow_combo6_thr2`의 비중 조절이 실제로는 열린 포지션을 건드려야 성립하는지 확인한다.")
    lines.append("- 같은 sleeve(`case1/case2/case3`) 위에 `upper bound / cash-only / open-floor / flat-freeze` allocator를 올려 비교한다.")
    lines.append(f"- 공통 구간: `{common_start}` -> `{common_end}`")
    lines.append("")
    lines.append("## 시나리오 정의")
    for cfg in SCENARIOS:
        lines.append(f"- `{cfg['variant']}`: {cfg['description']}")
    lines.append("")
    lines.append("## flat 비율")
    lines.append(f"- case1 flat ratio: `{_fmt(flat_map['case1_flat_ratio_pct'])}%`")
    lines.append(f"- case2 flat ratio: `{_fmt(flat_map['case2_flat_ratio_pct'])}%`")
    lines.append(f"- case3 flat ratio: `{_fmt(flat_map['case3_flat_ratio_pct'])}%`")
    lines.append(f"- all three flat ratio: `{_fmt(flat_map['all_three_flat_ratio_pct'])}%`")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Variant | Mode | Final Equity | Net Profit | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid | Blocked Open Overweight | No Flat Checks | Partial Flat Rebal | All Flat Rebal |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {row['mode']} | {_fmt(row['final_equity'])} | {_fmt(row['net_profit'])} | "
            f"{_fmt(row['twr_cagr_pct'])} | {_fmt(row['twr_mdd_pct'])} | {_fmt(row['twr_calmar_ratio'])} | {_fmt(row['xirr_pct'])} | "
            f"{int(row['rebalance_count'])} | {_fmt(row['fee_paid'])} | {int(row['blocked_open_overweight_checks'])} | "
            f"{int(row['no_flat_available_checks'])} | {int(row['partial_flat_rebalance_count'])} | {int(row['all_flat_rebalance_count'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append(
        f"- `fullreb_flow_thr2` 대비 가장 실전적인 대안 중 best는 `{best_practical['variant']}`였다. "
        f"CAGR 변화 `{_fmt(best_practical['twr_cagr_pct'] - baseline['twr_cagr_pct'])}pp`, "
        f"MDD 변화 `{_fmt(best_practical['twr_mdd_pct'] - baseline['twr_mdd_pct'])}pp`, "
        f"XIRR 변화 `{_fmt(best_practical['xirr_pct'] - baseline['xirr_pct'])}pp`."
    )
    lines.append("- `blocked_open_overweight_checks`는 이상적인 리밸런싱이라면 줄였어야 할 open sleeve를 실제 제약 때문에 못 줄인 횟수다.")
    lines.append("- `flat-freeze`가 크게 악화되면, 기존 리밸런싱 edge 상당 부분이 열린 포지션 리사이즈 가정에 의존했다는 뜻이다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 결과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- 상태 CSV: `{OUT_STATE_CSV}`")
    lines.append(f"- flat 요약 CSV: `{OUT_FLAT_SUMMARY_CSV}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    s86 = load_module("s86_105", BASE_86_PATH)
    merged, state_out, flat_summary = build_latest_merged()
    common_start = pd.Timestamp(merged["timestamp"].min())
    common_end = pd.Timestamp(merged["timestamp"].max())

    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    for cfg in SCENARIOS:
        curve, _, stats = run_allocator(merged, str(cfg["variant"]), str(cfg["mode"]), s86)
        rows.append(stats)
        curve_rows.append(curve)

    metrics_df = pd.DataFrame(rows).sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curve_rows, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    state_out.to_csv(OUT_STATE_CSV, index=False)
    flat_summary.to_csv(OUT_FLAT_SUMMARY_CSV, index=False)
    save_plot(metrics_df, curves_df)
    save_report(metrics_df, flat_summary, common_start, common_end)

    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_state={OUT_STATE_CSV}")
    print(f"saved_flat={OUT_FLAT_SUMMARY_CSV}")
    print(f"saved_report={OUT_MD}")
    print(f"saved_plot={OUT_PNG}")


if __name__ == "__main__":
    run()
