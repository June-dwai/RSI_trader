from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")

PLOT_FILE = Path("24_backtest_btcusdt_regime_scale_entryscale_sweep.png")
CSV_FILE = Path("24_backtest_btcusdt_regime_scale_entryscale_sweep.csv")
MD_FILE = Path("24_backtest_btcusdt_regime_scale_entryscale_sweep.md")

HYSTERESIS_BAND = 0.005
ENTRY_SCALES = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


@dataclass(frozen=True)
class SweepCase:
    entry_scale: float
    dynamic_regime_scale: bool

    @property
    def mode(self) -> str:
        prefix = "regime_scaled" if self.dynamic_regime_scale else "baseline"
        return f"{prefix}_es{self.entry_scale:.1f}"


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


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{v:.{digits}f}"


def build_case_class(base_module, helper_module, dynamic_regime_scale: bool):
    _, BaseHedgeCls = helper_module.build_mode_classes(base_module)

    class FixedBase5xWithRegimeScale(BaseHedgeCls):
        hysteresis = float(HYSTERESIS_BAND)
        use_dynamic_regime_scale = bool(dynamic_regime_scale)

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

        @staticmethod
        def _compute_run_length(series: pd.Series) -> pd.Series:
            valid = series.isin(["bullish", "bearish"])
            grp = (series != series.shift(1)).cumsum()
            run_len = series.groupby(grp).cumcount() + 1
            run_len = run_len.astype(float)
            run_len.loc[~valid] = np.nan
            return run_len

        @staticmethod
        def _compute_flip(series: pd.Series) -> pd.Series:
            prev = series.shift(1)
            flip = (series != prev) & series.isin(["bullish", "bearish"]) & prev.isin(["bullish", "bearish"])
            return flip.astype(float)

        @staticmethod
        def _regime_risk_score(run_len_4h: float, flip_count_30_4h: float, near_ema_ratio_30_4h: float) -> int:
            if pd.isna(run_len_4h) or pd.isna(flip_count_30_4h) or pd.isna(near_ema_ratio_30_4h):
                return 0

            score = 0
            if run_len_4h <= 8:
                score += 1
            if run_len_4h <= 3:
                score += 1
            if flip_count_30_4h >= 2:
                score += 1
            if flip_count_30_4h >= 4:
                score += 1
            if near_ema_ratio_30_4h >= 20:
                score += 1
            if near_ema_ratio_30_4h >= 40:
                score += 1
            return score

        def _get_position_scale(self, run_len_4h: float, flip_count_30_4h: float, near_ema_ratio_30_4h: float) -> tuple[float, int]:
            if not self.use_dynamic_regime_scale:
                return 1.0, 0
            score = self._regime_risk_score(run_len_4h, flip_count_30_4h, near_ema_ratio_30_4h)
            if score >= 4:
                return 0.25, score
            if score >= 2:
                return 0.5, score
            return 1.0, score

        def _process_long_entry_with_scale(self, price, timestamp, adx, current_time, position_scale: float):
            if not self.current_position:
                if self.capital <= 0:
                    return
                qty = (self.capital / price) * float(position_scale)
                if qty <= 0:
                    return
                self._open_position("LONG", price, timestamp, qty)
                self.last_order_time = current_time
                self.recent_trade = [price, "LONG"]
                self._update_cooldown("LONG")

            elif self.current_position["side"] == "LONG":
                if price <= self.recent_trade[0] * 0.995:
                    mult = self._get_adx_multiplier(adx)
                    if mult > 0:
                        qty = self.position_quantity * mult
                        self._add_to_position(price, timestamp, qty, adx)
                        self.last_order_time = current_time
                        self.recent_trade = [price, "LONG"]
                        self._update_cooldown("LONG")

            elif self.current_position["side"] == "SHORT":
                close_qty = self.current_position["quantity"] * 0.8
                self._partial_close(price, timestamp, close_qty, "Reverse")
                if self.capital <= 0:
                    return
                qty = self.capital / price
                self._open_position("LONG", price, timestamp, qty)
                self.last_order_time = current_time
                self.recent_trade = [price, "LONG"]
                self._update_cooldown("LONG")

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

            self.scale_entry_log: list[dict] = []

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

            out_4h["run_len_4h"] = self._compute_run_length(out_4h["trend_4h_confirmed"])
            out_4h["flip_4h"] = self._compute_flip(out_4h["trend_4h_confirmed"])
            out_4h["flip_count_30_4h"] = out_4h["flip_4h"].rolling(30, min_periods=1).sum()

            out_4h["abs_gap_pct_4h"] = ((out_4h["close"] - out_4h["ema200"]).abs() / out_4h["ema200"] * 100.0).replace(
                [np.inf, -np.inf], np.nan
            )
            out_4h["abs_gap_pct_confirmed"] = out_4h["abs_gap_pct_4h"].shift(1)
            out_4h["near_ema_0p5_4h"] = (out_4h["abs_gap_pct_confirmed"] <= 0.5).astype(float)
            out_4h["near_ema_ratio_30_4h"] = out_4h["near_ema_0p5_4h"].rolling(30, min_periods=1).mean() * 100.0

            out_1m["timestamp_4h"] = out_1m.index.floor("4h")
            out_1m["is_new_4h_bucket"] = out_1m["timestamp_4h"] != out_1m["timestamp_4h"].shift(1)
            out_1m = out_1m.merge(
                out_4h[
                    [
                        "ema200",
                        "ema_touch_confirmed",
                        "trend_4h_confirmed",
                        "run_len_4h",
                        "flip_count_30_4h",
                        "near_ema_ratio_30_4h",
                    ]
                ],
                left_on="timestamp_4h",
                right_index=True,
                how="left",
            )
            out_1m.drop("timestamp_4h", axis=1, inplace=True)
            out_1m["ema200"] = out_1m["ema200"].ffill()
            out_1m["ema_touch"] = out_1m["ema_touch_confirmed"].ffill().fillna(False)
            out_1m.drop("ema_touch_confirmed", axis=1, inplace=True)
            out_1m["run_len_4h"] = out_1m["run_len_4h"].ffill()
            out_1m["flip_count_30_4h"] = out_1m["flip_count_30_4h"].ffill()
            out_1m["near_ema_ratio_30_4h"] = out_1m["near_ema_ratio_30_4h"].ffill()
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
                run_len_4h = row["run_len_4h"]
                flip_count_30_4h = row["flip_count_30_4h"]
                near_ema_ratio_30_4h = row["near_ema_ratio_30_4h"]

                if pd.isna(rsi) or pd.isna(adx) or pd.isna(ema_val):
                    continue

                self._check_trend_change(trend, price, timestamp, float(ema_val))
                current_time = i
                time_since_last = current_time - self.last_order_time
                self._check_stop_loss(price, timestamp)
                self._manage_trend_hedge(confirmed_trend_4h, price, timestamp, is_new_4h_bucket)

                position_scale, risk_score = self._get_position_scale(run_len_4h, flip_count_30_4h, near_ema_ratio_30_4h)

                if (not ema_touch) and time_since_last >= self.cooldown_time:
                    if rsi <= self.rsi_oversold and trend == "bullish":
                        prev_last_order_time = self.last_order_time
                        self._process_long_entry_with_scale(price, timestamp, float(adx), current_time, position_scale)
                        if self.last_order_time != prev_last_order_time:
                            self.scale_entry_log.append(
                                {
                                    "timestamp": timestamp,
                                    "position_scale": float(position_scale),
                                    "price": price,
                                    "run_len_4h": float(run_len_4h) if pd.notna(run_len_4h) else np.nan,
                                    "flip_count_30_4h": float(flip_count_30_4h) if pd.notna(flip_count_30_4h) else np.nan,
                                    "near_ema_ratio_30_4h": float(near_ema_ratio_30_4h) if pd.notna(near_ema_ratio_30_4h) else np.nan,
                                    "risk_score": int(risk_score),
                                }
                            )

                self._check_take_profit(price, timestamp)
                self._record_equity(price, timestamp, float(ema_val))

            if self.current_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_timestamp = out_1m.index[-1]
                self._close_position(last_price, last_timestamp, "Final Close")

            if self.hedge_position:
                last_price = float(out_1m["close"].iloc[-1])
                last_timestamp = out_1m.index[-1]
                self._close_hedge_short(last_price, last_timestamp, "Final Hedge Close")
                self._record_equity(last_price, last_timestamp, float(out_1m["ema200"].iloc[-1]))

    return FixedBase5xWithRegimeScale


