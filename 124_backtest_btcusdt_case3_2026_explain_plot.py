from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
BASE_76_PATH = Path("76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py")
BASE_111_PATH = Path("111_backtest_btcusdt_sr_smc_5m_profitmax.py")
BASE_114_PATH = Path("114_backtest_btcusdt_best_with_sr_smc_filters.py")
BASE_117_PATH = Path("117_backtest_btcusdt_115_highcagr_push.py")

OUT_BASE = "124_backtest_btcusdt_case3_2026_explain_plot"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_STATE_CSV = Path(f"{OUT_BASE}.csv")
OUT_TRADES_CSV = Path(f"{OUT_BASE}_trades.csv")

PRIMARY_VARIANT = "lv3p0_g12_body25_tp20_lb5_none"
ANALYSIS_START = pd.Timestamp("2026-01-01 00:00:00")
TOP_NOTES = 3


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


def _fmt(v: float, digits: int = 2) -> str:
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


def compute_drawdown_episodes(curve: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    df = curve[["timestamp", "equity"]].copy().sort_values("timestamp").reset_index(drop=True)
    df["dd"] = df["equity"] / df["equity"].cummax() - 1.0

    episodes: list[dict] = []
    peak_idx = 0
    in_dd = False
    start_idx: int | None = None

    for i, dd in enumerate(df["dd"].to_numpy(dtype=float)):
        if not in_dd and dd < 0:
            in_dd = True
            start_idx = peak_idx
        if in_dd and dd == 0:
            assert start_idx is not None
            seg = df.iloc[start_idx : i + 1].copy()
            trough_idx = int(seg["dd"].idxmin())
            episodes.append(
                {
                    "peak_time": df.iloc[start_idx]["timestamp"],
                    "trough_time": df.iloc[trough_idx]["timestamp"],
                    "recovery_time": df.iloc[i]["timestamp"],
                    "depth_pct": -float(seg["dd"].min() * 100.0),
                }
            )
            in_dd = False
        if dd == 0:
            peak_idx = i

    if in_dd and start_idx is not None:
        seg = df.iloc[start_idx:].copy()
        trough_idx = int(seg["dd"].idxmin())
        episodes.append(
            {
                "peak_time": df.iloc[start_idx]["timestamp"],
                "trough_time": df.iloc[trough_idx]["timestamp"],
                "recovery_time": pd.NaT,
                "depth_pct": -float(seg["dd"].min() * 100.0),
            }
        )

    if not episodes:
        return pd.DataFrame(columns=["peak_time", "trough_time", "recovery_time", "depth_pct"])
    return pd.DataFrame(episodes).sort_values("depth_pct", ascending=False).head(top_n).reset_index(drop=True)


def run_logged_variant_124(df: pd.DataFrame, cfg: dict, s76, m117) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    leverage = float(cfg["leverage"])
    gate_bars = int(cfg["gate_bars"])
    body_atr_mult = float(cfg["body_atr_mult"])
    short_tp_threshold = float(cfg["short_tp_return_pct"]) / 100.0
    sr_entry_mode = str(cfg["sr_entry_mode"])
    long_block_threshold = int(cfg["long_block_threshold"])
    short_block_threshold = int(cfg["short_block_threshold"])

    timestamps = df["timestamp"].to_numpy()
    open_np = df["open"].to_numpy(dtype=float)
    high_np = df["high"].to_numpy(dtype=float)
    low_np = df["low"].to_numpy(dtype=float)
    close_np = df["close"].to_numpy(dtype=float)
    atr20 = df["atr20"].to_numpy(dtype=float)
    ema20 = df["ema20"].to_numpy(dtype=float)
    trend = df["trend_4h_confirmed"].astype(str).to_numpy()
    body = df["body"].to_numpy(dtype=float)
    liq_high = df["liq_high_24h_prev"].to_numpy(dtype=float)
    white_avg = df["white_avg"].to_numpy(dtype=float)
    red_floor = df["red_floor"].to_numpy(dtype=float)
    red_avg = df["red_avg"].to_numpy(dtype=float)
    bearish_ob_above_count = df["bearish_ob_above_count"].to_numpy(dtype=int)
    bullish_ob_below_count = df["bullish_ob_below_count"].to_numpy(dtype=int)

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
    active_trade: dict | None = None

    rows: list[dict] = []
    trades: list[dict] = []
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
        "short_sweep_events": 0,
        "gated_entries": 0,
        "blocked_short_gate": 0,
        "blocked_long_smc": 0,
        "blocked_short_smc": 0,
        "blocked_long_sr": 0,
        "blocked_short_sr": 0,
        "survived_to_end": 1,
    }
    first_liq_ts = None

    def close_active_trade(exit_idx: int, exit_price: float, exit_reason: str, realized_wallet: float) -> None:
        nonlocal active_trade
        if active_trade is None:
            return
        start = int(active_trade["entry_idx"])
        end = int(max(exit_idx, start))
        seg_high = float(np.nanmax(high_np[start : end + 1]))
        seg_low = float(np.nanmin(low_np[start : end + 1]))
        entry_price = float(active_trade["entry_price"])
        trade_side = int(active_trade["side"])
        underlying_return_pct = (float(exit_price) / entry_price - 1.0) * 100.0
        if trade_side > 0:
            favorable_excursion_pct = (seg_high / entry_price - 1.0) * 100.0
            adverse_excursion_pct = (seg_low / entry_price - 1.0) * 100.0
        else:
            favorable_excursion_pct = (entry_price / seg_low - 1.0) * 100.0
            adverse_excursion_pct = (entry_price / seg_high - 1.0) * 100.0
        trade_return_pct = (float(realized_wallet) / float(active_trade["entry_wallet"]) - 1.0) * 100.0
        trade_pnl = float(realized_wallet) - float(active_trade["entry_wallet"])

        trades.append(
            {
                "trade_id": int(active_trade["trade_id"]),
                "entry_idx": int(active_trade["entry_idx"]),
                "exit_idx": int(exit_idx),
                "entry_time": pd.Timestamp(active_trade["entry_time"]),
                "exit_time": pd.Timestamp(timestamps[exit_idx]),
                "side": trade_side,
                "side_label": "long" if trade_side > 0 else "short",
                "entry_price": entry_price,
                "exit_price": float(exit_price),
                "entry_reason": str(active_trade["entry_reason"]),
                "exit_reason": str(exit_reason),
                "entry_wallet": float(active_trade["entry_wallet"]),
                "exit_wallet": float(realized_wallet),
                "trade_return_pct": trade_return_pct,
                "trade_pnl": trade_pnl,
                "underlying_return_pct": underlying_return_pct,
                "favorable_excursion_pct": favorable_excursion_pct,
                "adverse_excursion_pct": adverse_excursion_pct,
                "bars_held": int(exit_idx - int(active_trade["entry_idx"]) + 1),
                "hours_held": (pd.Timestamp(timestamps[exit_idx]) - pd.Timestamp(active_trade["entry_time"])).total_seconds() / 3600.0,
                "entry_trend": str(active_trade["entry_trend"]),
                "entry_short_gate_open": int(active_trade["entry_short_gate_open"]),
                "entry_short_sweep_event": int(active_trade["entry_short_sweep_event"]),
                "entry_bearish_ob_above_count": int(active_trade["entry_bearish_ob_above_count"]),
                "entry_bullish_ob_below_count": int(active_trade["entry_bullish_ob_below_count"]),
                "entry_price_vs_red_avg_pct": float(active_trade["entry_price_vs_red_avg_pct"]),
                "entry_price_vs_white_avg_pct": float(active_trade["entry_price_vs_white_avg_pct"]),
                "entry_price_vs_red_floor_pct": float(active_trade["entry_price_vs_red_floor_pct"]),
            }
        )
        active_trade = None

    for i in range(len(df)):
        price_open = float(open_np[i])
        price_high = float(high_np[i])
        price_low = float(low_np[i])
        price_close = float(close_np[i])
        cur_trend = str(trend[i])
        blocked_reentry = False
        event_flag = ""

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
            event_flag = "short_sweep"

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
                close_active_trade(i, liq_price, "liquidation", wallet)
                event_flag = "liq_long"
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
                close_active_trade(i, liq_price, "liquidation", wallet)
                event_flag = "liq_short"
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
                close_active_trade(i, stop_price, "stop_loss", wallet)
                event_flag = "stop_long"
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
                close_active_trade(i, stop_price, "stop_loss", wallet)
                event_flag = "stop_short"
            elif side < 0 and entry_wallet > 0:
                marked_wallet = s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
                trade_return = marked_wallet / entry_wallet - 1.0
                if trade_return >= short_tp_threshold:
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
                    close_active_trade(i, price_close, "short_tp", wallet)
                    event_flag = "tp_short"

        desired_side = 1 if cur_trend == "bullish" else -1

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
                close_active_trade(i, price_close, "signal_flip", wallet)
                side = 0
                entry_wallet = np.nan
                stats["trades"] += 1
                stats["signal_exits"] += 1
                event_flag = "signal_exit"

            if desired_side != 0 and wallet > 0:
                allow_entry = True
                used_gate = False

                if desired_side < 0:
                    allow_entry = i <= short_gate_until and price_close < ema20[i]
                    used_gate = allow_entry
                    if not allow_entry:
                        stats["blocked_short_gate"] += 1

                if allow_entry and not m117.sr_entry_allowed(
                    desired_side,
                    price_close,
                    white_avg[i],
                    red_floor[i],
                    red_avg[i],
                    sr_entry_mode,
                ):
                    allow_entry = False
                    if desired_side > 0:
                        stats["blocked_long_sr"] += 1
                    else:
                        stats["blocked_short_sr"] += 1

                if allow_entry and not m117.smc_entry_allowed(
                    desired_side,
                    int(bearish_ob_above_count[i]),
                    int(bullish_ob_below_count[i]),
                    long_block_threshold,
                    short_block_threshold,
                ):
                    allow_entry = False
                    if desired_side > 0:
                        stats["blocked_long_smc"] += 1
                    else:
                        stats["blocked_short_smc"] += 1

                if allow_entry:
                    reserve, margin, qty, entry = s76._open_position(wallet, price_close, leverage, desired_side)
                    wallet = reserve + margin
                    side = desired_side
                    entry_wallet = wallet
                    active_trade = {
                        "trade_id": len(trades) + 1,
                        "entry_idx": i,
                        "entry_time": pd.Timestamp(timestamps[i]),
                        "side": desired_side,
                        "entry_price": price_close,
                        "entry_wallet": wallet,
                        "entry_reason": "bearish_trend_short_gate" if desired_side < 0 else "bullish_trend_long",
                        "entry_trend": cur_trend,
                        "entry_short_gate_open": int(i <= short_gate_until),
                        "entry_short_sweep_event": int(short_sweep_event),
                        "entry_bearish_ob_above_count": int(bearish_ob_above_count[i]),
                        "entry_bullish_ob_below_count": int(bullish_ob_below_count[i]),
                        "entry_price_vs_red_avg_pct": (price_close / red_avg[i] - 1.0) * 100.0 if red_avg[i] != 0 else np.nan,
                        "entry_price_vs_white_avg_pct": (price_close / white_avg[i] - 1.0) * 100.0 if white_avg[i] != 0 else np.nan,
                        "entry_price_vs_red_floor_pct": (price_close / red_floor[i] - 1.0) * 100.0 if red_floor[i] != 0 else np.nan,
                    }
                    if desired_side > 0:
                        stats["long_entries"] += 1
                        event_flag = "entry_long"
                    else:
                        stats["short_entries"] += 1
                        event_flag = "entry_short"
                    if used_gate:
                        stats["gated_entries"] += 1

        equity = wallet if side == 0 else s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
        rows.append(
            {
                "timestamp": pd.Timestamp(timestamps[i]),
                "open": price_open,
                "high": price_high,
                "low": price_low,
                "close": price_close,
                "ema20": float(ema20[i]),
                "white_avg": float(white_avg[i]),
                "red_avg": float(red_avg[i]),
                "red_floor": float(red_floor[i]),
                "equity": equity,
                "wallet": wallet,
                "reserve": reserve,
                "margin": margin,
                "side": side,
                "locked_side": locked_side,
                "short_gate_open": int(i <= short_gate_until),
                "short_sweep_event": int(short_sweep_event),
                "trend_4h_confirmed": cur_trend,
                "bearish_ob_above_count": int(bearish_ob_above_count[i]),
                "bullish_ob_below_count": int(bullish_ob_below_count[i]),
                "long_block_active": int(int(bearish_ob_above_count[i]) >= long_block_threshold),
                "event_flag": event_flag,
                "variant": str(cfg["variant"]),
            }
        )

    if side != 0 and len(df):
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close_np[-1]), side)
        close_active_trade(len(df) - 1, float(close_np[-1]), "final_close", wallet)
        rows[-1]["equity"] = wallet
        rows[-1]["wallet"] = wallet
        rows[-1]["reserve"] = wallet
        rows[-1]["margin"] = 0.0
        rows[-1]["side"] = 0
        stats["trades"] += 1

    curve = pd.DataFrame(rows)
    trades_df = pd.DataFrame(trades)
    stats["first_liquidation_ts"] = first_liq_ts
    return curve, trades_df, stats


