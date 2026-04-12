from __future__ import annotations

import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


CASE2_CACHE = Path("122_backtest_btcusdt_practical_rebalance_weight_sweep_2021plus_sleeve_state.pkl")
CASE3_CURVES_CSV = Path("126_backtest_btcusdt_case3_long_quality_push_curves.csv")
CASE3_METRICS_CSV = Path("126_backtest_btcusdt_case3_long_quality_push.csv")

OUT_BASE = "127_backtest_btcusdt_case2_vs_case3best_mix"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

PORTFOLIO_CAPITAL = 2000.0
CASE3_BEST_VARIANT = "lb4_delay8_capna_cd0"
ANALYSIS_2026_START = pd.Timestamp("2026-01-01 00:00:00")


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def compute_curve_stats(curve: pd.DataFrame, equity_col: str, initial_capital: float) -> dict:
    series = curve[equity_col].astype(float)
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


def compute_window_stats(curve: pd.DataFrame, start_ts: pd.Timestamp, initial_capital: float | None = None) -> dict:
    seg = curve[pd.to_datetime(curve["timestamp"]) >= pd.Timestamp(start_ts)].copy()
    if seg.empty:
        return {"return_pct": np.nan, "mdd_pct": np.nan}
    start_eq = float(seg["equity"].iloc[0]) if initial_capital is None else float(initial_capital)
    end_eq = float(seg["equity"].iloc[-1])
    dd = seg["equity"].astype(float) / seg["equity"].cummax().astype(float) - 1.0
    return {
        "return_pct": (end_eq / start_eq - 1.0) * 100.0,
        "mdd_pct": -float(dd.min() * 100.0),
    }


def load_case2_curve() -> tuple[pd.DataFrame, pd.Timestamp]:
    if not CASE2_CACHE.exists():
        raise FileNotFoundError(f"Missing case2 cache: {CASE2_CACHE}")
    with CASE2_CACHE.open("rb") as f:
        cache = pickle.load(f)
    curve = cache["case2_state"].copy()
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve[["timestamp", "equity"]].copy().sort_values("timestamp").reset_index(drop=True)
    return curve, pd.Timestamp(cache["cache_end_ts"])


def load_case3_best_curve() -> pd.DataFrame:
    if not CASE3_CURVES_CSV.exists():
        raise FileNotFoundError(f"Missing case3 curves csv: {CASE3_CURVES_CSV}")
    curve = pd.read_csv(CASE3_CURVES_CSV)
    curve = curve[curve["variant"] == CASE3_BEST_VARIANT].copy()
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").reset_index(drop=True)
    if curve.empty:
        raise RuntimeError(f"Variant not found in curve csv: {CASE3_BEST_VARIANT}")
    # 126 ran with 1000 initial capital; scale to 2000 for fair comparison with case2.
    curve["equity"] = curve["equity"].astype(float) * 2.0
    return curve[["timestamp", "equity"]].copy()


def align_curves(case2_curve: pd.DataFrame, case3_curve: pd.DataFrame) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    common_start = max(pd.Timestamp(case2_curve["timestamp"].min()), pd.Timestamp(case3_curve["timestamp"].min()))
    common_end = min(pd.Timestamp(case2_curve["timestamp"].max()), pd.Timestamp(case3_curve["timestamp"].max()))
    case2 = case2_curve[(case2_curve["timestamp"] >= common_start) & (case2_curve["timestamp"] <= common_end)].copy()
    case3 = case3_curve[(case3_curve["timestamp"] >= common_start) & (case3_curve["timestamp"] <= common_end)].copy()
    merged = pd.merge(
        case2.rename(columns={"equity": "equity_case2"}),
        case3.rename(columns={"equity": "equity_case3"}),
        on="timestamp",
        how="inner",
    ).sort_values("timestamp").reset_index(drop=True)
    return merged, common_start, common_end


def build_half_mix(merged: pd.DataFrame) -> pd.DataFrame:
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret3 = merged["equity_case3"].astype(float).pct_change().fillna(0.0).to_numpy()
    cap2 = np.zeros(len(merged), dtype=float)
    cap3 = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)

    cap2[0] = PORTFOLIO_CAPITAL * 0.5
    cap3[0] = PORTFOLIO_CAPITAL * 0.5
    total[0] = cap2[0] + cap3[0]

    for i in range(1, len(merged)):
        cap2[i] = cap2[i - 1] * (1.0 + float(ret2[i]))
        cap3[i] = cap3[i - 1] * (1.0 + float(ret3[i]))
        total[i] = cap2[i] + cap3[i]

    out = merged[["timestamp"]].copy()
    out["equity"] = total
    out["cap_case2"] = cap2
    out["cap_case3"] = cap3
    return out


