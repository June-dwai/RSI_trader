from __future__ import annotations

import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
BASE_32_PATH = Path("32_backtest_btcusdt_live_nla.py")
BASE_42_PATH = Path("42_backtest_btcusdt_scale06_adx002_equity_combo.py")
BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
BASE_62_PATH = Path("62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune.py")
BASE_76_PATH = Path("76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py")
BASE_86_PATH = Path("86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.py")
BASE_98_CSV = Path("98_backtest_btcusdt_scale06_adx002_case123_flow_hybrid_compare.csv")
DATA_DIR = Path("historical_data_mainnet")

OUT_BASE = "104_backtest_btcusdt_scale06_adx002_flow_combo6_thr2_with_2021"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_CASE_CURVES_CSV = Path(f"{OUT_BASE}_case_curves.csv")
OUT_MARKET_CSV = Path(f"{OUT_BASE}_market_state_4h.csv")

SYMBOL = "BTCUSDT"
BACKTEST_START = "2021-01-01"
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

VARIANTS = [
    {"variant": "static_thr2_2021", "mode": "static"},
    {"variant": "flow_combo6_thr2_2021", "mode": "flow_combo6"},
]

KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "qav",
    "num_trades",
    "taker_base_vol",
    "taker_quote_vol",
    "ignore",
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


def download_2021_archive(interval: str) -> Path:
    out_path = DATA_DIR / f"{SYMBOL}_{interval}_2021-01-01_2021-12-31.pkl"
    if out_path.exists():
        return out_path

    frames: list[pd.DataFrame] = []
    for month in range(1, 13):
        url = (
            f"https://data.binance.vision/data/futures/um/monthly/klines/"
            f"{SYMBOL}/{interval}/{SYMBOL}-{interval}-2021-{month:02d}.zip"
        )
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            member = zf.namelist()[0]
            df = pd.read_csv(zf.open(member), header=None, names=KLINE_COLUMNS)
        frames.append(df)

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.drop_duplicates(subset=["open_time"]).sort_values("open_time").reset_index(drop=True)
    merged["timestamp"] = pd.to_datetime(merged["open_time"], unit="ms", utc=True).dt.tz_convert(None)
    merged = merged.set_index("timestamp")
    merged = merged.drop(columns=["open_time"])
    for col in ["open", "high", "low", "close", "volume", "qav", "taker_base_vol", "taker_quote_vol"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")
    for col in ["close_time", "num_trades", "ignore"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").astype("int64")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_pickle(out_path)
    return out_path


def ensure_2021_cache() -> tuple[Path, Path]:
    one_m = download_2021_archive("1m")
    four_h = download_2021_archive("4h")
    return one_m, four_h


def load_concat_pickle(periods: list[tuple[str, str]], timeframe: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for start_date, end_date in periods:
        path = DATA_DIR / f"{SYMBOL}_{timeframe}_{start_date}_{end_date}.pkl"
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_pickle(path)
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        frames.append(df)
    merged = pd.concat(frames)
    merged = merged[~merged.index.duplicated(keep="first")].sort_index()
    return merged


def load_2021_to_latest() -> tuple[pd.DataFrame, pd.DataFrame]:
    df_1m = load_concat_pickle(
        [("2021-01-01", "2021-12-31"), ("2022-01-01", "2024-12-31"), ("2025-01-01", LATEST_END_DATE)],
        "1m",
    )
    df_4h = load_concat_pickle(
        [("2021-01-01", "2021-12-31"), ("2022-01-01", "2024-12-31"), ("2025-01-01", LATEST_END_DATE)],
        "4h",
    )
    return df_1m, df_4h


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


def prepare_case3_market(df_1m: pd.DataFrame, m47) -> pd.DataFrame:
    src = df_1m.copy()
    for col in ["open", "high", "low", "close", "volume", "taker_base_vol"]:
        src[col] = pd.to_numeric(src[col], errors="coerce")

    def _resample(rule: str) -> pd.DataFrame:
        return (
            src.resample(rule)
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                    "taker_base_vol": "sum",
                }
            )
            .dropna()
        )

    df_15m = _resample("15min")
    df_1h = _resample("1h")
    df_4h = _resample("4h")

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
    liq_hours = 24
    gate_bars = 12
    body_atr_mult = 0.25
    tp_threshold = 0.15
    leverage = 2.0

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
            elif side < 0 and leverage > 1.0 and price_high >= liq_price:
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
                    reserve, margin, qty, entry = s76._open_position(wallet, price_close, leverage, desired_side)
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
    return curve.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)


