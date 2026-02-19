from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


OUT_ALL = Path("23_backtest_01_22_rankings_all_cases.csv")
OUT_EQ = Path("23_backtest_01_22_rankings_by_equity.csv")
OUT_MDD = Path("23_backtest_01_22_rankings_by_mdd.csv")
OUT_COMBINED = Path("23_backtest_01_22_rankings_by_combined.csv")
OUT_MD = Path("23_backtest_01_22_rankings.md")


def _fmt_money(v):
    if pd.isna(v):
        return "N/A"
    return f"{float(v):,.0f}"


def _fmt_mdd(v):
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.2f}"


def parse_study_num(name: str) -> int | None:
    m = re.match(r"^(\d+)_", name)
    if not m:
        return None
    return int(m.group(1))


def infer_symbol(filename: str) -> str:
    lower = filename.lower()
    if "btcusdt" in lower:
        return "BTCUSDT"
    if "ethusdt" in lower:
        return "ETHUSDT"
    return "MIXED/OTHER"


def pick_case_label(row: pd.Series, fallback: str) -> str:
    if "case_id" in row.index and pd.notna(row["case_id"]):
        return str(row["case_id"])

    keys = [
        "mode",
        "strategy",
        "case",
        "band_label",
        "scale_label",
        "hyst_label",
        "tp_label",
        "sl_label",
        "entry_scale",
        "scale",
        "touch_window",
        "long_sl_enabled",
    ]
    vals: list[str] = []
    for k in keys:
        if k in row.index and pd.notna(row[k]):
            v = row[k]
            if isinstance(v, float):
                vals.append(f"{k}={v:.4g}")
            else:
                vals.append(f"{k}={v}")
    if vals:
        return " ; ".join(vals)
    return fallback


def _escape_md_cell(v) -> str:
    s = str(v)
    s = s.replace("\\", "\\\\")
    s = s.replace("|", "\\|")
    s = s.replace("\n", " ")
    return s


def load_csv_rows() -> list[dict]:
    rows: list[dict] = []
    csv_files = sorted(Path(".").glob("*.csv"))
    for p in csv_files:
        n = parse_study_num(p.name)
        if n is None or n < 3 or n > 22:
            continue
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        if "final_equity" not in df.columns:
            continue

        # Prefer strategy-level MDD where multiple drawdown columns exist.
        if "max_drawdown_pct" in df.columns:
            mdd_col = "max_drawdown_pct"
            mdd_type = "max_drawdown_pct"
        elif "strategy_nav_max_drawdown_pct" in df.columns:
            mdd_col = "strategy_nav_max_drawdown_pct"
            mdd_type = "strategy_nav_max_drawdown_pct"
        elif "account_max_drawdown_pct" in df.columns:
            mdd_col = "account_max_drawdown_pct"
            mdd_type = "account_max_drawdown_pct"
        else:
            # If no MDD-like column exists, skip from ranking.
            continue

        for i, r in df.iterrows():
            fe = pd.to_numeric(r.get("final_equity"), errors="coerce")
            mdd = pd.to_numeric(r.get(mdd_col), errors="coerce")
            if pd.isna(fe) or pd.isna(mdd):
                continue
            case_label = pick_case_label(r, fallback=f"row_{i+1}")
            rows.append(
                {
                    "study": n,
                    "source_file": p.name,
                    "symbol": infer_symbol(p.name),
                    "case": case_label,
                    "final_equity": float(fe),
                    "mdd_pct": float(mdd),
                    "mdd_column": mdd_type,
                }
            )
    return rows


def parse_md_metric(md_path: Path) -> tuple[float | None, float | None]:
    text = md_path.read_text(encoding="utf-8", errors="ignore")

    # Final Equity: captures numbers like 14,968.8275
    fe_match = re.search(r"Final Equity\)\s*\|\s*([0-9,]+\.[0-9]+)\s*USDT", text)
    mdd_match = re.search(r"\|\s*MDD\s*\|\s*([0-9,]+\.[0-9]+)%\s*\|", text)
    if not fe_match or not mdd_match:
        return None, None
    fe = float(fe_match.group(1).replace(",", ""))
    mdd = float(mdd_match.group(1).replace(",", ""))
    return fe, mdd


def load_md_rows() -> list[dict]:
    rows: list[dict] = []
    for name in ["001_backtest_btcusdt.md", "002_backtest_btcusdt.md"]:
        p = Path(name)
        if not p.exists():
            continue
        fe, mdd = parse_md_metric(p)
        if fe is None or mdd is None:
            continue
        study = parse_study_num(name.replace("001_", "1_").replace("002_", "2_"))
        if study is None:
            study = 1 if name.startswith("001") else 2
        rows.append(
            {
                "study": study,
                "source_file": p.name,
                "symbol": infer_symbol(p.name),
                "case": "single_run",
                "final_equity": float(fe),
                "mdd_pct": float(mdd),
                "mdd_column": "md_report_mdd",
            }
        )
    return rows


