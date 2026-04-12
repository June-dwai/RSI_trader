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

OUT_BASE = "102_backtest_ethusdt_case123_volatility_scaled_tune"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_SLEEVES_CSV = Path(f"{OUT_BASE}_sleeves.csv")

SYMBOL = "ETHUSDT"
LATEST_END_DATE = "2026-03-15"
INITIAL_CAPITAL_CASE = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
MONTHLY_TOPUP = 1000.0
REBALANCE_FEE_RATE = 0.0004
THRESHOLD = 0.02

CASE1_VARIANTS = [
    {
        "variant": "btc_ref_case1",
        "entry_scale": 0.60,
        "rsi_oversold": 18,
        "tp_pct": 0.012,
        "sl_pct": 0.03,
        "dca_drop_pct": 0.0050,
        "shallow_gap_pct": 0.06,
        "bullish_close_bars": 2,
        "base_cooldown": 5,
    },
    {
        "variant": "eth_v2_bal_case1",
        "entry_scale": 0.40,
        "rsi_oversold": 16,
        "tp_pct": 0.020,
        "sl_pct": 0.050,
        "dca_drop_pct": 0.0080,
        "shallow_gap_pct": 0.10,
        "bullish_close_bars": 2,
        "base_cooldown": 6,
    },
    {
        "variant": "eth_v2_loose_case1",
        "entry_scale": 0.35,
        "rsi_oversold": 14,
        "tp_pct": 0.024,
        "sl_pct": 0.060,
        "dca_drop_pct": 0.0100,
        "shallow_gap_pct": 0.12,
        "bullish_close_bars": 2,
        "base_cooldown": 7,
    },
    {
        "variant": "eth_v2_deep_case1",
        "entry_scale": 0.30,
        "rsi_oversold": 12,
        "tp_pct": 0.030,
        "sl_pct": 0.070,
        "dca_drop_pct": 0.0120,
        "shallow_gap_pct": 0.14,
        "bullish_close_bars": 3,
        "base_cooldown": 8,
    },
]

CASE3_VARIANTS = [
    {
        "variant": "btc_ref_case3",
        "leverage": 2.0,
        "stop_pct": 0.06,
        "liq_hours": 24,
        "gate_bars": 12,
        "body_atr_mult": 0.25,
        "tp_return_pct": 15.0,
    },
    {
        "variant": "eth_v2_bal_case3",
        "leverage": 1.5,
        "stop_pct": 0.08,
        "liq_hours": 24,
        "gate_bars": 12,
        "body_atr_mult": 0.25,
        "tp_return_pct": 20.0,
    },
    {
        "variant": "eth_v2_wide_case3",
        "leverage": 1.5,
        "stop_pct": 0.10,
        "liq_hours": 24,
        "gate_bars": 16,
        "body_atr_mult": 0.20,
        "tp_return_pct": 25.0,
    },
    {
        "variant": "eth_v2_slow_case3",
        "leverage": 1.0,
        "stop_pct": 0.10,
        "liq_hours": 36,
        "gate_bars": 16,
        "body_atr_mult": 0.20,
        "tp_return_pct": 20.0,
    },
    {
        "variant": "eth_v2_deep_case3",
        "leverage": 1.0,
        "stop_pct": 0.12,
        "liq_hours": 36,
        "gate_bars": 20,
        "body_atr_mult": 0.15,
        "tp_return_pct": 30.0,
    },
]

