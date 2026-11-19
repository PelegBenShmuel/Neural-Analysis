"""
Generalizes fano_window_compare.py to any of the 3 metrics (Fano factor,
Firing Rate, CV) -- Peleg's request, 2026-11-11 ("גם שתעשה את הזוגות FR CV
כמו שעשית ל-FF"), same exact design (one PNG per rat, GC|S1 panels, fixed
4min pre-block window vs. sleep-selected best-5min window, paired Wilcoxon
signed-rank annotation), parameterized by METRIC_CONFIG/METRIC_FUNCS
instead of copy-pasting fano_window_compare.py twice.

Usage (np_analysis): python metric_window_compare.py <fano|fr|cv> [RAT ...]
Defaults to all 10 rats in RAT_KEYS (not the >=15-unit "good rats" filter
-- same as fano_window_compare.py's own original scope).
"""
import sys
import os

import numpy as np
import openpyxl
from openpyxl.styles import Font
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, assign_regions, copy_to_share_safely, derive_training_blocks, load_spike_sorted_data
from training_day_sleep_state_extraction import load_states
from training_day_response_phases import label_blocks
from fano_factor_total import PRE_BLOCK_SECONDS as FIXED_WINDOW_SECONDS
from fano_in_sleep_window import SEARCH_WINDOW_SECONDS, SLEEP_CODES, SLEEP_FRACTION_THRESHOLD, find_best_sleep_window
from sleep_before_block import RAT_KEYS
from plot_metric_block_trend import METRIC_CONFIG
from metric_sleep_trajectory import METRIC_FUNCS

SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"
WINDOW_COLORS = {'4min pre-block': '#2a78d6', '5min sleep (best)': '#eb6834'}


def compute_both_windows(metric_func, rat):
    """Returns {region: {window_label: [[block1 vals], ..., [block7 vals]]}}."""
    key = RAT_KEYS[rat]
    cfg = ANIMALS[key]
    licl_time_s = cfg['licl_time_s']

    t, states, _bouts = load_states(cfg['mat_file'])
    dt = np.diff(t, append=t[-1])
    is_sleep = np.isin(states, SLEEP_CODES)

    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_spike_sorted_data(cfg)
    training_blocks = derive_training_blocks(all_events, licl_time_s)
    block_labels = label_blocks(training_blocks)
    region_by_cluster = assign_regions(good_clusters, cfg, label_undefined=True)

    sleep_windows = []
    for label, (t0, _t1) in block_labels:
        best = find_best_sleep_window(t, dt, is_sleep, t0 - SEARCH_WINDOW_SECONDS, t0,
                                       require_threshold=False)
        sleep_windows.append(best)
        below = best[2] < SLEEP_FRACTION_THRESHOLD
        tag = f"{best[2]:.0%} asleep" + (" (BELOW 75% THRESHOLD)" if below else "")
        print(f"  {rat} {label}: 5min sleep window -> {tag}")

    out = {region: {'4min pre-block': [[] for _ in range(7)],
                     '5min sleep (best)': [[] for _ in range(7)]}
           for region in ('GC', 'S1')}
    paired = {'GC': ([], []), 'S1': ([], [])}
    # Per-unit, per-block raw pairs -- saved to xlsx so a later real-time
    # trajectory of this same comparison (Peleg's request, 2026-11-17) can
    # be built from this data without a second full spike-data reload.
    pair_rows = []

    for cid in good_clusters:
        region = region_by_cluster[cid]
        if region not in ('GC', 'S1'):
            continue
        spikes = spike_times_samples[spike_clusters == cid] / sample_rate
        for i, (label, (t0, _t1)) in enumerate(block_labels):
            val_fixed = metric_func(spikes, t0 - FIXED_WINDOW_SECONDS, t0)
            if val_fixed is not None:
                out[region]['4min pre-block'][i].append(val_fixed)

            best = sleep_windows[i]
            val_sleep = metric_func(spikes, best[0], best[1]) if best is not None else None
            if val_sleep is not None:
                out[region]['5min sleep (best)'][i].append(val_sleep)

            if val_fixed is not None and val_sleep is not None:
                paired[region][0].append(val_fixed)
                paired[region][1].append(val_sleep)
                pair_rows.append({
                    'rat': rat, 'region': region, 'cluster_id': int(cid), 'block_index': i + 1,
                    'block_hour_since_licl': (t0 - licl_time_s) / 3600,
                    'fixed_value': val_fixed, 'sleep_value': val_sleep,
                    'sleep_fraction': best[2], 'window_start_s': best[0], 'window_end_s': best[1],
                })

    sleep_fracs = [best[2] for best in sleep_windows]
    return out, sleep_fracs, paired, pair_rows


