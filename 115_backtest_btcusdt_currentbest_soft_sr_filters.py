from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
BASE_76_PATH = Path("76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py")
BASE_114_PATH = Path("114_backtest_btcusdt_best_with_sr_smc_filters.py")

OUT_BASE = "115_backtest_btcusdt_currentbest_soft_sr_filters"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

CAGR_FLOOR_PCT = 90.0
SHORT_TP_RETURN_PCT = 15.0

REFERENCE_ORIGINAL_CFG = {
    "variant": "reference_original_83_2021plus",
    "leverage": 2.0,
    "gate_side": "short",
    "liq_window": "24h",
    "gate_bars": 8,
    "body_atr_mult": 0.25,
    "sr_entry_mode": "none",
    "smc_block_mode": "none",
}

CURRENT_BEST_CFG = {
    **REFERENCE_ORIGINAL_CFG,
    "variant": "currentbest_114_smc5_both_2021plus",
    "smc_block_mode": "both",
}

VARIANTS = [
    REFERENCE_ORIGINAL_CFG,
    CURRENT_BEST_CFG,
    {**CURRENT_BEST_CFG, "variant": "smc5_longonly_2021plus", "smc_block_mode": "long_only"},
    {**CURRENT_BEST_CFG, "variant": "smc5_shortonly_2021plus", "smc_block_mode": "short_only"},
    {**CURRENT_BEST_CFG, "variant": "smc5_both_long_above_whiteavg_2021plus", "sr_entry_mode": "long_above_white_avg"},
    {**CURRENT_BEST_CFG, "variant": "smc5_both_long_above_redfloor_2021plus", "sr_entry_mode": "long_above_red_floor"},
    {**CURRENT_BEST_CFG, "variant": "smc5_both_long_above_redavg_2021plus", "sr_entry_mode": "long_above_red_avg"},
    {**CURRENT_BEST_CFG, "variant": "smc5_both_both_soft_2021plus", "sr_entry_mode": "both_soft"},
    {**CURRENT_BEST_CFG, "variant": "smc5_longonly_long_above_whiteavg_2021plus", "smc_block_mode": "long_only", "sr_entry_mode": "long_above_white_avg"},
    {**CURRENT_BEST_CFG, "variant": "smc5_longonly_long_above_redfloor_2021plus", "smc_block_mode": "long_only", "sr_entry_mode": "long_above_red_floor"},
    {**CURRENT_BEST_CFG, "variant": "smc5_longonly_long_above_redavg_2021plus", "smc_block_mode": "long_only", "sr_entry_mode": "long_above_red_avg"},
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


def sr_entry_allowed(side: int, price_close: float, row: pd.Series, mode: str) -> bool:
    if mode == "none":
        return True
    if mode == "long_above_white_avg":
        return side < 0 or price_close > float(row["white_avg"])
    if mode == "long_above_red_floor":
        return side < 0 or price_close > float(row["red_floor"])
    if mode == "long_above_red_avg":
        return side < 0 or price_close > float(row["red_avg"])
    if mode == "both_soft":
        if side > 0:
            return price_close > float(row["red_floor"])
        return price_close < float(row["red_avg"])
    raise ValueError(f"Unsupported sr_entry_mode: {mode}")


def smc_entry_allowed(side: int, row: pd.Series, mode: str) -> bool:
    if mode == "none":
        return True
    if side > 0:
        if mode in {"both", "long_only"} and bool(row["bearish_stack_5_above"]):
            return False
    else:
        if mode in {"both", "short_only"} and bool(row["bullish_stack_5_below"]):
            return False
    return True


def run_variant_115(df: pd.DataFrame, cfg: dict, s76) -> tuple[pd.DataFrame, dict]:
    leverage = float(cfg["leverage"])
    gate_side = str(cfg["gate_side"])
    liq_window = str(cfg["liq_window"])
    gate_bars = int(cfg["gate_bars"])
    body_atr_mult = float(cfg["body_atr_mult"])
    sr_entry_mode = str(cfg["sr_entry_mode"])
    smc_block_mode = str(cfg["smc_block_mode"])
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
        "blocked_long_gate": 0,
        "blocked_short_gate": 0,
        "blocked_long_smc": 0,
        "blocked_short_smc": 0,
        "blocked_long_sr": 0,
        "blocked_short_sr": 0,
        "survived_to_end": 1,
    }
    first_liq_ts = None

    for i in range(len(df)):
        row = df.iloc[i]
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
                    if not allow_entry:
                        stats["blocked_long_gate"] += 1
                elif gate_side in ("short", "both") and desired_side < 0:
                    allow_entry = i <= short_gate_until and price_close < ema20[i]
                    used_gate = allow_entry
                    if not allow_entry:
                        stats["blocked_short_gate"] += 1

                if allow_entry and not sr_entry_allowed(desired_side, price_close, row, sr_entry_mode):
                    allow_entry = False
                    if desired_side > 0:
                        stats["blocked_long_sr"] += 1
                    else:
                        stats["blocked_short_sr"] += 1

                if allow_entry and not smc_entry_allowed(desired_side, row, smc_block_mode):
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


