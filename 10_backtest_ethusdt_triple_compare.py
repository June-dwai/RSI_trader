from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
BASE_08_PATH = Path("08_backtest_btcusdt_hysteresis_sweep.py")
BASE_08_CSV = Path("08_backtest_btcusdt_hysteresis_sweep.csv")

TARGET_SYMBOL = "ETHUSDT"

SCRIPT_FILE = Path("10_backtest_ethusdt_triple_compare.py")
PLOT_FILE = Path("10_backtest_ethusdt_triple_compare.png")
CSV_FILE = Path("10_backtest_ethusdt_triple_compare.csv")
MD_FILE = Path("10_backtest_ethusdt_triple_compare.md")

STRAT_02 = "02_baseline"
STRAT_04 = "04_long_only_with_trend_short_hedge_5x"
STRAT_08 = "08_best_hysteresis_fixed5x"
STRATEGIES = [STRAT_02, STRAT_04, STRAT_08]

DEFAULT_BEST_HYST_BAND = 0.005


@dataclass
class BacktestResult:
    name: str
    bt: object
    summary: dict
    equity: pd.DataFrame
    trades: pd.DataFrame
    monthly_returns: pd.Series
    drawdown_curve: pd.Series
    max_dd_episode: dict
    reason_pnl: pd.DataFrame


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


def detect_best_hysteresis_band(path: Path, fallback: float = DEFAULT_BEST_HYST_BAND) -> float:
    if not path.exists():
        return fallback
    try:
        df = pd.read_csv(path)
    except Exception:
        return fallback
    if df.empty:
        return fallback
    if "band" not in df.columns or "final_equity" not in df.columns:
        return fallback
    row = df.sort_values("final_equity", ascending=False).iloc[0]
    return float(row["band"])


def _safe_div(a: float, b: float) -> float:
    if b == 0:
        return np.nan
    return a / b


def _max_streak(values: pd.Series, cond) -> int:
    max_run = 0
    run = 0
    for v in values.tolist():
        if cond(v):
            run += 1
            if run > max_run:
                max_run = run
        else:
            run = 0
    return int(max_run)


def compute_drawdown_episode(eq: pd.DataFrame) -> dict:
    if eq.empty:
        return {
            "peak_time": pd.NaT,
            "trough_time": pd.NaT,
            "recovery_time": pd.NaT,
            "depth_pct": np.nan,
            "loss_amount": np.nan,
            "peak_to_trough_days": np.nan,
            "recovery_days": np.nan,
        }

    e = eq["equity"].astype(float)
    t = pd.to_datetime(eq["timestamp"])
    cummax = e.cummax()
    dd = (e / cummax) - 1.0
    trough_idx = int(dd.idxmin())

    peak_idx = int(e.loc[:trough_idx].idxmax())
    peak_val = float(e.loc[peak_idx])
    trough_val = float(e.loc[trough_idx])

    recovery_idx = None
    for i in range(trough_idx, len(e)):
        if e.iloc[i] >= peak_val:
            recovery_idx = i
            break

    peak_time = pd.Timestamp(t.iloc[peak_idx])
    trough_time = pd.Timestamp(t.iloc[trough_idx])
    recovery_time = pd.Timestamp(t.iloc[recovery_idx]) if recovery_idx is not None else pd.NaT

    return {
        "peak_time": peak_time,
        "trough_time": trough_time,
        "recovery_time": recovery_time,
        "depth_pct": float(-dd.iloc[trough_idx] * 100.0),
        "loss_amount": float(peak_val - trough_val),
        "peak_to_trough_days": float((trough_time - peak_time).total_seconds() / 86400.0),
        "recovery_days": float((recovery_time - peak_time).total_seconds() / 86400.0) if recovery_idx is not None else np.nan,
    }


