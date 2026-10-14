"""
04_static_ddd.py
================
Static (single-coefficient) triple-difference DDD for all 20 regressions:
5 dep-vars x {PPML, Lin-lin} x 2 Post-window definitions.

Two Post windows (static analogs of the dynamic reference-year choices):
  post2015 : Post = 1[year >= 2015], baseline 2010-2014 
  post2016 : Post = 1[year >= 2016], baseline 2010-2015

Output:
  output/tables/static_ddd.xlsx
    - sheet 'all'      : every model x both windows
    - sheet 'delta'    : delta (triple-diff) only, the headline coefficient
"""

import os
from pathlib import Path
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
PRETREND   = TABLES_DIR / "pretrend_ftest_ddd.xlsx"   # produced by 03 (run first)

# variant label -> (post_start, baseline string, dynamic analog, pretrend ref year)
WINDOWS = {
    "post2015": (2015, "2010-2014", "ref 2014", 2014),
    "post2016": (2016, "2010-2015", "ref 2015", 2015),
}


def load_pretrend() -> dict:
    """Lookup (model, ref_year) -> (F, p) from the dynamic pre-trend F-tests."""
    if not PRETREND.exists():
        print(f"  [warn] {PRETREND.name} not found — run 03 first; "
              f"pre-trend columns will be blank.")
        return {}
    pt = pd.read_excel(PRETREND, sheet_name="pretrend_ftests")
    return {(r["model"], int(r["ref_year"])): (float(r["F_stat"]), float(r["p_value"]))
            for _, r in pt.iterrows()}

TERM_NICE = {"gd_post": "delta: German x Dirty x Post (triple-diff)",
             "g_post":  "beta1: German x Post"}


def main() -> None:
    print("=" * 65)
    print("Script 04 — Static DDD (20 regressions: 5 dep x 2 est x 2 windows)")
    print("=" * 65)

    panel = pd.read_csv(IN_PANEL)
    n_brands = panel["brand"].nunique()
    print(f"  panel rows={len(panel)}  brands(clusters)={n_brands}")
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    pretrend = load_pretrend()

    rows = []
    for win, (post_start, baseline, analog, pt_ref) in WINDOWS.items():
        df = C.add_static(panel, post_start)
        print(f"\n  === {win}  (Post = year >= {post_start}; baseline {baseline}; "
              f"{analog}) ===")
        for est_label, estimator in C.ESTIMATORS:
            for depvar in C.DEPVARS:
                name = f"{est_label}_{depvar}"
                try:
                    model, _ = C.fit_static(depvar, estimator, df)
                    tidy = C.get_tidy(model)
                    n, r2 = C.model_n_r2(model, df)
                except Exception as e:
                    print(f"    {name:<16} !! {e}")
                    continue

                pt_F, pt_p = pretrend.get((name, pt_ref), (np.nan, np.nan))
                if np.isnan(pt_p):
                    pt_verdict = "n/a"
                elif pt_p >= 0.05:
                    pt_verdict = "parallel (no pre-trend)"
                else:
                    pt_verdict = "PRE-TREND (rejected)"

                for term in ("gd_post", "g_post"):
                    if term not in tidy.index:
                        continue
                    r = tidy.loc[term]
                    rows.append({
                        "model"     : name,
                        "estimator" : C.EST_NICE[est_label],
                        "depvar"    : depvar,
                        "window"    : win,
                        "post_start": post_start,
                        "baseline"  : baseline,
                        "coefficient": TERM_NICE[term],
                        "term"      : term,
                        "coef"      : float(r["Estimate"]),
                        "se"        : float(r["Std. Error"]),
                        "ci_lower"  : float(r["2.5%"]),
                        "ci_upper"  : float(r["97.5%"]),
                        "pvalue"    : float(r["pvalue"]),
                        "N"         : n,
                        "pseudo_or_r2": r2,
                        "pretrend_ref_year": pt_ref,
                        "pretrend_F": pt_F,
                        "pretrend_p": pt_p,
                        "parallel_trends": pt_verdict,
                    })
                dlt = tidy.loc["gd_post"]
                print(f"    {name:<16} delta={float(dlt['Estimate']):+.4f}  "
                      f"se={float(dlt['Std. Error']):.4f}  "
                      f"p={float(dlt['pvalue']):.4f}")

    out = pd.DataFrame(rows)
    out_xlsx = TABLES_DIR / "static_ddd.xlsx"
    tmp = out_xlsx.with_suffix(".tmp.xlsx")
    delta_only = out[out["term"] == "gd_post"].drop(columns="term").reset_index(drop=True)
    with pd.ExcelWriter(tmp) as xw:
        out.to_excel(xw, sheet_name="all", index=False)
        delta_only.to_excel(xw, sheet_name="delta", index=False)
    os.replace(tmp, out_xlsx)
    print(f"\n[SAVE] {out_xlsx}")
    print(f"  {len(delta_only)} delta estimates (10 models x 2 windows)")
    print("\n[DONE] Script 04 complete.")


if __name__ == "__main__":
    main()