def build_case_curves(df_1m: pd.DataFrame, df_4h: pd.DataFrame):
    m47 = load_module("m47_104", BASE_47_PATH)
    s62 = load_module("s62_104", BASE_62_PATH)
    base = load_module("m002_104", BASE_002_PATH)
    helper = load_module("m04_104", BASE_04_PATH)
    m32 = load_module("m32_104", BASE_32_PATH)
    s42 = load_module("s42_104", BASE_42_PATH)
    s76 = load_module("s76_104", BASE_76_PATH)

    m47.SYMBOL = SYMBOL
    m47.BACKTEST_START = BACKTEST_START
    m47.BACKTEST_END = LATEST_END_DATE
    base.SYMBOL = SYMBOL
    base.BACKTEST_START = BACKTEST_START
    base.BACKTEST_END = LATEST_END_DATE

    case1_cls = s62.build_variant_class(m47.LiveParityNoLookahead, bullish_close_bars=2, shallow_gap_pct=0.06)
    bt1 = case1_cls(symbol=SYMBOL, initial_capital=INITIAL_CAPITAL_CASE, commission=m47.COMMISSION, entry_scale=ENTRY_SCALE)
    m47.configure_baseline_params(bt1)
    bt1.run(df_1m, df_4h, backtest_start_date=BACKTEST_START)
    case1 = pd.DataFrame(bt1.equity_curve)[["timestamp", "equity"]].copy().rename(columns={"equity": "equity_case1"})
    case1["timestamp"] = pd.to_datetime(case1["timestamp"])
    case1 = case1.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)

    bt2_cls = s42.build_case2_class(m32)
    bt2 = bt2_cls(base_module=base, symbol=SYMBOL, initial_capital=INITIAL_CAPITAL_CASE, commission=base.COMMISSION, entry_scale=ENTRY_SCALE)
    helper.configure_baseline_params(bt2)
    bt2.run(df_1m, df_4h, backtest_start_date=BACKTEST_START)
    case2 = pd.DataFrame(bt2.equity_curve)[["timestamp", "equity"]].copy().rename(columns={"equity": "equity_case2"})
    case2["timestamp"] = pd.to_datetime(case2["timestamp"])
    case2 = case2.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)

    case3_market = prepare_case3_market(df_1m, m47)
    case3 = run_case3_variant(case3_market, s76)

    common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
    common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())
    case1 = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)]
    case2 = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)]
    case3 = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)]

    merged = pd.merge(case1, case2, on="timestamp", how="outer")
    merged = pd.merge(merged, case3, on="timestamp", how="outer")
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged["equity_case3"] = merged["equity_case3"].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2", "equity_case3"]).copy()
    return merged, common_start, common_end, m47


