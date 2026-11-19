"""
Generalizes fano_sleep_trajectory.py to any of the 3 metrics (Fano factor,
Firing Rate, CV) -- Peleg's request, 2026-11-10 ("תעשה כזה בדיוק רק עם
Firing rate ו-Cv"), same exact design, just parameterized by
METRIC_CONFIG (plot_metric_block_trend.py) instead of copy-pasting
fano_sleep_trajectory.py twice.

x=0 is each rat's own Block 1 (already in <Metric>Total.xlsx). Every other
point is the 4min window immediately after one of that rat's qualifying
sleep windows (WINDOW_MINUTES with >MIN_SLEEP_MINUTES asleep,
non-overlapping, sliding search from LiCl through end of Training day).
Only rats with >=MIN_UNITS_TO_DISPLAY units in a region appear in that
panel. One block-marker set (first plotted rat, representative). No
sleep-window shading (Peleg's explicit call on the Fano version, carried
over here for consistency).

Usage (np_analysis): python metric_sleep_trajectory.py <fano|fr|cv> [RAT ...] [--window=N] [--sleep=N]
With no rat names, runs all "good" rats (>=15 units in GC or S1).
Defaults to a 30min window / >25min sleep.
"""
import sys
import os

import numpy as np
import openpyxl
from openpyxl.styles import Font
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import (ANIMALS, assign_regions, copy_to_share_safely,
                                  derive_training_blocks, load_spike_sorted_data)
from training_day_sleep_state_extraction import STATE_CODE, load_states, training_day_window
from training_day_response_phases import label_blocks
from fano_factor_total import RAT_KEYS, PRE_BLOCK_SECONDS, fano_of_window
from coefficient_of_variation import cv_of_window
from firing_rate_total import firing_rate_of_window
from plot_fano_block_trend import SHEET_GROUP, RAT_COLORS, SURFACE, PRIMARY_INK, SECONDARY_INK, MUTED_INK, GRIDLINE
from plot_metric_block_trend import METRIC_CONFIG, MIN_UNITS_TO_DISPLAY
from postlicl_sleep_window import good_rats

SLEEP_CODES = (STATE_CODE['NREM'], STATE_CODE['REM'])
STEP_S = 60
METRIC_FUNCS = {'fano': fano_of_window, 'cv': cv_of_window, 'fr': firing_rate_of_window}


def block1_means_and_counts(metric_cfg, rat):
    xlsx_path = f"{metric_cfg['xlsx_dir']}/{metric_cfg['xlsx_name']}"
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    col = f"block1{metric_cfg['col_suffix']}"
    out = {}
    for sheet_name in SHEET_GROUP:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        header, data = rows[0], rows[1:]
        idx = {name: i for i, name in enumerate(header)}
        for r in data:
            if isinstance(r[idx['cluster']], str) or r[idx['rat']] != rat:
                continue
            region = r[idx['region']]
            if region not in ('GC', 'S1'):
                continue
            val = r[idx[col]]
            if val not in (None, ''):
                out.setdefault(region, []).append(val)
    means = {region: np.mean(vals) for region, vals in out.items()}
    counts = {region: len(vals) for region, vals in out.items()}
    return means, counts


def find_qualifying_windows(cfg, window_minutes, min_sleep_minutes):
    licl_time_s = cfg['licl_time_s']
    _day_start, day_end, _wh0, _wh1 = training_day_window(cfg, licl_time_s)
    window_s, min_sleep_s = window_minutes * 60, min_sleep_minutes * 60

    t, states, _bouts = load_states(cfg['mat_file'])
    dt = np.diff(t, append=t[-1])
    is_sleep = np.isin(states, SLEEP_CODES)

    found = []
    start = licl_time_s
    while start + window_s <= day_end:
        end = start + window_s
        mask = (t >= start) & (t < end)
        sleep_s = dt[mask & is_sleep].sum()
        if sleep_s > min_sleep_s:
            found.append((start, end, sleep_s))
            start = end
        else:
            start += STEP_S
    return found


