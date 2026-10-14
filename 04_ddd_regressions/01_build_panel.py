"""
01_build_panel.py
=================
Build the balanced brand x year x type panel for the triple-difference (DDD)
regressions, with FIVE dependent variables.

Source (patent-level, GM-corrected):
    ../02_quality_indicators/data/checkpoints/df_focal_indicators.csv
    columns: appln_id, docdb_family_id, year, brand, tech_type,
             FAMSIZE, BCIT, FCIT, REFNPAT

Aggregation to cell (brand i, year t, type k):
    counts   = number of patents in the cell           (count of appln_id)
    famsize  = sum of FAMSIZE over patents in the cell
    fcit     = sum of FCIT
    bcit     = sum of BCIT
    nptlit   = sum of REFNPAT      (non-patent-literature references)

Panel is balanced: 18 brands x 10 years x 2 types = 360.

type/Dirty coding:
    EV_Hybrid -> type='green', is_dirty=0
    ICE       -> type='dirty', is_dirty=1

Output:
    data/processed/ddd_panel.csv
"""

from pathlib import Path
import pandas as pd
import numpy as np

def _require(path, produced_by):
    if not path.exists():
        raise SystemExit(
            f"Missing input: {path} -- produced by {produced_by}. "
            "See SETUP.md, Part 2: the raw PATSTAT tables are not shipped with this repository."
        )

ROOT      = Path(__file__).resolve().parent
CHECKPOINT = (ROOT / ".." / "02_quality_indicators" / "data" /
              "checkpoints" / "df_focal_indicators.csv").resolve()

_require(CHECKPOINT, "02_quality_indicators/descriptives.ipynb")
OUT_DIR   = ROOT / "data" / "processed"

YEARS   = list(range(2010, 2020))            # 2010-2019; drop 2020-2021 (truncation)
GERMAN  = {"BMW", "Daimler", "Volkswagen Group"}
TYPE_MAP = {"EV_Hybrid": "green", "ICE": "dirty"}

# checkpoint indicator -> panel dep-var name
DEPVAR_SRC = {
    "famsize": "FAMSIZE",
    "fcit":    "FCIT",
    "bcit":    "BCIT",
    "nptlit":  "REFNPAT",
}


def main() -> None:
    print("=" * 65)
    print("Script 01 — Build DDD panel (brand x year x type, 5 dep-vars)")
    print("=" * 65)

    print(f"\n[LOAD] {CHECKPOINT}")
    df = pd.read_csv(CHECKPOINT)
    print(f"  rows={len(df):,}  brands={df['brand'].nunique()}  "
          f"tech_type={df['tech_type'].value_counts().to_dict()}")

    # Restrict to estimation window and known types
    df = df[df["year"].isin(YEARS) & df["tech_type"].isin(TYPE_MAP)].copy()
    df["type"] = df["tech_type"].map(TYPE_MAP)
    print(f"  after window+type filter: rows={len(df):,}  years={sorted(df['year'].unique())}")

    # Aggregate actual observations
    agg = (
        df.groupby(["brand", "year", "type"])
          .agg(
              counts =("appln_id", "count"),
              famsize=("FAMSIZE", "sum"),
              fcit   =("FCIT", "sum"),
              bcit   =("BCIT", "sum"),
              nptlit =("REFNPAT", "sum"),
          )
          .reset_index()
    )

    # Balanced skeleton: all brand x year x type combinations
    all_brands = sorted(df["brand"].unique())
    skel = pd.DataFrame(
        [(b, y, t) for b in all_brands for y in YEARS for t in ("green", "dirty")],
        columns=["brand", "year", "type"],
    )
    panel = skel.merge(agg, on=["brand", "year", "type"], how="left")
    for c in ["counts", "famsize", "fcit", "bcit", "nptlit"]:
        panel[c] = panel[c].fillna(0).astype(int)

    # Treatment / type indicators
    panel["is_german"] = panel["brand"].isin(GERMAN).astype(int)
    panel["is_dirty"]  = (panel["type"] == "dirty").astype(int)

    n_expected = len(all_brands) * len(YEARS) * 2
    assert len(panel) == n_expected, f"got {len(panel)}, expected {n_expected}"
    print(f"\n  Balanced panel: {len(panel)} rows "
          f"({len(all_brands)} brands x {len(YEARS)} years x 2 types)")
    print(f"  German brands : {sorted(GERMAN)}")
    for c in ["counts", "famsize", "fcit", "bcit", "nptlit"]:
        nz = (panel[c] == 0).sum()
        print(f"  {c:<8}: sum={panel[c].sum():>9,}  zero-cells={nz}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "ddd_panel.csv"
    panel.to_csv(out, index=False)
    print(f"\n[SAVE] {out}")
    print("[DONE] Script 01 complete.")


if __name__ == "__main__":
    main()
