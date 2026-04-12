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
BASE_86_PATH = Path("86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.py")
DATA_DIR = Path("historical_data_mainnet")

OUT_BASE = "100_backtest_crossasset_case123_flow_combo6_thr2"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_COMPONENTS_CSV = Path(f"{OUT_BASE}_components.csv")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "XRPUSDT"]
LATEST_END_DATE = "2026-03-15"
INITIAL_CAPITAL_CASE = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
ENTRY_SCALE = 0.60
MONTHLY_TOPUP = 1000.0
REBALANCE_FEE_RATE = 0.0004
THRESHOLD = 0.02

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


def compute_curve_stats(curve: pd.DataFrame, col: str, initial_capital: float) -> dict:
    series = curve[col].astype(float)
    final_equity = float(series.iloc[-1])
    elapsed_days = (curve["timestamp"].iloc[-1] - curve["timestamp"].iloc[0]).total_seconds() / 86400.0
    years = max(elapsed_days / 365.25, 1e-9)
    cagr_pct = ((final_equity / float(initial_capital)) ** (1.0 / years) - 1.0) * 100.0
    dd = series / series.cummax() - 1.0
    mdd_pct = float(-dd.min() * 100.0)
    calmar_ratio = cagr_pct / mdd_pct if mdd_pct > 0 else np.nan
    return {
        "final_equity": final_equity,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": mdd_pct,
        "calmar_ratio": calmar_ratio,
    }


def load_1m(symbol: str) -> pd.DataFrame:
    periods = [("2022-01-01", "2024-12-31"), ("2025-01-01", LATEST_END_DATE)]
    frames: list[pd.DataFrame] = []
    for start_date, end_date in periods:
        path = DATA_DIR / f"{symbol}_1m_{start_date}_{end_date}.pkl"
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_pickle(path)
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        frames.append(df)
    out = pd.concat(frames)
    out = out[~out.index.duplicated(keep="first")].sort_index()
    return out


def resample_ohlc(df_1m: pd.DataFrame, rule: str) -> pd.DataFrame:
    out = df_1m.resample(rule).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "taker_base_vol": "sum",
        }
    ).dropna()
    return out


def prepare_case3_market(symbol: str, m47) -> pd.DataFrame:
    df_1m = load_1m(symbol).copy()
    for col in ["open", "high", "low", "close", "volume", "taker_base_vol"]:
        df_1m[col] = pd.to_numeric(df_1m[col], errors="coerce")

    df_15m = resample_ohlc(df_1m, "15min")
    df_1h = resample_ohlc(df_1m, "1h")
    df_4h = resample_ohlc(df_1m, "4h")

    df_4h["ema200_closed"] = df_4h["close"].ewm(span=m47.EMA_PERIOD, adjust=False).mean()
    df_4h["ema200_prev_closed"] = df_4h["ema200_closed"].shift(1)
    df_4h["trend_4h_hyst"] = m47.LiveParityNoLookahead._compute_hysteresis_state(
        df_4h["close"], df_4h["ema200_prev_closed"], m47.HYSTERESIS_BAND
    )
    df_4h["trend_4h_confirmed"] = df_4h["trend_4h_hyst"].shift(1)
    df_4h = df_4h.reset_index().rename(columns={"index": "timestamp"})

    for hours in [12, 24, 36]:
        df_1h[f"liq_high_{hours}h_prev"] = df_1h["high"].rolling(hours).max().shift(1)
        df_1h[f"liq_low_{hours}h_prev"] = df_1h["low"].rolling(hours).min().shift(1)
    df_1h = df_1h.reset_index().rename(columns={"index": "timestamp"})

    out = df_15m.reset_index().rename(columns={"index": "timestamp"})
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

    hour_cols = ["timestamp"] + [f"liq_high_{h}h_prev" for h in [12, 24, 36]] + [f"liq_low_{h}h_prev" for h in [12, 24, 36]]
    out = pd.merge_asof(out.sort_values("timestamp"), df_1h.sort_values("timestamp")[hour_cols], on="timestamp", direction="backward")
    out = pd.merge_asof(
        out.sort_values("timestamp"),
        df_4h.sort_values("timestamp")[["timestamp", "trend_4h_confirmed"]],
        on="timestamp",
        direction="backward",
    )
    out = out.dropna(subset=["atr20", "ema20", "trend_4h_confirmed"]).reset_index(drop=True)
    return out