def trajectory_for_rat(metric_cfg, metric_func, rat, window_minutes, min_sleep_minutes):
    key = RAT_KEYS[rat]
    cfg = ANIMALS[key]
    licl_time_s = cfg['licl_time_s']

    baseline, counts = block1_means_and_counts(metric_cfg, rat)
    windows = find_qualifying_windows(cfg, window_minutes, min_sleep_minutes)
    print(f"{rat}: {len(windows)} qualifying {window_minutes}min windows (>{min_sleep_minutes}min sleep)")

    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_spike_sorted_data(cfg)
    training_blocks = derive_training_blocks(all_events, licl_time_s)
    block_labels = label_blocks(training_blocks)
    block1_t0 = block_labels[0][1][0]
    region_by_cluster = assign_regions(good_clusters, cfg, label_undefined=True)

    points = {'GC': [(block1_t0, 0.0)], 'S1': [(block1_t0, 0.0)]}
    # Per-window detail rows for export -- this script never persisted its
    # computed points anywhere before (only the final PNG); Peleg's request,
    # 2026-11-17, to save them for further computation.
    detail_rows = []
    for region in ('GC', 'S1'):
        if region in baseline:
            detail_rows.append({
                'rat': rat, 'region': region, 'point_type': 'block1', 'window_index': 0,
                'hour_since_licl': (block1_t0 - licl_time_s) / 3600,
                'window_start_s': block1_t0 - PRE_BLOCK_SECONDS, 'window_end_s': block1_t0,
                'sleep_duration_s': None, 'n_units': counts[region],
                'raw_value': baseline[region], 'pct_change_from_block1': 0.0,
            })

    for win_idx, (win_start, win_end, sleep_s) in enumerate(windows, start=1):
        values = {'GC': [], 'S1': []}
        for cid in good_clusters:
            region = region_by_cluster[cid]
            if region not in values:
                continue
            spikes = spike_times_samples[spike_clusters == cid] / sample_rate
            val = metric_func(spikes, win_end, win_end + PRE_BLOCK_SECONDS)
            if val is not None:
                values[region].append(val)
        for region, vals in values.items():
            if vals and region in baseline and baseline[region]:
                raw_mean = np.mean(vals)
                pct_change = 100 * (raw_mean / baseline[region] - 1)
                points[region].append((win_end, pct_change))
                detail_rows.append({
                    'rat': rat, 'region': region, 'point_type': 'sleep_window', 'window_index': win_idx,
                    'hour_since_licl': (win_end - licl_time_s) / 3600,
                    'window_start_s': win_start, 'window_end_s': win_end,
                    'sleep_duration_s': sleep_s, 'n_units': len(vals),
                    'raw_value': raw_mean, 'pct_change_from_block1': pct_change,
                })

    block_hours = [(t0 - licl_time_s) / 3600 for _label, (t0, _t1) in block_labels]
    points_h = {region: [((t - licl_time_s) / 3600, v) for t, v in pts] for region, pts in points.items()}
    return points_h, counts, block_hours, detail_rows


