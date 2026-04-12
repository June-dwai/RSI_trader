from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OUT_BASE = "95_backtest_conditional_intraday_structures"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

DATA_DIR = Path("historical_data_mainnet")
START = "2022-01-01"
END = "2026-03-15"
INITIAL_CAPITAL = 1000.0
FEE_RATE = 0.0004

VARIANTS = [
    {
        "variant": "breakout24_dual_h8_x100",
        "entry_type": "breakout",
        "breakout_bars": 96,
        "hold_bars": 8,
        "stop_atr": 1.0,
        "tp_atr": 2.0,
        "exposure": 1.0,
    },
    {
        "variant": "breakout24_dual_h8_x125",
        "entry_type": "breakout",
        "breakout_bars": 96,
        "hold_bars": 8,
        "stop_atr": 1.0,
        "tp_atr": 2.0,
        "exposure": 1.25,
    },
    {
        "variant": "breakout48_dual_h12_x100",
        "entry_type": "breakout",
        "breakout_bars": 192,
        "hold_bars": 12,
        "stop_atr": 1.0,
        "tp_atr": 2.5,
        "exposure": 1.0,
    },
    {
        "variant": "reclaim12_dual_h8_x100",
        "entry_type": "reclaim",
        "breakout_bars": 48,
        "hold_bars": 8,
        "stop_atr": 0.8,
        "tp_atr": 1.5,
        "exposure": 1.0,
    },
    {
        "variant": "reclaim24_dual_h12_x100",
        "entry_type": "reclaim",
        "breakout_bars": 96,
        "hold_bars": 12,
        "stop_atr": 1.0,
        "tp_atr": 1.8,
        "exposure": 1.0,
    },
]


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def load_1m(symbol: str) -> pd.DataFrame:
    periods = [(START, "2024-12-31"), ("2025-01-01", END)]
    frames: list[pd.DataFrame] = []
    for start_date, end_date in periods:
        path = DATA_DIR / f"{symbol}_1m_{start_date}_{end_date}.pkl"
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_pickle(path)
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        frames.append(df)
    out = pd.concat(frames)
    out = out[~out.index.duplicated(keep="first")].sort_index()
    return out[(out.index >= pd.Timestamp(START)) & (out.index <= pd.Timestamp(END))].copy()


def compute_curve_stats(curve: pd.DataFrame, col: str, initial_capital: float) -> dict:
    series = curve[col].astype(float)
    final_equity = float(series.iloc[-1])
    total_return_pct = ((final_equity / float(initial_capital)) - 1.0) * 100.0
    elapsed_days = (curve["timestamp"].iloc[-1] - curve["timestamp"].iloc[0]).total_seconds() / 86400.0
    years = max(elapsed_days / 365.25, 1e-9)
    cagr_pct = ((final_equity / float(initial_capital)) ** (1.0 / years) - 1.0) * 100.0
    dd = series / series.cummax() - 1.0
    mdd_pct = float(-dd.min() * 100.0)
    calmar = cagr_pct / mdd_pct if mdd_pct > 0 else np.nan
    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": mdd_pct,
        "calmar_ratio": calmar,
    }


def compute_hysteresis_state(close_series: pd.Series, ema_series: pd.Series, hysteresis: float) -> pd.Series:
    states: list[str | float] = []
    prev_state: str | None = None
    for close, ema in zip(close_series, ema_series):
        if pd.isna(close) or pd.isna(ema):
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
    return pd.Series(states, index=close_series.index)


