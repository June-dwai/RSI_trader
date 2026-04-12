from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OUT_BASE = "107_backtest_btcusdt_4h_ema200_counter_gap_study"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_SUMMARY_CSV = Path(f"{OUT_BASE}_summary.csv")
OUT_DISTRIBUTION_CSV = Path(f"{OUT_BASE}_distribution.csv")
OUT_COVERAGE_CSV = Path(f"{OUT_BASE}_coverage.csv")
OUT_EVENT_STATS_CSV = Path(f"{OUT_BASE}_event_stats.csv")
OUT_SWEEP_CSV = Path(f"{OUT_BASE}_sweep.csv")

DATA_DIR = Path("historical_data_mainnet")
SYMBOL = "BTCUSDT"
START = pd.Timestamp("2022-01-01")
EMA_PERIOD = 200
RESAMPLE_RULE = "15min"
FEE_RATE = 0.0004
ROUND_TRIP_FEE_PCT = FEE_RATE * 2.0 * 100.0

COVERAGE_THRESHOLDS = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0]
EVENT_THRESHOLDS = [4.0, 6.0, 8.0, 10.0, 12.0, 15.0]
HOLD_HOURS = [24, 48]
TP_GRID = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0]
SL_GRID = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]


@dataclass
class EventPath:
    timestamp: pd.Timestamp
    side: str
    threshold_pct: float
    entry_price: float
    entry_ema: float
    entry_gap_pct: float
    future_high: np.ndarray
    future_low: np.ndarray
    future_close: np.ndarray


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def _parse_cache_end(path: Path) -> pd.Timestamp:
    return pd.Timestamp(path.stem.split("_")[-1])


def _pick_latest_cache(symbol: str, timeframe: str, start_date: str) -> Path:
    matches = list(DATA_DIR.glob(f"{symbol}_{timeframe}_{start_date}_*.pkl"))
    if not matches:
        raise FileNotFoundError(f"No cache files for {symbol} {timeframe} {start_date}")
    return max(matches, key=_parse_cache_end)


def _load_cache(paths: list[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_pickle(path)
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        frames.append(df)
    merged = pd.concat(frames)
    merged = merged[~merged.index.duplicated(keep="first")].sort_index()
    return merged


def load_market_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    latest_1m = _pick_latest_cache(SYMBOL, "1m", "2025-01-01")
    latest_4h = _pick_latest_cache(SYMBOL, "4h", "2025-01-01")

    df_1m = _load_cache(
        [
            DATA_DIR / f"{SYMBOL}_1m_2022-01-01_2024-12-31.pkl",
            latest_1m,
        ]
    )
    df_4h = _load_cache(
        [
            DATA_DIR / f"{SYMBOL}_4h_2021-07-01_2021-12-31.pkl",
            DATA_DIR / f"{SYMBOL}_4h_2022-01-01_2024-12-31.pkl",
            latest_4h,
        ]
    )

    end_ts = min(df_1m.index.max(), _parse_cache_end(latest_1m) + pd.Timedelta(days=1) - pd.Timedelta(minutes=1))
    df_1m = df_1m[(df_1m.index >= START) & (df_1m.index <= end_ts)].copy()
    df_4h = df_4h[df_4h.index <= end_ts.ceil("4h")].copy()
    return df_1m, df_4h, end_ts


def build_market_frame(df_1m: pd.DataFrame, df_4h: pd.DataFrame) -> pd.DataFrame:
    bars = (
        df_1m.resample(RESAMPLE_RULE, label="right", closed="right")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
    )
    bars["timestamp"] = bars.index
    bars["bucket_4h"] = bars.index.floor("4h")

    ema = df_4h.copy()
    ema["ema200"] = ema["close"].ewm(span=EMA_PERIOD, adjust=False).mean().shift(1)

    bars = bars.merge(ema[["ema200"]], left_on="bucket_4h", right_index=True, how="left")
    bars["ema200"] = bars["ema200"].ffill()
    bars["gap_pct"] = ((bars["close"] - bars["ema200"]) / bars["ema200"] * 100.0).replace([np.inf, -np.inf], np.nan)
    bars["abs_gap_pct"] = bars["gap_pct"].abs()
    bars = bars.dropna(subset=["ema200", "gap_pct"]).copy()
    return bars.reset_index(drop=True)


def build_summary_table(market: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": SYMBOL,
                "resample_rule": RESAMPLE_RULE,
                "start": pd.to_datetime(market["timestamp"].min()),
                "end": pd.to_datetime(market["timestamp"].max()),
                "bars": int(len(market)),
                "below_ema_share_pct": float((market["gap_pct"] < 0).mean() * 100.0),
                "above_ema_share_pct": float((market["gap_pct"] > 0).mean() * 100.0),
                "mean_gap_pct": float(market["gap_pct"].mean()),
                "median_gap_pct": float(market["gap_pct"].median()),
                "median_abs_gap_pct": float(market["abs_gap_pct"].median()),
                "q05_gap_pct": float(market["gap_pct"].quantile(0.05)),
                "q25_gap_pct": float(market["gap_pct"].quantile(0.25)),
                "q50_gap_pct": float(market["gap_pct"].quantile(0.50)),
                "q75_gap_pct": float(market["gap_pct"].quantile(0.75)),
                "q95_gap_pct": float(market["gap_pct"].quantile(0.95)),
            }
        ]
    )


