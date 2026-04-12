from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent

BASE_47_PATH = ROOT / "47_backtest_btcusdt_scale06_adx002_case1_standalone.py"
BASE_76_PATH = ROOT / "76_backtest_btcusdt_scale06_adx002_regime_hold_leverage_sweep.py"
BASE_111_PATH = ROOT / "111_backtest_btcusdt_sr_smc_5m_profitmax.py"
BASE_114_PATH = ROOT / "114_backtest_btcusdt_best_with_sr_smc_filters.py"
BASE_117_PATH = ROOT / "117_backtest_btcusdt_115_highcagr_push.py"
BASE_126_PATH = ROOT / "126_backtest_btcusdt_case3_long_quality_push.py"

OUT_BASE = "136_backtest_btcusdt_row6_episode_state_analysis"
OUT_PNG = ROOT / f"{OUT_BASE}.png"
OUT_MD = ROOT / f"{OUT_BASE}.md"
OUT_EPISODES_CSV = ROOT / f"{OUT_BASE}.csv"
OUT_COMPARE_CSV = ROOT / f"{OUT_BASE}_compare.csv"
OUT_CURVES_CSV = ROOT / f"{OUT_BASE}_curves.csv"

PRIMARY_VARIANT = "lb4_delay8_capna_cd0"
COMPARE_VARIANTS = ["lb4_delay8_cap2p5_cd0", "lb4_delay0_cap1p5_cd16"]
TOP_DEPTH = 5
TOP_DURATION = 5


def load_module(alias: str, path: Path):
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def _fmt(v: float, digits: int = 4) -> str:
    return "N/A" if pd.isna(v) else f"{float(v):.{digits}f}"


def compute_curve_stats(curve: pd.DataFrame, equity_col: str, initial_capital: float) -> dict:
    series = curve[equity_col].astype(float)
    final_equity = float(series.iloc[-1])
    years = max((curve["timestamp"].iloc[-1] - curve["timestamp"].iloc[0]).total_seconds() / 86400.0 / 365.25, 1e-9)
    cagr_pct = ((final_equity / float(initial_capital)) ** (1.0 / years) - 1.0) * 100.0
    dd = series / series.cummax() - 1.0
    max_drawdown_pct = float(-dd.min() * 100.0)
    calmar_ratio = float(cagr_pct / max_drawdown_pct) if max_drawdown_pct > 0 else np.nan
    return {
        "final_equity": final_equity,
        "total_return_pct": (final_equity / float(initial_capital) - 1.0) * 100.0,
        "cagr_pct": cagr_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "calmar_ratio": calmar_ratio,
    }


def compute_underwater_episodes(curve: pd.DataFrame) -> pd.DataFrame:
    df = curve[["timestamp", "equity"]].copy().sort_values("timestamp").reset_index(drop=True)
    df["dd"] = df["equity"] / df["equity"].cummax() - 1.0
    episodes = []
    peak_idx = 0
    in_dd = False
    start_idx = None
    for i, dd in enumerate(df["dd"].to_numpy(dtype=float)):
        if not in_dd and dd < 0:
            in_dd = True
            start_idx = peak_idx
        if in_dd and dd == 0:
            seg = df.iloc[start_idx : i + 1].copy()
            trough_idx = int(seg["dd"].idxmin())
            episodes.append(
                {
                    "peak_idx": start_idx,
                    "trough_idx": trough_idx,
                    "recovery_idx": i,
                    "peak_time": df.iloc[start_idx]["timestamp"],
                    "trough_time": df.iloc[trough_idx]["timestamp"],
                    "recovery_time": df.iloc[i]["timestamp"],
                    "peak_equity": float(df.iloc[start_idx]["equity"]),
                    "trough_equity": float(df.iloc[trough_idx]["equity"]),
                    "recovery_equity": float(df.iloc[i]["equity"]),
                    "depth_pct": -float(seg["dd"].min() * 100.0),
                    "days_to_trough": (df.iloc[trough_idx]["timestamp"] - df.iloc[start_idx]["timestamp"]).total_seconds() / 86400.0,
                    "days_to_recovery": (df.iloc[i]["timestamp"] - df.iloc[start_idx]["timestamp"]).total_seconds() / 86400.0,
                    "recovered": True,
                }
            )
            in_dd = False
        if dd == 0:
            peak_idx = i
    if in_dd and start_idx is not None:
        seg = df.iloc[start_idx:].copy()
        trough_idx = int(seg["dd"].idxmin())
        end_idx = len(df) - 1
        episodes.append(
            {
                "peak_idx": start_idx,
                "trough_idx": trough_idx,
                "recovery_idx": np.nan,
                "peak_time": df.iloc[start_idx]["timestamp"],
                "trough_time": df.iloc[trough_idx]["timestamp"],
                "recovery_time": pd.NaT,
                "peak_equity": float(df.iloc[start_idx]["equity"]),
                "trough_equity": float(df.iloc[trough_idx]["equity"]),
                "recovery_equity": float(df.iloc[end_idx]["equity"]),
                "depth_pct": -float(seg["dd"].min() * 100.0),
                "days_to_trough": (df.iloc[trough_idx]["timestamp"] - df.iloc[start_idx]["timestamp"]).total_seconds() / 86400.0,
                "days_to_recovery": (df.iloc[end_idx]["timestamp"] - df.iloc[start_idx]["timestamp"]).total_seconds() / 86400.0,
                "recovered": False,
            }
        )
    out = pd.DataFrame(episodes).sort_values("peak_time").reset_index(drop=True)
    out.insert(0, "episode_id", [f"U{i+1}" for i in range(len(out))])
    return out


