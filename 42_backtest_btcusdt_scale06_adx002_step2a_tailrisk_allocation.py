from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


INPUT_CURVES = Path("42_backtest_btcusdt_scale06_adx002_equity_combo_curves.csv")
INPUT_RISE_CRASH = Path("42_backtest_btcusdt_scale06_adx002_structural_offset_step1_rise_crash_events.csv")

OUT_BASE = "42_backtest_btcusdt_scale06_adx002_step2a_tailrisk_allocation"
OUT_ALL_VAL = Path(f"{OUT_BASE}_all_policies_val.csv")
OUT_DYNAMIC_TRAIN = Path(f"{OUT_BASE}_dynamic_train.csv")
OUT_TOP10_CAGR80 = Path(f"{OUT_BASE}_top10_cagr80.csv")
OUT_TOP10_CAGR100 = Path(f"{OUT_BASE}_top10_cagr100.csv")
OUT_BEST_WEIGHTS = Path(f"{OUT_BASE}_best_policy_weights.csv")
OUT_REPORT = Path(f"{OUT_BASE}.md")

STATIC_W_STEP = 0.02
RISK_PARITY_WINDOWS = [30, 60, 120]
TAIL_QS = [0.01, 0.05]
TRAIN_RATIO = 0.70


@dataclass(frozen=True)
class PolicySpec:
    family: str
    name: str
    params: dict[str, Any]
    tc_bps: float = 0.0


