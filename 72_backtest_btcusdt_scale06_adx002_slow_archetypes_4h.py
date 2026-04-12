from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
REFERENCE_CURVES_CSV = Path("62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune_curves.csv")

OUT_BASE = "72_backtest_btcusdt_scale06_adx002_slow_archetypes_4h"
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
    {"variant": "regime_hold_dual", "mode": "live", "archetype": "regime_hold_dual", "entry_scale": 0.98, "stop_pct": 0.05},
    {"variant": "donchian_20_10_dual", "mode": "live", "archetype": "donchian_dual", "entry_scale": 0.98, "entry_window": 20, "exit_window": 10, "stop_pct": 0.05},
    {"variant": "ema_reclaim_dual", "mode": "live", "archetype": "ema_reclaim_dual", "entry_scale": 0.98, "stop_pct": 0.04, "trail_gap_pct": 0.05},
    {"variant": "rsi_regime_dual", "mode": "live", "archetype": "rsi_regime_dual", "entry_scale": 0.98, "stop_pct": 0.04},
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


def prepare_4h_market(m47, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
    _, df_4h = m47.load_data_no_filter()
    out = df_4h[(df_4h.index >= start_ts.floor("4h") - pd.Timedelta(days=120)) & (df_4h.index <= end_ts.ceil("4h"))].copy()
    out["ema200_closed"] = out["close"].ewm(span=m47.EMA_PERIOD, adjust=False).mean()
    out["ema200_prev_closed"] = out["ema200_closed"].shift(1)
    out["trend_4h_hyst"] = m47.LiveParityNoLookahead._compute_hysteresis_state(
        out["close"], out["ema200_prev_closed"], m47.HYSTERESIS_BAND
    )
    out["trend_4h_confirmed"] = out["trend_4h_hyst"].shift(1)
    out["ema20"] = out["close"].ewm(span=20, adjust=False).mean()

    delta = out["close"].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean().replace(0.0, np.nan)
    out["rsi14"] = 100.0 - (100.0 / (1.0 + rs))

    for window in [3, 10, 20]:
        out[f"high_{window}_prev"] = out["high"].rolling(window).max().shift(1)
        out[f"low_{window}_prev"] = out["low"].rolling(window).min().shift(1)

    out = out[(out.index >= start_ts) & (out.index <= end_ts)].copy()
    out = out.reset_index().rename(columns={"index": "timestamp"})
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
    archetype = str(cfg["archetype"])
    close = df["close"].to_numpy(dtype=float)
    ema20 = df["ema20"].to_numpy(dtype=float)
    rsi14 = df["rsi14"].to_numpy(dtype=float)
    trend = df["trend_4h_confirmed"].fillna("").to_numpy()
    timestamps = df["timestamp"].to_numpy()

    capital = INITIAL_CAPITAL
    side = 0
    avg_entry = 0.0
    qty = 0.0
    best_price = np.nan
    long_setup = False
    short_setup = False

    rows: list[dict] = []
    stats = {"trades": 0, "long_entries": 0, "short_entries": 0, "stop_exits": 0, "signal_exits": 0, "trail_exits": 0}

    for i in range(len(df)):
        price = float(close[i])
        cur_trend = str(trend[i])
        if pd.isna(price) or pd.isna(df.iloc[i]["ema200_prev_closed"]):
            rows.append({"timestamp": timestamps[i], "equity": capital})
            continue

        if side != 0:
            exit_reason = None
            if side > 0:
                best_price = price if np.isnan(best_price) else max(best_price, price)
                if archetype == "regime_hold_dual":
                    if cur_trend == "bearish":
                        exit_reason = "signal"
                    elif price <= avg_entry * (1.0 - float(cfg["stop_pct"])):
                        exit_reason = "stop"
                elif archetype == "donchian_dual":
                    exit_low = float(df.iloc[i][f"low_{int(cfg['exit_window'])}_prev"])
                    if cur_trend != "bullish" or price < exit_low:
                        exit_reason = "signal"
                    elif price <= avg_entry * (1.0 - float(cfg["stop_pct"])):
                        exit_reason = "stop"
                elif archetype == "ema_reclaim_dual":
                    if cur_trend != "bullish" or price < ema20[i]:
                        exit_reason = "signal"
                    elif price <= avg_entry * (1.0 - float(cfg["stop_pct"])):
                        exit_reason = "stop"
                    elif best_price >= avg_entry * 1.05 and price <= best_price * (1.0 - float(cfg["trail_gap_pct"])):
                        exit_reason = "trail"
                elif archetype == "rsi_regime_dual":
                    if cur_trend != "bullish" or rsi14[i] < 50.0:
                        exit_reason = "signal"
                    elif price <= avg_entry * (1.0 - float(cfg["stop_pct"])):
                        exit_reason = "stop"
            else:
                best_price = price if np.isnan(best_price) else min(best_price, price)
                if archetype == "regime_hold_dual":
                    if cur_trend == "bullish":
                        exit_reason = "signal"
                    elif price >= avg_entry * (1.0 + float(cfg["stop_pct"])):
                        exit_reason = "stop"
                elif archetype == "donchian_dual":
                    exit_high = float(df.iloc[i][f"high_{int(cfg['exit_window'])}_prev"])
                    if cur_trend != "bearish" or price > exit_high:
                        exit_reason = "signal"
                    elif price >= avg_entry * (1.0 + float(cfg["stop_pct"])):
                        exit_reason = "stop"
                elif archetype == "ema_reclaim_dual":
                    if cur_trend != "bearish" or price > ema20[i]:
                        exit_reason = "signal"
                    elif price >= avg_entry * (1.0 + float(cfg["stop_pct"])):
                        exit_reason = "stop"
                    elif best_price <= avg_entry * 0.95 and price >= best_price * (1.0 + float(cfg["trail_gap_pct"])):
                        exit_reason = "trail"
                elif archetype == "rsi_regime_dual":
                    if cur_trend != "bearish" or rsi14[i] > 50.0:
                        exit_reason = "signal"
                    elif price >= avg_entry * (1.0 + float(cfg["stop_pct"])):
                        exit_reason = "stop"

            if exit_reason is not None:
                capital = _close_position(capital, side, avg_entry, qty, price)
                side = 0
                avg_entry = 0.0
                qty = 0.0
                best_price = np.nan
                stats["trades"] += 1
                if exit_reason == "stop":
                    stats["stop_exits"] += 1
                elif exit_reason == "trail":
                    stats["trail_exits"] += 1
                else:
                    stats["signal_exits"] += 1

        if side == 0:
            if archetype == "regime_hold_dual":
                if cur_trend == "bullish":
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    capital -= open_qty * price * COMMISSION
                    side = 1
                    avg_entry = price
                    qty = open_qty
                    best_price = price
                    stats["long_entries"] += 1
                elif cur_trend == "bearish":
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    capital -= open_qty * price * COMMISSION
                    side = -1
                    avg_entry = price
                    qty = open_qty
                    best_price = price
                    stats["short_entries"] += 1
            elif archetype == "donchian_dual":
                high_prev = float(df.iloc[i][f"high_{int(cfg['entry_window'])}_prev"])
                low_prev = float(df.iloc[i][f"low_{int(cfg['entry_window'])}_prev"])
                if cur_trend == "bullish" and pd.notna(high_prev) and price > high_prev:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    capital -= open_qty * price * COMMISSION
                    side = 1
                    avg_entry = price
                    qty = open_qty
                    best_price = price
                    stats["long_entries"] += 1
                elif cur_trend == "bearish" and pd.notna(low_prev) and price < low_prev:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    capital -= open_qty * price * COMMISSION
                    side = -1
                    avg_entry = price
                    qty = open_qty
                    best_price = price
                    stats["short_entries"] += 1
            elif archetype == "ema_reclaim_dual":
                if cur_trend == "bullish" and price < ema20[i]:
                    long_setup = True
                if cur_trend == "bearish" and price > ema20[i]:
                    short_setup = True
                if long_setup and cur_trend == "bullish" and price > ema20[i] and price > float(df.iloc[i]["high_3_prev"]):
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    capital -= open_qty * price * COMMISSION
                    side = 1
                    avg_entry = price
                    qty = open_qty
                    best_price = price
                    long_setup = False
                    short_setup = False
                    stats["long_entries"] += 1
                elif short_setup and cur_trend == "bearish" and price < ema20[i] and price < float(df.iloc[i]["low_3_prev"]):
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    capital -= open_qty * price * COMMISSION
                    side = -1
                    avg_entry = price
                    qty = open_qty
                    best_price = price
                    long_setup = False
                    short_setup = False
                    stats["short_entries"] += 1
                if cur_trend == "bearish":
                    long_setup = False
                if cur_trend == "bullish":
                    short_setup = False
            elif archetype == "rsi_regime_dual":
                prev_rsi = float(rsi14[i - 1]) if i > 0 and pd.notna(rsi14[i - 1]) else np.nan
                if cur_trend == "bullish" and pd.notna(prev_rsi) and prev_rsi <= 55.0 and rsi14[i] > 55.0:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    capital -= open_qty * price * COMMISSION
                    side = 1
                    avg_entry = price
                    qty = open_qty
                    best_price = price
                    stats["long_entries"] += 1
                elif cur_trend == "bearish" and pd.notna(prev_rsi) and prev_rsi >= 45.0 and rsi14[i] < 45.0:
                    open_qty = (capital / price) * float(cfg["entry_scale"])
                    capital -= open_qty * price * COMMISSION
                    side = -1
                    avg_entry = price
                    qty = open_qty
                    best_price = price
                    stats["short_entries"] += 1

        rows.append({"timestamp": timestamps[i], "equity": _mark_to_market(capital, side, avg_entry, qty, price)})

    if side != 0 and len(df):
        capital = _close_position(capital, side, avg_entry, qty, float(close[-1]))
        rows[-1]["equity"] = capital
        stats["trades"] += 1

    curve = pd.DataFrame(rows)
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
    ax_eq.set_title("72 Study: Slow 4H Alternative Archetypes")
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
    lines.append("# Study 72: Slow 4H Alternative Archetypes")
    lines.append("")
    lines.append("## Purpose")
    lines.append("- This study tests slower, lower-turnover, 4h-bar alternative mindsets.")
    lines.append("- Families: `regime hold`, `donchian breakout`, `EMA reclaim`, `RSI regime momentum`.")
    lines.append("- Signals use only closed 4h bars and confirmed regime state.")
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
    lines.append("- If slower archetypes beat the fast 5m variants, then the alternate mindset is more plausible at swing horizon than intraday.")
    lines.append("- If they still fail badly versus `reference_case1`, then the current edge is likely coming more from the existing research stack than from generic trend systems.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    ref_case1, ref_case2 = load_reference_curves()
    m47 = load_module("study47_for_72", BASE_47_PATH)
    market = prepare_4h_market(m47, pd.Timestamp(ref_case1["timestamp"].iloc[0]), pd.Timestamp(ref_case1["timestamp"].iloc[-1]))

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        variant = str(cfg["variant"])
        if cfg["mode"] == "reference":
            curve = ref_case1.copy() if variant == "reference_case1" else ref_case2.copy()
            stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL)
            run_stats = {"trades": np.nan, "long_entries": np.nan, "short_entries": np.nan, "stop_exits": np.nan, "signal_exits": np.nan, "trail_exits": np.nan}
        else:
            curve, run_stats = run_archetype(market, cfg)
            stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL)
        curve["variant"] = variant
        rows.append({"variant": variant, "mode": cfg["mode"], **stats, **run_stats})
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
