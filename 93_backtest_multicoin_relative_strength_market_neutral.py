from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OUT_BASE = "93_backtest_multicoin_relative_strength_market_neutral"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

DATA_DIR = Path("historical_data_mainnet")
START = "2022-01-01"
END = "2026-03-15"
INITIAL_CAPITAL = 1000.0
FEE_RATE = 0.0004
ASSETS = ["BTCUSDT", "ETHUSDT", "XRPUSDT"]

VARIANTS = [
    {
        "variant": "relmom_1d_7d_4h",
        "signal_tf": "4h",
        "lookback_fast": 6,
        "lookback_slow": 42,
        "hold_bars": 1,
        "mode": "momentum",
    },
    {
        "variant": "relmom_3d_14d_4h",
        "signal_tf": "4h",
        "lookback_fast": 18,
        "lookback_slow": 84,
        "hold_bars": 1,
        "mode": "momentum",
    },
    {
        "variant": "relmom_1d_7d_1h",
        "signal_tf": "1h",
        "lookback_fast": 24,
        "lookback_slow": 168,
        "hold_bars": 4,
        "mode": "momentum",
    },
    {
        "variant": "relrev_1d_7d_4h",
        "signal_tf": "4h",
        "lookback_fast": 6,
        "lookback_slow": 42,
        "hold_bars": 1,
        "mode": "reversal",
    },
    {
        "variant": "relrev_3d_14d_4h",
        "signal_tf": "4h",
        "lookback_fast": 18,
        "lookback_slow": 84,
        "hold_bars": 1,
        "mode": "reversal",
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


def build_signal_panel(price_map: dict[str, pd.Series], cfg: dict) -> pd.DataFrame:
    tf_rule = "4h" if cfg["signal_tf"] == "4h" else "1h"
    panel = pd.DataFrame({symbol: price_map[symbol].resample(tf_rule).last() for symbol in ASSETS}).dropna().copy()
    rets = panel.pct_change()
    fast = (1.0 + rets).rolling(cfg["lookback_fast"]).apply(np.prod, raw=True) - 1.0
    slow = (1.0 + rets).rolling(cfg["lookback_slow"]).apply(np.prod, raw=True) - 1.0
    score = fast - slow
    if cfg["mode"] == "reversal":
        score = -score
    score = score.shift(1)
    score.columns = [f"score_{symbol}" for symbol in ASSETS]
    out = pd.concat([panel, score], axis=1).dropna().reset_index().rename(columns={"index": "timestamp"})
    return out


def run_variant(price_1m_map: dict[str, pd.DataFrame], cfg: dict) -> tuple[pd.DataFrame, dict]:
    close_1m = {symbol: price_1m_map[symbol]["close"].rename(symbol) for symbol in ASSETS}
    signal_df = build_signal_panel(close_1m, cfg)
    score_cols = [f"score_{symbol}" for symbol in ASSETS]
    ret_bars = signal_df[ASSETS].pct_change().fillna(0.0)

    capital = np.zeros(len(signal_df), dtype=float)
    gross_exposure = np.zeros(len(signal_df), dtype=float)
    long_asset = np.full(len(signal_df), "", dtype=object)
    short_asset = np.full(len(signal_df), "", dtype=object)
    side_change = np.zeros(len(signal_df), dtype=bool)

    capital[0] = INITIAL_CAPITAL
    hold_bars = int(cfg["hold_bars"])
    current_long = ""
    current_short = ""
    hold_counter = 0
    trades = 0
    fee_paid = 0.0
    prev_targets = np.zeros(len(ASSETS), dtype=float)

    for i in range(1, len(signal_df)):
        cur_capital = capital[i - 1]

        # Previous targets earn the current bar's close-to-close return.
        pnl = 0.0
        for j, symbol in enumerate(ASSETS):
            pnl += cur_capital * prev_targets[j] * float(ret_bars.iloc[i][symbol])
        cur_capital += pnl

        scores = signal_df.loc[i, score_cols].to_numpy(dtype=float)
        targets = prev_targets.copy()

        if hold_counter <= 0:
            order = np.argsort(scores)
            new_short = ASSETS[int(order[0])]
            new_long = ASSETS[int(order[-1])]
            if new_long != current_long or new_short != current_short:
                current_long = new_long
                current_short = new_short
                side_change[i] = True
                trades += 2
            hold_counter = hold_bars
        hold_counter -= 1

        targets = np.zeros(len(ASSETS), dtype=float)
        if current_long and current_short and current_long != current_short:
            targets[ASSETS.index(current_long)] = 0.5
            targets[ASSETS.index(current_short)] = -0.5

        turnover = float(np.abs(targets - prev_targets).sum())
        if turnover > 0:
            fee = cur_capital * turnover * FEE_RATE
            cur_capital -= fee
            fee_paid += fee

        prev_targets = targets.copy()
        capital[i] = cur_capital
        gross_exposure[i] = float(np.abs(targets).sum())
        long_asset[i] = current_long
        short_asset[i] = current_short

    curve = signal_df[["timestamp"]].copy()
    curve["variant"] = cfg["variant"]
    curve["equity"] = capital
    curve["gross_exposure"] = gross_exposure
    curve["long_asset"] = long_asset
    curve["short_asset"] = short_asset
    curve["side_change"] = side_change

    stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL)
    stats["variant"] = cfg["variant"]
    stats["trades"] = trades
    stats["fee_paid"] = fee_paid
    stats["avg_gross_exposure"] = float(pd.Series(gross_exposure[1:]).mean())
    stats["signal_tf"] = cfg["signal_tf"]
    stats["mode"] = cfg["mode"]
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
    ax_eq.set_title("93번 연구: 멀티코인 상대강도 시장중립")
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
    lines.append("# 93번 연구: 멀티코인 상대강도 시장중립")
    lines.append("")
    lines.append("## 설정")
    lines.append("- BTC/ETH/XRP 3개만 사용한다.")
    lines.append("- 각 시점에서 상대적으로 강한 코인을 롱, 약한 코인을 숏하는 시장중립 구조다.")
    lines.append("- gross exposure는 100%로 두고 롱 50% / 숏 50%를 유지한다.")
    lines.append("- `momentum`은 강한 것을 롱, 약한 것을 숏하고 `reversal`은 반대로 간다.")
    lines.append("- 목적은 기존 BTC 방향성 전략과 다른 low-MDD sleeve 후보가 있는지 보는 것이다.")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Variant | Signal TF | Mode | Final Equity | CAGR % | MDD % | Calmar | Trades | Fee Paid |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {row['signal_tf']} | {row['mode']} | {_fmt(row['final_equity'])} | "
            f"{_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{int(row['trades'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append(f"- best variant: `{best['variant']}`")
    lines.append("- 시장중립 구조는 높은 CAGR보다 낮은 MDD와 기존 BTC 방향성과 다른 경로가 더 중요하다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 성과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- 보고서: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run() -> None:
    price_1m_map = {symbol: load_1m(symbol) for symbol in ASSETS}
    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        curve, stats = run_variant(price_1m_map, cfg)
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
