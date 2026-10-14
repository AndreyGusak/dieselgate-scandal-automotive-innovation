"""
indicator_trends_famsize_german.py
===================================
Raw family-size (FAMSIZE) trend over filing year, split by tech type
(green = EV/Hybrid, dirty = ICE) AND by German vs. non-German maker.
Window restricted to 2010-2019.

German makers: BMW, Daimler, Volkswagen Group.

Plot styling follows indicator_trends.py:
  dotted grid, integer year ticks, dashed Dieselgate (2015) line,
  markers + linewidth 2, dpi 200.

Outputs
-------
  output/plots/indicator_trends/indicator_trend_FAMSIZE_german.png
  output/tables/indicator_trends_FAMSIZE_german_means.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

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

GERMAN_BRANDS = ["BMW", "Daimler", "Volkswagen Group"]

# tech-type colors (as in indicator_trends.py)
COLOR_GREEN = "green"     # EV/Hybrid
COLOR_DIRTY = "red"       # ICE
# German vs non-German distinguished by linestyle/marker
NAT_STYLE  = {"German": "-",  "Non-German": "--"}
NAT_MARKER = {"German": "o",  "Non-German": "s"}


def _style_axis(ax):
    """Integer year ticks, dotted grid, Dieselgate line at 2015."""
    ax.axvline(x=DIESELGATE, color="black", linestyle="--", linewidth=1.2,
               label="Dieselgate (2015)", zorder=3)
    ax.set_xlabel("Filing Year")
    ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.grid(True, linestyle=":", alpha=0.4)


def main() -> None:
    print("=" * 65)
    print("Raw FAMSIZE trend by tech type x German/non-German, 2010-2019")
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

    # Map brand -> German / Non-German
    df["nat"] = np.where(df["brand"].isin(GERMAN_BRANDS), "German", "Non-German")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    means = (df.groupby(["year", "grp", "nat"])["FAMSIZE"].mean()
               .reset_index())
    stds  = (df.groupby(["year", "grp", "nat"])["FAMSIZE"].std()
               .reset_index(name="std"))
    counts = (df.groupby(["year", "grp", "nat"]).size()
                .reset_index(name="n"))
    years = list(range(YEAR_MIN, YEAR_MAX + 1))

    out_csv = TABLES_DIR / "indicator_trends_FAMSIZE_german_means.csv"
    means.merge(counts, on=["year", "grp", "nat"]).merge(
        stds, on=["year", "grp", "nat"]).sort_values(
        ["grp", "nat", "year"]).to_csv(out_csv, index=False)
    print(f"[SAVE] {out_csv}")

    def series(grp, nat):
        sub = means[(means["grp"] == grp) & (means["nat"] == nat)].set_index("year")["FAMSIZE"]
        return [sub.get(y, np.nan) for y in years]

    def std_series(grp, nat):
        sub = stds[(stds["grp"] == grp) & (stds["nat"] == nat)].set_index("year")["std"]
        return [sub.get(y, np.nan) for y in years]

    combos = [
        ("green", "German",     COLOR_GREEN, NAT_STYLE["German"],     NAT_MARKER["German"],     (0, 7)),
        ("green", "Non-German", COLOR_GREEN, NAT_STYLE["Non-German"], NAT_MARKER["Non-German"], (0, 16)),
        ("dirty", "German",     COLOR_DIRTY, NAT_STYLE["German"],     NAT_MARKER["German"],     (0, -12)),
        ("dirty", "Non-German", COLOR_DIRTY, NAT_STYLE["Non-German"], NAT_MARKER["Non-German"], (0, -21)),
    ]

    fig, ax = plt.subplots(figsize=(11, 6))
    for grp, nat, color, ls, marker, offset in combos:
        vals = series(grp, nat)
        sds = std_series(grp, nat)
        ax.plot(years, vals, color=color, linestyle=ls, marker=marker,
                 linewidth=2, markersize=5, label=f"{grp.capitalize()} — {nat}")
        for y, v, sd in zip(years, vals, sds):
            if not np.isnan(v) and not np.isnan(sd):
                ax.annotate(f"σ={sd:.2f}", xy=(y, v), xytext=offset,
                            textcoords="offset points", ha="center",
                            fontsize=6.5, color=color)

    _style_axis(ax)
    ax.set_ylabel("Mean family size per patent")
    ax.legend(fontsize=9)
    fig.tight_layout()
    path = OUT_DIR / "indicator_trend_FAMSIZE_german.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {path.name}")

    # ── Same plot, fixed 0-20 y-axis scale ────────────────────────────────────
    fig, ax = plt.subplots(figsize=(11, 6))
    for grp, nat, color, ls, marker, offset in combos:
        vals = series(grp, nat)
        ax.plot(years, vals, color=color, linestyle=ls, marker=marker,
                 linewidth=2, markersize=5, label=f"{grp.capitalize()} — {nat}")

    _style_axis(ax)
    ax.set_ylim(0, 15)
    ax.set_ylabel("Mean family size per patent")
    ax.legend(fontsize=9)
    fig.tight_layout()
    path_scaled = OUT_DIR / "indicator_trend_FAMSIZE_german_scale0-15.png"
    fig.savefig(path_scaled, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {path_scaled.name}")

    print(f"\n[DONE] Plots → {path.relative_to(ROOT)}, {path_scaled.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