PORTFOLIO_WEIGHTS = [
    ("btc_62_31_07", (0.62, 0.31, 0.07)),
    ("eth_30_70_00", (0.30, 0.70, 0.00)),
    ("eth_25_75_00", (0.25, 0.75, 0.00)),
    ("eth_25_70_05", (0.25, 0.70, 0.05)),
    ("eth_20_75_05", (0.20, 0.75, 0.05)),
    ("eth_20_70_10", (0.20, 0.70, 0.10)),
    ("eth_15_80_05", (0.15, 0.80, 0.05)),
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


def compute_month_flags(ts: pd.Series) -> np.ndarray:
    flags = (ts.dt.to_period("M") != ts.dt.to_period("M").shift(1)).to_numpy(copy=True)
    if len(flags):
        flags[0] = False
    return flags


def prepare_case3_market(symbol: str, m47) -> pd.DataFrame:
    periods_1m = [("2022-01-01", "2024-12-31"), ("2025-01-01", LATEST_END_DATE)]
    df_1m = m47._load_cached_df(symbol, "1m", periods_1m).sort_index().copy()
    for col in ["open", "high", "low", "close", "volume", "taker_base_vol"]:
        df_1m[col] = pd.to_numeric(df_1m[col], errors="coerce")

    def _resample(rule: str) -> pd.DataFrame:
        return (
            df_1m.resample(rule)
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

    for hours in [24, 36]:
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

    hour_cols = ["timestamp", "liq_high_24h_prev", "liq_low_24h_prev", "liq_high_36h_prev", "liq_low_36h_prev"]
    out = pd.merge_asof(out.sort_values("timestamp"), df_1h.sort_values("timestamp")[hour_cols], on="timestamp", direction="backward")
    out = pd.merge_asof(
        out.sort_values("timestamp"),
        df_4h.sort_values("timestamp")[["timestamp", "trend_4h_confirmed"]],
        on="timestamp",
        direction="backward",
    )
    out = out.dropna(subset=["atr20", "ema20", "trend_4h_confirmed"]).reset_index(drop=True)
    return out


def run_case1_variant(df_1m: pd.DataFrame, df_4h: pd.DataFrame, m47, s62, cfg: dict) -> tuple[pd.DataFrame, dict]:
    case_cls = s62.build_variant_class(
        m47.LiveParityNoLookahead,
        bullish_close_bars=int(cfg["bullish_close_bars"]),
        shallow_gap_pct=float(cfg["shallow_gap_pct"]),
    )
    case_cls.dca_drop_pct = float(cfg["dca_drop_pct"])
    case_cls.max_entries_cap = 4

    bt = case_cls(
        symbol=SYMBOL,
        initial_capital=INITIAL_CAPITAL_CASE,
        commission=m47.COMMISSION,
        entry_scale=float(cfg["entry_scale"]),
    )
    m47.configure_baseline_params(bt)
    bt.rsi_oversold = int(cfg["rsi_oversold"])
    bt.take_profit_pct = float(cfg["tp_pct"])
    bt.stop_loss_pct = float(cfg["sl_pct"])
    bt.base_cooldown = int(cfg["base_cooldown"])
    bt.cooldown_time = int(cfg["base_cooldown"])
    bt.run(df_1m, df_4h, backtest_start_date=m47.BACKTEST_START)

    curve = pd.DataFrame(bt.equity_curve)[["timestamp", "equity"]].copy()
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    curve["variant"] = str(cfg["variant"])

    stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL_CASE)
    stats["sleeve"] = "case1"
    stats["variant"] = str(cfg["variant"])
    stats["entry_scale"] = float(cfg["entry_scale"])
    stats["rsi_oversold"] = int(cfg["rsi_oversold"])
    stats["tp_pct"] = float(cfg["tp_pct"]) * 100.0
    stats["sl_pct"] = float(cfg["sl_pct"]) * 100.0
    stats["dca_drop_pct"] = float(cfg["dca_drop_pct"]) * 100.0
    stats["shallow_gap_pct"] = float(cfg["shallow_gap_pct"]) * 100.0
    stats["base_cooldown"] = int(cfg["base_cooldown"])
    stats["trades"] = len(bt.trades)
    return curve, stats


def run_case2_baseline(df_1m: pd.DataFrame, df_4h: pd.DataFrame, base, helper, m32, s42) -> tuple[pd.DataFrame, dict]:
    bt_cls = s42.build_case2_class(m32)
    bt = bt_cls(
        base_module=base,
        symbol=SYMBOL,
        initial_capital=INITIAL_CAPITAL_CASE,
        commission=base.COMMISSION,
        entry_scale=0.60,
    )
    helper.configure_baseline_params(bt)
    bt.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)

    curve = pd.DataFrame(bt.equity_curve)[["timestamp", "equity"]].copy()
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    curve["variant"] = "baseline_case2"

    stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL_CASE)
    stats["sleeve"] = "case2"
    stats["variant"] = "baseline_case2"
    stats["trades"] = len(bt.trades)
    return curve, stats


