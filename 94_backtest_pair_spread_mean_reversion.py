from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OUT_BASE = "94_backtest_pair_spread_mean_reversion"
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
    {"variant": "eth_btc_mr_42_e15_x03_s30", "a": "ETHUSDT", "b": "BTCUSDT", "lookback": 42, "entry_z": 1.5, "exit_z": 0.3, "stop_z": 3.0},
    {"variant": "eth_btc_mr_84_e20_x05_s35", "a": "ETHUSDT", "b": "BTCUSDT", "lookback": 84, "entry_z": 2.0, "exit_z": 0.5, "stop_z": 3.5},
    {"variant": "xrp_btc_mr_42_e20_x05_s35", "a": "XRPUSDT", "b": "BTCUSDT", "lookback": 42, "entry_z": 2.0, "exit_z": 0.5, "stop_z": 3.5},
    {"variant": "eth_xrp_mr_42_e15_x03_s30", "a": "ETHUSDT", "b": "XRPUSDT", "lookback": 42, "entry_z": 1.5, "exit_z": 0.3, "stop_z": 3.0},
    {"variant": "eth_xrp_mr_84_e20_x05_s35", "a": "ETHUSDT", "b": "XRPUSDT", "lookback": 84, "entry_z": 2.0, "exit_z": 0.5, "stop_z": 3.5},
]


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def load_4h(symbol: str) -> pd.DataFrame:
    periods = [(START, "2024-12-31"), ("2025-01-01", END)]
    frames: list[pd.DataFrame] = []
    for start_date, end_date in periods:
        path = DATA_DIR / f"{symbol}_4h_{start_date}_{end_date}.pkl"
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


def build_pair_df(price_map: dict[str, pd.DataFrame], cfg: dict) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "close_a": price_map[cfg["a"]]["close"],
            "close_b": price_map[cfg["b"]]["close"],
        }
    ).dropna()
    ratio = np.log(df["close_a"] / df["close_b"])
    ratio_mean = ratio.rolling(cfg["lookback"]).mean()
    ratio_std = ratio.rolling(cfg["lookback"]).std()
    df["zscore"] = ((ratio - ratio_mean) / ratio_std).shift(1)
    df["ret_a"] = df["close_a"].pct_change().fillna(0.0)
    df["ret_b"] = df["close_b"].pct_change().fillna(0.0)
    out = df.dropna().reset_index().rename(columns={"index": "timestamp"})
    return out


def run_variant(price_map: dict[str, pd.DataFrame], cfg: dict) -> tuple[pd.DataFrame, dict]:
    df = build_pair_df(price_map, cfg)
    capital = np.zeros(len(df), dtype=float)
    spread_side = np.zeros(len(df), dtype=int)
    gross_exposure = np.zeros(len(df), dtype=float)
    capital[0] = INITIAL_CAPITAL

    current_side = 0
    trades = 0
    fee_paid = 0.0
    prev_targets = np.zeros(2, dtype=float)

    for i in range(1, len(df)):
        cur_capital = capital[i - 1]
        cur_capital += cur_capital * (prev_targets[0] * float(df.loc[i, "ret_a"]) + prev_targets[1] * float(df.loc[i, "ret_b"]))

        z = float(df.loc[i, "zscore"])
        new_side = current_side
        if current_side == 0:
            if z <= -cfg["entry_z"]:
                new_side = 1
            elif z >= cfg["entry_z"]:
                new_side = -1
        elif current_side == 1:
            if z >= -cfg["exit_z"] or z <= -cfg["stop_z"]:
                new_side = 0
        else:
            if z <= cfg["exit_z"] or z >= cfg["stop_z"]:
                new_side = 0

        targets = np.zeros(2, dtype=float)
        if new_side == 1:
            targets[:] = [0.5, -0.5]
        elif new_side == -1:
            targets[:] = [-0.5, 0.5]

        turnover = float(np.abs(targets - prev_targets).sum())
        if turnover > 0:
            fee = cur_capital * turnover * FEE_RATE
            cur_capital -= fee
            fee_paid += fee
            trades += 1

        current_side = new_side
        prev_targets = targets.copy()
        capital[i] = cur_capital
        spread_side[i] = current_side
        gross_exposure[i] = float(np.abs(targets).sum())

    curve = df[["timestamp"]].copy()
    curve["variant"] = cfg["variant"]
    curve["equity"] = capital
    curve["spread_side"] = spread_side
    curve["gross_exposure"] = gross_exposure
    curve["pair"] = f"{cfg['a']}/{cfg['b']}"

    stats = compute_curve_stats(curve, "equity", INITIAL_CAPITAL)
    stats["variant"] = cfg["variant"]
    stats["pair"] = f"{cfg['a']}/{cfg['b']}"
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
    ax_eq.set_title("94번 연구: 페어 스프레드 평균회귀")
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
    lines.append("# 94번 연구: 페어 스프레드 평균회귀")
    lines.append("")
    lines.append("## 설정")
    lines.append("- BTC/ETH/XRP 사이 비율 스프레드의 평균회귀만 먹는 시장중립 구조다.")
    lines.append("- z-score가 entry threshold를 넘으면 스프레드 진입, mean 근처로 돌아오면 청산한다.")
    lines.append("- 한쪽 자산을 50% 롱, 반대쪽을 50% 숏해서 gross exposure 100%를 유지한다.")
    lines.append("- 목적은 방향성 BTC 의존도를 낮춘 low-MDD 대안을 찾는 것이다.")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Variant | Pair | Final Equity | CAGR % | MDD % | Calmar | Trades | Fee Paid |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {row['pair']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | "
            f"{_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | {int(row['trades'])} | {_fmt(row['fee_paid'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append(f"- best variant: `{best['variant']}`")
    lines.append("- 페어 전략은 절대 CAGR보다, 방향성 sleeve와 다른 경로를 만들어주는지가 더 중요하다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 성과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- 보고서: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run() -> None:
    symbols = sorted({cfg["a"] for cfg in VARIANTS} | {cfg["b"] for cfg in VARIANTS})
    price_map = {symbol: load_4h(symbol) for symbol in symbols}
    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in VARIANTS:
        curve, stats = run_variant(price_map, cfg)
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
