"""
Generalizes fano_sleep_window_to_xlsx.py to any of the 3 metrics -- Peleg's
request, 2026-11-11, to make the Firing Rate / CV xlsx files match
FanoFactorTotal.xlsx exactly (it has "Sleep Experiment"/"Sleep Control"
sheets, the other two didn't yet).

Unlike the original Fano script (which rebuilds the whole workbook from
scratch via write_sheet() on freshly-read Experiment/Control data), this
one loads the FULL existing workbook and only replaces the two "Sleep
<Group>" sheets, leaving Experiment/Control/"Window Compare Wilcoxon"
completely untouched -- rebuilding from scratch would have silently
dropped the Wilcoxon sheet metric_window_compare.py already added.

Usage (np_analysis): python metric_sleep_window_to_xlsx.py <fano|fr|cv> [RAT ...]
Defaults to all 10 rats in RAT_KEYS.
"""
import sys
import os

import numpy as np
import openpyxl

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, assign_regions, copy_to_share_safely, derive_training_blocks, load_spike_sorted_data
from training_day_sleep_state_extraction import load_states
from training_day_response_phases import label_blocks
from fano_factor_total import RAT_KEYS, SHEET_ORDER, group_of, write_sheet
from fano_in_sleep_window import SEARCH_WINDOW_SECONDS, SLEEP_CODES, find_best_sleep_window
from plot_metric_block_trend import METRIC_CONFIG
from metric_sleep_trajectory import METRIC_FUNCS

SLEEP_SHEET_NAMES = {group: f"Sleep {group}" for group in SHEET_ORDER}


def rows_for_rat_sleep_window(metric_cfg, metric_func, rat):
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

    col_suffix = metric_cfg['col_suffix']
    rows = []
    for cid in good_clusters:
        spikes = spike_times_samples[spike_clusters == cid] / sample_rate
        row = {"rat": rat, "cluster": cid, "region": region_by_cluster[cid]}
        for i, best in enumerate(sleep_windows, start=1):
            val = metric_func(spikes, best[0], best[1]) if best is not None else None
            row[f"block{i}{col_suffix}"] = val if val is not None else ""
        rows.append(row)
    return rows


def main():
    args = sys.argv[1:]
    if not args or args[0] not in METRIC_CONFIG:
        raise SystemExit(f"First argument must be a metric: {list(METRIC_CONFIG)}")
    metric = args[0]
    metric_cfg = METRIC_CONFIG[metric]
    metric_func = METRIC_FUNCS[metric]

    requested = args[1:] if len(args) > 1 else list(RAT_KEYS.keys())
    unknown = [r for r in requested if r not in RAT_KEYS]
    if unknown:
        raise SystemExit(f"Unknown rat(s): {unknown}. Known rats: {list(RAT_KEYS.keys())}")

    fieldnames = ["rat", "cluster", "region"] + [f"block{i}{metric_cfg['col_suffix']}" for i in range(1, 8)]

    sleep_rows = []
    for rat in requested:
        print(f"Computing {rat}...")
        try:
            rows = rows_for_rat_sleep_window(metric_cfg, metric_func, rat)
        except Exception as e:
            print(f"[SKIP] {rat}: {type(e).__name__}: {e}")
            continue
        counts = {}
        for row in rows:
            counts[row['region']] = counts.get(row['region'], 0) + 1
        print(f"{rat}: {len(rows)} units -> {counts}")
        sleep_rows.extend(rows)

    sleep_rows_by_group = {group: [] for group in SHEET_ORDER}
    for row in sleep_rows:
        sleep_rows_by_group[group_of(row['rat'])].append(row)

    xlsx_path = f"{metric_cfg['xlsx_dir']}/{metric_cfg['xlsx_name']}"
    wb = openpyxl.load_workbook(xlsx_path)   # full load -- preserves every other sheet untouched
    for group, sheet_name in SLEEP_SHEET_NAMES.items():
        if sheet_name in wb.sheetnames:
            del wb[sheet_name]
        n = write_sheet(wb, sheet_name, sleep_rows_by_group[group], fieldnames)
        print(f"Sheet '{sheet_name}': {n} unit rows + mean rows")

    local_xlsx = f"/tmp/{metric_cfg['xlsx_name']}"
    wb.save(local_xlsx)
    print(f"Wrote {local_xlsx}")

    copy_to_share_safely(local_xlsx, metric_cfg['xlsx_dir'])
    print(f"Copied to {metric_cfg['xlsx_dir']}/")


if __name__ == '__main__':
    main()
