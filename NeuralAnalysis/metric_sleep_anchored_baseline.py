"""
Generalizes fano_sleep_anchored_baseline.py to compute all 3 metrics
(Fano factor, CV, Firing rate) in the same sleep-anchored 4min window, in
ONE spike-data pass per rat -- Peleg's request, 2026-11-10, to extend the
Block1-vs-sleep-window comparison to CV/FR too, split by GC/S1 same as
Fano. Reuses each metric's own window function unchanged: fano_of_window,
cv_of_window, firing_rate_of_window.

Usage (np_analysis): python metric_sleep_anchored_baseline.py [WINDOW_MINUTES MIN_SLEEP_MINUTES]
Defaults to 20min window / 15min sleep (Peleg's last example, 2026-11-10).
Prints one table per metric; copy the numbers into
<metric>_sleep_baseline_compare.py's hardcoded dict same as the Fano one.
"""
import sys
import os

import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, assign_regions, load_spike_sorted_data
from postlicl_sleep_window import good_rats, first_sleep_window_after_licl
from fano_factor_total import RAT_KEYS, PRE_BLOCK_SECONDS, fano_of_window
from coefficient_of_variation import cv_of_window
from firing_rate_total import firing_rate_of_window

METRIC_FUNCS = {'fano': fano_of_window, 'cv': cv_of_window, 'fr': firing_rate_of_window}


def main():
    window_minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    min_sleep_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    rats = good_rats()
    print(f"Good rats: {rats}\n")

    all_results = {metric: {} for metric in METRIC_FUNCS}

    for rat in rats:
        key = RAT_KEYS[rat]
        cfg = ANIMALS[key]
        result, skip_reason = first_sleep_window_after_licl(cfg, window_minutes, min_sleep_minutes)
        if result is None:
            print(f"[SKIP] {rat}: {skip_reason}")
            continue
        _start, window_end, _sleep_s = result

        (spike_times_samples, spike_clusters, sample_rate, good_clusters,
         events_by_taste, all_events) = load_spike_sorted_data(cfg)
        region_by_cluster = assign_regions(good_clusters, cfg, label_undefined=True)

        values_by_region = {metric: {'GC': [], 'S1': []} for metric in METRIC_FUNCS}
        for cid in good_clusters:
            region = region_by_cluster[cid]
            if region not in ('GC', 'S1'):
                continue
            spikes = spike_times_samples[spike_clusters == cid] / sample_rate
            for metric, func in METRIC_FUNCS.items():
                val = func(spikes, window_end, window_end + PRE_BLOCK_SECONDS)
                if val is not None:
                    values_by_region[metric][region].append(val)

        for metric in METRIC_FUNCS:
            for region, values in values_by_region[metric].items():
                if values:
                    all_results[metric][(rat, region)] = (len(values), float(np.mean(values)))

    for metric in METRIC_FUNCS:
        print(f"\n=== {metric} ===")
        print(f"{'Rat':<8}{'region':<10}{'n':>4}{'mean':>12}")
        for (rat, region), (n, mean_val) in sorted(all_results[metric].items()):
            print(f"{rat:<8}{region:<10}{n:>4}{mean_val:>12.3f}")


if __name__ == '__main__':
    main()
