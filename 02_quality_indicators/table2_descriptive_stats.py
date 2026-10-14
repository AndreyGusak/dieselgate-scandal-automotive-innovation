"""
Table 2 — Descriptive statistics for the quality indicators (thesis, p.21).

Computes N, mean, median, SD, min, max, Q1, Q3, and the share of zero values
for FAMSIZE, BCIT, FCIT, and REFNPAT, over the 2010-2019 analysis sample.
"""
import pandas as pd
from pathlib import Path

def _require(path, produced_by):
    if not path.exists():
        raise SystemExit(
            f"Missing input: {path} -- produced by {produced_by}. "
            "See SETUP.md, Part 2: the raw PATSTAT tables are not shipped with this repository."
        )

ROOT = Path(__file__).parent
CHECKPOINT = ROOT / "data" / "checkpoints" / "df_focal_indicators.csv"

_require(CHECKPOINT, "02_quality_indicators/descriptives.ipynb")
OUT = ROOT / "output" / "tables" / "table2_descriptive_stats.csv"

YEAR_START, YEAR_END = 2010, 2019
INDICATORS = ["FAMSIZE", "BCIT", "FCIT", "REFNPAT"]


def main():
    df = pd.read_csv(CHECKPOINT)
    df = df[(df["year"] >= YEAR_START) & (df["year"] <= YEAR_END)]

    rows = []
    for col in INDICATORS:
        s = df[col]
        rows.append({
            "indicator": col,
            "N": int(s.count()),
            "mean": round(s.mean(), 2),
            "median": round(s.median(), 1),
            "SD": round(s.std(ddof=1), 2),
            "min": s.min(),
            "max": s.max(),
            "Q1": round(s.quantile(0.25), 1),
            "Q3": round(s.quantile(0.75), 1),
            "share_zeros": round((s == 0).mean(), 2),
        })

    out_df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUT, index=False)
    print(out_df.to_string(index=False))
    print(f"\nWritten to {OUT}")


if __name__ == "__main__":
    main()
