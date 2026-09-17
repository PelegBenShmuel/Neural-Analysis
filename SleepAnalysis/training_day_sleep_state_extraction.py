"""
Training-day-only sleep-state classification: restricts the already-scored
buzcode WAKE/NREM/REM output to a 24h window for the Training/CTA day (Day 4,
the LiCl-pairing day) -- 9:00 AM on the day LiCl was injected through 9:00 AM
the following day, per Peleg's protocol convention -- and reports it against
the Arieli, Younis & Moran (2022) post-LiCl phase timeline (0-3h acquisition,
3-6h intermediate, 6-12h consolidation, 12-18h postconsolidation) plus a
pre-injection reference hour. This is the sleep-side counterpart to Peleg's
spike-level analysis, which is likewise scoped to Training day only (see
README.md's "Spike-level analysis" section).

Reuses per-animal config (paths, LFP channel, LiCl time) from
MS_buzcode_analysis.py's ANIMALS dict instead of redefining it -- see
feedback_no_script_duplication memory. Only animals with a known
licl_time_s have a Training day to isolate; others are skipped with a note
(e.g. MS11 is a hab-day-only recording, no CTA/LiCl event to anchor on). The
9AM-9AM window (see training_day_window()) assumes LiCl is injected after
9:00 AM local time, true for every animal scored so far -- if a future animal
were injected before 9:00 AM, the window would shift to start the previous
calendar day; sanity-check the printed window against the block-1 timing
before trusting it blindly for a new animal.

Usage: python training_day_sleep_state_extraction.py [ANIMAL]   (default: MS08)

Writes, locally to /tmp/<animal>_training_day first:
  - <session>_TrainingDay.SleepState.states.mat -- the buzcode WAKE/NREM/REM
    classification (timestamps + states + bout intervals), cut down to just
    the Training day window (see cut_training_day_states)
  - <animal>_training_day_hypnogram.png -- hypnogram + phase-composition plot
  - <animal>_training_day_phase_breakdown.csv -- per-phase WAKE/NREM/REM %s
Then copies all three onto the share, to a dedicated
Z:\\Peleg\\<animal>\\<animal>_Training_Day\\ folder (sibling of
<animal>_buzcode_analysis) -- see feedback_output_location memory: outputs
belong on the share, not just scratchpad.
"""
import sys
import os
import csv
import shutil
from datetime import timedelta

import h5py
import numpy as np
import scipy.io as sio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mpl_lines

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from MS_buzcode_analysis import ANIMALS, TASTE_COLORS, STATE_COL, STATE_LBL

STATE_CODE = {'WAKE': 1, 'NREM': 3, 'REM': 5}

# Phases relative to LiCl injection (Arieli, Younis & Moran 2022 timeline),
# plus a pre-injection reference hour for same-day baseline context.
PHASES = [
    ('Pre-injection (-1-0h)',    -1.0,  0.0),
    ('Acquisition (0-3h)',        0.0,  3.0),
    ('Intermediate (3-6h)',       3.0,  6.0),
    ('Consolidation (6-12h)',     6.0, 12.0),
    ('Postconsolidation (12-18h)', 12.0, 18.0),
]


def training_day_window(cfg, licl_time_s):
    """24h window: 9:00 AM on the calendar day LiCl was injected through 9:00
    AM the following day (Peleg's protocol convention -- an experiment day
    runs 9AM-to-9AM, not midnight-to-midnight). Returns
    (window_start_s, window_end_s, window_start_h, window_end_h), the last
    two in hours relative to licl_time_s so the rest of the script can keep
    plotting/binning relative to LiCl regardless of each animal's actual
    injection clock-time."""
    licl_dt = cfg['rec_start'] + timedelta(seconds=licl_time_s)
    day_start_dt = licl_dt.replace(hour=9, minute=0, second=0, microsecond=0)
    if licl_dt.hour < 9:
        day_start_dt -= timedelta(days=1)
    day_end_dt = day_start_dt + timedelta(days=1)

    window_start_s = (day_start_dt - cfg['rec_start']).total_seconds()
    window_end_s = (day_end_dt - cfg['rec_start']).total_seconds()
    window_start_h = (window_start_s - licl_time_s) / 3600.0
    window_end_h = (window_end_s - licl_time_s) / 3600.0
    return window_start_s, window_end_s, window_start_h, window_end_h


