"""
total_sleep_rat.py -- cross-rat cumulative-sleep comparison, 0-16h after each
rat's own LiCl injection (not wall-clock), so all 12 lines share both a
common x=0 (injection moment) and a common x=16 endpoint.

Reads every rat's <animal>_Training_Day/<session>_TrainingDay.SleepState.states.mat
(the cut + undefined-gap-filled output of training_day_sleep_state_extraction.py)
and, for each, computes a running cumulative total of time spent asleep
(NREM+REM, same "sleep" convention as sleep_char.py's sleep_bouts()), counting
only from the injection moment onward (pre-injection sleep is excluded, not
just hidden off-screen -- the cumulative sum itself restarts at 0 at t=0).
Overlays all rats as separate lines on one figure -- lets you compare how
fast total sleep accumulates across rats post-injection, not just within one
rat (which the per-rat sleep_char.py / training_day_sleep_state_extraction.py
plots already cover).

Produces these views of the data (Peleg's requests, 2026-10-11):
  1. total_sleep_rat.png -- the full-resolution (per-second) cumulative curve,
     all 12 rats + a bold black Mean line + a mean/SD text box (total sleep
     over the full 16h, across rats).
  2. total_sleep_rat_hourly.png -- the same cumulative values but sampled at
     round hour marks only (0, 1, 2, ..., 16h post-injection), connected by
     straight lines -- a cleaner, lower-resolution read for comparing rats
     hour-by-hour rather than following every small step. Y-axis in minutes.
  3. total_sleep_rat_hour_01.png .. _16.png -- 16 SEPARATE single-hour-window
     plots (hour h covers [h-1, h) post-LiCl). Each one resets to y=0 at the
     start of its own hour (independent per-hour sleep amount, not a slice of
     the running total), Y-axis in minutes, plus a bold Mean line and a
     mean/SD text box (minutes slept that hour, across rats).
Reuses per-animal config (folder/session-name resolution) from
MS_buzcode_analysis.py's ANIMALS dict -- the same per-rat key list already
established for training_day_sleep_state_extraction.py / sleep_char.py (the
plain key for MS08/09/11, the final videocorr/manualTH variant key for the
rest, since that's what actually holds each rat's final accepted scoring) --
see feedback_no_script_duplication memory.

Usage: python total_sleep_rat.py

Writes locally to /tmp/total_sleep_rat first, then copies all PNGs to
Z:\\Peleg\\Cross_Rat_Sleep_Analysis\\ (a new shared, not-per-rat folder,
since these plots span all animals), verified by size.
"""
import os
import sys

import numpy as np
import scipy.io as sio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from MS_buzcode_analysis import ANIMALS, copy_to_share_safely, plain_label, NAS_PELEG

STATE_CODE = {'WAKE': 1, 'NREM': 3, 'REM': 5}
SLEEP_CODES = (STATE_CODE['NREM'], STATE_CODE['REM'])
POST_LICL_HOURS = 16

# Same per-rat "which ANIMALS key holds the final accepted scoring" list used
# by the batch runs of training_day_sleep_state_extraction.py / sleep_char.py.
ANIMAL_KEYS = [
    'MS08', 'MS09', 'MS11',
    'MS14_videocorr', 'MS15_manualTH', 'MS18_videocorr', 'MS20_videocorr',
    'MS21_videocorr', 'MS22_videocorr', 'MS23_videocorr',
    'MS24_CTAtoExt_videocorr', 'MS25_manualTH_videocorr',
]


def mat_path_for(key):
    cfg = ANIMALS[key]
    animal = plain_label(key)
    nas_dir = os.path.join(os.path.dirname(cfg['out_dir']), f'{animal}_Training_Day')
    session_label = plain_label(cfg['session'])
    return animal, os.path.join(nas_dir, f'{session_label}_TrainingDay.SleepState.states.mat')


def load_training_day_mat(mat_path):
    d = sio.loadmat(mat_path)
    t = np.array(d['t']).flatten().astype(float)
    states = np.array(d['states']).flatten().astype(int)
    licl_time_s = float(np.array(d['licl_time_s']).flatten()[0])
    return t, states, licl_time_s


