from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
REFERENCE_CURVES_CSV = Path("62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune_curves.csv")

OUT_BASE = "71_backtest_btcusdt_scale06_adx002_alt_mindset_archetypes"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

INITIAL_CAPITAL = 1000.0
COMMISSION = 0.0004
CASE_VARIANT = "shallow6_else2bull"

VARIANTS = [
    {"variant": "reference_case1", "mode": "reference"},
    {"variant": "reference_case2", "mode": "reference"},
    {
        "variant": "turtle_dual_144_48",
        "mode": "live",
        "archetype": "turtle_dual",
        "entry_scale": 0.95,
        "entry_window": 144,
        "exit_window": 48,
        "stop_pct": 0.018,
        "cooldown_bars": 6,
    },
    {
        "variant": "breakout_long_96",
        "mode": "live",
        "archetype": "bull_breakout_long",
        "entry_scale": 0.95,
        "entry_window": 96,
        "stop_pct": 0.015,
        "trail_arm_pct": 0.020,
        "trail_gap_pct": 0.012,
        "cooldown_bars": 6,
    },
    {
        "variant": "pullback_reclaim_dual",
        "mode": "live",
        "archetype": "pullback_reclaim_dual",
        "entry_scale": 0.95,
        "flush_atr_mult": 1.0,
        "reclaim_window": 12,
        "stop_pct": 0.012,
        "trail_arm_pct": 0.018,
        "trail_gap_pct": 0.010,
        "cooldown_bars": 6,
    },
    {
        "variant": "compression_breakout_dual",
        "mode": "live",
        "archetype": "compression_breakout_dual",
        "entry_scale": 0.95,
        "entry_window": 48,
        "compression_ratio": 0.70,
        "stop_pct": 0.013,
        "trail_arm_pct": 0.020,
        "trail_gap_pct": 0.010,
        "cooldown_bars": 6,
    },
    {
        "variant": "hard_stop_meanrev_dual",
        "mode": "live",
        "archetype": "hard_stop_meanrev_dual",
        "entry_scale": 0.90,
        "stop_pct": 0.009,
        "take_profit_pct": 0.012,
        "max_hold_bars": 48,
        "cooldown_bars": 6,
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


def load_reference_curves() -> tuple[pd.DataFrame, pd.DataFrame]:
    curves = pd.read_csv(REFERENCE_CURVES_CSV, parse_dates=["timestamp"])
    ref = curves[curves["variant"] == CASE_VARIANT].copy()
    if ref.empty:
        raise ValueError(f"missing reference variant: {CASE_VARIANT}")
    ref = ref.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)
    case1 = ref[["timestamp", "equity_case1"]].rename(columns={"equity_case1": "equity"}).copy()
    case2 = ref[["timestamp", "equity_case2"]].rename(columns={"equity_case2": "equity"}).copy()
    return case1, case2


def prepare_market(m47, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
    df_1m, df_4h = m47.load_data_no_filter()
    df_1m = df_1m[(df_1m.index >= start_ts.floor("1min")) & (df_1m.index <= end_ts.ceil("1min"))].copy()
    df_4h = df_4h[(df_4h.index >= start_ts.floor("4h") - pd.Timedelta(days=90)) & (df_4h.index <= end_ts.ceil("4h"))].copy()

    df_5m = df_1m.resample("5min", label="right", closed="right").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    df_4h["ema200_closed"] = df_4h["close"].ewm(span=m47.EMA_PERIOD, adjust=False).mean()
    df_4h["ema200_prev_closed"] = df_4h["ema200_closed"].shift(1)
    df_4h["trend_4h_hyst"] = m47.LiveParityNoLookahead._compute_hysteresis_state(
        df_4h["close"], df_4h["ema200_prev_closed"], m47.HYSTERESIS_BAND
    )
    df_4h["trend_4h_confirmed"] = df_4h["trend_4h_hyst"].shift(1)

    out = df_5m.copy()
    out["timestamp"] = out.index
    out["bucket_4h"] = out["timestamp"].dt.floor("4h")
    out = out.merge(df_4h[["trend_4h_confirmed"]], left_on="bucket_4h", right_index=True, how="left")
    out["trend_4h_confirmed"] = out["trend_4h_confirmed"].ffill()

    tr = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - out["close"].shift(1)).abs(),
            (out["low"] - out["close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr20"] = tr.rolling(20).mean()
    out["atr100"] = tr.rolling(100).mean()
    out["ema20"] = out["close"].ewm(span=20, adjust=False).mean()
    out["ema60"] = out["close"].ewm(span=60, adjust=False).mean()

    delta = out["close"].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    rs = gain.rolling(6).mean() / loss.rolling(6).mean().replace(0.0, np.nan)
    out["rsi6"] = 100.0 - (100.0 / (1.0 + rs))

    for window in [12, 48, 96, 144]:
        out[f"high_{window}_prev"] = out["high"].rolling(window).max().shift(1)
        out[f"low_{window}_prev"] = out["low"].rolling(window).min().shift(1)

    out = out[(out["timestamp"] >= start_ts) & (out["timestamp"] <= end_ts)].copy()
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


def run_archetype(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    variant = str(cfg["variant"])
    archetype = str(cfg["archetype"])
    close = df["close"].to_numpy(dtype=float)
    ema20 = df["ema20"].to_numpy(dtype=float)
    ema60 = df["ema60"].to_numpy(dtype=float)
    atr20 = df["atr20"].to_numpy(dtype=float)
    atr100 = df["atr100"].to_numpy(dtype=float)
    rsi6 = df["rsi6"].to_numpy(dtype=float)
    trend = df["trend_4h_confirmed"].fillna("").to_numpy()
    timestamps = df["timestamp"].to_numpy()

    capital = INITIAL_CAPITAL
    side = 0
    avg_entry = 0.0
    qty = 0.0
    last_order_idx = -10**9
    best_price = np.nan
    bars_in_trade = 0
    long_setup = False
    short_setup = False

    rows: list[dict] = []
    stats = {
        "trades": 0,
        "long_entries": 0,
        "short_entries": 0,
        "stop_exits": 0,
        "trail_exits": 0,
        "signal_exits": 0,
        "time_exits": 0,
    }

    for i in range(len(df)):
        price = float(close[i])
        cur_trend = str(trend[i])

        if pd.isna(price) or pd.isna(ema60[i]) or pd.isna(atr20[i]):
            rows.append({"timestamp": timestamps[i], "equity": capital})
            continue

        if side != 0:
            bars_in_trade += 1
            exit_reason = None

            if side > 0:
                best_price = price if np.isnan(best_price) else max(best_price, price)
                if archetype == "turtle_dual":
                    exit_low = float(df.iloc[i][f"low_{int(cfg['exit_window'])}_prev"])
                    if cur_trend != "bullish" or price < exit_low:
                        exit_reason = "signal"
                    elif price <= avg_entry * (1.0 - float(cfg["stop_pct"])):
                        exit_reason = "stop"
                elif archetype in ("bull_breakout_long", "pullback_reclaim_dual", "compression_breakout_dual"):
                    trail_armed = best_price >= avg_entry * (1.0 + float(cfg.get("trail_arm_pct", 0.0)))
                    if cur_trend == "bearish":
                        exit_reason = "signal"
                    elif price <= avg_entry * (1.0 - float(cfg["stop_pct"])):
                        exit_reason = "stop"
                    elif trail_armed and price <= best_price * (1.0 - float(cfg.get("trail_gap_pct", 0.0))):
                        exit_reason = "trail"
                elif archetype == "hard_stop_meanrev_dual":
                    if price <= avg_entry * (1.0 - float(cfg["stop_pct"])):
                        exit_reason = "stop"
                    elif price >= avg_entry * (1.0 + float(cfg["take_profit_pct"])):
                        exit_reason = "signal"
                    elif bars_in_trade >= int(cfg["max_hold_bars"]):
                        exit_reason = "time"
            else:
                best_price = price if np.isnan(best_price) else min(best_price, price)
                if archetype == "turtle_dual":
                    exit_high = float(df.iloc[i][f"high_{int(cfg['exit_window'])}_prev"])
                    if cur_trend != "bearish" or price > exit_high:
                        exit_reason = "signal"
                    elif price >= avg_entry * (1.0 + float(cfg["stop_pct"])):
                        exit_reason = "stop"
                elif archetype in ("pullback_reclaim_dual", "compression_breakout_dual"):
                    trail_armed = best_price <= avg_entry * (1.0 - float(cfg.get("trail_arm_pct", 0.0)))
                    if cur_trend == "bullish":
                        exit_reason = "signal"
                    elif price >= avg_entry * (1.0 + float(cfg["stop_pct"])):
                        exit_reason = "stop"
                    elif trail_armed and price >= best_price * (1.0 + float(cfg.get("trail_gap_pct", 0.0))):
                        exit_reason = "trail"
                elif archetype == "hard_stop_meanrev_dual":
                    if price >= avg_entry * (1.0 + float(cfg["stop_pct"])):
                        exit_reason = "stop"
                    elif price <= avg_entry * (1.0 - float(cfg["take_profit_pct"])):
                        exit_reason = "signal"
                    elif bars_in_trade >= int(cfg["max_hold_bars"]):
                        exit_reason = "time"

            if exit_reason is not None:
                capital = _close_position(capital, side, avg_entry, qty, price)
                side = 0
                avg_entry = 0.0
                qty = 0.0
                best_price = np.nan
                bars_in_trade = 0
                last_order_idx = i
                stats["trades"] += 1
                if exit_reason == "stop":
                    stats["stop_exits"] += 1
                elif exit_reason == "trail":
                    stats["trail_exits"] += 1
                elif exit_reason == "time":
                    stats["time_exits"] += 1
                else:
                    stats["signal_exits"] += 1

        if side == 0 and i - last_order_idx >= int(cfg.get("cooldown_bars", 0)):
            if archetype == "turtle_dual":
                high_prev = float(df.iloc[i][f"high_{int(cfg['entry_window'])}_prev"])
                low_prev = float(df.iloc[i][f"low_{int(cfg['entry_window'])}_prev"])
                if cur_trend == "bullish" and pd.notna(high_prev) and price > high_prev:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0:
                        capital -= open_qty * price * COMMISSION
                        side = 1
                        avg_entry = price
                        qty = open_qty
                        best_price = price
                        bars_in_trade = 0
                        last_order_idx = i
                        stats["long_entries"] += 1
                elif cur_trend == "bearish" and pd.notna(low_prev) and price < low_prev:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0:
                        capital -= open_qty * price * COMMISSION
                        side = -1
                        avg_entry = price
                        qty = open_qty
                        best_price = price
                        bars_in_trade = 0
                        last_order_idx = i
                        stats["short_entries"] += 1
            elif archetype == "bull_breakout_long":
                high_prev = float(df.iloc[i][f"high_{int(cfg['entry_window'])}_prev"])
                if cur_trend == "bullish" and pd.notna(high_prev) and price > high_prev and price > ema20[i] > ema60[i]:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0:
                        capital -= open_qty * price * COMMISSION
                        side = 1
                        avg_entry = price
                        qty = open_qty
                        best_price = price
                        bars_in_trade = 0
                        last_order_idx = i
                        stats["long_entries"] += 1
            elif archetype == "pullback_reclaim_dual":
                if cur_trend == "bullish" and price < ema20[i] - float(cfg["flush_atr_mult"]) * atr20[i]:
                    long_setup = True
                if cur_trend == "bearish" and price > ema20[i] + float(cfg["flush_atr_mult"]) * atr20[i]:
                    short_setup = True

                high_prev = float(df.iloc[i][f"high_{int(cfg['reclaim_window'])}_prev"])
                low_prev = float(df.iloc[i][f"low_{int(cfg['reclaim_window'])}_prev"])
                if long_setup and cur_trend == "bullish" and pd.notna(high_prev) and price > ema20[i] and price > high_prev:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0:
                        capital -= open_qty * price * COMMISSION
                        side = 1
                        avg_entry = price
                        qty = open_qty
                        best_price = price
                        bars_in_trade = 0
                        last_order_idx = i
                        long_setup = False
                        short_setup = False
                        stats["long_entries"] += 1
                elif short_setup and cur_trend == "bearish" and pd.notna(low_prev) and price < ema20[i] and price < low_prev:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0:
                        capital -= open_qty * price * COMMISSION
                        side = -1
                        avg_entry = price
                        qty = open_qty
                        best_price = price
                        bars_in_trade = 0
                        last_order_idx = i
                        long_setup = False
                        short_setup = False
                        stats["short_entries"] += 1
                if cur_trend == "bearish":
                    long_setup = False
                if cur_trend == "bullish":
                    short_setup = False
            elif archetype == "compression_breakout_dual":
                compression = pd.notna(atr100[i]) and atr20[i] <= atr100[i] * float(cfg["compression_ratio"])
                high_prev = float(df.iloc[i][f"high_{int(cfg['entry_window'])}_prev"])
                low_prev = float(df.iloc[i][f"low_{int(cfg['entry_window'])}_prev"])
                if compression and cur_trend == "bullish" and pd.notna(high_prev) and price > high_prev:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0:
                        capital -= open_qty * price * COMMISSION
                        side = 1
                        avg_entry = price
                        qty = open_qty
                        best_price = price
                        bars_in_trade = 0
                        last_order_idx = i
                        stats["long_entries"] += 1
                elif compression and cur_trend == "bearish" and pd.notna(low_prev) and price < low_prev:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0:
                        capital -= open_qty * price * COMMISSION
                        side = -1
                        avg_entry = price
                        qty = open_qty
                        best_price = price
                        bars_in_trade = 0
                        last_order_idx = i
                        stats["short_entries"] += 1
            elif archetype == "hard_stop_meanrev_dual":
                if cur_trend == "bullish" and price > ema60[i] and rsi6[i] <= 10.0:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0:
                        capital -= open_qty * price * COMMISSION
                        side = 1
                        avg_entry = price
                        qty = open_qty
                        best_price = price
                        bars_in_trade = 0
                        last_order_idx = i
                        stats["long_entries"] += 1
                elif cur_trend == "bearish" and price < ema60[i] and rsi6[i] >= 90.0:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    if open_qty > 0:
                        capital -= open_qty * price * COMMISSION
                        side = -1
                        avg_entry = price
                        qty = open_qty
                        best_price = price
                        bars_in_trade = 0
                        last_order_idx = i
                        stats["short_entries"] += 1

        equity = _mark_to_market(capital, side, avg_entry, qty, price)
        rows.append({"timestamp": timestamps[i], "equity": equity})

    if side != 0 and len(df):
        last_price = float(close[-1])
        capital = _close_position(capital, side, avg_entry, qty, last_price)
        rows[-1]["equity"] = capital
        stats["trades"] += 1

    curve = pd.DataFrame(rows)
    curve["variant"] = variant
    return curve, stats


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_mdd = axes

    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("71 Study: Alternative Strategy Mindsets")
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

    ax_mdd.bar(metrics_df["variant"], metrics_df["trades"], color=[colors[v] for v in variants], alpha=0.85, label="Trades")
    ax_mdd.set_ylabel("Trades")
    ax_mdd.grid(True, axis="y", alpha=0.2)
    ax_mdd.tick_params(axis="x", rotation=20)
    ax_mdd_t = ax_mdd.twinx()
    ax_mdd_t.plot(metrics_df["variant"], metrics_df["calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Calmar")
    ax_mdd_t.set_ylabel("Calmar")
    h1, l1 = ax_mdd.get_legend_handles_labels()
    h2, l2 = ax_mdd_t.get_legend_handles_labels()
    ax_mdd.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    best_live = metrics_df[metrics_df["mode"] == "live"].iloc[0]

    lines: list[str] = []
    lines.append("# Study 71: Alternative Strategy Mindsets")
    lines.append("")
    lines.append("## Purpose")
    lines.append("- This study intentionally avoids the `inventory averaging + hedge management` mindset.")
    lines.append("- Tested families are: `turtle trend-follow`, `bull breakout`, `pullback then reclaim`, `compression breakout`, and `hard-stop mean reversion`.")
    lines.append("- All entries use only closed-bar information; breakout levels are shifted by one bar, and 4h regime uses confirmed hysteresis state.")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | CAGR % | MDD % | Calmar | Final Equity | Trades | Longs | Shorts |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{_fmt(row['final_equity'])} | {_fmt_count(row['trades'])} | {_fmt_count(row['long_entries'])} | {_fmt_count(row['short_entries'])} |"
        )
    lines.append("")
    lines.append("## Best New Archetype")
    lines.append(
        f"- `{best_live['variant']}`: CAGR `{_fmt(best_live['cagr_pct'])}%`, MDD `{_fmt(best_live['max_drawdown_pct'])}%`, Calmar `{_fmt(best_live['calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If a live archetype beats `reference_case2`, it is a plausible replacement candidate for the current second sleeve.")
    lines.append("- If a live archetype approaches `reference_case1` with much lower MDD, it is a candidate for a fundamentally different primary engine.")
    lines.append("- This study is about identifying promising mindsets first, not yet about perfect parameter tuning.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    ref_case1, ref_case2 = load_reference_curves()
    m47 = load_module("study47_for_71", BASE_47_PATH)
    market = prepare_market(m47, pd.Timestamp(ref_case1["timestamp"].iloc[0]), pd.Timestamp(ref_case1["timestamp"].iloc[-1]))

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        variant = str(cfg["variant"])
        if cfg["mode"] == "reference":
            curve = ref_case1.copy() if variant == "reference_case1" else ref_case2.copy()
            curve["variant"] = variant
            stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL)
            run_stats = {
                "trades": np.nan,
                "long_entries": np.nan,
                "short_entries": np.nan,
                "stop_exits": np.nan,
                "trail_exits": np.nan,
                "signal_exits": np.nan,
                "time_exits": np.nan,
            }
        else:
            curve, run_stats = run_archetype(market, cfg)
            stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL)

        row = {"variant": variant, "mode": cfg["mode"], **stats, **run_stats}
        rows.append(row)
        curves_out.append(curve)
        curve_map[variant] = curve.copy()

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
