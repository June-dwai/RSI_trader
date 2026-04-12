from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")
BASE_32_PATH = Path("32_backtest_btcusdt_live_nla.py")
BASE_42_PATH = Path("42_backtest_btcusdt_scale06_adx002_equity_combo.py")
BASE_47_PATH = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
BASE_62_PATH = Path("62_backtest_btcusdt_scale06_adx002_case1_m4_hedge_release_gap_tune.py")

CASE3_84_CURVES_CSV = Path("84_backtest_btcusdt_scale06_adx002_smc_short_gate_tune_curves.csv")

OUT_BASE = "86_backtest_btcusdt_scale06_adx002_case3_smc_shortgate_monthly_topup"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_TOPUPS_CSV = Path(f"{OUT_BASE}_topups.csv")

LATEST_END_DATE = "2026-03-15"
INITIAL_CAPITAL_TOTAL = 2000.0
INITIAL_CAPITAL_CASE = 1000.0
ENTRY_SCALE = 0.60
CASE1_VARIANT = "shallow6_else2bull"
CASE3_VARIANT = "short_gate_24h_g12_tp15"
W1 = 0.62
W2 = 0.31
W3 = 0.07
MONTHLY_TOPUP = 1000.0
REBALANCE_FEE_RATE = 0.0004


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


def _load_case3_curve() -> pd.DataFrame:
    curves = pd.read_csv(CASE3_84_CURVES_CSV, parse_dates=["timestamp"])
    ref = curves[curves["variant"] == CASE3_VARIANT].copy()
    if ref.empty:
        raise ValueError(f"Missing case3 variant in {CASE3_84_CURVES_CSV}: {CASE3_VARIANT}")
    ref = ref.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    return ref[["timestamp", "equity"]].rename(columns={"equity": "equity_case3"})


