from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
CASE1_BASE_PATH = Path("40_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_scale06.py")
CASE2_BASE_PATH = Path("32_backtest_btcusdt_live_nla.py")
CASE2_WRAPPER_PATH = Path("42_backtest_btcusdt_scale06_adx002_equity_combo.py")

OUT_BASE = "44_backtest_btcusdt_scale06_adx002_case1_debt_relief"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_CURVE_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_CASE1_COMPARE_CSV = Path(f"{OUT_BASE}_case1_compare.csv")
OUT_DEBT_EVENTS_CSV = Path(f"{OUT_BASE}_case1_debt_events.csv")
OUT_STUCK_CSV = Path(f"{OUT_BASE}_late2024_stuck_compare.csv")

INITIAL_CAPITAL_EACH = 1000.0
ENTRY_SCALE = 0.60
HEDGE_MULTIPLIER_BASE = 5.0
HEDGE_MULTIPLIER_ALT = 6.0

VARIANT_BASELINE = "baseline"
VARIANT_H6 = "baseline_plus_hedge6x"
VARIANT_DEBT_H6 = "baseline_plus_debtrelief_hedge6x"
VARIANT_ORDER = [VARIANT_BASELINE, VARIANT_H6, VARIANT_DEBT_H6]


def load_module(alias: str, path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing script: {path}")
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def build_hedge_multiplier_class(case1_base_mod, hedge_multiplier: float):
    BaseCls = case1_base_mod.LiveParityNoLookahead

    class HedgeMultiplierCase(BaseCls):
        def _open_hedge_short(self, price: float, timestamp):
            if self.hedge_position is not None:
                return
            if self.position_quantity > 0:
                self.hedge_base_qty = float(self.position_quantity)
            base_qty = float(self.hedge_base_qty)
            if base_qty <= 0:
                return

            hedge_qty = base_qty * float(self.hedge_multiplier)
            if hedge_qty <= 0:
                return

            open_commission = hedge_qty * float(price) * self.commission
            self.capital -= open_commission
            self.hedge_position = {
                "side": "SHORT",
                "avg_entry": float(price),
                "quantity": float(hedge_qty),
                "entry_time": pd.to_datetime(timestamp),
                "total_commission": float(open_commission),
            }
            self._mark_order(timestamp, price, "SELL", hedge_qty, f"HEDGE_OPEN_x{self.hedge_multiplier:.1f}")
            self.stats["hedge_open_events"] += 1

    HedgeMultiplierCase.hedge_multiplier = float(hedge_multiplier)
    return HedgeMultiplierCase


def build_debt_relief_class(parent_cls):
    class DebtReliefCase(parent_cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._in_partial_close = False
            self._reset_debt_state()

        def _reset_debt_state(self):
            self.long_debt_usd = 0.0
            self.long_campaign_id = 0
            self.debt_events: list[dict] = []
            self.debt_stats = {
                "hedge_profit_applied_usd": 0.0,
                "hedge_profit_applied_events": 0,
                "campaign_count": 0,
                "campaign_residual_debt_sum": 0.0,
                "campaign_residual_credit_sum": 0.0,
            }

        def run(self, df_1m: pd.DataFrame, df_4h: pd.DataFrame, backtest_start_date=None):
            self._in_partial_close = False
            self._reset_debt_state()
            super().run(df_1m, df_4h, backtest_start_date=backtest_start_date)

        def _long_qty(self) -> float:
            if self.current_position and self.current_position["side"] == "LONG":
                return float(self.current_position["quantity"])
            return 0.0

        def _bep_from(self, debt: float, qty: float) -> float:
            if qty <= 0:
                return np.nan
            denom = qty * (1.0 - self.commission)
            if denom <= 0:
                return np.nan
            return max(float(debt), 0.0) / denom

        def _record_debt_event(
            self,
            timestamp,
            event: str,
            price: float,
            qty_before: float,
            qty_after: float,
            debt_before: float,
            debt_after: float,
            hedge_pnl: float = 0.0,
            applied_usd: float = 0.0,
        ):
            self.debt_events.append(
                {
                    "timestamp": pd.to_datetime(timestamp),
                    "event": event,
                    "price": float(price),
                    "campaign_id": int(self.long_campaign_id),
                    "qty_before": float(qty_before),
                    "qty_after": float(qty_after),
                    "debt_before": float(debt_before),
                    "debt_after": float(debt_after),
                    "debt_delta": float(debt_after - debt_before),
                    "bep_before": self._bep_from(debt_before, qty_before if qty_before > 0 else qty_after),
                    "bep_after": self._bep_from(debt_after, qty_after),
                    "hedge_pnl": float(hedge_pnl),
                    "applied_usd": float(applied_usd),
                }
            )

        def _finalize_long_campaign(self):
            residual = float(self.long_debt_usd)
            self.debt_stats["campaign_count"] += 1
            self.debt_stats["campaign_residual_debt_sum"] += max(residual, 0.0)
            self.debt_stats["campaign_residual_credit_sum"] += max(-residual, 0.0)
            self.long_debt_usd = 0.0

        def _open_position(self, side: str, price: float, timestamp, quantity: float, tag: str):
            qty_before = self._long_qty()
            debt_before = float(self.long_debt_usd)
            super()._open_position(side, price, timestamp, quantity, tag)
            qty_after = self._long_qty()

            if side == "LONG" and qty_after > qty_before:
                add_qty = qty_after - qty_before
                if qty_before == 0:
                    self.long_campaign_id += 1
                self.long_debt_usd += add_qty * float(price) * (1.0 + self.commission)
                self._record_debt_event(
                    timestamp=timestamp,
                    event="LONG_BUY_OPEN",
                    price=float(price),
                    qty_before=qty_before,
                    qty_after=qty_after,
                    debt_before=debt_before,
                    debt_after=float(self.long_debt_usd),
                )

        def _add_to_position(self, price: float, timestamp, quantity: float, tag: str):
            qty_before = self._long_qty()
            debt_before = float(self.long_debt_usd)
            super()._add_to_position(price, timestamp, quantity, tag)
            qty_after = self._long_qty()

            if qty_after > qty_before and qty_after > 0:
                add_qty = qty_after - qty_before
                self.long_debt_usd += add_qty * float(price) * (1.0 + self.commission)
                self._record_debt_event(
                    timestamp=timestamp,
                    event=f"LONG_BUY_ADD_{tag}",
                    price=float(price),
                    qty_before=qty_before,
                    qty_after=qty_after,
                    debt_before=debt_before,
                    debt_after=float(self.long_debt_usd),
                )

        def _partial_close(self, price: float, timestamp, quantity: float, reason: str):
            qty_before = self._long_qty()
            was_long = qty_before > 0
            debt_before = float(self.long_debt_usd)

            self._in_partial_close = True
            try:
                super()._partial_close(price, timestamp, quantity, reason)
            finally:
                self._in_partial_close = False

            qty_after = self._long_qty()
            if was_long and qty_before > qty_after:
                sold_qty = qty_before - qty_after
                proceeds = sold_qty * float(price) * (1.0 - self.commission)
                self.long_debt_usd -= proceeds
                self._record_debt_event(
                    timestamp=timestamp,
                    event=f"LONG_SELL_PARTIAL_{reason}",
                    price=float(price),
                    qty_before=qty_before,
                    qty_after=qty_after,
                    debt_before=debt_before,
                    debt_after=float(self.long_debt_usd),
                )
                if qty_after <= 0:
                    self._finalize_long_campaign()

        def _close_position(self, price: float, timestamp, reason: str):
            qty_before = self._long_qty()
            was_long = qty_before > 0
            debt_before = float(self.long_debt_usd)
            super()._close_position(price, timestamp, reason)

            if self._in_partial_close:
                return

            qty_after = self._long_qty()
            if was_long and qty_before > 0:
                proceeds = qty_before * float(price) * (1.0 - self.commission)
                self.long_debt_usd -= proceeds
                self._record_debt_event(
                    timestamp=timestamp,
                    event=f"LONG_SELL_CLOSE_{reason}",
                    price=float(price),
                    qty_before=qty_before,
                    qty_after=qty_after,
                    debt_before=debt_before,
                    debt_after=float(self.long_debt_usd),
                )
                self._finalize_long_campaign()

        def _close_hedge_short(self, price: float, timestamp, reason: str):
            if self.hedge_position is None:
                return
            pos = self.hedge_position
            close_commission = pos["quantity"] * float(price) * self.commission
            pnl = (pos["avg_entry"] - float(price)) * pos["quantity"] - (pos["total_commission"] + close_commission)

            super()._close_hedge_short(price, timestamp, reason)

            if pnl > 0 and self._long_qty() > 0 and self.long_debt_usd > 0:
                qty_before = self._long_qty()
                debt_before = float(self.long_debt_usd)
                applied = min(float(pnl), float(self.long_debt_usd))
                self.long_debt_usd -= applied
                self.debt_stats["hedge_profit_applied_usd"] += applied
                self.debt_stats["hedge_profit_applied_events"] += 1
                self._record_debt_event(
                    timestamp=timestamp,
                    event=f"HEDGE_PROFIT_TO_DEBT_{reason}",
                    price=float(price),
                    qty_before=qty_before,
                    qty_after=qty_before,
                    debt_before=debt_before,
                    debt_after=float(self.long_debt_usd),
                    hedge_pnl=float(pnl),
                    applied_usd=float(applied),
                )

        def _check_take_profit(self, price: float, timestamp):
            if not self.current_position:
                return
            pos = self.current_position
            avg = float(pos["avg_entry"])
            if pos["side"] == "LONG":
                qty = self._long_qty()
                bep = self._bep_from(self.long_debt_usd, qty)
                if pd.isna(bep) or bep <= 0:
                    target = avg * (1.0 + self.take_profit_pct)
                else:
                    target = bep * (1.0 + self.take_profit_pct)
                if float(price) >= float(target):
                    self._close_position(price, timestamp, "Take Profit (Debt-BEP)")
            elif pos["side"] == "SHORT":
                if float(price) <= avg * (1.0 - self.take_profit_pct):
                    self._close_position(price, timestamp, "Take Profit")

    return DebtReliefCase


def build_total_curve(eq_case1: pd.DataFrame, eq_case2: pd.DataFrame) -> pd.DataFrame:
    c1 = eq_case1[["timestamp", "equity"]].rename(columns={"equity": "equity_case1"})
    c2 = eq_case2[["timestamp", "equity"]].rename(columns={"equity": "equity_case2"})
    out = pd.merge(c1, c2, on="timestamp", how="outer").sort_values("timestamp").reset_index(drop=True)
    out["equity_case1"] = out["equity_case1"].ffill()
    out["equity_case2"] = out["equity_case2"].ffill()
    out = out.dropna(subset=["equity_case1", "equity_case2"]).copy()
    out["equity_total"] = out["equity_case1"] + out["equity_case2"]
    return out


def compute_curve_stats(curve: pd.DataFrame, col: str, initial_capital: float) -> dict:
    s = curve[col].astype(float)
    final_equity = float(s.iloc[-1])
    total_return_pct = ((final_equity / float(initial_capital)) - 1.0) * 100.0

    if len(curve) > 1:
        elapsed_days = (curve["timestamp"].iloc[-1] - curve["timestamp"].iloc[0]).total_seconds() / 86400.0
        years = max(elapsed_days / 365.25, 1e-9)
        cagr_pct = ((final_equity / float(initial_capital)) ** (1.0 / years) - 1.0) * 100.0
    else:
        cagr_pct = np.nan

    dd = (s - s.cummax()) / s.cummax().replace(0, np.nan) * 100.0
    mdd = float(dd.min()) if len(dd) else np.nan
    calmar = (cagr_pct / abs(mdd)) if (pd.notna(cagr_pct) and pd.notna(mdd) and mdd != 0) else np.nan
    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": abs(mdd) if pd.notna(mdd) else np.nan,
        "calmar_ratio": calmar,
    }


def prepare_equity_df(bt) -> pd.DataFrame:
    eq = pd.DataFrame(bt.equity_curve)
    if eq.empty:
        return eq
    eq["timestamp"] = pd.to_datetime(eq["timestamp"])
    return eq.sort_values("timestamp").reset_index(drop=True)


def prepare_trades_df(bt) -> pd.DataFrame:
    t = pd.DataFrame(bt.trades)
    if t.empty:
        return t
    t["entry_time"] = pd.to_datetime(t["entry_time"])
    t["exit_time"] = pd.to_datetime(t["exit_time"])
    t["duration_days"] = (t["exit_time"] - t["entry_time"]).dt.total_seconds() / 86400.0
    return t


def run_case1_variant(variant: str, cls, base_mod, helper_mod, df_1m: pd.DataFrame, df_4h: pd.DataFrame) -> dict:
    bt = cls(
        base_module=base_mod,
        symbol=base_mod.SYMBOL,
        initial_capital=INITIAL_CAPITAL_EACH,
        commission=base_mod.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    helper_mod.configure_baseline_params(bt)
    bt.run(df_1m, df_4h, backtest_start_date=base_mod.BACKTEST_START)

    metrics = helper_mod.calculate_metrics(bt, INITIAL_CAPITAL_EACH)
    eq = prepare_equity_df(bt)
    trades = prepare_trades_df(bt)

    debt_events = pd.DataFrame(getattr(bt, "debt_events", []))
    if not debt_events.empty:
        debt_events["timestamp"] = pd.to_datetime(debt_events["timestamp"])
        debt_events = debt_events.sort_values("timestamp").reset_index(drop=True)

    debt_stats = getattr(
        bt,
        "debt_stats",
        {
            "hedge_profit_applied_usd": 0.0,
            "hedge_profit_applied_events": 0,
            "campaign_count": 0,
            "campaign_residual_debt_sum": 0.0,
            "campaign_residual_credit_sum": 0.0,
        },
    )

    return {
        "variant": variant,
        "bt": bt,
        "metrics": metrics,
        "eq": eq,
        "trades": trades,
        "debt_events": debt_events,
        "debt_stats": debt_stats,
    }


def analyze_stuck_baseline_window(trades_baseline: pd.DataFrame):
    if trades_baseline.empty:
        return None
    longs = trades_baseline[trades_baseline["side"] == "LONG"].copy()
    if longs.empty:
        return None

    cand = longs[longs["entry_time"] >= pd.Timestamp("2024-10-01")].copy()
    if cand.empty:
        cand = longs.copy()
    return cand.sort_values("duration_days", ascending=False).iloc[0]


def analyze_variant_in_window(variant: str, target_trade, trades: pd.DataFrame, debt_events: pd.DataFrame) -> dict:
    if target_trade is None:
        return {
            "variant": variant,
            "baseline_entry": np.nan,
            "baseline_exit": np.nan,
            "baseline_duration_days": np.nan,
            "baseline_num_entries": np.nan,
            "baseline_pnl": np.nan,
            "baseline_reason": "",
            "overlap_long_trades": 0,
            "overlap_total_pnl": np.nan,
            "overlap_max_duration_days": np.nan,
            "overlap_mean_duration_days": np.nan,
            "relief_events_in_window": 0,
            "relief_applied_usd_in_window": 0.0,
            "relief_avg_bep_drop": np.nan,
            "relief_max_bep_drop": np.nan,
        }

    win_start = pd.to_datetime(target_trade["entry_time"])
    win_end = pd.to_datetime(target_trade["exit_time"])

    long_trades = trades[trades["side"] == "LONG"].copy() if not trades.empty else pd.DataFrame()
    if long_trades.empty:
        overlap = pd.DataFrame()
    else:
        overlap = long_trades[(long_trades["entry_time"] <= win_end) & (long_trades["exit_time"] >= win_start)].copy()

    if debt_events.empty:
        ev_relief = pd.DataFrame()
    else:
        ev = debt_events.copy()
        ev["timestamp"] = pd.to_datetime(ev["timestamp"])
        ev = ev[(ev["timestamp"] >= win_start) & (ev["timestamp"] <= win_end)]
        ev_relief = ev[ev["event"].astype(str).str.startswith("HEDGE_PROFIT_TO_DEBT")]

    return {
        "variant": variant,
        "baseline_entry": win_start,
        "baseline_exit": win_end,
        "baseline_duration_days": float(target_trade["duration_days"]),
        "baseline_num_entries": int(target_trade.get("num_entries", 0)),
        "baseline_pnl": float(target_trade.get("pnl", np.nan)),
        "baseline_reason": str(target_trade.get("reason", "")),
        "overlap_long_trades": int(len(overlap)),
        "overlap_total_pnl": float(overlap["pnl"].sum()) if not overlap.empty else np.nan,
        "overlap_max_duration_days": float(overlap["duration_days"].max()) if not overlap.empty else np.nan,
        "overlap_mean_duration_days": float(overlap["duration_days"].mean()) if not overlap.empty else np.nan,
        "relief_events_in_window": int(len(ev_relief)),
        "relief_applied_usd_in_window": float(ev_relief["applied_usd"].sum()) if not ev_relief.empty else 0.0,
        "relief_avg_bep_drop": float((ev_relief["bep_before"] - ev_relief["bep_after"]).mean()) if not ev_relief.empty else np.nan,
        "relief_max_bep_drop": float((ev_relief["bep_before"] - ev_relief["bep_after"]).max()) if not ev_relief.empty else np.nan,
    }


def save_plot(total_map: dict[str, pd.DataFrame], case1_map: dict[str, pd.DataFrame], eq_case2: pd.DataFrame):
    colors = {
        VARIANT_BASELINE: "#1f77b4",
        VARIANT_H6: "#ff7f0e",
        VARIANT_DEBT_H6: "#2ca02c",
    }
    labels = {
        VARIANT_BASELINE: "Case1 baseline (hedge5x)",
        VARIANT_H6: "Case1 baseline+hedge6x",
        VARIANT_DEBT_H6: "Case1 baseline+debtrelief+hedge6x",
    }

    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True, gridspec_kw={"height_ratios": [1.2, 1.0, 1.0]})
    ax0, ax1, ax2 = axes

    for v in VARIANT_ORDER:
        tc = total_map[v]
        ax0.plot(tc["timestamp"], tc["equity_total"], linewidth=1.1, color=colors[v], label=f"Total ({labels[v]})")
    ax0.axhline(INITIAL_CAPITAL_EACH * 2.0, color="#777777", linestyle="--", linewidth=0.9, label="Start 2000")
    ax0.set_title("44 Study: 42 baseline + Case1 variant comparison")
    ax0.set_ylabel("Total Equity")
    ax0.grid(True, alpha=0.2)
    ax0.legend(loc="upper left")

    for v in VARIANT_ORDER:
        eq = case1_map[v]
        ax1.plot(eq["timestamp"], eq["equity"], linewidth=1.1, color=colors[v], label=labels[v])
    ax1.axhline(INITIAL_CAPITAL_EACH, color="#777777", linestyle="--", linewidth=0.9)
    ax1.set_ylabel("Case1 Equity")
    ax1.grid(True, alpha=0.2)
    ax1.legend(loc="upper left")

    ax2.plot(eq_case2["timestamp"], eq_case2["equity"], color="#d62728", linewidth=1.1, label="Case2 (study42)")
    ax2.axhline(INITIAL_CAPITAL_EACH, color="#777777", linestyle="--", linewidth=0.9)
    ax2.set_ylabel("Case2 Equity")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.2)
    ax2.legend(loc="upper left")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def df_to_md_table(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["(empty)"]
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in df.iterrows():
        vals = []
        for c in df.columns:
            v = r[c]
            if isinstance(v, float):
                vals.append(_fmt(v, 4))
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def save_report(metrics_df: pd.DataFrame, case1_df: pd.DataFrame, stuck_df: pd.DataFrame):
    lines: list[str] = []
    lines.append("# 44 백테스트: Case1 3-Variant 비교")
    lines.append("")
    lines.append("## 구성")
    lines.append("- 기준 구조는 42와 동일: Case1 + Case2 합산 Total")
    lines.append("- Case1만 아래 3가지로 비교")
    lines.append("  - baseline (기존 40: hedge 5x)")
    lines.append("  - baseline + hedge6x")
    lines.append("  - baseline + debt relief + hedge6x")
    lines.append("- Case2는 42와 동일 설정 유지")
    lines.append("")

    lines.append("## 성과 요약")
    lines.extend(df_to_md_table(metrics_df))
    lines.append("")

    lines.append("## Case1 전용 비교")
    lines.extend(df_to_md_table(case1_df))
    lines.append("")

    lines.append("## 장기 물림 구간 변화(기준 baseline long-window)")
    lines.append("- baseline의 2024년 10월 이후 LONG 중 최장 보유 구간을 기준 윈도우로 사용")
    lines.extend(df_to_md_table(stuck_df))
    lines.append("")

    lines.append("## 산출물")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVE_CSV}`")
    lines.append(f"- Case1 compare CSV: `{OUT_CASE1_COMPARE_CSV}`")
    lines.append(f"- Debt events CSV: `{OUT_DEBT_EVENTS_CSV}`")
    lines.append(f"- Stuck compare CSV: `{OUT_STUCK_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8-sig")


def run():
    base = load_module("m002_44v2", BASE_002_PATH)
    helper = load_module("m04_44v2", BASE_04_PATH)
    m40 = load_module("m40_44v2", CASE1_BASE_PATH)
    m32 = load_module("m32_44v2", CASE2_BASE_PATH)
    m42 = load_module("m42_44v2", CASE2_WRAPPER_PATH)

    df_1m, df_4h = m40.load_data_no_filter(base)
    df_1m = df_1m[(df_1m.index >= base.BACKTEST_START) & (df_1m.index <= base.BACKTEST_END)].copy()

    # Case2 (same as study42)
    Case2Class = m42.build_case2_class(m32)
    bt_case2 = Case2Class(
        base_module=base,
        symbol=base.SYMBOL,
        initial_capital=INITIAL_CAPITAL_EACH,
        commission=base.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    helper.configure_baseline_params(bt_case2)
    bt_case2.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)
    eq_case2 = prepare_equity_df(bt_case2)
    m_case2 = helper.calculate_metrics(bt_case2, INITIAL_CAPITAL_EACH)

    # Case1 variants
    BaselineCls = m40.LiveParityNoLookahead
    Hedge6Cls = build_hedge_multiplier_class(m40, HEDGE_MULTIPLIER_ALT)
    DebtH6Cls = build_debt_relief_class(Hedge6Cls)

    variant_to_cls = {
        VARIANT_BASELINE: BaselineCls,
        VARIANT_H6: Hedge6Cls,
        VARIANT_DEBT_H6: DebtH6Cls,
    }

    runs: dict[str, dict] = {}
    for v in VARIANT_ORDER:
        runs[v] = run_case1_variant(v, variant_to_cls[v], base, helper, df_1m, df_4h)

    # Curves + metrics
    total_map: dict[str, pd.DataFrame] = {}
    case1_map: dict[str, pd.DataFrame] = {}
    metric_rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []

    for v in VARIANT_ORDER:
        eq1 = runs[v]["eq"]
        case1_map[v] = eq1
        total_curve = build_total_curve(eq1, eq_case2)
        total_map[v] = total_curve

        tc = total_curve.copy()
        tc["variant"] = v
        curve_rows.append(tc)

        m1 = runs[v]["metrics"]
        mt = compute_curve_stats(total_curve, "equity_total", INITIAL_CAPITAL_EACH * 2.0)

        metric_rows.append(
            {
                "curve": f"total_{v}_plus_case2",
                "variant": v,
                "initial_capital": INITIAL_CAPITAL_EACH * 2.0,
                **mt,
                "trades": int(m1.get("trades", 0)) + int(m_case2.get("trades", 0)),
                "long_trades": int(m1.get("long_trades", 0)) + int(m_case2.get("long_trades", 0)),
                "short_trades": int(m1.get("short_trades", 0)) + int(m_case2.get("short_trades", 0)),
                "win_rate_pct": np.nan,
                "profit_factor": np.nan,
            }
        )
        metric_rows.append(
            {
                "curve": f"case1_{v}",
                "variant": v,
                "initial_capital": INITIAL_CAPITAL_EACH,
                **{k: m1.get(k, np.nan) for k in ["final_equity", "total_return_pct", "cagr_pct", "max_drawdown_pct", "calmar_ratio"]},
                "trades": m1.get("trades", 0),
                "long_trades": m1.get("long_trades", 0),
                "short_trades": m1.get("short_trades", 0),
                "win_rate_pct": m1.get("win_rate_pct", np.nan),
                "profit_factor": m1.get("profit_factor", np.nan),
            }
        )

    metric_rows.append(
        {
            "curve": "case2_study42",
            "variant": "case2",
            "initial_capital": INITIAL_CAPITAL_EACH,
            **{k: m_case2.get(k, np.nan) for k in ["final_equity", "total_return_pct", "cagr_pct", "max_drawdown_pct", "calmar_ratio"]},
            "trades": m_case2.get("trades", 0),
            "long_trades": m_case2.get("long_trades", 0),
            "short_trades": m_case2.get("short_trades", 0),
            "win_rate_pct": m_case2.get("win_rate_pct", np.nan),
            "profit_factor": m_case2.get("profit_factor", np.nan),
        }
    )

    metrics_df = pd.DataFrame(metric_rows)
    metrics_df.to_csv(OUT_CSV, index=False)

    pd.concat(curve_rows, ignore_index=True).to_csv(OUT_CURVE_CSV, index=False)

    case1_rows = []
    debt_event_rows = []
    for v in VARIANT_ORDER:
        m1 = runs[v]["metrics"]
        ds = runs[v]["debt_stats"]
        case1_rows.append(
            {
                "case1_variant": v,
                "final_equity": m1.get("final_equity", np.nan),
                "total_return_pct": m1.get("total_return_pct", np.nan),
                "cagr_pct": m1.get("cagr_pct", np.nan),
                "max_drawdown_pct": m1.get("max_drawdown_pct", np.nan),
                "calmar_ratio": m1.get("calmar_ratio", np.nan),
                "trades": m1.get("trades", 0),
                "long_trades": m1.get("long_trades", 0),
                "short_trades": m1.get("short_trades", 0),
                "win_rate_pct": m1.get("win_rate_pct", np.nan),
                "profit_factor": m1.get("profit_factor", np.nan),
                "hedge_profit_applied_events": ds.get("hedge_profit_applied_events", 0),
                "hedge_profit_applied_usd": ds.get("hedge_profit_applied_usd", 0.0),
                "campaign_count": ds.get("campaign_count", 0),
                "campaign_residual_debt_sum": ds.get("campaign_residual_debt_sum", 0.0),
                "campaign_residual_credit_sum": ds.get("campaign_residual_credit_sum", 0.0),
            }
        )

        ev = runs[v]["debt_events"]
        if not ev.empty:
            e2 = ev.copy()
            e2["variant"] = v
            debt_event_rows.append(e2)

    case1_df = pd.DataFrame(case1_rows)
    case1_df.to_csv(OUT_CASE1_COMPARE_CSV, index=False)

    if debt_event_rows:
        pd.concat(debt_event_rows, ignore_index=True).to_csv(OUT_DEBT_EVENTS_CSV, index=False)
    else:
        pd.DataFrame(columns=["variant", "timestamp", "event", "price", "campaign_id", "qty_before", "qty_after", "debt_before", "debt_after", "debt_delta", "bep_before", "bep_after", "hedge_pnl", "applied_usd"]).to_csv(OUT_DEBT_EVENTS_CSV, index=False)

    # Long stuck transformation summary
    target_trade = analyze_stuck_baseline_window(runs[VARIANT_BASELINE]["trades"])
    stuck_rows = []
    for v in VARIANT_ORDER:
        stuck_rows.append(analyze_variant_in_window(v, target_trade, runs[v]["trades"], runs[v]["debt_events"]))
    stuck_df = pd.DataFrame(stuck_rows)
    stuck_df.to_csv(OUT_STUCK_CSV, index=False)

    save_plot(total_map, case1_map, eq_case2)
    save_report(metrics_df, case1_df, stuck_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVE_CSV}")
    print(f"saved_case1_compare={OUT_CASE1_COMPARE_CSV}")
    print(f"saved_debt_events={OUT_DEBT_EVENTS_CSV}")
    print(f"saved_stuck_compare={OUT_STUCK_CSV}")
    print(f"saved_report={OUT_MD}")

    for v in VARIANT_ORDER:
        m = runs[v]["metrics"]
        print(f"case1_{v}_final={_fmt(m.get('final_equity'))}, cagr={_fmt(m.get('cagr_pct'))}%, mdd={_fmt(m.get('max_drawdown_pct'))}%")
    print(f"case2_final={_fmt(m_case2.get('final_equity'))}, cagr={_fmt(m_case2.get('cagr_pct'))}%, mdd={_fmt(m_case2.get('max_drawdown_pct'))}%")


if __name__ == "__main__":
    run()
