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

OUT_BASE = "140_backtest_btcusdt_row6_bestpair_episode_analysis"
OUT_PNG = ROOT / f"{OUT_BASE}.png"
OUT_MD = ROOT / f"{OUT_BASE}.md"
OUT_EPISODES_CSV = ROOT / f"{OUT_BASE}_episodes.csv"
OUT_LABEL_SUMMARY_CSV = ROOT / f"{OUT_BASE}_label_summary.csv"
OUT_VARIANT_SUMMARY_CSV = ROOT / f"{OUT_BASE}_variant_summary.csv"
OUT_CURVES_CSV = ROOT / f"{OUT_BASE}_curves.csv"

BASE_VARIANT = "lb4_delay8_capna_cd0"
ANALYSIS_2026_START = pd.Timestamp("2026-01-01 00:00:00")
TOP_DEPTH = 5
TOP_DURATION = 5

VARIANT_ORDER = [
    "unlock_slowbear_24h_2p0",
    "combo_trim2p0_unlock24h",
]


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


def compute_underwater_episodes(curve: pd.DataFrame, variant: str) -> pd.DataFrame:
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
                    "variant": variant,
                    "peak_idx": start_idx,
                    "trough_idx": trough_idx,
                    "recovery_idx": i,
                    "peak_time": df.iloc[start_idx]["timestamp"],
                    "trough_time": df.iloc[trough_idx]["timestamp"],
                    "recovery_time": df.iloc[i]["timestamp"],
                    "peak_equity": float(df.iloc[start_idx]["equity"]),
                    "trough_equity": float(df.iloc[trough_idx]["equity"]),
                    "recovery_equity": float(df.iloc[i]["equity"]),
                    "depth_pct": -float(seg["dd"].min() * 100.0),
                    "days_to_trough": (df.iloc[trough_idx]["timestamp"] - df.iloc[start_idx]["timestamp"]).total_seconds() / 86400.0,
                    "days_to_recovery": (df.iloc[i]["timestamp"] - df.iloc[start_idx]["timestamp"]).total_seconds() / 86400.0,
                    "recovered": True,
                }
            )
            in_dd = False
        if dd == 0:
            peak_idx = i
    if in_dd and start_idx is not None:
        seg = df.iloc[start_idx:].copy()
        trough_idx = int(seg["dd"].idxmin())
        end_idx = len(df) - 1
        episodes.append(
            {
                "variant": variant,
                "peak_idx": start_idx,
                "trough_idx": trough_idx,
                "recovery_idx": np.nan,
                "peak_time": df.iloc[start_idx]["timestamp"],
                "trough_time": df.iloc[trough_idx]["timestamp"],
                "recovery_time": pd.NaT,
                "peak_equity": float(df.iloc[start_idx]["equity"]),
                "trough_equity": float(df.iloc[trough_idx]["equity"]),
                "recovery_equity": float(df.iloc[end_idx]["equity"]),
                "depth_pct": -float(seg["dd"].min() * 100.0),
                "days_to_trough": (df.iloc[trough_idx]["timestamp"] - df.iloc[start_idx]["timestamp"]).total_seconds() / 86400.0,
                "days_to_recovery": (df.iloc[end_idx]["timestamp"] - df.iloc[start_idx]["timestamp"]).total_seconds() / 86400.0,
                "recovered": False,
            }
        )
    out = pd.DataFrame(episodes).sort_values("peak_time").reset_index(drop=True)
    out.insert(1, "episode_id", [f"U{i+1}" for i in range(len(out))])
    return out


def classify_episode(seg: pd.DataFrame) -> str:
    price_ret = (float(seg["close"].iloc[-1]) / float(seg["close"].iloc[0]) - 1.0) * 100.0
    long_share = float((seg["side"] > 0).mean() * 100.0)
    short_share = float((seg["side"] < 0).mean() * 100.0)
    flat_share = float((seg["side"] == 0).mean() * 100.0)
    bearish_share = float((seg["trend_4h_confirmed"] == "bearish").mean() * 100.0)
    gate_share = float(seg["short_gate_open"].astype(float).mean() * 100.0)
    side_changes = int((seg["side"].fillna(0).astype(int).diff().fillna(0) != 0).sum())
    if long_share >= 45.0 and price_ret <= -15.0:
        return "fast_selloff_long_stuck"
    if bearish_share >= 60.0 and flat_share >= 35.0 and gate_share <= 8.0:
        return "slow_bear_short_gap"
    if side_changes >= 10 and long_share >= 20.0 and short_share >= 20.0:
        return "two_way_whipsaw"
    return "mixed_trend_whipsaw"


