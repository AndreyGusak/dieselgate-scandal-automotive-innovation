"""
02_run_ddd.py
=============
Estimate the 10 DDD event-study regressions (5 dep-vars x {PPML, Lin-lin}) at
both reference years and produce:

  (1) output/tables/all_coefficients_ddd_ref2014.xlsx
      output/tables/all_coefficients_ddd_ref2015.xlsx

  (2) output/plots/ddd_ref<year>_<PPML|LinLin>_<depvar>.png   (20 files)
        Event-study plot of delta_t with 95% CI; the reference year is pinned
        to 0.

Reference years: 2014, 2015

"""

import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

import ddd_common as C
from utils_plot import COLOR_COEF, COLOR_CI, FIGSIZE, DPI, FONT_FAMILY

plt.rcParams["font.family"] = FONT_FAMILY

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
PLOTS_DIR  = ROOT / "output" / "plots"

REF_YEARS = [2015, 2014]   # main baseline 2015; 2014 = clean pre-treatment ref


def _label(term: str) -> tuple:
    """(family, year_or_sortkey, pretty label)."""
    if term == "Intercept":
        return ("level", -3, "Intercept")
    if term == "is_dirty":
        return ("level", -2, "Dirty (level)")
    if term == "gd_const":
        return ("level", -1, "German x Dirty (level)")
    if term.startswith("gd_"):
        yr = int(term[3:]); return ("delta (triple-diff)", yr, f"German x Dirty x {yr}")
    if term.startswith("g_"):
        yr = int(term[2:]); return ("beta1 (German x year)", yr, f"German x {yr}")
    if term.startswith("d_"):
        yr = int(term[2:]); return ("beta2 (Dirty x year)", yr, f"Dirty x {yr}")
    return ("other", 99, term)


def build_coef_table(tidy: pd.DataFrame, n: int, r2: float) -> pd.DataFrame:
    rows = []
    for term, r in tidy.iterrows():
        fam, srt, lab = _label(str(term))
        rows.append(dict(
            family=fam, label=lab, term=str(term),
            coef=float(r["Estimate"]), se=float(r["Std. Error"]),
            ci_lower=float(r["2.5%"]), ci_upper=float(r["97.5%"]),
            pvalue=float(r["pvalue"]), _sort=(0 if fam == "level" else
                       {"beta1 (German x year)": 1, "beta2 (Dirty x year)": 2,
                        "delta (triple-diff)": 3}.get(fam, 4), srt),
        ))
    out = pd.DataFrame(rows).sort_values("_sort").drop(columns="_sort").reset_index(drop=True)
    out["N"] = n
    out["pseudo_or_r2"] = r2
    return out


def delta_series(tidy: pd.DataFrame, ref_year: int) -> pd.DataFrame:
    """delta_t for every year, reference year pinned to 0."""
    rows = []
    for yr in C.YEARS:
        if yr == ref_year:
            rows.append(dict(year=yr, coef=0.0, ci_lo=0.0, ci_hi=0.0, is_ref=True))
        else:
            t = f"gd_{yr}"
            if t in tidy.index:
                rows.append(dict(year=yr, coef=float(tidy.loc[t, "Estimate"]),
                                 ci_lo=float(tidy.loc[t, "2.5%"]),
                                 ci_hi=float(tidy.loc[t, "97.5%"]), is_ref=False))
            else:
                rows.append(dict(year=yr, coef=np.nan, ci_lo=np.nan,
                                 ci_hi=np.nan, is_ref=False))
    return pd.DataFrame(rows)


def plot_delta(ds: pd.DataFrame, est_label: str, depvar: str, out_dir: Path,
               ref_year: int) -> None:
    d = ds[ds["coef"].notna()].sort_values("year")
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.fill_between(d["year"], d["ci_lo"], d["ci_hi"],
                    color=COLOR_CI, alpha=0.5, label="95% CI")
    ax.plot(d["year"], d["coef"], color=COLOR_COEF, marker="o",
            linewidth=2, label=r"$\hat{\delta}_t$")
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.axvline(x=ref_year, color="red", linestyle="--", linewidth=1.5,
               label=f"Reference year ({ref_year}, pinned 0)")
    ax.set_xlabel("Year")
    ax.set_ylabel(r"$\hat{\delta}_t$  (triple-difference)")
    ax.set_xticks(C.YEARS)
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%d"))
    ax.legend(framealpha=0.9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    path = out_dir / f"ddd_ref{ref_year}_{est_label}_{depvar}.png"
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print(f"    -> {path.name}")


def run_ref_year(panel: pd.DataFrame, ref_year: int) -> None:
    print("\n" + "=" * 65)
    print(f"  Reference (omitted-baseline) year = {ref_year}")
    print("=" * 65)

    df, ev_years, g_cols, d_cols, gd_cols = C.add_interactions(panel, ref_year)

    per_model = {}
    all_rows  = []

    for est_label, estimator in C.ESTIMATORS:
        for depvar in C.DEPVARS:
            name = f"{est_label}_{depvar}"
            print(f"\n  [{name}]  ({C.EST_NICE[est_label]}, {C.DEPVAR_NICE[depvar]})")
            try:
                model, fml = C.fit(depvar, estimator, df, g_cols, d_cols, gd_cols)
            except Exception as e:
                print(f"    !! fit failed: {e}")
                continue
            tidy = C.get_tidy(model)
            n, r2 = C.model_n_r2(model, df)
            print(f"    N={n}  fit={r2:.4f}  coefs={len(tidy)}")

            ctab = build_coef_table(tidy, n, r2)
            per_model[name] = ctab

            tagged = ctab.copy()
            tagged.insert(0, "model", name)
            tagged.insert(1, "estimator", C.EST_NICE[est_label])
            tagged.insert(2, "depvar", depvar)
            all_rows.append(tagged)

            plot_delta(delta_series(tidy, ref_year), est_label, depvar,
                       PLOTS_DIR, ref_year)

    # ── Save coefficient workbook ──────────────────────────────────────────────
    out_xlsx = TABLES_DIR / f"all_coefficients_ddd_ref{ref_year}.xlsx"
    tmp = out_xlsx.with_suffix(".tmp.xlsx")
    combined = pd.concat(all_rows, ignore_index=True)
    with pd.ExcelWriter(tmp) as xw:
        combined.to_excel(xw, sheet_name="all_models", index=False)
        for name, tab in per_model.items():
            tab.to_excel(xw, sheet_name=name[:31], index=False)
    os.replace(tmp, out_xlsx)
    print(f"\n[SAVE] {out_xlsx}  ({len(per_model)} model sheets + all_models)")


def main() -> None:
    print("=" * 65)
    print(f"Script 02 — DDD regressions (10 models x ref years {REF_YEARS})")
    print("=" * 65)

    panel = pd.read_csv(IN_PANEL)
    n_brands = panel["brand"].nunique()
    print(f"  panel rows={len(panel)}  brands={n_brands}")

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    for ref_year in REF_YEARS:
        run_ref_year(panel, ref_year)

    print("\n[DONE] Script 02 complete.")


if __name__ == "__main__":
    main()
