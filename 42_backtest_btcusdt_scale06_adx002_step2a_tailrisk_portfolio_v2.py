from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


INPUT_CURVES = Path("42_backtest_btcusdt_scale06_adx002_equity_combo_curves.csv")
INPUT_EVENTS = Path("42_backtest_btcusdt_scale06_adx002_structural_offset_step1_rise_crash_events.csv")

BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_40_PATH = Path("40_backtest_btcusdt_live_nla_longonly_hedge_hyst05_adx002_scale06.py")

OUT_BASE = "42_backtest_btcusdt_scale06_adx002_step2a_tailrisk_portfolio_v2"
OUT_DYNAMIC_TRAIN = Path(f"{OUT_BASE}_dynamic_train.csv")
OUT_VAL_ALL = Path(f"{OUT_BASE}_validation_all.csv")
OUT_TOP15_80 = Path(f"{OUT_BASE}_top15_cagr80.csv")
OUT_TOP15_100 = Path(f"{OUT_BASE}_top15_cagr100.csv")
OUT_COMPARE = Path(f"{OUT_BASE}_compare_baselines.csv")
OUT_BEST_WEIGHTS = Path(f"{OUT_BASE}_best_weights.csv")
OUT_REPORT = Path(f"{OUT_BASE}.md")

TRAIN_RATIO = 0.70
STATIC_STEP = 0.02
VOL_WINDOWS = [30, 60, 120]
TOP_DYNAMIC_FROM_TRAIN = 24
TOPN = 15


@dataclass(frozen=True)
class PolicySpec:
    family: str
    name: str
    params: dict[str, Any]
    tc_bps: float = 0.0


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


def _fmt(v: float | int | None, digits: int = 6) -> str:
    if v is None:
        return "N/A"
    try:
        if pd.isna(v):
            return "N/A"
    except TypeError:
        pass
    return f"{float(v):.{digits}f}"


def _to_md_table(df: pd.DataFrame, digits: int = 6) -> list[str]:
    if df.empty:
        return ["(empty)"]
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        vals = []
        for c in df.columns:
            v = row[c]
            if isinstance(v, float):
                vals.append(_fmt(v, digits))
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def calculate_rsi(closes: pd.Series, period: int = 6) -> pd.Series:
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi[(avg_loss == 0) & (avg_gain > 0)] = 100
    rsi[(avg_gain == 0) & (avg_loss > 0)] = 0
    rsi[(avg_gain == 0) & (avg_loss == 0)] = 50
    return rsi.fillna(50)


