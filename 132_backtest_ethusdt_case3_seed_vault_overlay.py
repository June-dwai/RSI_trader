from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SOURCE_76 = Path("76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py")
SOURCE_114 = Path("114_backtest_btcusdt_best_with_sr_smc_filters.py")
SOURCE_117 = Path("117_backtest_btcusdt_115_highcagr_push.py")
SOURCE_126 = Path("126_backtest_btcusdt_case3_long_quality_push.py")
SOURCE_129 = Path("129_backtest_ethusdt_case2_vs_case3best_mix.py")
SOURCE_47 = Path("47_backtest_btcusdt_scale06_adx002_case1_standalone.py")
SOURCE_111 = Path("111_backtest_btcusdt_sr_smc_5m_profitmax.py")

CURVE_FILE = Path("129_backtest_ethusdt_case2_vs_case3best_mix_curves.csv")
RAW_VARIANT = "lb4_delay9_capna_cd0_only"

OUT_BASE = "132_backtest_ethusdt_case3_seed_vault_overlay"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_EVENTS_CSV = Path(f"{OUT_BASE}_events.csv")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_MD = Path(f"{OUT_BASE}.md")

INITIAL_SEED = 2000.0
DOUBLE_THRESHOLD = 2.0
HALF_THRESHOLD = 0.5
ANALYSIS_2026_START = pd.Timestamp("2026-01-01 00:00:00")


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
    peak_row = curve.loc[series.idxmax()]
    trough_row = curve.loc[series.idxmin()]
    return {
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "calmar_ratio": calmar_ratio,
        "peak_ts": pd.Timestamp(peak_row["timestamp"]),
        "peak_equity": float(peak_row[equity_col]),
        "trough_ts": pd.Timestamp(trough_row["timestamp"]),
        "trough_equity": float(trough_row[equity_col]),
    }


def compute_window_stats(curve: pd.DataFrame, equity_col: str, start_ts: pd.Timestamp) -> dict:
    seg = curve[pd.to_datetime(curve["timestamp"]) >= pd.Timestamp(start_ts)].copy()
    if seg.empty:
        return {"return_pct": np.nan, "mdd_pct": np.nan}
    start_eq = float(seg[equity_col].iloc[0])
    end_eq = float(seg[equity_col].iloc[-1])
    if start_eq <= 0:
        return {"return_pct": np.nan, "mdd_pct": np.nan}
    dd = seg[equity_col].astype(float) / seg[equity_col].cummax().astype(float) - 1.0
    return {
        "return_pct": (end_eq / start_eq - 1.0) * 100.0,
        "mdd_pct": -float(dd.min() * 100.0),
    }


def load_raw_case3_curve() -> pd.DataFrame:
    if not CURVE_FILE.exists():
        raise FileNotFoundError(f"Missing curve file: {CURVE_FILE}")
    curve = pd.read_csv(CURVE_FILE)
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    curve = curve[curve["variant"] == RAW_VARIANT].copy()
    curve = curve.sort_values("timestamp").reset_index(drop=True)
    return curve[["timestamp", "equity"]].copy()


