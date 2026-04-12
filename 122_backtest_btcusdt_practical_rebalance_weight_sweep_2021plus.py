from __future__ import annotations

import importlib.util
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
BASE_76_PATH = Path("76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py")
BASE_111_PATH = Path("111_backtest_btcusdt_sr_smc_5m_profitmax.py")
BASE_114_PATH = Path("114_backtest_btcusdt_best_with_sr_smc_filters.py")
BASE_117_PATH = Path("117_backtest_btcusdt_115_highcagr_push.py")
BASE_121_CSV = Path("121_backtest_btcusdt_solo_vs_current_mix_2021plus.csv")

OUT_BASE = "122_backtest_btcusdt_practical_rebalance_weight_sweep_2021plus"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_SLEEVE_CACHE = Path(f"{OUT_BASE}_sleeve_state.pkl")

BACKTEST_START = pd.Timestamp("2021-01-01")
PORTFOLIO_CAPITAL = 2000.0
SLEEVE_CAPITAL = 1000.0
RESAMPLE_RULE = "15min"
REB_FEE_RATE = 0.0004
WEIGHT_STEP = 5

CASE1_VARIANT = "shallow6_else2bull"
CASE3_VARIANT = "lv3p0_g12_body25_tp20_lb5_none"

MODE_NONE = "no_rebalance"
MODE_WEEKLY_FLAT = "weekly_due_allflat"
MODE_MONTHLY_FLAT = "monthly_due_allflat"
MODES = [MODE_NONE, MODE_WEEKLY_FLAT, MODE_MONTHLY_FLAT]


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


def build_activity_from_trades(timestamps: pd.DatetimeIndex, trades_df: pd.DataFrame) -> np.ndarray:
    active = np.zeros(len(timestamps), dtype=bool)
    if trades_df.empty:
        return active

    entries = pd.to_datetime(trades_df["entry_time"]).to_numpy()
    exits = pd.to_datetime(trades_df["exit_time"]).to_numpy()
    ts = pd.DatetimeIndex(timestamps)

    for entry_time, exit_time in zip(entries, exits):
        start_idx = int(ts.searchsorted(pd.Timestamp(entry_time), side="left"))
        end_idx = int(ts.searchsorted(pd.Timestamp(exit_time), side="left"))
        if end_idx > start_idx:
            active[start_idx:end_idx] = True
    return active


def resample_state(curve: pd.DataFrame, equity_col: str, active_col: str) -> pd.DataFrame:
    out = curve.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    out = (
        out.set_index("timestamp")
        .sort_index()[[equity_col, active_col]]
        .resample(RESAMPLE_RULE, label="right", closed="right")
        .agg({equity_col: "last", active_col: "last"})
        .dropna(subset=[equity_col])
        .reset_index()
    )
    out[active_col] = out[active_col].fillna(False).astype(bool)
    return out


def scale_equity(curve: pd.DataFrame, equity_col: str, scale: float) -> pd.DataFrame:
    out = curve.copy()
    out[equity_col] = out[equity_col].astype(float) * float(scale)
    return out


def clip_state(curve: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp, equity_col: str, active_col: str) -> pd.DataFrame:
    out = curve.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    out = out[(out["timestamp"] >= start_ts) & (out["timestamp"] <= end_ts)].copy()
    out = out.sort_values("timestamp").reset_index(drop=True)
    if out.empty:
        raise RuntimeError("Clipped sleeve state is empty")
    return out[["timestamp", equity_col, active_col]].copy()


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


def get_due_flags(ts: pd.Series, mode: str) -> np.ndarray:
    if mode == MODE_NONE:
        return np.zeros(len(ts), dtype=bool)
    if mode == MODE_WEEKLY_FLAT:
        period = ts.dt.to_period("W-SUN")
    elif mode == MODE_MONTHLY_FLAT:
        period = ts.dt.to_period("M")
    else:
        raise ValueError(f"Unsupported rebalance mode: {mode}")
    due_flags = np.asarray((period != period.shift(1)).to_numpy(), dtype=bool).copy()
    if len(due_flags):
        due_flags[0] = False
    return due_flags