def run_case3_variant(df: pd.DataFrame, s76) -> pd.DataFrame:
    liq_hours = int(CASE3_CFG["liq_hours"])
    gate_bars = int(CASE3_CFG["gate_bars"])
    body_atr_mult = float(CASE3_CFG["body_atr_mult"])
    tp_threshold = float(CASE3_CFG["tp_return_pct"]) / 100.0

    timestamps = df["timestamp"].to_numpy()
    open_np = df["open"].to_numpy(dtype=float)
    high_np = df["high"].to_numpy(dtype=float)
    low_np = df["low"].to_numpy(dtype=float)
    close_np = df["close"].to_numpy(dtype=float)
    atr20 = df["atr20"].to_numpy(dtype=float)
    ema20 = df["ema20"].to_numpy(dtype=float)
    trend = df["trend_4h_confirmed"].astype(str).to_numpy()
    body = df["body"].to_numpy(dtype=float)
    liq_high = df[f"liq_high_{liq_hours}h_prev"].to_numpy(dtype=float)

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

    for i in range(len(df)):
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

    if side != 0 and len(df):
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close_np[-1]), side)
        rows[-1]["equity_case3"] = wallet

    curve = pd.DataFrame(rows)
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    return curve


def build_flow_state(symbol: str, m47) -> pd.DataFrame:
    periods_4h = [("2021-07-01", "2021-12-31"), ("2022-01-01", "2024-12-31"), ("2025-01-01", LATEST_END_DATE)]
    df = m47._load_cached_df(symbol, "4h", periods_4h).sort_index().copy()
    for col in ["open", "high", "low", "close", "volume", "taker_base_vol"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["ema200_closed"] = df["close"].ewm(span=m47.EMA_PERIOD, adjust=False).mean()
    df["ema200_prev_closed"] = df["ema200_closed"].shift(1)
    df["trend_4h_hyst"] = m47.LiveParityNoLookahead._compute_hysteresis_state(df["close"], df["ema200_prev_closed"], m47.HYSTERESIS_BAND)
    df["trend_4h_confirmed"] = df["trend_4h_hyst"].shift(1)

    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["atr20_pct"] = tr.rolling(20).mean() / df["close"]
    df["ret4h_pct"] = df["close"].pct_change()
    df["buy_ratio"] = (df["taker_base_vol"] / df["volume"].replace(0, np.nan)).clip(0.0, 1.0)
    df["taker_imbalance"] = (df["buy_ratio"] * 2.0) - 1.0
    df["log_volume"] = np.log(df["volume"].clip(lower=1.0))
    df["volume_z"] = (df["log_volume"] - df["log_volume"].rolling(30).mean()) / df["log_volume"].rolling(30).std()

    sell_climax = (
        (df["trend_4h_confirmed"] == "bearish")
        & (df["ret4h_pct"] <= -(df["atr20_pct"] * 0.75))
        & (df["volume_z"] >= 1.0)
        & (df["taker_imbalance"] <= -0.08)
    )
    squeeze_risk = (
        (df["trend_4h_confirmed"] == "bearish")
        & (df["ret4h_pct"] >= (df["atr20_pct"] * 0.50))
        & (df["volume_z"] >= 0.75)
        & (df["taker_imbalance"] >= 0.08)
    )
    df["sell_climax_event"] = sell_climax.fillna(False)
    df["squeeze_risk_event"] = squeeze_risk.fillna(False)
    df["sell_climax_active_6"] = df["sell_climax_event"].rolling(6, min_periods=1).max().fillna(0).astype(bool)
    df["squeeze_risk_active_3"] = df["squeeze_risk_event"].rolling(3, min_periods=1).max().fillna(0).astype(bool)
    out = df.reset_index().rename(columns={"index": "timestamp"})
    cols = ["timestamp", "trend_4h_confirmed", "sell_climax_event", "squeeze_risk_event", "sell_climax_active_6", "squeeze_risk_active_3"]
    return out[cols].dropna(subset=["trend_4h_confirmed"]).copy()


def merge_state_to_cases(case_curves: pd.DataFrame, market_state: pd.DataFrame) -> pd.DataFrame:
    left = case_curves.copy().reset_index(drop=True)
    right = market_state.copy().reset_index(drop=True)
    left["timestamp"] = left["timestamp"].to_numpy(dtype="datetime64[ns]")
    right["timestamp"] = right["timestamp"].to_numpy(dtype="datetime64[ns]")
    return pd.merge_asof(left.sort_values("timestamp"), right.sort_values("timestamp"), on="timestamp", direction="backward").dropna(
        subset=["trend_4h_confirmed"]
    ).reset_index(drop=True)


def get_target_weights(row: pd.Series) -> tuple[float, float, float]:
    if bool(row["squeeze_risk_active_3"]):
        return SQUEEZE_WEIGHTS
    if bool(row["sell_climax_active_6"]):
        return SELL_WEIGHTS
    return BASE_WEIGHTS


def run_flow_combo6_thr2(merged: pd.DataFrame, symbol: str, s86) -> tuple[pd.DataFrame, dict]:
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
    state_switches = 0
    turnover_notional = 0.0
    cur_target = BASE_WEIGHTS

    cap1[0] = INITIAL_CAPITAL_TOTAL * cur_target[0]
    cap2[0] = INITIAL_CAPITAL_TOTAL * cur_target[1]
    cap3[0] = INITIAL_CAPITAL_TOTAL * cur_target[2]
    total[0] = INITIAL_CAPITAL_TOTAL
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0
    w1_series[0], w2_series[0], w3_series[0] = cur_target

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        c3 = cap3[i - 1] * (1.0 + float(ret3[i]))
        cur_total = c1 + c2 + c3
        cur_flow = 0.0

        target_weights = get_target_weights(merged.iloc[i])
        target_w1, target_w2, target_w3 = target_weights
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

        if cur_total > 0:
            aw1, aw2, aw3 = c1 / cur_total, c2 / cur_total, c3 / cur_total
            max_drift = max(abs(aw1 - target_w1), abs(aw2 - target_w2), abs(aw3 - target_w3))
        else:
            max_drift = 0.0

        if rebal_flags[i] and max_drift >= THRESHOLD - 1e-12:
            target1 = cur_total * target_w1
            target2 = cur_total * target_w2
            target3 = cur_total * target_w3
            moved = abs(target1 - c1) + abs(target2 - c2) + abs(target3 - c3)
            fee = moved * REBALANCE_FEE_RATE
            cur_total -= fee
            c1 = cur_total * target_w1
            c2 = cur_total * target_w2
            c3 = cur_total * target_w3
            fee_paid += fee
            turnover_notional += moved
            rebalance_count += 1

        prev_total = total[i - 1]
        period_return = (cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0
        nav_index[i] = nav_index[i - 1] * (1.0 + period_return)

        cur_target = target_weights
        cap1[i], cap2[i], cap3[i] = c1, c2, c3
        total[i] = cur_total
        flow[i] = cur_flow
        contrib[i] = contrib[i - 1] + cur_flow
        w1_series[i], w2_series[i], w3_series[i] = cur_target

    out = merged[["timestamp"]].copy()
    out["symbol"] = symbol
    out["equity_total"] = total
    out["cash_flow"] = flow
    out["cumulative_contribution"] = contrib
    out["nav_index"] = nav_index
    out["w1"] = w1_series
    out["w2"] = w2_series
    out["w3"] = w3_series

    topups_df = pd.DataFrame({"timestamp": ts[topup_flags], "topup_amount": MONTHLY_TOPUP})
    stats = s86.compute_flow_metrics(out, topups_df)
    stats["symbol"] = symbol
    stats["rebalance_count"] = rebalance_count
    stats["state_switches"] = state_switches
    stats["fee_paid"] = fee_paid
    stats["turnover_notional"] = turnover_notional
    stats["avg_case3_weight_pct"] = float(pd.Series(w3_series[1:]).mean() * 100.0)
    return out, stats


def build_symbol_case_curves(symbol: str) -> tuple[pd.DataFrame, list[dict]]:
    print(f"[{symbol}] loading modules", flush=True)
    suffix = symbol.lower()
    m47 = load_module(f"m47_100_{suffix}", BASE_47_PATH)
    s62 = load_module(f"s62_100_{suffix}", BASE_62_PATH)
    base = load_module(f"m002_100_{suffix}", BASE_002_PATH)
    helper = load_module(f"m04_100_{suffix}", BASE_04_PATH)
    m32 = load_module(f"m32_100_{suffix}", BASE_32_PATH)
    s42 = load_module(f"s42_100_{suffix}", BASE_42_PATH)
    s76 = load_module(f"s76_100_{suffix}", BASE_76_PATH)

    m47.SYMBOL = symbol
    m47.BACKTEST_END = LATEST_END_DATE
    base.SYMBOL = symbol
    base.BACKTEST_END = LATEST_END_DATE

    print(f"[{symbol}] loading 1m/4h data", flush=True)
    df_1m, df_4h = m47.load_data_no_filter()
    latest_ts = df_1m.index.max()
    df_1m = df_1m[(df_1m.index >= m47.BACKTEST_START) & (df_1m.index <= latest_ts)].copy()

    print(f"[{symbol}] running case1", flush=True)
    case1_cls = s62.build_variant_class(m47.LiveParityNoLookahead, bullish_close_bars=2, shallow_gap_pct=0.06)
    bt1 = case1_cls(symbol=m47.SYMBOL, initial_capital=INITIAL_CAPITAL_CASE, commission=m47.COMMISSION, entry_scale=ENTRY_SCALE)
    m47.configure_baseline_params(bt1)
    bt1.run(df_1m, df_4h, backtest_start_date=m47.BACKTEST_START)
    case1 = pd.DataFrame(bt1.equity_curve)[["timestamp", "equity"]].copy()
    case1["timestamp"] = pd.to_datetime(case1["timestamp"])
    case1 = case1.sort_values("timestamp").drop_duplicates("timestamp", keep="last").rename(columns={"equity": "equity_case1"})

    print(f"[{symbol}] running case2", flush=True)
    bt2_cls = s42.build_case2_class(m32)
    bt2 = bt2_cls(base_module=base, symbol=base.SYMBOL, initial_capital=INITIAL_CAPITAL_CASE, commission=base.COMMISSION, entry_scale=ENTRY_SCALE)
    helper.configure_baseline_params(bt2)
    bt2.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)
    case2 = pd.DataFrame(bt2.equity_curve)[["timestamp", "equity"]].copy()
    case2["timestamp"] = pd.to_datetime(case2["timestamp"])
    case2 = case2.sort_values("timestamp").drop_duplicates("timestamp", keep="last").rename(columns={"equity": "equity_case2"})

    print(f"[{symbol}] running case3", flush=True)
    case3_market = prepare_case3_market(symbol, m47)
    case3 = run_case3_variant(case3_market, s76)

    common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
    common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())
    case1 = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)].copy()
    case2 = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy()
    case3 = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)].copy()

    print(f"[{symbol}] merging sleeves", flush=True)
    merged = pd.merge(case1, case2, on="timestamp", how="outer")
    merged = pd.merge(merged, case3, on="timestamp", how="outer")
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged["equity_case3"] = merged["equity_case3"].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2", "equity_case3"]).copy()

    components = []
    for label, col in [("case1", "equity_case1"), ("case2", "equity_case2"), ("case3", "equity_case3")]:
        stats = compute_curve_stats(merged[["timestamp", col]].rename(columns={col: "equity"}), "equity", INITIAL_CAPITAL_CASE)
        stats["symbol"] = symbol
        stats["sleeve"] = label
        components.append(stats)
    return merged, components


