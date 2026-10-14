"""
03_pretrend_ftest.py
====================
Pre-trend joint-significance F-tests on the DDD triple-difference coefficients
delta_t, for all 10 models (5 dep-vars x {PPML, Lin-lin}), at BOTH reference
years:

  ref 2015 -> H0: delta_2010 = delta_2011 = delta_2012 = delta_2013 = delta_2014 = 0
  ref 2014 -> H0: delta_2010 = delta_2011 = delta_2012 = delta_2013          = 0

The F-test is a joint-zero Wald test on the delta_t (term gd_<year>), SE clustered by brand
(18 clusters).

Output (single workbook, all models x both ref years):
  output/tables/pretrend_ftest_ddd.xlsx
"""

from pathlib import Path
import os
import numpy as np
import pandas as pd

import ddd_common as C

def _require(path, produced_by):
    if not path.exists():
        raise SystemExit(
            f"Missing input: {path} -- produced by {produced_by}. "
            "See SETUP.md, Part 2: the raw PATSTAT tables are not shipped with this repository."
        )

ROOT       = Path(__file__).resolve().parent
IN_PANEL   = ROOT / "data" / "processed" / "ddd_panel.csv"

_require(IN_PANEL, "01_build_panel.py")
TABLES_DIR = ROOT / "output" / "tables"

# reference year -> (pre-period years tested, human H0 string)
REF_SPECS = {
    2015: ([2010, 2011, 2012, 2013, 2014],
           "delta_2010 = delta_2011 = delta_2012 = delta_2013 = delta_2014 = 0"),
    2014: ([2010, 2011, 2012, 2013],
           "delta_2010 = delta_2011 = delta_2012 = delta_2013 = 0"),
}


def main() -> None:
    print("=" * 65)
    print("Script 03 — DDD pre-trend F-tests (delta_t jointly zero)")
    print("=" * 65)

    panel = pd.read_csv(IN_PANEL)
    n_brands = panel["brand"].nunique()
    print(f"  panel rows={len(panel)}  brands(clusters)={n_brands}")

    rows = []
    for ref_year, (pre_years, h0) in REF_SPECS.items():
        print(f"\n  === reference year {ref_year}  |  H0: {h0} ===")
        df, ev_years, g_cols, d_cols, gd_cols = C.add_interactions(panel, ref_year)
        test_cols = [f"gd_{yr}" for yr in pre_years]

        for est_label, estimator in C.ESTIMATORS:
            for depvar in C.DEPVARS:
                name = f"{est_label}_{depvar}"
                try:
                    model, _ = C.fit(depvar, estimator, df, g_cols, d_cols, gd_cols)
                    tidy = C.get_tidy(model)
                    ft = C.wald_zero(model, tidy, test_cols, n_brands)
                    n, r2 = C.model_n_r2(model, df)
                except Exception as e:
                    print(f"    {name:<16} !! {e}")
                    ft = dict(statistic=np.nan, df1=np.nan, df2=n_brands - 1,
                              pvalue=np.nan, k_tested=0)
                    n, r2 = np.nan, np.nan

                print(f"    {name:<16} F={ft['statistic']:.4f}  "
                      f"df1={ft['df1']} df2={ft['df2']}  p={ft['pvalue']:.4f}")

                rows.append({
                    "model"      : name,
                    "estimator"  : C.EST_NICE[est_label],
                    "depvar"     : depvar,
                    "ref_year"   : ref_year,
                    "H0"         : h0,
                    "pre_years"  : ", ".join(str(y) for y in pre_years),
                    "k_restrict" : ft["k_tested"],
                    "F_stat"     : ft["statistic"],
                    "df1"        : ft["df1"],
                    "df2"        : ft["df2"],
                    "p_value"    : ft["pvalue"],
                    "N"          : n,
                    "pseudo_or_r2": r2,
                })

    out = pd.DataFrame(rows).sort_values(["ref_year", "model"]).reset_index(drop=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out_xlsx = TABLES_DIR / "pretrend_ftest_ddd.xlsx"
    tmp = out_xlsx.with_suffix(".tmp.xlsx")
    with pd.ExcelWriter(tmp) as xw:
        out.to_excel(xw, sheet_name="pretrend_ftests", index=False)
        out[out["ref_year"] == 2015].to_excel(xw, sheet_name="ref2015", index=False)
        out[out["ref_year"] == 2014].to_excel(xw, sheet_name="ref2014", index=False)
    os.replace(tmp, out_xlsx)
    print(f"\n[SAVE] {out_xlsx}")
    print(out.to_string(index=False))
    print("\n[DONE] Script 03 complete.")


if __name__ == "__main__":
    main()
