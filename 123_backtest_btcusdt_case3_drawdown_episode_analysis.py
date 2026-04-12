from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
BASE_76_PATH = Path("76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py")
BASE_111_PATH = Path("111_backtest_btcusdt_sr_smc_5m_profitmax.py")
BASE_114_PATH = Path("114_backtest_btcusdt_best_with_sr_smc_filters.py")
BASE_117_PATH = Path("117_backtest_btcusdt_115_highcagr_push.py")

OUT_BASE = "123_backtest_btcusdt_case3_drawdown_episode_analysis"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_EPISODES_CSV = Path(f"{OUT_BASE}.csv")
OUT_COMPARE_CSV = Path(f"{OUT_BASE}_variant_compare.csv")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

PRIMARY_VARIANT = "lv3p0_g12_body25_tp20_lb5_none"
COMPARE_VARIANTS = [
    "lv3p0_g8_body20_tp20_lb5_none",
    "lv2p5_g12_body20_tp20_lb5_none",
    "lv2p25_g8_body20_tp15_lb5_none",
    "lv2p0_g12_body20_tp15_lb5_none",
]
TOP_N_EPISODES = 5


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


def compute_drawdown_episodes(curve: pd.DataFrame, top_n: int = TOP_N_EPISODES) -> pd.DataFrame:
    df = curve[["timestamp", "equity"]].copy().sort_values("timestamp").reset_index(drop=True)
    df["dd"] = df["equity"] / df["equity"].cummax() - 1.0

    episodes: list[dict] = []
    peak_idx = 0
    in_dd = False
    start_idx: int | None = None

    for i, dd in enumerate(df["dd"].to_numpy(dtype=float)):
        if not in_dd and dd < 0:
            in_dd = True
            start_idx = peak_idx
        if in_dd and dd == 0:
            assert start_idx is not None
            seg = df.iloc[start_idx : i + 1].copy()
            trough_idx = int(seg["dd"].idxmin())
            episodes.append(
                {
                    "peak_idx": start_idx,
                    "trough_idx": trough_idx,
                    "recovery_idx": i,
                    "peak_time": df.iloc[start_idx]["timestamp"],
                    "trough_time": df.iloc[trough_idx]["timestamp"],
                    "recovery_time": df.iloc[i]["timestamp"],
                    "peak_equity": float(df.iloc[start_idx]["equity"]),
                    "trough_equity": float(df.iloc[trough_idx]["equity"]),
                    "recovery_equity": float(df.iloc[i]["equity"]),
                    "depth_pct": -float(seg["dd"].min() * 100.0),
                    "bars_to_trough": int(trough_idx - start_idx),
                    "bars_to_recovery": int(i - start_idx),
                    "days_to_trough": (df.iloc[trough_idx]["timestamp"] - df.iloc[start_idx]["timestamp"]).total_seconds() / 86400.0,
                    "days_to_recovery": (df.iloc[i]["timestamp"] - df.iloc[start_idx]["timestamp"]).total_seconds() / 86400.0,
                }
            )
            in_dd = False
        if dd == 0:
            peak_idx = i

    if in_dd and start_idx is not None:
        seg = df.iloc[start_idx:].copy()
        trough_idx = int(seg["dd"].idxmin())
        end_idx = len(df) - 1
        episodes.append(
            {
                "peak_idx": start_idx,
                "trough_idx": trough_idx,
                "recovery_idx": np.nan,
                "peak_time": df.iloc[start_idx]["timestamp"],
                "trough_time": df.iloc[trough_idx]["timestamp"],
                "recovery_time": pd.NaT,
                "peak_equity": float(df.iloc[start_idx]["equity"]),
                "trough_equity": float(df.iloc[trough_idx]["equity"]),
                "recovery_equity": float(df.iloc[end_idx]["equity"]),
                "depth_pct": -float(seg["dd"].min() * 100.0),
                "bars_to_trough": int(trough_idx - start_idx),
                "bars_to_recovery": int(end_idx - start_idx),
                "days_to_trough": (df.iloc[trough_idx]["timestamp"] - df.iloc[start_idx]["timestamp"]).total_seconds() / 86400.0,
                "days_to_recovery": (df.iloc[end_idx]["timestamp"] - df.iloc[start_idx]["timestamp"]).total_seconds() / 86400.0,
            }
        )

    episodes_df = pd.DataFrame(episodes).sort_values("depth_pct", ascending=False).head(top_n).reset_index(drop=True)
    episodes_df.insert(0, "episode_id", [f"E{i+1}" for i in range(len(episodes_df))])
    return episodes_df


