from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_86_PATH = Path("86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.py")
BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")

OUT_BASE = "90_backtest_btcusdt_scale06_adx002_case123_stress_proxy_sweep"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_CASE_CURVES_CSV = Path(f"{OUT_BASE}_latest_case_curves.csv")
OUT_MARKET_CSV = Path(f"{OUT_BASE}_market_state_4h.csv")

MONTHLY_TOPUP = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
REBALANCE_FEE_RATE = 0.0004
THRESHOLD = 0.02
LATEST_END_DATE = "2026-03-15"

BASE_WEIGHTS = (0.62, 0.31, 0.07)
VARIANTS = [
    {"variant": "base_static", "stress_window": 0, "stress_weights": BASE_WEIGHTS, "bullcut": False},
    {"variant": "stress3_w10", "stress_window": 3, "stress_weights": (0.60, 0.30, 0.10), "bullcut": False},
    {"variant": "stress3_w12", "stress_window": 3, "stress_weights": (0.58, 0.30, 0.12), "bullcut": False},
    {"variant": "stress3_w15", "stress_window": 3, "stress_weights": (0.56, 0.29, 0.15), "bullcut": False},
    {"variant": "stress6_w12", "stress_window": 6, "stress_weights": (0.58, 0.30, 0.12), "bullcut": False},
    {"variant": "stress3_w12_bullcut", "stress_window": 3, "stress_weights": (0.58, 0.30, 0.12), "bullcut": True},
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


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def compute_month_flags(ts: pd.Series) -> np.ndarray:
    flags = (ts.dt.to_period("M") != ts.dt.to_period("M").shift(1)).to_numpy(copy=True)
    if len(flags):
        flags[0] = False
    return flags


def hysteresis_state(close: pd.Series, ema_prev: pd.Series, band: float) -> pd.Series:
    state = []
    prev = "bullish"
    for c, e in zip(close, ema_prev):
        if pd.isna(c) or pd.isna(e):
            state.append(np.nan)
            continue
        upper = e * (1.0 + band)
        lower = e * (1.0 - band)
        if c > upper:
            prev = "bullish"
        elif c < lower:
            prev = "bearish"
        state.append(prev)
    return pd.Series(state, index=close.index, dtype="object")


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
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


def build_latest_case_curves() -> tuple[pd.DataFrame, pd.DataFrame]:
    case1, case2 = s86._build_case12_latest()
    case3 = s86._load_case3_curve()

    common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
    common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())

    case1_clip = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)].copy()
    case2_clip = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy()
    case3_clip = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)].copy()
    merged_cases = s86._build_merged(case1_clip, case2_clip, case3_clip)
    return merged_cases, pd.DataFrame({"common_start": [common_start], "common_end": [common_end]})


