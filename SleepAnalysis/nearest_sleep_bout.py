"""
nearest_sleep_bout.py -- for a single animal, finds the NREM or REM bout
nearest to a given clock time within that animal's Training day, reporting
its type, start/end clock time, and duration.

Reads the same per-animal <animal>_Training_Day/<session>_TrainingDay.
SleepState.states.mat produced by training_day_sleep_state_extraction.py
(gap-filled WAKE/NREM/REM point states -- see that script's
fill_same_state_gaps) and re-derives typed bouts (NREM-only and REM-only
contiguous runs, kept separate) from those gap-filled states, rather than
reading the file's own saved NREMstate/REMstate interval tables -- those
predate the gap-fill and would occasionally report a bout gap-filling has
since merged. Shares ANIMALS / plain_label (per-animal config) from
MS_buzcode_analysis.py and the final-scoring-variant key list from
total_sleep_rat.py -- see feedback_no_script_duplication memory.

Usage: python nearest_sleep_bout.py <ANIMAL> <TIME>
  ANIMAL: a plain rat name (e.g. MS14) -- resolved to whichever ANIMALS key
    holds that rat's final accepted scoring, same mapping total_sleep_rat.py
    uses -- or a raw ANIMALS key directly (e.g. MS14_videocorr).
  TIME: "HH:MM" or "HH:MM:SS", resolved to whichever of the Training day's
    two calendar dates matches (the window runs 9:00 AM to 9:00 AM, so every
    clock-of-day maps to exactly one of the two dates -- no ambiguity), or a
    full "YYYY-MM-DD HH:MM[:SS]" to bypass that resolution entirely.

Examples:
  python nearest_sleep_bout.py MS08 14:30
  python nearest_sleep_bout.py MS14 "2025-07-23 02:15:00"
"""
import sys
import os
from datetime import datetime, timedelta

import numpy as np
import scipy.io as sio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from MS_buzcode_analysis import ANIMALS, plain_label
from sleep_char import mat_str
from total_sleep_rat import ANIMAL_KEYS, mat_path_for

STATE_CODE = {'WAKE': 1, 'NREM': 3, 'REM': 5}
SLEEP_STATES = ('NREM', 'REM')

# Plain rat name -> the ANIMALS key holding its final accepted scoring, same
# mapping total_sleep_rat.py's ANIMAL_KEYS list encodes (so "MS14" resolves
# to "MS14_videocorr" without Peleg needing to remember variant suffixes).
FINAL_ANIMAL_KEY = {plain_label(k): k for k in ANIMAL_KEYS}


def load_cut_mat(mat_path):
    d = sio.loadmat(mat_path)
    t = np.array(d['t']).flatten().astype(float)
    states = np.array(d['states']).flatten().astype(int)
    window_start_s = float(np.array(d['window_start_s']).flatten()[0])
    window_end_s = float(np.array(d['window_end_s']).flatten()[0])
    rec_start = datetime.fromisoformat(mat_str(d['rec_start']))
    return t, states, window_start_s, window_end_s, rec_start


def typed_sleep_bouts(t, states):
    """Contiguous runs of a single state (NREM-only or REM-only -- kept
    separate, unlike sleep_char.py's sleep_bouts(), which merges NREM<->REM
    transitions into one "asleep" category). Returns a list of
    (start_s, end_s, duration_s, state_name) sorted by start time."""
    dt_last = t[-1] - t[-2] if len(t) > 1 else 1.0
    out = []
    for name in SLEEP_STATES:
        code = STATE_CODE[name]
        is_state = states == code
        if not is_state.any():
            continue
        change = np.where(np.diff(is_state.astype(int)) != 0)[0]
        starts = np.concatenate(([0], change + 1))
        stops = np.concatenate((change, [len(is_state) - 1]))
        for s, e in zip(starts, stops):
            if not is_state[s]:
                continue
            start_s = t[s]
            end_s = t[e] + (dt_last if e == len(t) - 1 else (t[e + 1] - t[e]))
            out.append((start_s, end_s, end_s - start_s, name))
    out.sort(key=lambda b: b[0])
    return out