def calculate_adx_002(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr = tr.rolling(period).mean()
    plus_di = 100 * pd.Series(pos_dm, index=df.index).rolling(period).mean() / atr
    minus_di = 100 * pd.Series(neg_dm, index=df.index).rolling(period).mean() / atr
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).abs()
    return dx.rolling(period).mean()


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not INPUT_CURVES.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_CURVES}")
    if not INPUT_EVENTS.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_EVENTS}")

    curves = pd.read_csv(INPUT_CURVES, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    need = {"timestamp", "equity_case1", "equity_case2"}
    miss = need - set(curves.columns)
    if miss:
        raise ValueError(f"Missing columns in curves: {sorted(miss)}")

    events = pd.read_csv(INPUT_EVENTS, parse_dates=["drop_start", "drop_end"]).sort_values("drop_start").reset_index(drop=True)
    return curves, events


def build_market_features(curves: pd.DataFrame) -> pd.DataFrame:
    base = load_module("m002_s2a_v2", BASE_002_PATH)
    m40 = load_module("m40_s2a_v2", BASE_40_PATH)
    df_1m, df_4h = m40.load_data_no_filter(base)

    df_1m = df_1m[(df_1m.index >= pd.Timestamp(base.BACKTEST_START)) & (df_1m.index <= pd.Timestamp(base.BACKTEST_END))].copy()
    df_1m = df_1m.sort_index()
    df_4h = df_4h.sort_index()

    out_4h = df_4h.copy()
    out_4h["ema200_closed"] = out_4h["close"].ewm(span=200, adjust=False).mean()
    out_4h["trend4h_prev"] = (out_4h["close"] > out_4h["ema200_closed"]).shift(1)
    out_4h["trend4h_prev"] = out_4h["trend4h_prev"].fillna(False)

    out_1m = df_1m.copy()
    out_1m["bucket_4h"] = out_1m.index.floor("4h")
    out_1m = out_1m.merge(
        out_4h[["trend4h_prev"]],
        left_on="bucket_4h",
        right_index=True,
        how="left",
    )
    out_1m["trend4h_prev"] = out_1m["trend4h_prev"].ffill().fillna(False)
    out_1m["trend4h_bear_lag"] = (~out_1m["trend4h_prev"]).astype(int)

    out_1m["adx"] = calculate_adx_002(out_1m, period=14)
    out_1m["adx_lag"] = out_1m["adx"].shift(1).ffill().fillna(0.0)

    out_1m["rsi6"] = calculate_rsi(out_1m["close"], period=6)
    # At time t, use information up to t-1 only.
    out_1m["rsi_overbought_reversal_lag"] = (
        (out_1m["rsi6"].shift(2) >= 85.0) & (out_1m["rsi6"].shift(1) < 85.0)
    ).fillna(False).astype(int)

    feats = out_1m[["trend4h_bear_lag", "adx_lag", "rsi_overbought_reversal_lag"]].copy()
    feats = feats.reset_index().rename(columns={"index": "timestamp"})

    merged = curves[["timestamp"]].merge(feats, on="timestamp", how="left")
    merged["trend4h_bear_lag"] = merged["trend4h_bear_lag"].ffill().fillna(0).astype(int)
    merged["adx_lag"] = merged["adx_lag"].ffill().fillna(0.0)
    merged["rsi_overbought_reversal_lag"] = merged["rsi_overbought_reversal_lag"].fillna(0).astype(int)
    return merged


def build_base_df(curves: pd.DataFrame, market_feats: pd.DataFrame) -> dict[str, Any]:
    df = curves.copy()
    df["r1"] = df["equity_case1"].pct_change().fillna(0.0)
    df["r2"] = df["equity_case2"].pct_change().fillna(0.0)
    df["dd1"] = df["equity_case1"] / df["equity_case1"].cummax() - 1.0
    df["dd1_lag"] = df["dd1"].shift(1).fillna(0.0)

    for w in VOL_WINDOWS:
        v1 = df["r1"].rolling(w).std(ddof=0).shift(1)
        v2 = df["r2"].rolling(w).std(ddof=0).shift(1)
        v1 = v1.replace([np.inf, -np.inf], np.nan).fillna(v1.median())
        v2 = v2.replace([np.inf, -np.inf], np.nan).fillna(v2.median())
        df[f"vol1_{w}"] = v1
        df[f"vol2_{w}"] = v2

        inv1 = 1.0 / np.maximum(v1.to_numpy(dtype=float), 1e-12)
        inv2 = 1.0 / np.maximum(v2.to_numpy(dtype=float), 1e-12)
        w1 = inv1 / np.maximum(inv1 + inv2, 1e-12)
        df[f"w_rp_{w}"] = np.clip(np.nan_to_num(w1, nan=0.5), 0.0, 1.0)

    df["vol_ratio_60"] = (df["vol1_60"] / np.maximum(df["vol2_60"], 1e-12)).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    df["vol_ratio_60_lag"] = df["vol_ratio_60"].shift(1).fillna(1.0)

    df = df.merge(market_feats, on="timestamp", how="left")
    df["trend4h_bear_lag"] = df["trend4h_bear_lag"].fillna(0).astype(int)
    df["adx_lag"] = df["adx_lag"].fillna(0.0)
    df["rsi_overbought_reversal_lag"] = df["rsi_overbought_reversal_lag"].fillna(0).astype(int)

    n = len(df)
    split_idx = int(n * TRAIN_RATIO)
    split_idx = min(max(split_idx, 1), n - 1)
    return {"df": df, "split_idx": split_idx}


def build_event_windows(timestamps: np.ndarray, events: pd.DataFrame) -> list[tuple[int, int]]:
    windows: list[tuple[int, int]] = []
    for _, row in events.iterrows():
        s_raw = np.datetime64(row["drop_start"].to_datetime64())
        e_raw = np.datetime64(row["drop_end"].to_datetime64())
        s = int(np.searchsorted(timestamps, s_raw, side="left"))
        e = int(np.searchsorted(timestamps, e_raw, side="right")) - 1
        if s >= len(timestamps):
            continue
        s = max(0, s)
        e = min(len(timestamps) - 1, e)
        if s <= e:
            windows.append((s, e))
    return windows


def build_static_specs() -> list[PolicySpec]:
    ws = np.round(np.arange(0.0, 1.0 + 1e-12, STATIC_STEP), 2)
    return [PolicySpec(family="A_static", name=f"A_static_w1_{w:.2f}", params={"w1_const": float(w)}, tc_bps=0.0) for w in ws]


def build_risk_parity_specs() -> list[PolicySpec]:
    return [
        PolicySpec(family="B_risk_parity", name=f"B_riskparity_vol{w}", params={"window": int(w)}, tc_bps=0.0)
        for w in VOL_WINDOWS
    ]


def build_dynamic_specs() -> list[PolicySpec]:
    specs: list[PolicySpec] = []
    dd_pairs = [(-0.08, -0.16), (-0.10, -0.20), (-0.12, -0.24)]
    cap_pairs = [(0.45, 0.25), (0.40, 0.20)]
    bearish_caps = [0.45, 0.35]
    adx_hi = [30.0]
    adx_bear_caps = [0.30, 0.20]
    rsi_rev_caps = [0.30, 0.20]
    vol_ratio_hi = [1.20, 1.40]
    vol_caps = [0.40]
    half_lives = [30, 60]

    for dd_mid, dd_deep in dd_pairs:
        for cap_mid, cap_deep in cap_pairs:
            for bear_cap in bearish_caps:
                for adx_thr in adx_hi:
                    for adx_cap in adx_bear_caps:
                        for rsi_cap in rsi_rev_caps:
                            for vr_hi in vol_ratio_hi:
                                for vcap in vol_caps:
                                    for hl in half_lives:
                                        name = (
                                            "C_dyn"
                                            f"_ddm{abs(dd_mid):.2f}"
                                            f"_ddd{abs(dd_deep):.2f}"
                                            f"_cm{cap_mid:.2f}"
                                            f"_cd{cap_deep:.2f}"
                                            f"_bc{bear_cap:.2f}"
                                            f"_ac{adx_cap:.2f}"
                                            f"_rc{rsi_cap:.2f}"
                                            f"_vr{vr_hi:.2f}"
                                            f"_hl{hl}"
                                        )
                                        specs.append(
                                            PolicySpec(
                                                family="C_dynamic",
                                                name=name,
                                                params={
                                                    "dd_mid": dd_mid,
                                                    "dd_deep": dd_deep,
                                                    "cap_mid": cap_mid,
                                                    "cap_deep": cap_deep,
                                                    "bearish_cap": bear_cap,
                                                    "adx_thr": adx_thr,
                                                    "adx_bear_cap": adx_cap,
                                                    "rsi_rev_cap": rsi_cap,
                                                    "vol_ratio_hi": vr_hi,
                                                    "vol_cap": vcap,
                                                    "half_life": hl,
                                                    "quant_step": 0.05,
                                                },
                                                tc_bps=1.0,
                                            )
                                        )
    return specs


def weights_from_policy(spec: PolicySpec, df: pd.DataFrame) -> np.ndarray:
    n = len(df)
    if spec.family == "A_static":
        return np.full(n, float(spec.params["w1_const"]), dtype=float)

    if spec.family == "B_risk_parity":
        w = int(spec.params["window"])
        arr = df[f"w_rp_{w}"].to_numpy(dtype=float)
        return np.clip(np.nan_to_num(arr, nan=0.5), 0.0, 1.0)

    if spec.family == "C_dynamic":
        p = spec.params
        base = df["w_rp_60"].to_numpy(dtype=float)
        dd1 = df["dd1_lag"].to_numpy(dtype=float)
        vr = df["vol_ratio_60_lag"].to_numpy(dtype=float)
        bear = df["trend4h_bear_lag"].to_numpy(dtype=int) > 0
        adx = df["adx_lag"].to_numpy(dtype=float)
        rsi_rev = df["rsi_overbought_reversal_lag"].to_numpy(dtype=int) > 0

        cap = np.ones(n, dtype=float)
        cap = np.where(dd1 <= p["dd_mid"], np.minimum(cap, p["cap_mid"]), cap)
        cap = np.where(dd1 <= p["dd_deep"], np.minimum(cap, p["cap_deep"]), cap)
        cap = np.where(bear, np.minimum(cap, p["bearish_cap"]), cap)
        cap = np.where(bear & (adx >= p["adx_thr"]), np.minimum(cap, p["adx_bear_cap"]), cap)
        cap = np.where(rsi_rev, np.minimum(cap, p["rsi_rev_cap"]), cap)
        cap = np.where(vr >= p["vol_ratio_hi"], np.minimum(cap, p["vol_cap"]), cap)

        w_raw = np.minimum(base, cap)
        w_raw = np.clip(np.nan_to_num(w_raw, nan=0.5), 0.0, 1.0)

        w_sm = pd.Series(w_raw).ewm(halflife=int(p["half_life"]), adjust=False).mean().to_numpy(dtype=float)
        q = float(p["quant_step"])
        w_q = np.round(w_sm / q) * q
        return np.clip(np.nan_to_num(w_q, nan=0.5), 0.0, 1.0)

    raise ValueError(f"Unknown policy family: {spec.family}")


def get_segment_bounds(seg: str, split_idx: int, n: int) -> tuple[int, int]:
    if seg == "train":
        return 0, split_idx
    if seg == "val":
        return split_idx, n
    if seg == "full":
        return 0, n
    raise ValueError(f"Unknown segment: {seg}")


def compute_portfolio_stats(rp: np.ndarray, ts: np.ndarray) -> dict[str, float]:
    if len(rp) == 0:
        return {
            "q1_p": np.nan,
            "q5_p": np.nan,
            "p_tail_1pct": np.nan,
            "p_tail_5pct": np.nan,
            "cvar_1pct": np.nan,
            "cvar_5pct": np.nan,
            "final_equity": np.nan,
            "total_return_pct": np.nan,
            "cagr_pct": np.nan,
            "mdd_pct": np.nan,
            "calmar": np.nan,
        }

    q1 = float(np.quantile(rp, 0.01))
    q5 = float(np.quantile(rp, 0.05))
    tail1 = rp[rp <= q1]
    tail5 = rp[rp <= q5]

    p1 = float((rp <= q1).mean())
    p5 = float((rp <= q5).mean())
    cvar1 = float(tail1.mean()) if len(tail1) else np.nan
    cvar5 = float(tail5.mean()) if len(tail5) else np.nan

    eq = np.cumprod(1.0 + rp, dtype=float)
    final_eq = float(eq[-1])
    ret_pct = (final_eq - 1.0) * 100.0

    elapsed_sec = float((ts[-1] - ts[0]) / np.timedelta64(1, "s")) if len(ts) > 1 else 0.0
    years = max(elapsed_sec / (365.25 * 24 * 3600), 1e-9)
    cagr_pct = (final_eq ** (1.0 / years) - 1.0) * 100.0

    running_max = np.maximum.accumulate(eq)
    dd = eq / np.maximum(running_max, 1e-12) - 1.0
    mdd_pct = abs(float(dd.min())) * 100.0
    calmar = (cagr_pct / mdd_pct) if mdd_pct > 0 else np.nan

    return {
        "q1_p": q1,
        "q5_p": q5,
        "p_tail_1pct": p1,
        "p_tail_5pct": p5,
        "cvar_1pct": cvar1,
        "cvar_5pct": cvar5,
        "final_equity": final_eq,
        "total_return_pct": ret_pct,
        "cagr_pct": cagr_pct,
        "mdd_pct": mdd_pct,
        "calmar": calmar,
    }


def compute_event_damage_metrics(
    rp_full: np.ndarray,
    windows: list[tuple[int, int]],
    seg_start: int,
    seg_end_exclusive: int,
) -> dict[str, float]:
    seg_end = seg_end_exclusive - 1
    event_returns: list[float] = []
    event_worst_dds: list[float] = []
    event_loss_count = 0
    bar_count = 0
    neg_bar_count = 0

    for s, e in windows:
        ss = max(s, seg_start)
        ee = min(e, seg_end)
        if ss > ee:
            continue

        arr = rp_full[ss : ee + 1]
        if len(arr) == 0:
            continue

        cum = np.cumprod(1.0 + arr, dtype=float)
        evt_ret = float(cum[-1] - 1.0)
        run_max = np.maximum.accumulate(cum)
        evt_dd = float((cum / np.maximum(run_max, 1e-12) - 1.0).min())

        event_returns.append(evt_ret)
        event_worst_dds.append(evt_dd)
        if evt_ret < 0:
            event_loss_count += 1

        bar_count += len(arr)
        neg_bar_count += int((arr < 0).sum())

    n_evt = len(event_returns)
    return {
        "event_count": float(n_evt),
        "event_mean_return": float(np.mean(event_returns)) if n_evt else np.nan,
        "event_worst_return": float(np.min(event_returns)) if n_evt else np.nan,
        "event_loss_pct": (event_loss_count / n_evt) if n_evt else np.nan,
        "event_bar_neg_pct": (neg_bar_count / bar_count) if bar_count > 0 else np.nan,
        "event_mean_worst_dd": float(np.mean(event_worst_dds)) if n_evt else np.nan,
        "event_worst_dd_min": float(np.min(event_worst_dds)) if n_evt else np.nan,
    }


def evaluate_policy(
    spec: PolicySpec,
    w1_full: np.ndarray,
    df: pd.DataFrame,
    windows: list[tuple[int, int]],
    split_idx: int,
    segment: str,
) -> dict[str, Any]:
    n = len(df)
    s0, s1 = get_segment_bounds(segment, split_idx, n)

    r1 = df["r1"].to_numpy(dtype=float)
    r2 = df["r2"].to_numpy(dtype=float)
    ts = df["timestamp"].to_numpy()

    w1 = np.clip(np.nan_to_num(w1_full, nan=0.5), 0.0, 1.0)
    w2 = 1.0 - w1
    turn = np.abs(np.diff(w1, prepend=w1[0]))
    tc_rate = float(spec.tc_bps) * 1e-4

    rp_full = (w1 * r1) + (w2 * r2) - (tc_rate * turn)
    rp = rp_full[s0:s1]
    ts_seg = ts[s0:s1]
    turn_seg = turn[s0:s1]

    pstats = compute_portfolio_stats(rp, ts_seg)
    estats = compute_event_damage_metrics(rp_full, windows, s0, s1)

    row: dict[str, Any] = {
        "policy_name": spec.name,
        "family": spec.family,
        "segment": segment,
        "tc_bps": float(spec.tc_bps),
        "turnover_mean": float(turn_seg.mean()) if len(turn_seg) else np.nan,
        "turnover_total": float(turn_seg.sum()) if len(turn_seg) else np.nan,
        **pstats,
        **estats,
    }

    # Strict-order sorting helpers (smaller is better).
    row["cvar1_loss"] = -row["cvar_1pct"] if pd.notna(row["cvar_1pct"]) else np.nan
    row["cvar5_loss"] = -row["cvar_5pct"] if pd.notna(row["cvar_5pct"]) else np.nan
    row["event_worst_loss"] = -row["event_worst_return"] if pd.notna(row["event_worst_return"]) else np.nan
    return row


def sort_strict_priority(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "cvar1_loss",
        "cvar5_loss",
        "event_worst_loss",
        "mdd_pct",
        "policy_name",
    ]
    return df.sort_values(cols, ascending=[True, True, True, True, True]).reset_index(drop=True)


def select_top_with_cagr_constraint(df_val: pd.DataFrame, cagr_floor: float, topn: int = TOPN) -> tuple[pd.DataFrame, bool]:
    feasible = df_val[df_val["cagr_pct"] >= cagr_floor].copy()
    if len(feasible) == 0:
        return sort_strict_priority(df_val).head(topn).copy(), False
    return sort_strict_priority(feasible).head(topn).copy(), True


def pick_best_name(top_df: pd.DataFrame) -> str:
    return str(top_df.iloc[0]["policy_name"])


def run():
    curves, events = load_inputs()
    market_feats = build_market_features(curves)
    base = build_base_df(curves, market_feats)
    df = base["df"]
    split_idx = int(base["split_idx"])
    ts = df["timestamp"].to_numpy()
    windows = build_event_windows(ts, events)

    specs_a = build_static_specs()
    specs_b = build_risk_parity_specs()
    specs_c = build_dynamic_specs()

    # 1) Dynamic train search (walk-forward).
    dyn_train_rows: list[dict[str, Any]] = []
    for spec in specs_c:
        w = weights_from_policy(spec, df)
        dyn_train_rows.append(evaluate_policy(spec, w, df, windows, split_idx, "train"))
    dyn_train_df = sort_strict_priority(pd.DataFrame(dyn_train_rows))
    dyn_train_df.to_csv(OUT_DYNAMIC_TRAIN, index=False)

    dyn_train_feasible = dyn_train_df[dyn_train_df["cagr_pct"] >= 80.0].copy()
    if len(dyn_train_feasible) == 0:
        dyn_selected = dyn_train_df.head(TOP_DYNAMIC_FROM_TRAIN)
    else:
        dyn_selected = sort_strict_priority(dyn_train_feasible).head(TOP_DYNAMIC_FROM_TRAIN)
    selected_names = set(dyn_selected["policy_name"].tolist())
    specs_c_selected = [s for s in specs_c if s.name in selected_names]

    # 2) Validation evaluation.
    all_specs = specs_a + specs_b + specs_c_selected
    val_rows: list[dict[str, Any]] = []
    spec_map: dict[str, PolicySpec] = {}
    for spec in all_specs:
        w = weights_from_policy(spec, df)
        val_rows.append(evaluate_policy(spec, w, df, windows, split_idx, "val"))
        spec_map[spec.name] = spec

    val_df = sort_strict_priority(pd.DataFrame(val_rows))
    val_df.to_csv(OUT_VAL_ALL, index=False)

    top80, feasible80 = select_top_with_cagr_constraint(val_df, 80.0, topn=TOPN)
    top100, feasible100 = select_top_with_cagr_constraint(val_df, 100.0, topn=TOPN)
    top80.to_csv(OUT_TOP15_80, index=False)
    top100.to_csv(OUT_TOP15_100, index=False)

    best_name = pick_best_name(top80)
    best_spec = spec_map[best_name]
    best_w1 = weights_from_policy(best_spec, df)
    best_weights_df = pd.DataFrame(
        {
            "timestamp": df["timestamp"],
            "w1_case1": best_w1,
            "w2_case2": 1.0 - best_w1,
            "policy_name": best_name,
        }
    )
    best_weights_df.to_csv(OUT_BEST_WEIGHTS, index=False)

    # 3) Before/after comparison table.
    compare_names = [
        "A_static_w1_1.00",  # case1 only
        "A_static_w1_0.00",  # case2 only
        "A_static_w1_0.50",  # 50/50
        best_name,           # best policy
    ]
    compare_rows = []
    for nm in compare_names:
        row = val_df[val_df["policy_name"] == nm]
        if row.empty:
            continue
        r = row.iloc[0].to_dict()
        label = {
            "A_static_w1_1.00": "Case1 only",
            "A_static_w1_0.00": "Case2 only",
            "A_static_w1_0.50": "50/50 mix",
        }.get(nm, "Best policy")
        r["label"] = label
        compare_rows.append(r)
    compare_df = pd.DataFrame(compare_rows)
    compare_cols = [
        "label",
        "policy_name",
        "family",
        "p_tail_1pct",
        "p_tail_5pct",
        "cvar_1pct",
        "cvar_5pct",
        "event_mean_return",
        "event_worst_return",
        "event_loss_pct",
        "event_bar_neg_pct",
        "mdd_pct",
        "cagr_pct",
        "calmar",
        "turnover_mean",
    ]
    compare_df[compare_cols].to_csv(OUT_COMPARE, index=False)

    # 4) Report (Korean).
    show_cols = [
        "policy_name",
        "family",
        "tc_bps",
        "p_tail_1pct",
        "p_tail_5pct",
        "cvar_1pct",
        "cvar_5pct",
        "event_worst_return",
        "event_mean_return",
        "event_loss_pct",
        "event_bar_neg_pct",
        "mdd_pct",
        "cagr_pct",
        "calmar",
        "turnover_mean",
    ]

    lines: list[str] = []
    lines.append("# Step2-A 재실행 (포트폴리오 Tail 기준)")
    lines.append("")
    lines.append("## 설정")
    lines.append(f"- 입력 곡선: `{INPUT_CURVES}`")
    lines.append(f"- 이벤트 윈도우: `{INPUT_EVENTS}`")
    lines.append("- 포트폴리오 수익률: `r_p(t)=w1(t)*r1(t)+(1-w1(t))*r2(t)`")
    lines.append("- 워크포워드: 앞 70% train / 뒤 30% validation")
    lines.append("- 정책군:")
    lines.append("  - A) Static (`w1=0~1`, step 0.02)")
    lines.append("  - B) Vol 기반 risk-parity (`30/60/120`)")
    lines.append("  - C) Regime dynamic (`dd1`, `실현변동성`, `4h trend`, `ADX`, `RSI 과매수 반전`) + 히스테리시스 + turnover 페널티")
    lines.append("")
    lines.append("## 엄격 우선순위")
    lines.append("1. `CVaR_1%` 최소화")
    lines.append("2. `CVaR_5%` 최소화")
    lines.append("3. 상승→급락 이벤트 `worst event return` 손실 최소화")
    lines.append("4. `MDD` 최소화")
    lines.append("5. CAGR 제약 (`>=80%`, `>=100%`)")
    lines.append("")

    lines.append("## Validation Top15 (CAGR >= 80%)")
    lines.extend(_to_md_table(top80[show_cols]))
    lines.append("")
    lines.append(f"- CAGR>=80% feasible: `{feasible80}`")
    lines.append("")

    lines.append("## Validation Top15 (CAGR >= 100%)")
    lines.extend(_to_md_table(top100[show_cols]))
    lines.append("")
    lines.append(f"- CAGR>=100% feasible: `{feasible100}`")
    lines.append("")

    lines.append("## Before/After 비교 (Validation)")
    lines.extend(_to_md_table(compare_df[compare_cols]))
    lines.append("")

    lines.append("## Best 정책 요약")
    best_row = top80.iloc[0]
    lines.append(f"- Best policy: `{best_name}` (`{best_row['family']}`)")
    lines.append(f"- CVaR_1%: `{_fmt(best_row['cvar_1pct'])}`")
    lines.append(f"- CVaR_5%: `{_fmt(best_row['cvar_5pct'])}`")
    lines.append(f"- 이벤트 worst return: `{_fmt(best_row['event_worst_return'])}`")
    lines.append(f"- MDD: `{_fmt(best_row['mdd_pct'])}%`, CAGR: `{_fmt(best_row['cagr_pct'])}%`")
    lines.append(f"- weight 시계열: `{OUT_BEST_WEIGHTS}`")
    lines.append("")
    lines.append("### 왜 tail risk가 줄어드는가")
    if best_spec.family == "A_static":
        lines.append("- 고정 비중으로 더 안정적인 전략 쪽에 자본을 집중해 좌측 꼬리 손실을 줄입니다.")
    elif best_spec.family == "B_risk_parity":
        lines.append("- 실현 변동성이 높은 쪽 비중을 자동 축소해 tail 구간의 손실 크기를 완화합니다.")
    else:
        p = best_spec.params
        lines.append("- DD/추세/ADX/RSI 반전 조건에서 Case1 비중 상한을 낮춰 급락 민감 구간 노출을 줄입니다.")
        lines.append(f"- 핵심 임계값: dd_mid={p['dd_mid']}, dd_deep={p['dd_deep']}, bear_cap={p['bearish_cap']}, adx_cap={p['adx_bear_cap']}")
    lines.append("")
    lines.append("### 관찰된 트레이드오프")
    lines.append("- tail 방어를 강화할수록 상승장 참여율이 낮아져 CAGR이 줄어들 수 있습니다.")
    lines.append("- turnover penalty를 넣으면 과도한 비중 변경은 줄지만 단기 반응성도 일부 둔화됩니다.")
    lines.append("")

    lines.append("## 산출물")
    lines.append(f"- dynamic train: `{OUT_DYNAMIC_TRAIN}`")
    lines.append(f"- validation all: `{OUT_VAL_ALL}`")
    lines.append(f"- top15 (>=80): `{OUT_TOP15_80}`")
    lines.append(f"- top15 (>=100): `{OUT_TOP15_100}`")
    lines.append(f"- baseline compare: `{OUT_COMPARE}`")
    lines.append(f"- best weights: `{OUT_BEST_WEIGHTS}`")
    lines.append(f"- report: `{OUT_REPORT}`")

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"saved_dynamic_train={OUT_DYNAMIC_TRAIN}")
    print(f"saved_validation_all={OUT_VAL_ALL}")
    print(f"saved_top15_80={OUT_TOP15_80}")
    print(f"saved_top15_100={OUT_TOP15_100}")
    print(f"saved_compare={OUT_COMPARE}")
    print(f"saved_best_weights={OUT_BEST_WEIGHTS}")
    print(f"saved_report={OUT_REPORT}")
    print(
        f"best_policy={best_name}, "
        f"cvar1={_fmt(best_row['cvar_1pct'])}, "
        f"cvar5={_fmt(best_row['cvar_5pct'])}, "
        f"mdd={_fmt(best_row['mdd_pct'])}%, "
        f"cagr={_fmt(best_row['cagr_pct'])}%"
    )


if __name__ == "__main__":
    run()
