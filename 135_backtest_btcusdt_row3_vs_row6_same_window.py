from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent

BASE_74_PATH = ROOT / "74_backtest_btcusdt_scale06_adx002_case3_three_sleeve_grid.py"
BASE_76_PATH = ROOT / "76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py"
BASE_114_PATH = ROOT / "114_backtest_btcusdt_best_with_sr_smc_filters.py"
BASE_116_PATH = ROOT / "116_backtest_btcusdt_case123_portfolio_with_115_case3.py"
BASE_117_PATH = ROOT / "117_backtest_btcusdt_115_highcagr_push.py"
BASE_120_PATH = ROOT / "120_backtest_btcusdt_case123_fine_tune_rebalance_and_weights.py"
BASE_126_PATH = ROOT / "126_backtest_btcusdt_case3_long_quality_push.py"
BASE_47_PATH = ROOT / "47_backtest_btcusdt_scale06_adx002_case1_standalone.py"
BASE_111_PATH = ROOT / "111_backtest_btcusdt_sr_smc_5m_profitmax.py"

OUT_BASE = "135_backtest_btcusdt_row3_vs_row6_same_window"
OUT_CSV = ROOT / f"{OUT_BASE}.csv"
OUT_MD = ROOT / f"{OUT_BASE}.md"
OUT_PNG = ROOT / f"{OUT_BASE}.png"
OUT_CURVES_CSV = ROOT / f"{OUT_BASE}_curves.csv"

START_TS = pd.Timestamp("2022-01-01 08:00:00")
END_TS = pd.Timestamp("2026-02-12 00:00:00")
ANALYSIS_2026_START = pd.Timestamp("2026-01-01 00:00:00")
INITIAL_CAPITAL = 2000.0

ROW3_VARIANT = "lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_24_30"
ROW6_VARIANT = "lb4_delay8_capna_cd0"
ROW3_CASE3_NAME = "lv3p0_g12_body25_tp20_lb5_none_case3"


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


def compute_curve_stats(curve: pd.DataFrame, equity_col: str, initial_capital: float) -> dict[str, float]:
    series = curve[equity_col].astype(float)
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


def compute_window_stats(curve: pd.DataFrame, equity_col: str, start_ts: pd.Timestamp) -> dict[str, float]:
    seg = curve[curve["timestamp"] >= pd.Timestamp(start_ts)].copy()
    if seg.empty:
        return {"window_return_pct": np.nan, "window_mdd_pct": np.nan}
    series = seg[equity_col].astype(float)
    start_eq = float(series.iloc[0])
    end_eq = float(series.iloc[-1])
    drawdown = series / series.cummax() - 1.0
    return {
        "window_return_pct": (end_eq / start_eq - 1.0) * 100.0,
        "window_mdd_pct": float(-drawdown.min() * 100.0),
    }


def build_row3_curve() -> tuple[pd.DataFrame, dict[str, float]]:
    s74 = load_module("study74_for_135", BASE_74_PATH)
    m116 = load_module("study116_for_135", BASE_116_PATH)
    m120 = load_module("study120_for_135", BASE_120_PATH)

    case1, case2 = m116.load_case12_resampled(s74)
    case3_map = m120.load_case3_curves(m116)
    case3 = case3_map[ROW3_CASE3_NAME]
    merged = m116.build_merged(case1, case2, case3, ROW3_CASE3_NAME)
    merged = merged[(merged["timestamp"] >= START_TS) & (merged["timestamp"] <= END_TS)].copy().reset_index(drop=True)
    if merged.empty:
        raise RuntimeError("Row 3 merged curve window is empty.")

    curve, extras = m120.run_three_sleeve_custom_rebalance(
        merged=merged,
        case3_name=ROW3_CASE3_NAME,
        w1=0.46,
        w2=0.24,
        w3=0.30,
        rebalance_rule="30min",
        initial_capital_total=INITIAL_CAPITAL,
        fee_rate=m116.REBALANCE_FEE_RATE,
    )
    curve = curve[["timestamp", "equity_total"]].rename(columns={"equity_total": "equity"}).copy()
    curve["variant"] = ROW3_VARIANT
    return curve, extras


def build_row6_curve() -> tuple[pd.DataFrame, dict[str, float]]:
    m47 = load_module("study47_for_135", BASE_47_PATH)
    s76 = load_module("study76_for_135", BASE_76_PATH)
    m111 = load_module("study111_for_135", BASE_111_PATH)
    m114 = load_module("study114_for_135", BASE_114_PATH)
    m117 = load_module("study117_for_135", BASE_117_PATH)
    m126 = load_module("study126_for_135", BASE_126_PATH)

    df_1m, df_4h, _ = m114.load_market_data_2021plus()
    market = m114.prepare_market_114(df_1m.copy(), df_4h.copy(), m47, m111)
    market = market[(market["timestamp"] >= START_TS) & (market["timestamp"] <= END_TS)].copy().reset_index(drop=True)
    if market.empty:
        raise RuntimeError("Row 6 market window is empty.")

    original_initial_capital = s76.INITIAL_CAPITAL
    try:
        s76.INITIAL_CAPITAL = INITIAL_CAPITAL
        cfg = next(cfg for cfg in m126.build_variants() if cfg["variant"] == ROW6_VARIANT)
        curve, extras = m126.run_variant_126(market, cfg, s76, m117)
    finally:
        s76.INITIAL_CAPITAL = original_initial_capital

    curve = curve[["timestamp", "equity"]].copy()
    curve["variant"] = ROW6_VARIANT
    return curve, extras


