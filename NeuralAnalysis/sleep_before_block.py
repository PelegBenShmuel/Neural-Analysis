"""
For each Training-day block, how much of the 30 minutes immediately before
it the rat spent asleep (NREM+REM) vs awake -- Peleg's request, 2026-11-08,
to look at pre-block sleep state as a possible covariate for the Fano
factor matrix (fano_factor_total.py uses the same block structure with a
4min pre-block window; this one is sleep, 30min, deliberately separate).

Reuses existing helpers rather than reimplementing sleep-state loading:
load_states() from training_day_sleep_state_extraction.py (buzcode
SleepState.states.mat -> 1s-binned (t, states) arrays, t in seconds since
rec_start -- same clock as derive_training_blocks's block times), and the
(STATE_CODE, SLEEP_CODES=(NREM,REM)) convention already used throughout
SleepAnalysis/ (sleep_char.py, total_sleep_rat.py). The
PRE_BLOCK_SECONDS=30*60 pre-block-window pattern itself matches
pre_block_baseline_fano_factor.py's, just looped over all 7 blocks instead
of only Block 1/7.

Per rat, per block: seconds actually covered by the sleep-scoring file in
that window (span_s -- usually the full 1800s, less only if the window
runs off the start/end of the scored recording), seconds asleep
(NREM+REM), and sleep fraction (sleep_s / span_s, not /1800 -- so a
partially-covered window doesn't look artificially low).

Usage: python sleep_before_block.py [RAT ...]
With no arguments, runs all rats in RAT_KEYS. Prints a table per rat;
doesn't write any file yet -- Peleg asked to look at MS09 first before
deciding on an output format for the rest.
"""
import sys
import os

import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, derive_training_blocks
from training_day_sleep_state_extraction import load_states
from training_day_response_phases import label_blocks

PRE_BLOCK_SECONDS = 30 * 60   # 30 minutes
STATE_CODE = {'WAKE': 1, 'NREM': 3, 'REM': 5}
SLEEP_CODES = (STATE_CODE['NREM'], STATE_CODE['REM'])

# Reused from fano_factor_total.py rather than duplicated -- same accepted
# ANIMALS key per rat (plain where available, _videocorr/_manualTH where
# that's the accepted sleep-scoring variant). Extended beyond MS09 to all
# 10 rats 2026-11-08 once Peleg asked for the window-compare plot across
# the whole cohort, not just MS09.
from fano_factor_total import RAT_KEYS


def rat_report(rat):
    key = RAT_KEYS[rat]
    cfg = ANIMALS[key]

    t, states, _bouts = load_states(cfg['mat_file'])
    dt = np.diff(t, append=t[-1])
    is_sleep = np.isin(states, SLEEP_CODES)

    events_by_taste = {taste: np.loadtxt(path) for taste, path in cfg['taste_files'].items()}
    all_events = np.sort(np.concatenate(list(events_by_taste.values())))
    training_blocks = derive_training_blocks(all_events, cfg['licl_time_s'])
    block_labels = label_blocks(training_blocks)

    print(f"\n=== {rat} -- sleep in the 30min before each Training-day block ===")
    print(f"{'Block':<10}{'window (s)':<24}{'span_s':>8}{'asleep_s':>10}{'sleep %':>9}")
    for label, (t0, _t1) in block_labels:
        win_start, win_end = t0 - PRE_BLOCK_SECONDS, t0
        mask = (t >= win_start) & (t < win_end)
        span_s = dt[mask].sum()
        sleep_s = dt[mask & is_sleep].sum()
        pct = 100 * sleep_s / span_s if span_s > 0 else float('nan')
        window_str = f"{win_start:.0f}-{win_end:.0f}"
        print(f"{label:<10}{window_str:<24}{span_s:>8.0f}{sleep_s:>10.0f}{pct:>8.1f}%")


def main():
    requested = sys.argv[1:] if len(sys.argv) > 1 else list(RAT_KEYS.keys())
    unknown = [r for r in requested if r not in RAT_KEYS]
    if unknown:
        raise SystemExit(f"Unknown rat(s): {unknown}. Known rats: {list(RAT_KEYS.keys())}")
    for rat in requested:
        rat_report(rat)


if __name__ == '__main__':
    main()
