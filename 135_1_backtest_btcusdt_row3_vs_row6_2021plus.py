from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent

OUT_BASE = "135_1_backtest_btcusdt_row3_vs_row6_2021plus"
OUT_CSV = ROOT / f"{OUT_BASE}.csv"
OUT_MD = ROOT / f"{OUT_BASE}.md"
OUT_PNG = ROOT / f"{OUT_BASE}.png"
OUT_CURVES_CSV = ROOT / f"{OUT_BASE}_curves.csv"

ROW3_SOURCE = ROOT / "121_backtest_btcusdt_solo_vs_current_mix_2021plus_curves.csv"
ROW6_SOURCE = ROOT / "126_backtest_btcusdt_case3_long_quality_push_curves.csv"

ROW3_VARIANT = "study120_current_mix"
ROW6_VARIANT = "lb4_delay8_capna_cd0"
START_CAPITAL = 2000.0
ANALYSIS_2026_START = pd.Timestamp("2026-01-01 00:00:00")


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def load_variant_curve(path: Path, variant: str, equity_col: str, chunksize: int = 300_000) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for chunk in pd.read_csv(path, usecols=["timestamp", equity_col, "variant"], chunksize=chunksize):
        ref = chunk[chunk["variant"] == variant].copy()
        if not ref.empty:
            parts.append(ref)
    if not parts:
        raise RuntimeError(f"Could not find variant {variant} in {path.name}")
    curve = pd.concat(parts, ignore_index=True)
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)
    curve = curve.rename(columns={equity_col: "equity"})
    return curve[["timestamp", "equity"]]


def compute_curve_stats(curve: pd.DataFrame, initial_capital: float) -> dict[str, float | pd.Timestamp]:
    series = curve["equity"].astype(float)
    final_equity = float(series.iloc[-1])
    total_return_pct = (final_equity / float(initial_capital) - 1.0) * 100.0
    elapsed_days = (curve["timestamp"].iloc[-1] - curve["timestamp"].iloc[0]).total_seconds() / 86400.0
    years = max(elapsed_days / 365.25, 1e-9)
    cagr_pct = ((final_equity / float(initial_capital)) ** (1.0 / years) - 1.0) * 100.0
    drawdown = series / series.cummax() - 1.0
    max_drawdown_pct = float(-drawdown.min() * 100.0)
    calmar_ratio = float(cagr_pct / max_drawdown_pct) if max_drawdown_pct > 0 else np.nan
    peak_idx = series.cummax().idxmax()
    trough_idx = drawdown.idxmin()
    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "calmar_ratio": calmar_ratio,
        "peak_ts": pd.Timestamp(curve.loc[peak_idx, "timestamp"]),
        "peak_equity": float(series.loc[peak_idx]),
        "trough_ts": pd.Timestamp(curve.loc[trough_idx, "timestamp"]),
        "trough_equity": float(series.loc[trough_idx]),
    }


def compute_window_stats(curve: pd.DataFrame, start_ts: pd.Timestamp) -> dict[str, float]:
    seg = curve[curve["timestamp"] >= start_ts].copy()
    if seg.empty:
        return {"window_return_pct": np.nan, "window_mdd_pct": np.nan}
    series = seg["equity"].astype(float)
    start_eq = float(series.iloc[0])
    end_eq = float(series.iloc[-1])
    drawdown = series / series.cummax() - 1.0
    return {
        "window_return_pct": (end_eq / start_eq - 1.0) * 100.0,
        "window_mdd_pct": float(-drawdown.min() * 100.0),
    }


