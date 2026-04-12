from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
BASE_76_PATH = Path("76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py")
BASE_82_PATH = Path("82_backtest_btcusdt_scale06_adx002_ict_smc_archetypes.py")
REFERENCE_80_CURVES_CSV = Path("80_backtest_btcusdt_scale06_adx002_regime_hold_short_tp_tune_curves.csv")
REFERENCE_83_CURVES_CSV = Path("83_backtest_btcusdt_scale06_adx002_smc_sweep_filter_regime_hold_curves.csv")

OUT_BASE = "84_backtest_btcusdt_scale06_adx002_smc_short_gate_tune"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

LEVERAGE = 2.0


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


def build_variants() -> list[dict]:
    variants: list[dict] = [
        {"variant": "reference_shorttp15_2x", "mode": "reference", "source": "80", "source_variant": "short_tp15_lock_2x"},
        {"variant": "reference_short_gate24h_shorttp15_2x", "mode": "reference", "source": "83", "source_variant": "short_gate24h_shorttp15_2x"},
        {"variant": "base15m_shorttp15_2x", "mode": "live", "liq_hours": 0, "gate_bars": 0, "body_atr_mult": 0.0, "tp_return_pct": 15.0},
    ]

    for liq_hours in [12, 24, 36]:
        for gate_bars in [4, 8, 12]:
            for tp_return_pct in [10.0, 15.0, 20.0]:
                variants.append(
                    {
                        "variant": f"short_gate_{liq_hours}h_g{gate_bars}_tp{int(tp_return_pct)}",
                        "mode": "live",
                        "liq_hours": liq_hours,
                        "gate_bars": gate_bars,
                        "body_atr_mult": 0.25,
                        "tp_return_pct": tp_return_pct,
                    }
                )

    for body_atr_mult in [0.10, 0.20, 0.25, 0.35, 0.50]:
        variants.append(
            {
                "variant": f"short_gate_24h_g8_tp15_body{int(round(body_atr_mult * 100)):02d}",
                "mode": "live",
                "liq_hours": 24,
                "gate_bars": 8,
                "body_atr_mult": body_atr_mult,
                "tp_return_pct": 15.0,
            }
        )
    return variants


def load_reference_curves() -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}

    curves80 = pd.read_csv(REFERENCE_80_CURVES_CSV, parse_dates=["timestamp"])
    ref80 = curves80[curves80["variant"] == "short_tp15_lock_2x"].copy()
    if not ref80.empty:
        ref80 = ref80.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
        ref80 = ref80[["timestamp", "equity"]].copy()
        ref80["variant"] = "reference_shorttp15_2x"
        out["reference_shorttp15_2x"] = ref80

    curves83 = pd.read_csv(REFERENCE_83_CURVES_CSV, parse_dates=["timestamp"])
    ref83 = curves83[curves83["variant"] == "short_gate24h_shorttp15_2x"].copy()
    if not ref83.empty:
        ref83 = ref83.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
        ref83 = ref83[["timestamp", "equity"]].copy()
        ref83["variant"] = "reference_short_gate24h_shorttp15_2x"
        out["reference_short_gate24h_shorttp15_2x"] = ref83

    return out


def prepare_market_extended(m47) -> pd.DataFrame:
    df_1m = pd.read_pickle(s82.DATA_1M_PATH).copy().sort_index()
    if not isinstance(df_1m.index, pd.DatetimeIndex):
        df_1m.index = pd.to_datetime(df_1m.index)

    df_15m = s82._resample_ohlc(df_1m, "15min")
    df_1h = s82._resample_ohlc(df_1m, "1h")
    df_4h = s82._resample_ohlc(df_1m, "4h")

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


