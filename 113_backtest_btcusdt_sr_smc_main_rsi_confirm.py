from __future__ import annotations

import importlib.util
import itertools
import sys
from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_107_PATH = Path("107_backtest_btcusdt_4h_ema200_counter_gap_study.py")
BASE_109_PATH = Path("109_backtest_btcusdt_minus20_rsi15_case2_longonly_noreentry.py")
BASE_110_PATH = Path("110_backtest_btcusdt_gap_rsi15_case2_longonly_threshold_cases.py")
BASE_111_PATH = Path("111_backtest_btcusdt_sr_smc_5m_profitmax.py")
BASE_111_CSV = Path("111_backtest_btcusdt_sr_smc_5m_profitmax.csv")
BASE_111_CURVES_CSV = Path("111_backtest_btcusdt_sr_smc_5m_profitmax_selected_curves.csv")

OUT_BASE = "113_backtest_btcusdt_sr_smc_main_rsi_confirm"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_TRADES_CSV = Path(f"{OUT_BASE}_trades.csv")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_selected_curves.csv")

ZONE_ANCHORS = ["white_floor", "red_floor", "overlap"]
SWEEP_WINDOWS = [3, 6, 12]
STRUCT_WINDOWS = [1, 2, 3]

RSI_MODES: dict[str, dict[str, float | int | str]] = {
    "r6_os20_rec30": {"period": 6, "oversold": 20.0, "recover": 30.0, "mode": "recover"},
    "r6_os25_rec35": {"period": 6, "oversold": 25.0, "recover": 35.0, "mode": "recover"},
    "r8_os30_rec40": {"period": 8, "oversold": 30.0, "recover": 40.0, "mode": "recover"},
    "r6_os25_upturn": {"period": 6, "oversold": 25.0, "recover": 0.0, "mode": "upturn"},
}

BASE_CFG = {
    "entry_scale": 0.60,
    "max_entries": 2,
    "add_trigger": "ob_revisit",
    "add_profile": "taper",
    "cooldown_bars": 2,
    "stop_mode": "ob_low-0.1ATR",
    "tp_mode": "partial_1.5R_runner_to_bearish_ob",
    "max_hold_bars": 72,
}

ENTRY_SCALE_GRID = [0.30, 0.45, 0.60]
MAX_ENTRIES_GRID = [1, 2, 3]
ADD_TRIGGER_GRID = ["none", "retest_red_floor", "ob_revisit", "avg_minus_0.5ATR"]
ADD_PROFILE_GRID = ["equal", "taper"]
COOLDOWN_GRID = [0, 2, 4]
STOP_MODE_GRID = ["sweep_low-0.2ATR", "red_floor-0.15ATR", "ob_low-0.1ATR"]
TP_MODE_GRID = ["2R_fixed", "3R_fixed", "partial_1.5R_runner_to_bearish_ob", "trail_white_avg_after_2R"]
MAX_HOLD_GRID = [24, 48, 72, 96]


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def _better_metrics(a: dict, b: dict | None) -> bool:
    if b is None:
        return True
    key_a = (float(a["final_equity"]), float(a["cagr_pct"]), -float(a["max_drawdown_pct"]))
    key_b = (float(b["final_equity"]), float(b["cagr_pct"]), -float(b["max_drawdown_pct"]))
    return key_a > key_b


def _rolling_min(series: pd.Series, window: int) -> np.ndarray:
    return series.rolling(window, min_periods=1).min().to_numpy(dtype=float)


def build_rsi_cache(market: pd.DataFrame, m109) -> dict[int, pd.Series]:
    periods = sorted({int(spec["period"]) for spec in RSI_MODES.values()})
    return {period: m109.calculate_rsi(market["close"], period) for period in periods}