def build_distribution_table(market: pd.DataFrame) -> pd.DataFrame:
    quantiles = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
    rows: list[dict] = []
    groups = {
        "signed_gap_pct": market["gap_pct"],
        "below_gap_abs_pct": -market.loc[market["gap_pct"] < 0, "gap_pct"],
        "above_gap_abs_pct": market.loc[market["gap_pct"] > 0, "gap_pct"],
    }
    for group, series in groups.items():
        for q in quantiles:
            rows.append(
                {
                    "group": group,
                    "quantile": q,
                    "value_pct": float(series.quantile(q)),
                }
            )
    return pd.DataFrame(rows)


def build_coverage_table(market: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for threshold in COVERAGE_THRESHOLDS:
        below = float((market["gap_pct"] <= -threshold).mean() * 100.0)
        above = float((market["gap_pct"] >= threshold).mean() * 100.0)
        inside = float((market["abs_gap_pct"] < threshold).mean() * 100.0)
        rows.append(
            {
                "threshold_pct": threshold,
                "below_coverage_pct": below,
                "above_coverage_pct": above,
                "inside_band_pct": inside,
            }
        )
    return pd.DataFrame(rows)


def build_event_paths(market: pd.DataFrame, side: str, threshold_pct: float, max_hold_bars: int) -> list[EventPath]:
    gap = market["gap_pct"].to_numpy(dtype=float)
    close = market["close"].to_numpy(dtype=float)
    high = market["high"].to_numpy(dtype=float)
    low = market["low"].to_numpy(dtype=float)
    ema = market["ema200"].to_numpy(dtype=float)
    timestamps = pd.to_datetime(market["timestamp"]).to_numpy()

    if side == "long":
        signal_mask = (gap <= -threshold_pct) & np.r_[False, gap[:-1] > -threshold_pct]
    else:
        signal_mask = (gap >= threshold_pct) & np.r_[False, gap[:-1] < threshold_pct]

    indices = np.flatnonzero(signal_mask)
    indices = indices[indices < len(market) - 2]

    out: list[EventPath] = []
    for idx in indices:
        end = min(len(market) - 1, idx + max_hold_bars)
        if end <= idx:
            continue
        out.append(
            EventPath(
                timestamp=pd.Timestamp(timestamps[idx]),
                side=side,
                threshold_pct=float(threshold_pct),
                entry_price=float(close[idx]),
                entry_ema=float(ema[idx]),
                entry_gap_pct=float(gap[idx]),
                future_high=high[idx + 1 : end + 1].astype(float, copy=True),
                future_low=low[idx + 1 : end + 1].astype(float, copy=True),
                future_close=close[idx + 1 : end + 1].astype(float, copy=True),
            )
        )
    return out


def _first_true(mask: np.ndarray) -> int | None:
    if not bool(mask.any()):
        return None
    return int(np.flatnonzero(mask)[0])


def summarize_event_paths(events: list[EventPath], hold_bars: int) -> dict:
    if not events:
        return {
            "events": 0,
            "median_entry_gap_pct": np.nan,
            "half_reclaim_hit_rate_pct": np.nan,
            "ema_touch_hit_rate_pct": np.nan,
            "median_time_to_half_hours": np.nan,
            "median_time_to_ema_hours": np.nan,
            "median_mfe_pct": np.nan,
            "median_mae_pct": np.nan,
            "median_adverse_abs_pct": np.nan,
        }

    half_hits = 0
    ema_hits = 0
    half_times: list[float] = []
    ema_times: list[float] = []
    mfe_list: list[float] = []
    mae_list: list[float] = []
    entry_gap_abs: list[float] = []

    for event in events:
        highs = event.future_high[:hold_bars]
        lows = event.future_low[:hold_bars]
        entry = float(event.entry_price)
        entry_ema = float(event.entry_ema)
        half_target = entry + 0.5 * (entry_ema - entry)

        if event.side == "long":
            half_mask = highs >= half_target
            ema_mask = highs >= entry_ema
            mfe = (float(highs.max()) / entry - 1.0) * 100.0
            mae = (float(lows.min()) / entry - 1.0) * 100.0
        else:
            half_mask = lows <= half_target
            ema_mask = lows <= entry_ema
            mfe = (entry / float(lows.min()) - 1.0) * 100.0
            mae = (entry / float(highs.max()) - 1.0) * 100.0

        half_idx = _first_true(half_mask)
        ema_idx = _first_true(ema_mask)
        if half_idx is not None:
            half_hits += 1
            half_times.append((half_idx + 1) * 0.25)
        if ema_idx is not None:
            ema_hits += 1
            ema_times.append((ema_idx + 1) * 0.25)

        entry_gap_abs.append(abs(float(event.entry_gap_pct)))
        mfe_list.append(mfe)
        mae_list.append(mae)

    return {
        "events": int(len(events)),
        "median_entry_gap_pct": float(np.median(entry_gap_abs)),
        "half_reclaim_hit_rate_pct": float(half_hits / len(events) * 100.0),
        "ema_touch_hit_rate_pct": float(ema_hits / len(events) * 100.0),
        "median_time_to_half_hours": float(np.median(half_times)) if half_times else np.nan,
        "median_time_to_ema_hours": float(np.median(ema_times)) if ema_times else np.nan,
        "median_mfe_pct": float(np.median(mfe_list)),
        "median_mae_pct": float(np.median(mae_list)),
        "median_adverse_abs_pct": float(-np.median(mae_list)),
    }


def simulate_path(
    event: EventPath,
    hold_bars: int,
    tp_pct: float,
    sl_pct: float,
) -> tuple[float, str, float]:
    highs = event.future_high[:hold_bars]
    lows = event.future_low[:hold_bars]
    closes = event.future_close[:hold_bars]
    entry = float(event.entry_price)

    for idx, (hi, lo) in enumerate(zip(highs, lows), start=1):
        if event.side == "long":
            hit_sl = lo <= entry * (1.0 - sl_pct / 100.0)
            hit_tp = hi >= entry * (1.0 + tp_pct / 100.0)
            if hit_sl and hit_tp:
                return -sl_pct - ROUND_TRIP_FEE_PCT, "stop", idx * 0.25
            if hit_sl:
                return -sl_pct - ROUND_TRIP_FEE_PCT, "stop", idx * 0.25
            if hit_tp:
                return tp_pct - ROUND_TRIP_FEE_PCT, "tp", idx * 0.25
        else:
            hit_sl = hi >= entry * (1.0 + sl_pct / 100.0)
            hit_tp = lo <= entry * (1.0 - tp_pct / 100.0)
            if hit_sl and hit_tp:
                return -sl_pct - ROUND_TRIP_FEE_PCT, "stop", idx * 0.25
            if hit_sl:
                return -sl_pct - ROUND_TRIP_FEE_PCT, "stop", idx * 0.25
            if hit_tp:
                return tp_pct - ROUND_TRIP_FEE_PCT, "tp", idx * 0.25

    timeout_price = float(closes[-1])
    if event.side == "long":
        gross_return_pct = (timeout_price / entry - 1.0) * 100.0
    else:
        gross_return_pct = (entry / timeout_price - 1.0) * 100.0
    return gross_return_pct - ROUND_TRIP_FEE_PCT, "timeout", len(closes) * 0.25


def sweep_tp_sl(events: list[EventPath], hold_bars: int) -> pd.DataFrame:
    rows: list[dict] = []
    if not events:
        return pd.DataFrame(rows)

    for tp_pct in TP_GRID:
        for sl_pct in SL_GRID:
            returns: list[float] = []
            hold_hours: list[float] = []
            tp_hits = 0
            stop_hits = 0
            timeout_hits = 0
            positive_count = 0

            for event in events:
                ret_pct, exit_type, held_hours = simulate_path(event, hold_bars, tp_pct, sl_pct)
                returns.append(ret_pct)
                hold_hours.append(held_hours)
                if ret_pct > 0:
                    positive_count += 1
                if exit_type == "tp":
                    tp_hits += 1
                elif exit_type == "stop":
                    stop_hits += 1
                else:
                    timeout_hits += 1

            arr = np.asarray(returns, dtype=float)
            wins = arr[arr > 0]
            losses = arr[arr < 0]
            profit_factor = float(wins.sum() / abs(losses.sum())) if losses.size else np.nan

            rows.append(
                {
                    "side": events[0].side,
                    "threshold_pct": float(events[0].threshold_pct),
                    "hold_hours": int(hold_bars * 0.25),
                    "events": int(len(events)),
                    "tp_pct": float(tp_pct),
                    "sl_pct": float(sl_pct),
                    "expectancy_pct": float(arr.mean()),
                    "median_return_pct": float(np.median(arr)),
                    "win_rate_pct": float(positive_count / len(arr) * 100.0),
                    "tp_hit_rate_pct": float(tp_hits / len(arr) * 100.0),
                    "stop_hit_rate_pct": float(stop_hits / len(arr) * 100.0),
                    "timeout_rate_pct": float(timeout_hits / len(arr) * 100.0),
                    "avg_hold_hours": float(np.mean(hold_hours)),
                    "profit_factor": profit_factor,
                }
            )

    return pd.DataFrame(rows)


def build_event_and_sweep_tables(market: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    max_hold_bars = max(HOLD_HOURS) * 4
    event_rows: list[dict] = []
    sweep_frames: list[pd.DataFrame] = []

    for side in ["long", "short"]:
        for threshold in EVENT_THRESHOLDS:
            events = build_event_paths(market, side=side, threshold_pct=threshold, max_hold_bars=max_hold_bars)
            for hold in HOLD_HOURS:
                stats = summarize_event_paths(events, hold * 4)
                event_rows.append(
                    {
                        "side": side,
                        "threshold_pct": threshold,
                        "hold_hours": hold,
                        **stats,
                    }
                )
                sweep_frames.append(sweep_tp_sl(events, hold * 4))

    event_df = pd.DataFrame(event_rows)
    sweep_df = pd.concat(sweep_frames, ignore_index=True) if sweep_frames else pd.DataFrame()
    return event_df, sweep_df


def build_best_table(sweep_df: pd.DataFrame) -> pd.DataFrame:
    if sweep_df.empty:
        return pd.DataFrame()
    ranked = sweep_df.sort_values(
        ["side", "hold_hours", "threshold_pct", "expectancy_pct", "profit_factor", "win_rate_pct"],
        ascending=[True, True, True, False, False, False],
    )
    best = (
        ranked.groupby(["side", "hold_hours", "threshold_pct"], as_index=False)
        .first()
        .sort_values(["side", "hold_hours", "threshold_pct"])
        .reset_index(drop=True)
    )
    return best


def pick_recommendation(sweep_df: pd.DataFrame, side: str) -> pd.Series:
    if side == "long":
        mask = (
            (sweep_df["side"] == side)
            & (sweep_df["hold_hours"] == 48)
            & (sweep_df["events"] >= 200)
            & (sweep_df["tp_pct"].between(2.0, 3.0))
            & (sweep_df["sl_pct"].between(4.0, 6.0))
        )
    else:
        mask = (
            (sweep_df["side"] == side)
            & (sweep_df["hold_hours"] == 48)
            & (sweep_df["events"] >= 200)
            & (sweep_df["tp_pct"].between(2.0, 4.0))
            & (sweep_df["sl_pct"].between(1.5, 4.0))
        )

    ranked = sweep_df[mask].sort_values(
        ["expectancy_pct", "profit_factor", "win_rate_pct", "events"],
        ascending=[False, False, False, False],
    )
    if ranked.empty:
        ranked = sweep_df[sweep_df["side"] == side].sort_values(
            ["expectancy_pct", "profit_factor", "win_rate_pct", "events"],
            ascending=[False, False, False, False],
        )
    return ranked.iloc[0]


def save_plot(
    market: pd.DataFrame,
    coverage_df: pd.DataFrame,
    event_df: pd.DataFrame,
    best_df: pd.DataFrame,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    ax_hist, ax_cov, ax_mfe, ax_best = axes.flatten()

    ax_hist.hist(market["gap_pct"], bins=120, color="#1f77b4", alpha=0.85)
    ax_hist.axvline(0.0, color="black", linestyle="--", linewidth=1.0)
    ax_hist.set_title("Signed Gap vs Confirmed 4h EMA200")
    ax_hist.set_xlabel("Gap %")
    ax_hist.set_ylabel("Bars")
    ax_hist.grid(True, alpha=0.2)

    ax_cov.plot(coverage_df["threshold_pct"], coverage_df["below_coverage_pct"], marker="o", label="Below threshold")
    ax_cov.plot(coverage_df["threshold_pct"], coverage_df["above_coverage_pct"], marker="o", label="Above threshold")
    ax_cov.plot(coverage_df["threshold_pct"], coverage_df["inside_band_pct"], marker="o", label="Inside band")
    ax_cov.set_title("Whole-Period Gap Coverage")
    ax_cov.set_xlabel("Absolute gap threshold %")
    ax_cov.set_ylabel("Time coverage %")
    ax_cov.grid(True, alpha=0.2)
    ax_cov.legend(loc="upper right")

    e48 = event_df[event_df["hold_hours"] == 48].copy()
    for side, color in [("long", "#2ca02c"), ("short", "#d62728")]:
        sub = e48[e48["side"] == side].sort_values("threshold_pct")
        if sub.empty:
            continue
        ax_mfe.plot(sub["threshold_pct"], sub["median_mfe_pct"], marker="o", color=color, label=f"{side} median MFE")
        ax_mfe.plot(
            sub["threshold_pct"],
            sub["median_adverse_abs_pct"],
            marker="s",
            linestyle="--",
            color=color,
            alpha=0.75,
            label=f"{side} median adverse",
        )
    ax_mfe.set_title("48h Path Stats by Threshold")
    ax_mfe.set_xlabel("Threshold %")
    ax_mfe.set_ylabel("Percent move")
    ax_mfe.grid(True, alpha=0.2)
    ax_mfe.legend(loc="upper right")

    for side, hold, color in [
        ("long", 24, "#17becf"),
        ("long", 48, "#2ca02c"),
        ("short", 24, "#ff9896"),
        ("short", 48, "#d62728"),
    ]:
        sub = best_df[(best_df["side"] == side) & (best_df["hold_hours"] == hold)].sort_values("threshold_pct")
        if sub.empty:
            continue
        ax_best.plot(
            sub["threshold_pct"],
            sub["expectancy_pct"],
            marker="o",
            color=color,
            label=f"{side} {hold}h best expectancy",
        )
    ax_best.axhline(0.0, color="black", linestyle="--", linewidth=1.0)
    ax_best.set_title("Best TP/SL Expectancy by Threshold")
    ax_best.set_xlabel("Threshold %")
    ax_best.set_ylabel("Expectancy per event %")
    ax_best.grid(True, alpha=0.2)
    ax_best.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=170)
    plt.close(fig)


def save_report(
    summary_df: pd.DataFrame,
    coverage_df: pd.DataFrame,
    event_df: pd.DataFrame,
    best_df: pd.DataFrame,
    sweep_df: pd.DataFrame,
) -> None:
    summary = summary_df.iloc[0]
    long_pick = pick_recommendation(sweep_df, "long")
    short_pick = pick_recommendation(sweep_df, "short")

    q = {
        key: float(summary[key])
        for key in ["q05_gap_pct", "q25_gap_pct", "q50_gap_pct", "q75_gap_pct", "q95_gap_pct"]
    }

    lines: list[str] = []
    lines.append("# Study 107: Counter-EMA Gap Reversal")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Symbol: `{SYMBOL}`")
    lines.append(f"- Sample: `{pd.to_datetime(summary['start'])}` to `{pd.to_datetime(summary['end'])}`")
    lines.append(f"- Working bars: `{RESAMPLE_RULE}` built from cached 1m data")
    lines.append(f"- EMA anchor: confirmed 4h EMA200 (`ewm(span=200).mean().shift(1)`) mapped into the current 15m bar")
    lines.append("- Entry event: first 15m close that crosses below `-threshold%` for long, or above `+threshold%` for short")
    lines.append(
        f"- Exit sweep: fixed TP/SL, `24h` and `48h` max hold, round-trip fee `{ROUND_TRIP_FEE_PCT:.2f}%`, "
        "and conservative stop-first handling if TP and SL are both touched inside one 15m bar"
    )
    lines.append("- Important: this is an independent event study, not a flat-only sequential portfolio backtest")
    lines.append("")
    lines.append("## Whole-Period Gap Distribution")
    lines.append(f"- Bars analyzed: `{int(summary['bars'])}`")
    lines.append(
        f"- Time below / above EMA200: `{_fmt(summary['below_ema_share_pct'], 2)}%` / "
        f"`{_fmt(summary['above_ema_share_pct'], 2)}%`"
    )
    lines.append(
        f"- Signed gap quantiles (5 / 25 / 50 / 75 / 95): `{_fmt(q['q05_gap_pct'])}%`, "
        f"`{_fmt(q['q25_gap_pct'])}%`, `{_fmt(q['q50_gap_pct'])}%`, "
        f"`{_fmt(q['q75_gap_pct'])}%`, `{_fmt(q['q95_gap_pct'])}%`"
    )
    lines.append("")
    lines.append("| Threshold % | Below Coverage % | Above Coverage % | Inside Band % |")
    lines.append("| ---: | ---: | ---: | ---: |")
    for _, row in coverage_df.iterrows():
        lines.append(
            f"| {_fmt(row['threshold_pct'], 1)} | {_fmt(row['below_coverage_pct'], 2)} | "
            f"{_fmt(row['above_coverage_pct'], 2)} | {_fmt(row['inside_band_pct'], 2)} |"
        )
    lines.append("")
    lines.append("## 48h Reversion Path Stats")
    lines.append("| Side | Threshold % | Events | Median Entry Gap % | Half-Reclaim Hit % | EMA Touch % | Median MFE % | Median Adverse % |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in event_df[event_df["hold_hours"] == 48].sort_values(["side", "threshold_pct"]).iterrows():
        lines.append(
            f"| {row['side']} | {_fmt(row['threshold_pct'], 1)} | {int(row['events'])} | "
            f"{_fmt(row['median_entry_gap_pct'], 2)} | {_fmt(row['half_reclaim_hit_rate_pct'], 1)} | "
            f"{_fmt(row['ema_touch_hit_rate_pct'], 1)} | {_fmt(row['median_mfe_pct'], 2)} | "
            f"{_fmt(row['median_adverse_abs_pct'], 2)} |"
        )
    lines.append("")
    lines.append("## Best TP/SL per Threshold")
    lines.append("| Side | Hold h | Threshold % | TP % | SL % | Events | Expectancy % | Win Rate % | Profit Factor |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in best_df.sort_values(["side", "hold_hours", "threshold_pct"]).iterrows():
        lines.append(
            f"| {row['side']} | {int(row['hold_hours'])} | {_fmt(row['threshold_pct'], 1)} | "
            f"{_fmt(row['tp_pct'], 1)} | {_fmt(row['sl_pct'], 1)} | {int(row['events'])} | "
            f"{_fmt(row['expectancy_pct'], 3)} | {_fmt(row['win_rate_pct'], 1)} | {_fmt(row['profit_factor'], 3)} |"
        )
    lines.append("")
    lines.append("## Recommendation")
    lines.append(
        f"- Long candidate: below `-{_fmt(long_pick['threshold_pct'], 1)}%` with `48h` hold, "
        f"`TP {_fmt(long_pick['tp_pct'], 1)}%` / `SL {_fmt(long_pick['sl_pct'], 1)}%`. "
        f"Expectancy `{_fmt(long_pick['expectancy_pct'], 3)}%`, win rate `{_fmt(long_pick['win_rate_pct'], 1)}%`, "
        f"events `{int(long_pick['events'])}`."
    )
    lines.append(
        f"- Short candidate: above `+{_fmt(short_pick['threshold_pct'], 1)}%` with `48h` hold, "
        f"`TP {_fmt(short_pick['tp_pct'], 1)}%` / `SL {_fmt(short_pick['sl_pct'], 1)}%`. "
        f"Expectancy `{_fmt(short_pick['expectancy_pct'], 3)}%`, win rate `{_fmt(short_pick['win_rate_pct'], 1)}%`, "
        f"events `{int(short_pick['events'])}`."
    )
    lines.append("- EMA-touch take profit is too ambitious for this setup. Even after 48h, full EMA touch stays rare once the entry gap is deep.")
    lines.append("- Practical implication: treat this as a short-horizon snapback study. Fixed TP works better than waiting for full reversion to EMA200.")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    df_1m, df_4h, _ = load_market_data()
    market = build_market_frame(df_1m, df_4h)

    summary_df = build_summary_table(market)
    distribution_df = build_distribution_table(market)
    coverage_df = build_coverage_table(market)
    event_df, sweep_df = build_event_and_sweep_tables(market)
    best_df = build_best_table(sweep_df)

    summary_df.to_csv(OUT_SUMMARY_CSV, index=False)
    distribution_df.to_csv(OUT_DISTRIBUTION_CSV, index=False)
    coverage_df.to_csv(OUT_COVERAGE_CSV, index=False)
    event_df.to_csv(OUT_EVENT_STATS_CSV, index=False)
    sweep_df.to_csv(OUT_SWEEP_CSV, index=False)

    save_plot(market, coverage_df, event_df, best_df)
    save_report(summary_df, coverage_df, event_df, best_df, sweep_df)

    long_pick = pick_recommendation(sweep_df, "long")
    short_pick = pick_recommendation(sweep_df, "short")
    print(
        "study=107, "
        f"bars={len(market)}, "
        f"long={long_pick['threshold_pct']:.1f}%/tp{long_pick['tp_pct']:.1f}/sl{long_pick['sl_pct']:.1f}, "
        f"short={short_pick['threshold_pct']:.1f}%/tp{short_pick['tp_pct']:.1f}/sl{short_pick['sl_pct']:.1f}"
    )


if __name__ == "__main__":
    main()
