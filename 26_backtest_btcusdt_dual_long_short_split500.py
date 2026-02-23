from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
BASE_22_PATH = Path("22_backtest_btcusdt_dd_scale_entryscale_sweep.py")

OUT_BASE = "26_backtest_btcusdt_dual_long_short_split500"
PLOT_FILE = Path(f"{OUT_BASE}.png")
CSV_FILE = Path(f"{OUT_BASE}.csv")
MD_FILE = Path(f"{OUT_BASE}.md")
EQUITY_CSV_FILE = Path(f"{OUT_BASE}_equity.csv")

TOTAL_CAPITAL = 1000.0
LEG_CAPITAL = 500.0
LONG_ENTRY_SCALE = 0.6
SHORT_ENTRY_SCALE = 0.15
HYSTERESIS_BAND = 0.005


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


def load_data_no_filter(base_module) -> tuple[pd.DataFrame, pd.DataFrame]:
    periods_1m = [("2022-01-01", "2024-12-31"), ("2025-01-01", base_module.BACKTEST_END)]
    periods_4h = [
        ("2021-07-01", "2021-12-31"),
        ("2022-01-01", "2024-12-31"),
        ("2025-01-01", base_module.BACKTEST_END),
    ]
    df_1m = base_module._load_cached_df(base_module.SYMBOL, "1m", periods_1m).sort_index()
    df_4h = base_module._load_cached_df(base_module.SYMBOL, "4h", periods_4h).sort_index()
    return df_1m, df_4h


