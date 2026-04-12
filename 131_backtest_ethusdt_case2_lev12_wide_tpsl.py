from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SOURCE_002 = Path("002_backtest_btcusdt.py")
SOURCE_04 = Path("04_backtest_btcusdt_mode_compare.py")
SOURCE_32 = Path("32_backtest_btcusdt_live_nla.py")
SOURCE_42 = Path("42_backtest_btcusdt_scale06_adx002_equity_combo.py")
SOURCE_129 = Path("129_backtest_ethusdt_case2_vs_case3best_mix.py")
SOURCE_130 = Path("130_backtest_ethusdt_case2_bearish_escape_variants.py")

OUT_BASE = "131_backtest_ethusdt_case2_lev12_wide_tpsl"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_MD = Path(f"{OUT_BASE}.md")

SYMBOL = "ETHUSDT"
INITIAL_CAPITAL = 1000.0
BACKTEST_START = pd.Timestamp("2021-01-01 00:00:00")
ANALYSIS_2026_START = pd.Timestamp("2026-01-01 00:00:00")
CRASH_TS = pd.Timestamp("2021-05-19 12:50:00")
CRASH_WINDOW_START = pd.Timestamp("2021-05-10 00:00:00")
CRASH_WINDOW_END = pd.Timestamp("2021-05-31 00:00:00")

VARIANTS: list[dict] = [
    {
        "variant": "baseline_case2",
        "label": "Baseline 2.4x",
        "color": "#1f77b4",
        "entry_scale": 0.60,
        "take_profit_pct": 0.012,
        "stop_loss_pct": 0.03,
        "short_rsi_overbought": 85,
        "allow_short_reverse_on_prev_touch": False,
        "fix_stop_rearm": False,
        "bearish_flip_trim_frac": 0.0,
    },
    {
        "variant": "lev12_tp2x_sl2x",
        "label": "1.2x + TP/SL x2",
        "color": "#ff7f0e",
        "entry_scale": 0.30,
        "take_profit_pct": 0.024,
        "stop_loss_pct": 0.06,
        "short_rsi_overbought": 85,
        "allow_short_reverse_on_prev_touch": False,
        "fix_stop_rearm": False,
        "bearish_flip_trim_frac": 0.0,
    },
    {
        "variant": "lev12_tp2x_sl2x_stopfix",
        "label": "1.2x + TP/SL x2 + Stop Fix",
        "color": "#2ca02c",
        "entry_scale": 0.30,
        "take_profit_pct": 0.024,
        "stop_loss_pct": 0.06,
        "short_rsi_overbought": 85,
        "allow_short_reverse_on_prev_touch": False,
        "fix_stop_rearm": True,
        "bearish_flip_trim_frac": 0.0,
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


def run_variant_131(df_1m: pd.DataFrame, df_4h: pd.DataFrame, base, helper, m32, s42, study130, cfg: dict):
    bt_cls = study130.make_variant_class(m32, s42, cfg)
    bt = bt_cls(
        base_module=base,
        symbol=SYMBOL,
        initial_capital=INITIAL_CAPITAL,
        commission=base.COMMISSION,
        entry_scale=float(cfg["entry_scale"]),
    )
    helper.configure_baseline_params(bt)
    bt.take_profit_pct = float(cfg["take_profit_pct"])
    bt.stop_loss_pct = float(cfg["stop_loss_pct"])
    bt.rsi_overbought = int(cfg["short_rsi_overbought"])
    bt.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)

    curve = pd.DataFrame(bt.equity_curve)[["timestamp", "equity"]].copy()
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)

    stats = study130.compute_curve_stats(curve, "equity", INITIAL_CAPITAL)
    stats["variant"] = cfg["variant"]
    stats["entry_scale"] = float(cfg["entry_scale"])
    stats["max_notional_multiple"] = float(cfg["entry_scale"]) * float(s42.CASE2_MAX_ENTRIES)
    stats["take_profit_pct"] = float(cfg["take_profit_pct"])
    stats["stop_loss_pct"] = float(cfg["stop_loss_pct"])
    stats["short_rsi_overbought"] = int(cfg["short_rsi_overbought"])
    stats["allow_short_reverse_on_prev_touch"] = bool(cfg["allow_short_reverse_on_prev_touch"])
    stats["fix_stop_rearm"] = bool(cfg["fix_stop_rearm"])
    stats["bearish_flip_trim_frac"] = float(cfg["bearish_flip_trim_frac"])
    stats["trades"] = len(bt.trades)
    stats["reverse_events"] = int(bt.stats["reverse_events"])
    stats["stop_loss_events"] = int(bt.stats["stop_loss_events"])
    stats["reentry_events"] = int(bt.stats["reentry_events"])
    stats["trend_flip_trim_events"] = int(bt.stats["trend_flip_trim_events"])
    return curve, stats


