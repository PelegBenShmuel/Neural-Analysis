"""
sleep_char.py -- sleep-bout-duration and hourly-sleep-distribution
characterization for a single animal's Training-day sleep classification
(the 24h, 9AM-9AM cut produced by training_day_sleep_state_extraction.py).

Reads <animal>_Training_Day/<session>_TrainingDay.SleepState.states.mat from
Z:\\Peleg and reports:
  1. Sleep-bout-duration histogram -- how many *sleep* bouts (continuous
     NREM+REM stretches -- i.e. anything that isn't WAKE, merged across
     NREM<->REM transitions) fall in 0-5min / 5-10min / 10-20min / 20+min
     bins.
  2. Hourly sleep amount -- how many minutes of sleep fell in each of the 24
     clock hours of the Training day, plus each hour's % of that day's TOTAL
     sleep time (e.g. "18% of all sleep happened in the first hour"), and a
     final Total row/line summing to the day's total sleep. This is a
     different question from % of each hour spent asleep, which is already
     covered by training_day_sleep_state_extraction.py's phase-composition
     plot.
  3. Hourly hypnograms -- 24 SEPARATE per-hour hypnogram PNGs (one round
     hour per file, 09:00 on the LiCl day through 09:00 the next day),
     styled like MS_buzcode_analysis.py's own per-hour hypnogram panel
     (same WAKE/NREM/REM color scheme, 10-min HH:MM x-ticks, taste-event and
     LiCl markers) -- matches that script's one-file-per-hour convention.

Reuses per-animal config (session name, buzcode_analysis dir -> derives the
Training_Day dir the same way training_day_sleep_state_extraction.py does)
from MS_buzcode_analysis.py's ANIMALS dict, and load_taste_events /
STATE_Y/STATE_COL/STATE_LBL from the other two scripts -- see
feedback_no_script_duplication memory. Only animals that already have a
Training-day cut (see that script) can be characterized here.

Usage: python sleep_char.py [ANIMAL]   (default: MS08)

Writes locally to /tmp/<animal>_sleep_char first:
  - <animal>_sleep_bout_bins.csv
  - <animal>_hourly_sleep_pct.csv
  - <animal>_sleep_char.png (bout-bin bar chart + hourly-% bar chart)
  - <animal>_hourly_hypnogram_01.png .. _24.png (one hypnogram per round hour)
Then copies all of these into the SAME Z:\\Peleg\\<animal>\\<animal>_Training_Day\\
folder the input file came from, verified by size (per Peleg's explicit ask
to keep this analysis's output next to its source).
"""
import sys
import os
import csv
from datetime import timedelta, datetime

import numpy as np
import scipy.io as sio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mpl_lines

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from MS_buzcode_analysis import (ANIMALS, copy_to_share_safely, plain_label,
                                  STATE_Y, STATE_COL, STATE_LBL)
from training_day_sleep_state_extraction import load_taste_events

STATE_CODE = {'WAKE': 1, 'NREM': 3, 'REM': 5}
SLEEP_CODES = (STATE_CODE['NREM'], STATE_CODE['REM'])

BOUT_BINS = [
    ('0-5 min',   0.0,   300.0),
    ('5-10 min',  300.0, 600.0),
    ('10-20 min', 600.0, 1200.0),
    ('20+ min',   1200.0, np.inf),
]


def mat_str(value):
    """scipy.io.savemat/loadmat round-trips a plain Python str as a nested
    length-1 array; unwrap it back to a plain str."""
    arr = np.array(value)
    while arr.dtype == object or arr.ndim > 0:
        arr = arr[0]
    return str(arr)


def load_training_day_mat(mat_path):
    d = sio.loadmat(mat_path)
    t = np.array(d['t']).flatten().astype(float)
    states = np.array(d['states']).flatten().astype(int)
    window_start_s = float(np.array(d['window_start_s']).flatten()[0])
    session = mat_str(d['session'])
    rec_start = datetime.fromisoformat(mat_str(d['rec_start']))
    return t, states, window_start_s, session, rec_start