def save_plot(case2_curve: pd.DataFrame, case3_curve: pd.DataFrame, mix_curve: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.0]})
    ax_eq, ax_dd, ax_2026 = axes

    series = [
        (case2_curve, "case2_only", "#1f77b4"),
        (case3_curve, f"{CASE3_BEST_VARIANT}_only", "#d62728"),
        (mix_curve, "case2_case3best_half_mix", "#2ca02c"),
    ]

    for curve, label, color in series:
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.1, label=label, color=color)
        dd = curve["equity"].astype(float) / curve["equity"].cummax().astype(float) - 1.0
        ax_dd.plot(curve["timestamp"], -dd * 100.0, linewidth=1.0, label=label, color=color)

        seg = curve[pd.to_datetime(curve["timestamp"]) >= ANALYSIS_2026_START].copy()
        if not seg.empty:
            ax_2026.plot(seg["timestamp"], seg["equity"], linewidth=1.1, label=label, color=color)

    ax_eq.axhline(PORTFOLIO_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 127: Case2 vs 126 Best Case3 vs 50/50 Static Mix")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_dd.set_ylabel("Drawdown %")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="upper left")

    ax_2026.set_title("2026 Zoom")
    ax_2026.set_ylabel("Equity (USDT)")
    ax_2026.set_xlabel("Time")
    ax_2026.grid(True, alpha=0.2)
    ax_2026.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, common_start: pd.Timestamp, common_end: pd.Timestamp, cache_end_ts: pd.Timestamp) -> None:
    case2 = metrics_df.loc[metrics_df["variant"] == "case2_only"].iloc[0]
    case3 = metrics_df.loc[metrics_df["variant"] == f"{CASE3_BEST_VARIANT}_only"].iloc[0]
    mix = metrics_df.loc[metrics_df["variant"] == "case2_case3best_half_mix"].iloc[0]

    lines: list[str] = []
    lines.append("# 127 연구: case2 vs 126 best case3 vs 50:50 혼합")
    lines.append("")
    lines.append("## 설정")
    lines.append(f"- 공정 비교 구간: `{common_start}` ~ `{common_end}`")
    lines.append(f"- 로컬 최신 캐시 종료 시각: `{cache_end_ts}`")
    lines.append(f"- case3 후보는 126 raw-best인 `{CASE3_BEST_VARIANT}`를 사용했다.")
    lines.append("- 세 번째 곡선은 `case2 50% + case3best 50%`를 시작 시점에 고정한 정적 혼합이다.")
    lines.append("- 리밸런싱 없이 보유 비중만 고정했다.")
    lines.append("")
    lines.append("## 결과")
    lines.append("| Variant | Final Equity | Total Return % | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['total_return_pct'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {_fmt(row['return_2026_pct'])} | {_fmt(row['mdd_2026_pct'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append(
        f"- 수익 극대화 기준으로는 `{CASE3_BEST_VARIANT}_only`가 가장 강했다. "
        f"CAGR `{_fmt(case3['cagr_pct'])}%`, final equity `{_fmt(case3['final_equity'])}`."
    )
    lines.append(
        f"- 방어 효율까지 보면 `case2_case3best_half_mix`가 꽤 좋다. "
        f"CAGR `{_fmt(mix['cagr_pct'])}%`, MDD `{_fmt(mix['max_drawdown_pct'])}%`, Calmar `{_fmt(mix['calmar_ratio'])}`."
    )
    lines.append(
        f"- `case2_only`는 여전히 의미가 있지만, 지금 비교에선 알파의 중심이 아니라 완충재에 더 가깝다. "
        f"CAGR `{_fmt(case2['cagr_pct'])}%`, MDD `{_fmt(case2['max_drawdown_pct'])}%`."
    )
    lines.append(
        f"- 2026만 보면 `case3best`가 그대로 제일 강한지는 별도로 봐야 한다. "
        f"`case3best 2026 = {_fmt(case3['return_2026_pct'])}%`, `mix 2026 = {_fmt(mix['return_2026_pct'])}%`, "
        f"`case2 2026 = {_fmt(case2['return_2026_pct'])}%`."
    )
    lines.append("")
    lines.append("## 결론")
    lines.append("- `case3best 단독`은 고CAGR 코어 후보다.")
    lines.append("- `case2 + case3best 50:50`은 CAGR을 조금 내주고 MDD를 줄이는 타협안이다.")
    lines.append("- 앞으로 포트폴리오화할 때는 `case3best`를 코어로 두고 `case2`를 완충 슬리브로 얹는 방향이 자연스럽다.")
    lines.append("")
    lines.append("## 출력물")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    case2_curve, cache_end_ts = load_case2_curve()
    case3_curve = load_case3_best_curve()
    merged, common_start, common_end = align_curves(case2_curve, case3_curve)

    case2 = merged[["timestamp", "equity_case2"]].rename(columns={"equity_case2": "equity"}).copy()
    case3 = merged[["timestamp", "equity_case3"]].rename(columns={"equity_case3": "equity"}).copy()
    mix = build_half_mix(merged)

    metrics_rows = []
    curve_rows = []
    for variant, curve in [
        ("case2_only", case2),
        (f"{CASE3_BEST_VARIANT}_only", case3),
        ("case2_case3best_half_mix", mix[["timestamp", "equity"]].copy()),
    ]:
        overall = compute_curve_stats(curve, "equity", PORTFOLIO_CAPITAL)
        stats_2026 = compute_window_stats(curve, ANALYSIS_2026_START)
        metrics_rows.append({"variant": variant, **overall, "return_2026_pct": stats_2026["return_pct"], "mdd_2026_pct": stats_2026["mdd_pct"]})
        curve_out = curve.copy()
        curve_out["variant"] = variant
        curve_rows.append(curve_out)

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    pd.concat(curve_rows, ignore_index=True).to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")
    save_plot(case2, case3, mix)
    save_report(metrics_df, common_start, common_end, cache_end_ts)

    print(f"[127] Common period: {common_start} -> {common_end}")
    for _, row in metrics_df.iterrows():
        print(
            f"[127] {row['variant']}: CAGR={_fmt(row['cagr_pct'])}% "
            f"MDD={_fmt(row['max_drawdown_pct'])}% Calmar={_fmt(row['calmar_ratio'])} "
            f"2026={_fmt(row['return_2026_pct'])}%"
        )
    print(f"[127] Outputs: {OUT_PNG}, {OUT_CSV}, {OUT_CURVES_CSV}, {OUT_MD}")


if __name__ == "__main__":
    main()
