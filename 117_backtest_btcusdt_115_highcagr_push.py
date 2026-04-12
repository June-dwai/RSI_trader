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

OUT_BASE = "117_backtest_btcusdt_115_highcagr_push"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

TARGET_CAGR_PCT = 130.0
EXPECTED_115_CAGR = 109.510547120524


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


REFERENCE_115_CFG = {
    "variant": "reference_115_best",
    "leverage": 2.0,
    "gate_bars": 8,
    "body_atr_mult": 0.25,
    "short_tp_return_pct": 15.0,
    "sr_entry_mode": "none",
    "long_block_threshold": 5,
    "short_block_threshold": 0,
}

REFERENCE_84_CFG = {
    "variant": "reference_84_best",
    "leverage": 2.0,
    "gate_bars": 12,
    "body_atr_mult": 0.25,
    "short_tp_return_pct": 15.0,
    "sr_entry_mode": "none",
    "long_block_threshold": 0,
    "short_block_threshold": 0,
}


def build_variants() -> list[dict]:
    variants = [REFERENCE_115_CFG, REFERENCE_84_CFG]
    for leverage in [2.0, 2.25, 2.5, 3.0]:
        for gate_bars in [8, 12]:
            for body_atr_mult in [0.20, 0.25]:
                for short_tp_return_pct in [15.0, 20.0]:
                    for sr_entry_mode in ["none", "long_above_red_avg"]:
                        for long_block_threshold in [4, 5]:
                            cfg = {
                                "variant": (
                                    f"lv{str(leverage).replace('.', 'p')}_g{gate_bars}_"
                                    f"body{int(round(body_atr_mult * 100)):02d}_"
                                    f"tp{int(round(short_tp_return_pct))}_"
                                    f"lb{long_block_threshold}_{sr_entry_mode}"
                                ),
                                "leverage": leverage,
                                "gate_bars": gate_bars,
                                "body_atr_mult": body_atr_mult,
                                "short_tp_return_pct": short_tp_return_pct,
                                "sr_entry_mode": sr_entry_mode,
                                "long_block_threshold": long_block_threshold,
                                "short_block_threshold": 0,
                            }
                            if cfg == REFERENCE_115_CFG:
                                continue
                            variants.append(cfg)
    return variants


def sr_entry_allowed(side: int, price_close: float, white_avg: float, red_floor: float, red_avg: float, mode: str) -> bool:
    if mode == "none":
        return True
    if mode == "long_above_red_avg":
        return side < 0 or price_close > red_avg
    if mode == "long_above_red_floor":
        return side < 0 or price_close > red_floor
    if mode == "long_above_white_avg":
        return side < 0 or price_close > white_avg
    raise ValueError(f"Unsupported sr_entry_mode: {mode}")


def smc_entry_allowed(side: int, bearish_above_count: int, bullish_below_count: int, long_block_threshold: int, short_block_threshold: int) -> bool:
    if side > 0 and long_block_threshold > 0 and bearish_above_count >= long_block_threshold:
        return False
    if side < 0 and short_block_threshold > 0 and bullish_below_count >= short_block_threshold:
        return False
    return True


