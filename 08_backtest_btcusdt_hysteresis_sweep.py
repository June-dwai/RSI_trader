from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")

PLOT_FILE = Path("08_backtest_btcusdt_hysteresis_sweep.png")
CSV_FILE = Path("08_backtest_btcusdt_hysteresis_sweep.csv")
MD_FILE = Path("08_backtest_btcusdt_hysteresis_sweep.md")

# Hysteresis bands to test: 0%, 0.1%, 0.2%, 0.3%, 0.5%
HYSTERESIS_BANDS = [0.0, 0.001, 0.002, 0.003, 0.005]


@dataclass(frozen=True)
class SweepCase:
    band: float

    @property
    def mode(self) -> str:
        return f"hyst_{self.band * 100:.2f}pct"


def load_module(alias: str, path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing script: {path}")
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_fixed5x_hyst_class(base_module, helper_module, hysteresis_pct: float):
    _, BaseHedgeCls = helper_module.build_mode_classes(base_module)

    class FixedBase5xWithHysteresis(BaseHedgeCls):
        hysteresis = float(hysteresis_pct)

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
            out_4h["ema_touch"] = (out_4h["high"] >= out_4h["ema200"]) & (out_4h["low"] <= out_4h["ema200"])
            out_4h["trend_4h_hyst"] = self._compute_hysteresis_state(out_4h, self.hysteresis)
            # No look-ahead: use previous closed 4h state for current 4h bucket.
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

    return FixedBase5xWithHysteresis


def save_plot(equity_curves: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    cmap = plt.get_cmap("viridis")
    modes = metrics_df["mode"].tolist()
    colors = {mode: cmap(i / max(1, len(modes) - 1)) for i, mode in enumerate(modes)}

    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("08 Hysteresis Sweep (Fixed Base5x Hedge)")
    ax_eq.set_ylabel("Equity (USDT)")
    for mode in modes:
        eq = equity_curves.get(mode)
        if eq is None or eq.empty:
            continue
        ax_eq.plot(eq["timestamp"], eq["equity"], linewidth=1.1, label=mode, color=colors[mode])
    ax_eq.legend(loc="upper left", ncol=2)
    ax_eq.grid(True, alpha=0.2)

    ax_final = fig.add_subplot(gs[1, 0])
    ax_final.set_title("Final Equity by Band")
    ax_final.bar(metrics_df["band_label"], metrics_df["final_equity"], color=[colors[m] for m in modes])
    ax_final.set_ylabel("USDT")
    ax_final.set_xlabel("Hysteresis Band")
    ax_final.grid(True, axis="y", alpha=0.2)

    ax_mdd = fig.add_subplot(gs[1, 1])
    ax_mdd.set_title("MDD by Band")
    ax_mdd.bar(metrics_df["band_label"], metrics_df["max_drawdown_pct"], color=[colors[m] for m in modes])
    ax_mdd.set_ylabel("MDD (%)")
    ax_mdd.set_xlabel("Hysteresis Band")
    ax_mdd.grid(True, axis="y", alpha=0.2)

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
    plt.close()


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{v:.{digits}f}"


def save_report(metrics_df: pd.DataFrame):
    best_equity = metrics_df.sort_values("final_equity", ascending=False).iloc[0]
    best_calmar = metrics_df.sort_values("calmar_ratio", ascending=False).iloc[0]
    best_mdd = metrics_df.sort_values("max_drawdown_pct", ascending=True).iloc[0]

    lines: list[str] = []
    lines.append("# 08 Hysteresis Band Sweep")
    lines.append("")
    lines.append("## Objective")
    lines.append("- Test only hysteresis impact on fixed `base_qty * 5` hedge strategy.")
    lines.append("- Keep all other 04 strategy rules unchanged.")
    lines.append("- Use confirmed 4h trend only (`shift(1)`) to avoid look-ahead.")
    lines.append("")
    lines.append("## Sweep Setup")
    lines.append("- Bands tested: `0.00%`, `0.10%`, `0.20%`, `0.30%`, `0.50%`")
    lines.append("- Mode naming: `hyst_XXpct` where `XX` is hysteresis band in percent.")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Band | Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['band_label']}` | `{r['mode']}` | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | "
            f"{_fmt(r['cagr_pct'])} | {_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} |"
        )

    lines.append("")
    lines.append("## Best Bands")
    lines.append(
        f"- Best Final Equity: `{best_equity['band_label']}` (`{_fmt(best_equity['final_equity'])}` USDT, "
        f"return `{_fmt(best_equity['total_return_pct'])}%`)."
    )
    lines.append(
        f"- Best Calmar: `{best_calmar['band_label']}` (Calmar `{_fmt(best_calmar['calmar_ratio'])}`, "
        f"MDD `{_fmt(best_calmar['max_drawdown_pct'])}%`)."
    )
    lines.append(
        f"- Lowest MDD: `{best_mdd['band_label']}` (MDD `{_fmt(best_mdd['max_drawdown_pct'])}%`, "
        f"Final Equity `{_fmt(best_mdd['final_equity'])}` USDT)."
    )
    lines.append("")
    lines.append("## Output Files")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{CSV_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002", BASE_002_PATH)
    helper_module = load_module("m04", BASE_04_PATH)

    df_1m, df_4h = base_module.load_data()
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    rows = []
    equity_map: dict[str, pd.DataFrame] = {}

    cases = [SweepCase(band=b) for b in HYSTERESIS_BANDS]
    for case in cases:
        cls = build_fixed5x_hyst_class(base_module, helper_module, case.band)
        bt = cls(
            symbol=base_module.SYMBOL,
            initial_capital=base_module.INITIAL_CAPITAL,
            commission=base_module.COMMISSION,
            entry_scale=base_module.ENTRY_SCALE,
        )
        helper_module.configure_baseline_params(bt)
        bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

        metrics = helper_module.calculate_metrics(bt, base_module.INITIAL_CAPITAL)
        metrics["band"] = case.band
        metrics["band_label"] = f"{case.band * 100:.2f}%"
        metrics["mode"] = case.mode
        rows.append(metrics)

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            equity_map[case.mode] = eq[["timestamp", "equity"]].copy()
        else:
            equity_map[case.mode] = pd.DataFrame(columns=["timestamp", "equity"])

    metrics_df = pd.DataFrame(rows).sort_values("band").reset_index(drop=True)
    save_plot(equity_map, metrics_df)
    metrics_df.to_csv(CSV_FILE, index=False)
    save_report(metrics_df)

    show_cols = [
        "band_label",
        "mode",
        "final_equity",
        "total_return_pct",
        "cagr_pct",
        "max_drawdown_pct",
        "trades",
        "short_trades",
        "win_rate_pct",
        "profit_factor",
    ]
    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(f"saved_report={MD_FILE}")
    print(metrics_df[show_cols].to_string(index=False))


if __name__ == "__main__":
    run()