def sleep_bouts(t, states):
    """Contiguous runs of NREM/REM -- merged across NREM<->REM transitions,
    split only by WAKE/undefined -- i.e. "sleep bouts" as a single category,
    not the separate per-state (NREM-only / REM-only) buzcode bout tables."""
    dt = np.diff(t, append=t[-1] + (t[-1] - t[-2] if len(t) > 1 else 1.0))
    is_sleep = np.isin(states, SLEEP_CODES)
    change = np.where(np.diff(is_sleep.astype(int)) != 0)[0]
    starts = np.concatenate(([0], change + 1))
    stops = np.concatenate((change, [len(is_sleep) - 1]))

    durations = [dt[s:e + 1].sum() for s, e in zip(starts, stops) if is_sleep[s]]
    return np.array(durations), is_sleep, dt


def bout_duration_table(durations):
    rows = []
    total_n, total_s = len(durations), durations.sum()
    for label, lo, hi in BOUT_BINS:
        mask = (durations >= lo) & (durations < hi)
        n = int(mask.sum())
        s = float(durations[mask].sum())
        rows.append(dict(
            bin=label, n_bouts=n, total_seconds=round(s, 1), total_minutes=round(s / 60, 2),
            pct_of_bouts=round(100 * n / total_n, 1) if total_n else 0.0,
            pct_of_sleep_time=round(100 * s / total_s, 1) if total_s else 0.0,
        ))
    return rows, total_n, total_s


def hourly_sleep_pct(t, dt, is_sleep, window_start_s):
    hour_edges = window_start_s + np.arange(25) * 3600
    per_hour_s = np.array([
        dt[(t >= hour_edges[k]) & (t < hour_edges[k + 1]) & is_sleep].sum()
        for k in range(24)
    ])
    total_s = per_hour_s.sum()
    pct = 100 * per_hour_s / total_s if total_s > 0 else np.zeros_like(per_hour_s)
    return per_hour_s, pct


