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

OUT_BASE = "137_backtest_btcusdt_row6_improvement_trials"
OUT_CSV = ROOT / f"{OUT_BASE}.csv"
OUT_MD = ROOT / f"{OUT_BASE}.md"
OUT_PNG = ROOT / f"{OUT_BASE}.png"
OUT_CURVES_CSV = ROOT / f"{OUT_BASE}_curves.csv"

BASE_VARIANT = "lb4_delay8_capna_cd0"
ANALYSIS_2026_START = pd.Timestamp("2026-01-01 00:00:00")


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
    return "N/A" if pd.isna(v) else f"{float(v):.{digits}f}"


def compute_curve_stats(curve: pd.DataFrame, initial_capital: float) -> dict[str, float]:
    series = curve["equity"].astype(float)
    final_equity = float(series.iloc[-1])
    total_return_pct = (final_equity / float(initial_capital) - 1.0) * 100.0
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


def run_variant(df: pd.DataFrame, cfg: dict, s76, m117) -> tuple[pd.DataFrame, dict[str, float]]:
    leverage = float(cfg["leverage"])
    gate_bars = int(cfg["gate_bars"])
    body_atr_mult = float(cfg["body_atr_mult"])
    short_tp_threshold = float(cfg["short_tp_return_pct"]) / 100.0
    max_bearish_above_for_long = int(cfg["max_bearish_above_for_long"])
    long_bullish_delay_bars = int(cfg["long_bullish_delay_bars"])
    long_premium_cap_red_avg_pct = float(cfg["long_premium_cap_red_avg_pct"]) if not pd.isna(cfg["long_premium_cap_red_avg_pct"]) else np.nan
    long_short_sweep_cooldown_bars = int(cfg["long_short_sweep_cooldown_bars"])
    prebear_exit_enabled = bool(cfg["prebear_exit_enabled"])
    prebear_ob_threshold = int(cfg["prebear_ob_threshold"])
    prebear_cooldown_bars = int(cfg["prebear_cooldown_bars"])
    slow_bear_short_enabled = bool(cfg["slow_bear_short_enabled"])
    slow_bear_min_bars = int(cfg["slow_bear_min_bars"])
    slow_bear_min_ob_count = int(cfg["slow_bear_min_ob_count"])

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
    bullish_streak = 0
    bearish_streak = 0
    last_short_sweep_idx = -10**9
    long_reentry_block_until = -10**9

    rows: list[dict[str, float | str | int]] = []
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
        "blocked_long_prebear_cooldown": 0,
        "prebear_exit_count": 0,
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

        bullish_streak = bullish_streak + 1 if cur_trend == "bullish" else 0
        bearish_streak = bearish_streak + 1 if cur_trend == "bearish" else 0

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
            last_short_sweep_idx = i
            stats["short_sweep_events"] += 1

        # Early long de-risk before 4h bearish confirmation fully bites.
        if (
            prebear_exit_enabled
            and side > 0
            and cur_trend == "bullish"
            and price_close < ema20[i]
            and int(bearish_ob_above_count[i]) >= prebear_ob_threshold
        ):
            wallet = s76._realize_close(reserve, margin, qty, entry, price_close, side)
            reserve = wallet
            margin = 0.0
            qty = 0.0
            entry = 0.0
            side = 0
            entry_wallet = np.nan
            blocked_reentry = True
            long_reentry_block_until = max(long_reentry_block_until, i + prebear_cooldown_bars)
            stats["trades"] += 1
            stats["signal_exits"] += 1
            stats["prebear_exit_count"] += 1

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
                used_slow_bear_short = False

                if desired_side < 0:
                    allow_entry = i <= short_gate_until and price_close < ema20[i]
                    used_gate = allow_entry
                    if not allow_entry and slow_bear_short_enabled:
                        allow_entry = (
                            bearish_streak >= slow_bear_min_bars
                            and price_close < ema20[i]
                            and int(bearish_ob_above_count[i]) >= slow_bear_min_ob_count
                        )
                        used_slow_bear_short = allow_entry
                    if not allow_entry and not used_slow_bear_short:
                        stats["blocked_short_gate"] += 1

                if allow_entry and desired_side > 0:
                    if i <= long_reentry_block_until:
                        allow_entry = False
                        stats["blocked_long_prebear_cooldown"] += 1
                    elif int(bearish_ob_above_count[i]) > max_bearish_above_for_long:
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

                if allow_entry and not m117.smc_entry_allowed(
                    desired_side,
                    int(bearish_ob_above_count[i]),
                    int(bullish_ob_below_count[i]),
                    99,
                    0,
                ):
                    allow_entry = False

                if allow_entry:
                    reserve, margin, qty, entry = s76._open_position(wallet, price_close, leverage, desired_side)
                    wallet = reserve + margin
                    side = desired_side
                    entry_wallet = wallet
                    if desired_side > 0:
                        stats["long_entries"] += 1
                    else:
                        stats["short_entries"] += 1
                        if used_slow_bear_short:
                            stats["slow_bear_short_entries"] += 1
                    if used_gate:
                        stats["gated_entries"] += 1

        equity = wallet if side == 0 else s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
        rows.append(
            {
                "timestamp": timestamps[i],
                "equity": equity,
                "side": side,
                "short_gate_open": int(i <= short_gate_until),
                "variant": str(cfg["variant"]),
            }
        )

    if side != 0 and len(df):
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close_np[-1]), side)
        rows[-1]["equity"] = wallet
        rows[-1]["side"] = 0
        stats["trades"] += 1

    return pd.DataFrame(rows), stats


