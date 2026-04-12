from __future__ import annotations

import importlib.util
import io
import json
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DATA_DIR = Path("historical_data_mainnet")

SOURCE_47 = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
SOURCE_76 = Path("76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py")
SOURCE_102 = Path("102_backtest_ethusdt_case123_volatility_scaled_tune.py")
SOURCE_111 = Path("111_backtest_btcusdt_sr_smc_5m_profitmax.py")
SOURCE_114 = Path("114_backtest_btcusdt_best_with_sr_smc_filters.py")
SOURCE_117 = Path("117_backtest_btcusdt_115_highcagr_push.py")
SOURCE_126 = Path("126_backtest_btcusdt_case3_long_quality_push.py")

OUT_BASE = "129_backtest_ethusdt_case2_vs_case3best_mix"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

SYMBOL = "ETHUSDT"
PORTFOLIO_CAPITAL = 2000.0
SLEEVE_INITIAL_CAPITAL = 1000.0
BACKTEST_START = pd.Timestamp("2021-01-01 00:00:00")
ANALYSIS_2026_START = pd.Timestamp("2026-01-01 00:00:00")

CASE3_VARIANT = "lb4_delay9_capna_cd0"
CASE3_OUTPUT_LABEL = f"{CASE3_VARIANT}_only"
CASE3_CFG = {
    "variant": CASE3_VARIANT,
    "leverage": 3.0,
    "gate_bars": 12,
    "body_atr_mult": 0.25,
    "short_tp_return_pct": 20.0,
    "max_bearish_above_for_long": 4,
    "long_bullish_delay_bars": 9,
    "long_premium_cap_red_avg_pct": np.nan,
    "long_short_sweep_cooldown_bars": 0,
}

ETH_2021_1M_FILE = DATA_DIR / "ETHUSDT_1m_2021-01-01_2021-12-31.pkl"
ETH_2022_2024_1M_FILE = DATA_DIR / "ETHUSDT_1m_2022-01-01_2024-12-31.pkl"

BINANCE_DATA_ROOT = "https://data.binance.vision/data/futures/um"
BINANCE_FAPI_ROOT = "https://fapi.binance.com"


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


def _date_token(ts: pd.Timestamp) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


def _parse_end_token(path: Path) -> pd.Timestamp:
    return pd.Timestamp(path.stem.split("_")[-1])


def _request_json(url: str) -> object:
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def _request_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def _normalize_kline_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    first_value = str(df.iloc[0, 0]).strip().lower()
    if first_value in {"open_time", "timestamp"}:
        df = df.iloc[1:].copy()

    df = df.iloc[:, :6].copy()
    df.columns = ["open_time", "open", "high", "low", "close", "volume"]
    df["open_time"] = pd.to_numeric(df["open_time"], errors="coerce")
    df = df.dropna(subset=["open_time"]).copy()
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close", "volume"]).copy()
    df["timestamp"] = pd.to_datetime(df["open_time"].astype("int64"), unit="ms", utc=True).dt.tz_localize(None)
    out = df.set_index("timestamp")[["open", "high", "low", "close", "volume"]].sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out


def _load_zip_klines(url: str) -> pd.DataFrame:
    raw = _request_bytes(url)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        csv_names = [name for name in zf.namelist() if name.endswith(".csv")]
        if not csv_names:
            raise RuntimeError(f"No csv inside zip: {url}")
        with zf.open(csv_names[0]) as handle:
            frame = pd.read_csv(handle, header=None)
    return _normalize_kline_frame(frame)


