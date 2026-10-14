# Setup and reproduction

## Part 1 — The results that are already in this repository

Every figure of the thesis is stored as a `.png`, and the tables behind
Tables 2 to 5 are stored as `.csv` / `.xlsx`, in the `output/` folder of each
module:

| Thesis object | File |
|---|---|
| Table 2 | `02_quality_indicators/output/tables/table2_descriptive_stats.csv` |
| Tables 3–4 | `04_ddd_regressions/output/tables/all_coefficients_ddd_ref2014.xlsx` |
| Table 3, *F-test p* column | `04_ddd_regressions/output/tables/pretrend_ftest_ddd.xlsx` |
| Table 5 | `04_ddd_regressions/output/tables/static_ddd.xlsx` |
| Figure 1, Appendix A3 | `03_patent_count_figures/output/plots/all_makers/*.png` |
| Figure 2, Appendix A4 | `02_quality_indicators/output/plots/raw_density/*.png` |
| Figures 3–4 | `02_quality_indicators/output/plots/indicator_trends/*.png` |
| Appendix A5 | `04_ddd_regressions/output/plots/ddd_ref2014_*.png` |

The same regressions with reference year 2015 are included as well
(`all_coefficients_ddd_ref2015.xlsx`, `ddd_ref2015_*.png`).

`FILES.md` lists what every script does, what it reads and what it writes.

The intermediate datasets are **not** included: the PATSTAT source tables alone
exceed 50 GB, and the derived files run to several gigabytes (and PATSTAT is
licensed data, so no patent-level data is published here). Re-running a script
therefore requires rebuilding the data first, as described in Part 2. Each script
checks its inputs and stops with a message naming the file it needs and the script
that produces it.

### Requirements

Python 3.12. The versions the results were produced with are pinned in
`requirements.txt`:

```
pip install -r requirements.txt
```

The notebooks need a Jupyter front-end (JupyterLab, VS Code, …) in addition;
`ipykernel` is included in `requirements.txt`.

---

## Part 2 — Rebuilding everything from raw PATSTAT

### 2.1 Export the source tables and put them all in `patstat_raw/`

> **Every PATSTAT file goes into one folder called `patstat_raw/`, which you create
> next to the repository folder — not inside it.** The notebooks read the raw
> tables from there and nowhere else.

```
work/                         <- any parent folder
├── thesis-repo/              <- this repository (the folder name is up to you)
│   ├── 01_patstat_pipeline/
│   ├── 02_quality_indicators/
│   ├── 03_patent_count_figures/
│   └── 04_ddd_regressions/
└── patstat_raw/              <- you create this: ALL PATSTAT exports go here
    ├── tls206_part01.csv
    ├── tls206_part02.csv
    ├── tls207_part01.csv
    ├── tls201_united_no_exc_columns.csv
    ├── tls224_part01.csv  (… _part02, _part03)
    ├── tls216_part01.csv
    ├── tls211_part01.csv  (… _part02)
    └── tls212_part01.csv  (… _part02, _part03)
```

Put the files directly in `patstat_raw/`, with no subfolders. The raw tables exceed
50 GB, which is why they are kept out of the repository. Each notebook that reads
raw files checks them before it starts and, if any is missing, lists them and tells
you where they belong.

All of them come from **PATSTAT Global**:

| PATSTAT table | Export as | Read by |
|---|---|---|
| TLS206 — person | `patstat_raw/tls206_part01.csv`, `…/tls206_part02.csv` | `step1` |
| TLS207 — person–application link | `patstat_raw/tls207_part01.csv` | `step1` |
| TLS201 — application | `patstat_raw/tls201_united_no_exc_columns.csv` (see 2.2) | `step3` |
| TLS224 — CPC classification | `patstat_raw/tls224_part01.csv`, `…_part02.csv`, `…_part03.csv` | `step3` |
| TLS216 — continuations | `patstat_raw/tls216_part01.csv` | `step4` |
| TLS211 — publications (≈ 9 GB) | `patstat_raw/tls211_part01.csv`, `…_part02.csv` | `02_quality_indicators/descriptives.ipynb` |
| TLS212 — citations (≈ 20 GB) | `patstat_raw/tls212_part01.csv`, `…_part02.csv`, `…_part03.csv` | `02_quality_indicators/descriptives.ipynb` |