def rank_metrics(metrics_df: pd.DataFrame) -> pd.DataFrame:
    ranked = metrics_df.copy()
    ranked["meets_cagr_floor"] = ranked["cagr_pct"] >= CAGR_FLOOR_PCT
    ranked = ranked.sort_values(
        ["meets_cagr_floor", "calmar_ratio", "cagr_pct", "max_drawdown_pct"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    return ranked


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    display = ["currentbest_114_smc5_both_2021plus"]
    display.extend([v for v in metrics_df.head(7)["variant"].tolist() if v not in display])

    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_block = axes

    cmap = plt.get_cmap("tab10")
    colors = {v: cmap(i % 10) for i, v in enumerate(display)}

    for variant in display:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(1000.0, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 115: Current Best + Soft SR Entry Filters")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    top = metrics_df.head(10)
    ax_cagr.bar(top["variant"], top["cagr_pct"], color="#1f77b4", alpha=0.85, label="CAGR %")
    ax_cagr.set_ylabel("CAGR %")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr.tick_params(axis="x", rotation=20)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(top["variant"], top["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_cagr_t.set_ylabel("MDD %")
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    sr_blocks = top["blocked_long_sr"].fillna(0.0) + top["blocked_short_sr"].fillna(0.0)
    ax_block.bar(top["variant"], sr_blocks, color="#2ca02c", alpha=0.85, label="SR Blocks")
    ax_block.set_ylabel("SR Blocks")
    ax_block.grid(True, axis="y", alpha=0.2)
    ax_block.tick_params(axis="x", rotation=20)
    ax_block_t = ax_block.twinx()
    ax_block_t.plot(top["variant"], top["delta_calmar_vs_currentbest"], color="#9467bd", marker="o", linewidth=1.1, label="Delta Calmar")
    ax_block_t.set_ylabel("Delta Calmar vs Current Best")
    h1, l1 = ax_block.get_legend_handles_labels()
    h2, l2 = ax_block_t.get_legend_handles_labels()
    ax_block.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp):
    baseline = metrics_df[metrics_df["variant"] == CURRENT_BEST_CFG["variant"]].iloc[0]
    best = metrics_df.iloc[0]
    ref_original = metrics_df[metrics_df["variant"] == REFERENCE_ORIGINAL_CFG["variant"]].iloc[0]

    lines: list[str] = []
    lines.append("# Study 115: Current Best + Soft SR Entry Filters")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Baseline is the study-114 winner: `currentbest_114_smc5_both_2021plus`.")
    lines.append(f"- Backtest period is `{start_ts.date()}` to `{end_ts.date()}` on the same 2021+ BTCUSDT cache.")
    lines.append("- Unlike study 114, SR is now entry-only. It does not force flat or reverse while a trade is already open.")
    lines.append("- SMC blocking can be `both`, `long_only`, or `short_only` to test whether the improvement mainly came from filtering longs or shorts.")
    lines.append(f"- Ranking priority is `CAGR >= {CAGR_FLOOR_PCT:.0f}%` first, then higher Calmar, then higher CAGR, then lower MDD.")
    lines.append("")
    lines.append("## Baselines")
    lines.append(
        f"- Current-best baseline: `{baseline['variant']}` -> CAGR `{_fmt(baseline['cagr_pct'])}%`, MDD `{_fmt(baseline['max_drawdown_pct'])}%`, Calmar `{_fmt(baseline['calmar_ratio'])}`"
    )
    lines.append(
        f"- Original 83 reference: `{ref_original['variant']}` -> CAGR `{_fmt(ref_original['cagr_pct'])}%`, MDD `{_fmt(ref_original['max_drawdown_pct'])}%`, Calmar `{_fmt(ref_original['calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}` -> CAGR `{_fmt(best['cagr_pct'])}%`, MDD `{_fmt(best['max_drawdown_pct'])}%`, "
        f"Calmar `{_fmt(best['calmar_ratio'])}`, Final Equity `{_fmt(best['final_equity'])}`"
    )
    lines.append(
        f"- Delta vs current-best baseline: CAGR `{_fmt(best['delta_cagr_vs_currentbest'])}pp`, "
        f"MDD `{_fmt(best['delta_mdd_vs_currentbest'])}pp`, "
        f"Calmar `{_fmt(best['delta_calmar_vs_currentbest'])}`"
    )
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | SR Entry Mode | SMC Mode | CAGR % | MDD % | Calmar | Delta Calmar | Trades | SR Blocks | SMC Blocks |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        sr_blocks = float(row.get("blocked_long_sr", 0.0)) + float(row.get("blocked_short_sr", 0.0))
        smc_blocks = float(row.get("blocked_long_smc", 0.0)) + float(row.get("blocked_short_smc", 0.0))
        lines.append(
            f"| {row['variant']} | {row['sr_entry_mode']} | {row['smc_block_mode']} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {_fmt(row['delta_calmar_vs_currentbest'])} | "
            f"{_fmt_count(row.get('trades', np.nan))} | {_fmt_count(sr_blocks)} | {_fmt_count(smc_blocks)} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    if best["variant"] == baseline["variant"]:
        lines.append("- None of the softer SR entry permissions improved on the current-best 114 winner.")
    else:
        lines.append("- At least one softer SR entry permission improved on the current-best 114 winner.")
    lines.append("- If a `long_only` SMC mode wins, then the main value of the 5-box filter was preventing bad longs rather than screening both sides symmetrically.")
    lines.append("- If a soft SR entry filter wins, then the issue in study 114 was not the SR idea itself but the fact that SR was used too aggressively as a side-switch rule.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run_validations(market: pd.DataFrame, metrics_df: pd.DataFrame):
    if pd.to_datetime(market["timestamp"].min()).year != 2021:
        raise AssertionError("backtest did not start in 2021")
    required = {REFERENCE_ORIGINAL_CFG["variant"], CURRENT_BEST_CFG["variant"]}
    if not required.issubset(set(metrics_df["variant"])):
        raise AssertionError("missing required baseline rows")


def run():
    print("Loading modules...")
    m47 = load_module("study47_for_115", BASE_47_PATH)
    s76 = load_module("study76_for_115", BASE_76_PATH)
    m114 = load_module("study114_for_115", BASE_114_PATH)
    m111 = m114.load_module("study111_for_115", Path("111_backtest_btcusdt_sr_smc_5m_profitmax.py"))

    print("Loading 2021+ market data...")
    df_1m, df_4h, end_ts = m114.load_market_data_2021plus()
    market = m114.prepare_market_114(df_1m, df_4h, m47, m111)

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    print("Running variants...")
    for idx, cfg in enumerate(VARIANTS, start=1):
        print(f"  variant {idx}/{len(VARIANTS)} -> {cfg['variant']}")
        curve, run_stats = run_variant_115(market, cfg, s76)
        stats = m114.compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL)
        row = {
            "variant": str(cfg["variant"]),
            "sr_entry_mode": str(cfg["sr_entry_mode"]),
            "smc_block_mode": str(cfg["smc_block_mode"]),
            **stats,
            **run_stats,
        }
        rows.append(row)
        curves_out.append(curve.copy())
        curve_map[str(cfg["variant"])] = curve.copy()

    metrics_df = pd.DataFrame(rows)
    baseline_row = metrics_df[metrics_df["variant"] == CURRENT_BEST_CFG["variant"]].iloc[0]
    metrics_df["delta_cagr_vs_currentbest"] = metrics_df["cagr_pct"] - float(baseline_row["cagr_pct"])
    metrics_df["delta_mdd_vs_currentbest"] = metrics_df["max_drawdown_pct"] - float(baseline_row["max_drawdown_pct"])
    metrics_df["delta_calmar_vs_currentbest"] = metrics_df["calmar_ratio"] - float(baseline_row["calmar_ratio"])
    metrics_df = rank_metrics(metrics_df)
    curves_df = pd.concat(curves_out, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df)
    save_report(metrics_df, pd.Timestamp(market["timestamp"].min()), end_ts)
    run_validations(market, metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    run()
