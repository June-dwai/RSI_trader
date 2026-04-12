from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_86_PATH = Path("86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup.py")
CASE_CURVES_CSV = Path("90_backtest_btcusdt_scale06_adx002_case123_stress_proxy_sweep_latest_case_curves.csv")
DATA_DIR = Path("historical_data_mainnet")

OUT_BASE = "99_backtest_btcusdt_scale06_adx002_case123_crossasset_flow_hybrid_compare"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_STATE_CSV = Path(f"{OUT_BASE}_state_events.csv")

MONTHLY_TOPUP = 1000.0
INITIAL_CAPITAL_TOTAL = 2000.0
REBALANCE_FEE_RATE = 0.0004
THRESHOLD = 0.02
BASE_WEIGHTS = (0.62, 0.31, 0.07)
SELL_WEIGHTS = (0.58, 0.30, 0.12)
SQUEEZE_WEIGHTS = (0.66, 0.31, 0.03)
ASSETS = ["BTCUSDT", "ETHUSDT", "XRPUSDT"]


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


def compute_curve_stats(series: pd.Series) -> dict[str, float]:
    x = series.astype(float)
    dd = x / x.cummax() - 1.0
    return {
        "final_value": float(x.iloc[-1]),
        "mdd_pct": float(-dd.min() * 100.0),
    }


def compute_month_flags(ts: pd.Series) -> np.ndarray:
    flags = (ts.dt.to_period("M") != ts.dt.to_period("M").shift(1)).to_numpy(copy=True)
    if len(flags):
        flags[0] = False
    return flags


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


