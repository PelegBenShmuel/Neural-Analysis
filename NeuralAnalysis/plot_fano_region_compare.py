"""
Per-rat Fano factor trend, GC vs S1 side by side -- Peleg's complementary
request to plot_fano_block_trend.py, 2026-11-05 ("FF של כל חולדה לפי
האזורים שלה"). That script compares one region across all rats; this one
compares a single rat's own GC population against its own S1 population.
Reads FanoFactorTotal.xlsx (doesn't recompute) -- one small-multiples panel
per rat in a single figure, GC always blue / S1 always orange (region is
the fixed-color entity here, not the rat, unlike plot_fano_block_trend.py).

A rat with zero units in a region just skips that line (MS14: 0 GC) or shows
a "no region data" note if it has neither (MS23: still 100% undefined, no
gc_bounds_um yet) -- not an error.

Usage (np_analysis -- needs openpyxl): python plot_fano_region_compare.py
Writes locally to /tmp/, then copies to Z:\\Peleg\\CrossRatAnalysis\\.
"""
import sys
import os

import numpy as np
import openpyxl
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import NAS_PELEG, copy_to_share_safely
from plot_fano_block_trend import SHEET_GROUP, SURFACE, PRIMARY_INK, SECONDARY_INK, MUTED_INK, GRIDLINE

# dataviz-skill categorical palette slots 1-2: region is the fixed-identity
# entity in this plot (same two colors in every subplot), unlike
# plot_fano_block_trend.py where the rat is the fixed-identity entity.
REGION_COLORS = {'GC': '#2a78d6', 'S1': '#eb6834'}

RAT_ORDER = ['MS09', 'MS11', 'MS14', 'MS15', 'MS18', 'MS20', 'MS21', 'MS22', 'MS24', 'MS25']
# MS23 dropped 2026-11-05 along with MS08 -- both have zero GC/S1 units
# (no gc_bounds_um anywhere), so there's nothing to plot for either.
# MS24/MS25 added 2026-11-08 -- both PROVISIONAL gc_bounds_um (Mai's own
# config/gc_boundaries.csv marks both provisional=True).


def load_all_rows():
    """{rat: {'group': ..., 'regions': {region: [[block1 vals], ..., [block7 vals]]}}}."""
    xlsx_path = f"{NAS_PELEG}/CrossRatAnalysis/FanoFactorTotal.xlsx"
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    block_fields = [f"block{i}_fano" for i in range(1, 8)]

    by_rat = {}
    for sheet_name, group in SHEET_GROUP.items():
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        header, data = rows[0], rows[1:]
        idx = {name: i for i, name in enumerate(header)}
        for r in data:
            cluster = r[idx['cluster']]
            if isinstance(cluster, str):   # skip the bold "MEAN (n=...)" summary rows
                continue
            region = r[idx['region']]
            if region not in REGION_COLORS:   # skip 'undefined'
                continue
            rat = r[idx['rat']]
            rat_entry = by_rat.setdefault(rat, {'group': group, 'regions': {}})
            region_blocks = rat_entry['regions'].setdefault(region, [[] for _ in range(7)])
            for i, field in enumerate(block_fields):
                val = r[idx[field]]
                if val not in (None, ""):
                    region_blocks[i].append(val)
    return by_rat


def main():
    by_rat = load_all_rows()

    ncols = 3
    nrows = -(-len(RAT_ORDER) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 3.6 * nrows), sharex=True)
    axes = axes.flatten()
    blocks_x = np.arange(1, 8)

    for ax, rat in zip(axes, RAT_ORDER):
        ax.set_facecolor(SURFACE)
        entry = by_rat.get(rat)
        has_data = False
        if entry:
            for region, color in REGION_COLORS.items():
                region_blocks = entry['regions'].get(region)
                if not region_blocks or not any(region_blocks):
                    continue
                means = [np.mean(v) if v else np.nan for v in region_blocks]
                sems = [np.std(v, ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0 for v in region_blocks]
                n_units = max(len(v) for v in region_blocks)
                ax.errorbar(blocks_x, means, yerr=sems, color=color, marker='o',
                             markersize=5, linewidth=2, capsize=3, label=f"{region} (n={n_units})",
                             zorder=3)
                has_data = True
        group_label = entry['group'] if entry else '?'
        short_group = 'Exp' if group_label == 'Experiment' else 'Ctrl'
        ax.set_title(f"{rat} ({short_group})", fontsize=11, color=PRIMARY_INK, loc='left')
        if has_data:
            ax.legend(frameon=False, fontsize=8.5, labelcolor=SECONDARY_INK, loc='best')
        else:
            ax.text(0.5, 0.5, "no GC/S1 data\n(no gc_bounds_um)", ha='center', va='center',
                    transform=ax.transAxes, fontsize=9, color=MUTED_INK)
        ax.set_xticks(blocks_x)
        ax.tick_params(colors=MUTED_INK, labelsize=8.5)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        for spine in ('left', 'bottom'):
            ax.spines[spine].set_color(GRIDLINE)

    for ax in axes[len(RAT_ORDER):]:
        ax.axis('off')

    fig.supxlabel("Training-day block", fontsize=10.5, color=SECONDARY_INK)
    fig.supylabel("Fano factor (Var/Mean, 1s bins, 4min pre-block)", fontsize=10.5, color=SECONDARY_INK)
    fig.suptitle("Fano factor by region, per rat \u2014 GC vs S1 (mean \u00b1 SEM)",
                 fontsize=13, color=PRIMARY_INK, x=0.02, ha='left', fontweight='medium')
    fig.tight_layout(rect=[0.02, 0.02, 1, 0.96])

    local_path = "/tmp/FanoFactor_PerRat_GCvsS1_Block1to7.png"
    plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
    print(f"Wrote {local_path}")

    nas_dir = f"{NAS_PELEG}/CrossRatAnalysis"
    os.makedirs(nas_dir, exist_ok=True)
    copy_to_share_safely(local_path, nas_dir)
    print(f"Copied to {nas_dir}/")


if __name__ == '__main__':
    main()
