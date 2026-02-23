from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_22_PATH = Path("22_backtest_btcusdt_dd_scale_entryscale_sweep.py")

OUT_BASE = "00_1_backtest_btcusdt_trend_persistence_scale06"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_EPISODES = Path(f"{OUT_BASE}_episodes.csv")
OUT_REGIME_STATS = Path(f"{OUT_BASE}_regime_stats.csv")

ENTRY_SCALE = 0.6
HYSTERESIS_BAND = 0.005
DD_THRESHOLD_PCT = 20.0
PLOT_RESAMPLE = "30min"
EPISODE_RESAMPLE = "4h"


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


def compute_hysteresis_state(df_4h: pd.DataFrame, hysteresis: float) -> pd.Series:
    states: list[str | float] = []
    prev_state: str | None = None
    for _, row in df_4h.iterrows():
        ema = row["ema200"]
        close = row["close"]
        if pd.isna(ema) or pd.isna(close):
            states.append(np.nan)
            continue

        upper = ema * (1.0 + hysteresis)
        lower = ema * (1.0 - hysteresis)
        if close > upper:
            state = "bullish"
        elif close < lower:
            state = "bearish"
        else:
            if prev_state is None:
                state = "bullish" if close > ema else "bearish"
            else:
                state = prev_state

        states.append(state)
        prev_state = state
    return pd.Series(states, index=df_4h.index)


def compute_4h_features(df_4h: pd.DataFrame) -> pd.DataFrame:
    out = df_4h.copy()
    out["ema200"] = out["close"].ewm(span=200, adjust=False).mean().shift(1)
    out["trend_hyst"] = compute_hysteresis_state(out, HYSTERESIS_BAND)
    out["trend_confirmed"] = out["trend_hyst"].shift(1)

    valid = out["trend_confirmed"].isin(["bullish", "bearish"])
    grp = (out["trend_confirmed"] != out["trend_confirmed"].shift()).cumsum()
    out["run_len_4h"] = out.groupby(grp).cumcount() + 1
    out.loc[~valid, "run_len_4h"] = np.nan

    out["bull_run_len_4h"] = np.where(out["trend_confirmed"] == "bullish", out["run_len_4h"], 0.0)
    out["bear_run_len_4h"] = np.where(out["trend_confirmed"] == "bearish", out["run_len_4h"], 0.0)

    out["flip_4h"] = (
        (out["trend_confirmed"] != out["trend_confirmed"].shift())
        & out["trend_confirmed"].isin(["bullish", "bearish"])
        & out["trend_confirmed"].shift().isin(["bullish", "bearish"])
    ).astype(float)
    out["flip_count_30_4h"] = out["flip_4h"].rolling(30, min_periods=1).sum()

    out["abs_gap_pct_4h"] = ((out["close"] - out["ema200"]).abs() / out["ema200"] * 100.0).replace([np.inf, -np.inf], np.nan)
    out["near_ema_0p5_4h"] = (out["abs_gap_pct_4h"] <= 0.5).astype(float)
    out["near_ema_ratio_30_4h"] = out["near_ema_0p5_4h"].rolling(30, min_periods=1).mean() * 100.0

    return out[
        [
            "ema200",
            "trend_confirmed",
            "run_len_4h",
            "bull_run_len_4h",
            "bear_run_len_4h",
            "flip_4h",
            "flip_count_30_4h",
            "abs_gap_pct_4h",
            "near_ema_ratio_30_4h",
        ]
    ]


