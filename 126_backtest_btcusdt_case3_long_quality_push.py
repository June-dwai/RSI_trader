from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
BASE_76_PATH = Path("76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py")
BASE_111_PATH = Path("111_backtest_btcusdt_sr_smc_5m_profitmax.py")
BASE_114_PATH = Path("114_backtest_btcusdt_best_with_sr_smc_filters.py")
BASE_117_PATH = Path("117_backtest_btcusdt_115_highcagr_push.py")

OUT_BASE = "126_backtest_btcusdt_case3_long_quality_push"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

BASELINE_VARIANT = "baseline_case3_117"
BASELINE_CFG = {
    "variant": BASELINE_VARIANT,
    "leverage": 3.0,
    "gate_bars": 12,
    "body_atr_mult": 0.25,
    "short_tp_return_pct": 20.0,
    "max_bearish_above_for_long": 4,
    "long_bullish_delay_bars": 0,
    "long_premium_cap_red_avg_pct": np.nan,
    "long_short_sweep_cooldown_bars": 0,
}

BACKTEST_START = pd.Timestamp("2021-01-01")
ANALYSIS_2026_START = pd.Timestamp("2026-01-01 00:00:00")
CAGR_GUARDRAIL = 145.0


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


def compute_window_stats(curve: pd.DataFrame, start_ts: pd.Timestamp) -> dict:
    seg = curve[pd.to_datetime(curve["timestamp"]) >= pd.Timestamp(start_ts)].copy()
    if seg.empty:
        return {"window_return_pct": np.nan, "window_mdd_pct": np.nan}
    start_eq = float(seg["equity"].iloc[0])
    end_eq = float(seg["equity"].iloc[-1])
    dd = seg["equity"].astype(float) / seg["equity"].cummax().astype(float) - 1.0
    return {
        "window_return_pct": (end_eq / start_eq - 1.0) * 100.0,
        "window_mdd_pct": -float(dd.min() * 100.0),
    }


def build_variants() -> list[dict]:
    variants = [dict(BASELINE_CFG)]
    for max_bearish_above_for_long in [4, 3, 2]:
        for long_bullish_delay_bars in [0, 4, 8, 16]:
            for premium_cap in [np.nan, 1.5, 2.5]:
                for cooldown in [0, 8, 16]:
                    cfg = {
                        "variant": (
                            f"lb{max_bearish_above_for_long}_"
                            f"delay{long_bullish_delay_bars}_"
                            f"cap{'na' if pd.isna(premium_cap) else str(premium_cap).replace('.', 'p')}_"
                            f"cd{cooldown}"
                        ),
                        "leverage": 3.0,
                        "gate_bars": 12,
                        "body_atr_mult": 0.25,
                        "short_tp_return_pct": 20.0,
                        "max_bearish_above_for_long": max_bearish_above_for_long,
                        "long_bullish_delay_bars": long_bullish_delay_bars,
                        "long_premium_cap_red_avg_pct": premium_cap,
                        "long_short_sweep_cooldown_bars": cooldown,
                    }
                    if cfg == BASELINE_CFG:
                        continue
                    variants.append(cfg)
    return variants


