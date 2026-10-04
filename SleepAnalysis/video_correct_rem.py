"""
Post-hoc correction: reclassify any REM-labeled timepoint whose independent
video-movement signal is too high (above the same per-animal "wake" movement
threshold sleep_sanity_check.py already computes) back to WAKE.

Why: buzcode's theta criterion alone can't tell real muscle-atonia REM apart
from an active-movement artifact (seen repeatedly in this project -- REM
epochs that move almost as much as WAKE on the independent video signal).
Rather than keep hand-tuning the theta threshold, directly veto any REM call
that the video signal itself contradicts.

One script for every rat, not a copy per animal -- reuses the exact same
ANIMALS config (video_file/sync_file/mov_fps/mat_file) already in
sleep_sanity_check.py instead of redefining it.

Usage: python video_correct_rem.py ANIMAL   (e.g. MS14_manualTH)
Writes <ANIMAL>_videocorr.SleepState.states.mat next to the source .mat.
"""
import sys
import os
import shutil
import numpy as np
import h5py

from sleep_sanity_check import ANIMALS, STATE_CODE


def states_to_intervals(t, states_arr, code):
    mask = states_arr == code
    if not mask.any():
        return np.zeros((2, 0))
    d = np.diff(mask.astype(int))
    starts = np.where(d == 1)[0] + 1
    ends = np.where(d == -1)[0]
    if mask[0]:
        starts = np.r_[0, starts]
    if mask[-1]:
        ends = np.r_[ends, len(mask) - 1]
    start_times = t[starts]
    stop_idx = np.minimum(ends + 1, len(t) - 1)
    stop_times = t[stop_idx]
    return np.vstack([start_times, stop_times])


def main():
    animal = sys.argv[1]
    cfg = ANIMALS[animal]
    src_mat = cfg['mat_file']
    video_file = cfg['video_file']
    sync_file = cfg['sync_file']
    mov_fps = cfg['mov_fps']

    base, ext = os.path.splitext(src_mat)
    assert base.endswith('.SleepState.states')
    out_mat = base[:-len('.SleepState.states')] + '_videocorr.SleepState.states' + ext

    print(f'Copying {src_mat}\n  -> {out_mat}')
    shutil.copyfile(src_mat, out_mat)

    print('Loading states + video movement...')
    with h5py.File(src_mat, 'r') as f:
        t = np.array(f['SleepState/idx/timestamps']).flatten()
        states = np.array(f['SleepState/idx/states']).flatten().copy()

    with open(sync_file) as f:
        offset = float(f.readline().strip())
    mov_raw = np.load(video_file).astype(np.float32)
    n_sec = len(mov_raw) // mov_fps
    mov_1hz = mov_raw[:n_sec * mov_fps].reshape(n_sec, mov_fps).mean(axis=1)
    log_mov = np.log1p(mov_1hz)
    mov_wake_thr = float(np.expm1(log_mov.mean() + 1.5 * log_mov.std()))
    print(f'  mov_wake_thr = {mov_wake_thr:.1f} px/frame (same formula as '
          f'sleep_sanity_check.py)')

    rem_code = STATE_CODE['REM']
    wake_code = STATE_CODE['WAKE']
    rem_mask = states == rem_code
    n_rem_before = rem_mask.sum()

    idx_mov = (t[rem_mask] - offset).astype(int)
    valid = (idx_mov >= 0) & (idx_mov < len(mov_1hz))
    too_much_movement = np.zeros(n_rem_before, dtype=bool)
    too_much_movement[valid] = mov_1hz[idx_mov[valid]] > mov_wake_thr
    # Timepoints where video is unreachable (invalid) are left as REM --
    # only reclassify where we have positive evidence of movement.
    rem_indices = np.where(rem_mask)[0]
    reclassify = rem_indices[too_much_movement]

    print(f'  REM samples before: {n_rem_before}')
    print(f'  Reclassified to WAKE (video movement > threshold): {len(reclassify)} '
          f'({100*len(reclassify)/max(n_rem_before,1):.1f}% of REM)')
    print(f'  REM samples after:  {n_rem_before - len(reclassify)}')

    states[reclassify] = wake_code

    print('Rebuilding WAKE/NREM/REM intervals from corrected states...')
    with h5py.File(out_mat, 'r+') as f:
        del f['SleepState/idx/states']
        f.create_dataset('SleepState/idx/states', data=states.reshape(1, -1))
        for name, code in STATE_CODE.items():
            path = f'SleepState/ints/{name}state'
            ints = states_to_intervals(t, states, code)
            del f[path]
            f.create_dataset(path, data=ints)

    dt = np.diff(t, append=t[-1])
    for name, code in STATE_CODE.items():
        pct = 100 * dt[states == code].sum() / t[-1]
        print(f'  {name:5s}: {pct:5.1f}%')

    print(f'\nSaved -> {out_mat}')


if __name__ == '__main__':
    main()