def _fmt(v, digits: int = 6) -> str:
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


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not INPUT_CURVES.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_CURVES}")
    if not INPUT_RISE_CRASH.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_RISE_CRASH}")

    curves = pd.read_csv(INPUT_CURVES, parse_dates=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    need = {"timestamp", "equity_case1", "equity_case2"}
    miss = need - set(curves.columns)
    if miss:
        raise ValueError(f"Missing columns in curves: {sorted(miss)}")

    events = pd.read_csv(INPUT_RISE_CRASH, parse_dates=["drop_start", "drop_end"]).sort_values("drop_start").reset_index(drop=True)
    return curves, events


def build_base_series(curves: pd.DataFrame) -> dict[str, Any]:
    df = curves.copy()
    df["r1"] = df["equity_case1"].pct_change().fillna(0.0)
    df["r2"] = df["equity_case2"].pct_change().fillna(0.0)
    df["dd1"] = df["equity_case1"] / df["equity_case1"].cummax() - 1.0
    df["dd1_lag"] = df["dd1"].shift(1).fillna(0.0)

    for w in RISK_PARITY_WINDOWS:
        v1 = df["r1"].rolling(w).std(ddof=0).shift(1)
        v2 = df["r2"].rolling(w).std(ddof=0).shift(1)
        v1 = v1.replace([np.inf, -np.inf], np.nan).fillna(v1.median())
        v2 = v2.replace([np.inf, -np.inf], np.nan).fillna(v2.median())
        df[f"vol1_{w}"] = v1
        df[f"vol2_{w}"] = v2

        inv1 = 1.0 / np.maximum(v1.to_numpy(dtype=float), 1e-12)
        inv2 = 1.0 / np.maximum(v2.to_numpy(dtype=float), 1e-12)
        w1 = inv1 / np.maximum(inv1 + inv2, 1e-12)
        w1 = np.clip(np.nan_to_num(w1, nan=0.5), 0.0, 1.0)
        df[f"w_rp_{w}"] = w1

    df["vol_ratio_60"] = df["vol1_60"] / np.maximum(df["vol2_60"], 1e-12)
    df["vol_ratio_60"] = df["vol_ratio_60"].replace([np.inf, -np.inf], np.nan).fillna(1.0)

    ts = df["timestamp"].to_numpy()
    r1 = df["r1"].to_numpy(dtype=float)
    r2 = df["r2"].to_numpy(dtype=float)

    n = len(df)
    split_idx = int(n * TRAIN_RATIO)
    split_idx = min(max(split_idx, 1), n - 1)

    neg1 = df.loc[df["r1"] < 0.0, "r1"]
    neg2 = df.loc[df["r2"] < 0.0, "r2"]
    tail_thresholds = {}
    for q in TAIL_QS:
        tail_thresholds[q] = (
            float(neg1.quantile(q)) if len(neg1) else np.nan,
            float(neg2.quantile(q)) if len(neg2) else np.nan,
        )

    return {
        "df": df,
        "ts": ts,
        "r1": r1,
        "r2": r2,
        "split_idx": split_idx,
        "tail_thresholds": tail_thresholds,
    }


def build_event_windows(ts: np.ndarray, events: pd.DataFrame) -> list[tuple[int, int]]:
    windows: list[tuple[int, int]] = []
    for _, row in events.iterrows():
        s_raw = np.datetime64(row["drop_start"].to_datetime64())
        e_raw = np.datetime64(row["drop_end"].to_datetime64())
        s = int(np.searchsorted(ts, s_raw, side="left"))
        e = int(np.searchsorted(ts, e_raw, side="right")) - 1
        if e < s:
            continue
        if s >= len(ts):
            continue
        s = max(0, s)
        e = min(len(ts) - 1, e)
        if s <= e:
            windows.append((s, e))
    return windows


def segment_mask(n: int, seg: str, split_idx: int) -> np.ndarray:
    mask = np.zeros(n, dtype=bool)
    if seg == "train":
        mask[:split_idx] = True
    elif seg == "val":
        mask[split_idx:] = True
    elif seg == "full":
        mask[:] = True
    else:
        raise ValueError(f"Unknown segment: {seg}")
    return mask


def compute_tail_metrics_for_segment(
    r1: np.ndarray,
    r2: np.ndarray,
    seg_mask: np.ndarray,
    tail_thresholds: dict[float, tuple[float, float]],
) -> dict[str, float]:
    out: dict[str, float] = {}
    x1 = r1[seg_mask]
    x2 = r2[seg_mask]
    for q in TAIL_QS:
        t1, t2 = tail_thresholds[q]
        e1 = x1 <= t1
        e2 = x2 <= t2
        p1 = float(e1.mean()) if len(e1) else np.nan
        p2 = float(e2.mean()) if len(e2) else np.nan
        pj = float((e1 & e2).mean()) if len(e1) else np.nan
        pind = p1 * p2 if pd.notna(p1) and pd.notna(p2) else np.nan
        lift = (pj / pind) if (pd.notna(pj) and pd.notna(pind) and pind > 0) else np.nan
        p2_given1 = (float((e1 & e2).sum()) / float(e1.sum())) if e1.sum() > 0 else np.nan

        key = str(int(q * 100))
        out[f"joint_p_q{key}"] = pj
        out[f"joint_ind_q{key}"] = pind
        out[f"joint_lift_q{key}"] = lift
        out[f"p_r2_tail_given_r1_tail_q{key}"] = p2_given1
    return out


def compute_rise_crash_metrics_for_segment(
    both_loss: np.ndarray,
    windows: list[tuple[int, int]],
    seg_start: int,
    seg_end_exclusive: int,
) -> dict[str, float]:
    total_bars = 0
    both_bars = 0
    event_cnt = 0
    event_joint_cnt = 0

    seg_end = seg_end_exclusive - 1
    for s, e in windows:
        ss = max(s, seg_start)
        ee = min(e, seg_end)
        if ss > ee:
            continue
        event_cnt += 1
        part = both_loss[ss : ee + 1]
        total_bars += int(len(part))
        c = int(part.sum())
        both_bars += c
        if c > 0:
            event_joint_cnt += 1

    both_ratio = (both_bars / total_bars) if total_bars > 0 else np.nan
    event_freq = (event_joint_cnt / event_cnt) if event_cnt > 0 else np.nan
    return {
        "rise_crash_both_loss_ratio": both_ratio,
        "rise_crash_event_joint_loss_freq": event_freq,
        "rise_crash_event_count": float(event_cnt),
        "rise_crash_bars": float(total_bars),
    }


def portfolio_metrics_from_returns(rp: np.ndarray, ts: np.ndarray) -> dict[str, float]:
    if len(rp) == 0:
        return {
            "final_equity": np.nan,
            "total_return_pct": np.nan,
            "cagr_pct": np.nan,
            "mdd_pct": np.nan,
            "calmar": np.nan,
        }

    eq = np.cumprod(1.0 + rp, dtype=float)
    final_eq = float(eq[-1])
    total_return_pct = (final_eq - 1.0) * 100.0

    elapsed_sec = float((ts[-1] - ts[0]) / np.timedelta64(1, "s")) if len(ts) > 1 else 0.0
    years = max(elapsed_sec / (365.25 * 24.0 * 3600.0), 1e-9)
    cagr_pct = (final_eq ** (1.0 / years) - 1.0) * 100.0

    running_max = np.maximum.accumulate(eq)
    dd = eq / np.maximum(running_max, 1e-12) - 1.0
    mdd_pct = abs(float(dd.min())) * 100.0 if len(dd) else np.nan
    calmar = (cagr_pct / mdd_pct) if (pd.notna(cagr_pct) and pd.notna(mdd_pct) and mdd_pct > 0) else np.nan

    return {
        "final_equity": final_eq,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "mdd_pct": mdd_pct,
        "calmar": calmar,
    }


def build_static_specs() -> list[PolicySpec]:
    weights = np.round(np.arange(0.0, 1.0 + 1e-12, STATIC_W_STEP), 2)
    specs = []
    for w in weights:
        specs.append(
            PolicySpec(
                family="A_static",
                name=f"A_static_w1_{w:.2f}",
                params={"w1_const": float(w)},
                tc_bps=0.0,
            )
        )
    return specs


def build_risk_parity_specs() -> list[PolicySpec]:
    specs = []
    for w in RISK_PARITY_WINDOWS:
        specs.append(
            PolicySpec(
                family="B_risk_parity",
                name=f"B_riskparity_vol{w}",
                params={"window": int(w)},
                tc_bps=0.0,
            )
        )
    return specs


def build_dynamic_candidate_specs() -> list[PolicySpec]:
    specs: list[PolicySpec] = []
    dd_mid_list = [-0.08, -0.10, -0.12]
    dd_deep_list = [-0.16, -0.20]
    w_mid_list = [0.35, 0.45]
    w_deep_list = [0.15, 0.25]
    vol_ratio_hi_list = [1.20, 1.35]
    half_life_list = [30, 60]

    for dd_mid in dd_mid_list:
        for dd_deep in dd_deep_list:
            for w_mid in w_mid_list:
                for w_deep in w_deep_list:
                    for vr_hi in vol_ratio_hi_list:
                        for hl in half_life_list:
                            name = (
                                "C_dyn"
                                f"_ddm{abs(dd_mid):.2f}"
                                f"_ddd{abs(dd_deep):.2f}"
                                f"_wm{w_mid:.2f}"
                                f"_wd{w_deep:.2f}"
                                f"_vr{vr_hi:.2f}"
                                f"_hl{hl}"
                            )
                            specs.append(
                                PolicySpec(
                                    family="C_dynamic",
                                    name=name,
                                    params={
                                        "dd_mid": float(dd_mid),
                                        "dd_deep": float(dd_deep),
                                        "w_mid": float(w_mid),
                                        "w_deep": float(w_deep),
                                        "vol_ratio_hi": float(vr_hi),
                                        "half_life": int(hl),
                                        "quant_step": 0.05,
                                        "vol_cap": 0.40,
                                    },
                                    tc_bps=0.0,
                                )
                            )
    return specs


def weights_from_policy(spec: PolicySpec, base_df: pd.DataFrame) -> np.ndarray:
    n = len(base_df)
    if spec.family == "A_static":
        w = float(spec.params["w1_const"])
        return np.full(n, w, dtype=float)

    if spec.family == "B_risk_parity":
        w = int(spec.params["window"])
        arr = base_df[f"w_rp_{w}"].to_numpy(dtype=float)
        return np.clip(np.nan_to_num(arr, nan=0.5), 0.0, 1.0)

    if spec.family == "C_dynamic":
        dd_mid = float(spec.params["dd_mid"])
        dd_deep = float(spec.params["dd_deep"])
        w_mid = float(spec.params["w_mid"])
        w_deep = float(spec.params["w_deep"])
        vr_hi = float(spec.params["vol_ratio_hi"])
        vol_cap = float(spec.params["vol_cap"])
        hl = int(spec.params["half_life"])
        q_step = float(spec.params["quant_step"])

        dd1 = base_df["dd1_lag"].to_numpy(dtype=float)
        vr = base_df["vol_ratio_60"].to_numpy(dtype=float)
        base_w = base_df["w_rp_60"].to_numpy(dtype=float)

        w_raw = np.where(dd1 <= dd_deep, w_deep, np.where(dd1 <= dd_mid, w_mid, base_w))
        w_raw = np.where(vr >= vr_hi, np.minimum(w_raw, vol_cap), w_raw)
        w_raw = np.where(vr <= (1.0 / vr_hi), np.maximum(w_raw, 1.0 - vol_cap), w_raw)
        w_raw = np.clip(np.nan_to_num(w_raw, nan=0.5), 0.0, 1.0)

        w_sm = pd.Series(w_raw).ewm(halflife=hl, adjust=False).mean().to_numpy(dtype=float)
        w_q = np.round(w_sm / q_step) * q_step
        return np.clip(np.nan_to_num(w_q, nan=0.5), 0.0, 1.0)

    raise ValueError(f"Unknown policy family: {spec.family}")


def evaluate_policy_on_segment(
    spec: PolicySpec,
    w1_full: np.ndarray,
    base: dict[str, Any],
    seg: str,
    seg_tail_metrics: dict[str, float],
    seg_rise_metrics: dict[str, float],
    joint_masks_by_q: dict[float, np.ndarray],
) -> dict[str, Any]:
    ts = base["ts"]
    r1 = base["r1"]
    r2 = base["r2"]
    n = len(ts)
    split_idx = int(base["split_idx"])

    mask = segment_mask(n, seg, split_idx)
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return {}

    w1 = np.clip(np.nan_to_num(w1_full, nan=0.5), 0.0, 1.0)
    dw = np.diff(w1, prepend=w1[0])
    turnover = np.abs(dw)

    tc_rate = float(spec.tc_bps) * 1e-4
    rp_full = w1 * r1 + (1.0 - w1) * r2 - tc_rate * turnover
    rp = rp_full[idx]
    ts_seg = ts[idx]

    pm = portfolio_metrics_from_returns(rp, ts_seg)

    row: dict[str, Any] = {
        "policy_name": spec.name,
        "family": spec.family,
        "segment": seg,
        "tc_bps": float(spec.tc_bps),
        "turnover_mean": float(turnover[idx].mean()),
        "turnover_total": float(turnover[idx].sum()),
        **pm,
        **seg_tail_metrics,
        **seg_rise_metrics,
    }

    # Tie-breaker metrics: portfolio downside magnitude during strategy joint-tail bars.
    for q in TAIL_QS:
        key = str(int(q * 100))
        jmask = joint_masks_by_q[q][idx]
        if jmask.sum() > 0:
            jret = rp[jmask]
            row[f"joint_tail_port_mean_q{key}"] = float(jret.mean())
            row[f"joint_tail_port_p10_q{key}"] = float(np.quantile(jret, 0.10))
        else:
            row[f"joint_tail_port_mean_q{key}"] = np.nan
            row[f"joint_tail_port_p10_q{key}"] = np.nan

    return row


def sort_by_priority(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "joint_p_q1",
        "joint_lift_q1",
        "joint_p_q5",
        "joint_lift_q5",
        "rise_crash_both_loss_ratio",
        "rise_crash_event_joint_loss_freq",
        "joint_tail_port_mean_q1",
        "joint_tail_port_mean_q5",
        "mdd_pct",
        "turnover_mean",
        "policy_name",
    ]
    ascending = [True, True, True, True, True, True, False, False, True, True, True]
    return df.sort_values(cols, ascending=ascending).reset_index(drop=True)


def pick_top_by_cagr_constraint(df_val: pd.DataFrame, cagr_floor: float, topn: int = 10) -> tuple[pd.DataFrame, bool]:
    feasible = df_val[df_val["cagr_pct"] >= cagr_floor].copy()
    if len(feasible) == 0:
        return sort_by_priority(df_val).head(topn).copy(), False
    return sort_by_priority(feasible).head(topn).copy(), True


def get_seg_bounds(seg: str, split_idx: int, n: int) -> tuple[int, int]:
    if seg == "train":
        return 0, split_idx
    if seg == "val":
        return split_idx, n
    if seg == "full":
        return 0, n
    raise ValueError(f"Unknown segment: {seg}")


def run():
    curves, events = load_data()
    base = build_base_series(curves)
    df = base["df"]
    ts = base["ts"]
    r1 = base["r1"]
    r2 = base["r2"]
    n = len(df)
    split_idx = int(base["split_idx"])

    windows = build_event_windows(ts, events)
    both_loss = (r1 < 0.0) & (r2 < 0.0)

    tail_metrics_seg = {}
    rise_metrics_seg = {}
    joint_masks_by_q = {}
    for q in TAIL_QS:
        t1, t2 = base["tail_thresholds"][q]
        joint_masks_by_q[q] = (r1 <= t1) & (r2 <= t2)

    for seg in ["train", "val", "full"]:
        m = segment_mask(n, seg, split_idx)
        tail_metrics_seg[seg] = compute_tail_metrics_for_segment(r1, r2, m, base["tail_thresholds"])
        s0, s1 = get_seg_bounds(seg, split_idx, n)
        rise_metrics_seg[seg] = compute_rise_crash_metrics_for_segment(both_loss, windows, s0, s1)

    # A/B 정책 전체 + C 후보 생성
    specs_a = build_static_specs()
    specs_b = build_risk_parity_specs()
    dyn_candidates = build_dynamic_candidate_specs()

    # C 후보는 train 구간으로 먼저 선별
    dyn_train_rows: list[dict[str, Any]] = []
    for spec in dyn_candidates:
        w1 = weights_from_policy(spec, df)
        row = evaluate_policy_on_segment(
            spec=spec,
            w1_full=w1,
            base=base,
            seg="train",
            seg_tail_metrics=tail_metrics_seg["train"],
            seg_rise_metrics=rise_metrics_seg["train"],
            joint_masks_by_q=joint_masks_by_q,
        )
        dyn_train_rows.append(row)

    dyn_train_df = pd.DataFrame(dyn_train_rows)
    dyn_train_df = sort_by_priority(dyn_train_df)
    dyn_train_df.to_csv(OUT_DYNAMIC_TRAIN, index=False)

    # 과적합 억제를 위해 dynamic은 train 상위만 validation으로 진행
    dyn_top = dyn_train_df[dyn_train_df["cagr_pct"] >= 80.0].head(12)
    if len(dyn_top) == 0:
        dyn_top = dyn_train_df.head(12)
    dyn_top_names = set(dyn_top["policy_name"].tolist())
    dyn_top_specs = [s for s in dyn_candidates if s.name in dyn_top_names]

    # dynamic에 turnover penalty 버전 추가 (tc-free + tc)
    dyn_eval_specs: list[PolicySpec] = []
    for s in dyn_top_specs:
        dyn_eval_specs.append(s)
        dyn_eval_specs.append(
            PolicySpec(
                family=s.family,
                name=f"{s.name}_tc5bps",
                params=s.params,
                tc_bps=5.0,
            )
        )

    final_specs = specs_a + specs_b + dyn_eval_specs

    # validation 성능 평가
    val_rows: list[dict[str, Any]] = []
    spec_map: dict[str, PolicySpec] = {}
    for spec in final_specs:
        w1 = weights_from_policy(spec, df)
        row = evaluate_policy_on_segment(
            spec=spec,
            w1_full=w1,
            base=base,
            seg="val",
            seg_tail_metrics=tail_metrics_seg["val"],
            seg_rise_metrics=rise_metrics_seg["val"],
            joint_masks_by_q=joint_masks_by_q,
        )
        val_rows.append(row)
        spec_map[spec.name] = spec

    val_df = pd.DataFrame(val_rows)
    val_df = sort_by_priority(val_df)
    val_df.to_csv(OUT_ALL_VAL, index=False)

    top80, feasible80 = pick_top_by_cagr_constraint(val_df, 80.0, topn=10)
    top100, feasible100 = pick_top_by_cagr_constraint(val_df, 100.0, topn=10)
    top80.to_csv(OUT_TOP10_CAGR80, index=False)
    top100.to_csv(OUT_TOP10_CAGR100, index=False)

    best = top80.iloc[0].to_dict()
    best_name = str(best["policy_name"])
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

    # 보고서 (한글)
    lines: list[str] = []
    lines.append("# Step2-A: Joint Tail Risk 최소화 목적의 Allocation 정책 탐색 (Study42)")
    lines.append("")
    lines.append("## 분석 설정")
    lines.append(f"- 입력 곡선: `{INPUT_CURVES}`")
    lines.append(f"- 상승후급락 이벤트: `{INPUT_RISE_CRASH}`")
    lines.append("- 포트폴리오 수익률: `r_p(t) = w1(t)*r1(t) + (1-w1(t))*r2(t)`")
    lines.append("- 워크포워드: 앞 70% train, 뒤 30% validation")
    lines.append("- 정책군:")
    lines.append("  - A) Static weight grid (`w1=0.00~1.00`, step 0.02)")
    lines.append("  - B) Risk parity (`vol window=30/60/120`)")
    lines.append("  - C) Regime dynamic (`dd1`, `vol ratio`, `hysteresis=EWM`, `quantized weights`) + `tc 5bps` 페널티 버전")
    lines.append("")
    lines.append("## 우선순위 목적함수 반영")
    lines.append("- 1순위/2순위 지표(`strategy tail joint`, `both-loss bar`)는 정의상 전략 수익률 기반이라 정책 간 값이 거의 동일합니다.")
    lines.append("- 따라서 실질 순위는 동일 1/2순위 동률 하에서, `joint-tail 구간의 포트폴리오 손실 강도`와 `MDD`를 중심으로 갈립니다.")
    lines.append("- CAGR 제약은 별도로 적용: `>=80%`, `>=100%` 두 버전 보고.")
    lines.append("")

    lines.append("## Validation Top10 (CAGR >= 80%)")
    show_cols = [
        "policy_name",
        "family",
        "tc_bps",
        "joint_p_q1",
        "joint_lift_q1",
        "joint_p_q5",
        "joint_lift_q5",
        "rise_crash_both_loss_ratio",
        "rise_crash_event_joint_loss_freq",
        "mdd_pct",
        "cagr_pct",
        "calmar",
        "turnover_mean",
    ]
    lines.extend(_to_md_table(top80[show_cols]))
    lines.append("")
    lines.append(f"- CAGR>=80% feasible 여부: `{feasible80}`")
    lines.append("")

    lines.append("## Validation Top10 (CAGR >= 100%)")
    lines.extend(_to_md_table(top100[show_cols]))
    lines.append("")
    lines.append(f"- CAGR>=100% feasible 여부: `{feasible100}`")
    lines.append("")

    lines.append("## Best 정책")
    lines.append(f"- 선택 기준: `CAGR>=80%` 제약 하 우선순위 정렬 1위")
    lines.append(f"- Best policy: `{best_name}`")
    lines.append(f"- Family: `{best.get('family')}`, tc_bps=`{_fmt(best.get('tc_bps'))}`")
    lines.append(f"- Validation CAGR: `{_fmt(best.get('cagr_pct'))}%`")
    lines.append(f"- Validation MDD: `{_fmt(best.get('mdd_pct'))}%`")
    lines.append(f"- Validation Calmar: `{_fmt(best.get('calmar'))}`")
    lines.append(f"- Weight 시계열: `{OUT_BEST_WEIGHTS}`")
    lines.append("")

    # 규칙 설명 텍스트
    if best_spec.family == "A_static":
        lines.append("### 규칙 설명")
        lines.append(f"- 고정 비중: `w1={_fmt(best_spec.params['w1_const'], 2)}`, `w2={_fmt(1.0-best_spec.params['w1_const'], 2)}`")
    elif best_spec.family == "B_risk_parity":
        lines.append("### 규칙 설명")
        lines.append(
            f"- Risk parity: `w1(t) ∝ 1/vol1(t)` with rolling window `{best_spec.params['window']}` (1-bar lag 적용)"
        )
    else:
        p = best_spec.params
        lines.append("### 규칙 설명")
        lines.append("- 기본: `w1`은 60분 risk-parity 비중 사용")
        lines.append(f"- DD 레짐: `dd1<= {p['dd_deep']}`이면 `w1={p['w_deep']}`, `dd1<= {p['dd_mid']}`이면 `w1={p['w_mid']}`")
        lines.append(f"- 변동성 레짐: `vol1/vol2 >= {p['vol_ratio_hi']}`이면 `w1` 상한 `{p['vol_cap']}`")
        lines.append(f"- 히스테리시스: `EWM half-life={p['half_life']}`")
        lines.append(f"- 빈번한 미세변경 억제: `0.05` 단위 양자화")
        if best_spec.tc_bps > 0:
            lines.append(f"- Turnover penalty: `{best_spec.tc_bps}` bps")
    lines.append("")

    lines.append("## 다음 정책 제안 (Step2-B)")
    lines.append("- 현재 정의(`w2=1-w1`, long-only)에서는 1/2순위 확률 지표가 정책에 거의 불변입니다.")
    lines.append("- 따라서 다음 단계는 `cash/risk-off` 허용(예: `w1+w2<1`) 또는 `hedge(음수 가중)` 허용 정책을 추가해,")
    lines.append("  동일한 tail joint 사건에서 포트폴리오 손실 자체를 줄이는 방향으로 확장하는 것을 권장합니다.")
    lines.append("- 우선 시도안: `DD+Vol gating` 기반으로 `총 익스포저 cap`을 레짐별로 1.0/0.7/0.4로 조절.")
    lines.append("")

    lines.append("## 산출물")
    lines.append(f"- Dynamic train ranking: `{OUT_DYNAMIC_TRAIN}`")
    lines.append(f"- Validation all policies: `{OUT_ALL_VAL}`")
    lines.append(f"- Top10 (CAGR>=80): `{OUT_TOP10_CAGR80}`")
    lines.append(f"- Top10 (CAGR>=100): `{OUT_TOP10_CAGR100}`")
    lines.append(f"- Best weights: `{OUT_BEST_WEIGHTS}`")
    lines.append(f"- Report: `{OUT_REPORT}`")
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"saved_dynamic_train={OUT_DYNAMIC_TRAIN}")
    print(f"saved_all_val={OUT_ALL_VAL}")
    print(f"saved_top80={OUT_TOP10_CAGR80}")
    print(f"saved_top100={OUT_TOP10_CAGR100}")
    print(f"saved_best_weights={OUT_BEST_WEIGHTS}")
    print(f"saved_report={OUT_REPORT}")
    print(
        f"best_policy={best_name}, "
        f"cagr={_fmt(best.get('cagr_pct'))}%, "
        f"mdd={_fmt(best.get('mdd_pct'))}%"
    )


if __name__ == "__main__":
    run()