def build_short_only_case_class(base_module, helper_module):
    _, BaseHedgeCls = helper_module.build_mode_classes(base_module)

    class FixedBase5xShortOnlyWithTrendLongHedge(BaseHedgeCls):
        hysteresis = float(HYSTERESIS_BAND)
        hedge_long_multiplier = 5.0

        @staticmethod
        def _compute_hysteresis_state(df_4h: pd.DataFrame, hysteresis: float) -> pd.Series:
            states: list[str | float] = []
            prev_state: str | None = None
            for _, row in df_4h.iterrows():
                ema = row["ema200"]
                close = row["close"]
                if pd.isna(ema) or pd.isna(close):
                    states.append(np.nan)
                    continue

                upper = ema * (1.0 + hysteresis)
                lower = ema * (1.0 - hysteresis)
                if close > upper:
                    state = "bullish"
                elif close < lower:
                    state = "bearish"
                else:
                    if prev_state is None:
                        state = "bullish" if close > ema else "bearish"
                    else:
                        state = prev_state
                states.append(state)
                prev_state = state
            return pd.Series(states, index=df_4h.index)

        def _process_short_entry(self, price, timestamp, adx, current_time):
            # BaseHedgeCls is derived from LongOnlyBacktest, so we must explicitly
            # restore the original short-entry logic for this short-only engine.
            return base_module.RSIAveragingBacktestStandalone._process_short_entry(self, price, timestamp, adx, current_time)

        def _open_position(self, side, price, timestamp, quantity):
            super()._open_position(side, price, timestamp, quantity)
            if side == "SHORT" and self.position_quantity:
                self.hedge_base_qty = float(self.position_quantity)

        def _open_hedge_long(self, price, timestamp):
            if self.hedge_position is not None:
                return
            if self.position_quantity:
                self.hedge_base_qty = float(self.position_quantity)
            base_qty = float(self.hedge_base_qty)
            if base_qty <= 0:
                return

            hedge_qty = base_qty * self.hedge_long_multiplier
            if hedge_qty <= 0:
                return

            open_commission = hedge_qty * price * self.commission
            self.capital -= open_commission
            self.hedge_position = {
                "side": "LONG",
                "avg_entry": float(price),
                "quantity": float(hedge_qty),
                "entry_time": timestamp,
                "total_commission": float(open_commission),
            }

        def _close_hedge_long(self, price, timestamp, reason):
            if self.hedge_position is None:
                return

            pos = self.hedge_position
            close_commission = pos["quantity"] * price * self.commission
            pnl = (price - pos["avg_entry"]) * pos["quantity"]
            pnl -= (pos["total_commission"] + close_commission)
            self.capital += pnl

            self.trades.append(
                {
                    "entry_time": pos["entry_time"],
                    "exit_time": timestamp,
                    "side": "LONG",
                    "avg_entry": pos["avg_entry"],
                    "exit_price": float(price),
                    "quantity": pos["quantity"],
                    "num_entries": 1,
                    "pnl": float(pnl),
                    "return_pct": float((pnl / self.initial_capital) * 100.0),
                    "reason": reason,
                }
            )
            self.hedge_position = None

        def _manage_trend_hedge(self, confirmed_trend_4h, price, timestamp, is_new_4h_bucket):
            if not is_new_4h_bucket:
                return
            if confirmed_trend_4h not in ("bullish", "bearish"):
                return

            if confirmed_trend_4h == "bullish" and self.hedge_position is None:
                self._open_hedge_long(price, timestamp)

            if confirmed_trend_4h == "bearish" and self.hedge_position is not None:
                self._close_hedge_long(price, timestamp, "Hedge Close Trend Down")

        def _record_equity(self, price, timestamp, ema=0):
            if self.bankrupt:
                self.equity_curve.append({"timestamp": timestamp, "equity": 0.0, "price": price, "ema200": ema})
                return

            equity = float(self.capital)
            if self.current_position:
                pos = self.current_position
                if pos["side"] == "LONG":
                    equity += (price - pos["avg_entry"]) * pos["quantity"]
                else:
                    equity += (pos["avg_entry"] - price) * pos["quantity"]

            if self.hedge_position:
                hedge = self.hedge_position
                equity += (price - hedge["avg_entry"]) * hedge["quantity"]

            if equity <= 0:
                self.equity_curve.append({"timestamp": timestamp, "equity": 0.0, "price": price, "ema200": ema})
                self.capital = 0.0
                self.current_position = None
                self.position_quantity = None
                self.entry_count = 0
                self.skip_count = 0
                self.stop_loss = [0, 0]
                self.hedge_position = None
                self.bankrupt = True
                return

            self.equity_curve.append(
                {
                    "timestamp": timestamp,
                    "equity": float(equity),
                    "price": float(price),
                    "ema200": float(ema),
                }
            )

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

            out_1m = df_1m.copy()
            out_4h = df_4h.copy()
            if backtest_start_date is not None:
                out_1m = out_1m[out_1m.index >= pd.Timestamp(backtest_start_date)].copy()
            if len(out_1m) == 0:
                return

            out_1m["rsi"] = self.calculate_rsi(out_1m["close"], period=self.rsi_period)
            out_1m["adx"] = self.calculate_adx(out_1m, period=14)

            out_4h["ema200"] = out_4h["close"].ewm(span=200, adjust=False).mean().shift(1)
            out_4h["ema_touch_raw"] = (out_4h["high"] >= out_4h["ema200"]) & (out_4h["low"] <= out_4h["ema200"])
            out_4h["ema_touch_confirmed"] = out_4h["ema_touch_raw"].shift(1).fillna(False)
            out_4h["trend_4h_hyst"] = self._compute_hysteresis_state(out_4h, self.hysteresis)
            out_4h["trend_4h_confirmed"] = out_4h["trend_4h_hyst"].shift(1)

            out_1m["timestamp_4h"] = out_1m.index.floor("4h")
            out_1m["is_new_4h_bucket"] = out_1m["timestamp_4h"] != out_1m["timestamp_4h"].shift(1)
            out_1m = out_1m.merge(
                out_4h[["ema200", "ema_touch_confirmed", "trend_4h_confirmed"]],
                left_on="timestamp_4h",
                right_index=True,
                how="left",
            )
            out_1m.drop("timestamp_4h", axis=1, inplace=True)
            out_1m["ema200"] = out_1m["ema200"].ffill()
            out_1m["ema_touch"] = out_1m["ema_touch_confirmed"].ffill().fillna(False)
            out_1m.drop("ema_touch_confirmed", axis=1, inplace=True)
            out_1m["trend"] = np.where(out_1m["close"] > out_1m["ema200"], "bullish", "bearish")

            for i in range(200, len(out_1m)):
                row = out_1m.iloc[i]
                timestamp = row.name
                price = float(row["close"])
                rsi = row["rsi"]
                adx = row["adx"]
                trend = row["trend"]
                ema_touch = bool(row["ema_touch"])
                ema_val = row["ema200"]
                confirmed_trend_4h = row["trend_4h_confirmed"]
                is_new_4h_bucket = bool(row["is_new_4h_bucket"])

                if pd.isna(rsi) or pd.isna(adx) or pd.isna(ema_val):
                    continue

                self._check_trend_change(trend, price, timestamp, float(ema_val))

                current_time = i
                time_since_last = current_time - self.last_order_time
                self._check_stop_loss(price, timestamp)
                self._manage_trend_hedge(confirmed_trend_4h, price, timestamp, is_new_4h_bucket)

                if (not ema_touch) and time_since_last >= self.cooldown_time:
                    if rsi >= self.rsi_overbought and trend == "bearish":
                        self._process_short_entry(price, timestamp, float(adx), current_time)

                self._check_take_profit(price, timestamp)
                self._record_equity(price, timestamp, float(ema_val))

            if self.current_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_timestamp = out_1m.index[-1]
                self._close_position(last_price, last_timestamp, "Final Close")

            if self.hedge_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_timestamp = out_1m.index[-1]
                self._close_hedge_long(last_price, last_timestamp, "Final Hedge Close")
                self._record_equity(last_price, last_timestamp, float(out_1m["ema200"].iloc[-1]))

    return FixedBase5xShortOnlyWithTrendLongHedge


