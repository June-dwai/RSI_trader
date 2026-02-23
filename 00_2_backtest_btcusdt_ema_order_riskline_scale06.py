from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_22_PATH = Path("22_backtest_btcusdt_dd_scale_entryscale_sweep.py")

OUT_BASE = "00_2_backtest_btcusdt_ema_order_riskline_scale06"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_EPISODES = Path(f"{OUT_BASE}_episodes.csv")
OUT_REGIME_STATS = Path(f"{OUT_BASE}_regime_stats.csv")

ENTRY_SCALE = 0.6
DD_THRESHOLD_PCT = 20.0
PLOT_RESAMPLE = "30min"
EPISODE_RESAMPLE = "4h"

RISK_LOOKBACK_4H = 12
ATR_PERIOD = 14
ATR_MULT = 2.2


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


def compute_4h_features(df_4h: pd.DataFrame) -> pd.DataFrame:
    out = df_4h.copy()

    out["ema16"] = out["close"].ewm(span=16, adjust=False).mean().shift(1)
    out["ema50"] = out["close"].ewm(span=50, adjust=False).mean().shift(1)
    out["ema99"] = out["close"].ewm(span=99, adjust=False).mean().shift(1)
    out["ema200"] = out["close"].ewm(span=200, adjust=False).mean().shift(1)

    ema_ready = out[["ema16", "ema50", "ema99", "ema200"]].notna().all(axis=1)
    bull_order = (out["ema16"] > out["ema50"]) & (out["ema50"] > out["ema99"]) & (out["ema99"] > out["ema200"])
    bear_order = (out["ema16"] < out["ema50"]) & (out["ema50"] < out["ema99"]) & (out["ema99"] < out["ema200"])

    out["ema_order_state_raw"] = np.nan
    out.loc[ema_ready, "ema_order_state_raw"] = 0.0
    out.loc[ema_ready & bull_order, "ema_order_state_raw"] = 1.0
    out.loc[ema_ready & bear_order, "ema_order_state_raw"] = -1.0
    out["ema_order_state_4h"] = out["ema_order_state_raw"].shift(1)

    out["mixed_flag_4h"] = np.where(out["ema_order_state_4h"] == 0.0, 1.0, 0.0)
    out.loc[out["ema_order_state_4h"].isna(), "mixed_flag_4h"] = np.nan

    prev_close = out["close"].shift(1)
    tr = pd.concat(
        [
            (out["high"] - out["low"]).abs(),
            (out["high"] - prev_close).abs(),
            (out["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr14"] = tr.ewm(alpha=1.0 / ATR_PERIOD, adjust=False).mean().shift(1)
    out["rolling_high_n"] = out["high"].rolling(RISK_LOOKBACK_4H, min_periods=RISK_LOOKBACK_4H).max().shift(1)
    out["risk_line"] = out["rolling_high_n"] - ATR_MULT * out["atr14"]
    out["risk_gap_pct_4h"] = ((out["close"] - out["risk_line"]) / out["close"] * 100.0).replace([np.inf, -np.inf], np.nan)
    out["risk_breach_raw_4h"] = np.where(out["close"] < out["risk_line"], 1.0, 0.0)
    out.loc[out["risk_line"].isna(), "risk_breach_raw_4h"] = np.nan
    out["risk_breach_4h"] = out["risk_breach_raw_4h"].shift(1)

    out["recent_high_n_close"] = out["close"].rolling(RISK_LOOKBACK_4H, min_periods=RISK_LOOKBACK_4H).max().shift(1)
    out["retrace_12_pct_4h"] = (
        (out["recent_high_n_close"] - out["close"]) / out["recent_high_n_close"] * 100.0
    ).replace([np.inf, -np.inf], np.nan)
    out["retrace_12_pct_4h"] = out["retrace_12_pct_4h"].clip(lower=0.0)

    return out[
        [
            "ema16",
            "ema50",
            "ema99",
            "ema200",
            "ema_order_state_4h",
            "mixed_flag_4h",
            "risk_line",
            "risk_gap_pct_4h",
            "risk_breach_4h",
            "retrace_12_pct_4h",
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

    for c in [
        "ema16",
        "ema50",
        "ema99",
        "ema200",
        "ema_order_state_4h",
        "mixed_flag_4h",
        "risk_line",
        "risk_gap_pct_4h",
        "risk_breach_4h",
        "retrace_12_pct_4h",
    ]:
        p1[c] = p1[c].ffill()

    p1["btc_close"] = p1["close"]
    p1.drop(columns=["close"], inplace=True)

    p1["ema_order_state"] = p1["ema_order_state_4h"]
    p1["mixed_flag"] = np.where(p1["ema_order_state"] == 0.0, 1.0, 0.0)
    p1.loc[p1["ema_order_state"].isna(), "mixed_flag"] = np.nan
    p1["risk_gap_pct"] = ((p1["btc_close"] - p1["risk_line"]) / p1["btc_close"] * 100.0).replace([np.inf, -np.inf], np.nan)
    p1["risk_breach"] = np.where(p1["btc_close"] < p1["risk_line"], 1.0, 0.0)
    p1.loc[p1["risk_line"].isna(), "risk_breach"] = np.nan
    p1["retrace_12_pct"] = p1["retrace_12_pct_4h"]
    p1["long_trap_risk_flag"] = np.where((p1["btc_close"] > p1["ema200"]) & (p1["risk_breach"] == 1.0), 1.0, 0.0)

    out = eq.join(
        p1[
            [
                "btc_close",
                "ema16",
                "ema50",
                "ema99",
                "ema200",
                "ema_order_state",
                "mixed_flag",
                "risk_line",
                "risk_gap_pct",
                "risk_breach",
                "retrace_12_pct",
                "long_trap_risk_flag",
            ]
        ],
        how="left",
    )
    out = out.dropna(subset=["btc_close", "ema200", "ema_order_state", "risk_line"]).copy()
    out["ema_order_state_label"] = out["ema_order_state"].map(
        {
            1.0: "ordered_bull",
            0.0: "mixed",
            -1.0: "ordered_bear",
        }
    )
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
    tmp = (
        df[
            [
                "drawdown_pct",
                "ema_order_state",
                "mixed_flag",
                "risk_breach",
                "risk_gap_pct",
                "retrace_12_pct",
                "long_trap_risk_flag",
            ]
        ]
        .resample(EPISODE_RESAMPLE)
        .last()
        .dropna()
    )
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
                "avg_ema_state": float(seg["ema_order_state"].mean()),
                "mixed_ratio_pct": float(seg["mixed_flag"].mean() * 100.0),
                "risk_breach_ratio_pct": float(seg["risk_breach"].mean() * 100.0),
                "avg_risk_gap_pct": float(seg["risk_gap_pct"].mean()),
                "avg_retrace_12_pct": float(seg["retrace_12_pct"].mean()),
                "long_trap_ratio_pct": float(seg["long_trap_risk_flag"].mean() * 100.0),
            }
        )
    return pd.DataFrame(rows)


def build_regime_stats(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()
    base = base.dropna(subset=["ema_order_state", "risk_gap_pct", "retrace_12_pct", "long_trap_risk_flag"])

    state_bins = base["ema_order_state_label"]
    risk_bins = pd.cut(
        base["risk_gap_pct"],
        bins=[-10**9, 0, 2, 5, 10**9],
        labels=["risk_below_line", "risk_0_2", "risk_2_5", "risk_5_plus"],
        right=False,
    )
    retrace_bins = pd.cut(
        base["retrace_12_pct"],
        bins=[-0.1, 3, 6, 9, 10**9],
        labels=["ret_0_3", "ret_3_6", "ret_6_9", "ret_9_plus"],
        right=True,
    )
    trap_bins = pd.cut(
        base["long_trap_risk_flag"],
        bins=[-0.1, 0.5, 1.0],
        labels=["trap_off", "trap_on"],
        right=True,
    )

    def _group_stats(group_key: str, bins: pd.Series) -> pd.DataFrame:
        t = base.copy()
        t[group_key] = bins
        g = t.groupby(group_key, dropna=False, observed=True)
        out = g.agg(
            bars=("dd20", "size"),
            dd20_rate_pct=("dd20", lambda x: float(np.mean(x) * 100.0)),
            avg_drawdown_pct=("drawdown_pct", "mean"),
            p90_drawdown_pct=("drawdown_pct", lambda x: float(np.quantile(x, 0.90))),
            avg_ema_state=("ema_order_state", "mean"),
            mixed_ratio_pct=("mixed_flag", lambda x: float(np.mean(x) * 100.0)),
            avg_risk_gap_pct=("risk_gap_pct", "mean"),
            avg_retrace_12_pct=("retrace_12_pct", "mean"),
            long_trap_ratio_pct=("long_trap_risk_flag", lambda x: float(np.mean(x) * 100.0)),
        ).reset_index()
        out = out.rename(columns={group_key: "bucket"})
        out.insert(0, "regime_dimension", group_key)
        return out

    r1 = _group_stats("ema_order_state_bin", state_bins)
    r2 = _group_stats("risk_gap_bin", risk_bins)
    r3 = _group_stats("retrace_bin", retrace_bins)
    r4 = _group_stats("long_trap_bin", trap_bins)
    return pd.concat([r1, r2, r3, r4], ignore_index=True)


def save_plot(df: pd.DataFrame):
    plot_df = (
        df[
            [
                "btc_close",
                "ema200",
                "risk_line",
                "ema_order_state",
                "risk_gap_pct",
                "retrace_12_pct",
                "long_trap_risk_flag",
                "drawdown_pct",
            ]
        ]
        .resample(PLOT_RESAMPLE)
        .last()
        .dropna()
    )
    mixed_intervals = _extract_true_intervals((plot_df["ema_order_state"] == 0.0).astype(bool))

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(17, 12),
        sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.1, 1.2, 1.2]},
    )
    ax_price, ax_state, ax_risk, ax_dd = axes

    for s, e in mixed_intervals:
        for ax in axes:
            ax.axvspan(s, e, color="#9a9a9a", alpha=0.14, linewidth=0)

    ax_price.plot(plot_df.index, plot_df["btc_close"], color="#1f77b4", linewidth=1.0, label="BTC Close")
    ax_price.plot(plot_df.index, plot_df["ema200"], color="#2ca02c", linewidth=1.0, label="4h EMA200 (confirmed)")
    ax_price.plot(plot_df.index, plot_df["risk_line"], color="#d62728", linewidth=1.0, label=f"Risk line (HH{RISK_LOOKBACK_4H}-ATR{ATR_MULT})")
    trap_idx = plot_df["long_trap_risk_flag"] > 0.5
    if trap_idx.any():
        ax_price.scatter(
            plot_df.index[trap_idx],
            plot_df.loc[trap_idx, "btc_close"],
            color="#d62728",
            s=6,
            alpha=0.30,
            label="Long-trap risk point",
        )
    ax_price.set_title("00_2 Study: EMA Order State + Risk Line vs Drawdown (Scale=0.6 baseline)")
    ax_price.set_ylabel("Price (USDT)")
    ax_price.grid(True, alpha=0.2)
    ax_price.legend(loc="upper left")

    ax_state.step(plot_df.index, plot_df["ema_order_state"], where="post", color="#6a3d9a", linewidth=1.0, label="EMA order state (1 / 0 / -1)")
    ax_state.axhline(1.0, color="#2ca02c", linestyle="--", linewidth=0.8, alpha=0.7)
    ax_state.axhline(0.0, color="#666666", linestyle="-", linewidth=0.8, alpha=0.7)
    ax_state.axhline(-1.0, color="#d62728", linestyle="--", linewidth=0.8, alpha=0.7)
    ax_state.set_yticks([-1.0, 0.0, 1.0])
    ax_state.set_yticklabels(["-1 bear", "0 mixed", "1 bull"])
    ax_state.set_ylim(-1.4, 1.4)
    ax_state.set_ylabel("EMA Order")
    ax_state.grid(True, alpha=0.2)
    ax_state.legend(loc="upper left")

    ax_risk.plot(plot_df.index, plot_df["risk_gap_pct"], color="#d62728", linewidth=0.9, label="Risk gap % (close vs risk line)")
    ax_risk.axhline(0.0, color="black", linestyle="--", linewidth=0.9, label="Risk line breach")
    ax_risk.fill_between(
        plot_df.index,
        plot_df["risk_gap_pct"],
        0.0,
        where=plot_df["risk_gap_pct"] < 0.0,
        color="#d62728",
        alpha=0.14,
    )
    ax_risk.set_ylabel("Risk Gap %")
    ax_risk.grid(True, alpha=0.2)
    ax_risk2 = ax_risk.twinx()
    ax_risk2.plot(plot_df.index, plot_df["retrace_12_pct"], color="#ff7f0e", linewidth=0.9, label=f"Retrace from HH{RISK_LOOKBACK_4H} %")
    ax_risk2.set_ylabel("Retrace %")
    l1, lb1 = ax_risk.get_legend_handles_labels()
    l2, lb2 = ax_risk2.get_legend_handles_labels()
    ax_risk.legend(l1 + l2, lb1 + lb2, loc="upper left")

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

    corr_state = float(df["drawdown_pct"].corr(df["ema_order_state"], method="spearman"))
    corr_mixed = float(df["drawdown_pct"].corr(df["mixed_flag"], method="spearman"))
    corr_risk_gap = float(df["drawdown_pct"].corr(df["risk_gap_pct"], method="spearman"))
    corr_retrace = float(df["drawdown_pct"].corr(df["retrace_12_pct"], method="spearman"))

    dd20_ratio = float(df["dd20"].mean() * 100.0)
    ep_count = int(len(episodes))

    longest = episodes.sort_values("duration_days", ascending=False).head(1) if ep_count else pd.DataFrame()
    worst = episodes.sort_values("max_drawdown_pct", ascending=False).head(1) if ep_count else pd.DataFrame()

    lines: list[str] = []
    lines.append("# 00_2 Study: EMA Order State + Risk Line vs DD")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Base strategy/case: `22` baseline with `entry_scale=0.6` (no DD scaling)")
    lines.append("- 4h EMA order state: `1` ordered bull (`16>50>99>200`), `0` mixed, `-1` ordered bear")
    lines.append(f"- Risk line: `highest high({RISK_LOOKBACK_4H}) - {ATR_MULT} * ATR({ATR_PERIOD})` on 4h confirmed bars")
    lines.append("- Shading in chart: only `EMA order state == 0` (mixed)")
    lines.append("- DD threshold reference: `20%`")
    lines.append("")
    lines.append("## Core Metrics")
    lines.append(f"- Final Equity: `{_fmt(metrics.get('final_equity', np.nan))}` USDT")
    lines.append(f"- MDD: `{_fmt(metrics.get('max_drawdown_pct', np.nan))}%`")
    lines.append(f"- Trades: `{int(metrics.get('trades', 0))}` (Long `{int(metrics.get('long_trades', 0))}`, Short `{int(metrics.get('short_trades', 0))}`)")
    lines.append("")
    lines.append("## Regime Correlations (Spearman)")
    lines.append(f"- Drawdown vs EMA order state (1/0/-1): `{_fmt(corr_state)}`")
    lines.append(f"- Drawdown vs mixed flag (state==0): `{_fmt(corr_mixed)}`")
    lines.append(f"- Drawdown vs risk gap %: `{_fmt(corr_risk_gap)}`")
    lines.append(f"- Drawdown vs retrace from recent high %: `{_fmt(corr_retrace)}`")
    lines.append("")
    lines.append("## DD>=20 vs DD<20 Conditioned Means")
    lines.append(f"- Time in DD>=20: `{_fmt(dd20_ratio)}`%")
    lines.append(f"- Avg EMA state (DD>=20 / DD<20): `{_fmt(dd20['ema_order_state'].mean())}` / `{_fmt(non['ema_order_state'].mean())}`")
    lines.append(f"- Mixed ratio % (DD>=20 / DD<20): `{_fmt(dd20['mixed_flag'].mean() * 100.0)}` / `{_fmt(non['mixed_flag'].mean() * 100.0)}`")
    lines.append(f"- Risk breach ratio % (DD>=20 / DD<20): `{_fmt(dd20['risk_breach'].mean() * 100.0)}` / `{_fmt(non['risk_breach'].mean() * 100.0)}`")
    lines.append(f"- Long-trap risk ratio % (DD>=20 / DD<20): `{_fmt(dd20['long_trap_risk_flag'].mean() * 100.0)}` / `{_fmt(non['long_trap_risk_flag'].mean() * 100.0)}`")
    lines.append(f"- Avg risk gap % (DD>=20 / DD<20): `{_fmt(dd20['risk_gap_pct'].mean())}` / `{_fmt(non['risk_gap_pct'].mean())}`")
    lines.append(f"- Avg retrace % (DD>=20 / DD<20): `{_fmt(dd20['retrace_12_pct'].mean())}` / `{_fmt(non['retrace_12_pct'].mean())}`")
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
            f"avg risk gap `{_fmt(worst.iloc[0]['avg_risk_gap_pct'])}%`, "
            f"trap ratio `{_fmt(worst.iloc[0]['long_trap_ratio_pct'])}%`)"
        )
    lines.append("")
    lines.append("## Regime Bucket Stats")
    lines.append("| Dimension | Bucket | Bars | DD>=20 Rate % | Avg DD % | P90 DD % | Avg EMA State | Mixed % | Avg Risk Gap % | Avg Retrace % | Trap % |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, r in regime_stats.iterrows():
        lines.append(
            f"| {r['regime_dimension']} | {r['bucket']} | {int(r['bars'])} | {_fmt(r['dd20_rate_pct'])} | {_fmt(r['avg_drawdown_pct'])} | "
            f"{_fmt(r['p90_drawdown_pct'])} | {_fmt(r['avg_ema_state'])} | {_fmt(r['mixed_ratio_pct'])} | {_fmt(r['avg_risk_gap_pct'])} | "
            f"{_fmt(r['avg_retrace_12_pct'])} | {_fmt(r['long_trap_ratio_pct'])} |"
        )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Episodes: `{OUT_EPISODES}`")
    lines.append(f"- Regime stats: `{OUT_REGIME_STATS}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    m22 = load_module("m22_002", BASE_22_PATH)
    base_module = m22.load_module("m002_002", m22.BASE_002_PATH)
    helper_module = m22.load_module("m04_002", m22.BASE_04_PATH)

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
        raise RuntimeError("Empty equity curve for 00_2 analysis.")

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
