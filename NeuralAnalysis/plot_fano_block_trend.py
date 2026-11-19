"""
Per-rat Fano factor trend across the 7 Training-day blocks, for one region at
a time -- Peleg's request, 2026-11-05 ("FF plot across block 1 to block 7 to
the GC of all the rats"). Reads FanoFactorTotal.xlsx (built by
fano_factor_total.py) rather than recomputing from raw spike data -- the
per-unit values don't change here, only how they're plotted.

One line per rat that actually has units in the requested region (a rat with
no gc_bounds_um comes back 100% 'undefined' and has zero GC/S1 units, so it's
silently absent from the plot, not an error -- see fano_factor_total.py's
docstring for which rats that is as of 2026-11-05). Each rat's line is
mean +/- SEM across that rat's units in that region, per block -- not the
same as pooling all units from all rats into one line, since rat is the true
unit of replication here (pseudoreplication caveat, see
project_neural_changes_training_day_2026_10 memory). Solid line = Experimental
group, dashed = Control/Familiar group (README.md "Animals & groups"), so the
CTA-relevant distinction is visible without a 5th visual channel.

Colors are the dataviz-skill categorical palette's first slots (fixed order,
validated CVD-safe for a line chart's adjacent-pairlist use), assigned by
rat in alphabetical order -- not cycled, not reused across unrelated charts.

Usage (peleg_env is enough -- no openpyxl write, no zetapy):
    python plot_fano_block_trend.py [GC|S1|undefined]
Defaults to GC.

Writes locally to /tmp/, then copies to Z:\\Peleg\\CrossRatAnalysis\\.
"""
import sys
import os

import numpy as np
import openpyxl
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import NAS_PELEG, copy_to_share_safely
from fano_factor_total import CROSS_RAT_FANO_DIR

SHEET_GROUP = {'Experiment': 'Experiment', 'Control': 'Control'}

# dataviz-skill categorical palette, fixed order (slots 1-4): blue, orange,
# aqua, yellow -- validated CVD-safe for a line chart's adjacent-pairlist use.
# Slots 9-10 (brown, teal) are NOT part of the validated 8-slot set -- added
# 2026-11-08 when a 9th rat (MS25) got real GC data and silently fell off
# the end of this list (zip() truncates silently, no error) -- picked for
# visual distinctness only, not CVD-validated.
RAT_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948',
              '#8c564b', '#17a398']

SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"

# Display-only exclusion (Anan Moran's request via Peleg, 2026-11-08/09):
# a rat with very few units adds visual noise to a cross-rat comparison
# plot without much statistical value -- rule of thumb is <=12 neurons.
# This does NOT touch FanoFactorTotal.xlsx itself (every rat's real data
# stays in the table) -- it only hides these rats from this plot's lines.
# MS15 (GC n=2), MS22 (GC n=12, S1 n=7), MS24 (GC n=5, no S1 units) are
# Peleg's explicit list, 2026-11-09 -- see project_anan_meeting_2026_11_08
# memory. Revisit if a rat's unit count changes (e.g. MS24/MS25's
# provisional gc_bounds_um gets finalized).
EXCLUDED_FROM_DISPLAY = {'MS15', 'MS22', 'MS24'}


def load_region_rows(region):
    """Returns {rat: {'group': ..., 'blocks': [[block1 vals], ..., [block7 vals]]}}."""
    xlsx_path = f"{CROSS_RAT_FANO_DIR}/FanoFactorTotal.xlsx"
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
            if r[idx['region']] != region:
                continue
            rat = r[idx['rat']]
            if rat in EXCLUDED_FROM_DISPLAY:
                continue
            entry = by_rat.setdefault(rat, {'group': group, 'blocks': [[] for _ in range(7)]})
            for i, field in enumerate(block_fields):
                val = r[idx[field]]
                if val not in (None, ""):
                    entry['blocks'][i].append(val)
    return by_rat