def compute_curve_metrics(eq: pd.DataFrame, initial_capital: float) -> dict:
    if eq.empty:
        return {
            "period_start": pd.NaT,
            "period_end": pd.NaT,
            "final_equity": 0.0,
            "total_return_pct": -100.0,
            "cagr_pct": -100.0,
            "max_drawdown_pct": 100.0,
            "calmar_ratio": np.nan,
        }

    t = eq.copy()
    t["timestamp"] = pd.to_datetime(t["timestamp"])
    t = t.sort_values("timestamp")

    start = t["timestamp"].iloc[0]
    end = t["timestamp"].iloc[-1]
    final_equity = float(t["equity"].iloc[-1])
    total_return_pct = (final_equity - initial_capital) / initial_capital * 100.0

    years = max((end - start).days / 365.25, 1e-9)
    cagr_pct = (pow(max(final_equity, 1e-12) / initial_capital, 1.0 / years) - 1.0) * 100.0

    equity = t["equity"].astype(float)
    drawdown = (equity - equity.cummax()) / equity.cummax().replace(0, np.nan)
    max_drawdown_pct = float((-drawdown.min()) * 100.0) if len(drawdown) else 0.0
    calmar_ratio = float(cagr_pct / max_drawdown_pct) if max_drawdown_pct > 0 else np.nan

    return {
        "period_start": start,
        "period_end": end,
        "final_equity": final_equity,
        "total_return_pct": float(total_return_pct),
        "cagr_pct": float(cagr_pct),
        "max_drawdown_pct": float(max_drawdown_pct),
        "calmar_ratio": float(calmar_ratio) if pd.notna(calmar_ratio) else np.nan,
    }


def build_combined_curve(eq_long: pd.DataFrame, eq_short: pd.DataFrame) -> pd.DataFrame:
    l = eq_long.copy()
    s = eq_short.copy()
    l["timestamp"] = pd.to_datetime(l["timestamp"])
    s["timestamp"] = pd.to_datetime(s["timestamp"])

    l = l[["timestamp", "equity"]].rename(columns={"equity": "equity_long"}).sort_values("timestamp")
    s = s[["timestamp", "equity"]].rename(columns={"equity": "equity_short"}).sort_values("timestamp")

    merged = pd.merge(l, s, on="timestamp", how="outer").sort_values("timestamp")
    merged["equity_long"] = merged["equity_long"].ffill()
    merged["equity_short"] = merged["equity_short"].ffill()
    merged = merged.dropna(subset=["equity_long", "equity_short"]).copy()
    merged["equity_combined"] = merged["equity_long"] + merged["equity_short"]
    return merged


def build_yearly_returns(eq: pd.DataFrame, equity_col: str) -> pd.DataFrame:
    t = eq.copy()
    t["timestamp"] = pd.to_datetime(t["timestamp"])
    t = t.sort_values("timestamp")
    t["year"] = t["timestamp"].dt.year.astype(int)
    out = (
        t.groupby("year", dropna=False)[equity_col]
        .agg(equity_start="first", equity_end="last")
        .reset_index()
    )
    out["return_pct"] = np.where(
        out["equity_start"] > 0,
        (out["equity_end"] / out["equity_start"] - 1.0) * 100.0,
        np.nan,
    )
    return out[["year", "equity_start", "equity_end", "return_pct"]].reset_index(drop=True)


