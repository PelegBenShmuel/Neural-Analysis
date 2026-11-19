"""
Fano factor trajectory across real elapsed time (not block number) --
Peleg's request, 2026-11-10, extending the earlier 2-point
Block1-vs-sleep-window comparison into a full multi-point trajectory, for
ALL good rats on the same plot (GC | S1 panels), not just MS09.

x=0 is each rat's own Block 1 (hours after ITS OWN LiCl, its usual
4min-pre-block Fano value, already in FanoFactorTotal.xlsx) -- the
per-rat normalization baseline (0% change). Every other point is the 4min
window immediately AFTER one of that rat's qualifying sleep windows
(WINDOW_MINUTES with >MIN_SLEEP_MINUTES of sleep in it, non-overlapping,
sliding search from LiCl through the end of the Training day) --
x-position is that window's own real time (hours after LiCl), not a
sequential index, so gaps in time between sleep opportunities are visible.

Only rats with >=MIN_UNITS_TO_DISPLAY units in a given region appear in
that region's panel (same threshold as plot_metric_block_trend.py).
Taste-block markers (B1-B7) are drawn once using the first plotted rat's
own block timing as a representative guide -- real per-rat block times
differ only slightly (same protocol structure for everyone). Sleep-window
spans are NOT shaded (Peleg's explicit request, 2026-11-10 -- too
cluttered with multiple rats on one plot; still visible as the gap in time
between each point and the one before it).

One spike-data load per rat (not per window).

Usage (np_analysis): python fano_sleep_trajectory.py [RAT ...] [--window=N] [--sleep=N]
With no rat names, runs all "good" rats (>=15 units in GC or S1).
Defaults to a 30min window / >25min sleep (Peleg's last example, 2026-11-10).
"""
import sys
import os

import numpy as np
import openpyxl
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import (ANIMALS, assign_regions, copy_to_share_safely,
                                  derive_training_blocks, load_spike_sorted_data)
from training_day_sleep_state_extraction import STATE_CODE, load_states, training_day_window
from training_day_response_phases import label_blocks
from fano_factor_total import CROSS_RAT_FANO_DIR, RAT_KEYS, PRE_BLOCK_SECONDS, fano_of_window
from plot_fano_block_trend import SHEET_GROUP, RAT_COLORS, SURFACE, PRIMARY_INK, SECONDARY_INK, MUTED_INK, GRIDLINE
from plot_metric_block_trend import MIN_UNITS_TO_DISPLAY
from postlicl_sleep_window import good_rats

SLEEP_CODES = (STATE_CODE['NREM'], STATE_CODE['REM'])
STEP_S = 60


def block1_means_and_counts(rat):
    xlsx_path = f"{CROSS_RAT_FANO_DIR}/FanoFactorTotal.xlsx"
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
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
            val = r[idx['block1_fano']]
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


def trajectory_for_rat(rat, window_minutes, min_sleep_minutes):
    """Returns ({region: [(hour, pct_change), ...]}, {region: n_units}, block_hours)."""
    key = RAT_KEYS[rat]
    cfg = ANIMALS[key]
    licl_time_s = cfg['licl_time_s']

    baseline, counts = block1_means_and_counts(rat)
    windows = find_qualifying_windows(cfg, window_minutes, min_sleep_minutes)
    print(f"{rat}: {len(windows)} qualifying {window_minutes}min windows (>{min_sleep_minutes}min sleep)")

    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_spike_sorted_data(cfg)
    training_blocks = derive_training_blocks(all_events, licl_time_s)
    block_labels = label_blocks(training_blocks)
    block1_t0 = block_labels[0][1][0]
    region_by_cluster = assign_regions(good_clusters, cfg, label_undefined=True)

    points = {'GC': [(block1_t0, 0.0)], 'S1': [(block1_t0, 0.0)]}
    for win_start, win_end, sleep_s in windows:
        values = {'GC': [], 'S1': []}
        for cid in good_clusters:
            region = region_by_cluster[cid]
            if region not in values:
                continue
            spikes = spike_times_samples[spike_clusters == cid] / sample_rate
            ff = fano_of_window(spikes, win_end, win_end + PRE_BLOCK_SECONDS)
            if ff is not None:
                values[region].append(ff)
        for region, vals in values.items():
            if vals and region in baseline and baseline[region]:
                pct_change = 100 * (np.mean(vals) / baseline[region] - 1)
                points[region].append((win_end, pct_change))

    block_hours = [(t0 - licl_time_s) / 3600 for _label, (t0, _t1) in block_labels]
    points_h = {region: [((t - licl_time_s) / 3600, v) for t, v in pts] for region, pts in points.items()}
    return points_h, counts, block_hours


def main():
    args = sys.argv[1:]
    window_minutes = 30
    min_sleep_minutes = 25
    rat_args = []
    for a in args:
        if a.startswith('--window='):
            window_minutes = int(a.split('=')[1])
        elif a.startswith('--sleep='):
            min_sleep_minutes = int(a.split('=')[1])
        else:
            rat_args.append(a)
    rats = rat_args if rat_args else good_rats()

    all_points = {}
    all_counts = {}
    block_hours_by_rat = {}
    for rat in rats:
        points_h, counts, block_hours = trajectory_for_rat(rat, window_minutes, min_sleep_minutes)
        all_points[rat] = points_h
        all_counts[rat] = counts
        block_hours_by_rat[rat] = block_hours

    fig, (ax_gc, ax_s1) = plt.subplots(1, 2, figsize=(15, 6), sharey=True)
    for ax, region in [(ax_gc, 'GC'), (ax_s1, 'S1')]:
        ax.set_facecolor(SURFACE)
        ax.margins(x=0)
        ax.axhline(0, color=GRIDLINE, linewidth=1.2, linestyle='--', zorder=1)

        # Taste-block markers: one representative rat's block timing (real
        # per-rat times differ only slightly -- same protocol structure).
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
    ax_gc.set_ylabel("Fano factor (% change from Block 1)", fontsize=10.5, color=SECONDARY_INK)
    fig.suptitle(f"All rats: Fano factor after each qualifying sleep window "
                 f"({window_minutes}min, >{min_sleep_minutes}min asleep)",
                 fontsize=13, color=PRIMARY_INK, x=0.02, ha='left', fontweight='medium')
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    local_path = "/tmp/FanoFactor_AllRats_SleepTrajectory.png"
    plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
    print(f"Wrote {local_path}")
    os.makedirs(CROSS_RAT_FANO_DIR, exist_ok=True)
    copy_to_share_safely(local_path, CROSS_RAT_FANO_DIR)
    print(f"Copied to {CROSS_RAT_FANO_DIR}/")


if __name__ == '__main__':
    main()
