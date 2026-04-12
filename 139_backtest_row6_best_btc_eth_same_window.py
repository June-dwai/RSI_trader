from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "historical_data_mainnet"

BASE_47_PATH = ROOT / "47_backtest_btcusdt_scale06_adx002_case1_standalone.py"
BASE_76_PATH = ROOT / "76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py"
BASE_111_PATH = ROOT / "111_backtest_btcusdt_sr_smc_5m_profitmax.py"
BASE_114_PATH = ROOT / "114_backtest_btcusdt_best_with_sr_smc_filters.py"
BASE_117_PATH = ROOT / "117_backtest_btcusdt_115_highcagr_push.py"
BASE_126_PATH = ROOT / "126_backtest_btcusdt_case3_long_quality_push.py"
BASE_138_PATH = ROOT / "138_backtest_btcusdt_row6_refined_fix_trials.py"

OUT_BASE = "139_backtest_row6_best_btc_eth_same_window"
OUT_CSV = ROOT / f"{OUT_BASE}.csv"
OUT_MD = ROOT / f"{OUT_BASE}.md"
OUT_PNG = ROOT / f"{OUT_BASE}.png"
OUT_CURVES_CSV = ROOT / f"{OUT_BASE}_curves.csv"

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
BASE_VARIANT = "lb4_delay8_capna_cd0"
SELECTED_VARIANT = "combo_trim2p0_unlock24h"
ANALYSIS_2026_START = pd.Timestamp("2026-01-01 00:00:00")


def load_module(alias: str, path: Path):
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def _fmt(v: float, digits: int = 4) -> str:
    return "N/A" if pd.isna(v) else f"{float(v):.{digits}f}"


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
        frame = pd.read_pickle(path)
        if not isinstance(frame.index, pd.DatetimeIndex):
            frame.index = pd.to_datetime(frame.index)
        frames.append(frame)
    merged = pd.concat(frames)
    merged = merged[~merged.index.duplicated(keep="first")].sort_index()
    return merged


def load_1m_2021plus(symbol: str) -> tuple[pd.DataFrame, pd.Timestamp]:
    latest_1m = _pick_latest_cache(symbol, "1m", "2022-01-01")
    df_1m = _load_cache(
        [
            DATA_DIR / f"{symbol}_1m_2021-01-01_2021-12-31.pkl",
            latest_1m,
        ]
    )
    start = pd.Timestamp("2021-01-01")
    end_ts = min(df_1m.index.max(), _parse_cache_end(latest_1m) + pd.Timedelta(days=1) - pd.Timedelta(minutes=1))
    df_1m = df_1m[(df_1m.index >= start) & (df_1m.index <= end_ts)].copy()
    return df_1m, pd.Timestamp(end_ts)


def build_cfg(m126) -> dict:
    base_cfg = next(cfg for cfg in m126.build_variants() if cfg["variant"] == BASE_VARIANT)
    return {
        **base_cfg,
        "variant": SELECTED_VARIANT,
        "bulltrim_enabled": True,
        "bulltrim_ob_threshold": 5,
        "bulltrim_leverage": 2.0,
        "unlock_short_lock_enabled": True,
        "slow_bear_enabled": True,
        "slow_bear_bars": 1440,
        "slow_bear_ob_threshold": 4,
        "slow_bear_leverage": 2.0,
    }