def run_portfolio(merged: pd.DataFrame, w1: float, w2: float, w3: float, mode: str) -> tuple[pd.DataFrame, dict]:
    ret1 = merged["equity_case1"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret2 = merged["equity_case2"].astype(float).pct_change().fillna(0.0).to_numpy()
    ret3 = merged["equity_case3"].astype(float).pct_change().fillna(0.0).to_numpy()
    flat_all = (~merged["active_case1"].astype(bool) & ~merged["active_case2"].astype(bool) & ~merged["active_case3"].astype(bool)).to_numpy()
    due_flags = get_due_flags(merged["timestamp"], mode)

    cap1 = np.zeros(len(merged), dtype=float)
    cap2 = np.zeros(len(merged), dtype=float)
    cap3 = np.zeros(len(merged), dtype=float)
    total = np.zeros(len(merged), dtype=float)
    pending_due = False
    rebalance_count = 0
    fee_paid = 0.0
    deferred_due_bars = 0
    flat_rebalance_hits = 0

    cap1[0] = PORTFOLIO_CAPITAL * w1
    cap2[0] = PORTFOLIO_CAPITAL * w2
    cap3[0] = PORTFOLIO_CAPITAL * w3
    total[0] = cap1[0] + cap2[0] + cap3[0]

    for i in range(1, len(merged)):
        c1 = cap1[i - 1] * (1.0 + float(ret1[i]))
        c2 = cap2[i - 1] * (1.0 + float(ret2[i]))
        c3 = cap3[i - 1] * (1.0 + float(ret3[i]))
        cur_total = c1 + c2 + c3

        if due_flags[i]:
            pending_due = True

        if pending_due and flat_all[i]:
            target1 = cur_total * w1
            target2 = cur_total * w2
            target3 = cur_total * w3
            fee = (abs(target1 - c1) + abs(target2 - c2) + abs(target3 - c3)) * REB_FEE_RATE
            cur_total -= fee
            c1 = cur_total * w1
            c2 = cur_total * w2
            c3 = cur_total * w3
            fee_paid += fee
            rebalance_count += 1
            pending_due = False
            flat_rebalance_hits += 1
        elif pending_due:
            deferred_due_bars += 1

        cap1[i] = c1
        cap2[i] = c2
        cap3[i] = c3
        total[i] = cur_total

    out = merged[["timestamp"]].copy()
    out["equity"] = total
    out["cap1"] = cap1
    out["cap2"] = cap2
    out["cap3"] = cap3
    return out, {
        "rebalance_count": rebalance_count,
        "fee_paid": fee_paid,
        "deferred_due_bars": deferred_due_bars,
        "flat_rebalance_hits": flat_rebalance_hits,
    }


def build_weight_grid(step_pct: int = WEIGHT_STEP) -> list[tuple[float, float, float]]:
    weights: list[tuple[float, float, float]] = []
    for w1_pct in range(0, 101, step_pct):
        for w2_pct in range(0, 101 - w1_pct, step_pct):
            w3_pct = 100 - w1_pct - w2_pct
            weights.append((w1_pct / 100.0, w2_pct / 100.0, w3_pct / 100.0))
    return weights


def load_reference_121() -> pd.DataFrame:
    if not BASE_121_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(BASE_121_CSV)


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame):
    display = []
    for candidate in ["best_cagr", "best_calmar", "best_weekly", "best_monthly", "best_static"]:
        if candidate in curve_map:
            display.append(candidate)
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.0]})
    ax_eq, ax_perf, ax_meta = axes

    cmap = plt.get_cmap("tab10")
    colors = {variant: cmap(i % 10) for i, variant in enumerate(display)}

    for variant in display:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        label = str(curve["label"].iloc[0]) if "label" in curve.columns else variant
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=label)
    ax_eq.axhline(PORTFOLIO_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("Study 122: Practical Weekly/Monthly Flat-Only Rebalance")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    top = metrics_df.head(12)
    ax_perf.bar(top["variant"], top["cagr_pct"], color="#1f77b4", alpha=0.85, label="CAGR %")
    ax_perf.set_ylabel("CAGR %")
    ax_perf.grid(True, axis="y", alpha=0.2)
    ax_perf.tick_params(axis="x", rotation=20)
    ax_perf_t = ax_perf.twinx()
    ax_perf_t.plot(top["variant"], top["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_perf_t.set_ylabel("MDD %")
    h1, l1 = ax_perf.get_legend_handles_labels()
    h2, l2 = ax_perf_t.get_legend_handles_labels()
    ax_perf.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_meta.bar(top["variant"], top["rebalance_count"], color="#2ca02c", alpha=0.85, label="Rebalances")
    ax_meta.set_ylabel("Rebalances")
    ax_meta.grid(True, axis="y", alpha=0.2)
    ax_meta.tick_params(axis="x", rotation=20)
    ax_meta_t = ax_meta.twinx()
    ax_meta_t.plot(top["variant"], top["calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Calmar")
    ax_meta_t.set_ylabel("Calmar")
    h1, l1 = ax_meta.get_legend_handles_labels()
    h2, l2 = ax_meta_t.get_legend_handles_labels()
    ax_meta.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(
    metrics_df: pd.DataFrame,
    cache_end_ts: pd.Timestamp,
    common_start: pd.Timestamp,
    common_end: pd.Timestamp,
    ref121: pd.DataFrame,
):
    best_cagr = metrics_df.sort_values(["cagr_pct", "calmar_ratio"], ascending=[False, False]).iloc[0]
    best_calmar = metrics_df.sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]
    best_static = metrics_df[metrics_df["rebalance_mode"] == MODE_NONE].sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]
    best_weekly = metrics_df[metrics_df["rebalance_mode"] == MODE_WEEKLY_FLAT].sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]
    best_monthly = metrics_df[metrics_df["rebalance_mode"] == MODE_MONTHLY_FLAT].sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]

    lines: list[str] = []
    lines.append("# 122 연구: 실전형 리밸런스 검증 + 비중 재탐색")
    lines.append("")
    lines.append("## 설정")
    lines.append(f"- 로컬 최신 BTCUSDT 1분 캐시는 `{cache_end_ts}`까지 존재한다.")
    lines.append(f"- 이번 연구의 공통 구간은 `{common_start}` ~ `{common_end}` 이다.")
    lines.append("- sleeve는 case1/case2/case3를 그대로 유지하고, 비중만 넓게 흔들었다.")
    lines.append("- weight grid는 `5%` 단위 전체 simplex 탐색이다. 즉 `case1=0%`부터 `100%`까지 모두 열어둔다.")
    lines.append("- 리밸런스는 포지션을 강제로 정리하지 않는다.")
    lines.append("  주간/월간 due가 지난 뒤 `세 sleeve가 모두 flat`인 첫 시점에서만 리밸런스한다.")
    lines.append("")
    lines.append("## Sleeve 정의")
    lines.append(f"- case1: study62 `{CASE1_VARIANT}`")
    lines.append("- case2: study42 case2 sleeve")
    lines.append(f"- case3: study117 `{CASE3_VARIANT}`")
    lines.append("")
    lines.append("## 최고 결과")
    lines.append(
        f"- 최고 CAGR: `{best_cagr['variant']}` -> CAGR `{_fmt(best_cagr['cagr_pct'])}%`, "
        f"MDD `{_fmt(best_cagr['max_drawdown_pct'])}%`, Calmar `{_fmt(best_cagr['calmar_ratio'])}`, "
        f"weights `{_fmt(best_cagr['w1'],2)}/{_fmt(best_cagr['w2'],2)}/{_fmt(best_cagr['w3'],2)}`, mode `{best_cagr['rebalance_mode']}`"
    )
    lines.append(
        f"- 최고 Calmar: `{best_calmar['variant']}` -> CAGR `{_fmt(best_calmar['cagr_pct'])}%`, "
        f"MDD `{_fmt(best_calmar['max_drawdown_pct'])}%`, Calmar `{_fmt(best_calmar['calmar_ratio'])}`, "
        f"weights `{_fmt(best_calmar['w1'],2)}/{_fmt(best_calmar['w2'],2)}/{_fmt(best_calmar['w3'],2)}`, mode `{best_calmar['rebalance_mode']}`"
    )
    lines.append("")
    lines.append("## 모드별 우승")
    lines.append(
        f"- no rebalance: `{best_static['variant']}` -> CAGR `{_fmt(best_static['cagr_pct'])}%`, MDD `{_fmt(best_static['max_drawdown_pct'])}%`, Calmar `{_fmt(best_static['calmar_ratio'])}`"
    )
    lines.append(
        f"- weekly due + all-flat: `{best_weekly['variant']}` -> CAGR `{_fmt(best_weekly['cagr_pct'])}%`, MDD `{_fmt(best_weekly['max_drawdown_pct'])}%`, Calmar `{_fmt(best_weekly['calmar_ratio'])}`"
    )
    lines.append(
        f"- monthly due + all-flat: `{best_monthly['variant']}` -> CAGR `{_fmt(best_monthly['cagr_pct'])}%`, MDD `{_fmt(best_monthly['max_drawdown_pct'])}%`, Calmar `{_fmt(best_monthly['calmar_ratio'])}`"
    )
    lines.append("")
    if not ref121.empty:
        ref120 = ref121[ref121["variant"] == "study120_current_mix"]
        ref119 = ref121[ref121["variant"] == "study119_current_mix"]
        ref_case3 = ref121[ref121["variant"] == "case3_only"]
        lines.append("## 121 기준 참고값")
        if not ref119.empty:
            r = ref119.iloc[0]
            lines.append(f"- 121 study119_current_mix: CAGR `{_fmt(r['cagr_pct'])}%`, MDD `{_fmt(r['max_drawdown_pct'])}%`, Calmar `{_fmt(r['calmar_ratio'])}`")
        if not ref120.empty:
            r = ref120.iloc[0]
            lines.append(f"- 121 study120_current_mix: CAGR `{_fmt(r['cagr_pct'])}%`, MDD `{_fmt(r['max_drawdown_pct'])}%`, Calmar `{_fmt(r['calmar_ratio'])}`")
        if not ref_case3.empty:
            r = ref_case3.iloc[0]
            lines.append(f"- 121 case3_only: CAGR `{_fmt(r['cagr_pct'])}%`, MDD `{_fmt(r['max_drawdown_pct'])}%`, Calmar `{_fmt(r['calmar_ratio'])}`")
        lines.append("")
    lines.append("## 상위 15개")
    lines.append("")
    lines.append("| Variant | Mode | W1 | W2 | W3 | Final Equity | CAGR % | MDD % | Calmar | Rebalances | Deferred Bars |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.head(15).iterrows():
        lines.append(
            f"| {row['variant']} | {row['rebalance_mode']} | {_fmt(row['w1'],2)} | {_fmt(row['w2'],2)} | {_fmt(row['w3'],2)} | "
            f"{_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['calmar_ratio'])} | "
            f"{int(row['rebalance_count'])} | {int(row['deferred_due_bars'])} |"
        )
    lines.append("")
    lines.append("## 해석")
    lines.append("- weekly/monthly flat-only가 상위에 온다면, 잦은 기계적 리밸런스 없이도 포트폴리오 구성 효과가 유지된다는 뜻이다.")
    lines.append("- no rebalance가 계속 이긴다면, 현재는 분산보다 case3 단독 알파가 더 강하다는 뜻이다.")
    lines.append("- case1 비중이 낮은 조합이 상위라면, 2021~현재 전체 구간에서는 기존의 높은 case1 비중이 허수였을 가능성이 크다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run_validations(metrics_df: pd.DataFrame, common_start: pd.Timestamp, cache_end_ts: pd.Timestamp):
    if common_start.year != 2021:
        raise AssertionError("comparison did not start in 2021")
    if cache_end_ts.date() != pd.Timestamp("2026-03-15").date():
        raise AssertionError("unexpected latest cache end")
    if not {MODE_NONE, MODE_WEEKLY_FLAT, MODE_MONTHLY_FLAT}.issubset(set(metrics_df["rebalance_mode"])):
        raise AssertionError("missing rebalance mode rows")


def run():
    print("Loading modules...")
    m002 = load_module("study002_for_122", BASE_002_PATH)
    m04 = load_module("study04_for_122", BASE_04_PATH)
    m32 = load_module("study32_for_122", BASE_32_PATH)
    m42 = load_module("study42_for_122", BASE_42_PATH)
    m47 = load_module("study47_for_122", BASE_47_PATH)
    m62 = load_module("study62_for_122", BASE_62_PATH)
    s76 = load_module("study76_for_122", BASE_76_PATH)
    m111 = load_module("study111_for_122", BASE_111_PATH)
    m114 = load_module("study114_for_122", BASE_114_PATH)
    m117 = load_module("study117_for_122", BASE_117_PATH)

    print("Loading 2021+ raw market...")
    df_1m, df_4h, cache_end_ts = m114.load_market_data_2021plus()

    case3_stats_raw = {"trades": np.nan}
    if OUT_SLEEVE_CACHE.exists():
        print("Loading cached sleeve states...")
        cache = pd.read_pickle(OUT_SLEEVE_CACHE)
        if cache.get("cache_end_ts") == cache_end_ts:
            case1_state = cache["case1_state"].copy()
            case2_state = cache["case2_state"].copy()
            case3_state = cache["case3_state"].copy()
            case3_stats_raw = dict(cache.get("case3_stats_raw", case3_stats_raw))
        else:
            OUT_SLEEVE_CACHE.unlink(missing_ok=True)
            cache = None
    else:
        cache = None

    if cache is None:
        print("Running case1 sleeve with activity reconstruction...")
        case1_cfg = next(item for item in m62.VARIANTS if str(item["variant"]) == CASE1_VARIANT)
        Case1Class = m62.build_variant_class(
            m47.LiveParityNoLookahead,
            int(case1_cfg["bullish_close_bars"]),
            float(case1_cfg["shallow_gap_pct"]),
        )
        bt1 = Case1Class(
            symbol=m47.SYMBOL,
            initial_capital=SLEEVE_CAPITAL,
            commission=m47.COMMISSION,
            entry_scale=m62.ENTRY_SCALE,
        )
        m47.configure_baseline_params(bt1)
        bt1.run(df_1m.copy(), df_4h.copy(), backtest_start_date=BACKTEST_START)
        eq1 = pd.DataFrame(bt1.equity_curve)[["timestamp", "equity"]].copy()
        eq1["timestamp"] = pd.to_datetime(eq1["timestamp"])
        trades1 = pd.DataFrame(bt1.trades)
        active1 = build_activity_from_trades(pd.DatetimeIndex(eq1["timestamp"]), trades1)
        eq1["active"] = active1
        case1_state = resample_state(eq1, "equity", "active")
        case1_state = scale_equity(case1_state, "equity", PORTFOLIO_CAPITAL / SLEEVE_CAPITAL)

        print("Running case2 sleeve with activity reconstruction...")
        Case2Class = m42.build_case2_class(m32)
        bt2 = Case2Class(
            base_module=m002,
            symbol=m002.SYMBOL,
            initial_capital=SLEEVE_CAPITAL,
            commission=m002.COMMISSION,
            entry_scale=m42.ENTRY_SCALE,
        )
        m04.configure_baseline_params(bt2)
        bt2.run(df_1m.copy(), df_4h.copy(), backtest_start_date=BACKTEST_START)
        eq2 = pd.DataFrame(bt2.equity_curve)[["timestamp", "equity"]].copy()
        eq2["timestamp"] = pd.to_datetime(eq2["timestamp"])
        trades2 = pd.DataFrame(bt2.trades)
        active2 = build_activity_from_trades(pd.DatetimeIndex(eq2["timestamp"]), trades2)
        eq2["active"] = active2
        case2_state = resample_state(eq2, "equity", "active")
        case2_state = scale_equity(case2_state, "equity", PORTFOLIO_CAPITAL / SLEEVE_CAPITAL)

        print("Running case3 sleeve...")
        market = m114.prepare_market_114(df_1m.copy(), df_4h.copy(), m47, m111)
        case3_cfg = next(item for item in m117.build_variants() if str(item["variant"]) == CASE3_VARIANT)
        case3_curve_raw, case3_stats_raw = m117.run_variant_117(market, case3_cfg, s76)
        case3_state = case3_curve_raw[["timestamp", "equity", "side"]].copy()
        case3_state["timestamp"] = pd.to_datetime(case3_state["timestamp"])
        case3_state["active"] = case3_state["side"].astype(int) != 0
        case3_state = case3_state[["timestamp", "equity", "active"]].copy()
        case3_state = resample_state(case3_state, "equity", "active")
        case3_state = scale_equity(case3_state, "equity", PORTFOLIO_CAPITAL / float(s76.INITIAL_CAPITAL))

        pd.to_pickle(
            {
                "cache_end_ts": cache_end_ts,
                "case1_state": case1_state,
                "case2_state": case2_state,
                "case3_state": case3_state,
                "case3_stats_raw": case3_stats_raw,
            },
            OUT_SLEEVE_CACHE,
        )

    common_start = max(
        pd.Timestamp(case1_state["timestamp"].min()),
        pd.Timestamp(case2_state["timestamp"].min()),
        pd.Timestamp(case3_state["timestamp"].min()),
    )
    common_end = min(
        pd.Timestamp(case1_state["timestamp"].max()),
        pd.Timestamp(case2_state["timestamp"].max()),
        pd.Timestamp(case3_state["timestamp"].max()),
    )

    case1_state = clip_state(case1_state, common_start, common_end, "equity", "active")
    case2_state = clip_state(case2_state, common_start, common_end, "equity", "active")
    case3_state = clip_state(case3_state, common_start, common_end, "equity", "active")

    merged = pd.merge(
        case1_state.rename(columns={"equity": "equity_case1", "active": "active_case1"}),
        case2_state.rename(columns={"equity": "equity_case2", "active": "active_case2"}),
        on="timestamp",
        how="inner",
    )
    merged = pd.merge(
        merged,
        case3_state.rename(columns={"equity": "equity_case3", "active": "active_case3"}),
        on="timestamp",
        how="inner",
    )
    merged = merged.sort_values("timestamp").reset_index(drop=True)

    rows: list[dict] = []
    curve_map: dict[str, pd.DataFrame] = {}
    weight_grid = build_weight_grid()
    print(f"Running portfolio sweep across {len(weight_grid)} weight combos and {len(MODES)} practical modes...")

    for mode in MODES:
        for w1, w2, w3 in weight_grid:
            variant = f"{mode}_w{int(round(w1*100))}_{int(round(w2*100))}_{int(round(w3*100))}"
            curve, run_stats = run_portfolio(merged, w1, w2, w3, mode)
            stats = compute_curve_stats(curve, "equity", PORTFOLIO_CAPITAL)
            rows.append(
                {
                    "variant": variant,
                    "rebalance_mode": mode,
                    "w1": w1,
                    "w2": w2,
                    "w3": w3,
                    **stats,
                    **run_stats,
                }
            )
            curve_map[variant] = curve.copy()

    metrics_df = pd.DataFrame(rows)
    metrics_df = metrics_df.sort_values(
        ["calmar_ratio", "cagr_pct", "max_drawdown_pct"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    ref121 = load_reference_121()

    best_cagr_row = metrics_df.sort_values(["cagr_pct", "calmar_ratio"], ascending=[False, False]).iloc[0]
    best_calmar_row = metrics_df.sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]
    best_static_row = metrics_df[metrics_df["rebalance_mode"] == MODE_NONE].sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]
    best_weekly_row = metrics_df[metrics_df["rebalance_mode"] == MODE_WEEKLY_FLAT].sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]
    best_monthly_row = metrics_df[metrics_df["rebalance_mode"] == MODE_MONTHLY_FLAT].sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).iloc[0]

    selected = {
        "best_cagr": best_cagr_row["variant"],
        "best_calmar": best_calmar_row["variant"],
        "best_static": best_static_row["variant"],
        "best_weekly": best_weekly_row["variant"],
        "best_monthly": best_monthly_row["variant"],
    }
    selected_curves: list[pd.DataFrame] = []
    labelled_curve_map: dict[str, pd.DataFrame] = {}
    for label, variant in selected.items():
        curve = curve_map[str(variant)].copy()
        curve["variant"] = str(variant)
        curve["label"] = f"{label}: {variant}"
        selected_curves.append(curve)
        labelled_curve_map[label] = curve

    selected_curves_df = pd.concat(selected_curves, ignore_index=True)
    metrics_df.to_csv(OUT_CSV, index=False)
    selected_curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(labelled_curve_map, metrics_df)
    save_report(metrics_df, cache_end_ts, common_start, common_end, ref121)
    run_validations(metrics_df, common_start, cache_end_ts)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.head(15).to_string(index=False))
    print(f"case3_trades={int(case3_stats_raw.get('trades', 0))}")


if __name__ == "__main__":
    run()