def trade_note_ko(row: pd.Series) -> str:
    ret = float(row["trade_return_pct"])
    gate_text = "24시간 상단 유동성 스윕 뒤 short gate가 열려" if int(row["entry_short_gate_open"]) else "gate 없이"
    boxes = int(row["entry_bearish_ob_above_count"])
    if int(row["side"]) < 0:
        if row["exit_reason"] == "short_tp":
            return f"{gate_text} 들어간 숏이 가격 하락을 타고 TP에 도달했다. 트레이드 수익률 {ret:.2f}%."
        if row["exit_reason"] == "stop_loss":
            return f"{gate_text} 들어간 숏이었지만 반등이 커서 6% 손절로 종료됐다. 트레이드 수익률 {ret:.2f}%."
        if row["exit_reason"] == "signal_flip":
            return f"{gate_text} 들어간 숏이었지만 4시간 추세가 위로 뒤집히며 시그널 청산됐다. 트레이드 수익률 {ret:.2f}%."
        if row["exit_reason"] == "liquidation":
            return f"{gate_text} 들어간 숏이 강한 역추세 반등을 맞아 청산됐다. 트레이드 수익률 {ret:.2f}%."
        return f"{gate_text} 들어간 숏이 마감 시점까지 보유됐다. 트레이드 수익률 {ret:.2f}%."
    if row["exit_reason"] == "stop_loss":
        return f"4시간 bullish 롱이었지만 상단 bearish OB {boxes}개를 둔 상태에서 하락 반전이 빨라 6% 손절이 났다. 트레이드 수익률 {ret:.2f}%."
    if row["exit_reason"] == "signal_flip":
        return f"4시간 bullish 롱이었지만 추세가 다시 bearish로 꺾여 시그널 청산됐다. 트레이드 수익률 {ret:.2f}%."
    if row["exit_reason"] == "liquidation":
        return f"4시간 bullish 롱이 급락을 맞아 청산됐다. 트레이드 수익률 {ret:.2f}%."
    return f"4시간 bullish 롱이 상승 구간을 타며 이익 실현됐다. 트레이드 수익률 {ret:.2f}%."