def summarize_detailed(bt, initial_capital: float) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, dict, pd.DataFrame]:
    eq = pd.DataFrame(bt.equity_curve)
    tr = pd.DataFrame(bt.trades)

    if eq.empty:
        summary = {
            "period_start": pd.NaT,
            "period_end": pd.NaT,
            "final_equity": 0.0,
            "total_return_pct": -100.0,
            "cagr_pct": -100.0,
            "max_drawdown_pct": 100.0,
            "max_drawdown_amount": np.nan,
            "calmar_ratio": np.nan,
            "annual_volatility_pct": np.nan,
            "sharpe_365": np.nan,
            "sortino_365": np.nan,
            "trades": 0,
            "long_trades": 0,
            "short_trades": 0,
            "win_rate_pct": 0.0,
            "long_win_rate_pct": 0.0,
            "short_win_rate_pct": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "net_pnl_sum": 0.0,
            "profit_factor": np.nan,
            "avg_pnl_per_trade": np.nan,
            "median_pnl_per_trade": np.nan,
            "avg_return_pct_per_trade": np.nan,
            "median_return_pct_per_trade": np.nan,
            "avg_holding_hours": np.nan,
            "median_holding_hours": np.nan,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
            "best_trade_pnl": np.nan,
            "worst_trade_pnl": np.nan,
            "best_trade_reason": None,
            "worst_trade_reason": None,
        }
        monthly = pd.Series(dtype=float)
        dd_curve = pd.Series(dtype=float)
        episode = compute_drawdown_episode(eq)
        reason = pd.DataFrame(columns=["side", "reason", "trades", "pnl_sum", "pnl_avg"])
        return summary, eq, tr, monthly, dd_curve, episode, reason

    eq["timestamp"] = pd.to_datetime(eq["timestamp"])
    eq = eq.sort_values("timestamp").reset_index(drop=True)
    start = pd.Timestamp(eq["timestamp"].iloc[0])
    end = pd.Timestamp(eq["timestamp"].iloc[-1])
    equity = eq["equity"].astype(float)

    final_equity = float(equity.iloc[-1])
    total_return_pct = (final_equity - initial_capital) / initial_capital * 100.0

    years = max((end - start).days / 365.25, 1e-9)
    cagr_pct = (pow(max(final_equity, 1e-12) / initial_capital, 1.0 / years) - 1.0) * 100.0

    cummax = equity.cummax()
    dd = (equity / cummax) - 1.0
    max_dd_pct = float(-dd.min() * 100.0)
    max_dd_amt = float((cummax - equity).max())
    calmar = _safe_div(cagr_pct, max_dd_pct)

    eq_daily = eq.set_index("timestamp")["equity"].resample("1D").last().dropna()
    daily_ret = eq_daily.pct_change().dropna()
    vol = float(daily_ret.std(ddof=0) * math.sqrt(365) * 100.0) if len(daily_ret) > 1 else np.nan
    sharpe = float((daily_ret.mean() / daily_ret.std(ddof=0)) * math.sqrt(365)) if len(daily_ret) > 1 and daily_ret.std(ddof=0) > 0 else np.nan
    downside = daily_ret[daily_ret < 0]
    sortino = float((daily_ret.mean() / downside.std(ddof=0)) * math.sqrt(365)) if len(downside) > 1 and downside.std(ddof=0) > 0 else np.nan

    monthly = eq.set_index("timestamp")["equity"].resample("ME").last().dropna().pct_change().dropna() * 100.0

    if not tr.empty:
        tr = tr.copy()
        tr["entry_time"] = pd.to_datetime(tr["entry_time"])
        tr["exit_time"] = pd.to_datetime(tr["exit_time"])

        long_tr = tr[tr["side"] == "LONG"]
        short_tr = tr[tr["side"] == "SHORT"]

        win_rate = float((tr["pnl"] > 0).mean() * 100.0)
        long_win = float((long_tr["pnl"] > 0).mean() * 100.0) if len(long_tr) else 0.0
        short_win = float((short_tr["pnl"] > 0).mean() * 100.0) if len(short_tr) else 0.0

        gross_profit = float(tr.loc[tr["pnl"] > 0, "pnl"].sum())
        gross_loss = float(tr.loc[tr["pnl"] < 0, "pnl"].sum())
        net_pnl_sum = float(tr["pnl"].sum())
        pf = float(gross_profit / abs(gross_loss)) if gross_loss < 0 else np.inf

        avg_pnl = float(tr["pnl"].mean())
        med_pnl = float(tr["pnl"].median())
        avg_ret = float(tr["return_pct"].mean())
        med_ret = float(tr["return_pct"].median())

        holding_h = (tr["exit_time"] - tr["entry_time"]).dt.total_seconds() / 3600.0
        avg_hold = float(holding_h.mean())
        med_hold = float(holding_h.median())

        max_wins = _max_streak(tr["pnl"], lambda x: x > 0)
        max_losses = _max_streak(tr["pnl"], lambda x: x < 0)

        best_idx = tr["pnl"].idxmax()
        worst_idx = tr["pnl"].idxmin()
        best_pnl = float(tr.loc[best_idx, "pnl"])
        worst_pnl = float(tr.loc[worst_idx, "pnl"])
        best_reason = str(tr.loc[best_idx, "reason"])
        worst_reason = str(tr.loc[worst_idx, "reason"])

        reason = tr.groupby(["side", "reason"], as_index=False).agg(
            trades=("pnl", "count"),
            pnl_sum=("pnl", "sum"),
            pnl_avg=("pnl", "mean"),
        ).sort_values(["side", "pnl_sum"], ascending=[True, True])
    else:
        win_rate = 0.0
        long_win = 0.0
        short_win = 0.0
        gross_profit = 0.0
        gross_loss = 0.0
        net_pnl_sum = 0.0
        pf = np.nan
        avg_pnl = np.nan
        med_pnl = np.nan
        avg_ret = np.nan
        med_ret = np.nan
        avg_hold = np.nan
        med_hold = np.nan
        max_wins = 0
        max_losses = 0
        best_pnl = np.nan
        worst_pnl = np.nan
        best_reason = None
        worst_reason = None
        reason = pd.DataFrame(columns=["side", "reason", "trades", "pnl_sum", "pnl_avg"])

    summary = {
        "period_start": start,
        "period_end": end,
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": max_dd_pct,
        "max_drawdown_amount": max_dd_amt,
        "calmar_ratio": calmar,
        "annual_volatility_pct": vol,
        "sharpe_365": sharpe,
        "sortino_365": sortino,
        "trades": int(len(tr)),
        "long_trades": int((tr["side"] == "LONG").sum()) if not tr.empty else 0,
        "short_trades": int((tr["side"] == "SHORT").sum()) if not tr.empty else 0,
        "win_rate_pct": win_rate,
        "long_win_rate_pct": long_win,
        "short_win_rate_pct": short_win,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_pnl_sum": net_pnl_sum,
        "profit_factor": pf,
        "avg_pnl_per_trade": avg_pnl,
        "median_pnl_per_trade": med_pnl,
        "avg_return_pct_per_trade": avg_ret,
        "median_return_pct_per_trade": med_ret,
        "avg_holding_hours": avg_hold,
        "median_holding_hours": med_hold,
        "max_consecutive_wins": max_wins,
        "max_consecutive_losses": max_losses,
        "best_trade_pnl": best_pnl,
        "worst_trade_pnl": worst_pnl,
        "best_trade_reason": best_reason,
        "worst_trade_reason": worst_reason,
    }

    episode = compute_drawdown_episode(eq)
    return summary, eq, tr, monthly, dd, episode, reason


