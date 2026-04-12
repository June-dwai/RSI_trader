from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT_CSV = ROOT / "134_meta_best_strategies_review.csv"
OUT_MD = ROOT / "134_meta_best_strategies_review.md"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def pick_row(path: str, variant: str | None = None) -> dict[str, str]:
    rows = read_csv_rows(ROOT / path)
    if variant is None:
        if len(rows) != 1:
            raise ValueError(f"{path} has {len(rows)} rows; variant must be specified.")
        return rows[0]
    for row in rows:
        if row.get("variant") == variant:
            return row
    raise KeyError(f"Variant {variant!r} not found in {path}.")


def pick_float(row: dict[str, str], *keys: str) -> float:
    for key in keys:
        value = row.get(key, "")
        if value != "":
            return float(value)
    raise KeyError(f"None of {keys!r} found in row: {row}")


def fmt(value: float) -> str:
    return f"{value:.4f}"


def main() -> None:
    entries = [
        {
            "bucket": "BTC 포트폴리오 진화",
            "study": "118",
            "label": "첫 case3 확대형 포트폴리오 승자",
            "asset": "BTCUSDT",
            "window": "2022-01-01 08:00:00 ~ 2026-02-12 00:00:00",
            "variant": "lv3p0_g12_body25_tp20_lb5_none_case3_w52_28_20",
            "source_csv": "118_backtest_btcusdt_case123_portfolio_with_117_case3.csv",
            "why": "case3를 약 20%까지 키우는 게 유효하다는 첫 명확한 신호였다.",
            "verdict": "역사적 전환점",
        },
        {
            "bucket": "BTC 포트폴리오 진화",
            "study": "119",
            "label": "BTC 2022+ 저MDD 완성형",
            "asset": "BTCUSDT",
            "window": "2022-01-01 08:00:00 ~ 2026-02-12 00:00:00",
            "variant": "lv3p0_g12_body25_tp20_lb5_none_case3_rb1h_w49_27_24",
            "source_csv": "119_backtest_btcusdt_case123_portfolio_fine_tune_around_118.csv",
            "why": "1시간 리밸런스와 49/27/24 비중이 2022+ 구간에서 가장 안정적으로 잘 맞았다.",
            "verdict": "BTC 2022+ 밸런스 우승",
        },
        {
            "bucket": "BTC 포트폴리오 진화",
            "study": "120",
            "label": "BTC 2022+ 공격형 포트폴리오",
            "asset": "BTCUSDT",
            "window": "2022-01-01 08:00:00 ~ 2026-02-12 00:00:00",
            "variant": "lv3p0_g12_body25_tp20_lb5_none_case3_rb30min_w46_24_30",
            "source_csv": "120_backtest_btcusdt_case123_fine_tune_rebalance_and_weights.csv",
            "why": "30분 리밸런스로 CAGR과 Calmar를 더 끌어올렸지만 운영 복잡도가 크게 늘었다.",
            "verdict": "BTC 2022+ 고성능, 고운영비",
        },
        {
            "bucket": "BTC 2021+ 단독/혼합 비교",
            "study": "121",
            "label": "2021+에서 case3 우위 재확인",
            "asset": "BTCUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-03-15 05:15:00",
            "variant": "case3_only",
            "source_csv": "121_backtest_btcusdt_solo_vs_current_mix_2021plus.csv",
            "why": "2021을 포함하니 기존 current mix보다 case3 단독 알파가 더 선명하게 드러났다.",
            "verdict": "2021+ raw 우세 확인",
        },
        {
            "bucket": "BTC 2021+ 실전형",
            "study": "122",
            "label": "BTC 실전형 최고",
            "asset": "BTCUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-03-15 05:30:00",
            "variant": "weekly_due_allflat_w0_55_45",
            "source_csv": "122_backtest_btcusdt_practical_rebalance_weight_sweep_2021plus.csv",
            "why": "거의 리밸런스를 하지 않으면서도 case2/case3 55/45가 수익과 낙폭의 균형이 가장 좋았다.",
            "verdict": "BTC 실전형 1순위",
        },
        {
            "bucket": "BTC case3 엔진",
            "study": "126",
            "label": "BTC raw CAGR 최고 case3",
            "asset": "BTCUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-03-15 05:30:00",
            "variant": "lb4_delay8_capna_cd0",
            "source_csv": "126_backtest_btcusdt_case3_long_quality_push.csv",
            "why": "127과 122의 상위 결과를 만든 핵심 엔진으로, 절대 CAGR 자체는 최근 BTC 연구 중 가장 강했다.",
            "verdict": "BTC raw 엔진 우승",
        },
        {
            "bucket": "BTC case3 엔진",
            "study": "127",
            "label": "BTC case2+case3 완충 혼합",
            "asset": "BTCUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-03-15 05:30:00",
            "variant": "case2_case3best_half_mix",
            "source_csv": "127_backtest_btcusdt_case2_vs_case3best_mix.csv",
            "why": "raw case3보다 CAGR은 조금 낮지만 낙폭을 줄여서 Calmar는 오히려 더 좋아졌다.",
            "verdict": "BTC 공격형 혼합 우승",
        },
        {
            "bucket": "ETH raw / salvage",
            "study": "129",
            "label": "ETH raw case3 red line",
            "asset": "ETHUSDT",
            "window": "2021-01-02 00:00:00 ~ 2026-04-12 03:15:00",
            "variant": "lb4_delay9_capna_cd0_only",
            "source_csv": "129_backtest_ethusdt_case2_vs_case3best_mix.csv",
            "why": "ETH에서도 알파 중심은 case3였지만, 수익을 계속 재투입해 peak-to-trough가 지나치게 커졌다.",
            "verdict": "연구용 엔진, 실전은 비추천",
        },
        {
            "bucket": "ETH raw / salvage",
            "study": "131",
            "label": "ETH case2 생존형",
            "asset": "ETHUSDT",
            "window": "2021-01-01 00:00:00 ~ 2026-04-12 08:20:00",
            "variant": "lev12_tp2x_sl2x",
            "source_csv": "131_backtest_ethusdt_case2_lev12_wide_tpsl.csv",
            "why": "case2를 최대 1.2배 노출과 2배 TP/SL로 눌러서 처음으로 끝까지 살려낸 버전이다.",
            "verdict": "참고용 salvage, 주력은 아님",
        },
        {
            "bucket": "ETH 리스크 관리",
            "study": "132",
            "label": "ETH 보수형 실전 후보",
            "asset": "ETHUSDT",
            "window": "129 raw curve overlay, base window 2021-01-02 00:00:00 ~ 2026-04-12 03:15:00",
            "variant": "seed_vault_overlay",
            "source_csv": "132_backtest_ethusdt_case3_seed_vault_overlay.csv",
            "why": "수익 일부를 금고로 빼는 단순 규칙만으로 raw red line의 파괴적 drawdown을 크게 줄였다.",
            "verdict": "ETH 안정형 1순위",
        },
        {
            "bucket": "ETH 리스크 관리",
            "study": "133",
            "label": "ETH 공격형 실전 후보",
            "asset": "ETHUSDT",
            "window": "129 raw curve overlay, base window 2021-01-02 00:00:00 ~ 2026-04-12 03:15:00",
            "variant": "multiplier_ladder_overlay",
            "source_csv": "133_backtest_ethusdt_case3_seed_ladder_overlay.csv",
            "why": "배수 래더 출금으로 raw red line의 업사이드를 더 보존하면서도 낙폭을 일부 제어했다.",
            "verdict": "ETH 공격형 1순위",
        },
    ]

    summary_rows: list[dict[str, str]] = []
    for entry in entries:
        row = pick_row(entry["source_csv"], entry["variant"])
        summary_rows.append(
            {
                "bucket": entry["bucket"],
                "study": entry["study"],
                "label": entry["label"],
                "verdict": entry["verdict"],
                "asset": entry["asset"],
                "window": entry["window"],
                "variant": entry["variant"],
                "source_csv": entry["source_csv"],
                "final_equity": fmt(pick_float(row, "final_equity")),
                "cagr_pct": fmt(pick_float(row, "cagr_pct", "total_cagr_pct")),
                "mdd_pct": fmt(pick_float(row, "max_drawdown_pct", "total_mdd_pct")),
                "calmar": fmt(pick_float(row, "calmar_ratio", "total_calmar_ratio")),
                "return_2026_pct": (
                    fmt(pick_float(row, "return_2026_pct"))
                    if row.get("return_2026_pct", "") != ""
                    else ""
                ),
                "why": entry["why"],
            }
        )

    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "bucket",
                "study",
                "label",
                "verdict",
                "asset",
                "window",
                "variant",
                "source_csv",
                "final_equity",
                "cagr_pct",
                "mdd_pct",
                "calmar",
                "return_2026_pct",
                "why",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    by_study = {row["study"]: row for row in summary_rows}

    lines: list[str] = []
    lines.append("# 134번 연구: 최근 MD 전체 흐름을 다시 훑은 최고 전략 정리")
    lines.append("")
    lines.append("## 범위와 비교 기준")
    lines.append("- 이번 메타 리뷰는 현재 운용 후보로 이어지는 후기 연구를 중심으로 다시 읽었다. 핵심 축은 `118~133`이고, 보조 해석으로 `123`, `124`를 반영했다.")
    lines.append("- 초기 `00~117`번대는 구조 탐색 비중이 커서 직접 우승 후보를 다시 뽑기보다는, 이후 실제로 살아남은 계보를 우선 정리했다.")
    lines.append("- 기간이 다르면 숫자를 그대로 일대일 비교하면 안 된다.")
    lines.append("  - BTC 포트폴리오 진화축 `118~120`: `2022-01-01 08:00:00` ~ `2026-02-12 00:00:00`")
    lines.append("  - BTC 실전 비교축 `121~127`: `2021-01-02 00:00:00` ~ `2026-03-15 05:30:00` 전후")
    lines.append("  - ETH 축 `129~133`: `2021-01-02 00:00:00` ~ `2026-04-12 03:15:00` 전후")
    lines.append("")
    lines.append("## 한 줄 결론")
    lines.append(f"- BTC에서 raw 엔진 최고는 study 126/127의 `{by_study['126']['variant']}`였다. CAGR `{by_study['126']['cagr_pct']}%`, MDD `{by_study['126']['mdd_pct']}%`, Calmar `{by_study['126']['calmar']}`.")
    lines.append(f"- BTC에서 실제 운용형 최고는 study 122의 `{by_study['122']['variant']}`였다. CAGR `{by_study['122']['cagr_pct']}%`, MDD `{by_study['122']['mdd_pct']}%`, Calmar `{by_study['122']['calmar']}`.")
    lines.append(f"- BTC 2022+ 구간에서 가장 예쁘게 다듬어진 저MDD 포트폴리오는 study 119의 `{by_study['119']['variant']}`였다. CAGR `{by_study['119']['cagr_pct']}%`, MDD `{by_study['119']['mdd_pct']}%`, Calmar `{by_study['119']['calmar']}`.")
    lines.append(f"- ETH에서 알파 엔진은 여전히 study 129의 raw case3였지만, 그대로 쓰면 MDD가 `{by_study['129']['mdd_pct']}%`까지 벌어진다.")
    lines.append(f"- ETH 실전형은 보수적으로는 study 132 `{by_study['132']['variant']}` , 공격적으로는 study 133 `{by_study['133']['variant']}`가 가장 납득 가능했다.")
    lines.append("")
    lines.append("## 최고 전략 표")
    lines.append("| Bucket | Study | Label | Variant | CAGR % | MDD % | Calmar | Verdict |")
    lines.append("| --- | ---: | --- | --- | ---: | ---: | ---: | --- |")
    for row in summary_rows:
        lines.append(
            f"| {row['bucket']} | {row['study']} | {row['label']} | `{row['variant']}` | "
            f"{row['cagr_pct']} | {row['mdd_pct']} | {row['calmar']} | {row['verdict']} |"
        )
    lines.append("")
    lines.append("## 흐름 해석")
    lines.append(f"- study 118은 `case3를 20%대까지 키워도 된다`는 첫 증거였다. 승자 `{by_study['118']['variant']}`가 CAGR `{by_study['118']['cagr_pct']}%` / MDD `{by_study['118']['mdd_pct']}%` / Calmar `{by_study['118']['calmar']}`를 만들었다.")
    lines.append(f"- study 119는 이 흐름을 `1시간 리밸런스`로 정리해 `49/27/24`를 현재형 포트폴리오로 굳혔다. 2022+ 기준 가장 낮은 MDD 축에 속하면서도 Calmar가 `{by_study['119']['calmar']}`까지 올라갔다.")
    lines.append(f"- study 120은 `30분 리밸런스 + case3 30%`까지 밀어붙여 CAGR `{by_study['120']['cagr_pct']}%`, Calmar `{by_study['120']['calmar']}`를 만들었다. 다만 리밸런스 횟수가 매우 많아 실전 단순성은 떨어진다.")
    lines.append(f"- study 121과 122에서 `2021`을 포함해 보니, case1 비중이 큰 구형 포트폴리오보다 `case2/case3` 중심 구성이 더 강했다. 그 정리본이 `{by_study['122']['variant']}`다.")
    lines.append(f"- study 126과 127은 BTC 알파의 중심이 사실상 case3라는 점을 확인했다. raw는 `{by_study['126']['cagr_pct']}%` CAGR까지 갔고, 반면 50:50 혼합은 `{by_study['127']['cagr_pct']}%` CAGR / `{by_study['127']['mdd_pct']}%` MDD로 완충 효과를 보여줬다.")
    lines.append(f"- study 123과 124의 해석도 중요하다. BTC case3 drawdown의 주원인은 미세한 타이밍보다 `3.0x 레버리지 자체`에 더 가까웠고, 2026 손실도 `빠른 역행 + 시그널 뒤집힘`에서 나왔다.")
    lines.append(f"- ETH에 이걸 옮긴 study 129에서는 case3가 여전히 엔진이었지만, CAGR `{by_study['129']['cagr_pct']}%` 대비 MDD가 `{by_study['129']['mdd_pct']}%`로 너무 크다. 여기서는 `청산`보다 `수익 재복리 후 대규모 반환`이 문제였다.")
    lines.append(f"- ETH case2를 억지로 살리려 한 130은 대부분 실패했고, study 131의 `{by_study['131']['variant']}`가 최대 1.2배 노출과 넓은 TP/SL로 겨우 생존한 수준이었다. CAGR `{by_study['131']['cagr_pct']}%`라 주력 채택감은 약하다.")
    lines.append(f"- ETH 실전형 해법은 엔진 수정이 아니라 `자금관리 오버레이`에서 나왔다. study 132는 MDD를 `{by_study['129']['mdd_pct']}% -> {by_study['132']['mdd_pct']}%`로 크게 줄였고, study 133은 CAGR을 `{by_study['133']['cagr_pct']}%`까지 올리면서도 raw보단 훨씬 나은 형태로 만들었다.")
    lines.append("")
    lines.append("## 카테고리별 최종 판단")
    lines.append(f"- BTC 순수 수익 극대화: study 126 `{by_study['126']['variant']}`. 숫자는 가장 세지만, drawdown을 견딜 수 있어야 한다.")
    lines.append(f"- BTC 공격형 타협안: study 127 `{by_study['127']['variant']}`. raw case3보다 CAGR을 조금 내주고 MDD와 2026 손실을 줄인다.")
    lines.append(f"- BTC 실전형 기본안: study 122 `{by_study['122']['variant']}`. 이유는 `운영 단순성`, `2021 포함`, `Calmar 균형` 세 가지가 동시에 좋기 때문이다.")
    lines.append(f"- BTC 2022+ 저MDD 포트폴리오: study 119 `{by_study['119']['variant']}`. 다만 이건 기간이 `2022-01-01` 시작이라 2021+ 연구와 직접 우열 비교는 조심해야 한다.")
    lines.append(f"- ETH 보수형: study 132 `{by_study['132']['variant']}`. CAGR `{by_study['132']['cagr_pct']}%` / MDD `{by_study['132']['mdd_pct']}%` / Calmar `{by_study['132']['calmar']}`로 가장 실전적이다.")
    lines.append(f"- ETH 공격형: study 133 `{by_study['133']['variant']}`. CAGR `{by_study['133']['cagr_pct']}%`로 ETH 계열 중 업사이드가 가장 매력적이지만, MDD `{by_study['133']['mdd_pct']}%`는 여전히 크다.")
    lines.append(f"- ETH raw 엔진 참고용: study 129 `{by_study['129']['variant']}`. 엔진 연구에는 가치가 있지만 그대로 쓰기엔 너무 거칠다.")
    lines.append("")
    lines.append("## 내가 지금 고른다면")
    lines.append(f"1. BTC를 실제로 굴린다면 1순위는 study 122 `{by_study['122']['variant']}`다.")
    lines.append(f"2. BTC에서 연구용 최고 엔진을 계속 밀고 싶다면 study 126 raw case3와 study 127 half-mix를 같이 본다.")
    lines.append(f"3. ETH는 case2를 주력으로 보기보다 case3 엔진 위에 오버레이를 얹는 방향이 맞다. 안정형은 study 132, 공격형은 study 133이다.")
    lines.append(f"4. study 129 raw red line과 study 130 계열 case2 변형은 그대로 실전 배치하기엔 메리트가 약하다.")
    lines.append("")
    lines.append("## 산출물")
    lines.append("- Summary CSV: `134_meta_best_strategies_review.csv`")
    lines.append("- Report: `134_meta_best_strategies_review.md`")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_CSV.name}")
    print(f"Wrote {OUT_MD.name}")


if __name__ == "__main__":
    main()