def save_plot(curves: list[tuple[dict, pd.DataFrame]]) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.1]})
    ax_eq, ax_dd, ax_crash = axes

    for cfg, curve in curves:
        color = cfg["color"]
        label = cfg["variant"]
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.05, label=label, color=color)
        dd = curve["equity"].astype(float) / curve["equity"].cummax().astype(float) - 1.0
        ax_dd.plot(curve["timestamp"], -dd * 100.0, linewidth=1.0, label=label, color=color)
        seg = curve[(curve["timestamp"] >= CRASH_WINDOW_START) & (curve["timestamp"] <= CRASH_WINDOW_END)].copy()
        if not seg.empty:
            ax_crash.plot(seg["timestamp"], seg["equity"], linewidth=1.1, label=label, color=color)

    ax_eq.axhline(INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 131: ETHUSDT Case2 1.2x Exposure + Wider TP/SL")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_dd.set_ylabel("Drawdown %")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="upper left")

    ax_crash.axvline(CRASH_TS, color="#444444", linestyle="--", linewidth=0.9)
    ax_crash.set_title("May 2021 Crash Zoom")
    ax_crash.set_ylabel("Equity (USDT)")
    ax_crash.set_xlabel("Time")
    ax_crash.grid(True, alpha=0.2)
    ax_crash.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, latest_closed_ts: pd.Timestamp, used_paths: list[Path], s42) -> None:
    best_cagr = metrics_df.sort_values("cagr_pct", ascending=False).iloc[0]
    best_calmar = metrics_df.sort_values("calmar_ratio", ascending=False).iloc[0]
    best_crash = metrics_df.sort_values("equity_at_2021_05_19_1250", ascending=False).iloc[0]

    lines: list[str] = []
    lines.append("# Study 131: ETHUSDT case2 leverage cut + wider TP/SL")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Symbol: `{SYMBOL}`")
    lines.append(f"- Window: `{BACKTEST_START}` -> `{latest_closed_ts}`")
    lines.append("- Initial capital per variant: `1000 USDT`")
    lines.append(f"- Max entries stays `{s42.CASE2_MAX_ENTRIES}`.")
    lines.append("- Requested test: lower max notional from `2.4x` to `1.2x` by changing `entry_scale 0.60 -> 0.30`.")
    lines.append("- Requested TP/SL widening: baseline `1.2% / 3.0%` -> `2.4% / 6.0%`.")
    lines.append("- Included one extra control with `stop rearm` fix so the leverage test is not fully dominated by the known reentry bug.")
    lines.append("- Data sources used:")
    for path in used_paths:
        lines.append(f"  - `{path}`")
    lines.append("")
    lines.append("## Results")
    lines.append("| Variant | Max Notional x | TP % | SL % | Final Equity | CAGR % | MDD % | Calmar | 2026 Return % | Crash Equity | First Zero TS | Reverse | Stop | Reentry |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        zero_ts = "N/A" if pd.isna(row["first_zero_ts"]) else str(pd.Timestamp(row["first_zero_ts"]))
        lines.append(
            f"| {row['variant']} | {_fmt(row['max_notional_multiple'], 2)} | {_fmt(row['take_profit_pct'] * 100.0, 2)} | "
            f"{_fmt(row['stop_loss_pct'] * 100.0, 2)} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {_fmt(row['return_2026_pct'])} | "
            f"{_fmt(row['equity_at_2021_05_19_1250'])} | {zero_ts} | {int(row['reverse_events'])} | "
            f"{int(row['stop_loss_events'])} | {int(row['reentry_events'])} |"
        )
    lines.append("")
    lines.append("## Takeaways")
    lines.append(
        f"- Highest CAGR: `{best_cagr['variant']}` with CAGR `{_fmt(best_cagr['cagr_pct'])}%`, MDD `{_fmt(best_cagr['max_drawdown_pct'])}%`."
    )
    lines.append(
        f"- Best Calmar: `{best_calmar['variant']}` with Calmar `{_fmt(best_calmar['calmar_ratio'])}`."
    )
    lines.append(
        f"- Best May 19 crash survival equity: `{best_crash['variant']}` with `{_fmt(best_crash['equity_at_2021_05_19_1250'])}` at `{CRASH_TS}`."
    )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    study129 = load_module("study129_for_131", SOURCE_129)
    study130 = load_module("study130_for_131", SOURCE_130)
    base = load_module("m002_for_131", SOURCE_002)
    helper = load_module("m04_for_131", SOURCE_04)
    m32 = load_module("m32_for_131", SOURCE_32)
    s42 = load_module("s42_for_131", SOURCE_42)

    print("[131] Loading ETH 2021+ market...", flush=True)
    df_1m, df_4h, latest_closed_ts, used_paths = study129.load_eth_market_2021plus()
    print(f"[131] ETH 1m span: {df_1m.index.min()} -> {df_1m.index.max()} ({len(df_1m)} rows)", flush=True)
    print(f"[131] ETH 4h span: {df_4h.index.min()} -> {df_4h.index.max()} ({len(df_4h)} rows)", flush=True)

    base.SYMBOL = SYMBOL
    base.BACKTEST_START = str(BACKTEST_START.date())
    base.BACKTEST_END = str(pd.Timestamp(latest_closed_ts).date())

    metrics_rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    plot_curves: list[tuple[dict, pd.DataFrame]] = []

    for cfg in VARIANTS:
        print(f"[131] Running {cfg['variant']}...", flush=True)
        curve, stats = run_variant_131(df_1m.copy(), df_4h.copy(), base, helper, m32, s42, study130, cfg)
        stats_2026 = study130.compute_window_stats(curve, ANALYSIS_2026_START)
        crash_equity = study130.equity_at_or_before(curve, CRASH_TS)
        zero_ts = study130.first_zero_ts(curve)
        metrics_rows.append(
            {
                **stats,
                "return_2026_pct": stats_2026["return_pct"],
                "mdd_2026_pct": stats_2026["mdd_pct"],
                "equity_at_2021_05_19_1250": crash_equity,
                "first_zero_ts": zero_ts,
                "survived_2021_05_19": bool(pd.notna(crash_equity) and crash_equity > 0),
            }
        )
        curve_out = curve.copy()
        curve_out["variant"] = cfg["variant"]
        curve_rows.append(curve_out)
        plot_curves.append((cfg, curve))

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    pd.concat(curve_rows, ignore_index=True).to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")
    save_plot(plot_curves)
    save_report(metrics_df, latest_closed_ts, used_paths, s42)

    for _, row in metrics_df.iterrows():
        zero_ts = "N/A" if pd.isna(row["first_zero_ts"]) else str(pd.Timestamp(row["first_zero_ts"]))
        print(
            f"[131] {row['variant']}: max={_fmt(row['max_notional_multiple'], 2)}x "
            f"TP={_fmt(row['take_profit_pct'] * 100.0, 2)}% SL={_fmt(row['stop_loss_pct'] * 100.0, 2)}% "
            f"CAGR={_fmt(row['cagr_pct'])}% MDD={_fmt(row['max_drawdown_pct'])}% "
            f"CrashEq={_fmt(row['equity_at_2021_05_19_1250'])} Zero={zero_ts}",
            flush=True,
        )
    print(f"[131] Outputs: {OUT_PNG}, {OUT_CSV}, {OUT_CURVES_CSV}, {OUT_MD}", flush=True)


if __name__ == "__main__":
    main()
