from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")

OUT_BASE = "00_3_backtest_btcusdt_price_rsi6_4h"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_4H_CSV = Path(f"{OUT_BASE}_4h.csv")

RSI_PERIOD = 6
ADX_PERIOD = 14
PLOT_RESAMPLE = "30min"
RSI_LOW = 15.0
RSI_HIGH = 85.0


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


def load_data_no_filter(base_module) -> tuple[pd.DataFrame, pd.DataFrame]:
    periods_1m = [("2022-01-01", "2024-12-31"), ("2025-01-01", base_module.BACKTEST_END)]
    periods_4h = [
        ("2021-07-01", "2021-12-31"),
        ("2022-01-01", "2024-12-31"),
        ("2025-01-01", base_module.BACKTEST_END),
    ]
    df_1m = base_module._load_cached_df(base_module.SYMBOL, "1m", periods_1m).sort_index()
    df_4h = base_module._load_cached_df(base_module.SYMBOL, "4h", periods_4h).sort_index()
    return df_1m, df_4h


def compute_rsi(series: pd.Series, period: int = 6) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    rsi[(avg_loss == 0) & (avg_gain > 0)] = 100
    rsi[(avg_gain == 0) & (avg_loss > 0)] = 0
    rsi[(avg_gain == 0) & (avg_loss == 0)] = 50
    return rsi.fillna(50)


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr = tr.rolling(window=period).mean()
    plus_di = 100.0 * pd.Series(pos_dm, index=df.index).rolling(window=period).mean() / atr
    minus_di = 100.0 * pd.Series(neg_dm, index=df.index).rolling(window=period).mean() / atr
    dx = (100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di)).abs()
    adx = dx.rolling(window=period).mean()
    return adx


