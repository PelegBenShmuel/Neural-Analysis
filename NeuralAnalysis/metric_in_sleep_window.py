"""
Generalizes fano_in_sleep_window.py to any of the 3 metrics -- Peleg's
request, 2026-11-11 ("בדיוק את אותם הגרפים רק ב-FR CV"), same design
(sleep-selected best-5min window per block, >=75% asleep, Block 1 left
blank if no qualifying window -- unlike the WindowCompare/trajectory
scripts, this one does NOT force Block 1 to show a below-threshold point),
parameterized by METRIC_CONFIG/METRIC_FUNCS instead of copy-pasting.

Usage (np_analysis): python metric_in_sleep_window.py <fano|fr|cv> [RAT ...]
Defaults to MS09.
"""
import sys
import os

import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, assign_regions, copy_to_share_safely, derive_training_blocks, load_spike_sorted_data
from training_day_sleep_state_extraction import load_states
from training_day_response_phases import label_blocks
from sleep_before_block import RAT_KEYS, PRE_BLOCK_SECONDS as SEARCH_WINDOW_SECONDS, SLEEP_CODES
from fano_in_sleep_window import SLEEP_FRACTION_THRESHOLD, find_best_sleep_window
from plot_metric_block_trend import METRIC_CONFIG
from metric_sleep_trajectory import METRIC_FUNCS

SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"
REGION_COLORS = {'GC': '#2a78d6', 'S1': '#eb6834'}


def main():
    args = sys.argv[1:]
    if not args or args[0] not in METRIC_CONFIG:
        raise SystemExit(f"First argument must be a metric: {list(METRIC_CONFIG)}")
    metric = args[0]
    metric_cfg = METRIC_CONFIG[metric]
    metric_func = METRIC_FUNCS[metric]
    requested = args[1:] if len(args) > 1 else ['MS09']

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.set_facecolor(SURFACE)
    ax.margins(x=0)
    for i in range(1, 7):
        ax.axvline(i + 0.5, color=GRIDLINE, linewidth=0.8, zorder=1)
    blocks_x = np.arange(1, 8)

    for rat in requested:
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

        print(f"\n=== {rat} -- best 5min sleep window (>={SLEEP_FRACTION_THRESHOLD:.0%} asleep) per block ===")
        chosen_windows = []
        for label, (t0, _t1) in block_labels:
            best = find_best_sleep_window(t, dt, is_sleep, t0 - SEARCH_WINDOW_SECONDS, t0)
            chosen_windows.append(best)
            if best is None:
                print(f"{label}: no qualifying 5min window in the 30min before it")
            else:
                win_start, win_end, frac = best
                print(f"{label}: {win_start:.0f}-{win_end:.0f}s  ({frac:.0%} asleep)")

        values_by_region_block = {'GC': [[] for _ in range(7)], 'S1': [[] for _ in range(7)]}
        for cid in good_clusters:
            region = region_by_cluster[cid]
            if region not in ('GC', 'S1'):
                continue
            spikes = spike_times_samples[spike_clusters == cid] / sample_rate
            for i, best in enumerate(chosen_windows):
                if best is None:
                    continue
                win_start, win_end, _frac = best
                val = metric_func(spikes, win_start, win_end)
                if val is not None:
                    values_by_region_block[region][i].append(val)

        for region, color in REGION_COLORS.items():
            means = [np.mean(v) if v else np.nan for v in values_by_region_block[region]]
            sems = [np.std(v, ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0 for v in values_by_region_block[region]]
            n_units = max((len(v) for v in values_by_region_block[region]), default=0)
            ax.errorbar(blocks_x, means, yerr=sems, color=color, marker='o', markersize=6,
                        linewidth=2, capsize=3, label=f"{rat} {region} (n={n_units})", zorder=3)

    ax.set_xticks(blocks_x)
    ax.set_xlabel("Training-day block", fontsize=10.5, color=SECONDARY_INK)
    ax.set_ylabel(f"{metric_cfg['display_name']} (best 5min sleep window)", fontsize=10.5, color=SECONDARY_INK)
    ax.set_title(f"{metric_cfg['display_name']} in a sleep-selected 5min window (≥{SLEEP_FRACTION_THRESHOLD:.0%} asleep, "
                 f"within 30min pre-block)", fontsize=12, color=PRIMARY_INK, pad=14, loc='left', fontweight='medium')
    ax.tick_params(colors=MUTED_INK)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('left', 'bottom'):
        ax.spines[spine].set_color(GRIDLINE)
    ax.legend(frameon=False, fontsize=9.5, labelcolor=SECONDARY_INK, loc='best')
    fig.tight_layout()

    local_path = f"/tmp/{metric_cfg['out_prefix']}_SleepWindow_{'_'.join(requested)}_GCvsS1.png"
    plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
    print(f"\nWrote {local_path}")

    os.makedirs(metric_cfg['xlsx_dir'], exist_ok=True)
    copy_to_share_safely(local_path, metric_cfg['xlsx_dir'])
    print(f"Copied to {metric_cfg['xlsx_dir']}/")


if __name__ == '__main__':
    main()
