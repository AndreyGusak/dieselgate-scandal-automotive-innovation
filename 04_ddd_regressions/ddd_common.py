"""
ddd_common.py
=============
Shared design-builder, estimator wrapper, and Wald-test helpers for the
triple-difference (DDD) event-study regressions.

Model (saturated FE structure — brand x type and year x type fixed effects):

  Lin-lin (OLS, feols):
    y_itk = alpha_ik + gamma_tk
            + sum_{t != ref} [ b1_t (German_i x D_t)
                             + delta_t (German_i x Dirty_k x D_t) ] + e

  PPML (fepois): same linear index inside exp{.}.

  alpha_ik : brand x type FE  (entered via | brand^type)
             absorbs German_i, Dirty_k, German_i x Dirty_k, and each brand's
             own green/dirty level gap.
  gamma_tk : year  x type FE  (entered via | year^type)
             absorbs the Dirty_k x D_t (b2_t) family.
  SE       : clustered by brand, 18 clusters.

Because alpha_ik / gamma_tk absorb the constant level terms and the Dirty x year
family, only b1_t (German x year) and delta_t (German x Dirty x year) remain.
delta_t (term gd_<year>) is the dynamic coefficient of interest.
"""

import warnings
import numpy as np
import pandas as pd
from scipy import stats

YEARS   = list(range(2010, 2020))
DEPVARS = ["counts", "famsize", "fcit", "bcit", "nptlit"]
# (label, pyfixest estimator)
ESTIMATORS = [("PPML", "fepois"), ("LinLin", "feols")]

DEPVAR_NICE = {
    "counts":  "patent counts",
    "famsize": "family size (sum)",
    "fcit":    "forward citations (sum)",
    "bcit":    "backward citations (sum)",
    "nptlit":  "NPL citations (sum)",
}
EST_NICE = {"PPML": "PPML (Poisson)", "LinLin": "Lin-lin (OLS levels)"}


def add_interactions(panel: pd.DataFrame, ref_year: int):
    """Add the constant level terms and the dynamic interaction dummies for a
    given reference (omitted-baseline) year. Returns (df, event_years,
    g_cols, d_cols, gd_cols)."""
    df = panel.copy()
    event_years = [y for y in YEARS if y != ref_year]
    df["gd_const"] = df["is_german"] * df["is_dirty"]      # constant German x Dirty
    g_cols, d_cols, gd_cols = [], [], []
    for yr in event_years:
        gi = (df["is_german"] == 1)
        di = (df["is_dirty"] == 1)
        yi = (df["year"] == yr)
        df[f"g_{yr}"]  = (gi & yi).astype(int)
        df[f"d_{yr}"]  = (di & yi).astype(int)
        df[f"gd_{yr}"] = (gi & di & yi).astype(int)
        g_cols.append(f"g_{yr}")
        d_cols.append(f"d_{yr}")
        gd_cols.append(f"gd_{yr}")
    return df, event_years, g_cols, d_cols, gd_cols


def add_static(panel: pd.DataFrame, post_start: int):
    """Static DDD design: a single Post dummy (1 if year >= post_start) and the
    two surviving interactions g_post (German x Post) and gd_post
    (German x Dirty x Post). Returns df with those columns."""
    df = panel.copy()
    post = (df["year"] >= post_start).astype(int)
    df["g_post"]  = df["is_german"] * post
    df["gd_post"] = df["is_german"] * df["is_dirty"] * post
    return df


def build_static_formula(depvar: str) -> str:
    # Saturated FE absorb Dirty/German x Dirty levels and Dirty x Post; only the
    # German x Post (g_post) and triple German x Dirty x Post (gd_post) remain.
    return f"{depvar} ~ g_post + gd_post | brand^type + year^type"


def fit_static(depvar: str, estimator: str, df: pd.DataFrame):
    """Fit the static DDD (fepois or feols), CRV1 by brand."""
    import pyfixest as pf
    fml = build_static_formula(depvar)
    est = pf.fepois if estimator == "fepois" else pf.feols
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = est(fml, data=df, vcov={"CRV1": "brand"})
    return model, fml


def build_formula(depvar: str, g_cols, d_cols, gd_cols) -> str:
    # Saturated FE: brand^type + year^type absorb the level terms and the
    # Dirty x year (b2_t) family, so only German x year (g_) and the triple
    # German x Dirty x year (gd_) interactions enter the RHS.
    rhs = g_cols + gd_cols
    return f"{depvar} ~ " + " + ".join(rhs) + " | brand^type + year^type"