def build_analysis_frame(equity_curve: pd.DataFrame, df_1m: pd.DataFrame, df_4h: pd.DataFrame) -> pd.DataFrame:
    eq = equity_curve.copy()
    eq["timestamp"] = pd.to_datetime(eq["timestamp"])
    eq = eq.sort_values("timestamp")
    eq = eq[["timestamp", "equity"]].drop_duplicates(subset=["timestamp"]).set_index("timestamp")
    eq["equity_peak"] = eq["equity"].cummax().replace(0, np.nan)
    eq["drawdown_pct"] = ((eq["equity_peak"] - eq["equity"]) / eq["equity_peak"] * 100.0).fillna(0.0)

    f4h = compute_4h_features(df_4h)

    p1 = df_1m.copy()
    p1 = p1[["close"]].astype(float)
    p1["timestamp_4h"] = p1.index.floor("4h")
    p1 = p1.merge(f4h, left_on="timestamp_4h", right_index=True, how="left")
    p1.drop(columns=["timestamp_4h"], inplace=True)

    p1["ema200"] = p1["ema200"].ffill()
    for c in [
        "run_len_4h",
        "bull_run_len_4h",
        "bear_run_len_4h",
        "flip_count_30_4h",
        "abs_gap_pct_4h",
        "near_ema_ratio_30_4h",
    ]:
        p1[c] = p1[c].ffill()

    p1["btc_close"] = p1["close"]
    p1.drop(columns=["close"], inplace=True)

    p1["ema_gap_signed_pct"] = ((p1["btc_close"] - p1["ema200"]) / p1["ema200"] * 100.0).replace([np.inf, -np.inf], np.nan)
    p1["ema_below_pct"] = np.where(
        p1["btc_close"] < p1["ema200"],
        (p1["ema200"] - p1["btc_close"]) / p1["ema200"] * 100.0,
        0.0,
    )
    p1["active_run_len_4h"] = p1["run_len_4h"]

    out = eq.join(
        p1[
            [
                "btc_close",
                "ema200",
                "trend_confirmed",
                "active_run_len_4h",
                "bull_run_len_4h",
                "bear_run_len_4h",
                "flip_count_30_4h",
                "near_ema_ratio_30_4h",
                "ema_gap_signed_pct",
                "ema_below_pct",
            ]
        ],
        how="left",
    )
    out = out.dropna(subset=["btc_close", "ema200"]).copy()
    out["dd20"] = out["drawdown_pct"] >= DD_THRESHOLD_PCT
    return out