def main():
    args = sys.argv[1:]
    normalize = '--normalize' in args
    args = [a for a in args if a != '--normalize']
    region = args[0] if args else 'GC'

    by_rat = load_region_rows(region)
    if not by_rat:
        raise SystemExit(f"No units labeled '{region}' in any sheet of FanoFactorTotal.xlsx")

    assert len(RAT_COLORS) >= len(by_rat), (
        f"{len(by_rat)} rats have '{region}' data but RAT_COLORS only has "
        f"{len(RAT_COLORS)} slots -- zip() would silently drop the rest. Add more colors.")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.set_facecolor(SURFACE)
    ax.margins(x=0)
    for i in range(1, 7):
        ax.axvline(i + 0.5, color=GRIDLINE, linewidth=0.8, zorder=1)
    if normalize:
        ax.axhline(100, color=GRIDLINE, linewidth=1.2, linestyle='--', zorder=1)

    blocks_x = np.arange(1, 8)
    for color, rat in zip(RAT_COLORS, sorted(by_rat)):
        entry = by_rat[rat]
        means = [np.mean(v) if v else np.nan for v in entry['blocks']]
        sems = [np.std(v, ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0 for v in entry['blocks']]
        n_units = max(len(v) for v in entry['blocks'])

        if normalize:
            # % of Block 1 (Anan Moran's request via Peleg, 2026-11-09): every
            # rat's own Block 1 mean becomes 100%, so absolute-level
            # differences between rats (e.g. MS25 ~5 vs MS11 ~1.7) don't hide
            # the shape of each rat's own trend. SEM rescaled by the same
            # factor so error bars stay proportional, not the raw-units size.
            baseline = means[0]
            if not baseline or np.isnan(baseline):
                print(f"[SKIP] {rat}: no valid Block 1 mean to normalize against")
                continue
            means = [100 * m / baseline for m in means]
            sems = [100 * s / baseline for s in sems]

        linestyle = '-' if entry['group'] == 'Experiment' else '--'
        label = f"{rat} ({'Exp' if entry['group'] == 'Experiment' else 'Ctrl'}, n={n_units})"
        ax.errorbar(blocks_x, means, yerr=sems, color=color, linestyle=linestyle,
                     marker='o', markersize=6, linewidth=2, capsize=3, label=label, zorder=3)

    ax.set_xticks(blocks_x)
    ax.set_xlabel("Training-day block", fontsize=10.5, color=SECONDARY_INK)
    if normalize:
        ax.set_ylabel("Fano factor (% of Block 1)", fontsize=10.5, color=SECONDARY_INK)
        title_suffix = " \u2014 normalized to Block 1 = 100%"
    else:
        ax.set_ylabel("Fano factor (Var/Mean, 1s bins, 4min pre-block)", fontsize=10.5, color=SECONDARY_INK)
        title_suffix = ""
    ax.set_title(f"Fano factor across Training-day blocks \u2014 {region} population (mean \u00b1 SEM per rat)"
                 f"{title_suffix}",
                 fontsize=12, color=PRIMARY_INK, pad=14, loc='left', fontweight='medium')
    ax.tick_params(colors=MUTED_INK)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('left', 'bottom'):
        ax.spines[spine].set_color(GRIDLINE)
    ax.legend(frameon=False, fontsize=9.5, labelcolor=SECONDARY_INK, loc='upper left',
              bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()

    suffix = "_Normalized" if normalize else ""
    local_path = f"/tmp/FanoFactor_{region}_AllRats_Block1to7{suffix}.png"
    plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
    print(f"Wrote {local_path}")

    os.makedirs(CROSS_RAT_FANO_DIR, exist_ok=True)
    copy_to_share_safely(local_path, CROSS_RAT_FANO_DIR)
    print(f"Copied to {CROSS_RAT_FANO_DIR}/")


if __name__ == '__main__':
    main()
