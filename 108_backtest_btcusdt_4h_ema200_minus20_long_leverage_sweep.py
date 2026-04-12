from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_107_PATH = Path("107_backtest_btcusdt_4h_ema200_counter_gap_study.py")

OUT_BASE = "108_backtest_btcusdt_4h_ema200_minus20_long_leverage_sweep"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_TRADES_CSV = Path(f"{OUT_BASE}_trades.csv")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_selected_curves.csv")

INITIAL_CAPITAL = 1000.0
FEE_RATE = 0.0004
THRESHOLD_PCT = 20.0

LEVERAGE_GRID = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0]
TP_GRID = [5.0, 7.5, 10.0, 12.5, 15.0]
SL_GRID = [5.0, 7.5, 10.0, 12.5, 15.0]

BASE_VARIANT = "thr20_long_5x_tp10_sl10"


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


def compute_curve_stats(curve: pd.DataFrame, initial_capital: float) -> dict:
    series = curve["equity"].astype(float)
    final_equity = float(series.iloc[-1])
    total_return_pct = (final_equity / float(initial_capital) - 1.0) * 100.0
    elapsed_days = (curve["timestamp"].iloc[-1] - curve["timestamp"].iloc[0]).total_seconds() / 86400.0
    years = max(elapsed_days / 365.25, 1e-9)
    cagr_pct = ((final_equity / float(initial_capital)) ** (1.0 / years) - 1.0) * 100.0
    dd = series / series.cummax() - 1.0
    max_drawdown_pct = float(-dd.min() * 100.0)
    calmar = float(cagr_pct / max_drawdown_pct) if max_drawdown_pct > 0 else np.nan
    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "calmar_ratio": calmar,
    }


def build_variants() -> list[dict]:
    variants: list[dict] = []
    for leverage in LEVERAGE_GRID:
        for tp_pct in TP_GRID:
            for sl_pct in SL_GRID:
                variants.append(
                    {
                        "variant": f"thr20_long_{str(leverage).replace('.0', '')}x_tp{str(tp_pct).replace('.0', '')}_sl{str(sl_pct).replace('.0', '')}",
                        "threshold_pct": THRESHOLD_PCT,
                        "leverage": float(leverage),
                        "tp_pct": float(tp_pct),
                        "sl_pct": float(sl_pct),
                    }
                )
    return variants


