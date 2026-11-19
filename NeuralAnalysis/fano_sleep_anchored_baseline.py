"""
A new, per-rat "sleep-anchored baseline" Fano factor value -- Peleg's
request, 2026-11-10, first concrete step of Anan Moran's request #5 (align
by sleep, not strictly by block number -- see
project_anan_meeting_2026_11_08 memory). Finds each "good" rat's first
post-LiCl window with enough sleep in it
(postlicl_sleep_window.py's first_sleep_window_after_licl(), same
window/sleep-minute parameters), then computes Fano factor the normal way
(fano_factor_total.py's own 4-minute window, fano_of_window) but anchored
right AFTER that sleep window ends, instead of right before a Training-day
block. This is meant to replace Block 1's role as the normalization
baseline -- a per-rat baseline tied to when that rat actually had enough
sleep, not a fixed clock position shared across rats.

Explicitly a first step, not a finished pipeline (Peleg: "אני מתחיל לשחק
עם זה" -- starting to play with this): computes ONE new baseline value per
rat x region, doesn't yet extend it into a 7-point trajectory or apply it
to CV/Firing Rate. Ask Peleg before building further.

Usage (np_analysis): python fano_sleep_anchored_baseline.py [WINDOW_MINUTES MIN_SLEEP_MINUTES]
Defaults to 20min window / 15min sleep (Peleg's last example).
"""
import sys
import os

import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, assign_regions, load_spike_sorted_data
from postlicl_sleep_window import good_rats, first_sleep_window_after_licl
from fano_factor_total import RAT_KEYS, PRE_BLOCK_SECONDS, fano_of_window


def main():
    window_minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    min_sleep_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    rats = good_rats()
    print(f"Good rats: {rats}\n")
    print(f"{'Rat':<8}{'region':<10}{'n':>4}{'mean FF (4min post-sleep-window)':>36}")

    for rat in rats:
        key = RAT_KEYS[rat]
        cfg = ANIMALS[key]
        result, skip_reason = first_sleep_window_after_licl(cfg, window_minutes, min_sleep_minutes)
        if result is None:
            print(f"{rat:<8}[SKIP] {skip_reason}")
            continue
        _start, window_end, _sleep_s = result

        (spike_times_samples, spike_clusters, sample_rate, good_clusters,
         events_by_taste, all_events) = load_spike_sorted_data(cfg)
        region_by_cluster = assign_regions(good_clusters, cfg, label_undefined=True)

        ff_by_region = {'GC': [], 'S1': []}
        for cid in good_clusters:
            region = region_by_cluster[cid]
            if region not in ff_by_region:
                continue
            spikes = spike_times_samples[spike_clusters == cid] / sample_rate
            ff = fano_of_window(spikes, window_end, window_end + PRE_BLOCK_SECONDS)
            if ff is not None:
                ff_by_region[region].append(ff)

        for region, values in ff_by_region.items():
            if values:
                print(f"{rat:<8}{region:<10}{len(values):>4}{np.mean(values):>36.3f}")
            else:
                print(f"{rat:<8}{region:<10}{'0':>4}{'(no units)':>36}")


if __name__ == '__main__':
    main()