def episode_note_ko(row: pd.Series, state_2026: pd.DataFrame) -> str:
    peak_time = pd.Timestamp(row["peak_time"])
    trough_time = pd.Timestamp(row["trough_time"])
    seg = state_2026[(state_2026["timestamp"] >= peak_time) & (state_2026["timestamp"] <= trough_time)].copy()
    if seg.empty:
        return "세부 구간 데이터를 충분히 잡지 못했다."
    btc_move = (float(seg["close"].iloc[-1]) / float(seg["close"].iloc[0]) - 1.0) * 100.0
    long_share = float((seg["side"] > 0).mean() * 100.0)
    short_share = float((seg["side"] < 0).mean() * 100.0)
    gate_share = float(seg["short_gate_open"].mean() * 100.0)
    block_share = float(seg["long_block_active"].mean() * 100.0)
    if btc_move < -8 and long_share > short_share:
        return f"BTC가 {btc_move:.2f}% 빠지는 동안 롱 노출 비중이 {long_share:.1f}%로 더 높아 손실이 커졌다."
    if short_share >= 40 and abs(btc_move) < 4:
        return f"가격 방향이 애매한데 숏 노출이 {short_share:.1f}%로 유지돼 휩쏘성 손실이 누적됐다."
    return f"gate open 비중 {gate_share:.1f}%, long block 활성 비중 {block_share:.1f}% 상태에서 방향성이 약해 회복이 지연됐다."