def apply_seed_vault_overlay(curve: pd.DataFrame, seed: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    active = float(seed)
    vault = 0.0
    prev_raw = float(curve["equity"].iloc[0])
    rows: list[dict] = []
    events: list[dict] = []

    for i, row in curve.iterrows():
        ts = pd.Timestamp(row["timestamp"])
        raw_equity = float(row["equity"])
        ret = 0.0 if i == 0 or prev_raw <= 0 else raw_equity / prev_raw - 1.0
        active *= 1.0 + ret
        prev_raw = raw_equity

        while active >= seed * DOUBLE_THRESHOLD:
            active -= seed
            vault += seed
            events.append(
                {
                    "timestamp": ts,
                    "event": "withdraw",
                    "amount": seed,
                    "active_after": active,
                    "vault_after": vault,
                    "total_after": active + vault,
                }
            )

        if active <= seed * HALF_THRESHOLD and vault > 0:
            deposit = min(seed - active, vault)
            if deposit > 0:
                active += deposit
                vault -= deposit
                events.append(
                    {
                        "timestamp": ts,
                        "event": "deposit",
                        "amount": deposit,
                        "active_after": active,
                        "vault_after": vault,
                        "total_after": active + vault,
                    }
                )

        rows.append(
            {
                "timestamp": ts,
                "raw_equity": raw_equity,
                "managed_total_equity": active + vault,
                "managed_active_equity": active,
                "vault_balance": vault,
            }
        )

    return pd.DataFrame(rows), pd.DataFrame(events)


def build_worst_months(curve: pd.DataFrame, col: str, count: int = 8) -> pd.DataFrame:
    temp = curve.copy()
    temp["month"] = temp["timestamp"].dt.to_period("M")
    rows = []
    for month, grp in temp.groupby("month"):
        start = float(grp[col].iloc[0])
        end = float(grp[col].iloc[-1])
        rows.append(
            {
                "month": str(month),
                "start_equity": start,
                "end_equity": end,
                "return_pct": (end / start - 1.0) * 100.0,
            }
        )
    out = pd.DataFrame(rows).sort_values("return_pct").reset_index(drop=True)
    return out.head(count)


def compute_post_peak_trough(curve: pd.DataFrame, col: str) -> dict:
    peak_idx = curve[col].astype(float).idxmax()
    peak_ts = pd.Timestamp(curve.loc[peak_idx, "timestamp"])
    peak_eq = float(curve.loc[peak_idx, col])
    post = curve[curve["timestamp"] >= peak_ts].copy()
    trough_idx = post[col].astype(float).idxmin()
    trough_ts = pd.Timestamp(post.loc[trough_idx, "timestamp"])
    trough_eq = float(post.loc[trough_idx, col])
    return {
        "peak_ts": peak_ts,
        "peak_equity": peak_eq,
        "trough_ts": trough_ts,
        "trough_equity": trough_eq,
        "drop_pct": (trough_eq / peak_eq - 1.0) * 100.0,
    }


def load_market_local(end_ts: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = [
        pd.read_pickle(Path("historical_data_mainnet/ETHUSDT_1m_2021-01-01_2021-12-31.pkl")),
        pd.read_pickle(Path("historical_data_mainnet/ETHUSDT_1m_2022-01-01_2024-12-31.pkl")),
        pd.read_pickle(Path("historical_data_mainnet/ETHUSDT_1m_2025-01-01_2026-04-12.pkl")),
    ]
    df_1m = pd.concat(frames).sort_index()
    if not isinstance(df_1m.index, pd.DatetimeIndex):
        df_1m.index = pd.to_datetime(df_1m.index)
    df_1m = df_1m[~df_1m.index.duplicated(keep="last")]
    df_1m = df_1m[df_1m.index <= pd.Timestamp(end_ts)].copy()
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df_1m.columns:
            df_1m[col] = pd.to_numeric(df_1m[col], errors="coerce")
    df_1m = df_1m.dropna(subset=["open", "high", "low", "close", "volume"])
    df_4h = (
        df_1m.resample("4h")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
    )
    return df_1m, df_4h


def run_case3_stats(end_ts: pd.Timestamp) -> tuple[dict, dict]:
    m129 = load_module("m129_for_132", SOURCE_129)
    m47 = load_module("m47_for_132", SOURCE_47)
    s76 = load_module("s76_for_132", SOURCE_76)
    m111 = load_module("m111_for_132", SOURCE_111)
    m114 = load_module("m114_for_132", SOURCE_114)
    m117 = load_module("m117_for_132", SOURCE_117)
    s126 = load_module("s126_for_132", SOURCE_126)

    df_1m, df_4h = load_market_local(end_ts)
    m47.SYMBOL = "ETHUSDT"
    m47.BACKTEST_START = "2021-01-01"
    m47.BACKTEST_END = pd.Timestamp(end_ts).strftime("%Y-%m-%d")
    market = m114.prepare_market_114(df_1m.copy(), df_4h.copy(), m47, m111)
    curve, stats = s126.run_variant_126(market, m129.CASE3_CFG, s76, m117)
    curve["timestamp"] = pd.to_datetime(curve["timestamp"])
    side_mix = {
        "pct_long": float((curve["side"] > 0).mean() * 100.0),
        "pct_short": float((curve["side"] < 0).mean() * 100.0),
        "pct_flat": float((curve["side"] == 0).mean() * 100.0),
    }
    return stats, side_mix


def save_plot(curve: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.0]})
    ax_eq, ax_alloc, ax_dd = axes

    ax_eq.plot(curve["timestamp"], curve["raw_equity"], color="#d62728", linewidth=1.0, label="raw_case3_equity")
    ax_eq.plot(curve["timestamp"], curve["managed_total_equity"], color="#1f77b4", linewidth=1.2, label="seed_vault_total_wealth")
    ax_eq.set_title("Study 132: 129 Red-Line Case3 vs Seed Vault Overlay")
    ax_eq.set_ylabel("Equity / Wealth (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_alloc.plot(curve["timestamp"], curve["managed_active_equity"], color="#2ca02c", linewidth=1.0, label="active_equity")
    ax_alloc.plot(curve["timestamp"], curve["vault_balance"], color="#9467bd", linewidth=1.0, label="vault_balance")
    ax_alloc.set_ylabel("Managed Split (USDT)")
    ax_alloc.grid(True, alpha=0.2)
    ax_alloc.legend(loc="upper left")

    raw_dd = curve["raw_equity"].astype(float) / curve["raw_equity"].cummax().astype(float) - 1.0
    managed_dd = curve["managed_total_equity"].astype(float) / curve["managed_total_equity"].cummax().astype(float) - 1.0
    ax_dd.plot(curve["timestamp"], -raw_dd * 100.0, color="#d62728", linewidth=1.0, label="raw_case3_dd")
    ax_dd.plot(curve["timestamp"], -managed_dd * 100.0, color="#1f77b4", linewidth=1.0, label="seed_vault_dd")
    ax_dd.set_ylabel("Drawdown %")
    ax_dd.set_xlabel("Time")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(
    raw_curve: pd.DataFrame,
    managed_curve: pd.DataFrame,
    events: pd.DataFrame,
    metrics_df: pd.DataFrame,
    raw_stats: dict,
    managed_stats: dict,
    worst_raw_months: pd.DataFrame,
    case3_engine_stats: dict,
    side_mix: dict,
) -> None:
    raw_row = metrics_df.loc[metrics_df["variant"] == "raw_case3"].iloc[0]
    managed_row = metrics_df.loc[metrics_df["variant"] == "seed_vault_overlay"].iloc[0]
    raw_post_peak = compute_post_peak_trough(raw_curve.rename(columns={"equity": "series"}), "series")
    managed_post_peak = compute_post_peak_trough(managed_curve.rename(columns={"managed_total_equity": "series"}), "series")
    withdrawals = events[events["event"] == "withdraw"].copy()
    deposits = events[events["event"] == "deposit"].copy()

    lines: list[str] = []
    lines.append("# Study 132: ETHUSDT 129 red-line case3 drawdown check + seed vault overlay")
    lines.append("")
    lines.append("## Assumption")
    lines.append(f"- Base strategy is the existing red line: `{RAW_VARIANT}` from study 129.")
    lines.append(f"- Starting seed: `{INITIAL_SEED:.0f}` USDT.")
    lines.append(
        f"- Overlay rule: when active equity reaches `{DOUBLE_THRESHOLD:.1f}x seed` (`{INITIAL_SEED * DOUBLE_THRESHOLD:.0f}`), withdraw `{INITIAL_SEED:.0f}` into a vault."
    )
    lines.append(
        f"- Refill rule: when active equity falls to `{HALF_THRESHOLD:.1f}x seed` (`{INITIAL_SEED * HALF_THRESHOLD:.0f}`) or lower, deposit from the vault only enough to restore active equity back to `{INITIAL_SEED:.0f}`."
    )
    lines.append("- Deposits are funded only from prior withdrawals; no outside capital is added.")
    lines.append("")
    lines.append("## Why The Red Line Whipsaws So Hard")
    lines.append(f"- It is a `3.0x` leverage regime-hold engine with `98%` of wallet posted as margin on each new position.")
    lines.append(f"- Effective full-wallet notional per new trade is about `2.94x` wallet (`0.98 * 3.0`).")
    lines.append("- Profits are not skimmed out, so every big gain gets recycled into the next trade size.")
    lines.append("- This ETH run had `0` liquidations, so the giant drawdown is not a margin-call story; it is a compounding give-back story.")
    lines.append(
        f"- Trade stats on the matched window: trades `{case3_engine_stats['trades']}`, longs `{case3_engine_stats['long_entries']}`, shorts `{case3_engine_stats['short_entries']}`, "
        f"stops `{case3_engine_stats['stop_exits']}`, signal exits `{case3_engine_stats['signal_exits']}`, short TP exits `{case3_engine_stats['tp_exits']}`."
    )
    lines.append(
        f"- Side mix by bar: long `{_fmt(side_mix['pct_long'], 2)}%`, short `{_fmt(side_mix['pct_short'], 2)}%`, flat `{_fmt(side_mix['pct_flat'], 2)}%`."
    )
    lines.append(
        f"- Peak-to-trough on the raw curve: `{raw_post_peak['peak_ts']}` `{_fmt(raw_post_peak['peak_equity'])}` -> "
        f"`{raw_post_peak['trough_ts']}` `{_fmt(raw_post_peak['trough_equity'])}` (`{_fmt(raw_post_peak['drop_pct'])}%`)."
    )
    lines.append("- Worst raw months were:")
    for _, row in worst_raw_months.iterrows():
        lines.append(
            f"  - `{row['month']}`: `{_fmt(row['return_pct'])}%` (`{_fmt(row['start_equity'])}` -> `{_fmt(row['end_equity'])}`)"
        )
    lines.append("")
    lines.append("## Results")
    lines.append("| Variant | Final Equity | CAGR % | MDD % | Calmar | 2026 Return % | 2026 MDD % | Peak Equity | Post-Peak Trough | Post-Peak Drop % |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        lines.append(
            f"| {row['variant']} | {_fmt(row['final_equity'])} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | "
            f"{_fmt(row['calmar_ratio'])} | {_fmt(row['return_2026_pct'])} | {_fmt(row['mdd_2026_pct'])} | {_fmt(row['peak_equity'])} | "
            f"{_fmt(row['post_peak_trough_equity'])} | {_fmt(row['post_peak_drop_pct'])} |"
        )
    lines.append("")
    lines.append("## Overlay Event Summary")
    lines.append(
        f"- Withdrawals: `{len(withdrawals)}` events, cumulative `{_fmt(withdrawals['amount'].sum() if not withdrawals.empty else 0.0)}`."
    )
    lines.append(
        f"- Deposits: `{len(deposits)}` events, cumulative `{_fmt(deposits['amount'].sum() if not deposits.empty else 0.0)}`."
    )
    lines.append(
        f"- Final split: active `{_fmt(managed_curve['managed_active_equity'].iloc[-1])}`, vault `{_fmt(managed_curve['vault_balance'].iloc[-1])}`, total `{_fmt(managed_curve['managed_total_equity'].iloc[-1])}`."
    )
    if not withdrawals.empty:
        lines.append("- First withdrawals:")
        for _, row in withdrawals.head(5).iterrows():
            lines.append(
                f"  - `{pd.Timestamp(row['timestamp'])}` withdraw `{_fmt(row['amount'])}` -> active `{_fmt(row['active_after'])}`, vault `{_fmt(row['vault_after'])}`"
            )
    if not deposits.empty:
        lines.append("- First deposits:")
        for _, row in deposits.head(5).iterrows():
            lines.append(
                f"  - `{pd.Timestamp(row['timestamp'])}` deposit `{_fmt(row['amount'])}` -> active `{_fmt(row['active_after'])}`, vault `{_fmt(row['vault_after'])}`"
            )
    lines.append("")
    lines.append("## Interpretation")
    lines.append(
        f"- Raw red line finished higher (`{_fmt(raw_row['final_equity'])}`) but with extreme MDD `{_fmt(raw_row['max_drawdown_pct'])}%` and a post-peak collapse of `{_fmt(raw_row['post_peak_drop_pct'])}%`."
    )
    lines.append(
        f"- The seed-vault overlay finished lower (`{_fmt(managed_row['final_equity'])}`) but cut MDD to `{_fmt(managed_row['max_drawdown_pct'])}%` and reduced the post-peak drop to `{_fmt(managed_row['post_peak_drop_pct'])}%`."
    )
    lines.append(
        f"- In 2026 the overlay changed return from `{_fmt(raw_row['return_2026_pct'])}%` to `{_fmt(managed_row['return_2026_pct'])}%` and MDD from `{_fmt(raw_row['mdd_2026_pct'])}%` to `{_fmt(managed_row['mdd_2026_pct'])}%`."
    )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Events CSV: `{OUT_EVENTS_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    raw_curve = load_raw_case3_curve()
    if not np.isclose(float(raw_curve["equity"].iloc[0]), INITIAL_SEED):
        raise ValueError(f"Expected initial curve equity {INITIAL_SEED}, got {raw_curve['equity'].iloc[0]}")

    print(f"[132] Loaded raw 129 red-line curve: {raw_curve['timestamp'].min()} -> {raw_curve['timestamp'].max()} ({len(raw_curve)} rows)", flush=True)
    managed_curve, events = apply_seed_vault_overlay(raw_curve, INITIAL_SEED)

    raw_stats = compute_curve_stats(raw_curve, "equity", INITIAL_SEED)
    managed_stats = compute_curve_stats(managed_curve, "managed_total_equity", INITIAL_SEED)
    raw_2026 = compute_window_stats(raw_curve, "equity", ANALYSIS_2026_START)
    managed_2026 = compute_window_stats(managed_curve, "managed_total_equity", ANALYSIS_2026_START)
    worst_raw_months = build_worst_months(raw_curve.rename(columns={"equity": "series"}), "series")
    case3_engine_stats, side_mix = run_case3_stats(pd.Timestamp(raw_curve["timestamp"].iloc[-1]))

    raw_post_peak = compute_post_peak_trough(raw_curve.rename(columns={"equity": "series"}), "series")
    managed_post_peak = compute_post_peak_trough(managed_curve.rename(columns={"managed_total_equity": "series"}), "series")

    metrics_rows = [
        {
            "variant": "raw_case3",
            **raw_stats,
            "return_2026_pct": raw_2026["return_pct"],
            "mdd_2026_pct": raw_2026["mdd_pct"],
            "post_peak_trough_equity": raw_post_peak["trough_equity"],
            "post_peak_drop_pct": raw_post_peak["drop_pct"],
        },
        {
            "variant": "seed_vault_overlay",
            **managed_stats,
            "return_2026_pct": managed_2026["return_pct"],
            "mdd_2026_pct": managed_2026["mdd_pct"],
            "post_peak_trough_equity": managed_post_peak["trough_equity"],
            "post_peak_drop_pct": managed_post_peak["drop_pct"],
        },
    ]
    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    events.to_csv(OUT_EVENTS_CSV, index=False, encoding="utf-8-sig")
    managed_curve.to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")
    save_plot(managed_curve)
    save_report(raw_curve, managed_curve, events, metrics_df, raw_stats, managed_stats, worst_raw_months, case3_engine_stats, side_mix)

    print(
        f"[132] raw_case3: final={_fmt(metrics_df.loc[0, 'final_equity'])} CAGR={_fmt(metrics_df.loc[0, 'cagr_pct'])}% "
        f"MDD={_fmt(metrics_df.loc[0, 'max_drawdown_pct'])}% peakdrop={_fmt(metrics_df.loc[0, 'post_peak_drop_pct'])}%",
        flush=True,
    )
    print(
        f"[132] seed_vault_overlay: final={_fmt(metrics_df.loc[1, 'final_equity'])} CAGR={_fmt(metrics_df.loc[1, 'cagr_pct'])}% "
        f"MDD={_fmt(metrics_df.loc[1, 'max_drawdown_pct'])}% peakdrop={_fmt(metrics_df.loc[1, 'post_peak_drop_pct'])}%",
        flush=True,
    )
    print(
        f"[132] Events: withdrawals={len(events[events['event'] == 'withdraw'])} deposits={len(events[events['event'] == 'deposit'])}",
        flush=True,
    )
    print(f"[132] Outputs: {OUT_PNG}, {OUT_CSV}, {OUT_EVENTS_CSV}, {OUT_CURVES_CSV}, {OUT_MD}", flush=True)


if __name__ == "__main__":
    main()
