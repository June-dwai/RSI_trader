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

SCRIPT_FILE = Path("11_backtest_ethusdt_hyst_tpsl_sweep.py")
PLOT_FILE = Path("11_backtest_ethusdt_hyst_tpsl_sweep.png")
CSV_FILE = Path("11_backtest_ethusdt_hyst_tpsl_sweep.csv")
MD_FILE = Path("11_backtest_ethusdt_hyst_tpsl_sweep.md")

TARGET_SYMBOL = "ETHUSDT"
ENTRY_SCALE_OVERRIDE = 0.40

# ETH sweep: wider hysteresis than BTC-centric ranges.
HYSTERESIS_BANDS = [0.000, 0.005, 0.010, 0.020, 0.030]  # 0.0%, 0.5%, 1.0%, 2.0%, 3.0%
TAKE_PROFIT_VALUES = [0.008, 0.016]  # 0.8%, 1.6%
STOP_LOSS_VALUES = [0.020, 0.040]  # 2.0%, 4.0%

TOP_N_PLOT = 4


@dataclass(frozen=True)
class SweepCase:
    band: float
    take_profit_pct: float
    stop_loss_pct: float

    @property
    def case_id(self) -> str:
        return (
            f"h{self.band * 100:.2f}_tp{self.take_profit_pct * 100:.2f}_sl{self.stop_loss_pct * 100:.2f}"
        )


@dataclass
class CaseResult:
    case: SweepCase
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


def summarize_detailed(
    bt,
    initial_capital: float,
) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, dict, pd.DataFrame]:
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


def _fmt(v, digits=4, suffix=""):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "N/A"
    return f"{v:.{digits}f}{suffix}"


def _worst_month_text(monthly: pd.Series) -> str:
    if monthly.empty:
        return "N/A"
    idx = monthly.idxmin()
    return f"{idx.strftime('%Y-%m')} ({monthly.min():.4f}%)"


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


def run_case(
    case: SweepCase,
    idx: int,
    total_cases: int,
    base_module,
    helper_04,
    helper_08,
    df_1m: pd.DataFrame,
    df_4h: pd.DataFrame,
) -> CaseResult:
    cls = helper_08.build_fixed5x_hyst_class(base_module, helper_04, case.band)
    bt = cls(
        symbol=base_module.SYMBOL,
        initial_capital=base_module.INITIAL_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=ENTRY_SCALE_OVERRIDE,
    )
    helper_04.configure_baseline_params(bt)
    bt.take_profit_pct = case.take_profit_pct
    bt.stop_loss_pct = case.stop_loss_pct

    print(
        f"[{idx}/{total_cases}] run {case.case_id} "
        f"(h={case.band * 100:.2f}%, tp={case.take_profit_pct * 100:.2f}%, sl={case.stop_loss_pct * 100:.2f}%)"
    )
    bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

    summary, eq, tr, monthly, dd_curve, episode, reason = summarize_detailed(bt, base_module.INITIAL_CAPITAL)
    summary["case_id"] = case.case_id
    summary["band"] = case.band
    summary["band_pct"] = case.band * 100.0
    summary["take_profit_pct"] = case.take_profit_pct
    summary["stop_loss_pct"] = case.stop_loss_pct
    summary["entry_scale"] = ENTRY_SCALE_OVERRIDE
    summary["worst_month"] = _worst_month_text(monthly)
    summary["max_dd_peak_time"] = episode["peak_time"]
    summary["max_dd_trough_time"] = episode["trough_time"]
    summary["max_dd_recovery_time"] = episode["recovery_time"]
    summary["max_dd_peak_to_trough_days"] = episode["peak_to_trough_days"]
    summary["max_dd_recovery_days"] = episode["recovery_days"]

    return CaseResult(
        case=case,
        summary=summary,
        equity=eq,
        trades=tr,
        monthly_returns=monthly,
        drawdown_curve=dd_curve,
        max_dd_episode=episode,
        reason_pnl=reason,
    )


def save_csv(results: list[CaseResult]):
    rows = [dict(r.summary) for r in results]
    df = pd.DataFrame(rows).sort_values("final_equity", ascending=False).reset_index(drop=True)
    df.insert(0, "rank_by_final_equity", np.arange(1, len(df) + 1))
    df.to_csv(CSV_FILE, index=False)
    return df


