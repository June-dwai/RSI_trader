from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


INPUT_CURVES_CSV = Path("42_backtest_btcusdt_scale06_adx002_equity_combo_curves.csv")

OUT_BASE = "42_backtest_btcusdt_scale06_adx002_structural_offset_step1"
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_ROLLING_CSV = Path(f"{OUT_BASE}_rolling_corr.csv")
OUT_ROLLING_SUMMARY_CSV = Path(f"{OUT_BASE}_rolling_corr_summary.csv")
OUT_DD_CSV = Path(f"{OUT_BASE}_drawdown_conditional_corr.csv")
OUT_RISE_CRASH_CSV = Path(f"{OUT_BASE}_rise_crash_events.csv")
OUT_TAIL_CSV = Path(f"{OUT_BASE}_tail_joint_loss.csv")

ROLLING_WINDOWS = [30, 60, 120]
RISE_WINDOW = 720
DROP_WINDOW = 240
RISE_Q = 0.90
DROP_Q = 0.10
TAIL_QS = [0.01, 0.05]


def _fmt(v, digits: int = 6) -> str:
    if v is None:
        return "N/A"
    try:
        if pd.isna(v):
            return "N/A"
    except TypeError:
        pass
    return f"{float(v):.{digits}f}"


def _df_to_md_table(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["(empty)"]
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        vals = []
        for c in df.columns:
            v = row[c]
            if isinstance(v, float):
                vals.append(_fmt(v, 6))
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def load_curves(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    need_cols = {"timestamp", "equity_case1", "equity_case2"}
    miss = need_cols - set(df.columns)
    if miss:
        raise ValueError(f"Missing required columns: {sorted(miss)}")
    return df


def build_returns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret_case1"] = out["equity_case1"].pct_change()
    out["ret_case2"] = out["equity_case2"].pct_change()
    out["dd_case1"] = out["equity_case1"] / out["equity_case1"].cummax() - 1.0
    return out


def rolling_corr_analysis(df: pd.DataFrame, windows: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = df[["timestamp", "ret_case1", "ret_case2", "dd_case1"]].copy()
    rows: list[dict] = []

    for w in windows:
        col = f"corr_{w}"
        std1 = out["ret_case1"].rolling(w).std(ddof=0)
        std2 = out["ret_case2"].rolling(w).std(ddof=0)
        corr = out["ret_case1"].rolling(w).corr(out["ret_case2"])
        corr = corr.where((std1 > 1e-12) & (std2 > 1e-12)).clip(-1.0, 1.0)
        out[col] = corr
        s = out[col].dropna()
        rows.append(
            {
                "window": int(w),
                "count": int(s.shape[0]),
                "mean_corr": s.mean() if len(s) else np.nan,
                "median_corr": s.median() if len(s) else np.nan,
                "std_corr": s.std(ddof=0) if len(s) else np.nan,
                "p10_corr": s.quantile(0.10) if len(s) else np.nan,
                "p90_corr": s.quantile(0.90) if len(s) else np.nan,
                "min_corr": s.min() if len(s) else np.nan,
                "max_corr": s.max() if len(s) else np.nan,
                "neg_corr_share": (s < 0).mean() if len(s) else np.nan,
            }
        )
    summary = pd.DataFrame(rows).sort_values("window").reset_index(drop=True)
    return out, summary


def drawdown_conditional_corr(df: pd.DataFrame) -> pd.DataFrame:
    ret1 = df["ret_case1"]
    ret2 = df["ret_case2"]
    dd = df["dd_case1"]

    masks = {
        "all_bars": ret1.notna() & ret2.notna(),
        "case1_new_high": np.isclose(dd, 0.0, atol=1e-12) & ret1.notna() & ret2.notna(),
        "case1_drawdown_any": (dd < 0.0) & ret1.notna() & ret2.notna(),
        "case1_drawdown_5pct": (dd <= -0.05) & ret1.notna() & ret2.notna(),
        "case1_drawdown_10pct": (dd <= -0.10) & ret1.notna() & ret2.notna(),
        "case1_drawdown_20pct": (dd <= -0.20) & ret1.notna() & ret2.notna(),
    }

    rows: list[dict] = []
    for name, m in masks.items():
        x = ret1[m]
        y = ret2[m]
        if len(x) < 2:
            corr = np.nan
        else:
            corr = x.corr(y)

        case1_loss = x < 0
        hedge_hit = (x < 0) & (y > 0)
        both_loss = (x < 0) & (y < 0)

        rows.append(
            {
                "regime": name,
                "bars": int(m.sum()),
                "corr": corr,
                "case1_loss_rate": case1_loss.mean() if len(x) else np.nan,
                "hedge_hit_rate_given_case1_loss": (hedge_hit.sum() / case1_loss.sum()) if case1_loss.sum() > 0 else np.nan,
                "both_loss_rate": both_loss.mean() if len(x) else np.nan,
                "mean_ret_case1": x.mean() if len(x) else np.nan,
                "mean_ret_case2": y.mean() if len(y) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def detect_rise_then_crash_events(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    out["past_rise"] = out["equity_case1"] / out["equity_case1"].shift(RISE_WINDOW) - 1.0
    out["future_drop"] = out["equity_case1"].shift(-DROP_WINDOW) / out["equity_case1"] - 1.0

    valid = out["past_rise"].notna() & out["future_drop"].notna()
    rise_thr = out.loc[valid, "past_rise"].quantile(RISE_Q)
    drop_thr = out.loc[valid, "future_drop"].quantile(DROP_Q)

    candidate_idx = out.index[(valid) & (out["past_rise"] >= rise_thr) & (out["future_drop"] <= drop_thr) & (out["future_drop"] < 0.0)].tolist()

    events: list[dict] = []
    last_end = -1
    for idx in candidate_idx:
        if idx <= last_end:
            continue

        drop_start = idx + 1
        drop_end = min(idx + DROP_WINDOW, len(out) - 1)
        if drop_start >= len(out):
            break

        window = out.iloc[drop_start : drop_end + 1]
        r1 = window["ret_case1"].dropna()
        r2 = window["ret_case2"].dropna()
        if min(len(r1), len(r2)) < 2:
            continue

        if window["ret_case1"].std(ddof=0) <= 1e-12 or window["ret_case2"].std(ddof=0) <= 1e-12:
            corr = np.nan
        else:
            corr = window["ret_case1"].corr(window["ret_case2"])
        case1_drop = out["equity_case1"].iloc[drop_end] / out["equity_case1"].iloc[idx] - 1.0
        case2_ret = out["equity_case2"].iloc[drop_end] / out["equity_case2"].iloc[idx] - 1.0
        both_loss_rate = ((window["ret_case1"] < 0) & (window["ret_case2"] < 0)).mean()
        offset_rate = ((window["ret_case1"] < 0) & (window["ret_case2"] > 0)).mean()

        events.append(
            {
                "anchor_timestamp": out["timestamp"].iloc[idx],
                "drop_start": out["timestamp"].iloc[drop_start],
                "drop_end": out["timestamp"].iloc[drop_end],
                "past_rise": out["past_rise"].iloc[idx],
                "future_drop_signal": out["future_drop"].iloc[idx],
                "realized_case1_drop_window": case1_drop,
                "case2_return_same_window": case2_ret,
                "corr_drop_window": corr,
                "both_loss_rate_drop_window": both_loss_rate,
                "offset_rate_drop_window": offset_rate,
                "bars_in_drop_window": int(len(window)),
            }
        )
        last_end = drop_end

    events_df = pd.DataFrame(events)
    meta = {
        "rise_window_bars": RISE_WINDOW,
        "drop_window_bars": DROP_WINDOW,
        "rise_quantile": RISE_Q,
        "drop_quantile": DROP_Q,
        "rise_threshold": rise_thr,
        "drop_threshold": drop_thr,
        "candidate_count": int(len(candidate_idx)),
        "event_count_nonoverlap": int(len(events_df)),
    }
    return events_df, meta


def tail_joint_loss_analysis(df: pd.DataFrame, qs: list[float]) -> pd.DataFrame:
    ret1 = df["ret_case1"]
    ret2 = df["ret_case2"]
    dd = df["dd_case1"]

    neg1 = ret1[ret1 < 0].dropna()
    neg2 = ret2[ret2 < 0].dropna()

    rows: list[dict] = []
    regimes = {
        "all_bars": ret1.notna() & ret2.notna(),
        "case1_drawdown_any": (dd < 0.0) & ret1.notna() & ret2.notna(),
        "case1_drawdown_10pct": (dd <= -0.10) & ret1.notna() & ret2.notna(),
    }

    for q in qs:
        t1 = neg1.quantile(q) if len(neg1) else np.nan
        t2 = neg2.quantile(q) if len(neg2) else np.nan

        for regime_name, mask in regimes.items():
            x = ret1[mask]
            y = ret2[mask]
            if len(x) == 0 or pd.isna(t1) or pd.isna(t2):
                rows.append(
                    {
                        "tail_q": q,
                        "regime": regime_name,
                        "bars": int(len(x)),
                        "tail_thr_case1": t1,
                        "tail_thr_case2": t2,
                        "p_case1_tail": np.nan,
                        "p_case2_tail": np.nan,
                        "p_joint_tail": np.nan,
                        "p_joint_independent": np.nan,
                        "joint_lift_vs_independence": np.nan,
                        "p_case2_tail_given_case1_tail": np.nan,
                        "p_case1_tail_given_case2_tail": np.nan,
                    }
                )
                continue

            e1 = x <= t1
            e2 = y <= t2
            p1 = e1.mean()
            p2 = e2.mean()
            pj = (e1 & e2).mean()
            pind = p1 * p2
            lift = (pj / pind) if pind > 0 else np.nan
            p2_g_e1 = ((e1 & e2).sum() / e1.sum()) if e1.sum() > 0 else np.nan
            p1_g_e2 = ((e1 & e2).sum() / e2.sum()) if e2.sum() > 0 else np.nan

            rows.append(
                {
                    "tail_q": q,
                    "regime": regime_name,
                    "bars": int(len(x)),
                    "tail_thr_case1": t1,
                    "tail_thr_case2": t2,
                    "p_case1_tail": p1,
                    "p_case2_tail": p2,
                    "p_joint_tail": pj,
                    "p_joint_independent": pind,
                    "joint_lift_vs_independence": lift,
                    "p_case2_tail_given_case1_tail": p2_g_e1,
                    "p_case1_tail_given_case2_tail": p1_g_e2,
                }
            )

    return pd.DataFrame(rows)


def write_report(
    df: pd.DataFrame,
    rolling_summary: pd.DataFrame,
    dd_summary: pd.DataFrame,
    rise_crash_df: pd.DataFrame,
    rise_crash_meta: dict,
    tail_df: pd.DataFrame,
):
    start_ts = df["timestamp"].min()
    end_ts = df["timestamp"].max()
    bars = len(df)

    lines: list[str] = []
    lines.append("# Step1 Structural Offset Analysis (Study 42: Case1 vs Case2)")
    lines.append("")
    lines.append("## Data")
    lines.append(f"- Input: `{INPUT_CURVES_CSV}`")
    lines.append(f"- Period: `{start_ts}` -> `{end_ts}`")
    lines.append(f"- Bars: `{bars}` (1-minute curve)")
    lines.append("- Return definition: minute `pct_change` of each case equity.")
    lines.append("")

    lines.append("## 1) Rolling Correlation (Return-based)")
    lines.append(f"- Windows: `{', '.join(str(w) for w in ROLLING_WINDOWS)}`")
    lines.extend(_df_to_md_table(rolling_summary))
    lines.append("")

    lines.append("## 2) Conditional Correlation on Case1 Drawdown Regimes")
    lines.extend(_df_to_md_table(dd_summary))
    lines.append("")

    lines.append("## 3) Rise-Then-Crash Event Correlation")
    lines.append(
        f"- Detection rule (Case1): past `{RISE_WINDOW}` bars rise in top `{int(RISE_Q*100)}%` "
        f"and next `{DROP_WINDOW}` bars drop in bottom `{int(DROP_Q*100)}%`."
    )
    lines.append(
        f"- Thresholds: rise >= `{_fmt(rise_crash_meta['rise_threshold'], 6)}`, "
        f"drop <= `{_fmt(rise_crash_meta['drop_threshold'], 6)}`"
    )
    lines.append(
        f"- Candidate points: `{rise_crash_meta['candidate_count']}`, "
        f"non-overlap events: `{rise_crash_meta['event_count_nonoverlap']}`"
    )
    if rise_crash_df.empty:
        lines.append("- No events detected under current rule.")
    else:
        show_cols = [
            "anchor_timestamp",
            "drop_start",
            "drop_end",
            "past_rise",
            "realized_case1_drop_window",
            "case2_return_same_window",
            "corr_drop_window",
            "both_loss_rate_drop_window",
            "offset_rate_drop_window",
        ]
        lines.append("")
        lines.append("### Event Summary (Top 40 worst Case1 drop windows)")
        tmp = rise_crash_df.sort_values("realized_case1_drop_window").head(40)[show_cols].copy()
        lines.extend(_df_to_md_table(tmp))
        lines.append("")
        lines.append("### Aggregated")
        agg = pd.DataFrame(
            [
                {
                    "events": int(len(rise_crash_df)),
                    "mean_corr_drop_window": rise_crash_df["corr_drop_window"].mean(),
                    "median_corr_drop_window": rise_crash_df["corr_drop_window"].median(),
                    "neg_corr_share_drop_window": (rise_crash_df["corr_drop_window"] < 0).mean(),
                    "mean_case1_drop_window": rise_crash_df["realized_case1_drop_window"].mean(),
                    "mean_case2_return_window": rise_crash_df["case2_return_same_window"].mean(),
                    "mean_both_loss_rate_window": rise_crash_df["both_loss_rate_drop_window"].mean(),
                    "mean_offset_rate_window": rise_crash_df["offset_rate_drop_window"].mean(),
                }
            ]
        )
        lines.extend(_df_to_md_table(agg))
    lines.append("")

    lines.append("## 4) Tail Loss Joint Probability")
    lines.append("- Tail threshold is computed from each strategy's negative-return distribution (q=1%, 5%).")
    lines.extend(_df_to_md_table(tail_df))
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Rolling series: `{OUT_ROLLING_CSV}`")
    lines.append(f"- Rolling summary: `{OUT_ROLLING_SUMMARY_CSV}`")
    lines.append(f"- Drawdown conditional: `{OUT_DD_CSV}`")
    lines.append(f"- Rise-crash events: `{OUT_RISE_CRASH_CSV}`")
    lines.append(f"- Tail joint loss: `{OUT_TAIL_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    curves = load_curves(INPUT_CURVES_CSV)
    df = build_returns(curves)

    rolling_series, rolling_summary = rolling_corr_analysis(df, ROLLING_WINDOWS)
    dd_summary = drawdown_conditional_corr(df)
    rise_crash_df, rise_crash_meta = detect_rise_then_crash_events(df)
    tail_df = tail_joint_loss_analysis(df, TAIL_QS)

    rolling_series.to_csv(OUT_ROLLING_CSV, index=False)
    rolling_summary.to_csv(OUT_ROLLING_SUMMARY_CSV, index=False)
    dd_summary.to_csv(OUT_DD_CSV, index=False)
    rise_crash_df.to_csv(OUT_RISE_CRASH_CSV, index=False)
    tail_df.to_csv(OUT_TAIL_CSV, index=False)

    write_report(df, rolling_summary, dd_summary, rise_crash_df, rise_crash_meta, tail_df)

    print(f"saved_rolling={OUT_ROLLING_CSV}")
    print(f"saved_rolling_summary={OUT_ROLLING_SUMMARY_CSV}")
    print(f"saved_drawdown_conditional={OUT_DD_CSV}")
    print(f"saved_rise_crash={OUT_RISE_CRASH_CSV}")
    print(f"saved_tail={OUT_TAIL_CSV}")
    print(f"saved_report={OUT_MD}")


if __name__ == "__main__":
    run()
