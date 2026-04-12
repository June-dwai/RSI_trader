from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
INPUT_CASE2_CURVE_CSV = Path("42_backtest_btcusdt_scale06_adx002_equity_combo_curves.csv")

OUT_BASE = "57_backtest_btcusdt_scale06_adx002_case1_m4_dca075_rsi_open_compare"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

INITIAL_CAPITAL_CASE = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
ENTRY_SCALE = 0.60
MAX_ENTRIES = 4
VERIFY_TOL = 1e-6

DCA_DROP_PCT = 0.0075

VARIANTS = [
    {"variant": "rsi18_dca0p75", "rsi_oversold": 18},
    {"variant": "rsi16_dca0p75", "rsi_oversold": 16},
    {"variant": "rsi15_dca0p75", "rsi_oversold": 15},
    {"variant": "rsi14_dca0p75", "rsi_oversold": 14},
    {"variant": "rsi12_dca0p75", "rsi_oversold": 12},
]

EXPECTED_BASELINE_TOTAL = {
    "final_equity": 38126.11397467511,
    "cagr_pct": 104.70734554000711,
    "mdd_pct": 52.241617709852015,
}


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


def load_case2_curve() -> pd.DataFrame:
    case2 = pd.read_csv(INPUT_CASE2_CURVE_CSV, parse_dates=["timestamp"])[["timestamp", "equity_case2"]]
    return case2.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)


def build_total_curve(case1_curve: pd.DataFrame, case2_curve: pd.DataFrame) -> pd.DataFrame:
    c1 = case1_curve[["timestamp", "equity"]].rename(columns={"equity": "equity_case1"})
    merged = pd.merge(c1, case2_curve, on="timestamp", how="outer").sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2"]).copy()
    merged["equity_total"] = merged["equity_case1"] + merged["equity_case2"]
    return merged


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


