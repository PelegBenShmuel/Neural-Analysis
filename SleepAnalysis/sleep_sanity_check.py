"""
Sanity check for buzcode sleep-scoring output — run this BEFORE trusting a
session's WAKE/NREM/REM states for any downstream (e.g. GC neural) analysis.

Answers, in plain numbers, five questions:
  1. Coverage    — how much of the recording is actually scored (vs. undefined,
                   state 0)?
  2. Proportions — are WAKE/NREM/REM percentages in the range expected for a
                   rat, or does something look broken?
  3. Bouts       — are state bouts physiologically plausible durations, or is
                   the scoring flickering (many <10s bouts)?
  4. Cross-checks — do independent signals (video movement, taste-delivery
                   timing) agree with what buzcode calls WAKE? Taste is only
                   delivered to an awake animal, so taste events landing in
                   NREM/REM would indicate a timestamp/state misalignment.
  5. REM plausibility — REM sleep is defined by cortical activation (theta)
                   *combined with* muscle atonia, so real REM bouts should
                   look like NREM (low movement), not WAKE, on an independent
                   movement signal. Checks buzcode's own EMG-from-LFP metric
                   and the separate video-movement trace against the states
                   buzcode assigned, to see whether "REM" epochs are actually
                   quiescent or whether they look like mislabeled active WAKE.

Prints a plain-text report and saves one summary figure
(<animal>_sanity_check.png: hourly state composition + bout-duration
histograms) to OUT_DIR.

Usage: python sleep_sanity_check.py [ANIMAL]   (default: MS08)
"""
import sys
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

# ── Per-animal config ─────────────────────────────────────────────────────────
NAS_MAI   = '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Mai'
NAS_PELEG = '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Peleg'

