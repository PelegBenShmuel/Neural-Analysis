"""
All-rats, real-time view of the Window Compare analysis -- Peleg's request,
2026-11-17. Window Compare (metric_window_compare.py) already tests, per
rat x region, whether the fixed 4min pre-block window differs from the
sleep-selected 5min window, pooling all 7 blocks into one paired Wilcoxon.
This script instead shows, per rat (one line, GC | S1 panels), how that
same per-block difference (fixed - sleep) moves across REAL time (hours
since LiCl, like metric_sleep_trajectory.py) rather than block number.

Reads the "Window Compare Pairs" sheet that metric_window_compare.py now
writes (one row per unit x block: fixed_value, sleep_value,
block_hour_since_licl) -- no spike-data reload needed, this is an xlsx-only
script. Only rats with >=MIN_UNITS_TO_DISPLAY units in a region (same
convention as every other all-rats plot) appear in that region's panel.

Usage (np_analysis): python metric_window_diff_trajectory.py <fano|fr|cv>
"""
import sys
import os
from collections import defaultdict

import numpy as np
import openpyxl
from openpyxl.styles import Font
import matplotlib.pyplot as plt

from plot_fano_block_trend import RAT_COLORS, SURFACE, PRIMARY_INK, SECONDARY_INK, MUTED_INK, GRIDLINE
from plot_metric_block_trend import METRIC_CONFIG, MIN_UNITS_TO_DISPLAY
from metric_sleep_trajectory import block1_means_and_counts
from MS_buzcode_analysis import copy_to_share_safely


def load_pairs(metric_cfg):
    xlsx_path = f"{metric_cfg['xlsx_dir']}/{metric_cfg['xlsx_name']}"
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb['Window Compare Pairs']
    rows = list(ws.iter_rows(values_only=True))
    header, data = rows[0], rows[1:]
    idx = {name: i for i, name in enumerate(header)}

    # {(rat, region): {block_index: {'hour': h, 'diffs': [fixed-sleep, ...]}}}
    by_rat_region_block = defaultdict(lambda: defaultdict(lambda: {'hour': None, 'diffs': []}))
    for r in data:
        rat, region = r[idx['rat']], r[idx['region']]
        block_i = r[idx['block_index']]
        entry = by_rat_region_block[(rat, region)][block_i]
        entry['hour'] = r[idx['block_hour_since_licl']]
        entry['diffs'].append(r[idx['fixed_value']] - r[idx['sleep_value']])
    return by_rat_region_block


def main():
    args = sys.argv[1:]
    if not args or args[0] not in METRIC_CONFIG:
        raise SystemExit(f"First argument must be a metric: {list(METRIC_CONFIG)}")
    metric = args[0]
    metric_cfg = METRIC_CONFIG[metric]

    by_rat_region_block = load_pairs(metric_cfg)
    rats = sorted({rat for (rat, _region) in by_rat_region_block})

    # Per-rat, per-region series + unit counts for the display filter and
    # for the data export below.
    series = {}   # (rat, region) -> [(hour, mean_diff, n), ...] sorted by hour
    counts_by_rat = {}
    all_rows = []
    for rat in rats:
        _baseline, counts = block1_means_and_counts(metric_cfg, rat)
        counts_by_rat[rat] = counts
        for region in ('GC', 'S1'):
            blocks = by_rat_region_block.get((rat, region), {})
            pts = []
            for block_i, entry in sorted(blocks.items()):
                diffs = entry['diffs']
                if not diffs:
                    continue
                mean_diff, n = float(np.mean(diffs)), len(diffs)
                pts.append((entry['hour'], mean_diff, n))
                all_rows.append({'rat': rat, 'region': region, 'block_index': block_i,
                                  'hour_since_licl': entry['hour'], 'n_units': n,
                                  'mean_diff_fixed_minus_sleep': mean_diff,
                                  'region_n_units_total': counts.get(region, 0)})
            series[(rat, region)] = pts

    fig, (ax_gc, ax_s1) = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    for ax, region in [(ax_gc, 'GC'), (ax_s1, 'S1')]:
        ax.set_facecolor(SURFACE)
        ax.margins(x=0)
        ax.axhline(0, color=GRIDLINE, linewidth=1.2, linestyle='--', zorder=1)

        plotted_rats = [rat for rat in rats if counts_by_rat[rat].get(region, 0) >= MIN_UNITS_TO_DISPLAY]

        for color, rat in zip(RAT_COLORS, plotted_rats):
            pts = series[(rat, region)]
            if not pts:
                continue
            xs = [h for h, _v, _n in pts]
            ys = [v for _h, v, _n in pts]
            n_max = max(n for _h, _v, n in pts)
            ax.plot(xs, ys, color=color, marker='o', markersize=6, linewidth=2,
                     zorder=3, label=f"{rat} (n={n_max})")

        ax.set_xlabel("Hours after LiCl injection", fontsize=10.5, color=SECONDARY_INK)
        ax.set_title(region, fontsize=12, color=PRIMARY_INK, pad=14, loc='left', fontweight='medium')
        ax.tick_params(colors=MUTED_INK)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        for spine in ('left', 'bottom'):
            ax.spines[spine].set_color(GRIDLINE)
        ax.legend(frameon=False, fontsize=8.5, labelcolor=SECONDARY_INK, loc='upper left',
                  bbox_to_anchor=(1.01, 1.0))
    ax_gc.set_ylabel(f"{metric_cfg['display_name']} difference (fixed window − sleep window)",
                      fontsize=10.5, color=SECONDARY_INK)
    fig.suptitle(f"All rats: {metric_cfg['display_name']} -- fixed vs. sleep-window difference, "
                 f"per block, over real time",
                 fontsize=13, color=PRIMARY_INK, x=0.02, ha='left', fontweight='medium')
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    local_path = f"/tmp/{metric_cfg['out_prefix']}_AllRats_WindowDiffTrajectory.png"
    plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
    print(f"Wrote {local_path}")
    os.makedirs(metric_cfg['xlsx_dir'], exist_ok=True)
    copy_to_share_safely(local_path, metric_cfg['xlsx_dir'])
    print(f"Copied to {metric_cfg['xlsx_dir']}/")

    # Save the underlying (rat, region, block) diff data -- standing rule,
    # 2026-11-17: every calculation saves its data, not just the plot.
    xlsx_path = f"{metric_cfg['xlsx_dir']}/{metric_cfg['xlsx_name']}"
    wb = openpyxl.load_workbook(xlsx_path)
    sheet_name = "Window Diff Trajectory"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)
    header = ["rat", "region", "block_index", "hour_since_licl", "n_units",
              "mean_diff_fixed_minus_sleep", "region_n_units_total"]
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in all_rows:
        ws.append([row['rat'], row['region'], row['block_index'], round(row['hour_since_licl'], 4),
                   row['n_units'], round(row['mean_diff_fixed_minus_sleep'], 6), row['region_n_units_total']])
    for col_idx, field in enumerate(header, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(14, len(field) + 2)

    local_xlsx = f"/tmp/{metric_cfg['xlsx_name']}"
    wb.save(local_xlsx)
    copy_to_share_safely(local_xlsx, metric_cfg['xlsx_dir'])
    print(f"Added '{sheet_name}' sheet to {xlsx_path}")


if __name__ == '__main__':
    main()