def summarize_episode(episode: pd.Series, merged: pd.DataFrame) -> dict[str, float | int | str]:
    peak_time = pd.Timestamp(episode["peak_time"])
    trough_time = pd.Timestamp(episode["trough_time"])
    recovery_time = pd.Timestamp(episode["recovery_time"]) if pd.notna(episode["recovery_time"]) else pd.Timestamp(merged["timestamp"].max())
    seg_pt = merged[(merged["timestamp"] >= peak_time) & (merged["timestamp"] <= trough_time)].copy()
    seg_full = merged[(merged["timestamp"] >= peak_time) & (merged["timestamp"] <= recovery_time)].copy()
    price_peak = float(seg_pt["close"].iloc[0])
    price_trough = float(seg_pt["close"].iloc[-1])
    price_recovery = float(seg_full["close"].iloc[-1])
    return {
        "btc_peak_to_trough_pct": (price_trough / price_peak - 1.0) * 100.0,
        "btc_peak_to_recovery_pct": (price_recovery / price_peak - 1.0) * 100.0,
        "bullish_4h_share_pct": float((seg_pt["trend_4h_confirmed"] == "bullish").mean() * 100.0),
        "bearish_4h_share_pct": float((seg_pt["trend_4h_confirmed"] == "bearish").mean() * 100.0),
        "long_share_pct": float((seg_pt["side"] > 0).mean() * 100.0),
        "short_share_pct": float((seg_pt["side"] < 0).mean() * 100.0),
        "flat_share_pct": float((seg_pt["side"] == 0).mean() * 100.0),
        "short_gate_open_share_pct": float(seg_pt["short_gate_open"].astype(float).mean() * 100.0),
        "avg_bearish_ob_above_count": float(seg_pt["bearish_ob_above_count"].mean()),
        "avg_bullish_ob_below_count": float(seg_pt["bullish_ob_below_count"].mean()),
        "side_change_count": int((seg_pt["side"].fillna(0).astype(int).diff().fillna(0) != 0).sum()),
        "bulltrim_events_pt": int(seg_pt["bulltrim_event"].sum()),
        "unlock_events_pt": int(seg_pt["unlock_event"].sum()),
        "slow_bear_entries_pt": int(seg_pt["slow_bear_short_event"].sum()),
        "episode_label": classify_episode(seg_pt),
    }


