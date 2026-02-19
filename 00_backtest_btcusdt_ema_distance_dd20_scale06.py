from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_22_PATH = Path("22_backtest_btcusdt_dd_scale_entryscale_sweep.py")

OUT_PNG = Path("00_backtest_btcusdt_ema_distance_dd20_scale06.png")
OUT_MD = Path("00_backtest_btcusdt_ema_distance_dd20_scale06.md")
OUT_EPISODES = Path("00_backtest_btcusdt_ema_distance_dd20_scale06_episodes.csv")
OUT_THRESHOLDS = Path("00_backtest_btcusdt_ema_distance_dd20_scale06_thresholds.csv")

ENTRY_SCALE = 0.6
DD_THRESHOLD_PCT = 20.0
PLOT_RESAMPLE = "30min"


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


def build_analysis_frame(
    equity_curve: pd.DataFrame,
    df_1m: pd.DataFrame,
    df_4h: pd.DataFrame,
) -> pd.DataFrame:
    eq = equity_curve.copy()
    eq["timestamp"] = pd.to_datetime(eq["timestamp"])
    eq = eq.sort_values("timestamp")
    eq = eq[["timestamp", "equity"]].drop_duplicates(subset=["timestamp"]).set_index("timestamp")

    eq["equity_peak"] = eq["equity"].cummax().replace(0, np.nan)
    eq["drawdown_pct"] = ((eq["equity_peak"] - eq["equity"]) / eq["equity_peak"] * 100.0).fillna(0.0)

    p1 = df_1m.copy()
    p1 = p1[["close"]].astype(float)
    p1["timestamp_4h"] = p1.index.floor("4h")

    p4 = df_4h.copy()
    p4["ema200"] = p4["close"].ewm(span=200, adjust=False).mean().shift(1)
    p4 = p4[["ema200"]]

    p1 = p1.merge(p4, left_on="timestamp_4h", right_index=True, how="left")
    p1["ema200"] = p1["ema200"].ffill()
    p1.drop(columns=["timestamp_4h"], inplace=True)
    p1 = p1.rename(columns={"close": "btc_close"}).sort_index()

    p1["ema_gap_signed_pct"] = ((p1["btc_close"] - p1["ema200"]) / p1["ema200"] * 100.0).replace([np.inf, -np.inf], np.nan)
    p1["ema_below_pct"] = np.where(
        p1["btc_close"] < p1["ema200"],
        (p1["ema200"] - p1["btc_close"]) / p1["ema200"] * 100.0,
        0.0,
    )

    out = eq.join(p1[["btc_close", "ema200", "ema_gap_signed_pct", "ema_below_pct"]], how="left")
    out = out.dropna(subset=["btc_close", "ema200"]).copy()
    out["dd20"] = out["drawdown_pct"] >= DD_THRESHOLD_PCT
    return out


def extract_dd_episodes(df: pd.DataFrame, dd_threshold_pct: float) -> pd.DataFrame:
    mask = (df["drawdown_pct"] >= dd_threshold_pct).astype(bool)
    if mask.sum() == 0:
        return pd.DataFrame(
            columns=[
                "episode_id",
                "start",
                "end",
                "bars",
                "duration_hours",
                "duration_days",
                "max_drawdown_pct",
                "avg_drawdown_pct",
                "max_ema_below_pct",
                "avg_ema_below_pct",
            ]
        )

    grp = (mask != mask.shift(1)).cumsum()
    rows: list[dict] = []
    eid = 1
    for _, seg in df.groupby(grp):
        if not bool(seg["dd20"].iloc[0]):
            continue
        start = seg.index[0]
        end = seg.index[-1]
        bars = int(len(seg))
        duration_hours = float((end - start).total_seconds() / 3600.0)
        rows.append(
            {
                "episode_id": eid,
                "start": start,
                "end": end,
                "bars": bars,
                "duration_hours": duration_hours,
                "duration_days": duration_hours / 24.0,
                "max_drawdown_pct": float(seg["drawdown_pct"].max()),
                "avg_drawdown_pct": float(seg["drawdown_pct"].mean()),
                "max_ema_below_pct": float(seg["ema_below_pct"].max()),
                "avg_ema_below_pct": float(seg["ema_below_pct"].mean()),
            }
        )
        eid += 1
    return pd.DataFrame(rows)