def build_markets(m47, m111, m114) -> tuple[dict[str, pd.DataFrame], pd.Timestamp, pd.Timestamp, dict[str, pd.Timestamp], dict[str, str]]:
    markets: dict[str, pd.DataFrame] = {}
    raw_end_map: dict[str, pd.Timestamp] = {}
    loader_note: dict[str, str] = {}

    btc_1m, btc_4h, btc_end_ts = m114.load_market_data_2021plus()
    btc_market = m114.prepare_market_114(btc_1m.copy(), btc_4h.copy(), m47, m111)
    btc_market["timestamp"] = pd.to_datetime(btc_market["timestamp"])
    markets["BTCUSDT"] = btc_market
    raw_end_map["BTCUSDT"] = pd.Timestamp(btc_end_ts)
    loader_note["BTCUSDT"] = "native_4h_cache"

    for symbol in [s for s in SYMBOLS if s != "BTCUSDT"]:
        df_1m, raw_end_ts = load_1m_2021plus(symbol)
        full_2021_4h = DATA_DIR / f"{symbol}_4h_2021-01-01_2021-12-31.pkl"
        try:
            latest_4h = _pick_latest_cache(symbol, "4h", "2022-01-01")
        except FileNotFoundError:
            latest_4h = None
        if full_2021_4h.exists() and latest_4h is not None:
            df_4h = _load_cache([full_2021_4h, latest_4h])
            loader_note[symbol] = "native_4h_cache"
        else:
            df_4h = m114._resample_ohlc(df_1m, "4h")
            loader_note[symbol] = "resampled_4h_from_1m"
        market = m114.prepare_market_114(df_1m.copy(), df_4h.copy(), m47, m111)
        market["timestamp"] = pd.to_datetime(market["timestamp"])
        markets[symbol] = market
        raw_end_map[symbol] = raw_end_ts

    common_start = max(pd.Timestamp(frame["timestamp"].min()) for frame in markets.values())
    common_end = min(pd.Timestamp(frame["timestamp"].max()) for frame in markets.values())

    for symbol in SYMBOLS:
        frame = markets[symbol]
        markets[symbol] = frame[(frame["timestamp"] >= common_start) & (frame["timestamp"] <= common_end)].reset_index(drop=True)

    return markets, common_start, common_end, raw_end_map, loader_note