def run_live_variant(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    liq_hours = int(cfg["liq_hours"])
    gate_bars = int(cfg["gate_bars"])
    body_atr_mult = float(cfg["body_atr_mult"])
    tp_threshold = float(cfg["tp_return_pct"]) / 100.0

    timestamps = df["timestamp"].to_numpy()
    open_np = df["open"].to_numpy(dtype=float)
    high_np = df["high"].to_numpy(dtype=float)
    low_np = df["low"].to_numpy(dtype=float)
    close_np = df["close"].to_numpy(dtype=float)
    atr20 = df["atr20"].to_numpy(dtype=float)
    ema20 = df["ema20"].to_numpy(dtype=float)
    trend = df["trend_4h_confirmed"].astype(str).to_numpy()
    body = df["body"].to_numpy(dtype=float)
    liq_high = df[f"liq_high_{liq_hours}h_prev"].to_numpy(dtype=float) if liq_hours > 0 else np.full(len(df), np.nan)

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
        "survived_to_end": 1,
    }
    first_liq_ts = None

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

        if liq_hours > 0:
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
            liq_price = s76._liq_price(entry, LEVERAGE, side)
            stop_price = entry * (1.0 - s76.STOP_PCT) if side > 0 else entry * (1.0 + s76.STOP_PCT)

            if side > 0 and LEVERAGE > 1.0 and price_low <= liq_price:
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
            elif side < 0 and LEVERAGE > 1.0 and price_high >= liq_price:
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
                side = 0
                entry_wallet = np.nan
                stats["trades"] += 1
                stats["signal_exits"] += 1

            if desired_side != 0 and wallet > 0:
                allow_entry = True
                if desired_side < 0 and liq_hours > 0:
                    allow_entry = i <= short_gate_until and price_close < ema20[i]
                if allow_entry:
                    reserve, margin, qty, entry = s76._open_position(wallet, price_close, LEVERAGE, desired_side)
                    wallet = reserve + margin
                    side = desired_side
                    entry_wallet = wallet
                    if desired_side > 0:
                        stats["long_entries"] += 1
                    else:
                        stats["short_entries"] += 1
                        if liq_hours > 0:
                            stats["gated_entries"] += 1

        equity = wallet if side == 0 else s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
        rows.append(
            {
                "timestamp": timestamps[i],
                "equity": equity,
                "variant": str(cfg["variant"]),
            }
        )

    if side != 0 and len(df):
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close_np[-1]), side)
        rows[-1]["equity"] = wallet
        stats["trades"] += 1

    curve = pd.DataFrame(rows)
    stats["first_liquidation_ts"] = first_liq_ts
    return curve, stats


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_tp = axes

    cmap = plt.get_cmap("tab20")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 20) for i, v in enumerate(variants)}

    for variant in variants[:14]:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(s76.INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("84 Study: Short-Side Sweep Gate Tuning")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    top = metrics_df.head(12)
    ax_cagr.bar(top["variant"], top["cagr_pct"], color=[colors[v] for v in top["variant"]], alpha=0.85, label="CAGR %")
    ax_cagr.set_ylabel("CAGR %")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr.tick_params(axis="x", rotation=20)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(top["variant"], top["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_cagr_t.set_ylabel("MDD %")
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_tp.bar(top["variant"], top["tp_exits"].fillna(0.0), color=[colors[v] for v in top["variant"]], alpha=0.85, label="TP Exits")
    ax_tp.set_ylabel("TP Exits")
    ax_tp.grid(True, axis="y", alpha=0.2)
    ax_tp.tick_params(axis="x", rotation=20)
    ax_tp_t = ax_tp.twinx()
    ax_tp_t.plot(top["variant"], top["calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Calmar")
    ax_tp_t.set_ylabel("Calmar")
    h1, l1 = ax_tp.get_legend_handles_labels()
    h2, l2 = ax_tp_t.get_legend_handles_labels()
    ax_tp.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    best_live = metrics_df[~metrics_df["variant"].str.startswith("reference_")].iloc[0]
    ref83 = metrics_df[metrics_df["variant"] == "reference_short_gate24h_shorttp15_2x"].iloc[0]
    ref80 = metrics_df[metrics_df["variant"] == "reference_shorttp15_2x"].iloc[0]

    lines: list[str] = []
    lines.append("# Study 84: Short-Side Sweep Gate Tuning")
    lines.append("")
    lines.append("## Scope")
    lines.append("- Focus only on the promising idea from study 83: `short-side liquidity sweep gate` on the 15m regime-hold + short-TP engine.")
    lines.append("- Leverage is fixed at `2x` because that was the strongest configuration in study 83.")
    lines.append("- Search dimensions: sweep lookback hours, gate duration bars, short TP threshold, and body-strength filter.")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | CAGR % | MDD % | Calmar | Final Equity | TP Exits | Short Sweeps | Gated Entries |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{_fmt(row['final_equity'])} | {_fmt_count(row.get('tp_exits', np.nan))} | {_fmt_count(row.get('short_sweep_events', np.nan))} | "
            f"{_fmt_count(row.get('gated_entries', np.nan))} |"
        )
    lines.append("")
    lines.append("## Best Live Variant")
    lines.append(
        f"- `{best_live['variant']}`: CAGR `{_fmt(best_live['cagr_pct'])}%`, MDD `{_fmt(best_live['max_drawdown_pct'])}%`, Calmar `{_fmt(best_live['calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Delta vs References")
    lines.append(
        f"- vs study-80 `short_tp15_lock_2x`: CAGR `{_fmt(best_live['cagr_pct'] - ref80['cagr_pct'])}pp`, "
        f"MDD `{_fmt(best_live['max_drawdown_pct'] - ref80['max_drawdown_pct'])}pp`, "
        f"Calmar `{_fmt(best_live['calmar_ratio'] - ref80['calmar_ratio'])}`"
    )
    lines.append(
        f"- vs study-83 `short_gate24h_shorttp15_2x`: CAGR `{_fmt(best_live['cagr_pct'] - ref83['cagr_pct'])}pp`, "
        f"MDD `{_fmt(best_live['max_drawdown_pct'] - ref83['max_drawdown_pct'])}pp`, "
        f"Calmar `{_fmt(best_live['calmar_ratio'] - ref83['calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If lower TP thresholds dominate, the short edge needs faster monetization once the sweep-confirmed move starts working.")
    lines.append("- If longer lookback windows dominate, the market is respecting larger liquidity pools rather than intraday ones.")
    lines.append("- If very short gate windows dominate, the sweep timing edge decays quickly and should be used only as a narrow entry window.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    market = prepare_market_extended(m47)
    variants = build_variants()

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    refs = load_reference_curves()
    for cfg in variants:
        if str(cfg["mode"]) == "reference":
            curve = refs.get(str(cfg["variant"]))
            if curve is None or curve.empty:
                continue
            stats = s82.compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL)
            rows.append({"variant": str(cfg["variant"]), **stats})
            curves_out.append(curve.copy())
            curve_map[str(cfg["variant"])] = curve.copy()
            continue

        curve, run_stats = run_live_variant(market, cfg)
        stats = s82.compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL)
        rows.append({"variant": str(cfg["variant"]), **stats, **run_stats})
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


m47 = load_module("study47_for_84", BASE_47_PATH)
s76 = load_module("study76_for_84", BASE_76_PATH)
s82 = load_module("study82_for_84", BASE_82_PATH)


if __name__ == "__main__":
    run()
