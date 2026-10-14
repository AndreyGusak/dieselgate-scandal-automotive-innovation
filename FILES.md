# What each file does

Every script anchors its paths to its own location, so the repository can be
cloned anywhere. Run scripts from the folder they live in. The finished
figures and result tables are already in each module's `output/` folder; the
intermediate datasets are not included — see `SETUP.md` (Part 2) to rebuild them.

All raw PATSTAT tables (every `patstat_raw/tls…` file below) live in one folder,
`patstat_raw/`, which you create **next to** the repository folder, not inside it
(`SETUP.md`, section 2.1).

## 01_patstat_pipeline: raw PATSTAT to a clean patent table

These four notebooks rebuild the patent sample from the raw PATSTAT tables.
See `SETUP.md` for what to export and where to put it. Running them takes hours.

| File | Purpose | In | Out |
|---|---|---|---|
| `step1/link_makers_to_applications.ipynb` | Link automaker names to their patent applications | `patstat_raw/tls206_part01/02.csv`, `patstat_raw/tls207_part01.csv` | `maker_app_links.csv` |
| `step2/select_major_makers.ipynb` | Keep firms with >400 applications, then the 90 manually selected automakers | `step1/maker_app_links.csv` | `major_makers.csv`, `makers_above_400.csv`, `patent_counts_by_maker.xlsx` |
| `step3/classify_applications_by_cpc.ipynb` | Classify every PATSTAT application as ICE / EV / Hybrid by CPC code (**Table A2.1**) | `patstat_raw/tls201_united_no_exc_columns.csv`, `patstat_raw/tls224_part01/02/03.csv` | `patents_cpc_classified.csv` (plus the intermediate `cpc_codes_aggregated.csv`) |
| `step4/merge_and_clean_us_patents.ipynb` | Merge the two branches, keep US filings, drop continuation patents | `step2/major_makers.csv`, `step3/patents_cpc_classified.csv`, `patstat_raw/tls216_part01.csv` | `us_patents_clean.csv`, `unique_inventions_per_maker.xlsx` |

## 02_quality_indicators: patent-level quality indicators

| File | Purpose | In | Out |
|---|---|---|---|
| `descriptives.ipynb` | Scan TLS211/TLS212 and the CPC table to build the patent-level indicators FAMSIZE, BCIT, FCIT, REFNPAT; draw the density plots (**Figure 2**, **Appendix A4.1–A4.3**) | `../01_patstat_pipeline/step4/us_patents_clean.csv`, `../01_patstat_pipeline/step3/patents_cpc_classified.csv`, `patstat_raw/tls211_part01/02.csv`, `patstat_raw/tls212_part01/02/03.csv` | `data/checkpoints/df_focal_indicators.csv` (plus the six intermediate extracts), `output/plots/raw_density/*.png` |
| `table2_descriptive_stats.py` | Descriptive statistics of the four indicators (**Table 2**) | `data/checkpoints/df_focal_indicators.csv` | `output/tables/table2_descriptive_stats.csv` |
| `indicator_trends.py` | Yearly trend of each indicator, green vs dirty (**Figure 3**) | same checkpoint | `output/plots/indicator_trends/indicator_trends_all.png` and per-indicator plots |
| `indicator_trends_famsize_german.py` | Mean family size by technology type, German vs non-German (**Figure 4**) | same checkpoint | `output/plots/indicator_trends/indicator_trend_FAMSIZE_german*.png` |

The four indicators are called FAMSIZE (family size), BCIT (backward citations),
FCIT (forward citations) and REFNPAT (references to non-patent literature). The
regression outputs in `04_ddd_regressions` name the last one `nptlit`.

## 03_patent_count_figures: patent counts by maker

| File | Purpose | In | Out |
|---|---|---|---|
| `build_figure1_and_appendixA3.py` | Yearly green/dirty patent counts per nationality group (**Figure 1** = Tesla, **Appendix A3.1–A3.6** = the other groups) | `../02_quality_indicators/data/checkpoints/df_focal_indicators.csv` | `output/plots/all_makers/*.png` |

## 04_ddd_regressions: the regressions

Run in order: `01` → `02` → `03` → `04` (`04` reads a workbook written by `03`).

| File | Purpose | In | Out |
|---|---|---|---|
| `01_build_panel.py` | Aggregate patents into brand x year x technology cells | `../02_quality_indicators/data/checkpoints/df_focal_indicators.csv` | `data/processed/ddd_panel.csv` (360 rows) |
| `02_run_ddd.py` | 10 dynamic event-study regressions (5 outcomes x {PPML, Lin-lin}) at reference years 2014 and 2015 (**Tables 3–4**, **Appendix A5**) | `data/processed/ddd_panel.csv` | `output/tables/all_coefficients_ddd_ref2014.xlsx`, `..._ref2015.xlsx`, `output/plots/ddd_ref*.png` |
| `03_pretrend_ftest.py` | Joint F-test that the pre-scandal triple-difference coefficients are zero (the *F-test p* column of **Table 3**) | `data/processed/ddd_panel.csv` | `output/tables/pretrend_ftest_ddd.xlsx` |
| `04_static_ddd.py` | Static specification: one post-scandal coefficient per model (**Table 5**) | `data/processed/ddd_panel.csv`, `output/tables/pretrend_ftest_ddd.xlsx` | `output/tables/static_ddd.xlsx` |
| `ddd_common.py` | Shared library: builds the design matrix, fits PPML/OLS with brand x type and year x type fixed effects, runs the Wald tests. Imported by `02`, `03`, `04` — not run directly. | — | — |
| `utils_plot.py` | Plot constants (font, figure size, colours, dpi) used by `02`. | — | — |
