"""
Adds two sheets, "Sleep Experiment" and "Sleep Control", to
FanoFactorTotal.xlsx -- Peleg's request, 2026-11-08: all the per-unit Fano
factor data from the sleep-selected 5min window
(fano_in_sleep_window.py / fano_window_compare.py's convention: within the
30min before each block, the best 5min sub-window by sleep fraction, used
even if it never reaches 75% asleep -- same require_threshold=False choice
as the window-compare plots, so every block gets a number instead of a
gap). First built as ONE combined sheet ("Sleep Fano Factor"); Peleg then
asked to split it the same way as the other two (Experiment/Control) --
same row schema (rat, cluster, region, block1_fano..block7_fano), same
region-colored + bold-mean-row formatting (reuses write_sheet/REGION_FILL
from fano_factor_total.py unchanged).

Usage (np_analysis): python fano_sleep_window_to_xlsx.py [RAT ...]
Defaults to all 10 rats in RAT_KEYS.
"""
import sys
import os

import numpy as np
import openpyxl

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, NAS_PELEG, assign_regions, copy_to_share_safely, derive_training_blocks, load_spike_sorted_data
from training_day_sleep_state_extraction import load_states
from training_day_response_phases import label_blocks
from fano_factor_total import RAT_KEYS, SHEET_ORDER, fano_of_window, group_of, write_sheet
from fano_in_sleep_window import SEARCH_WINDOW_SECONDS, SLEEP_CODES, find_best_sleep_window

FIELDNAMES = ["rat", "cluster", "region"] + [f"block{i}_fano" for i in range(1, 8)]
SLEEP_SHEET_NAMES = {group: f"Sleep {group}" for group in SHEET_ORDER}


def rows_for_rat_sleep_window(rat):
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

    rows = []
    for cid in good_clusters:
        spikes = spike_times_samples[spike_clusters == cid] / sample_rate
        row = {"rat": rat, "cluster": cid, "region": region_by_cluster[cid]}
        for i, best in enumerate(sleep_windows, start=1):
            ff = fano_of_window(spikes, best[0], best[1]) if best is not None else None
            row[f"block{i}_fano"] = ff if ff is not None else ""
        rows.append(row)
    return rows


def main():
    requested = sys.argv[1:] if len(sys.argv) > 1 else list(RAT_KEYS.keys())
    unknown = [r for r in requested if r not in RAT_KEYS]
    if unknown:
        raise SystemExit(f"Unknown rat(s): {unknown}. Known rats: {list(RAT_KEYS.keys())}")

    sleep_rows = []
    for rat in requested:
        print(f"Computing {rat}...")
        try:
            rows = rows_for_rat_sleep_window(rat)
        except Exception as e:
            print(f"[SKIP] {rat}: {type(e).__name__}: {e}")
            continue
        counts = {}
        for row in rows:
            counts[row['region']] = counts.get(row['region'], 0) + 1
        print(f"{rat}: {len(rows)} units -> {counts}")
        sleep_rows.extend(rows)

    xlsx_path = f"{NAS_PELEG}/CrossRatAnalysis/FanoFactorTotal.xlsx"
    wb_in = openpyxl.load_workbook(xlsx_path, data_only=True)

    existing_rows = {}
    for sheet_name in SHEET_ORDER:
        ws = wb_in[sheet_name]
        all_rows = list(ws.iter_rows(values_only=True))
        header, data = all_rows[0], all_rows[1:]
        idx = {name: i for i, name in enumerate(header)}
        rows = []
        for r in data:
            if isinstance(r[idx['cluster']], str):   # skip existing bold "MEAN (n=...)" rows
                continue
            rows.append({f: (r[idx[f]] if r[idx[f]] is not None else "") for f in FIELDNAMES})
        existing_rows[sheet_name] = rows

    local_xlsx = "/tmp/FanoFactorTotal.xlsx"
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name in SHEET_ORDER:
        n = write_sheet(wb, sheet_name, existing_rows[sheet_name], FIELDNAMES)
        print(f"Sheet '{sheet_name}' (unchanged): {n} unit rows + mean rows")

    sleep_rows_by_group = {group: [] for group in SHEET_ORDER}
    for row in sleep_rows:
        sleep_rows_by_group[group_of(row['rat'])].append(row)
    for group, sheet_name in SLEEP_SHEET_NAMES.items():
        n = write_sheet(wb, sheet_name, sleep_rows_by_group[group], FIELDNAMES)
        print(f"Sheet '{sheet_name}': {n} unit rows + mean rows")
    wb.save(local_xlsx)
    print(f"Wrote {local_xlsx}")

    nas_dir = f"{NAS_PELEG}/CrossRatAnalysis"
    copy_to_share_safely(local_xlsx, nas_dir)
    print(f"Copied to {nas_dir}/")


if __name__ == '__main__':
    main()