def run_strategy(name: str, bt, base_module) -> BacktestResult:
    summary, eq, tr, monthly, dd_curve, episode, reason = summarize_detailed(bt, base_module.INITIAL_CAPITAL)
    return BacktestResult(
        name=name,
        bt=bt,
        summary=summary,
        equity=eq,
        trades=tr,
        monthly_returns=monthly,
        drawdown_curve=dd_curve,
        max_dd_episode=episode,
        reason_pnl=reason,
    )


def save_plot(results: list[BacktestResult]):
    colors = {
        STRAT_02: "#1f77b4",
        STRAT_04: "#d62728",
        STRAT_08: "#2ca02c",
    }

    fig = plt.figure(figsize=(16, 11))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title(f"10 Strategy Comparison ({TARGET_SYMBOL}): 02 vs 04 vs 08-best")
    ax_eq.set_ylabel("Equity (USDT)")
    for r in results:
        if r.equity.empty:
            continue
        ax_eq.plot(r.equity["timestamp"], r.equity["equity"], label=r.name, linewidth=1.2, color=colors.get(r.name))
    ax_eq.legend(loc="upper left")
    ax_eq.grid(True, alpha=0.2)

    ax_final = fig.add_subplot(gs[1, 0])
    ax_final.set_title("Final Equity")
    ax_final.bar([r.name for r in results], [r.summary["final_equity"] for r in results], color=[colors.get(r.name) for r in results])
    ax_final.set_ylabel("USDT")
    ax_final.tick_params(axis="x", rotation=12)
    ax_final.grid(True, axis="y", alpha=0.2)

    ax_dd = fig.add_subplot(gs[1, 1])
    ax_dd.set_title("Max Drawdown")
    ax_dd.bar([r.name for r in results], [r.summary["max_drawdown_pct"] for r in results], color=[colors.get(r.name) for r in results])
    ax_dd.set_ylabel("MDD (%)")
    ax_dd.tick_params(axis="x", rotation=12)
    ax_dd.grid(True, axis="y", alpha=0.2)

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
    plt.close()