def classify_episode(seg: pd.DataFrame) -> str:
    price_ret = (float(seg["close"].iloc[-1]) / float(seg["close"].iloc[0]) - 1.0) * 100.0
    long_share = float((seg["side"] > 0).mean() * 100.0)
    short_share = float((seg["side"] < 0).mean() * 100.0)
    flat_share = float((seg["side"] == 0).mean() * 100.0)
    bearish_share = float((seg["trend_4h_confirmed"] == "bearish").mean() * 100.0)
    gate_share = float(seg["short_gate_open"].astype(float).mean() * 100.0)
    side_changes = int((seg["side"].fillna(0).astype(int).diff().fillna(0) != 0).sum())
    if long_share >= 45.0 and price_ret <= -15.0:
        return "급락 초입 롱 잔류"
    if bearish_share >= 60.0 and flat_share >= 35.0 and gate_share <= 8.0:
        return "느린 약세장 숏 기회 부족"
    if side_changes >= 10 and long_share >= 20.0 and short_share >= 20.0:
        return "양방향 휩쏘 누적"
    return "혼합형 추세/휩쏘"


def summarize_episode(episode: pd.Series, merged: pd.DataFrame) -> dict:
    peak_time = pd.Timestamp(episode["peak_time"])
    trough_time = pd.Timestamp(episode["trough_time"])
    recovery_time = pd.Timestamp(episode["recovery_time"]) if pd.notna(episode["recovery_time"]) else pd.Timestamp(merged["timestamp"].max())
    seg_pt = merged[(merged["timestamp"] >= peak_time) & (merged["timestamp"] <= trough_time)].copy()
    seg_full = merged[(merged["timestamp"] >= peak_time) & (merged["timestamp"] <= recovery_time)].copy()
    price_peak = float(seg_pt["close"].iloc[0])
    price_trough = float(seg_pt["close"].iloc[-1])
    price_recovery = float(seg_full["close"].iloc[-1])
    return {
        "btc_peak_to_trough_pct": (price_trough / price_peak - 1.0) * 100.0,
        "btc_peak_to_recovery_pct": (price_recovery / price_peak - 1.0) * 100.0,
        "bullish_4h_share_pct": float((seg_pt["trend_4h_confirmed"] == "bullish").mean() * 100.0),
        "bearish_4h_share_pct": float((seg_pt["trend_4h_confirmed"] == "bearish").mean() * 100.0),
        "long_share_pct": float((seg_pt["side"] > 0).mean() * 100.0),
        "short_share_pct": float((seg_pt["side"] < 0).mean() * 100.0),
        "flat_share_pct": float((seg_pt["side"] == 0).mean() * 100.0),
        "short_gate_open_share_pct": float(seg_pt["short_gate_open"].astype(float).mean() * 100.0),
        "avg_bearish_ob_above_count": float(seg_pt["bearish_ob_above_count"].mean()),
        "avg_bullish_ob_below_count": float(seg_pt["bullish_ob_below_count"].mean()),
        "side_change_count": int((seg_pt["side"].fillna(0).astype(int).diff().fillna(0) != 0).sum()),
        "episode_label": classify_episode(seg_pt),
    }


