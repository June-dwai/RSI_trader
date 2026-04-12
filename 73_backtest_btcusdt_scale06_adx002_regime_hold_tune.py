from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_72_PATH = Path("72_backtest_btcusdt_scale06_adx002_slow_archetypes_4h.py")

OUT_BASE = "73_backtest_btcusdt_scale06_adx002_regime_hold_tune"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

VARIANTS = [
    {"variant": "reference_case1", "mode": "reference"},
    {"variant": "reference_case2", "mode": "reference"},
    {"variant": "dual_stop4", "mode": "live", "position_mode": "dual", "stop_pct": 0.04, "band_pct": 0.00, "entry_delay": 0},
    {"variant": "dual_stop5", "mode": "live", "position_mode": "dual", "stop_pct": 0.05, "band_pct": 0.00, "entry_delay": 0},
    {"variant": "dual_stop6", "mode": "live", "position_mode": "dual", "stop_pct": 0.06, "band_pct": 0.00, "entry_delay": 0},
    {"variant": "dual_band1_stop5", "mode": "live", "position_mode": "dual", "stop_pct": 0.05, "band_pct": 0.01, "entry_delay": 1},
    {"variant": "dual_band2_stop5", "mode": "live", "position_mode": "dual", "stop_pct": 0.05, "band_pct": 0.02, "entry_delay": 1},
    {"variant": "longflat_stop5", "mode": "live", "position_mode": "longflat", "stop_pct": 0.05, "band_pct": 0.00, "entry_delay": 0},
    {"variant": "longflat_band1_stop5", "mode": "live", "position_mode": "longflat", "stop_pct": 0.05, "band_pct": 0.01, "entry_delay": 1},
    {"variant": "longflat_band2_stop5", "mode": "live", "position_mode": "longflat", "stop_pct": 0.05, "band_pct": 0.02, "entry_delay": 1},
]


