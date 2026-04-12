from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
DATA_4H_PATH = Path("historical_data_mainnet/BTCUSDT_4h_2022-01-01_2026-03-15.pkl")

OUT_BASE = "76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

INITIAL_CAPITAL = 1000.0
COMMISSION = 0.0004
ENTRY_MARGIN_FRACTION = 0.98
STOP_PCT = 0.06
MAINTENANCE_MARGIN_RATE = 0.005
LEVERAGES = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]


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


def load_market() -> pd.DataFrame:
    m47 = load_module("study47_for_76", BASE_47_PATH)
    df = pd.read_pickle(DATA_4H_PATH).copy().sort_index()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    df["ema200_closed"] = df["close"].ewm(span=m47.EMA_PERIOD, adjust=False).mean()
    df["ema200_prev_closed"] = df["ema200_closed"].shift(1)
    df["trend_4h_hyst"] = m47.LiveParityNoLookahead._compute_hysteresis_state(
        df["close"], df["ema200_prev_closed"], m47.HYSTERESIS_BAND
    )
    df["trend_4h_confirmed"] = df["trend_4h_hyst"].shift(1)
    df = df.dropna(subset=["ema200_prev_closed", "trend_4h_confirmed"]).copy()
    df = df.reset_index().rename(columns={"index": "timestamp"})
    return df


def _liq_price(entry: float, leverage: float, side: int) -> float:
    if leverage <= 1.0:
        return 0.0 if side > 0 else float("inf")
    if side > 0:
        return entry * (1.0 - 1.0 / leverage) / (1.0 - MAINTENANCE_MARGIN_RATE)
    return entry * (1.0 + 1.0 / leverage) / (1.0 + MAINTENANCE_MARGIN_RATE)


def _mark_to_market(reserve: float, margin: float, qty: float, entry: float, price: float, side: int) -> float:
    if side == 0 or qty <= 0:
        return reserve + margin
    if side > 0:
        pnl = (price - entry) * qty
    else:
        pnl = (entry - price) * qty
    return reserve + margin + pnl


def _realize_close(reserve: float, margin: float, qty: float, entry: float, exit_price: float, side: int) -> float:
    if side == 0 or qty <= 0:
        return reserve + margin
    if side > 0:
        pnl = (exit_price - entry) * qty
    else:
        pnl = (entry - exit_price) * qty
    close_fee = qty * exit_price * COMMISSION
    return reserve + margin + pnl - close_fee


def _open_position(wallet: float, price: float, leverage: float, side: int) -> tuple[float, float, float, float]:
    margin = wallet * ENTRY_MARGIN_FRACTION
    reserve = wallet - margin
    notional = margin * leverage
    open_fee = notional * COMMISSION
    reserve -= open_fee
    if reserve < 0:
        margin += reserve
        reserve = 0.0
        notional = margin * leverage
    qty = notional / price if price > 0 else 0.0
    return reserve, margin, qty, price