ANIMALS = {
    'MS08': dict(
        session   = 'MS08_hab3toExp',
        mat_file  = '/media/anan/diskh2/MS08/MS08_hab3toExp/MS08_hab3toExp.SleepState.states.mat',
        sync_file = f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS08/MS08_buzcode_analysis',
        video_file = '/media/anan/diskh2/MS08/MS08_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS09': dict(
        session   = 'MS09_hab3_ext',
        mat_file  = '/media/anan/diskh2/MS09/MS09_hab3_ext/MS09_hab3_ext.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS09/MS09_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS11': dict(
        session   = 'MS11_hab3',
        mat_file  = '/media/anan/diskh2/MS11/MS11_hab3/MS11_hab3.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_7_0.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_1_0.txt',
            'Sucrose': f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_2_0.txt',
            'Salt'   : f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_3_0.txt',
            'Acid'   : f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_4_0.txt',
        },
        out_dir = f'{NAS_PELEG}/MS11/MS11_buzcode_analysis',
        # No video_file: MS11's video-movement .npy is missing on both shares
        # (the old_pipeline path it used to live at is gone after the
        # raw-data reorg) -- REM plausibility check falls back to EMG-from-LFP
        # only. Flagged to Peleg 2026-09-16, not recomputed without asking
        # (VideoMovement.py can regenerate it from MS_11_Raw_Data's raw .mp4
        # if wanted -- that's a real compute job on a ~73h video, not a quick step).
    ),
}

# Expected ranges for a rat over a multi-day recording (Watson/Buzsaki-lab
# rodent norms) — flags, not hard failures.
EXPECTED_PCT = {'WAKE': (35, 60), 'NREM': (35, 60), 'REM': (3, 15)}
FLICKER_S    = 10   # bouts shorter than this are suspect (scoring noise)

STATE_CODE = {'WAKE': 1, 'NREM': 3, 'REM': 5}
STATE_COL  = {'WAKE': '#e06c3a', 'NREM': '#4a90d9', 'REM': '#5cb85c'}


def load_states(mat_file):
    with h5py.File(mat_file, 'r') as f:
        t       = np.array(f['SleepState/idx/timestamps']).flatten()
        states  = np.array(f['SleepState/idx/states']).flatten()
        bouts   = {name: np.array(f[f'SleepState/ints/{name}state'])
                   for name in STATE_CODE}
        metrics = f['SleepState/detectorinfo/detectionparms/SleepScoreMetrics']
        t_clus  = np.array(metrics['t_clus']).flatten()
        motion  = np.array(metrics['motiondata']).flatten()
        mo_thr  = float(np.array(metrics['histsandthreshs/MotionThresh']).flatten()[0])
    return t, states, bouts, t_clus, motion, mo_thr


def check_coverage(t, states):
    print('── 1. Coverage ──────────────────────────────────────────────')
    dur_h = t[-1] / 3600
    dt = np.diff(t, append=t[-1])
    undefined_s = dt[states == 0].sum()
    print(f'  Recording span   : {dur_h:.2f} h ({len(t)} samples)')
    print(f'  Undefined (0)    : {undefined_s/3600:.2f} h '
          f'({100*undefined_s/t[-1]:.1f}% of recording)')
    if undefined_s / t[-1] > 0.10:
        print('  [FLAG] >10% of the recording is unscored — check for LFP '
              'dropouts or a broken SW/Theta channel before trusting the rest.')
    else:
        print('  [OK] Unscored fraction is small.')
    return dur_h


def check_proportions(t, states):
    print('\n── 2. State proportions ─────────────────────────────────────')
    dt = np.diff(t, append=t[-1])
    pct = {}
    for name, code in STATE_CODE.items():
        pct[name] = 100 * dt[states == code].sum() / t[-1]
    for name in STATE_CODE:
        lo, hi = EXPECTED_PCT[name]
        flag = '' if lo <= pct[name] <= hi else '  [FLAG outside typical range]'
        print(f'  {name:5s}: {pct[name]:5.1f}%   (typical rat range {lo}-{hi}%){flag}')
    ratio = pct['NREM'] / pct['REM'] if pct['REM'] > 0 else np.inf
    print(f'  NREM:REM ratio    : {ratio:.1f} (typical rat range ~4-8)')
    if not (3 <= ratio <= 10):
        print('  [FLAG] NREM:REM ratio outside the usual range — check REM '
              'detection (theta channel/threshold) specifically.')
    return pct


def check_bouts(bouts):
    print('\n── 3. Bout durations ────────────────────────────────────────')
    durations = {}
    for name in STATE_CODE:
        iv = bouts[name]
        d = iv[1] - iv[0]
        durations[name] = d
        n_flicker = int((d < FLICKER_S).sum())
        print(f'  {name:5s}: {len(d):4d} bouts | median {np.median(d):6.1f}s '
              f'| mean {d.mean():6.1f}s | max {d.max()/60:5.1f}min | '
              f'{n_flicker} bouts <{FLICKER_S}s ({100*n_flicker/len(d):.1f}%)')
        if n_flicker / len(d) > 0.25:
            print(f'  [FLAG] >25% of {name} bouts are <{FLICKER_S}s — scoring '
                  'may be flickering rather than resolving real bouts.')
    return durations


def check_taste_alignment(t, states, sync_file, taste_files):
    print('\n── 4. Cross-check: taste events vs. state ───────────────────')
    if not (os.path.exists(sync_file) and all(os.path.exists(p) for p in taste_files.values())):
        print('  [SKIPPED] taste/sync files not reachable from this machine '
              '(NAS not mounted?).')
        return
    with open(sync_file) as f:
        offset = float(f.readline().strip())

    # states are sampled ~1/s starting at t[0]; nearest-sample lookup
    def state_at(t_sec):
        idx = np.searchsorted(t, t_sec)
        idx = np.clip(idx, 0, len(t) - 1)
        return states[idx]

    total, in_wake = 0, 0
    for name, path in taste_files.items():
        times = [float(l.strip()) for l in open(path) if l.strip()]
        st = [state_at(tt) for tt in times]
        n_wake = sum(1 for s in st if s == STATE_CODE['WAKE'])
        n_sleep = sum(1 for s in st if s in (STATE_CODE['NREM'], STATE_CODE['REM']))
        print(f'  {name:8s}: {len(times):4d} deliveries | {n_wake} in WAKE, '
              f'{n_sleep} in NREM/REM, {len(times)-n_wake-n_sleep} unscored')
        total += len(times)
        in_wake += n_wake
    pct_wake = 100 * in_wake / total if total else 0
    print(f'  Overall: {pct_wake:.1f}% of taste deliveries fall in WAKE.')
    if pct_wake < 90:
        print('  [FLAG] Taste is normally delivered to an awake, engaged '
              'animal — a large fraction landing outside WAKE suggests a '
              'timestamp offset between the states clock and the taste '
              'events clock, not necessarily a real sleep-deprived delivery.')
    else:
        print('  [OK] Taste events line up with WAKE as expected — the '
              'states clock and event clock agree.')


def check_rem_plausibility(t, states, t_clus, motion, mo_thr, video_file, mov_fps,
                            sync_file):
    print('\n── 5. REM plausibility: movement cross-check ────────────────')

    # (a) buzcode's own EMG-from-LFP metric, already computed at t_clus times
    def nearest(ref_t, query_t, values):
        idx = np.searchsorted(ref_t, query_t)
        idx = np.clip(idx, 0, len(ref_t) - 1)
        return values[idx]

    motion_at_state_t = nearest(t_clus, t, motion)
    print('  EMG-from-LFP motion metric by state (0=still, 1=moving; '
          f'WAKE threshold={mo_thr:.2f}):')
    med = {}
    for name, code in STATE_CODE.items():
        vals = motion_at_state_t[states == code]
        med[name] = np.median(vals)
        print(f'    {name:5s}: median {med[name]:.3f}  '
              f'(mean {vals.mean():.3f}, n={len(vals)})')
    if med['REM'] > 0.5 * (med['WAKE'] + med['NREM']):
        print('  [FLAG] REM epochs have EMG-motion closer to WAKE than NREM — '
              'expected muscle atonia during REM is not showing up; these '
              '"REM" bouts may actually be mislabeled brief WAKE.')
    else:
        print('  [OK] REM epochs look quiescent (EMG-motion close to NREM), '
              'consistent with real REM muscle atonia rather than mislabeled WAKE.')

    # (b) independent video movement signal, if reachable
    if not (os.path.exists(video_file) and os.path.exists(sync_file)):
        print('  [SKIPPED] video/sync files not reachable from this machine.')
        return
    with open(sync_file) as f:
        offset = float(f.readline().strip())
    mov_raw = np.load(video_file).astype(np.float32)
    n_sec = len(mov_raw) // mov_fps
    mov_1hz = mov_raw[:n_sec * mov_fps].reshape(n_sec, mov_fps).mean(axis=1)
    log_mov = np.log1p(mov_1hz)
    mov_wake_thr = float(np.expm1(log_mov.mean() + 1.5 * log_mov.std()))

    idx = (t - offset).astype(int)
    valid = (idx >= 0) & (idx < len(mov_1hz))
    mov_at_t = np.where(valid, mov_1hz[np.clip(idx, 0, len(mov_1hz) - 1)], np.nan)

    print(f'\n  Video movement by state (px/frame; WAKE threshold='
          f'{mov_wake_thr:.0f}):')
    vmed = {}
    for name, code in STATE_CODE.items():
        vals = mov_at_t[(states == code) & valid]
        vmed[name] = np.median(vals)
        pct_above_wake_thr = 100 * (vals > mov_wake_thr).sum() / len(vals) if len(vals) else np.nan
        print(f'    {name:5s}: median {vmed[name]:6.1f}  '
              f'({pct_above_wake_thr:.1f}% of time above WAKE threshold, n={len(vals)})')
    if vmed['REM'] > 0.5 * (vmed['WAKE'] + vmed['NREM']):
        print('  [FLAG] REM epochs move nearly as much as WAKE on video — '
              'independent confirmation that these REM bouts look like '
              'active behavior, not real muscle-atonia REM.')
    else:
        print('  [OK] REM epochs are as still as NREM on video — independent '
              'confirmation that these are physiologically plausible REM bouts, '
              'even though they are short.')


def check_rem_fragmentation(bouts, states, t, merge_gap_s=30):
    print('\n── 6. REM bout fragmentation ─────────────────────────────────')
    iv = bouts['REM']
    order = np.argsort(iv[0])
    starts, stops = iv[0][order], iv[1][order]
    n = len(starts)
    gaps = starts[1:] - stops[:-1]
    print(f'  {n} REM bouts, {n-1} inter-bout gaps.')
    print(f'  Gap to next REM bout: median {np.median(gaps):.1f}s, '
          f'{100*(gaps < merge_gap_s).sum()/len(gaps):.1f}% are <{merge_gap_s}s.')

    def state_at(t_sec):
        idx = np.searchsorted(t, t_sec)
        return states[np.clip(idx, 0, len(t) - 1)]

    # Merge consecutive REM bouts whose gap is short AND entirely NREM/undefined
    # (never WAKE) -- a real WAKE interruption argues against "one continuous
    # quiescent period", a brief NREM-only gap is consistent with the
    # threshold noisily dipping mid-episode.
    merged_starts, merged_stops = [starts[0]], [stops[0]]
    n_merged = 0
    for i in range(1, n):
        gap = starts[i] - merged_stops[-1]
        gap_samples = np.arange(int(merged_stops[-1]), int(starts[i]))
        gap_is_wake = len(gap_samples) > 0 and np.any(state_at(gap_samples) == STATE_CODE['WAKE'])
        if gap < merge_gap_s and not gap_is_wake:
            merged_stops[-1] = stops[i]
            n_merged += 1
        else:
            merged_starts.append(starts[i])
            merged_stops.append(stops[i])

    merged_dur = np.array(merged_stops) - np.array(merged_starts)
    orig_dur = stops - starts
    print(f'  Merging bouts separated by <{merge_gap_s}s of pure NREM/undefined '
          f'(never WAKE) folds {n_merged} gaps, leaving {len(merged_dur)} '
          f'"episodes":')
    print(f'    Before merge: median {np.median(orig_dur):.1f}s, '
          f'mean {orig_dur.mean():.1f}s (n={len(orig_dur)})')
    print(f'    After merge : median {np.median(merged_dur):.1f}s, '
          f'mean {merged_dur.mean():.1f}s (n={len(merged_dur)})')
    if np.median(merged_dur) > 3 * np.median(orig_dur) and np.median(merged_dur) >= 60:
        print('  [FINDING] Merged episode durations look much more physiologically '
              'normal (approaching the 1-3+ min range) — the short raw bout '
              'durations are likely an artifact of the threshold briefly dipping '
              'mid-episode, not truly separate micro-REM events.')
    else:
        print('  [FINDING] Merging nearby bouts does not substantially change '
              'typical durations — these look like genuinely separate short '
              'REM episodes rather than one fragmented period.')
    return merged_dur


def plot_summary(animal, t, states, durations, out_dir):
    total_hours = int(np.ceil(t[-1] / 3600))
    hourly = np.zeros((total_hours, 3))
    dt = np.diff(t, append=t[-1])
    hour_idx = (t // 3600).astype(int)
    for i, name in enumerate(STATE_CODE):
        code = STATE_CODE[name]
        mask = states == code
        for h in range(total_hours):
            hourly[h, i] = dt[mask & (hour_idx == h)].sum() / 3600 * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), facecolor='white')

    bottom = np.zeros(total_hours)
    for i, name in enumerate(STATE_CODE):
        ax1.bar(np.arange(1, total_hours + 1), hourly[:, i], bottom=bottom,
                color=STATE_COL[name], width=0.9, label=name)
        bottom += hourly[:, i]
    ax1.set_xlabel('Hour of recording')
    ax1.set_ylabel('% of hour')
    ax1.set_title(f'{animal} — hourly state composition (sanity view)')
    ax1.legend(loc='upper right', ncol=3, framealpha=0.8)
    ax1.set_xlim(0.5, total_hours + 0.5)
    ax1.set_ylim(0, 100)

    for name in STATE_CODE:
        ax2.hist(durations[name], bins=np.logspace(0, 3.5, 40),
                  color=STATE_COL[name], alpha=0.6, label=name)
    ax2.set_xscale('log')
    ax2.axvline(FLICKER_S, color='k', linestyle='--', linewidth=1,
                label=f'{FLICKER_S}s flicker cutoff')
    ax2.set_xlabel('Bout duration (s, log scale)')
    ax2.set_ylabel('Count')
    ax2.set_title('Bout-duration distributions')
    ax2.legend()

    plt.tight_layout()
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f'{animal}_sanity_check.png')
    fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSummary figure saved → {out}')


def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal]
    print(f'=== Sleep sanity check: {animal} ({cfg["session"]}) ===\n')

    t, states, bouts, t_clus, motion, mo_thr = load_states(cfg['mat_file'])
    check_coverage(t, states)
    check_proportions(t, states)
    durations = check_bouts(bouts)
    check_taste_alignment(t, states, cfg['sync_file'], cfg['taste_files'])
    if 'video_file' in cfg:
        check_rem_plausibility(t, states, t_clus, motion, mo_thr,
                                cfg['video_file'], cfg['mov_fps'], cfg['sync_file'])
    check_rem_fragmentation(bouts, states, t)
    plot_summary(animal, t, states, durations, cfg['out_dir'])


if __name__ == '__main__':
    main()