def save_plot(metrics_df: pd.DataFrame, curve_map: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.0]})
    ax_eq, ax_perf, ax_cost = axes
    cmap = plt.get_cmap("tab10")
    symbols = metrics_df["symbol"].tolist()
    colors = {symbol: cmap(i % 10) for i, symbol in enumerate(symbols)}

    for symbol in symbols:
        curve = curve_map[symbol]
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[symbol], label=symbol)
    ax_eq.set_title("100번 연구: BTC/ETH/XRP 실제 case123 + flow_combo6_thr2 비교")
    ax_eq.set_ylabel("Total Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_perf.bar(metrics_df["symbol"], metrics_df["twr_cagr_pct"], color=[colors[s] for s in symbols], alpha=0.85, label="TWR CAGR %")
    ax_perf.set_ylabel("TWR CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(metrics_df["symbol"], metrics_df["twr_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="TWR MDD %")
    ax_perf_t.set_ylabel("TWR MDD %")
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_cost.bar(metrics_df["symbol"], metrics_df["rebalance_count"], color=[colors[s] for s in symbols], alpha=0.85, label="Rebalances")
    ax_cost.set_ylabel("Rebalances")
    ax_cost.grid(True, axis="y", alpha=0.2)
    ax_cost_t = ax_cost.twinx()
    ax_cost_t.plot(metrics_df["symbol"], metrics_df["fee_paid"], color="#9467bd", marker="o", linewidth=1.1, label="Fee Paid")
    ax_cost_t.set_ylabel("Fee Paid")
    h1, l1 = ax_cost.get_legend_handles_labels()
    h2, l2 = ax_cost_t.get_legend_handles_labels()
    ax_cost.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, components_df: pd.DataFrame) -> None:
    best = metrics_df.sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).iloc[0]
    lines: list[str] = []
    lines.append("# 100번 연구: BTC/ETH/XRP 실제 case123 + flow_combo6_thr2 비교")
    lines.append("")
    lines.append("## 설정")
    lines.append("- 상태 센서만 바꾸는 것이 아니라, case1/case2/case3 매매 자체를 BTC/ETH/XRP 각각에 실제로 적용한다.")
    lines.append("- case1: `shallow6_else2bull`")
    lines.append("- case2: study-42 baseline case2")
    lines.append("- case3: `short_gate_24h_g12_tp15`")
    lines.append("- 포트폴리오 운용은 98 best와 동일한 `flow_combo6_thr2`이다.")
    lines.append("")
    lines.append("## 포트폴리오 결과")
    lines.append("")
    lines.append("| Symbol | Final Equity | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid | Avg Case3 Weight % |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['symbol']} | {_fmt(row['final_equity'])} | {_fmt(row['twr_cagr_pct'])} | {_fmt(row['twr_mdd_pct'])} | "
            f"{_fmt(row['twr_calmar_ratio'])} | {_fmt(row['xirr_pct'])} | {int(row['rebalance_count'])} | {_fmt(row['fee_paid'])} | {_fmt(row['avg_case3_weight_pct'])} |"
        )
    lines.append("")
    lines.append("## Sleeve Standalone")
    lines.append("")
    lines.append("| Symbol | Sleeve | Final Equity | CAGR % | MDD % | Calmar |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
    for _, row in components_df.iterrows():
        lines.append(
            f"| {row['symbol']} | {row['sleeve']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append(f"- best symbol: `{best['symbol']}`")
    lines.append("- 이번 비교는 진짜로 심볼별 매매를 다시 돌린 결과라, curve가 거의 같아 보이면 안 된다. 실제로 심볼별 sleeve와 포트폴리오 결과가 모두 따로 계산된다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 성과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- sleeve CSV: `{OUT_COMPONENTS_CSV}`")
    lines.append(f"- 보고서: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run() -> None:
    s86 = load_module("m86_100", BASE_86_PATH)
    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}
    component_rows: list[dict] = []

    for symbol in SYMBOLS:
        print(f"[{symbol}] start portfolio build", flush=True)
        merged_cases, components = build_symbol_case_curves(symbol)
        component_rows.extend(components)
        print(f"[{symbol}] building flow state", flush=True)
        market_state = build_flow_state(symbol, load_module(f"m47_state_{symbol.lower()}", BASE_47_PATH))
        merged = merge_state_to_cases(
            merged_cases.set_index("timestamp").resample("15min").last().dropna().reset_index(),
            market_state,
        )
        print(f"[{symbol}] running flow_combo6_thr2 portfolio", flush=True)
        curve, stats = run_flow_combo6_thr2(merged, symbol, s86)
        rows.append(stats)
        curve_rows.append(curve.assign(symbol=symbol))
        curve_map[symbol] = curve
        print(f"[{symbol}] done", flush=True)

    metrics_df = pd.DataFrame(rows).sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curve_rows, ignore_index=True)
    components_df = pd.DataFrame(component_rows).sort_values(["symbol", "sleeve"]).reset_index(drop=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    components_df.to_csv(OUT_COMPONENTS_CSV, index=False)
    save_plot(metrics_df, curve_map)
    save_report(metrics_df, components_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_components={OUT_COMPONENTS_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    run()