def _fmt(v, digits=4, suffix=""):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "N/A"
    return f"{v:.{digits}f}{suffix}"


def _worst_month_text(monthly: pd.Series) -> str:
    if monthly.empty:
        return "N/A"
    idx = monthly.idxmin()
    return f"{idx.strftime('%Y-%m')} ({monthly.min():.4f}%)"


def save_csv(results: list[BacktestResult]):
    rows = []
    for r in results:
        row = dict(r.summary)
        row["strategy"] = r.name
        row["worst_month"] = _worst_month_text(r.monthly_returns)
        row["max_dd_peak_time"] = r.max_dd_episode["peak_time"]
        row["max_dd_trough_time"] = r.max_dd_episode["trough_time"]
        row["max_dd_recovery_time"] = r.max_dd_episode["recovery_time"]
        row["max_dd_peak_to_trough_days"] = r.max_dd_episode["peak_to_trough_days"]
        row["max_dd_recovery_days"] = r.max_dd_episode["recovery_days"]
        rows.append(row)

    df = pd.DataFrame(rows)
    preferred = [
        "strategy",
        "period_start",
        "period_end",
        "final_equity",
        "total_return_pct",
        "cagr_pct",
        "max_drawdown_pct",
        "max_drawdown_amount",
        "calmar_ratio",
        "annual_volatility_pct",
        "sharpe_365",
        "sortino_365",
        "trades",
        "long_trades",
        "short_trades",
        "win_rate_pct",
        "long_win_rate_pct",
        "short_win_rate_pct",
        "profit_factor",
        "avg_pnl_per_trade",
        "avg_holding_hours",
        "worst_month",
        "max_dd_peak_time",
        "max_dd_trough_time",
        "max_dd_recovery_time",
        "max_dd_peak_to_trough_days",
        "max_dd_recovery_days",
    ]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    df = df[cols]
    df.to_csv(CSV_FILE, index=False)


def _reason_table_text(reason_df: pd.DataFrame) -> str:
    if reason_df.empty:
        return "- N/A"
    lines = []
    for _, row in reason_df.iterrows():
        lines.append(
            f"- `{row['side']}` / `{row['reason']}`: trades={int(row['trades'])}, "
            f"pnl_sum={_fmt(float(row['pnl_sum']))}, pnl_avg={_fmt(float(row['pnl_avg']))}"
        )
    return "\n".join(lines)