def build_threshold_table(df: pd.DataFrame) -> pd.DataFrame:
    thresholds = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0]
    rows: list[dict] = []
    total_dd20 = int(df["dd20"].sum())
    total_bars = int(len(df))

    for t in thresholds:
        sub = df[df["ema_below_pct"] >= t]
        bars = int(len(sub))
        dd20_bars = int(sub["dd20"].sum()) if bars > 0 else 0
        p_dd20_given_gap = (dd20_bars / bars * 100.0) if bars > 0 else np.nan
        cover_dd20 = (dd20_bars / total_dd20 * 100.0) if total_dd20 > 0 else np.nan
        cover_all = (bars / total_bars * 100.0) if total_bars > 0 else np.nan
        rows.append(
            {
                "ema_below_threshold_pct": t,
                "bars_with_gap": bars,
                "bars_with_dd20_and_gap": dd20_bars,
                "p_dd20_given_gap_pct": p_dd20_given_gap,
                "dd20_coverage_pct": cover_dd20,
                "time_coverage_pct": cover_all,
            }
        )

    return pd.DataFrame(rows)


def save_plot(df: pd.DataFrame, episodes: pd.DataFrame):
    plot_df = (
        df[["btc_close", "ema200", "ema_below_pct", "drawdown_pct"]]
        .resample(PLOT_RESAMPLE)
        .last()
        .dropna()
    )

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(16, 10),
        sharex=True,
        gridspec_kw={"height_ratios": [2.0, 1.2, 1.2]},
    )
    ax_price, ax_gap, ax_dd = axes

    for _, ep in episodes.iterrows():
        s = pd.to_datetime(ep["start"])
        e = pd.to_datetime(ep["end"])
        for ax in axes:
            ax.axvspan(s, e, color="red", alpha=0.10, linewidth=0)

    ax_price.plot(plot_df.index, plot_df["btc_close"], color="#1f77b4", linewidth=1.0, label="BTC Close (1m->30m)")
    ax_price.plot(plot_df.index, plot_df["ema200"], color="#2ca02c", linewidth=1.0, label="4h EMA200 (confirmed)")
    ax_price.set_title("00 Study: BTC Price vs 4h EMA200 and DD>=20% Regions (Scale=0.6, 22-baseline)")
    ax_price.set_ylabel("Price (USDT)")
    ax_price.grid(True, alpha=0.2)
    ax_price.legend(loc="upper left")

    ax_gap.plot(plot_df.index, plot_df["ema_below_pct"], color="#ff7f0e", linewidth=1.0, label="EMA Below Distance %")
    ax_gap.fill_between(
        plot_df.index,
        np.zeros(len(plot_df)),
        plot_df["ema_below_pct"].values,
        color="#ff7f0e",
        alpha=0.20,
    )
    ax_gap.set_ylabel("Below EMA200 (%)")
    ax_gap.grid(True, alpha=0.2)
    ax_gap.legend(loc="upper left")

    ax_dd.plot(plot_df.index, plot_df["drawdown_pct"], color="#d62728", linewidth=1.0, label="Strategy Drawdown %")
    ax_dd.axhline(DD_THRESHOLD_PCT, color="black", linestyle="--", linewidth=1.0, label=f"DD {DD_THRESHOLD_PCT:.0f}% Threshold")
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


