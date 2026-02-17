from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


SYMBOL = "BTCUSDT"
INITIAL_CAPITAL = 1000.0
COMMISSION = 0.0004
ENTRY_SCALE = 0.50
DATA_DIR = Path("historical_data_mainnet")
BACKTEST_START = "2022-01-01"
BACKTEST_END = "latest"

RSI_OVERSOLD = 18
RSI_OVERBOUGHT = 85
TAKE_PROFIT_PCT = 0.012
INITIAL_ENTRY_CAPITAL_RATIO = 1.0
MAX_ENTRY_COUNT = 5
USE_ADX_MULTIPLIER = True
EMA_BUFFER = 0.001
ENABLE_TREND_BREAK_CLOSE = True


def _parse_cache_range(path: Path) -> tuple[pd.Timestamp, pd.Timestamp]:
    parts = path.stem.split("_")
    if len(parts) < 4:
        raise ValueError(f"Invalid cache filename format: {path}")
    return pd.to_datetime(parts[-2]), pd.to_datetime(parts[-1])


def _collect_cache_paths(symbol: str, timeframe: str, start_date: str, end_date: str) -> list[Path]:
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    ranges: list[tuple[pd.Timestamp, pd.Timestamp, Path]] = []
    for path in DATA_DIR.glob(f"{symbol}_{timeframe}_*.pkl"):
        try:
            file_start, file_end = _parse_cache_range(path)
        except Exception:
            continue
        if file_end < start_dt or file_start > end_dt:
            continue
        ranges.append((file_start, file_end, path))

    if not ranges:
        raise FileNotFoundError(
            f"No overlapping cache files for {symbol} {timeframe} in range {start_date}~{end_date}"
        )

    exact_cover = [
        (file_start, file_end, path)
        for file_start, file_end, path in ranges
        if file_start <= start_dt and file_end >= end_dt
    ]
    if exact_cover:
        exact_cover.sort(key=lambda x: (x[1] - x[0]))
        return [x[2] for x in exact_cover[:1]]

    # Greedy coverage for fragmented ranges
    ranges.sort(key=lambda x: (x[0], x[1]))
    selected = []
    cursor = start_dt
    while cursor <= end_dt:
        candidates = [x for x in ranges if x[0] <= cursor <= x[1]]
        if not candidates:
            break
        best = max(candidates, key=lambda x: x[1])
        selected.append(best[2])
        cursor = best[1] + pd.Timedelta(seconds=1)
        if best[1] >= end_dt:
            return list(dict.fromkeys(selected))
    raise FileNotFoundError(
        f"Cache files do not fully cover requested range {start_date}~{end_date} for {symbol} {timeframe}"
    )


def _load_cached_df(symbol: str, timeframe: str, periods: list[tuple[str, str]]) -> pd.DataFrame:
    frames = []
    for start_date, end_date in periods:
        for path in _collect_cache_paths(symbol, timeframe, start_date, end_date):
            df = pd.read_pickle(path)
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames)
    out = out[~out.index.duplicated(keep="first")].sort_index()
    return out


def _clean_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    out = df.copy()

    q1 = out["close"].quantile(0.25)
    q3 = out["close"].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    out = out[(out["close"] >= lower) & (out["close"] <= upper)]
    out = out[(out["high"] >= lower) & (out["high"] <= upper)]
    out = out[(out["low"] >= lower) & (out["low"] <= upper)]

    if timeframe == "1m" and len(out) > 1:
        prev_close = out["close"].shift(1).replace(0, np.nan)
        open_gap = ((out["open"] - prev_close) / prev_close).abs() * 100
        close_gap = ((out["close"] - prev_close) / prev_close).abs() * 100
        body_gap = ((out["close"] - out["open"]) / out["open"].replace(0, np.nan)).abs() * 100
        range_gap = ((out["high"] - out["low"]) / out["low"].replace(0, np.nan)).abs() * 100
        high_gap = ((out["high"] - prev_close) / prev_close).abs() * 100
        low_gap = ((out["low"] - prev_close) / prev_close).abs() * 100

        jump = (
            (open_gap > 10)
            | (close_gap > 10)
            | (body_gap > 10)
            | (range_gap > 10)
            | (high_gap > 10)
            | (low_gap > 10)
        )
        jump.iloc[0] = False
        out = out[~jump]

    return out.sort_index()