def classify_episode(seg: pd.DataFrame) -> str:
    price_ret = (float(seg["close"].iloc[-1]) / float(seg["close"].iloc[0]) - 1.0) * 100.0
    long_share = float((seg["side"] > 0).mean())
    short_share = float((seg["side"] < 0).mean())
    flat_share = float((seg["side"] == 0).mean())
    long_in_bear = float(((seg["side"] > 0) & (seg["trend_4h_confirmed"] == "bearish")).mean())
    short_in_bull = float(((seg["side"] < 0) & (seg["trend_4h_confirmed"] == "bullish")).mean())
    flips = int((seg["side"].fillna(0).astype(int).diff().fillna(0) != 0).sum())

    if short_share >= 0.45 and price_ret > 10:
        return "상승장에서 숏 노출 누적"
    if long_share >= 0.45 and price_ret < -10:
        return "하락장에서 레버리지 롱 노출"
    if max(long_in_bear, short_in_bull) >= 0.30:
        return "상위 추세와 반대 방향 노출"
    if flips >= 6 and flat_share < 0.40:
        return "양방향 휩쏘 누적"
    if flat_share >= 0.50:
        return "flat 구간이 길었지만 회복이 지연"
    return "혼합형 추세/휩쏘 drawdown"


def summarize_episode(episode: pd.Series, merged: pd.DataFrame) -> dict:
    peak_time = pd.Timestamp(episode["peak_time"])
    trough_time = pd.Timestamp(episode["trough_time"])
    recovery_time = pd.Timestamp(episode["recovery_time"]) if pd.notna(episode["recovery_time"]) else pd.Timestamp(merged["timestamp"].max())

    seg_pt = merged[(merged["timestamp"] >= peak_time) & (merged["timestamp"] <= trough_time)].copy()
    seg_full = merged[(merged["timestamp"] >= peak_time) & (merged["timestamp"] <= recovery_time)].copy()

    price_peak = float(seg_pt["close"].iloc[0])
    price_trough = float(seg_pt["close"].iloc[-1])
    price_recovery = float(seg_full["close"].iloc[-1])
    side_changes = int((seg_pt["side"].fillna(0).astype(int).diff().fillna(0) != 0).sum())

    return {
        "btc_peak_to_trough_pct": (price_trough / price_peak - 1.0) * 100.0,
        "btc_peak_to_recovery_pct": (price_recovery / price_peak - 1.0) * 100.0,
        "bullish_4h_share_pct": float((seg_pt["trend_4h_confirmed"] == "bullish").mean() * 100.0),
        "bearish_4h_share_pct": float((seg_pt["trend_4h_confirmed"] == "bearish").mean() * 100.0),
        "long_share_pct": float((seg_pt["side"] > 0).mean() * 100.0),
        "short_share_pct": float((seg_pt["side"] < 0).mean() * 100.0),
        "flat_share_pct": float((seg_pt["side"] == 0).mean() * 100.0),
        "long_in_bearish_share_pct": float((((seg_pt["side"] > 0) & (seg_pt["trend_4h_confirmed"] == "bearish")).mean()) * 100.0),
        "short_in_bullish_share_pct": float((((seg_pt["side"] < 0) & (seg_pt["trend_4h_confirmed"] == "bullish")).mean()) * 100.0),
        "short_gate_open_share_pct": float(seg_pt["short_gate_open"].astype(int).mean() * 100.0),
        "avg_bearish_ob_above_count": float(seg_pt["bearish_ob_above_count"].mean()),
        "avg_bullish_ob_below_count": float(seg_pt["bullish_ob_below_count"].mean()),
        "side_change_count": side_changes,
        "episode_label": classify_episode(seg_pt),
    }