def save_plot(results: list[CaseResult]):
    sorted_results = sorted(results, key=lambda r: r.summary["final_equity"], reverse=True)
    top_results = sorted_results[:TOP_N_PLOT]
    if not top_results:
        return

    colors = ["#1f77b4", "#d62728", "#2ca02c", "#ff7f0e"]

    fig = plt.figure(figsize=(16, 11))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("11 ETHUSDT Sweep: Top 4 Equity Cases Only")
    ax_eq.set_ylabel("Equity (USDT)")

    top_labels = []
    for i, r in enumerate(top_results):
        label = (
            f"#{i + 1} {r.case.case_id} "
            f"(Eq={r.summary['final_equity']:.2f}, MDD={r.summary['max_drawdown_pct']:.2f}%)"
        )
        top_labels.append(label)
        eq = r.equity
        if eq.empty:
            continue
        ax_eq.plot(eq["timestamp"], eq["equity"], label=label, linewidth=1.2, color=colors[i % len(colors)])
    ax_eq.legend(loc="upper left", fontsize=9)
    ax_eq.grid(True, alpha=0.2)

    ax_final = fig.add_subplot(gs[1, 0])
    ax_final.set_title("Top 4 Final Equity")
    ax_final.bar(top_labels, [r.summary["final_equity"] for r in top_results], color=colors[: len(top_results)])
    ax_final.set_ylabel("USDT")
    ax_final.tick_params(axis="x", labelrotation=20)
    ax_final.grid(True, axis="y", alpha=0.2)

    ax_mdd = fig.add_subplot(gs[1, 1])
    ax_mdd.set_title("Top 4 Max Drawdown")
    ax_mdd.bar(top_labels, [r.summary["max_drawdown_pct"] for r in top_results], color=colors[: len(top_results)])
    ax_mdd.set_ylabel("MDD (%)")
    ax_mdd.tick_params(axis="x", labelrotation=20)
    ax_mdd.grid(True, axis="y", alpha=0.2)

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
    plt.close()


