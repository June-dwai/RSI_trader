from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent

BASE_47_PATH = ROOT / "47_backtest_btcusdt_scale06_adx002_case1_standalone.py"
BASE_76_PATH = ROOT / "76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py"
BASE_111_PATH = ROOT / "111_backtest_btcusdt_sr_smc_5m_profitmax.py"
BASE_114_PATH = ROOT / "114_backtest_btcusdt_best_with_sr_smc_filters.py"
BASE_117_PATH = ROOT / "117_backtest_btcusdt_115_highcagr_push.py"
BASE_126_PATH = ROOT / "126_backtest_btcusdt_case3_long_quality_push.py"

OUT_BASE = "141_backtest_btcusdt_row6_whipsaw_guard_trials"
OUT_CSV = ROOT / f"{OUT_BASE}.csv"
OUT_MD = ROOT / f"{OUT_BASE}.md"
OUT_PNG = ROOT / f"{OUT_BASE}.png"
OUT_CURVES_CSV = ROOT / f"{OUT_BASE}_curves.csv"
OUT_WHIPSAW_CSV = ROOT / f"{OUT_BASE}_whipsaw_windows.csv"

BASE_VARIANT = "lb4_delay8_capna_cd0"
ANALYSIS_2026_START = pd.Timestamp("2026-01-01 00:00:00")
WHIPSAW_EPISODES_PATH = ROOT / "140_backtest_btcusdt_row6_bestpair_episode_analysis_episodes.csv"


def load_module(alias: str, path: Path):
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def _fmt(v: float, digits: int = 4) -> str:
    return "N/A" if pd.isna(v) else f"{float(v):.{digits}f}"


def compute_curve_stats(curve: pd.DataFrame, initial_capital: float) -> dict[str, float]:
    series = curve["equity"].astype(float)
    final_equity = float(series.iloc[-1])
    elapsed_days = (curve["timestamp"].iloc[-1] - curve["timestamp"].iloc[0]).total_seconds() / 86400.0
    years = max(elapsed_days / 365.25, 1e-9)
    cagr_pct = ((final_equity / float(initial_capital)) ** (1.0 / years) - 1.0) * 100.0
    dd = series / series.cummax() - 1.0
    max_drawdown_pct = float(-dd.min() * 100.0)
    calmar_ratio = float(cagr_pct / max_drawdown_pct) if max_drawdown_pct > 0 else np.nan
    return {
        "final_equity": final_equity,
        "total_return_pct": (final_equity / float(initial_capital) - 1.0) * 100.0,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "calmar_ratio": calmar_ratio,
    }


def compute_window_stats(curve: pd.DataFrame, start_ts: pd.Timestamp) -> dict[str, float]:
    seg = curve[curve["timestamp"] >= start_ts].copy()
    if seg.empty:
        return {"window_return_pct": np.nan, "window_mdd_pct": np.nan}
    series = seg["equity"].astype(float)
    start_eq = float(series.iloc[0])
    end_eq = float(series.iloc[-1])
    dd = series / series.cummax() - 1.0
    return {
        "window_return_pct": (end_eq / start_eq - 1.0) * 100.0,
        "window_mdd_pct": float(-dd.min() * 100.0),
    }


