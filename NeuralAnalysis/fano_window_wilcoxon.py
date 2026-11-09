"""
One Wilcoxon signed-rank test per region (GC, S1) per rat, comparing the
two Fano-factor windowing schemes (fixed 4min pre-block vs. sleep-selected
best-5min window) -- Peleg's request, 2026-11-08, as a follow-up to
fano_window_compare.py's plot. Paired by (cluster, block): each unit's own
4min-window Fano and 5min-sleep-window Fano for the same block form one
pair, pooled across all 7 blocks and all units in that region -- 2 tests
per rat (GC, S1), not one per block, per Peleg's explicit call ("מבחן אחד
ל-GC ומבחן אחד ל-S1 ולכל חולדה 2 מבחנים").

A (cluster, block) pair is only included if BOTH windows produced a real
Fano value for it (fano_of_window returns None when a unit never spiked in
that window) -- an unpaired observation can't go into a paired test.

Reuses the same loading/windowing helpers as fano_window_compare.py
(load_states, load_spike_sorted_data, derive_training_blocks, label_blocks,
assign_regions, find_best_sleep_window, fano_of_window) rather than
duplicating them -- this script only adds the pairing + the test itself.

Usage (np_analysis -- needs scipy): python fano_window_wilcoxon.py [RAT ...]
Defaults to all rats in RAT_KEYS (extended from MS09-only, 2026-11-08, once
Peleg asked to run this across the whole cohort).
"""
import sys
import os

import numpy as np
from scipy.stats import wilcoxon

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, assign_regions, derive_training_blocks, load_spike_sorted_data
from training_day_sleep_state_extraction import load_states
from training_day_response_phases import label_blocks
from fano_factor_total import PRE_BLOCK_SECONDS as FIXED_WINDOW_SECONDS, fano_of_window
from fano_in_sleep_window import SEARCH_WINDOW_SECONDS, SLEEP_CODES, find_best_sleep_window
from sleep_before_block import RAT_KEYS


def paired_values_for_rat(rat):
    """Returns {region: (fixed_values, sleep_values)} -- two same-length,
    index-aligned lists per region, one pair per (cluster, block) where
    both windows gave a real Fano value."""
    key = RAT_KEYS[rat]
    cfg = ANIMALS[key]

    t, states, _bouts = load_states(cfg['mat_file'])
    dt = np.diff(t, append=t[-1])
    is_sleep = np.isin(states, SLEEP_CODES)

    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_spike_sorted_data(cfg)
    training_blocks = derive_training_blocks(all_events, cfg['licl_time_s'])
    block_labels = label_blocks(training_blocks)
    region_by_cluster = assign_regions(good_clusters, cfg, label_undefined=True)

    sleep_windows = [find_best_sleep_window(t, dt, is_sleep, t0 - SEARCH_WINDOW_SECONDS, t0,
                                             require_threshold=False)
                     for _label, (t0, _t1) in block_labels]

    paired = {'GC': ([], []), 'S1': ([], [])}
    for cid in good_clusters:
        region = region_by_cluster[cid]
        if region not in paired:
            continue
        spikes = spike_times_samples[spike_clusters == cid] / sample_rate
        for i, (label, (t0, _t1)) in enumerate(block_labels):
            ff_fixed = fano_of_window(spikes, t0 - FIXED_WINDOW_SECONDS, t0)
            best = sleep_windows[i]
            ff_sleep = fano_of_window(spikes, best[0], best[1]) if best is not None else None
            if ff_fixed is not None and ff_sleep is not None:
                paired[region][0].append(ff_fixed)
                paired[region][1].append(ff_sleep)
    return paired


def main():
    requested = sys.argv[1:] if len(sys.argv) > 1 else list(RAT_KEYS.keys())
    for rat in requested:
        print(f"\n=== {rat} ===")
        paired = paired_values_for_rat(rat)
        for region in ('GC', 'S1'):
            fixed, sleep = paired[region]
            n = len(fixed)
            if n < 1:
                print(f"{region}: no paired observations")
                continue
            fixed_arr, sleep_arr = np.array(fixed), np.array(sleep)
            diff = fixed_arr - sleep_arr
            if np.all(diff == 0):
                print(f"{region}: n={n}, all differences are zero -- Wilcoxon undefined")
                continue
            stat, p = wilcoxon(fixed_arr, sleep_arr)
            print(f"{region}: n={n} pairs, median(4min-sleep)={np.median(diff):+.3f}, "
                  f"W={stat:.1f}, p={p:.4g}")


if __name__ == '__main__':
    main()
