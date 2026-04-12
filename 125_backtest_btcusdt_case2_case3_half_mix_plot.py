from __future__ import annotations

import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_122_PATH = Path("122_backtest_btcusdt_practical_rebalance_weight_sweep_2021plus.py")
SLEEVE_CACHE = Path("122_backtest_btcusdt_practical_rebalance_weight_sweep_2021plus_sleeve_state.pkl")

OUT_BASE = "125_backtest_btcusdt_case2_case3_half_mix_plot"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")

PORTFOLIO_CAPITAL = 2000.0


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


def load_sleeve_cache() -> dict:
    if not SLEEVE_CACHE.exists():
        raise FileNotFoundError(f"Missing sleeve cache: {SLEEVE_CACHE}")
    with SLEEVE_CACHE.open("rb") as f:
        return pickle.load(f)


def align_case2_case3(cache: dict) -> pd.DataFrame:
    case2 = cache["case2_state"].copy()
    case3 = cache["case3_state"].copy()
    case2["timestamp"] = pd.to_datetime(case2["timestamp"])
    case3["timestamp"] = pd.to_datetime(case3["timestamp"])

    common_start = max(pd.Timestamp(case2["timestamp"].min()), pd.Timestamp(case3["timestamp"].min()))
    common_end = min(pd.Timestamp(case2["timestamp"].max()), pd.Timestamp(case3["timestamp"].max()))

    case2 = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy()
    case3 = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)].copy()

    merged = pd.merge(
        case2.rename(columns={"equity": "equity_case2", "active": "active_case2"}),
        case3.rename(columns={"equity": "equity_case3", "active": "active_case3"}),
        on="timestamp",
        how="inner",
    ).sort_values("timestamp").reset_index(drop=True)
    return merged


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
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0]})
    ax_eq, ax_dd = axes

    for curve, label, color in [
        (case2_curve, "case2_only", "#1f77b4"),
        (case3_curve, "case3_only", "#d62728"),
        (mix_curve, "case2_case3_half_mix", "#2ca02c"),
    ]:
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.1, label=label, color=color)
        dd = curve["equity"].astype(float) / curve["equity"].cummax().astype(float) - 1.0
        ax_dd.plot(curve["timestamp"], -dd * 100.0, linewidth=1.0, label=label, color=color)

    ax_eq.axhline(PORTFOLIO_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 125: Case2 vs Case3 vs 50/50 Static Mix")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_dd.set_ylabel("Drawdown %")
    ax_dd.set_xlabel("Time")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, common_start: pd.Timestamp, common_end: pd.Timestamp, cache_end_ts: pd.Timestamp) -> None:
    case2 = metrics_df.loc[metrics_df["variant"] == "case2_only"].iloc[0]
    case3 = metrics_df.loc[metrics_df["variant"] == "case3_only"].iloc[0]
    mix = metrics_df.loc[metrics_df["variant"] == "case2_case3_half_mix"].iloc[0]

    lines: list[str] = []
    lines.append("# 125 연구: case2 / case3 / 50:50 정적 혼합 비교")
    lines.append("")
    lines.append("## 구간")
    lines.append(f"- 공정 비교 구간: `{common_start}` ~ `{common_end}`")
    lines.append(f"- 로컬 최신 캐시 종료 시각: `{cache_end_ts}`")
    lines.append("- 리밸런싱 없이 시작 시점에 `case2 50% + case3 50%`로 고정한 정적 혼합을 함께 비교했다.")
    lines.append("")
    lines.append("## 결과")
    lines.append("| Variant | Final Equity | Total Return % | CAGR % | MDD % | Calmar |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['total_return_pct'])} | "
            f"{_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append(
        f"- CAGR 기준으로는 `case3_only ({_fmt(case3['cagr_pct'])}%)`가 `case2_only ({_fmt(case2['cagr_pct'])}%)`와 "
        f"`50:50 mix ({_fmt(mix['cagr_pct'])}%)`를 모두 앞섰다."
    )
    lines.append(
        f"- MDD도 `case3_only ({_fmt(case3['max_drawdown_pct'])}%)`가 `case2_only ({_fmt(case2['max_drawdown_pct'])}%)`보다 낮았다."
    )
    lines.append(
        f"- `50:50 mix`는 `case2`보다 훨씬 좋아졌지만, 결국 `case3`의 알파를 희석해서 CAGR이 `{_fmt(case3['cagr_pct'] - mix['cagr_pct'])}%p` 낮아졌다."
    )
    lines.append("- 정리하면 현재 2021~최신 구간에서는 `case3가 메인 엔진`, `case2는 완충재`, `반반 혼합은 중간 성격`으로 보는 게 맞다.")
    lines.append("")
    lines.append("## 출력물")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    cache = load_sleeve_cache()
    merged = align_case2_case3(cache)
    cache_end_ts = pd.Timestamp(cache["cache_end_ts"])
    common_start = pd.Timestamp(merged["timestamp"].min())
    common_end = pd.Timestamp(merged["timestamp"].max())

    case2_curve = merged[["timestamp", "equity_case2"]].rename(columns={"equity_case2": "equity"}).copy()
    case3_curve = merged[["timestamp", "equity_case3"]].rename(columns={"equity_case3": "equity"}).copy()
    mix_curve = build_half_mix(merged)

    metrics_rows = []
    for variant, curve in [
        ("case2_only", case2_curve),
        ("case3_only", case3_curve),
        ("case2_case3_half_mix", mix_curve[["timestamp", "equity"]].copy()),
    ]:
        stats = compute_curve_stats(curve, "equity", PORTFOLIO_CAPITAL)
        metrics_rows.append({"variant": variant, **stats})

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    save_plot(case2_curve, case3_curve, mix_curve)
    save_report(metrics_df, common_start, common_end, cache_end_ts)

    print(f"[125] Common period: {common_start} -> {common_end}")
    for _, row in metrics_df.iterrows():
        print(
            f"[125] {row['variant']}: CAGR={_fmt(row['cagr_pct'])}% "
            f"MDD={_fmt(row['max_drawdown_pct'])}% Calmar={_fmt(row['calmar_ratio'])}"
        )
    print(f"[125] Outputs: {OUT_PNG}, {OUT_CSV}, {OUT_MD}")


if __name__ == "__main__":
    main()