def build_market_state(common_start: pd.Timestamp, common_end: pd.Timestamp) -> pd.DataFrame:
    m47 = load_module("m47_90", BASE_47_PATH)
    m47.BACKTEST_END = LATEST_END_DATE
    _, df_4h = m47.load_data_no_filter()
    df_4h = df_4h[(df_4h.index >= common_start.floor("4h")) & (df_4h.index <= common_end.ceil("4h"))].copy()

    df_4h["ema200_closed"] = df_4h["close"].ewm(span=m47.EMA_PERIOD, adjust=False).mean()
    df_4h["ema200_prev_closed"] = df_4h["ema200_closed"].shift(1)
    df_4h["trend_4h_hyst"] = hysteresis_state(df_4h["close"], df_4h["ema200_prev_closed"], m47.HYSTERESIS_BAND)
    df_4h["trend_4h_confirmed"] = df_4h["trend_4h_hyst"].shift(1)

    prev_close = df_4h["close"].shift(1)
    tr = pd.concat(
        [
            df_4h["high"] - df_4h["low"],
            (df_4h["high"] - prev_close).abs(),
            (df_4h["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df_4h["tr_pct"] = tr / df_4h["close"]
    df_4h["atr20_pct"] = tr.rolling(20).mean() / df_4h["close"]
    df_4h["ret4h_pct"] = df_4h["close"].pct_change()
    df_4h["adx14"] = compute_adx(df_4h, 14)
    df_4h["ema_dist_pct"] = (df_4h["close"] / df_4h["ema200_prev_closed"]) - 1.0

    stress_event = (
        (df_4h["trend_4h_confirmed"] == "bearish")
        & (df_4h["ret4h_pct"] <= -(df_4h["atr20_pct"] * 0.8))
        & (df_4h["tr_pct"] >= df_4h["atr20_pct"] * 1.15)
    )
    bull_impulse_event = (
        (df_4h["trend_4h_confirmed"] == "bullish")
        & (df_4h["ret4h_pct"] >= df_4h["atr20_pct"] * 0.8)
        & (df_4h["tr_pct"] >= df_4h["atr20_pct"] * 1.15)
    )
    df_4h["stress_event"] = stress_event.fillna(False)
    df_4h["bull_impulse_event"] = bull_impulse_event.fillna(False)

    for bars in [3, 6]:
        df_4h[f"stress_active_{bars}"] = (
            df_4h["stress_event"].rolling(bars, min_periods=1).max().fillna(0).astype(bool)
        )
    df_4h["bull_impulse_active_3"] = (
        df_4h["bull_impulse_event"].rolling(3, min_periods=1).max().fillna(0).astype(bool)
    )

    out = df_4h.reset_index().rename(columns={"index": "timestamp"})
    cols = [
        "timestamp",
        "trend_4h_confirmed",
        "ema200_prev_closed",
        "ret4h_pct",
        "tr_pct",
        "atr20_pct",
        "adx14",
        "ema_dist_pct",
        "stress_event",
        "bull_impulse_event",
        "stress_active_3",
        "stress_active_6",
        "bull_impulse_active_3",
    ]
    return out[cols].dropna(subset=["trend_4h_confirmed"]).copy()


def merge_state_to_cases(case_curves: pd.DataFrame, market_state: pd.DataFrame) -> pd.DataFrame:
    left = case_curves.copy().reset_index(drop=True)
    right = market_state.copy().reset_index(drop=True)
    left["timestamp"] = left["timestamp"].to_numpy(dtype="datetime64[ns]")
    right["timestamp"] = right["timestamp"].to_numpy(dtype="datetime64[ns]")
    return pd.merge_asof(
        left.sort_values("timestamp"),
        right.sort_values("timestamp"),
        on="timestamp",
        direction="backward",
    ).dropna(subset=["trend_4h_confirmed"]).reset_index(drop=True)


def get_target_weights(row: pd.Series, cfg: dict) -> tuple[float, float, float]:
    base_w = BASE_WEIGHTS
    stress_window = int(cfg["stress_window"])
    stress_weights = tuple(cfg["stress_weights"])
    bullcut = bool(cfg["bullcut"])

    if stress_window > 0 and bool(row[f"stress_active_{stress_window}"]):
        return stress_weights
    if bullcut and bool(row["bull_impulse_active_3"]):
        return (0.67, 0.33, 0.00)
    return base_w


def run_dynamic_weights(merged: pd.DataFrame, variant: str, cfg: dict) -> tuple[pd.DataFrame, dict]:
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret3 = merged["equity_case3"].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"].reset_index(drop=True)
    rebal_flags = (ts.dt.floor("4h") != ts.dt.floor("4h").shift(1)).to_numpy()
    topup_flags = compute_month_flags(ts)

    cap1 = np.zeros(len(merged), dtype=float)
    cap2 = np.zeros(len(merged), dtype=float)
    cap3 = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    contrib = np.zeros(len(merged), dtype=float)
    flow = np.zeros(len(merged), dtype=float)
    nav_index = np.zeros(len(merged), dtype=float)
    w1_series = np.zeros(len(merged), dtype=float)
    w2_series = np.zeros(len(merged), dtype=float)
    w3_series = np.zeros(len(merged), dtype=float)

    fee_paid = 0.0
    rebalance_count = 0
    state_switches = 0
    turnover_notional = 0.0

    cur_w1, cur_w2, cur_w3 = BASE_WEIGHTS
    cap1[0] = INITIAL_CAPITAL_TOTAL * cur_w1
    cap2[0] = INITIAL_CAPITAL_TOTAL * cur_w2
    cap3[0] = INITIAL_CAPITAL_TOTAL * cur_w3
    total[0] = cap1[0] + cap2[0] + cap3[0]
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0
    w1_series[0], w2_series[0], w3_series[0] = cur_w1, cur_w2, cur_w3

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        c3 = cap3[i - 1] * (1.0 + float(ret3[i]))
        cur_total = c1 + c2 + c3
        cur_flow = 0.0

        if topup_flags[i]:
            cur_flow = MONTHLY_TOPUP
            c1 += cur_flow * cur_w1
            c2 += cur_flow * cur_w2
            c3 += cur_flow * cur_w3
            cur_total += cur_flow

        target_w1, target_w2, target_w3 = get_target_weights(merged.iloc[i], cfg)
        state_changed = (
            abs(target_w1 - cur_w1) > 1e-12
            or abs(target_w2 - cur_w2) > 1e-12
            or abs(target_w3 - cur_w3) > 1e-12
        )
        if state_changed:
            state_switches += 1

        if cur_total > 0:
            aw1, aw2, aw3 = c1 / cur_total, c2 / cur_total, c3 / cur_total
            max_drift = max(abs(aw1 - target_w1), abs(aw2 - target_w2), abs(aw3 - target_w3))
        else:
            max_drift = 0.0

        if rebal_flags[i] and (max_drift >= THRESHOLD - 1e-12 or state_changed or topup_flags[i]):
            target1 = cur_total * target_w1
            target2 = cur_total * target_w2
            target3 = cur_total * target_w3
            moved = abs(target1 - c1) + abs(target2 - c2) + abs(target3 - c3)
            fee = moved * REBALANCE_FEE_RATE
            cur_total -= fee
            c1 = cur_total * target_w1
            c2 = cur_total * target_w2
            c3 = cur_total * target_w3
            fee_paid += fee
            turnover_notional += moved
            rebalance_count += 1
            cur_w1, cur_w2, cur_w3 = target_w1, target_w2, target_w3
        else:
            cur_w1, cur_w2, cur_w3 = target_w1, target_w2, target_w3

        prev_total = total[i - 1]
        period_return = (cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0
        nav_index[i] = nav_index[i - 1] * (1.0 + period_return)

        cap1[i], cap2[i], cap3[i] = c1, c2, c3
        total[i] = cur_total
        flow[i] = cur_flow
        contrib[i] = contrib[i - 1] + cur_flow
        w1_series[i], w2_series[i], w3_series[i] = cur_w1, cur_w2, cur_w3

    out = merged[["timestamp"]].copy()
    out["variant"] = variant
    out["equity_total"] = total
    out["cap1"] = cap1
    out["cap2"] = cap2
    out["cap3"] = cap3
    out["cash_flow"] = flow
    out["cumulative_contribution"] = contrib
    out["nav_index"] = nav_index
    out["w1"] = w1_series
    out["w2"] = w2_series
    out["w3"] = w3_series

    topups_df = pd.DataFrame({"timestamp": ts[topup_flags], "topup_amount": MONTHLY_TOPUP})
    stats = s86.compute_flow_metrics(out, topups_df)
    stats["variant"] = variant
    stats["rebalance_count"] = rebalance_count
    stats["state_switches"] = state_switches
    stats["fee_paid"] = fee_paid
    stats["turnover_notional"] = turnover_notional
    stats["avg_case3_weight_pct"] = float(pd.Series(w3_series[1:]).mean() * 100.0)
    stats["topup_count"] = int(topup_flags.sum())
    return out, stats


def save_plot(metrics_df: pd.DataFrame, curve_map: dict[str, pd.DataFrame]):
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.0]})
    ax_eq, ax_perf, ax_cost = axes
    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map[variant]
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.set_title("90번 연구: Stress Proxy State Sweep")
    ax_eq.set_ylabel("Total Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_perf.bar(metrics_df["variant"], metrics_df["twr_cagr_pct"], color=[colors[v] for v in variants], alpha=0.85, label="TWR CAGR %")
    ax_perf.set_ylabel("TWR CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf.tick_params(axis="x", rotation=20)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(metrics_df["variant"], metrics_df["twr_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="TWR MDD %")
    ax_perf_t.set_ylabel("TWR MDD %")
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_cost.bar(metrics_df["variant"], metrics_df["rebalance_count"], color=[colors[v] for v in variants], alpha=0.85, label="Rebalances")
    ax_cost.set_ylabel("Rebalances")
    ax_cost.grid(True, axis="y", alpha=0.2)
    ax_cost.tick_params(axis="x", rotation=20)
    ax_cost_t = ax_cost.twinx()
    ax_cost_t.plot(metrics_df["variant"], metrics_df["fee_paid"], color="#9467bd", marker="o", linewidth=1.1, label="Fee Paid")
    ax_cost_t.set_ylabel("Fee Paid")
    h1, l1 = ax_cost.get_legend_handles_labels()
    h2, l2 = ax_cost_t.get_legend_handles_labels()
    ax_cost.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, common_start: pd.Timestamp, common_end: pd.Timestamp):
    best = metrics_df.sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).iloc[0]
    baseline = metrics_df[metrics_df["variant"] == "base_static"].iloc[0]

    lines: list[str] = []
    lines.append("# 90번 연구: Stress Proxy State Sweep")
    lines.append("")
    lines.append("## 설정")
    lines.append("- 로컬에 funding/OI 캐시가 없어서, 90번은 `가격 기반 deleveraging/stress proxy`로 대체했다.")
    lines.append("- 공통 최신 슬리브 곡선과 4시간 상태 지표를 같이 저장해서 이후 연구(91, 92)가 재활용할 수 있게 했다.")
    lines.append("- baseline은 `case123 + threshold 2%`의 고정 비중 구조다.")
    lines.append("- stress state가 감지되면 case3 비중을 키우고 case1 비중을 줄이는 방식으로 동적 가중치를 건다.")
    lines.append("- 일부 variant는 bullish impulse 구간에서 case3 비중을 0으로 줄여 squeeze 구간 노출을 낮춘다.")
    lines.append(f"- 공통 구간: `{common_start}` -> `{common_end}`")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Variant | Final Equity | Net Profit | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid | Avg Case3 W % | State Switches |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['net_profit'])} | {_fmt(row['twr_cagr_pct'])} | "
            f"{_fmt(row['twr_mdd_pct'])} | {_fmt(row['twr_calmar_ratio'])} | {_fmt(row['xirr_pct'])} | "
            f"{int(row['rebalance_count'])} | {_fmt(row['fee_paid'])} | {_fmt(row['avg_case3_weight_pct'])} | {int(row['state_switches'])} |"
        )
    lines.append("")
    lines.append("## 핵심 해석")
    lines.append(f"- best variant: `{best['variant']}`")
    lines.append(
        f"- best vs baseline: TWR CAGR `{_fmt(best['twr_cagr_pct'] - baseline['twr_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best['twr_mdd_pct'] - baseline['twr_mdd_pct'])}pp`, "
        f"XIRR `{_fmt(best['xirr_pct'] - baseline['xirr_pct'])}pp`."
    )
    lines.append("- 이 연구는 진짜 perp positioning 데이터가 아니라 `가격/변동성 기반 proxy`라는 점을 반드시 감안해야 한다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 성과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- 최신 슬리브 캐시: `{OUT_CASE_CURVES_CSV}`")
    lines.append(f"- 4시간 상태 캐시: `{OUT_MARKET_CSV}`")
    lines.append(f"- 보고서: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    if OUT_CASE_CURVES_CSV.exists():
        case_curves = pd.read_csv(OUT_CASE_CURVES_CSV, parse_dates=["timestamp"])
        common_start = pd.Timestamp(case_curves["timestamp"].min())
        common_end = pd.Timestamp(case_curves["timestamp"].max())
    else:
        case_curves, meta = build_latest_case_curves()
        common_start = pd.Timestamp(meta["common_start"].iloc[0])
        common_end = pd.Timestamp(meta["common_end"].iloc[0])
        case_curves.to_csv(OUT_CASE_CURVES_CSV, index=False)

    if OUT_MARKET_CSV.exists():
        market_state = pd.read_csv(OUT_MARKET_CSV, parse_dates=["timestamp"])
    else:
        market_state = build_market_state(common_start, common_end)
        market_state.to_csv(OUT_MARKET_CSV, index=False)

    merged = merge_state_to_cases(case_curves, market_state)

    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        curve, stats = run_dynamic_weights(merged, str(cfg["variant"]), cfg)
        rows.append(stats)
        curve_rows.append(curve)
        curve_map[str(cfg["variant"])] = curve

    metrics_df = pd.DataFrame(rows).sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curve_rows, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(metrics_df, curve_map)
    save_report(metrics_df, common_start, common_end)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_case_curves={OUT_CASE_CURVES_CSV}")
    print(f"saved_market_state={OUT_MARKET_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


s86 = load_module("s86_90", BASE_86_PATH)


if __name__ == "__main__":
    run()
