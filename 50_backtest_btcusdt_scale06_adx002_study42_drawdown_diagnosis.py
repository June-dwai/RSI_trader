from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
BASE_32_PATH = Path("32_backtest_btcusdt_live_nla.py")
BASE_40_PATH = Path("40_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_scale06.py")
BASE_42_PATH = Path("42_backtest_btcusdt_scale06_adx002_equity_combo.py")

INPUT_CURVES_CSV = Path("42_backtest_btcusdt_scale06_adx002_equity_combo_curves.csv")
INPUT_MAX_ENTRIES_CSV = Path("49_backtest_btcusdt_scale06_adx002_case1_max_entries_hedge_matched_sweep.csv")
INPUT_TAILRISK_COMPARE_CSV = Path("42_backtest_btcusdt_scale06_adx002_step2a_tailrisk_portfolio_v2_compare_baselines.csv")

OUT_BASE = "50_backtest_btcusdt_scale06_adx002_study42_drawdown_diagnosis"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_STRESS_WINDOWS_CSV = Path(f"{OUT_BASE}_stress_windows.csv")
OUT_WINDOW_SUMMARY_CSV = Path(f"{OUT_BASE}_window_summary.csv")
OUT_STATE_TIMELINE_CSV = Path(f"{OUT_BASE}_state_timeline.csv")
OUT_EVENT_SUMMARY_CSV = Path(f"{OUT_BASE}_event_summary.csv")
OUT_WORST_DAILY_RETURNS_CSV = Path(f"{OUT_BASE}_worst_daily_returns.csv")

FORWARD_WINDOW_SPECS = [
    ("worst_forward_4h", 240, 5),
    ("worst_forward_1d", 1440, 5),
    ("worst_forward_7d", 10080, 5),
]

INITIAL_CAPITAL_CASE = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
ENTRY_SCALE = 0.60
CASE1_FULL_ENTRIES = 5
CASE2_FULL_ENTRIES = 4
VERIFY_TOL = 1e-6