def plot_hourly_hypnograms(animal, session, cfg, t, states, rec_start, window_start_s, out_dir):
    """24 SEPARATE per-hour hypnogram PNGs for the Training day (09:00 on
    the LiCl day through 09:00 the next day, one round hour per file) --
    styled like MS_buzcode_analysis.py's own per-hour hypnogram panel (same
    STATE_Y/STATE_COL/STATE_LBL scheme, 10-min x-ticks in HH:MM, taste-event
    and LiCl markers), matching that script's one-file-per-hour convention
    rather than a single combined grid (Peleg's explicit request, 2026-10-08,
    superseding the combined-grid version tried first)."""
    taste_events = load_taste_events(cfg)
    licl_time_s = cfg.get('licl_time_s')
    out_paths = []

    for hour in range(24):
        t0 = window_start_s + hour * 3600
        t1 = t0 + 3600
        mask = (t >= t0) & (t < t1)
        t_seg, st_seg = t[mask], states[mask]
        if len(t_seg) == 0:
            continue

        hour_start = rec_start + timedelta(seconds=t0)
        hour_end = rec_start + timedelta(seconds=t1)
        tick_pos = [t0 + m * 600 for m in range(7)]
        tick_lbl = [(rec_start + timedelta(seconds=p)).strftime('%H:%M') for p in tick_pos]
        date_s = hour_start.strftime('%Y-%m-%d')
        time_lbl = f"{hour_start.strftime('%H:%M')} - {hour_end.strftime('%H:%M')}"

        fig, ax = plt.subplots(figsize=(14, 3.2))
        fig.suptitle(f'{session} -- {date_s}  {time_lbl}  (hour {hour + 1}/24)',
                     fontsize=12, fontweight='bold')

        for i in range(len(t_seg) - 1):
            s = int(st_seg[i])
            if s in STATE_Y:
                ax.fill_between([t_seg[i], t_seg[i + 1]], STATE_Y[s] - 0.45, STATE_Y[s] + 0.45,
                                 color=STATE_COL[s], linewidth=0)

        plotted = {}
        for t_sec, name, color in taste_events:
            if t0 <= t_sec <= t1:
                ax.axvline(t_sec, color=color, linestyle=':', linewidth=1.5, alpha=0.85)
                plotted[name] = color

        licl_in_view = licl_time_s is not None and t0 <= licl_time_s <= t1
        if licl_in_view:
            ax.axvline(licl_time_s, color='black', linewidth=2.2, zorder=10)

        ax.set_xlim(t0, t1)
        ax.set_xticks(tick_pos)
        ax.set_xticklabels(tick_lbl)
        ax.set_yticks([0, 1, 2])
        ax.set_yticklabels(['NREM', 'REM', 'WAKE'], fontsize=10)
        ax.set_ylim(-0.6, 2.6)
        ax.set_ylabel('State', fontsize=11)
        ax.set_xlabel('Time', fontsize=11)
        ax.grid(axis='x', linestyle='--', alpha=0.25)

        state_patches = [mpatches.Patch(color=STATE_COL[k], label=STATE_LBL[k]) for k in [1, 3, 5]]
        state_legend = ax.legend(handles=state_patches, loc='upper right', ncol=3,
                                  fontsize=9, framealpha=0.7)
        ax.add_artist(state_legend)
        if plotted or licl_in_view:
            legend_handles = [mpatches.Patch(color=c, label=n) for n, c in plotted.items()]
            if licl_in_view:
                legend_handles.append(mpl_lines.Line2D([0], [0], color='black', linewidth=2.2,
                                                         label='LiCl injection'))
            ax.legend(handles=legend_handles, loc='upper left', ncol=len(legend_handles),
                      fontsize=8, framealpha=0.7, title='Taste / event')

        plt.tight_layout()
        out = os.path.join(out_dir, f'{animal}_hourly_hypnogram_{hour + 1:02d}.png')
        fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        out_paths.append(out)

    print(f'{len(out_paths)} hourly hypnogram PNGs saved -> {out_dir}')
    return out_paths