def load_states(mat_file):
    with h5py.File(mat_file, 'r') as f:
        t      = np.array(f['SleepState/idx/timestamps']).flatten()
        states = np.array(f['SleepState/idx/states']).flatten()
        bouts  = {name: np.array(f[f'SleepState/ints/{name}state'])
                  for name in STATE_CODE}
    return t, states, bouts


def load_taste_events(cfg):
    events = []
    for name, path in cfg['taste_files'].items():
        if not os.path.exists(path):
            continue
        for line in open(path):
            line = line.strip()
            if line:
                events.append((float(line), name, TASTE_COLORS[name]))
    return events


def phase_breakdown(t, states, bouts, licl_time_s):
    dt = np.diff(t, append=t[-1])
    rows = []
    for label, h0, h1 in PHASES:
        t0, t1 = licl_time_s + h0 * 3600, licl_time_s + h1 * 3600
        mask = (t >= t0) & (t < t1)
        span_s = dt[mask].sum()
        row = {'phase': label, 'hours_from_licl': f'{h0:+.0f}h to {h1:+.0f}h',
               'span_s': span_s}
        for name, code in STATE_CODE.items():
            state_s = dt[mask & (states == code)].sum()
            row[f'{name}_pct'] = 100 * state_s / span_s if span_s > 0 else np.nan
            iv = bouts[name]
            n_bouts = int(np.sum((iv[0] >= t0) & (iv[0] < t1)))
            row[f'{name}_n_bouts'] = n_bouts
        rows.append(row)
    return rows


def print_and_save_table(rows, animal, out_dir):
    print(f'\n{"Phase":<28s}{"WAKE%":>8s}{"NREM%":>8s}{"REM%":>8s}'
          f'{"REM bouts":>11s}')
    for r in rows:
        print(f'{r["phase"]:<28s}{r["WAKE_pct"]:>7.1f}%{r["NREM_pct"]:>7.1f}%'
              f'{r["REM_pct"]:>7.1f}%{r["REM_n_bouts"]:>11d}')

    csv_path = os.path.join(out_dir, f'{animal}_training_day_phase_breakdown.csv')
    fieldnames = ['phase', 'hours_from_licl', 'span_s',
                  'WAKE_pct', 'WAKE_n_bouts', 'NREM_pct', 'NREM_n_bouts',
                  'REM_pct', 'REM_n_bouts']
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'\nPhase-breakdown table saved -> {csv_path}')
    return csv_path