EXPECTED_FINALS = {
    "case1": 28615.42758147987,
    "case2": 16957.767743076576,
    "total": 45573.195324556444,
}
EXPECTED_GLOBAL_MDD = {
    "start": pd.Timestamp("2024-12-17 18:08:00"),
    "end": pd.Timestamp("2025-04-16 17:59:00"),
    "total_return": -0.6473926177164875,
    "case1_return": -0.7683889295167448,
    "case2_return": 0.029083653808392285,
    "both_loss_rate": 0.201677239383028,
    "offset_rate": 0.06921384510338308,
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


def _fmt(value, digits: int = 4) -> str:
    if value is None:
        return "N/A"
    try:
        if pd.isna(value):
            return "N/A"
    except TypeError:
        pass
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _df_to_md_table(df: pd.DataFrame, digits: int = 4) -> list[str]:
    if df.empty:
        return ["(empty)"]
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        vals = [_fmt(row[c], digits=digits) for c in df.columns]
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def load_reference_curves(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    df = pd.read_csv(path, parse_dates=["timestamp"])
    need = {"timestamp", "equity_case1", "equity_case2", "equity_total"}
    miss = need - set(df.columns)
    if miss:
        raise ValueError(f"Missing required columns: {sorted(miss)}")
    df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    for suffix in ("case1", "case2", "total"):
        eq_col = f"equity_{suffix}"
        ret_col = f"ret_{suffix}"
        dd_col = f"dd_{suffix}"
        df[ret_col] = df[eq_col].pct_change()
        df[dd_col] = df[eq_col] / df[eq_col].cummax() - 1.0
    return df


def build_global_mdd_window(curves: pd.DataFrame) -> dict:
    trough_idx = int(curves["dd_total"].idxmin())
    peak_idx = int(curves.loc[:trough_idx, "equity_total"].idxmax())
    start_row = curves.iloc[peak_idx]
    end_row = curves.iloc[trough_idx]
    return {
        "window_id": "global_mdd_episode",
        "window_group": "global_mdd_episode",
        "window_rank": 1,
        "anchor_timestamp": start_row["timestamp"],
        "start_timestamp": start_row["timestamp"],
        "end_timestamp": end_row["timestamp"],
        "anchor_index": peak_idx,
        "start_index": peak_idx,
        "end_index": trough_idx,
        "bars_in_window": int(trough_idx - peak_idx + 1),
        "horizon_bars": int(trough_idx - peak_idx),
        "selection_metric_total_return": float(end_row["equity_total"] / start_row["equity_total"] - 1.0),
        "selection_metric_case1_return": float(end_row["equity_case1"] / start_row["equity_case1"] - 1.0),
        "selection_metric_case2_return": float(end_row["equity_case2"] / start_row["equity_case2"] - 1.0),
    }


def _intervals_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return not (end_a < start_b or end_b < start_a)


def select_forward_windows(curves: pd.DataFrame, group: str, horizon_bars: int, top_n: int) -> list[dict]:
    work = curves.copy()
    ret_total_col = f"{group}_total"
    ret_case1_col = f"{group}_case1"
    ret_case2_col = f"{group}_case2"
    work[ret_total_col] = work["equity_total"].shift(-horizon_bars) / work["equity_total"] - 1.0
    work[ret_case1_col] = work["equity_case1"].shift(-horizon_bars) / work["equity_case1"] - 1.0
    work[ret_case2_col] = work["equity_case2"].shift(-horizon_bars) / work["equity_case2"] - 1.0

    selected: list[dict] = []
    intervals: list[tuple[int, int]] = []
    candidates = work[ret_total_col].dropna().sort_values().index.tolist()
    for idx in candidates:
        start_idx = int(idx)
        end_idx = int(idx + horizon_bars)
        if any(_intervals_overlap(start_idx, end_idx, s, e) for s, e in intervals):
            continue
        row = work.iloc[start_idx]
        end_row = work.iloc[end_idx]
        selected.append(
            {
                "window_id": f"{group}_{len(selected) + 1:02d}",
                "window_group": group,
                "window_rank": len(selected) + 1,
                "anchor_timestamp": row["timestamp"],
                "start_timestamp": row["timestamp"],
                "end_timestamp": end_row["timestamp"],
                "anchor_index": start_idx,
                "start_index": start_idx,
                "end_index": end_idx,
                "bars_in_window": int(horizon_bars + 1),
                "horizon_bars": int(horizon_bars),
                "selection_metric_total_return": float(row[ret_total_col]),
                "selection_metric_case1_return": float(row[ret_case1_col]),
                "selection_metric_case2_return": float(row[ret_case2_col]),
            }
        )
        intervals.append((start_idx, end_idx))
        if len(selected) >= top_n:
            break
    return selected


def build_stress_windows(curves: pd.DataFrame) -> pd.DataFrame:
    rows = [build_global_mdd_window(curves)]
    for group, horizon_bars, top_n in FORWARD_WINDOW_SPECS:
        rows.extend(select_forward_windows(curves, group, horizon_bars, top_n))
    out = pd.DataFrame(rows)
    group_order = {"global_mdd_episode": 0, "worst_forward_4h": 1, "worst_forward_1d": 2, "worst_forward_7d": 3}
    out["group_order"] = out["window_group"].map(group_order).fillna(99).astype(int)
    out = out.sort_values(["group_order", "window_rank", "start_timestamp"]).reset_index(drop=True)
    return out.drop(columns=["group_order"])


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


def compute_daily_returns(curves: pd.DataFrame) -> pd.DataFrame:
    daily = curves.copy()
    daily["date"] = daily["timestamp"].dt.floor("D")
    agg = (
        daily.groupby("date")
        .agg(
            timestamp_start=("timestamp", "first"),
            timestamp_end=("timestamp", "last"),
            equity_total_start=("equity_total", "first"),
            equity_total_end=("equity_total", "last"),
            equity_case1_start=("equity_case1", "first"),
            equity_case1_end=("equity_case1", "last"),
            equity_case2_start=("equity_case2", "first"),
            equity_case2_end=("equity_case2", "last"),
        )
        .reset_index()
    )
    for suffix in ("total", "case1", "case2"):
        agg[f"return_{suffix}_pct"] = (
            agg[f"equity_{suffix}_end"] / agg[f"equity_{suffix}_start"] - 1.0
        ) * 100.0
    agg = agg.sort_values("return_total_pct").reset_index(drop=True)
    agg["loss_rank_total"] = np.arange(1, len(agg) + 1)
    return agg


def compute_window_daily_returns(window_curve: pd.DataFrame) -> pd.DataFrame:
    work = window_curve.copy()
    work["date"] = work["timestamp"].dt.floor("D")
    daily = (
        work.groupby("date")
        .agg(
            timestamp_start=("timestamp", "first"),
            timestamp_end=("timestamp", "last"),
            equity_total_start=("equity_total", "first"),
            equity_total_end=("equity_total", "last"),
            equity_case1_start=("equity_case1", "first"),
            equity_case1_end=("equity_case1", "last"),
            equity_case2_start=("equity_case2", "first"),
            equity_case2_end=("equity_case2", "last"),
        )
        .reset_index()
    )
    for suffix in ("total", "case1", "case2"):
        daily[f"return_{suffix}_pct"] = (
            daily[f"equity_{suffix}_end"] / daily[f"equity_{suffix}_start"] - 1.0
        ) * 100.0
    return daily.sort_values("return_total_pct").reset_index(drop=True)


def summarize_window(curves: pd.DataFrame, window_row: pd.Series) -> dict:
    sub = curves.iloc[int(window_row["start_index"]) : int(window_row["end_index"]) + 1].copy()
    start = sub.iloc[0]
    end = sub.iloc[-1]
    minute_returns = sub[["ret_case1", "ret_case2"]].dropna()
    if len(minute_returns) >= 2 and minute_returns["ret_case1"].std(ddof=0) > 1e-12 and minute_returns["ret_case2"].std(ddof=0) > 1e-12:
        corr = float(minute_returns["ret_case1"].corr(minute_returns["ret_case2"]))
    else:
        corr = np.nan

    if len(minute_returns):
        both_loss_rate = float(((minute_returns["ret_case1"] < 0) & (minute_returns["ret_case2"] < 0)).mean())
        offset_rate = float(((minute_returns["ret_case1"] < 0) & (minute_returns["ret_case2"] > 0)).mean())
        case1_loss_rate = float((minute_returns["ret_case1"] < 0).mean())
        case2_loss_rate = float((minute_returns["ret_case2"] < 0).mean())
    else:
        both_loss_rate = np.nan
        offset_rate = np.nan
        case1_loss_rate = np.nan
        case2_loss_rate = np.nan

    total_pnl = float(end["equity_total"] - start["equity_total"])
    case1_pnl = float(end["equity_case1"] - start["equity_case1"])
    case2_pnl = float(end["equity_case2"] - start["equity_case2"])
    if total_pnl < 0:
        case1_loss_contribution_share = max(-case1_pnl, 0.0) / max(-total_pnl, 1e-12)
    else:
        case1_loss_contribution_share = np.nan

    daily = compute_window_daily_returns(sub)
    if daily.empty:
        daily_worst_date = pd.NaT
        daily_worst_total_return_pct = np.nan
        daily_worst_case1_return_pct = np.nan
        daily_worst_case2_return_pct = np.nan
    else:
        worst_day = daily.iloc[0]
        daily_worst_date = worst_day["date"]
        daily_worst_total_return_pct = float(worst_day["return_total_pct"])
        daily_worst_case1_return_pct = float(worst_day["return_case1_pct"])
        daily_worst_case2_return_pct = float(worst_day["return_case2_pct"])

    return {
        "window_id": window_row["window_id"],
        "window_group": window_row["window_group"],
        "window_rank": int(window_row["window_rank"]),
        "start_timestamp": start["timestamp"],
        "end_timestamp": end["timestamp"],
        "bars_in_window": int(len(sub)),
        "horizon_bars": int(window_row["horizon_bars"]),
        "selection_metric_total_return_pct": float(window_row["selection_metric_total_return"] * 100.0),
        "selection_metric_case1_return_pct": float(window_row["selection_metric_case1_return"] * 100.0),
        "selection_metric_case2_return_pct": float(window_row["selection_metric_case2_return"] * 100.0),
        "start_equity_total": float(start["equity_total"]),
        "end_equity_total": float(end["equity_total"]),
        "start_equity_case1": float(start["equity_case1"]),
        "end_equity_case1": float(end["equity_case1"]),
        "start_equity_case2": float(start["equity_case2"]),
        "end_equity_case2": float(end["equity_case2"]),
        "total_return_pct": float((end["equity_total"] / start["equity_total"] - 1.0) * 100.0),
        "case1_return_pct": float((end["equity_case1"] / start["equity_case1"] - 1.0) * 100.0),
        "case2_return_pct": float((end["equity_case2"] / start["equity_case2"] - 1.0) * 100.0),
        "total_pnl": total_pnl,
        "case1_pnl": case1_pnl,
        "case2_pnl": case2_pnl,
        "case1_loss_contribution_share": case1_loss_contribution_share,
        "corr_case1_case2": corr,
        "both_loss_rate": both_loss_rate,
        "offset_rate": offset_rate,
        "case1_loss_rate": case1_loss_rate,
        "case2_loss_rate": case2_loss_rate,
        "daily_worst_date": daily_worst_date,
        "daily_worst_total_return_pct": daily_worst_total_return_pct,
        "daily_worst_case1_return_pct": daily_worst_case1_return_pct,
        "daily_worst_case2_return_pct": daily_worst_case2_return_pct,
    }


def build_probe_class(base_cls, strategy_id: str, capture_windows: list[dict]):
    capture_min_ts = min(x["start_timestamp"] for x in capture_windows)
    capture_max_ts = max(x["end_timestamp"] for x in capture_windows)

    class Probe(base_cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.captured_state_rows: list[dict] = []

        def _record_equity(self, price, timestamp, ema):
            super()._record_equity(price, timestamp, ema)
            ts = pd.to_datetime(timestamp)
            if ts < self.capture_min or ts > self.capture_max:
                return
            matched = [w for w in self.capture_windows if w["start_timestamp"] <= ts <= w["end_timestamp"]]
            if not matched:
                return

            pos = self.current_position
            hedge = getattr(self, "hedge_position", None)
            position_side = pos["side"] if pos else None
            position_qty = float(pos["quantity"]) if pos else 0.0
            position_avg_entry = float(pos["avg_entry"]) if pos else np.nan
            if pos:
                if position_side == "LONG":
                    position_unrealized = (float(price) - position_avg_entry) * position_qty
                    long_unrealized = position_unrealized
                else:
                    position_unrealized = (position_avg_entry - float(price)) * position_qty
                    long_unrealized = 0.0
            else:
                position_unrealized = 0.0
                long_unrealized = 0.0

            hedge_qty = float(hedge["quantity"]) if hedge else 0.0
            hedge_avg_entry = float(hedge["avg_entry"]) if hedge else np.nan
            hedge_unrealized = (hedge_avg_entry - float(price)) * hedge_qty if hedge else 0.0
            latest_equity = float(self.equity_curve[-1]["equity"]) if self.equity_curve else np.nan

            base_row = {
                "timestamp": ts,
                "strategy_id": self.capture_strategy_id,
                "price": float(price),
                "equity": latest_equity,
                "capital": float(self.capital),
                "position_side": position_side,
                "position_qty": position_qty,
                "position_avg_entry": position_avg_entry,
                "entry_count": int(self.entry_count),
                "hedge_qty": hedge_qty,
                "hedge_avg_entry": hedge_avg_entry,
                "trend": self.current_trend,
                "long_unrealized": float(long_unrealized),
                "hedge_unrealized": float(hedge_unrealized),
                "position_unrealized": float(position_unrealized),
                "bankrupt": bool(self.bankrupt),
            }
            for window in matched:
                row = base_row.copy()
                row["window_id"] = window["window_id"]
                row["window_group"] = window["window_group"]
                self.captured_state_rows.append(row)

    Probe.capture_strategy_id = strategy_id
    Probe.capture_windows = capture_windows
    Probe.capture_min = capture_min_ts
    Probe.capture_max = capture_max_ts
    return Probe


def dataframe_from_records(records: list[dict], columns: list[str] | None = None) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(records)
    if columns is None:
        return df
    for col in columns:
        if col not in df.columns:
            df[col] = np.nan
    return df[columns]


def prepare_trade_event_frames(bt) -> tuple[pd.DataFrame, pd.DataFrame]:
    trades = dataframe_from_records(bt.trades)
    events = dataframe_from_records(bt.order_events)
    if not trades.empty:
        trades["entry_time"] = pd.to_datetime(trades["entry_time"])
        trades["exit_time"] = pd.to_datetime(trades["exit_time"])
    if not events.empty:
        events["timestamp"] = pd.to_datetime(events["timestamp"])
    return trades, events


def build_event_summary(
    stress_windows: pd.DataFrame,
    state_timeline: pd.DataFrame,
    case1_bt,
    case2_bt,
) -> pd.DataFrame:
    rows: list[dict] = []
    bt_specs = [
        ("case1", case1_bt, CASE1_FULL_ENTRIES, True),
        ("case2", case2_bt, CASE2_FULL_ENTRIES, False),
    ]

    for strategy_id, bt, full_entries, has_hedge in bt_specs:
        trades, events = prepare_trade_event_frames(bt)
        state = state_timeline[state_timeline["strategy_id"] == strategy_id].copy()

        for _, window in stress_windows.iterrows():
            start_ts = window["start_timestamp"]
            end_ts = window["end_timestamp"]
            state_in = state[state["window_id"] == window["window_id"]].copy()
            events_in = events[(events["timestamp"] >= start_ts) & (events["timestamp"] <= end_ts)].copy()
            trades_in = trades[(trades["exit_time"] >= start_ts) & (trades["exit_time"] <= end_ts)].copy()

            if len(state_in):
                full_entries_share = float((state_in["entry_count"] >= full_entries).mean())
                active_position_share = float((state_in["position_qty"] > 0).mean())
                max_entry_count = int(state_in["entry_count"].max())
                position_unrealized_min = float(state_in["position_unrealized"].min())
                if strategy_id == "case1":
                    underwater = state_in["long_unrealized"] < 0
                    underwater_share = float(underwater.mean())
                    if underwater.any():
                        no_hedge_while_underwater_share = float(
                            ((state_in["hedge_qty"] <= 0) & underwater).sum() / underwater.sum()
                        )
                    else:
                        no_hedge_while_underwater_share = np.nan
                    hedge_active_share = float((state_in["hedge_qty"] > 0).mean())
                else:
                    underwater_share = float((state_in["position_unrealized"] < 0).mean())
                    no_hedge_while_underwater_share = np.nan
                    hedge_active_share = float((state_in["hedge_qty"] > 0).mean())
            else:
                full_entries_share = np.nan
                active_position_share = np.nan
                max_entry_count = 0
                underwater_share = np.nan
                no_hedge_while_underwater_share = np.nan
                hedge_active_share = np.nan
                position_unrealized_min = np.nan

            if len(trades_in):
                net_trade_pnl = float(trades_in["pnl"].sum())
                worst_trade_pnl = float(trades_in["pnl"].min())
                closed_trades = int(len(trades_in))
                winning_trades = int((trades_in["pnl"] > 0).sum())
                losing_trades = int((trades_in["pnl"] < 0).sum())
            else:
                net_trade_pnl = 0.0
                worst_trade_pnl = np.nan
                closed_trades = 0
                winning_trades = 0
                losing_trades = 0

            if has_hedge and len(trades_in):
                hedge_trades = trades_in[(trades_in["side"] == "SHORT") & trades_in["reason"].isin(["Trend Up", "Final Hedge Close"])]
                hedge_close_loss_count = int((hedge_trades["pnl"] < 0).sum())
                hedge_close_count = int(len(hedge_trades))
                hedge_close_loss_rate = float((hedge_trades["pnl"] < 0).mean()) if len(hedge_trades) else np.nan
            else:
                hedge_close_loss_count = 0
                hedge_close_count = int(events_in["tag"].fillna("").str.startswith("HEDGE_CLOSE_").sum()) if len(events_in) else 0
                hedge_close_loss_rate = np.nan

            rows.append(
                {
                    "window_id": window["window_id"],
                    "window_group": window["window_group"],
                    "window_rank": int(window["window_rank"]),
                    "strategy_id": strategy_id,
                    "events_in_window": int(len(events_in)),
                    "closed_trades": closed_trades,
                    "net_trade_pnl": net_trade_pnl,
                    "worst_trade_pnl": worst_trade_pnl,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "open_count": int((events_in["tag"] == "OPEN").sum()) if len(events_in) else 0,
                    "dca_count": int(events_in["tag"].fillna("").str.startswith("DCA_").sum()) if len(events_in) else 0,
                    "reentry_count": int((events_in["tag"] == "REENTRY").sum()) if len(events_in) else 0,
                    "partial_stop_loss_count": int((events_in["tag"] == "PARTIAL_Stop Loss").sum()) if len(events_in) else 0,
                    "partial_reverse_count": int((events_in["tag"] == "PARTIAL_Reverse").sum()) if len(events_in) else 0,
                    "close_count": int(events_in["tag"].fillna("").str.startswith("CLOSE_").sum()) if len(events_in) else 0,
                    "take_profit_close_count": int((events_in["tag"] == "CLOSE_Take Profit").sum()) if len(events_in) else 0,
                    "final_close_count": int((events_in["tag"] == "CLOSE_Final Close").sum()) if len(events_in) else 0,
                    "reverse_open_count": int((events_in["tag"] == "REVERSE_OPEN").sum()) if len(events_in) else 0,
                    "hedge_open_count": int((events_in["tag"] == "HEDGE_OPEN").sum()) if len(events_in) else 0,
                    "hedge_close_count": hedge_close_count,
                    "hedge_close_loss_count": hedge_close_loss_count,
                    "hedge_close_loss_rate": hedge_close_loss_rate,
                    "full_entries_share": full_entries_share,
                    "active_position_share": active_position_share,
                    "hedge_active_share": hedge_active_share,
                    "underwater_share": underwater_share,
                    "no_hedge_while_underwater_share": no_hedge_while_underwater_share,
                    "max_entry_count": max_entry_count,
                    "min_position_unrealized": position_unrealized_min,
                }
            )

    return pd.DataFrame(rows).sort_values(["window_group", "window_rank", "strategy_id"]).reset_index(drop=True)


def load_benchmark_context() -> dict:
    ctx: dict[str, dict] = {}
    if INPUT_MAX_ENTRIES_CSV.exists():
        max_entries = pd.read_csv(INPUT_MAX_ENTRIES_CSV)
        row4 = max_entries[max_entries["max_entries"] == 4].iloc[0]
        row5 = max_entries[max_entries["max_entries"] == 5].iloc[0]
        ctx["study49"] = {
            "max4_mdd_pct": float(row4["max_drawdown_pct"]),
            "max5_mdd_pct": float(row5["max_drawdown_pct"]),
            "max4_cagr_pct": float(row4["cagr_pct"]),
            "max5_cagr_pct": float(row5["cagr_pct"]),
        }
    if INPUT_TAILRISK_COMPARE_CSV.exists():
        compare = pd.read_csv(INPUT_TAILRISK_COMPARE_CSV)
        best = compare[compare["label"] == "Best policy"].iloc[0]
        case2_only = compare[compare["label"] == "Case2 only"].iloc[0]
        ctx["study42_step2a"] = {
            "best_policy": str(best["policy_name"]),
            "best_mdd_pct": float(best["mdd_pct"]),
            "best_cagr_pct": float(best["cagr_pct"]),
            "case2_only_mdd_pct": float(case2_only["mdd_pct"]),
            "case2_only_cagr_pct": float(case2_only["cagr_pct"]),
        }
    return ctx


def save_plot(curves: pd.DataFrame, window_summary: pd.DataFrame, state_timeline: pd.DataFrame):
    global_row = window_summary[window_summary["window_id"] == "global_mdd_episode"].iloc[0]
    mdd_start = global_row["start_timestamp"]
    mdd_end = global_row["end_timestamp"]
    zoom = curves[(curves["timestamp"] >= mdd_start) & (curves["timestamp"] <= mdd_end)].copy()
    state = state_timeline[
        (state_timeline["window_id"] == "global_mdd_episode") & (state_timeline["strategy_id"] == "case1")
    ].copy()
    state = state.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")

    fig, axes = plt.subplots(3, 1, figsize=(16, 13), gridspec_kw={"height_ratios": [1.2, 1.1, 1.0]})
    ax_dd, ax_zoom, ax_state = axes

    ax_dd.plot(curves["timestamp"], curves["dd_total"] * 100.0, color="#111111", linewidth=1.2, label="Total DD %")
    ax_dd.plot(curves["timestamp"], curves["dd_case1"] * 100.0, color="#c03a2b", linewidth=0.9, alpha=0.8, label="Case1 DD %")
    ax_dd.plot(curves["timestamp"], curves["dd_case2"] * 100.0, color="#1f618d", linewidth=0.9, alpha=0.8, label="Case2 DD %")
    ax_dd.axvspan(mdd_start, mdd_end, color="#f5cba7", alpha=0.25, label="Global MDD episode")
    ax_dd.set_title("Study 50: Study 42 Full-Period Drawdown")
    ax_dd.set_ylabel("Drawdown %")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="lower left", ncol=4)

    ax_zoom.plot(zoom["timestamp"], zoom["equity_total"], color="#111111", linewidth=1.3, label="Total Equity")
    ax_zoom.plot(zoom["timestamp"], zoom["equity_case1"], color="#c03a2b", linewidth=1.0, label="Case1 Equity")
    ax_zoom.plot(zoom["timestamp"], zoom["equity_case2"], color="#1f618d", linewidth=1.0, label="Case2 Equity")
    ax_zoom.set_title("Global MDD Episode Zoom")
    ax_zoom.set_ylabel("Equity (USDT)")
    ax_zoom.grid(True, alpha=0.2)
    ax_zoom.legend(loc="upper right", ncol=3)

    ax_state.plot(state["timestamp"], state["long_unrealized"], color="#c0392b", linewidth=1.0, label="Case1 Long Unrealized")
    ax_state.plot(state["timestamp"], state["hedge_unrealized"], color="#2874a6", linewidth=1.0, label="Case1 Hedge Unrealized")
    unhedged_underwater = (state["long_unrealized"] < 0) & (state["hedge_qty"] <= 0)
    if len(state):
        ax_state.fill_between(
            state["timestamp"],
            state["long_unrealized"],
            0.0,
            where=unhedged_underwater,
            color="#f1948a",
            alpha=0.25,
            label="Underwater + no hedge",
        )
    ax_state.set_title("Case1 State During Global MDD")
    ax_state.set_ylabel("Unrealized PnL (USDT)")
    ax_state.grid(True, alpha=0.2)
    ax_state_t = ax_state.twinx()
    ax_state_t.step(state["timestamp"], state["entry_count"], where="post", color="#6c3483", linewidth=1.0, label="Entry Count")
    ax_state_t.step(
        state["timestamp"],
        (state["hedge_qty"] > 0).astype(int),
        where="post",
        color="#117864",
        linewidth=1.0,
        label="Hedge Active",
    )
    ax_state_t.set_ylabel("State")
    h1, l1 = ax_state.get_legend_handles_labels()
    h2, l2 = ax_state_t.get_legend_handles_labels()
    ax_state.legend(h1 + h2, l1 + l2, loc="lower left", ncol=4)

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def verify_results(
    case1_metrics: dict,
    case2_metrics: dict,
    total_metrics: dict,
    window_summary: pd.DataFrame,
):
    checks = {
        "case1": float(case1_metrics["final_equity"]),
        "case2": float(case2_metrics["final_equity"]),
        "total": float(total_metrics["final_equity"]),
    }
    for key, actual in checks.items():
        expected = EXPECTED_FINALS[key]
        if abs(actual - expected) > VERIFY_TOL:
            raise ValueError(f"{key} final equity mismatch: expected {expected}, got {actual}")

    global_row = window_summary[window_summary["window_id"] == "global_mdd_episode"].iloc[0]
    if pd.Timestamp(global_row["start_timestamp"]) != EXPECTED_GLOBAL_MDD["start"]:
        raise ValueError(f"Global MDD start mismatch: {global_row['start_timestamp']}")
    if pd.Timestamp(global_row["end_timestamp"]) != EXPECTED_GLOBAL_MDD["end"]:
        raise ValueError(f"Global MDD end mismatch: {global_row['end_timestamp']}")

    compare_cols = {
        "total_return_pct": EXPECTED_GLOBAL_MDD["total_return"] * 100.0,
        "case1_return_pct": EXPECTED_GLOBAL_MDD["case1_return"] * 100.0,
        "case2_return_pct": EXPECTED_GLOBAL_MDD["case2_return"] * 100.0,
        "both_loss_rate": EXPECTED_GLOBAL_MDD["both_loss_rate"],
        "offset_rate": EXPECTED_GLOBAL_MDD["offset_rate"],
    }
    for col, expected in compare_cols.items():
        actual = float(global_row[col])
        if abs(actual - expected) > max(VERIFY_TOL, 1e-9):
            raise ValueError(f"{col} mismatch: expected {expected}, got {actual}")


def build_report(
    curves: pd.DataFrame,
    stress_windows: pd.DataFrame,
    window_summary: pd.DataFrame,
    state_timeline: pd.DataFrame,
    event_summary: pd.DataFrame,
    worst_daily_returns: pd.DataFrame,
    case1_metrics: dict,
    case2_metrics: dict,
    total_metrics: dict,
    benchmark_ctx: dict,
):
    global_row = window_summary[window_summary["window_id"] == "global_mdd_episode"].iloc[0]
    global_case1_state = state_timeline[
        (state_timeline["window_id"] == "global_mdd_episode") & (state_timeline["strategy_id"] == "case1")
    ].copy()
    global_case1_state = global_case1_state.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    trough_ts = pd.Timestamp(global_row["end_timestamp"])
    trough_row = global_case1_state[global_case1_state["timestamp"] == trough_ts].iloc[-1]
    first_full_row = global_case1_state[global_case1_state["entry_count"] >= CASE1_FULL_ENTRIES].head(1)
    first_full_row = first_full_row.iloc[0] if len(first_full_row) else trough_row

    global_event_case1 = event_summary[
        (event_summary["window_id"] == "global_mdd_episode") & (event_summary["strategy_id"] == "case1")
    ].iloc[0]
    global_event_case2 = event_summary[
        (event_summary["window_id"] == "global_mdd_episode") & (event_summary["strategy_id"] == "case2")
    ].iloc[0]

    verification_df = pd.DataFrame(
        [
            {"curve": "case1", "final_equity": case1_metrics["final_equity"], "mdd_pct": case1_metrics["max_drawdown_pct"], "cagr_pct": case1_metrics["cagr_pct"]},
            {"curve": "case2", "final_equity": case2_metrics["final_equity"], "mdd_pct": case2_metrics["max_drawdown_pct"], "cagr_pct": case2_metrics["cagr_pct"]},
            {"curve": "total", "final_equity": total_metrics["final_equity"], "mdd_pct": total_metrics["max_drawdown_pct"], "cagr_pct": total_metrics["cagr_pct"]},
        ]
    )

    window_table = window_summary.sort_values(["window_group", "window_rank"])[
        [
            "window_id",
            "start_timestamp",
            "end_timestamp",
            "total_return_pct",
            "case1_return_pct",
            "case2_return_pct",
            "both_loss_rate",
            "offset_rate",
            "case1_loss_contribution_share",
        ]
    ].reset_index(drop=True)

    checkpoint_rows = [
        {
            "checkpoint": "mdd_start",
            "timestamp": global_case1_state.iloc[0]["timestamp"],
            "price": global_case1_state.iloc[0]["price"],
            "equity": global_case1_state.iloc[0]["equity"],
            "capital": global_case1_state.iloc[0]["capital"],
            "entry_count": global_case1_state.iloc[0]["entry_count"],
            "hedge_qty": global_case1_state.iloc[0]["hedge_qty"],
            "long_unrealized": global_case1_state.iloc[0]["long_unrealized"],
            "hedge_unrealized": global_case1_state.iloc[0]["hedge_unrealized"],
        },
        {
            "checkpoint": "first_full_entries",
            "timestamp": first_full_row["timestamp"],
            "price": first_full_row["price"],
            "equity": first_full_row["equity"],
            "capital": first_full_row["capital"],
            "entry_count": first_full_row["entry_count"],
            "hedge_qty": first_full_row["hedge_qty"],
            "long_unrealized": first_full_row["long_unrealized"],
            "hedge_unrealized": first_full_row["hedge_unrealized"],
        },
        {
            "checkpoint": "mdd_trough",
            "timestamp": trough_row["timestamp"],
            "price": trough_row["price"],
            "equity": trough_row["equity"],
            "capital": trough_row["capital"],
            "entry_count": trough_row["entry_count"],
            "hedge_qty": trough_row["hedge_qty"],
            "long_unrealized": trough_row["long_unrealized"],
            "hedge_unrealized": trough_row["hedge_unrealized"],
        },
    ]
    checkpoint_df = pd.DataFrame(checkpoint_rows)

    worst_daily_table = worst_daily_returns[
        ["date", "return_total_pct", "return_case1_pct", "return_case2_pct", "loss_rank_total"]
    ].head(10)

    lines: list[str] = []
    lines.append("# 50 Backtest: Study 42 Drawdown Diagnosis")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Base curve: `42_backtest_btcusdt_scale06_adx002_equity_combo_curves.csv`")
    lines.append("- Reproduced engines: `case1 = study-40 baseline`, `case2 = study-42 case2 exact`")
    lines.append("- Goal: explain when large losses happened, why the losses were large, and which mitigation directions are most credible.")
    lines.append(f"- Stress windows: `global_mdd_episode` + `{sum(x[2] for x in FORWARD_WINDOW_SPECS)}` forward crash windows")
    lines.append("")
    lines.append("## Reproduction Check")
    lines.extend(_df_to_md_table(verification_df, digits=4))
    lines.append("")
    lines.append("## Global MDD")
    lines.extend(
        _df_to_md_table(
            pd.DataFrame(
                [
                    {
                        "start": global_row["start_timestamp"],
                        "end": global_row["end_timestamp"],
                        "total_return_pct": global_row["total_return_pct"],
                        "case1_return_pct": global_row["case1_return_pct"],
                        "case2_return_pct": global_row["case2_return_pct"],
                        "both_loss_rate": global_row["both_loss_rate"],
                        "offset_rate": global_row["offset_rate"],
                        "case1_loss_contribution_share": global_row["case1_loss_contribution_share"],
                    }
                ]
            ),
            digits=4,
        )
    )
    lines.append("")
    lines.append("## Selected Stress Windows")
    lines.extend(_df_to_md_table(window_table, digits=4))
    lines.append("")
    lines.append("## Case1 State Checkpoints")
    lines.extend(_df_to_md_table(checkpoint_df, digits=4))
    lines.append("")
    lines.append("## Worst Daily Losses")
    lines.extend(_df_to_md_table(worst_daily_table, digits=4))
    lines.append("")
    lines.append("## Why The Loss Was Large")
    lines.append(
        f"- The largest total drawdown episode ran from `{_fmt(global_row['start_timestamp'])}` to `{_fmt(global_row['end_timestamp'])}` with `total {_fmt(global_row['total_return_pct'])}%`."
    )
    lines.append(
        f"- `case1` drove the damage: `{_fmt(global_row['case1_return_pct'])}%` vs `case2 {_fmt(global_row['case2_return_pct'])}%`, so `case1` contributed `{_fmt(global_row['case1_loss_contribution_share'] * 100.0)}%` of the total drop before `case2` offsets."
    )
    lines.append(
        f"- During the same window, `both_loss_rate={_fmt(global_row['both_loss_rate'] * 100.0)}%` and `offset_rate={_fmt(global_row['offset_rate'] * 100.0)}%`, so `case2` was not a reliable structural hedge when the portfolio was under stress."
    )
    lines.append(
        f"- `case1` spent `{_fmt(global_event_case1['full_entries_share'] * 100.0)}%` of the MDD window at full size and `{_fmt(global_event_case1['no_hedge_while_underwater_share'] * 100.0)}%` of underwater bars without hedge protection."
    )
    lines.append(
        f"- `case1` hedge behavior was asymmetric: `{int(global_event_case1['hedge_open_count'])}` hedge opens, `{int(global_event_case1['hedge_close_count'])}` hedge closes, and `{int(global_event_case1['hedge_close_loss_count'])}` closes were loss-making `Trend Up` exits."
    )
    lines.append(
        f"- At the trough timestamp `{_fmt(trough_row['timestamp'])}`, `entry_count={int(trough_row['entry_count'])}`, `hedge_qty={_fmt(trough_row['hedge_qty'])}`, `price={_fmt(trough_row['price'])}`, `position_avg_entry={_fmt(trough_row['position_avg_entry'])}`, `long_unrealized={_fmt(trough_row['long_unrealized'])}`."
    )
    lines.append(
        f"- `case2` helped only partially: in the MDD window it closed `{int(global_event_case2['closed_trades'])}` trades, but the total series still showed frequent same-direction minute losses."
    )
    lines.append("")
    lines.append("## How To Reduce The Loss")
    if "study49" in benchmark_ctx:
        s49 = benchmark_ctx["study49"]
        lines.append(
            f"- Priority 1: reduce `case1` size concentration. Study 49 already showed `max_entries=4` improved case1 MDD to `{_fmt(s49['max4_mdd_pct'])}%` versus `{_fmt(s49['max5_mdd_pct'])}%` at `max_entries=5`."
        )
    else:
        lines.append("- Priority 1: reduce `case1` size concentration via lower `max_entries` or smaller hedge multiple matching.")
    lines.append(
        "- Priority 2: keep some hedge on when the long is fully built and still deeply underwater; the current hedge often closes on `Trend Up` before the real stress is over."
    )
    lines.append(
        "- Priority 3: add an earlier stress gate that blocks new DCA/reentry once bearish stress becomes mature, instead of waiting until the position is already at full size."
    )
    if "study42_step2a" in benchmark_ctx:
        s42 = benchmark_ctx["study42_step2a"]
        lines.append(
            f"- Priority 4: cap `case1` portfolio weight. Study 42 step2a showed `{s42['best_policy']}` reached `MDD {_fmt(s42['best_mdd_pct'])}%` with `CAGR {_fmt(s42['best_cagr_pct'])}%`, materially below the full-`case1` configuration."
        )
    else:
        lines.append("- Priority 4: add a portfolio-level `case1` weight cap rather than relying on `case2` as a passive offset.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Stress windows: `{OUT_STRESS_WINDOWS_CSV}`")
    lines.append(f"- Window summary: `{OUT_WINDOW_SUMMARY_CSV}`")
    lines.append(f"- State timeline: `{OUT_STATE_TIMELINE_CSV}`")
    lines.append(f"- Event summary: `{OUT_EVENT_SUMMARY_CSV}`")
    lines.append(f"- Worst daily returns: `{OUT_WORST_DAILY_RETURNS_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    print("loading_reference_curves")
    reference_curves = load_reference_curves(INPUT_CURVES_CSV)
    stress_windows = build_stress_windows(reference_curves)
    window_summary_rows = [summarize_window(reference_curves, row) for _, row in stress_windows.iterrows()]
    window_summary = pd.DataFrame(window_summary_rows)
    worst_daily_returns = compute_daily_returns(reference_curves)
    benchmark_ctx = load_benchmark_context()

    capture_windows = stress_windows[
        ["window_id", "window_group", "start_timestamp", "end_timestamp"]
    ].to_dict("records")

    print("loading_modules")
    base = load_module("m002_50", BASE_002_PATH)
    helper = load_module("m04_50", BASE_04_PATH)
    m32 = load_module("m32_50", BASE_32_PATH)
    m40 = load_module("m40_50", BASE_40_PATH)
    m42 = load_module("m42_50", BASE_42_PATH)

    print("loading_market_data")
    df_1m, df_4h = m40.load_data_no_filter(base)
    df_1m = df_1m[(df_1m.index >= base.BACKTEST_START) & (df_1m.index <= base.BACKTEST_END)].copy()

    print("running_case1")
    Case1Probe = build_probe_class(m40.LiveParityNoLookahead, "case1", capture_windows)
    bt_case1 = Case1Probe(
        base_module=base,
        symbol=base.SYMBOL,
        initial_capital=INITIAL_CAPITAL_CASE,
        commission=base.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    helper.configure_baseline_params(bt_case1)
    bt_case1.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)

    print("running_case2")
    Case2Base = m42.build_case2_class(m32)
    Case2Probe = build_probe_class(Case2Base, "case2", capture_windows)
    bt_case2 = Case2Probe(
        base_module=base,
        symbol=base.SYMBOL,
        initial_capital=INITIAL_CAPITAL_CASE,
        commission=base.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    helper.configure_baseline_params(bt_case2)
    bt_case2.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)

    print("building_rerun_curves")
    eq_case1 = dataframe_from_records(bt_case1.equity_curve, columns=["timestamp", "equity", "price", "ema200"])
    eq_case2 = dataframe_from_records(bt_case2.equity_curve, columns=["timestamp", "equity", "price", "ema200"])
    eq_case1["timestamp"] = pd.to_datetime(eq_case1["timestamp"])
    eq_case2["timestamp"] = pd.to_datetime(eq_case2["timestamp"])
    rerun_total_curve = m42.build_total_curve(eq_case1, eq_case2)

    case1_metrics = helper.calculate_metrics(bt_case1, INITIAL_CAPITAL_CASE)
    case2_metrics = helper.calculate_metrics(bt_case2, INITIAL_CAPITAL_CASE)
    total_metrics = compute_curve_stats(rerun_total_curve, "equity_total", INITIAL_CAPITAL_TOTAL)

    print("building_state_timeline")
    state_columns = [
        "window_id",
        "window_group",
        "timestamp",
        "strategy_id",
        "price",
        "equity",
        "capital",
        "position_side",
        "position_qty",
        "position_avg_entry",
        "entry_count",
        "hedge_qty",
        "hedge_avg_entry",
        "trend",
        "long_unrealized",
        "hedge_unrealized",
        "position_unrealized",
        "bankrupt",
    ]
    state_timeline = dataframe_from_records(
        bt_case1.captured_state_rows + bt_case2.captured_state_rows,
        columns=state_columns,
    )
    if not state_timeline.empty:
        state_timeline = state_timeline.sort_values(["window_group", "window_id", "strategy_id", "timestamp"]).reset_index(drop=True)

    print("building_event_summary")
    event_summary = build_event_summary(stress_windows, state_timeline, bt_case1, bt_case2)

    print("verifying")
    verify_results(case1_metrics, case2_metrics, total_metrics, window_summary)

    print("saving_outputs")
    stress_windows.to_csv(OUT_STRESS_WINDOWS_CSV, index=False)
    window_summary.to_csv(OUT_WINDOW_SUMMARY_CSV, index=False)
    state_timeline.to_csv(OUT_STATE_TIMELINE_CSV, index=False)
    event_summary.to_csv(OUT_EVENT_SUMMARY_CSV, index=False)
    worst_daily_returns.to_csv(OUT_WORST_DAILY_RETURNS_CSV, index=False)
    save_plot(reference_curves, window_summary, state_timeline)
    build_report(
        curves=reference_curves,
        stress_windows=stress_windows,
        window_summary=window_summary,
        state_timeline=state_timeline,
        event_summary=event_summary,
        worst_daily_returns=worst_daily_returns,
        case1_metrics=case1_metrics,
        case2_metrics=case2_metrics,
        total_metrics=total_metrics,
        benchmark_ctx=benchmark_ctx,
    )

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_stress_windows={OUT_STRESS_WINDOWS_CSV}")
    print(f"saved_window_summary={OUT_WINDOW_SUMMARY_CSV}")
    print(f"saved_state_timeline={OUT_STATE_TIMELINE_CSV}")
    print(f"saved_event_summary={OUT_EVENT_SUMMARY_CSV}")
    print(f"saved_worst_daily_returns={OUT_WORST_DAILY_RETURNS_CSV}")
    print(f"saved_report={OUT_MD}")
    print("verification_passed")


if __name__ == "__main__":
    run()