def build_frames(df_1m: pd.DataFrame, df_4h: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    p4 = df_4h.copy()
    p4["ema200"] = p4["close"].ewm(span=200, adjust=False).mean().shift(1)
    p4["rsi6_raw"] = compute_rsi(p4["close"].astype(float), period=RSI_PERIOD)
    p4["rsi6_confirmed"] = p4["rsi6_raw"].shift(1)
    p4["adx14_raw"] = compute_adx(p4, period=ADX_PERIOD)
    p4["adx14_confirmed"] = p4["adx14_raw"].shift(1)
    p4["ema_gap_pct"] = ((p4["close"] - p4["ema200"]) / p4["ema200"] * 100.0).replace([np.inf, -np.inf], np.nan)
    p4["rsi50_abs_dev"] = (p4["rsi6_confirmed"] - 50.0).abs()
    p4["ema_rsi_mix_feature"] = p4["ema_gap_pct"] * p4["rsi50_abs_dev"]
    p4["ema_rsi_adx_mix_feature"] = p4["ema_rsi_mix_feature"] * p4["adx14_confirmed"]
    p4["next_ret_4h_pct"] = p4["close"].shift(-1) / p4["close"] - 1.0
    p4["next_ret_4h_pct"] = p4["next_ret_4h_pct"] * 100.0

    p1 = df_1m[["close"]].copy().astype(float)
    p1["timestamp_4h"] = p1.index.floor("4h")
    p1 = p1.merge(p4[["rsi6_confirmed", "ema200", "adx14_confirmed"]], left_on="timestamp_4h", right_index=True, how="left")
    p1.drop(columns=["timestamp_4h"], inplace=True)
    p1["rsi6_confirmed"] = p1["rsi6_confirmed"].ffill()
    p1["ema200"] = p1["ema200"].ffill()
    p1["adx14_confirmed"] = p1["adx14_confirmed"].ffill()
    p1.rename(columns={"close": "btc_close"}, inplace=True)
    p1["ema_gap_pct"] = ((p1["btc_close"] - p1["ema200"]) / p1["ema200"] * 100.0).replace([np.inf, -np.inf], np.nan)
    p1["rsi50_abs_dev"] = (p1["rsi6_confirmed"] - 50.0).abs()
    p1["ema_rsi_mix_feature"] = p1["ema_gap_pct"] * p1["rsi50_abs_dev"]
    p1["ema_rsi_adx_mix_feature"] = p1["ema_rsi_mix_feature"] * p1["adx14_confirmed"]

    return p1, p4


def summarize_4h(p4: pd.DataFrame) -> dict:
    t = p4[["close", "rsi6_confirmed", "next_ret_4h_pct"]].dropna().copy()
    if t.empty:
        return {
            "bars": 0,
            "rsi_mean": np.nan,
            "rsi_std": np.nan,
            "time_rsi_le_low_pct": np.nan,
            "time_rsi_ge_high_pct": np.nan,
            "next_ret_when_rsi_le_low": np.nan,
            "next_ret_when_rsi_ge_high": np.nan,
            "next_ret_when_between": np.nan,
        }

    low = t[t["rsi6_confirmed"] <= RSI_LOW]
    high = t[t["rsi6_confirmed"] >= RSI_HIGH]
    mid = t[(t["rsi6_confirmed"] > RSI_LOW) & (t["rsi6_confirmed"] < RSI_HIGH)]

    return {
        "bars": int(len(t)),
        "rsi_mean": float(t["rsi6_confirmed"].mean()),
        "rsi_std": float(t["rsi6_confirmed"].std(ddof=0)),
        "time_rsi_le_low_pct": float((t["rsi6_confirmed"] <= RSI_LOW).mean() * 100.0),
        "time_rsi_ge_high_pct": float((t["rsi6_confirmed"] >= RSI_HIGH).mean() * 100.0),
        "next_ret_when_rsi_le_low": float(low["next_ret_4h_pct"].mean()) if len(low) else np.nan,
        "next_ret_when_rsi_ge_high": float(high["next_ret_4h_pct"].mean()) if len(high) else np.nan,
        "next_ret_when_between": float(mid["next_ret_4h_pct"].mean()) if len(mid) else np.nan,
    }


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


def save_plot(plot_df: pd.DataFrame):
    res = (
        plot_df[["btc_close", "rsi6_confirmed", "ema_rsi_mix_feature", "ema_rsi_adx_mix_feature"]]
        .resample(PLOT_RESAMPLE)
        .last()
        .dropna()
    )

    high_intervals = _extract_true_intervals(res["rsi6_confirmed"] >= RSI_HIGH)
    low_intervals = _extract_true_intervals(res["rsi6_confirmed"] <= RSI_LOW)

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(16, 13),
        sharex=True,
        gridspec_kw={"height_ratios": [2.0, 1.0, 1.0, 1.0]},
    )
    ax_px, ax_rsi, ax_feat, ax_feat2 = axes

    for s, e in high_intervals:
        ax_px.axvspan(s, e, color="#2ca02c", alpha=0.08, zorder=0)
        ax_rsi.axvspan(s, e, color="#2ca02c", alpha=0.08, zorder=0)
        ax_feat.axvspan(s, e, color="#2ca02c", alpha=0.08, zorder=0)
        ax_feat2.axvspan(s, e, color="#2ca02c", alpha=0.08, zorder=0)
    for s, e in low_intervals:
        ax_px.axvspan(s, e, color="#d62728", alpha=0.08, zorder=0)
        ax_rsi.axvspan(s, e, color="#d62728", alpha=0.08, zorder=0)
        ax_feat.axvspan(s, e, color="#d62728", alpha=0.08, zorder=0)
        ax_feat2.axvspan(s, e, color="#d62728", alpha=0.08, zorder=0)

    ax_px.plot(res.index, res["btc_close"], color="#1f77b4", linewidth=1.0, label="BTC Close")
    ax_px.set_title("00_3 Study: BTC Price with Confirmed 4h RSI(6)")
    ax_px.set_ylabel("Price (USDT)")
    ax_px.grid(True, alpha=0.2)
    ax_px.legend(loc="upper left")

    ax_rsi.plot(res.index, res["rsi6_confirmed"], color="#d62728", linewidth=0.9, label="4h RSI(6) confirmed")
    ax_rsi.axhline(RSI_HIGH, color="#2ca02c", linestyle="--", linewidth=0.8, alpha=0.8)
    ax_rsi.axhline(50, color="#7f7f7f", linestyle="--", linewidth=0.7, alpha=0.7)
    ax_rsi.axhline(RSI_LOW, color="#d62728", linestyle="--", linewidth=0.8, alpha=0.8)
    ax_rsi.set_ylim(0, 100)
    ax_rsi.set_ylabel("RSI")
    ax_rsi.set_xlabel("Time")
    ax_rsi.grid(True, alpha=0.2)
    ax_rsi.legend(loc="upper left")

    ax_feat.plot(
        res.index,
        res["ema_rsi_mix_feature"],
        color="#9467bd",
        linewidth=0.9,
        label="EMA gap % * abs(RSI-50)",
    )
    ax_feat.axhline(0.0, color="#7f7f7f", linestyle="--", linewidth=0.7, alpha=0.7)
    ax_feat.set_ylabel("Feature")
    ax_feat.set_xlabel("Time")
    ax_feat.grid(True, alpha=0.2)
    ax_feat.legend(loc="upper left")

    ax_feat2.plot(
        res.index,
        res["ema_rsi_adx_mix_feature"],
        color="#8c564b",
        linewidth=0.9,
        label="EMA gap % * abs(RSI-50) * ADX14(4h)",
    )
    ax_feat2.axhline(0.0, color="#7f7f7f", linestyle="--", linewidth=0.7, alpha=0.7)
    ax_feat2.set_ylabel("Feature*ADX")
    ax_feat2.set_xlabel("Time")
    ax_feat2.grid(True, alpha=0.2)
    ax_feat2.legend(loc="upper left")

    ax_feat2.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax_feat2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(plot_df: pd.DataFrame, p4: pd.DataFrame, stats: dict):
    period_start = pd.to_datetime(plot_df.index.min()) if len(plot_df) else pd.NaT
    period_end = pd.to_datetime(plot_df.index.max()) if len(plot_df) else pd.NaT

    lines: list[str] = []
    lines.append("# 00_3 Study: 4h RSI(6) under BTC Price")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Symbol: `BTCUSDT`")
    lines.append(f"- Data period: `{period_start}` ~ `{period_end}`")
    lines.append("- Data source: raw cached 1m/4h (no additional filtering)")
    lines.append("- RSI definition: Wilder-style `RSI(6)` on 4h close")
    lines.append(f"- Regime thresholds: low `<= {int(RSI_LOW)}`, high `>= {int(RSI_HIGH)}`")
    lines.append("- No-lookahead for display: `rsi6_confirmed = rsi6_raw.shift(1)`")
    lines.append("- Shading: RSI>=85 intervals = light green, RSI<=15 intervals = light red (all panels)")
    lines.append("- Added feature: `ema_rsi_mix_feature = ema_gap_pct * abs(rsi6_confirmed - 50)`")
    lines.append("- where `ema_gap_pct = (close - ema200) / ema200 * 100`")
    lines.append("- Added feature2: `ema_rsi_adx_mix_feature = ema_rsi_mix_feature * adx14_confirmed`")
    lines.append("- where `adx14_confirmed = adx14_raw.shift(1)` on 4h")
    lines.append("")
    lines.append("## 4h RSI Summary")
    lines.append(f"- Bars: `{int(stats['bars'])}`")
    lines.append(f"- Mean / Std: `{_fmt(stats['rsi_mean'])}` / `{_fmt(stats['rsi_std'])}`")
    lines.append(f"- Time RSI<={int(RSI_LOW)}: `{_fmt(stats['time_rsi_le_low_pct'])}%`")
    lines.append(f"- Time RSI>={int(RSI_HIGH)}: `{_fmt(stats['time_rsi_ge_high_pct'])}%`")
    lines.append("")
    lines.append("## Conditional Next 4h Return (for quick intuition)")
    lines.append(f"- Avg next 4h return when RSI<={int(RSI_LOW)}: `{_fmt(stats['next_ret_when_rsi_le_low'])}%`")
    lines.append(f"- Avg next 4h return when {int(RSI_LOW)}<RSI<{int(RSI_HIGH)}: `{_fmt(stats['next_ret_when_between'])}%`")
    lines.append(f"- Avg next 4h return when RSI>={int(RSI_HIGH)}: `{_fmt(stats['next_ret_when_rsi_ge_high'])}%`")
    lines.append("")
    f = plot_df["ema_rsi_mix_feature"].dropna()
    f2 = plot_df["ema_rsi_adx_mix_feature"].dropna()
    lines.append("## Feature Summary")
    lines.append("- Feature1 = `ema_gap_pct * abs(rsi6_confirmed - 50)`")
    lines.append(f"  - Mean / Std: `{_fmt(f.mean())}` / `{_fmt(f.std(ddof=0))}`")
    lines.append(f"  - P10 / P50 / P90: `{_fmt(f.quantile(0.10))}` / `{_fmt(f.quantile(0.50))}` / `{_fmt(f.quantile(0.90))}`")
    lines.append("- Feature2 = `Feature1 * adx14_confirmed`")
    lines.append(f"  - Mean / Std: `{_fmt(f2.mean())}` / `{_fmt(f2.std(ddof=0))}`")
    lines.append(f"  - P10 / P50 / P90: `{_fmt(f2.quantile(0.10))}` / `{_fmt(f2.quantile(0.50))}` / `{_fmt(f2.quantile(0.90))}`")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- 4h data: `{OUT_4H_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    base_module = load_module("m002_00_3", BASE_002_PATH)

    df_1m, df_4h = load_data_no_filter(base_module)
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()

    plot_df, p4 = build_frames(df_1m, df_4h)
    if plot_df.empty:
        raise RuntimeError("Empty plot frame")

    save_plot(plot_df)

    out4 = p4[
        [
            "open",
            "high",
            "low",
            "close",
            "ema200",
            "ema_gap_pct",
            "rsi6_raw",
            "rsi6_confirmed",
            "rsi50_abs_dev",
            "adx14_raw",
            "adx14_confirmed",
            "ema_rsi_mix_feature",
            "ema_rsi_adx_mix_feature",
            "next_ret_4h_pct",
        ]
    ].copy()
    out4.to_csv(OUT_4H_CSV, index_label="timestamp")

    stats = summarize_4h(p4)
    save_report(plot_df, p4, stats)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_4h={OUT_4H_CSV}")
    print(f"saved_report={OUT_MD}")
    print(
        " ".join(
            [
                f"rsi_mean={_fmt(stats['rsi_mean'])}",
                f"rsi_le_{int(RSI_LOW)}_pct={_fmt(stats['time_rsi_le_low_pct'])}",
                f"rsi_ge_{int(RSI_HIGH)}_pct={_fmt(stats['time_rsi_ge_high_pct'])}",
            ]
        )
    )


if __name__ == "__main__":
    run()