def wilcoxon_annotation(paired, region):
    fixed, sleep = paired[region]
    n = len(fixed)
    if n < 1:
        return "Wilcoxon: no paired observations"
    diff = np.array(fixed) - np.array(sleep)
    if np.all(diff == 0):
        return f"Wilcoxon: n={n}, all differences zero"
    stat, p = wilcoxon(fixed, sleep)
    return f"Wilcoxon: n={n}, medianΔ={np.median(diff):+.3f}, p={p:.3g}"


def plot_region(ax, region, data, rat, sleep_fracs, paired, metric_cfg):
    blocks_x = np.arange(1, 8)
    for window_label, color in WINDOW_COLORS.items():
        block_values = data[window_label]
        means = [np.mean(v) if v else np.nan for v in block_values]
        sems = [np.std(v, ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0 for v in block_values]
        n_units = max((len(v) for v in block_values), default=0)
        ax.errorbar(blocks_x, means, yerr=sems, color=color, marker='o', markersize=6,
                    linewidth=2, capsize=3, label=f"{window_label} (n={n_units})", zorder=3)

        if window_label == '5min sleep (best)':
            for i, frac in enumerate(sleep_fracs):
                if frac < SLEEP_FRACTION_THRESHOLD and not np.isnan(means[i]):
                    ax.scatter([blocks_x[i]], [means[i]], s=130, facecolors='none',
                               edgecolors=PRIMARY_INK, linewidths=1.3, zorder=4)
                    ax.annotate(f"~{frac:.0%} asleep", (blocks_x[i], means[i]),
                                textcoords="offset points", xytext=(8, -14),
                                fontsize=8.5, color=MUTED_INK)

    ax.set_facecolor(SURFACE)
    ax.margins(x=0)
    for i in range(1, 7):
        ax.axvline(i + 0.5, color=GRIDLINE, linewidth=0.8, zorder=1)
    ax.set_xticks(blocks_x)
    ax.set_xlabel("Training-day block", fontsize=10.5, color=SECONDARY_INK)
    ax.set_title(f"{rat} — {region}", fontsize=12, color=PRIMARY_INK, loc='left', fontweight='medium')
    ax.tick_params(colors=MUTED_INK)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('left', 'bottom'):
        ax.spines[spine].set_color(GRIDLINE)
    ax.legend(frameon=False, fontsize=9, labelcolor=SECONDARY_INK, loc='best')

    ax.text(0.02, 0.02, wilcoxon_annotation(paired, region), transform=ax.transAxes,
            fontsize=8.5, color=SECONDARY_INK, ha='left', va='bottom')


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

    nas_dir = metric_cfg['xlsx_dir']
    os.makedirs(nas_dir, exist_ok=True)

    wilcoxon_rows = []
    all_pair_rows = []
    for rat in requested:
        print(f"\nComputing both windows for {rat} ({metric})...")
        try:
            data, sleep_fracs, paired, pair_rows = compute_both_windows(metric_func, rat)
        except Exception as e:
            print(f"[SKIP] {rat}: {type(e).__name__}: {e}")
            continue
        all_pair_rows.extend(pair_rows)

        fig, (ax_gc, ax_s1) = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
        plot_region(ax_gc, 'GC', data['GC'], rat, sleep_fracs, paired, metric_cfg)
        plot_region(ax_s1, 'S1', data['S1'], rat, sleep_fracs, paired, metric_cfg)
        ax_gc.set_ylabel(metric_cfg['raw_ylabel'], fontsize=10.5, color=SECONDARY_INK)
        fig.suptitle(f"{rat}: 4min pre-block vs. sleep-selected 5min window "
                     f"(≥{SLEEP_FRACTION_THRESHOLD:.0%} asleep) — {metric_cfg['display_name']}",
                     fontsize=13, color=PRIMARY_INK, x=0.02, ha='left', fontweight='medium')
        fig.tight_layout(rect=[0, 0, 1, 0.94])

        local_path = f"/tmp/{metric_cfg['out_prefix']}_WindowCompare_{rat}_GC_S1.png"
        plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
        plt.close(fig)
        print(f"Wrote {local_path}")
        copy_to_share_safely(local_path, nas_dir)

        # Reuse this same run's paired data for the Wilcoxon stats sheet --
        # no second spike-data reload (same efficiency lesson Peleg taught
        # us 2026-11-05: "why you dont do it based on the FanoFactor xlsx
        # file" -- don't recompute what's already in hand).
        for region in ('GC', 'S1'):
            fixed, sleep = paired[region]
            n = len(fixed)
            if n < 1:
                wilcoxon_rows.append([rat, region, 0, "", "", "", "no paired observations"])
                continue
            diff = np.array(fixed) - np.array(sleep)
            if np.all(diff == 0):
                wilcoxon_rows.append([rat, region, n, 0.0, "", "", "all differences zero"])
                continue
            stat, p = wilcoxon(fixed, sleep)
            note = "significant (p<0.05)" if p < 0.05 else ""
            wilcoxon_rows.append([rat, region, n, round(float(np.median(diff)), 4),
                                  round(float(stat), 1), p, note])
    print(f"Copied plots to {nas_dir}/")

    xlsx_path = f"{nas_dir}/{metric_cfg['xlsx_name']}"
    wb = openpyxl.load_workbook(xlsx_path)
    sheet_name = "Window Compare Wilcoxon"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)
    header = ["rat", "region", "n_pairs", "median_diff_4min_minus_5minsleep", "W_statistic", "p_value", "note"]
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in wilcoxon_rows:
        ws.append(row)
    for col_idx, field in enumerate(header, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(14, len(field) + 2)

    # Raw per-unit, per-block pairs -- Peleg's standing rule (2026-11-17):
    # always save the underlying data, not just the plot/summary. This lets
    # a real-time trajectory of this same comparison be built later without
    # another full spike-data reload.
    pairs_sheet_name = "Window Compare Pairs"
    if pairs_sheet_name in wb.sheetnames:
        del wb[pairs_sheet_name]
    ws_pairs = wb.create_sheet(pairs_sheet_name)
    pairs_header = ["rat", "region", "cluster_id", "block_index", "block_hour_since_licl",
                     "fixed_value", "sleep_value", "sleep_fraction", "window_start_s", "window_end_s"]
    ws_pairs.append(pairs_header)
    for cell in ws_pairs[1]:
        cell.font = Font(bold=True)
    for row in all_pair_rows:
        ws_pairs.append([row['rat'], row['region'], row['cluster_id'], row['block_index'],
                          round(row['block_hour_since_licl'], 4), round(row['fixed_value'], 6),
                          round(row['sleep_value'], 6), round(row['sleep_fraction'], 4),
                          row['window_start_s'], row['window_end_s']])
    for col_idx, field in enumerate(pairs_header, start=1):
        ws_pairs.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(14, len(field) + 2)

    local_xlsx = f"/tmp/{metric_cfg['xlsx_name']}"
    wb.save(local_xlsx)
    copy_to_share_safely(local_xlsx, nas_dir)
    print(f"Added '{sheet_name}' and '{pairs_sheet_name}' sheets to {xlsx_path}")


if __name__ == '__main__':
    main()
