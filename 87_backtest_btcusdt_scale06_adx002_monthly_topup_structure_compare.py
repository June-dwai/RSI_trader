from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_86_PATH = Path("86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.py")

OUT_BASE = "87_backtest_btcusdt_scale06_adx002_monthly_topup_structure_compare"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_TOPUPS_CSV = Path(f"{OUT_BASE}_topups.csv")

MONTHLY_TOPUP = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
CASE12_W1 = 0.74
CASE12_W2 = 0.26
CASE123_W1 = 0.62
CASE123_W2 = 0.31
CASE123_W3 = 0.07
REBALANCE_FEE_RATE = 0.0004


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


def build_case12_merged(case1: pd.DataFrame, case2: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge(case1, case2, on="timestamp", how="outer").sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2"]).copy()
    return merged


def compute_month_flags(ts: pd.Series) -> np.ndarray:
    flags = (ts.dt.to_period("M") != ts.dt.to_period("M").shift(1)).to_numpy(copy=True)
    if len(flags):
        flags[0] = False
    return flags


def run_case12_topup_only(merged: pd.DataFrame, variant: str, deposit_mode: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"].reset_index(drop=True)
    topup_flags = compute_month_flags(ts)

    cap1 = np.zeros(len(merged), dtype=float)
    cap2 = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    flow = np.zeros(len(merged), dtype=float)
    contrib = np.zeros(len(merged), dtype=float)
    nav_index = np.zeros(len(merged), dtype=float)

    topup_rows: list[dict] = []
    topup_count = 0

    cap1[0] = INITIAL_CAPITAL_TOTAL * CASE12_W1
    cap2[0] = INITIAL_CAPITAL_TOTAL * CASE12_W2
    total[0] = cap1[0] + cap2[0]
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        cur_total = c1 + c2
        cur_flow = 0.0

        if topup_flags[i]:
            cur_flow = MONTHLY_TOPUP
            if deposit_mode == "fixed_weight":
                add1 = cur_flow * CASE12_W1
                add2 = cur_flow * CASE12_W2
            elif deposit_mode == "underweight_only":
                target1_after = CASE12_W1 * (cur_total + cur_flow)
                add1 = min(max(target1_after - c1, 0.0), cur_flow)
                add2 = cur_flow - add1
            else:
                raise ValueError(f"Unknown deposit mode: {deposit_mode}")

            c1 += add1
            c2 += add2
            cur_total += cur_flow
            topup_count += 1
            topup_rows.append(
                {
                    "variant": variant,
                    "timestamp": ts.iloc[i],
                    "topup_amount": cur_flow,
                    "topup_case1": add1,
                    "topup_case2": add2,
                    "topup_case3": 0.0,
                    "equity_before_topup": cur_total - cur_flow,
                    "equity_after_topup": cur_total,
                    "cumulative_contribution": contrib[i - 1] + cur_flow,
                }
            )

        prev_total = total[i - 1]
        period_return = (cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0
        nav_index[i] = nav_index[i - 1] * (1.0 + period_return)

        cap1[i] = c1
        cap2[i] = c2
        total[i] = cur_total
        flow[i] = cur_flow
        contrib[i] = contrib[i - 1] + cur_flow

    out = merged[["timestamp"]].copy()
    out["variant"] = variant
    out["equity_total"] = total
    out["cap1"] = cap1
    out["cap2"] = cap2
    out["cap3"] = 0.0
    out["cash_flow"] = flow
    out["cumulative_contribution"] = contrib
    out["nav_index"] = nav_index
    out["w1"] = CASE12_W1
    out["w2"] = CASE12_W2
    out["w3"] = 0.0

    topups_df = pd.DataFrame(topup_rows)
    stats = s86.compute_flow_metrics(out, topups_df)
    stats["variant"] = variant
    stats["rebalance_count"] = 0
    stats["fee_paid"] = 0.0
    stats["topup_count"] = topup_count
    stats["topup_amount_each"] = MONTHLY_TOPUP
    return out, topups_df, stats


def run_case12_rebalance_topup(merged: pd.DataFrame, variant: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"].reset_index(drop=True)
    rebal_flags = (ts.dt.floor("4h") != ts.dt.floor("4h").shift(1)).to_numpy()
    topup_flags = compute_month_flags(ts)

    cap1 = np.zeros(len(merged), dtype=float)
    cap2 = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    flow = np.zeros(len(merged), dtype=float)
    contrib = np.zeros(len(merged), dtype=float)
    nav_index = np.zeros(len(merged), dtype=float)

    fee_paid = 0.0
    rebalance_count = 0
    topup_count = 0
    topup_rows: list[dict] = []

    cap1[0] = INITIAL_CAPITAL_TOTAL * CASE12_W1
    cap2[0] = INITIAL_CAPITAL_TOTAL * CASE12_W2
    total[0] = cap1[0] + cap2[0]
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        cur_total = c1 + c2
        cur_flow = 0.0

        if topup_flags[i]:
            cur_flow = MONTHLY_TOPUP
            c1 += cur_flow * CASE12_W1
            c2 += cur_flow * CASE12_W2
            cur_total += cur_flow
            topup_count += 1
            topup_rows.append(
                {
                    "variant": variant,
                    "timestamp": ts.iloc[i],
                    "topup_amount": cur_flow,
                    "topup_case1": cur_flow * CASE12_W1,
                    "topup_case2": cur_flow * CASE12_W2,
                    "topup_case3": 0.0,
                    "equity_before_topup": cur_total - cur_flow,
                    "equity_after_topup": cur_total,
                    "cumulative_contribution": contrib[i - 1] + cur_flow,
                }
            )

        if rebal_flags[i]:
            target1 = cur_total * CASE12_W1
            target2 = cur_total * CASE12_W2
            fee = (abs(target1 - c1) + abs(target2 - c2)) * REBALANCE_FEE_RATE
            cur_total -= fee
            c1 = cur_total * CASE12_W1
            c2 = cur_total * CASE12_W2
            fee_paid += fee
            rebalance_count += 1

        prev_total = total[i - 1]
        period_return = (cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0
        nav_index[i] = nav_index[i - 1] * (1.0 + period_return)

        cap1[i] = c1
        cap2[i] = c2
        total[i] = cur_total
        flow[i] = cur_flow
        contrib[i] = contrib[i - 1] + cur_flow

    out = merged[["timestamp"]].copy()
    out["variant"] = variant
    out["equity_total"] = total
    out["cap1"] = cap1
    out["cap2"] = cap2
    out["cap3"] = 0.0
    out["cash_flow"] = flow
    out["cumulative_contribution"] = contrib
    out["nav_index"] = nav_index
    out["w1"] = CASE12_W1
    out["w2"] = CASE12_W2
    out["w3"] = 0.0

    topups_df = pd.DataFrame(topup_rows)
    stats = s86.compute_flow_metrics(out, topups_df)
    stats["variant"] = variant
    stats["rebalance_count"] = rebalance_count
    stats["fee_paid"] = fee_paid
    stats["topup_count"] = topup_count
    stats["topup_amount_each"] = MONTHLY_TOPUP
    return out, topups_df, stats


def save_plot(curves_df: pd.DataFrame):
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0]})
    ax_eq, ax_nav = axes
    cmap = plt.get_cmap("tab10")
    variants = curves_df["variant"].drop_duplicates().tolist()
    colors = {v: cmap(i % 10) for i, v in enumerate(variants)}

    for variant, curve in curves_df.groupby("variant"):
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
        ax_eq.plot(curve["timestamp"], curve["cumulative_contribution"], linewidth=0.85, linestyle="--", color=colors[variant], alpha=0.65)
        ax_nav.plot(curve["timestamp"], curve["nav_index"], linewidth=1.1, color=colors[variant], label=variant)

    ax_eq.set_title("87 Study: Monthly Top-Up Structure Compare")
    ax_eq.set_ylabel("Equity / Contribution")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_nav.set_title("Flow-Adjusted NAV Index")
    ax_nav.set_ylabel("NAV Index")
    ax_nav.grid(True, alpha=0.2)
    ax_nav.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, common_start: pd.Timestamp, common_end: pd.Timestamp):
    lines: list[str] = []
    lines.append("# 87번 연구: 월 적립식 구조 비교")
    lines.append("")
    lines.append("## 설정")
    lines.append("- 모든 비교 대상이 완전히 같은 시장 구간을 보도록 공통 기간으로 잘라서 계산했다.")
    lines.append(f"- 시작 시점: `{common_start}`")
    lines.append(f"- 종료 시점: `{common_end}`")
    lines.append(f"- 월 적립금: 매월 새로운 달의 첫 시점에 `{MONTHLY_TOPUP:.0f}` 달러를 추가한다.")
    lines.append("- `case1/case2 only`는 70번 연구의 2-sleeve 목표 비중 `74/26`을 사용한다.")
    lines.append("- `case1/case2/case3`는 현재 85번 연구 best 비중인 `62/31/7`을 사용한다.")
    lines.append("- 현금 유입이 있으므로 비교 지표는 `TWR CAGR`, `TWR MDD`, `TWR Calmar`, `XIRR`를 중심으로 본다.")
    lines.append("")
    lines.append("## 슬리브별 매매 로직")
    lines.append("")
    lines.append("### Case1: `shallow6_else2bull`")
    lines.append("- 기본 철학: 롱 위주의 눌림매수 엔진이고, 별도의 추세 헤지를 붙인 구조다. 대칭적인 롱/숏 전략은 아니다.")
    lines.append("- 실행 단위: 1분봉.")
    lines.append("- 진입 아이디어: 상위 타임프레임이 아직 bullish일 때 과매도 눌림을 롱으로 산다.")
    lines.append("- 포지션 누적: 가격이 더 밀리면 `0.5%` 간격으로 물타기를 하고, `max_entries=4`에서 제한한다. 추가 진입 크기는 ADX 상태를 반영한다.")
    lines.append("- 리스크 관리: 확정된 4시간 추세가 bearish로 바뀌면 기존 롱 inventory를 상대로 hedge short를 연다.")
    lines.append("- 여기서 쓰는 62번 개선: 롱이 평균단가 대비 얕게 물려 있을 때는 가격이 평균단가의 `-6%` 안쪽으로 오면 hedge를 조기 해제하고, 깊게 물려 있으면 bullish 4시간봉이 두 번 확인될 때까지 hedge를 유지한다.")
    lines.append("- 실전적으로는 이 슬리브가 가장 강한 수익 엔진이지만, 단독으로 돌리면 inventory drawdown이 크다.")
    lines.append("")
    lines.append("### Case2: 42번 연구 dual-direction no-hedge 엔진")
    lines.append("- 기본 철학: 양방향 mean-reversion이지만, case1처럼 별도의 hedge 계층은 없다.")
    lines.append("- 실행 단위: 1분봉.")
    lines.append("- 진입 아이디어: bullish 구간에서는 과매도 롱, bearish 구간에서는 과매수 숏을 잡는다.")
    lines.append("- 포지션 처리: 최대 `max_entries=4`까지 누적 가능하다. 반대 신호가 나오면 기존 포지션을 `80%` 부분청산하고, 곧바로 반대 방향을 새로 연다.")
    lines.append("- hedge 없음, hysteresis overlay 없음, case1 같은 보호 장치도 없다.")
    lines.append("- 포트폴리오에서 이 슬리브의 가치는 단독 안정성보다, case1과 경로가 완전히 같지 않아서 분산과 리밸런싱 이득을 주는 데 있다.")
    lines.append("")
    lines.append("### Case3: `short_gate_24h_g12_tp15`")
    lines.append("- 기본 철학: 추세추종 슬리브인데, 숏 타이밍을 더 엄격하게 걸러서 보조 엔진으로 쓰는 구조다.")
    lines.append("- 실행 단위: 1분봉을 15분봉으로 리샘플한 뒤 사용.")
    lines.append("- 바이어스 엔진: 4시간 EMA200 hysteresis 확정 추세.")
    lines.append("- 롱 측면: bullish regime이면 기본적으로 그대로 따라간다.")
    lines.append("- 숏 측면: bearish라고 바로 숏하지 않는다. 먼저 직전 `24시간` 유동성 고점을 위로 쓸고 올라갔다가 다시 밀리는 rejection이 나와야 하고, 그 뒤 `12개 bar` 동안만 숏 진입을 허용한다.")
    lines.append("- 청산 로직: 레버리지 `2배`, 손절 `6%`, 그리고 숏 전용 `+15%` 익절 lock을 쓴다. 숏이 목표 수익에 도달하면 익절하고, 이후 bullish flip이 나올 때까지 새 숏 재진입을 막는다.")
    lines.append("- 이 슬리브는 비중을 작게 두는 게 전제다. 총수익의 핵심 엔진이 아니라, 하락 구간 타이밍 개선과 포트폴리오 완충 역할이 목적이다.")
    lines.append("")
    lines.append("## 비교 시나리오 정의")
    lines.append("")
    lines.append("### 1. `current_run_topup_only`")
    lines.append("- 지금처럼 `case1`과 `case2`를 별도로 굴리면서 새 돈만 넣는 상황에 가장 가까운 가정이다.")
    lines.append("- 초기 비중은 `74/26`이다.")
    lines.append("- 매월 들어오는 새 `1000`달러도 같은 `74/26` 비율로 넣는다.")
    lines.append("- 기존 자산을 팔지 않고, 정기 리밸런싱도 하지 않으며, 포트폴리오 차원의 리밸런싱 수수료도 없다.")
    lines.append("")
    lines.append("### 2. `case12_rebal4h_topup`")
    lines.append("- 같은 두 슬리브, 같은 초기 비중, 같은 월 적립금을 쓴다.")
    lines.append("- 다만 각 슬리브의 손익으로 비중이 틀어질 때마다 전체 포트폴리오를 `4시간마다` 다시 `74/26`으로 맞춘다.")
    lines.append("- 즉 전략 구성은 안 바꾸고, 포트폴리오 레벨 리밸런싱의 가치만 따로 분리해서 보는 케이스다.")
    lines.append("")
    lines.append("### 3. `case123_rebal4h_topup`")
    lines.append("- 여기에 `case3`를 추가해서 현재 best 3-sleeve 목표 비중 `62/31/7`을 사용한다.")
    lines.append("- 월 적립금도 그 비중대로 바로 나눠 넣는다.")
    lines.append("- 포트폴리오는 85번 연구와 같은 방식으로 `4시간마다` 수수료를 반영해 리밸런싱한다.")
    lines.append("- 현재까지 비교한 월 적립식 구조 중에서는 이 케이스가 가장 강한 historical 결과를 보였다.")
    lines.append("")
    lines.append("### 추가 실전 참고: `case12_cash_only_rebalance_topup`")
    lines.append("- 기존 자산을 팔지 않고, 정기 리밸런싱도 하지 않는다.")
    lines.append("- 대신 매월 들어오는 새 돈만 underweight 쪽에 더 넣어서 비중 틀어짐을 일부 복구한다.")
    lines.append("- 즉 실제 운용에서 포지션을 직접 스왑하긴 부담스럽지만, 새 자금으로만 비중을 조절하고 싶을 때 가까운 형태다.")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Variant | Final Equity | Contributed | Net Profit | Money Multiple | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['total_contributed'])} | {_fmt(row['net_profit'])} | "
            f"{_fmt(row['money_multiple'])} | {_fmt(row['twr_cagr_pct'])} | {_fmt(row['twr_mdd_pct'])} | {_fmt(row['twr_calmar_ratio'])} | "
            f"{_fmt(row['xirr_pct'])} | {int(row['rebalance_count'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    best_twr = metrics_df.sort_values(["twr_calmar_ratio", "twr_cagr_pct"], ascending=[False, False]).iloc[0]
    best_xirr = metrics_df.sort_values("xirr_pct", ascending=False).iloc[0]
    lines.append(f"- TWR/Calmar 기준 최고 구조는 `{best_twr['variant']}`다.")
    lines.append(f"- 투자자 체감 수익률에 가까운 XIRR 기준 최고 구조도 `{best_xirr['variant']}`다.")
    lines.append("- `current_run_topup_only`는 지금처럼 슬리브를 따로 돌리고 새 돈만 넣는 형태의 기준선이다.")
    lines.append("- `case12_rebal4h_topup`는 case3 없이도 리밸런싱만으로 얼마나 좋아지는지 보여준다.")
    lines.append("- `case123_rebal4h_topup`는 월 적립식 자금 유입이 있어도 case3 diversifier가 여전히 유효한지 보여준다.")
    lines.append("- `case12_cash_only_rebalance_topup`는 실전에서 기존 자산을 팔지 않고 새 돈으로만 비중을 조절할 때 어느 정도 개선이 가능한지 보는 참고선이다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 성과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- 적립금 CSV: `{OUT_TOPUPS_CSV}`")
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

    merged12 = build_case12_merged(case1_clip, case2_clip)
    merged123 = s86._build_merged(case1_clip, case2_clip, case3_clip)

    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    topup_rows: list[pd.DataFrame] = []

    scenarios = [
        run_case12_topup_only(merged12, "current_run_topup_only", deposit_mode="fixed_weight"),
        run_case12_rebalance_topup(merged12, "case12_rebal4h_topup"),
        s86.run_portfolio(merged123, "case123_rebal4h_topup", monthly_topup=MONTHLY_TOPUP),
        run_case12_topup_only(merged12, "case12_cash_only_rebalance_topup", deposit_mode="underweight_only"),
    ]

    for curve, topups, stats in scenarios:
        rows.append(stats)
        curve_rows.append(curve)
        topup_rows.append(topups)

    metrics_df = pd.DataFrame(rows).sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curve_rows, ignore_index=True)
    topups_df = pd.concat(topup_rows, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    topups_df.to_csv(OUT_TOPUPS_CSV, index=False)
    save_plot(curves_df)
    save_report(metrics_df, common_start, common_end)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_topups={OUT_TOPUPS_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


s86 = load_module("s86_87", BASE_86_PATH)


if __name__ == "__main__":
    run()