def build_2026_outputs(curve: pd.DataFrame, trades_df: pd.DataFrame, end_ts: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    analysis_end = min(pd.Timestamp(end_ts).floor("15min"), pd.Timestamp(curve["timestamp"].max()))
    state_2026 = curve[(curve["timestamp"] >= ANALYSIS_START) & (curve["timestamp"] <= analysis_end)].copy().reset_index(drop=True)
    if state_2026.empty:
        raise RuntimeError("No 2026 data found in curve.")
    base_equity = float(state_2026["equity"].iloc[0])
    state_2026["equity_index_2026"] = state_2026["equity"].astype(float) / base_equity * 100.0
    state_2026["drawdown_2026_pct"] = (state_2026["equity"].astype(float) / state_2026["equity"].cummax().astype(float) - 1.0) * 100.0

    if trades_df.empty:
        trades_2026 = trades_df.copy()
    else:
        trades_2026 = trades_df[
            (pd.to_datetime(trades_df["exit_time"]) >= ANALYSIS_START)
            & (pd.to_datetime(trades_df["entry_time"]) <= analysis_end)
        ].copy()
        trades_2026["analysis_note"] = trades_2026.apply(trade_note_ko, axis=1)

    closed_2026 = trades_2026[pd.to_datetime(trades_2026["exit_time"]).between(ANALYSIS_START, analysis_end)].copy()
    period_return_pct = (float(state_2026["equity"].iloc[-1]) / base_equity - 1.0) * 100.0
    period_mdd_pct = float(-state_2026["drawdown_2026_pct"].min())
    exit_breakdown = (
        closed_2026.groupby("exit_reason")
        .agg(
            trades=("trade_id", "count"),
            avg_trade_return_pct=("trade_return_pct", "mean"),
            total_trade_pnl=("trade_pnl", "sum"),
        )
        .reset_index()
        .sort_values(["total_trade_pnl", "trades"], ascending=[False, False])
    )
    side_breakdown = (
        closed_2026.groupby("side_label")
        .agg(
            trades=("trade_id", "count"),
            win_rate_pct=("trade_return_pct", lambda x: float((x > 0).mean() * 100.0) if len(x) else np.nan),
            avg_trade_return_pct=("trade_return_pct", "mean"),
            total_trade_pnl=("trade_pnl", "sum"),
        )
        .reset_index()
        .sort_values("total_trade_pnl", ascending=False)
    )
    dd_episodes = compute_drawdown_episodes(state_2026, top_n=3)
    if not dd_episodes.empty:
        dd_episodes["episode_note"] = dd_episodes.apply(lambda row: episode_note_ko(row, state_2026), axis=1)

    summary = {
        "analysis_start": ANALYSIS_START,
        "analysis_end": analysis_end,
        "period_start_equity": base_equity,
        "period_end_equity": float(state_2026["equity"].iloc[-1]),
        "period_return_pct": period_return_pct,
        "period_mdd_pct": period_mdd_pct,
        "trade_count": int(len(closed_2026)),
        "win_rate_pct": float((closed_2026["trade_return_pct"] > 0).mean() * 100.0) if len(closed_2026) else np.nan,
        "carry_in_trade_count": int(((pd.to_datetime(trades_2026["entry_time"]) < ANALYSIS_START) & (pd.to_datetime(trades_2026["exit_time"]) >= ANALYSIS_START)).sum()) if len(trades_2026) else 0,
        "exit_breakdown": exit_breakdown,
        "side_breakdown": side_breakdown,
        "drawdown_episodes": dd_episodes,
    }
    return state_2026, trades_2026, summary


def save_plot(state_2026: pd.DataFrame, trades_2026: pd.DataFrame, summary: dict) -> None:
    fig, axes = plt.subplots(
        4,
        1,
        figsize=(18, 14),
        sharex=True,
        gridspec_kw={"height_ratios": [2.4, 1.2, 1.4, 1.3]},
    )
    ax_price, ax_filters, ax_equity, ax_trades = axes

    bearish_mask = state_2026["trend_4h_confirmed"].eq("bearish").to_numpy(dtype=bool)
    short_gate_mask = state_2026["short_gate_open"].astype(bool).to_numpy()
    long_block_mask = state_2026["long_block_active"].astype(bool).to_numpy()

    ax_price.plot(state_2026["timestamp"], state_2026["close"], color="#111111", linewidth=1.1, label="BTC close")
    ax_price.plot(state_2026["timestamp"], state_2026["white_avg"], color="#e6e6e6", linewidth=0.9, label="white_avg")
    ax_price.plot(state_2026["timestamp"], state_2026["red_avg"], color="#ff4d4d", linewidth=0.9, label="red_avg")
    ax_price.plot(state_2026["timestamp"], state_2026["red_floor"], color="#aa0000", linewidth=0.8, alpha=0.8, label="red_floor")
    ax_price.fill_between(state_2026["timestamp"], state_2026["red_floor"], state_2026["red_avg"], color="#ffcccc", alpha=0.15)
    ax_price.fill_between(
        state_2026["timestamp"],
        0,
        1,
        where=bearish_mask,
        color="#000000",
        alpha=0.04,
        transform=ax_price.get_xaxis_transform(),
        label="4h bearish",
    )

    if not trades_2026.empty:
        entry_in = trades_2026[pd.to_datetime(trades_2026["entry_time"]).between(summary["analysis_start"], summary["analysis_end"])]
        exit_in = trades_2026[pd.to_datetime(trades_2026["exit_time"]).between(summary["analysis_start"], summary["analysis_end"])]
        long_entries = entry_in[entry_in["side"] > 0]
        short_entries = entry_in[entry_in["side"] < 0]
        ax_price.scatter(long_entries["entry_time"], long_entries["entry_price"], marker="^", s=42, color="#2ca02c", label="long entry", zorder=5)
        ax_price.scatter(short_entries["entry_time"], short_entries["entry_price"], marker="v", s=42, color="#d62728", label="short entry", zorder=5)

        good_exits = exit_in[exit_in["trade_return_pct"] >= 0]
        bad_exits = exit_in[exit_in["trade_return_pct"] < 0]
        ax_price.scatter(good_exits["exit_time"], good_exits["exit_price"], marker="o", s=28, color="#1f77b4", label="profit exit", zorder=5)
        ax_price.scatter(bad_exits["exit_time"], bad_exits["exit_price"], marker="x", s=36, color="#ff7f0e", label="loss exit", zorder=5)

        note_candidates = pd.concat(
            [
                trades_2026.nlargest(TOP_NOTES, "trade_return_pct"),
                trades_2026.nsmallest(TOP_NOTES, "trade_return_pct"),
            ],
            ignore_index=True,
        ).drop_duplicates(subset=["trade_id"])
        for _, row in note_candidates.iterrows():
            exit_time = pd.Timestamp(row["exit_time"])
            if exit_time < summary["analysis_start"] or exit_time > summary["analysis_end"]:
                continue
            label = f"{'+' if row['trade_return_pct'] >= 0 else ''}{row['trade_return_pct']:.1f}%\n{row['exit_reason']}"
            ax_price.annotate(
                label,
                (exit_time, float(row["exit_price"])),
                xytext=(0, 10 if row["trade_return_pct"] >= 0 else -28),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "#999999", "alpha": 0.85},
            )

    ax_price.set_title("Study 124: 2026 Case3 Detailed Explanation")
    ax_price.set_ylabel("Price")
    ax_price.grid(True, alpha=0.2)
    ax_price.legend(loc="upper left", ncol=4, fontsize=8)

    ax_filters.plot(state_2026["timestamp"], state_2026["bearish_ob_above_count"], color="#c62828", linewidth=1.0, label="bearish OB above")
    ax_filters.plot(state_2026["timestamp"], state_2026["bullish_ob_below_count"], color="#1565c0", linewidth=1.0, label="bullish OB below")
    ax_filters.axhline(5, color="#555555", linestyle="--", linewidth=0.8, label="SMC block threshold")
    ax_filters.fill_between(state_2026["timestamp"], 0, 5.2, where=short_gate_mask, color="#ffb3b3", alpha=0.22, label="short gate open")
    ax_filters.fill_between(state_2026["timestamp"], 0, 5.2, where=long_block_mask, color="#cce5ff", alpha=0.22, label="long block active")
    ax_filters.set_ylim(-0.1, 5.4)
    ax_filters.set_ylabel("Filter")
    ax_filters.grid(True, alpha=0.2)

    ax_side = ax_filters.twinx()
    ax_side.step(state_2026["timestamp"], state_2026["side"], where="post", color="#222222", linewidth=1.0, alpha=0.7, label="position side")
    ax_side.set_ylim(-1.4, 1.4)
    ax_side.set_yticks([-1, 0, 1])
    ax_side.set_yticklabels(["Short", "Flat", "Long"])
    lines1, labels1 = ax_filters.get_legend_handles_labels()
    lines2, labels2 = ax_side.get_legend_handles_labels()
    ax_filters.legend(lines1 + lines2, labels1 + labels2, loc="upper left", ncol=4, fontsize=8)

    ax_equity.plot(state_2026["timestamp"], state_2026["equity_index_2026"], color="#2f4f4f", linewidth=1.1, label="Equity index (2026=100)")
    ax_equity.set_ylabel("Equity")
    ax_equity.grid(True, alpha=0.2)
    ax_dd = ax_equity.twinx()
    ax_dd.fill_between(state_2026["timestamp"], state_2026["drawdown_2026_pct"], 0, color="#ffb3b3", alpha=0.35, label="Drawdown %")
    ax_dd.set_ylabel("Drawdown %")
    ax_dd.set_ylim(min(-1.0, float(state_2026["drawdown_2026_pct"].min()) * 1.15), 1.0)

    dd_episodes = summary["drawdown_episodes"]
    if isinstance(dd_episodes, pd.DataFrame) and not dd_episodes.empty:
        for _, row in dd_episodes.iterrows():
            end = pd.Timestamp(row["recovery_time"]) if pd.notna(row["recovery_time"]) else summary["analysis_end"]
            ax_equity.axvspan(pd.Timestamp(row["peak_time"]), end, color="#d62728", alpha=0.08)

    lines1, labels1 = ax_equity.get_legend_handles_labels()
    lines2, labels2 = ax_dd.get_legend_handles_labels()
    ax_equity.legend(lines1 + lines2, labels1 + labels2, loc="upper left", ncol=2, fontsize=8)

    if not trades_2026.empty:
        plot_trades = trades_2026[pd.to_datetime(trades_2026["exit_time"]).between(summary["analysis_start"], summary["analysis_end"])].copy()
        colors = np.where(plot_trades["trade_return_pct"].to_numpy(dtype=float) >= 0, "#2ca02c", "#d62728")
        ax_trades.bar(plot_trades["exit_time"], plot_trades["trade_return_pct"], width=4 / 24, color=colors, alpha=0.85)
        ax_trades.axhline(0, color="#444444", linewidth=0.8)
        for _, row in plot_trades.iterrows():
            if abs(float(row["trade_return_pct"])) < 8:
                continue
            ax_trades.annotate(
                row["side_label"][0].upper(),
                (pd.Timestamp(row["exit_time"]), float(row["trade_return_pct"])),
                xytext=(0, 6 if row["trade_return_pct"] >= 0 else -12),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )
    ax_trades.set_ylabel("Trade %")
    ax_trades.set_xlabel("2026")
    ax_trades.grid(True, axis="y", alpha=0.2)

    locator = mdates.AutoDateLocator(minticks=6, maxticks=10)
    formatter = mdates.ConciseDateFormatter(locator)
    ax_trades.xaxis.set_major_locator(locator)
    ax_trades.xaxis.set_major_formatter(formatter)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(overall_stats: dict, summary: dict, trades_2026: pd.DataFrame, stats: dict, end_ts: pd.Timestamp) -> None:
    exit_breakdown = summary["exit_breakdown"]
    side_breakdown = summary["side_breakdown"]
    dd_episodes = summary["drawdown_episodes"]
    closed_2026 = trades_2026[pd.to_datetime(trades_2026["exit_time"]).between(summary["analysis_start"], summary["analysis_end"])].copy()
    top_winners = closed_2026[closed_2026["trade_return_pct"] > 0].nlargest(TOP_NOTES, "trade_return_pct")
    top_losers = closed_2026[closed_2026["trade_return_pct"] < 0].nsmallest(TOP_NOTES, "trade_return_pct")
    profit_side = side_breakdown.iloc[0]["side_label"] if not side_breakdown.empty else "N/A"
    profit_side_pnl = side_breakdown.iloc[0]["total_trade_pnl"] if not side_breakdown.empty else np.nan

    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("# Study 124: 2026 Case3 Detailed Explanation\n\n")
        f.write("## 분석 대상\n")
        f.write(f"- 전략: `{PRIMARY_VARIANT}`\n")
        f.write(f"- 데이터 사용 기간: `2021-01-01`부터 로컬 최신 캐시 종료 시점인 `{pd.Timestamp(end_ts)}`까지\n")
        f.write(f"- 2026 상세 분석 구간: `{summary['analysis_start']}` ~ `{summary['analysis_end']}`\n")
        f.write("- 주의: 오늘 날짜는 2026-04-12이지만 로컬 1분/4시간 캐시는 2026-03-15까지만 존재했다.\n\n")

        f.write("## 전체 전략 성적\n")
        for key, label in [
            ("final_equity", "최종 자산"),
            ("total_return_pct", "총수익률"),
            ("cagr_pct", "CAGR"),
            ("max_drawdown_pct", "최대낙폭"),
            ("calmar_ratio", "Calmar"),
        ]:
            suffix = "%" if "pct" in key else ""
            f.write(f"- {label}: `{_fmt(overall_stats[key])}{suffix}`\n")

        f.write("\n## 2026 구간 요약\n")
        f.write(f"- 2026 시작 자산: `{_fmt(summary['period_start_equity'])}`\n")
        f.write(f"- 2026 종료 자산: `{_fmt(summary['period_end_equity'])}`\n")
        f.write(f"- 2026 구간 수익률: `{_fmt(summary['period_return_pct'])}%`\n")
        f.write(f"- 2026 구간 최대낙폭: `{_fmt(summary['period_mdd_pct'])}%`\n")
        f.write(f"- 2026 종료 기준 거래 수: `{summary['trade_count']}`\n")
        f.write(f"- 2026 승률: `{_fmt(summary['win_rate_pct'])}%`\n")
        f.write(f"- 2026 시작 시점에 이미 들고 온 포지션 수: `{summary['carry_in_trade_count']}`\n")
        f.write(f"- 2026에서 수익 기여가 가장 큰 방향: `{profit_side}` (`{_fmt(profit_side_pnl)}` USDT)\n")
        f.write(f"- 전체 short gate 발동 횟수: `{stats['short_sweep_events']}`\n")
        f.write(f"- long SMC 차단 횟수: `{stats['blocked_long_smc']}`\n\n")

        f.write("## 왜 수익이 났나\n")
        if not side_breakdown.empty:
            for _, row in side_breakdown.iterrows():
                f.write(
                    f"- `{row['side_label']}`: 거래 `{int(row['trades'])}`건, 평균 `{_fmt(row['avg_trade_return_pct'])}%`, "
                    f"총손익 `{_fmt(row['total_trade_pnl'])}` USDT, 승률 `{_fmt(row['win_rate_pct'])}%`\n"
                )
        if not exit_breakdown.empty:
            for _, row in exit_breakdown.iterrows():
                f.write(
                    f"- `{row['exit_reason']}`: `{int(row['trades'])}`건, 평균 `{_fmt(row['avg_trade_return_pct'])}%`, "
                    f"총손익 `{_fmt(row['total_trade_pnl'])}` USDT\n"
                )
        f.write("- 해석: 이 전략은 4시간 bearish 구간에서 24시간 상단 유동성 스윕이 나온 뒤 short gate가 열릴 때 숏으로 돈을 버는 구조가 가장 강했다.\n")
        f.write("- 반대로 bullish 롱은 상단 OB가 5개 미만일 때만 허용되는데, 2026에서는 상승 추세가 오래 이어지지 않는 구간에서 롱이 흔들렸다.\n\n")

        f.write("## 왜 손실이 났나\n")
        if isinstance(dd_episodes, pd.DataFrame) and not dd_episodes.empty:
            for idx, row in dd_episodes.iterrows():
                recovery = pd.Timestamp(row["recovery_time"]) if pd.notna(row["recovery_time"]) else summary["analysis_end"]
                f.write(
                    f"- DD{idx+1}: `{pd.Timestamp(row['peak_time'])}` -> `{pd.Timestamp(row['trough_time'])}` "
                    f"(회복 기준 `{recovery}`), 낙폭 `{_fmt(row['depth_pct'])}%`. {row['episode_note']}\n"
                )
        else:
            f.write("- 2026 구간에 독립적으로 식별된 drawdown episode가 거의 없었다.\n")
        f.write("- 요약하면 2026 손실은 주로 `빠른 반등으로 숏 손절`, `롱 진입 뒤 추세가 바로 꺾이는 구간`, `가격은 크게 안 움직이는데 방향만 자주 바뀌는 구간`에서 나왔다.\n\n")

        f.write("## 대표 수익 트레이드\n")
        if top_winners.empty:
            f.write("- 2026 종료 거래가 없어 대표 수익 트레이드를 뽑지 못했다.\n")
        else:
            for _, row in top_winners.iterrows():
                f.write(
                    f"- `{pd.Timestamp(row['entry_time'])}` -> `{pd.Timestamp(row['exit_time'])}` / `{row['side_label']}` / "
                    f"`{_fmt(row['trade_return_pct'])}%` / `{row['exit_reason']}` / {row['analysis_note']}\n"
                )

        f.write("\n## 대표 손실 트레이드\n")
        if top_losers.empty:
            f.write("- 2026 종료 거래가 없어 대표 손실 트레이드를 뽑지 못했다.\n")
        else:
            for _, row in top_losers.iterrows():
                f.write(
                    f"- `{pd.Timestamp(row['entry_time'])}` -> `{pd.Timestamp(row['exit_time'])}` / `{row['side_label']}` / "
                    f"`{_fmt(row['trade_return_pct'])}%` / `{row['exit_reason']}` / {row['analysis_note']}\n"
                )

        f.write("\n## 해석 결론\n")
        f.write("- 2026 수익의 중심은 여전히 short gate 기반 숏이었다.\n")
        f.write("- 2026 손실의 중심은 3.0x 레버리지에서 발생하는 빠른 역행과 시그널 뒤집힘이었다.\n")
        f.write("- CAGR을 크게 훼손하지 않으면서 방어하려면, 123에서 본 것처럼 `3.0x -> 2.5x` 다운시프트가 가장 먼저 검토할 후보로 남아 있다.\n")


