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

SCRIPT_FILE = Path("16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.py")
PLOT_FILE = Path("16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.png")
CSV_FILE = Path("16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.csv")
MD_FILE = Path("16_backtest_btcusdt_best_hyst_fixed5x_scale_monthly_dca.md")

TARGET_SYMBOL = "BTCUSDT"
DEFAULT_BEST_HYST_BAND = 0.005
ENTRY_SCALES = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80]

# Updated per user request: add 1000 USDT every month.
DCA_AMOUNT = 1000.0
DCA_FREQUENCY = "monthly"
DCA_START_NEXT_MONTH = True


@dataclass
class ScaleResult:
    scale: float
    summary: dict
    equity: pd.DataFrame
    trades: pd.DataFrame
    deposits: pd.DataFrame


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
    if df.empty or "band" not in df.columns or "final_equity" not in df.columns:
        return fallback
    row = df.sort_values("final_equity", ascending=False).iloc[0]
    return float(row["band"])


def build_monthly_dca_class(base_module, helper_04, helper_08, best_band: float, dca_amount: float):
    BaseCls = helper_08.build_fixed5x_hyst_class(base_module, helper_04, best_band)

    class Fixed5xHystMonthlyDCA(BaseCls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.dca_amount = float(dca_amount)
            self.dca_total = 0.0
            self.deposit_events: list[dict] = []
            self._last_dca_month = None

        def _reset_dca(self):
            self.dca_total = 0.0
            self.deposit_events = []
            self._last_dca_month = None

        def _apply_monthly_dca(self, timestamp):
            ts = pd.Timestamp(timestamp)
            cur_month = (ts.year, ts.month)
            if self._last_dca_month is None:
                self._last_dca_month = cur_month
                return
            if cur_month == self._last_dca_month:
                return

            # Add DCA amount at the first minute observed in each new month.
            self.capital += self.dca_amount
            self.dca_total += self.dca_amount
            self.deposit_events.append({"timestamp": ts, "amount": self.dca_amount})
            self._last_dca_month = cur_month

        def run(self, df_1m: pd.DataFrame, df_4h: pd.DataFrame, backtest_start_date=None):
            self.capital = self.initial_capital
            self.current_position = None
            self.position_quantity = 0.0
            self.entry_count = 0
            self.skip_count = 0
            self.stop_loss = [0, 0]
            self.last_order_time = -10**9
            self.recent_trade = [0.0, None]
            self.cooldown_time = self.base_cooldown
            self.trades = []
            self.equity_curve = []
            self.current_trend = None
            self.bankrupt = False
            self._reset_hedge()
            self._reset_dca()

            out_1m = df_1m.copy()
            out_4h = df_4h.copy()

            if backtest_start_date is not None:
                out_1m = out_1m[out_1m.index >= pd.Timestamp(backtest_start_date)].copy()
            if len(out_1m) == 0:
                return

            out_1m["rsi"] = self.calculate_rsi(out_1m["close"], period=self.rsi_period)
            out_1m["adx"] = self.calculate_adx(out_1m, period=14)

            out_4h["ema200"] = out_4h["close"].ewm(span=200, adjust=False).mean().shift(1)
            out_4h["ema_touch"] = (out_4h["high"] >= out_4h["ema200"]) & (out_4h["low"] <= out_4h["ema200"])
            out_4h["trend_4h_hyst"] = self._compute_hysteresis_state(out_4h, self.hysteresis)
            out_4h["trend_4h_confirmed"] = out_4h["trend_4h_hyst"].shift(1)

            out_1m["timestamp_4h"] = out_1m.index.floor("4h")
            out_1m["is_new_4h_bucket"] = out_1m["timestamp_4h"] != out_1m["timestamp_4h"].shift(1)
            out_1m = out_1m.merge(
                out_4h[["ema200", "ema_touch", "trend_4h_confirmed"]],
                left_on="timestamp_4h",
                right_index=True,
                how="left",
            )
            out_1m.drop("timestamp_4h", axis=1, inplace=True)
            out_1m["ema200"] = out_1m["ema200"].ffill()
            out_1m["ema_touch"] = out_1m["ema_touch"].ffill().fillna(False)
            out_1m["trend"] = np.where(out_1m["close"] > out_1m["ema200"], "bullish", "bearish")

            for i in range(200, len(out_1m)):
                row = out_1m.iloc[i]
                timestamp = row.name
                price = row["close"]
                rsi = row["rsi"]
                adx = row["adx"]
                trend = row["trend"]
                ema_touch = row["ema_touch"]
                ema_val = row["ema200"]
                confirmed_trend_4h = row["trend_4h_confirmed"]
                is_new_4h_bucket = bool(row["is_new_4h_bucket"])

                if pd.isna(rsi) or pd.isna(adx) or pd.isna(ema_val):
                    continue

                # Monthly DCA applied before trade decisions.
                if DCA_START_NEXT_MONTH:
                    self._apply_monthly_dca(timestamp)
                else:
                    ts = pd.Timestamp(timestamp)
                    cur_month = (ts.year, ts.month)
                    if self._last_dca_month != cur_month:
                        self.capital += self.dca_amount
                        self.dca_total += self.dca_amount
                        self.deposit_events.append({"timestamp": ts, "amount": self.dca_amount})
                        self._last_dca_month = cur_month

                self._check_trend_change(trend, price, timestamp, ema_val)

                current_time = i
                time_since_last = current_time - self.last_order_time
                self._check_stop_loss(price, timestamp)
                self._manage_trend_hedge(confirmed_trend_4h, price, timestamp, is_new_4h_bucket)

                if (not ema_touch) and time_since_last >= self.cooldown_time:
                    if rsi <= self.rsi_oversold and trend == "bullish":
                        self._process_long_entry(price, timestamp, adx, current_time)

                self._check_take_profit(price, timestamp)
                self._record_equity(price, timestamp, ema_val)

            if self.current_position:
                last_price = out_1m["close"].iloc[-1]
                last_timestamp = out_1m.index[-1]
                self._close_position(last_price, last_timestamp, "Final Close")

            if self.hedge_position:
                last_price = out_1m["close"].iloc[-1]
                last_timestamp = out_1m.index[-1]
                self._close_hedge_short(last_price, last_timestamp, "Final Hedge Close")
                self._record_equity(last_price, last_timestamp, float(out_1m["ema200"].iloc[-1]))

    return Fixed5xHystMonthlyDCA


def _fmt(v, digits: int = 4) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "N/A"
    return f"{v:.{digits}f}"


def _worst_month(series: pd.Series) -> str:
    if series.empty:
        return "N/A"
    idx = series.idxmin()
    return f"{idx.strftime('%Y-%m')} ({series.min():.4f}%)"


def _profit_factor(trades: pd.DataFrame) -> float:
    if trades.empty:
        return np.nan
    gross_profit = float(trades.loc[trades["pnl"] > 0, "pnl"].sum())
    gross_loss = float(trades.loc[trades["pnl"] < 0, "pnl"].sum())
    if gross_loss >= 0:
        return np.inf
    return gross_profit / abs(gross_loss)


def _build_contribution_series(eq: pd.DataFrame, initial_capital: float, deposits: pd.DataFrame) -> pd.Series:
    dep_map = {}
    if not deposits.empty:
        for _, row in deposits.iterrows():
            ts = pd.Timestamp(row["timestamp"])
            dep_map[ts] = dep_map.get(ts, 0.0) + float(row["amount"])

    total = float(initial_capital)
    values = []
    for ts in eq["timestamp"]:
        total += dep_map.get(pd.Timestamp(ts), 0.0)
        values.append(total)
    return pd.Series(values, index=eq.index, dtype=float)


def _calc_flow_adjusted_nav(eq: pd.DataFrame, deposits: pd.DataFrame) -> tuple[np.ndarray, pd.Series]:
    if eq.empty:
        return np.array([]), pd.Series(dtype=float)

    dep_map = {}
    if not deposits.empty:
        for _, row in deposits.iterrows():
            ts = pd.Timestamp(row["timestamp"])
            dep_map[ts] = dep_map.get(ts, 0.0) + float(row["amount"])

    returns = []
    nav = [1.0]
    for i in range(1, len(eq)):
        prev_equity = float(eq["equity"].iloc[i - 1])
        cur_equity = float(eq["equity"].iloc[i])
        ts = pd.Timestamp(eq["timestamp"].iloc[i])
        cf = dep_map.get(ts, 0.0)

        if prev_equity <= 0:
            r = -1.0
        else:
            r = (cur_equity - prev_equity - cf) / prev_equity
        returns.append(r)
        nav.append(nav[-1] * (1.0 + r))

    nav_series = pd.Series(nav, index=eq["timestamp"], dtype=float)
    return np.array(returns, dtype=float), nav_series


def _summarize_case(bt, initial_capital: float, scale: float) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eq = pd.DataFrame(bt.equity_curve)
    tr = pd.DataFrame(bt.trades)
    dep = pd.DataFrame(bt.deposit_events)

    if eq.empty:
        summary = {
            "entry_scale": scale,
            "final_equity": 0.0,
            "dca_count": 0,
            "dca_total": 0.0,
            "total_contribution": initial_capital,
            "net_profit_after_contribution": -initial_capital,
            "account_return_on_contribution_pct": -100.0,
            "strategy_twr_total_pct": np.nan,
            "strategy_twr_cagr_pct": np.nan,
            "account_max_drawdown_pct": np.nan,
            "strategy_nav_max_drawdown_pct": np.nan,
            "calmar_twr_nav": np.nan,
            "trades": 0,
            "long_trades": 0,
            "short_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": np.nan,
            "avg_holding_hours": np.nan,
            "worst_month_account": "N/A",
            "worst_month_strategy_nav": "N/A",
        }
        return summary, eq, tr, dep

    eq["timestamp"] = pd.to_datetime(eq["timestamp"])
    eq = eq.sort_values("timestamp").reset_index(drop=True)

    if not dep.empty:
        dep["timestamp"] = pd.to_datetime(dep["timestamp"])
        dep = dep.sort_values("timestamp").reset_index(drop=True)
    else:
        dep = pd.DataFrame(columns=["timestamp", "amount"])

    eq["contribution"] = _build_contribution_series(eq, initial_capital, dep)
    eq["excess_equity"] = eq["equity"] - eq["contribution"]

    adj_returns, nav = _calc_flow_adjusted_nav(eq, dep)
    eq["strategy_nav"] = nav.values

    final_equity = float(eq["equity"].iloc[-1])
    dca_count = int(len(dep))
    dca_total = float(dep["amount"].sum()) if not dep.empty else 0.0
    total_contribution = float(initial_capital + dca_total)
    net_profit = final_equity - total_contribution
    account_return_on_contrib = (final_equity / total_contribution - 1.0) * 100.0 if total_contribution > 0 else np.nan

    twr_total = float(np.prod(1.0 + adj_returns) - 1.0) if len(adj_returns) else np.nan
    years = max((eq["timestamp"].iloc[-1] - eq["timestamp"].iloc[0]).days / 365.25, 1e-9)
    twr_cagr = (pow(1.0 + twr_total, 1.0 / years) - 1.0) if not np.isnan(twr_total) and twr_total > -1.0 else np.nan

    account_dd = (eq["equity"] / eq["equity"].cummax()) - 1.0
    account_mdd = float(-account_dd.min() * 100.0)
    nav_dd = (eq["strategy_nav"] / eq["strategy_nav"].cummax()) - 1.0
    nav_mdd = float(-nav_dd.min() * 100.0)
    calmar_twr_nav = (twr_cagr * 100.0) / nav_mdd if nav_mdd > 0 and not np.isnan(twr_cagr) else np.nan

    monthly_account = eq.set_index("timestamp")["equity"].resample("ME").last().dropna().pct_change().dropna() * 100.0
    monthly_nav = eq.set_index("timestamp")["strategy_nav"].resample("ME").last().dropna().pct_change().dropna() * 100.0

    if not tr.empty:
        tr = tr.copy()
        tr["entry_time"] = pd.to_datetime(tr["entry_time"])
        tr["exit_time"] = pd.to_datetime(tr["exit_time"])
        avg_holding_hours = float((tr["exit_time"] - tr["entry_time"]).dt.total_seconds().mean() / 3600.0)
    else:
        avg_holding_hours = np.nan

    summary = {
        "entry_scale": scale,
        "final_equity": final_equity,
        "dca_count": dca_count,
        "dca_total": dca_total,
        "total_contribution": total_contribution,
        "net_profit_after_contribution": net_profit,
        "account_return_on_contribution_pct": account_return_on_contrib,
        "strategy_twr_total_pct": twr_total * 100.0 if not np.isnan(twr_total) else np.nan,
        "strategy_twr_cagr_pct": twr_cagr * 100.0 if not np.isnan(twr_cagr) else np.nan,
        "account_max_drawdown_pct": account_mdd,
        "strategy_nav_max_drawdown_pct": nav_mdd,
        "calmar_twr_nav": calmar_twr_nav,
        "trades": int(len(tr)),
        "long_trades": int((tr["side"] == "LONG").sum()) if not tr.empty else 0,
        "short_trades": int((tr["side"] == "SHORT").sum()) if not tr.empty else 0,
        "win_rate_pct": float((tr["pnl"] > 0).mean() * 100.0) if not tr.empty else 0.0,
        "profit_factor": _profit_factor(tr),
        "avg_holding_hours": avg_holding_hours,
        "worst_month_account": _worst_month(monthly_account),
        "worst_month_strategy_nav": _worst_month(monthly_nav),
    }
    return summary, eq, tr, dep


def save_plot(results: list[ScaleResult]):
    colors = plt.get_cmap("tab10")
    scales = [f"{r.scale:.2f}" for r in results]

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1.3])

    ax_eq = fig.add_subplot(gs[0, 0])
    ax_excess = fig.add_subplot(gs[0, 1])
    ax_final = fig.add_subplot(gs[1, 0])
    ax_twr = fig.add_subplot(gs[1, 1])

    ax_eq.set_title("Account Equity (Monthly +1000 DCA)")
    ax_eq.set_ylabel("USDT")
    ax_eq.grid(True, alpha=0.2)

    # Contribution line is common across scales by construction.
    contrib_ref = None

    ax_excess.set_title("Excess Equity = Equity - Contribution")
    ax_excess.set_ylabel("USDT")
    ax_excess.grid(True, alpha=0.2)

    for i, r in enumerate(results):
        if r.equity.empty:
            continue
        color = colors(i)
        label = f"scale={r.scale:.2f}"
        ax_eq.plot(r.equity["timestamp"], r.equity["equity"], label=label, color=color, linewidth=1.1)
        ax_excess.plot(r.equity["timestamp"], r.equity["excess_equity"], label=label, color=color, linewidth=1.1)
        if contrib_ref is None:
            contrib_ref = r.equity[["timestamp", "contribution"]].copy()

    if contrib_ref is not None:
        ax_eq.plot(
            contrib_ref["timestamp"],
            contrib_ref["contribution"],
            color="black",
            linewidth=1.0,
            linestyle="--",
            label="Contribution",
            alpha=0.9,
        )
    ax_eq.legend(loc="upper left", fontsize=8, ncol=2)
    ax_excess.legend(loc="upper left", fontsize=8, ncol=2)

    summary_df = pd.DataFrame([r.summary for r in results]).sort_values("entry_scale").reset_index(drop=True)
    ax_final.set_title("Final Equity / Net Profit by Scale")
    x = np.arange(len(summary_df))
    width = 0.38
    ax_final.bar(x - width / 2, summary_df["final_equity"], width=width, label="Final Equity")
    ax_final.bar(x + width / 2, summary_df["net_profit_after_contribution"], width=width, label="Net Profit over Contribution")
    ax_final.set_xticks(x)
    ax_final.set_xticklabels([f"{v:.2f}" for v in summary_df["entry_scale"]])
    ax_final.set_xlabel("Scale")
    ax_final.set_ylabel("USDT")
    ax_final.grid(True, axis="y", alpha=0.2)
    ax_final.legend(loc="upper left")

    ax_twr.set_title("Strategy TWR CAGR / NAV MDD")
    ax_twr.bar(x - width / 2, summary_df["strategy_twr_cagr_pct"], width=width, label="TWR CAGR %")
    ax_twr.bar(x + width / 2, summary_df["strategy_nav_max_drawdown_pct"], width=width, label="NAV MDD %")
    ax_twr.set_xticks(x)
    ax_twr.set_xticklabels([f"{v:.2f}" for v in summary_df["entry_scale"]])
    ax_twr.set_xlabel("Scale")
    ax_twr.set_ylabel("%")
    ax_twr.grid(True, axis="y", alpha=0.2)
    ax_twr.legend(loc="upper left")

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
    plt.close()


