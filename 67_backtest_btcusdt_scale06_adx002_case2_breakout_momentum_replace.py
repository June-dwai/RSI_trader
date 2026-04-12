from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
CASE1_CURVES_CSV = Path("62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune_curves.csv")

OUT_BASE = "67_backtest_btcusdt_scale06_adx002_case2_breakout_momentum_replace"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

INITIAL_CAPITAL_CASE = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
COMMISSION = 0.0004

CASE1_VARIANT = "shallow6_else2bull"
EXPECTED_BASELINE_TOTAL = {
    "final_equity": 37042.70606845802,
    "cagr_pct": 103.27812652063195,
    "mdd_pct": 50.853607894861834,
}

VARIANTS = [
    {"variant": "baseline_case2", "mode": "baseline"},
    {
        "variant": "dual_240_fast",
        "mode": "momentum",
        "allow_long": True,
        "allow_short": True,
        "lookback_bars": 240,
        "entry_scale": 0.80,
        "stop_pct": 0.010,
        "trail_arm_pct": 0.014,
        "trail_gap_pct": 0.008,
        "max_entries": 2,
        "add_step_pct": 0.008,
        "cooldown_bars": 30,
    },
    {
        "variant": "dual_720_slow",
        "mode": "momentum",
        "allow_long": True,
        "allow_short": True,
        "lookback_bars": 720,
        "entry_scale": 0.80,
        "stop_pct": 0.012,
        "trail_arm_pct": 0.018,
        "trail_gap_pct": 0.010,
        "max_entries": 2,
        "add_step_pct": 0.010,
        "cooldown_bars": 60,
    },
    {
        "variant": "dual_240_aggr",
        "mode": "momentum",
        "allow_long": True,
        "allow_short": True,
        "lookback_bars": 240,
        "entry_scale": 1.00,
        "stop_pct": 0.009,
        "trail_arm_pct": 0.012,
        "trail_gap_pct": 0.007,
        "max_entries": 3,
        "add_step_pct": 0.007,
        "cooldown_bars": 20,
    },
    {
        "variant": "short_240_fast",
        "mode": "momentum",
        "allow_long": False,
        "allow_short": True,
        "lookback_bars": 240,
        "entry_scale": 1.00,
        "stop_pct": 0.010,
        "trail_arm_pct": 0.014,
        "trail_gap_pct": 0.008,
        "max_entries": 2,
        "add_step_pct": 0.008,
        "cooldown_bars": 20,
    },
    {
        "variant": "short_720_slow",
        "mode": "momentum",
        "allow_long": False,
        "allow_short": True,
        "lookback_bars": 720,
        "entry_scale": 0.80,
        "stop_pct": 0.012,
        "trail_arm_pct": 0.018,
        "trail_gap_pct": 0.010,
        "max_entries": 2,
        "add_step_pct": 0.010,
        "cooldown_bars": 60,
    },
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


def load_case1_curve() -> pd.DataFrame:
    curves = pd.read_csv(CASE1_CURVES_CSV, parse_dates=["timestamp"])
    case1 = curves[curves["variant"] == CASE1_VARIANT][["timestamp", "equity_case1"]].copy()
    if case1.empty:
        raise ValueError(f"missing case1 variant {CASE1_VARIANT}")
    return case1.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)


def load_baseline_case2_curve() -> pd.DataFrame:
    curves = pd.read_csv(CASE1_CURVES_CSV, parse_dates=["timestamp"])
    case2 = curves[curves["variant"] == CASE1_VARIANT][["timestamp", "equity_case2"]].copy()
    return case2.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)


