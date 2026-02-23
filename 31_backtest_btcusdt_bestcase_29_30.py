from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
BASE_28_PATH = Path("28_backtest_btcusdt_08_02_split500.py")
BASE_29_PATH = Path("29_backtest_btcusdt_08_longonly_max_entries_sweep.py")
BASE_30_PATH = Path("30_backtest_btcusdt_02_both_max_entries_sweep.py")

SRC_29_CSV = Path("29_backtest_btcusdt_08_longonly_max_entries_sweep.csv")
SRC_30_CSV = Path("30_backtest_btcusdt_02_both_max_entries_sweep.csv")

OUT_BASE = "31_backtest_btcusdt_bestcase_29_30"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_EQUITY_CSV = Path(f"{OUT_BASE}_equity.csv")
OUT_MD = Path(f"{OUT_BASE}.md")

LEG_CAPITAL = 500.0
TOTAL_CAPITAL = 1000.0
ENTRY_SCALE = 0.50


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


def pick_best_case(csv_path: Path, source_name: str) -> dict:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing source metrics csv: {csv_path}")
    df = pd.read_csv(csv_path)
    needed = {"max_entries", "cagr_pct", "calmar_ratio", "max_drawdown_pct", "final_equity"}
    miss = needed - set(df.columns)
    if miss:
        raise ValueError(f"{source_name} csv missing required columns: {sorted(miss)}")

    ranked = df.sort_values(
        by=["calmar_ratio", "cagr_pct", "final_equity", "max_drawdown_pct"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    best = ranked.iloc[0]
    return {
        "source": source_name,
        "max_entries": int(best["max_entries"]),
        "final_equity": float(best["final_equity"]),
        "cagr_pct": float(best["cagr_pct"]),
        "max_drawdown_pct": float(best["max_drawdown_pct"]),
        "calmar_ratio": float(best["calmar_ratio"]),
    }


def build_metrics_row(name: str, initial_capital: float, metrics: dict) -> dict:
    return {
        "portfolio": name,
        "initial_capital": float(initial_capital),
        "final_equity": float(metrics.get("final_equity", np.nan)),
        "total_return_pct": float(metrics.get("total_return_pct", np.nan)),
        "cagr_pct": float(metrics.get("cagr_pct", np.nan)),
        "max_drawdown_pct": float(metrics.get("max_drawdown_pct", np.nan)),
        "calmar_ratio": float(metrics.get("calmar_ratio", np.nan)),
        "trades": int(metrics.get("trades", 0)),
        "long_trades": int(metrics.get("long_trades", 0)),
        "short_trades": int(metrics.get("short_trades", 0)),
        "win_rate_pct": float(metrics.get("win_rate_pct", np.nan)),
        "profit_factor": float(metrics.get("profit_factor", np.nan)),
    }


def save_plot(eq_combined: pd.DataFrame, eq_08: pd.DataFrame, eq_02: pd.DataFrame, m08: int, m02: int):
    fig, axes = plt.subplots(3, 1, figsize=(16, 11), sharex=True, gridspec_kw={"height_ratios": [1.35, 1.0, 1.0]})
    ax0, ax1, ax2 = axes

    ax0.plot(eq_combined["timestamp"], eq_combined["equity_combined"], color="#111111", linewidth=1.2, label="Combined Equity (1000)")
    ax0.axhline(TOTAL_CAPITAL, color="#666666", linestyle="--", linewidth=0.9, label="Start 1000")
    ax0.set_title(f"31 Study: Best Cases from 29/30 | 08 max_entries={m08} + 02 max_entries={m02}")
    ax0.set_ylabel("Equity (USDT)")
    ax0.grid(True, alpha=0.2)
    ax0.legend(loc="upper left")

    ax1.plot(eq_08["timestamp"], eq_08["equity"], color="#1f77b4", linewidth=1.0, label=f"08 Long-only Best (500), max_entries={m08}")
    ax1.axhline(LEG_CAPITAL, color="#6fa3dc", linestyle="--", linewidth=0.9, label="Start 500")
    ax1.set_ylabel("Equity (USDT)")
    ax1.grid(True, alpha=0.2)
    ax1.legend(loc="upper left")

    ax2.plot(eq_02["timestamp"], eq_02["equity"], color="#d62728", linewidth=1.0, label=f"02 Both-sides Best (500), max_entries={m02}")
    ax2.axhline(LEG_CAPITAL, color="#e59b9b", linestyle="--", linewidth=0.9, label="Start 500")
    ax2.set_ylabel("Equity (USDT)")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.2)
    ax2.legend(loc="upper left")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(
    best08: dict,
    best02: dict,
    metrics_df: pd.DataFrame,
    trades_08: pd.DataFrame,
    trades_02: pd.DataFrame,
    corr_daily_returns: float,
):
    reason_08 = summarize_trade_reasons(trades_08)
    reason_02 = summarize_trade_reasons(trades_02)

    lines: list[str] = []
    lines.append("# 31 Backtest: Best Cases from 29 and 30 (No-lookahead)")
    lines.append("")
    lines.append("## Selected Cases")
    lines.append("- Selection rule: highest `Calmar`, tie-breaker `CAGR`, then `Final Equity`.")
    lines.append("| Source Study | Strategy | Selected max entries | Source Final Equity | Source CAGR % | Source MDD % | Source Calmar |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    lines.append(
        f"| `29` | `08 long-only + trend short hedge` | {best08['max_entries']} | {_fmt(best08['final_equity'])} | "
        f"{_fmt(best08['cagr_pct'])} | {_fmt(best08['max_drawdown_pct'])} | {_fmt(best08['calmar_ratio'])} |"
    )
    lines.append(
        f"| `30` | `02 both-sides` | {best02['max_entries']} | {_fmt(best02['final_equity'])} | "
        f"{_fmt(best02['cagr_pct'])} | {_fmt(best02['max_drawdown_pct'])} | {_fmt(best02['calmar_ratio'])} |"
    )
    lines.append("")
    lines.append("## Common Strategy Layer")
    lines.append("- Symbol/data: BTCUSDT, cached 1m + 4h raw data (same universe as studies 29/30).")
    lines.append("- Risk baseline params (same in both legs): `RSI oversold=18`, `RSI overbought=85`, `TP=1.2%`, `SL=3.0%`, `cooldown=5 bars`.")
    lines.append("- Position sizing: floor-scaled averaging with `entry_scale=0.50` and max entries cap from selected case.")
    lines.append("- No-lookahead guard (same in both): `ema200_4h = EWM(close_4h, 200).shift(1)`.")
    lines.append("- No-lookahead guard (same in both): `ema_touch_confirmed = ema_touch_raw.shift(1)`.")
    lines.append("- Time consistency: current 1m bar only sees already-closed 4h states.")
    lines.append("")
    lines.append("## Execution Flow Comparison")
    lines.append("| Step | Shared Logic | 08 leg behavior | 02 leg behavior |")
    lines.append("|---|---|---|---|")
    lines.append("| 1. Regime base | Build confirmed 4h EMA200/touch state | Same | Same |")
    lines.append("| 2. Entry filter | Respect cooldown + no-touch gate | Long entry only when bullish + RSI<=oversold | Long entry in bullish + short entry in bearish |")
    lines.append("| 3. Position scaling | Add units up to selected `max_entries` cap | Cap=`5` from study 29 best case | Cap=`4` from study 30 best case |")
    lines.append("| 4. Short handling | Strategy-specific | No strategy short; separate 4h trend hedge short (`5x`) | Strategy short entries are native side of core logic |")
    lines.append("| 5. Exit accounting | TP/SL/reverse/final close | Includes hedge open/close effects | No hedge events |")
    lines.append("")
    lines.append("## Different Strategy Layer")
    lines.append("| Item | 08 leg (from 29) | 02 leg (from 30) |")
    lines.append("|---|---|---|")
    lines.append("| Core mode | Long-only entries + trend short hedge | Both long + short strategy entries |")
    lines.append("| Entry direction | Only long entries allowed | Long in bullish + short in bearish |")
    lines.append("| 4h trend usage | Hysteresis 4h trend state, then confirmed with `shift(1)` | No hysteresis trend state; uses 1m close vs 4h EMA200 for bullish/bearish |")
    lines.append("| Short exposure source | Hedge short (size = `5x` base long qty) when confirmed 4h bearish | Native short entries from strategy logic |")
    lines.append("| Expected behavior | Captures uptrend growth, uses hedge in bearish phases | More symmetric direction coverage, usually more trades |")
    lines.append("")
    lines.append("## Re-run Metrics (31)")
    lines.append("| Portfolio | Initial | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['portfolio']}` | {_fmt(r['initial_capital'])} | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | "
            f"{_fmt(r['cagr_pct'])} | {_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} |"
        )
    lines.append(f"- Daily return correlation between selected 08 and 02 legs: `{_fmt(corr_daily_returns)}`.")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- 08 best case is the dominant profit contributor in this pair; growth is concentrated on long-trend capture.")
    lines.append("- 02 best case adds directional coverage via native short entries, but drawdown reduction is limited here.")
    lines.append("- Positive daily-return correlation means the two legs are not consistently offsetting each other.")
    lines.append("- Combined profile stays high-growth/high-drawdown rather than low-volatility.")
    lines.append("")
    lines.append("## Reason Breakdown (31 Re-run)")
    lines.append("### 08 Leg")
    lines.append("| Reason | Trades | Win Rate % | Net PnL | Avg PnL |")
    lines.append("|---|---:|---:|---:|---:|")
    if reason_08.empty:
        lines.append("| `N/A` | 0 | N/A | N/A | N/A |")
    else:
        for _, r in reason_08.head(12).iterrows():
            lines.append(
                f"| `{r['reason']}` | {int(r['trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['net_pnl'])} | {_fmt(r['avg_pnl'])} |"
            )
    lines.append("")
    lines.append("### 02 Leg")
    lines.append("| Reason | Trades | Win Rate % | Net PnL | Avg PnL |")
    lines.append("|---|---:|---:|---:|---:|")
    if reason_02.empty:
        lines.append("| `N/A` | 0 | N/A | N/A | N/A |")
    else:
        for _, r in reason_02.head(12).iterrows():
            lines.append(
                f"| `{r['reason']}` | {int(r['trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['net_pnl'])} | {_fmt(r['avg_pnl'])} |"
            )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics: `{OUT_CSV}`")
    lines.append(f"- Equity series: `{OUT_EQUITY_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def summarize_trade_reasons(trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return pd.DataFrame(columns=["reason", "trades", "win_rate_pct", "net_pnl", "avg_pnl"])
    t = trades_df.copy()
    g = (
        t.groupby("reason", dropna=False)
        .agg(
            trades=("pnl", "size"),
            win_rate_pct=("pnl", lambda x: float((x > 0).mean() * 100.0)),
            net_pnl=("pnl", "sum"),
            avg_pnl=("pnl", "mean"),
        )
        .reset_index()
        .sort_values("net_pnl", ascending=False)
    )
    return g


def run():
    base = load_module("m002_31", BASE_002_PATH)
    helper = load_module("m04_31", BASE_04_PATH)
    m28 = load_module("m28_31", BASE_28_PATH)
    m29 = load_module("m29_31", BASE_29_PATH)
    m30 = load_module("m30_31", BASE_30_PATH)

    best08 = pick_best_case(SRC_29_CSV, "29")
    best02 = pick_best_case(SRC_30_CSV, "30")

    if abs(m29.ENTRY_SCALE - ENTRY_SCALE) > 1e-12 or abs(m30.ENTRY_SCALE - ENTRY_SCALE) > 1e-12:
        raise ValueError("ENTRY_SCALE mismatch with source studies 29/30.")

    df_1m, df_4h = m28.load_data_no_filter(base)
    df_1m = df_1m[(df_1m.index >= base.BACKTEST_START) & (df_1m.index <= base.BACKTEST_END)].copy()

    base_08_cls = m28.build_08_no_lookahead_class(base, helper)
    cls_08_best = m29.build_max_entries_class(base_08_cls, best08["max_entries"])
    cls_02_best = m30.build_max_entries_class(base.FloorScaledRSIAveragingBacktest, best02["max_entries"])

    bt_08 = cls_08_best(
        symbol=base.SYMBOL,
        initial_capital=LEG_CAPITAL,
        commission=base.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    bt_02 = cls_02_best(
        symbol=base.SYMBOL,
        initial_capital=LEG_CAPITAL,
        commission=base.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )

    helper.configure_baseline_params(bt_08)
    helper.configure_baseline_params(bt_02)

    bt_08.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)
    bt_02.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)

    eq_08 = pd.DataFrame(bt_08.equity_curve)
    eq_02 = pd.DataFrame(bt_02.equity_curve)
    if eq_08.empty or eq_02.empty:
        raise RuntimeError("Empty equity curve in one of the selected best-case legs.")
    eq_08["timestamp"] = pd.to_datetime(eq_08["timestamp"])
    eq_02["timestamp"] = pd.to_datetime(eq_02["timestamp"])
    eq_08 = eq_08.sort_values("timestamp")[["timestamp", "equity"]].copy()
    eq_02 = eq_02.sort_values("timestamp")[["timestamp", "equity"]].copy()

    eq_combined = m28.build_combined_curve(eq_08, eq_02)
    if eq_combined.empty:
        raise RuntimeError("Combined equity curve is empty.")
    eq_combined = eq_combined[["timestamp", "equity_combined", "equity_08", "equity_02"]].copy()
    eq_combined.to_csv(OUT_EQUITY_CSV, index=False)

    m_08 = helper.calculate_metrics(bt_08, LEG_CAPITAL)
    m_02 = helper.calculate_metrics(bt_02, LEG_CAPITAL)
    m_comb = m28.compute_curve_metrics(
        eq_combined[["timestamp", "equity_combined"]].rename(columns={"equity_combined": "equity"}),
        TOTAL_CAPITAL,
    )
    m_comb["trades"] = int(m_08.get("trades", 0) + m_02.get("trades", 0))
    m_comb["long_trades"] = int(m_08.get("long_trades", 0) + m_02.get("long_trades", 0))
    m_comb["short_trades"] = int(m_08.get("short_trades", 0) + m_02.get("short_trades", 0))
    m_comb["win_rate_pct"] = np.nan
    m_comb["profit_factor"] = np.nan

    metrics_df = pd.DataFrame(
        [
            build_metrics_row("combined_1000", TOTAL_CAPITAL, m_comb),
            build_metrics_row(f"08_best_500_me{best08['max_entries']}", LEG_CAPITAL, m_08),
            build_metrics_row(f"02_best_500_me{best02['max_entries']}", LEG_CAPITAL, m_02),
        ]
    )
    metrics_df.to_csv(OUT_CSV, index=False)

    d08 = eq_08.copy().set_index("timestamp").resample("1D").last().pct_change()
    d02 = eq_02.copy().set_index("timestamp").resample("1D").last().pct_change()
    d = d08.rename(columns={"equity": "ret_08"}).join(d02.rename(columns={"equity": "ret_02"}), how="inner").dropna()
    corr_daily_returns = float(d["ret_08"].corr(d["ret_02"])) if not d.empty else np.nan

    trades_08 = pd.DataFrame(bt_08.trades)
    trades_02 = pd.DataFrame(bt_02.trades)

    save_plot(eq_combined, eq_08, eq_02, best08["max_entries"], best02["max_entries"])
    save_report(best08, best02, metrics_df, trades_08, trades_02, corr_daily_returns)

    print(f"selected_08_max_entries={best08['max_entries']}")
    print(f"selected_02_max_entries={best02['max_entries']}")
    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_equity={OUT_EQUITY_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    run()
