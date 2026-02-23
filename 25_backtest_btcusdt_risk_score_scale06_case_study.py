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

PLOT_FILE = Path("25_backtest_btcusdt_risk_score_scale06_case_study.png")
CSV_FILE = Path("25_backtest_btcusdt_risk_score_scale06_case_study.csv")
MD_FILE = Path("25_backtest_btcusdt_risk_score_scale06_case_study.md")

HYSTERESIS_BAND = 0.005
ENTRY_SCALE_FIXED = 0.6


@dataclass(frozen=True)
class RiskScaleCase:
    case_id: str
    description: str
    # Sorted by min_score ascending: (min_score, position_scale)
    rules: tuple[tuple[int, float], ...]

    def rules_str(self) -> str:
        return ", ".join([f"s>={ms}:{sc:.2f}" for ms, sc in self.rules])


CASES: list[RiskScaleCase] = [
    RiskScaleCase(
        case_id="baseline_no_scale",
        description="No regime scaling",
        rules=((0, 1.00),),
    ),
    RiskScaleCase(
        case_id="mild_s2_0p90",
        description="Reduce lightly at score>=2",
        rules=((0, 1.00), (2, 0.90)),
    ),
    RiskScaleCase(
        case_id="mild_s2_0p85",
        description="Reduce lightly at score>=2 (stronger)",
        rules=((0, 1.00), (2, 0.85)),
    ),
    RiskScaleCase(
        case_id="two_step_90_75",
        description="Two-step mild reduction",
        rules=((0, 1.00), (2, 0.90), (4, 0.75)),
    ),
    RiskScaleCase(
        case_id="two_step_85_65",
        description="Two-step medium reduction",
        rules=((0, 1.00), (2, 0.85), (4, 0.65)),
    ),
    RiskScaleCase(
        case_id="high_only_s4_0p70",
        description="Scale only in very high-risk regime",
        rules=((0, 1.00), (4, 0.70)),
    ),
    RiskScaleCase(
        case_id="aggressive_24_style",
        description="Same aggressive style as 24",
        rules=((0, 1.00), (2, 0.50), (4, 0.25)),
    ),
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


def build_case_class(base_module, helper_module, case: RiskScaleCase):
    _, BaseHedgeCls = helper_module.build_mode_classes(base_module)
    rules_sorted = tuple(sorted(case.rules, key=lambda x: x[0]))

    class FixedBase5xRiskScoreScale(BaseHedgeCls):
        hysteresis = float(HYSTERESIS_BAND)
        rules = rules_sorted

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
        def _risk_score(run_len_4h: float, flip_count_30_4h: float, near_ema_ratio_30_4h: float) -> int:
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

        def _get_position_scale(self, score: int) -> float:
            scale = 1.0
            for min_score, sc in self.rules:
                if score >= int(min_score):
                    scale = float(sc)
                else:
                    break
            return float(scale)

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

                score = self._risk_score(run_len_4h, flip_count_30_4h, near_ema_ratio_30_4h)
                position_scale = self._get_position_scale(score)

                if (not ema_touch) and time_since_last >= self.cooldown_time:
                    if rsi <= self.rsi_oversold and trend == "bullish":
                        prev_last_order_time = self.last_order_time
                        self._process_long_entry_with_scale(price, timestamp, float(adx), current_time, position_scale)
                        if self.last_order_time != prev_last_order_time:
                            self.scale_entry_log.append(
                                {
                                    "timestamp": timestamp,
                                    "position_scale": float(position_scale),
                                    "risk_score": int(score),
                                    "run_len_4h": float(run_len_4h) if pd.notna(run_len_4h) else np.nan,
                                    "flip_count_30_4h": float(flip_count_30_4h) if pd.notna(flip_count_30_4h) else np.nan,
                                    "near_ema_ratio_30_4h": float(near_ema_ratio_30_4h) if pd.notna(near_ema_ratio_30_4h) else np.nan,
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

    return FixedBase5xRiskScoreScale


def summarize_scale_usage(entry_log_df: pd.DataFrame) -> dict:
    if entry_log_df.empty:
        return {
            "entries_scaled_total": 0,
            "entries_scaled_lt1": 0,
            "avg_entry_scale": np.nan,
            "avg_entry_risk_score": np.nan,
            "p90_entry_risk_score": np.nan,
            "avg_entry_run_len_4h": np.nan,
            "avg_entry_flip_count_30_4h": np.nan,
            "avg_entry_near_ema_ratio_30_4h": np.nan,
            "scale_usage_map": "",
        }
    s = entry_log_df["position_scale"].astype(float)
    vc = s.value_counts().sort_index()
    usage_map = "|".join([f"{k:.2f}:{int(v)}" for k, v in vc.items()])
    return {
        "entries_scaled_total": int(len(entry_log_df)),
        "entries_scaled_lt1": int((s < 1.0).sum()),
        "avg_entry_scale": float(s.mean()),
        "avg_entry_risk_score": float(entry_log_df["risk_score"].astype(float).mean()),
        "p90_entry_risk_score": float(entry_log_df["risk_score"].astype(float).quantile(0.90)),
        "avg_entry_run_len_4h": float(entry_log_df["run_len_4h"].astype(float).mean()),
        "avg_entry_flip_count_30_4h": float(entry_log_df["flip_count_30_4h"].astype(float).mean()),
        "avg_entry_near_ema_ratio_30_4h": float(entry_log_df["near_ema_ratio_30_4h"].astype(float).mean()),
        "scale_usage_map": usage_map,
    }


def save_plot(equity_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    order = [c.case_id for c in CASES]
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[2.1, 1.0])

    ax0 = fig.add_subplot(gs[0, :])
    for cid in order:
        eq = equity_map.get(cid)
        if eq is None or eq.empty:
            continue
        ls = "--" if cid != "baseline_no_scale" else "-"
        lw = 1.4 if cid == "baseline_no_scale" else 1.0
        ax0.plot(eq["timestamp"], eq["equity"], linewidth=lw, linestyle=ls, label=cid)
    ax0.set_title("25 Equity Curves (entry_scale fixed = 0.6)")
    ax0.set_ylabel("Equity (USDT)")
    ax0.grid(True, alpha=0.2)
    ax0.legend(loc="upper left", ncol=2, fontsize=8)

    ax1 = fig.add_subplot(gs[1, 0])
    m = metrics_df.set_index("case_id").loc[order]
    ax1.bar(np.arange(len(order)), m["final_equity"].values, color="steelblue", alpha=0.9)
    ax1.set_title("Final Equity by Case")
    ax1.set_ylabel("Final Equity")
    ax1.set_xticks(np.arange(len(order)))
    ax1.set_xticklabels(order, rotation=35, ha="right", fontsize=8)
    ax1.grid(True, axis="y", alpha=0.2)

    ax2 = fig.add_subplot(gs[1, 1])
    ax2.bar(np.arange(len(order)), m["max_drawdown_pct"].values, color="indianred", alpha=0.9, label="MDD %")
    ax2.set_title("MDD and Avg Entry Scale by Case")
    ax2.set_ylabel("MDD (%)")
    ax2.set_xticks(np.arange(len(order)))
    ax2.set_xticklabels(order, rotation=35, ha="right", fontsize=8)
    ax2.grid(True, axis="y", alpha=0.2)
    ax2_t = ax2.twinx()
    ax2_t.plot(np.arange(len(order)), m["avg_entry_scale"].values, marker="o", color="green", label="avg_entry_scale")
    ax2_t.set_ylabel("Avg Entry Scale")
    l1, lb1 = ax2.get_legend_handles_labels()
    l2, lb2 = ax2_t.get_legend_handles_labels()
    ax2.legend(l1 + l2, lb1 + lb2, loc="upper left", fontsize=8)

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=180)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    lines: list[str] = []
    lines.append("# 25 Backtest: Risk-Score Scaling Case Study (entry_scale=0.6 fixed)")
    lines.append("")
    lines.append("## Why This Study")
    lines.append("- `00_1` showed higher DD in short run-length / higher flip / higher near-EMA regimes.")
    lines.append("- This study tests how to map that risk score into position scaling, while keeping base entry_scale fixed at `0.6`.")
    lines.append("")
    lines.append("## Risk Score Definition")
    lines.append("- score +1 if run_len_4h <= 8")
    lines.append("- score +1 if run_len_4h <= 3")
    lines.append("- score +1 if flip_count_30_4h >= 2")
    lines.append("- score +1 if flip_count_30_4h >= 4")
    lines.append("- score +1 if near_ema_ratio_30_4h >= 20")
    lines.append("- score +1 if near_ema_ratio_30_4h >= 40")
    lines.append("")
    lines.append("## Case Definitions")
    lines.append("| Case | Rule (min score -> scale) | Description |")
    lines.append("|---|---|---|")
    for c in CASES:
        lines.append(f"| `{c.case_id}` | `{c.rules_str()}` | {c.description} |")
    lines.append("")
    lines.append("## Metrics")
    lines.append(
        "| Case | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Win Rate % | Avg Entry Scale | Entries(<1.0) | Avg Risk Score | Scale Usage |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for _, r in metrics_df.sort_values("final_equity", ascending=False).iterrows():
        lines.append(
            f"| `{r['case_id']}` | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | {_fmt(r['cagr_pct'])} | {_fmt(r['max_drawdown_pct'])} | "
            f"{_fmt(r['calmar_ratio'])} | {int(r['trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['avg_entry_scale'])} | "
            f"{int(r['entries_scaled_lt1'])} | {_fmt(r['avg_entry_risk_score'])} | `{r['scale_usage_map']}` |"
        )
    lines.append("")

    baseline = metrics_df[metrics_df["case_id"] == "baseline_no_scale"].iloc[0]
    lines.append("## Delta vs Baseline")
    lines.append("| Case | Equity Delta | Equity Delta % | MDD Delta %pt | Calmar Delta |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, r in metrics_df[metrics_df["case_id"] != "baseline_no_scale"].iterrows():
        eq_delta = float(r["final_equity"] - baseline["final_equity"])
        eq_delta_pct = float((r["final_equity"] / baseline["final_equity"] - 1.0) * 100.0) if baseline["final_equity"] != 0 else np.nan
        mdd_delta = float(r["max_drawdown_pct"] - baseline["max_drawdown_pct"])
        calmar_delta = float(r["calmar_ratio"] - baseline["calmar_ratio"])
        lines.append(
            f"| `{r['case_id']}` | {_fmt(eq_delta)} | {_fmt(eq_delta_pct)} | {_fmt(mdd_delta)} | {_fmt(calmar_delta)} |"
        )
    lines.append("")

    best_eq = metrics_df.sort_values("final_equity", ascending=False).iloc[0]
    best_mdd = metrics_df.sort_values("max_drawdown_pct", ascending=True).iloc[0]
    best_calmar = metrics_df.sort_values("calmar_ratio", ascending=False).iloc[0]
    lines.append("## Highlights")
    lines.append(f"- Best Final Equity: `{best_eq['case_id']}` ({_fmt(best_eq['final_equity'])})")
    lines.append(f"- Lowest MDD: `{best_mdd['case_id']}` ({_fmt(best_mdd['max_drawdown_pct'])}%)")
    lines.append(f"- Best Calmar: `{best_calmar['case_id']}` ({_fmt(best_calmar['calmar_ratio'])})")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{PLOT_FILE}`")
    lines.append(f"- Metrics: `{CSV_FILE}`")
    lines.append(f"- Report: `{MD_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_25", BASE_002_PATH)
    helper_module = load_module("m04_25", BASE_04_PATH)

    df_1m, df_4h = load_data_no_filter(base_module)
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    rows: list[dict] = []
    equity_map: dict[str, pd.DataFrame] = {}

    for case in CASES:
        print(f"[run] case={case.case_id} rules={case.rules_str()}")
        cls = build_case_class(base_module, helper_module, case)
        bt = cls(
            symbol=base_module.SYMBOL,
            initial_capital=base_module.INITIAL_CAPITAL,
            commission=base_module.COMMISSION,
            entry_scale=ENTRY_SCALE_FIXED,
        )
        helper_module.configure_baseline_params(bt)
        bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

        metrics = helper_module.calculate_metrics(bt, base_module.INITIAL_CAPITAL)
        metrics["case_id"] = case.case_id
        metrics["case_description"] = case.description
        metrics["rules"] = case.rules_str()
        metrics["entry_scale_fixed"] = float(ENTRY_SCALE_FIXED)
        metrics.update(summarize_scale_usage(pd.DataFrame(bt.scale_entry_log)))
        rows.append(metrics)

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            equity_map[case.case_id] = eq[["timestamp", "equity"]].copy()
        else:
            equity_map[case.case_id] = pd.DataFrame(columns=["timestamp", "equity"])

    metrics_df = pd.DataFrame(rows).reset_index(drop=True)
    metrics_df.to_csv(CSV_FILE, index=False)
    save_plot(equity_map, metrics_df)
    save_report(metrics_df)

    show_cols = [
        "case_id",
        "final_equity",
        "max_drawdown_pct",
        "calmar_ratio",
        "avg_entry_scale",
        "entries_scaled_lt1",
        "avg_entry_risk_score",
        "scale_usage_map",
    ]
    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(f"saved_report={MD_FILE}")
    print(metrics_df[show_cols].sort_values("final_equity", ascending=False).to_string(index=False))


if __name__ == "__main__":
    run()