def _build_case12_latest() -> tuple[pd.DataFrame, pd.DataFrame]:
    m47 = load_module("m47_86", BASE_47_PATH)
    s62 = load_module("s62_86", BASE_62_PATH)

    m47.BACKTEST_END = LATEST_END_DATE
    df_1m, df_4h = m47.load_data_no_filter()
    latest_ts = df_1m.index.max()
    df_1m = df_1m[(df_1m.index >= m47.BACKTEST_START) & (df_1m.index <= latest_ts)].copy()

    case1_cls = s62.build_variant_class(m47.LiveParityNoLookahead, bullish_close_bars=2, shallow_gap_pct=0.06)
    bt1 = case1_cls(
        symbol=m47.SYMBOL,
        initial_capital=INITIAL_CAPITAL_CASE,
        commission=m47.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    m47.configure_baseline_params(bt1)
    bt1.run(df_1m, df_4h, backtest_start_date=m47.BACKTEST_START)
    eq1 = pd.DataFrame(bt1.equity_curve)
    eq1["timestamp"] = pd.to_datetime(eq1["timestamp"])
    eq1 = eq1.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    case1 = eq1[["timestamp", "equity"]].rename(columns={"equity": "equity_case1"})

    base = load_module("m002_86", BASE_002_PATH)
    helper = load_module("m04_86", BASE_04_PATH)
    m32 = load_module("m32_86", BASE_32_PATH)
    s42 = load_module("s42_86", BASE_42_PATH)

    base.BACKTEST_END = LATEST_END_DATE
    bt2_cls = s42.build_case2_class(m32)
    bt2 = bt2_cls(
        base_module=base,
        symbol=base.SYMBOL,
        initial_capital=INITIAL_CAPITAL_CASE,
        commission=base.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    helper.configure_baseline_params(bt2)
    bt2.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)
    eq2 = pd.DataFrame(bt2.equity_curve)
    eq2["timestamp"] = pd.to_datetime(eq2["timestamp"])
    eq2 = eq2.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    case2 = eq2[["timestamp", "equity"]].rename(columns={"equity": "equity_case2"})

    return case1, case2


def _build_merged(case1: pd.DataFrame, case2: pd.DataFrame, case3: pd.DataFrame) -> pd.DataFrame:
    merged = pd.merge(case1, case2, on="timestamp", how="outer")
    merged = pd.merge(merged, case3, on="timestamp", how="outer")
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    merged["equity_case1"] = merged["equity_case1"].ffill()
    merged["equity_case2"] = merged["equity_case2"].ffill()
    merged["equity_case3"] = merged["equity_case3"].ffill()
    merged = merged.dropna(subset=["equity_case1", "equity_case2", "equity_case3"]).copy()
    return merged


def _xirr(cashflows: list[tuple[pd.Timestamp, float]]) -> float:
    if not cashflows:
        return np.nan
    dates = [pd.Timestamp(d) for d, _ in cashflows]
    amounts = [float(v) for _, v in cashflows]
    t0 = dates[0]
    years = np.array([(d - t0).total_seconds() / 86400.0 / 365.25 for d in dates], dtype=float)

    if not any(v < 0 for v in amounts) or not any(v > 0 for v in amounts):
        return np.nan

    def npv(rate: float) -> float:
        if rate <= -0.999999999:
            return np.inf
        return float(sum(v / ((1.0 + rate) ** y) for v, y in zip(amounts, years)))

    low = -0.9999
    high = 1.0
    f_low = npv(low)
    f_high = npv(high)
    expand = 0
    while math.isfinite(f_low) and math.isfinite(f_high) and f_low * f_high > 0 and expand < 40:
        high = high * 2.0 + 1.0
        f_high = npv(high)
        expand += 1
    if not math.isfinite(f_low) or not math.isfinite(f_high) or f_low * f_high > 0:
        return np.nan

    for _ in range(200):
        mid = (low + high) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < 1e-10:
            return mid
        if f_low * f_mid <= 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    return (low + high) / 2.0


def run_portfolio(merged: pd.DataFrame, variant: str, monthly_topup: float) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret3 = merged["equity_case3"].astype(float).pct_change().fillna(0.0).to_numpy()
    ts = merged["timestamp"].reset_index(drop=True)

    rebal_flags = (ts.dt.floor("4h") != ts.dt.floor("4h").shift(1)).to_numpy()
    month_change = (ts.dt.to_period("M") != ts.dt.to_period("M").shift(1)).to_numpy()
    topup_flags = month_change.copy()
    if len(topup_flags):
        topup_flags[0] = False

    cap1 = np.zeros(len(merged), dtype=float)
    cap2 = np.zeros(len(merged), dtype=float)
    cap3 = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    contrib = np.zeros(len(merged), dtype=float)
    flow = np.zeros(len(merged), dtype=float)
    nav_index = np.zeros(len(merged), dtype=float)

    fee_paid = 0.0
    rebalance_count = 0
    topup_count = 0
    topup_rows: list[dict] = []

    cap1[0] = INITIAL_CAPITAL_TOTAL * W1
    cap2[0] = INITIAL_CAPITAL_TOTAL * W2
    cap3[0] = INITIAL_CAPITAL_TOTAL * W3
    total[0] = cap1[0] + cap2[0] + cap3[0]
    contrib[0] = INITIAL_CAPITAL_TOTAL
    nav_index[0] = 1.0

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        c3 = cap3[i - 1] * (1.0 + float(ret3[i]))
        cur_total = c1 + c2 + c3
        cur_flow = 0.0

        if monthly_topup > 0.0 and topup_flags[i]:
            cur_flow = monthly_topup
            cur_total += cur_flow
            c1 += cur_flow * W1
            c2 += cur_flow * W2
            c3 += cur_flow * W3
            topup_count += 1
            topup_rows.append(
                {
                    "variant": variant,
                    "timestamp": ts.iloc[i],
                    "topup_amount": cur_flow,
                    "equity_before_topup": cur_total - cur_flow,
                    "equity_after_topup": cur_total,
                    "cap1_after_topup": c1,
                    "cap2_after_topup": c2,
                    "cap3_after_topup": c3,
                    "cumulative_contribution": contrib[i - 1] + cur_flow,
                }
            )

        if rebal_flags[i]:
            target1 = cur_total * W1
            target2 = cur_total * W2
            target3 = cur_total * W3
            fee = (abs(target1 - c1) + abs(target2 - c2) + abs(target3 - c3)) * REBALANCE_FEE_RATE
            cur_total -= fee
            c1 = cur_total * W1
            c2 = cur_total * W2
            c3 = cur_total * W3
            fee_paid += fee
            rebalance_count += 1

        prev_total = total[i - 1]
        if prev_total > 0:
            period_return = (cur_total - prev_total - cur_flow) / prev_total
            nav_index[i] = nav_index[i - 1] * (1.0 + period_return)
        else:
            nav_index[i] = nav_index[i - 1]

        cap1[i] = c1
        cap2[i] = c2
        cap3[i] = c3
        total[i] = cur_total
        flow[i] = cur_flow
        contrib[i] = contrib[i - 1] + cur_flow

    out = merged[["timestamp"]].copy()
    out["variant"] = variant
    out["equity_total"] = total
    out["cap1"] = cap1
    out["cap2"] = cap2
    out["cap3"] = cap3
    out["w1"] = W1
    out["w2"] = W2
    out["w3"] = W3
    out["cash_flow"] = flow
    out["cumulative_contribution"] = contrib
    out["nav_index"] = nav_index

    topups_df = pd.DataFrame(topup_rows)
    stats = compute_flow_metrics(out, topups_df)
    stats["variant"] = variant
    stats["rebalance_count"] = rebalance_count
    stats["fee_paid"] = fee_paid
    stats["topup_count"] = topup_count
    stats["topup_amount_each"] = monthly_topup
    return out, topups_df, stats


def compute_flow_metrics(curve: pd.DataFrame, topups_df: pd.DataFrame) -> dict:
    final_equity = float(curve["equity_total"].iloc[-1])
    total_contributed = float(curve["cumulative_contribution"].iloc[-1])
    net_profit = final_equity - total_contributed
    money_multiple = final_equity / total_contributed if total_contributed > 0 else np.nan

    elapsed_days = (curve["timestamp"].iloc[-1] - curve["timestamp"].iloc[0]).total_seconds() / 86400.0
    years = max(elapsed_days / 365.25, 1e-9)

    nav = curve["nav_index"].astype(float)
    twr_final = float(nav.iloc[-1])
    twr_cagr_pct = ((twr_final ** (1.0 / years)) - 1.0) * 100.0 if twr_final > 0 else np.nan
    twr_dd = nav / nav.cummax() - 1.0
    twr_mdd_pct = float(-twr_dd.min() * 100.0)
    twr_calmar = twr_cagr_pct / twr_mdd_pct if twr_mdd_pct > 0 else np.nan

    cashflows: list[tuple[pd.Timestamp, float]] = [(pd.Timestamp(curve["timestamp"].iloc[0]), -INITIAL_CAPITAL_TOTAL)]
    if not topups_df.empty:
        cashflows.extend((pd.Timestamp(r["timestamp"]), -float(r["topup_amount"])) for _, r in topups_df.iterrows())
    cashflows.append((pd.Timestamp(curve["timestamp"].iloc[-1]), final_equity))
    xirr = _xirr(cashflows)

    return {
        "start_timestamp": curve["timestamp"].iloc[0],
        "end_timestamp": curve["timestamp"].iloc[-1],
        "final_equity": final_equity,
        "total_contributed": total_contributed,
        "net_profit": net_profit,
        "money_multiple": money_multiple,
        "twr_final_index": twr_final,
        "twr_cagr_pct": twr_cagr_pct,
        "twr_mdd_pct": twr_mdd_pct,
        "twr_calmar_ratio": twr_calmar,
        "xirr_pct": xirr * 100.0 if pd.notna(xirr) else np.nan,
    }


def save_plot(curves_df: pd.DataFrame, topups_df: pd.DataFrame):
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0]})
    ax_eq, ax_nav = axes

    color_map = {"no_topup": "#1f77b4", "monthly_topup_1000": "#d62728"}
    for variant, curve in curves_df.groupby("variant"):
        ax_eq.plot(curve["timestamp"], curve["equity_total"], linewidth=1.1, color=color_map.get(variant), label=variant)
        ax_eq.plot(curve["timestamp"], curve["cumulative_contribution"], linewidth=0.9, linestyle="--", color=color_map.get(variant), alpha=0.7)
        ax_nav.plot(curve["timestamp"], curve["nav_index"], linewidth=1.1, color=color_map.get(variant), label=variant)

    if not topups_df.empty:
        topups = topups_df[topups_df["variant"] == "monthly_topup_1000"]
        ax_eq.scatter(topups["timestamp"], topups["equity_after_topup"], s=10, color="#111111", alpha=0.55, label="Top-up points")

    ax_eq.set_title("86 Study: 85-Best Mix With Monthly 1000 Top-Up")
    ax_eq.set_ylabel("Total Equity / Contribution")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_nav.set_title("Flow-Adjusted NAV Index")
    ax_nav.set_ylabel("NAV Index")
    ax_nav.grid(True, alpha=0.2)
    ax_nav.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, merged: pd.DataFrame):
    base = metrics_df[metrics_df["variant"] == "no_topup"].iloc[0]
    topup = metrics_df[metrics_df["variant"] == "monthly_topup_1000"].iloc[0]

    lines: list[str] = []
    lines.append("# Study 86: 85-Best Mix With Monthly 1000 Top-Up")
    lines.append("")
    lines.append("## Setup")
    lines.append(f"- Fixed weights from study 85 best mix: `case1 {int(W1 * 100)}% / case2 {int(W2 * 100)}% / case3 {int(W3 * 100)}%`.")
    lines.append(f"- `case1` is rerun latest as `{CASE1_VARIANT}` using the cached file ending on `{LATEST_END_DATE}` and keeps the last available minute in that cache.")
    lines.append(f"- `case2` is rerun latest with study-42 case2 logic using the same latest cached minute range.")
    lines.append(f"- `case3` uses study-84 winner `{CASE3_VARIANT}`.")
    lines.append("- Portfolio keeps the same `4h rebalance` logic and fee model as studies 70/81/85.")
    lines.append(f"- Top-up assumption: add `{MONTHLY_TOPUP:.0f}` USDT on the first available timestamp of each new month, starting after the initial month, and split it directly at target weights.")
    lines.append("- Because cash flows distort plain CAGR, this report uses `TWR CAGR/MDD/Calmar` and also reports `final equity`, `total contributed`, and `XIRR`.")
    lines.append("")
    lines.append("## Common Period")
    lines.append(f"- Start: `{merged['timestamp'].iloc[0]}`")
    lines.append(f"- End: `{merged['timestamp'].iloc[-1]}`")
    lines.append(f"- Rows: `{len(merged)}`")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Variant | Final Equity | Total Contributed | Net Profit | Money Multiple | TWR CAGR % | TWR MDD % | TWR Calmar | XIRR % | Rebalances | Fee Paid | Topups |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['total_contributed'])} | {_fmt(row['net_profit'])} | "
            f"{_fmt(row['money_multiple'])} | {_fmt(row['twr_cagr_pct'])} | {_fmt(row['twr_mdd_pct'])} | {_fmt(row['twr_calmar_ratio'])} | "
            f"{_fmt(row['xirr_pct'])} | {int(row['rebalance_count'])} | {_fmt(row['fee_paid'])} | {int(row['topup_count'])} |"
        )
    lines.append("")
    lines.append("## Delta: Monthly Top-Up vs No Top-Up")
    lines.append(f"- Final equity delta: `{_fmt(topup['final_equity'] - base['final_equity'])}`")
    lines.append(f"- Total contributed delta: `{_fmt(topup['total_contributed'] - base['total_contributed'])}`")
    lines.append(f"- Net profit delta: `{_fmt(topup['net_profit'] - base['net_profit'])}`")
    lines.append(f"- TWR CAGR delta: `{_fmt(topup['twr_cagr_pct'] - base['twr_cagr_pct'])}pp`")
    lines.append(f"- TWR MDD delta: `{_fmt(topup['twr_mdd_pct'] - base['twr_mdd_pct'])}pp`")
    lines.append(f"- XIRR delta: `{_fmt(topup['xirr_pct'] - base['xirr_pct'])}pp`")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If `TWR CAGR/MDD` stay close to the no-topup run, then monthly cash injection is mostly scaling notional rather than changing the strategy edge.")
    lines.append("- If `XIRR` stays strong while `money multiple` compresses, that means the portfolio is still compounding well but the later deposits had less time to work.")
    lines.append("- Deposit-on-target-weights is the cleanest analogue to adding capital into a portfolio that is already maintained by scheduled rebalancing.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Topups CSV: `{OUT_TOPUPS_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    case1, case2 = _build_case12_latest()
    case3 = _load_case3_curve()

    common_start = max(case1["timestamp"].min(), case2["timestamp"].min(), case3["timestamp"].min())
    common_end = min(case1["timestamp"].max(), case2["timestamp"].max(), case3["timestamp"].max())

    case1_clip = case1[(case1["timestamp"] >= common_start) & (case1["timestamp"] <= common_end)].copy()
    case2_clip = case2[(case2["timestamp"] >= common_start) & (case2["timestamp"] <= common_end)].copy()
    case3_clip = case3[(case3["timestamp"] >= common_start) & (case3["timestamp"] <= common_end)].copy()
    merged = _build_merged(case1_clip, case2_clip, case3_clip)

    no_topup_curve, no_topup_topups, no_topup_stats = run_portfolio(merged, "no_topup", monthly_topup=0.0)
    topup_curve, topup_topups, topup_stats = run_portfolio(merged, "monthly_topup_1000", monthly_topup=MONTHLY_TOPUP)

    metrics_df = pd.DataFrame([no_topup_stats, topup_stats])
    metrics_df.to_csv(OUT_CSV, index=False)

    curves_df = pd.concat([no_topup_curve, topup_curve], ignore_index=True)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)

    topups_df = pd.concat([no_topup_topups, topup_topups], ignore_index=True)
    topups_df.to_csv(OUT_TOPUPS_CSV, index=False)

    save_plot(curves_df, topups_df)
    save_report(metrics_df, merged)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_topups={OUT_TOPUPS_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    run()
