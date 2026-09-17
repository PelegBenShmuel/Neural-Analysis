"""
sleep_char.py -- sleep-bout-duration and hourly-sleep-distribution
characterization for a single animal's Training-day sleep classification
(the 24h, 9AM-9AM cut produced by training_day_sleep_state_extraction.py).

Reads <animal>_Training_Day/<session>_TrainingDay.SleepState.states.mat from
Z:\\Peleg and reports:
  1. Sleep-bout-duration histogram -- how many *sleep* bouts (continuous
     NREM+REM stretches -- i.e. anything that isn't WAKE, merged across
     NREM<->REM transitions) fall in 0-2min / 2-5min / 5-10min bins (plus a
     >10min bin, added so no bout is silently dropped from the accounting).
  2. Hourly sleep distribution -- what % of the day's TOTAL sleep time fell
     in each of the 24 clock hours of the Training day (e.g. "18% of all
     sleep happened in the first hour") -- not the % of each hour spent
     asleep, which is a different question already covered by
     training_day_sleep_state_extraction.py's phase-composition plot.

Reuses per-animal config (session name, buzcode_analysis dir -> derives the
Training_Day dir the same way training_day_sleep_state_extraction.py does)
from MS_buzcode_analysis.py's ANIMALS dict -- see
feedback_no_script_duplication memory. Only animals that already have a
Training-day cut (see that script) can be characterized here.

Usage: python sleep_char.py [ANIMAL]   (default: MS08)

Writes locally to /tmp/<animal>_sleep_char first:
  - <animal>_sleep_bout_bins.csv
  - <animal>_hourly_sleep_pct.csv
  - <animal>_sleep_char.png (bout-bin bar chart + hourly-% bar chart)
Then copies all three into the SAME Z:\\Peleg\\<animal>\\<animal>_Training_Day\\
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from MS_buzcode_analysis import ANIMALS, copy_to_share_safely

STATE_CODE = {'WAKE': 1, 'NREM': 3, 'REM': 5}
SLEEP_CODES = (STATE_CODE['NREM'], STATE_CODE['REM'])

BOUT_BINS = [
    ('0-2 min',  0.0,   120.0),
    ('2-5 min',  120.0, 300.0),
    ('5-10 min', 300.0, 600.0),
    ('>10 min',  600.0, np.inf),
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


def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal]
    nas_dir = os.path.join(os.path.dirname(cfg['out_dir']), f'{animal}_Training_Day')
    mat_path = os.path.join(nas_dir, f'{cfg["session"]}_TrainingDay.SleepState.states.mat')
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
        writer.writerow(['hour_index', 'hour_start_clock', 'sleep_seconds', 'pct_of_total_sleep'])
        for k in range(24):
            hour_start = rec_start + timedelta(seconds=window_start_s + k * 3600)
            writer.writerow([k, hour_start.strftime('%H:%M'), f'{per_hour_s[k]:.1f}', f'{pct[k]:.2f}'])
    print(f'Hourly sleep-% table saved -> {hourly_csv}')

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

    hour_labels = [(rec_start + timedelta(seconds=window_start_s + k * 3600)).strftime('%H:%M')
                   for k in range(24)]
    ax_hourly.bar(range(24), pct, color='#5cb85c', edgecolor='white')
    ax_hourly.set_xticks(range(0, 24, 2))
    ax_hourly.set_xticklabels([hour_labels[i] for i in range(0, 24, 2)], rotation=45, ha='right')
    ax_hourly.set_ylabel('% of total sleep that day')
    ax_hourly.set_xlabel('Hour of Training day')
    ax_hourly.set_title("When the day's sleep happened", fontsize=11)
    ax_hourly.spines[['top', 'right']].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    png_path = os.path.join(out_dir, f'{animal}_sleep_char.png')
    fig.savefig(png_path, dpi=170, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'Plot saved -> {png_path}')

    for local_path in (bins_csv, hourly_csv, png_path):
        copy_to_share_safely(local_path, nas_dir)
    print(f'\nCopied to the share -> {nas_dir}')


if __name__ == '__main__':
    main()
