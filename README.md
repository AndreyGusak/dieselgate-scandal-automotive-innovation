# Dieselgate and the Direction of Automotive Innovation: Evidence from USPTO Patent Data

Code and results for the Master's thesis of Andrey Gusak, Friedrich-Alexander-Universität
Erlangen-Nürnberg (Chair for Labor and Innovation Economics, 2026). The thesis asks
how the 2015 Volkswagen emissions scandal (Dieselgate) changed the innovation of
German automakers in green (EV / hybrid) versus dirty (internal-combustion)
technologies, using US patent applications from PATSTAT.

## Method in brief

- **Design:** a triple difference-in-differences (DDD) event study. The outcome gap
  between dirty and green patents of German makers is compared with the same gap
  for non-German makers, year by year, around 2015.
- **Sample:** US patent applications of 18 automaker brand groups (three German:
  Volkswagen Group, Daimler, BMW), filing years 2010–2019. Technology type (ICE /
  EV / hybrid) is assigned from CPC codes; continuation patents are excluded.
- **Outcomes (5):** the yearly patent count, and four patent-quality indicators —
  family size, backward citations, forward citations, references to non-patent
  literature.
- **Estimation:** PPML and OLS (Lin-lin) with brand × type and year × type fixed
  effects, standard errors clustered by brand. Event studies at reference years 2014 and
  2015, a pre-trend F-test, and a static post-scandal specification.

## Repository layout

```
01_patstat_pipeline/    raw PATSTAT tables -> clean US patent table (notebooks, step1-step4)
02_quality_indicators/  patent-level quality indicators; Table 2, Figures 2-4, Appendix A4
03_patent_count_figures/ patent counts by maker; Figure 1, Appendix A3
04_ddd_regressions/     panel, DDD regressions, tests; Tables 3-5, Appendix A5
SETUP.md                where each thesis table/figure is stored; how to rebuild everything
FILES.md                what every script reads and writes
```

## Where to find the results

The finished figures and tables are already in each module's `output/` folder, so
nothing has to be run to look at them.

| Thesis object | File |
|---|---|
| Table 2 | `02_quality_indicators/output/tables/table2_descriptive_stats.csv` |
| Tables 3–5 | `04_ddd_regressions/output/tables/` |
| Figure 1, Appendix A3 | `03_patent_count_figures/output/plots/all_makers/` |
| Figures 2–4, Appendix A4 | `02_quality_indicators/output/plots/` |
| Appendix A5 | `04_ddd_regressions/output/plots/` |

The full mapping is in [`SETUP.md`](SETUP.md).

## Data availability

**Data source:** European Patent Office (EPO), Worldwide Patent Statistical Database
([PATSTAT Global](https://www.epo.org/en/searching-for-patents/business/patstat));
the data used were last updated in October 2021.

PATSTAT requires a licence from the EPO. This repository therefore contains **no
PATSTAT data** — neither the raw tables (more than 50 GB) nor any patent-level
datasets derived from them. Only aggregated results are included: summary
statistics, regression coefficients, and figures. To rebuild the intermediate
data from your own PATSTAT access, follow [`SETUP.md`](SETUP.md), Part 2.

## Reproducing the results

```
pip install -r requirements.txt     # Python 3.12
```

Then follow [`SETUP.md`](SETUP.md), Part 2.

**All PATSTAT files must be put into one folder called `patstat_raw/`, created
next to the repository folder (not inside it):**

```
work/
├── <this repository>/
└── patstat_raw/        <- all PATSTAT exports (tls206…, tls207…, tls224…, tls211…, …)
```

(Another location can be set with the `PATSTAT_DIR` environment variable; see
`SETUP.md`, section 2.1, for the exact file list.) Every notebook that reads raw
files checks them before it starts and tells you which are missing. The scripts find their
other inputs relative to their own location and stop with a message naming the
missing file and the step that produces it. [`FILES.md`](FILES.md) documents each script.

## License

The code, documentation and the result figures and tables in this repository are
released under the [MIT License](LICENSE). The licence does **not** cover:

- PATSTAT data, which belongs to the EPO and is not included here;
- the thesis document itself, which is not part of this repository.
