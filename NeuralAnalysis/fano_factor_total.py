"""
Cross-rat Fano factor matrix -- rebuilt 2026-11-05 (the previous version was
deleted at Peleg's request to redesign the output layout; same core
computation, different layout).

For every rat with spike-sorted Training-day data: Fano factor (Var/Mean of
1s-binned spike counts) in the 4 minutes immediately BEFORE each of the 7
Training-day blocks, per unit -- one row per unit, one column per block. Not
a statistical comparison (c.f. pre_block_baseline_fano_factor.py's 30min
Block1-vs-Block7 test) -- just the raw per-block Fano values across the whole
Training day, for every rat at once.

Every unit is labeled 'GC', 'S1', or 'undefined' -- never dropped (see
assign_regions's label_undefined=True mode, feedback_gc_s1_separation
memory). A rat with no gc_bounds_um entry at all (MS20, MS21, MS22, MS23 as
of 2026-11-05) comes back entirely 'undefined' -- not an error, just a
boundary-data gap to close later with Mai's electrode-track file.

MS08 was run once (2026-11-05), came back 100% undefined (no gc_bounds_um),
and was dropped from RAT_KEYS at Peleg's request -- add it back once MS08
has real boundary data.

Output layout (Peleg's explicit redesign, 2026-11-05): ONE xlsx with TWO
sheets -- "Experiment" and "Control" -- per README.md's "Animals & groups"
(Control/Familiar = MS15/MS18/MS20, Experimental = every other rat). Each
sheet is sorted by rat, then region (GC, S1, undefined), then cluster, so
every rat's GC/S1 split is a contiguous, color-coded block within its
group's sheet (replaces the old single-sheet version sorted by region first
across all rats). Each (rat, region) block ends with one bold, gold-filled
population-mean row (mean per block across that group's units, skipping
units with no data for a given block) -- Peleg's explicit request,
2026-11-05, so a per-population summary sits right under its own units
without a separate table.

Usage (from np_analysis -- needs openpyxl): python fano_factor_total.py [RAT ...]
With no arguments, runs all rats in RAT_KEYS. With one or more rat names,
only those rats are processed -- the output reflects only the rats actually
requested that run (does NOT merge with a previous run's rows).

Writes FanoFactorTotal.xlsx locally first (/tmp/), then copies it to
Z:\\Peleg\\CrossRatAnalysis\\.
"""
import sys
import os

import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import (ANIMALS, NAS_PELEG, assign_regions, copy_to_share_safely,
                                  derive_training_blocks, load_spike_sorted_data)
from training_day_response_phases import label_blocks

PRE_BLOCK_SECONDS = 4 * 60    # 4 minutes
BIN_WIDTH = 1.0               # s

# One ANIMALS key per physical rat -- each rat's *accepted* sleep-scoring
# key, i.e. the one with spike_sorted_dir actually set (see MS_buzcode_
# analysis.py's per-rat comments, e.g. "MS14's accepted sleep-scoring key").
RAT_KEYS = {
    'MS09': 'MS09',
    'MS11': 'MS11',
    'MS14': 'MS14_videocorr',
    'MS15': 'MS15_manualTH',
    'MS18': 'MS18_videocorr',
    'MS20': 'MS20_videocorr',
    'MS21': 'MS21_videocorr',
    'MS22': 'MS22_videocorr',
    # MS23 dropped 2026-11-05 at Peleg's request, same reason as MS08: 100%
    # undefined (no gc_bounds_um at all -- neither Mai's electrode_track
    # file nor the lab dashboard/gc_boundaries.csv has an entry for it).
    # Add back once MS23 has real boundary data.
    'MS24': 'MS24_CTAtoExt',
    'MS25': 'MS25',
}

# MS24 and MS25 both have PROVISIONAL gc_bounds_um (Mai's own
# config/gc_boundaries.csv marks both provisional=True, "recount after
# preprocessing") -- their region counts/labels in the output may change
# once Mai confirms. Not excluded, since label_undefined=True means nothing
# is silently dropped either way -- just flagged here so results aren't
# over-trusted.
PROVISIONAL_BOUNDS_RATS = {'MS24', 'MS25'}

# Per README.md "Animals & groups": Control/Familiar = MS15/MS18/MS20
# (sucrose pre-exposed), Experimental = every other rat (sucrose novel,
# real CTA).
CONTROL_RATS = {'MS15', 'MS18', 'MS20'}
SHEET_ORDER = ['Experiment', 'Control']


def group_of(rat):
    return 'Control' if rat in CONTROL_RATS else 'Experiment'