def build_total_curve(case1_curve: pd.DataFrame, case2_curve: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge(case1_curve, case2_curve, on="timestamp", how="outer").sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2"]).copy()
    merged["equity_total"] = merged["equity_case1"] + merged["equity_case2"]
    return merged


def prepare_market(m47, start_ts: pd.Timestamp, end_ts: pd.Timestamp, lookbacks: list[int]) -> pd.DataFrame:
    df_1m, df_4h = m47.load_data_no_filter()
    df_1m = df_1m[(df_1m.index >= start_ts) & (df_1m.index <= end_ts)].copy()
    df_4h = df_4h[(df_4h.index >= start_ts.floor("4h") - pd.Timedelta(days=60)) & (df_4h.index <= end_ts.ceil("4h"))].copy()

    df_4h["ema200_closed"] = df_4h["close"].ewm(span=m47.EMA_PERIOD, adjust=False).mean()
    df_4h["ema200_prev_closed"] = df_4h["ema200_closed"].shift(1)
    df_4h["trend_4h_hyst"] = m47.LiveParityNoLookahead._compute_hysteresis_state(
        df_4h["close"], df_4h["ema200_prev_closed"], m47.HYSTERESIS_BAND
    )
    df_4h["trend_4h_confirmed"] = df_4h["trend_4h_hyst"].shift(1)

    out = df_1m[["open", "high", "low", "close"]].copy()
    out["bucket_4h"] = out.index.floor("4h")
    out = out.merge(df_4h[["trend_4h_confirmed"]], left_on="bucket_4h", right_index=True, how="left")
    out["trend_4h_confirmed"] = out["trend_4h_confirmed"].ffill()
    for lookback in sorted(set(lookbacks)):
        out[f"break_high_{lookback}"] = out["high"].rolling(lookback).max().shift(1)
        out[f"break_low_{lookback}"] = out["low"].rolling(lookback).min().shift(1)
    return out.reset_index().rename(columns={"index": "timestamp"})


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


def run_momentum_case2(market: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    lookback = int(cfg["lookback_bars"])
    break_high = market[f"break_high_{lookback}"].to_numpy(dtype=float)
    break_low = market[f"break_low_{lookback}"].to_numpy(dtype=float)
    close = market["close"].to_numpy(dtype=float)
    trend = market["trend_4h_confirmed"].fillna("").to_numpy()
    timestamps = market["timestamp"].to_numpy()

    entry_scale = float(cfg["entry_scale"])
    stop_pct = float(cfg["stop_pct"])
    trail_arm_pct = float(cfg["trail_arm_pct"])
    trail_gap_pct = float(cfg["trail_gap_pct"])
    max_entries = int(cfg["max_entries"])
    add_step_pct = float(cfg["add_step_pct"])
    cooldown_bars = int(cfg["cooldown_bars"])
    allow_long = bool(cfg["allow_long"])
    allow_short = bool(cfg["allow_short"])

    capital = INITIAL_CAPITAL_CASE
    side = 0
    avg_entry = 0.0
    qty = 0.0
    base_qty = 0.0
    entry_count = 0
    last_order_idx = -10**9
    best_price = np.nan
    next_add_price = np.nan

    equity_rows: list[dict] = []
    stats = {
        "trades": 0,
        "long_entries": 0,
        "short_entries": 0,
        "winner_adds": 0,
        "stop_exits": 0,
        "trail_exits": 0,
        "regime_exits": 0,
    }

    for i in range(len(market)):
        price = float(close[i])
        cur_trend = str(trend[i])

        if side != 0:
            if side > 0:
                best_price = price if np.isnan(best_price) else max(best_price, price)
                if entry_count < max_entries and cur_trend == "bullish" and price >= next_add_price:
                    add_qty = min(base_qty, (capital / price) * entry_scale)
                    if add_qty > 0:
                        capital -= add_qty * price * COMMISSION
                        total_qty = qty + add_qty
                        avg_entry = ((avg_entry * qty) + (price * add_qty)) / total_qty
                        qty = total_qty
                        entry_count += 1
                        next_add_price = price * (1.0 + add_step_pct)
                        last_order_idx = i
                        stats["winner_adds"] += 1

                trail_armed = best_price >= avg_entry * (1.0 + trail_arm_pct)
                exit_reason = None
                if cur_trend == "bearish":
                    exit_reason = "regime"
                elif price <= avg_entry * (1.0 - stop_pct):
                    exit_reason = "stop"
                elif trail_armed and price <= best_price * (1.0 - trail_gap_pct):
                    exit_reason = "trail"
            else:
                best_price = price if np.isnan(best_price) else min(best_price, price)
                if entry_count < max_entries and cur_trend == "bearish" and price <= next_add_price:
                    add_qty = min(base_qty, (capital / price) * entry_scale)
                    if add_qty > 0:
                        capital -= add_qty * price * COMMISSION
                        total_qty = qty + add_qty
                        avg_entry = ((avg_entry * qty) + (price * add_qty)) / total_qty
                        qty = total_qty
                        entry_count += 1
                        next_add_price = price * (1.0 - add_step_pct)
                        last_order_idx = i
                        stats["winner_adds"] += 1

                trail_armed = best_price <= avg_entry * (1.0 - trail_arm_pct)
                exit_reason = None
                if cur_trend == "bullish":
                    exit_reason = "regime"
                elif price >= avg_entry * (1.0 + stop_pct):
                    exit_reason = "stop"
                elif trail_armed and price >= best_price * (1.0 + trail_gap_pct):
                    exit_reason = "trail"

            if exit_reason is not None:
                capital = _close_position(capital, side, avg_entry, qty, price)
                side = 0
                avg_entry = 0.0
                qty = 0.0
                base_qty = 0.0
                entry_count = 0
                best_price = np.nan
                next_add_price = np.nan
                last_order_idx = i
                stats["trades"] += 1
                if exit_reason == "stop":
                    stats["stop_exits"] += 1
                elif exit_reason == "trail":
                    stats["trail_exits"] += 1
                else:
                    stats["regime_exits"] += 1

        if side == 0 and i - last_order_idx >= cooldown_bars:
            if allow_long and cur_trend == "bullish" and pd.notna(break_high[i]) and price > float(break_high[i]):
                open_qty = (capital / price) * entry_scale
                if open_qty > 0:
                    capital -= open_qty * price * COMMISSION
                    side = 1
                    avg_entry = price
                    qty = open_qty
                    base_qty = open_qty
                    entry_count = 1
                    best_price = price
                    next_add_price = price * (1.0 + add_step_pct)
                    last_order_idx = i
                    stats["long_entries"] += 1
            elif allow_short and cur_trend == "bearish" and pd.notna(break_low[i]) and price < float(break_low[i]):
                open_qty = (capital / price) * entry_scale
                if open_qty > 0:
                    capital -= open_qty * price * COMMISSION
                    side = -1
                    avg_entry = price
                    qty = open_qty
                    base_qty = open_qty
                    entry_count = 1
                    best_price = price
                    next_add_price = price * (1.0 - add_step_pct)
                    last_order_idx = i
                    stats["short_entries"] += 1

        equity_rows.append({"timestamp": timestamps[i], "equity_case2": _mark_to_market(capital, side, avg_entry, qty, price)})

    if side != 0 and len(market):
        last_price = float(close[-1])
        capital = _close_position(capital, side, avg_entry, qty, last_price)
        equity_rows[-1]["equity_case2"] = capital
        stats["trades"] += 1

    return pd.DataFrame(equity_rows), stats


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
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(INITIAL_CAPITAL_TOTAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("67 Study: Replace Case2 With Regime-Aware Breakout Momentum")
    ax_eq.set_ylabel("Total Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_cagr.bar(metrics_df["variant"], metrics_df["total_cagr_pct"], color=[colors[v] for v in variants], alpha=0.85, label="Total CAGR %")
    ax_cagr.set_ylabel("Total CAGR %")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr.tick_params(axis="x", rotation=20)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(metrics_df["variant"], metrics_df["total_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="Total MDD %")
    ax_cagr_t.set_ylabel("Total MDD %")
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_mdd.bar(metrics_df["variant"], metrics_df["case2_cagr_pct"], color=[colors[v] for v in variants], alpha=0.85, label="Case2 CAGR %")
    ax_mdd.set_ylabel("Case2 CAGR %")
    ax_mdd.grid(True, axis="y", alpha=0.2)
    ax_mdd.tick_params(axis="x", rotation=20)
    ax_mdd_t = ax_mdd.twinx()
    ax_mdd_t.plot(metrics_df["variant"], metrics_df["case2_mdd_pct"], color="#9467bd", marker="o", linewidth=1.1, label="Case2 MDD %")
    ax_mdd_t.set_ylabel("Case2 MDD %")
    h1, l1 = ax_mdd.get_legend_handles_labels()
    h2, l2 = ax_mdd_t.get_legend_handles_labels()
    ax_mdd.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    baseline = metrics_df[metrics_df["variant"] == "baseline_case2"].iloc[0]
    best = metrics_df.iloc[0]

    lines: list[str] = []
    lines.append("# Study 67: Replace Case2 With Regime-Aware Breakout Momentum")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Fixed case1 variant: `{CASE1_VARIANT}` from study 62")
    lines.append("- New case2 family: no-lookahead 1m breakout momentum gated by confirmed 4h hysteresis trend")
    lines.append("- Entry uses prior rolling breakout levels only (`shift(1)`), so no future bars are referenced")
    lines.append("- Goal: improve total CAGR / MDD frontier by making case2 more orthogonal to case1")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | Total CAGR % | Total MDD % | Total Calmar | Case2 CAGR % | Case2 MDD % | Trades | Winner Adds |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['total_cagr_pct'])} | {_fmt(row['total_mdd_pct'])} | {_fmt(row['total_calmar_ratio'])} | "
            f"{_fmt(row['case2_cagr_pct'])} | {_fmt(row['case2_mdd_pct'])} | {_fmt_count(row['case2_trades'])} | {_fmt_count(row['winner_adds'])} |"
        )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}`: total CAGR `{_fmt(best['total_cagr_pct'])}%`, total MDD `{_fmt(best['total_mdd_pct'])}%`, total Calmar `{_fmt(best['total_calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Delta vs baseline_case2")
    for _, row in metrics_df.iterrows():
        if row["variant"] == "baseline_case2":
            continue
        lines.append(
            f"- `{row['variant']}`: CAGR `{_fmt(row['total_cagr_pct'] - baseline['total_cagr_pct'])}pp`, "
            f"MDD `{_fmt(row['total_mdd_pct'] - baseline['total_mdd_pct'])}pp`, "
            f"Calmar `{_fmt(row['total_calmar_ratio'] - baseline['total_calmar_ratio'])}`"
        )
    lines.append("")
    lines.append("## Interpretation")
    if ((metrics_df["total_cagr_pct"] > baseline["total_cagr_pct"]) & (metrics_df["total_mdd_pct"] < baseline["total_mdd_pct"])).any():
        lines.append("- At least one replacement case2 dominated the current baseline on both total CAGR and total MDD.")
    else:
        lines.append("- No replacement case2 dominated the current baseline on both total CAGR and total MDD.")
    lines.append("- If dual breakout variants outperform short-only variants, case2 should remain a full orthogonal alpha engine instead of a pure hedge sleeve.")
    lines.append("- If short-only variants reduce MDD but crush CAGR, then protection is being bought too expensively and case2 needs a better bull-side alpha component.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    case1_curve = load_case1_curve()
    baseline_case2_curve = load_baseline_case2_curve()
    baseline_total = build_total_curve(case1_curve, baseline_case2_curve)
    baseline_stats = compute_curve_stats(baseline_total, "equity_total", INITIAL_CAPITAL_TOTAL)
    if abs(baseline_stats["final_equity"] - EXPECTED_BASELINE_TOTAL["final_equity"]) > 1e-6:
        raise ValueError("baseline final equity mismatch")
    if abs(baseline_stats["cagr_pct"] - EXPECTED_BASELINE_TOTAL["cagr_pct"]) > 1e-6:
        raise ValueError("baseline cagr mismatch")
    if abs(baseline_stats["max_drawdown_pct"] - EXPECTED_BASELINE_TOTAL["mdd_pct"]) > 1e-6:
        raise ValueError("baseline mdd mismatch")

    m47 = load_module("study47_for_67", BASE_47_PATH)
    market = prepare_market(
        m47,
        start_ts=pd.Timestamp(case1_curve["timestamp"].iloc[0]),
        end_ts=pd.Timestamp(case1_curve["timestamp"].iloc[-1]),
        lookbacks=[int(v["lookback_bars"]) for v in VARIANTS if v["mode"] == "momentum"],
    )

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        variant = str(cfg["variant"])
        if cfg["mode"] == "baseline":
            case2_curve = baseline_case2_curve.copy()
            case2_stats = compute_curve_stats(case2_curve, "equity_case2", INITIAL_CAPITAL_CASE)
            run_stats = {
                "trades": np.nan,
                "long_entries": np.nan,
                "short_entries": np.nan,
                "winner_adds": np.nan,
                "stop_exits": np.nan,
                "trail_exits": np.nan,
                "regime_exits": np.nan,
            }
        else:
            case2_curve, run_stats = run_momentum_case2(market, cfg)
            case2_stats = compute_curve_stats(case2_curve, "equity_case2", INITIAL_CAPITAL_CASE)

        total_curve = build_total_curve(case1_curve, case2_curve)
        total_stats = compute_curve_stats(total_curve, "equity_total", INITIAL_CAPITAL_TOTAL)
        total_curve["variant"] = variant
        total_curve["case2_variant"] = variant
        curves_out.append(total_curve)
        curve_map[variant] = total_curve.copy()

        rows.append(
            {
                "variant": variant,
                "mode": cfg["mode"],
                "total_final_equity": total_stats["final_equity"],
                "total_return_pct": total_stats["total_return_pct"],
                "total_cagr_pct": total_stats["cagr_pct"],
                "total_mdd_pct": total_stats["max_drawdown_pct"],
                "total_calmar_ratio": total_stats["calmar_ratio"],
                "case2_final_equity": case2_stats["final_equity"],
                "case2_return_pct": case2_stats["total_return_pct"],
                "case2_cagr_pct": case2_stats["cagr_pct"],
                "case2_mdd_pct": case2_stats["max_drawdown_pct"],
                "case2_calmar_ratio": case2_stats["calmar_ratio"],
                "case2_trades": run_stats["trades"],
                "long_entries": run_stats["long_entries"],
                "short_entries": run_stats["short_entries"],
                "winner_adds": run_stats["winner_adds"],
                "stop_exits": run_stats["stop_exits"],
                "trail_exits": run_stats["trail_exits"],
                "regime_exits": run_stats["regime_exits"],
            }
        )

    metrics_df = pd.DataFrame(rows).sort_values(["total_calmar_ratio", "total_cagr_pct"], ascending=[False, False]).reset_index(drop=True)
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