def select_representative(episodes_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    deepest_df = episodes_df.sort_values(["depth_pct", "days_to_recovery"], ascending=[False, False]).head(TOP_DEPTH).copy()
    longest_df = episodes_df.sort_values(["days_to_recovery", "depth_pct"], ascending=[False, False]).head(TOP_DURATION).copy()
    rep_ids = set(deepest_df["episode_id"]).union(set(longest_df["episode_id"]))
    representative_df = episodes_df[episodes_df["episode_id"].isin(rep_ids)].copy().sort_values("peak_time").reset_index(drop=True)
    representative_df["is_representative"] = 1
    return deepest_df, longest_df, representative_df


def run_variant_138_state(df: pd.DataFrame, cfg: dict, s76, m117) -> tuple[pd.DataFrame, dict]:
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
        "blocked_long_quality_bearish_ob": 0,
        "blocked_long_quality_delay": 0,
        "blocked_long_quality_cap": 0,
        "blocked_long_quality_cooldown": 0,
        "bulltrim_count": 0,
        "unlock_short_lock_count": 0,
        "slow_bear_short_entries": 0,
        "survived_to_end": 1,
    }

    for i in range(len(df)):
        price_open = float(open_np[i])
        price_high = float(high_np[i])
        price_low = float(low_np[i])
        price_close = float(close_np[i])
        cur_trend = str(trend[i])
        blocked_reentry = False
        bulltrim_event = 0
        unlock_event = 0
        slow_bear_short_event = 0

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
            elif cur_trend == "bearish":
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
            stats["short_sweep_events"] += 1

        if unlock_short_lock_enabled and locked_side < 0 and cur_trend == "bearish" and bearish_streak >= slow_bear_bars and price_close < ema20[i]:
            locked_side = 0
            unlock_event = 1
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
                stats["trades"] += 1
                stats["liquidations"] += 1
                stats["survived_to_end"] = 0
            elif side < 0 and pos_leverage > 1.0 and price_high >= liq_price:
                wallet = max(reserve, 0.0)
                reserve = wallet
                margin = qty = entry = 0.0
                side = 0
                pos_leverage = 0.0
                entry_wallet = np.nan
                blocked_reentry = True
                stats["trades"] += 1
                stats["liquidations"] += 1
                stats["survived_to_end"] = 0
            elif side > 0 and price_low <= stop_price:
                wallet = s76._realize_close(reserve, margin, qty, entry, stop_price, side)
                reserve = wallet
                margin = qty = entry = 0.0
                side = 0
                pos_leverage = 0.0
                entry_wallet = np.nan
                blocked_reentry = True
                stats["trades"] += 1
                stats["stop_exits"] += 1
            elif side < 0 and price_high >= stop_price:
                wallet = s76._realize_close(reserve, margin, qty, entry, stop_price, side)
                reserve = wallet
                margin = qty = entry = 0.0
                side = 0
                pos_leverage = 0.0
                entry_wallet = np.nan
                blocked_reentry = True
                stats["trades"] += 1
                stats["stop_exits"] += 1
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
                    stats["trades"] += 1
                    stats["tp_exits"] += 1

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
            bulltrim_event = 1
            blocked_reentry = True
            stats["trades"] += 1
            stats["signal_exits"] += 1
            stats["long_entries"] += 1
            stats["bulltrim_count"] += 1

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
                margin = qty = entry = 0.0
                side = 0
                pos_leverage = 0.0
                entry_wallet = np.nan
                stats["trades"] += 1
                stats["signal_exits"] += 1

            if desired_side != 0 and wallet > 0:
                allow_entry = True
                used_gate = False
                used_slow_bear = False
                lev_to_open = base_leverage

                if desired_side < 0:
                    allow_entry = i <= short_gate_until and price_close < ema20[i]
                    used_gate = allow_entry
                    if not allow_entry and slow_bear_enabled and not slow_bear_used:
                        allow_entry = bearish_streak >= slow_bear_bars and price_close < ema20[i] and int(bearish_ob_above_count[i]) >= slow_bear_ob_threshold
                        used_slow_bear = allow_entry
                        if used_slow_bear:
                            lev_to_open = slow_bear_leverage
                    if not allow_entry:
                        stats["blocked_short_gate"] += 1

                if allow_entry and desired_side > 0:
                    if int(bearish_ob_above_count[i]) > max_bearish_above_for_long:
                        allow_entry = False
                        stats["blocked_long_quality_bearish_ob"] += 1
                    elif bullish_streak <= long_bullish_delay_bars:
                        allow_entry = False
                        stats["blocked_long_quality_delay"] += 1
                    elif long_short_sweep_cooldown_bars > 0 and (i - last_short_sweep_idx) <= long_short_sweep_cooldown_bars:
                        allow_entry = False
                        stats["blocked_long_quality_cooldown"] += 1
                    elif not pd.isna(long_premium_cap_red_avg_pct):
                        max_allowed_price = red_avg[i] * (1.0 + long_premium_cap_red_avg_pct / 100.0)
                        if price_close > max_allowed_price:
                            allow_entry = False
                            stats["blocked_long_quality_cap"] += 1

                if allow_entry and not m117.smc_entry_allowed(desired_side, int(bearish_ob_above_count[i]), int(bullish_ob_below_count[i]), 99, 0):
                    allow_entry = False

                if allow_entry:
                    reserve, margin, qty, entry = s76._open_position(wallet, price_close, lev_to_open, desired_side)
                    wallet = reserve + margin
                    side = desired_side
                    pos_leverage = lev_to_open
                    entry_wallet = wallet
                    if desired_side > 0:
                        stats["long_entries"] += 1
                    else:
                        stats["short_entries"] += 1
                        if used_slow_bear:
                            slow_bear_used = True
                            slow_bear_short_event = 1
                            stats["slow_bear_short_entries"] += 1
                    if used_gate:
                        stats["gated_entries"] += 1

        equity = wallet if side == 0 else s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
        rows.append(
            {
                "timestamp": ts[i],
                "equity": equity,
                "side": side,
                "locked_side": locked_side,
                "short_gate_open": int(i <= short_gate_until),
                "bulltrim_event": bulltrim_event,
                "unlock_event": unlock_event,
                "slow_bear_short_event": slow_bear_short_event,
                "variant": str(cfg["variant"]),
            }
        )

    if side != 0 and len(df):
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close_np[-1]), side)
        rows[-1]["equity"] = wallet
        rows[-1]["side"] = 0
        stats["trades"] += 1
    return pd.DataFrame(rows), stats


