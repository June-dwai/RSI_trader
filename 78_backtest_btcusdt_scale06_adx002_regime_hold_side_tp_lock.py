from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_76_PATH = Path("76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py")

OUT_BASE = "78_backtest_btcusdt_scale06_adx002_regime_hold_side_tp_lock"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

VARIANTS = [
    {"variant": "base_1.5x", "leverage": 1.5, "tp_return_pct": np.nan, "tp_side": "none"},
    {"variant": "long_tp20_lock_1.5x", "leverage": 1.5, "tp_return_pct": 20.0, "tp_side": "long"},
    {"variant": "long_tp30_lock_1.5x", "leverage": 1.5, "tp_return_pct": 30.0, "tp_side": "long"},
    {"variant": "short_tp20_lock_1.5x", "leverage": 1.5, "tp_return_pct": 20.0, "tp_side": "short"},
    {"variant": "short_tp30_lock_1.5x", "leverage": 1.5, "tp_return_pct": 30.0, "tp_side": "short"},
    {"variant": "base_2x", "leverage": 2.0, "tp_return_pct": np.nan, "tp_side": "none"},
    {"variant": "long_tp20_lock_2x", "leverage": 2.0, "tp_return_pct": 20.0, "tp_side": "long"},
    {"variant": "long_tp30_lock_2x", "leverage": 2.0, "tp_return_pct": 30.0, "tp_side": "long"},
    {"variant": "short_tp20_lock_2x", "leverage": 2.0, "tp_return_pct": 20.0, "tp_side": "short"},
    {"variant": "short_tp30_lock_2x", "leverage": 2.0, "tp_return_pct": 30.0, "tp_side": "short"},
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


def run_variant(market: pd.DataFrame, cfg: dict, s76) -> tuple[pd.DataFrame, dict]:
    leverage = float(cfg["leverage"])
    tp_return_pct = cfg["tp_return_pct"]
    tp_threshold = None if pd.isna(tp_return_pct) else float(tp_return_pct) / 100.0
    tp_side = str(cfg["tp_side"])

    timestamps = market["timestamp"].to_numpy()
    close = market["close"].to_numpy(dtype=float)
    high = market["high"].to_numpy(dtype=float)
    low = market["low"].to_numpy(dtype=float)
    trend = market["trend_4h_confirmed"].astype(str).to_numpy()

    wallet = s76.INITIAL_CAPITAL
    reserve = s76.INITIAL_CAPITAL
    margin = 0.0
    qty = 0.0
    entry = 0.0
    side = 0
    entry_wallet = np.nan
    locked_side = 0

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
        "survived_to_end": 1,
    }
    first_liq_ts = None

    for i in range(len(market)):
        price_close = float(close[i])
        price_high = float(high[i])
        price_low = float(low[i])
        state = str(trend[i])
        blocked_reentry = False

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
            elif tp_threshold is not None and entry_wallet > 0:
                apply_tp = (tp_side == "long" and side > 0) or (tp_side == "short" and side < 0)
                if apply_tp:
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

        desired_side = 1 if state == "bullish" else -1
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
                reserve, margin, qty, entry = s76._open_position(wallet, price_close, leverage, desired_side)
                wallet = reserve + margin
                side = desired_side
                entry_wallet = wallet
                if desired_side > 0:
                    stats["long_entries"] += 1
                else:
                    stats["short_entries"] += 1

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
                "leverage": leverage,
                "tp_return_pct": tp_return_pct,
            }
        )

    if side != 0 and len(market):
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close[-1]), side)
        rows[-1]["equity"] = wallet
        rows[-1]["wallet"] = wallet
        rows[-1]["reserve"] = wallet
        rows[-1]["margin"] = 0.0
        rows[-1]["side"] = 0
        stats["trades"] += 1

    curve = pd.DataFrame(rows)
    curve["variant"] = str(cfg["variant"])
    stats["first_liquidation_ts"] = first_liq_ts
    return curve, stats


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_tp = axes

    cmap = plt.get_cmap("tab20")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 20) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(s76.INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("78 Study: Side-Selective Take-Profit Lock")
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

    ax_tp.bar(metrics_df["variant"], metrics_df["tp_exits"], color=[colors[v] for v in variants], alpha=0.85, label="TP Exits")
    ax_tp.set_ylabel("TP Exits")
    ax_tp.grid(True, axis="y", alpha=0.2)
    ax_tp.tick_params(axis="x", rotation=20)
    ax_tp_t = ax_tp.twinx()
    ax_tp_t.plot(metrics_df["variant"], metrics_df["calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Calmar")
    ax_tp_t.set_ylabel("Calmar")
    h1, l1 = ax_tp.get_legend_handles_labels()
    h2, l2 = ax_tp_t.get_legend_handles_labels()
    ax_tp.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    base_15 = metrics_df[metrics_df["variant"] == "base_1.5x"].iloc[0]
    base_20 = metrics_df[metrics_df["variant"] == "base_2x"].iloc[0]
    best = metrics_df.iloc[0]

    lines: list[str] = []
    lines.append("# Study 78: Side-Selective Take-Profit Lock")
    lines.append("")
    lines.append("## Model")
    lines.append("- Uses the study-76 regime-hold leverage engine with the same no-lookahead confirmed 4h regime signal.")
    lines.append("- A TP exit is allowed only on the configured side (`long` or `short`), and it uses current 4h close wallet return from the active trade.")
    lines.append("- After TP, the same side is locked out until the confirmed regime flips to the opposite side.")
    lines.append("- This isolates whether the late-trend giveback problem is mainly in longs or shorts.")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | Lev | TP Side | TP % | CAGR % | MDD % | Calmar | Final Equity | TP Exits | Locked Bars |")
    lines.append("| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        tp_text = "N/A" if pd.isna(row["tp_return_pct"]) else _fmt(row["tp_return_pct"], 0)
        lines.append(
            f"| {row['variant']} | {_fmt(row['leverage'], 1)} | {row['tp_side']} | {tp_text} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {_fmt(row['final_equity'])} | "
            f"{_fmt_count(row['tp_exits'])} | {_fmt_count(row['locked_signal_bars'])} |"
        )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}`: CAGR `{_fmt(best['cagr_pct'])}%`, MDD `{_fmt(best['max_drawdown_pct'])}%`, Calmar `{_fmt(best['calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Delta vs Same-Leverage Baseline")
    for _, row in metrics_df.iterrows():
        if row["variant"] in {"base_1.5x", "base_2x"}:
            continue
        base = base_15 if float(row["leverage"]) == 1.5 else base_20
        lines.append(
            f"- `{row['variant']}` vs `{base['variant']}`: CAGR `{_fmt(row['cagr_pct'] - base['cagr_pct'])}pp`, "
            f"MDD `{_fmt(row['max_drawdown_pct'] - base['max_drawdown_pct'])}pp`, Calmar `{_fmt(row['calmar_ratio'] - base['calmar_ratio'])}`, "
            f"TP exits `{_fmt_count(row['tp_exits'])}`"
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If long-only TP works materially better than short-only TP, the regime-hold pain is mostly long giveback after extended bullish phases.")
    lines.append("- If short-only TP works better, the problem is the opposite: short squeezes are giving back too much.")
    lines.append("- If neither side-selective version improves enough, full TP-lock was not too blunt by accident; the issue is more structural.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    market = s76.load_market()

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        curve, run_stats = run_variant(market, cfg, s76)
        stats = s76.compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL)
        row = {
            "variant": str(cfg["variant"]),
            "leverage": float(cfg["leverage"]),
            "tp_return_pct": cfg["tp_return_pct"],
            "tp_side": str(cfg["tp_side"]),
            **stats,
            **run_stats,
        }
        rows.append(row)
        curves_out.append(curve)
        curve_map[row["variant"]] = curve.copy()

    metrics_df = pd.DataFrame(rows).sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).reset_index(drop=True)
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


s76 = load_module("study76_for_78", BASE_76_PATH)


if __name__ == "__main__":
    run()