def save_md(results: list[CaseResult], metrics_df: pd.DataFrame):
    sorted_results = sorted(results, key=lambda r: r.summary["final_equity"], reverse=True)
    top4 = sorted_results[:TOP_N_PLOT]
    best_eq = sorted_results[0]
    best_calmar = max(sorted_results, key=lambda x: x.summary["calmar_ratio"] if not math.isnan(x.summary["calmar_ratio"]) else -1e9)
    best_mdd = min(sorted_results, key=lambda x: x.summary["max_drawdown_pct"])

    lines: list[str] = []
    lines.append("# 11 ETHUSDT Hysteresis + TP/SL Case Study")
    lines.append("")
    lines.append("## 1) Objective")
    lines.append("- Use ETH-specific sweep with wider hysteresis bands and TP/SL permutations.")
    lines.append("- Keep strategy core as: `04 long-only + trend short hedge 5x` with 4h confirmed trend.")
    lines.append("- Apply `entry_scale=0.40` for all cases.")
    lines.append("")
    lines.append("## 2) Sweep Grid")
    lines.append(f"- Symbol: `{TARGET_SYMBOL}`")
    lines.append("- Data period: `2022-01-01` to `2026-02-12`")
    lines.append("- Confirmation policy: closed 4h state only (`shift(1)`, no look-ahead)")
    lines.append(f"- Hysteresis bands (%): `{', '.join([f'{b * 100:.2f}' for b in HYSTERESIS_BANDS])}`")
    lines.append(f"- TP values (%): `{', '.join([f'{v * 100:.2f}' for v in TAKE_PROFIT_VALUES])}`")
    lines.append(f"- SL values (%): `{', '.join([f'{v * 100:.2f}' for v in STOP_LOSS_VALUES])}`")
    lines.append(f"- Total cases: `{len(results)}`")
    lines.append("")
    lines.append("## 3) Best Summary")
    lines.append(f"- Best Final Equity: `{best_eq.case.case_id}` (`{_fmt(best_eq.summary['final_equity'])} USDT`).")
    lines.append(f"- Best Calmar: `{best_calmar.case.case_id}` (`{_fmt(best_calmar.summary['calmar_ratio'])}`).")
    lines.append(f"- Lowest MDD: `{best_mdd.case.case_id}` (`{_fmt(best_mdd.summary['max_drawdown_pct'])}%`).")
    lines.append("")
    lines.append("## 4) Top 4 Cases (Plotted)")
    lines.append("")
    lines.append("| Rank | Case | Hysteresis % | TP % | SL % | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Win Rate % |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for i, r in enumerate(top4, start=1):
        s = r.summary
        lines.append(
            f"| {i} | `{r.case.case_id}` | {_fmt(s['band_pct'])} | {_fmt(s['take_profit_pct'] * 100)} | "
            f"{_fmt(s['stop_loss_pct'] * 100)} | {_fmt(s['final_equity'])} | {_fmt(s['total_return_pct'])} | "
            f"{_fmt(s['cagr_pct'])} | {_fmt(s['max_drawdown_pct'])} | {_fmt(s['calmar_ratio'])} | "
            f"{int(s['trades'])} | {_fmt(s['win_rate_pct'])} |"
        )

    lines.append("")
    lines.append("## 5) Full Ranking Table (All Cases)")
    lines.append("")
    lines.append("| Rank | Case | Hyst % | TP % | SL % | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Worst Month |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for i, r in enumerate(sorted_results, start=1):
        s = r.summary
        lines.append(
            f"| {i} | `{r.case.case_id}` | {_fmt(s['band_pct'])} | {_fmt(s['take_profit_pct'] * 100)} | {_fmt(s['stop_loss_pct'] * 100)} | "
            f"{_fmt(s['final_equity'])} | {_fmt(s['total_return_pct'])} | {_fmt(s['cagr_pct'])} | {_fmt(s['max_drawdown_pct'])} | "
            f"{_fmt(s['calmar_ratio'])} | {int(s['trades'])} | {int(s['long_trades'])}/{int(s['short_trades'])} | "
            f"{_fmt(s['win_rate_pct'])} | {_fmt(s['profit_factor'])} | `{s['worst_month']}` |"
        )

    lines.append("")
    lines.append("## 6) Detailed Per-Case Notes (All Cases)")
    lines.append("")
    for i, r in enumerate(sorted_results, start=1):
        s = r.summary
        e = r.max_dd_episode
        lines.append(f"### Rank {i} - `{r.case.case_id}`")
        lines.append(
            f"- Params: hysteresis `{_fmt(s['band_pct'])}%`, TP `{_fmt(s['take_profit_pct'] * 100)}%`, "
            f"SL `{_fmt(s['stop_loss_pct'] * 100)}%`, entry_scale `{_fmt(s['entry_scale'], digits=2)}`"
        )
        lines.append(f"- Period: `{s['period_start']}` ~ `{s['period_end']}`")
        lines.append(f"- Final Equity: `{_fmt(s['final_equity'])} USDT`")
        lines.append(f"- Total Return / CAGR: `{_fmt(s['total_return_pct'])}%` / `{_fmt(s['cagr_pct'])}%`")
        lines.append(f"- MDD: `{_fmt(s['max_drawdown_pct'])}%` (`{_fmt(s['max_drawdown_amount'])} USDT`), Calmar `{_fmt(s['calmar_ratio'])}`")
        lines.append(f"- Vol/Sharpe/Sortino: `{_fmt(s['annual_volatility_pct'])}%` / `{_fmt(s['sharpe_365'])}` / `{_fmt(s['sortino_365'])}`")
        lines.append(
            f"- Trades: `{int(s['trades'])}` (Long `{int(s['long_trades'])}`, Short `{int(s['short_trades'])}`), "
            f"Win `{_fmt(s['win_rate_pct'])}%`, PF `{_fmt(s['profit_factor'])}`"
        )
        lines.append(
            f"- Avg/Median trade PnL: `{_fmt(s['avg_pnl_per_trade'])}` / `{_fmt(s['median_pnl_per_trade'])}`, "
            f"Avg/Median hold: `{_fmt(s['avg_holding_hours'])}h` / `{_fmt(s['median_holding_hours'])}h`"
        )
        lines.append(
            f"- Worst Month: `{s['worst_month']}`, DD episode: peak `{e['peak_time']}` -> trough `{e['trough_time']}` -> "
            f"recovery `{e['recovery_time']}`, depth `{_fmt(e['depth_pct'])}%`"
        )
        lines.append("- PnL by side/reason:")
        lines.append(_reason_table_text(r.reason_pnl))
        lines.append("")

    lines.append("## 7) Output Files")
    lines.append(f"- script: `{SCRIPT_FILE}`")
    lines.append(f"- plot (top 4 only): `{PLOT_FILE}`")
    lines.append(f"- metrics (all cases): `{CSV_FILE}`")
    lines.append(f"- report (all cases detailed): `{MD_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_11", BASE_002_PATH)
    helper_04 = load_module("m04_11", BASE_04_PATH)
    helper_08 = load_module("m08_11", BASE_08_PATH)

    base_module.SYMBOL = TARGET_SYMBOL
    df_1m, df_4h = base_module.load_data()
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    cases = [
        SweepCase(band=b, take_profit_pct=tp, stop_loss_pct=sl)
        for b in HYSTERESIS_BANDS
        for tp in TAKE_PROFIT_VALUES
        for sl in STOP_LOSS_VALUES
    ]

    results: list[CaseResult] = []
    for idx, case in enumerate(cases, start=1):
        result = run_case(
            case=case,
            idx=idx,
            total_cases=len(cases),
            base_module=base_module,
            helper_04=helper_04,
            helper_08=helper_08,
            df_1m=df_1m,
            df_4h=df_4h,
        )
        results.append(result)

    metrics_df = save_csv(results)
    save_plot(results)
    save_md(results, metrics_df)

    show_cols = [
        "rank_by_final_equity",
        "case_id",
        "band_pct",
        "take_profit_pct",
        "stop_loss_pct",
        "final_equity",
        "total_return_pct",
        "cagr_pct",
        "max_drawdown_pct",
        "calmar_ratio",
        "trades",
        "win_rate_pct",
        "profit_factor",
    ]
    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(f"saved_report={MD_FILE}")
    print(metrics_df[show_cols].head(12).to_string(index=False))


if __name__ == "__main__":
    run()