def save_plot(curves: dict[str, pd.DataFrame], metrics_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.3, 1.0, 1.0]})
    ax_eq, ax_dd, ax_bar = axes

    colors = {
        ROW3_VARIANT: "#1f77b4",
        ROW6_VARIANT: "#d62728",
    }

    for variant, curve in curves.items():
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.2, label=variant, color=colors[variant])
    ax_eq.axhline(INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 135: 134 Table Row 3 vs Row 6 On The Same Window")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    for variant, curve in curves.items():
        series = curve["equity"].astype(float)
        dd = (series / series.cummax() - 1.0) * 100.0
        ax_dd.plot(curve["timestamp"], dd, linewidth=1.0, label=variant, color=colors[variant])
    ax_dd.set_ylabel("Drawdown %")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="lower left")

    bar_positions = np.arange(len(metrics_df))
    width = 0.36
    ax_bar.bar(bar_positions - width / 2, metrics_df["cagr_pct"], width=width, color="#1f77b4", label="CAGR %")
    ax_bar.set_ylabel("CAGR %")
    ax_bar.set_xticks(bar_positions)
    ax_bar.set_xticklabels(metrics_df["label"], rotation=0)
    ax_bar.grid(True, axis="y", alpha=0.2)
    ax_bar_t = ax_bar.twinx()
    ax_bar_t.bar(bar_positions + width / 2, metrics_df["max_drawdown_pct"], width=width, color="#d62728", alpha=0.85, label="MDD %")
    ax_bar_t.set_ylabel("MDD %")
    h1, l1 = ax_bar.get_legend_handles_labels()
    h2, l2 = ax_bar_t.get_legend_handles_labels()
    ax_bar.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame) -> None:
    row3 = metrics_df.loc[metrics_df["variant"] == ROW3_VARIANT].iloc[0]
    row6 = metrics_df.loc[metrics_df["variant"] == ROW6_VARIANT].iloc[0]

    cagr_winner = row3 if row3["cagr_pct"] > row6["cagr_pct"] else row6
    calmar_winner = row3 if row3["calmar_ratio"] > row6["calmar_ratio"] else row6
    mdd_winner = row3 if row3["max_drawdown_pct"] < row6["max_drawdown_pct"] else row6
    y2026_winner = row3 if row3["return_2026_pct"] > row6["return_2026_pct"] else row6

    lines: list[str] = []
    lines.append("# 135번 연구: 134 최고전략표 3행 vs 6행 같은 구간 정면 비교")
    lines.append("")
    lines.append("## 비교 대상")
    lines.append(f"- 3행: study 120 포트폴리오 `{ROW3_VARIANT}`")
    lines.append(f"- 6행: study 126 raw case3 `{ROW6_VARIANT}`")
    lines.append("- 목적은 서로 다른 기간에서 뽑힌 숫자를 그대로 보지 말고, 완전히 같은 창에서 다시 비교하는 것이다.")
    lines.append(f"- 공통 비교 구간: `{START_TS}` ~ `{END_TS}`")
    lines.append(f"- 시작 자본은 둘 다 `{INITIAL_CAPITAL:.0f}` USDT로 맞췄다.")
    lines.append("")
    lines.append("## 결과 표")
    lines.append("")
    lines.append("| Strategy | Final Equity | Total Return % | CAGR % | MDD % | Calmar | 2026 YTD Return % | 2026 YTD MDD % |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['label']} | {_fmt(row['final_equity'])} | {_fmt(row['total_return_pct'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {_fmt(row['return_2026_pct'])} | {_fmt(row['mdd_2026_pct'])} |"
        )
    lines.append("")
    lines.append("## 핵심 해석")
    lines.append(
        f"- CAGR 우위는 `{cagr_winner['label']}`였다. "
        f"`{_fmt(cagr_winner['cagr_pct'])}%`로 다른 쪽 대비 `{_fmt(abs(row3['cagr_pct'] - row6['cagr_pct']))}pp` 차이가 났다."
    )
    lines.append(
        f"- MDD 방어 우위는 `{mdd_winner['label']}`였다. "
        f"MDD `{_fmt(mdd_winner['max_drawdown_pct'])}%`로 더 낮았다."
    )
    lines.append(
        f"- Calmar 우위는 `{calmar_winner['label']}`였다. "
        f"즉 이 구간에선 단순 CAGR뿐 아니라 위험 대비 효율도 `{calmar_winner['label']}` 쪽이 더 좋았다."
    )
    lines.append(
        f"- 2026 YTD 방어는 `{y2026_winner['label']}`가 더 나았다. "
        f"2026 수익률 `{_fmt(y2026_winner['return_2026_pct'])}%`, 2026 MDD `{_fmt(y2026_winner['mdd_2026_pct'])}%`였다."
    )
    lines.append("")
    lines.append("## 전략 성격 차이")
    lines.append(
        f"- `{ROW3_VARIANT}`는 case1/case2/case3를 `46/24/30`으로 섞고 `30분`마다 리밸런스하는 포트폴리오라, "
        "하나의 강한 엔진을 밀기보다 여러 슬리브가 서로의 drawdown을 상쇄하는 구조다."
    )
    lines.append(
        f"- `{ROW6_VARIANT}`는 3배 regime-hold 성격의 단일 case3 엔진이라, "
        "포트폴리오 완충 없이 방향성이 맞을 때 강하게 치고 나가지만 흔들릴 때 낙폭도 더 크게 받는다."
    )
    lines.append("")
    lines.append("## 내가 읽는 결론")
    if row3["calmar_ratio"] > row6["calmar_ratio"] and row3["cagr_pct"] >= row6["cagr_pct"]:
        lines.append("- 같은 구간에서도 3행이 CAGR과 위험조정 성과를 모두 이겼다. 그러면 3행이 사실상 상위 호환에 가깝다.")
    elif row6["cagr_pct"] > row3["cagr_pct"] and row3["max_drawdown_pct"] < row6["max_drawdown_pct"]:
        lines.append("- 6행은 여전히 더 공격적인 수익 엔진이고, 3행은 그 수익을 일부 덜어내는 대신 MDD를 낮춘 실전형이라고 보는 게 맞다.")
    else:
        lines.append("- 둘의 우열이 한쪽으로 완전히 기울진 않았고, 수익 우선인지 낙폭 우선인지에 따라 선택이 갈린다.")
    lines.append("- 그래서 실제 배치라면 3행을 기본형으로 보고, 6행은 더 공격적인 별도 엔진 혹은 포트폴리오의 고알파 코어로 보는 해석이 자연스럽다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- Metrics CSV: `{OUT_CSV.name}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV.name}`")
    lines.append(f"- Plot: `{OUT_PNG.name}`")
    lines.append(f"- Report: `{OUT_MD.name}`")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    row3_curve, row3_extras = build_row3_curve()
    row6_curve, row6_extras = build_row6_curve()

    common_start = max(pd.Timestamp(row3_curve["timestamp"].min()), pd.Timestamp(row6_curve["timestamp"].min()))
    common_end = min(pd.Timestamp(row3_curve["timestamp"].max()), pd.Timestamp(row6_curve["timestamp"].max()))

    row3_curve = row3_curve[(row3_curve["timestamp"] >= common_start) & (row3_curve["timestamp"] <= common_end)].copy().reset_index(drop=True)
    row6_curve = row6_curve[(row6_curve["timestamp"] >= common_start) & (row6_curve["timestamp"] <= common_end)].copy().reset_index(drop=True)

    row3_stats = compute_curve_stats(row3_curve, "equity", INITIAL_CAPITAL)
    row3_2026 = compute_window_stats(row3_curve, "equity", ANALYSIS_2026_START)
    row6_stats = compute_curve_stats(row6_curve, "equity", INITIAL_CAPITAL)
    row6_2026 = compute_window_stats(row6_curve, "equity", ANALYSIS_2026_START)

    metrics = [
        {
            "label": "row3_study120_portfolio",
            "variant": ROW3_VARIANT,
            **row3_stats,
            "return_2026_pct": row3_2026["window_return_pct"],
            "mdd_2026_pct": row3_2026["window_mdd_pct"],
            "rebalance_count": int(row3_extras["rebalance_count"]),
            "fee_paid": float(row3_extras["fee_paid"]),
            "trades": np.nan,
        },
        {
            "label": "row6_study126_case3",
            "variant": ROW6_VARIANT,
            **row6_stats,
            "return_2026_pct": row6_2026["window_return_pct"],
            "mdd_2026_pct": row6_2026["window_mdd_pct"],
            "rebalance_count": np.nan,
            "fee_paid": np.nan,
            "trades": int(row6_extras["trades"]),
            "long_entries": int(row6_extras["long_entries"]),
            "short_entries": int(row6_extras["short_entries"]),
        },
    ]
    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    curves_out = pd.concat([row3_curve, row6_curve], ignore_index=True)
    curves_out.to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")
    save_plot({ROW3_VARIANT: row3_curve, ROW6_VARIANT: row6_curve}, metrics_df)
    save_report(metrics_df)

    print(f"[135] Common window: {common_start} -> {common_end}")
    for _, row in metrics_df.iterrows():
        print(
            f"[135] {row['label']}: CAGR={_fmt(row['cagr_pct'])}% "
            f"MDD={_fmt(row['max_drawdown_pct'])}% Calmar={_fmt(row['calmar_ratio'])} "
            f"2026={_fmt(row['return_2026_pct'])}%"
        )
    print(f"[135] Outputs: {OUT_CSV.name}, {OUT_MD.name}, {OUT_PNG.name}, {OUT_CURVES_CSV.name}")


if __name__ == "__main__":
    main()