def summarize_scale_usage(entry_log_df: pd.DataFrame) -> dict:
    if entry_log_df.empty:
        return {
            "entries_scaled_total": 0,
            "scale_1_0_entries": 0,
            "scale_0_5_entries": 0,
            "scale_0_25_entries": 0,
            "avg_entry_scale": np.nan,
            "avg_entry_run_len_4h": np.nan,
            "avg_entry_flip_count_30_4h": np.nan,
            "avg_entry_near_ema_ratio_30_4h": np.nan,
            "avg_entry_risk_score": np.nan,
        }

    s = entry_log_df["position_scale"].astype(float)
    return {
        "entries_scaled_total": int(len(entry_log_df)),
        "scale_1_0_entries": int((s == 1.0).sum()),
        "scale_0_5_entries": int((s == 0.5).sum()),
        "scale_0_25_entries": int((s == 0.25).sum()),
        "avg_entry_scale": float(s.mean()),
        "avg_entry_run_len_4h": float(entry_log_df["run_len_4h"].astype(float).mean()),
        "avg_entry_flip_count_30_4h": float(entry_log_df["flip_count_30_4h"].astype(float).mean()),
        "avg_entry_near_ema_ratio_30_4h": float(entry_log_df["near_ema_ratio_30_4h"].astype(float).mean()),
        "avg_entry_risk_score": float(entry_log_df["risk_score"].astype(float).mean()),
    }