def main():
    args = sys.argv[1:]
    if not args or args[0] not in METRIC_CONFIG:
        raise SystemExit(f"First argument must be a metric: {list(METRIC_CONFIG)}")
    metric = args[0]
    metric_cfg = METRIC_CONFIG[metric]
    metric_func = METRIC_FUNCS[metric]

    window_minutes, min_sleep_minutes = 30, 25
    skip_plot = False
    rat_args = []
    for a in args[1:]:
        if a.startswith('--window='):
            window_minutes = int(a.split('=')[1])
        elif a.startswith('--sleep='):
            min_sleep_minutes = int(a.split('=')[1])
        elif a == '--skip-plot':
            skip_plot = True
        else:
            rat_args.append(a)
    rats = rat_args if rat_args else good_rats()

    all_points, all_counts, block_hours_by_rat = {}, {}, {}
    all_detail_rows = []
    for rat in rats:
        points_h, counts, block_hours, detail_rows = trajectory_for_rat(metric_cfg, metric_func, rat,
                                                             window_minutes, min_sleep_minutes)
        all_points[rat] = points_h
        all_counts[rat] = counts
        block_hours_by_rat[rat] = block_hours
        all_detail_rows.extend(detail_rows)

    if skip_plot:
        print("--skip-plot: leaving the existing PNG untouched, only exporting data")
    else:
        fig, (ax_gc, ax_s1) = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
        for ax, region in [(ax_gc, 'GC'), (ax_s1, 'S1')]:
            ax.set_facecolor(SURFACE)
            ax.margins(x=0)
            ax.axhline(0, color=GRIDLINE, linewidth=1.2, linestyle='--', zorder=1)

            representative_rat = rats[0]
            for i, bh in enumerate(block_hours_by_rat[representative_rat], start=1):
                ax.axvline(bh, color=MUTED_INK, linewidth=1, linestyle=':', zorder=2, alpha=0.6)
                ax.annotate(f"B{i}", (bh, 1), xycoords=('data', 'axes fraction'),
                            textcoords='offset points', xytext=(2, -12),
                            fontsize=8, color=MUTED_INK, ha='left')

            plotted_rats = [rat for rat in rats if all_counts[rat].get(region, 0) >= MIN_UNITS_TO_DISPLAY]
            for color, rat in zip(RAT_COLORS, plotted_rats):
                pts = all_points[rat][region]
                xs = [h for h, _v in pts]
                ys = [v for _h, v in pts]
                n = all_counts[rat][region]
                ax.plot(xs, ys, color=color, marker='o', markersize=6, linewidth=2,
                         zorder=3, label=f"{rat} (n={n})")

            ax.set_xlabel("Hours after LiCl injection", fontsize=10.5, color=SECONDARY_INK)
            ax.set_title(region, fontsize=12, color=PRIMARY_INK, pad=14, loc='left', fontweight='medium')
            ax.tick_params(colors=MUTED_INK)
            for spine in ('top', 'right'):
                ax.spines[spine].set_visible(False)
            for spine in ('left', 'bottom'):
                ax.spines[spine].set_color(GRIDLINE)
            ax.legend(frameon=False, fontsize=8.5, labelcolor=SECONDARY_INK, loc='upper left',
                      bbox_to_anchor=(1.01, 1.0))
        ax_gc.set_ylabel(f"{metric_cfg['display_name']} (% change from Block 1)", fontsize=10.5, color=SECONDARY_INK)
        fig.suptitle(f"All rats: {metric_cfg['display_name']} after each qualifying sleep window "
                     f"({window_minutes}min, >{min_sleep_minutes}min asleep)",
                     fontsize=13, color=PRIMARY_INK, x=0.02, ha='left', fontweight='medium')
        fig.tight_layout(rect=[0, 0, 1, 0.94])

        local_path = f"/tmp/{metric_cfg['out_prefix']}_AllRats_SleepTrajectory.png"
        plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
        print(f"Wrote {local_path}")
        os.makedirs(metric_cfg['xlsx_dir'], exist_ok=True)
        copy_to_share_safely(local_path, metric_cfg['xlsx_dir'])
        print(f"Copied to {metric_cfg['xlsx_dir']}/")

    # Save the underlying per-window data into a sheet of <Metric>Total.xlsx
    # -- full load so every other sheet (Experiment, Sleep Experiment,
    # Window Compare Wilcoxon, ...) is preserved untouched.
    xlsx_path = f"{metric_cfg['xlsx_dir']}/{metric_cfg['xlsx_name']}"
    wb = openpyxl.load_workbook(xlsx_path)
    sheet_name = "Sleep Trajectory"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)
    header = ["rat", "region", "point_type", "window_index", "hour_since_licl",
              "window_start_s", "window_end_s", "sleep_duration_s", "n_units",
              "raw_value", "pct_change_from_block1", "search_window_minutes", "min_sleep_minutes"]
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in all_detail_rows:
        ws.append([row['rat'], row['region'], row['point_type'], row['window_index'],
                   round(row['hour_since_licl'], 4), row['window_start_s'], row['window_end_s'],
                   row['sleep_duration_s'], row['n_units'], round(row['raw_value'], 6),
                   round(row['pct_change_from_block1'], 4), window_minutes, min_sleep_minutes])
    for col_idx, field in enumerate(header, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(14, len(field) + 2)

    local_xlsx = f"/tmp/{metric_cfg['xlsx_name']}"
    wb.save(local_xlsx)
    copy_to_share_safely(local_xlsx, metric_cfg['xlsx_dir'])
    print(f"Added '{sheet_name}' sheet to {xlsx_path}")


if __name__ == '__main__':
    main()