def _latest_cache_end(symbol: str, timeframe: str) -> str:
    candidates = []
    for path in DATA_DIR.glob(f"{symbol}_{timeframe}_*.pkl"):
        parts = path.stem.split("_")
        if len(parts) < 4:
            continue
        end_token = parts[-1]
        try:
            parsed = pd.to_datetime(end_token)
        except Exception:
            continue
        candidates.append(parsed)
    if not candidates:
        raise RuntimeError(f"No cached {timeframe} files found for {symbol} in {DATA_DIR}")
    return sorted(candidates)[-1].strftime("%Y-%m-%d")


def load_data(backtest_end: str):
    periods_1m = [("2022-01-01", "2024-12-31"), ("2025-01-01", backtest_end)]
    periods_4h = [
        ("2021-07-01", "2021-12-31"),
        ("2022-01-01", backtest_end),
    ]
    df_1m = _clean_data(_load_cached_df(SYMBOL, "1m", periods_1m), "1m")
    df_4h = _clean_data(_load_cached_df(SYMBOL, "4h", periods_4h), "4h")
    return df_1m, df_4h


def load_legacy_backtest_class():
    """
    Load legacy RSI backtest class.
    Prefer commit snapshot when available, otherwise fallback to local complete file.
    """
    namespace = {"__name__": "legacy_backtest"}
    try:
        git_result = subprocess.run(
            ["git", "show", "fce92a1:backtest_rsi_complete.py"],
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        source = git_result.stdout.lstrip("\ufeff")
        if not source.strip():
            raise RuntimeError("Empty source from git show")
        exec(source, namespace)
        return namespace["RSIAveragingBacktest"]
    except Exception:
        fallback_candidates = [
            Path("check_this/backtest_rsi_complete.py"),
            Path(r"C:\\AppDev\\pro_scalper_ai\\_tmp_legacy_scale_plot.py"),
            Path(r"C:\\AppDev\\pro_scalper_ai\\tmp_backtest_rsi_fce92a1.py"),
            Path("backtest_rsi_complete.py"),
            Path(r"C:\\AppDev\\pro_scalper_ai\\backtest_rsi_complete.py"),
            Path(r"C:\\AppDev\\pro_scalper_ai\\tmp_backtest_rsi_fce92a1_from_git.py"),
        ]
        fallback_path = None
        for path in fallback_candidates:
            if path.exists():
                fallback_path = path
                break
        if fallback_path is None:
            raise RuntimeError(
                "Legacy backtest source is unavailable. "
                "Expected git commit or check_this/backtest_rsi_complete.py"
            )
        source = fallback_path.read_text(encoding="utf-8", errors="ignore").lstrip("\ufeff")
        if "RSIAveragingBacktest" not in source:
            raise RuntimeError(f"{fallback_path} does not define RSIAveragingBacktest.")
        exec(source, namespace)
    return namespace["RSIAveragingBacktest"]


def run_baseline_ema200():
    backtest_end = BACKTEST_END
    if backtest_end == "latest":
        latest_end_1m = _latest_cache_end(SYMBOL, "1m")
        latest_end_4h = _latest_cache_end(SYMBOL, "4h")
        backtest_end = min(latest_end_1m, latest_end_4h)

    BaseClass = load_legacy_backtest_class()
    if hasattr(BaseClass, "logger"):
        BaseClass.logger.remove()
        BaseClass.logger.add(
            sys.stderr,
            level="ERROR",
        )

    class FloorScaled(BaseClass):
        def __init__(self, *args, entry_scale: float = ENTRY_SCALE, **kwargs):
            super().__init__(*args, **kwargs)
            self.entry_scale = float(entry_scale)

        def _open_position(self, side, price, timestamp, quantity):
            return super()._open_position(side, price, timestamp, quantity * self.entry_scale)

        def _check_trend_change(self, new_trend, price, timestamp, ema_value=0, current_time=None):
            if self.current_trend is None:
                self.current_trend = new_trend
                return
            self.current_trend = new_trend

        def _record_equity(self, price, timestamp, ema=0):
            equity = self.capital
            if self.current_position:
                pos = self.current_position
                if pos["side"] == "LONG":
                    unrealized = (price - pos["avg_entry"]) * pos["quantity"]
                else:
                    unrealized = (pos["avg_entry"] - price) * pos["quantity"]
                equity += unrealized
            self.equity_curve.append({
                "timestamp": timestamp,
                "equity": equity,
                "price": price,
                "ema200": ema,
            })

    df_1m, df_4h = load_data(backtest_end)
    df_1m = df_1m[(df_1m.index >= BACKTEST_START) & (df_1m.index <= backtest_end)].copy()

    bt = FloorScaled(symbol=SYMBOL, initial_capital=INITIAL_CAPITAL, commission=COMMISSION, entry_scale=ENTRY_SCALE)
    if hasattr(bt, "initial_entry_capital_ratio"):
        bt.initial_entry_capital_ratio = INITIAL_ENTRY_CAPITAL_RATIO
    if hasattr(bt, "rsi_oversold"):
        bt.rsi_oversold = RSI_OVERSOLD
    if hasattr(bt, "rsi_overbought"):
        bt.rsi_overbought = RSI_OVERBOUGHT
    if hasattr(bt, "take_profit_pct"):
        bt.take_profit_pct = TAKE_PROFIT_PCT
    if hasattr(bt, "max_entry_count"):
        bt.max_entry_count = MAX_ENTRY_COUNT
    if hasattr(bt, "use_adx_multiplier"):
        bt.use_adx_multiplier = USE_ADX_MULTIPLIER
    if hasattr(bt, "ema_buffer"):
        bt.ema_buffer = EMA_BUFFER
    if hasattr(bt, "enable_trend_break_close"):
        bt.enable_trend_break_close = ENABLE_TREND_BREAK_CLOSE

    bt.run(df_1m, df_4h, backtest_start_date=BACKTEST_START)
    return bt


def summarize(bt):
    eq = pd.DataFrame(bt.equity_curve)
    tr = pd.DataFrame(bt.trades)
    eq["timestamp"] = pd.to_datetime(eq["timestamp"])
    final_equity = float(eq["equity"].iloc[-1])
    total_return_pct = (final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100.0
    years = max((eq["timestamp"].iloc[-1] - eq["timestamp"].iloc[0]).days / 365.25, 1e-9)
    cagr_pct = (pow(max(final_equity, 1e-12) / INITIAL_CAPITAL, 1 / years) - 1.0) * 100.0
    max_dd_pct = abs((eq["equity"] - eq["equity"].cummax()) / eq["equity"].cummax().replace(0, np.nan) * 100.0).fillna(0.0).max()
    win_rate = float((tr["pnl"] > 0).mean() * 100.0) if len(tr) else 0.0
    return {
        "period_start": eq["timestamp"].iloc[0],
        "period_end": eq["timestamp"].iloc[-1],
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_dd_pct": float(max_dd_pct),
        "trades": int(len(tr)),
        "win_rate_pct": win_rate,
    }


def main():
    bt = run_baseline_ema200()
    metrics = summarize(bt)

    if hasattr(bt, "print_results"):
        try:
            bt.print_results(plot_filename="backtest_real_results.png", show_plot=False)
        except Exception:
            eq = pd.DataFrame(bt.equity_curve)
            tr = pd.DataFrame(bt.trades)
            if len(eq) > 0:
                plt.figure(figsize=(12, 8))
                plt.plot(eq["timestamp"], eq["equity"], label="Equity")
                if not tr.empty:
                    longs = tr[tr["side"] == "LONG"]
                    shorts = tr[tr["side"] == "SHORT"]
                    if not longs.empty:
                        plt.scatter(longs["entry_time"], longs["avg_entry"], s=10, alpha=0.5, label="LONG entry")
                    if not shorts.empty:
                        plt.scatter(shorts["entry_time"], shorts["avg_entry"], s=10, alpha=0.5, label="SHORT entry")
                plt.title("Backtest RSI Averaging")
                plt.xlabel("Time")
                plt.ylabel("Equity (USDT)")
                plt.legend()
                plt.tight_layout()
                plt.savefig("backtest_real_results.png", dpi=300, bbox_inches="tight")
                plt.close()

    print(f"symbol={SYMBOL}")
    print(f"period={metrics['period_start']} ~ {metrics['period_end']}")
    print(f"final_equity={metrics['final_equity']:.4f}")
    print(f"total_return_pct={metrics['total_return_pct']:.4f}%")
    print(f"CAGR={metrics['cagr_pct']:.4f}%")
    print(f"max_dd_pct={metrics['max_dd_pct']:.4f}%")
    print(f"trades={metrics['trades']}, win_rate={metrics['win_rate_pct']:.2f}%")


if __name__ == "__main__":
    main()