**Optional — a different location.** If the data has to live elsewhere (for example
on another drive), set the environment variable `PATSTAT_DIR` to that folder
instead of using `patstat_raw/`. Set it before starting Jupyter or VS Code, and
start the notebook from the same terminal so that it sees the variable:

```
# Windows PowerShell
$env:PATSTAT_DIR = "D:\data\patstat_raw"

# macOS / Linux
export PATSTAT_DIR=/data/patstat_raw
```

This table lists only what has to be exported from PATSTAT. Steps 2 and 4 read
the outputs of earlier steps (step2 reads `step1/maker_app_links.csv`; step4 reads
`step2/major_makers.csv` and `step3/patents_cpc_classified.csv`), so apart from
TLS216 there is nothing to export for them. See 2.3 for the full chain. The files
that the notebooks themselves create (`maker_app_links.csv`,
`patents_cpc_classified.csv`, …) stay inside the repository, in the step folder
of the notebook that writes them.

Splitting a table into `_part01`, `_part02`, … is only an export convenience:
the scripts read the parts in sequence and concatenate them. A single file works
too, as long as the path constants at the top of the corresponding notebook are
adjusted.

### 2.2 The TLS201 file

`step3` does not read TLS201 directly. It expects one concatenated file,
`tls201_united_no_exc_columns.csv`, holding the full application table reduced
to five columns:

```
appln_id, appln_auth, appln_filing_date, ipr_type, docdb_family_id
```

Build it by exporting TLS201 (all parts), concatenating them, and dropping the
other 22 columns. Do this inside `patstat_raw/` — for example by running this
from there:

```python
import pandas as pd
COLS = ['appln_id', 'appln_auth', 'appln_filing_date', 'ipr_type', 'docdb_family_id']
parts = ['tls201_part01.csv', 'tls201_part02.csv', 'tls201_part03.csv']
first = True
for p in parts:
    for chunk in pd.read_csv(p, usecols=COLS, chunksize=2_000_000):
        chunk.to_csv('tls201_united_no_exc_columns.csv',
                     mode='w' if first else 'a', header=first, index=False)
        first = False
```

These five columns are exactly the ones that survive into
`patents_cpc_classified.csv`, to which `step3` adds three CPC counters
(`count_ICE_codes`, `count_EV_codes`, `count_Hybrid_codes`).

### 2.3 Run, in this order

Run every notebook and script **from the folder it sits in** — all paths are
relative to it. Scripts overwrite their own outputs and can be re-run any
number of times.

Folders named `data/` (for example `02_quality_indicators/data/checkpoints/` and
`04_ddd_regressions/data/processed/`) are not part of the repository: the
notebooks and scripts create them the first time they run.

```
# 1. data preparation — reads the raw tables above; takes hours; run step1 -> step4
01_patstat_pipeline/step1/link_makers_to_applications.ipynb        -> maker_app_links.csv
01_patstat_pipeline/step2/select_major_makers.ipynb                -> major_makers.csv
01_patstat_pipeline/step3/classify_applications_by_cpc.ipynb       -> patents_cpc_classified.csv
01_patstat_pipeline/step4/merge_and_clean_us_patents.ipynb         -> us_patents_clean.csv

# 2. patent-level quality indicators — scans TLS211 and TLS212
02_quality_indicators/descriptives.ipynb
    -> data/checkpoints/df_focal_indicators.csv
    -> output/plots/raw_density/*.png                  Figure 2, Appendix A4

# 3. tables and figures built from the indicator checkpoint
cd 02_quality_indicators
python table2_descriptive_stats.py                     # Table 2
python indicator_trends.py                             # Figure 3
python indicator_trends_famsize_german.py              # Figure 4

cd ../03_patent_count_figures
python build_figure1_and_appendixA3.py                 # Figure 1, Appendix A3

# 4. regressions — the order matters: 04 reads a workbook written by 03
cd ../04_ddd_regressions
python 01_build_panel.py                               # panel, 360 cells
python 02_run_ddd.py                                   # Tables 3-4, Appendix A5
python 03_pretrend_ftest.py                            # F-test column of Table 3
python 04_static_ddd.py                                # Table 5
```

Steps 1 to 4 build on each other, so they also have to run in this order.