def cumulative_sleep_since_licl(t, states, licl_time_s):
    """Hours-since-LiCl + cumulative sleep-hours arrays, restricted to
    [0, POST_LICL_HOURS] and with the cumulative sum itself starting at 0 at
    t=0 (not carrying over any pre-injection sleep)."""
    t_rel_h = (t - licl_time_s) / 3600.0
    mask = (t_rel_h >= 0) & (t_rel_h <= POST_LICL_HOURS)
    t_rel_h = t_rel_h[mask]
    t_masked = t[mask]
    states_masked = states[mask]
    if len(t_masked) == 0:
        return np.array([]), np.array([])
    dt = np.diff(t_masked, append=t_masked[-1] + (t_masked[-1] - t_masked[-2] if len(t_masked) > 1 else 1.0))
    is_sleep = np.isin(states_masked, SLEEP_CODES)
    cum_sleep_h = np.cumsum(dt * is_sleep) / 3600.0
    return t_rel_h, cum_sleep_h


def sample_at_times(t_rel_h, cum_sleep_h, query_times):
    """Cumulative sleep value at each query time -- the value from the last
    sample at or before that time (a real reading of the step function, not
    an interpolated/smoothed one). query_times may be hour marks or a fine
    grid; same lookup either way."""
    out = []
    for q in query_times:
        idx = np.searchsorted(t_rel_h, q, side='right') - 1
        out.append(cum_sleep_h[idx] if idx >= 0 else 0.0)
    return np.array(out)


def add_mean_sd_box(ax, values, unit, fmt='{:.2f}'):
    """Text box (lower-right, out of the legend's way) reporting mean ± SD
    across rats, plus n -- Peleg's explicit preference (2026-10-11) over a
    shaded SD band, to keep the individual rat lines uncluttered."""
    values = np.asarray(values)
    mean, sd, n = values.mean(), values.std(ddof=1) if len(values) > 1 else 0.0, len(values)
    text = f'Mean: {fmt.format(mean)}{unit} \u00b1 {fmt.format(sd)}{unit}  (n={n})'
    ax.text(0.98, 0.03, text, transform=ax.transAxes, ha='right', va='bottom',
             fontsize=10, bbox=dict(boxstyle='round', facecolor='white', edgecolor='#888', alpha=0.9))


def plot_single_hour_windows(rat_lines, out_dir):
    """16 separate PNGs, one per hour window [h-1, h) post-LiCl -- each
    reset to y=0 at the start of its own window (independent per-hour sleep
    amount, not a slice of the running cumulative total), per Peleg's
    explicit choice, 2026-10-11. Each also gets a bold Mean line and a
    mean/SD text box (minutes slept that hour, across rats)."""
    out_paths = []
    for h in range(1, POST_LICL_HOURS + 1):
        t0, t1 = h - 1, h
        fig, ax = plt.subplots(figsize=(10, 6))
        final_vals_min = []
        fine_times = np.linspace(t0, t1, 61)  # every minute within the hour
        resampled = []
        for animal, color, t_rel_h, cum_sleep_h in rat_lines:
            mask = (t_rel_h >= t0) & (t_rel_h <= t1)
            if not mask.any():
                continue
            before_mask = t_rel_h < t0
            offset = cum_sleep_h[before_mask][-1] if before_mask.any() else 0.0
            window_min = (cum_sleep_h[mask] - offset) * 60
            ax.plot(t_rel_h[mask], window_min, label=animal, color=color, linewidth=1.5, alpha=0.85)
            final_vals_min.append(window_min[-1])
            resampled.append((sample_at_times(t_rel_h, cum_sleep_h, fine_times) - offset) * 60)
        if not final_vals_min:
            plt.close(fig)
            continue

        mean_traj = np.array(resampled).mean(axis=0)
        ax.plot(fine_times, mean_traj, color='black', linewidth=3, label='Mean', zorder=10)
        add_mean_sd_box(ax, final_vals_min, ' min', fmt='{:.1f}')

        ax.set_xlim(t0, t1)
        ax.set_ylim(0, 60)
        ax.set_xlabel('Hours since LiCl injection', fontsize=12)
        ax.set_ylabel('Sleep this hour (minutes)', fontsize=12)
        ax.set_title(f'Total Sleep per Rat -- hour {h} post-LiCl ({t0}-{t1}h)',
                     fontsize=13, fontweight='bold')
        ax.legend(loc='upper left', ncol=2, fontsize=8, framealpha=0.85)
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='both', linestyle='--', alpha=0.25)

        plt.tight_layout()
        out = os.path.join(out_dir, f'total_sleep_rat_hour_{h:02d}.png')
        fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        out_paths.append(out)

    print(f'{len(out_paths)} per-hour-window plots saved -> {out_dir}')
    return out_paths