def _extract_true_intervals(mask: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    if mask.empty:
        return []
    grp = (mask != mask.shift(1)).cumsum()
    intervals: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for _, seg in mask.groupby(grp):
        if not bool(seg.iloc[0]):
            continue
        intervals.append((seg.index[0], seg.index[-1]))
    return intervals


def extract_dd20_episodes(df: pd.DataFrame) -> pd.DataFrame:
    tmp = df[["drawdown_pct", "ema_below_pct", "active_run_len_4h", "flip_count_30_4h", "near_ema_ratio_30_4h"]].resample(EPISODE_RESAMPLE).last().dropna()
    tmp["dd20"] = tmp["drawdown_pct"] >= DD_THRESHOLD_PCT
    intervals = _extract_true_intervals(tmp["dd20"])

    rows: list[dict] = []
    for i, (s, e) in enumerate(intervals, start=1):
        seg = tmp.loc[s:e]
        dur_h = float((e - s).total_seconds() / 3600.0)
        rows.append(
            {
                "episode_id": i,
                "start": s,
                "end": e,
                "bars_4h": int(len(seg)),
                "duration_hours": dur_h,
                "duration_days": dur_h / 24.0,
                "max_drawdown_pct": float(seg["drawdown_pct"].max()),
                "avg_drawdown_pct": float(seg["drawdown_pct"].mean()),
                "avg_run_len_4h": float(seg["active_run_len_4h"].mean()),
                "max_run_len_4h": float(seg["active_run_len_4h"].max()),
                "avg_flip_count_30_4h": float(seg["flip_count_30_4h"].mean()),
                "avg_near_ema_ratio_30_4h": float(seg["near_ema_ratio_30_4h"].mean()),
                "avg_ema_below_pct": float(seg["ema_below_pct"].mean()),
            }
        )
    return pd.DataFrame(rows)


def build_regime_stats(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()
    base = base.dropna(subset=["active_run_len_4h", "flip_count_30_4h", "near_ema_ratio_30_4h"])

    run_bins = pd.cut(
        base["active_run_len_4h"],
        bins=[0, 3, 8, 16, 10**9],
        labels=["run_1_3", "run_4_8", "run_9_16", "run_17_plus"],
        right=True,
    )
    flip_bins = pd.cut(
        base["flip_count_30_4h"],
        bins=[-0.1, 1, 3, 5, 30],
        labels=["flip_0_1", "flip_2_3", "flip_4_5", "flip_6_plus"],
        right=True,
    )
    near_bins = pd.cut(
        base["near_ema_ratio_30_4h"],
        bins=[-0.1, 20, 40, 60, 100],
        labels=["near_0_20", "near_20_40", "near_40_60", "near_60_100"],
        right=True,
    )

    def _group_stats(group_key: str, bins: pd.Series) -> pd.DataFrame:
        t = base.copy()
        t[group_key] = bins
        g = t.groupby(group_key, dropna=False)
        out = g.agg(
            bars=("dd20", "size"),
            dd20_rate_pct=("dd20", lambda x: float(np.mean(x) * 100.0)),
            avg_drawdown_pct=("drawdown_pct", "mean"),
            p90_drawdown_pct=("drawdown_pct", lambda x: float(np.quantile(x, 0.90))),
            avg_ema_below_pct=("ema_below_pct", "mean"),
            avg_run_len_4h=("active_run_len_4h", "mean"),
            avg_flip_count_30_4h=("flip_count_30_4h", "mean"),
            avg_near_ema_ratio_30_4h=("near_ema_ratio_30_4h", "mean"),
        ).reset_index()
        out = out.rename(columns={group_key: "bucket"})
        out.insert(0, "regime_dimension", group_key)
        return out

    r1 = _group_stats("run_bin", run_bins)
    r2 = _group_stats("flip_bin", flip_bins)
    r3 = _group_stats("near_ema_bin", near_bins)
    return pd.concat([r1, r2, r3], ignore_index=True)


def save_plot(df: pd.DataFrame):
    plot_df = (
        df[
            [
                "btc_close",
                "ema200",
                "bull_run_len_4h",
                "bear_run_len_4h",
                "flip_count_30_4h",
                "near_ema_ratio_30_4h",
                "drawdown_pct",
            ]
        ]
        .resample(PLOT_RESAMPLE)
        .last()
        .dropna()
    )
    plot_df["dd20"] = plot_df["drawdown_pct"] >= DD_THRESHOLD_PCT
    dd_intervals = _extract_true_intervals(plot_df["dd20"])

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(17, 12),
        sharex=True,
        gridspec_kw={"height_ratios": [2.1, 1.2, 1.2, 1.2]},
    )
    ax_price, ax_run, ax_reg, ax_dd = axes

    for s, e in dd_intervals:
        for ax in axes:
            ax.axvspan(s, e, color="red", alpha=0.10, linewidth=0)

    ax_price.plot(plot_df.index, plot_df["btc_close"], color="#1f77b4", linewidth=1.0, label="BTC Close")
    ax_price.plot(plot_df.index, plot_df["ema200"], color="#2ca02c", linewidth=1.0, label="4h EMA200 (confirmed)")
    ax_price.set_title("00_1 Study: Trend Persistence Regime vs Drawdown (Scale=0.6 baseline)")
    ax_price.set_ylabel("Price (USDT)")
    ax_price.grid(True, alpha=0.2)
    ax_price.legend(loc="upper left")

    ax_run.plot(plot_df.index, plot_df["bull_run_len_4h"], color="#2ca02c", linewidth=0.9, label="Bull run len (4h bars)")
    ax_run.plot(plot_df.index, plot_df["bear_run_len_4h"], color="#d62728", linewidth=0.9, label="Bear run len (4h bars)")
    ax_run.set_ylabel("Run Length")
    ax_run.grid(True, alpha=0.2)
    ax_run.legend(loc="upper left")

    ax_reg.plot(plot_df.index, plot_df["flip_count_30_4h"], color="#9467bd", linewidth=0.9, label="Flip count (last 30x4h)")
    ax_reg.set_ylabel("Flip Count")
    ax_reg.grid(True, alpha=0.2)
    ax_reg2 = ax_reg.twinx()
    ax_reg2.plot(plot_df.index, plot_df["near_ema_ratio_30_4h"], color="#ff7f0e", linewidth=0.9, label="Near EMA ratio (last 30x4h) %")
    ax_reg2.set_ylabel("Near EMA %")
    l1, lb1 = ax_reg.get_legend_handles_labels()
    l2, lb2 = ax_reg2.get_legend_handles_labels()
    ax_reg.legend(l1 + l2, lb1 + lb2, loc="upper left")

    ax_dd.plot(plot_df.index, plot_df["drawdown_pct"], color="#111111", linewidth=1.0, label="Drawdown %")
    ax_dd.axhline(DD_THRESHOLD_PCT, color="black", linestyle="--", linewidth=1.0, label=f"DD {DD_THRESHOLD_PCT:.0f}%")
    ax_dd.set_ylabel("Drawdown (%)")
    ax_dd.set_xlabel("Time")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="upper left")

    ax_dd.xaxis.set_major_locator(mdates.YearLocator())
    ax_dd.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(metrics: dict, df: pd.DataFrame, episodes: pd.DataFrame, regime_stats: pd.DataFrame):
    dd20 = df[df["dd20"]]
    non = df[~df["dd20"]]

    corr_run = float(df["drawdown_pct"].corr(df["active_run_len_4h"], method="spearman"))
    corr_flip = float(df["drawdown_pct"].corr(df["flip_count_30_4h"], method="spearman"))
    corr_near = float(df["drawdown_pct"].corr(df["near_ema_ratio_30_4h"], method="spearman"))

    dd20_ratio = float(df["dd20"].mean() * 100.0)
    ep_count = int(len(episodes))

    longest = episodes.sort_values("duration_days", ascending=False).head(1) if ep_count else pd.DataFrame()
    worst = episodes.sort_values("max_drawdown_pct", ascending=False).head(1) if ep_count else pd.DataFrame()

    lines: list[str] = []
    lines.append("# 00_1 Study: Trend Persistence / Choppiness vs DD")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Base strategy/case: `22` baseline with `entry_scale=0.6` (no DD scaling)")
    lines.append("- Regime features from confirmed 4h EMA200 + hysteresis trend (`0.5%`)")
    lines.append("- DD threshold for highlighting: `20%`")
    lines.append("")
    lines.append("## Core Metrics")
    lines.append(f"- Final Equity: `{_fmt(metrics.get('final_equity', np.nan))}` USDT")
    lines.append(f"- MDD: `{_fmt(metrics.get('max_drawdown_pct', np.nan))}%`")
    lines.append(f"- Trades: `{int(metrics.get('trades', 0))}` (Long `{int(metrics.get('long_trades', 0))}`, Short `{int(metrics.get('short_trades', 0))}`)")
    lines.append("")
    lines.append("## Regime Correlations (Spearman)")
    lines.append(f"- Drawdown vs active run length (4h bars): `{_fmt(corr_run)}`")
    lines.append(f"- Drawdown vs flip count (last 30x4h): `{_fmt(corr_flip)}`")
    lines.append(f"- Drawdown vs near-EMA ratio (last 30x4h): `{_fmt(corr_near)}`")
    lines.append("")
    lines.append("## DD>=20 vs DD<20 Conditioned Means")
    lines.append(f"- Time in DD>=20: `{_fmt(dd20_ratio)}`%")
    lines.append(f"- Avg run len (DD>=20 / DD<20): `{_fmt(dd20['active_run_len_4h'].mean())}` / `{_fmt(non['active_run_len_4h'].mean())}`")
    lines.append(f"- Avg flip count (DD>=20 / DD<20): `{_fmt(dd20['flip_count_30_4h'].mean())}` / `{_fmt(non['flip_count_30_4h'].mean())}`")
    lines.append(f"- Avg near-EMA ratio (DD>=20 / DD<20): `{_fmt(dd20['near_ema_ratio_30_4h'].mean())}` / `{_fmt(non['near_ema_ratio_30_4h'].mean())}`")
    lines.append("")
    lines.append("## DD>=20 Episodes (4h aggregated)")
    lines.append(f"- Episode count: `{ep_count}`")
    if ep_count:
        lines.append(
            f"- Longest: `ID {int(longest.iloc[0]['episode_id'])}` "
            f"({pd.to_datetime(longest.iloc[0]['start'])} ~ {pd.to_datetime(longest.iloc[0]['end'])}, "
            f"{_fmt(longest.iloc[0]['duration_days'])} days)"
        )
        lines.append(
            f"- Worst DD: `ID {int(worst.iloc[0]['episode_id'])}` "
            f"(max DD `{_fmt(worst.iloc[0]['max_drawdown_pct'])}%`, "
            f"avg run len `{_fmt(worst.iloc[0]['avg_run_len_4h'])}`, "
            f"avg flip `{_fmt(worst.iloc[0]['avg_flip_count_30_4h'])}`)"
        )
    lines.append("")
    lines.append("## Regime Bucket Stats")
    lines.append("| Dimension | Bucket | Bars | DD>=20 Rate % | Avg DD % | P90 DD % | Avg Run Len | Avg Flip(30x4h) | Avg Near EMA % |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in regime_stats.iterrows():
        lines.append(
            f"| {r['regime_dimension']} | {r['bucket']} | {int(r['bars'])} | {_fmt(r['dd20_rate_pct'])} | {_fmt(r['avg_drawdown_pct'])} | "
            f"{_fmt(r['p90_drawdown_pct'])} | {_fmt(r['avg_run_len_4h'])} | {_fmt(r['avg_flip_count_30_4h'])} | {_fmt(r['avg_near_ema_ratio_30_4h'])} |"
        )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Episodes: `{OUT_EPISODES}`")
    lines.append(f"- Regime stats: `{OUT_REGIME_STATS}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    m22 = load_module("m22_001", BASE_22_PATH)
    base_module = m22.load_module("m002_001", m22.BASE_002_PATH)
    helper_module = m22.load_module("m04_001", m22.BASE_04_PATH)

    df_1m, df_4h = m22.load_data_no_filter(base_module)
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    cls = m22.build_case_class(base_module, helper_module, dynamic_dd_scale=False)
    bt = cls(
        symbol=base_module.SYMBOL,
        initial_capital=base_module.INITIAL_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=float(ENTRY_SCALE),
    )
    helper_module.configure_baseline_params(bt)
    bt.run(df_1m, df_4h, backtest_start_date=base_module.BACKTEST_START)

    metrics = helper_module.calculate_metrics(bt, base_module.INITIAL_CAPITAL)
    eq = pd.DataFrame(bt.equity_curve)
    if eq.empty:
        raise RuntimeError("Empty equity curve for 00_1 analysis.")

    analysis_df = build_analysis_frame(eq, df_1m, df_4h)
    episodes = extract_dd20_episodes(analysis_df)
    regime_stats = build_regime_stats(analysis_df)

    episodes.to_csv(OUT_EPISODES, index=False)
    regime_stats.to_csv(OUT_REGIME_STATS, index=False)
    save_plot(analysis_df)
    save_report(metrics, analysis_df, episodes, regime_stats)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_report={OUT_MD}")
    print(f"saved_episodes={OUT_EPISODES}")
    print(f"saved_regime_stats={OUT_REGIME_STATS}")
    print(
        "summary="
        f"final_equity:{_fmt(metrics.get('final_equity', np.nan))},"
        f"mdd:{_fmt(metrics.get('max_drawdown_pct', np.nan))},"
        f"trades:{int(metrics.get('trades', 0))}"
    )


if __name__ == "__main__":
    run()