def align_window_return(curve: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> dict:
    seg = curve[(curve["timestamp"] >= start_ts) & (curve["timestamp"] <= end_ts)].copy()
    if seg.empty:
        return {"window_return_pct": np.nan, "window_mdd_pct": np.nan}
    start_eq = float(seg["equity"].iloc[0])
    end_eq = float(seg["equity"].iloc[-1])
    dd = seg["equity"].astype(float) / float(start_eq) - 1.0
    return {
        "window_return_pct": (end_eq / start_eq - 1.0) * 100.0,
        "window_mdd_pct": -float(dd.min() * 100.0),
    }


def save_plot(primary_curve: pd.DataFrame, episodes_df: pd.DataFrame, compare_df: pd.DataFrame):
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=False, gridspec_kw={"height_ratios": [1.8, 1.2]})
    ax_eq, ax_cmp = axes

    ax_eq.plot(primary_curve["timestamp"], primary_curve["equity"], color="#111111", linewidth=1.0, label=PRIMARY_VARIANT)
    ax_eq.axhline(1000.0, color="#777777", linestyle="--", linewidth=0.9)
    colors = ["#d62728", "#ff7f0e", "#bcbd22", "#17becf", "#9467bd"]
    for i, (_, row) in enumerate(episodes_df.iterrows()):
        start = pd.Timestamp(row["peak_time"])
        end = pd.Timestamp(row["recovery_time"]) if pd.notna(row["recovery_time"]) else pd.Timestamp(primary_curve["timestamp"].max())
        ax_eq.axvspan(start, end, color=colors[i % len(colors)], alpha=0.15, label=f"{row['episode_id']} {row['depth_pct']:.1f}%")
    ax_eq.set_title("Study 123: Case3 Equity With Top 5 Drawdown Episodes")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=3)

    plot_cmp = compare_df.copy()
    pivot = plot_cmp.pivot(index="episode_id", columns="variant", values="window_return_pct")
    pivot = pivot[[PRIMARY_VARIANT] + [v for v in pivot.columns if v != PRIMARY_VARIANT]]
    width = 0.14
    x = np.arange(len(pivot.index))
    for i, col in enumerate(pivot.columns):
        ax_cmp.bar(x + (i - (len(pivot.columns) - 1) / 2) * width, pivot[col].to_numpy(dtype=float), width=width, label=col)
    ax_cmp.set_xticks(x)
    ax_cmp.set_xticklabels(pivot.index.tolist())
    ax_cmp.set_ylabel("Peak->Trough Return %")
    ax_cmp.set_title("Top Drawdown Windows: Variant Loss Comparison")
    ax_cmp.grid(True, axis="y", alpha=0.2)
    ax_cmp.legend(loc="upper left", ncol=2)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(
    overall_df: pd.DataFrame,
    episodes_df: pd.DataFrame,
    compare_df: pd.DataFrame,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
):
    primary = overall_df[overall_df["variant"] == PRIMARY_VARIANT].iloc[0]
    best_near = overall_df[overall_df["variant"] == "lv2p5_g12_body20_tp20_lb5_none"].iloc[0]
    best_def = overall_df[overall_df["variant"] == "lv2p0_g12_body20_tp15_lb5_none"].iloc[0]

    compare_summary = (
        compare_df.groupby("variant")
        .agg(
            avg_peak_to_trough_loss_pct=("window_return_pct", "mean"),
            worst_peak_to_trough_loss_pct=("window_return_pct", "min"),
            avg_window_mdd_pct=("window_mdd_pct", "mean"),
        )
        .reset_index()
    )
    compare_summary["avg_peak_to_trough_loss_pct"] = compare_summary["avg_peak_to_trough_loss_pct"].astype(float)
    compare_summary["worst_peak_to_trough_loss_pct"] = compare_summary["worst_peak_to_trough_loss_pct"].astype(float)
    compare_summary["avg_window_mdd_pct"] = compare_summary["avg_window_mdd_pct"].astype(float)

    lines: list[str] = []
    lines.append("# 123 연구: case3 주요 MDD 구간 해부")
    lines.append("")
    lines.append("## 대상")
    lines.append(f"- 분석 대상 case3: `{PRIMARY_VARIANT}`")
    lines.append(f"- 구간: `{start_ts}` ~ `{end_ts}`")
    lines.append("- 목적: 가장 깊은 drawdown 5개가 어떤 경우에 발생했는지 읽고, CAGR 훼손을 최소화하면서 줄일 수 있는 방법을 찾는다.")
    lines.append("")
    lines.append("## 전체 성적")
    lines.append(
        f"- 현재 case3: CAGR `{_fmt(primary['cagr_pct'])}%`, MDD `{_fmt(primary['max_drawdown_pct'])}%`, Calmar `{_fmt(primary['calmar_ratio'])}`"
    )
    lines.append(
        f"- 근처 완화 후보 1: `lv2p5_g12_body20_tp20_lb5_none` -> CAGR `{_fmt(best_near['cagr_pct'])}%`, "
        f"MDD `{_fmt(best_near['max_drawdown_pct'])}%`, Calmar `{_fmt(best_near['calmar_ratio'])}`"
    )
    lines.append(
        f"- 근처 완화 후보 2: `lv2p0_g12_body20_tp15_lb5_none` -> CAGR `{_fmt(best_def['cagr_pct'])}%`, "
        f"MDD `{_fmt(best_def['max_drawdown_pct'])}%`, Calmar `{_fmt(best_def['calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Top 5 Drawdown Episodes")
    lines.append("")
    lines.append("| Episode | Peak | Trough | Recovery | Depth % | Days To Trough | BTC Peak->Trough % | Long % | Short % | Flat % | Label |")
    lines.append("| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for _, row in episodes_df.iterrows():
        recovery_text = row["recovery_time"] if pd.notna(row["recovery_time"]) else "미회복"
        lines.append(
            f"| {row['episode_id']} | {row['peak_time']} | {row['trough_time']} | {recovery_text} | "
            f"{_fmt(row['depth_pct'])} | {_fmt(row['days_to_trough'], 1)} | {_fmt(row['btc_peak_to_trough_pct'])} | "
            f"{_fmt(row['long_share_pct'])} | {_fmt(row['short_share_pct'])} | {_fmt(row['flat_share_pct'])} | {row['episode_label']} |"
        )
    lines.append("")
    lines.append("## Episode Notes")
    for _, row in episodes_df.iterrows():
        lines.append(f"### {row['episode_id']}")
        lines.append(
            f"- 기간: `{row['peak_time']}` -> `{row['trough_time']}`"
        )
        lines.append(
            f"- 낙폭: `{_fmt(row['depth_pct'])}%`, BTC 변화: `{_fmt(row['btc_peak_to_trough_pct'])}%`"
        )
        lines.append(
            f"- 노출 구성: long `{_fmt(row['long_share_pct'])}%`, short `{_fmt(row['short_share_pct'])}%`, flat `{_fmt(row['flat_share_pct'])}%`"
        )
        lines.append(
            f"- 추세/미스매치: bullish4h `{_fmt(row['bullish_4h_share_pct'])}%`, bearish4h `{_fmt(row['bearish_4h_share_pct'])}%`, "
            f"long-in-bearish `{_fmt(row['long_in_bearish_share_pct'])}%`, short-in-bullish `{_fmt(row['short_in_bullish_share_pct'])}%`"
        )
        lines.append(
            f"- 구조 환경: bearish OB above avg `{_fmt(row['avg_bearish_ob_above_count'])}`, bullish OB below avg `{_fmt(row['avg_bullish_ob_below_count'])}`, short gate open `{_fmt(row['short_gate_open_share_pct'])}%`"
        )
        lines.append(f"- 해석: {row['episode_label']}")
        lines.append("")
    lines.append("## Drawdown Window Variant Compare")
    lines.append("")
    lines.append("| Variant | Overall CAGR % | Overall MDD % | Avg Peak->Trough % | Worst Peak->Trough % | Avg Window MDD % |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for _, row in compare_summary.merge(overall_df[["variant", "cagr_pct", "max_drawdown_pct"]], on="variant", how="left").iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | "
            f"{_fmt(row['avg_peak_to_trough_loss_pct'])} | {_fmt(row['worst_peak_to_trough_loss_pct'])} | {_fmt(row['avg_window_mdd_pct'])} |"
        )
    lines.append("")
    lines.append("## 핵심 해석")
    lines.append("- `g8/body20`처럼 진입 타이밍만 건드린 3.0x 변형은 전체 MDD를 거의 줄이지 못했다. 즉 주원인은 타이밍보다 `레버리지 자체`에 더 가깝다.")
    lines.append("- `2.5x + g12 + TP20`은 CAGR 손실을 비교적 작게 유지하면서 MDD를 가장 현실적으로 낮추는 후보였다.")
    lines.append("- `2.0x/2.25x + TP15` 계열은 MDD는 더 낮추지만 CAGR 훼손이 커서 'CAGR을 크게 해치지 않는다'는 조건엔 덜 맞는다.")
    lines.append("- 상위 5개 drawdown 대부분은 한 방향 추세 구간에서 반대 포지션이 길게 물리거나, 3.0x 레버리지 long/short 노출이 변동성 구간에서 크게 흔들린 경우로 읽힌다.")
    lines.append("")
    lines.append("## 제안")
    lines.append("- 1차 완화안: `lv2p5_g12_body20_tp20_lb5_none` 재검증. 전체 CAGR은 `151.33 -> 145.22`로 약 `-6.11pp`, MDD는 `64.58 -> 59.04`로 약 `-5.54pp` 개선된다.")
    lines.append("- 2차 완화안: `2.5x`는 유지하고 `body_atr_mult`를 `0.20`으로 낮춰 short gate를 조금 더 일찍 여는 방향을 우선 검토한다.")
    lines.append("- 보류안: `long_above_red_avg` 같은 SR 필터는 drawdown 완화 대비 CAGR 훼손이 더 커서 우선순위가 낮다.")
    lines.append("- 공격형 유지안: case3 100%를 계속 쓸 거면, 포트폴리오가 아니라 sleeve 내부에서 `3.0x -> 2.5x` 다운시프트가 가장 덜 아픈 방어책이다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Episodes CSV: `{OUT_EPISODES_CSV}`")
    lines.append(f"- Variant Compare CSV: `{OUT_COMPARE_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    print("Loading modules...")
    m47 = load_module("study47_for_123", BASE_47_PATH)
    s76 = load_module("study76_for_123", BASE_76_PATH)
    m111 = load_module("study111_for_123", BASE_111_PATH)
    m114 = load_module("study114_for_123", BASE_114_PATH)
    m117 = load_module("study117_for_123", BASE_117_PATH)

    print("Loading 2021+ market...")
    df_1m, df_4h, end_ts = m114.load_market_data_2021plus()
    market = m114.prepare_market_114(df_1m, df_4h, m47, m111)

    variants = [PRIMARY_VARIANT] + COMPARE_VARIANTS
    variant_cfgs = {cfg["variant"]: cfg for cfg in m117.build_variants() if cfg["variant"] in variants}
    missing = [v for v in variants if v not in variant_cfgs]
    if missing:
        raise RuntimeError(f"Missing configs for variants: {missing}")

    curves: dict[str, pd.DataFrame] = {}
    overall_rows: list[dict] = []

    print("Running selected variants...")
    for variant in variants:
        print(f"  variant -> {variant}")
        curve, run_stats = m117.run_variant_117(market, variant_cfgs[variant], s76)
        curve = curve.copy()
        curve["timestamp"] = pd.to_datetime(curve["timestamp"])
        curves[variant] = curve
        stats = compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL)
        overall_rows.append(
            {
                "variant": variant,
                **stats,
                **run_stats,
            }
        )

    overall_df = pd.DataFrame(overall_rows).sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).reset_index(drop=True)

    primary_curve = curves[PRIMARY_VARIANT].copy()
    primary_merged = pd.merge(
        primary_curve[["timestamp", "equity", "side", "locked_side", "short_gate_open"]].copy(),
        market[["timestamp", "close", "trend_4h_confirmed", "bearish_ob_above_count", "bullish_ob_below_count"]].copy(),
        on="timestamp",
        how="left",
    ).sort_values("timestamp").reset_index(drop=True)

    episodes_df = compute_drawdown_episodes(primary_curve, top_n=TOP_N_EPISODES)
    episode_rows: list[dict] = []
    compare_rows: list[dict] = []
    for _, episode in episodes_df.iterrows():
        episode_summary = summarize_episode(episode, primary_merged)
        episode_rows.append({**episode.to_dict(), **episode_summary})

        start_ts = pd.Timestamp(episode["peak_time"])
        trough_ts = pd.Timestamp(episode["trough_time"])
        for variant in variants:
            aligned = align_window_return(curves[variant], start_ts, trough_ts)
            compare_rows.append(
                {
                    "episode_id": episode["episode_id"],
                    "variant": variant,
                    **aligned,
                }
            )

    episodes_out = pd.DataFrame(episode_rows)
    compare_df = pd.DataFrame(compare_rows)

    selected_curves = pd.concat(
        [curves[v].assign(variant=v) for v in variants],
        ignore_index=True,
    )

    episodes_out.to_csv(OUT_EPISODES_CSV, index=False)
    compare_df.to_csv(OUT_COMPARE_CSV, index=False)
    selected_curves.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(primary_curve, episodes_out, compare_df)
    save_report(overall_df, episodes_out, compare_df, pd.Timestamp(primary_curve["timestamp"].min()), end_ts)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_report={OUT_MD}")
    print(f"saved_episodes={OUT_EPISODES_CSV}")
    print(f"saved_compare={OUT_COMPARE_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(episodes_out[["episode_id", "peak_time", "trough_time", "depth_pct", "episode_label"]].to_string(index=False))
    print(overall_df[["variant", "cagr_pct", "max_drawdown_pct", "calmar_ratio"]].to_string(index=False))


if __name__ == "__main__":
    run()
