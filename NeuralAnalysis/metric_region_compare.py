"""
Generalizes plot_fano_region_compare.py to any of the 3 metrics (Fano
factor, Firing Rate, CV) -- Peleg's request, 2026-11-11 ("בדיוק את אותם
הגרפים רק ב-FR CV"), same design (per-rat small-multiples grid, GC vs S1
side by side within each rat's own panel), parameterized by METRIC_CONFIG
instead of copy-pasting.

Usage (np_analysis -- needs openpyxl, no spike-data reload, fast): python metric_region_compare.py <fano|fr|cv>
"""
import sys
import os

import numpy as np
import openpyxl
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import copy_to_share_safely
from plot_fano_block_trend import SHEET_GROUP, SURFACE, PRIMARY_INK, SECONDARY_INK, MUTED_INK, GRIDLINE
from plot_metric_block_trend import METRIC_CONFIG

REGION_COLORS = {'GC': '#2a78d6', 'S1': '#eb6834'}

RAT_ORDER = ['MS09', 'MS11', 'MS14', 'MS15', 'MS18', 'MS20', 'MS21', 'MS22', 'MS24', 'MS25']


def load_all_rows(metric_cfg):
    xlsx_path = f"{metric_cfg['xlsx_dir']}/{metric_cfg['xlsx_name']}"
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    block_fields = [f"block{i}{metric_cfg['col_suffix']}" for i in range(1, 8)]

    by_rat = {}
    for sheet_name, group in SHEET_GROUP.items():
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        header, data = rows[0], rows[1:]
        idx = {name: i for i, name in enumerate(header)}
        for r in data:
            cluster = r[idx['cluster']]
            if isinstance(cluster, str):
                continue
            region = r[idx['region']]
            if region not in REGION_COLORS:
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
    args = sys.argv[1:]
    metric = args[0] if args else 'fano'
    if metric not in METRIC_CONFIG:
        raise SystemExit(f"Unknown metric '{metric}'. Known: {list(METRIC_CONFIG)}")
    metric_cfg = METRIC_CONFIG[metric]

    by_rat = load_all_rows(metric_cfg)

    ncols = 3
    nrows = -(-len(RAT_ORDER) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols, 3.6 * nrows), sharex=True)
    axes = axes.flatten()
    blocks_x = np.arange(1, 8)

    for ax, rat in zip(axes, RAT_ORDER):
        ax.set_facecolor(SURFACE)
        ax.margins(x=0)
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
    fig.supylabel(metric_cfg['raw_ylabel'], fontsize=10.5, color=SECONDARY_INK)
    fig.suptitle(f"{metric_cfg['display_name']} by region, per rat — GC vs S1 (mean ± SEM)",
                 fontsize=13, color=PRIMARY_INK, x=0.02, ha='left', fontweight='medium')
    fig.tight_layout(rect=[0.02, 0.02, 1, 0.96])

    local_path = f"/tmp/{metric_cfg['out_prefix']}_PerRat_GCvsS1_Block1to7.png"
    plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
    print(f"Wrote {local_path}")

    os.makedirs(metric_cfg['xlsx_dir'], exist_ok=True)
    copy_to_share_safely(local_path, metric_cfg['xlsx_dir'])
    print(f"Copied to {metric_cfg['xlsx_dir']}/")


if __name__ == '__main__':
    main()
