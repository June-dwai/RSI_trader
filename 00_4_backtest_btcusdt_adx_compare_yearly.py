from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")

OUT_BASE = "00_4_backtest_btcusdt_adx_compare_yearly"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_YEARLY_CSV = Path(f"{OUT_BASE}_yearly.csv")

ADX_PERIOD = 14
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


def load_data_1m(base_module) -> pd.DataFrame:
    periods_1m = [("2022-01-01", "2024-12-31"), ("2025-01-01", base_module.BACKTEST_END)]
    df_1m = base_module._load_cached_df(base_module.SYMBOL, "1m", periods_1m).sort_index()
    df_1m = df_1m[(df_1m.index >= base_module.BACKTEST_START) & (df_1m.index <= base_module.BACKTEST_END)].copy()
    return df_1m


def compute_adx_35_style(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period).mean() / atr)
    minus_di = 100 * (minus_dm.abs().ewm(alpha=1 / period).mean() / atr)
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).abs()) * 100
    adx = ((dx.shift(1) * (period - 1)) + dx) / period
    return adx.ewm(alpha=1 / period).mean().fillna(0)


def compute_adx_002_style(df: pd.DataFrame, period: int = 14) -> pd.Series:
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
    plus_di = 100 * pd.Series(pos_dm, index=df.index).rolling(window=period).mean() / atr
    minus_di = 100 * pd.Series(neg_dm, index=df.index).rolling(window=period).mean() / atr
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).abs()
    return dx.rolling(window=period).mean()


def build_compare_df(df_1m: pd.DataFrame) -> pd.DataFrame:
    out = df_1m[["close"]].copy().astype(float)
    out["adx_35"] = compute_adx_35_style(df_1m, period=ADX_PERIOD)
    out["adx_002"] = compute_adx_002_style(df_1m, period=ADX_PERIOD)
    out["adx_diff"] = out["adx_35"] - out["adx_002"]

    out["mult_35"] = np.select(
        [out["adx_35"] >= 50, out["adx_35"] >= 40],
        [3, 2],
        default=1,
    )
    out["mult_002"] = np.select(
        [out["adx_002"] >= 50, out["adx_002"] >= 40],
        [3, 2],
        default=1,
    )
    out["mult_equal"] = out["mult_35"] == out["mult_002"]
    return out


def summarize_yearly(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for year, g in df.groupby(df.index.year):
        t = g.dropna(subset=["adx_35", "adx_002"]).copy()
        if t.empty:
            continue

        rows.append(
            {
                "year": int(year),
                "bars": int(len(t)),
                "adx35_mean": float(t["adx_35"].mean()),
                "adx002_mean": float(t["adx_002"].mean()),
                "adx35_ge40_pct": float((t["adx_35"] >= 40).mean() * 100.0),
                "adx002_ge40_pct": float((t["adx_002"] >= 40).mean() * 100.0),
                "adx35_ge50_pct": float((t["adx_35"] >= 50).mean() * 100.0),
                "adx002_ge50_pct": float((t["adx_002"] >= 50).mean() * 100.0),
                "mult_disagree_pct": float((~t["mult_equal"]).mean() * 100.0),
                "adx_abs_diff_mean": float((t["adx_diff"]).abs().mean()),
                "adx_abs_diff_p95": float((t["adx_diff"]).abs().quantile(0.95)),
            }
        )
    return pd.DataFrame(rows).sort_values("year")


def save_plot(df: pd.DataFrame):
    res = df[["adx_35", "adx_002", "adx_diff"]].resample(PLOT_RESAMPLE).last().dropna(how="all")
    years = sorted(int(y) for y in res.index.year.unique())
    if not years:
        raise RuntimeError("No yearly data to plot.")

    fig, axes = plt.subplots(len(years), 1, figsize=(16, max(3.2 * len(years), 7.0)), sharey=True)
    if len(years) == 1:
        axes = [axes]

    for ax, y in zip(axes, years):
        y0 = pd.Timestamp(f"{y}-01-01")
        y1 = pd.Timestamp(f"{y + 1}-01-01")
        d = res[(res.index >= y0) & (res.index < y1)]
        if d.empty:
            continue

        ax.plot(d.index, d["adx_35"], color="#1f77b4", linewidth=0.8, label="ADX (35 style)")
        ax.plot(d.index, d["adx_002"], color="#ff7f0e", linewidth=0.8, alpha=0.9, label="ADX (002 style)")
        ax.axhline(40, color="#7f7f7f", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.axhline(50, color="#7f7f7f", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.set_ylabel(f"{y}\nADX")
        ax.grid(True, alpha=0.2)
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.set_ylim(0, 100)

    axes[0].legend(loc="upper left", ncol=2)
    axes[0].set_title("00_4 Study: BTCUSDT 1m ADX Comparison by Year (35 vs 002 method)")
    axes[-1].set_xlabel("Time")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(summary_df: pd.DataFrame):
    lines: list[str] = []
    lines.append("# 00_4 ADX Comparison (Yearly)")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Symbol: `BTCUSDT`")
    lines.append("- Timeframe for ADX: `1m`")
    lines.append("- ADX period: `14`")
    lines.append("- Compared methods:")
    lines.append("  1) `35-style`: mixed EWM smoothing ADX")
    lines.append("  2) `002-style`: rolling mean ADX")
    lines.append(f"- Plot resample: `{PLOT_RESAMPLE}`")
    lines.append("")
    lines.append("## Yearly Stats")
    lines.append("| Year | Bars | ADX35 Mean | ADX002 Mean | ADX35>=40 % | ADX002>=40 % | ADX35>=50 % | ADX002>=50 % | Mult disagree % | |ADX diff| mean | |ADX diff| p95 |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    if summary_df.empty:
        lines.append("| N/A | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |")
    else:
        for _, r in summary_df.iterrows():
            lines.append(
                f"| {int(r['year'])} | {int(r['bars'])} | {_fmt(r['adx35_mean'])} | {_fmt(r['adx002_mean'])} | "
                f"{_fmt(r['adx35_ge40_pct'])} | {_fmt(r['adx002_ge40_pct'])} | {_fmt(r['adx35_ge50_pct'])} | "
                f"{_fmt(r['adx002_ge50_pct'])} | {_fmt(r['mult_disagree_pct'])} | {_fmt(r['adx_abs_diff_mean'])} | {_fmt(r['adx_abs_diff_p95'])} |"
            )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Report: `{OUT_MD}`")
    lines.append(f"- Yearly CSV: `{OUT_YEARLY_CSV}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    base = load_module("m002_00_4", BASE_002_PATH)
    df_1m = load_data_1m(base)
    cmp_df = build_compare_df(df_1m)
    yearly = summarize_yearly(cmp_df)
    yearly.to_csv(OUT_YEARLY_CSV, index=False)
    save_plot(cmp_df)
    save_report(yearly)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_report={OUT_MD}")
    print(f"saved_yearly_csv={OUT_YEARLY_CSV}")
    if not yearly.empty:
        last = yearly.iloc[-1]
        print(
            "latest_year="
            f"{int(last['year'])}, "
            f"mult_disagree_pct={_fmt(last['mult_disagree_pct'])}, "
            f"adx35_mean={_fmt(last['adx35_mean'])}, "
            f"adx002_mean={_fmt(last['adx002_mean'])}"
        )


if __name__ == "__main__":
    run()
