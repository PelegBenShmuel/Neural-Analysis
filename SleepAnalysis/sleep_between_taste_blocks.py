"""
sleep_between_taste_blocks.py -- cross-rat comparison of how much each rat
slept in the 6 gaps between the Training day's 7 taste-delivery blocks (gap i
= block i's last tastant to block i+1's first tastant).

Block boundaries come from derive_training_blocks() in MS_buzcode_analysis.py
(gap-detection on raw taste-event timestamps, anchored on licl_time_s) --
not re-derived here. Called with its sorted_min/sorted_max left at their
default -inf/+inf: that check only guards against a spike-sorted window not
covering the full Training day, and this script never touches spike data, so
every rat in ANIMAL_KEYS qualifies -- not just the 3 with Kilosort output
(see feedback_no_script_duplication memory).

For each rat and each inter-block gap, reports: gap duration, NREM/REM/total
sleep time within it, and % of the gap spent asleep (raw minutes alone isn't
comparable since gap length varies across rats and across gaps). Sleep
states come from each rat's gap-filled <animal>_TrainingDay.SleepState.
states.mat (same source training_day_sleep_state_extraction.py / sleep_char.py
/ total_sleep_rat.py already use), not the raw buzcode bout-interval tables --
see nearest_sleep_bout.py's docstring for why the gap-filled point states are
the trusted source.

Usage: python sleep_between_taste_blocks.py

Writes locally to /tmp/sleep_between_taste_blocks first, then copies to
Z:\\Peleg\\Cross_Rat_Sleep_Analysis\\ (same shared folder total_sleep_rat.py
uses), verified by size.
"""
import os
import sys
import csv

import numpy as np
import scipy.io as sio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from MS_buzcode_analysis import ANIMALS, copy_to_share_safely, NAS_PELEG, derive_training_blocks
from total_sleep_rat import ANIMAL_KEYS, mat_path_for

STATE_CODE = {'WAKE': 1, 'NREM': 3, 'REM': 5}
N_GAPS = 6


def load_cut_states(mat_path):
    d = sio.loadmat(mat_path)
    t = np.array(d['t']).flatten().astype(float)
    states = np.array(d['states']).flatten().astype(int)
    return t, states


def sleep_in_window(t, states, t0, t1):
    mask = (t >= t0) & (t < t1)
    if not mask.any():
        return 0.0, 0.0, 0.0, 0.0
    t_seg, st_seg = t[mask], states[mask]
    dt = np.diff(t_seg, append=t1)
    nrem_s = dt[st_seg == STATE_CODE['NREM']].sum()
    rem_s = dt[st_seg == STATE_CODE['REM']].sum()
    span_s = dt.sum()
    return nrem_s, rem_s, nrem_s + rem_s, span_s


def load_all_taste_events(cfg):
    arrays = [np.loadtxt(p) for p in cfg['taste_files'].values() if os.path.exists(p)]
    return np.sort(np.concatenate(arrays))


def main():
    out_dir = '/tmp/sleep_between_taste_blocks'
    os.makedirs(out_dir, exist_ok=True)

    rows = []
    per_rat_pct = {}
    per_rat_min = {}

    for key in ANIMAL_KEYS:
        cfg = ANIMALS[key]
        animal, mat_path = mat_path_for(key)
        if not os.path.exists(mat_path):
            print(f'{animal}: {mat_path} not found -- skipping')
            continue
        if cfg.get('licl_time_s') is None:
            print(f'{animal}: no licl_time_s set -- no Training day blocks to find -- skipping')
            continue

        all_events = load_all_taste_events(cfg)
        try:
            blocks = derive_training_blocks(all_events, cfg['licl_time_s'])
        except AssertionError as e:
            print(f'{animal}: could not derive Training-day blocks ({e}) -- skipping')
            continue

        t, states = load_cut_states(mat_path)
        pct_row, min_row = [], []
        for gap_i in range(N_GAPS):
            t0 = blocks[gap_i][1]       # end of block gap_i+1
            t1 = blocks[gap_i + 1][0]   # start of block gap_i+2
            nrem_s, rem_s, sleep_s, span_s = sleep_in_window(t, states, t0, t1)
            pct = 100 * sleep_s / span_s if span_s > 0 else np.nan
            rows.append(dict(
                animal=animal, gap=gap_i + 1, gap_start_s=round(t0, 1), gap_end_s=round(t1, 1),
                gap_duration_min=round(span_s / 60, 2),
                nrem_min=round(nrem_s / 60, 2), rem_min=round(rem_s / 60, 2),
                sleep_min=round(sleep_s / 60, 2), pct_asleep=round(pct, 1),
            ))
            pct_row.append(pct)
            min_row.append(sleep_s / 60)
        per_rat_pct[animal] = pct_row
        per_rat_min[animal] = min_row
        print(f'{animal}: ' + '  '.join(f'Gap{i+1}={m:.1f}min({p:.0f}%)'
                                         for i, (m, p) in enumerate(zip(min_row, pct_row))))

    if not rows:
        print('No rats had usable data -- nothing to summarize.')
        return

    csv_path = os.path.join(out_dir, 'sleep_between_taste_blocks.csv')
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f'\nTable saved -> {csv_path}')

    # ── Plot: grouped bars, minutes asleep (left) + % of gap asleep (right) ──
    animals = list(per_rat_min.keys())
    x = np.arange(N_GAPS)
    width = 0.8 / len(animals)
    colors = plt.get_cmap('tab20').colors

    fig, (ax_min, ax_pct) = plt.subplots(1, 2, figsize=(16, 6))
    for i, animal in enumerate(animals):
        offset = (i - len(animals) / 2) * width + width / 2
        color = colors[i % len(colors)]
        ax_min.bar(x + offset, per_rat_min[animal], width, label=animal, color=color)
        ax_pct.bar(x + offset, per_rat_pct[animal], width, label=animal, color=color)

    gap_labels = [f'Gap {i+1}\n(Blk{i+1}\u2192{i+2})' for i in range(N_GAPS)]

    ax_min.set_xticks(x)
    ax_min.set_xticklabels(gap_labels)
    ax_min.set_ylabel('Minutes asleep')
    ax_min.set_title('Sleep time between taste-delivery blocks', fontsize=11)
    ax_min.spines[['top', 'right']].set_visible(False)

    ax_pct.set_xticks(x)
    ax_pct.set_xticklabels(gap_labels)
    ax_pct.set_ylabel('% of gap spent asleep')
    ax_pct.set_ylim(0, 100)
    ax_pct.set_title("Same data, normalized by each gap's own duration", fontsize=11)
    ax_pct.spines[['top', 'right']].set_visible(False)
    ax_pct.legend(loc='upper left', ncol=2, fontsize=8, framealpha=0.85)

    fig.suptitle('Sleep between Training-day taste blocks, all rats', fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    png_path = os.path.join(out_dir, 'sleep_between_taste_blocks.png')
    fig.savefig(png_path, dpi=170, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'Plot saved -> {png_path}')

    nas_dir = f'{NAS_PELEG}/Cross_Rat_Sleep_Analysis'
    os.makedirs(nas_dir, exist_ok=True)
    for p in (csv_path, png_path):
        copy_to_share_safely(p, nas_dir)
    print(f'Copied to the share -> {nas_dir}')


if __name__ == '__main__':
    main()