def style_axes(ax, title, ylabel='Cumulative sleep (hours)'):
    ax.set_xlabel('Hours since LiCl injection', fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_xlim(0, POST_LICL_HOURS)
    ax.set_xticks(range(0, POST_LICL_HOURS + 1))
    ax.legend(loc='upper left', ncol=2, fontsize=9, framealpha=0.85)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='both', linestyle='--', alpha=0.25)


def main():
    out_dir = '/tmp/total_sleep_rat'
    os.makedirs(out_dir, exist_ok=True)
    colors = plt.get_cmap('tab20').colors
    hour_marks = np.arange(0, POST_LICL_HOURS + 1)
    fine_times = np.linspace(0, POST_LICL_HOURS, 16 * 60 + 1)  # every minute

    fig1, ax1 = plt.subplots(figsize=(13, 7.5))
    fig2, ax2 = plt.subplots(figsize=(13, 7.5))
    rat_lines = []
    final_totals_h = []

    print(f'{"Rat":<16s}{f"sleep in {POST_LICL_HOURS}h post-LiCl":>26s}')
    for i, key in enumerate(ANIMAL_KEYS):
        animal, mat_path = mat_path_for(key)
        if not os.path.exists(mat_path):
            print(f'{animal}: {mat_path} not found -- skipping')
            continue

        t, states, licl_time_s = load_training_day_mat(mat_path)
        t_rel_h, cum_sleep_h = cumulative_sleep_since_licl(t, states, licl_time_s)
        if len(t_rel_h) == 0:
            print(f'{animal}: no data in the {POST_LICL_HOURS}h post-LiCl window -- skipping')
            continue
        color = colors[i % len(colors)]
        rat_lines.append((animal, color, t_rel_h, cum_sleep_h))
        final_totals_h.append(cum_sleep_h[-1])

        ax1.plot(t_rel_h, cum_sleep_h, label=animal, color=color, linewidth=1.5, alpha=0.85)

        hourly_vals_min = sample_at_times(t_rel_h, cum_sleep_h, hour_marks) * 60
        ax2.plot(hour_marks, hourly_vals_min, label=animal, color=color, linewidth=1.5,
                 alpha=0.85, marker='o', markersize=4)

        print(f'{animal:<16s}{cum_sleep_h[-1]:>25.2f}h')

    mean_traj_h = np.array([sample_at_times(t_rel_h, cum_sleep_h, fine_times)
                             for _, _, t_rel_h, cum_sleep_h in rat_lines]).mean(axis=0)
    ax1.plot(fine_times, mean_traj_h, color='black', linewidth=3, label='Mean', zorder=10)
    add_mean_sd_box(ax1, final_totals_h, 'h')

    style_axes(ax1, f'Total Sleep per Rat -- {POST_LICL_HOURS}h post-LiCl injection (full resolution)')
    plt.figure(fig1.number)
    plt.tight_layout()
    png_path1 = os.path.join(out_dir, 'total_sleep_rat.png')
    fig1.savefig(png_path1, dpi=170, bbox_inches='tight', facecolor='white')
    plt.close(fig1)
    print(f'\nPlot saved -> {png_path1}')

    style_axes(ax2, f'Total Sleep per Rat -- {POST_LICL_HOURS}h post-LiCl injection (hourly resolution)',
               ylabel='Cumulative sleep (minutes)')
    plt.figure(fig2.number)
    plt.tight_layout()
    png_path2 = os.path.join(out_dir, 'total_sleep_rat_hourly.png')
    fig2.savefig(png_path2, dpi=170, bbox_inches='tight', facecolor='white')
    plt.close(fig2)
    print(f'Plot saved -> {png_path2}')

    hourly_window_paths = plot_single_hour_windows(rat_lines, out_dir)

    nas_dir = f'{NAS_PELEG}/Cross_Rat_Sleep_Analysis'
    os.makedirs(nas_dir, exist_ok=True)
    for p in (png_path1, png_path2, *hourly_window_paths):
        copy_to_share_safely(p, nas_dir)
    print(f'Copied to the share -> {nas_dir}')


if __name__ == '__main__':
    main()