def save_plot(equity_curves: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    piv_eq = metrics_df.pivot(index="entry_scale", columns="mode_group", values="final_equity").sort_index()
    piv_mdd = metrics_df.pivot(index="entry_scale", columns="mode_group", values="max_drawdown_pct").sort_index()
    piv_avg_scale = metrics_df.pivot(index="entry_scale", columns="mode_group", values="avg_entry_scale").sort_index()

    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[2.2, 1.0])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("24 Equity Curves by Mode (Time Axis)")
    ax_eq.set_ylabel("Equity (USDT)")

    cmap = plt.get_cmap("tab20")
    modes = metrics_df["mode"].tolist()
    colors = {m: cmap(i % 20) for i, m in enumerate(modes)}
    for mode in modes:
        eq = equity_curves.get(mode)
        if eq is None or eq.empty:
            continue
        ls = "--" if mode.startswith("regime_scaled") else "-"
        ax_eq.plot(eq["timestamp"], eq["equity"], linewidth=1.0, linestyle=ls, label=mode, color=colors[mode])
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2, fontsize=8)

    ax1 = fig.add_subplot(gs[1, 0])
    if "baseline" in piv_eq.columns:
        ax1.plot(piv_eq.index, piv_eq["baseline"], marker="o", label="baseline")
    if "regime_scaled" in piv_eq.columns:
        ax1.plot(piv_eq.index, piv_eq["regime_scaled"], marker="o", label="regime_scaled")
    ax1.set_title("Final Equity by entry_scale")
    ax1.set_xlabel("entry_scale")
    ax1.set_ylabel("Final Equity")
    ax1.grid(True, alpha=0.2)
    ax1.legend()

    ax2 = fig.add_subplot(gs[1, 1])
    if "baseline" in piv_mdd.columns:
        ax2.plot(piv_mdd.index, piv_mdd["baseline"], marker="o", label="baseline MDD")
    if "regime_scaled" in piv_mdd.columns:
        ax2.plot(piv_mdd.index, piv_mdd["regime_scaled"], marker="o", label="regime_scaled MDD")
    if "regime_scaled" in piv_avg_scale.columns:
        ax2_t = ax2.twinx()
        ax2_t.plot(piv_avg_scale.index, piv_avg_scale["regime_scaled"], marker="s", color="tab:green", label="regime avg entry scale")
        ax2_t.set_ylabel("Avg Entry Scale")
        l1, lb1 = ax2.get_legend_handles_labels()
        l2, lb2 = ax2_t.get_legend_handles_labels()
        ax2.legend(l1 + l2, lb1 + lb2, loc="upper left", fontsize=8)
    else:
        ax2.legend(loc="upper left")

    ax2.set_title("MDD by entry_scale + Regime Avg Scale")
    ax2.set_xlabel("entry_scale")
    ax2.set_ylabel("MDD (%)")
    ax2.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=180)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    lines: list[str] = []
    lines.append("# 24 Backtest: Regime-Based Scaling (from 00_1 findings)")
    lines.append("")
    lines.append("## Regime Scaling Rule")
    lines.append("- Use confirmed 4h features only (no look-ahead).")
    lines.append("- Risk score components:")
    lines.append("  - run_len_4h <= 8: +1")
    lines.append("  - run_len_4h <= 3: +1")
    lines.append("  - flip_count_30_4h >= 2: +1")
    lines.append("  - flip_count_30_4h >= 4: +1")
    lines.append("  - near_ema_ratio_30_4h >= 20: +1")
    lines.append("  - near_ema_ratio_30_4h >= 40: +1")
    lines.append("- Position scale:")
    lines.append("  - score >= 4 -> 0.25")
    lines.append("  - score >= 2 -> 0.5")
    lines.append("  - else -> 1.0")
    lines.append("")
    lines.append("## Sweep")
    lines.append("- entry_scale: `0.3, 0.4, 0.5, 0.6, 0.7, 0.8`")
    lines.append("- modes: `baseline` vs `regime_scaled`")
    lines.append("")
    lines.append("## Metrics Table")
    lines.append(
        "| Mode | entry_scale | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor | Avg Entry Scale | Avg Risk Score |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|")
    for _, r in metrics_df.sort_values(["mode_group", "entry_scale"]).iterrows():
        lines.append(
            f"| `{r['mode_group']}` | {_fmt(r['entry_scale'], 1)} | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | "
            f"{_fmt(r['cagr_pct'])} | {_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} | "
            f"{_fmt(r['avg_entry_scale'])} | {_fmt(r['avg_entry_risk_score'])} |"
        )
    lines.append("")
    lines.append("## Delta (regime_scaled - baseline) by entry_scale")
    lines.append("| entry_scale | Equity Delta | Equity Delta % | MDD Delta %pt | Calmar Delta |")
    lines.append("|---:|---:|---:|---:|---:|")
    for es in ENTRY_SCALES:
        b = metrics_df[(metrics_df["entry_scale"] == es) & (metrics_df["mode_group"] == "baseline")]
        d = metrics_df[(metrics_df["entry_scale"] == es) & (metrics_df["mode_group"] == "regime_scaled")]
        if b.empty or d.empty:
            continue
        b = b.iloc[0]
        d = d.iloc[0]
        eq_delta = float(d["final_equity"] - b["final_equity"])
        eq_delta_pct = float((d["final_equity"] / b["final_equity"] - 1.0) * 100.0) if b["final_equity"] != 0 else np.nan
        mdd_delta = float(d["max_drawdown_pct"] - b["max_drawdown_pct"])
        calmar_delta = float(d["calmar_ratio"] - b["calmar_ratio"])
        lines.append(
            f"| {_fmt(es, 1)} | {_fmt(eq_delta)} | {_fmt(eq_delta_pct)} | {_fmt(mdd_delta)} | {_fmt(calmar_delta)} |"
        )

    best_eq = metrics_df.sort_values("final_equity", ascending=False).iloc[0]
    best_calmar = metrics_df.sort_values("calmar_ratio", ascending=False).iloc[0]
    best_mdd = metrics_df.sort_values("max_drawdown_pct", ascending=True).iloc[0]
    lines.append("")
    lines.append("## Highlights")
    lines.append(
        f"- Best Final Equity: `{best_eq['mode']}` (entry_scale `{_fmt(best_eq['entry_scale'], 1)}`, "
        f"equity `{_fmt(best_eq['final_equity'])}`)"
    )
    lines.append(
        f"- Best Calmar: `{best_calmar['mode']}` (entry_scale `{_fmt(best_calmar['entry_scale'], 1)}`, "
        f"calmar `{_fmt(best_calmar['calmar_ratio'])}`)"
    )
    lines.append(
        f"- Lowest MDD: `{best_mdd['mode']}` (entry_scale `{_fmt(best_mdd['entry_scale'], 1)}`, "
        f"MDD `{_fmt(best_mdd['max_drawdown_pct'])}%`)"
    )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{PLOT_FILE}`")
    lines.append(f"- Metrics: `{CSV_FILE}`")
    lines.append(f"- Report: `{MD_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_24", BASE_002_PATH)
    helper_module = load_module("m04_24", BASE_04_PATH)

    df_1m, df_4h = load_data_no_filter(base_module)
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    cases: list[SweepCase] = []
    for es in ENTRY_SCALES:
        cases.append(SweepCase(entry_scale=es, dynamic_regime_scale=False))
        cases.append(SweepCase(entry_scale=es, dynamic_regime_scale=True))

    rows: list[dict] = []
    equity_map: dict[str, pd.DataFrame] = {}

    for case in cases:
        cls = build_case_class(base_module, helper_module, case.dynamic_regime_scale)
        bt = cls(
            symbol=base_module.SYMBOL,
            initial_capital=base_module.INITIAL_CAPITAL,
            commission=base_module.COMMISSION,
            entry_scale=case.entry_scale,
        )
        helper_module.configure_baseline_params(bt)
        bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

        metrics = helper_module.calculate_metrics(bt, base_module.INITIAL_CAPITAL)
        metrics["mode"] = case.mode
        metrics["mode_group"] = "regime_scaled" if case.dynamic_regime_scale else "baseline"
        metrics["entry_scale"] = float(case.entry_scale)
        metrics.update(summarize_scale_usage(pd.DataFrame(bt.scale_entry_log)))
        rows.append(metrics)

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            equity_map[case.mode] = eq[["timestamp", "equity"]].copy()
        else:
            equity_map[case.mode] = pd.DataFrame(columns=["timestamp", "equity"])

    metrics_df = pd.DataFrame(rows).sort_values(["entry_scale", "mode_group"]).reset_index(drop=True)
    metrics_df.to_csv(CSV_FILE, index=False)
    save_plot(equity_map, metrics_df)
    save_report(metrics_df)

    show_cols = [
        "mode",
        "entry_scale",
        "final_equity",
        "max_drawdown_pct",
        "calmar_ratio",
        "avg_entry_scale",
        "avg_entry_risk_score",
        "scale_0_5_entries",
        "scale_0_25_entries",
    ]
    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(f"saved_report={MD_FILE}")
    print(metrics_df[show_cols].to_string(index=False))


if __name__ == "__main__":
    run()