def run_variant_117(df: pd.DataFrame, cfg: dict, s76) -> tuple[pd.DataFrame, dict]:
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
        "blocked_short_gate": 0,
        "blocked_long_smc": 0,
        "blocked_short_smc": 0,
        "blocked_long_sr": 0,
        "blocked_short_sr": 0,
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

                if desired_side < 0:
                    allow_entry = i <= short_gate_until and price_close < ema20[i]
                    used_gate = allow_entry
                    if not allow_entry:
                        stats["blocked_short_gate"] += 1

                if allow_entry and not sr_entry_allowed(
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

                if allow_entry and not smc_entry_allowed(
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
    ranked["meets_target"] = ranked["cagr_pct"] >= TARGET_CAGR_PCT
    ranked = ranked.sort_values(
        ["meets_target", "calmar_ratio", "cagr_pct", "max_drawdown_pct"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    return ranked


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    display = ["reference_115_best", "reference_84_best"]
    display.extend([v for v in metrics_df.head(8)["variant"].tolist() if v not in display])

    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_perf, ax_blocks = axes

    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(display)}

    for variant in display:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(1000.0, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 117: Push Study-115 Toward 130% CAGR")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    top = metrics_df.head(10)
    ax_perf.bar(top["variant"], top["cagr_pct"], color="#1f77b4", alpha=0.85, label="CAGR %")
    ax_perf.set_ylabel("CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf.tick_params(axis="x", rotation=20)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(top["variant"], top["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_perf_t.set_ylabel("MDD %")
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_blocks.bar(top["variant"], top["blocked_long_smc"], color="#2ca02c", alpha=0.85, label="Blocked Long SMC")
    ax_blocks.set_ylabel("Blocked Long SMC")
    ax_blocks.grid(True, axis="y", alpha=0.2)
    ax_blocks.tick_params(axis="x", rotation=20)
    ax_blocks_t = ax_blocks.twinx()
    ax_blocks_t.plot(top["variant"], top["delta_cagr_vs_115"], color="#9467bd", marker="o", linewidth=1.1, label="Delta CAGR vs 115")
    ax_blocks_t.set_ylabel("Delta CAGR pp")
    h1, l1 = ax_blocks.get_legend_handles_labels()
    h2, l2 = ax_blocks_t.get_legend_handles_labels()
    ax_blocks.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp):
    ref115 = metrics_df[metrics_df["variant"] == "reference_115_best"].iloc[0]
    ref84 = metrics_df[metrics_df["variant"] == "reference_84_best"].iloc[0]
    best = metrics_df.iloc[0]

    lines: list[str] = []
    lines.append("# Study 117: Push Study-115 Toward 130% CAGR")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Base idea is to keep the study-115 long-side SMC filter, but pair it with stronger short-gate settings closer to study 84.")
    lines.append(f"- Backtest period is `{start_ts.date()}` to `{end_ts.date()}` on the 2021+ BTCUSDT cache.")
    lines.append("- Search axes are leverage, short gate length, short TP threshold, SMC long-block threshold, and whether longs must stay above `red_avg`.")
    lines.append(f"- Ranking priority is `CAGR >= {TARGET_CAGR_PCT:.0f}%` first, then higher Calmar, then higher CAGR, then lower MDD.")
    lines.append("")
    lines.append("## References")
    lines.append(
        f"- `reference_115_best`: CAGR `{_fmt(ref115['cagr_pct'])}%`, MDD `{_fmt(ref115['max_drawdown_pct'])}%`, "
        f"Calmar `{_fmt(ref115['calmar_ratio'])}`"
    )
    lines.append(
        f"- `reference_84_best`: CAGR `{_fmt(ref84['cagr_pct'])}%`, MDD `{_fmt(ref84['max_drawdown_pct'])}%`, "
        f"Calmar `{_fmt(ref84['calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}` -> CAGR `{_fmt(best['cagr_pct'])}%`, MDD `{_fmt(best['max_drawdown_pct'])}%`, "
        f"Calmar `{_fmt(best['calmar_ratio'])}`, Final Equity `{_fmt(best['final_equity'])}`"
    )
    lines.append(
        f"- Delta vs study-115 best: CAGR `{_fmt(best['delta_cagr_vs_115'])}pp`, "
        f"MDD `{_fmt(best['delta_mdd_vs_115'])}pp`, Calmar `{_fmt(best['delta_calmar_vs_115'])}`"
    )
    lines.append(
        f"- Delta vs study-84 best reference: CAGR `{_fmt(best['delta_cagr_vs_84'])}pp`, "
        f"MDD `{_fmt(best['delta_mdd_vs_84'])}pp`, Calmar `{_fmt(best['delta_calmar_vs_84'])}`"
    )
    lines.append("")
    lines.append("## Top 12")
    lines.append("")
    lines.append("| Variant | Leverage | Gate Bars | TP % | Long Block | SR Mode | CAGR % | MDD % | Calmar | Trades |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.head(12).iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['leverage'], 2)} | {_fmt_count(row['gate_bars'])} | {_fmt(row['short_tp_return_pct'], 1)} | "
            f"{_fmt_count(row['long_block_threshold'])} | {row['sr_entry_mode']} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {_fmt_count(row['trades'])} |"
        )
    lines.append("")
    lines.append("## Interpretation")
    if (metrics_df["cagr_pct"] >= TARGET_CAGR_PCT).any():
        lines.append("- The search found at least one variant above the 130% CAGR target.")
    else:
        lines.append("- The search did not find a variant above the 130% CAGR target.")
    lines.append("- If higher leverage plus the stronger short-gate family ranks near the top, then the 115 improvement is portable into the 84-style engine.")
    lines.append("- If `long_above_red_avg` does not appear in the winners, then SR is still weaker than the SMC long-block signal for this engine family.")
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
    required = {"reference_115_best", "reference_84_best"}
    if not required.issubset(set(metrics_df["variant"])):
        raise AssertionError("missing required reference rows")
    ref115 = metrics_df[metrics_df["variant"] == "reference_115_best"].iloc[0]
    if abs(float(ref115["cagr_pct"]) - EXPECTED_115_CAGR) > 1e-6:
        raise AssertionError("reference_115_best did not reproduce the known 115 CAGR")


def run():
    print("Loading modules...")
    m47 = load_module("study47_for_117", BASE_47_PATH)
    s76 = load_module("study76_for_117", BASE_76_PATH)
    m114 = load_module("study114_for_117", BASE_114_PATH)
    m111 = m114.load_module("study111_for_117", Path("111_backtest_btcusdt_sr_smc_5m_profitmax.py"))

    print("Loading 2021+ market...")
    df_1m, df_4h, end_ts = m114.load_market_data_2021plus()
    market = m114.prepare_market_114(df_1m, df_4h, m47, m111)

    variants = build_variants()
    rows: list[dict] = []
    curve_map: dict[str, pd.DataFrame] = {}

    print("Running targeted high-CAGR sweep...")
    for idx, cfg in enumerate(variants, start=1):
        print(f"  variant {idx}/{len(variants)} -> {cfg['variant']}")
        curve, run_stats = run_variant_117(market, cfg, s76)
        stats = compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL)
        rows.append({**cfg, **stats, **run_stats})
        if cfg["variant"] in {"reference_115_best", "reference_84_best"}:
            curve_map[str(cfg["variant"])] = curve.copy()

    metrics_df = pd.DataFrame(rows)
    ref115 = metrics_df[metrics_df["variant"] == "reference_115_best"].iloc[0]
    ref84 = metrics_df[metrics_df["variant"] == "reference_84_best"].iloc[0]
    metrics_df["delta_cagr_vs_115"] = metrics_df["cagr_pct"] - float(ref115["cagr_pct"])
    metrics_df["delta_mdd_vs_115"] = metrics_df["max_drawdown_pct"] - float(ref115["max_drawdown_pct"])
    metrics_df["delta_calmar_vs_115"] = metrics_df["calmar_ratio"] - float(ref115["calmar_ratio"])
    metrics_df["delta_cagr_vs_84"] = metrics_df["cagr_pct"] - float(ref84["cagr_pct"])
    metrics_df["delta_mdd_vs_84"] = metrics_df["max_drawdown_pct"] - float(ref84["max_drawdown_pct"])
    metrics_df["delta_calmar_vs_84"] = metrics_df["calmar_ratio"] - float(ref84["calmar_ratio"])
    metrics_df = rank_metrics(metrics_df)

    for variant in metrics_df.head(10)["variant"].tolist():
        if variant not in curve_map:
            cfg = next(item for item in variants if item["variant"] == variant)
            curve, _ = run_variant_117(market, cfg, s76)
            curve_map[variant] = curve.copy()

    selected_variants = list(dict.fromkeys(["reference_115_best", "reference_84_best"] + metrics_df.head(10)["variant"].tolist()))
    curves_df = pd.concat([curve_map[v] for v in selected_variants], ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df)
    save_report(metrics_df, pd.Timestamp(market["timestamp"].min()), end_ts)
    run_validations(market, metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.head(12).to_string(index=False))


if __name__ == "__main__":
    run()