def build_variant_class(base_cls, dca_drop_pct: float):
    dca_drop_pct_value = float(dca_drop_pct)

    class DcaSpacingCase(base_cls):
        max_entries_cap = MAX_ENTRIES
        dca_drop_pct = dca_drop_pct_value

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.stats["hedge_topup_events"] = 0
            self.stats["dca_signal_events"] = 0

        def _desired_full_hedge_qty(self) -> float:
            if self.position_quantity > 0:
                self.hedge_base_qty = float(self.position_quantity)
            base_qty = float(self.hedge_base_qty)
            if base_qty <= 0:
                return 0.0
            return base_qty * float(self.max_entries_cap)

        def _add_to_position(self, price: float, timestamp, quantity: float, tag: str):
            if not self.current_position or quantity <= 0 or self.position_quantity <= 0:
                return

            pos = self.current_position
            max_position = self.position_quantity * self.max_entries_cap
            add_qty = min(quantity, max_position - pos["quantity"])
            if add_qty <= 0:
                return

            value = add_qty * price
            commission = value * self.commission
            total_qty = pos["quantity"] + add_qty
            new_avg = (pos["avg_entry"] * pos["quantity"] + price * add_qty) / total_qty

            self.capital -= commission
            pos["avg_entry"] = float(new_avg)
            pos["quantity"] = float(total_qty)
            pos["total_commission"] += float(commission)
            self.entry_count = max(1, round(total_qty / self.position_quantity))
            self.recent_trade = [float(price), pos["side"]]
            self._update_cooldown()

            exec_side = "BUY" if pos["side"] == "LONG" else "SELL"
            self._mark_order(timestamp, price, exec_side, add_qty, tag)

        def _open_hedge_short(self, price: float, timestamp):
            desired_qty = self._desired_full_hedge_qty()
            if desired_qty <= 0:
                return

            if self.hedge_position is None:
                open_commission = desired_qty * price * self.commission
                self.capital -= open_commission
                self.hedge_position = {
                    "side": "SHORT",
                    "avg_entry": float(price),
                    "quantity": float(desired_qty),
                    "entry_time": pd.to_datetime(timestamp),
                    "total_commission": float(open_commission),
                }
                self._mark_order(timestamp, price, "SELL", desired_qty, "HEDGE_OPEN")
                self.stats["hedge_open_events"] += 1
                return

            current_qty = float(self.hedge_position["quantity"])
            add_qty = desired_qty - current_qty
            if add_qty <= 1e-12:
                return
            self._topup_hedge_short(price, timestamp, add_qty)

        def _topup_hedge_short(self, price: float, timestamp, add_qty: float):
            if self.hedge_position is None or add_qty <= 0:
                return
            pos = self.hedge_position
            value = add_qty * price
            commission = value * self.commission
            total_qty = pos["quantity"] + add_qty
            new_avg = (pos["avg_entry"] * pos["quantity"] + price * add_qty) / total_qty

            self.capital -= commission
            pos["avg_entry"] = float(new_avg)
            pos["quantity"] = float(total_qty)
            pos["total_commission"] += float(commission)
            self._mark_order(timestamp, price, "SELL", add_qty, "HEDGE_TOPUP")
            self.stats["hedge_topup_events"] = int(self.stats.get("hedge_topup_events", 0)) + 1

        def _process_long_entry(self, price: float, timestamp, adx: float, current_time: int):
            if not self.current_position:
                if self.capital <= 0:
                    return
                qty = (self.capital / price) * self.entry_scale
                self._open_position("LONG", price, timestamp, qty, "OPEN")
                self.last_order_time = current_time
                return

            if self.current_position["side"] == "LONG":
                trigger_price = self.recent_trade[0] * (1.0 - self.dca_drop_pct)
                if price <= trigger_price:
                    mult = self._get_adx_multiplier(adx)
                    if mult > 0:
                        self.stats["dca_signal_events"] = int(self.stats.get("dca_signal_events", 0)) + 1
                        self._add_to_position(price, timestamp, self.position_quantity * mult, f"DCA_x{mult}")
                        self.last_order_time = current_time
                return

            self._execute_reverse_signal("LONG", price, timestamp, current_time)

        def _manage_trend_hedge(self, confirmed_trend_4h, price: float, timestamp, is_new_4h_bucket: bool):
            if not is_new_4h_bucket:
                return
            if confirmed_trend_4h not in ("bullish", "bearish"):
                return

            if confirmed_trend_4h == "bearish":
                self._open_hedge_short(price, timestamp)
                return

            if self.hedge_position is None:
                return

            self._close_hedge_short(price, timestamp, "Trend Up")

    return DcaSpacingCase


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_mdd = axes

    cmap = plt.get_cmap("viridis")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i / max(1, len(variants) - 1)) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(INITIAL_CAPITAL_TOTAL, color="#777777", linestyle="--", linewidth=0.9, label=f"Start {INITIAL_CAPITAL_TOTAL:.0f}")
    ax_eq.set_title("57 Study: MaxEntries=4 with DCA 0.75% and RSI Entry Variants + Fixed Case2")
    ax_eq.set_ylabel("Total Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_cagr.bar(metrics_df["variant"], metrics_df["total_final_equity"], color=[colors[v] for v in variants], alpha=0.85, label="Total Final Equity")
    ax_cagr.set_ylabel("Total Final Equity")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr.tick_params(axis="x", rotation=20)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(metrics_df["variant"], metrics_df["total_cagr_pct"], color="#d62728", marker="o", linewidth=1.1, label="Total CAGR %")
    ax_cagr_t.set_ylabel("Total CAGR %")
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_mdd.bar(metrics_df["variant"], metrics_df["total_mdd_pct"], color=[colors[v] for v in variants], alpha=0.85, label="Total MDD %")
    ax_mdd.set_ylabel("Total MDD %")
    ax_mdd.grid(True, axis="y", alpha=0.2)
    ax_mdd.tick_params(axis="x", rotation=20)
    ax_mdd_t = ax_mdd.twinx()
    ax_mdd_t.plot(metrics_df["variant"], metrics_df["total_calmar_ratio"], color="#1f77b4", marker="o", linewidth=1.1, label="Total Calmar")
    ax_mdd_t.set_ylabel("Total Calmar")
    h3, l3 = ax_mdd.get_legend_handles_labels()
    h4, l4 = ax_mdd_t.get_legend_handles_labels()
    ax_mdd.legend(h3 + h4, l3 + l4, loc="upper left")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    best_cagr = metrics_df.sort_values("total_cagr_pct", ascending=False).iloc[0]
    best_mdd = metrics_df.sort_values("total_mdd_pct", ascending=True).iloc[0]
    best_calmar = metrics_df.sort_values("total_calmar_ratio", ascending=False).iloc[0]
    baseline = metrics_df[metrics_df["variant"] == "rsi18_dca0p75"].iloc[0]
    improved = metrics_df[
        (metrics_df["total_cagr_pct"] > baseline["total_cagr_pct"])
        & (metrics_df["total_mdd_pct"] < baseline["total_mdd_pct"])
    ].copy()

    lines: list[str] = []
    lines.append("# 57 Backtest: MaxEntries=4 with DCA 0.75% and RSI Entry Variants")
    lines.append("")
    lines.append("## Setup")
    lines.append("- `case1` baseline is the study-56 best CAGR candidate: `max_entries=4`, matched hedge size, `DCA drop = 0.75%`.")
    lines.append("- `case2` stays fixed as study-42 case2 curve.")
    lines.append("- Variant idea: keep DCA spacing fixed at `0.75%`, but require deeper RSI oversold before taking bullish long entries.")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Variant | RSI Oversold | Total Final Equity | Total CAGR % | Total MDD % | Total Calmar | Case1 CAGR % | Case1 MDD % | DCA Signals | Hedge Top-up |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['variant']}` | {int(r['rsi_oversold'])} | "
            f"{_fmt(r['total_final_equity'])} | {_fmt(r['total_cagr_pct'])} | {_fmt(r['total_mdd_pct'])} | "
            f"{_fmt(r['total_calmar_ratio'])} | {_fmt(r['case1_cagr_pct'])} | {_fmt(r['case1_mdd_pct'])} | "
            f"{int(r['dca_signal_events'])} | {int(r['hedge_topup_events'])} |"
        )
    lines.append("")
    lines.append("## Best Cases")
    lines.append(f"- Best total CAGR: `{best_cagr['variant']}` (`{_fmt(best_cagr['total_cagr_pct'])}%`).")
    lines.append(f"- Lowest total MDD: `{best_mdd['variant']}` (`{_fmt(best_mdd['total_mdd_pct'])}%`).")
    lines.append(f"- Best total Calmar: `{best_calmar['variant']}` (`{_fmt(best_calmar['total_calmar_ratio'])}`).")
    lines.append("")
    lines.append("## Delta vs rsi18_dca0p75")
    lines.append("| Variant | Total Final Equity Delta | Total CAGR Delta (pp) | Total MDD Delta (pp) | Total Calmar Delta |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['variant']}` | {_fmt(r['total_final_equity'] - baseline['total_final_equity'])} | "
            f"{_fmt(r['total_cagr_pct'] - baseline['total_cagr_pct'])} | "
            f"{_fmt(r['total_mdd_pct'] - baseline['total_mdd_pct'])} | "
            f"{_fmt(r['total_calmar_ratio'] - baseline['total_calmar_ratio'])} |"
        )
    lines.append("")
    lines.append("## Dominance Check")
    if improved.empty:
        lines.append("- No tested RSI-entry variant achieved both `higher total CAGR` and `lower total MDD` than `rsi18_dca0p75`.")
    else:
        for _, r in improved.iterrows():
            lines.append(
                f"- `{r['variant']}` dominates baseline: CAGR `{_fmt(r['total_cagr_pct'])}%` vs `{_fmt(baseline['total_cagr_pct'])}%`, "
                f"MDD `{_fmt(r['total_mdd_pct'])}%` vs `{_fmt(baseline['total_mdd_pct'])}%`."
            )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If a variant helps, it means the main problem was entering too early on the first bullish oversold signal.")
    lines.append("- If CAGR and MDD both improve, waiting for deeper RSI is filtering weak catches without losing the good ones.")
    lines.append("- The key metric is whether delayed bullish entry can keep the study-56 CAGR gain while pulling MDD back down.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    m47 = load_module("m47_52", BASE_47_PATH)
    case2_curve = load_case2_curve()

    df_1m, df_4h = m47.load_data_no_filter()
    df_1m = df_1m[(df_1m.index >= m47.BACKTEST_START) & (df_1m.index <= m47.BACKTEST_END)].copy()

    rows: list[dict] = []
    total_curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        cls = build_variant_class(m47.LiveParityNoLookahead, DCA_DROP_PCT)
        bt = cls(
            symbol=m47.SYMBOL,
            initial_capital=INITIAL_CAPITAL_CASE,
            commission=m47.COMMISSION,
            entry_scale=ENTRY_SCALE,
        )
        m47.configure_baseline_params(bt)
        bt.rsi_oversold = int(cfg["rsi_oversold"])
        bt.run(df_1m, df_4h, backtest_start_date=m47.BACKTEST_START)

        case1_metrics = m47.calculate_metrics(bt, INITIAL_CAPITAL_CASE)
        eq_case1 = pd.DataFrame(bt.equity_curve)
        eq_case1["timestamp"] = pd.to_datetime(eq_case1["timestamp"])
        total_curve = build_total_curve(eq_case1[["timestamp", "equity"]], case2_curve)
        total_stats = compute_curve_stats(total_curve, "equity_total", INITIAL_CAPITAL_TOTAL)

        total_curve["variant"] = cfg["variant"]
        total_curve_rows.append(total_curve)
        curve_map[cfg["variant"]] = total_curve.copy()

        rows.append(
            {
                "variant": cfg["variant"],
                "rsi_oversold": cfg["rsi_oversold"],
                "case1_final_equity": float(case1_metrics["final_equity"]),
                "case1_cagr_pct": float(case1_metrics["cagr_pct"]),
                "case1_mdd_pct": float(case1_metrics["max_drawdown_pct"]),
                "case1_calmar_ratio": float(case1_metrics["calmar_ratio"]),
                "total_final_equity": total_stats["final_equity"],
                "total_return_pct": total_stats["total_return_pct"],
                "total_cagr_pct": total_stats["cagr_pct"],
                "total_mdd_pct": total_stats["max_drawdown_pct"],
                "total_calmar_ratio": total_stats["calmar_ratio"],
                "dca_signal_events": int(bt.stats.get("dca_signal_events", 0)),
                "hedge_open_events": int(bt.stats.get("hedge_open_events", 0)),
                "hedge_close_events": int(bt.stats.get("hedge_close_events", 0)),
                "hedge_topup_events": int(bt.stats.get("hedge_topup_events", 0)),
            }
        )

    metrics_df = pd.DataFrame(rows)
    curves_df = pd.concat(total_curve_rows, ignore_index=True)

    baseline = metrics_df[metrics_df["variant"] == "rsi18_dca0p75"].iloc[0]
    if abs(float(baseline["total_final_equity"]) - EXPECTED_BASELINE_TOTAL["final_equity"]) > VERIFY_TOL:
        raise ValueError("baseline total final equity mismatch")
    if abs(float(baseline["total_cagr_pct"]) - EXPECTED_BASELINE_TOTAL["cagr_pct"]) > 1e-6:
        raise ValueError("baseline total cagr mismatch")
    if abs(float(baseline["total_mdd_pct"]) - EXPECTED_BASELINE_TOTAL["mdd_pct"]) > 1e-6:
        raise ValueError("baseline total mdd mismatch")

    metrics_df = metrics_df.sort_values(["total_calmar_ratio", "total_cagr_pct"], ascending=[False, False]).reset_index(drop=True)
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