def compute_segment_loss(curve: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> dict[str, float]:
    seg = curve[(curve["timestamp"] >= start_ts) & (curve["timestamp"] <= end_ts)].copy()
    if seg.empty:
        return {"window_return_pct": np.nan, "window_mdd_pct": np.nan}
    start_eq = float(seg["equity"].iloc[0])
    end_eq = float(seg["equity"].iloc[-1])
    dd = seg["equity"].astype(float) / seg["equity"].cummax().astype(float) - 1.0
    return {
        "window_return_pct": (end_eq / start_eq - 1.0) * 100.0,
        "window_mdd_pct": float(-dd.min() * 100.0),
    }


def load_whipsaw_windows() -> pd.DataFrame:
    if WHIPSAW_EPISODES_PATH.exists():
        df = pd.read_csv(WHIPSAW_EPISODES_PATH)
        out = df[(df["is_representative"] == 1) & (df["episode_label"] == "two_way_whipsaw")][["peak_time", "trough_time"]].drop_duplicates()
        out["peak_time"] = pd.to_datetime(out["peak_time"])
        out["trough_time"] = pd.to_datetime(out["trough_time"])
        return out.sort_values(["peak_time", "trough_time"]).reset_index(drop=True)
    return pd.DataFrame(
        {
            "peak_time": pd.to_datetime(
                [
                    "2022-07-05 13:00:00",
                    "2024-07-08 01:15:00",
                    "2024-12-17 15:00:00",
                    "2025-07-14 07:45:00",
                ]
            ),
            "trough_time": pd.to_datetime(
                [
                    "2022-11-08 05:30:00",
                    "2024-10-13 15:30:00",
                    "2025-02-21 13:45:00",
                    "2025-10-13 20:00:00",
                ]
            ),
        }
    )


def add_chop_features(market: pd.DataFrame) -> pd.DataFrame:
    out = market.copy()
    ema_side = np.where(out["close"].to_numpy(dtype=float) >= out["ema20"].to_numpy(dtype=float), 1, -1)
    ema_cross = np.zeros(len(out), dtype=float)
    ema_cross[1:] = (ema_side[1:] != ema_side[:-1]).astype(float)
    out["ema_cross_count_64"] = pd.Series(ema_cross).rolling(64, min_periods=1).sum().to_numpy(dtype=float)
    return out


def run_variant(df: pd.DataFrame, cfg: dict, s76, m117) -> tuple[pd.DataFrame, dict]:
    base_leverage = float(cfg["leverage"])
    gate_bars = int(cfg["gate_bars"])
    body_atr_mult = float(cfg["body_atr_mult"])
    short_tp_threshold = float(cfg["short_tp_return_pct"]) / 100.0
    max_bearish_above_for_long = int(cfg["max_bearish_above_for_long"])
    long_bullish_delay_bars = int(cfg["long_bullish_delay_bars"])
    long_premium_cap_red_avg_pct = float(cfg["long_premium_cap_red_avg_pct"]) if not pd.isna(cfg["long_premium_cap_red_avg_pct"]) else np.nan
    long_short_sweep_cooldown_bars = int(cfg["long_short_sweep_cooldown_bars"])

    bulltrim_enabled = bool(cfg["bulltrim_enabled"])
    bulltrim_ob_threshold = int(cfg["bulltrim_ob_threshold"])
    bulltrim_leverage = float(cfg["bulltrim_leverage"])
    unlock_short_lock_enabled = bool(cfg["unlock_short_lock_enabled"])
    slow_bear_enabled = bool(cfg["slow_bear_enabled"])
    slow_bear_bars = int(cfg["slow_bear_bars"])
    slow_bear_ob_threshold = int(cfg["slow_bear_ob_threshold"])
    slow_bear_leverage = float(cfg["slow_bear_leverage"])

    chop_cross_threshold = int(cfg["chop_cross_threshold"])
    chop_entry_leverage = float(cfg["chop_entry_leverage"]) if not pd.isna(cfg["chop_entry_leverage"]) else np.nan
    chop_cooldown_bars = int(cfg["chop_cooldown_bars"])
    chop_long_bullish_delay_bars = int(cfg["chop_long_bullish_delay_bars"])

    ts = df["timestamp"].to_numpy()
    open_np = df["open"].to_numpy(dtype=float)
    high_np = df["high"].to_numpy(dtype=float)
    low_np = df["low"].to_numpy(dtype=float)
    close_np = df["close"].to_numpy(dtype=float)
    atr20 = df["atr20"].to_numpy(dtype=float)
    ema20 = df["ema20"].to_numpy(dtype=float)
    trend = df["trend_4h_confirmed"].astype(str).to_numpy()
    body = df["body"].to_numpy(dtype=float)
    liq_high = df["liq_high_24h_prev"].to_numpy(dtype=float)
    red_avg = df["red_avg"].to_numpy(dtype=float)
    bearish_ob_above_count = df["bearish_ob_above_count"].to_numpy(dtype=int)
    bullish_ob_below_count = df["bullish_ob_below_count"].to_numpy(dtype=int)
    ema_cross_count_64 = df["ema_cross_count_64"].to_numpy(dtype=float)

    wallet = s76.INITIAL_CAPITAL
    reserve = s76.INITIAL_CAPITAL
    margin = 0.0
    qty = 0.0
    entry = 0.0
    side = 0
    entry_wallet = np.nan
    pos_leverage = 0.0
    locked_side = 0
    short_gate_until = -10**9
    prev_trend = None
    bullish_streak = 0
    bearish_streak = 0
    bulltrim_used = False
    slow_bear_used = False
    last_short_sweep_idx = -10**9
    last_exit_idx = -10**9

    rows = []
    stats = {
        "trades": 0,
        "bulltrim_count": 0,
        "unlock_short_lock_count": 0,
        "slow_bear_short_entries": 0,
        "blocked_chop_cooldown": 0,
        "blocked_chop_delay": 0,
        "chop_downshift_entries": 0,
    }

    for i in range(len(df)):
        price_open = float(open_np[i])
        price_high = float(high_np[i])
        price_low = float(low_np[i])
        price_close = float(close_np[i])
        cur_trend = str(trend[i])
        blocked_reentry = False
        chop_active = ema_cross_count_64[i] >= chop_cross_threshold if chop_cross_threshold > 0 else False

        if cur_trend == "bullish":
            bullish_streak += 1
            bearish_streak = 0
        else:
            bearish_streak += 1
            bullish_streak = 0

        if prev_trend is not None and cur_trend != prev_trend:
            if cur_trend == "bullish":
                short_gate_until = -10**9
                bulltrim_used = False
            else:
                slow_bear_used = False
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
            last_short_sweep_idx = i

        if unlock_short_lock_enabled and locked_side < 0 and cur_trend == "bearish" and bearish_streak >= slow_bear_bars and price_close < ema20[i]:
            locked_side = 0
            stats["unlock_short_lock_count"] += 1

        if side != 0:
            liq_price = s76._liq_price(entry, pos_leverage, side)
            stop_price = entry * (1.0 - s76.STOP_PCT) if side > 0 else entry * (1.0 + s76.STOP_PCT)
            if side > 0 and pos_leverage > 1.0 and price_low <= liq_price:
                wallet = max(reserve, 0.0)
                reserve = wallet
                margin = qty = entry = 0.0
                side = 0
                pos_leverage = 0.0
                entry_wallet = np.nan
                blocked_reentry = True
                last_exit_idx = i
                stats["trades"] += 1
            elif side < 0 and pos_leverage > 1.0 and price_high >= liq_price:
                wallet = max(reserve, 0.0)
                reserve = wallet
                margin = qty = entry = 0.0
                side = 0
                pos_leverage = 0.0
                entry_wallet = np.nan
                blocked_reentry = True
                last_exit_idx = i
                stats["trades"] += 1
            elif side > 0 and price_low <= stop_price:
                wallet = s76._realize_close(reserve, margin, qty, entry, stop_price, side)
                reserve = wallet
                margin = qty = entry = 0.0
                side = 0
                pos_leverage = 0.0
                entry_wallet = np.nan
                blocked_reentry = True
                last_exit_idx = i
                stats["trades"] += 1
            elif side < 0 and price_high >= stop_price:
                wallet = s76._realize_close(reserve, margin, qty, entry, stop_price, side)
                reserve = wallet
                margin = qty = entry = 0.0
                side = 0
                pos_leverage = 0.0
                entry_wallet = np.nan
                blocked_reentry = True
                last_exit_idx = i
                stats["trades"] += 1
            elif side < 0 and entry_wallet > 0:
                marked_wallet = s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
                if marked_wallet / entry_wallet - 1.0 >= short_tp_threshold:
                    wallet = s76._realize_close(reserve, margin, qty, entry, price_close, side)
                    reserve = wallet
                    margin = qty = entry = 0.0
                    locked_side = side
                    side = 0
                    pos_leverage = 0.0
                    entry_wallet = np.nan
                    last_exit_idx = i
                    stats["trades"] += 1

        if (
            bulltrim_enabled
            and side > 0
            and pos_leverage > bulltrim_leverage
            and cur_trend == "bullish"
            and not bulltrim_used
            and price_close < ema20[i]
            and int(bearish_ob_above_count[i]) >= bulltrim_ob_threshold
        ):
            wallet = s76._realize_close(reserve, margin, qty, entry, price_close, side)
            reserve, margin, qty, entry = s76._open_position(wallet, price_close, bulltrim_leverage, 1)
            wallet = reserve + margin
            side = 1
            pos_leverage = bulltrim_leverage
            entry_wallet = wallet
            bulltrim_used = True
            blocked_reentry = True
            stats["trades"] += 1
            stats["bulltrim_count"] += 1

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
                margin = qty = entry = 0.0
                side = 0
                pos_leverage = 0.0
                entry_wallet = np.nan
                last_exit_idx = i
                stats["trades"] += 1

            if desired_side != 0 and wallet > 0:
                allow_entry = True
                lev_to_open = base_leverage
                used_slow_bear = False

                if chop_active and (i - last_exit_idx) <= chop_cooldown_bars:
                    allow_entry = False
                    stats["blocked_chop_cooldown"] += 1

                if allow_entry and desired_side < 0:
                    allow_entry = i <= short_gate_until and price_close < ema20[i]
                    if not allow_entry and slow_bear_enabled and not slow_bear_used:
                        allow_entry = bearish_streak >= slow_bear_bars and price_close < ema20[i] and int(bearish_ob_above_count[i]) >= slow_bear_ob_threshold
                        used_slow_bear = allow_entry
                        if used_slow_bear:
                            lev_to_open = slow_bear_leverage

                if allow_entry and desired_side > 0:
                    if int(bearish_ob_above_count[i]) > max_bearish_above_for_long:
                        allow_entry = False
                    elif bullish_streak <= long_bullish_delay_bars:
                        allow_entry = False
                    elif chop_active and bullish_streak <= chop_long_bullish_delay_bars:
                        allow_entry = False
                        stats["blocked_chop_delay"] += 1
                    elif long_short_sweep_cooldown_bars > 0 and (i - last_short_sweep_idx) <= long_short_sweep_cooldown_bars:
                        allow_entry = False
                    elif not pd.isna(long_premium_cap_red_avg_pct):
                        max_allowed_price = red_avg[i] * (1.0 + long_premium_cap_red_avg_pct / 100.0)
                        if price_close > max_allowed_price:
                            allow_entry = False

                if allow_entry and not m117.smc_entry_allowed(desired_side, int(bearish_ob_above_count[i]), int(bullish_ob_below_count[i]), 99, 0):
                    allow_entry = False

                if allow_entry and not pd.isna(chop_entry_leverage) and chop_active:
                    new_lev = min(lev_to_open, chop_entry_leverage)
                    if new_lev < lev_to_open:
                        lev_to_open = new_lev
                        stats["chop_downshift_entries"] += 1

                if allow_entry:
                    reserve, margin, qty, entry = s76._open_position(wallet, price_close, lev_to_open, desired_side)
                    wallet = reserve + margin
                    side = desired_side
                    pos_leverage = lev_to_open
                    entry_wallet = wallet
                    if used_slow_bear:
                        slow_bear_used = True
                        stats["slow_bear_short_entries"] += 1

        equity = wallet if side == 0 else s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
        rows.append({"timestamp": ts[i], "equity": equity, "variant": str(cfg["variant"])})

    if side != 0 and len(df):
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close_np[-1]), side)
        rows[-1]["equity"] = wallet
        stats["trades"] += 1
    return pd.DataFrame(rows), stats