REGION_FILL = {
    # Full 8-digit ARGB (FF alpha) -- a 6-digit hex gets padded with 00
    # (fully transparent) by openpyxl, a silent-invisible-fill gotcha found
    # 2026-11-04.
    'GC': PatternFill(start_color='FFF8CBD1', end_color='FFF8CBD1', fill_type='solid'),       # pink
    'S1': PatternFill(start_color='FFC9DDF5', end_color='FFC9DDF5', fill_type='solid'),       # blue
    'undefined': PatternFill(start_color='FFE3E3E3', end_color='FFE3E3E3', fill_type='solid'),  # gray
}
REGION_ORDER = {'GC': 0, 'S1': 1, 'undefined': 2}

# One dedicated highlight for every per-(rat, region) population-mean row,
# across all regions -- Peleg's explicit request, 2026-11-05: bold + a
# distinct color from the GC/S1/undefined fills above it, so a mean row
# reads as "this is a summary", not just another unit.
SUMMARY_FILL = PatternFill(start_color='FFFFD966', end_color='FFFFD966', fill_type='solid')  # gold
SUMMARY_FONT = Font(bold=True)


def fano_of_window(spikes, window_start, window_end):
    """Fano = Var(1s-binned counts)/Mean(counts) over [window_start, window_end).
    None if the unit never spiked in the window (mean=0, Fano undefined)."""
    edges = np.arange(window_start, window_end + BIN_WIDTH, BIN_WIDTH)
    counts, _ = np.histogram(spikes, bins=edges)
    counts = counts.astype(float)
    mean_count = counts.mean()
    if mean_count == 0:
        return None
    return counts.var(ddof=1) / mean_count


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
            ff = fano_of_window(spikes, t0 - PRE_BLOCK_SECONDS, t0)
            row[f"block{i}_fano"] = ff if ff is not None else ""
        rows.append(row)
    return rows


def write_mean_row(ws, group_rows, block_fields, fieldnames):
    """One bold, gold-filled population-mean row for a (rat, region) group --
    mean per block across that group's units, skipping units with no data
    (empty cell) for that block rather than treating them as 0."""
    rat, region = group_rows[0]['rat'], group_rows[0]['region']
    summary = {"rat": rat, "cluster": f"MEAN (n={len(group_rows)})", "region": region}
    for field in block_fields:
        vals = [r[field] for r in group_rows if r[field] != ""]
        summary[field] = float(np.mean(vals)) if vals else ""
    ws.append([summary[field] for field in fieldnames])
    for cell in ws[ws.max_row]:
        cell.fill = SUMMARY_FILL
        cell.font = SUMMARY_FONT


def write_sheet(wb, title, rows, fieldnames):
    ws = wb.create_sheet(title)
    ws.append(fieldnames)
    rows = sorted(rows, key=lambda r: (r['rat'], REGION_ORDER[r['region']], r['cluster']))
    block_fields = [f for f in fieldnames if f.startswith('block')]

    current_key, current_group = None, []
    for row in rows:
        key = (row['rat'], row['region'])
        if current_group and key != current_key:
            write_mean_row(ws, current_group, block_fields, fieldnames)
            current_group = []
        current_key = key
        current_group.append(row)
        ws.append([row[field] for field in fieldnames])
        for cell in ws[ws.max_row]:
            cell.fill = REGION_FILL[row['region']]
    if current_group:
        write_mean_row(ws, current_group, block_fields, fieldnames)

    for col_idx, field in enumerate(fieldnames, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(10, len(field) + 2)
    return len(rows)


def main():
    requested = sys.argv[1:] if len(sys.argv) > 1 else list(RAT_KEYS.keys())
    unknown = [r for r in requested if r not in RAT_KEYS]
    if unknown:
        raise SystemExit(f"Unknown rat(s): {unknown}. Known rats: {list(RAT_KEYS.keys())}")
    if len(requested) < len(RAT_KEYS):
        print(f"Partial run: {requested} only (full set is {list(RAT_KEYS.keys())})")

    fieldnames = ["rat", "cluster", "region"] + [f"block{i}_fano" for i in range(1, 8)]
    rows_by_group = {'Experiment': [], 'Control': []}

    for rat in requested:
        try:
            rows = rows_for_rat(rat, fieldnames)
        except Exception as e:
            print(f"[SKIP] {rat}: {e}")
            continue
        rows_by_group[group_of(rat)].extend(rows)
        region_counts = {}
        for row in rows:
            region_counts[row['region']] = region_counts.get(row['region'], 0) + 1
        print(f"{rat} ({group_of(rat)}): {len(rows)} units -> {region_counts}")

    local_xlsx = "/tmp/FanoFactorTotal.xlsx"
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name in SHEET_ORDER:
        n = write_sheet(wb, sheet_name, rows_by_group[sheet_name], fieldnames)
        print(f"Sheet '{sheet_name}': {n} rows")
    wb.save(local_xlsx)
    print(f"Wrote {local_xlsx}")

    nas_dir = f"{NAS_PELEG}/CrossRatAnalysis"
    os.makedirs(nas_dir, exist_ok=True)
    copy_to_share_safely(local_xlsx, nas_dir)
    print(f"Copied to {nas_dir}/")


if __name__ == '__main__':
    main()