def save_plot(curves: dict[str, pd.DataFrame], metrics_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.3, 1.0, 1.0]})
    ax_eq, ax_dd, ax_bar = axes

    colors = {
        ROW3_VARIANT: "#1f77b4",
        ROW6_VARIANT: "#d62728",
    }
    labels = {
        ROW3_VARIANT: "row3_2021plus_study120_mix",
        ROW6_VARIANT: "row6_2021plus_study126_case3",
    }

    for variant, curve in curves.items():
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.1, color=colors[variant], label=labels[variant])
    ax_eq.axhline(START_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 135_1: 134 Table Row 3 vs Row 6 On 2021+ Common Window")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    for variant, curve in curves.items():
        dd = (curve["equity"].astype(float) / curve["equity"].astype(float).cummax() - 1.0) * 100.0
        ax_dd.plot(curve["timestamp"], dd, linewidth=1.0, color=colors[variant], label=labels[variant])
    ax_dd.set_ylabel("Drawdown %")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="lower left")

    xpos = np.arange(len(metrics_df))
    width = 0.36
    ax_bar.bar(xpos - width / 2, metrics_df["cagr_pct"], width=width, color="#1f77b4", label="CAGR %")
    ax_bar.set_ylabel("CAGR %")
    ax_bar.set_xticks(xpos)
    ax_bar.set_xticklabels(metrics_df["label"])
    ax_bar.grid(True, axis="y", alpha=0.2)
    ax_bar_t = ax_bar.twinx()
    ax_bar_t.bar(xpos + width / 2, metrics_df["max_drawdown_pct"], width=width, color="#d62728", alpha=0.85, label="MDD %")
    ax_bar_t.set_ylabel("MDD %")
    h1, l1 = ax_bar.get_legend_handles_labels()
    h2, l2 = ax_bar_t.get_legend_handles_labels()
    ax_bar.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, common_start: pd.Timestamp, common_end: pd.Timestamp) -> None:
    row3 = metrics_df.loc[metrics_df["variant"] == ROW3_VARIANT].iloc[0]
    row6 = metrics_df.loc[metrics_df["variant"] == ROW6_VARIANT].iloc[0]

    cagr_winner = row3 if row3["cagr_pct"] > row6["cagr_pct"] else row6
    calmar_winner = row3 if row3["calmar_ratio"] > row6["calmar_ratio"] else row6
    mdd_winner = row3 if row3["max_drawdown_pct"] < row6["max_drawdown_pct"] else row6
    y2026_winner = row3 if row3["return_2026_pct"] > row6["return_2026_pct"] else row6

    lines: list[str] = []
    lines.append("# 135_1번 연구: 134 최고전략표 3행 vs 6행을 2021~로컬최신까지 다시 비교")
    lines.append("")
    lines.append("## 비교 대상")
    lines.append(f"- 3행 2021+ 복원본: `{ROW3_VARIANT}` from study 121")
    lines.append(f"- 6행 2021+ raw engine: `{ROW6_VARIANT}` from study 126")
    lines.append("- 이번 비교는 두 전략을 모두 `2000 USDT` 기준으로 맞췄다.")
    lines.append("- 6행은 원본 126 curve가 `1000 USDT` 시작이라, 같은 비교를 위해 equity를 `x2` 스케일링했다.")
    lines.append(f"- 공통 비교 구간은 `{common_start}` ~ `{common_end}` 이다.")
    lines.append("- 참고로 오늘 날짜는 `2026-04-12`이지만, 로컬 최신 BTC 1분 캐시는 `2026-03-15`까지만 있다.")
    lines.append("")
    lines.append("## 결과 표")
    lines.append("")
    lines.append("| Strategy | Final Equity | Total Return % | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['label']} | {_fmt(row['final_equity'])} | {_fmt(row['total_return_pct'])} | "
            f"{_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{_fmt(row['return_2026_pct'])} | {_fmt(row['mdd_2026_pct'])} |"
        )
    lines.append("")
    lines.append("## 핵심 해석")
    lines.append(
        f"- CAGR 우위는 `{cagr_winner['label']}`였다. `{_fmt(cagr_winner['cagr_pct'])}%`로 더 높았다."
    )
    lines.append(
        f"- MDD 방어 우위는 `{mdd_winner['label']}`였다. MDD `{_fmt(mdd_winner['max_drawdown_pct'])}%`로 더 낮았다."
    )
    lines.append(
        f"- Calmar 우위는 `{calmar_winner['label']}`였다. 위험조정 효율은 이쪽이 더 좋았다."
    )
    lines.append(
        f"- 2026 구간 수익 우위는 `{y2026_winner['label']}`였다. 2026 return `{_fmt(y2026_winner['return_2026_pct'])}%`."
    )
    lines.append("")
    lines.append("## 읽는 방법")
    lines.append("- 3행은 `case1/case2/case3`를 섞은 포트폴리오라 변동을 깎는 대신 최고 수익을 일부 포기한다.")
    lines.append("- 6행은 단일 case3 엔진이라 방향이 맞을 때 더 강하지만, drawdown도 더 크게 받는다.")
    lines.append("- 따라서 2021+ 전체 구간에서도 핵심 구도는 그대로다. `6행 = 고수익 엔진`, `3행 = 실전형 완충 포트폴리오`.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- Metrics CSV: `{OUT_CSV.name}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV.name}`")
    lines.append(f"- Plot: `{OUT_PNG.name}`")
    lines.append(f"- Report: `{OUT_MD.name}`")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    row3_curve = load_variant_curve(ROW3_SOURCE, ROW3_VARIANT, "equity")
    row6_curve = load_variant_curve(ROW6_SOURCE, ROW6_VARIANT, "equity")

    row6_curve["equity"] = row6_curve["equity"].astype(float) * (START_CAPITAL / 1000.0)

    common_start = max(pd.Timestamp(row3_curve["timestamp"].min()), pd.Timestamp(row6_curve["timestamp"].min()))
    common_end = min(pd.Timestamp(row3_curve["timestamp"].max()), pd.Timestamp(row6_curve["timestamp"].max()))

    row3_curve = row3_curve[(row3_curve["timestamp"] >= common_start) & (row3_curve["timestamp"] <= common_end)].copy().reset_index(drop=True)
    row6_curve = row6_curve[(row6_curve["timestamp"] >= common_start) & (row6_curve["timestamp"] <= common_end)].copy().reset_index(drop=True)

    row3_stats = compute_curve_stats(row3_curve, START_CAPITAL)
    row3_2026 = compute_window_stats(row3_curve, ANALYSIS_2026_START)
    row6_stats = compute_curve_stats(row6_curve, START_CAPITAL)
    row6_2026 = compute_window_stats(row6_curve, ANALYSIS_2026_START)

    metrics_df = pd.DataFrame(
        [
            {
                "label": "row3_2021plus_study120_mix",
                "variant": ROW3_VARIANT,
                **row3_stats,
                "return_2026_pct": row3_2026["window_return_pct"],
                "mdd_2026_pct": row3_2026["window_mdd_pct"],
            },
            {
                "label": "row6_2021plus_study126_case3",
                "variant": ROW6_VARIANT,
                **row6_stats,
                "return_2026_pct": row6_2026["window_return_pct"],
                "mdd_2026_pct": row6_2026["window_mdd_pct"],
            },
        ]
    )
    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    curves_out = pd.concat(
        [
            row3_curve.assign(variant=ROW3_VARIANT),
            row6_curve.assign(variant=ROW6_VARIANT),
        ],
        ignore_index=True,
    )
    curves_out.to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")

    save_plot(
        {
            ROW3_VARIANT: row3_curve,
            ROW6_VARIANT: row6_curve,
        },
        metrics_df,
    )
    save_report(metrics_df, common_start, common_end)

    print(f"[135_1] Common window: {common_start} -> {common_end}")
    for _, row in metrics_df.iterrows():
        print(
            f"[135_1] {row['label']}: CAGR={_fmt(row['cagr_pct'])}% "
            f"MDD={_fmt(row['max_drawdown_pct'])}% Calmar={_fmt(row['calmar_ratio'])} "
            f"2026={_fmt(row['return_2026_pct'])}%"
        )
    print(f"[135_1] Outputs: {OUT_CSV.name}, {OUT_MD.name}, {OUT_PNG.name}, {OUT_CURVES_CSV.name}")


if __name__ == "__main__":
    main()