def plot_training_day(animal, cfg, t, states, taste_events, licl_time_s, window, out_dir):
    t0_abs, t1_abs, window_start_h, window_end_h = window
    mask = (t >= t0_abs) & (t < t1_abs)
    t_seg, st_seg = t[mask], states[mask]
    t_h = (t_seg - licl_time_s) / 3600.0   # hours relative to LiCl

    fig, (ax_hyp, ax_bar) = plt.subplots(
        2, 1, figsize=(16, 6.5), gridspec_kw={'height_ratios': [1.4, 1]})
    fig.suptitle(f'{cfg["session"]} -- Training day sleep classification '
                 f'(24h, 9AM-9AM; time relative to LiCl injection)', fontsize=13, fontweight='bold')

    # ── Hypnogram, hours relative to LiCl ──
    state_y = {1: 2, 3: 0, 5: 1}
    for i in range(len(t_seg) - 1):
        s = int(st_seg[i])
        if s in state_y:
            ax_hyp.fill_between([t_h[i], t_h[i+1]], state_y[s] - 0.45, state_y[s] + 0.45,
                                 color=STATE_COL[s], linewidth=0)
    ax_hyp.set_yticks([0, 1, 2])
    ax_hyp.set_yticklabels(['NREM', 'REM', 'WAKE'], fontsize=10)
    ax_hyp.set_ylim(-0.6, 2.6)

    ax_hyp.axvline(0, color='black', linewidth=2.2, zorder=10)
    for _, h0, h1 in PHASES[1:]:
        ax_hyp.axvline(h1, color='#888', linestyle='--', linewidth=1, alpha=0.7)

    plotted = {}
    for t_sec, name, color in taste_events:
        t_h_ev = (t_sec - licl_time_s) / 3600.0
        if window_start_h <= t_h_ev <= window_end_h:
            ax_hyp.axvline(t_h_ev, color=color, linestyle=':', linewidth=1.2, alpha=0.75)
            plotted[name] = color

    state_patches = [mpatches.Patch(color=STATE_COL[k], label=STATE_LBL[k]) for k in [1, 3, 5]]
    licl_handle = mpl_lines.Line2D([0], [0], color='black', linewidth=2.2, label='LiCl injection')
    state_legend = ax_hyp.legend(handles=state_patches + [licl_handle], loc='upper right',
                                  ncol=4, fontsize=9, framealpha=0.7)
    ax_hyp.add_artist(state_legend)
    if plotted:
        legend_handles = [mpatches.Patch(color=c, label=n) for n, c in plotted.items()]
        ax_hyp.legend(handles=legend_handles, loc='upper left', ncol=len(legend_handles),
                       fontsize=8, framealpha=0.7, title='Taste')

    ax_hyp.set_xlim(window_start_h, window_end_h)

    # ── Phase-composition stacked bar ──
    dt = np.diff(t, append=t[-1])
    bottom = np.zeros(len(PHASES))
    centers = [(h0 + h1) / 2 for _, h0, h1 in PHASES]
    widths = [h1 - h0 for _, h0, h1 in PHASES]
    for name, code in STATE_CODE.items():
        pcts = []
        for _, h0, h1 in PHASES:
            t0, t1 = licl_time_s + h0 * 3600, licl_time_s + h1 * 3600
            m = (t >= t0) & (t < t1)
            span = dt[m].sum()
            pcts.append(100 * dt[m & (states == code)].sum() / span if span > 0 else 0)
        ax_bar.bar(centers, pcts, bottom=bottom, width=widths, color=STATE_COL[code],
                   edgecolor='white', linewidth=0.5, label=name)
        bottom += np.array(pcts)
    ax_bar.set_ylim(0, 100)
    ax_bar.set_ylabel('% of phase')
    ax_bar.set_xlabel('Hours relative to LiCl injection')
    ax_bar.set_xlim(window_start_h, window_end_h)
    ax_bar.axvline(0, color='black', linewidth=2.2, zorder=10)
    for _, h0, h1 in PHASES:
        ax_bar.axvline(h1, color='#888', linestyle='--', linewidth=1, alpha=0.7)
    for label, h0, h1 in PHASES:
        rot = 90 if (h1 - h0) < 2 else 0
        ax_bar.text((h0 + h1) / 2, 50, label, ha='center', va='center', fontsize=7.5,
                    rotation=rot, color='white', fontweight='bold')
    ax_bar.set_title('WAKE / NREM / REM composition per Arieli-timeline phase', fontsize=11, loc='left')

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(out_dir, f'{animal}_training_day_hypnogram.png')
    fig.savefig(out, dpi=170, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nHypnogram saved -> {out}')
    return out


def cut_training_day_states(cfg, t, states, bouts, licl_time_s, window):
    """Cut the buzcode WAKE/NREM/REM classification down to just the Training
    day's 24h window (9AM on the LiCl day through 9AM the next day -- see
    training_day_window()). Returns a dict ready for scipy.io.savemat."""
    t0_abs, t1_abs, window_start_h, window_end_h = window
    mask = (t >= t0_abs) & (t < t1_abs)

    cut_bouts = {}
    for name, iv in bouts.items():
        b_mask = (iv[0] >= t0_abs) & (iv[0] < t1_abs)
        cut_bouts[f'{name}state'] = iv[:, b_mask]

    return dict(
        t=t[mask],
        states=states[mask],
        licl_time_s=licl_time_s,
        window_start_s=t0_abs,
        window_end_s=t1_abs,
        window_start_h_from_licl=window_start_h,
        window_end_h_from_licl=window_end_h,
        rec_start=cfg['rec_start'].isoformat(),
        session=cfg['session'],
        note=('WAKE=1, NREM=3, REM=5 (buzcode SleepState.idx convention). '
              'Cut from the full-recording SleepState.states.mat to just the '
              'Training day: a 24h window from 9:00 AM on the day LiCl was '
              'injected through 9:00 AM the following day (see '
              'window_start_s/window_end_s for the exact recording-relative '
              'bounds, and licl_time_s for the injection timestamp).'),
        **cut_bouts,
    )


def save_training_day_mat(animal, cfg, cut_data, out_dir):
    mat_path = os.path.join(out_dir, f'{cfg["session"]}_TrainingDay.SleepState.states.mat')
    sio.savemat(mat_path, cut_data)
    dur_h = (cut_data['t'][-1] - cut_data['t'][0]) / 3600
    day_start_dt = cfg['rec_start'] + timedelta(seconds=cut_data['window_start_s'])
    day_end_dt = cfg['rec_start'] + timedelta(seconds=cut_data['window_end_s'])
    print(f'\nCut Training-day states saved -> {mat_path}')
    print(f'  {len(cut_data["t"])} samples spanning {dur_h:.2f}h '
          f'({day_start_dt} to {day_end_dt})')
    return mat_path


def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal]
    licl_time_s = cfg.get('licl_time_s')
    if licl_time_s is None:
        print(f'{animal} ({cfg["session"]}) has no licl_time_s set -- no '
              f'Training/CTA day in this recording, nothing to isolate. Skipping.')
        return

    out_dir = f'/tmp/{animal}_training_day'
    os.makedirs(out_dir, exist_ok=True)

    print(f'=== Training-day sleep classification: {animal} ({cfg["session"]}) ===')
    print(f'LiCl injection: t={licl_time_s:.1f}s ({licl_time_s/3600:.2f}h into recording) '
          f'= {cfg["rec_start"] + timedelta(seconds=licl_time_s)}')

    window = training_day_window(cfg, licl_time_s)
    t0_abs, t1_abs, window_start_h, window_end_h = window
    print(f'Training day window (9AM-9AM): '
          f'{cfg["rec_start"] + timedelta(seconds=t0_abs)} to '
          f'{cfg["rec_start"] + timedelta(seconds=t1_abs)} '
          f'({window_start_h:+.2f}h to {window_end_h:+.2f}h relative to LiCl)')

    t, states, bouts = load_states(cfg['mat_file'])
    taste_events = load_taste_events(cfg)

    rows = phase_breakdown(t, states, bouts, licl_time_s)
    csv_path = print_and_save_table(rows, animal, out_dir)
    png_path = plot_training_day(animal, cfg, t, states, taste_events, licl_time_s, window, out_dir)

    cut_data = cut_training_day_states(cfg, t, states, bouts, licl_time_s, window)
    mat_path = save_training_day_mat(animal, cfg, cut_data, out_dir)

    nas_dir = os.path.join(os.path.dirname(cfg['out_dir']), f'{animal}_Training_Day')
    os.makedirs(nas_dir, exist_ok=True)
    for local_path in (mat_path, csv_path, png_path):
        dest = os.path.join(nas_dir, os.path.basename(local_path))
        # plain copyfile, not copy2/copystat -- the gvfs-SMB mount doesn't
        # support chmod (same class of limitation as its no-symlinks issue,
        # see TODO.md's MS08_Buzaki_results note), so preserving metadata fails.
        shutil.copyfile(local_path, dest)
        assert os.path.getsize(dest) == os.path.getsize(local_path), f'size mismatch copying {local_path}'
    print(f'\nCopied to the share -> {nas_dir}')


if __name__ == '__main__':
    main()