def run_case3_variant(df: pd.DataFrame, s76, cfg: dict) -> tuple[pd.DataFrame, dict]:
    liq_hours = int(cfg["liq_hours"])
    gate_bars = int(cfg["gate_bars"])
    body_atr_mult = float(cfg["body_atr_mult"])
    tp_threshold = float(cfg["tp_return_pct"]) / 100.0
    stop_pct = float(cfg["stop_pct"])
    leverage = float(cfg["leverage"])

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
    stats = {
        "trades": 0,
        "tp_exits": 0,
        "stop_exits": 0,
        "signal_exits": 0,
        "liquidations": 0,
        "short_sweep_events": 0,
        "gated_entries": 0,
    }

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
            stats["short_sweep_events"] += 1

        if side != 0:
            liq_price = s76._liq_price(entry, leverage, side)
            stop_price = entry * (1.0 - stop_pct) if side > 0 else entry * (1.0 + stop_pct)

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
                stats["trades"] += 1
                stats["signal_exits"] += 1

            if desired_side != 0 and wallet > 0:
                allow_entry = True
                if desired_side < 0:
                    allow_entry = i <= short_gate_until and price_close < ema20[i]
                if allow_entry:
                    reserve, margin, qty, entry = s76._open_position(wallet, price_close, leverage, desired_side)
                    wallet = reserve + margin
                    side = desired_side
                    entry_wallet = wallet
                    if desired_side < 0:
                        stats["gated_entries"] += 1

        equity = wallet if side == 0 else s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
        rows.append({"timestamp": timestamps[i], "equity": equity, "variant": str(cfg["variant"])})

    if side != 0 and len(df):
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close_np[-1]), side)
        rows[-1]["equity"] = wallet
        stats["trades"] += 1

    curve = pd.DataFrame(rows)
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)

    out = compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL)
    out["sleeve"] = "case3"
    out["variant"] = str(cfg["variant"])
    out["leverage"] = leverage
    out["stop_pct"] = stop_pct * 100.0
    out["tp_return_pct"] = tp_threshold * 100.0
    out["liq_hours"] = liq_hours
    out["gate_bars"] = gate_bars
    out["body_atr_mult"] = body_atr_mult
    out["trades"] = stats["trades"]
    out["tp_exits"] = stats["tp_exits"]
    out["gated_entries"] = stats["gated_entries"]
    out["liquidations"] = stats["liquidations"]
    return curve, out


def build_merged(case1: pd.DataFrame, case2: pd.DataFrame, case3: pd.DataFrame) -> pd.DataFrame:
    common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
    common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())
    c1 = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)][["timestamp", "equity"]].rename(columns={"equity": "equity_case1"})
    c2 = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)][["timestamp", "equity"]].rename(columns={"equity": "equity_case2"})
    c3 = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)][["timestamp", "equity"]].rename(columns={"equity": "equity_case3"})

    merged = pd.merge(c1, c2, on="timestamp", how="outer")
    merged = pd.merge(merged, c3, on="timestamp", how="outer")
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged["equity_case3"] = merged["equity_case3"].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2", "equity_case3"]).copy()
    merged = merged.set_index("timestamp").resample("15min").last().dropna().reset_index()
    return merged


