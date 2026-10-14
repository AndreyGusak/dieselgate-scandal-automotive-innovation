"""
indicator_trends.py
===================
Raw patent-indicator trends over filing year, split by tech type
(green = EV/Hybrid, dirty = ICE). Window restricted to 2010-2019.

Indicators (raw counts, NOT z-scored), excluding family size:
  - BCIT    : backward citations
  - FCIT    : forward citations
  - REFNPAT : non-patent (reference) literature citations

Plot styling:
  dotted grid, integer year ticks, dashed Dieselgate (2015) line,
  per-point n= annotations, markers + linewidth 2, dpi 200.

Outputs
-------
  output/plots/indicator_trends/indicator_trends_all.png        (all 6 trends)
  output/plots/indicator_trends/indicator_trend_BCIT.png
  output/plots/indicator_trends/indicator_trend_FCIT.png
  output/plots/indicator_trends/indicator_trend_REFNPAT.png
  output/tables/indicator_trends_means.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

SEED = 42
np.random.seed(SEED)

def _require(path, produced_by):
    if not path.exists():
        raise SystemExit(
            f"Missing input: {path} -- produced by {produced_by}. "
            "See SETUP.md, Part 2: the raw PATSTAT tables are not shipped with this repository."
        )

ROOT       = Path(__file__).resolve().parent
CHECKPOINT = ROOT / "data" / "checkpoints" / "df_focal_indicators.csv"

_require(CHECKPOINT, "02_quality_indicators/descriptives.ipynb")
OUT_DIR    = ROOT / "output" / "plots" / "indicator_trends"
TABLES_DIR = ROOT / "output" / "tables"

YEAR_MIN, YEAR_MAX = 2010, 2019
DIESELGATE = 2015
DPI = 200

INDICATORS = ["BCIT", "FCIT", "REFNPAT", "FAMSIZE"]
IND_LABEL  = {
    "BCIT":    "Backward citations",
    "FCIT":    "Forward citations",
    "REFNPAT": "Non-patent (reference) literature",
    "FAMSIZE": "Family size",
}

COLOR_GREEN = "green"     # EV/Hybrid
COLOR_DIRTY = "red"       # ICE
# Line styles to distinguish indicators on the combined plot
IND_STYLE   = {"BCIT": "-", "FCIT": "--", "REFNPAT": ":", "FAMSIZE": "-."}
IND_MARKER  = {"BCIT": "o", "FCIT": "s", "REFNPAT": "^", "FAMSIZE": "D"}


def _style_axis(ax):
    """Integer year ticks, dotted grid, Dieselgate line at 2015."""
    ax.axvline(x=DIESELGATE, color="black", linestyle="--", linewidth=1.2,
               label="Dieselgate (2015)", zorder=3)
    ax.set_xlabel("Filing Year")
    ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.grid(True, linestyle=":", alpha=0.4)


def main() -> None:
    print("=" * 65)
    print("Raw indicator trends by tech type (green vs dirty), 2010-2019")
    print("=" * 65)

    print(f"\n[LOAD] {CHECKPOINT}")
    df = pd.read_csv(CHECKPOINT)
    print(f"  rows={len(df):,}  years={df.year.min()}–{df.year.max()}")

    # Restrict to 2010-2019
    df = df[(df["year"] >= YEAR_MIN) & (df["year"] <= YEAR_MAX)].copy()
    print(f"  kept {len(df):,} rows in {YEAR_MIN}-{YEAR_MAX}")

    # Map tech_type -> green/dirty
    df["grp"] = df["tech_type"].map({"EV_Hybrid": "green", "ICE": "dirty"})
    assert df["grp"].notna().all(), "Unmapped tech_type values present"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    # Mean per (year, group) for each indicator + counts
    means = (df.groupby(["year", "grp"])[INDICATORS].mean().reset_index())
    counts = (df.groupby(["year", "grp"]).size()
                .reset_index(name="n"))
    years = list(range(YEAR_MIN, YEAR_MAX + 1))

    out_csv = TABLES_DIR / "indicator_trends_means.csv"
    means.merge(counts, on=["year", "grp"]).sort_values(
        ["grp", "year"]).to_csv(out_csv, index=False)
    print(f"[SAVE] {out_csv}")

    def series(grp, ind):
        s = means[means["grp"] == grp].set_index("year")[ind]
        return [s.get(y, np.nan) for y in years]

    def ncount(grp):
        s = counts[counts["grp"] == grp].set_index("year")["n"]
        return {y: int(s.get(y, 0)) for y in years}

    # ── Combined plot: all 6 trends ───────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(11, 6))
    for ind in INDICATORS:
        for grp, color in [("green", COLOR_GREEN), ("dirty", COLOR_DIRTY)]:
            ax.plot(years, series(grp, ind),
                    color=color, linestyle=IND_STYLE[ind],
                    marker=IND_MARKER[ind], linewidth=2, markersize=5,
                    label=f"{IND_LABEL[ind]} — {grp}")
    _style_axis(ax)
    ax.set_ylabel("Mean count per patent")
    ax.legend(fontsize=9, ncol=1)
    fig.tight_layout()
    path = OUT_DIR / "indicator_trends_all.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {path.name}")

    # ── One plot per indicator ────────────────────────────────────────────────
    for ind in INDICATORS:
        fig, ax = plt.subplots(figsize=(11, 6))
        g_vals, d_vals = series("green", ind), series("dirty", ind)
        g_n, d_n = ncount("green"), ncount("dirty")

        ax.plot(years, g_vals, color=COLOR_GREEN, marker="o", linewidth=2,
                label="Green (EV/Hybrid)")
        ax.plot(years, d_vals, color=COLOR_DIRTY, marker="s", linewidth=2,
                label="Dirty (ICE)")

        # n= annotations per point (green above, dirty below), as in the
        for y, v in zip(years, g_vals):
            if not np.isnan(v):
                ax.annotate(f"n={g_n[y]:,}", xy=(y, v), xytext=(0, 7),
                            textcoords="offset points", ha="center",
                            fontsize=7, color="green")
        for y, v in zip(years, d_vals):
            if not np.isnan(v):
                ax.annotate(f"n={d_n[y]:,}", xy=(y, v), xytext=(0, -12),
                            textcoords="offset points", ha="center",
                            fontsize=7, color="red")

        _style_axis(ax)
        ax.set_ylabel(f"Mean {IND_LABEL[ind].lower()} per patent")
        ax.legend(fontsize=9)
        fig.tight_layout()
        path = OUT_DIR / f"indicator_trend_{ind}.png"
        fig.savefig(path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"  → {path.name}")

    print(f"\n[DONE] Plots → {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
