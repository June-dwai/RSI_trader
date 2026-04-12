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

OUT_BASE = "83_backtest_btcusdt_scale06_adx002_smc_sweep_filter_regime_hold"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

SHORT_TP_RETURN_PCT = 15.0

REFERENCE_VARIANTS = [
    {"variant": "reference_shorttp15_15x", "source_variant": "short_tp15_lock_1.5x"},
    {"variant": "reference_shorttp15_2x", "source_variant": "short_tp15_lock_2x"},
]

VARIANTS = [
    {"variant": "base15m_shorttp15_1.5x", "leverage": 1.5, "gate_side": "none", "liq_window": "none", "gate_bars": 0, "body_atr_mult": 0.0},
    {"variant": "long_gate8h_shorttp15_1.5x", "leverage": 1.5, "gate_side": "long", "liq_window": "8h", "gate_bars": 8, "body_atr_mult": 0.25},
    {"variant": "long_gate24h_shorttp15_1.5x", "leverage": 1.5, "gate_side": "long", "liq_window": "24h", "gate_bars": 8, "body_atr_mult": 0.25},
    {"variant": "short_gate8h_shorttp15_1.5x", "leverage": 1.5, "gate_side": "short", "liq_window": "8h", "gate_bars": 8, "body_atr_mult": 0.25},
    {"variant": "short_gate24h_shorttp15_1.5x", "leverage": 1.5, "gate_side": "short", "liq_window": "24h", "gate_bars": 8, "body_atr_mult": 0.25},
    {"variant": "both_gate24h_shorttp15_1.5x", "leverage": 1.5, "gate_side": "both", "liq_window": "24h", "gate_bars": 8, "body_atr_mult": 0.25},
    {"variant": "base15m_shorttp15_2x", "leverage": 2.0, "gate_side": "none", "liq_window": "none", "gate_bars": 0, "body_atr_mult": 0.0},
    {"variant": "long_gate24h_shorttp15_2x", "leverage": 2.0, "gate_side": "long", "liq_window": "24h", "gate_bars": 8, "body_atr_mult": 0.25},
    {"variant": "short_gate24h_shorttp15_2x", "leverage": 2.0, "gate_side": "short", "liq_window": "24h", "gate_bars": 8, "body_atr_mult": 0.25},
    {"variant": "both_gate24h_shorttp15_2x", "leverage": 2.0, "gate_side": "both", "liq_window": "24h", "gate_bars": 8, "body_atr_mult": 0.25},
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


def run_variant(df: pd.DataFrame, cfg: dict, s76) -> tuple[pd.DataFrame, dict]:
    leverage = float(cfg["leverage"])
    gate_side = str(cfg["gate_side"])
    liq_window = str(cfg["liq_window"])
    gate_bars = int(cfg["gate_bars"])
    body_atr_mult = float(cfg["body_atr_mult"])
    tp_threshold = SHORT_TP_RETURN_PCT / 100.0

    timestamps = df["timestamp"].to_numpy()
    open_np = df["open"].to_numpy(dtype=float)
    high_np = df["high"].to_numpy(dtype=float)
    low_np = df["low"].to_numpy(dtype=float)
    close_np = df["close"].to_numpy(dtype=float)
    atr20 = df["atr20"].to_numpy(dtype=float)
    ema20 = df["ema20"].to_numpy(dtype=float)
    trend = df["trend_4h_confirmed"].astype(str).to_numpy()
    body = df["body"].to_numpy(dtype=float)

    liq_high_col = "liq_high_8h_prev" if liq_window == "8h" else "liq_high_24h_prev"
    liq_low_col = "liq_low_8h_prev" if liq_window == "8h" else "liq_low_24h_prev"
    liq_high = df[liq_high_col].to_numpy(dtype=float) if liq_window != "none" else np.full(len(df), np.nan)
    liq_low = df[liq_low_col].to_numpy(dtype=float) if liq_window != "none" else np.full(len(df), np.nan)

    wallet = s76.INITIAL_CAPITAL
    reserve = s76.INITIAL_CAPITAL
    margin = 0.0
    qty = 0.0
    entry = 0.0
    side = 0
    entry_wallet = np.nan
    locked_side = 0

    long_gate_until = -10**9
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
        "long_sweep_events": 0,
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

        if prev_trend is not None and cur_trend != prev_trend:
            if cur_trend == "bullish":
                short_gate_until = -10**9
            elif cur_trend == "bearish":
                long_gate_until = -10**9
        prev_trend = cur_trend

        if liq_window != "none":
            strong_body = bool(pd.notna(atr20[i]) and body[i] >= atr20[i] * body_atr_mult)
            long_sweep_event = bool(
                cur_trend == "bullish"
                and strong_body
                and pd.notna(liq_low[i])
                and price_low < liq_low[i]
                and price_close > liq_low[i]
                and price_close > price_open
            )
            short_sweep_event = bool(
                cur_trend == "bearish"
                and strong_body
                and pd.notna(liq_high[i])
                and price_high > liq_high[i]
                and price_close < liq_high[i]
                and price_close < price_open
            )
            if long_sweep_event:
                long_gate_until = max(long_gate_until, i + gate_bars)
                stats["long_sweep_events"] += 1
            if short_sweep_event:
                short_gate_until = max(short_gate_until, i + gate_bars)
                stats["short_sweep_events"] += 1

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
                used_gate = False
                if gate_side in ("long", "both") and desired_side > 0:
                    allow_entry = i <= long_gate_until and price_close > ema20[i]
                    used_gate = allow_entry
                elif gate_side in ("short", "both") and desired_side < 0:
                    allow_entry = i <= short_gate_until and price_close < ema20[i]
                    used_gate = allow_entry

                if allow_entry:
                    reserve, margin, qty, entry = s76._open_position(wallet, price_close, leverage, desired_side)
                    wallet = reserve + margin
                    side = desired_side
                    entry_wallet = wallet
                    if desired_side > 0:
                        stats["long_entries"] += 1
                    else:
                        stats["short_entries"] += 1
                    if used_gate:
                        stats["gated_entries"] += 1

        equity = wallet if side == 0 else s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
        rows.append(
            {
                "timestamp": timestamps[i],
                "equity": equity,
                "wallet": wallet,
                "reserve": reserve,
                "margin": margin,
                "side": side,
                "locked_side": locked_side,
                "long_gate_open": int(i <= long_gate_until),
                "short_gate_open": int(i <= short_gate_until),
                "variant": str(cfg["variant"]),
            }
        )

    if side != 0 and len(df):
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close_np[-1]), side)
        rows[-1]["equity"] = wallet
        rows[-1]["wallet"] = wallet
        rows[-1]["reserve"] = wallet
        rows[-1]["margin"] = 0.0
        rows[-1]["side"] = 0
        stats["trades"] += 1

    curve = pd.DataFrame(rows)
    stats["first_liquidation_ts"] = first_liq_ts
    return curve, stats


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_gate = axes

    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(s76.INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("83 Study: SMC Sweep Filter on Regime-Hold")
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

    ax_gate.bar(metrics_df["variant"], metrics_df["gated_entries"].fillna(0.0), color=[colors[v] for v in variants], alpha=0.85, label="Gated Entries")
    ax_gate.set_ylabel("Gated Entries")
    ax_gate.grid(True, axis="y", alpha=0.2)
    ax_gate.tick_params(axis="x", rotation=20)
    ax_gate_t = ax_gate.twinx()
    ax_gate_t.plot(metrics_df["variant"], metrics_df["calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Calmar")
    ax_gate_t.set_ylabel("Calmar")
    h1, l1 = ax_gate.get_legend_handles_labels()
    h2, l2 = ax_gate_t.get_legend_handles_labels()
    ax_gate.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    live_df = metrics_df[metrics_df["variant"].str.startswith("reference_") == False].copy()
    best_live = live_df.iloc[0]

    lines: list[str] = []
    lines.append("# Study 83: SMC Sweep Filter on Regime-Hold")
    lines.append("")
    lines.append("## Scope")
    lines.append("- Reuse only the least-bad SMC ingredient from study 82: liquidity sweep.")
    lines.append("- Base engine is the study-80 winner concept: regime-hold with short-only TP-lock at `15%`.")
    lines.append("- Change only the entry timing: selected variants wait for a 15m sweep-reclaim event against 1h liquidity before entering in the 4h confirmed trend direction.")
    lines.append("- This tests SMC as a filter rather than a standalone trading system.")
    lines.append("")
    lines.append("## Variants")
    lines.append("- `base15m_*`: same regime-hold/short-TP concept on the 15m execution engine, no sweep gate.")
    lines.append("- `long_gate*`: only longs require a recent downside sweep-reclaim.")
    lines.append("- `short_gate*`: only shorts require a recent upside sweep-reject.")
    lines.append("- `both_gate*`: both sides require the filter.")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | CAGR % | MDD % | Calmar | Final Equity | Trades | Gated Entries | Long Sweeps | Short Sweeps |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{_fmt(row['final_equity'])} | {_fmt_count(row.get('trades', np.nan))} | {_fmt_count(row.get('gated_entries', np.nan))} | "
            f"{_fmt_count(row.get('long_sweep_events', np.nan))} | {_fmt_count(row.get('short_sweep_events', np.nan))} |"
        )
    lines.append("")
    lines.append("## Best Live Variant")
    lines.append(
        f"- `{best_live['variant']}`: CAGR `{_fmt(best_live['cagr_pct'])}%`, MDD `{_fmt(best_live['max_drawdown_pct'])}%`, Calmar `{_fmt(best_live['calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If a gated variant beats its `base15m` sibling, then liquidity sweep works better as entry timing than as a full standalone strategy.")
    lines.append("- If only long-gated variants work, then the noisy side was long chasing, not short chasing.")
    lines.append("- If only short-gated variants work, then late short entries after downside extension were the real problem.")
    lines.append("- If all gated variants underperform, then the sweep filter is overconstraining the regime-hold engine.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    market = s82.prepare_market(m47)

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    reference_curves = load_reference_curves()
    for variant, curve in reference_curves.items():
        stats = s82.compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL)
        row = {"variant": variant, **stats}
        rows.append(row)
        curves_out.append(curve.copy())
        curve_map[variant] = curve.copy()

    for cfg in VARIANTS:
        curve, run_stats = run_variant(market, cfg, s76)
        stats = s82.compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL)
        row = {"variant": str(cfg["variant"]), **stats, **run_stats}
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


m47 = load_module("study47_for_83", BASE_47_PATH)
s76 = load_module("study76_for_83", BASE_76_PATH)
s82 = load_module("study82_for_83", BASE_82_PATH)


if __name__ == "__main__":
    run()