def run_portfolio_variant(merged: pd.DataFrame, weights: tuple[float, float, float], variant: str, s86) -> tuple[pd.DataFrame, dict]:
    w1, w2, w3 = weights
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

    fee_paid = 0.0
    rebalance_count = 0
    turnover_notional = 0.0

    cap1[0] = INITIAL_CAPITAL_TOTAL * w1
    cap2[0] = INITIAL_CAPITAL_TOTAL * w2
    cap3[0] = INITIAL_CAPITAL_TOTAL * w3
    total[0] = INITIAL_CAPITAL_TOTAL
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        c3 = cap3[i - 1] * (1.0 + float(ret3[i]))
        cur_total = c1 + c2 + c3
        cur_flow = 0.0

        if topup_flags[i]:
            cur_flow = MONTHLY_TOPUP
            target1_after = w1 * (cur_total + cur_flow)
            target2_after = w2 * (cur_total + cur_flow)
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
            max_drift = max(abs(aw1 - w1), abs(aw2 - w2), abs(aw3 - w3))
        else:
            max_drift = 0.0

        if rebal_flags[i] and max_drift >= THRESHOLD - 1e-12:
            target1 = cur_total * w1
            target2 = cur_total * w2
            target3 = cur_total * w3
            moved = abs(target1 - c1) + abs(target2 - c2) + abs(target3 - c3)
            fee = moved * REBALANCE_FEE_RATE
            cur_total -= fee
            c1 = cur_total * w1
            c2 = cur_total * w2
            c3 = cur_total * w3
            fee_paid += fee
            turnover_notional += moved
            rebalance_count += 1

        prev_total = total[i - 1]
        period_return = (cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0
        nav_index[i] = nav_index[i - 1] * (1.0 + period_return)

        cap1[i], cap2[i], cap3[i] = c1, c2, c3
        total[i] = cur_total
        flow[i] = cur_flow
        contrib[i] = contrib[i - 1] + cur_flow

    curve = merged[["timestamp"]].copy()
    curve["variant"] = variant
    curve["equity_total"] = total
    curve["cash_flow"] = flow
    curve["cumulative_contribution"] = contrib
    curve["nav_index"] = nav_index

    topups_df = pd.DataFrame({"timestamp": ts[topup_flags], "topup_amount": MONTHLY_TOPUP})
    stats = s86.compute_flow_metrics(curve, topups_df)
    stats["variant"] = variant
    stats["w1"] = w1
    stats["w2"] = w2
    stats["w3"] = w3
    stats["rebalance_count"] = rebalance_count
    stats["fee_paid"] = fee_paid
    stats["turnover_notional"] = turnover_notional
    return curve, stats


def save_plot(portfolio_metrics: pd.DataFrame, curve_map: dict[str, pd.DataFrame], sleeve_metrics: pd.DataFrame) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(16, 17), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.0, 1.0]})
    ax_eq, ax_perf, ax_case1, ax_case3 = axes
    cmap = plt.get_cmap("tab10")

    top = portfolio_metrics.head(8)
    colors = {variant: cmap(i % 10) for i, variant in enumerate(top["variant"])}
    for variant in top["variant"]:
        curve = curve_map[variant]
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.set_title("102 Study: ETH vol-scaled sleeve tuning")
    ax_eq.set_ylabel("Portfolio Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_perf.bar(top["variant"], top["twr_cagr_pct"], color=[colors[v] for v in top["variant"]], alpha=0.85, label="TWR CAGR %")
    ax_perf.set_ylabel("TWR CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf.tick_params(axis="x", rotation=20)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(top["variant"], top["twr_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="TWR MDD %")
    ax_perf_t.set_ylabel("TWR MDD %")
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper left")

    case1 = sleeve_metrics[sleeve_metrics["sleeve"] == "case1"].copy().sort_values("cagr_pct", ascending=False)
    ax_case1.bar(case1["variant"], case1["cagr_pct"], color="#1f77b4", alpha=0.85, label="CAGR %")
    ax_case1.set_ylabel("Case1 CAGR %")
    ax_case1.grid(True, axis="y", alpha=0.2)
    ax_case1.tick_params(axis="x", rotation=20)
    ax_case1_t = ax_case1.twinx()
    ax_case1_t.plot(case1["variant"], case1["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_case1_t.set_ylabel("Case1 MDD %")

    case3 = sleeve_metrics[sleeve_metrics["sleeve"] == "case3"].copy().sort_values("cagr_pct", ascending=False)
    ax_case3.bar(case3["variant"], case3["cagr_pct"], color="#2ca02c", alpha=0.85, label="CAGR %")
    ax_case3.set_ylabel("Case3 CAGR %")
    ax_case3.grid(True, axis="y", alpha=0.2)
    ax_case3.tick_params(axis="x", rotation=20)
    ax_case3_t = ax_case3.twinx()
    ax_case3_t.plot(case3["variant"], case3["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_case3_t.set_ylabel("Case3 MDD %")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(portfolio_metrics: pd.DataFrame, sleeve_metrics: pd.DataFrame) -> None:
    best = portfolio_metrics.iloc[0]
    baseline = portfolio_metrics[portfolio_metrics["variant"] == "eth_30_70_00__btc_ref_case1__btc_ref_case3"].iloc[0]
    best_case1 = sleeve_metrics[sleeve_metrics["sleeve"] == "case1"].sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]
    best_case3 = sleeve_metrics[sleeve_metrics["sleeve"] == "case3"].sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]

    lines: list[str] = []
    lines.append("# 102 Study: ETH vol-scaled sleeve tuning")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Treat ETH as higher-vol than BTC and retune case1/case3 absolute thresholds.")
    lines.append("- case1 axes: lower entry_scale, deeper RSI, wider DCA gap, wider TP/SL, wider hedge release gap.")
    lines.append("- case3 axes: lower leverage, wider stop, wider TP, longer gate duration.")
    lines.append("- case2 stays unchanged because it survived best on ETH.")
    lines.append("- Portfolio uses monthly 1000 top-up plus threshold 2% rebalance.")
    lines.append("")
    lines.append("## Sleeves")
    lines.append("")
    lines.append("| Sleeve | Variant | Final Equity | CAGR % | MDD % | Calmar | Trades |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for _, row in sleeve_metrics.sort_values(["sleeve", "calmar_ratio", "cagr_pct"], ascending=[True, False, False]).iterrows():
        lines.append(
            f"| {row['sleeve']} | {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {int(row['trades'])} |"
        )
    lines.append("")
    lines.append("## Portfolio")
    lines.append("")
    lines.append("| Variant | Weights | Final Equity | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in portfolio_metrics.head(20).iterrows():
        lines.append(
            f"| {row['variant']} | `{_fmt(row['w1'], 2)}/{_fmt(row['w2'], 2)}/{_fmt(row['w3'], 2)}` | "
            f"{_fmt(row['final_equity'])} | {_fmt(row['twr_cagr_pct'])} | {_fmt(row['twr_mdd_pct'])} | "
            f"{_fmt(row['twr_calmar_ratio'])} | {_fmt(row['xirr_pct'])} | {int(row['rebalance_count'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Best case1: `{best_case1['variant']}` -> CAGR `{_fmt(best_case1['cagr_pct'])}`, MDD `{_fmt(best_case1['max_drawdown_pct'])}`.")
    lines.append(f"- Best case3: `{best_case3['variant']}` -> CAGR `{_fmt(best_case3['cagr_pct'])}`, MDD `{_fmt(best_case3['max_drawdown_pct'])}`.")
    lines.append(
        f"- Best portfolio: `{best['variant']}` -> vs baseline CAGR `{_fmt(best['twr_cagr_pct'] - baseline['twr_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best['twr_mdd_pct'] - baseline['twr_mdd_pct'])}pp`, XIRR `{_fmt(best['xirr_pct'] - baseline['xirr_pct'])}pp`."
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run() -> None:
    m47 = load_module("m47_102", BASE_47_PATH)
    s62 = load_module("s62_102", BASE_62_PATH)
    base = load_module("m002_102", BASE_002_PATH)
    helper = load_module("m04_102", BASE_04_PATH)
    m32 = load_module("m32_102", BASE_32_PATH)
    s42 = load_module("s42_102", BASE_42_PATH)
    s76 = load_module("s76_102", BASE_76_PATH)
    s86 = load_module("s86_102", BASE_86_PATH)

    m47.SYMBOL = SYMBOL
    m47.BACKTEST_END = LATEST_END_DATE
    base.SYMBOL = SYMBOL
    base.BACKTEST_END = LATEST_END_DATE

    print(f"[{SYMBOL}] loading 1m/4h data", flush=True)
    df_1m, df_4h = m47.load_data_no_filter()
    latest_ts = df_1m.index.max()
    df_1m = df_1m[(df_1m.index >= m47.BACKTEST_START) & (df_1m.index <= latest_ts)].copy()

    sleeve_rows: list[dict] = []
    case1_curves: dict[str, pd.DataFrame] = {}
    case3_curves: dict[str, pd.DataFrame] = {}

    print(f"[{SYMBOL}] running case1 variants", flush=True)
    for cfg in CASE1_VARIANTS:
        curve, stats = run_case1_variant(df_1m, df_4h, m47, s62, cfg)
        case1_curves[str(cfg['variant'])] = curve
        sleeve_rows.append(stats)
        print(f"  case1 {cfg['variant']}: CAGR={stats['cagr_pct']:.4f}, MDD={stats['max_drawdown_pct']:.4f}", flush=True)

    print(f"[{SYMBOL}] running case2 baseline", flush=True)
    case2_curve, case2_stats = run_case2_baseline(df_1m, df_4h, base, helper, m32, s42)
    sleeve_rows.append(case2_stats)
    print(f"  case2 baseline: CAGR={case2_stats['cagr_pct']:.4f}, MDD={case2_stats['max_drawdown_pct']:.4f}", flush=True)

    print(f"[{SYMBOL}] preparing case3 market", flush=True)
    case3_market = prepare_case3_market(SYMBOL, m47)
    print(f"[{SYMBOL}] running case3 variants", flush=True)
    for cfg in CASE3_VARIANTS:
        curve, stats = run_case3_variant(case3_market, s76, cfg)
        case3_curves[str(cfg['variant'])] = curve
        sleeve_rows.append(stats)
        print(f"  case3 {cfg['variant']}: CAGR={stats['cagr_pct']:.4f}, MDD={stats['max_drawdown_pct']:.4f}", flush=True)

    sleeve_metrics = pd.DataFrame(sleeve_rows)
    sleeve_metrics = sleeve_metrics.sort_values(["sleeve", "calmar_ratio", "cagr_pct"], ascending=[True, False, False]).reset_index(drop=True)
    sleeve_metrics.to_csv(OUT_SLEEVES_CSV, index=False)

    print(f"[{SYMBOL}] sweeping portfolios", flush=True)
    portfolio_rows: list[dict] = []
    spec_map: dict[str, tuple[str, tuple[float, float, float], str]] = {}
    merged_cache: dict[tuple[str, str], pd.DataFrame] = {}
    for weight_name, weights in PORTFOLIO_WEIGHTS:
        for case1_name in case1_curves:
            for case3_name in case3_curves:
                merged_key = (case1_name, case3_name)
                if merged_key not in merged_cache:
                    merged_cache[merged_key] = build_merged(case1_curves[case1_name], case2_curve, case3_curves[case3_name])
                variant = f"{weight_name}__{case1_name}__{case3_name}"
                _, stats = run_portfolio_variant(merged_cache[merged_key], weights, variant, s86)
                portfolio_rows.append(stats)
                spec_map[variant] = (case1_name, weights, case3_name)

    portfolio_metrics = pd.DataFrame(portfolio_rows)
    portfolio_metrics = portfolio_metrics.sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).reset_index(drop=True)
    portfolio_metrics.to_csv(OUT_CSV, index=False)

    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}
    print(f"[{SYMBOL}] rebuilding top portfolio curves", flush=True)
    for variant in portfolio_metrics.head(12)["variant"]:
        case1_name, weights, case3_name = spec_map[variant]
        merged = merged_cache[(case1_name, case3_name)]
        curve, _ = run_portfolio_variant(merged, weights, variant, s86)
        curve_rows.append(curve)
        curve_map[variant] = curve

    pd.concat(curve_rows, ignore_index=True).to_csv(OUT_CURVES_CSV, index=False)
    save_plot(portfolio_metrics, curve_map, sleeve_metrics)
    save_report(portfolio_metrics, sleeve_metrics)

    best = portfolio_metrics.iloc[0]
    print(
        f"best portfolio={best['variant']} twr_cagr={best['twr_cagr_pct']:.6f} "
        f"mdd={best['twr_mdd_pct']:.6f} xirr={best['xirr_pct']:.6f}",
        flush=True,
    )


if __name__ == "__main__":
    run()