def detect_bankruptcy_timestamp(eq: pd.DataFrame, equity_col: str) -> pd.Timestamp | pd.NaT:
    if eq.empty:
        return pd.NaT
    t = eq.copy()
    t["timestamp"] = pd.to_datetime(t["timestamp"])
    t = t.sort_values("timestamp")
    hit = t[t[equity_col].astype(float) <= 0.0]
    if hit.empty:
        return pd.NaT
    return pd.to_datetime(hit.iloc[0]["timestamp"])


def summarize_trade_book(trades_df: pd.DataFrame) -> dict:
    if trades_df.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "net_pnl": 0.0,
            "avg_pnl": np.nan,
            "median_pnl": np.nan,
            "avg_holding_hours": np.nan,
        }

    t = trades_df.copy()
    t["entry_time"] = pd.to_datetime(t["entry_time"])
    t["exit_time"] = pd.to_datetime(t["exit_time"])
    t["holding_hours"] = (t["exit_time"] - t["entry_time"]).dt.total_seconds() / 3600.0
    wins = int((t["pnl"] > 0).sum())
    losses = int((t["pnl"] <= 0).sum())
    gross_profit = float(t.loc[t["pnl"] > 0, "pnl"].sum())
    gross_loss = float(t.loc[t["pnl"] < 0, "pnl"].sum())
    return {
        "trades": int(len(t)),
        "wins": wins,
        "losses": losses,
        "win_rate_pct": float((wins / len(t)) * 100.0),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_pnl": float(t["pnl"].sum()),
        "avg_pnl": float(t["pnl"].mean()),
        "median_pnl": float(t["pnl"].median()),
        "avg_holding_hours": float(t["holding_hours"].mean()),
    }


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


def extract_dd_episodes(eq: pd.DataFrame, equity_col: str, threshold_pct: float = 20.0) -> pd.DataFrame:
    if eq.empty:
        return pd.DataFrame(columns=["start", "end", "bars", "duration_days", "max_dd_pct", "avg_dd_pct"])
    t = eq.copy()
    t["timestamp"] = pd.to_datetime(t["timestamp"])
    t = t.sort_values("timestamp").set_index("timestamp")
    e = t[equity_col].astype(float)
    dd = ((e.cummax() - e) / e.cummax().replace(0, np.nan) * 100.0).fillna(0.0)
    flag = dd >= threshold_pct
    grp = (flag != flag.shift(1)).cumsum()

    rows: list[dict] = []
    for _, seg in flag.groupby(grp):
        if not bool(seg.iloc[0]):
            continue
        s = seg.index[0]
        e_ts = seg.index[-1]
        dd_seg = dd.loc[s:e_ts]
        dur_days = float((e_ts - s).total_seconds() / 86400.0)
        rows.append(
            {
                "start": s,
                "end": e_ts,
                "bars": int(len(seg)),
                "duration_days": dur_days,
                "max_dd_pct": float(dd_seg.max()),
                "avg_dd_pct": float(dd_seg.mean()),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["max_dd_pct", "duration_days"], ascending=[False, False]).reset_index(drop=True)


def save_plot(eq_combined: pd.DataFrame, eq_long: pd.DataFrame, eq_short: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 11), sharex=True, gridspec_kw={"height_ratios": [1.35, 1.0, 1.0]})
    ax0, ax1, ax2 = axes

    ax0.plot(eq_combined["timestamp"], eq_combined["equity_combined"], color="#111111", linewidth=1.2, label="Combined Equity (1000)")
    ax0.axhline(TOTAL_CAPITAL, color="#666666", linestyle="--", linewidth=0.9, label="Start 1000")
    ax0.set_title("26 Dual Engine Split: Combined / Long-only / Short-only")
    ax0.set_ylabel("Equity (USDT)")
    ax0.grid(True, alpha=0.2)
    ax0.legend(loc="upper left")

    ax1.plot(eq_long["timestamp"], eq_long["equity"], color="#1f77b4", linewidth=1.1, label="Long-only Equity (500)")
    ax1.axhline(LEG_CAPITAL, color="#1f77b4", linestyle="--", linewidth=0.8, alpha=0.7, label="Start 500")
    ax1.set_ylabel("Equity (USDT)")
    ax1.grid(True, alpha=0.2)
    ax1.legend(loc="upper left")

    ax2.plot(eq_short["timestamp"], eq_short["equity"], color="#d62728", linewidth=1.1, label="Short-only Equity (500)")
    ax2.axhline(LEG_CAPITAL, color="#d62728", linestyle="--", linewidth=0.8, alpha=0.7, label="Start 500")
    ax2.set_ylabel("Equity (USDT)")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.2)
    ax2.legend(loc="upper left")

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=180)
    plt.close(fig)