def load_study72():
    spec = importlib.util.spec_from_file_location("study72_for_73", BASE_72_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {BASE_72_PATH}")
    module = importlib.util.module_from_spec(spec)
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


def build_regime_signal(df: pd.DataFrame, position_mode: str, band_pct: float, entry_delay: int) -> pd.Series:
    raw: list[str] = []
    for _, row in df.iterrows():
        trend = str(row["trend_4h_confirmed"])
        close = float(row["close"])
        ema_prev = float(row["ema200_prev_closed"])
        if pd.isna(close) or pd.isna(ema_prev):
            raw.append("flat")
            continue

        if band_pct > 0:
            upper = ema_prev * (1.0 + band_pct)
            lower = ema_prev * (1.0 - band_pct)
            if trend == "bullish" and close > upper:
                state = "bullish"
            elif position_mode == "dual" and trend == "bearish" and close < lower:
                state = "bearish"
            else:
                state = "flat"
        else:
            if trend == "bullish":
                state = "bullish"
            elif position_mode == "dual" and trend == "bearish":
                state = "bearish"
            else:
                state = "flat"
        raw.append(state)

    signal = pd.Series(raw, index=df.index)
    if entry_delay > 0:
        signal = signal.shift(entry_delay)
    return signal.fillna("flat")


def _mark_to_market(capital: float, side: int, avg_entry: float, qty: float, price: float) -> float:
    if side == 0 or qty <= 0:
        return capital
    if side > 0:
        return capital + (price - avg_entry) * qty
    return capital + (avg_entry - price) * qty


def _close_position(capital: float, side: int, avg_entry: float, qty: float, price: float, commission: float) -> float:
    if side == 0 or qty <= 0:
        return capital
    close_commission = qty * price * commission
    if side > 0:
        pnl = (price - avg_entry) * qty
    else:
        pnl = (avg_entry - price) * qty
    return capital + pnl - close_commission


def run_variant(df: pd.DataFrame, cfg: dict, s72) -> tuple[pd.DataFrame, dict]:
    signal = build_regime_signal(df, str(cfg["position_mode"]), float(cfg["band_pct"]), int(cfg["entry_delay"]))
    close = df["close"].to_numpy(dtype=float)
    timestamps = df["timestamp"].to_numpy()
    signal_np = signal.to_numpy()

    capital = s72.INITIAL_CAPITAL
    side = 0
    avg_entry = 0.0
    qty = 0.0

    rows: list[dict] = []
    stats = {"trades": 0, "long_entries": 0, "short_entries": 0, "stop_exits": 0, "signal_exits": 0, "reverse_entries": 0}

    for i in range(len(df)):
        price = float(close[i])
        state = str(signal_np[i])
        if pd.isna(price):
            rows.append({"timestamp": timestamps[i], "equity": capital})
            continue

        if side > 0 and price <= avg_entry * (1.0 - float(cfg["stop_pct"])):
            capital = _close_position(capital, side, avg_entry, qty, price, s72.COMMISSION)
            side = 0
            avg_entry = 0.0
            qty = 0.0
            stats["trades"] += 1
            stats["stop_exits"] += 1
        elif side < 0 and price >= avg_entry * (1.0 + float(cfg["stop_pct"])):
            capital = _close_position(capital, side, avg_entry, qty, price, s72.COMMISSION)
            side = 0
            avg_entry = 0.0
            qty = 0.0
            stats["trades"] += 1
            stats["stop_exits"] += 1

        desired_side = 1 if state == "bullish" else (-1 if state == "bearish" else 0)
        if side != desired_side:
            if side != 0:
                capital = _close_position(capital, side, avg_entry, qty, price, s72.COMMISSION)
                stats["trades"] += 1
                stats["signal_exits"] += 1
                side = 0
                avg_entry = 0.0
                qty = 0.0

            if desired_side != 0:
                open_qty = (capital / price) * 0.98
                if open_qty > 0:
                    capital -= open_qty * price * s72.COMMISSION
                    side = desired_side
                    avg_entry = price
                    qty = open_qty
                    if desired_side > 0:
                        stats["long_entries"] += 1
                    else:
                        stats["short_entries"] += 1
                    if state != "flat" and i > 0 and str(signal_np[i - 1]) not in ("", state):
                        stats["reverse_entries"] += 1

        rows.append({"timestamp": timestamps[i], "equity": _mark_to_market(capital, side, avg_entry, qty, price)})

    if side != 0 and len(df):
        capital = _close_position(capital, side, avg_entry, qty, float(close[-1]), s72.COMMISSION)
        rows[-1]["equity"] = capital
        stats["trades"] += 1

    curve = pd.DataFrame(rows)
    curve["variant"] = str(cfg["variant"])
    return curve, stats


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame, initial_capital: float):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_mdd = axes

    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(initial_capital, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("73 Study: Regime-Hold Tuning")
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

    ax_mdd.bar(metrics_df["variant"], metrics_df["trades"], color=[colors[v] for v in variants], alpha=0.85, label="Trades")
    ax_mdd.set_ylabel("Trades")
    ax_mdd.grid(True, axis="y", alpha=0.2)
    ax_mdd.tick_params(axis="x", rotation=20)
    ax_mdd_t = ax_mdd.twinx()
    ax_mdd_t.plot(metrics_df["variant"], metrics_df["calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Calmar")
    ax_mdd_t.set_ylabel("Calmar")
    h1, l1 = ax_mdd.get_legend_handles_labels()
    h2, l2 = ax_mdd_t.get_legend_handles_labels()
    ax_mdd.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    best_live = metrics_df[metrics_df["mode"] == "live"].iloc[0]

    lines: list[str] = []
    lines.append("# Study 73: Regime-Hold Tuning")
    lines.append("")
    lines.append("## Purpose")
    lines.append("- Tune the `regime_hold_dual` idea from study 72 instead of abandoning it after the first pass.")
    lines.append("- Tested levers: stop width, neutral EMA band, and `dual` versus `long-flat` regime handling.")
    lines.append("- Band variants delay entry by one 4h bar after signal formation to avoid same-bar lookahead.")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | CAGR % | MDD % | Calmar | Final Equity | Trades | Longs | Shorts |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{_fmt(row['final_equity'])} | {_fmt_count(row['trades'])} | {_fmt_count(row['long_entries'])} | {_fmt_count(row['short_entries'])} |"
        )
    lines.append("")
    lines.append("## Best Tuned Variant")
    lines.append(
        f"- `{best_live['variant']}`: CAGR `{_fmt(best_live['cagr_pct'])}%`, MDD `{_fmt(best_live['max_drawdown_pct'])}%`, Calmar `{_fmt(best_live['calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If the best tuned variant still cannot clear the original references, this logic is more plausible as a low-risk third sleeve than as a primary engine.")
    lines.append("- If `long-flat` beats `dual`, then bearish short exposure is not carrying its weight inside this slow regime framework.")
    lines.append("- If the EMA band helps, then avoiding ambiguous regime transitions is the main missing ingredient.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    s72 = load_study72()
    ref_case1, ref_case2 = s72.load_reference_curves()
    market = s72.prepare_4h_market(s72.load_module("study47_for_73", s72.BASE_47_PATH), pd.Timestamp(ref_case1["timestamp"].iloc[0]), pd.Timestamp(ref_case1["timestamp"].iloc[-1]))

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        variant = str(cfg["variant"])
        if cfg["mode"] == "reference":
            curve = ref_case1.copy() if variant == "reference_case1" else ref_case2.copy()
            stats = s72.compute_curve_stats(curve, "equity", s72.INITIAL_CAPITAL)
            run_stats = {"trades": np.nan, "long_entries": np.nan, "short_entries": np.nan, "stop_exits": np.nan, "signal_exits": np.nan, "reverse_entries": np.nan}
            curve["variant"] = variant
        else:
            curve, run_stats = run_variant(market, cfg, s72)
            stats = s72.compute_curve_stats(curve, "equity", s72.INITIAL_CAPITAL)

        rows.append({"variant": variant, "mode": cfg["mode"], **stats, **run_stats})
        curves_out.append(curve)
        curve_map[variant] = curve.copy()

    metrics_df = pd.DataFrame(rows).sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curves_out, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df, s72.INITIAL_CAPITAL)
    save_report(metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    run()