def build_signal_cache_113(market: pd.DataFrame, m109, m111) -> dict:
    cache: dict = {}

    close = market["close"].to_numpy(dtype=float)
    high = market["high"].to_numpy(dtype=float)
    low = market["low"].to_numpy(dtype=float)
    white_avg = market["white_avg"].to_numpy(dtype=float)
    prev3_high = market["prev3_high"].to_numpy(dtype=float)
    long_regime = market["long_regime"].to_numpy(dtype=bool)
    sweep_event = market["weak_low_sweep"].to_numpy(dtype=bool) | market["proxy_sweep_low"].to_numpy(dtype=bool)
    choch = market["internal_bullish_choch"].to_numpy(dtype=bool)
    bos = market["internal_bullish_bos"].to_numpy(dtype=bool)
    ob_revisit = market["bullish_internal_ob_revisit"].to_numpy(dtype=bool)
    active_ob = market["active_bullish_internal_ob"].to_numpy(dtype=bool)
    exact_ob_low = market["exact_bullish_internal_ob_bottom"].to_numpy(dtype=float)
    exact_ob_high = market["exact_bullish_internal_ob_top"].to_numpy(dtype=float)
    weak_low_level = market["weak_low_level"].to_numpy(dtype=float)
    atr5 = market["atr_5m"].to_numpy(dtype=float)

    rsi_cache = build_rsi_cache(market, m109)
    zone_cache = {anchor: m111._zone_bounds(market, anchor) for anchor in ZONE_ANCHORS}

    for anchor in ZONE_ANCHORS:
        zone_low, zone_high = zone_cache[anchor]
        zone_touch = long_regime & (low <= zone_high) & (high >= zone_low)
        reclaimed_white = (close > white_avg) & ~(np.r_[False, close[:-1] > white_avg[:-1]])
        prev3_break = np.isfinite(prev3_high) & (close > prev3_high)

        for sweep_window, struct_window in itertools.product(SWEEP_WINDOWS, STRUCT_WINDOWS):
            sweep_recent = m111._rolling_any(sweep_event, sweep_window)
            choch_recent = m111._rolling_any(choch, struct_window)
            bull_struct_recent = m111._rolling_any(choch | bos, struct_window)
            ob_recent = m111._rolling_any(active_ob, struct_window)
            ob_revisit_recent = m111._rolling_any(ob_revisit, struct_window)

            sweep_stop_ref = pd.Series(np.where(sweep_event, np.minimum(low, weak_low_level), np.nan)).ffill().to_numpy(dtype=float)
            sweep_stop_ref = np.where(np.isfinite(sweep_stop_ref), sweep_stop_ref, np.minimum(low, zone_low - 0.2 * atr5))
            ob_stop_ref = np.where(np.isfinite(exact_ob_low), exact_ob_low, np.minimum(low, zone_low))
            band_stop_ref = np.nanmin(
                np.column_stack(
                    [
                        np.where(np.isfinite(weak_low_level), weak_low_level, np.nan),
                        np.where(np.isfinite(exact_ob_low), exact_ob_low, np.nan),
                        zone_low,
                    ]
                ),
                axis=1,
            )
            band_stop_ref = np.where(np.isfinite(band_stop_ref), band_stop_ref, np.minimum(low, zone_low))

            for rsi_mode_name, spec in RSI_MODES.items():
                rsi = rsi_cache[int(spec["period"])]
                recent_os = _rolling_min(rsi, max(2, sweep_window)) <= float(spec["oversold"])
                rising = rsi.to_numpy(dtype=float) > rsi.shift(1).to_numpy(dtype=float)
                if str(spec["mode"]) == "recover":
                    rsi_ok = recent_os & (rsi.to_numpy(dtype=float) >= float(spec["recover"])) & rising
                else:
                    rsi_ok = recent_os & rising

                sweep_raw = (
                    long_regime
                    & zone_touch
                    & sweep_recent
                    & choch_recent
                    & ob_recent
                    & ob_revisit_recent
                    & reclaimed_white
                    & rsi_ok
                )
                ob_raw = (
                    long_regime
                    & zone_touch
                    & active_ob
                    & ob_revisit
                    & bull_struct_recent
                    & (close > zone_low)
                    & rsi_ok
                )
                band_raw = (
                    long_regime
                    & zone_touch
                    & bull_struct_recent
                    & prev3_break
                    & reclaimed_white
                    & rsi_ok
                )

                signal_defs = {
                    "sweep_choch_ob": (sweep_raw, sweep_stop_ref, exact_ob_low, exact_ob_high),
                    "ob_revisit_bull": (ob_raw, ob_stop_ref, exact_ob_low, exact_ob_high),
                    "band_reclaim_break": (band_raw, band_stop_ref, exact_ob_low, exact_ob_high),
                }

                for family, (raw_mask, stop_ref, ob_low_ref, ob_high_ref) in signal_defs.items():
                    signal_mask = m111._edge_from_bool(raw_mask)
                    signal_idx = np.flatnonzero(signal_mask)
                    seed = m111.SeedConfig(family, anchor, sweep_window, struct_window, rsi_mode_name)
                    cache[seed] = {
                        "signal_mask": signal_mask,
                        "signal_idx": signal_idx.astype(int),
                        "signal_stop_ref": np.asarray(stop_ref, dtype=float)[signal_idx],
                        "signal_ob_low": np.asarray(ob_low_ref, dtype=float)[signal_idx],
                        "signal_ob_high": np.asarray(ob_high_ref, dtype=float)[signal_idx],
                        "signal_count": int(signal_idx.size),
                    }
    return cache