def run_variant_126(df: pd.DataFrame, cfg: dict, s76, m117) -> tuple[pd.DataFrame, dict]:
    leverage = float(cfg["leverage"])
    gate_bars = int(cfg["gate_bars"])
    body_atr_mult = float(cfg["body_atr_mult"])
    short_tp_threshold = float(cfg["short_tp_return_pct"]) / 100.0
    max_bearish_above_for_long = int(cfg["max_bearish_above_for_long"])
    long_bullish_delay_bars = int(cfg["long_bullish_delay_bars"])
    long_premium_cap_red_avg_pct = float(cfg["long_premium_cap_red_avg_pct"]) if not pd.isna(cfg["long_premium_cap_red_avg_pct"]) else np.nan
    long_short_sweep_cooldown_bars = int(cfg["long_short_sweep_cooldown_bars"])

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
    bullish_streak = 0
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

        if cur_trend == "bullish":
            bullish_streak += 1
        else:
            bullish_streak = 0

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
                    if used_gate:
                        stats["gated_entries"] += 1

        equity = wallet if side == 0 else s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
        rows.append(
            {
                "timestamp": timestamps[i],
                "equity": equity,
                "wallet": wallet,
                "side": side,
                "variant": str(cfg["variant"]),
            }
        )

    if side != 0 and len(df):
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close_np[-1]), side)
        rows[-1]["equity"] = wallet
        rows[-1]["wallet"] = wallet
        rows[-1]["side"] = 0
        stats["trades"] += 1

    curve = pd.DataFrame(rows)
    stats["first_liquidation_ts"] = first_liq_ts
    return curve, stats


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame) -> None:
    baseline = BASELINE_VARIANT
    best_guardrail = metrics_df.iloc[0]["variant"]
    best_cagr = metrics_df.sort_values(["cagr_pct", "calmar_ratio"], ascending=[False, False]).iloc[0]["variant"]
    best_2026 = metrics_df[metrics_df["cagr_pct"] >= 140.0].sort_values(
        ["return_2026_pct", "mdd_2026_pct", "calmar_ratio"],
        ascending=[False, True, False],
    ).iloc[0]["variant"]
    baseline_row = metrics_df.loc[metrics_df["variant"] == baseline].iloc[0]
    balanced_pool = metrics_df[
        (metrics_df["cagr_pct"] > baseline_row["cagr_pct"])
        & (metrics_df["return_2026_pct"] > baseline_row["return_2026_pct"])
    ]
    best_balanced = (
        balanced_pool.sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]["variant"]
        if not balanced_pool.empty
        else best_guardrail
    )

    display = []
    for variant in [baseline, best_guardrail, best_balanced, best_2026]:
        if variant not in display:
            display.append(variant)

    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.1, 1.0, 1.0]})
    ax_eq, ax_perf, ax_long = axes
    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(display)}

    for variant in display:
        curve = curve_map[variant]
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(1000.0, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 126: Case3 Long Quality Push At 3x")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    top = metrics_df.head(12)
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

    ax_long.bar(top["variant"], top["long_entries"], color="#2ca02c", alpha=0.85, label="Long entries")
    ax_long.set_ylabel("Long Entries")
    ax_long.grid(True, axis="y", alpha=0.2)
    ax_long.tick_params(axis="x", rotation=20)
    ax_long_t = ax_long.twinx()
    ax_long_t.plot(top["variant"], top["return_2026_pct"], color="#9467bd", marker="o", linewidth=1.1, label="2026 Return %")
    ax_long_t.set_ylabel("2026 Return %")
    h1, l1 = ax_long.get_legend_handles_labels()
    h2, l2 = ax_long_t.get_legend_handles_labels()
    ax_long.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, cache_end_ts: pd.Timestamp, common_start: pd.Timestamp, common_end: pd.Timestamp) -> None:
    baseline = metrics_df.loc[metrics_df["variant"] == BASELINE_VARIANT].iloc[0]
    best_guardrail = metrics_df.iloc[0]
    best_cagr = metrics_df.sort_values(["cagr_pct", "calmar_ratio"], ascending=[False, False]).iloc[0]
    best_2026 = metrics_df[metrics_df["cagr_pct"] >= 140.0].sort_values(
        ["return_2026_pct", "mdd_2026_pct", "calmar_ratio"],
        ascending=[False, True, False],
    ).iloc[0]
    balanced_pool = metrics_df[
        (metrics_df["cagr_pct"] > baseline["cagr_pct"])
        & (metrics_df["return_2026_pct"] > baseline["return_2026_pct"])
    ]
    best_balanced = (
        balanced_pool.sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]
        if not balanced_pool.empty
        else best_guardrail
    )

    lines: list[str] = []
    lines.append("# 126 연구: case3 롱 품질 강화 실험")
    lines.append("")
    lines.append("## 설정")
    lines.append(f"- 공정 비교 구간: `{common_start}` ~ `{common_end}`")
    lines.append(f"- 로컬 최신 캐시 종료 시각: `{cache_end_ts}`")
    lines.append("- 기준 엔진은 study117 best인 `3.0x / gate12 / body25 / TP20 / long_block_threshold=5`다.")
    lines.append("- 숏 로직은 그대로 두고, 롱 진입 품질만 강화했다.")
    lines.append("- 실험한 롱 필터는 네 가지다.")
    lines.append("  1. 상단 bearish OB 허용 개수 축소")
    lines.append("  2. bullish 추세가 몇 바 유지된 뒤에만 롱 허용")
    lines.append("  3. red_avg 대비 과열 추격 롱 금지")
    lines.append("  4. short_sweep 직후 일정 바 동안 롱 금지")
    lines.append("")
    lines.append("## 기준선")
    lines.append(
        f"- `{baseline['variant']}`: CAGR `{_fmt(baseline['cagr_pct'])}%`, "
        f"MDD `{_fmt(baseline['max_drawdown_pct'])}%`, Calmar `{_fmt(baseline['calmar_ratio'])}`, "
        f"2026 수익률 `{_fmt(baseline['return_2026_pct'])}%`, long entries `{int(baseline['long_entries'])}`"
    )
    lines.append("")
    lines.append("## 승자")
    lines.append(
        f"- 고CAGR 유지 + Calmar 우승: `{best_guardrail['variant']}` -> CAGR `{_fmt(best_guardrail['cagr_pct'])}%`, "
        f"MDD `{_fmt(best_guardrail['max_drawdown_pct'])}%`, Calmar `{_fmt(best_guardrail['calmar_ratio'])}`, "
        f"2026 `{_fmt(best_guardrail['return_2026_pct'])}%`"
    )
    lines.append(
        f"- raw CAGR 우승: `{best_cagr['variant']}` -> CAGR `{_fmt(best_cagr['cagr_pct'])}%`, "
        f"MDD `{_fmt(best_cagr['max_drawdown_pct'])}%`, Calmar `{_fmt(best_cagr['calmar_ratio'])}`"
    )
    lines.append(
        f"- 균형형 추천(기준선보다 CAGR도 높고 2026도 덜 나쁨): `{best_balanced['variant']}` -> "
        f"CAGR `{_fmt(best_balanced['cagr_pct'])}%`, MDD `{_fmt(best_balanced['max_drawdown_pct'])}%`, "
        f"Calmar `{_fmt(best_balanced['calmar_ratio'])}`, 2026 `{_fmt(best_balanced['return_2026_pct'])}%`"
    )
    lines.append(
        f"- 2026 방어형 우승(cagr>=140): `{best_2026['variant']}` -> 2026 `{_fmt(best_2026['return_2026_pct'])}%`, "
        f"2026 MDD `{_fmt(best_2026['mdd_2026_pct'])}%`, CAGR `{_fmt(best_2026['cagr_pct'])}%`"
    )
    lines.append("")
    lines.append("## 상위 15개")
    lines.append("")
    lines.append("| Variant | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Long Entries | Short Entries |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.head(15).iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{_fmt(row['return_2026_pct'])} | {_fmt(row['mdd_2026_pct'])} | {int(row['long_entries'])} | {int(row['short_entries'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append("- baseline보다 좋아졌다면, 개선의 핵심은 숏을 더 잘한 게 아니라 저품질 롱을 얼마나 잘 잘라냈느냐에 있다.")
    lines.append("- `long_entries`가 너무 급감하는데 CAGR도 꺾이면 필터가 너무 과한 것이다.")
    lines.append("- 2026 손실 구간을 줄이려면 `상단 bearish OB 4개 근처 롱`과 `bullish 전환 직후 롱`을 특히 잘라내는 조합이 유력하다.")
    lines.append("")
    lines.append("## 출력물")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    m47 = load_module("study47_for_126", BASE_47_PATH)
    s76 = load_module("study76_for_126", BASE_76_PATH)
    m111 = load_module("study111_for_126", BASE_111_PATH)
    m114 = load_module("study114_for_126", BASE_114_PATH)
    m117 = load_module("study117_for_126", BASE_117_PATH)

    df_1m, df_4h, cache_end_ts = m114.load_market_data_2021plus()
    market = m114.prepare_market_114(df_1m.copy(), df_4h.copy(), m47, m111)
    common_start = pd.Timestamp(market["timestamp"].min())
    common_end = pd.Timestamp(market["timestamp"].max())

    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}
    variants = build_variants()
    print(f"Running {len(variants)} case3 long-quality variants...")

    for cfg in variants:
        curve, stats = run_variant_126(market, cfg, s76, m117)
        overall = compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL)
        stats_2026 = compute_window_stats(curve, ANALYSIS_2026_START)
        row = {
            "variant": cfg["variant"],
            "max_bearish_above_for_long": cfg["max_bearish_above_for_long"],
            "long_bullish_delay_bars": cfg["long_bullish_delay_bars"],
            "long_premium_cap_red_avg_pct": cfg["long_premium_cap_red_avg_pct"],
            "long_short_sweep_cooldown_bars": cfg["long_short_sweep_cooldown_bars"],
            **overall,
            "return_2026_pct": stats_2026["window_return_pct"],
            "mdd_2026_pct": stats_2026["window_mdd_pct"],
            **stats,
        }
        rows.append(row)
        curve_out = curve[["timestamp", "equity"]].copy()
        curve_out["variant"] = cfg["variant"]
        curve_rows.append(curve_out)
        curve_map[cfg["variant"]] = curve_out

    metrics_df = pd.DataFrame(rows)
    metrics_df["meets_cagr_guardrail"] = metrics_df["cagr_pct"] >= CAGR_GUARDRAIL
    metrics_df = metrics_df.sort_values(
        ["meets_cagr_guardrail", "calmar_ratio", "cagr_pct", "max_drawdown_pct"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)

    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    pd.concat(curve_rows, ignore_index=True).to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")
    save_plot(curve_map, metrics_df)
    save_report(metrics_df, pd.Timestamp(cache_end_ts), common_start, common_end)

    best = metrics_df.iloc[0]
    print(
        f"[126] Best guardrail variant: {best['variant']} "
        f"CAGR={_fmt(best['cagr_pct'])}% MDD={_fmt(best['max_drawdown_pct'])}% "
        f"Calmar={_fmt(best['calmar_ratio'])} 2026={_fmt(best['return_2026_pct'])}%"
    )
    print(f"[126] Outputs: {OUT_CSV}, {OUT_MD}, {OUT_PNG}")


if __name__ == "__main__":
    main()