def align_window_return(curve: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> dict:
    seg = curve[(curve["timestamp"] >= start_ts) & (curve["timestamp"] <= end_ts)].copy()
    start_eq = float(seg["equity"].iloc[0])
    end_eq = float(seg["equity"].iloc[-1])
    dd = seg["equity"].astype(float) / seg["equity"].cummax().astype(float) - 1.0
    return {"window_return_pct": (end_eq / start_eq - 1.0) * 100.0, "window_mdd_pct": -float(dd.min() * 100.0)}


def run_variant_126_state(df: pd.DataFrame, cfg: dict, s76, m117) -> tuple[pd.DataFrame, dict]:
    leverage = float(cfg["leverage"])
    gate_bars = int(cfg["gate_bars"])
    body_atr_mult = float(cfg["body_atr_mult"])
    short_tp_threshold = float(cfg["short_tp_return_pct"]) / 100.0
    max_bearish_above_for_long = int(cfg["max_bearish_above_for_long"])
    long_bullish_delay_bars = int(cfg["long_bullish_delay_bars"])
    long_premium_cap_red_avg_pct = float(cfg["long_premium_cap_red_avg_pct"]) if not pd.isna(cfg["long_premium_cap_red_avg_pct"]) else np.nan
    long_short_sweep_cooldown_bars = int(cfg["long_short_sweep_cooldown_bars"])

    timestamps = df["timestamp"].to_numpy()
    open_np = df["open"].to_numpy(dtype=float)
    high_np = df["high"].to_numpy(dtype=float)
    low_np = df["low"].to_numpy(dtype=float)
    close_np = df["close"].to_numpy(dtype=float)
    atr20 = df["atr20"].to_numpy(dtype=float)
    ema20 = df["ema20"].to_numpy(dtype=float)
    trend = df["trend_4h_confirmed"].astype(str).to_numpy()
    body = df["body"].to_numpy(dtype=float)
    liq_high = df["liq_high_24h_prev"].to_numpy(dtype=float)
    red_avg = df["red_avg"].to_numpy(dtype=float)
    bearish_ob_above_count = df["bearish_ob_above_count"].to_numpy(dtype=int)
    bullish_ob_below_count = df["bullish_ob_below_count"].to_numpy(dtype=int)

    wallet = s76.INITIAL_CAPITAL
    reserve = s76.INITIAL_CAPITAL
    margin = 0.0
    qty = 0.0
    entry = 0.0
    side = 0
    entry_wallet = np.nan
    locked_side = 0
    short_gate_until = -10**9
    prev_trend = None
    bullish_streak = 0
    last_short_sweep_idx = -10**9
    rows: list[dict] = []
    stats = {"trades": 0, "long_entries": 0, "short_entries": 0, "stop_exits": 0, "signal_exits": 0, "tp_exits": 0, "liquidations": 0}

    for i in range(len(df)):
        price_open = float(open_np[i])
        price_high = float(high_np[i])
        price_low = float(low_np[i])
        price_close = float(close_np[i])
        cur_trend = str(trend[i])
        blocked_reentry = False
        bullish_streak = bullish_streak + 1 if cur_trend == "bullish" else 0
        if prev_trend is not None and cur_trend != prev_trend and cur_trend == "bullish":
            short_gate_until = -10**9
        prev_trend = cur_trend

        short_sweep_event = bool(cur_trend == "bearish" and pd.notna(liq_high[i]) and pd.notna(atr20[i]) and body[i] >= atr20[i] * body_atr_mult and price_high > liq_high[i] and price_close < liq_high[i] and price_close < price_open)
        if short_sweep_event:
            short_gate_until = max(short_gate_until, i + gate_bars)
            last_short_sweep_idx = i

        if side != 0:
            liq_price = s76._liq_price(entry, leverage, side)
            stop_price = entry * (1.0 - s76.STOP_PCT) if side > 0 else entry * (1.0 + s76.STOP_PCT)
            if side > 0 and leverage > 1.0 and price_low <= liq_price:
                wallet = max(reserve, 0.0)
                reserve = wallet
                margin = qty = entry = 0.0
                side = 0
                entry_wallet = np.nan
                blocked_reentry = True
                stats["trades"] += 1
                stats["liquidations"] += 1
            elif side < 0 and leverage > 1.0 and price_high >= liq_price:
                wallet = max(reserve, 0.0)
                reserve = wallet
                margin = qty = entry = 0.0
                side = 0
                entry_wallet = np.nan
                blocked_reentry = True
                stats["trades"] += 1
                stats["liquidations"] += 1
            elif side > 0 and price_low <= stop_price:
                wallet = s76._realize_close(reserve, margin, qty, entry, stop_price, side)
                reserve = wallet
                margin = qty = entry = 0.0
                side = 0
                entry_wallet = np.nan
                blocked_reentry = True
                stats["trades"] += 1
                stats["stop_exits"] += 1
            elif side < 0 and price_high >= stop_price:
                wallet = s76._realize_close(reserve, margin, qty, entry, stop_price, side)
                reserve = wallet
                margin = qty = entry = 0.0
                side = 0
                entry_wallet = np.nan
                blocked_reentry = True
                stats["trades"] += 1
                stats["stop_exits"] += 1
            elif side < 0 and entry_wallet > 0:
                marked_wallet = s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
                if marked_wallet / entry_wallet - 1.0 >= short_tp_threshold:
                    wallet = s76._realize_close(reserve, margin, qty, entry, price_close, side)
                    reserve = wallet
                    margin = qty = entry = 0.0
                    locked_side = side
                    side = 0
                    entry_wallet = np.nan
                    stats["trades"] += 1
                    stats["tp_exits"] += 1

        desired_side = 1 if cur_trend == "bullish" else -1
        if locked_side != 0:
            if desired_side == locked_side:
                desired_side = 0
            elif desired_side == -locked_side:
                locked_side = 0

        if not blocked_reentry and side != desired_side:
            if side != 0:
                wallet = s76._realize_close(reserve, margin, qty, entry, price_close, side)
                reserve = wallet
                margin = qty = entry = 0.0
                side = 0
                entry_wallet = np.nan
                stats["trades"] += 1
                stats["signal_exits"] += 1
            if desired_side != 0 and wallet > 0:
                allow_entry = True
                if desired_side < 0:
                    allow_entry = i <= short_gate_until and price_close < ema20[i]
                if allow_entry and desired_side > 0:
                    if int(bearish_ob_above_count[i]) > max_bearish_above_for_long:
                        allow_entry = False
                    elif bullish_streak <= long_bullish_delay_bars:
                        allow_entry = False
                    elif long_short_sweep_cooldown_bars > 0 and (i - last_short_sweep_idx) <= long_short_sweep_cooldown_bars:
                        allow_entry = False
                    elif not pd.isna(long_premium_cap_red_avg_pct) and price_close > red_avg[i] * (1.0 + long_premium_cap_red_avg_pct / 100.0):
                        allow_entry = False
                if allow_entry and not m117.smc_entry_allowed(desired_side, int(bearish_ob_above_count[i]), int(bullish_ob_below_count[i]), 99, 0):
                    allow_entry = False
                if allow_entry:
                    reserve, margin, qty, entry = s76._open_position(wallet, price_close, leverage, desired_side)
                    wallet = reserve + margin
                    side = desired_side
                    entry_wallet = wallet
                    stats["long_entries" if desired_side > 0 else "short_entries"] += 1

        equity = wallet if side == 0 else s76._mark_to_market(reserve, margin, qty, entry, price_close, side)
        rows.append({"timestamp": timestamps[i], "equity": equity, "side": side, "locked_side": locked_side, "short_gate_open": int(i <= short_gate_until), "variant": str(cfg["variant"])})

    if side != 0 and len(df):
        wallet = s76._realize_close(reserve, margin, qty, entry, float(close_np[-1]), side)
        rows[-1]["equity"] = wallet
        rows[-1]["side"] = 0
        stats["trades"] += 1
    return pd.DataFrame(rows), stats


def save_plot(primary_curve: pd.DataFrame, representative_df: pd.DataFrame, compare_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=False, gridspec_kw={"height_ratios": [1.8, 1.2]})
    ax_eq, ax_cmp = axes
    ax_eq.plot(primary_curve["timestamp"], primary_curve["equity"], color="#111111", linewidth=1.0, label=PRIMARY_VARIANT)
    ax_eq.axhline(1000.0, color="#777777", linestyle="--", linewidth=0.9)
    colors = ["#d62728", "#ff7f0e", "#bcbd22", "#17becf", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]
    for i, (_, row) in enumerate(representative_df.iterrows()):
        start = pd.Timestamp(row["peak_time"])
        end = pd.Timestamp(row["recovery_time"]) if pd.notna(row["recovery_time"]) else pd.Timestamp(primary_curve["timestamp"].max())
        ax_eq.axvspan(start, end, color=colors[i % len(colors)], alpha=0.14, label=f"{row['episode_id']} {row['depth_pct']:.1f}%")
    ax_eq.set_title("Study 136: Row6 Equity With Representative Weak Periods")
    ax_eq.set_ylabel("Equity (USDT)")
    ax_eq.grid(True, alpha=0.2)
    ax_eq.legend(loc="upper left", ncol=3)

    pivot = compare_df.pivot(index="episode_id", columns="variant", values="window_return_pct")
    pivot = pivot[[PRIMARY_VARIANT] + [v for v in pivot.columns if v != PRIMARY_VARIANT]]
    width = 0.22
    x = np.arange(len(pivot.index))
    for i, col in enumerate(pivot.columns):
        ax_cmp.bar(x + (i - (len(pivot.columns) - 1) / 2) * width, pivot[col].to_numpy(dtype=float), width=width, label=col)
    ax_cmp.set_xticks(x)
    ax_cmp.set_xticklabels(pivot.index.tolist())
    ax_cmp.set_ylabel("Peak->Trough Return %")
    ax_cmp.set_title("Representative Weak Windows: Variant Loss Comparison")
    ax_cmp.grid(True, axis="y", alpha=0.2)
    ax_cmp.legend(loc="upper left", ncol=2)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    plt.close(fig)


def save_report(overall_df: pd.DataFrame, deepest_df: pd.DataFrame, longest_df: pd.DataFrame, representative_df: pd.DataFrame, compare_df: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> None:
    primary = overall_df[overall_df["variant"] == PRIMARY_VARIANT].iloc[0]
    summary = compare_df.groupby("variant").agg(avg_peak_to_trough_loss_pct=("window_return_pct", "mean"), worst_peak_to_trough_loss_pct=("window_return_pct", "min"), avg_window_mdd_pct=("window_mdd_pct", "mean")).reset_index()
    label_counts = representative_df["episode_label"].value_counts().to_dict()
    lines: list[str] = []
    lines.append("# 136번 연구: row6 약한 구간의 BTC 상태 분석")
    lines.append("")
    lines.append(f"- 대상 전략: `{PRIMARY_VARIANT}`")
    lines.append(f"- 분석 구간: `{start_ts}` ~ `{end_ts}`")
    lines.append(f"- 현재 성적: CAGR `{_fmt(primary['cagr_pct'])}%`, MDD `{_fmt(primary['max_drawdown_pct'])}%`, Calmar `{_fmt(primary['calmar_ratio'])}`")
    lines.append("")
    lines.append("## 깊게 잃은 구간 Top 5")
    lines.append("| Episode | Peak | Trough | Recovery | Depth % | Days To Recovery | BTC Peak->Trough % | Label |")
    lines.append("| --- | --- | --- | --- | ---: | ---: | ---: | --- |")
    for _, row in deepest_df.iterrows():
        recovery_text = row["recovery_time"] if pd.notna(row["recovery_time"]) else "미회복"
        lines.append(f"| {row['episode_id']} | {row['peak_time']} | {row['trough_time']} | {recovery_text} | {_fmt(row['depth_pct'])} | {_fmt(row['days_to_recovery'], 1)} | {_fmt(row['btc_peak_to_trough_pct'])} | {row['episode_label']} |")
    lines.append("")
    lines.append("## 오래 묶인 구간 Top 5")
    lines.append("| Episode | Peak | Trough | Recovery | Depth % | Days To Recovery | Flat % | Gate Open % | Label |")
    lines.append("| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |")
    for _, row in longest_df.iterrows():
        recovery_text = row["recovery_time"] if pd.notna(row["recovery_time"]) else "미회복"
        lines.append(f"| {row['episode_id']} | {row['peak_time']} | {row['trough_time']} | {recovery_text} | {_fmt(row['depth_pct'])} | {_fmt(row['days_to_recovery'], 1)} | {_fmt(row['flat_share_pct'])} | {_fmt(row['short_gate_open_share_pct'])} | {row['episode_label']} |")
    lines.append("")
    lines.append("## 대표 구간 해석")
    for _, row in representative_df.iterrows():
        recovery_text = row["recovery_time"] if pd.notna(row["recovery_time"]) else "미회복"
        lines.append(f"- `{row['episode_id']}` {row['episode_label']}: `{row['peak_time']}` -> `{row['trough_time']}` -> `{recovery_text}` / BTC `{_fmt(row['btc_peak_to_trough_pct'])}%` / long `{_fmt(row['long_share_pct'])}%` short `{_fmt(row['short_share_pct'])}%` flat `{_fmt(row['flat_share_pct'])}%` / bearish4h `{_fmt(row['bearish_4h_share_pct'])}%` / gate `{_fmt(row['short_gate_open_share_pct'])}%` / side changes `{int(row['side_change_count'])}`")
    lines.append("")
    lines.append("## 공통 패턴")
    lines.append(f"- 대표 약한 구간 분류: 급락 초입 롱 잔류 `{int(label_counts.get('급락 초입 롱 잔류', 0))}`회, 느린 약세장 숏 기회 부족 `{int(label_counts.get('느린 약세장 숏 기회 부족', 0))}`회, 양방향 휩쏘 누적 `{int(label_counts.get('양방향 휩쏘 누적', 0))}`회.")
    lines.append("- row6의 약점은 두 갈래로 보인다. 빠른 하락 초입에서 롱을 늦게 접는 문제와, 천천히 미끄러지는 약세장에서 숏을 충분히 못 잡는 문제가 같이 있다.")
    lines.append("- 긴 정체 구간은 bearish 4h 비중이 높은데도 flat 비중이 높고 short gate open 비중이 낮다. 즉 느린 bear trend를 자주 놓친다.")
    lines.append("- 깊은 손실 구간 일부는 long 비중이 높은 상태에서 BTC가 이미 크게 밀렸다. 즉 bullish confirmed 체계가 급락 초입엔 늦게 반응한다.")
    lines.append("")
    lines.append("## 개선 힌트")
    lines.append("- 1. `slow bear continuation short` 경로를 따로 넣는 게 가장 유력하다. 지금 short는 sweep 이벤트 의존도가 높다.")
    lines.append("- 2. bearish 전환 초입 long de-risk를 더 빠르게 해야 한다. delay8만으로는 큰 급락 초입 방어가 부족해 보인다.")
    lines.append("- 3. 3.0x는 약한 구간을 증폭한다. 공격성을 유지하더라도 `3.0x -> 2.5x` 다운시프트가 첫 수정안으로 자연스럽다.")
    lines.append("- 4. premium cap 계열은 추격 롱 완화 후보로 여전히 유효하다.")
    lines.append("")
    lines.append("## 대표 구간 비교")
    lines.append("| Variant | Overall CAGR % | Overall MDD % | Avg Peak->Trough % | Worst Peak->Trough % | Avg Window MDD % |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for _, row in summary.merge(overall_df[["variant", "cagr_pct", "max_drawdown_pct"]], on="variant", how="left").iterrows():
        lines.append(f"| {row['variant']} | {_fmt(row['cagr_pct'])} | {_fmt(row['max_drawdown_pct'])} | {_fmt(row['avg_peak_to_trough_loss_pct'])} | {_fmt(row['worst_peak_to_trough_loss_pct'])} | {_fmt(row['avg_window_mdd_pct'])} |")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- Plot: `{OUT_PNG.name}`")
    lines.append(f"- Episodes CSV: `{OUT_EPISODES_CSV.name}`")
    lines.append(f"- Compare CSV: `{OUT_COMPARE_CSV.name}`")
    lines.append(f"- Curves CSV: `{OUT_CURVES_CSV.name}`")
    lines.append(f"- Report: `{OUT_MD.name}`")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> None:
    m47 = load_module("study47_for_136", BASE_47_PATH)
    s76 = load_module("study76_for_136", BASE_76_PATH)
    m111 = load_module("study111_for_136", BASE_111_PATH)
    m114 = load_module("study114_for_136", BASE_114_PATH)
    m117 = load_module("study117_for_136", BASE_117_PATH)
    m126 = load_module("study126_for_136", BASE_126_PATH)
    df_1m, df_4h, end_ts = m114.load_market_data_2021plus()
    market = m114.prepare_market_114(df_1m, df_4h, m47, m111)
    variants = [PRIMARY_VARIANT] + COMPARE_VARIANTS
    cfgs = {cfg["variant"]: cfg for cfg in m126.build_variants() if cfg["variant"] in variants}

    primary_curve, primary_stats = run_variant_126_state(market, cfgs[PRIMARY_VARIANT], s76, m117)
    primary_curve["timestamp"] = pd.to_datetime(primary_curve["timestamp"])
    curves = {PRIMARY_VARIANT: primary_curve.copy()}
    overall_rows = [{"variant": PRIMARY_VARIANT, **compute_curve_stats(primary_curve, "equity", s76.INITIAL_CAPITAL), **primary_stats}]
    for variant in COMPARE_VARIANTS:
        curve, run_stats = m126.run_variant_126(market, cfgs[variant], s76, m117)
        curve["timestamp"] = pd.to_datetime(curve["timestamp"])
        curves[variant] = curve.copy()
        overall_rows.append({"variant": variant, **compute_curve_stats(curve, "equity", s76.INITIAL_CAPITAL), **run_stats})
    overall_df = pd.DataFrame(overall_rows).sort_values(["calmar_ratio", "cagr_pct"], ascending=[False, False]).reset_index(drop=True)

    merged = pd.merge(primary_curve[["timestamp", "equity", "side", "locked_side", "short_gate_open"]], market[["timestamp", "close", "trend_4h_confirmed", "bearish_ob_above_count", "bullish_ob_below_count"]], on="timestamp", how="left").sort_values("timestamp").reset_index(drop=True)
    episodes_df = compute_underwater_episodes(primary_curve)
    episodes_df = pd.DataFrame([{**row.to_dict(), **summarize_episode(row, merged)} for _, row in episodes_df.iterrows()])
    deepest_df = episodes_df.sort_values(["depth_pct", "days_to_recovery"], ascending=[False, False]).head(TOP_DEPTH).copy()
    longest_df = episodes_df.sort_values(["days_to_recovery", "depth_pct"], ascending=[False, False]).head(TOP_DURATION).copy()
    rep_ids = set(deepest_df["episode_id"]).union(set(longest_df["episode_id"]))
    representative_df = episodes_df[episodes_df["episode_id"].isin(rep_ids)].copy().sort_values("peak_time").reset_index(drop=True)

    compare_rows = []
    for _, episode in representative_df.iterrows():
        for variant in variants:
            compare_rows.append({"episode_id": episode["episode_id"], "variant": variant, **align_window_return(curves[variant], pd.Timestamp(episode["peak_time"]), pd.Timestamp(episode["trough_time"]))})
    compare_df = pd.DataFrame(compare_rows)

    episodes_df.to_csv(OUT_EPISODES_CSV, index=False, encoding="utf-8-sig")
    compare_df.to_csv(OUT_COMPARE_CSV, index=False, encoding="utf-8-sig")
    pd.concat([curves[v].assign(variant=v) for v in variants], ignore_index=True).to_csv(OUT_CURVES_CSV, index=False, encoding="utf-8-sig")
    save_plot(primary_curve, representative_df, compare_df)
    save_report(overall_df, deepest_df, longest_df, representative_df, compare_df, pd.Timestamp(primary_curve["timestamp"].min()), pd.Timestamp(end_ts))
    print(f"saved_plot={OUT_PNG.name}")
    print(f"saved_report={OUT_MD.name}")
    print(f"saved_episodes={OUT_EPISODES_CSV.name}")
    print(representative_df[['episode_id','peak_time','trough_time','days_to_recovery','depth_pct','episode_label']].to_string(index=False))
    print(overall_df[['variant','cagr_pct','max_drawdown_pct','calmar_ratio']].to_string(index=False))


if __name__ == "__main__":
    run()
