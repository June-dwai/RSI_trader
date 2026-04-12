from __future__ import annotations

from pathlib import Path

import importlib.util
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


CASE_CURVES_CSV = Path("90_backtest_btcusdt_scale06_adx002_case123_stress_proxy_sweep_latest_case_curves.csv")
MARKET_STATE_CSV = Path("90_backtest_btcusdt_scale06_adx002_case123_stress_proxy_sweep_market_state_4h.csv")

OUT_BASE = "92_backtest_btcusdt_scale06_adx002_case123_regime_allocator_sweep"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

MONTHLY_TOPUP = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
REBALANCE_FEE_RATE = 0.0004
THRESHOLD = 0.02

BASE_WEIGHTS = (0.62, 0.31, 0.07)
CHOP_OFF_WEIGHTS = (0.74, 0.26, 0.00)
CHOP_LIGHT_WEIGHTS = (0.70, 0.30, 0.00)
BEAR10_WEIGHTS = (0.60, 0.30, 0.10)
BEAR12_WEIGHTS = (0.58, 0.30, 0.12)

VARIANTS = [
    {"variant": "base_static", "chop_adx": None, "chop_band": None, "chop_weights": BASE_WEIGHTS, "bear_weights": BASE_WEIGHTS},
    {"variant": "chop18_b05_off", "chop_adx": 18.0, "chop_band": 0.005, "chop_weights": CHOP_OFF_WEIGHTS, "bear_weights": BASE_WEIGHTS},
    {"variant": "chop22_b10_off", "chop_adx": 22.0, "chop_band": 0.010, "chop_weights": CHOP_OFF_WEIGHTS, "bear_weights": BASE_WEIGHTS},
    {"variant": "chop26_b15_off", "chop_adx": 26.0, "chop_band": 0.015, "chop_weights": CHOP_OFF_WEIGHTS, "bear_weights": BASE_WEIGHTS},
    {"variant": "chop22_b10_light", "chop_adx": 22.0, "chop_band": 0.010, "chop_weights": CHOP_LIGHT_WEIGHTS, "bear_weights": BASE_WEIGHTS},
    {"variant": "chop22_b10_bear10", "chop_adx": 22.0, "chop_band": 0.010, "chop_weights": CHOP_OFF_WEIGHTS, "bear_weights": BEAR10_WEIGHTS},
    {"variant": "chop22_b10_bear12", "chop_adx": 22.0, "chop_band": 0.010, "chop_weights": CHOP_OFF_WEIGHTS, "bear_weights": BEAR12_WEIGHTS},
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


def merge_state(case_curves: pd.DataFrame, market_state: pd.DataFrame) -> pd.DataFrame:
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


def get_target_weights_from_state(
    trend_value: str,
    adx_value: float,
    ema_dist_value: float,
    cfg: dict,
) -> tuple[float, float, float]:
    if cfg["chop_adx"] is not None:
        is_chop = (adx_value < float(cfg["chop_adx"])) or (abs(ema_dist_value) < float(cfg["chop_band"]))
    else:
        is_chop = False

    is_strong_bear = trend_value == "bearish" and adx_value >= 25.0 and ema_dist_value <= -0.02

    if is_strong_bear and tuple(cfg["bear_weights"]) != BASE_WEIGHTS:
        return tuple(cfg["bear_weights"])
    if is_chop:
        return tuple(cfg["chop_weights"])
    return BASE_WEIGHTS


def run_allocator(merged: pd.DataFrame, variant: str, cfg: dict) -> tuple[pd.DataFrame, dict]:
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret3 = merged["equity_case3"].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"].reset_index(drop=True)
    trend_np = merged["trend_4h_confirmed"].astype(str).to_numpy()
    adx_np = merged["adx14"].to_numpy(dtype=float)
    ema_dist_np = merged["ema_dist_pct"].to_numpy(dtype=float)
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

    cur_w1, cur_w2, cur_w3 = BASE_WEIGHTS
    cap1[0] = INITIAL_CAPITAL_TOTAL * cur_w1
    cap2[0] = INITIAL_CAPITAL_TOTAL * cur_w2
    cap3[0] = INITIAL_CAPITAL_TOTAL * cur_w3
    total[0] = INITIAL_CAPITAL_TOTAL
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0
    w1_series[0], w2_series[0], w3_series[0] = cur_w1, cur_w2, cur_w3

    fee_paid = 0.0
    rebalance_count = 0
    state_switches = 0
    turnover_notional = 0.0

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

        target_w1, target_w2, target_w3 = get_target_weights_from_state(
            trend_value=trend_np[i],
            adx_value=float(adx_np[i]),
            ema_dist_value=float(ema_dist_np[i]),
            cfg=cfg,
        )
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
    ax_eq, ax_perf, ax_state = axes
    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map[variant]
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.set_title("92번 연구: Case123 Regime Allocator Sweep")
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

    ax_state.bar(metrics_df["variant"], metrics_df["avg_case3_weight_pct"], color=[colors[v] for v in variants], alpha=0.85, label="Avg Case3 W %")
    ax_state.set_ylabel("Avg Case3 W %")
    ax_state.grid(True, axis="y", alpha=0.2)
    ax_state.tick_params(axis="x", rotation=20)
    ax_state_t = ax_state.twinx()
    ax_state_t.plot(metrics_df["variant"], metrics_df["state_switches"], color="#9467bd", marker="o", linewidth=1.1, label="State Switches")
    ax_state_t.set_ylabel("State Switches")
    h1, l1 = ax_state.get_legend_handles_labels()
    h2, l2 = ax_state_t.get_legend_handles_labels()
    ax_state.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, common_start: pd.Timestamp, common_end: pd.Timestamp):
    best = metrics_df.sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).iloc[0]
    baseline = metrics_df[metrics_df["variant"] == "base_static"].iloc[0]

    lines: list[str] = []
    lines.append("# 92번 연구: Case123 Regime Allocator Sweep")
    lines.append("")
    lines.append("## 설정")
    lines.append("- 90번에서 만든 `4시간 시장 상태 캐시`를 활용해 동적 weight allocator를 테스트한다.")
    lines.append("- chop 구간에서는 case3 비중을 줄이거나 0으로 만들고, 강한 bear trend에서는 case3 비중을 늘린다.")
    lines.append("- 판단 기준은 4시간 `ADX14`, `EMA200 대비 거리`, `확정 추세`다.")
    lines.append("- baseline은 `base_static = 62/31/7` 고정 비중 + threshold 2% 구조다.")
    lines.append(f"- 공통 구간: `{common_start}` -> `{common_end}`")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Variant | Final Equity | Net Profit | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Avg Case3 W % | State Switches | Fee Paid |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['net_profit'])} | {_fmt(row['twr_cagr_pct'])} | "
            f"{_fmt(row['twr_mdd_pct'])} | {_fmt(row['twr_calmar_ratio'])} | {_fmt(row['xirr_pct'])} | {_fmt(row['avg_case3_weight_pct'])} | "
            f"{int(row['state_switches'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## 핵심 해석")
    lines.append(f"- best variant: `{best['variant']}`")
    lines.append(
        f"- best vs baseline: TWR CAGR `{_fmt(best['twr_cagr_pct'] - baseline['twr_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best['twr_mdd_pct'] - baseline['twr_mdd_pct'])}pp`, "
        f"XIRR `{_fmt(best['xirr_pct'] - baseline['xirr_pct'])}pp`."
    )
    lines.append("- 이 연구가 먹히면, 핵심은 `추세추종 성격의 case3를 언제 끄고 언제 키울지`에 있었다는 뜻이다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 성과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- 보고서: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    case_curves = pd.read_csv(CASE_CURVES_CSV, parse_dates=["timestamp"])
    market_state = pd.read_csv(MARKET_STATE_CSV, parse_dates=["timestamp"])
    merged = merge_state(case_curves, market_state)
    common_start = pd.Timestamp(merged["timestamp"].min())
    common_end = pd.Timestamp(merged["timestamp"].max())

    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        curve, stats = run_allocator(merged, str(cfg["variant"]), cfg)
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
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


s86 = load_module("s86_92", Path("86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.py"))


if __name__ == "__main__":
    run()