def build_market_state(df_4h: pd.DataFrame, common_start: pd.Timestamp, common_end: pd.Timestamp, m47) -> pd.DataFrame:
    raw = df_4h[(df_4h.index >= common_start.floor("4h")) & (df_4h.index <= common_end.ceil("4h"))].copy()
    for col in ["open", "high", "low", "close", "volume", "taker_base_vol"]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")

    raw["ema200_closed"] = raw["close"].ewm(span=m47.EMA_PERIOD, adjust=False).mean()
    raw["ema200_prev_closed"] = raw["ema200_closed"].shift(1)
    raw["trend_4h_hyst"] = m47.LiveParityNoLookahead._compute_hysteresis_state(raw["close"], raw["ema200_prev_closed"], m47.HYSTERESIS_BAND)
    raw["trend_4h_confirmed"] = raw["trend_4h_hyst"].shift(1)

    prev_close = raw["close"].shift(1)
    tr = pd.concat(
        [
            raw["high"] - raw["low"],
            (raw["high"] - prev_close).abs(),
            (raw["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    raw["tr_pct"] = tr / raw["close"]
    raw["atr20_pct"] = tr.rolling(20).mean() / raw["close"]
    raw["ret4h_pct"] = raw["close"].pct_change()
    raw["buy_ratio"] = (raw["taker_base_vol"] / raw["volume"].replace(0, np.nan)).clip(0.0, 1.0)
    raw["taker_imbalance"] = (raw["buy_ratio"] * 2.0) - 1.0
    raw["log_volume"] = np.log(raw["volume"].clip(lower=1.0))
    raw["volume_z"] = (raw["log_volume"] - raw["log_volume"].rolling(30).mean()) / raw["log_volume"].rolling(30).std()

    sell_climax = (
        (raw["trend_4h_confirmed"] == "bearish")
        & (raw["ret4h_pct"] <= -(raw["atr20_pct"] * 0.75))
        & (raw["volume_z"] >= 1.0)
        & (raw["taker_imbalance"] <= -0.08)
    )
    squeeze_risk = (
        (raw["trend_4h_confirmed"] == "bearish")
        & (raw["ret4h_pct"] >= (raw["atr20_pct"] * 0.50))
        & (raw["volume_z"] >= 0.75)
        & (raw["taker_imbalance"] >= 0.08)
    )
    raw["sell_climax_event"] = sell_climax.fillna(False)
    raw["squeeze_risk_event"] = squeeze_risk.fillna(False)
    raw["sell_climax_active_6"] = raw["sell_climax_event"].rolling(6, min_periods=1).max().fillna(0).astype(bool)
    raw["squeeze_risk_active_3"] = raw["squeeze_risk_event"].rolling(3, min_periods=1).max().fillna(0).astype(bool)

    out = raw.reset_index().rename(columns={"index": "timestamp"})
    cols = ["timestamp", "trend_4h_confirmed", "sell_climax_active_6", "squeeze_risk_active_3"]
    return out[cols].dropna(subset=["trend_4h_confirmed"]).copy()


def merge_state_to_cases(case_curves: pd.DataFrame, market_state: pd.DataFrame) -> pd.DataFrame:
    left = case_curves.copy().reset_index(drop=True)
    right = market_state.copy().reset_index(drop=True)
    left["timestamp"] = left["timestamp"].to_numpy(dtype="datetime64[ns]")
    right["timestamp"] = right["timestamp"].to_numpy(dtype="datetime64[ns]")
    merged = pd.merge_asof(left.sort_values("timestamp"), right.sort_values("timestamp"), on="timestamp", direction="backward")
    merged = merged.dropna(subset=["trend_4h_confirmed"]).reset_index(drop=True)
    return merged


def get_target_weights(row: pd.Series, mode: str) -> tuple[float, float, float]:
    if mode == "flow_combo6":
        if bool(row["squeeze_risk_active_3"]):
            return SQUEEZE_WEIGHTS
        if bool(row["sell_climax_active_6"]):
            return SELL_WEIGHTS
    return BASE_WEIGHTS


def run_hybrid(merged: pd.DataFrame, variant: str, mode: str, s86) -> tuple[pd.DataFrame, dict]:
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

        target_w1, target_w2, target_w3 = get_target_weights(merged.iloc[i], mode)
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
    out["variant"] = variant
    out["equity_total"] = total
    out["cash_flow"] = flow
    out["cumulative_contribution"] = contrib
    out["nav_index"] = nav_index
    out["w1"] = w1_series
    out["w2"] = w2_series
    out["w3"] = w3_series

    topups_df = pd.DataFrame({"timestamp": ts[topup_flags], "topup_amount": MONTHLY_TOPUP})
    stats = s86.compute_flow_metrics(out, topups_df)
    stats["variant"] = variant
    stats["mode"] = mode
    stats["rebalance_count"] = rebalance_count
    stats["state_switches"] = state_switches
    stats["fee_paid"] = fee_paid
    stats["turnover_notional"] = turnover_notional
    return out, stats


def save_plot(metrics_df: pd.DataFrame, curve_map: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0]})
    ax_eq, ax_perf = axes
    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(metrics_df["variant"])}
    for variant in metrics_df["variant"]:
        curve = curve_map[variant]
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.set_title("104 Study: BTC flow_combo6_thr2 with 2021 data")
    ax_eq.set_ylabel("Total Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_perf.bar(metrics_df["variant"], metrics_df["twr_cagr_pct"], color=[colors[v] for v in metrics_df["variant"]], alpha=0.85, label="TWR CAGR %")
    ax_perf.set_ylabel("TWR CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(metrics_df["variant"], metrics_df["twr_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="TWR MDD %")
    ax_perf_t.set_ylabel("TWR MDD %")
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, ref_old: pd.Series, common_start: pd.Timestamp, common_end: pd.Timestamp) -> None:
    lines: list[str] = []
    lines.append("# 104 Study: BTC flow_combo6_thr2 with 2021 data")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Added real 2021 BTCUSDT futures archive data to the local cache.")
    lines.append("- Rebuilt case1/case2/case3 from 2021-01-01, then reran current BTC best candidate (`flow_combo6_thr2`).")
    lines.append(f"- Common period: `{common_start}` -> `{common_end}`")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Variant | Final Equity | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | State Switches | Fee Paid |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['twr_cagr_pct'])} | {_fmt(row['twr_mdd_pct'])} | "
            f"{_fmt(row['twr_calmar_ratio'])} | {_fmt(row['xirr_pct'])} | {int(row['rebalance_count'])} | {int(row['state_switches'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## Compare To Old 98 Result")
    lines.append("")
    lines.append(f"- Old `flow_combo6_thr2` TWR CAGR: `{_fmt(ref_old['twr_cagr_pct'])}%`")
    lines.append(f"- Old `flow_combo6_thr2` TWR MDD: `{_fmt(ref_old['twr_mdd_pct'])}%`")
    lines.append(f"- Old `flow_combo6_thr2` XIRR: `{_fmt(ref_old['xirr_pct'])}%`")
    new = metrics_df[metrics_df["variant"] == "flow_combo6_thr2_2021"].iloc[0]
    lines.append(
        f"- New vs old: CAGR `{_fmt(new['twr_cagr_pct'] - ref_old['twr_cagr_pct'])}pp`, "
        f"MDD `{_fmt(new['twr_mdd_pct'] - ref_old['twr_mdd_pct'])}pp`, "
        f"XIRR `{_fmt(new['xirr_pct'] - ref_old['xirr_pct'])}pp`."
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run() -> None:
    ensure_2021_cache()
    df_1m, df_4h = load_2021_to_latest()

    case_curves, common_start, common_end, m47 = build_case_curves(df_1m, df_4h)
    case_curves.to_csv(OUT_CASE_CURVES_CSV, index=False)

    market_state = build_market_state(df_4h, common_start, common_end, m47)
    market_state.to_csv(OUT_MARKET_CSV, index=False)
    merged = merge_state_to_cases(case_curves, market_state)

    s86 = load_module("s86_104", BASE_86_PATH)
    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}
    for cfg in VARIANTS:
        curve, stats = run_hybrid(merged, str(cfg["variant"]), str(cfg["mode"]), s86)
        rows.append(stats)
        curve_rows.append(curve)
        curve_map[str(cfg["variant"])] = curve

    metrics_df = pd.DataFrame(rows).sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curve_rows, ignore_index=True)
    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(metrics_df, curve_map)

    ref98 = pd.read_csv(BASE_98_CSV)
    ref_old = ref98[ref98["variant"] == "flow_combo6_thr2"].iloc[0]
    save_report(metrics_df, ref_old, common_start, common_end)

    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_case_curves={OUT_CASE_CURVES_CSV}")
    print(f"saved_market_state={OUT_MARKET_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    run()