def save_report(
    metrics_df: pd.DataFrame,
    contribution_df: pd.DataFrame,
    yearly_df: pd.DataFrame,
    corr_daily_returns: float,
    long_book: dict,
    short_book: dict,
    reason_long_df: pd.DataFrame,
    reason_short_df: pd.DataFrame,
    dd_combined_df: pd.DataFrame,
    dd_long_df: pd.DataFrame,
    dd_short_df: pd.DataFrame,
    bankrupt_long_ts: pd.Timestamp | pd.NaT,
    bankrupt_short_ts: pd.Timestamp | pd.NaT,
):
    lines: list[str] = []
    lines.append("# 26 Backtest: Split Capital Dual Engine (Long-only + Short-only)")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Total initial capital: `{_fmt(TOTAL_CAPITAL)}`")
    lines.append(f"- Long-only leg: `{_fmt(LEG_CAPITAL)}`")
    lines.append(f"- Short-only leg: `{_fmt(LEG_CAPITAL)}`")
    lines.append(f"- Long entry scale: `{_fmt(LONG_ENTRY_SCALE, 2)}`")
    lines.append(f"- Short entry scale: `{_fmt(SHORT_ENTRY_SCALE, 2)}`")
    lines.append(f"- 4h trend hysteresis: `{_fmt(HYSTERESIS_BAND * 100.0, 2)}%`")
    lines.append("- Data: raw cached data (no extra filtering), no-lookahead confirmed 4h state")
    lines.append("- Long leg: long-only entries + trend-based short hedge")
    lines.append("- Short leg: short-only entries + trend-based long hedge (mirror)")
    lines.append(f"- Long leg bankruptcy timestamp: `{bankrupt_long_ts if pd.notna(bankrupt_long_ts) else 'None'}`")
    lines.append(f"- Short leg bankruptcy timestamp: `{bankrupt_short_ts if pd.notna(bankrupt_short_ts) else 'None'}`")
    lines.append("")
    lines.append("## Portfolio Metrics")
    lines.append("| Portfolio | Initial | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['portfolio']}` | {_fmt(r['initial_capital'])} | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | "
            f"{_fmt(r['cagr_pct'])} | {_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} |"
        )
    lines.append("")
    lines.append("## Contribution Breakdown")
    lines.append("| Leg | Initial | Final | Net PnL | Share of Total Net PnL % |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, r in contribution_df.iterrows():
        lines.append(
            f"| `{r['leg']}` | {_fmt(r['initial'])} | {_fmt(r['final'])} | {_fmt(r['net_pnl'])} | {_fmt(r['pnl_share_pct'])} |"
        )
    lines.append(f"- Daily return correlation (long vs short): `{_fmt(corr_daily_returns)}`")
    lines.append("")
    lines.append("## Yearly Returns")
    lines.append("| Portfolio | Year | Start Equity | End Equity | Return % |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, r in yearly_df.sort_values(["portfolio", "year"]).iterrows():
        lines.append(
            f"| `{r['portfolio']}` | {int(r['year'])} | {_fmt(r['equity_start'])} | {_fmt(r['equity_end'])} | {_fmt(r['return_pct'])} |"
        )
    lines.append("")
    lines.append("## Trade Book Summary")
    lines.append("| Leg | Trades | Wins | Losses | Win Rate % | Gross Profit | Gross Loss | Net PnL | Avg PnL | Median PnL | Avg Holding Hours |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| `long_only_500` | {int(long_book['trades'])} | {int(long_book['wins'])} | {int(long_book['losses'])} | {_fmt(long_book['win_rate_pct'])} | "
        f"{_fmt(long_book['gross_profit'])} | {_fmt(long_book['gross_loss'])} | {_fmt(long_book['net_pnl'])} | "
        f"{_fmt(long_book['avg_pnl'])} | {_fmt(long_book['median_pnl'])} | {_fmt(long_book['avg_holding_hours'])} |"
    )
    lines.append(
        f"| `short_only_500` | {int(short_book['trades'])} | {int(short_book['wins'])} | {int(short_book['losses'])} | {_fmt(short_book['win_rate_pct'])} | "
        f"{_fmt(short_book['gross_profit'])} | {_fmt(short_book['gross_loss'])} | {_fmt(short_book['net_pnl'])} | "
        f"{_fmt(short_book['avg_pnl'])} | {_fmt(short_book['median_pnl'])} | {_fmt(short_book['avg_holding_hours'])} |"
    )
    lines.append("")
    lines.append("## PnL Consistency Check")
    lines.append("| Leg | Equity Net PnL (Final-Initial) | Sum of Trade PnL | Gap |")
    lines.append("|---|---:|---:|---:|")
    eq_long = contribution_df.loc[contribution_df["leg"] == "long_only_500", "net_pnl"]
    eq_short = contribution_df.loc[contribution_df["leg"] == "short_only_500", "net_pnl"]
    eq_long_val = float(eq_long.iloc[0]) if not eq_long.empty else np.nan
    eq_short_val = float(eq_short.iloc[0]) if not eq_short.empty else np.nan
    long_gap = eq_long_val - float(long_book["net_pnl"]) if pd.notna(eq_long_val) else np.nan
    short_gap = eq_short_val - float(short_book["net_pnl"]) if pd.notna(eq_short_val) else np.nan
    lines.append(f"| `long_only_500` | {_fmt(eq_long_val)} | {_fmt(long_book['net_pnl'])} | {_fmt(long_gap)} |")
    lines.append(f"| `short_only_500` | {_fmt(eq_short_val)} | {_fmt(short_book['net_pnl'])} | {_fmt(short_gap)} |")
    lines.append("- Gap can be non-zero when bankruptcy/forced reset happens while a position is open.")
    lines.append("")
    lines.append("## Reason Breakdown (Long Leg)")
    lines.append("| Reason | Trades | Win Rate % | Net PnL | Avg PnL |")
    lines.append("|---|---:|---:|---:|---:|")
    if reason_long_df.empty:
        lines.append("| `N/A` | 0 | N/A | N/A | N/A |")
    else:
        for _, r in reason_long_df.iterrows():
            lines.append(
                f"| `{r['reason']}` | {int(r['trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['net_pnl'])} | {_fmt(r['avg_pnl'])} |"
            )
    lines.append("")
    lines.append("## Reason Breakdown (Short Leg)")
    lines.append("| Reason | Trades | Win Rate % | Net PnL | Avg PnL |")
    lines.append("|---|---:|---:|---:|---:|")
    if reason_short_df.empty:
        lines.append("| `N/A` | 0 | N/A | N/A | N/A |")
    else:
        for _, r in reason_short_df.iterrows():
            lines.append(
                f"| `{r['reason']}` | {int(r['trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['net_pnl'])} | {_fmt(r['avg_pnl'])} |"
            )
    lines.append("")
    lines.append("## DD>=20 Episodes")
    lines.append("### Combined")
    lines.append("| Start | End | Bars | Duration Days | Max DD % | Avg DD % |")
    lines.append("|---|---|---:|---:|---:|---:|")
    if dd_combined_df.empty:
        lines.append("| N/A | N/A | 0 | N/A | N/A | N/A |")
    else:
        for _, r in dd_combined_df.head(10).iterrows():
            lines.append(
                f"| {pd.to_datetime(r['start'])} | {pd.to_datetime(r['end'])} | {int(r['bars'])} | {_fmt(r['duration_days'])} | {_fmt(r['max_dd_pct'])} | {_fmt(r['avg_dd_pct'])} |"
            )
    lines.append("")
    lines.append("### Long-only")
    lines.append("| Start | End | Bars | Duration Days | Max DD % | Avg DD % |")
    lines.append("|---|---|---:|---:|---:|---:|")
    if dd_long_df.empty:
        lines.append("| N/A | N/A | 0 | N/A | N/A | N/A |")
    else:
        for _, r in dd_long_df.head(10).iterrows():
            lines.append(
                f"| {pd.to_datetime(r['start'])} | {pd.to_datetime(r['end'])} | {int(r['bars'])} | {_fmt(r['duration_days'])} | {_fmt(r['max_dd_pct'])} | {_fmt(r['avg_dd_pct'])} |"
            )
    lines.append("")
    lines.append("### Short-only")
    lines.append("| Start | End | Bars | Duration Days | Max DD % | Avg DD % |")
    lines.append("|---|---|---:|---:|---:|---:|")
    if dd_short_df.empty:
        lines.append("| N/A | N/A | 0 | N/A | N/A | N/A |")
    else:
        for _, r in dd_short_df.head(10).iterrows():
            lines.append(
                f"| {pd.to_datetime(r['start'])} | {pd.to_datetime(r['end'])} | {int(r['bars'])} | {_fmt(r['duration_days'])} | {_fmt(r['max_dd_pct'])} | {_fmt(r['avg_dd_pct'])} |"
            )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{PLOT_FILE}`")
    lines.append(f"- Metrics: `{CSV_FILE}`")
    lines.append(f"- Equity time-series: `{EQUITY_CSV_FILE}`")
    lines.append(f"- Report: `{MD_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_26", BASE_002_PATH)
    helper_module = load_module("m04_26", BASE_04_PATH)
    m22 = load_module("m22_26", BASE_22_PATH)

    df_1m, df_4h = load_data_no_filter(base_module)
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    long_cls = m22.build_case_class(base_module, helper_module, dynamic_dd_scale=False)
    short_cls = build_short_only_case_class(base_module, helper_module)

    bt_long = long_cls(
        symbol=base_module.SYMBOL,
        initial_capital=LEG_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=LONG_ENTRY_SCALE,
    )
    bt_short = short_cls(
        symbol=base_module.SYMBOL,
        initial_capital=LEG_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=SHORT_ENTRY_SCALE,
    )

    helper_module.configure_baseline_params(bt_long)
    helper_module.configure_baseline_params(bt_short)

    bt_long.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)
    bt_short.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

    eq_long = pd.DataFrame(bt_long.equity_curve)
    eq_short = pd.DataFrame(bt_short.equity_curve)
    if eq_long.empty or eq_short.empty:
        raise RuntimeError("Empty equity curve in one of the split legs.")

    eq_long["timestamp"] = pd.to_datetime(eq_long["timestamp"])
    eq_short["timestamp"] = pd.to_datetime(eq_short["timestamp"])
    eq_combined = build_combined_curve(eq_long[["timestamp", "equity"]], eq_short[["timestamp", "equity"]])
    eq_combined_out = eq_combined[["timestamp", "equity_combined", "equity_long", "equity_short"]].copy()
    eq_combined_out.to_csv(EQUITY_CSV_FILE, index=False)

    trades_long = pd.DataFrame(bt_long.trades)
    trades_short = pd.DataFrame(bt_short.trades)

    long_metrics = helper_module.calculate_metrics(bt_long, LEG_CAPITAL)
    short_metrics = helper_module.calculate_metrics(bt_short, LEG_CAPITAL)
    combined_metrics = compute_curve_metrics(
        eq_combined[["timestamp", "equity_combined"]].rename(columns={"equity_combined": "equity"}),
        TOTAL_CAPITAL,
    )

    combined_row = {
        "portfolio": "combined_1000",
        "initial_capital": float(TOTAL_CAPITAL),
        **combined_metrics,
        "trades": int(long_metrics.get("trades", 0) + short_metrics.get("trades", 0)),
        "long_trades": int(long_metrics.get("long_trades", 0) + short_metrics.get("long_trades", 0)),
        "short_trades": int(long_metrics.get("short_trades", 0) + short_metrics.get("short_trades", 0)),
        "win_rate_pct": np.nan,
        "profit_factor": np.nan,
    }
    long_row = {
        "portfolio": "long_only_500",
        "initial_capital": float(LEG_CAPITAL),
        **{k: long_metrics.get(k, np.nan) for k in ["period_start", "period_end", "final_equity", "total_return_pct", "cagr_pct", "max_drawdown_pct", "calmar_ratio", "trades", "long_trades", "short_trades", "win_rate_pct", "profit_factor"]},
    }
    short_row = {
        "portfolio": "short_only_500",
        "initial_capital": float(LEG_CAPITAL),
        **{k: short_metrics.get(k, np.nan) for k in ["period_start", "period_end", "final_equity", "total_return_pct", "cagr_pct", "max_drawdown_pct", "calmar_ratio", "trades", "long_trades", "short_trades", "win_rate_pct", "profit_factor"]},
    }
    metrics_df = pd.DataFrame([combined_row, long_row, short_row])

    total_net_pnl = float((combined_row["final_equity"] - TOTAL_CAPITAL))
    long_net_pnl = float(long_row["final_equity"] - LEG_CAPITAL)
    short_net_pnl = float(short_row["final_equity"] - LEG_CAPITAL)
    contribution_df = pd.DataFrame(
        [
            {
                "leg": "long_only_500",
                "initial": float(LEG_CAPITAL),
                "final": float(long_row["final_equity"]),
                "net_pnl": long_net_pnl,
                "pnl_share_pct": float(long_net_pnl / total_net_pnl * 100.0) if total_net_pnl != 0 else np.nan,
            },
            {
                "leg": "short_only_500",
                "initial": float(LEG_CAPITAL),
                "final": float(short_row["final_equity"]),
                "net_pnl": short_net_pnl,
                "pnl_share_pct": float(short_net_pnl / total_net_pnl * 100.0) if total_net_pnl != 0 else np.nan,
            },
        ]
    )

    yearly_frames: list[pd.DataFrame] = []
    yl = build_yearly_returns(eq_long[["timestamp", "equity"]], "equity")
    yl["portfolio"] = "long_only_500"
    yearly_frames.append(yl)
    ys = build_yearly_returns(eq_short[["timestamp", "equity"]], "equity")
    ys["portfolio"] = "short_only_500"
    yearly_frames.append(ys)
    yc = build_yearly_returns(eq_combined[["timestamp", "equity_combined"]].rename(columns={"equity_combined": "equity"}), "equity")
    yc["portfolio"] = "combined_1000"
    yearly_frames.append(yc)
    yearly_df = pd.concat(yearly_frames, ignore_index=True)

    dlong = eq_long[["timestamp", "equity"]].copy().set_index("timestamp").resample("1D").last().pct_change()
    dshort = eq_short[["timestamp", "equity"]].copy().set_index("timestamp").resample("1D").last().pct_change()
    d = dlong.rename(columns={"equity": "ret_long"}).join(dshort.rename(columns={"equity": "ret_short"}), how="inner").dropna()
    corr_daily_returns = float(d["ret_long"].corr(d["ret_short"])) if not d.empty else np.nan

    long_book = summarize_trade_book(trades_long)
    short_book = summarize_trade_book(trades_short)
    reason_long_df = summarize_trade_reasons(trades_long)
    reason_short_df = summarize_trade_reasons(trades_short)

    dd_combined_df = extract_dd_episodes(
        eq_combined[["timestamp", "equity_combined"]].rename(columns={"equity_combined": "equity"}),
        "equity",
        threshold_pct=20.0,
    )
    dd_long_df = extract_dd_episodes(eq_long[["timestamp", "equity"]], "equity", threshold_pct=20.0)
    dd_short_df = extract_dd_episodes(eq_short[["timestamp", "equity"]], "equity", threshold_pct=20.0)
    bankrupt_long_ts = detect_bankruptcy_timestamp(eq_long[["timestamp", "equity"]], "equity")
    bankrupt_short_ts = detect_bankruptcy_timestamp(eq_short[["timestamp", "equity"]], "equity")

    metrics_df.to_csv(CSV_FILE, index=False)
    save_plot(eq_combined, eq_long[["timestamp", "equity"]], eq_short[["timestamp", "equity"]])
    save_report(
        metrics_df=metrics_df,
        contribution_df=contribution_df,
        yearly_df=yearly_df,
        corr_daily_returns=corr_daily_returns,
        long_book=long_book,
        short_book=short_book,
        reason_long_df=reason_long_df,
        reason_short_df=reason_short_df,
        dd_combined_df=dd_combined_df,
        dd_long_df=dd_long_df,
        dd_short_df=dd_short_df,
        bankrupt_long_ts=bankrupt_long_ts,
        bankrupt_short_ts=bankrupt_short_ts,
    )

    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(f"saved_equity={EQUITY_CSV_FILE}")
    print(f"saved_report={MD_FILE}")
    print(metrics_df[["portfolio", "initial_capital", "final_equity", "max_drawdown_pct", "calmar_ratio"]].to_string(index=False))


if __name__ == "__main__":
    run()