def load_4h(symbol: str) -> pd.DataFrame:
    periods = [("2022-01-01", "2024-12-31"), ("2025-01-01", "2026-03-15")]
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
    out = out[~out.index.duplicated(keep="first")].sort_index().reset_index().rename(columns={"index": "timestamp"})
    for col in ["open", "high", "low", "close", "volume", "taker_base_vol"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def build_market_state(symbol: str) -> pd.DataFrame:
    df = load_4h(symbol).copy()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["trend_4h"] = compute_hysteresis_state(df["close"], df["ema200"], hysteresis=0.01)
    df["trend_4h_confirmed"] = df["trend_4h"].shift(1)

    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["tr_pct"] = tr / df["close"]
    df["atr20_pct"] = tr.rolling(20).mean() / df["close"]
    df["ret4h_pct"] = df["close"].pct_change()
    df["buy_ratio"] = (df["taker_base_vol"] / df["volume"].replace(0, np.nan)).clip(0.0, 1.0)
    df["taker_imbalance"] = (df["buy_ratio"] * 2.0) - 1.0
    df["log_volume"] = np.log(df["volume"].clip(lower=1.0))
    df["volume_z"] = (df["log_volume"] - df["log_volume"].rolling(30).mean()) / df["log_volume"].rolling(30).std()
    df["source_asset"] = symbol

    sell_climax = (
        (df["trend_4h_confirmed"] == "bearish")
        & (df["ret4h_pct"] <= -(df["atr20_pct"] * 0.75))
        & (df["volume_z"] >= 1.0)
        & (df["taker_imbalance"] <= -0.08)
    )
    squeeze_risk = (
        (df["trend_4h_confirmed"] == "bearish")
        & (df["ret4h_pct"] >= (df["atr20_pct"] * 0.50))
        & (df["volume_z"] >= 0.75)
        & (df["taker_imbalance"] >= 0.08)
    )

    df["sell_climax_event"] = sell_climax.fillna(False)
    df["squeeze_risk_event"] = squeeze_risk.fillna(False)
    df["sell_climax_active_6"] = df["sell_climax_event"].rolling(6, min_periods=1).max().fillna(0).astype(bool)
    df["squeeze_risk_active_3"] = df["squeeze_risk_event"].rolling(3, min_periods=1).max().fillna(0).astype(bool)

    cols = [
        "timestamp",
        "source_asset",
        "trend_4h_confirmed",
        "ret4h_pct",
        "atr20_pct",
        "buy_ratio",
        "taker_imbalance",
        "volume_z",
        "sell_climax_event",
        "squeeze_risk_event",
        "sell_climax_active_6",
        "squeeze_risk_active_3",
    ]
    return df[cols].dropna(subset=["trend_4h_confirmed"]).reset_index(drop=True)


def merge_state_to_cases(case_curves: pd.DataFrame, market_state: pd.DataFrame) -> pd.DataFrame:
    left = case_curves.copy().reset_index(drop=True)
    right = market_state.copy().reset_index(drop=True)
    left["timestamp"] = left["timestamp"].to_numpy(dtype="datetime64[ns]")
    right["timestamp"] = right["timestamp"].to_numpy(dtype="datetime64[ns]")
    return pd.merge_asof(left.sort_values("timestamp"), right.sort_values("timestamp"), on="timestamp", direction="backward").dropna(
        subset=["trend_4h_confirmed"]
    ).reset_index(drop=True)


def get_target_weights(row: pd.Series) -> tuple[float, float, float]:
    if bool(row["squeeze_risk_active_3"]):
        return SQUEEZE_WEIGHTS
    if bool(row["sell_climax_active_6"]):
        return SELL_WEIGHTS
    return BASE_WEIGHTS


def run_hybrid(merged: pd.DataFrame, variant: str, source_asset: str) -> tuple[pd.DataFrame, dict]:
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret3 = merged["equity_case3"].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"].reset_index(drop=True)
    topup_flags = compute_month_flags(ts)
    rebal_flags = (ts.dt.floor("4h") != ts.dt.floor("4h").shift(1)).to_numpy()

    cap1 = np.zeros(len(merged), dtype=float)
    cap2 = np.zeros(len(merged), dtype=float)
    cap3 = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    contrib = np.zeros(len(merged), dtype=float)
    flow = np.zeros(len(merged), dtype=float)
    nav_index = np.zeros(len(merged), dtype=float)
    w1_series = np.zeros(len(merged), dtype=float)
    w2_series = np.zeros(len(merged), dtype=float)
    w3_series = np.zeros(len(merged), dtype=float)

    fee_paid = 0.0
    rebalance_count = 0
    state_switches = 0
    turnover_notional = 0.0

    cur_target = BASE_WEIGHTS
    cap1[0] = INITIAL_CAPITAL_TOTAL * cur_target[0]
    cap2[0] = INITIAL_CAPITAL_TOTAL * cur_target[1]
    cap3[0] = INITIAL_CAPITAL_TOTAL * cur_target[2]
    total[0] = INITIAL_CAPITAL_TOTAL
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0
    w1_series[0], w2_series[0], w3_series[0] = cur_target

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        c3 = cap3[i - 1] * (1.0 + float(ret3[i]))
        cur_total = c1 + c2 + c3
        cur_flow = 0.0

        target_weights = get_target_weights(merged.iloc[i])
        target_w1, target_w2, target_w3 = target_weights
        if target_weights != cur_target:
            state_switches += 1

        if topup_flags[i]:
            cur_flow = MONTHLY_TOPUP
            target1_after = target_w1 * (cur_total + cur_flow)
            target2_after = target_w2 * (cur_total + cur_flow)
            add1 = min(max(target1_after - c1, 0.0), cur_flow)
            remaining = cur_flow - add1
            add2 = min(max(target2_after - c2, 0.0), remaining)
            add3 = cur_flow - add1 - add2
            c1 += add1
            c2 += add2
            c3 += add3
            cur_total += cur_flow

        if cur_total > 0:
            aw1, aw2, aw3 = c1 / cur_total, c2 / cur_total, c3 / cur_total
            max_drift = max(abs(aw1 - target_w1), abs(aw2 - target_w2), abs(aw3 - target_w3))
        else:
            max_drift = 0.0

        if rebal_flags[i] and max_drift >= THRESHOLD - 1e-12:
            target1 = cur_total * target_w1
            target2 = cur_total * target_w2
            target3 = cur_total * target_w3
            moved = abs(target1 - c1) + abs(target2 - c2) + abs(target3 - c3)
            fee = moved * REBALANCE_FEE_RATE
            cur_total -= fee
            c1 = cur_total * target_w1
            c2 = cur_total * target_w2
            c3 = cur_total * target_w3
            fee_paid += fee
            turnover_notional += moved
            rebalance_count += 1

        prev_total = total[i - 1]
        period_return = (cur_total - prev_total - cur_flow) / prev_total if prev_total > 0 else 0.0
        nav_index[i] = nav_index[i - 1] * (1.0 + period_return)

        cur_target = target_weights
        cap1[i], cap2[i], cap3[i] = c1, c2, c3
        total[i] = cur_total
        flow[i] = cur_flow
        contrib[i] = contrib[i - 1] + cur_flow
        w1_series[i], w2_series[i], w3_series[i] = cur_target

    out = merged[["timestamp"]].copy()
    out["variant"] = variant
    out["source_asset"] = source_asset
    out["equity_total"] = total
    out["cap1"] = cap1
    out["cap2"] = cap2
    out["cap3"] = cap3
    out["cash_flow"] = flow
    out["cumulative_contribution"] = contrib
    out["nav_index"] = nav_index
    out["w1"] = w1_series
    out["w2"] = w2_series
    out["w3"] = w3_series

    topups_df = pd.DataFrame({"timestamp": ts[topup_flags], "topup_amount": MONTHLY_TOPUP})
    stats = s86.compute_flow_metrics(out, topups_df)
    post_start = pd.Timestamp("2025-01-01")
    post = out[out["timestamp"] >= post_start].copy()
    if len(post) > 1:
        post_eq = compute_curve_stats(post["equity_total"])
        post_nav = compute_curve_stats(post["nav_index"])
        elapsed_days = (post["timestamp"].iloc[-1] - post["timestamp"].iloc[0]).total_seconds() / 86400.0
        years = max(elapsed_days / 365.25, 1e-9)
        post_twr_cagr = ((post_nav["final_value"] / float(post["nav_index"].iloc[0])) ** (1.0 / years) - 1.0) * 100.0
    else:
        post_eq = {"mdd_pct": np.nan}
        post_nav = {"mdd_pct": np.nan}
        post_twr_cagr = np.nan
    stats["variant"] = variant
    stats["source_asset"] = source_asset
    stats["rebalance_count"] = rebalance_count
    stats["state_switches"] = state_switches
    stats["fee_paid"] = fee_paid
    stats["turnover_notional"] = turnover_notional
    stats["avg_case3_weight_pct"] = float(pd.Series(w3_series[1:]).mean() * 100.0)
    stats["sell_event_count"] = int(merged["sell_climax_event"].sum())
    stats["squeeze_event_count"] = int(merged["squeeze_risk_event"].sum())
    stats["first_nonbase_timestamp"] = merged.loc[
        (merged["sell_climax_event"]) | (merged["squeeze_risk_event"]), "timestamp"
    ].min()
    stats["post2025_equity_mdd_pct"] = post_eq["mdd_pct"]
    stats["post2025_twr_mdd_pct"] = post_nav["mdd_pct"]
    stats["post2025_twr_cagr_pct"] = post_twr_cagr
    return out, stats


def save_plot(metrics_df: pd.DataFrame, curve_map: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(16, 16), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.4, 1.0, 1.0]})
    ax_eq, ax_zoom, ax_perf, ax_cost = axes
    cmap = plt.get_cmap("tab10")
    variants = metrics_df["variant"].tolist()
    colors = {variant: cmap(i % 10) for i, variant in enumerate(variants)}

    for variant in variants:
        curve = curve_map[variant]
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
        zoom = curve[curve["timestamp"] >= pd.Timestamp("2025-01-01")]
        ax_zoom.plot(zoom["timestamp"], zoom["equity_total"], linewidth=1.1, color=colors[variant], label=variant)
    ax_eq.set_title("99번 연구: Cross-Asset Flow Hybrid Compare")
    ax_eq.set_ylabel("Total Equity")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")
    ax_zoom.set_title("2025-01-01 이후 확대")
    ax_zoom.set_ylabel("Zoomed Equity")
    ax_zoom.grid(True, alpha=0.2)

    base_variant = metrics_df[metrics_df["source_asset"] == "BTCUSDT"]["variant"].iloc[0]
    base_zoom = curve_map[base_variant][["timestamp", "equity_total"]].rename(columns={"equity_total": "base_eq"})
    for variant in variants:
        if variant == base_variant:
            continue
        curve = curve_map[variant][["timestamp", "equity_total"]].rename(columns={"equity_total": "eq"})
        diff = base_zoom.merge(curve, on="timestamp", how="inner")
        diff = diff[diff["timestamp"] >= pd.Timestamp("2025-01-01")].copy()
        ax_zoom.plot(diff["timestamp"], diff["eq"] - diff["base_eq"], linestyle="--", linewidth=0.9, color=colors[variant], alpha=0.9)

    ax_perf.bar(metrics_df["variant"], metrics_df["twr_cagr_pct"], color=[colors[v] for v in variants], alpha=0.85, label="TWR CAGR %")
    ax_perf.set_ylabel("TWR CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf.tick_params(axis="x", rotation=20)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(metrics_df["variant"], metrics_df["twr_mdd_pct"], color="#d62728", marker="o", linewidth=1.1, label="TWR MDD %")
    ax_perf_t.set_ylabel("TWR MDD %")
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_cost.bar(metrics_df["variant"], metrics_df["rebalance_count"], color=[colors[v] for v in variants], alpha=0.85, label="Rebalances")
    ax_cost.set_ylabel("Rebalances")
    ax_cost.grid(True, axis="y", alpha=0.2)
    ax_cost.tick_params(axis="x", rotation=20)
    ax_cost_t = ax_cost.twinx()
    ax_cost_t.plot(metrics_df["variant"], metrics_df["fee_paid"], color="#9467bd", marker="o", linewidth=1.1, label="Fee Paid")
    ax_cost_t.set_ylabel("Fee Paid")
    h1, l1 = ax_cost.get_legend_handles_labels()
    h2, l2 = ax_cost_t.get_legend_handles_labels()
    ax_cost.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame) -> None:
    best = metrics_df.sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).iloc[0]
    baseline = metrics_df[metrics_df["source_asset"] == "BTCUSDT"].iloc[0]
    lines: list[str] = []
    lines.append("# 99번 연구: Cross-Asset Flow Hybrid Compare")
    lines.append("")
    lines.append("## 설정")
    lines.append("- 98의 best 상태 정의인 `flow_combo6_thr2`를 고정한다.")
    lines.append("- 상태 신호의 원천만 BTC, ETH, XRP 4시간 taker flow/volume state로 바꿔 본다.")
    lines.append("- 포트폴리오 자체는 동일한 BTC case1/case2/case3를 유지한다.")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| Source Asset | Final Equity | TWR CAGR % | TWR MDD % | Post-2025 TWR CAGR % | Post-2025 TWR MDD % | Rebalances | State Switches | Fee Paid | First Event |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['source_asset']} | {_fmt(row['final_equity'])} | {_fmt(row['twr_cagr_pct'])} | {_fmt(row['twr_mdd_pct'])} | "
            f"{_fmt(row['post2025_twr_cagr_pct'])} | {_fmt(row['post2025_twr_mdd_pct'])} | {int(row['rebalance_count'])} | {int(row['state_switches'])} | "
            f"{_fmt(row['fee_paid'])} | {row['first_nonbase_timestamp']} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append(f"- best source asset: `{best['source_asset']}`")
    lines.append("- 전체 기간 MDD가 동일하게 보인 이유는 세 상태 소스 모두 2025년 전에는 이벤트가 거의 없어서, 2023~2024 drawdown을 동일하게 겪었기 때문이다.")
    lines.append(
        f"- best vs BTC-state baseline: TWR CAGR `{_fmt(best['twr_cagr_pct'] - baseline['twr_cagr_pct'])}pp`, "
        f"MDD `{_fmt(best['twr_mdd_pct'] - baseline['twr_mdd_pct'])}pp`, "
        f"XIRR `{_fmt(best['xirr_pct'] - baseline['xirr_pct'])}pp`, "
        f"fee `{_fmt(best['fee_paid'] - baseline['fee_paid'])}`."
    )
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- 플롯: `{OUT_PNG}`")
    lines.append(f"- 성과 CSV: `{OUT_CSV}`")
    lines.append(f"- 곡선 CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- 상태 이벤트 CSV: `{OUT_STATE_CSV}`")
    lines.append(f"- 보고서: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run() -> None:
    case_curves = pd.read_csv(CASE_CURVES_CSV, parse_dates=["timestamp"])
    case_curves = case_curves.set_index("timestamp").resample("15min").last().dropna().reset_index()

    rows: list[dict] = []
    curve_rows: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}
    state_rows: list[pd.DataFrame] = []

    for source_asset in ASSETS:
        market_state = build_market_state(source_asset)
        state_rows.append(market_state.assign(source_asset=source_asset))
        merged = merge_state_to_cases(case_curves, market_state)
        variant = f"flow_combo6_thr2_{source_asset.lower()}"
        curve, stats = run_hybrid(merged, variant, source_asset)
        rows.append(stats)
        curve_rows.append(curve)
        curve_map[variant] = curve

    metrics_df = pd.DataFrame(rows).sort_values(["twr_calmar_ratio", "xirr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curve_rows, ignore_index=True)
    states_df = pd.concat(state_rows, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    states_df.to_csv(OUT_STATE_CSV, index=False)
    save_plot(metrics_df, curve_map)
    save_report(metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_states={OUT_STATE_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


s86 = load_module("m86_99", BASE_86_PATH)


if __name__ == "__main__":
    run()
