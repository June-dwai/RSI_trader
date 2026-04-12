from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
REFERENCE_80_CURVES_CSV = Path("80_backtest_btcusdt_scale06_adx002_regime_hold_short_tp_tune_curves.csv")
DATA_1M_PATH = Path("historical_data_mainnet/BTCUSDT_1m_2022-01-01_2026-03-15.pkl")

OUT_BASE = "82_backtest_btcusdt_scale06_adx002_ict_smc_archetypes"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

INITIAL_CAPITAL = 1000.0
COMMISSION = 0.0004

REFERENCE_VARIANTS = [
    {"variant": "reference_shorttp15_15x", "source_variant": "short_tp15_lock_1.5x"},
    {"variant": "reference_shorttp15_2x", "source_variant": "short_tp15_lock_2x"},
]

VARIANTS = [
    {
        "variant": "smc_sweep8h_reversal_15m",
        "mode": "live",
        "archetype": "sweep_reversal",
        "liq_window": "8h",
        "entry_scale": 0.95,
        "body_atr_mult": 0.35,
        "stop_buffer_atr": 0.20,
        "target_r": 2.0,
        "max_hold_bars": 24,
        "cooldown_bars": 4,
    },
    {
        "variant": "smc_sweep24h_reversal_15m",
        "mode": "live",
        "archetype": "sweep_reversal",
        "liq_window": "24h",
        "entry_scale": 0.95,
        "body_atr_mult": 0.40,
        "stop_buffer_atr": 0.20,
        "target_r": 2.2,
        "max_hold_bars": 32,
        "cooldown_bars": 4,
    },
    {
        "variant": "smc_fvg_reclaim_15m",
        "mode": "live",
        "archetype": "fvg_reclaim",
        "entry_scale": 0.95,
        "displacement_atr_mult": 1.00,
        "bos_window": 16,
        "expiry_bars": 12,
        "stop_buffer_atr": 0.25,
        "target_r": 2.5,
        "max_hold_bars": 36,
        "cooldown_bars": 4,
    },
    {
        "variant": "smc_orderblock_reclaim_15m",
        "mode": "live",
        "archetype": "orderblock_reclaim",
        "entry_scale": 0.95,
        "displacement_atr_mult": 0.90,
        "bos_window": 20,
        "ob_lookback": 6,
        "expiry_bars": 20,
        "stop_buffer_atr": 0.25,
        "target_r": 3.0,
        "max_hold_bars": 48,
        "cooldown_bars": 4,
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


def _fmt_count(v: float) -> str:
    if pd.isna(v):
        return "N/A"
    return str(int(v))


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


def _resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    out = (
        df.resample(rule, label="right", closed="right")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna()
    )
    return out


def load_reference_curves() -> dict[str, pd.DataFrame]:
    curves = pd.read_csv(REFERENCE_80_CURVES_CSV, parse_dates=["timestamp"])
    out: dict[str, pd.DataFrame] = {}
    for cfg in REFERENCE_VARIANTS:
        ref = curves[curves["variant"] == str(cfg["source_variant"])].copy()
        if ref.empty:
            continue
        ref = ref.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)
        ref = ref[["timestamp", "equity"]].copy()
        ref["variant"] = str(cfg["variant"])
        out[str(cfg["variant"])] = ref
    return out


def prepare_market(m47) -> pd.DataFrame:
    df_1m = pd.read_pickle(DATA_1M_PATH).copy().sort_index()
    if not isinstance(df_1m.index, pd.DatetimeIndex):
        df_1m.index = pd.to_datetime(df_1m.index)

    df_15m = _resample_ohlc(df_1m, "15min")
    df_1h = _resample_ohlc(df_1m, "1h")
    df_4h = _resample_ohlc(df_1m, "4h")

    df_4h["ema200_closed"] = df_4h["close"].ewm(span=m47.EMA_PERIOD, adjust=False).mean()
    df_4h["ema200_prev_closed"] = df_4h["ema200_closed"].shift(1)
    df_4h["trend_4h_hyst"] = m47.LiveParityNoLookahead._compute_hysteresis_state(
        df_4h["close"], df_4h["ema200_prev_closed"], m47.HYSTERESIS_BAND
    )
    df_4h["trend_4h_confirmed"] = df_4h["trend_4h_hyst"].shift(1)
    df_4h = df_4h.reset_index().rename(columns={"index": "timestamp"})

    df_1h["liq_high_8h_prev"] = df_1h["high"].rolling(8).max().shift(1)
    df_1h["liq_low_8h_prev"] = df_1h["low"].rolling(8).min().shift(1)
    df_1h["liq_high_24h_prev"] = df_1h["high"].rolling(24).max().shift(1)
    df_1h["liq_low_24h_prev"] = df_1h["low"].rolling(24).min().shift(1)
    df_1h["hour_close_prev"] = df_1h["close"].shift(1)
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
    out["ema50"] = out["close"].ewm(span=50, adjust=False).mean()

    for window in [4, 16, 20]:
        out[f"high_{window}_prev"] = out["high"].rolling(window).max().shift(1)
        out[f"low_{window}_prev"] = out["low"].rolling(window).min().shift(1)

    out = pd.merge_asof(
        out.sort_values("timestamp"),
        df_1h.sort_values("timestamp")[
            ["timestamp", "liq_high_8h_prev", "liq_low_8h_prev", "liq_high_24h_prev", "liq_low_24h_prev", "hour_close_prev"]
        ],
        on="timestamp",
        direction="backward",
    )
    out = pd.merge_asof(
        out.sort_values("timestamp"),
        df_4h.sort_values("timestamp")[["timestamp", "trend_4h_confirmed", "ema200_prev_closed"]],
        on="timestamp",
        direction="backward",
    )

    out = out.dropna(
        subset=[
            "atr20",
            "ema20",
            "high_16_prev",
            "low_16_prev",
            "liq_high_8h_prev",
            "liq_low_8h_prev",
            "trend_4h_confirmed",
            "ema200_prev_closed",
        ]
    ).reset_index(drop=True)
    return out


def _mark_to_market(capital: float, side: int, avg_entry: float, qty: float, price: float) -> float:
    if side == 0 or qty <= 0:
        return capital
    if side > 0:
        return capital + (price - avg_entry) * qty
    return capital + (avg_entry - price) * qty


def _close_position(capital: float, side: int, avg_entry: float, qty: float, price: float) -> float:
    if side == 0 or qty <= 0:
        return capital
    close_commission = qty * price * COMMISSION
    if side > 0:
        pnl = (price - avg_entry) * qty
    else:
        pnl = (avg_entry - price) * qty
    return capital + pnl - close_commission


def _find_last_opposite_candle(
    open_np: np.ndarray,
    close_np: np.ndarray,
    high_np: np.ndarray,
    low_np: np.ndarray,
    i: int,
    lookback: int,
    direction: int,
) -> tuple[float, float] | None:
    start = max(0, i - lookback)
    for j in range(i - 1, start - 1, -1):
        if direction > 0 and close_np[j] < open_np[j]:
            return float(low_np[j]), float(open_np[j])
        if direction < 0 and close_np[j] > open_np[j]:
            return float(open_np[j]), float(high_np[j])
    return None


def run_variant(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    archetype = str(cfg["archetype"])
    close = df["close"].to_numpy(dtype=float)
    open_ = df["open"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    atr20 = df["atr20"].to_numpy(dtype=float)
    ema20 = df["ema20"].to_numpy(dtype=float)
    trend = df["trend_4h_confirmed"].astype(str).to_numpy()
    timestamps = df["timestamp"].to_numpy()

    capital = INITIAL_CAPITAL
    side = 0
    avg_entry = 0.0
    qty = 0.0
    stop_price = np.nan
    target_price = np.nan
    bars_in_trade = 0
    last_order_idx = -10**9
    pending: dict | None = None

    rows: list[dict] = []
    stats = {
        "trades": 0,
        "long_entries": 0,
        "short_entries": 0,
        "stop_exits": 0,
        "target_exits": 0,
        "signal_exits": 0,
        "time_exits": 0,
        "setup_created": 0,
        "setup_triggered": 0,
        "setup_expired": 0,
    }

    for i in range(len(df)):
        price = float(close[i])
        cur_trend = str(trend[i])
        exit_reason = None
        exit_price = np.nan

        if side != 0:
            bars_in_trade += 1
            if side > 0:
                if low[i] <= stop_price:
                    exit_reason = "stop"
                    exit_price = float(stop_price)
                elif high[i] >= target_price:
                    exit_reason = "target"
                    exit_price = float(target_price)
                elif cur_trend != "bullish":
                    exit_reason = "signal"
                    exit_price = price
                elif bars_in_trade >= int(cfg["max_hold_bars"]):
                    exit_reason = "time"
                    exit_price = price
            else:
                if high[i] >= stop_price:
                    exit_reason = "stop"
                    exit_price = float(stop_price)
                elif low[i] <= target_price:
                    exit_reason = "target"
                    exit_price = float(target_price)
                elif cur_trend != "bearish":
                    exit_reason = "signal"
                    exit_price = price
                elif bars_in_trade >= int(cfg["max_hold_bars"]):
                    exit_reason = "time"
                    exit_price = price

            if exit_reason is not None:
                capital = _close_position(capital, side, avg_entry, qty, exit_price)
                side = 0
                avg_entry = 0.0
                qty = 0.0
                stop_price = np.nan
                target_price = np.nan
                bars_in_trade = 0
                last_order_idx = i
                stats["trades"] += 1
                if exit_reason == "stop":
                    stats["stop_exits"] += 1
                elif exit_reason == "target":
                    stats["target_exits"] += 1
                elif exit_reason == "time":
                    stats["time_exits"] += 1
                else:
                    stats["signal_exits"] += 1

        if pending is not None:
            expired = i > int(pending["expiry"])
            wrong_trend = (int(pending["dir"]) > 0 and cur_trend != "bullish") or (int(pending["dir"]) < 0 and cur_trend != "bearish")
            if expired or wrong_trend:
                pending = None
                stats["setup_expired"] += 1

        if side == 0 and i - last_order_idx >= int(cfg.get("cooldown_bars", 0)):
            if pending is not None:
                zone_low = float(pending["zone_low"])
                zone_high = float(pending["zone_high"])
                zone_mid = float(pending["zone_mid"])
                stop_ref = float(pending["stop_ref"])
                overlap = low[i] <= zone_high and high[i] >= zone_low
                if int(pending["dir"]) > 0 and cur_trend == "bullish" and overlap and price >= zone_mid:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0 and stop_ref < price:
                        capital -= open_qty * price * COMMISSION
                        side = 1
                        avg_entry = price
                        qty = open_qty
                        stop_price = stop_ref
                        target_price = price + (price - stop_ref) * float(cfg["target_r"])
                        bars_in_trade = 0
                        last_order_idx = i
                        stats["long_entries"] += 1
                        stats["setup_triggered"] += 1
                        pending = None
                elif int(pending["dir"]) < 0 and cur_trend == "bearish" and overlap and price <= zone_mid:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0 and stop_ref > price:
                        capital -= open_qty * price * COMMISSION
                        side = -1
                        avg_entry = price
                        qty = open_qty
                        stop_price = stop_ref
                        target_price = price - (stop_ref - price) * float(cfg["target_r"])
                        bars_in_trade = 0
                        last_order_idx = i
                        stats["short_entries"] += 1
                        stats["setup_triggered"] += 1
                        pending = None

        if side == 0 and i - last_order_idx >= int(cfg.get("cooldown_bars", 0)):
            if archetype == "sweep_reversal":
                liq_high = float(df.iloc[i]["liq_high_8h_prev"] if str(cfg["liq_window"]) == "8h" else df.iloc[i]["liq_high_24h_prev"])
                liq_low = float(df.iloc[i]["liq_low_8h_prev"] if str(cfg["liq_window"]) == "8h" else df.iloc[i]["liq_low_24h_prev"])
                body_ok = float(df.iloc[i]["body"]) >= float(cfg["body_atr_mult"]) * float(atr20[i])
                if cur_trend == "bullish" and low[i] < liq_low and price > liq_low and price > open_[i] and price > ema20[i] and body_ok:
                    stop_ref = min(low[i], liq_low) - float(cfg["stop_buffer_atr"]) * float(atr20[i])
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0 and stop_ref < price:
                        capital -= open_qty * price * COMMISSION
                        side = 1
                        avg_entry = price
                        qty = open_qty
                        stop_price = stop_ref
                        target_price = price + (price - stop_ref) * float(cfg["target_r"])
                        bars_in_trade = 0
                        last_order_idx = i
                        stats["long_entries"] += 1
                elif cur_trend == "bearish" and high[i] > liq_high and price < liq_high and price < open_[i] and price < ema20[i] and body_ok:
                    stop_ref = max(high[i], liq_high) + float(cfg["stop_buffer_atr"]) * float(atr20[i])
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0 and stop_ref > price:
                        capital -= open_qty * price * COMMISSION
                        side = -1
                        avg_entry = price
                        qty = open_qty
                        stop_price = stop_ref
                        target_price = price - (stop_ref - price) * float(cfg["target_r"])
                        bars_in_trade = 0
                        last_order_idx = i
                        stats["short_entries"] += 1

        if side == 0 and pending is None:
            body_ok = float(df.iloc[i]["body"]) >= float(cfg.get("displacement_atr_mult", 0.0)) * float(atr20[i])

            if archetype == "fvg_reclaim" and i >= 2:
                high_prev = float(df.iloc[i][f"high_{int(cfg['bos_window'])}_prev"])
                low_prev = float(df.iloc[i][f"low_{int(cfg['bos_window'])}_prev"])
                if cur_trend == "bullish" and body_ok and price > open_[i] and pd.notna(high_prev) and price > high_prev and low[i] > high[i - 2]:
                    zone_low = float(high[i - 2])
                    zone_high = float(low[i])
                    pending = {
                        "dir": 1,
                        "zone_low": zone_low,
                        "zone_high": zone_high,
                        "zone_mid": (zone_low + zone_high) / 2.0,
                        "stop_ref": zone_low - float(cfg["stop_buffer_atr"]) * float(atr20[i]),
                        "expiry": i + int(cfg["expiry_bars"]),
                    }
                    stats["setup_created"] += 1
                elif cur_trend == "bearish" and body_ok and price < open_[i] and pd.notna(low_prev) and price < low_prev and high[i] < low[i - 2]:
                    zone_low = float(high[i])
                    zone_high = float(low[i - 2])
                    pending = {
                        "dir": -1,
                        "zone_low": zone_low,
                        "zone_high": zone_high,
                        "zone_mid": (zone_low + zone_high) / 2.0,
                        "stop_ref": zone_high + float(cfg["stop_buffer_atr"]) * float(atr20[i]),
                        "expiry": i + int(cfg["expiry_bars"]),
                    }
                    stats["setup_created"] += 1

            elif archetype == "orderblock_reclaim":
                high_prev = float(df.iloc[i][f"high_{int(cfg['bos_window'])}_prev"])
                low_prev = float(df.iloc[i][f"low_{int(cfg['bos_window'])}_prev"])
                if cur_trend == "bullish" and body_ok and price > open_[i] and pd.notna(high_prev) and price > high_prev:
                    zone = _find_last_opposite_candle(open_, close, high, low, i, int(cfg["ob_lookback"]), 1)
                    if zone is not None:
                        zone_low, zone_high = zone
                        pending = {
                            "dir": 1,
                            "zone_low": zone_low,
                            "zone_high": zone_high,
                            "zone_mid": (zone_low + zone_high) / 2.0,
                            "stop_ref": zone_low - float(cfg["stop_buffer_atr"]) * float(atr20[i]),
                            "expiry": i + int(cfg["expiry_bars"]),
                        }
                        stats["setup_created"] += 1
                elif cur_trend == "bearish" and body_ok and price < open_[i] and pd.notna(low_prev) and price < low_prev:
                    zone = _find_last_opposite_candle(open_, close, high, low, i, int(cfg["ob_lookback"]), -1)
                    if zone is not None:
                        zone_low, zone_high = zone
                        pending = {
                            "dir": -1,
                            "zone_low": zone_low,
                            "zone_high": zone_high,
                            "zone_mid": (zone_low + zone_high) / 2.0,
                            "stop_ref": zone_high + float(cfg["stop_buffer_atr"]) * float(atr20[i]),
                            "expiry": i + int(cfg["expiry_bars"]),
                        }
                        stats["setup_created"] += 1

        equity = _mark_to_market(capital, side, avg_entry, qty, price)
        rows.append({"timestamp": timestamps[i], "equity": equity, "variant": str(cfg["variant"])})

    if pending is not None:
        stats["setup_expired"] += 1

    if side != 0 and len(df):
        last_price = float(close[-1])
        capital = _close_position(capital, side, avg_entry, qty, last_price)
        rows[-1]["equity"] = capital
        stats["trades"] += 1

    curve = pd.DataFrame(rows)
    return curve, stats


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_trades = axes

    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("82 Study: ICT/SMC-Inspired Archetypes")
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

    ax_trades.bar(metrics_df["variant"], metrics_df["trades"], color=[colors[v] for v in variants], alpha=0.85, label="Trades")
    ax_trades.set_ylabel("Trades")
    ax_trades.grid(True, axis="y", alpha=0.2)
    ax_trades.tick_params(axis="x", rotation=20)
    ax_trades_t = ax_trades.twinx()
    ax_trades_t.plot(metrics_df["variant"], metrics_df["calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Calmar")
    ax_trades_t.set_ylabel("Calmar")
    h1, l1 = ax_trades.get_legend_handles_labels()
    h2, l2 = ax_trades_t.get_legend_handles_labels()
    ax_trades.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    best_live = metrics_df[~metrics_df["variant"].str.startswith("reference_")].iloc[0]

    lines: list[str] = []
    lines.append("# Study 82: ICT/SMC-Inspired Archetypes")
    lines.append("")
    lines.append("## Scope")
    lines.append("- This study is not a canonical ICT/SMC implementation. It uses machine-testable proxies inspired by common SMC ideas.")
    lines.append("- Execution timeframe: `15m` bars rebuilt from `1m` data.")
    lines.append("- Context timeframes: `1h` liquidity pools and `4h` confirmed EMA200 hysteresis bias.")
    lines.append("- All entries are based on information available at the current completed bar; no future bars are read.")
    lines.append("")
    lines.append("## Archetypes")
    lines.append("- `smc_sweep8h_reversal_15m`: sweep of the previous 8h liquidity pool, reclaim, trade back in 4h bias direction.")
    lines.append("- `smc_sweep24h_reversal_15m`: same idea using a wider 24h liquidity pool.")
    lines.append("- `smc_fvg_reclaim_15m`: displacement + break of structure + fair value gap, then wait for gap reclaim.")
    lines.append("- `smc_orderblock_reclaim_15m`: displacement + break of structure, then revisit the last opposite candle zone as an order block proxy.")
    lines.append("- References are the current regime-hold case3 winners from study 80.")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | CAGR % | MDD % | Calmar | Final Equity | Trades | Setup Created | Setup Triggered |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{_fmt(row['final_equity'])} | {_fmt_count(row.get('trades', np.nan))} | {_fmt_count(row.get('setup_created', np.nan))} | {_fmt_count(row.get('setup_triggered', np.nan))} |"
        )
    lines.append("")
    lines.append("## Best Live Variant")
    lines.append(
        f"- `{best_live['variant']}`: CAGR `{_fmt(best_live['cagr_pct'])}%`, MDD `{_fmt(best_live['max_drawdown_pct'])}%`, Calmar `{_fmt(best_live['calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If a sweep-reversal variant wins, then the SMC idea that matters here is liquidity-taking plus reclaim, not continuation chasing.")
    lines.append("- If FVG or order-block reclaim wins, then delayed pullback entries after displacement are the more machine-tractable edge.")
    lines.append("- If none of the SMC-inspired variants beat the regime-hold references, then this concept remains ideation rather than portfolio-ready.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    m47 = load_module("study47_for_82", BASE_47_PATH)
    market = prepare_market(m47)

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    reference_curves = load_reference_curves()
    for variant, curve in reference_curves.items():
        stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL)
        rows.append({"variant": variant, **stats, "trades": np.nan, "setup_created": np.nan, "setup_triggered": np.nan})
        curves_out.append(curve.copy())
        curve_map[variant] = curve.copy()

    for cfg in VARIANTS:
        curve, run_stats = run_variant(market, cfg)
        stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL)
        row = {
            "variant": str(cfg["variant"]),
            **stats,
            **run_stats,
        }
        rows.append(row)
        curves_out.append(curve.copy())
        curve_map[str(cfg["variant"])] = curve.copy()

    metrics_df = pd.DataFrame(rows).sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curves_out, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df)
    save_report(metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    run()