def save_plot(curves_df: pd.DataFrame, metrics_df: pd.DataFrame) -> None:
    order = metrics_df["variant"].tolist()
    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(order)}

    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_perf, ax_2026 = axes

    for variant in order:
        curve = curves_df[curves_df["variant"] == variant]
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(1000.0, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 137: Row6 Improvement Trials")
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

    ax_2026.bar(metrics_df["variant"], metrics_df["return_2026_pct"], color=[colors[v] for v in order], alpha=0.85, label="2026 Return %")
    ax_2026.set_ylabel("2026 Return %")
    ax_2026.grid(True, axis="y", alpha=0.2)
    ax_2026.tick_params(axis="x", rotation=18)
    ax_2026_t = ax_2026.twinx()
    ax_2026_t.plot(metrics_df["variant"], metrics_df["mdd_2026_pct"], color="#9467bd", marker="o", linewidth=1.1, label="2026 MDD %")
    ax_2026_t.set_ylabel("2026 MDD %")
    h1, l1 = ax_2026.get_legend_handles_labels()
    h2, l2 = ax_2026_t.get_legend_handles_labels()
    ax_2026.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> None:
    baseline = metrics_df[metrics_df["variant"] == "baseline_row6"].iloc[0]
    best_calmar = metrics_df.sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]
    best_2026 = metrics_df.sort_values(["return_2026_pct", "mdd_2026_pct", "calmar_ratio"], ascending=[False, True, False]).iloc[0]

    lines: list[str] = []
    lines.append("# 137번 연구: row6 개선 실험")
    lines.append("")
    lines.append("## 설정")
    lines.append("- 기준 전략은 `lb4_delay8_capna_cd0`이다.")
    lines.append(f"- 비교 구간은 `{start_ts}` ~ `{end_ts}` 이다.")
    lines.append("- 이번 실험은 두 가지 개선축을 본다.")
    lines.append("  1. bearish 전환 전조에서 롱을 먼저 접고 4시간 동안 롱 재진입을 막는 `pre-bear exit`")
    lines.append("  2. sweep가 없어도 장시간 bearish 상태가 이어지면 숏을 허용하는 `slow bear continuation short`")
    lines.append("")
    lines.append("## 결과 표")
    lines.append("")
    lines.append("| Variant | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Prebear Exits | Slow Bear Shorts |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{_fmt(row['return_2026_pct'])} | {_fmt(row['mdd_2026_pct'])} | {int(row['prebear_exit_count'])} | {int(row['slow_bear_short_entries'])} |"
        )
    lines.append("")
    lines.append("## 읽는 법")
    lines.append(
        f"- baseline은 CAGR `{_fmt(baseline['cagr_pct'])}%`, MDD `{_fmt(baseline['max_drawdown_pct'])}%`, Calmar `{_fmt(baseline['calmar_ratio'])}`, 2026 `{_fmt(baseline['return_2026_pct'])}%`였다."
    )
    lines.append(
        f"- 전체 균형 우승은 `{best_calmar['variant']}`였다. Calmar `{_fmt(best_calmar['calmar_ratio'])}`, CAGR `{_fmt(best_calmar['cagr_pct'])}%`, MDD `{_fmt(best_calmar['max_drawdown_pct'])}%`."
    )
    lines.append(
        f"- 2026 방어 우승은 `{best_2026['variant']}`였다. 2026 return `{_fmt(best_2026['return_2026_pct'])}%`, 2026 MDD `{_fmt(best_2026['mdd_2026_pct'])}%`."
    )
    lines.append("")
    lines.append("## 해석")
    lines.append("- `pre-bear exit`는 급락 초입 롱 잔류를 줄이는 쪽을 겨냥했다.")
    lines.append("- `slow bear short`는 느린 약세장에서 숏을 못 잡는 문제를 겨냥했다.")
    lines.append("- 둘을 합친 결과가 baseline보다 좋아졌다면, row6의 약점이 실제로 이 두 축에 있다는 뜻이다.")
    lines.append("- 반대로 개선이 약하거나 오히려 나빠졌다면, 이 문제는 규칙 추가보다 레버리지나 엔진 구조 문제가 더 크다는 뜻에 가깝다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- Plot: `{OUT_PNG.name}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV.name}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV.name}`")
    lines.append(f"- Report: `{OUT_MD.name}`")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    m47 = load_module("study47_for_137", BASE_47_PATH)
    s76 = load_module("study76_for_137", BASE_76_PATH)
    m111 = load_module("study111_for_137", BASE_111_PATH)
    m114 = load_module("study114_for_137", BASE_114_PATH)
    m117 = load_module("study117_for_137", BASE_117_PATH)
    m126 = load_module("study126_for_137", BASE_126_PATH)

    df_1m, df_4h, end_ts = m114.load_market_data_2021plus()
    market = m114.prepare_market_114(df_1m.copy(), df_4h.copy(), m47, m111)

    base_cfg = next(cfg for cfg in m126.build_variants() if cfg["variant"] == BASE_VARIANT)
    trial_cfgs = [
        {
            **base_cfg,
            "variant": "baseline_row6",
            "prebear_exit_enabled": False,
            "prebear_ob_threshold": 5,
            "prebear_cooldown_bars": 240,
            "slow_bear_short_enabled": False,
            "slow_bear_min_bars": 720,
            "slow_bear_min_ob_count": 4,
        },
        {
            **base_cfg,
            "variant": "prebear_exit_ob5_cool4h",
            "prebear_exit_enabled": True,
            "prebear_ob_threshold": 5,
            "prebear_cooldown_bars": 240,
            "slow_bear_short_enabled": False,
            "slow_bear_min_bars": 720,
            "slow_bear_min_ob_count": 4,
        },
        {
            **base_cfg,
            "variant": "slowbear_short_12h_ob4",
            "prebear_exit_enabled": False,
            "prebear_ob_threshold": 5,
            "prebear_cooldown_bars": 240,
            "slow_bear_short_enabled": True,
            "slow_bear_min_bars": 720,
            "slow_bear_min_ob_count": 4,
        },
        {
            **base_cfg,
            "variant": "slowbear_short_24h_ob4",
            "prebear_exit_enabled": False,
            "prebear_ob_threshold": 5,
            "prebear_cooldown_bars": 240,
            "slow_bear_short_enabled": True,
            "slow_bear_min_bars": 1440,
            "slow_bear_min_ob_count": 4,
        },
        {
            **base_cfg,
            "variant": "combo_prebear_plus_slow12h",
            "prebear_exit_enabled": True,
            "prebear_ob_threshold": 5,
            "prebear_cooldown_bars": 240,
            "slow_bear_short_enabled": True,
            "slow_bear_min_bars": 720,
            "slow_bear_min_ob_count": 4,
        },
    ]

    rows = []
    curves = []
    for cfg in trial_cfgs:
        print(f"running={cfg['variant']}")
        curve, run_stats = run_variant(market, cfg, s76, m117)
        curve["timestamp"] = pd.to_datetime(curve["timestamp"])
        overall = compute_curve_stats(curve, s76.INITIAL_CAPITAL)
        stats_2026 = compute_window_stats(curve, ANALYSIS_2026_START)
        rows.append(
            {
                "variant": cfg["variant"],
                **overall,
                "return_2026_pct": stats_2026["window_return_pct"],
                "mdd_2026_pct": stats_2026["window_mdd_pct"],
                **run_stats,
            }
        )
        curves.append(curve[["timestamp", "equity"]].assign(variant=cfg["variant"]))

    metrics_df = pd.DataFrame(rows).sort_values(
        ["calmar_ratio", "cagr_pct", "max_drawdown_pct"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    curves_df = pd.concat(curves, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    curves_df.to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")
    save_plot(curves_df, metrics_df)
    save_report(metrics_df, pd.Timestamp(market["timestamp"].min()), pd.Timestamp(end_ts))

    print(f"saved_plot={OUT_PNG.name}")
    print(f"saved_metrics={OUT_CSV.name}")
    print(f"saved_curves={OUT_CURVES_CSV.name}")
    print(f"saved_report={OUT_MD.name}")
    print(metrics_df[["variant", "cagr_pct", "max_drawdown_pct", "calmar_ratio", "return_2026_pct", "mdd_2026_pct", "prebear_exit_count", "slow_bear_short_entries"]].to_string(index=False))


if __name__ == "__main__":
    main()
