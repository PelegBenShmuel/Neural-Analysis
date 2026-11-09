"""
Fano factor computed in a sleep-selected 5min window (instead of the fixed
4min pre-block window fano_factor_total.py uses) -- Peleg's request,
2026-11-08: within the 30 minutes before each Training-day block, find a
5-minute sub-window that's at least 75% asleep (NREM+REM), then compute
Fano factor (Var/Mean, 1s bins) in THAT window instead of an arbitrary
fixed one -- the idea being to look at Fano during a comparable brain
state across blocks, not just whatever activity happens to precede the
block. First pass, MS09 only (build-then-judge, same as the cross-rat
Fano matrix's own history).

Reuses existing helpers rather than reimplementing anything:
load_states() (training_day_sleep_state_extraction.py) for sleep state,
derive_training_blocks/label_blocks for block times (same as
sleep_before_block.py), fano_of_window()/assign_regions() from
fano_factor_total.py/MS_buzcode_analysis.py for the actual Fano
computation -- identical math to the main matrix, just a different window
per block.

Window search: slide a 5min window across the 30min pre-block period in
10s steps; among all candidates with sleep fraction >= 75%, keep the one
with the highest sleep fraction (ties broken by whichever starts latest,
i.e. closest to the block). A block with no qualifying 5min window (e.g.
Block 1, which barely has any sleep at all in its 30min pre-block period)
is left blank for that block -- not fabricated.

Usage (np_analysis -- needs openpyxl via fano_factor_total.py's import,
matplotlib): python fano_in_sleep_window.py [RAT ...]
Defaults to MS09.
"""
import sys
import os

import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, NAS_PELEG, assign_regions, copy_to_share_safely, derive_training_blocks, load_spike_sorted_data
from training_day_sleep_state_extraction import load_states
from training_day_response_phases import label_blocks
from fano_factor_total import fano_of_window
from sleep_before_block import RAT_KEYS, PRE_BLOCK_SECONDS as SEARCH_WINDOW_SECONDS, SLEEP_CODES

SLEEP_WINDOW_SECONDS = 5 * 60     # the window Fano is actually computed in
SLEEP_FRACTION_THRESHOLD = 0.75
SEARCH_STEP_SECONDS = 10          # slide step when searching for a qualifying window

SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"
REGION_COLORS = {'GC': '#2a78d6', 'S1': '#eb6834'}


def find_best_sleep_window(t, dt, is_sleep, search_start, search_end, require_threshold=True):
    """Slides a SLEEP_WINDOW_SECONDS window across [search_start, search_end)
    in SEARCH_STEP_SECONDS steps. Always tracks the single highest-sleep-
    fraction candidate found (ties broken by the latest start, i.e. closest
    to the block) and returns (win_start, win_end, sleep_frac) for it --
    even if its fraction is below SLEEP_FRACTION_THRESHOLD. With
    require_threshold=True (the default -- used wherever "no real sleep
    window" should mean "skip this block", e.g. the standalone
    sleep-window-only plot), returns None instead if the best candidate
    doesn't clear the threshold. require_threshold=False (added 2026-11-08,
    Peleg's explicit request to still see Block 1 -- "~2% asleep over the
    whole 30min" -- plotted on the same 5min-window Fano, not left blank)
    returns the best candidate regardless, so the caller can decide what to
    do with a low-sleep window itself."""
    best = None
    start = search_start
    while start + SLEEP_WINDOW_SECONDS <= search_end:
        end = start + SLEEP_WINDOW_SECONDS
        mask = (t >= start) & (t < end)
        span = dt[mask].sum()
        if span > 0:
            frac = dt[mask & is_sleep].sum() / span
            if best is None or frac > best[2] or (frac == best[2] and start > best[0]):
                best = (start, end, frac)
        start += SEARCH_STEP_SECONDS
    if best is not None and require_threshold and best[2] < SLEEP_FRACTION_THRESHOLD:
        return None
    return best


def main():
    requested = sys.argv[1:] if len(sys.argv) > 1 else ['MS09']

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.set_facecolor(SURFACE)
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

        fano_by_region_block = {'GC': [[] for _ in range(7)], 'S1': [[] for _ in range(7)]}
        for cid in good_clusters:
            region = region_by_cluster[cid]
            if region not in ('GC', 'S1'):
                continue
            spikes = spike_times_samples[spike_clusters == cid] / sample_rate
            for i, best in enumerate(chosen_windows):
                if best is None:
                    continue
                win_start, win_end, _frac = best
                ff = fano_of_window(spikes, win_start, win_end)
                if ff is not None:
                    fano_by_region_block[region][i].append(ff)

        for region, color in REGION_COLORS.items():
            means = [np.mean(v) if v else np.nan for v in fano_by_region_block[region]]
            sems = [np.std(v, ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0 for v in fano_by_region_block[region]]
            n_units = max((len(v) for v in fano_by_region_block[region]), default=0)
            ax.errorbar(blocks_x, means, yerr=sems, color=color, marker='o', markersize=6,
                        linewidth=2, capsize=3, label=f"{rat} {region} (n={n_units})", zorder=3)

    ax.set_xticks(blocks_x)
    ax.set_xlabel("Training-day block", fontsize=10.5, color=SECONDARY_INK)
    ax.set_ylabel("Fano factor (Var/Mean, 1s bins, best 5min sleep window)", fontsize=10.5, color=SECONDARY_INK)
    ax.set_title(f"Fano factor in a sleep-selected 5min window (≥{SLEEP_FRACTION_THRESHOLD:.0%} asleep, "
                 f"within 30min pre-block)", fontsize=12, color=PRIMARY_INK, pad=14, loc='left', fontweight='medium')
    ax.tick_params(colors=MUTED_INK)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('left', 'bottom'):
        ax.spines[spine].set_color(GRIDLINE)
    ax.legend(frameon=False, fontsize=9.5, labelcolor=SECONDARY_INK, loc='best')
    fig.tight_layout()

    local_path = "/tmp/FanoFactor_SleepWindow_MS09_GCvsS1.png"
    plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
    print(f"\nWrote {local_path}")

    nas_dir = f"{NAS_PELEG}/CrossRatAnalysis"
    os.makedirs(nas_dir, exist_ok=True)
    copy_to_share_safely(local_path, nas_dir)
    print(f"Copied to {nas_dir}/")


if __name__ == '__main__':
    main()