def save_plot(curves_df: pd.DataFrame, metrics_df: pd.DataFrame, common_start: pd.Timestamp, common_end: pd.Timestamp) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True, gridspec_kw={"height_ratios": [2.2, 1.0]})
    ax_eq, ax_dd = axes
    colors = {"BTCUSDT": "#1f77b4", "ETHUSDT": "#d62728"}

    for symbol in SYMBOLS:
        curve = curves_df[curves_df["symbol"] == symbol].copy()
        curve["drawdown_pct"] = (curve["equity"] / curve["equity"].cummax() - 1.0) * 100.0
        label = f"{symbol} | CAGR {metrics_df.loc[metrics_df['symbol'] == symbol, 'cagr_pct'].iloc[0]:.1f}% | MDD {metrics_df.loc[metrics_df['symbol'] == symbol, 'max_drawdown_pct'].iloc[0]:.1f}%"
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.2, color=colors[symbol], label=label)
        ax_dd.plot(curve["timestamp"], curve["drawdown_pct"], linewidth=1.0, color=colors[symbol], label=symbol)

    ax_eq.set_yscale("log")
    ax_eq.set_title(f"Study 139: {SELECTED_VARIANT} on BTCUSDT vs ETHUSDT ({common_start} ~ {common_end})")
    ax_eq.set_ylabel("Equity (log scale)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_dd.axhline(0.0, color="#777777", linewidth=0.8)
    ax_dd.set_ylabel("Drawdown %")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="lower left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(
    metrics_df: pd.DataFrame,
    common_start: pd.Timestamp,
    common_end: pd.Timestamp,
    raw_end_map: dict[str, pd.Timestamp],
    loader_note: dict[str, str],
) -> None:
    btc = metrics_df[metrics_df["symbol"] == "BTCUSDT"].iloc[0]
    eth = metrics_df[metrics_df["symbol"] == "ETHUSDT"].iloc[0]

    lines: list[str] = []
    lines.append("# 139번 연구: 138 best 사례 BTC vs ETH 동일 구간 비교")
    lines.append("")
    lines.append(f"- 적용 전략은 `138`에서 실전형으로 가장 좋아 보였던 `{SELECTED_VARIANT}`이다.")
    lines.append(f"- 공통 비교 구간은 `{common_start}` ~ `{common_end}`이다.")
    lines.append(f"- BTC는 `138`과 같은 로컬 `4h` 캐시 파이프라인을 유지했다: `{loader_note['BTCUSDT']}`.")
    lines.append(f"- ETH는 `2021-01-01 ~ 2021-12-31` 전체 `4h` 캐시가 없어 `{loader_note['ETHUSDT']}` 방식으로 만들었다.")
    lines.append(f"- 로컬 원시 캐시 최신 시각은 BTC `{raw_end_map['BTCUSDT']}`, ETH `{raw_end_map['ETHUSDT']}`였고, 공통 종료 시점은 BTC 기준에 맞춰 잘렸다.")
    lines.append("")
    lines.append("| Symbol | Final Equity | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Bull Trims | Unlocks | Slow Bear Shorts |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['symbol']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | "
            f"{_fmt(row['calmar_ratio'])} | {_fmt(row['return_2026_pct'])} | {_fmt(row['mdd_2026_pct'])} | "
            f"{int(row['bulltrim_count'])} | {int(row['unlock_short_lock_count'])} | {int(row['slow_bear_short_entries'])} |"
        )
    lines.append("")
    lines.append(f"- BTC: CAGR `{_fmt(btc['cagr_pct'])}%`, MDD `{_fmt(btc['max_drawdown_pct'])}%`, 2026 `{_fmt(btc['return_2026_pct'])}%`.")
    lines.append(f"- ETH: CAGR `{_fmt(eth['cagr_pct'])}%`, MDD `{_fmt(eth['max_drawdown_pct'])}%`, 2026 `{_fmt(eth['return_2026_pct'])}%`.")
    lines.append(f"- ETH/BTC CAGR 비율은 `{_fmt(eth['cagr_pct'] / btc['cagr_pct'] if btc['cagr_pct'] else np.nan)}`배, MDD 차이는 `{_fmt(eth['max_drawdown_pct'] - btc['max_drawdown_pct'])}`%p다.")
    lines.append("")
    lines.append("## 해석")
    lines.append("- 이 비교는 자산만 바꾸고 로직은 그대로 유지한 크로스-애셋 적합성 체크다.")
    lines.append("- `unlock + slow bear short`가 ETH에서도 작동하면 row6 개선이 자산 공통 구조일 가능성이 높고, 아니면 BTC 특화 성격이 강하다고 볼 수 있다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- Plot: `{OUT_PNG.name}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV.name}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV.name}`")
    lines.append(f"- Report: `{OUT_MD.name}`")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    m47 = load_module("study47_for_139", BASE_47_PATH)
    s76 = load_module("study76_for_139", BASE_76_PATH)
    m111 = load_module("study111_for_139", BASE_111_PATH)
    m114 = load_module("study114_for_139", BASE_114_PATH)
    m117 = load_module("study117_for_139", BASE_117_PATH)
    m126 = load_module("study126_for_139", BASE_126_PATH)
    m138 = load_module("study138_for_139", BASE_138_PATH)

    cfg = build_cfg(m126)
    markets, common_start, common_end, raw_end_map, loader_note = build_markets(m47, m111, m114)

    rows: list[dict] = []
    curves: list[pd.DataFrame] = []
    for symbol in SYMBOLS:
        market = markets[symbol]
        curve, run_stats = m138.run_variant(market, cfg, s76, m117)
        curve["timestamp"] = pd.to_datetime(curve["timestamp"])
        overall = m138.compute_curve_stats(curve, s76.INITIAL_CAPITAL)
        stats_2026 = m138.compute_window_stats(curve, ANALYSIS_2026_START)
        rows.append(
            {
                "symbol": symbol,
                "variant": SELECTED_VARIANT,
                **overall,
                "return_2026_pct": stats_2026["window_return_pct"],
                "mdd_2026_pct": stats_2026["window_mdd_pct"],
                **run_stats,
            }
        )
        curves.append(curve[["timestamp", "equity"]].assign(symbol=symbol, variant=SELECTED_VARIANT))

    metrics_df = pd.DataFrame(rows).sort_values("symbol").reset_index(drop=True)
    curves_df = pd.concat(curves, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    curves_df.to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")
    save_plot(curves_df, metrics_df, common_start, common_end)
    save_report(metrics_df, common_start, common_end, raw_end_map, loader_note)

    print(f"saved_plot={OUT_PNG.name}")
    print(f"saved_metrics={OUT_CSV.name}")
    print(f"saved_curves={OUT_CURVES_CSV.name}")
    print(f"saved_report={OUT_MD.name}")
    print(metrics_df[["symbol", "cagr_pct", "max_drawdown_pct", "calmar_ratio", "return_2026_pct", "mdd_2026_pct", "bulltrim_count", "unlock_short_lock_count", "slow_bear_short_entries"]].to_string(index=False))


if __name__ == "__main__":
    main()