def save_csv(results: list[ScaleResult]) -> pd.DataFrame:
    rows = [dict(r.summary) for r in results]
    df = pd.DataFrame(rows).sort_values("entry_scale").reset_index(drop=True)
    df.to_csv(CSV_FILE, index=False)
    return df


def save_md(results: list[ScaleResult], metrics_df: pd.DataFrame, best_band: float):
    by_final = metrics_df.sort_values("final_equity", ascending=False).iloc[0]
    by_net = metrics_df.sort_values("net_profit_after_contribution", ascending=False).iloc[0]
    by_twr = metrics_df.sort_values("strategy_twr_cagr_pct", ascending=False).iloc[0]
    by_mdd = metrics_df.sort_values("strategy_nav_max_drawdown_pct", ascending=True).iloc[0]

    lines: list[str] = []
    lines.append("# 16 BTCUSDT - Scale Sweep with Monthly 1000 USDT DCA")
    lines.append("")
    lines.append("## 1) Objective")
    lines.append("- Evaluate `15` strategy family under external cash flow scenario.")
    lines.append("- Base strategy: `08_best_hysteresis_fixed5x` on BTC.")
    lines.append("- Sweep `scale` and add fixed DCA cash inflow monthly.")
    lines.append("")
    lines.append("## 2) DCA Assumption")
    lines.append("- Updated by request: this report uses `monthly DCA`.")
    lines.append(f"- DCA amount: `{DCA_AMOUNT:.0f} USDT` each month (`frequency={DCA_FREQUENCY}`).")
    lines.append(f"- First-month DCA skipped: `{DCA_START_NEXT_MONTH}` (deposit starts from next month).")
    lines.append("")
    lines.append("## 3) Test Setup")
    lines.append(f"- Symbol: `{TARGET_SYMBOL}`")
    lines.append("- Data period: `2022-01-01` to `2026-02-12`")
    lines.append(f"- Hysteresis fixed to 08-best: `{best_band * 100:.2f}%`")
    lines.append("- TP fixed: `1.20%`")
    lines.append("- SL fixed: `3.00%`")
    lines.append(f"- Scale sweep: `{', '.join([f'{s:.2f}' for s in ENTRY_SCALES])}`")
    lines.append("")
    lines.append("## 4) Summary Table")
    lines.append("")
    lines.append("| Scale | Final Equity | Total Contribution | Net Profit | Account Return on Contribution % | TWR Total % | TWR CAGR % | NAV MDD % | Calmar(TWR/NAV) | Trades | Win Rate % | PF | Worst Month(Account) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['entry_scale']:.2f}` | {_fmt(r['final_equity'])} | {_fmt(r['total_contribution'])} | "
            f"{_fmt(r['net_profit_after_contribution'])} | {_fmt(r['account_return_on_contribution_pct'])} | "
            f"{_fmt(r['strategy_twr_total_pct'])} | {_fmt(r['strategy_twr_cagr_pct'])} | "
            f"{_fmt(r['strategy_nav_max_drawdown_pct'])} | {_fmt(r['calmar_twr_nav'])} | {int(r['trades'])} | "
            f"{_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} | `{r['worst_month_account']}` |"
        )

    lines.append("")
    lines.append("## 5) Best by Objective")
    lines.append(f"- Highest Final Equity: `scale={by_final['entry_scale']:.2f}` (`{_fmt(by_final['final_equity'])} USDT`).")
    lines.append(f"- Highest Net Profit: `scale={by_net['entry_scale']:.2f}` (`{_fmt(by_net['net_profit_after_contribution'])} USDT`).")
    lines.append(f"- Highest Strategy TWR CAGR: `scale={by_twr['entry_scale']:.2f}` (`{_fmt(by_twr['strategy_twr_cagr_pct'])}%`).")
    lines.append(f"- Lowest Strategy NAV MDD: `scale={by_mdd['entry_scale']:.2f}` (`{_fmt(by_mdd['strategy_nav_max_drawdown_pct'])}%`).")
    lines.append("")
    lines.append("## 6) Interpretation")
    lines.append("- Since contribution schedule is identical across scales, scale comparison remains meaningful for net profit and risk.")
    lines.append("- Higher scale tends to increase final equity and net profit but also increases drawdown risk on strategy NAV.")
    lines.append("- `Account Return on Contribution` reflects investor-level outcome including cash inflows.")
    lines.append("- `TWR` and `NAV MDD` are flow-adjusted strategy metrics, useful for pure strategy quality.")
    lines.append("")
    lines.append("## 7) Output Files")
    lines.append(f"- script: `{SCRIPT_FILE}`")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{CSV_FILE}`")
    lines.append(f"- report: `{MD_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_16m", BASE_002_PATH)
    helper_04 = load_module("m04_16m", BASE_04_PATH)
    helper_08 = load_module("m08_16m", BASE_08_PATH)

    best_band = detect_best_hysteresis_band(BASE_08_CSV, DEFAULT_BEST_HYST_BAND)
    base_module.SYMBOL = TARGET_SYMBOL

    df_1m, df_4h = base_module.load_data()
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    DCACls = build_monthly_dca_class(base_module, helper_04, helper_08, best_band=best_band, dca_amount=DCA_AMOUNT)

    results: list[ScaleResult] = []
    for i, scale in enumerate(ENTRY_SCALES, start=1):
        print(f"[{i}/{len(ENTRY_SCALES)}] run scale={scale:.2f}")
        bt = DCACls(
            symbol=base_module.SYMBOL,
            initial_capital=base_module.INITIAL_CAPITAL,
            commission=base_module.COMMISSION,
            entry_scale=scale,
        )
        helper_04.configure_baseline_params(bt)
        bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

        summary, eq, tr, dep = _summarize_case(bt, base_module.INITIAL_CAPITAL, scale=scale)
        results.append(ScaleResult(scale=scale, summary=summary, equity=eq, trades=tr, deposits=dep))

    metrics_df = save_csv(results)
    save_plot(results)
    save_md(results, metrics_df, best_band)

    show_cols = [
        "entry_scale",
        "final_equity",
        "total_contribution",
        "net_profit_after_contribution",
        "account_return_on_contribution_pct",
        "strategy_twr_cagr_pct",
        "strategy_nav_max_drawdown_pct",
        "calmar_twr_nav",
    ]
    print(f"best_hysteresis_band={best_band * 100:.2f}%")
    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(f"saved_report={MD_FILE}")
    print(metrics_df[show_cols].to_string(index=False))


if __name__ == "__main__":
    run()