def main() -> None:
    m47 = load_module("study47_for_124", BASE_47_PATH)
    s76 = load_module("study76_for_124", BASE_76_PATH)
    m111 = load_module("study111_for_124", BASE_111_PATH)
    m114 = load_module("study114_for_124", BASE_114_PATH)
    m117 = load_module("study117_for_124", BASE_117_PATH)

    df_1m, df_4h, end_ts = m114.load_market_data_2021plus()
    market = m114.prepare_market_114(df_1m, df_4h, m47, m111)
    cfg = next((row for row in m117.build_variants() if row["variant"] == PRIMARY_VARIANT), None)
    if cfg is None:
        raise RuntimeError(f"Variant not found: {PRIMARY_VARIANT}")

    curve, trades_df, stats = run_logged_variant_124(market, cfg, s76, m117)
    overall_stats = compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL)
    state_2026, trades_2026, summary = build_2026_outputs(curve, trades_df, end_ts)

    state_2026.to_csv(OUT_STATE_CSV, index=False, encoding="utf-8-sig")
    trades_2026.to_csv(OUT_TRADES_CSV, index=False, encoding="utf-8-sig")
    save_plot(state_2026, trades_2026, summary)
    save_report(overall_stats, summary, trades_2026, stats, end_ts)

    print(f"[124] Variant: {PRIMARY_VARIANT}")
    print(f"[124] Data end: {pd.Timestamp(end_ts)}")
    print(f"[124] 2026 period: {summary['analysis_start']} -> {summary['analysis_end']}")
    print(f"[124] 2026 return: {_fmt(summary['period_return_pct'])}%")
    print(f"[124] 2026 max drawdown: {_fmt(summary['period_mdd_pct'])}%")
    print(f"[124] 2026 trades: {summary['trade_count']}")
    print(f"[124] Outputs: {OUT_MD}, {OUT_STATE_CSV}, {OUT_TRADES_CSV}, {OUT_PNG}")


if __name__ == "__main__":
    main()
