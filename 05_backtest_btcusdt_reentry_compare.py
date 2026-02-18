from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")

PLOT_FILE = Path("05_backtest_btcusdt_reentry_compare.png")
CSV_FILE = Path("05_backtest_btcusdt_reentry_compare_metrics.csv")
MD_FILE = Path("05_backtest_btcusdt_reentry_compare.md")

MODE_HEDGE_04 = "hedge_04_confirmed_4h"
MODE_HEDGE_REENTRY_BEP = "hedge_04_plus_infinite_stop_reentry_hybrid_tp"
MODES = [MODE_HEDGE_04, MODE_HEDGE_REENTRY_BEP]


def load_module(alias: str, path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing script: {path}")
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_modified_class(hedge_base_cls):
    class HedgeWithInfiniteStopReentryBepTP(hedge_base_cls):
        """
        04 hedge strategy + modified long management:
        - Infinite stop-loss/re-entry loop:
          stop -> re-entry -> stop -> re-entry ...
        - After re-entry, next stop anchor is re-entry price (not avg price).
        - Hybrid TP:
          before first stop in cycle -> BEP target
          after any stop in cycle -> avg-entry target
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.long_cycle_realized_pnl = 0.0
            self.long_stop_triggered_in_cycle = False

        def run(self, df_1m: pd.DataFrame, df_4h: pd.DataFrame, backtest_start_date=None):
            self.long_cycle_realized_pnl = 0.0
            self.long_stop_triggered_in_cycle = False
            return super().run(df_1m, df_4h, backtest_start_date=backtest_start_date)

        def _open_position(self, side, price, timestamp, quantity):
            opening_new = self.current_position is None
            super()._open_position(side, price, timestamp, quantity)
            if side == "LONG" and opening_new:
                self.long_cycle_realized_pnl = 0.0
                self.long_stop_triggered_in_cycle = False

        def _close_position(self, price, timestamp, reason):
            closing_side = self.current_position["side"] if self.current_position else None
            super()._close_position(price, timestamp, reason)
            if closing_side == "LONG":
                self.long_cycle_realized_pnl = 0.0
                self.long_stop_triggered_in_cycle = False

        def _partial_close(self, price, timestamp, quantity, reason):
            if not self.current_position:
                return

            pos = self.current_position
            side = pos["side"]
            qty = min(quantity, pos["quantity"])
            if qty <= 0:
                return

            # Compute realized pnl before mutation for BEP accounting.
            position_value = qty * price
            commission = position_value * self.commission
            if side == "LONG":
                realized_pnl = (price - pos["avg_entry"]) * qty - commission
            else:
                realized_pnl = (pos["avg_entry"] - price) * qty - commission

            super()._partial_close(price, timestamp, quantity, reason)

            if side == "LONG":
                self.long_cycle_realized_pnl += realized_pnl

        def _calc_long_bep_price(self) -> float:
            if not self.current_position or self.current_position["side"] != "LONG":
                return np.nan

            pos = self.current_position
            qty = float(pos["quantity"])
            if qty <= 0:
                return np.nan

            denominator = qty * (1.0 - self.commission)
            if denominator <= 1e-12:
                return np.nan

            # Need enough closing pnl to offset realized cycle pnl and opening/add commissions.
            numerator = (qty * float(pos["avg_entry"])) + float(pos["total_commission"]) - float(self.long_cycle_realized_pnl)
            return numerator / denominator

        def _check_take_profit(self, price, timestamp):
            if not self.current_position:
                return

            pos = self.current_position
            if pos["side"] != "LONG":
                return super()._check_take_profit(price, timestamp)

            if self.long_stop_triggered_in_cycle:
                tp_price = float(pos["avg_entry"]) * (1.0 + self.take_profit_pct)
                if price >= tp_price:
                    self._close_position(price, timestamp, "Take Profit (Avg After Stop)")
            else:
                bep_price = self._calc_long_bep_price()
                if pd.isna(bep_price):
                    return
                tp_price = bep_price * (1.0 + self.take_profit_pct)
                if price >= tp_price:
                    self._close_position(price, timestamp, "Take Profit (BEP Before Stop)")

        def _trigger_long_stop_partial(self, price, timestamp):
            if not self.current_position or self.current_position["side"] != "LONG":
                return

            close_qty = self.current_position["quantity"] * 0.8
            self._partial_close(price, timestamp, close_qty, "Stop Loss")
            if self.current_position and self.current_position["side"] == "LONG":
                # arm re-entry with stopped size
                self.stop_loss = [price, close_qty]
                self.long_stop_triggered_in_cycle = True

        def _check_stop_loss(self, price, timestamp):
            if not self.current_position:
                if self.stop_loss != [0, 0]:
                    self.stop_loss = [0, 0]
                return

            pos = self.current_position
            if pos["side"] != "LONG":
                return super()._check_stop_loss(price, timestamp)

            entry_price = float(pos["avg_entry"])
            anchor_price = float(self.stop_loss[0]) if self.stop_loss else 0.0
            pending_qty = float(self.stop_loss[1]) if self.stop_loss else 0.0

            # State A: no active stop-reentry cycle yet.
            if anchor_price == 0.0 and pending_qty == 0.0:
                stop_price = entry_price * (1.0 - self.stop_loss_pct)
                if price <= stop_price:
                    self._trigger_long_stop_partial(price, timestamp)
                return

            # State B: waiting for re-entry trigger.
            if pending_qty > 0.0:
                reentry_trigger = anchor_price * (1.0 - self.stop_loss_pct)
                if price <= reentry_trigger:
                    before_qty = float(self.current_position["quantity"]) if self.current_position else 0.0
                    self._add_to_position(price, timestamp, pending_qty, 20)
                    after_qty = float(self.current_position["quantity"]) if self.current_position else 0.0
                    if after_qty > before_qty + 1e-12:
                        # Re-entry happened; arm next stop cycle from this re-entry price.
                        self.stop_loss = [price, 0.0]
                return

            # State C: re-entry done, waiting for next stop from re-entry anchor.
            next_stop_trigger = anchor_price * (1.0 - self.stop_loss_pct)
            if price <= next_stop_trigger:
                self._trigger_long_stop_partial(price, timestamp)

    return HedgeWithInfiniteStopReentryBepTP


def create_backtest(base_module, mode: str, hedge_cls, modified_cls, helper_module):
    if mode == MODE_HEDGE_04:
        cls = hedge_cls
    elif mode == MODE_HEDGE_REENTRY_BEP:
        cls = modified_cls
    else:
        raise ValueError(f"Unknown mode: {mode}")

    bt = cls(
        symbol=base_module.SYMBOL,
        initial_capital=base_module.INITIAL_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=base_module.ENTRY_SCALE,
    )
    helper_module.configure_baseline_params(bt)
    return bt


def save_plot(equity_curves: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    if not equity_curves:
        return

    color_map = {
        MODE_HEDGE_04: "#1f77b4",
        MODE_HEDGE_REENTRY_BEP: "#d62728",
    }

    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])

    ax_eq = fig.add_subplot(gs[0, :])
    ax_eq.set_title("005 Re-entry/BEP TP Comparison (Hedge 04)")
    ax_eq.set_ylabel("Equity (USDT)")
    for mode in MODES:
        eq = equity_curves.get(mode)
        if eq is None or eq.empty:
            continue
        ax_eq.plot(eq["timestamp"], eq["equity"], linewidth=1.2, label=mode, color=color_map[mode])
    ax_eq.legend(loc="upper left")
    ax_eq.grid(True, alpha=0.2)

    ax_final = fig.add_subplot(gs[1, 0])
    ax_final.set_title("Final Equity")
    ax_final.bar(metrics_df["mode"], metrics_df["final_equity"], color=[color_map[m] for m in metrics_df["mode"]])
    ax_final.tick_params(axis="x", rotation=15)
    ax_final.set_ylabel("USDT")
    ax_final.grid(True, axis="y", alpha=0.2)

    ax_mdd = fig.add_subplot(gs[1, 1])
    ax_mdd.set_title("Max Drawdown")
    ax_mdd.bar(metrics_df["mode"], metrics_df["max_drawdown_pct"], color=[color_map[m] for m in metrics_df["mode"]])
    ax_mdd.tick_params(axis="x", rotation=15)
    ax_mdd.set_ylabel("%")
    ax_mdd.grid(True, axis="y", alpha=0.2)

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
    plt.close()


def _fmt(v, digits=4):
    if pd.isna(v):
        return "N/A"
    return f"{v:.{digits}f}"


def save_report(metrics_df: pd.DataFrame):
    base_row = metrics_df[metrics_df["mode"] == MODE_HEDGE_04].iloc[0]
    mod_row = metrics_df[metrics_df["mode"] == MODE_HEDGE_REENTRY_BEP].iloc[0]

    eq_delta_pct = (mod_row["final_equity"] / base_row["final_equity"] - 1.0) * 100.0
    mdd_delta_pp = mod_row["max_drawdown_pct"] - base_row["max_drawdown_pct"]
    trade_delta = int(mod_row["trades"] - base_row["trades"])

    lines = []
    lines.append("# 05 Re-entry Strategy Comparison")
    lines.append("")
    lines.append("## Compared Modes")
    lines.append(f"- `{MODE_HEDGE_04}`")
    lines.append("  - 04 successful hedge strategy (confirmed 4h trend hedge)")
    lines.append("  - original 002 stop-loss/reentry handling")
    lines.append(f"- `{MODE_HEDGE_REENTRY_BEP}`")
    lines.append("  - same 4h-confirmed hedge")
    lines.append("  - long stop-loss/reentry loop enabled indefinitely")
    lines.append("  - after each re-entry, next stop anchor = re-entry price")
    lines.append("  - long TP hybrid rule")
    lines.append("    - before first stop in cycle: BEP-based target (`bep * (1 + take_profit_pct)`)")
    lines.append("    - after any stop in cycle: avg-entry target (`avg_entry * (1 + take_profit_pct)`)")
    lines.append("")
    lines.append("## Performance")
    lines.append("")
    lines.append("| Mode | Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in metrics_df.iterrows():
        lines.append(
            f"| `{r['mode']}` | {_fmt(r['final_equity'])} | {_fmt(r['total_return_pct'])} | {_fmt(r['cagr_pct'])} | "
            f"{_fmt(r['max_drawdown_pct'])} | {_fmt(r['calmar_ratio'])} | {int(r['trades'])} | "
            f"{int(r['long_trades'])}/{int(r['short_trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['profit_factor'])} |"
        )

    lines.append("")
    lines.append("## Delta (Modified vs 04 Hedge)")
    lines.append("")
    lines.append(f"- Final Equity Delta: {_fmt(eq_delta_pct)}%")
    lines.append(f"- MDD Delta: {_fmt(mdd_delta_pp)}%p")
    lines.append(f"- Trades Delta: {trade_delta:+d}")
    lines.append("")
    lines.append("## Notes")
    lines.append("- This update removes the one-time stop/reentry lock state and allows repeated stop/reentry cycles.")
    lines.append("- BEP-based TP is designed to avoid locking losses from repeated stop/reentry on long positions.")
    lines.append("- Profit is not mathematically guaranteed in all paths due to fees, whipsaw, and hedge timing effects.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- plot: `{PLOT_FILE}`")
    lines.append(f"- metrics: `{CSV_FILE}`")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("bt002", BASE_002_PATH)
    helper_module = load_module("m04", BASE_04_PATH)

    _, hedge_cls = helper_module.build_mode_classes(base_module)
    modified_cls = build_modified_class(hedge_cls)

    df_1m, df_4h = base_module.load_data()
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    rows = []
    equity_curves: dict[str, pd.DataFrame] = {}

    for mode in MODES:
        bt = create_backtest(base_module, mode, hedge_cls, modified_cls, helper_module)
        bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

        metrics = helper_module.calculate_metrics(bt, base_module.INITIAL_CAPITAL)
        metrics["mode"] = mode
        rows.append(metrics)

        eq = pd.DataFrame(bt.equity_curve)
        if not eq.empty:
            eq["timestamp"] = pd.to_datetime(eq["timestamp"])
            equity_curves[mode] = eq[["timestamp", "equity"]].copy()
        else:
            equity_curves[mode] = pd.DataFrame(columns=["timestamp", "equity"])

    order_map = {m: i for i, m in enumerate(MODES)}
    metrics_df = pd.DataFrame(rows).sort_values(by="mode", key=lambda s: s.map(order_map)).reset_index(drop=True)

    save_plot(equity_curves, metrics_df)
    metrics_df.to_csv(CSV_FILE, index=False)
    save_report(metrics_df)

    cols = [
        "mode",
        "final_equity",
        "total_return_pct",
        "cagr_pct",
        "max_drawdown_pct",
        "trades",
        "long_trades",
        "short_trades",
        "win_rate_pct",
        "profit_factor",
    ]
    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(f"saved_report={MD_FILE}")
    print(metrics_df[cols].to_string(index=False))


if __name__ == "__main__":
    run()