def rank_all(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["equity_rank"] = out["final_equity"].rank(method="min", ascending=False).astype(int)
    out["mdd_rank"] = out["mdd_pct"].rank(method="min", ascending=True).astype(int)
    out["rank_sum"] = out["equity_rank"] + out["mdd_rank"]
    out["combined_rank"] = out["rank_sum"].rank(method="min", ascending=True).astype(int)
    return out


def write_markdown(df: pd.DataFrame):
    eq_sorted = df.sort_values(["equity_rank", "mdd_rank", "study", "source_file"]).reset_index(drop=True)
    mdd_sorted = df.sort_values(["mdd_rank", "equity_rank", "study", "source_file"]).reset_index(drop=True)
    combo_sorted = df.sort_values(["combined_rank", "rank_sum", "equity_rank", "mdd_rank"]).reset_index(drop=True)

    def table_lines(sub: pd.DataFrame, title: str, topn: int = 30) -> list[str]:
        lines = []
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Rank | Study | Symbol | Source | Case | Final Equity | MDD % | Equity Rank | MDD Rank | Rank Sum | Combined Rank |")
        lines.append("|---:|---:|---|---|---|---:|---:|---:|---:|---:|---:|")
        for i, (_, r) in enumerate(sub.head(topn).iterrows(), start=1):
            case_text = _escape_md_cell(r["case"])
            lines.append(
                f"| {i} | {int(r['study']):02d} | {r['symbol']} | `{r['source_file']}` | `{case_text}` | "
                f"{_fmt_money(r['final_equity'])} | {_fmt_mdd(r['mdd_pct'])} | {int(r['equity_rank'])} | {int(r['mdd_rank'])} | "
                f"{int(r['rank_sum'])} | {int(r['combined_rank'])} |"
            )
        lines.append("")
        return lines

    lines: list[str] = []
    lines.append("# 23 Aggregated Ranking (01~22)")
    lines.append("")
    lines.append("## Notes")
    lines.append(f"- Total cases aggregated: `{len(df)}`")
    lines.append("- Source priority: `03~22` from CSV + `001/002` from MD.")
    lines.append("- MDD column used per case is recorded in `23_backtest_01_22_rankings_all_cases.csv`.")
    lines.append("- Rankings mix BTC/ETH and DCA/non-DCA experiments. Interpret cross-study comparisons carefully.")
    lines.append("")
    lines.extend(table_lines(eq_sorted, "Equity Ranking (Top 30)"))
    lines.extend(table_lines(mdd_sorted, "MDD Ranking (Top 30, lower is better)"))
    lines.extend(table_lines(combo_sorted, "Combined Ranking (Top 30 by Equity Rank + MDD Rank)"))
    lines.append("## Output Files")
    lines.append(f"- all cases: `{OUT_ALL}`")
    lines.append(f"- equity sorted: `{OUT_EQ}`")
    lines.append(f"- mdd sorted: `{OUT_MDD}`")
    lines.append(f"- combined sorted: `{OUT_COMBINED}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    rows = []
    rows.extend(load_md_rows())
    rows.extend(load_csv_rows())
    if not rows:
        raise RuntimeError("No rows found to rank.")

    df = pd.DataFrame(rows)
    df = rank_all(df)

    eq_sorted = df.sort_values(["equity_rank", "mdd_rank", "study", "source_file"]).reset_index(drop=True)
    mdd_sorted = df.sort_values(["mdd_rank", "equity_rank", "study", "source_file"]).reset_index(drop=True)
    combo_sorted = df.sort_values(["combined_rank", "rank_sum", "equity_rank", "mdd_rank"]).reset_index(drop=True)

    df.to_csv(OUT_ALL, index=False)
    eq_sorted.to_csv(OUT_EQ, index=False)
    mdd_sorted.to_csv(OUT_MDD, index=False)
    combo_sorted.to_csv(OUT_COMBINED, index=False)
    write_markdown(df)

    print(f"saved={OUT_ALL}")
    print(f"saved={OUT_EQ}")
    print(f"saved={OUT_MDD}")
    print(f"saved={OUT_COMBINED}")
    print(f"saved={OUT_MD}")
    print(f"rows={len(df)}")
    print("top_equity:")
    print(eq_sorted[["study", "source_file", "case", "final_equity", "mdd_pct", "equity_rank", "mdd_rank", "rank_sum", "combined_rank"]].head(10).to_string(index=False))
    print("top_mdd:")
    print(mdd_sorted[["study", "source_file", "case", "final_equity", "mdd_pct", "equity_rank", "mdd_rank", "rank_sum", "combined_rank"]].head(10).to_string(index=False))
    print("top_combined:")
    print(combo_sorted[["study", "source_file", "case", "final_equity", "mdd_pct", "equity_rank", "mdd_rank", "rank_sum", "combined_rank"]].head(10).to_string(index=False))


if __name__ == "__main__":
    run()