def build_market_df() -> pd.DataFrame:
    btc_1m = load_1m("BTCUSDT")
    df15 = btc_1m.resample("15min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()

    prev_close = df15["close"].shift(1)
    tr = pd.concat(
        [
            df15["high"] - df15["low"],
            (df15["high"] - prev_close).abs(),
            (df15["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df15["atr20"] = tr.rolling(20).mean()
    df15["ret_close"] = df15["close"].pct_change().fillna(0.0)
    df15["range"] = df15["high"] - df15["low"]
    df15["body"] = (df15["close"] - df15["open"]).abs()

    df4h = btc_1m.resample("4h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
    df4h["ema200"] = df4h["close"].ewm(span=200, adjust=False).mean()
    df4h["trend_4h"] = compute_hysteresis_state(df4h["close"], df4h["ema200"], hysteresis=0.01)
    df4h["trend_4h_confirmed"] = df4h["trend_4h"].shift(1)

    merged = pd.merge_asof(
        df15.reset_index().sort_values("timestamp"),
        df4h[["trend_4h_confirmed"]].reset_index().sort_values("timestamp"),
        on="timestamp",
        direction="backward",
    )
    merged["trend_4h_confirmed"] = merged["trend_4h_confirmed"].fillna("bearish")
    return merged.dropna().reset_index(drop=True)


def run_variant(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    entry_window = int(cfg["breakout_bars"])
    work = df.copy()
    work["prev_high"] = work["high"].rolling(entry_window).max().shift(1)
    work["prev_low"] = work["low"].rolling(entry_window).min().shift(1)
    work = work.dropna().reset_index(drop=True)

    capital = np.zeros(len(work), dtype=float)
    position_side = np.zeros(len(work), dtype=int)
    gross_exposure = np.zeros(len(work), dtype=float)
    capital[0] = INITIAL_CAPITAL

    current_side = 0
    entry_price = np.nan
    entry_atr = np.nan
    bars_in_trade = 0
    trades = 0
    fee_paid = 0.0
    prev_target = 0.0

    for i in range(1, len(work)):
        cur_capital = capital[i - 1]
        if prev_target != 0:
            cur_capital += cur_capital * prev_target * float(work.loc[i, "ret_close"])

        close_i = float(work.loc[i, "close"])
        atr_i = float(work.loc[i, "atr20"])
        trend_i = work.loc[i, "trend_4h_confirmed"]

        if current_side != 0:
            bars_in_trade += 1
            if current_side == 1:
                pnl_pct = (close_i / entry_price) - 1.0
            else:
                pnl_pct = (entry_price / close_i) - 1.0

            stop_pct = cfg["stop_atr"] * entry_atr / entry_price
            tp_pct = cfg["tp_atr"] * entry_atr / entry_price
            if pnl_pct <= -stop_pct or pnl_pct >= tp_pct or bars_in_trade >= cfg["hold_bars"]:
                current_side = 0
                entry_price = np.nan
                entry_atr = np.nan
                bars_in_trade = 0

        long_signal = False
        short_signal = False
        if current_side == 0:
            prev_high = float(work.loc[i, "prev_high"])
            prev_low = float(work.loc[i, "prev_low"])
            range_ok = float(work.loc[i, "range"]) >= atr_i * 1.05
            body_ok = float(work.loc[i, "body"]) >= atr_i * 0.25
            if cfg["entry_type"] == "breakout":
                long_signal = trend_i == "bullish" and close_i > prev_high and range_ok
                short_signal = trend_i == "bearish" and close_i < prev_low and range_ok
            else:
                long_signal = trend_i == "bullish" and float(work.loc[i, "low"]) < prev_low and close_i > prev_low and close_i > float(work.loc[i, "open"]) and body_ok
                short_signal = trend_i == "bearish" and float(work.loc[i, "high"]) > prev_high and close_i < prev_high and close_i < float(work.loc[i, "open"]) and body_ok

            if long_signal:
                current_side = 1
                entry_price = close_i
                entry_atr = atr_i
                bars_in_trade = 0
            elif short_signal:
                current_side = -1
                entry_price = close_i
                entry_atr = atr_i
                bars_in_trade = 0

        new_target = current_side * float(cfg["exposure"])
        turnover = abs(new_target - prev_target)
        if turnover > 0:
            fee = cur_capital * turnover * FEE_RATE
            cur_capital -= fee
            fee_paid += fee
            trades += 1

        prev_target = new_target
        capital[i] = cur_capital
        position_side[i] = current_side
        gross_exposure[i] = abs(new_target)

    curve = work[["timestamp"]].copy()
    curve["variant"] = cfg["variant"]
    curve["equity"] = capital
    curve["position_side"] = position_side
    curve["gross_exposure"] = gross_exposure

    stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL)
    stats["variant"] = cfg["variant"]
    stats["entry_type"] = cfg["entry_type"]
    stats["trades"] = trades
    stats["fee_paid"] = fee_paid
    stats["avg_gross_exposure"] = float(pd.Series(gross_exposure[1:]).mean())
    return curve, stats


def save_plot(metrics_df: pd.DataFrame, curve_map: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0]})
    ax_eq, ax_perf = axes
    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {variant: cmap(i % 10) for i, variant in enumerate(variants)}

    for variant in variants:
        curve = curve_map[variant]
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.axhline(INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("95번 연구: 조건부 인트라데이 구조")
    ax_eq.set_ylabel("Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_perf.bar(metrics_df["variant"], metrics_df["cagr_pct"], color=[colors[v] for v in variants], alpha=0.85, label="CAGR %")
    ax_perf.set_ylabel("CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf.tick_params(axis="x", rotation=20)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(metrics_df["variant"], metrics_df["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_perf_t.set_ylabel("MDD %")
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame) -> None:
    best = metrics_df.sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]
    lines: list[str] = []
    lines.append("# 95번 연구: 조건부 인트라데이 구조")
    lines.append("")
    lines.append("## 설정")
    lines.append("- BTC 15분봉 기반으로만 운용한다.")
    lines.append("- 4시간 confirmed trend를 상위 필터로 사용한다.")
    lines.append("- breakout은 추세 방향 돌파를 따라가고, reclaim은 유동성 sweep 후 range 복귀를 역추세로 먹는다.")
    lines.append("- 진입/청산은 모두 bar close 기준으로 처리해 미래시를 피한다.")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Variant | Entry Type | Final Equity | CAGR % | MDD % | Calmar | Trades | Fee Paid |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {row['entry_type']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {int(row['trades'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append(f"- best variant: `{best['variant']}`")
    lines.append("- 이 구조는 저빈도 포트폴리오 sleeve와 다른 짧은 holding-period 알파 후보를 찾는 목적이다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 성과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- 보고서: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run() -> None:
    market_df = build_market_df()
    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        curve, stats = run_variant(market_df, cfg)
        rows.append(stats)
        curve_rows.append(curve)
        curve_map[cfg["variant"]] = curve

    metrics_df = pd.DataFrame(rows).sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curve_rows, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(metrics_df, curve_map)
    save_report(metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    run()