def run_leverage_variant(market: pd.DataFrame, leverage: float) -> tuple[pd.DataFrame, dict]:
    timestamps = market["timestamp"].to_numpy()
    close = market["close"].to_numpy(dtype=float)
    high = market["high"].to_numpy(dtype=float)
    low = market["low"].to_numpy(dtype=float)
    trend = market["trend_4h_confirmed"].astype(str).to_numpy()

    wallet = INITIAL_CAPITAL
    reserve = INITIAL_CAPITAL
    margin = 0.0
    qty = 0.0
    entry = 0.0
    side = 0

    rows: list[dict] = []
    stats = {
        "trades": 0,
        "long_entries": 0,
        "short_entries": 0,
        "stop_exits": 0,
        "signal_exits": 0,
        "liquidations": 0,
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
            liq_price = _liq_price(entry, leverage, side)
            stop_price = entry * (1.0 - STOP_PCT) if side > 0 else entry * (1.0 + STOP_PCT)

            if side > 0 and leverage > 1.0 and price_low <= liq_price:
                wallet = max(reserve, 0.0)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
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
                blocked_reentry = True
                stats["trades"] += 1
                stats["liquidations"] += 1
                stats["survived_to_end"] = 0
                if first_liq_ts is None:
                    first_liq_ts = pd.Timestamp(timestamps[i])
            elif side > 0 and price_low <= stop_price:
                wallet = _realize_close(reserve, margin, qty, entry, stop_price, side)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                blocked_reentry = True
                stats["trades"] += 1
                stats["stop_exits"] += 1
            elif side < 0 and price_high >= stop_price:
                wallet = _realize_close(reserve, margin, qty, entry, stop_price, side)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                blocked_reentry = True
                stats["trades"] += 1
                stats["stop_exits"] += 1

        desired_side = 1 if state == "bullish" else -1
        if not blocked_reentry and side != desired_side:
            if side != 0:
                wallet = _realize_close(reserve, margin, qty, entry, price_close, side)
                reserve = wallet
                margin = 0.0
                qty = 0.0
                entry = 0.0
                side = 0
                stats["trades"] += 1
                stats["signal_exits"] += 1

            if wallet > 0:
                reserve, margin, qty, entry = _open_position(wallet, price_close, leverage, desired_side)
                wallet = reserve + margin
                side = desired_side
                if desired_side > 0:
                    stats["long_entries"] += 1
                else:
                    stats["short_entries"] += 1

        equity = wallet if side == 0 else _mark_to_market(reserve, margin, qty, entry, price_close, side)
        rows.append(
            {
                "timestamp": timestamps[i],
                "equity": equity,
                "wallet": wallet,
                "reserve": reserve,
                "margin": margin,
                "side": side,
                "leverage": leverage,
            }
        )

    if side != 0 and len(market):
        wallet = _realize_close(reserve, margin, qty, entry, float(close[-1]), side)
        rows[-1]["equity"] = wallet
        rows[-1]["wallet"] = wallet
        rows[-1]["reserve"] = wallet
        rows[-1]["margin"] = 0.0
        rows[-1]["side"] = 0
        stats["trades"] += 1

    curve = pd.DataFrame(rows)
    curve["variant"] = f"lev_{leverage:g}x"
    stats["first_liquidation_ts"] = first_liq_ts
    return curve, stats


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_liq = axes

    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("76 Study: Regime-Hold Leverage Sweep With Liquidation Model")
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

    ax_liq.bar(metrics_df["variant"], metrics_df["liquidations"], color=[colors[v] for v in variants], alpha=0.85, label="Liquidations")
    ax_liq.set_ylabel("Liquidations")
    ax_liq.grid(True, axis="y", alpha=0.2)
    ax_liq.tick_params(axis="x", rotation=20)
    ax_liq_t = ax_liq.twinx()
    ax_liq_t.plot(metrics_df["variant"], metrics_df["calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Calmar")
    ax_liq_t.set_ylabel("Calmar")
    h1, l1 = ax_liq.get_legend_handles_labels()
    h2, l2 = ax_liq_t.get_legend_handles_labels()
    ax_liq.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    baseline = metrics_df[metrics_df["variant"] == "lev_1x"].iloc[0]
    best = metrics_df.iloc[0]

    lines: list[str] = []
    lines.append("# Study 76: Regime-Hold Leverage Sweep With Liquidation Model")
    lines.append("")
    lines.append("## Model")
    lines.append("- Base signal is the study-73 `dual_stop6` idea: confirmed 4h trend decides long versus short.")
    lines.append(f"- Start capital: `{INITIAL_CAPITAL:.0f}` USDT")
    lines.append(f"- Margin posted per trade: `{ENTRY_MARGIN_FRACTION * 100:.1f}%` of wallet")
    lines.append("- Margin mode assumption: `isolated`, no auto-add")
    lines.append(f"- Maintenance margin rate assumption: `{MAINTENANCE_MARGIN_RATE * 100:.2f}%`")
    lines.append(f"- Stop loss: `{STOP_PCT * 100:.1f}%` from entry")
    lines.append("- Liquidation check uses bar extremes (`low` for long, `high` for short) before stop-loss, which is intentionally conservative.")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | CAGR % | MDD % | Calmar | Final Equity | Liquidations | First Liq | Trades |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |")
    for _, row in metrics_df.iterrows():
        first_liq = pd.to_datetime(row["first_liquidation_ts"]).strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row["first_liquidation_ts"]) else "N/A"
        lines.append(
            f"| {row['variant']} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{_fmt(row['final_equity'])} | {_fmt_count(row['liquidations'])} | {first_liq} | {_fmt_count(row['trades'])} |"
        )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}`: CAGR `{_fmt(best['cagr_pct'])}%`, MDD `{_fmt(best['max_drawdown_pct'])}%`, Calmar `{_fmt(best['calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Delta vs 1x")
    for _, row in metrics_df.iterrows():
        if row["variant"] == "lev_1x":
            continue
        lines.append(
            f"- `{row['variant']}`: CAGR `{_fmt(row['cagr_pct'] - baseline['cagr_pct'])}pp`, "
            f"MDD `{_fmt(row['max_drawdown_pct'] - baseline['max_drawdown_pct'])}pp`, "
            f"Calmar `{_fmt(row['calmar_ratio'] - baseline['calmar_ratio'])}`, "
            f"liquidations `{_fmt_count(row['liquidations'])}`"
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If leverage improves CAGR faster than it increases MDD without triggering many liquidations, then regime-hold may support modest leverage as a sleeve.")
    lines.append("- If high-leverage variants suffer frequent liquidations, they are not suitable as case3 diversifiers even if their CAGR looks attractive.")
    lines.append("- This study is still a simplified margin model; funding, slippage, and Binance risk-tier changes are not included.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    market = load_market()

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for leverage in LEVERAGES:
        curve, run_stats = run_leverage_variant(market, float(leverage))
        stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL)
        row = {
            "variant": f"lev_{leverage:g}x",
            "leverage": float(leverage),
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


if __name__ == "__main__":
    run()