def download_monthly_2021_1m(symbol: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for month in range(1, 13):
        month_token = f"2021-{month:02d}"
        url = (
            f"{BINANCE_DATA_ROOT}/monthly/klines/{symbol}/1m/"
            f"{symbol}-1m-{month_token}.zip"
        )
        print(f"[129] Downloading monthly 1m zip: {month_token}", flush=True)
        frames.append(_load_zip_klines(url))
    out = pd.concat(frames).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out


def get_latest_closed_kline_ts(symbol: str) -> pd.Timestamp:
    server_time_payload = _request_json(f"{BINANCE_FAPI_ROOT}/fapi/v1/time")
    if not isinstance(server_time_payload, dict) or "serverTime" not in server_time_payload:
        raise RuntimeError("Unexpected Binance server time payload")
    server_time_ms = int(server_time_payload["serverTime"])

    params = urllib.parse.urlencode({"symbol": symbol, "interval": "1m", "limit": 2})
    rows = _request_json(f"{BINANCE_FAPI_ROOT}/fapi/v1/klines?{params}")
    if not isinstance(rows, list) or len(rows) < 1:
        raise RuntimeError("Unexpected Binance klines payload")

    chosen = rows[-1]
    if int(chosen[6]) > server_time_ms and len(rows) >= 2:
        chosen = rows[-2]
    return pd.to_datetime(int(chosen[0]), unit="ms", utc=True).tz_localize(None)


def fetch_api_klines_1m(symbol: str, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> pd.DataFrame:
    start_ts = pd.Timestamp(start_ts)
    end_ts = pd.Timestamp(end_ts)
    if start_ts > end_ts:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    frames: list[pd.DataFrame] = []
    cursor = int(start_ts.timestamp() * 1000)
    end_ms = int(end_ts.timestamp() * 1000)

    while cursor <= end_ms:
        params = urllib.parse.urlencode(
            {
                "symbol": symbol,
                "interval": "1m",
                "startTime": cursor,
                "endTime": end_ms,
                "limit": 1500,
            }
        )
        rows = _request_json(f"{BINANCE_FAPI_ROOT}/fapi/v1/klines?{params}")
        if not isinstance(rows, list) or not rows:
            break

        frame = _normalize_kline_frame(pd.DataFrame(rows))
        if frame.empty:
            break
        frames.append(frame)

        last_open_ms = int(rows[-1][0])
        next_cursor = last_open_ms + 60_000
        if next_cursor <= cursor:
            break
        cursor = next_cursor

    if not frames:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    out = pd.concat(frames).sort_index()
    out = out[(out.index >= start_ts) & (out.index <= end_ts)].copy()
    out = out[~out.index.duplicated(keep="last")]
    return out


def ensure_eth_2021_file() -> Path:
    if ETH_2021_1M_FILE.exists():
        return ETH_2021_1M_FILE
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    frame = download_monthly_2021_1m(SYMBOL)
    frame.to_pickle(ETH_2021_1M_FILE)
    print(f"[129] Saved 2021 ETH 1m cache: {ETH_2021_1M_FILE}", flush=True)
    return ETH_2021_1M_FILE


def ensure_eth_2025_latest_file() -> tuple[Path, pd.Timestamp]:
    candidates = sorted(DATA_DIR.glob(f"{SYMBOL}_1m_2025-01-01_*.pkl"), key=_parse_end_token)
    if not candidates:
        raise FileNotFoundError("Missing ETH 2025+ base cache")

    latest_closed_ts = get_latest_closed_kline_ts(SYMBOL)
    base_path = candidates[-1]
    base_frame = pd.read_pickle(base_path).sort_index()
    base_frame = base_frame[~base_frame.index.duplicated(keep="last")]

    if pd.Timestamp(base_frame.index.max()) >= latest_closed_ts:
        return base_path, latest_closed_ts

    tail_start = pd.Timestamp(base_frame.index.max()) + pd.Timedelta(minutes=1)
    print(f"[129] Fetching ETH 1m API tail: {tail_start} -> {latest_closed_ts}", flush=True)
    tail = fetch_api_klines_1m(SYMBOL, tail_start, latest_closed_ts)
    merged = pd.concat([base_frame, tail]).sort_index()
    merged = merged[~merged.index.duplicated(keep="last")]

    out_path = DATA_DIR / f"{SYMBOL}_1m_2025-01-01_{_date_token(latest_closed_ts)}.pkl"
    merged.to_pickle(out_path)
    print(f"[129] Saved 2025+ ETH 1m cache: {out_path}", flush=True)
    return out_path, latest_closed_ts


def load_pickle_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_pickle(path)
    if not isinstance(frame.index, pd.DatetimeIndex):
        frame.index = pd.to_datetime(frame.index)
    frame = frame.sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    return frame


def load_eth_1m_2021plus() -> tuple[pd.DataFrame, pd.Timestamp, list[Path]]:
    path_2021 = ensure_eth_2021_file()
    path_2025, latest_closed_ts = ensure_eth_2025_latest_file()
    if not ETH_2022_2024_1M_FILE.exists():
        raise FileNotFoundError(f"Missing cache file: {ETH_2022_2024_1M_FILE}")

    frames = [
        load_pickle_frame(path_2021),
        load_pickle_frame(ETH_2022_2024_1M_FILE),
        load_pickle_frame(path_2025),
    ]
    merged = pd.concat(frames).sort_index()
    merged = merged[(merged.index >= BACKTEST_START) & (merged.index <= latest_closed_ts)].copy()
    merged = merged[~merged.index.duplicated(keep="last")]
    return merged, latest_closed_ts, [path_2021, ETH_2022_2024_1M_FILE, path_2025]


def resample_ohlc(df_1m: pd.DataFrame, rule: str) -> pd.DataFrame:
    out = (
        df_1m.resample(rule)
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna()
    )
    out.index.name = "timestamp"
    return out


def load_eth_market_2021plus() -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp, list[Path]]:
    df_1m, latest_closed_ts, used_paths = load_eth_1m_2021plus()
    df_4h = resample_ohlc(df_1m, "4h")
    return df_1m, df_4h, latest_closed_ts, used_paths


def scale_curve(curve: pd.DataFrame, initial_capital: float, target_capital: float) -> pd.DataFrame:
    out = curve.copy()
    out["equity"] = out["equity"].astype(float) * (float(target_capital) / float(initial_capital))
    return out


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


def compute_window_stats(curve: pd.DataFrame, start_ts: pd.Timestamp, initial_capital: float | None = None) -> dict:
    seg = curve[pd.to_datetime(curve["timestamp"]) >= pd.Timestamp(start_ts)].copy()
    if seg.empty:
        return {"return_pct": np.nan, "mdd_pct": np.nan}
    start_eq = float(seg["equity"].iloc[0]) if initial_capital is None else float(initial_capital)
    end_eq = float(seg["equity"].iloc[-1])
    if start_eq <= 0:
        return {"return_pct": np.nan, "mdd_pct": np.nan}
    dd = seg["equity"].astype(float) / seg["equity"].cummax().astype(float) - 1.0
    return {
        "return_pct": (end_eq / start_eq - 1.0) * 100.0,
        "mdd_pct": -float(dd.min() * 100.0),
    }


def build_case2_curve(df_1m: pd.DataFrame, df_4h: pd.DataFrame, latest_closed_ts: pd.Timestamp) -> pd.DataFrame:
    study102 = load_module("study102_for_129_case2", SOURCE_102)
    base = study102.load_module("m002_129_case2", study102.BASE_002_PATH)
    helper = study102.load_module("m04_129_case2", study102.BASE_04_PATH)
    m32 = study102.load_module("m32_129_case2", study102.BASE_32_PATH)
    s42 = study102.load_module("s42_129_case2", study102.BASE_42_PATH)

    base.SYMBOL = SYMBOL
    base.BACKTEST_START = _date_token(BACKTEST_START)
    base.BACKTEST_END = _date_token(latest_closed_ts)

    curve_raw, _ = study102.run_case2_baseline(df_1m.copy(), df_4h.copy(), base, helper, m32, s42)
    curve = curve_raw[["timestamp", "equity"]].copy()
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    return scale_curve(curve, SLEEVE_INITIAL_CAPITAL, PORTFOLIO_CAPITAL)


def build_case3_curve(df_1m: pd.DataFrame, df_4h: pd.DataFrame, latest_closed_ts: pd.Timestamp) -> pd.DataFrame:
    m47 = load_module("m47_129_case3", SOURCE_47)
    s76 = load_module("s76_129_case3", SOURCE_76)
    m111 = load_module("m111_129_case3", SOURCE_111)
    m114 = load_module("m114_129_case3", SOURCE_114)
    m117 = load_module("m117_129_case3", SOURCE_117)
    s126 = load_module("s126_129_case3", SOURCE_126)

    m47.SYMBOL = SYMBOL
    m47.BACKTEST_START = _date_token(BACKTEST_START)
    m47.BACKTEST_END = _date_token(latest_closed_ts)

    market = m114.prepare_market_114(df_1m.copy(), df_4h.copy(), m47, m111)
    curve_raw, _ = s126.run_variant_126(market, CASE3_CFG, s76, m117)
    curve = curve_raw[["timestamp", "equity"]].copy()
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    return scale_curve(curve, SLEEVE_INITIAL_CAPITAL, PORTFOLIO_CAPITAL)


def align_curves(case2_curve: pd.DataFrame, case3_curve: pd.DataFrame) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    common_start = max(pd.Timestamp(case2_curve["timestamp"].min()), pd.Timestamp(case3_curve["timestamp"].min()))
    common_end = min(pd.Timestamp(case2_curve["timestamp"].max()), pd.Timestamp(case3_curve["timestamp"].max()))
    case2 = case2_curve[(case2_curve["timestamp"] >= common_start) & (case2_curve["timestamp"] <= common_end)].copy()
    case3 = case3_curve[(case3_curve["timestamp"] >= common_start) & (case3_curve["timestamp"] <= common_end)].copy()
    merged = pd.merge(
        case2.rename(columns={"equity": "equity_case2"}),
        case3.rename(columns={"equity": "equity_case3"}),
        on="timestamp",
        how="inner",
    ).sort_values("timestamp").reset_index(drop=True)
    return merged, common_start, common_end


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
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.0]})
    ax_eq, ax_dd, ax_2026 = axes

    series = [
        (case2_curve, "case2_only", "#1f77b4"),
        (case3_curve, CASE3_OUTPUT_LABEL, "#d62728"),
        (mix_curve, "case2_case3best_half_mix", "#2ca02c"),
    ]

    for curve, label, color in series:
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.1, label=label, color=color)
        dd = curve["equity"].astype(float) / curve["equity"].cummax().astype(float) - 1.0
        ax_dd.plot(curve["timestamp"], -dd * 100.0, linewidth=1.0, label=label, color=color)

        seg = curve[pd.to_datetime(curve["timestamp"]) >= ANALYSIS_2026_START].copy()
        if not seg.empty:
            ax_2026.plot(seg["timestamp"], seg["equity"], linewidth=1.1, label=label, color=color)

    ax_eq.axhline(PORTFOLIO_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 129: ETHUSDT Case2 vs 127-Family Delay9 Case3 vs 50/50 Static Mix")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_dd.set_ylabel("Drawdown %")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="upper left")

    ax_2026.set_title("2026 Zoom")
    ax_2026.set_ylabel("Equity (USDT)")
    ax_2026.set_xlabel("Time")
    ax_2026.grid(True, alpha=0.2)
    ax_2026.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(
    metrics_df: pd.DataFrame,
    common_start: pd.Timestamp,
    common_end: pd.Timestamp,
    latest_closed_ts: pd.Timestamp,
    used_paths: list[Path],
) -> None:
    case2 = metrics_df.loc[metrics_df["variant"] == "case2_only"].iloc[0]
    case3 = metrics_df.loc[metrics_df["variant"] == CASE3_OUTPUT_LABEL].iloc[0]
    mix = metrics_df.loc[metrics_df["variant"] == "case2_case3best_half_mix"].iloc[0]

    lines: list[str] = []
    lines.append("# 129번 연구: ETHUSDT case2 vs delay9 case3 vs 50:50 혼합")
    lines.append("")
    lines.append("## 설정")
    lines.append("- case3는 더 이상 102 ETH best를 쓰지 않고, 127 계열 long-quality case3를 ETH에 이식했다.")
    lines.append(f"- 이번 연구의 case3 정의: `{CASE3_VARIANT}`")
    lines.append("- 파라미터는 `lb4 / delay9 / capna / cd0`, leverage `3.0`, short TP `20%`, gate `12`, body ATR `0.25`다.")
    lines.append(f"- 비교 구간: `{common_start}` ~ `{common_end}`")
    lines.append(f"- Binance 기준 최신 닫힌 1m 바 시각: `{latest_closed_ts}`")
    lines.append("- 2021 ETH 1m은 Binance public archive에서 보강했고, 최근 부족 구간은 Binance futures API로 이어 붙였다.")
    lines.append("- 사용한 로컬 캐시:")
    for path in used_paths:
        lines.append(f"  - `{path}`")
    lines.append("")
    lines.append("## 결과")
    lines.append("| Variant | Final Equity | Total Return % | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['total_return_pct'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {_fmt(row['return_2026_pct'])} | {_fmt(row['mdd_2026_pct'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append(
        f"- `case2_only`: CAGR `{_fmt(case2['cagr_pct'])}%`, MDD `{_fmt(case2['max_drawdown_pct'])}%`, "
        f"2026 `{_fmt(case2['return_2026_pct'])}%`."
    )
    lines.append(
        f"- `{CASE3_OUTPUT_LABEL}`: CAGR `{_fmt(case3['cagr_pct'])}%`, MDD `{_fmt(case3['max_drawdown_pct'])}%`, "
        f"2026 `{_fmt(case3['return_2026_pct'])}%`."
    )
    lines.append(
        f"- `case2_case3best_half_mix`: CAGR `{_fmt(mix['cagr_pct'])}%`, MDD `{_fmt(mix['max_drawdown_pct'])}%`, "
        f"2026 `{_fmt(mix['return_2026_pct'])}%`."
    )
    lines.append("")
    lines.append("## 출력물")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    print("[129] Loading ETH 2021+ market...", flush=True)
    df_1m, df_4h, latest_closed_ts, used_paths = load_eth_market_2021plus()
    print(f"[129] ETH 1m span: {df_1m.index.min()} -> {df_1m.index.max()} ({len(df_1m)} rows)", flush=True)
    print(f"[129] ETH 4h span: {df_4h.index.min()} -> {df_4h.index.max()} ({len(df_4h)} rows)", flush=True)

    print("[129] Running ETH case2 baseline on 2021+...", flush=True)
    case2_curve = build_case2_curve(df_1m, df_4h, latest_closed_ts)

    print(f"[129] Running ETH case3 using {CASE3_VARIANT}...", flush=True)
    case3_curve = build_case3_curve(df_1m, df_4h, latest_closed_ts)

    merged, common_start, common_end = align_curves(case2_curve, case3_curve)
    case2 = merged[["timestamp", "equity_case2"]].rename(columns={"equity_case2": "equity"}).copy()
    case3 = merged[["timestamp", "equity_case3"]].rename(columns={"equity_case3": "equity"}).copy()
    mix = build_half_mix(merged)

    metrics_rows = []
    curve_rows = []
    for variant, curve in [
        ("case2_only", case2),
        (CASE3_OUTPUT_LABEL, case3),
        ("case2_case3best_half_mix", mix[["timestamp", "equity"]].copy()),
    ]:
        overall = compute_curve_stats(curve, "equity", PORTFOLIO_CAPITAL)
        stats_2026 = compute_window_stats(curve, ANALYSIS_2026_START)
        metrics_rows.append(
            {
                "variant": variant,
                **overall,
                "return_2026_pct": stats_2026["return_pct"],
                "mdd_2026_pct": stats_2026["mdd_pct"],
            }
        )
        curve_out = curve.copy()
        curve_out["variant"] = variant
        curve_rows.append(curve_out)

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    pd.concat(curve_rows, ignore_index=True).to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")
    save_plot(case2, case3, mix)
    save_report(metrics_df, common_start, common_end, latest_closed_ts, used_paths)

    print(f"[129] Common period: {common_start} -> {common_end}", flush=True)
    for _, row in metrics_df.iterrows():
        print(
            f"[129] {row['variant']}: CAGR={_fmt(row['cagr_pct'])}% "
            f"MDD={_fmt(row['max_drawdown_pct'])}% Calmar={_fmt(row['calmar_ratio'])} "
            f"2026={_fmt(row['return_2026_pct'])}%",
            flush=True,
        )
    print(f"[129] Outputs: {OUT_PNG}, {OUT_CSV}, {OUT_CURVES_CSV}, {OUT_MD}", flush=True)


if __name__ == "__main__":
    main()