def fit(depvar: str, estimator: str, df: pd.DataFrame,
        g_cols, d_cols, gd_cols):
    """Fit fepois (PPML) or feols (lin-lin) with brand^type + year^type FE,
    CRV1 by brand."""
    import pyfixest as pf
    fml = build_formula(depvar, g_cols, d_cols, gd_cols)
    est = pf.fepois if estimator == "fepois" else pf.feols
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = est(fml, data=df, vcov={"CRV1": "brand"})
    return model, fml


def get_tidy(model) -> pd.DataFrame:
    """Return tidy table indexed by term with canonical columns:
    Estimate, Std. Error, 2.5%, 97.5%, pvalue."""
    tidy = model.tidy()
    for term_col in ("Coefficient", "term", "coefnames"):
        if term_col in tidy.columns:
            tidy = tidy.set_index(term_col)
            break
    col_map = {}
    for c in tidy.columns:
        cl = c.lower()
        if cl in ("estimate", "coef", "coefficient"):
            col_map[c] = "Estimate"
        elif "std" in cl or cl == "se":
            col_map[c] = "Std. Error"
        elif "2.5" in c or cl in ("ci_lo", "lower"):
            col_map[c] = "2.5%"
        elif "97.5" in c or cl in ("ci_hi", "upper"):
            col_map[c] = "97.5%"
        elif "pr(>" in cl or cl in ("pvalue", "p-value", "p_value", "p"):
            col_map[c] = "pvalue"
    tidy = tidy.rename(columns=col_map)
    if "pvalue" not in tidy.columns:
        tidy["pvalue"] = np.nan
    if "2.5%" not in tidy.columns and "Std. Error" in tidy.columns:
        tidy["2.5%"]  = tidy["Estimate"] - 1.96 * tidy["Std. Error"]
        tidy["97.5%"] = tidy["Estimate"] + 1.96 * tidy["Std. Error"]
    return tidy


def model_n_r2(model, df):
    n = int(getattr(model, "_N", len(df)))
    r2 = getattr(model, "_pseudo_r2", None)
    if r2 is None:
        r2 = getattr(model, "_r2", np.nan)
    try:
        r2 = float(r2)
    except (TypeError, ValueError):
        r2 = np.nan
    return n, r2


# ── Wald joint-zero F-test on a list of coefficients ────────────────────────────
def wald_zero(model, tidy: pd.DataFrame, test_cols, n_brands: int) -> dict:
    """H0: all coefficients in test_cols == 0 (small-sample F, df2 = n_brands-1)."""
    present = [c for c in test_cols if c in tidy.index]
    default = dict(statistic=np.nan, df1=np.nan, df2=n_brands - 1,
                   pvalue=np.nan, k_tested=len(present))
    if not present:
        return default

    all_params = list(tidy.index)
    n_params   = len(all_params)
    k          = len(present)
    R = np.zeros((k, n_params))
    for i, c in enumerate(present):
        R[i, all_params.index(c)] = 1.0
    q = np.zeros(k)

    # Attempt 1: pyfixest wald_test
    try:
        wt = model.wald_test(R=R, q=q)
        res = _parse_wald(wt, k, n_brands)
        if not np.isnan(res["statistic"]):
            res["k_tested"] = k
            return res
    except Exception:
        pass

    # Attempt 2: manual Wald via vcov
    try:
        vcov = _get_vcov(model, all_params)
        beta = tidy["Estimate"].values
        Rb   = R @ beta - q
        RVR  = R @ vcov @ R.T
        W    = float(Rb @ np.linalg.solve(RVR, Rb))
        F    = W / k
        df2  = n_brands - 1
        pval = float(1 - stats.f.cdf(F, k, df2))
        return dict(statistic=F, df1=k, df2=df2, pvalue=pval, k_tested=k)
    except Exception:
        return default


def _parse_wald(wt, k, n_brands) -> dict:
    if isinstance(wt, pd.Series):
        row = wt.to_dict()
    elif isinstance(wt, pd.DataFrame):
        row = wt.iloc[0].to_dict()
    elif isinstance(wt, dict):
        row = wt
    else:
        row = {}
    stat = next((float(row[k_]) for k_ in row
                 if any(x in k_.lower() for x in ("stat", " f ", "chi"))), np.nan)
    pval = next((float(row[k_]) for k_ in row
                 if "p" in k_.lower() and "val" in k_.lower()), np.nan)
    return dict(statistic=stat, df1=k, df2=n_brands - 1, pvalue=pval)


def _get_vcov(model, param_names):
    for attr in ("_vcov", "vcov", "_V"):
        v = getattr(model, attr, None)
        if v is None:
            continue
        if isinstance(v, pd.DataFrame):
            return v.loc[param_names, param_names].values
        if isinstance(v, np.ndarray) and v.shape == (len(param_names),) * 2:
            return v
    raise RuntimeError("vcov not found")