def run_buy_hold(market: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    work = market.copy()
    first_price = float(work["close"].iloc[0])
    qty = (INITIAL_CAPITAL * (1.0 - FEE_RATE)) / first_price

    curve = work[["timestamp"]].copy()
    curve["variant"] = "buy_hold"
    curve["equity"] = qty * work["close"].astype(float)
    curve.loc[curve.index[0], "equity"] = INITIAL_CAPITAL * (1.0 - FEE_RATE)

    final_capital = qty * float(work["close"].iloc[-1]) * (1.0 - FEE_RATE)
    curve.loc[curve.index[-1], "equity"] = final_capital

    trades = pd.DataFrame(
        [
            {
                "variant": "buy_hold",
                "side": "LONG",
                "entry_time": pd.to_datetime(work["timestamp"].iloc[0]),
                "exit_time": pd.to_datetime(work["timestamp"].iloc[-1]),
                "entry_price": first_price,
                "exit_price": float(work["close"].iloc[-1]),
                "exit_reason": "final",
                "bars_held": int(len(work) - 1),
                "hours_held": float((len(work) - 1) * 0.25),
                "entry_capital": INITIAL_CAPITAL,
                "exit_capital": final_capital,
                "return_pct": (final_capital / INITIAL_CAPITAL - 1.0) * 100.0,
                "leverage": 1.0,
                "tp_pct": np.nan,
                "sl_pct": np.nan,
            }
        ]
    )

    stats = compute_curve_stats(curve, INITIAL_CAPITAL)
    stats.update(
        {
            "variant": "buy_hold",
            "threshold_pct": THRESHOLD_PCT,
            "leverage": 1.0,
            "tp_pct": np.nan,
            "sl_pct": np.nan,
            "trades": 1,
            "win_rate_pct": 100.0 if final_capital > INITIAL_CAPITAL else 0.0,
            "avg_trade_return_pct": float(trades["return_pct"].mean()),
            "avg_hours_held": float(trades["hours_held"].mean()),
            "median_hours_held": float(trades["hours_held"].median()),
            "max_hours_held": float(trades["hours_held"].max()),
            "tp_exits": 0,
            "stop_exits": 0,
            "liquidations": 0,
            "final_exits": 1,
            "signal_crosses": np.nan,
            "actual_entries": 1,
            "bankrupt": False,
        }
    )
    return curve, trades, stats


def run_variant(market: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    work = market.copy().reset_index(drop=True)
    close = work["close"].to_numpy(dtype=float)
    high = work["high"].to_numpy(dtype=float)
    low = work["low"].to_numpy(dtype=float)
    gap = work["gap_pct"].to_numpy(dtype=float)
    timestamps = pd.to_datetime(work["timestamp"]).to_numpy()

    threshold_pct = float(cfg["threshold_pct"])
    leverage = float(cfg["leverage"])
    tp_pct = float(cfg["tp_pct"])
    sl_pct = float(cfg["sl_pct"])

    signal_crosses = int(((gap <= -threshold_pct) & np.r_[False, gap[:-1] > -threshold_pct]).sum())

    capital = float(INITIAL_CAPITAL)
    qty = 0.0
    entry_price = 0.0
    entry_capital = 0.0
    entry_margin = 0.0
    liq_price = 0.0
    entry_idx = -1
    in_position = False
    bankrupt = False

    curve_rows: list[dict] = []
    trade_rows: list[dict] = []
    tp_exits = 0
    stop_exits = 0
    liquidations = 0
    final_exits = 0

    for i in range(len(work)):
        if bankrupt:
            curve_rows.append(
                {
                    "timestamp": pd.Timestamp(timestamps[i]),
                    "variant": cfg["variant"],
                    "equity": 0.0,
                    "position": "bankrupt",
                }
            )
            continue

        if i > 0 and in_position:
            exit_reason = None
            exit_price = None

            tp_price = entry_price * (1.0 + tp_pct / 100.0)
            sl_price = entry_price * (1.0 - sl_pct / 100.0)

            hit_liq = low[i] <= liq_price
            hit_sl = low[i] <= sl_price
            hit_tp = high[i] >= tp_price

            if hit_liq:
                exit_reason = "liquidation"
                exit_price = liq_price
            elif hit_sl and hit_tp:
                exit_reason = "stop"
                exit_price = sl_price
            elif hit_sl:
                exit_reason = "stop"
                exit_price = sl_price
            elif hit_tp:
                exit_reason = "tp"
                exit_price = tp_price

            if exit_reason is not None and exit_price is not None:
                if exit_reason == "liquidation":
                    capital = 0.0
                    liquidations += 1
                else:
                    exit_fee = qty * float(exit_price) * FEE_RATE
                    pnl = (float(exit_price) - entry_price) * qty
                    capital = max(entry_margin + pnl - exit_fee, 0.0)
                    if exit_reason == "tp":
                        tp_exits += 1
                    else:
                        stop_exits += 1

                trade_rows.append(
                    {
                        "variant": cfg["variant"],
                        "side": "LONG",
                        "entry_time": pd.Timestamp(timestamps[entry_idx]),
                        "exit_time": pd.Timestamp(timestamps[i]),
                        "entry_price": float(entry_price),
                        "exit_price": float(exit_price),
                        "exit_reason": exit_reason,
                        "bars_held": int(i - entry_idx),
                        "hours_held": float((i - entry_idx) * 0.25),
                        "entry_capital": float(entry_capital),
                        "exit_capital": float(capital),
                        "return_pct": (capital / entry_capital - 1.0) * 100.0 if entry_capital > 0 else np.nan,
                        "leverage": leverage,
                        "tp_pct": tp_pct,
                        "sl_pct": sl_pct,
                    }
                )

                in_position = False
                qty = 0.0
                entry_price = 0.0
                entry_capital = 0.0
                entry_margin = 0.0
                liq_price = 0.0
                entry_idx = -1

                if capital <= 0:
                    bankrupt = True
                    curve_rows.append(
                        {
                            "timestamp": pd.Timestamp(timestamps[i]),
                            "variant": cfg["variant"],
                            "equity": 0.0,
                            "position": "bankrupt",
                        }
                    )
                    continue

        if i > 0 and (not in_position):
            signal_now = (gap[i] <= -threshold_pct) and (gap[i - 1] > -threshold_pct)
            if signal_now and capital > 0:
                entry_capital = capital
                notional = capital * leverage
                entry_fee = notional * FEE_RATE
                entry_margin = capital - entry_fee
                qty = notional / close[i] if close[i] > 0 else 0.0
                entry_price = float(close[i])
                liq_price = max(entry_price - entry_margin / qty, 0.0) if qty > 0 else 0.0
                entry_idx = i
                in_position = qty > 0

        if in_position:
            equity = max(entry_margin + (close[i] - entry_price) * qty, 0.0)
            pos_label = "long"
        else:
            equity = capital
            pos_label = "flat"

        curve_rows.append(
            {
                "timestamp": pd.Timestamp(timestamps[i]),
                "variant": cfg["variant"],
                "equity": float(equity),
                "position": pos_label,
            }
        )

    if in_position and (not bankrupt):
        final_price = float(close[-1])
        exit_fee = qty * final_price * FEE_RATE
        pnl = (final_price - entry_price) * qty
        capital = max(entry_margin + pnl - exit_fee, 0.0)
        final_exits += 1
        trade_rows.append(
            {
                "variant": cfg["variant"],
                "side": "LONG",
                "entry_time": pd.Timestamp(timestamps[entry_idx]),
                "exit_time": pd.Timestamp(timestamps[-1]),
                "entry_price": float(entry_price),
                "exit_price": final_price,
                "exit_reason": "final",
                "bars_held": int(len(work) - 1 - entry_idx),
                "hours_held": float((len(work) - 1 - entry_idx) * 0.25),
                "entry_capital": float(entry_capital),
                "exit_capital": float(capital),
                "return_pct": (capital / entry_capital - 1.0) * 100.0 if entry_capital > 0 else np.nan,
                "leverage": leverage,
                "tp_pct": tp_pct,
                "sl_pct": sl_pct,
            }
        )
        curve_rows[-1]["equity"] = float(capital)
        curve_rows[-1]["position"] = "flat"

    curve = pd.DataFrame(curve_rows)
    trades = pd.DataFrame(trade_rows)

    stats = compute_curve_stats(curve, INITIAL_CAPITAL)
    wins = int((trades["return_pct"] > 0).sum()) if not trades.empty else 0
    stats.update(
        {
            "variant": cfg["variant"],
            "threshold_pct": threshold_pct,
            "leverage": leverage,
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
            "trades": int(len(trades)),
            "win_rate_pct": float(wins / len(trades) * 100.0) if len(trades) else np.nan,
            "avg_trade_return_pct": float(trades["return_pct"].mean()) if len(trades) else np.nan,
            "avg_hours_held": float(trades["hours_held"].mean()) if len(trades) else np.nan,
            "median_hours_held": float(trades["hours_held"].median()) if len(trades) else np.nan,
            "max_hours_held": float(trades["hours_held"].max()) if len(trades) else np.nan,
            "tp_exits": int(tp_exits),
            "stop_exits": int(stop_exits),
            "liquidations": int(liquidations),
            "final_exits": int(final_exits),
            "signal_crosses": int(signal_crosses),
            "actual_entries": int(len(trades)),
            "bankrupt": bool(bankrupt),
        }
    )
    return curve, trades, stats


def select_curve_variants(metrics_df: pd.DataFrame) -> list[str]:
    selected = ["buy_hold", BASE_VARIANT]

    live = metrics_df[metrics_df["variant"] != "buy_hold"].copy()
    if not live.empty:
        best_final = live.sort_values(["final_equity", "calmar_ratio"], ascending=[False, False]).iloc[0]["variant"]
        best_calmar = live.sort_values(["calmar_ratio", "final_equity"], ascending=[False, False]).iloc[0]["variant"]
        selected.extend([best_final, best_calmar])

    lever_tp10_sl10 = metrics_df[
        (metrics_df["variant"] != "buy_hold")
        & (metrics_df["tp_pct"] == 10.0)
        & (metrics_df["sl_pct"] == 10.0)
    ].sort_values("leverage")
    selected.extend(lever_tp10_sl10["variant"].head(6).tolist())
    return list(dict.fromkeys(selected))


def save_plot(metrics_df: pd.DataFrame, curves_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    ax_eq, ax_tp_heat, ax_sl_heat, ax_lev = axes.flatten()

    selected = select_curve_variants(metrics_df)
    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(selected)}

    for variant in selected:
        sub = curves_df[curves_df["variant"] == variant]
        if sub.empty:
            continue
        lw = 1.8 if variant == BASE_VARIANT else 1.1
        ax_eq.plot(sub["timestamp"], sub["equity"], linewidth=lw, label=variant, color=colors[variant])
    ax_eq.axhline(INITIAL_CAPITAL, color="black", linestyle="--", linewidth=0.9)
    ax_eq.set_title("108 Sequential Equity Curves")
    ax_eq.set_ylabel("Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", fontsize=8, ncol=2)

    base_sl = 10.0
    heat_tp = metrics_df[
        (metrics_df["variant"] != "buy_hold")
        & (metrics_df["sl_pct"] == base_sl)
    ].pivot(index="leverage", columns="tp_pct", values="final_equity").sort_index()
    im1 = ax_tp_heat.imshow(heat_tp.values, aspect="auto", cmap="viridis")
    ax_tp_heat.set_title("Final Equity by Leverage x TP (SL=10)")
    ax_tp_heat.set_xticks(range(len(heat_tp.columns)), [str(c) for c in heat_tp.columns])
    ax_tp_heat.set_yticks(range(len(heat_tp.index)), [str(i) for i in heat_tp.index])
    ax_tp_heat.set_xlabel("TP %")
    ax_tp_heat.set_ylabel("Leverage x")
    fig.colorbar(im1, ax=ax_tp_heat, fraction=0.046, pad=0.04)

    base_tp = 10.0
    heat_sl = metrics_df[
        (metrics_df["variant"] != "buy_hold")
        & (metrics_df["tp_pct"] == base_tp)
    ].pivot(index="leverage", columns="sl_pct", values="final_equity").sort_index()
    im2 = ax_sl_heat.imshow(heat_sl.values, aspect="auto", cmap="viridis")
    ax_sl_heat.set_title("Final Equity by Leverage x SL (TP=10)")
    ax_sl_heat.set_xticks(range(len(heat_sl.columns)), [str(c) for c in heat_sl.columns])
    ax_sl_heat.set_yticks(range(len(heat_sl.index)), [str(i) for i in heat_sl.index])
    ax_sl_heat.set_xlabel("SL %")
    ax_sl_heat.set_ylabel("Leverage x")
    fig.colorbar(im2, ax=ax_sl_heat, fraction=0.046, pad=0.04)

    ladder = metrics_df[
        (metrics_df["variant"] != "buy_hold")
        & (metrics_df["tp_pct"] == 10.0)
        & (metrics_df["sl_pct"] == 10.0)
    ].sort_values("leverage")
    ax_lev.plot(ladder["leverage"], ladder["final_equity"], marker="o", label="Final equity")
    ax_lev_t = ax_lev.twinx()
    ax_lev_t.plot(ladder["leverage"], ladder["max_drawdown_pct"], marker="s", color="#d62728", label="MDD %")
    ax_lev.set_title("Base TP10 / SL10 Leverage Ladder")
    ax_lev.set_xlabel("Leverage x")
    ax_lev.set_ylabel("Final Equity")
    ax_lev_t.set_ylabel("MDD %")
    ax_lev.grid(True, alpha=0.2)
    h1, l1 = ax_lev.get_legend_handles_labels()
    h2, l2 = ax_lev_t.get_legend_handles_labels()
    ax_lev.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=170)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, trades_df: pd.DataFrame, signal_crosses: int) -> None:
    base = metrics_df[metrics_df["variant"] == BASE_VARIANT].iloc[0]
    live = metrics_df[metrics_df["variant"] != "buy_hold"].copy()
    best_final = live.sort_values(["final_equity", "calmar_ratio"], ascending=[False, False]).iloc[0]
    best_calmar = live.sort_values(["calmar_ratio", "final_equity"], ascending=[False, False]).iloc[0]
    ladder = live[(live["tp_pct"] == 10.0) & (live["sl_pct"] == 10.0)].sort_values("leverage")
    top10 = live.sort_values(["final_equity", "calmar_ratio"], ascending=[False, False]).head(10)

    lines: list[str] = []
    lines.append("# Study 108: Deep Gap Long with Leverage")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Long only")
    lines.append("- Entry when 15m close first crosses below `-20%` vs confirmed 4h EMA200")
    lines.append("- No timeout. Exit only by TP, SL, liquidation, or final mark")
    lines.append("- Position size = full equity * leverage")
    lines.append("- Fees: `0.04%` on entry notional and `0.04%` on exit notional")
    lines.append("- Intrabar order of events: liquidation first, then stop, then take-profit")
    lines.append(f"- Whole-sample signal crosses at `-20%`: `{signal_crosses}`")
    lines.append("")
    lines.append("## Base Case")
    lines.append(
        f"- Variant: `{BASE_VARIANT}` = `5x`, `TP +10%`, `SL -10%`"
    )
    lines.append(
        f"- Final Equity `{_fmt(base['final_equity'])}`, CAGR `{_fmt(base['cagr_pct'])}%`, "
        f"MDD `{_fmt(base['max_drawdown_pct'])}%`, trades `{int(base['trades'])}`, "
        f"win rate `{_fmt(base['win_rate_pct'])}%`, avg trade `{_fmt(base['avg_trade_return_pct'])}%`"
    )
    lines.append(
        f"- Avg / median / max hold: `{_fmt(base['avg_hours_held'])}h` / `{_fmt(base['median_hours_held'])}h` / "
        f"`{_fmt(base['max_hours_held'])}h`"
    )
    lines.append(
        f"- Exit counts: TP `{int(base['tp_exits'])}`, Stop `{int(base['stop_exits'])}`, "
        f"Liquidation `{int(base['liquidations'])}`, Final `{int(base['final_exits'])}`"
    )
    lines.append("")
    lines.append("## Best Variants")
    lines.append(
        f"- Best final equity: `{best_final['variant']}` -> equity `{_fmt(best_final['final_equity'])}`, "
        f"CAGR `{_fmt(best_final['cagr_pct'])}%`, MDD `{_fmt(best_final['max_drawdown_pct'])}%`"
    )
    lines.append(
        f"- Best Calmar: `{best_calmar['variant']}` -> Calmar `{_fmt(best_calmar['calmar_ratio'])}`, "
        f"equity `{_fmt(best_calmar['final_equity'])}`, trades `{int(best_calmar['trades'])}`"
    )
    lines.append("")
    lines.append("## Leverage Ladder at TP10 / SL10")
    lines.append("| Leverage | Final Equity | CAGR % | MDD % | Trades | Win Rate % | Liquidations |")
    lines.append("| ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in ladder.iterrows():
        lines.append(
            f"| {_fmt(row['leverage'], 1)} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {int(row['trades'])} | {_fmt(row['win_rate_pct'])} | "
            f"{int(row['liquidations'])} |"
        )
    lines.append("")
    lines.append("## Top 10 by Final Equity")
    lines.append("| Variant | Leverage | TP % | SL % | Final Equity | CAGR % | MDD % | Calmar | Trades | Win Rate % |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in top10.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['leverage'], 1)} | {_fmt(row['tp_pct'], 1)} | {_fmt(row['sl_pct'], 1)} | "
            f"{_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | "
            f"{_fmt(row['calmar_ratio'])} | {int(row['trades'])} | {_fmt(row['win_rate_pct'])} |"
        )
    lines.append("")
    lines.append("## Caveat")
    lines.append("- `-20%` is a very small sample. Most variants only trade around 8-13 times, so ranking stability is weak.")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    m107 = load_module("study107_gap", BASE_107_PATH)
    df_1m, df_4h, _ = m107.load_market_data()
    market = m107.build_market_frame(df_1m, df_4h)

    signal_crosses = int(((market["gap_pct"] <= -THRESHOLD_PCT) & (market["gap_pct"].shift(1) > -THRESHOLD_PCT)).sum())

    variants = build_variants()
    metrics_rows: list[dict] = []
    trade_frames: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    buy_curve, buy_trades, buy_stats = run_buy_hold(market)
    metrics_rows.append(buy_stats)
    trade_frames.append(buy_trades)
    curve_map["buy_hold"] = buy_curve

    for cfg in variants:
        curve, trades, stats = run_variant(market, cfg)
        metrics_rows.append(stats)
        trade_frames.append(trades)
        curve_map[cfg["variant"]] = curve

    metrics_df = pd.DataFrame(metrics_rows).sort_values(["variant"]).reset_index(drop=True)
    trades_df = pd.concat(trade_frames, ignore_index=True)

    selected_variants = select_curve_variants(metrics_df)
    curves_df = pd.concat([curve_map[v] for v in selected_variants if v in curve_map], ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    trades_df.to_csv(OUT_TRADES_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)

    save_plot(metrics_df, curves_df)
    save_report(metrics_df, trades_df, signal_crosses)

    base = metrics_df[metrics_df["variant"] == BASE_VARIANT].iloc[0]
    print(
        "study=108, "
        f"signals={signal_crosses}, "
        f"base_final={base['final_equity']:.2f}, "
        f"base_cagr={base['cagr_pct']:.2f}, "
        f"base_mdd={base['max_drawdown_pct']:.2f}, "
        f"base_trades={int(base['trades'])}"
    )


if __name__ == "__main__":
    main()