def save_plot(variant_curves: dict[str, pd.DataFrame], rep_map: dict[str, pd.DataFrame], variant_summary_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=False, gridspec_kw={"height_ratios": [1.4, 1.4, 1.0]})
    colors = ["#d62728", "#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]

    for ax_idx, variant in enumerate(VARIANT_ORDER):
        ax = axes[ax_idx]
        curve = variant_curves[variant]
        ax.plot(curve["timestamp"], curve["equity"], color="#111111", linewidth=1.0, label=variant)
        ax.axhline(1000.0, color="#777777", linestyle="--", linewidth=0.9)
        rep_df = rep_map[variant]
        for i, (_, row) in enumerate(rep_df.iterrows()):
            start = pd.Timestamp(row["peak_time"])
            end = pd.Timestamp(row["recovery_time"]) if pd.notna(row["recovery_time"]) else pd.Timestamp(curve["timestamp"].max())
            ax.axvspan(start, end, color=colors[i % len(colors)], alpha=0.14)
        ax.set_title(f"Study 140: {variant} representative weak periods")
        ax.set_ylabel("Equity (USDT)")
        ax.grid(True, alpha=0.2)
        ax.legend(loc="upper left")

    ax_bar = axes[2]
    x = np.arange(len(variant_summary_df))
    width = 0.35
    ax_bar.bar(x - width / 2, variant_summary_df["avg_rep_depth_pct"].to_numpy(dtype=float), width=width, color="#d62728", alpha=0.85, label="Avg Rep Depth %")
    ax_bar.set_ylabel("Avg Rep Depth %")
    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(variant_summary_df["variant"].tolist(), rotation=10)
    ax_bar.grid(True, axis="y", alpha=0.2)
    ax_bar_t = ax_bar.twinx()
    ax_bar_t.plot(x + width / 2, variant_summary_df["avg_rep_days_to_recovery"].to_numpy(dtype=float), color="#1f77b4", marker="o", linewidth=1.2, label="Avg Rep Days")
    ax_bar_t.set_ylabel("Avg Rep Days To Recovery")
    h1, l1 = ax_bar.get_legend_handles_labels()
    h2, l2 = ax_bar_t.get_legend_handles_labels()
    ax_bar.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(
    variant_summary_df: pd.DataFrame,
    top_depth_map: dict[str, pd.DataFrame],
    top_duration_map: dict[str, pd.DataFrame],
    rep_map: dict[str, pd.DataFrame],
    label_summary_df: pd.DataFrame,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
) -> None:
    lines: list[str] = []
    lines.append("# Study 140: Weak-state analysis for the two best row6 variants")
    lines.append("")
    lines.append("- Target variants: `unlock_slowbear_24h_2p0` and `combo_trim2p0_unlock24h`.")
    lines.append(f"- Analysis window: `{start_ts}` ~ `{end_ts}`.")
    lines.append("- Method: same `136` style underwater-episode study, but with extra event tracking for `bulltrim`, `unlock`, and `slow_bear_short`.")
    lines.append("")
    lines.append("## Variant Summary")
    lines.append("| Variant | CAGR % | MDD % | Calmar | 2026 Return % | Avg Rep Depth % | Avg Rep Days | Rep Episodes | Top Label |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for _, row in variant_summary_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{_fmt(row['return_2026_pct'])} | {_fmt(row['avg_rep_depth_pct'])} | {_fmt(row['avg_rep_days_to_recovery'], 1)} | "
            f"{int(row['representative_episode_count'])} | {row['top_label']} |"
        )
    lines.append("")

    for variant in VARIANT_ORDER:
        rep_df = rep_map[variant]
        depth_df = top_depth_map[variant]
        duration_df = top_duration_map[variant]
        lines.append(f"## {variant}")
        lines.append("")
        lines.append("### Deepest Top 5")
        lines.append("| Episode | Peak | Trough | Recovery | Depth % | Days To Recovery | BTC Peak->Trough % | Label | BullTrim | Unlock | SlowBear |")
        lines.append("| --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |")
        for _, row in depth_df.iterrows():
            recovery_text = row["recovery_time"] if pd.notna(row["recovery_time"]) else "unrecovered"
            lines.append(
                f"| {row['episode_id']} | {row['peak_time']} | {row['trough_time']} | {recovery_text} | {_fmt(row['depth_pct'])} | "
                f"{_fmt(row['days_to_recovery'], 1)} | {_fmt(row['btc_peak_to_trough_pct'])} | {row['episode_label']} | "
                f"{int(row['bulltrim_events_pt'])} | {int(row['unlock_events_pt'])} | {int(row['slow_bear_entries_pt'])} |"
            )
        lines.append("")
        lines.append("### Longest Top 5")
        lines.append("| Episode | Peak | Trough | Recovery | Depth % | Days To Recovery | Flat % | Bearish4h % | Gate Open % | Label |")
        lines.append("| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |")
        for _, row in duration_df.iterrows():
            recovery_text = row["recovery_time"] if pd.notna(row["recovery_time"]) else "unrecovered"
            lines.append(
                f"| {row['episode_id']} | {row['peak_time']} | {row['trough_time']} | {recovery_text} | {_fmt(row['depth_pct'])} | "
                f"{_fmt(row['days_to_recovery'], 1)} | {_fmt(row['flat_share_pct'])} | {_fmt(row['bearish_4h_share_pct'])} | "
                f"{_fmt(row['short_gate_open_share_pct'])} | {row['episode_label']} |"
            )
        lines.append("")
        lines.append("### Representative Windows")
        for _, row in rep_df.iterrows():
            recovery_text = row["recovery_time"] if pd.notna(row["recovery_time"]) else "unrecovered"
            lines.append(
                f"- `{row['episode_id']}` `{row['episode_label']}`: `{row['peak_time']}` -> `{row['trough_time']}` -> `{recovery_text}` / "
                f"BTC `{_fmt(row['btc_peak_to_trough_pct'])}%` / long `{_fmt(row['long_share_pct'])}%` short `{_fmt(row['short_share_pct'])}%` flat `{_fmt(row['flat_share_pct'])}%` / "
                f"bearish4h `{_fmt(row['bearish_4h_share_pct'])}%` / gate `{_fmt(row['short_gate_open_share_pct'])}%` / "
                f"bulltrim `{int(row['bulltrim_events_pt'])}` unlock `{int(row['unlock_events_pt'])}` slowbear `{int(row['slow_bear_entries_pt'])}`"
            )
        lines.append("")

    lines.append("## Label Summary")
    lines.append("| Variant | Label | Count | Avg Depth % | Avg Days | Avg BTC Peak->Trough % | Avg Long % | Avg Short % | Avg Flat % | Avg BullTrim | Avg Unlock | Avg SlowBear |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in label_summary_df.iterrows():
        lines.append(
            f"| {row['variant']} | {row['episode_label']} | {int(row['episode_count'])} | {_fmt(row['avg_depth_pct'])} | {_fmt(row['avg_days_to_recovery'], 1)} | "
            f"{_fmt(row['avg_btc_peak_to_trough_pct'])} | {_fmt(row['avg_long_share_pct'])} | {_fmt(row['avg_short_share_pct'])} | "
            f"{_fmt(row['avg_flat_share_pct'])} | {_fmt(row['avg_bulltrim_events'])} | {_fmt(row['avg_unlock_events'])} | {_fmt(row['avg_slow_bear_entries'])} |"
        )
    lines.append("")

    unlock_row = variant_summary_df[variant_summary_df["variant"] == "unlock_slowbear_24h_2p0"].iloc[0]
    combo_row = variant_summary_df[variant_summary_df["variant"] == "combo_trim2p0_unlock24h"].iloc[0]
    lines.append("## Quick Evaluation")
    lines.append(
        f"- `unlock_slowbear_24h_2p0` is the stronger raw engine: CAGR `{_fmt(unlock_row['cagr_pct'])}%`, but it pays with representative weak-window depth `{_fmt(unlock_row['avg_rep_depth_pct'])}%` and MDD `{_fmt(unlock_row['max_drawdown_pct'])}%`."
    )
    lines.append(
        f"- `combo_trim2p0_unlock24h` sacrifices some CAGR to reduce representative weak-window depth to `{_fmt(combo_row['avg_rep_depth_pct'])}%` and overall MDD to `{_fmt(combo_row['max_drawdown_pct'])}%`."
    )
    lines.append("- If representative episodes remain dominated by `slow_bear_short_gap`, the bottleneck is still slow bearish continuation handling.")
    lines.append("- If they shift toward `two_way_whipsaw`, the continuation-short fix is working and the remaining pain is mainly chop noise.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG.name}`")
    lines.append(f"- Episodes CSV: `{OUT_EPISODES_CSV.name}`")
    lines.append(f"- Label Summary CSV: `{OUT_LABEL_SUMMARY_CSV.name}`")
    lines.append(f"- Variant Summary CSV: `{OUT_VARIANT_SUMMARY_CSV.name}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV.name}`")
    lines.append(f"- Report: `{OUT_MD.name}`")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> None:
    m47 = load_module("study47_for_140", BASE_47_PATH)
    s76 = load_module("study76_for_140", BASE_76_PATH)
    m111 = load_module("study111_for_140", BASE_111_PATH)
    m114 = load_module("study114_for_140", BASE_114_PATH)
    m117 = load_module("study117_for_140", BASE_117_PATH)
    m126 = load_module("study126_for_140", BASE_126_PATH)

    df_1m, df_4h, end_ts = m114.load_market_data_2021plus()
    market = m114.prepare_market_114(df_1m.copy(), df_4h.copy(), m47, m111)

    base_cfg = next(cfg for cfg in m126.build_variants() if cfg["variant"] == BASE_VARIANT)
    trial_cfgs = {
        "unlock_slowbear_24h_2p0": {
            **base_cfg,
            "variant": "unlock_slowbear_24h_2p0",
            "bulltrim_enabled": False,
            "bulltrim_ob_threshold": 5,
            "bulltrim_leverage": 2.0,
            "unlock_short_lock_enabled": True,
            "slow_bear_enabled": True,
            "slow_bear_bars": 1440,
            "slow_bear_ob_threshold": 4,
            "slow_bear_leverage": 2.0,
        },
        "combo_trim2p0_unlock24h": {
            **base_cfg,
            "variant": "combo_trim2p0_unlock24h",
            "bulltrim_enabled": True,
            "bulltrim_ob_threshold": 5,
            "bulltrim_leverage": 2.0,
            "unlock_short_lock_enabled": True,
            "slow_bear_enabled": True,
            "slow_bear_bars": 1440,
            "slow_bear_ob_threshold": 4,
            "slow_bear_leverage": 2.0,
        },
    }

    variant_curves: dict[str, pd.DataFrame] = {}
    top_depth_map: dict[str, pd.DataFrame] = {}
    top_duration_map: dict[str, pd.DataFrame] = {}
    rep_map: dict[str, pd.DataFrame] = {}
    episode_frames: list[pd.DataFrame] = []
    summary_rows: list[dict] = []
    label_summary_rows: list[dict] = []

    for variant in VARIANT_ORDER:
        cfg = trial_cfgs[variant]
        curve, run_stats = run_variant_138_state(market, cfg, s76, m117)
        curve["timestamp"] = pd.to_datetime(curve["timestamp"])
        variant_curves[variant] = curve.copy()
        overall = compute_curve_stats(curve, s76.INITIAL_CAPITAL)
        stats_2026 = compute_window_stats(curve, ANALYSIS_2026_START)

        merged = pd.merge(
            curve[["timestamp", "equity", "side", "locked_side", "short_gate_open", "bulltrim_event", "unlock_event", "slow_bear_short_event"]],
            market[["timestamp", "close", "trend_4h_confirmed", "bearish_ob_above_count", "bullish_ob_below_count"]],
            on="timestamp",
            how="left",
        ).sort_values("timestamp").reset_index(drop=True)

        episodes_df = compute_underwater_episodes(curve, variant)
        episodes_df = pd.DataFrame([{**row.to_dict(), **summarize_episode(row, merged)} for _, row in episodes_df.iterrows()])
        deepest_df, longest_df, representative_df = select_representative(episodes_df)
        episodes_df["is_representative"] = episodes_df["episode_id"].isin(set(representative_df["episode_id"])).astype(int)

        top_depth_map[variant] = deepest_df
        top_duration_map[variant] = longest_df
        rep_map[variant] = representative_df
        episode_frames.append(episodes_df)

        label_counts = representative_df["episode_label"].value_counts()
        top_label = label_counts.index[0] if not label_counts.empty else "none"
        summary_rows.append(
            {
                "variant": variant,
                **overall,
                "return_2026_pct": stats_2026["window_return_pct"],
                "mdd_2026_pct": stats_2026["window_mdd_pct"],
                **run_stats,
                "episode_count": len(episodes_df),
                "representative_episode_count": len(representative_df),
                "avg_rep_depth_pct": float(representative_df["depth_pct"].mean()),
                "avg_rep_days_to_recovery": float(representative_df["days_to_recovery"].mean()),
                "deepest_rep_depth_pct": float(representative_df["depth_pct"].max()),
                "longest_rep_days_to_recovery": float(representative_df["days_to_recovery"].max()),
                "top_label": top_label,
            }
        )

        label_summary = (
            representative_df.groupby("episode_label")
            .agg(
                episode_count=("episode_id", "count"),
                avg_depth_pct=("depth_pct", "mean"),
                avg_days_to_recovery=("days_to_recovery", "mean"),
                avg_btc_peak_to_trough_pct=("btc_peak_to_trough_pct", "mean"),
                avg_long_share_pct=("long_share_pct", "mean"),
                avg_short_share_pct=("short_share_pct", "mean"),
                avg_flat_share_pct=("flat_share_pct", "mean"),
                avg_bulltrim_events=("bulltrim_events_pt", "mean"),
                avg_unlock_events=("unlock_events_pt", "mean"),
                avg_slow_bear_entries=("slow_bear_entries_pt", "mean"),
            )
            .reset_index()
        )
        for _, row in label_summary.iterrows():
            label_summary_rows.append({"variant": variant, **row.to_dict()})

    episodes_all_df = pd.concat(episode_frames, ignore_index=True)
    label_summary_df = pd.DataFrame(label_summary_rows).sort_values(["variant", "episode_count", "avg_depth_pct"], ascending=[True, False, False]).reset_index(drop=True)
    variant_summary_df = pd.DataFrame(summary_rows).sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).reset_index(drop=True)

    episodes_all_df.to_csv(OUT_EPISODES_CSV, index=False, encoding="utf-8-sig")
    label_summary_df.to_csv(OUT_LABEL_SUMMARY_CSV, index=False, encoding="utf-8-sig")
    variant_summary_df.to_csv(OUT_VARIANT_SUMMARY_CSV, index=False, encoding="utf-8-sig")
    pd.concat([variant_curves[v].assign(variant=v) for v in VARIANT_ORDER], ignore_index=True).to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")

    save_plot(variant_curves, rep_map, variant_summary_df)
    save_report(variant_summary_df, top_depth_map, top_duration_map, rep_map, label_summary_df, pd.Timestamp(market["timestamp"].min()), pd.Timestamp(end_ts))

    print(f"saved_plot={OUT_PNG.name}")
    print(f"saved_report={OUT_MD.name}")
    print(f"saved_episodes={OUT_EPISODES_CSV.name}")
    print(f"saved_label_summary={OUT_LABEL_SUMMARY_CSV.name}")
    print(f"saved_variant_summary={OUT_VARIANT_SUMMARY_CSV.name}")
    print(variant_summary_df[["variant", "cagr_pct", "max_drawdown_pct", "calmar_ratio", "avg_rep_depth_pct", "avg_rep_days_to_recovery", "top_label"]].to_string(index=False))


if __name__ == "__main__":
    run()
