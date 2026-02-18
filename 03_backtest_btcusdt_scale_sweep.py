from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCALES = [0.2, 0.3, 0.4, 0.5]
BASE_SCRIPT_PATH = Path("002_backtest_btcusdt.py")
PLOT_FILE = Path("03_backtest_btcusdt_scales.png")
CSV_FILE = Path("03_backtest_btcusdt_scale_metrics.csv")


def load_base_module(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing base script: {path}")

    spec = importlib.util.spec_from_file_location("bt002", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_backtest(base_module, entry_scale: float):
    bt = base_module.FloorScaledRSIAveragingBacktest(
        symbol=base_module.SYMBOL,
        initial_capital=base_module.INITIAL_CAPITAL,
        commission=base_module.COMMISSION,
        entry_scale=entry_scale,
    )
    bt.rsi_oversold = 18
    bt.rsi_overbought = 85
    bt.take_profit_pct = 0.012
    bt.stop_loss_pct = 0.03
    bt.base_cooldown = 5
    bt.cooldown_time = 5
    return bt


def calculate_metrics(bt, initial_capital: float) -> dict:
    eq = pd.DataFrame(bt.equity_curve)
    tr = pd.DataFrame(bt.trades)

    if eq.empty:
        return {
            "period_start": pd.NaT,
            "period_end": pd.NaT,
            "final_equity": 0.0,
            "total_return_pct": -100.0,
            "cagr_pct": -100.0,
            "max_drawdown_pct": 100.0,
            "calmar_ratio": np.nan,
            "trades": 0,
            "long_trades": 0,
            "short_trades": 0,
            "win_rate_pct": 0.0,
            "long_win_rate_pct": 0.0,
            "short_win_rate_pct": 0.0,
            "profit_factor": np.nan,
            "avg_holding_hours": np.nan,
            "max_exposure_multiple": np.nan,
        }

    eq["timestamp"] = pd.to_datetime(eq["timestamp"])
    start = eq["timestamp"].iloc[0]
    end = eq["timestamp"].iloc[-1]
    final_equity = float(eq["equity"].iloc[-1])
    total_return_pct = (final_equity - initial_capital) / initial_capital * 100.0

    years = max((end - start).days / 365.25, 1e-9)
    cagr_pct = (pow(max(final_equity, 1e-12) / initial_capital, 1 / years) - 1.0) * 100.0

    equity = eq["equity"].astype(float)
    drawdown = (equity - equity.cummax()) / equity.cummax().replace(0, np.nan)
    max_drawdown_pct = float((-drawdown.min()) * 100.0) if len(drawdown) else 0.0
    calmar_ratio = float(cagr_pct / max_drawdown_pct) if max_drawdown_pct > 0 else np.nan

    trades = len(tr)
    if trades > 0:
        tr["entry_time"] = pd.to_datetime(tr["entry_time"])
        tr["exit_time"] = pd.to_datetime(tr["exit_time"])

        long_trades = tr[tr["side"] == "LONG"]
        short_trades = tr[tr["side"] == "SHORT"]
        long_count = int(len(long_trades))
        short_count = int(len(short_trades))

        win_rate = float((tr["pnl"] > 0).mean() * 100.0)
        long_win_rate = float((long_trades["pnl"] > 0).mean() * 100.0) if long_count > 0 else 0.0
        short_win_rate = float((short_trades["pnl"] > 0).mean() * 100.0) if short_count > 0 else 0.0

        gross_profit = float(tr.loc[tr["pnl"] > 0, "pnl"].sum())
        gross_loss = float(tr.loc[tr["pnl"] < 0, "pnl"].sum())
        profit_factor = float(gross_profit / abs(gross_loss)) if gross_loss < 0 else np.inf

        avg_holding_hours = float((tr["exit_time"] - tr["entry_time"]).dt.total_seconds().mean() / 3600.0)
    else:
        long_count = 0
        short_count = 0
        win_rate = 0.0
        long_win_rate = 0.0
        short_win_rate = 0.0
        profit_factor = np.nan
        avg_holding_hours = np.nan

    return {
        "period_start": start,
        "period_end": end,
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "calmar_ratio": calmar_ratio,
        "trades": int(trades),
        "long_trades": long_count,
        "short_trades": short_count,
        "win_rate_pct": win_rate,
        "long_win_rate_pct": long_win_rate,
        "short_win_rate_pct": short_win_rate,
        "profit_factor": profit_factor,
        "avg_holding_hours": avg_holding_hours,
    }


def save_comparison_plot(equity_curves: dict[float, pd.DataFrame], metrics_df: pd.DataFrame, output_file: Path) -> None:
    if not equity_curves:
        return

    fig = plt.figure(figsize=(14, 10))
    grid = fig.add_gridspec(2, 2, height_ratios=[2, 1])
    ax_equity = fig.add_subplot(grid[0, :])
    ax_equity.set_title("003 Scale Sweep Equity Curves (based on 002 model)")
    ax_equity.set_ylabel("Equity (USDT)")

    palette = {
        0.2: "#1f77b4",
        0.3: "#2ca02c",
        0.4: "#ff7f0e",
        0.5: "#d62728",
    }

    for scale in sorted(equity_curves):
        eq_df = equity_curves[scale]
        if eq_df.empty:
            continue
        ax_equity.plot(
            eq_df["timestamp"],
            eq_df["equity"],
            linewidth=1.2,
            label=f"scale={scale:.1f} (max {scale * 5.0:.1f}x)",
            color=palette.get(scale),
        )

    ax_equity.grid(True, alpha=0.2)
    ax_equity.legend(loc="upper left")

    ax_final = fig.add_subplot(grid[1, 0])
    ax_final.set_title("Final Equity by Entry Scale")
    ax_final.bar(
        metrics_df["entry_scale"].astype(str),
        metrics_df["final_equity"],
        color=[palette.get(s) for s in metrics_df["entry_scale"]],
    )
    ax_final.set_xlabel("Entry Scale")
    ax_final.set_ylabel("Final Equity (USDT)")
    ax_final.grid(True, axis="y", alpha=0.2)

    ax_mdd = fig.add_subplot(grid[1, 1])
    ax_mdd.set_title("Max Drawdown by Entry Scale")
    ax_mdd.bar(
        metrics_df["entry_scale"].astype(str),
        metrics_df["max_drawdown_pct"],
        color=[palette.get(s) for s in metrics_df["entry_scale"]],
    )
    ax_mdd.set_xlabel("Entry Scale")
    ax_mdd.set_ylabel("MDD (%)")
    ax_mdd.grid(True, axis="y", alpha=0.2)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()


def run_scale_sweep():
    base = load_base_module(BASE_SCRIPT_PATH)

    df_1m, df_4h = base.load_data()
    df_1m = df_1m[(df_1m.index >= base.BACKTEST_START) & (df_1m.index <= base.BACKTEST_END)].copy()

    rows = []
    equity_curves: dict[float, pd.DataFrame] = {}

    for scale in SCALES:
        bt = create_backtest(base, scale)
        bt.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)

        metrics = calculate_metrics(bt, base.INITIAL_CAPITAL)
        metrics["entry_scale"] = float(scale)
        metrics["max_exposure_multiple"] = float(scale * 5.0)
        rows.append(metrics)

        eq_df = pd.DataFrame(bt.equity_curve)
        if not eq_df.empty:
            eq_df["timestamp"] = pd.to_datetime(eq_df["timestamp"])
            equity_curves[scale] = eq_df[["timestamp", "equity"]].copy()
        else:
            equity_curves[scale] = pd.DataFrame(columns=["timestamp", "equity"])

    metrics_df = pd.DataFrame(rows).sort_values("entry_scale").reset_index(drop=True)
    return metrics_df, equity_curves


def main():
    metrics_df, equity_curves = run_scale_sweep()

    save_comparison_plot(equity_curves, metrics_df, PLOT_FILE)
    metrics_df.to_csv(CSV_FILE, index=False)

    display_cols = [
        "entry_scale",
        "max_exposure_multiple",
        "final_equity",
        "total_return_pct",
        "cagr_pct",
        "max_drawdown_pct",
        "trades",
        "win_rate_pct",
        "profit_factor",
    ]

    print(f"saved_plot={PLOT_FILE}")
    print(f"saved_metrics={CSV_FILE}")
    print(metrics_df[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
