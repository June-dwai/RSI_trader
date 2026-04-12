from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


SOURCE_132 = Path("132_backtest_ethusdt_case3_seed_vault_overlay.py")

OUT_BASE = "133_backtest_ethusdt_case3_seed_ladder_overlay"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_EVENTS_CSV = Path(f"{OUT_BASE}_events.csv")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")
OUT_MD = Path(f"{OUT_BASE}.md")

INITIAL_SEED = 2000.0
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


def apply_multiplier_ladder_overlay(curve: pd.DataFrame, seed: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    active = float(seed)
    vault = 0.0
    current_seed = float(seed)
    next_target = float(seed) * 2.0
    prev_raw = float(curve["equity"].iloc[0])
    rows: list[dict] = []
    events: list[dict] = []

    for i, row in curve.iterrows():
        ts = pd.Timestamp(row["timestamp"])
        raw_equity = float(row["equity"])
        ret = 0.0 if i == 0 or prev_raw <= 0 else raw_equity / prev_raw - 1.0
        active *= 1.0 + ret
        prev_raw = raw_equity

        while active >= next_target:
            withdraw = active - (next_target / 2.0)
            active = next_target / 2.0
            vault += withdraw
            current_seed = next_target / 2.0
            events.append(
                {
                    "timestamp": ts,
                    "variant": "multiplier_ladder_overlay",
                    "event": "withdraw",
                    "amount": withdraw,
                    "active_after": active,
                    "vault_after": vault,
                    "current_seed_after": current_seed,
                    "next_target_after": next_target * 2.0,
                }
            )
            next_target *= 2.0

        refill_trigger = current_seed / 2.0
        if active <= refill_trigger and vault > 0:
            deposit = min(current_seed - active, vault)
            if deposit > 0:
                active += deposit
                vault -= deposit
                events.append(
                    {
                        "timestamp": ts,
                        "variant": "multiplier_ladder_overlay",
                        "event": "deposit",
                        "amount": deposit,
                        "active_after": active,
                        "vault_after": vault,
                        "current_seed_after": current_seed,
                        "next_target_after": next_target,
                    }
                )

        rows.append(
            {
                "timestamp": ts,
                "variant": "multiplier_ladder_overlay",
                "raw_equity": raw_equity,
                "managed_total_equity": active + vault,
                "managed_active_equity": active,
                "vault_balance": vault,
                "current_seed": current_seed,
                "next_target": next_target,
            }
        )

    return pd.DataFrame(rows), pd.DataFrame(events)


def build_metrics(study132, curve: pd.DataFrame, col: str, variant: str) -> dict:
    stats = study132.compute_curve_stats(curve.rename(columns={col: "series"}), "series", INITIAL_SEED)
    window = study132.compute_window_stats(curve.rename(columns={col: "series"}), "series", ANALYSIS_2026_START)
    post_peak = study132.compute_post_peak_trough(curve.rename(columns={col: "series"}), "series")
    return {
        "variant": variant,
        "final_equity": stats["final_equity"],
        "total_return_pct": stats["total_return_pct"],
        "cagr_pct": stats["cagr_pct"],
        "max_drawdown_pct": stats["max_drawdown_pct"],
        "calmar_ratio": stats["calmar_ratio"],
        "peak_ts": stats["peak_ts"],
        "peak_equity": stats["peak_equity"],
        "return_2026_pct": window["return_pct"],
        "mdd_2026_pct": window["mdd_pct"],
        "post_peak_trough_ts": post_peak["trough_ts"],
        "post_peak_trough_equity": post_peak["trough_equity"],
        "post_peak_drop_pct": post_peak["drop_pct"],
    }


def save_plot(raw_curve: pd.DataFrame, fixed_curve: pd.DataFrame, ladder_curve: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.0, 1.0, 1.0]})
    ax_eq, ax_dd, ax_alloc = axes

    series = [
        ("raw_case3", raw_curve["timestamp"], raw_curve["equity"], "#d62728"),
        ("fixed_seed_overlay", fixed_curve["timestamp"], fixed_curve["managed_total_equity"], "#1f77b4"),
        ("multiplier_ladder_overlay", ladder_curve["timestamp"], ladder_curve["managed_total_equity"], "#2ca02c"),
    ]

    for label, ts, eq, color in series:
        ax_eq.plot(ts, eq, linewidth=1.1, label=label, color=color)
        dd = eq.astype(float) / eq.astype(float).cummax() - 1.0
        ax_dd.plot(ts, -dd * 100.0, linewidth=1.0, label=label, color=color)

    ax_alloc.plot(ladder_curve["timestamp"], ladder_curve["managed_active_equity"], color="#2ca02c", linewidth=1.0, label="ladder_active")
    ax_alloc.plot(ladder_curve["timestamp"], ladder_curve["vault_balance"], color="#9467bd", linewidth=1.0, label="ladder_vault")

    ax_eq.set_title("Study 133: Red-Line Case3 vs Fixed Seed vs Multiplier Ladder Overlay")
    ax_eq.set_ylabel("Equity / Wealth (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left")

    ax_dd.set_ylabel("Drawdown %")
    ax_dd.grid(True, alpha=0.2)
    ax_dd.legend(loc="upper left")

    ax_alloc.set_ylabel("Ladder Split (USDT)")
    ax_alloc.set_xlabel("Time")
    ax_alloc.grid(True, alpha=0.2)
    ax_alloc.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame, fixed_events: pd.DataFrame, ladder_events: pd.DataFrame, ladder_curve: pd.DataFrame) -> None:
    raw = metrics_df.loc[metrics_df["variant"] == "raw_case3"].iloc[0]
    fixed = metrics_df.loc[metrics_df["variant"] == "fixed_seed_overlay"].iloc[0]
    ladder = metrics_df.loc[metrics_df["variant"] == "multiplier_ladder_overlay"].iloc[0]

    lines: list[str] = []
    lines.append("# Study 133: ETHUSDT case3 fixed-seed overlay vs multiplier ladder overlay")
    lines.append("")
    lines.append("## Interpretation Of The User Rule")
    lines.append("- Previous study 132 assumed a fixed `2000 USDT` seed forever.")
    lines.append("- New ladder interpretation uses multiplier levels: `4k -> 8k -> 16k -> 32k -> 64k -> 128k ...`.")
    lines.append("- When active equity reaches a ladder level `T`, the system skims it down to `T/2`, sends the rest to the vault, and the new refill seed becomes `T/2`.")
    lines.append("- When active equity later falls to half of that seed, it refills back to the current seed from the vault.")
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
    lines.append("## Why The New Ladder Matches Better")
    lines.append(
        f"- Fixed-seed overlay only withdrew `{_fmt(fixed_events[fixed_events['event'] == 'withdraw']['amount'].sum())}` in total because it kept resetting the operating seed back to `2000`."
    )
    lines.append(
        f"- Multiplier ladder withdrew `{_fmt(ladder_events[ladder_events['event'] == 'withdraw']['amount'].sum())}` in total and refilled `{_fmt(ladder_events[ladder_events['event'] == 'deposit']['amount'].sum())}`."
    )
    lines.append(
        f"- Under the ladder, the last active seed reached `{_fmt(ladder_curve['current_seed'].iloc[-1])}` and the next withdrawal ladder became `{_fmt(ladder_curve['next_target'].iloc[-1])}`."
    )
    lines.append(
        f"- At the ladder wealth peak, active was `{_fmt(ladder_curve.loc[ladder_curve['managed_total_equity'].idxmax(), 'managed_active_equity'])}` and vault was `{_fmt(ladder_curve.loc[ladder_curve['managed_total_equity'].idxmax(), 'vault_balance'])}`."
    )
    lines.append("")
    lines.append("## Takeaways")
    lines.append(
        f"- Raw red line has the highest terminal equity of the un-managed sleeve (`{_fmt(raw['final_equity'])}`) but catastrophic MDD `{_fmt(raw['max_drawdown_pct'])}%`."
    )
    lines.append(
        f"- Fixed seed overlay cut MDD hardest (`{_fmt(fixed['max_drawdown_pct'])}%`) but also suppressed the upside too much."
    )
    lines.append(
        f"- Multiplier ladder sits in the middle: final wealth `{_fmt(ladder['final_equity'])}`, CAGR `{_fmt(ladder['cagr_pct'])}%`, MDD `{_fmt(ladder['max_drawdown_pct'])}%`."
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
    study132 = load_module("study132_for_133", SOURCE_132)
    raw_curve = study132.load_raw_case3_curve()
    fixed_curve, fixed_events = study132.apply_seed_vault_overlay(raw_curve.copy(), INITIAL_SEED)
    ladder_curve, ladder_events = apply_multiplier_ladder_overlay(raw_curve.copy(), INITIAL_SEED)

    metrics_rows = [
        build_metrics(study132, raw_curve.copy(), "equity", "raw_case3"),
        build_metrics(study132, fixed_curve.copy(), "managed_total_equity", "fixed_seed_overlay"),
        build_metrics(study132, ladder_curve.copy(), "managed_total_equity", "multiplier_ladder_overlay"),
    ]
    metrics_df = pd.DataFrame(metrics_rows)

    fixed_curve_out = fixed_curve.copy()
    fixed_curve_out["variant"] = "fixed_seed_overlay"
    ladder_curve_out = ladder_curve.copy()
    raw_curve_out = raw_curve.copy()
    raw_curve_out["raw_equity"] = raw_curve_out["equity"]
    raw_curve_out["managed_total_equity"] = raw_curve_out["equity"]
    raw_curve_out["managed_active_equity"] = raw_curve_out["equity"]
    raw_curve_out["vault_balance"] = 0.0
    raw_curve_out["current_seed"] = INITIAL_SEED
    raw_curve_out["next_target"] = INITIAL_SEED * 2.0
    raw_curve_out["variant"] = "raw_case3"

    fixed_events = fixed_events.copy()
    fixed_events["variant"] = "fixed_seed_overlay"
    ladder_events = ladder_events.copy()

    metrics_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    pd.concat([raw_curve_out, fixed_curve_out, ladder_curve_out], ignore_index=True).to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")
    pd.concat([fixed_events, ladder_events], ignore_index=True).to_csv(OUT_EVENTS_CSV, index=False, encoding="utf-8-sig")
    save_plot(raw_curve, fixed_curve, ladder_curve)
    save_report(metrics_df, fixed_events, ladder_events, ladder_curve)

    for _, row in metrics_df.iterrows():
        print(
            f"[133] {row['variant']}: final={_fmt(row['final_equity'])} CAGR={_fmt(row['cagr_pct'])}% "
            f"MDD={_fmt(row['max_drawdown_pct'])}% peakdrop={_fmt(row['post_peak_drop_pct'])}%",
            flush=True,
        )
    print(f"[133] Outputs: {OUT_PNG}, {OUT_CSV}, {OUT_EVENTS_CSV}, {OUT_CURVES_CSV}, {OUT_MD}", flush=True)


if __name__ == "__main__":
    main()