def save_report(metrics: dict, df: pd.DataFrame, episodes: pd.DataFrame, threshold_df: pd.DataFrame):
    pearson = float(df["drawdown_pct"].corr(df["ema_below_pct"], method="pearson"))
    spearman = float(df["drawdown_pct"].corr(df["ema_below_pct"], method="spearman"))

    dd20 = df[df["dd20"]]
    normal = df[~df["dd20"]]

    dd20_ratio = float(dd20.shape[0] / max(len(df), 1) * 100.0)
    mean_gap_dd20 = float(dd20["ema_below_pct"].mean()) if len(dd20) else np.nan
    mean_gap_normal = float(normal["ema_below_pct"].mean()) if len(normal) else np.nan
    q90_gap_dd20 = float(dd20["ema_below_pct"].quantile(0.90)) if len(dd20) else np.nan
    q90_gap_normal = float(normal["ema_below_pct"].quantile(0.90)) if len(normal) else np.nan

    ep_count = int(len(episodes))
    total_ep_days = float(episodes["duration_days"].sum()) if ep_count else 0.0
    longest = episodes.sort_values("duration_days", ascending=False).head(1) if ep_count else pd.DataFrame()
    worst = episodes.sort_values("max_drawdown_pct", ascending=False).head(1) if ep_count else pd.DataFrame()

    lines: list[str] = []
    lines.append("# 00 Study: EMA Distance vs Drawdown (22 baseline scale=0.6)")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Strategy base: `22_backtest_btcusdt_dd_scale_entryscale_sweep.py`")
    lines.append("- Case: `baseline_es0.6` (`dynamic_dd_scale=False`) with 4h hysteresis + fixed 5x trend hedge")
    lines.append("- Data: BTCUSDT 1m + 4h cached data (raw, no extra IQR/jump filtering)")
    lines.append(f"- DD threshold analyzed: `{DD_THRESHOLD_PCT:.0f}%`")
    lines.append("")
    lines.append("## Core Metrics")
    lines.append(f"- Final Equity: `{_fmt(metrics.get('final_equity', np.nan))}` USDT")
    lines.append(f"- Total Return: `{_fmt(metrics.get('total_return_pct', np.nan))}%`")
    lines.append(f"- CAGR: `{_fmt(metrics.get('cagr_pct', np.nan))}%`")
    lines.append(f"- MDD: `{_fmt(metrics.get('max_drawdown_pct', np.nan))}%`")
    lines.append(f"- Trades: `{int(metrics.get('trades', 0))}` (Long `{int(metrics.get('long_trades', 0))}`, Short `{int(metrics.get('short_trades', 0))}`)")
    lines.append("")
    lines.append("## EMA Distance vs Drawdown")
    lines.append(f"- Pearson corr (`drawdown_pct`, `ema_below_pct`): `{_fmt(pearson)}`")
    lines.append(f"- Spearman corr (`drawdown_pct`, `ema_below_pct`): `{_fmt(spearman)}`")
    lines.append(f"- Time in DD>=20%: `{dd20_ratio:.2f}%`")
    lines.append(f"- Avg EMA-below% when DD>=20: `{_fmt(mean_gap_dd20)}`")
    lines.append(f"- Avg EMA-below% when DD<20: `{_fmt(mean_gap_normal)}`")
    lines.append(f"- 90th pct EMA-below% (DD>=20 / DD<20): `{_fmt(q90_gap_dd20)}` / `{_fmt(q90_gap_normal)}`")
    lines.append("")
    lines.append("## DD>=20% Episodes")
    lines.append(f"- Episode count: `{ep_count}`")
    lines.append(f"- Total duration: `{total_ep_days:.2f}` days")
    if ep_count:
        lines.append(
            f"- Longest episode: `ID {int(longest.iloc[0]['episode_id'])}` "
            f"({pd.to_datetime(longest.iloc[0]['start'])} ~ {pd.to_datetime(longest.iloc[0]['end'])}, "
            f"{_fmt(longest.iloc[0]['duration_days'])} days, "
            f"max DD {_fmt(longest.iloc[0]['max_drawdown_pct'])}%)"
        )
        lines.append(
            f"- Worst DD episode: `ID {int(worst.iloc[0]['episode_id'])}` "
            f"({pd.to_datetime(worst.iloc[0]['start'])} ~ {pd.to_datetime(worst.iloc[0]['end'])}, "
            f"max DD {_fmt(worst.iloc[0]['max_drawdown_pct'])}%, "
            f"max EMA-below {_fmt(worst.iloc[0]['max_ema_below_pct'])}%)"
        )
    lines.append("")
    lines.append("## Threshold Table (ema_below_pct >= threshold)")
    lines.append("| Threshold % | Bars | DD>=20 Bars | P(DD>=20 | gap) % | DD>=20 Coverage % | Time Coverage % |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    for _, r in threshold_df.iterrows():
        lines.append(
            f"| {_fmt(r['ema_below_threshold_pct'], 1)} | {int(r['bars_with_gap'])} | {int(r['bars_with_dd20_and_gap'])} | "
            f"{_fmt(r['p_dd20_given_gap_pct'])} | {_fmt(r['dd20_coverage_pct'])} | {_fmt(r['time_coverage_pct'])} |"
        )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Episodes CSV: `{OUT_EPISODES}`")
    lines.append(f"- Threshold CSV: `{OUT_THRESHOLDS}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    m22 = load_module("m22_00", BASE_22_PATH)
    base_module = m22.load_module("m002_00", m22.BASE_002_PATH)
    helper_module = m22.load_module("m04_00", m22.BASE_04_PATH)

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
        raise RuntimeError("Empty equity curve. Cannot run 00 study.")

    analysis_df = build_analysis_frame(eq, df_1m, df_4h)
    episodes = extract_dd_episodes(analysis_df, DD_THRESHOLD_PCT)
    threshold_df = build_threshold_table(analysis_df)

    episodes.to_csv(OUT_EPISODES, index=False)
    threshold_df.to_csv(OUT_THRESHOLDS, index=False)
    save_plot(analysis_df, episodes)
    save_report(metrics, analysis_df, episodes, threshold_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_report={OUT_MD}")
    print(f"saved_episodes={OUT_EPISODES}")
    print(f"saved_thresholds={OUT_THRESHOLDS}")
    print(
        "summary="
        f"final_equity:{_fmt(metrics.get('final_equity', np.nan))},"
        f"mdd:{_fmt(metrics.get('max_drawdown_pct', np.nan))},"
        f"trades:{int(metrics.get('trades', 0))}"
    )


if __name__ == "__main__":
    run()