def save_plot(curves_df: pd.DataFrame, metrics_df: pd.DataFrame) -> None:
    order = metrics_df["variant"].tolist()
    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(order)}
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.1, 1.0, 1.0]})
    ax_eq, ax_perf, ax_whip = axes
    for variant in order:
        curve = curves_df[curves_df["variant"] == variant]
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(1000.0, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 141: Row6 Whipsaw Guard Trials")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)
    ax_perf.bar(metrics_df["variant"], metrics_df["cagr_pct"], color=[colors[v] for v in order], alpha=0.85, label="CAGR %")
    ax_perf.set_ylabel("CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf.tick_params(axis="x", rotation=18)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(metrics_df["variant"], metrics_df["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_perf_t.set_ylabel("MDD %")
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper left")
    ax_whip.bar(metrics_df["variant"], metrics_df["whipsaw_avg_return_pct"], color=[colors[v] for v in order], alpha=0.85, label="Whipsaw Avg Return %")
    ax_whip.set_ylabel("Whipsaw Avg Return %")
    ax_whip.grid(True, axis="y", alpha=0.2)
    ax_whip.tick_params(axis="x", rotation=18)
    ax_whip_t = ax_whip.twinx()
    ax_whip_t.plot(metrics_df["variant"], metrics_df["whipsaw_avg_mdd_pct"], color="#9467bd", marker="o", linewidth=1.1, label="Whipsaw Avg MDD %")
    ax_whip_t.set_ylabel("Whipsaw Avg MDD %")
    h1, l1 = ax_whip.get_legend_handles_labels()
    h2, l2 = ax_whip_t.get_legend_handles_labels()
    ax_whip.legend(h1 + h2, l1 + l2, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, whipsaw_windows: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> None:
    baseline = metrics_df[metrics_df["variant"] == "combo_base"].iloc[0]
    best_practical = metrics_df.sort_values(["calmar_ratio", "whipsaw_avg_return_pct", "max_drawdown_pct"], ascending=[False, False, True]).iloc[0]
    best_whipsaw = metrics_df.sort_values(["whipsaw_avg_return_pct", "whipsaw_avg_mdd_pct", "calmar_ratio"], ascending=[False, True, False]).iloc[0]
    lines = []
    lines.append("# Study 141: row6 whipsaw-guard trials")
    lines.append("")
    lines.append("- Base engine: `lb4_delay8_capna_cd0` with the 138 improvements.")
    lines.append(f"- Analysis window: `{start_ts}` ~ `{end_ts}`.")
    lines.append("- This study targets the remaining weakness identified in Study 140: long, costly two-way whipsaw periods.")
    lines.append("- Note: the inherited `slow_bear_bars=1440` setting is on 15-minute bars, so it means about 15 days, not 24 hours.")
    lines.append("")
    lines.append("## Variant Table")
    lines.append("| Variant | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Whipsaw Avg Return % | Whipsaw Avg MDD % | Chop Downshift | Chop Cooldown Blocks | Chop Delay Blocks |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{_fmt(row['return_2026_pct'])} | {_fmt(row['mdd_2026_pct'])} | {_fmt(row['whipsaw_avg_return_pct'])} | {_fmt(row['whipsaw_avg_mdd_pct'])} | "
            f"{int(row['chop_downshift_entries'])} | {int(row['blocked_chop_cooldown'])} | {int(row['blocked_chop_delay'])} |"
        )
    lines.append("")
    lines.append(f"- `combo_base`: CAGR `{_fmt(baseline['cagr_pct'])}%`, MDD `{_fmt(baseline['max_drawdown_pct'])}%`, whipsaw avg return `{_fmt(baseline['whipsaw_avg_return_pct'])}%`.")
    lines.append(f"- Best practical balance: `{best_practical['variant']}`.")
    lines.append(f"- Best whipsaw-window protection: `{best_whipsaw['variant']}`.")
    lines.append("")
    lines.append("## What Was Tested")
    lines.append("- `combo_base`: Study 138 practical base (`combo_trim2p0_unlock24h`).")
    lines.append("- `combo_choplev2_x6`: if the last 64 bars have at least 6 EMA20 crosses, downshift new entries to 2.0x.")
    lines.append("- `combo_chopcool8_x6`: in the same chop state, block fresh entries for 8 bars after the last exit.")
    lines.append("- `combo_chopdelay24_x6`: in chop, require a longer bullish confirmation delay (`24` bars) before long re-entry.")
    lines.append("- `combo_choppack_x6`: combine downshift + cooldown + longer bullish delay.")
    lines.append("- `unlock_choppack_x6`: apply the same guard pack to the raw 206% engine without bull trim.")
    lines.append("")
    lines.append("## Whipsaw Windows Used")
    for _, row in whipsaw_windows.iterrows():
        lines.append(f"- `{row['peak_time']}` -> `{row['trough_time']}`")
    lines.append("")
    lines.append("## Practical Read")
    lines.append("- A good whipsaw guard should improve the whipsaw-window average loss first, then try to preserve CAGR.")
    lines.append("- If a variant improves whipsaw windows but destroys CAGR too much, it is over-filtering.")
    lines.append("- If a variant preserves CAGR but whipsaw-window losses stay large, it is not solving the real bottleneck.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG.name}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV.name}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV.name}`")
    lines.append(f"- Whipsaw Windows CSV: `{OUT_WHIPSAW_CSV.name}`")
    lines.append(f"- Report: `{OUT_MD.name}`")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    m47 = load_module("study47_for_141", BASE_47_PATH)
    s76 = load_module("study76_for_141", BASE_76_PATH)
    m111 = load_module("study111_for_141", BASE_111_PATH)
    m114 = load_module("study114_for_141", BASE_114_PATH)
    m117 = load_module("study117_for_141", BASE_117_PATH)
    m126 = load_module("study126_for_141", BASE_126_PATH)

    df_1m, df_4h, end_ts = m114.load_market_data_2021plus()
    market = add_chop_features(m114.prepare_market_114(df_1m.copy(), df_4h.copy(), m47, m111))
    whipsaw_windows = load_whipsaw_windows()
    base_cfg = next(cfg for cfg in m126.build_variants() if cfg["variant"] == BASE_VARIANT)

    trial_cfgs = [
        {**base_cfg, "variant": "combo_base", "bulltrim_enabled": True, "bulltrim_ob_threshold": 5, "bulltrim_leverage": 2.0, "unlock_short_lock_enabled": True, "slow_bear_enabled": True, "slow_bear_bars": 1440, "slow_bear_ob_threshold": 4, "slow_bear_leverage": 2.0, "chop_cross_threshold": 0, "chop_entry_leverage": np.nan, "chop_cooldown_bars": 0, "chop_long_bullish_delay_bars": 8},
        {**base_cfg, "variant": "combo_choplev2_x6", "bulltrim_enabled": True, "bulltrim_ob_threshold": 5, "bulltrim_leverage": 2.0, "unlock_short_lock_enabled": True, "slow_bear_enabled": True, "slow_bear_bars": 1440, "slow_bear_ob_threshold": 4, "slow_bear_leverage": 2.0, "chop_cross_threshold": 6, "chop_entry_leverage": 2.0, "chop_cooldown_bars": 0, "chop_long_bullish_delay_bars": 8},
        {**base_cfg, "variant": "combo_chopcool8_x6", "bulltrim_enabled": True, "bulltrim_ob_threshold": 5, "bulltrim_leverage": 2.0, "unlock_short_lock_enabled": True, "slow_bear_enabled": True, "slow_bear_bars": 1440, "slow_bear_ob_threshold": 4, "slow_bear_leverage": 2.0, "chop_cross_threshold": 6, "chop_entry_leverage": np.nan, "chop_cooldown_bars": 8, "chop_long_bullish_delay_bars": 8},
        {**base_cfg, "variant": "combo_chopdelay24_x6", "bulltrim_enabled": True, "bulltrim_ob_threshold": 5, "bulltrim_leverage": 2.0, "unlock_short_lock_enabled": True, "slow_bear_enabled": True, "slow_bear_bars": 1440, "slow_bear_ob_threshold": 4, "slow_bear_leverage": 2.0, "chop_cross_threshold": 6, "chop_entry_leverage": np.nan, "chop_cooldown_bars": 0, "chop_long_bullish_delay_bars": 24},
        {**base_cfg, "variant": "combo_choppack_x6", "bulltrim_enabled": True, "bulltrim_ob_threshold": 5, "bulltrim_leverage": 2.0, "unlock_short_lock_enabled": True, "slow_bear_enabled": True, "slow_bear_bars": 1440, "slow_bear_ob_threshold": 4, "slow_bear_leverage": 2.0, "chop_cross_threshold": 6, "chop_entry_leverage": 2.0, "chop_cooldown_bars": 8, "chop_long_bullish_delay_bars": 24},
        {**base_cfg, "variant": "unlock_choppack_x6", "bulltrim_enabled": False, "bulltrim_ob_threshold": 5, "bulltrim_leverage": 2.0, "unlock_short_lock_enabled": True, "slow_bear_enabled": True, "slow_bear_bars": 1440, "slow_bear_ob_threshold": 4, "slow_bear_leverage": 2.0, "chop_cross_threshold": 6, "chop_entry_leverage": 2.0, "chop_cooldown_bars": 8, "chop_long_bullish_delay_bars": 24},
    ]

    rows = []
    curves = []
    whipsaw_rows = []
    for cfg in trial_cfgs:
        print(f"running={cfg['variant']}")
        curve, run_stats = run_variant(market, cfg, s76, m117)
        curve["timestamp"] = pd.to_datetime(curve["timestamp"])
        overall = compute_curve_stats(curve, s76.INITIAL_CAPITAL)
        stats_2026 = compute_window_stats(curve, ANALYSIS_2026_START)
        window_returns = []
        window_mdds = []
        for idx, win in whipsaw_windows.iterrows():
            seg = compute_segment_loss(curve, pd.Timestamp(win["peak_time"]), pd.Timestamp(win["trough_time"]))
            whipsaw_rows.append({"variant": cfg["variant"], "window_id": f"W{idx+1}", "peak_time": pd.Timestamp(win["peak_time"]), "trough_time": pd.Timestamp(win["trough_time"]), **seg})
            window_returns.append(seg["window_return_pct"])
            window_mdds.append(seg["window_mdd_pct"])
        rows.append(
            {
                "variant": cfg["variant"],
                **overall,
                "return_2026_pct": stats_2026["window_return_pct"],
                "mdd_2026_pct": stats_2026["window_mdd_pct"],
                "whipsaw_avg_return_pct": float(np.nanmean(window_returns)),
                "whipsaw_avg_mdd_pct": float(np.nanmean(window_mdds)),
                **run_stats,
            }
        )
        curves.append(curve[["timestamp", "equity"]].assign(variant=cfg["variant"]))

    metrics_df = pd.DataFrame(rows).sort_values(["calmar_ratio", "whipsaw_avg_return_pct", "max_drawdown_pct"], ascending=[False, False, True]).reset_index(drop=True)
    curves_df = pd.concat(curves, ignore_index=True)
    whipsaw_df = pd.DataFrame(whipsaw_rows)
    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    curves_df.to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")
    whipsaw_df.to_csv(OUT_WHIPSAW_CSV, index=False, encoding="utf-8-sig")
    save_plot(curves_df, metrics_df)
    save_report(metrics_df, whipsaw_windows, pd.Timestamp(market["timestamp"].min()), pd.Timestamp(end_ts))
    print(f"saved_plot={OUT_PNG.name}")
    print(f"saved_metrics={OUT_CSV.name}")
    print(f"saved_whipsaw={OUT_WHIPSAW_CSV.name}")
    print(metrics_df[["variant", "cagr_pct", "max_drawdown_pct", "calmar_ratio", "return_2026_pct", "whipsaw_avg_return_pct", "whipsaw_avg_mdd_pct", "chop_downshift_entries", "blocked_chop_cooldown", "blocked_chop_delay"]].to_string(index=False))


if __name__ == "__main__":
    main()
