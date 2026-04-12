from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT_BASE = "143_meta_method_lines_review"
OUT_CSV = ROOT / f"{OUT_BASE}.csv"
OUT_MD = ROOT / f"{OUT_BASE}.md"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def pick_row(path: str, key: str, value: str) -> dict[str, str]:
    rows = read_csv_rows(ROOT / path)
    for row in rows:
        if row.get(key) == value:
            return row
    raise KeyError(f"{value!r} not found by {key!r} in {path}")


def pick_float(row: dict[str, str], *keys: str) -> float:
    for key in keys:
        value = row.get(key, "")
        if value != "":
            return float(value)
    raise KeyError(f"None of {keys!r} found in row: {row}")


def fmt(value: float) -> str:
    return f"{value:.4f}"


def opt_fmt(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key, "")
        if value != "":
            return fmt(float(value))
    return ""


def main() -> None:
    r119 = pick_row("119_backtest_btcusdt_case123_portfolio_fine_tune_around_118.csv", "variant", "lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w49_27_24")
    r120 = pick_row("120_backtest_btcusdt_case123_fine_tune_rebalance_and_weights.csv", "variant", "lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_24_30")
    r122 = pick_row("122_backtest_btcusdt_practical_rebalance_weight_sweep_2021plus.csv", "variant", "weekly_due_allflat_w0_55_45")
    r126 = pick_row("126_backtest_btcusdt_case3_long_quality_push.csv", "variant", "lb4_delay8_capna_cd0")
    r127 = pick_row("127_backtest_btcusdt_case2_vs_case3best_mix.csv", "variant", "case2_case3best_half_mix")
    r129 = pick_row("129_backtest_ethusdt_case2_vs_case3best_mix.csv", "variant", "lb4_delay9_capna_cd0_only")
    r130 = pick_row("130_backtest_ethusdt_case2_bearish_escape_variants.csv", "variant", "short_rsi80_reverse_nogate_stopfix_trim80")
    r131 = pick_row("131_backtest_ethusdt_case2_lev12_wide_tpsl.csv", "variant", "lev12_tp2x_sl2x")
    r132 = pick_row("132_backtest_ethusdt_case3_seed_vault_overlay.csv", "variant", "seed_vault_overlay")
    r133 = pick_row("133_backtest_ethusdt_case3_seed_ladder_overlay.csv", "variant", "multiplier_ladder_overlay")
    r135_row3 = pick_row("135_backtest_btcusdt_row3_vs_row6_same_window.csv", "label", "row3_study120_portfolio")
    r135_row6 = pick_row("135_backtest_btcusdt_row3_vs_row6_same_window.csv", "label", "row6_study126_case3")
    r1351_row3 = pick_row("135_1_backtest_btcusdt_row3_vs_row6_2021plus.csv", "label", "row3_2021plus_study120_mix")
    r1351_row6 = pick_row("135_1_backtest_btcusdt_row3_vs_row6_2021plus.csv", "label", "row6_2021plus_study126_case3")
    r137_base = pick_row("137_backtest_btcusdt_row6_improvement_trials.csv", "variant", "baseline_row6")
    r137_slow = pick_row("137_backtest_btcusdt_row6_improvement_trials.csv", "variant", "slowbear_short_24h_ob4")
    r137_prebear = pick_row("137_backtest_btcusdt_row6_improvement_trials.csv", "variant", "prebear_exit_ob5_cool4h")
    r138_unlock = pick_row("138_backtest_btcusdt_row6_refined_fix_trials.csv", "variant", "unlock_slowbear_24h_2p0")
    r138_combo = pick_row("138_backtest_btcusdt_row6_refined_fix_trials.csv", "variant", "combo_trim2p0_unlock24h")
    r139_eth = pick_row("139_backtest_row6_best_btc_eth_same_window.csv", "symbol", "ETHUSDT")
    r140_unlock = pick_row("140_backtest_btcusdt_row6_bestpair_episode_analysis_variant_summary.csv", "variant", "unlock_slowbear_24h_2p0")
    r140_combo = pick_row("140_backtest_btcusdt_row6_bestpair_episode_analysis_variant_summary.csv", "variant", "combo_trim2p0_unlock24h")
    r141_base = pick_row("141_backtest_btcusdt_row6_whipsaw_guard_trials.csv", "variant", "combo_base")
    r141_choplev = pick_row("141_backtest_btcusdt_row6_whipsaw_guard_trials.csv", "variant", "combo_choplev2_x6")
    r142_best = pick_row("142_backtest_btcusdt_row6_posttrim_releverage_trials.csv", "variant", "combo_posttrim_same_regime_2p0")
    r142_base_2022 = pick_row("142_backtest_btcusdt_row6_posttrim_releverage_trials_2022plus_metrics.csv", "variant", "combo_base")
    r142_best_2022 = pick_row("142_backtest_btcusdt_row6_posttrim_releverage_trials_2022plus_metrics.csv", "variant", "combo_posttrim_same_regime_2p0")

    summary_rows = [
        {
            "section": "BTC core candidates",
            "study": "119",
            "label": "BTC 2022+ 저MDD 포트폴리오",
            "asset": "BTCUSDT",
            "window": "2022-01-01 08:00:00 ~ 2026-02-12 00:00:00",
            "variant": "lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w49_27_24",
            "source_csv": "119_backtest_btcusdt_case123_portfolio_fine_tune_around_118.csv",
            "cagr_pct": fmt(pick_float(r119, "total_cagr_pct", "cagr_pct")),
            "mdd_pct": fmt(pick_float(r119, "total_mdd_pct", "max_drawdown_pct")),
            "calmar": fmt(pick_float(r119, "total_calmar_ratio", "calmar_ratio")),
            "return_2026_pct": opt_fmt(r119, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "BTC 2022+ 저MDD 1순위",
            "note": "1시간 리밸런스 49/27/24. 2022+ 기준 균형이 가장 좋았던 포트폴리오 라인.",
        },
        {
            "section": "BTC core candidates",
            "study": "120",
            "label": "BTC 2022+ 공격형 포트폴리오",
            "asset": "BTCUSDT",
            "window": "2022-01-01 08:00:00 ~ 2026-02-12 00:00:00",
            "variant": "lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_24_30",
            "source_csv": "120_backtest_btcusdt_case123_fine_tune_rebalance_and_weights.csv",
            "cagr_pct": fmt(pick_float(r120, "total_cagr_pct", "cagr_pct")),
            "mdd_pct": fmt(pick_float(r120, "total_mdd_pct", "max_drawdown_pct")),
            "calmar": fmt(pick_float(r120, "total_calmar_ratio", "calmar_ratio")),
            "return_2026_pct": opt_fmt(r120, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "BTC 2022+ 공격형 포트폴리오",
            "note": "30분 리밸런스로 CAGR과 Calmar를 더 끌어올렸지만 운영 복잡도가 큼.",
        },
        {
            "section": "BTC core candidates",
            "study": "122",
            "label": "BTC 단순 실전형",
            "asset": "BTCUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-03-15 05:30:00",
            "variant": "weekly_due_allflat_w0_55_45",
            "source_csv": "122_backtest_btcusdt_practical_rebalance_weight_sweep_2021plus.csv",
            "cagr_pct": fmt(pick_float(r122, "cagr_pct", "total_cagr_pct")),
            "mdd_pct": fmt(pick_float(r122, "max_drawdown_pct", "total_mdd_pct")),
            "calmar": fmt(pick_float(r122, "calmar_ratio", "total_calmar_ratio")),
            "return_2026_pct": opt_fmt(r122, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "BTC 단순 배치 1순위",
            "note": "리밸런스 거의 없이 case2/case3 55/45로 가는 실전형 기본안.",
        },
        {
            "section": "BTC core candidates",
            "study": "126",
            "label": "BTC raw case3 엔진",
            "asset": "BTCUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-03-15 05:30:00",
            "variant": "lb4_delay8_capna_cd0",
            "source_csv": "126_backtest_btcusdt_case3_long_quality_push.csv",
            "cagr_pct": fmt(pick_float(r126, "cagr_pct")),
            "mdd_pct": fmt(pick_float(r126, "max_drawdown_pct")),
            "calmar": fmt(pick_float(r126, "calmar_ratio")),
            "return_2026_pct": opt_fmt(r126, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "BTC raw 엔진 기준점",
            "note": "이후 135~142 개선 연구의 출발점이 된 row6 원형.",
        },
        {
            "section": "BTC core candidates",
            "study": "127",
            "label": "BTC case2+case3 절충안",
            "asset": "BTCUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-03-15 05:30:00",
            "variant": "case2_case3best_half_mix",
            "source_csv": "127_backtest_btcusdt_case2_vs_case3best_mix.csv",
            "cagr_pct": fmt(pick_float(r127, "cagr_pct")),
            "mdd_pct": fmt(pick_float(r127, "max_drawdown_pct")),
            "calmar": fmt(pick_float(r127, "calmar_ratio")),
            "return_2026_pct": opt_fmt(r127, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "BTC 공격형 절충안",
            "note": "raw case3보다 MDD와 최근 성과를 완화한 50:50 혼합.",
        },
        {
            "section": "BTC refined engine",
            "study": "138",
            "label": "BTC 최고 엔진형",
            "asset": "BTCUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-03-15 05:19:00",
            "variant": "unlock_slowbear_24h_2p0",
            "source_csv": "138_backtest_btcusdt_row6_refined_fix_trials.csv",
            "cagr_pct": fmt(pick_float(r138_unlock, "cagr_pct")),
            "mdd_pct": fmt(pick_float(r138_unlock, "max_drawdown_pct")),
            "calmar": fmt(pick_float(r138_unlock, "calmar_ratio")),
            "return_2026_pct": opt_fmt(r138_unlock, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "BTC 최고 CAGR 엔진",
            "note": "slow bear continuation short를 다시 열어주는 수정이 실제로 먹힌 사례.",
        },
        {
            "section": "BTC refined engine",
            "study": "138",
            "label": "BTC 실전형 개선 엔진",
            "asset": "BTCUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-03-15 05:19:00",
            "variant": "combo_trim2p0_unlock24h",
            "source_csv": "138_backtest_btcusdt_row6_refined_fix_trials.csv",
            "cagr_pct": fmt(pick_float(r138_combo, "cagr_pct")),
            "mdd_pct": fmt(pick_float(r138_combo, "max_drawdown_pct")),
            "calmar": fmt(pick_float(r138_combo, "calmar_ratio")),
            "return_2026_pct": opt_fmt(r138_combo, "return_2026_pct"),
            "cagr_2022plus_pct": fmt(pick_float(r142_base_2022, "cagr_2022plus_pct")),
            "verdict": "BTC 현 시점 실전형 알파 1순위",
            "note": "bulltrim을 더해 same-state 손실 깊이를 줄였고, 2026도 플러스로 뒤집은 버전.",
        },
        {
            "section": "BTC rejected / limited",
            "study": "141",
            "label": "Generic chop guard",
            "asset": "BTCUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-03-15 05:19:00",
            "variant": "combo_choplev2_x6",
            "source_csv": "141_backtest_btcusdt_row6_whipsaw_guard_trials.csv",
            "cagr_pct": fmt(pick_float(r141_choplev, "cagr_pct")),
            "mdd_pct": fmt(pick_float(r141_choplev, "max_drawdown_pct")),
            "calmar": fmt(pick_float(r141_choplev, "calmar_ratio")),
            "return_2026_pct": opt_fmt(r141_choplev, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "부분 효과, 비용 큼",
            "note": "whipsaw 평균 손실은 조금 줄였지만 CAGR 희생이 커서 주력안으로 채택하기 어려움.",
        },
        {
            "section": "BTC rejected / limited",
            "study": "142",
            "label": "Post-bulltrim 재레버리지 제한",
            "asset": "BTCUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-03-15 05:19:00",
            "variant": "combo_posttrim_same_regime_2p0",
            "source_csv": "142_backtest_btcusdt_row6_posttrim_releverage_trials.csv",
            "cagr_pct": fmt(pick_float(r142_best, "cagr_pct")),
            "mdd_pct": fmt(pick_float(r142_best, "max_drawdown_pct")),
            "calmar": fmt(pick_float(r142_best, "calmar_ratio")),
            "return_2026_pct": opt_fmt(r142_best, "return_2026_pct"),
            "cagr_2022plus_pct": fmt(pick_float(r142_best_2022, "cagr_2022plus_pct")),
            "verdict": "숫자 개선은 있으나 구조 효과 미미",
            "note": "posttrim capped long이 3회뿐이라 whipsaw 구조를 못 건드렸음. 2021 효과를 빼면 CAGR은 111%대.",
        },
        {
            "section": "ETH candidates",
            "study": "129",
            "label": "ETH raw case3 red line",
            "asset": "ETHUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-04-12 03:15:00",
            "variant": "lb4_delay9_capna_cd0_only",
            "source_csv": "129_backtest_ethusdt_case2_vs_case3best_mix.csv",
            "cagr_pct": fmt(pick_float(r129, "cagr_pct")),
            "mdd_pct": fmt(pick_float(r129, "max_drawdown_pct")),
            "calmar": fmt(pick_float(r129, "calmar_ratio")),
            "return_2026_pct": opt_fmt(r129, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "엔진 연구용, 실전 배치 부적합",
            "note": "ETH에서도 알파는 있었지만 drawdown이 너무 커서 원형 그대로는 배치 불가.",
        },
        {
            "section": "ETH rejected / limited",
            "study": "130",
            "label": "ETH case2 bearish escape 변형",
            "asset": "ETHUSDT",
            "window": "2021-01-01 00:00:00 ~ 2026-04-12 05:30:00",
            "variant": "short_rsi80_reverse_nogate_stopfix_trim80",
            "source_csv": "130_backtest_ethusdt_case2_bearish_escape_variants.csv",
            "cagr_pct": fmt(pick_float(r130, "cagr_pct")),
            "mdd_pct": fmt(pick_float(r130, "max_drawdown_pct")),
            "calmar": fmt(pick_float(r130, "calmar_ratio")),
            "return_2026_pct": opt_fmt(r130, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "실패 라인",
            "note": "RSI 완화, reverse 허용, stopfix, trim까지 넣어도 구조적 회생에 실패.",
        },
        {
            "section": "ETH rejected / limited",
            "study": "131",
            "label": "ETH case2 저레버 salvage",
            "asset": "ETHUSDT",
            "window": "2021-01-01 00:00:00 ~ 2026-04-12 08:20:00",
            "variant": "lev12_tp2x_sl2x",
            "source_csv": "131_backtest_ethusdt_case2_lev12_wide_tpsl.csv",
            "cagr_pct": fmt(pick_float(r131, "cagr_pct")),
            "mdd_pct": fmt(pick_float(r131, "max_drawdown_pct")),
            "calmar": fmt(pick_float(r131, "calmar_ratio")),
            "return_2026_pct": opt_fmt(r131, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "생존형 참고안",
            "note": "case2를 1.2배 노출로 낮추고 TP/SL을 넓혀 겨우 끝까지 생존시킨 버전.",
        },
        {
            "section": "ETH candidates",
            "study": "132",
            "label": "ETH 보수형 오버레이",
            "asset": "ETHUSDT",
            "window": "129 raw curve overlay",
            "variant": "seed_vault_overlay",
            "source_csv": "132_backtest_ethusdt_case3_seed_vault_overlay.csv",
            "cagr_pct": fmt(pick_float(r132, "cagr_pct")),
            "mdd_pct": fmt(pick_float(r132, "max_drawdown_pct")),
            "calmar": fmt(pick_float(r132, "calmar_ratio")),
            "return_2026_pct": opt_fmt(r132, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "ETH 보수형 1순위",
            "note": "엔진 수정이 아니라 자금관리 오버레이로 raw red line을 실전형으로 변환한 대표 사례.",
        },
        {
            "section": "ETH candidates",
            "study": "133",
            "label": "ETH 공격형 오버레이",
            "asset": "ETHUSDT",
            "window": "129 raw curve overlay",
            "variant": "multiplier_ladder_overlay",
            "source_csv": "133_backtest_ethusdt_case3_seed_ladder_overlay.csv",
            "cagr_pct": fmt(pick_float(r133, "cagr_pct")),
            "mdd_pct": fmt(pick_float(r133, "max_drawdown_pct")),
            "calmar": fmt(pick_float(r133, "calmar_ratio")),
            "return_2026_pct": opt_fmt(r133, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "ETH 공격형 1순위",
            "note": "배수 래더 출금으로 업사이드는 유지하면서 raw red line보다 훨씬 다룰 만한 형태로 정리.",
        },
        {
            "section": "ETH rejected / limited",
            "study": "139",
            "label": "BTC 개선안의 ETH 이식",
            "asset": "ETHUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-03-15 05:30:00",
            "variant": "combo_trim2p0_unlock24h",
            "source_csv": "139_backtest_row6_best_btc_eth_same_window.csv",
            "cagr_pct": fmt(pick_float(r139_eth, "cagr_pct")),
            "mdd_pct": fmt(pick_float(r139_eth, "max_drawdown_pct")),
            "calmar": fmt(pick_float(r139_eth, "calmar_ratio")),
            "return_2026_pct": opt_fmt(r139_eth, "return_2026_pct"),
            "cagr_2022plus_pct": "",
            "verdict": "BTC 전용 개선으로 판정",
            "note": "BTC에서는 먹힌 138 combo가 ETH에서는 거의 재현되지 않음을 확인한 이식 실패 사례.",
        },
    ]

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "section",
                "study",
                "label",
                "asset",
                "window",
                "variant",
                "source_csv",
                "cagr_pct",
                "mdd_pct",
                "calmar",
                "return_2026_pct",
                "cagr_2022plus_pct",
                "verdict",
                "note",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    lines: list[str] = []
    lines.append("# 143번 연구: 134 메타 정리 최신판")
    lines.append("")
    lines.append("## 목적")
    lines.append("- 134에서 정리했던 method/전략 표를 135~142까지 확장해서 다시 묶는다.")
    lines.append("- 이번 버전은 `좋았던 전략`만이 아니라 `실패한 개선 line`도 같이 남겨서, 지금 어디까지 유효했고 어디서 막혔는지 한 번에 보이게 하는 데 목적이 있다.")
    lines.append("")
    lines.append("## 비교 시 주의")
    lines.append("- 기간이 다르면 숫자를 그대로 일대일 비교하면 안 된다.")
    lines.append("- 특히 row6 계열은 `2021`이 CAGR을 크게 끌어올린다. 142에서 same-family 전략을 `2022-01-01`부터 다시 보면 CAGR이 `109% ~ 114%` 수준으로 내려온다.")
    lines.append("- 따라서 `2021 포함 CAGR`은 최대 잠재력, `2022+`는 지금 시장 기준의 실전 체감이라고 보는 게 맞다.")
    lines.append("")
    lines.append("## 현재 살아남은 핵심 후보")
    lines.append("| Bucket | Study | Label | Variant | CAGR % | MDD % | Calmar | 2026 % | 2022+ CAGR % | Verdict |")
    lines.append("| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for row in summary_rows:
        if row["section"] in {"BTC core candidates", "BTC refined engine", "ETH candidates"}:
            lines.append(
                f"| {row['section']} | {row['study']} | {row['label']} | `{row['variant']}` | "
                f"{row['cagr_pct']} | {row['mdd_pct']} | {row['calmar']} | "
                f"{row['return_2026_pct'] or ''} | {row['cagr_2022plus_pct'] or ''} | {row['verdict']} |"
            )
    lines.append("")
    lines.append("## 134 이후 추가된 핵심 method line 요약")
    lines.append(
        f"- `135`: 같은 2022+ 구간으로 row3와 row6를 붙여보면 row6가 CAGR `{fmt(pick_float(r135_row6, 'cagr_pct'))}%`로 row3 `{fmt(pick_float(r135_row3, 'cagr_pct'))}%`보다 강했다. "
        f"대신 MDD는 row6 `{fmt(pick_float(r135_row6, 'max_drawdown_pct'))}%`, row3 `{fmt(pick_float(r135_row3, 'max_drawdown_pct'))}%`라 row3가 더 얕았다."
    )
    lines.append(
        f"- `135_1`: 2021+로 창을 늘리면 row6 CAGR이 `{fmt(pick_float(r1351_row6, 'cagr_pct'))}%`, row3는 `{fmt(pick_float(r1351_row3, 'cagr_pct'))}%`가 되어 격차가 더 벌어진다. "
        f"즉 row6는 엔진, row3는 완충형 성격이 더 뚜렷해졌다."
    )
    lines.append("- `136`: baseline row6의 대표 약점이 `급락 초입 롱 잔류`, `느린 약세장에서 숏 기회 부족`, `양방향 whipsaw`라는 점을 구조적으로 확인했다.")
    lines.append(
        f"- `137`: 첫 개선 시도는 대부분 실패했다. slow bear short 24h는 CAGR을 `{fmt(pick_float(r137_base, 'cagr_pct'))}% -> {fmt(pick_float(r137_slow, 'cagr_pct'))}%`로 아주 약간 올렸지만 실질적 구조 개선은 약했고, "
        f"pre-bear exit는 CAGR이 `{fmt(pick_float(r137_prebear, 'cagr_pct'))}%`까지 무너져 과필터링이었다."
    )
    lines.append(
        f"- `138`: 진짜 개선은 여기서 나왔다. baseline `{fmt(pick_float(r137_base, 'cagr_pct'))}% / {fmt(pick_float(r137_base, 'max_drawdown_pct'))}%`에서 "
        f"`unlock_slowbear_24h_2p0`는 `{fmt(pick_float(r138_unlock, 'cagr_pct'))}% / {fmt(pick_float(r138_unlock, 'max_drawdown_pct'))}%`, "
        f"`combo_trim2p0_unlock24h`는 `{fmt(pick_float(r138_combo, 'cagr_pct'))}% / {fmt(pick_float(r138_combo, 'max_drawdown_pct'))}%`가 나왔다."
    )
    lines.append(
        f"- `139`: 138 combo를 ETH에 같은 구간으로 옮기면 CAGR `{fmt(pick_float(r139_eth, 'cagr_pct'))}%`, MDD `{fmt(pick_float(r139_eth, 'max_drawdown_pct'))}%`에 그쳤다. "
        "즉 이 개선 line은 BTC 전용 성격이 강하다."
    )
    lines.append(
        f"- `140`: 138의 best 2개를 다시 뜯어보니 남은 병목은 `slow_bear_short_gap`보다 `two_way_whipsaw`였다. "
        f"대표 약한 구간 평균 depth가 `unlock`은 `{fmt(pick_float(r140_unlock, 'avg_rep_depth_pct'))}%`, `combo`는 `{fmt(pick_float(r140_combo, 'avg_rep_depth_pct'))}%`로 줄었다."
    )
    lines.append(
        f"- `141`: generic chop filter는 거의 실패했다. 가장 나았던 `combo_choplev2_x6`도 whipsaw 평균 손실을 "
        f"`{fmt(pick_float(r141_base, 'whipsaw_avg_return_pct'))}% -> {fmt(pick_float(r141_choplev, 'whipsaw_avg_return_pct'))}%`로만 줄였고, "
        f"CAGR은 `{fmt(pick_float(r141_choplev, 'cagr_pct'))}%`로 크게 내려갔다."
    )
    lines.append(
        f"- `142`: bulltrim 이후 재레버리지 제한은 숫자는 약간 좋아 보여도 구조 효과가 거의 없었다. best 수치가 `{fmt(pick_float(r142_best, 'cagr_pct'))}% / {fmt(pick_float(r142_best, 'max_drawdown_pct'))}%`였지만 "
        f"`posttrim capped long`이 3회뿐이었고, 2022+ CAGR도 `{fmt(pick_float(r142_best_2022, 'cagr_2022plus_pct'))}%`였다."
    )
    lines.append("")
    lines.append("## 현재 해석")
    lines.append("- BTC는 이제 크게 세 줄기로 정리된다.")
    lines.append("  1. 단순 실전 포트폴리오 줄기: `122`")
    lines.append("  2. raw case3 / 공격형 절충 줄기: `126`, `127`")
    lines.append("  3. row6 개선 엔진 줄기: `138`, `140`, `141`, `142`")
    lines.append("- 이 중 현재 가장 의미 있는 신규 성과는 `138`이다. `137`까지의 미세 수정과 달리, `unlock short lock + slow bear continuation short + bulltrim` 조합은 숫자와 상태 분석 양쪽에서 개선 흔적이 분명하다.")
    lines.append("- 반대로 `141`, `142`는 다음 길을 알려준 연구다. generic chop filter나 posttrim re-entry cap은 핵심 병목을 못 찔렀다. 즉 다음 개선은 `재진입 제한`보다 `open long 관리` 쪽으로 가야 한다.")
    lines.append("- ETH는 여전히 `엔진 개선`보다 `오버레이`가 더 유효하다. 현재까지는 `132`, `133`이 `129 raw`보다 실전성이 훨씬 높다.")
    lines.append("")
    lines.append("## 최종 판정")
    lines.append(f"- BTC 최고 엔진: `138 / {r138_unlock['variant']}`. CAGR `{fmt(pick_float(r138_unlock, 'cagr_pct'))}%`, MDD `{fmt(pick_float(r138_unlock, 'max_drawdown_pct'))}%`.")
    lines.append(f"- BTC 현 시점 실전형 알파: `138 / {r138_combo['variant']}`. CAGR `{fmt(pick_float(r138_combo, 'cagr_pct'))}%`, MDD `{fmt(pick_float(r138_combo, 'max_drawdown_pct'))}%`, 2026 `{opt_fmt(r138_combo, 'return_2026_pct')}%`.")
    lines.append(f"- BTC 단순 배치형: `122 / {r122['variant']}`. CAGR `{fmt(pick_float(r122, 'cagr_pct'))}%`, MDD `{fmt(pick_float(r122, 'max_drawdown_pct'))}%`.")
    lines.append(f"- BTC 2022+ 저MDD 포트폴리오: `119 / {r119['variant']}`. CAGR `{fmt(pick_float(r119, 'total_cagr_pct'))}%`, MDD `{fmt(pick_float(r119, 'total_mdd_pct'))}%`.")
    lines.append(f"- ETH 보수형: `132 / {r132['variant']}`. CAGR `{fmt(pick_float(r132, 'cagr_pct'))}%`, MDD `{fmt(pick_float(r132, 'max_drawdown_pct'))}%`.")
    lines.append(f"- ETH 공격형: `133 / {r133['variant']}`. CAGR `{fmt(pick_float(r133, 'cagr_pct'))}%`, MDD `{fmt(pick_float(r133, 'max_drawdown_pct'))}%`.")
    lines.append("- 보류 또는 탈락 라인: `129 raw ETH case3`, `130 ETH case2 bearish escape`, `139 BTC->ETH 이식`, `141 generic chop guard`, `142 posttrim re-leverage`.")
    lines.append("")
    lines.append("## 산출물")
    lines.append(f"- Summary CSV: `{OUT_CSV.name}`")
    lines.append(f"- Report: `{OUT_MD.name}`")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
