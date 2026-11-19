"""
Cross-rat Coefficient of Variation (CV) matrix -- same structure as
fano_factor_total.py / firing_rate_total.py (Peleg's request, 2026-11-09,
from Anan Moran's meeting ask to also check CV -- see
project_anan_meeting_2026_11_08 memory). CV = SD(ISI)/Mean(ISI) in the 4
minutes immediately BEFORE each of the 7 Training-day blocks, per unit --
same window as Fano factor and Firing Rate, for direct cross-metric
comparability (CV=1 is the Poisson reference, same as Fano factor's
Fano=1).

Reuses fano_factor_total.py's shared machinery unchanged: RAT_KEYS,
SHEET_ORDER/group_of, PRE_BLOCK_SECONDS, write_sheet (region coloring +
bold population-mean rows per (rat, region) group) -- and reuses
coefficient_of_variation.py's own cv_of_window() (SD(ISI)/Mean(ISI),
requires >=MIN_ISIS_FOR_CV=5 ISIs in the window, else None) rather than
reimplementing the CV math a second time. That script's own window was
30min (for a Mann-Whitney sub-window test); this one is the 4min window
instead, but the same function works unchanged for any (window_start,
window_end).

Usage (np_analysis -- needs openpyxl): python coefficient_of_variation_total.py [RAT ...]
Defaults to all rats in RAT_KEYS (the same 10 rats as the Fano/FR
matrices -- MS08/MS23 excluded, no gc_bounds_um at all).

Writes CoefficientOfVariationTotal.xlsx locally first (/tmp/), then copies
to Z:\\Peleg\\CrossRatAnalysis\\Coefficient of Variation\\ (Peleg's
per-metric subfolder reorg, 2026-11-09).
"""
import sys
import os

import numpy as np
import openpyxl

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import (ANIMALS, NAS_PELEG, assign_regions, copy_to_share_safely,
                                  derive_training_blocks, load_spike_sorted_data)
from training_day_response_phases import label_blocks
from fano_factor_total import RAT_KEYS, SHEET_ORDER, PRE_BLOCK_SECONDS, write_sheet, group_of
from coefficient_of_variation import cv_of_window

CROSS_RAT_CV_DIR = f"{NAS_PELEG}/CrossRatAnalysis/Coefficient of Variation"


def rows_for_rat(rat, fieldnames):
    key = RAT_KEYS[rat]
    cfg = ANIMALS[key]
    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_spike_sorted_data(cfg)
    training_blocks = derive_training_blocks(all_events, cfg['licl_time_s'])
    block_labels = label_blocks(training_blocks)
    region_by_cluster = assign_regions(good_clusters, cfg, label_undefined=True)

    rows = []
    for cid in good_clusters:
        spikes = spike_times_samples[spike_clusters == cid] / sample_rate
        row = {"rat": rat, "cluster": cid, "region": region_by_cluster[cid]}
        for i, (label, (t0, _t1)) in enumerate(block_labels, start=1):
            cv = cv_of_window(spikes, t0 - PRE_BLOCK_SECONDS, t0)
            row[f"block{i}_cv"] = cv if cv is not None else ""
        rows.append(row)
    return rows


def main():
    requested = sys.argv[1:] if len(sys.argv) > 1 else list(RAT_KEYS.keys())
    unknown = [r for r in requested if r not in RAT_KEYS]
    if unknown:
        raise SystemExit(f"Unknown rat(s): {unknown}. Known rats: {list(RAT_KEYS.keys())}")
    if len(requested) < len(RAT_KEYS):
        print(f"Partial run: {requested} only (full set is {list(RAT_KEYS.keys())})")

    fieldnames = ["rat", "cluster", "region"] + [f"block{i}_cv" for i in range(1, 8)]
    rows_by_group = {'Experiment': [], 'Control': []}

    for rat in requested:
        print(f"Computing {rat}...")
        try:
            rows = rows_for_rat(rat, fieldnames)
        except Exception as e:
            print(f"[SKIP] {rat}: {type(e).__name__}: {e}")
            continue
        rows_by_group[group_of(rat)].extend(rows)
        region_counts = {}
        for row in rows:
            region_counts[row['region']] = region_counts.get(row['region'], 0) + 1
        print(f"{rat} ({group_of(rat)}): {len(rows)} units -> {region_counts}")

    local_xlsx = "/tmp/CoefficientOfVariationTotal.xlsx"
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name in SHEET_ORDER:
        n = write_sheet(wb, sheet_name, rows_by_group[sheet_name], fieldnames)
        print(f"Sheet '{sheet_name}': {n} unit rows + mean rows")
    wb.save(local_xlsx)
    print(f"Wrote {local_xlsx}")

    os.makedirs(CROSS_RAT_CV_DIR, exist_ok=True)
    copy_to_share_safely(local_xlsx, CROSS_RAT_CV_DIR)
    print(f"Copied to {CROSS_RAT_CV_DIR}/")


if __name__ == '__main__':
    main()
