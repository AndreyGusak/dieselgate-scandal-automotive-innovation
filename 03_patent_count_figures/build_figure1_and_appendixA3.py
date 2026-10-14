"""
Figure 1 (Tesla, patent counts) and Appendix A3.1-A3.6 (patent counts by
maker nationality).

Aggregates unique patent applications per (brand, year, tech_type) from the
patent-level checkpoint, balances the panel (2010-2019, zero-filled), and
plots one chart per nationality group.

Input:  ../02_quality_indicators/data/checkpoints/df_focal_indicators.csv
Output: output/plots/all_makers/{group_label}.png

  01_German_Treatment.png -> Appendix A3.1 (German makers)
  02_American.png          -> Appendix A3.2 (American makers)
  03_Japanese.png           -> Appendix A3.3 (Japanese makers)
  04_Korean.png              -> Appendix A3.4 (Korean makers)
  05_Swedish_British.png      -> Appendix A3.5 (Swedish makers)
  06_Italian.png               -> Appendix A3.6 (Italian makers)
  07_Other.png (Tesla)           -> Figure 1
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.cm as cm
from pathlib import Path

def _require(path, produced_by):
    if not path.exists():
        raise SystemExit(
            f"Missing input: {path} -- produced by {produced_by}. "
            "See SETUP.md, Part 2: the raw PATSTAT tables are not shipped with this repository."
        )

ROOT = Path(__file__).parent
CHECKPOINT = ROOT.parent / "02_quality_indicators" / "data" / "checkpoints" / "df_focal_indicators.csv"

_require(CHECKPOINT, "02_quality_indicators/descriptives.ipynb")
OUT_DIR = ROOT / "output" / "plots" / "all_makers"
OUT_DIR.mkdir(parents=True, exist_ok=True)

YEAR_START, YEAR_END = 2010, 2019
YEARS = list(range(YEAR_START, YEAR_END + 1))
TECH_TYPES = ["Dirty", "Green"]

BRAND_ORDER = [
    "Volkswagen Group", "Daimler", "BMW",
    "Ford", "General Motors",
    "Toyota", "Honda", "Nissan", "Mitsubishi",
    "Mazda", "Suzuki", "Subaru",
    "Hyundai-Kia",
    "Volvo Cars", "Volvo Trucks",
    "Jaguar Land Rover",
    "Fiat",
    "Tesla",
]

NATIONALITY_GROUPS = {
    "01_German_Treatment": ["Volkswagen Group", "Daimler", "BMW"],
    "02_American": ["Ford", "General Motors"],
    "03_Japanese": ["Toyota", "Honda", "Nissan", "Mitsubishi", "Mazda", "Suzuki", "Subaru"],
    "04_Korean": ["Hyundai-Kia"],
    "05_Swedish_British": ["Volvo Cars", "Volvo Trucks", "Jaguar Land Rover"],
    "06_Italian": ["Fiat"],
    "07_Other": ["Tesla"],  # == Figure 1
}

TAB10 = cm.get_cmap("tab10").colors


def _add_dieselgate_line(ax):
    ax.axvline(x=2015, color="black", linestyle="--", linewidth=1.2,
               label="Dieselgate (2015)", zorder=3)


def load_panel():
    df = pd.read_csv(CHECKPOINT, usecols=["appln_id", "year", "brand", "tech_type"])
    df = df[(df["year"] >= YEAR_START) & (df["year"] <= YEAR_END)].copy()
    df["tech_type"] = df["tech_type"].map({"ICE": "Dirty", "EV_Hybrid": "Green"})

    agg = (
        df.groupby(["brand", "year", "tech_type"])["appln_id"]
        .nunique()
        .reset_index(name="Patents")
    )

    known_brands = [b for b in BRAND_ORDER if b in agg["brand"].unique()]
    full_idx = pd.MultiIndex.from_product(
        [known_brands, YEARS, TECH_TYPES], names=["brand", "year", "tech_type"]
    )
    return (
        agg.set_index(["brand", "year", "tech_type"])
        .reindex(full_idx, fill_value=0)
        .reset_index()
    )


def plot_all_makers(df_balanced, nationality_groups, out_dir):
    for group_label, brands in nationality_groups.items():
        available = [b for b in brands if b in df_balanced["brand"].unique()]
        if not available:
            continue

        fig, ax = plt.subplots(figsize=(11, 5))

        for idx, brand in enumerate(available):
            color = TAB10[idx % len(TAB10)]
            bdata = df_balanced[df_balanced["brand"] == brand]

            green = bdata[bdata["tech_type"] == "Green"].sort_values("year")
            dirty = bdata[bdata["tech_type"] == "Dirty"].sort_values("year")

            ax.plot(green["year"], green["Patents"], linestyle="-", marker="o",
                     linewidth=2, markersize=5, color=color, label=f"{brand} — Green")
            ax.plot(dirty["year"], dirty["Patents"], linestyle="--", marker="s",
                     linewidth=2, markersize=5, color=color, label=f"{brand} — Dirty")

        _add_dieselgate_line(ax)
        ax.set_xlabel("Filing Year")
        ax.set_ylabel("Number of Unique Patent Applications")
        ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
        ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
        ax.grid(True, linestyle=":", alpha=0.5)
        plt.tight_layout()

        fig.savefig(out_dir / f"{group_label}.png", dpi=300, bbox_inches="tight")
        plt.close(fig)


def main():
    df_balanced = load_panel()
    plot_all_makers(df_balanced, NATIONALITY_GROUPS, OUT_DIR)
    print(f"Saved {len(NATIONALITY_GROUPS)} figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
