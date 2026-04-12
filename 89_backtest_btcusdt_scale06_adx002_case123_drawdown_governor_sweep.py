from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_86_PATH = Path("86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.py")

OUT_BASE = "89_backtest_btcusdt_scale06_adx002_case123_drawdown_governor_sweep"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

MONTHLY_TOPUP = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
REBALANCE_FEE_RATE = 0.0004
THRESHOLD = 0.02
RISK_WEIGHTS = (0.62, 0.31, 0.07)

VARIANTS = [
    {"variant": "base_thr2_nogov", "thresholds": [], "exposures": [1.0], "recovery_gap": 0.0},
    {"variant": "soft_12_20_30", "thresholds": [12.0, 20.0, 30.0], "exposures": [1.0, 0.90, 0.75, 0.60], "recovery_gap": 4.0},
    {"variant": "mid_10_18_26", "thresholds": [10.0, 18.0, 26.0], "exposures": [1.0, 0.85, 0.70, 0.55], "recovery_gap": 4.0},
    {"variant": "hard_8_15_22", "thresholds": [8.0, 15.0, 22.0], "exposures": [1.0, 0.80, 0.60, 0.40], "recovery_gap": 4.0},
    {"variant": "twostep_15_25", "thresholds": [15.0, 25.0], "exposures": [1.0, 0.85, 0.65], "recovery_gap": 5.0},
    {"variant": "ultrasoft_15_25_35", "thresholds": [15.0, 25.0, 35.0], "exposures": [1.0, 0.95, 0.85, 0.70], "recovery_gap": 5.0},
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


def update_level(dd_pct: float, current_level: int, thresholds: list[float], recovery_gap: float) -> int:
    level = current_level
    while level < len(thresholds) and dd_pct >= thresholds[level]:
        level += 1
    while level > 0 and dd_pct <= thresholds[level - 1] - recovery_gap:
        level -= 1
    return level


def run_governor_portfolio(
    merged: pd.DataFrame,
    variant: str,
    dd_thresholds: list[float],
    exposures: list[float],
    recovery_gap: float,
) -> tuple[pd.DataFrame, dict]:
    w1, w2, w3 = RISK_WEIGHTS
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret3 = merged["equity_case3"].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"].reset_index(drop=True)

    rebal_flags = (ts.dt.floor("4h") != ts.dt.floor("4h").shift(1)).to_numpy()
    topup_flags = compute_month_flags(ts)

    cap1 = np.zeros(len(merged), dtype=float)
    cap2 = np.zeros(len(merged), dtype=float)
    cap3 = np.zeros(len(merged), dtype=float)
    cash = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    contrib = np.zeros(len(merged), dtype=float)
    flow = np.zeros(len(merged), dtype=float)
    nav_index = np.zeros(len(merged), dtype=float)
    dd_pct_series = np.zeros(len(merged), dtype=float)
    exposure_series = np.zeros(len(merged), dtype=float)

    cap1[0] = INITIAL_CAPITAL_TOTAL * w1
    cap2[0] = INITIAL_CAPITAL_TOTAL * w2
    cap3[0] = INITIAL_CAPITAL_TOTAL * w3
    cash[0] = 0.0
    total[0] = cap1[0] + cap2[0] + cap3[0]
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0
    exposure_series[0] = 1.0

    fee_paid = 0.0
    rebalance_count = 0
    threshold_hits = 0
    governor_level_changes = 0
    turnover_notional = 0.0
    current_level = 0
    nav_peak = 1.0

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        c3 = cap3[i - 1] * (1.0 + float(ret3[i]))
        c_cash = cash[i - 1]
        cur_total = c1 + c2 + c3 + c_cash
        cur_flow = 0.0

        if topup_flags[i]:
            cur_flow = MONTHLY_TOPUP
            c_cash += cur_flow
            cur_total += cur_flow

        prev_total = total[i - 1]
        nav_pre = nav_index[i - 1] * (1.0 + ((cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0))
        nav_peak = max(nav_peak, nav_pre)
        dd_pct = max(0.0, (1.0 - nav_pre / nav_peak) * 100.0) if nav_peak > 0 else 0.0
        dd_pct_series[i] = dd_pct

        new_level = update_level(dd_pct, current_level, dd_thresholds, recovery_gap)
        level_changed = new_level != current_level
        if level_changed:
            governor_level_changes += 1
        current_level = new_level
        exposure = exposures[current_level]
        exposure_series[i] = exposure

        if cur_total > 0:
            tw1 = exposure * w1
            tw2 = exposure * w2
            tw3 = exposure * w3
            tw_cash = 1.0 - exposure
            aw1 = c1 / cur_total
            aw2 = c2 / cur_total
            aw3 = c3 / cur_total
            aw_cash = c_cash / cur_total
            max_drift = max(abs(aw1 - tw1), abs(aw2 - tw2), abs(aw3 - tw3), abs(aw_cash - tw_cash))
        else:
            max_drift = 0.0

        if rebal_flags[i] and (max_drift >= THRESHOLD - 1e-12 or level_changed or topup_flags[i]):
            threshold_hits += 1
            target1 = cur_total * exposure * w1
            target2 = cur_total * exposure * w2
            target3 = cur_total * exposure * w3
            target_cash = cur_total * (1.0 - exposure)
            moved = abs(target1 - c1) + abs(target2 - c2) + abs(target3 - c3) + abs(target_cash - c_cash)
            fee = moved * REBALANCE_FEE_RATE
            cur_total -= fee
            c1 = cur_total * exposure * w1
            c2 = cur_total * exposure * w2
            c3 = cur_total * exposure * w3
            c_cash = cur_total * (1.0 - exposure)
            fee_paid += fee
            turnover_notional += moved
            rebalance_count += 1

        period_return = (cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0
        nav_index[i] = nav_index[i - 1] * (1.0 + period_return)
        nav_peak = max(nav_peak, nav_index[i])

        cap1[i] = c1
        cap2[i] = c2
        cap3[i] = c3
        cash[i] = c_cash
        total[i] = cur_total
        flow[i] = cur_flow
        contrib[i] = contrib[i - 1] + cur_flow

    out = merged[["timestamp"]].copy()
    out["variant"] = variant
    out["equity_total"] = total
    out["cap1"] = cap1
    out["cap2"] = cap2
    out["cap3"] = cap3
    out["cash"] = cash
    out["cash_flow"] = flow
    out["cumulative_contribution"] = contrib
    out["nav_index"] = nav_index
    out["dd_pct"] = dd_pct_series
    out["exposure"] = exposure_series

    topups_df = pd.DataFrame(
        {
            "timestamp": ts[topup_flags],
            "topup_amount": MONTHLY_TOPUP,
        }
    )
    stats = s86.compute_flow_metrics(out, topups_df)
    stats["variant"] = variant
    stats["rebalance_count"] = rebalance_count
    stats["threshold_hits"] = threshold_hits
    stats["governor_level_changes"] = governor_level_changes
    stats["fee_paid"] = fee_paid
    stats["turnover_notional"] = turnover_notional
    stats["avg_exposure_pct"] = float(pd.Series(exposure_series[1:]).mean() * 100.0)
    stats["min_exposure_pct"] = float(pd.Series(exposure_series[1:]).min() * 100.0)
    stats["topup_count"] = int(topup_flags.sum())
    return out, stats


def save_plot(metrics_df: pd.DataFrame, curve_map: dict[str, pd.DataFrame]):
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.0]})
    ax_eq, ax_perf, ax_exp = axes
    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map[variant]
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.set_title("89번 연구: Case123 Drawdown Governor Sweep")
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

    ax_exp.bar(metrics_df["variant"], metrics_df["avg_exposure_pct"], color=[colors[v] for v in variants], alpha=0.85, label="Avg Exposure %")
    ax_exp.set_ylabel("Avg Exposure %")
    ax_exp.grid(True, axis="y", alpha=0.2)
    ax_exp.tick_params(axis="x", rotation=20)
    ax_exp_t = ax_exp.twinx()
    ax_exp_t.plot(metrics_df["variant"], metrics_df["fee_paid"], color="#9467bd", marker="o", linewidth=1.1, label="Fee Paid")
    ax_exp_t.set_ylabel("Fee Paid")
    h1, l1 = ax_exp.get_legend_handles_labels()
    h2, l2 = ax_exp_t.get_legend_handles_labels()
    ax_exp.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, common_start: pd.Timestamp, common_end: pd.Timestamp):
    best = metrics_df.sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).iloc[0]
    baseline = metrics_df[metrics_df["variant"] == "base_thr2_nogov"].iloc[0]

    lines: list[str] = []
    lines.append("# 89번 연구: Case123 Drawdown Governor Sweep")
    lines.append("")
    lines.append("## 설정")
    lines.append("- 기준 포트폴리오는 88번 연구에서 가장 강했던 `case123 + threshold 2%` 구조다.")
    lines.append("- 월 적립금은 기존과 동일하게 매월 첫 시점에 `1000` 달러를 넣는다.")
    lines.append("- drawdown governor는 포트폴리오의 flow-adjusted NAV drawdown이 커질수록 위험자산 비중을 줄이고, 남는 비중은 현금으로 둔다.")
    lines.append("- 리스크 슬리브 비중은 줄어들지만, `case1:case2:case3 = 62:31:7`의 내부 비율은 유지한다.")
    lines.append(f"- 공통 구간: `{common_start}` -> `{common_end}`")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Variant | Final Equity | Net Profit | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Avg Exposure % | Min Exposure % | Rebalances | Fee Paid |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['net_profit'])} | {_fmt(row['twr_cagr_pct'])} | "
            f"{_fmt(row['twr_mdd_pct'])} | {_fmt(row['twr_calmar_ratio'])} | {_fmt(row['xirr_pct'])} | "
            f"{_fmt(row['avg_exposure_pct'])} | {_fmt(row['min_exposure_pct'])} | {int(row['rebalance_count'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## 핵심 해석")
    lines.append(f"- best governor: `{best['variant']}` (`TWR CAGR {_fmt(best['twr_cagr_pct'])}%`, `MDD {_fmt(best['twr_mdd_pct'])}%`, `XIRR {_fmt(best['xirr_pct'])}%`).")
    lines.append(
        f"- best vs base: TWR CAGR `{_fmt(best['twr_cagr_pct'] - baseline['twr_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best['twr_mdd_pct'] - baseline['twr_mdd_pct'])}pp`, "
        f"XIRR `{_fmt(best['xirr_pct'] - baseline['xirr_pct'])}pp`, "
        f"fee `{_fmt(best['fee_paid'] - baseline['fee_paid'])}`."
    )
    lines.append("- governor가 잘 먹히면 `대형 손실 구간에서 현금 비중을 늘려 MDD를 줄이면서`, 회복 구간에서는 다시 위험자산 비중을 복구한다.")
    lines.append("- 너무 공격적인 governor는 MDD는 줄여도 상승 구간 노출을 너무 많이 잃어서 CAGR/XIRR이 꺾일 수 있다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 성과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- 보고서: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    case1, case2 = s86._build_case12_latest()
    case3 = s86._load_case3_curve()

    common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
    common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())

    case1_clip = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)].copy()
    case2_clip = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy()
    case3_clip = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)].copy()
    merged = s86._build_merged(case1_clip, case2_clip, case3_clip)

    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        curve, stats = run_governor_portfolio(
            merged=merged,
            variant=str(cfg["variant"]),
            dd_thresholds=list(cfg["thresholds"]),
            exposures=list(cfg["exposures"]),
            recovery_gap=float(cfg["recovery_gap"]),
        )
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


s86 = load_module("s86_89", BASE_86_PATH)


if __name__ == "__main__":
    run()
