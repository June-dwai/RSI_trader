from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_78_PATH = Path("78_backtest_btcusdt_scale06_adx002_regime_hold_side_tp_lock.py")

OUT_BASE = "80_backtest_btcusdt_scale06_adx002_regime_hold_short_tp_tune"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CURVES_CSV = Path(f"{OUT_BASE}_curves.csv")

LEVERAGES = [1.5, 2.0]
TP_RETURN_PCTS = [10.0, 15.0, 20.0, 25.0, 30.0, 40.0]


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


def _fmt_count(v: float) -> str:
    if pd.isna(v):
        return "N/A"
    return str(int(v))


def build_variants() -> list[dict]:
    variants: list[dict] = []
    for leverage in LEVERAGES:
        variants.append(
            {
                "variant": f"base_{leverage:g}x",
                "leverage": float(leverage),
                "tp_return_pct": pd.NA,
                "tp_side": "none",
            }
        )
        for tp_return_pct in TP_RETURN_PCTS:
            variants.append(
                {
                    "variant": f"short_tp{int(tp_return_pct)}_lock_{leverage:g}x",
                    "leverage": float(leverage),
                    "tp_return_pct": float(tp_return_pct),
                    "tp_side": "short",
                }
            )
    return variants


def save_plot(curve_map: dict[str, pd.DataFrame], metrics_df: pd.DataFrame, s78):
    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False, gridspec_kw={"height_ratios": [2.2, 1.0, 1.0]})
    ax_eq, ax_cagr, ax_tp = axes

    cmap = plt.get_cmap("tab20")
    variants = metrics_df["variant"].tolist()
    colors = {v: cmap(i % 20) for i, v in enumerate(variants)}

    for variant in variants:
        curve = curve_map.get(variant)
        if curve is None or curve.empty:
            continue
        ax_eq.plot(curve["timestamp"], curve["equity"], linewidth=1.0, color=colors[variant], label=variant)
    ax_eq.axhline(s78.s76.INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9)
    ax_eq.set_title("80 Study: Short-Only Take-Profit Lock Tuning")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=2)

    ax_cagr.bar(metrics_df["variant"], metrics_df["cagr_pct"], color=[colors[v] for v in variants], alpha=0.85, label="CAGR %")
    ax_cagr.set_ylabel("CAGR %")
    ax_cagr.grid(True, axis="y", alpha=0.2)
    ax_cagr.tick_params(axis="x", rotation=20)
    ax_cagr_t = ax_cagr.twinx()
    ax_cagr_t.plot(metrics_df["variant"], metrics_df["max_drawdown_pct"], color="#d62728", marker="o", linewidth=1.1, label="MDD %")
    ax_cagr_t.set_ylabel("MDD %")
    h1, l1 = ax_cagr.get_legend_handles_labels()
    h2, l2 = ax_cagr_t.get_legend_handles_labels()
    ax_cagr.legend(h1 + h2, l1 + l2, loc="upper left")

    ax_tp.bar(metrics_df["variant"], metrics_df["tp_exits"], color=[colors[v] for v in variants], alpha=0.85, label="TP Exits")
    ax_tp.set_ylabel("TP Exits")
    ax_tp.grid(True, axis="y", alpha=0.2)
    ax_tp.tick_params(axis="x", rotation=20)
    ax_tp_t = ax_tp.twinx()
    ax_tp_t.plot(metrics_df["variant"], metrics_df["calmar_ratio"], color="#9467bd", marker="o", linewidth=1.1, label="Calmar")
    ax_tp_t.set_ylabel("Calmar")
    h1, l1 = ax_tp.get_legend_handles_labels()
    h2, l2 = ax_tp_t.get_legend_handles_labels()
    ax_tp.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(metrics_df: pd.DataFrame):
    base_15 = metrics_df[metrics_df["variant"] == "base_1.5x"].iloc[0]
    base_20 = metrics_df[metrics_df["variant"] == "base_2x"].iloc[0]
    best = metrics_df.iloc[0]

    lines: list[str] = []
    lines.append("# Study 80: Short-Only Take-Profit Lock Tuning")
    lines.append("")
    lines.append("## Model")
    lines.append("- Reuses the study-78 short-only TP-lock logic.")
    lines.append("- After a profitable short reaches the threshold on the current 4h close, the short is closed and re-entry on the short side stays locked until a confirmed bullish flip occurs.")
    lines.append("- Long trades are untouched.")
    lines.append("")
    lines.append("## Ranking")
    lines.append("")
    lines.append("| Variant | Lev | TP % | CAGR % | MDD % | Calmar | Final Equity | TP Exits | Locked Bars |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for _, row in metrics_df.iterrows():
        tp_text = "N/A" if pd.isna(row["tp_return_pct"]) else _fmt(row["tp_return_pct"], 0)
        lines.append(
            f"| {row['variant']} | {_fmt(row['leverage'], 1)} | {tp_text} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | "
            f"{_fmt(row['calmar_ratio'])} | {_fmt(row['final_equity'])} | {_fmt_count(row['tp_exits'])} | {_fmt_count(row['locked_signal_bars'])} |"
        )
    lines.append("")
    lines.append("## Best Variant")
    lines.append(
        f"- `{best['variant']}`: CAGR `{_fmt(best['cagr_pct'])}%`, MDD `{_fmt(best['max_drawdown_pct'])}%`, Calmar `{_fmt(best['calmar_ratio'])}`"
    )
    lines.append("")
    lines.append("## Delta vs Same-Leverage Baseline")
    for _, row in metrics_df.iterrows():
        if row["variant"] in {"base_1.5x", "base_2x"}:
            continue
        base = base_15 if float(row["leverage"]) == 1.5 else base_20
        lines.append(
            f"- `{row['variant']}` vs `{base['variant']}`: CAGR `{_fmt(row['cagr_pct'] - base['cagr_pct'])}pp`, "
            f"MDD `{_fmt(row['max_drawdown_pct'] - base['max_drawdown_pct'])}pp`, Calmar `{_fmt(row['calmar_ratio'] - base['calmar_ratio'])}`, "
            f"TP exits `{_fmt_count(row['tp_exits'])}`"
        )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("- If lower short TP thresholds dominate, short squeezes are a major source of giveback and shorts should be monetized earlier.")
    lines.append("- If higher thresholds dominate, shorts still need room to run and only the biggest winners should be clipped.")
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV}`")
    lines.append(f"- Report: `{OUT_MD}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    market = s78.s76.load_market()
    variants = build_variants()

    rows: list[dict] = []
    curves_out: list[pd.DataFrame] = []
    curve_map: dict[str, pd.DataFrame] = {}

    for cfg in variants:
        curve, run_stats = s78.run_variant(market, cfg, s78.s76)
        stats = s78.s76.compute_curve_stats(curve, "equity", s78.s76.INITIAL_CAPITAL)
        row = {
            "variant": str(cfg["variant"]),
            "leverage": float(cfg["leverage"]),
            "tp_return_pct": cfg["tp_return_pct"],
            **stats,
            **run_stats,
        }
        rows.append(row)
        curves_out.append(curve)
        curve_map[row["variant"]] = curve.copy()

    metrics_df = pd.DataFrame(rows).sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).reset_index(drop=True)
    curves_df = pd.concat(curves_out, ignore_index=True)

    metrics_df.to_csv(OUT_CSV, index=False)
    curves_df.to_csv(OUT_CURVES_CSV, index=False)
    save_plot(curve_map, metrics_df, s78)
    save_report(metrics_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_curves={OUT_CURVES_CSV}")
    print(f"saved_report={OUT_MD}")
    print(metrics_df.to_string(index=False))


s78 = load_module("study78_for_80", BASE_78_PATH)


if __name__ == "__main__":
    run()