def strategy_from_seed(seed, stage: str, m111):
    return m111.StrategyConfig(seed=seed, stage=stage, **BASE_CFG).normalized()


def coordinate_optimize_seed_113(seed, evaluate, m111):
    current = strategy_from_seed(seed, "stage113_fullstack", m111)
    best_metrics = evaluate(current).metrics
    fields = [
        ("entry_scale", ENTRY_SCALE_GRID),
        ("max_entries", MAX_ENTRIES_GRID),
        ("add_trigger", ADD_TRIGGER_GRID),
        ("add_profile", ADD_PROFILE_GRID),
        ("cooldown_bars", COOLDOWN_GRID),
        ("stop_mode", STOP_MODE_GRID),
        ("tp_mode", TP_MODE_GRID),
        ("max_hold_bars", MAX_HOLD_GRID),
    ]
    for _ in range(2):
        improved = False
        for field_name, values in fields:
            local_best_cfg = current
            local_best_metrics = best_metrics
            for value in values:
                candidate = replace(current, **{field_name: value}, stage="stage113_fullstack").normalized()
                if field_name in {"add_trigger", "add_profile"} and candidate.max_entries == 1:
                    continue
                artifacts = evaluate(candidate)
                if _better_metrics(artifacts.metrics, local_best_metrics):
                    local_best_cfg = candidate
                    local_best_metrics = artifacts.metrics
            if local_best_cfg != current:
                current = local_best_cfg
                best_metrics = local_best_metrics
                improved = True
        if not improved:
            break
    return current, best_metrics


def run_validations(trade_df: pd.DataFrame, metrics_df: pd.DataFrame):
    if not trade_df.empty:
        strategy_trades = trade_df[trade_df["stage"] != "benchmark"].copy()
        if not strategy_trades.empty and not (pd.to_datetime(strategy_trades["entry_time"]) > pd.to_datetime(strategy_trades["signal_time"])).all():
            raise AssertionError("same-bar entry detected")
        if not strategy_trades.empty and not (strategy_trades["num_entries"] <= strategy_trades["max_entries_allowed"]).all():
            raise AssertionError("max entries violation detected")

    benchmark_flags = set(metrics_df["benchmark_flag"].fillna("").astype(str))
    required = {"buy_hold", "gap_12", "study111_proxy", "winner_113"}
    if not required.issubset(benchmark_flags):
        raise AssertionError("missing required benchmark rows")


