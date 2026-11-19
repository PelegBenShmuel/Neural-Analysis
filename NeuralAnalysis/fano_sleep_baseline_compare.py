"""
2-point comparison -- Peleg's explicit design, 2026-11-10: x=0 is each
rat's ORIGINAL block1_fano (the standard 4min-pre-Block-1 Rest window,
already in FanoFactorTotal.xlsx), x=1 is the NEW sleep-anchored value
(fano_sleep_anchored_baseline.py's 4min window immediately after each
rat's first post-LiCl window with enough sleep in it). Normalized to
x=0 = 100% per rat. First, minimal step of Anan Moran's request #5 --
"ואז נראה מה קורה" (then we'll see what happens) -- not yet a full
trajectory.

Combines two already-computed sources rather than reloading spike data a
third time: block1_fano means read directly from FanoFactorTotal.xlsx,
the sleep-anchored values hardcoded from fano_sleep_anchored_baseline.py's
completed run (2026-11-10) -- rerun that script if the underlying data
ever changes rather than trusting this hardcoded copy indefinitely.

Same >=15-units-in-this-region display filter as plot_metric_block_trend.py.
"""
import os

import numpy as np
import matplotlib.pyplot as plt
import openpyxl

from fano_factor_total import CROSS_RAT_FANO_DIR
from plot_fano_block_trend import SHEET_GROUP, RAT_COLORS, SURFACE, PRIMARY_INK, SECONDARY_INK, MUTED_INK, GRIDLINE
from plot_metric_block_trend import MIN_UNITS_TO_DISPLAY
from MS_buzcode_analysis import copy_to_share_safely

# fano_sleep_anchored_baseline.py's completed output, 2026-11-10 (rat, region) -> (n, mean_ff)
SLEEP_ANCHORED = {
    ('MS09', 'GC'): (68, 2.552), ('MS09', 'S1'): (141, 2.761),
    ('MS11', 'GC'): (52, 2.333), ('MS11', 'S1'): (127, 3.617),
    ('MS14', 'S1'): (27, 2.818),
    ('MS15', 'GC'): (2, 1.806), ('MS15', 'S1'): (17, 1.733),
    ('MS18', 'GC'): (42, 2.765), ('MS18', 'S1'): (51, 2.985),
    ('MS20', 'GC'): (100, 2.278), ('MS20', 'S1'): (53, 2.879),
    ('MS21', 'GC'): (46, 1.549), ('MS21', 'S1'): (81, 1.860),
    ('MS25', 'GC'): (69, 4.958), ('MS25', 'S1'): (28, 5.286),
}


def block1_means():
    xlsx_path = f"{CROSS_RAT_FANO_DIR}/FanoFactorTotal.xlsx"
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    out = {}
    for sheet_name in SHEET_GROUP:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        header, data = rows[0], rows[1:]
        idx = {name: i for i, name in enumerate(header)}
        for r in data:
            if isinstance(r[idx['cluster']], str):
                continue
            rat, region = r[idx['rat']], r[idx['region']]
            if region not in ('GC', 'S1'):
                continue
            val = r[idx['block1_fano']]
            if val in (None, ''):
                continue
            out.setdefault((rat, region), []).append(val)
    return {k: np.mean(v) for k, v in out.items()}


def plot_region(ax, region, b1):
    ax.set_facecolor(SURFACE)
    ax.margins(x=0)
    ax.axhline(0, color=GRIDLINE, linewidth=1.2, linestyle='--', zorder=1)

    rats = sorted({rat for (rat, r) in SLEEP_ANCHORED if r == region
                    and SLEEP_ANCHORED[(rat, r)][0] >= MIN_UNITS_TO_DISPLAY})
    for color, rat in zip(RAT_COLORS, rats):
        n, post_sleep = SLEEP_ANCHORED[(rat, region)]
        baseline = b1.get((rat, region))
        if baseline is None or not baseline:
            continue
        # Block 1 = 0 (Peleg's explicit request, 2026-11-10): % CHANGE from
        # Block 1, not % OF Block 1 -- y0 is always exactly 0 for every
        # rat, y1 is how much higher/lower the post-sleep-window value is.
        y0, y1 = 0.0, 100 * (post_sleep / baseline - 1)
        ax.plot([0, 1], [y0, y1], color=color, marker='o', markersize=8,
                 linewidth=2.2, zorder=3, label=f"{rat} (n={n})")

    ax.set_xlim(0, 1.1)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Block 1\n(4min Rest)", "4min after\nqualifying sleep"],
                        fontsize=10, color=SECONDARY_INK)
    ax.set_title(f"{region}", fontsize=12, color=PRIMARY_INK, pad=14, loc='left', fontweight='medium')
    ax.tick_params(colors=MUTED_INK)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('left', 'bottom'):
        ax.spines[spine].set_color(GRIDLINE)
    ax.legend(frameon=False, fontsize=9, labelcolor=SECONDARY_INK, loc='best')


def main():
    # One combined figure, 2 side-by-side panels (GC | S1), same style as
    # fano_window_compare.py's per-rat GC/S1 panels -- Peleg's explicit
    # request, 2026-11-10 ("תחלק לי את הגרף שעשית ל-2 אוכלוסיות"), replacing
    # the two-separate-files version tried first.
    b1 = block1_means()
    fig, (ax_gc, ax_s1) = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
    plot_region(ax_gc, 'GC', b1)
    plot_region(ax_s1, 'S1', b1)
    ax_gc.set_ylabel("Fano factor (% change from Block 1)", fontsize=10.5, color=SECONDARY_INK)
    fig.suptitle("Fano factor — Block 1 vs. post-sleep-window (normalized)",
                 fontsize=13, color=PRIMARY_INK, x=0.02, ha='left', fontweight='medium')
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    local_path = "/tmp/FanoFactor_Block1_vs_SleepWindow_GC_S1.png"
    plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
    print(f"Wrote {local_path}")
    os.makedirs(CROSS_RAT_FANO_DIR, exist_ok=True)
    copy_to_share_safely(local_path, CROSS_RAT_FANO_DIR)
    print(f"Copied to {CROSS_RAT_FANO_DIR}/")


if __name__ == '__main__':
    main()