def parse_query_time(time_str, rec_start, window_start_s, window_end_s):
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            dt = datetime.strptime(time_str, fmt)
            return (dt - rec_start).total_seconds()
        except ValueError:
            continue

    clock = None
    for fmt in ('%H:%M:%S', '%H:%M'):
        try:
            clock = datetime.strptime(time_str, fmt).time()
            break
        except ValueError:
            continue
    if clock is None:
        raise ValueError(f'Unrecognized time {time_str!r} -- use "HH:MM", "HH:MM:SS", '
                          f'or "YYYY-MM-DD HH:MM[:SS]"')

    day_start_dt = rec_start + timedelta(seconds=window_start_s)
    day_end_dt = rec_start + timedelta(seconds=window_end_s)
    date = day_start_dt.date() if clock >= day_start_dt.time() else day_end_dt.date()
    dt = datetime.combine(date, clock)
    return (dt - rec_start).total_seconds()


def find_nearest_bout(bouts, t_query):
    """Returns (bout, distance_s, relation), relation in {'inside', 'before',
    'after'} -- 'before' means the bout ended before the query time (the rat
    slept, then the query moment came later); 'after' means the bout hasn't
    started yet at the query moment."""
    best, best_dist, best_rel = None, None, None
    for bout in bouts:
        start_s, end_s, _, _ = bout
        if start_s <= t_query <= end_s:
            return bout, 0.0, 'inside'
        if t_query < start_s:
            dist, rel = start_s - t_query, 'after'
        else:
            dist, rel = t_query - end_s, 'before'
        if best_dist is None or dist < best_dist:
            best, best_dist, best_rel = bout, dist, rel
    return best, best_dist, best_rel


def main():
    if len(sys.argv) < 3:
        print('Usage: python nearest_sleep_bout.py <ANIMAL> <TIME>')
        print('  TIME: "HH:MM", "HH:MM:SS", or "YYYY-MM-DD HH:MM[:SS]"')
        sys.exit(1)

    animal_arg, time_str = sys.argv[1], sys.argv[2]
    animal_key = FINAL_ANIMAL_KEY.get(animal_arg, animal_arg)
    if animal_key not in ANIMALS:
        print(f'{animal_arg!r} is not a known animal/key. Known rats: '
              f'{sorted(FINAL_ANIMAL_KEY.keys())}')
        sys.exit(1)

    animal, mat_path = mat_path_for(animal_key)
    if not os.path.exists(mat_path):
        print(f'{mat_path} not found -- run training_day_sleep_state_extraction.py '
              f'for {animal} first.')
        return

    t, states, window_start_s, window_end_s, rec_start = load_cut_mat(mat_path)

    try:
        t_query = parse_query_time(time_str, rec_start, window_start_s, window_end_s)
    except ValueError as e:
        print(e)
        sys.exit(1)

    day_start_dt = rec_start + timedelta(seconds=window_start_s)
    day_end_dt = rec_start + timedelta(seconds=window_end_s)
    if not (window_start_s <= t_query <= window_end_s):
        print(f'{time_str} falls outside {animal}\'s Training day window '
              f'({day_start_dt} to {day_end_dt}) -- nothing to search.')
        return

    query_dt = rec_start + timedelta(seconds=t_query)
    bouts = typed_sleep_bouts(t, states)
    if not bouts:
        print(f'{animal} has no NREM/REM bouts in its Training day window.')
        return

    bout, dist, rel = find_nearest_bout(bouts, t_query)
    start_s, end_s, dur_s, name = bout
    start_dt = rec_start + timedelta(seconds=start_s)
    end_dt = rec_start + timedelta(seconds=end_s)

    print(f'=== {animal}: nearest sleep to {query_dt.strftime("%Y-%m-%d %H:%M:%S")} ===')
    if rel == 'inside':
        print(f'Asleep AT this time -- {name} bout, {start_dt.strftime("%H:%M:%S")} to '
              f'{end_dt.strftime("%H:%M:%S")} ({dur_s/60:.1f} min long)')
    else:
        when = 'before' if rel == 'before' else 'after'
        print(f'Nearest bout is {name}, {dist/60:.1f} min {when} the query time: '
              f'{start_dt.strftime("%Y-%m-%d %H:%M:%S")} to {end_dt.strftime("%H:%M:%S")} '
              f'({dur_s/60:.1f} min long)')


if __name__ == '__main__':
    main()