def save_plot(curve_map: dict[str, pd.DataFrame], summary_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=False, gridspec_kw={"height_ratios": [2.4, 1.0, 1.0]})
    ax_eq, ax_final, ax_risk = axes

    variants = summary_df["variant"].tolist()
    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.1, label=variant, color=colors[variant])
    ax_eq.axhline(1000.0, color="#666666", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 113: SR/SMC Main, RSI Confirmation")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_final.bar(summary_df["variant"], summary_df["final_equity"], color=[colors[v] for v in variants], alpha=0.9)
    ax_final.set_ylabel("Final Equity")
    ax_final.grid(True, axis="y", alpha=0.2)
    ax_final.tick_params(axis="x", rotation=20)

    ax_risk.bar(summary_df["variant"], summary_df["cagr_pct"], color=[colors[v] for v in variants], alpha=0.85, label="CAGR %")
    ax_risk_t = ax_risk.twinx()
    ax_risk_t.plot(summary_df["variant"], summary_df["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_risk.set_ylabel("CAGR %")
    ax_risk_t.set_ylabel("MDD %")
    ax_risk.grid(True, axis="y", alpha=0.2)
    ax_risk.tick_params(axis="x", rotation=20)
    h1, l1 = ax_risk.get_legend_handles_labels()
    h2, l2 = ax_risk_t.get_legend_handles_labels()
    ax_risk.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def build_report(winner: dict, sanity_df: pd.DataFrame, coarse_df: pd.DataFrame, fullstack_df: pd.DataFrame, benchmark_summary: pd.DataFrame, proxy_row: dict, gap12_row: dict) -> str:
    uplift_gap = float(winner["final_equity"] - gap12_row["final_equity"])
    uplift_proxy = float(winner["final_equity"] - proxy_row["final_equity"])
    lines: list[str] = []
    lines.append("# Study 113: SR/SMC Main, RSI Confirmation")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Base market prep reuses study 111: 5m execution from BTCUSDT 1m data with the same SR and LuxAlgo-style exact/internal structure features.")
    lines.append("- This study flips the priority: SR + SMC define the trigger, RSI only confirms that the pullback is washed out and starting to recover.")
    lines.append("- Signal families are `sweep_choch_ob`, `ob_revisit_bull`, and `band_reclaim_break`.")
    lines.append("- Coarse pass sweeps structural seeds; full-stack pass only tunes position sizing, adds, stop mode, TP mode, and max hold.")
    lines.append("")
    lines.append("## Winner")
    lines.append(
        f"- Winner: `{winner['variant']}` -> equity `{_fmt(winner['final_equity'])}`, CAGR `{_fmt(winner['cagr_pct'])}%`, "
        f"MDD `{_fmt(winner['max_drawdown_pct'])}%`, Calmar `{_fmt(winner['calmar_ratio'])}`, trades `{int(winner['trades'])}`"
    )
    lines.append(
        f"- Structural trigger: `{winner['entry_family']}` on `{winner['zone_anchor']}`, sweep window `{int(winner['sweep_lookback'])}`, "
        f"struct window `{int(winner['reclaim_window'])}`, RSI confirm `{winner['confirm_mode']}`"
    )
    lines.append(f"- vs `110 gap_12`: equity uplift `{_fmt(uplift_gap)}`")
    lines.append(f"- vs `111 proxy winner`: equity uplift `{_fmt(uplift_proxy)}`")
    lines.append("")
    lines.append("## Benchmarks")
    lines.append("| Variant | Stage | Final Equity | CAGR % | MDD % | Calmar | Trades |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for _, row in benchmark_summary.iterrows():
        lines.append(
            f"| {row['variant']} | {row['stage']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {int(row['trades']) if pd.notna(row['trades']) else 'N/A'} |"
        )
    lines.append("")
    lines.append("## Stage 113 Full-Stack Top 10")
    lines.append("| Variant | Entry Family | Final Equity | CAGR % | MDD % | Calmar | Trades |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for _, row in fullstack_df.head(10).iterrows():
        lines.append(
            f"| {row['variant']} | {row['entry_family']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {int(row['trades'])} |"
        )
    lines.append("")
    lines.append("## Stage 113 Coarse Top 10")
    lines.append("| Variant | Entry Family | Final Equity | CAGR % | MDD % | Trades |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
    for _, row in coarse_df.head(10).iterrows():
        lines.append(
            f"| {row['variant']} | {row['entry_family']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {int(row['trades'])} |"
        )
    lines.append("")
    lines.append("## Sanity Leaderboard")
    lines.append("| Variant | Stage | Final Equity | CAGR % | MDD % | Trades |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
    if sanity_df.empty:
        lines.append("| none | N/A | N/A | N/A | N/A | N/A |")
    else:
        for _, row in sanity_df.iterrows():
            lines.append(
                f"| {row['variant']} | {row['stage']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | "
                f"{_fmt(row['max_drawdown_pct'])} | {int(row['trades'])} |"
            )
    lines.append("")
    lines.append("## Notes")
    lines.append("- RSI is never used as the standalone trigger here; every entry starts from SR touch + SMC structure alignment.")
    lines.append("- If this still loses to `gap_12` or `111 proxy`, the next step is likely to improve the exit logic rather than add more RSI conditions.")
    return "\n".join(lines) + "\n"


def main():
    print("Loading study modules and market data...")
    spec111 = importlib.util.spec_from_file_location("_m111_113", BASE_111_PATH)
    if spec111 is None or spec111.loader is None:
        raise RuntimeError(f"Cannot load module from: {BASE_111_PATH}")
    m111 = importlib.util.module_from_spec(spec111)
    sys.modules["_m111_113"] = m111
    spec111.loader.exec_module(m111)
    m107 = m111.load_module("_m107_113", BASE_107_PATH)
    m109 = m111.load_module("_m109_113", BASE_109_PATH)
    m110 = m111.load_module("_m110_113", BASE_110_PATH)

    df_1m, df_4h, _ = m107.load_market_data()
    market = m111.prepare_market_111(df_1m)
    bundle = m111.build_market_bundle(market, df_1m)
    signal_cache = build_signal_cache_113(market, m109, m111)

    eval_cache: dict[str, object] = {}

    def evaluate(cfg, benchmark_flag: str = "", keep_curve: bool = False, keep_trades: bool = False):
        cfg = cfg.normalized()
        cache_key = cfg.variant()
        if cache_key in eval_cache and not keep_curve and not keep_trades:
            return eval_cache[cache_key]
        pack = signal_cache[cfg.seed]
        artifacts = m111.simulate_strategy(bundle, pack, cfg, benchmark_flag=benchmark_flag, keep_curve=keep_curve, keep_trades=keep_trades)
        if not keep_curve and not keep_trades:
            eval_cache[cache_key] = artifacts
        return artifacts

    print("Stage 113 coarse pass...")
    seeds = []
    for family, anchor, sweep_window, struct_window, rsi_mode_name in itertools.product(
        ["sweep_choch_ob", "ob_revisit_bull", "band_reclaim_break"],
        ZONE_ANCHORS,
        SWEEP_WINDOWS,
        STRUCT_WINDOWS,
        list(RSI_MODES.keys()),
    ):
        seeds.append(m111.SeedConfig(family, anchor, sweep_window, struct_window, rsi_mode_name))

    coarse_rows: list[dict] = []
    for idx, seed in enumerate(seeds, start=1):
        if idx % 40 == 0 or idx == len(seeds):
            print(f"  coarse {idx}/{len(seeds)}")
        coarse_rows.append(evaluate(strategy_from_seed(seed, "stage113_coarse", m111)).metrics)
    coarse_df = pd.DataFrame(coarse_rows).sort_values(["final_equity", "cagr_pct", "max_drawdown_pct"], ascending=[False, False, True]).reset_index(drop=True)

    top12 = coarse_df.head(12)
    top_per_family = coarse_df.groupby("entry_family", as_index=False).head(1)
    seed_rows = pd.concat([top12, top_per_family], ignore_index=True)
    unique_seed_map = {}
    for _, row in seed_rows.iterrows():
        seed = m111.SeedConfig(str(row["entry_family"]), str(row["zone_anchor"]), int(row["sweep_lookback"]), int(row["reclaim_window"]), str(row["confirm_mode"]))
        unique_seed_map[(seed.entry_family, seed.zone_anchor, seed.sweep_lookback, seed.reclaim_window, seed.confirm_mode)] = seed

    print("Stage 113 full-stack pass...")
    fullstack_rows: list[dict] = []
    for idx, seed in enumerate(unique_seed_map.values(), start=1):
        print(f"  full-stack {idx}/{len(unique_seed_map)} -> {seed.short_name()}")
        _, best_metrics = coordinate_optimize_seed_113(seed, evaluate, m111)
        fullstack_rows.append(best_metrics)
    fullstack_df = pd.DataFrame(fullstack_rows).sort_values(["final_equity", "cagr_pct", "max_drawdown_pct"], ascending=[False, False, True]).reset_index(drop=True)

    print("Benchmarks...")
    benchmark_market_1m = m109.build_market_1m(df_1m, df_4h)
    buy_hold_curve, buy_hold_trades, buy_hold_stats = m109.run_buy_hold(benchmark_market_1m)
    gap12_curve, gap12_trades, gap12_stats = m110.run_threshold_case(benchmark_market_1m, 12.0, m109)

    study111_metrics = pd.read_csv(BASE_111_CSV)
    study111_curves = pd.read_csv(BASE_111_CURVES_CSV, parse_dates=["timestamp"])
    proxy_row = study111_metrics[study111_metrics["benchmark_flag"] == "proxy_winner"].iloc[0].to_dict()
    proxy_variant = str(proxy_row["variant"])
    proxy_curve = study111_curves[study111_curves["variant"] == proxy_variant].copy()
    proxy_curve = proxy_curve[["timestamp", "variant", "equity"]].copy()

    winner_row = fullstack_df.iloc[0].to_dict()

    summary_rows = [
        m111.benchmark_to_row(buy_hold_stats, "buy_hold"),
        m111.benchmark_to_row(gap12_stats, "gap_12"),
        {**proxy_row, "benchmark_flag": "study111_proxy"},
    ]
    winner_benchmark = dict(winner_row)
    winner_benchmark["benchmark_flag"] = "winner_113"

    metrics_df = pd.concat(
        [
            coarse_df.assign(benchmark_flag=""),
            fullstack_df.assign(benchmark_flag=""),
            pd.DataFrame(summary_rows),
        ],
        ignore_index=True,
        sort=False,
    )
    metrics_df.loc[metrics_df["variant"] == winner_benchmark["variant"], "benchmark_flag"] = "winner_113"
    metrics_df.to_csv(OUT_CSV, index=False)

    print("Collecting selected curves and trades...")
    selected_curves: dict[str, pd.DataFrame] = {
        "buy_hold": m111._compress_curve(buy_hold_curve[["timestamp", "variant", "equity"]]),
        "gap_12": m111._compress_curve(gap12_curve[["timestamp", "variant", "equity"]]),
        proxy_variant: m111._compress_curve(proxy_curve),
    }
    selected_trade_frames = [
        buy_hold_trades.assign(stage="benchmark", gate="none", signal_time=buy_hold_trades["entry_time"], max_entries_allowed=1, entry_family="buy_hold", exit_reason="Final Close", realized_r=buy_hold_trades["return_pct"], hold_minutes=buy_hold_trades["hours_held"] * 60.0, size_path="1.00"),
        gap12_trades.assign(stage="benchmark", gate="none", signal_time=gap12_trades["entry_time"], max_entries_allowed=4, entry_family="gap_12", size_path="benchmark").rename(columns={"reason": "exit_reason", "return_pct": "realized_r", "hours_held": "hold_minutes"}),
    ]
    if "hold_minutes" in selected_trade_frames[1].columns:
        selected_trade_frames[1]["hold_minutes"] = selected_trade_frames[1]["hold_minutes"] * 60.0

    selected_cfgs = []
    for row in [winner_row]:
        selected_cfgs.append(
            m111.StrategyConfig(
                seed=m111.SeedConfig(str(row["entry_family"]), str(row["zone_anchor"]), int(row["sweep_lookback"]), int(row["reclaim_window"]), str(row["confirm_mode"])),
                entry_scale=float(row["entry_scale"]),
                max_entries=int(row["max_entries"]),
                add_trigger=str(row["add_trigger"]),
                add_profile=str(row["add_profile"]),
                cooldown_bars=int(row["cooldown_bars"]),
                stop_mode=str(row["stop_mode"]),
                tp_mode=str(row["tp_mode"]),
                max_hold_bars=int(row["max_hold_bars"]),
                smc_gate_mode=str(row.get("gate", "none")),
                stage=str(row["stage"]),
            ).normalized()
        )
    sanity_pick = fullstack_df[(fullstack_df["trades"] >= 20) & (fullstack_df["max_drawdown_pct"] <= 40.0)].head(1)
    for _, row in sanity_pick.iterrows():
        selected_cfgs.append(
            m111.StrategyConfig(
                seed=m111.SeedConfig(str(row["entry_family"]), str(row["zone_anchor"]), int(row["sweep_lookback"]), int(row["reclaim_window"]), str(row["confirm_mode"])),
                entry_scale=float(row["entry_scale"]),
                max_entries=int(row["max_entries"]),
                add_trigger=str(row["add_trigger"]),
                add_profile=str(row["add_profile"]),
                cooldown_bars=int(row["cooldown_bars"]),
                stop_mode=str(row["stop_mode"]),
                tp_mode=str(row["tp_mode"]),
                max_hold_bars=int(row["max_hold_bars"]),
                smc_gate_mode=str(row.get("gate", "none")),
                stage=str(row["stage"]),
            ).normalized()
        )

    for cfg in {cfg.variant(): cfg for cfg in selected_cfgs}.values():
        artifacts = evaluate(cfg, keep_curve=True, keep_trades=True)
        if artifacts.curve is not None:
            selected_curves[cfg.variant()] = m111._compress_curve(artifacts.curve[["timestamp", "variant", "equity"]])
        if artifacts.trades is not None and not artifacts.trades.empty:
            selected_trade_frames.append(artifacts.trades)

    pd.concat(selected_curves.values(), ignore_index=True).to_csv(OUT_CURVES_CSV, index=False)
    selected_trade_df = pd.concat(selected_trade_frames, ignore_index=True, sort=False)
    selected_trade_df.to_csv(OUT_TRADES_CSV, index=False)

    benchmark_summary = pd.DataFrame(
        [
            m111.benchmark_to_row(buy_hold_stats, "buy_hold"),
            m111.benchmark_to_row(gap12_stats, "gap_12"),
            {**proxy_row, "benchmark_flag": "study111_proxy"},
            winner_benchmark,
        ]
    ).sort_values(["final_equity", "cagr_pct", "max_drawdown_pct"], ascending=[False, False, True]).reset_index(drop=True)
    save_plot(selected_curves, benchmark_summary[["variant", "final_equity", "cagr_pct", "max_drawdown_pct"]])

    sanity_df = metrics_df[
        (metrics_df["stage"].isin(["stage113_coarse", "stage113_fullstack"]))
        & (metrics_df["max_drawdown_pct"] <= 40.0)
        & (metrics_df["trades"] >= 20)
    ].sort_values(["final_equity", "cagr_pct", "max_drawdown_pct"], ascending=[False, False, True]).head(10)
    report = build_report(winner_row, sanity_df, coarse_df, fullstack_df, benchmark_summary, proxy_row, m111.benchmark_to_row(gap12_stats, "gap_12"))
    OUT_MD.write_text(report, encoding="utf-8")

    run_validations(selected_trade_df, pd.concat([metrics_df, benchmark_summary], ignore_index=True, sort=False))
    print("Done.")
    print(f"- metrics: {OUT_CSV}")
    print(f"- trades: {OUT_TRADES_CSV}")
    print(f"- curves: {OUT_CURVES_CSV}")
    print(f"- report: {OUT_MD}")
    print(f"- plot: {OUT_PNG}")


if __name__ == "__main__":
    main()