def save_md(results: list[BacktestResult], best_band: float):
    by_name = {r.name: r for r in results}
    r02 = by_name[STRAT_02]
    r04 = by_name[STRAT_04]
    r08 = by_name[STRAT_08]

    lines: list[str] = []
    lines.append(f"# 10 Strategy Evolution Comparison ({TARGET_SYMBOL})")
    lines.append("")
    lines.append("## 1) Purpose")
    lines.append("- Compare three evolved strategies in one run with identical data and core parameters.")
    lines.append("- Target set:")
    lines.append(f"  - `{STRAT_02}`: base strategy from `002_backtest_btcusdt.py`.")
    lines.append(f"  - `{STRAT_04}`: long-only + confirmed 4h trend short hedge 5x from `04_backtest_btcusdt_mode_compare.py`.")
    lines.append(
        f"  - `{STRAT_08}`: fixed-base5x + hysteresis best variant from `08_backtest_btcusdt_hysteresis_sweep.py` "
        f"(band `{best_band * 100:.2f}%`)."
    )
    lines.append("")
    lines.append("## 2) Common Test Setup")
    lines.append(f"- Symbol: `{TARGET_SYMBOL}`")
    lines.append("- Data period: `2022-01-01` to `2026-02-12`")
    lines.append("- Initial capital: `1000 USDT`")
    lines.append("- Commission: `0.04%` per side")
    lines.append("- Entry scale: `0.50`")
    lines.append("- Confirmation policy for hedge variants: closed 4h state only (`shift(1)`, no look-ahead)")
    lines.append("")
    lines.append("## 3) Topline Performance")
    lines.append("")
    lines.append("| Strategy | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in results:
        s = r.summary
        lines.append(
            f"| `{r.name}` | {_fmt(s['final_equity'])} | {_fmt(s['total_return_pct'])} | {_fmt(s['cagr_pct'])} | "
            f"{_fmt(s['max_drawdown_pct'])} | {_fmt(s['calmar_ratio'])} | {int(s['trades'])} | "
            f"{int(s['long_trades'])}/{int(s['short_trades'])} | {_fmt(s['win_rate_pct'])} | {_fmt(s['profit_factor'])} |"
        )

    lines.append("")
    lines.append("## 4) Detailed Metrics")
    lines.append("")
    for r in results:
        s = r.summary
        e = r.max_dd_episode
        lines.append(f"### `{r.name}`")
        lines.append(f"- Period: `{s['period_start']}` ~ `{s['period_end']}`")
        lines.append(f"- Final Equity: `{_fmt(s['final_equity'])} USDT`")
        lines.append(f"- Total Return: `{_fmt(s['total_return_pct'])}%`")
        lines.append(f"- CAGR: `{_fmt(s['cagr_pct'])}%`")
        lines.append(f"- MDD: `{_fmt(s['max_drawdown_pct'])}%` (`{_fmt(s['max_drawdown_amount'])} USDT`)")
        lines.append(f"- Calmar: `{_fmt(s['calmar_ratio'])}`")
        lines.append(f"- Annual Volatility: `{_fmt(s['annual_volatility_pct'])}%`")
        lines.append(f"- Sharpe(365): `{_fmt(s['sharpe_365'])}`")
        lines.append(f"- Sortino(365): `{_fmt(s['sortino_365'])}`")
        lines.append(f"- Trades: `{int(s['trades'])}` (Long `{int(s['long_trades'])}`, Short `{int(s['short_trades'])}`)")
        lines.append(f"- Win Rate: `{_fmt(s['win_rate_pct'])}%` (Long `{_fmt(s['long_win_rate_pct'])}%`, Short `{_fmt(s['short_win_rate_pct'])}%`)")
        lines.append(f"- Gross Profit / Gross Loss: `{_fmt(s['gross_profit'])}` / `{_fmt(s['gross_loss'])}`")
        lines.append(f"- Net PnL Sum (trades): `{_fmt(s['net_pnl_sum'])}`")
        lines.append(f"- Avg/Median PnL per trade: `{_fmt(s['avg_pnl_per_trade'])}` / `{_fmt(s['median_pnl_per_trade'])}`")
        lines.append(f"- Avg/Median Return per trade: `{_fmt(s['avg_return_pct_per_trade'])}%` / `{_fmt(s['median_return_pct_per_trade'])}%`")
        lines.append(f"- Avg/Median Holding: `{_fmt(s['avg_holding_hours'])}h` / `{_fmt(s['median_holding_hours'])}h`")
        lines.append(f"- Max Consecutive Wins/Losses: `{int(s['max_consecutive_wins'])}` / `{int(s['max_consecutive_losses'])}`")
        lines.append(f"- Best/Worst Trade PnL: `{_fmt(s['best_trade_pnl'])}` / `{_fmt(s['worst_trade_pnl'])}`")
        lines.append(f"- Best/Worst Trade Reason: `{s['best_trade_reason']}` / `{s['worst_trade_reason']}`")
        lines.append(f"- Worst Month: `{_worst_month_text(r.monthly_returns)}`")
        lines.append(
            f"- Max DD Episode: peak `{e['peak_time']}`, trough `{e['trough_time']}`, "
            f"recovery `{e['recovery_time']}`, depth `{_fmt(e['depth_pct'])}%`, "
            f"peak->trough `{_fmt(e['peak_to_trough_days'])} days`"
        )
        lines.append("- PnL by side/reason:")
        lines.append(_reason_table_text(r.reason_pnl))
        lines.append("")

    lines.append("## 5) Comparative Interpretation")
    best_eq = max(results, key=lambda x: x.summary["final_equity"])
    best_calmar = max(results, key=lambda x: x.summary["calmar_ratio"] if not math.isnan(x.summary["calmar_ratio"]) else -1e9)
    best_mdd = min(results, key=lambda x: x.summary["max_drawdown_pct"])

    lines.append(f"- Best Final Equity: `{best_eq.name}` (`{_fmt(best_eq.summary['final_equity'])} USDT`).")
    lines.append(f"- Best Calmar: `{best_calmar.name}` (`{_fmt(best_calmar.summary['calmar_ratio'])}`).")
    lines.append(f"- Lowest MDD: `{best_mdd.name}` (`{_fmt(best_mdd.summary['max_drawdown_pct'])}%`).")
    lines.append("- Hysteresis best variant in this test uses a wider band to reduce unnecessary hedge flips.")
    lines.append("")
    lines.append("## 6) Output Files")
    lines.append(f"- script: `{SCRIPT_FILE}`")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{CSV_FILE}`")
    lines.append(f"- report: `{MD_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002", BASE_002_PATH)
    helper_04 = load_module("m04", BASE_04_PATH)
    helper_08 = load_module("m08", BASE_08_PATH)

    best_band = detect_best_hysteresis_band(BASE_08_CSV, DEFAULT_BEST_HYST_BAND)

    base_module.SYMBOL = TARGET_SYMBOL
    df_1m, df_4h = base_module.load_data()
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    # 02 baseline
    bt02 = base_module.FloorScaledRSIAveragingBacktest(
        symbol=base_module.SYMBOL,
        initial_capital=base_module.INITIAL_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=base_module.ENTRY_SCALE,
    )
    helper_04.configure_baseline_params(bt02)
    bt02.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)
    r02 = run_strategy(STRAT_02, bt02, base_module)

    # 04 best hedge mode class
    _, cls04 = helper_04.build_mode_classes(base_module)
    bt04 = cls04(
        symbol=base_module.SYMBOL,
        initial_capital=base_module.INITIAL_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=base_module.ENTRY_SCALE,
    )
    helper_04.configure_baseline_params(bt04)
    bt04.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)
    r04 = run_strategy(STRAT_04, bt04, base_module)

    # 08 best hysteresis class
    cls08 = helper_08.build_fixed5x_hyst_class(base_module, helper_04, best_band)
    bt08 = cls08(
        symbol=base_module.SYMBOL,
        initial_capital=base_module.INITIAL_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=base_module.ENTRY_SCALE,
    )
    helper_04.configure_baseline_params(bt08)
    bt08.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)
    r08 = run_strategy(STRAT_08, bt08, base_module)

    results = [r02, r04, r08]
    save_plot(results)
    save_csv(results)
    save_md(results, best_band)

    print(f"best_band_from_08={best_band * 100:.2f}%")
    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(f"saved_report={MD_FILE}")

    rows = []
    for r in results:
        s = r.summary
        rows.append(
            {
                "strategy": r.name,
                "final_equity": s["final_equity"],
                "total_return_pct": s["total_return_pct"],
                "cagr_pct": s["cagr_pct"],
                "max_drawdown_pct": s["max_drawdown_pct"],
                "trades": s["trades"],
                "long_trades": s["long_trades"],
                "short_trades": s["short_trades"],
                "win_rate_pct": s["win_rate_pct"],
                "profit_factor": s["profit_factor"],
            }
        )
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    run()