def main():
    animal_key = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal_key]
    # plain_label() on both the key and the session name: some rats (e.g.
    # MS18, MS20) only have a _videocorr-suffixed ANIMALS key at all, so the
    # key itself needs collapsing for folder naming, same as the session
    # name needs collapsing to match the filename
    # training_day_sleep_state_extraction.py actually wrote (see its
    # save_training_day_mat for the matching logic).
    animal = plain_label(animal_key)
    nas_dir = os.path.join(os.path.dirname(cfg['out_dir']), f'{animal}_Training_Day')
    session_label = plain_label(cfg['session'])
    mat_path = os.path.join(nas_dir, f'{session_label}_TrainingDay.SleepState.states.mat')
    if not os.path.exists(mat_path):
        print(f'{mat_path} not found -- run training_day_sleep_state_extraction.py '
              f'for {animal} first.')
        return

    print(f'=== Sleep characterization: {animal} ===')
    print(f'Reading {mat_path}')
    t, states, window_start_s, session, rec_start = load_training_day_mat(mat_path)

    durations, is_sleep, dt = sleep_bouts(t, states)
    bin_rows, total_n, total_s = bout_duration_table(durations)

    print(f'\n{len(durations)} total sleep bouts, {total_s/3600:.2f}h asleep total '
          f'({100*total_s/dt.sum():.1f}% of the 24h window)')
    print(f'\n{"Bin":<10s}{"n bouts":>10s}{"% bouts":>10s}{"total min":>12s}{"% time":>9s}')
    for r in bin_rows:
        print(f'{r["bin"]:<10s}{r["n_bouts"]:>10d}{r["pct_of_bouts"]:>9.1f}%'
              f'{r["total_minutes"]:>12.1f}{r["pct_of_sleep_time"]:>8.1f}%')

    per_hour_s, pct = hourly_sleep_pct(t, dt, is_sleep, window_start_s)

    hour_clock_labels = [(rec_start + timedelta(seconds=window_start_s + k * 3600)).strftime('%H:%M')
                         for k in range(24)]
    pct_header = "% of day's sleep"
    print(f'\n{"Hour":<6s}{"Clock":<8s}{"Sleep (min)":>13s}{pct_header:>18s}')
    for k in range(24):
        print(f'{k:<6d}{hour_clock_labels[k]:<8s}{per_hour_s[k]/60:>12.1f} {pct[k]:>16.1f}%')
    print(f'{"-"*45}')
    print(f'{"Total":<14s}{total_s/3600:>10.2f}h{"":>7s}{100.0:>16.1f}%')

    out_dir = f'/tmp/{animal}_sleep_char'
    os.makedirs(out_dir, exist_ok=True)

    bins_csv = os.path.join(out_dir, f'{animal}_sleep_bout_bins.csv')
    with open(bins_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(bin_rows[0].keys()))
        writer.writeheader()
        writer.writerows(bin_rows)
    print(f'\nBout-duration table saved -> {bins_csv}')

    hourly_csv = os.path.join(out_dir, f'{animal}_hourly_sleep_pct.csv')
    with open(hourly_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['hour_index', 'hour_start_clock', 'sleep_seconds', 'sleep_minutes', 'pct_of_total_sleep'])
        for k in range(24):
            writer.writerow([k, hour_clock_labels[k], f'{per_hour_s[k]:.1f}',
                              f'{per_hour_s[k]/60:.2f}', f'{pct[k]:.2f}'])
        writer.writerow(['Total', '', f'{total_s:.1f}', f'{total_s/60:.2f}', '100.00'])
    print(f'Hourly sleep-amount table saved -> {hourly_csv}')

    # ── Plot ──
    fig, (ax_bins, ax_hourly) = plt.subplots(1, 2, figsize=(15, 5.5))
    fig.suptitle(f'{animal} Experiment Day', fontsize=15, fontweight='bold')

    labels = [r['bin'] for r in bin_rows]
    counts = [r['n_bouts'] for r in bin_rows]
    bars = ax_bins.bar(labels, counts, color='#4a90d9', edgecolor='white')
    for b, r in zip(bars, bin_rows):
        ax_bins.text(b.get_x() + b.get_width() / 2, b.get_height() + max(counts) * 0.01,
                      f'{r["n_bouts"]}\n({r["pct_of_bouts"]:.0f}%)', ha='center', va='bottom', fontsize=9)
    ax_bins.set_ylabel('Number of sleep bouts')
    ax_bins.set_title('Sleep-bout duration distribution', fontsize=11)
    ax_bins.spines[['top', 'right']].set_visible(False)

    ax_hourly.bar(range(24), per_hour_s / 60, color='#5cb85c', edgecolor='white')
    ax_hourly.axhline(60, color='#888', linestyle='--', linewidth=1)
    ax_hourly.set_xticks(range(0, 24, 2))
    ax_hourly.set_xticklabels([hour_clock_labels[i] for i in range(0, 24, 2)], rotation=45, ha='right')
    ax_hourly.set_ylabel('Minutes asleep')
    ax_hourly.set_xlabel('Hour of Training day')
    ax_hourly.set_title(f"Sleep amount by hour (total: {total_s/3600:.2f}h/24h)", fontsize=11)
    ax_hourly.spines[['top', 'right']].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    png_path = os.path.join(out_dir, f'{animal}_sleep_char.png')
    fig.savefig(png_path, dpi=170, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'Plot saved -> {png_path}')

    hourly_hyp_paths = plot_hourly_hypnograms(animal, session, cfg, t, states,
                                               rec_start, window_start_s, out_dir)

    for local_path in (bins_csv, hourly_csv, png_path, *hourly_hyp_paths):
        copy_to_share_safely(local_path, nas_dir)
    print(f'\nCopied to the share -> {nas_dir}')


if __name__ == '__main__':
    main()
