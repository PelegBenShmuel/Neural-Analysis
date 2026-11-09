"""
Side-by-side comparison of the two Fano-factor windowing schemes this
project now has -- Peleg's request, 2026-11-08: one PNG, two subplots (GC,
S1), each with two lines -- the fixed 4min pre-block window
(fano_factor_total.py's convention) vs. the sleep-selected best-5min window
(>=75% asleep within 30min pre-block, fano_in_sleep_window.py's convention)
-- same rat, same blocks, same units, just two different windows per block.

Reuses both existing scripts' logic directly rather than reimplementing
either: PRE_BLOCK_SECONDS/fano_of_window from fano_factor_total.py,
find_best_sleep_window/SLEEP_WINDOW_SECONDS/SEARCH_WINDOW_SECONDS/
SLEEP_CODES from fano_in_sleep_window.py, load_states from
training_day_sleep_state_extraction.py. Nothing about either window's own
definition is changed here -- this script only adds the shared figure.

Usage (np_analysis): python fano_window_compare.py [RAT ...]
Defaults to MS09.
"""
import sys
import os

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import wilcoxon

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, NAS_PELEG, assign_regions, copy_to_share_safely, derive_training_blocks, load_spike_sorted_data
from training_day_sleep_state_extraction import load_states
from training_day_response_phases import label_blocks
from fano_factor_total import PRE_BLOCK_SECONDS as FIXED_WINDOW_SECONDS, fano_of_window
from fano_in_sleep_window import SEARCH_WINDOW_SECONDS, SLEEP_CODES, SLEEP_FRACTION_THRESHOLD, find_best_sleep_window
from sleep_before_block import RAT_KEYS

SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"
WINDOW_COLORS = {'4min pre-block': '#2a78d6', '5min sleep (best)': '#eb6834'}


def compute_both_windows(rat):
    """Returns {region: {window_label: [[block1 vals], ..., [block7 vals]]}}."""
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

    # require_threshold=False (Peleg's explicit request, 2026-11-08): still
    # compute Block 1's 5min window and plot it, even though its best
    # candidate is nowhere near 75% asleep -- better to show the low-sleep
    # number than a gap, as long as it's clearly flagged as such.
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
    # Paired (cluster, block) observations for the Wilcoxon signed-rank test
    # (fano_window_wilcoxon.py's own convention, computed inline here too --
    # Peleg's request, 2026-11-08 -- to avoid a second full spike-data
    # reload just to re-derive the same pairs for an annotation).
    paired = {'GC': ([], []), 'S1': ([], [])}

    for cid in good_clusters:
        region = region_by_cluster[cid]
        if region not in ('GC', 'S1'):
            continue
        spikes = spike_times_samples[spike_clusters == cid] / sample_rate
        for i, (label, (t0, _t1)) in enumerate(block_labels):
            ff_fixed = fano_of_window(spikes, t0 - FIXED_WINDOW_SECONDS, t0)
            if ff_fixed is not None:
                out[region]['4min pre-block'][i].append(ff_fixed)

            best = sleep_windows[i]
            ff_sleep = fano_of_window(spikes, best[0], best[1]) if best is not None else None
            if ff_sleep is not None:
                out[region]['5min sleep (best)'][i].append(ff_sleep)

            if ff_fixed is not None and ff_sleep is not None:
                paired[region][0].append(ff_fixed)
                paired[region][1].append(ff_sleep)

    sleep_fracs = [best[2] for best in sleep_windows]
    return out, sleep_fracs, paired


def wilcoxon_annotation(paired, region):
    """One-line Wilcoxon signed-rank summary for this region's paired
    (4min, 5min-sleep) observations -- same test/pairing as
    fano_window_wilcoxon.py, 2 tests per rat (GC, S1), not one per block."""
    fixed, sleep = paired[region]
    n = len(fixed)
    if n < 1:
        return "Wilcoxon: no paired observations"
    diff = np.array(fixed) - np.array(sleep)
    if np.all(diff == 0):
        return f"Wilcoxon: n={n}, all differences zero"
    stat, p = wilcoxon(fixed, sleep)
    return f"Wilcoxon: n={n}, medianΔ={np.median(diff):+.3f}, p={p:.3g}"


def plot_region(ax, region, data, rat, sleep_fracs, paired):
    blocks_x = np.arange(1, 8)
    for window_label, color in WINDOW_COLORS.items():
        block_values = data[window_label]
        means = [np.mean(v) if v else np.nan for v in block_values]
        sems = [np.std(v, ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0 for v in block_values]
        n_units = max((len(v) for v in block_values), default=0)
        ax.errorbar(blocks_x, means, yerr=sems, color=color, marker='o', markersize=6,
                    linewidth=2, capsize=3, label=f"{window_label} (n={n_units})", zorder=3)

        # Flag any sleep-window point built from a window that never
        # reached 75% asleep (currently only possible for Block 1, which
        # has ~2% sleep in its whole 30min pre-block period) -- a hollow
        # ring + "~X% asleep" label, so a low-sleep point never looks like
        # an ordinary one just because it's plotted at all.
        if window_label == '5min sleep (best)':
            for i, frac in enumerate(sleep_fracs):
                if frac < SLEEP_FRACTION_THRESHOLD and not np.isnan(means[i]):
                    ax.scatter([blocks_x[i]], [means[i]], s=130, facecolors='none',
                               edgecolors=PRIMARY_INK, linewidths=1.3, zorder=4)
                    ax.annotate(f"~{frac:.0%} asleep", (blocks_x[i], means[i]),
                                textcoords="offset points", xytext=(8, -14),
                                fontsize=8.5, color=MUTED_INK)

    ax.set_facecolor(SURFACE)
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
    # One PNG per rat (Peleg's explicit request, 2026-11-08: "כל חולדה אני
    # רוצה תמונה" -- every rat, one picture each), not one combined figure.
    requested = sys.argv[1:] if len(sys.argv) > 1 else list(RAT_KEYS.keys())
    unknown = [r for r in requested if r not in RAT_KEYS]
    if unknown:
        raise SystemExit(f"Unknown rat(s): {unknown}. Known rats: {list(RAT_KEYS.keys())}")

    nas_dir = f"{NAS_PELEG}/CrossRatAnalysis"
    os.makedirs(nas_dir, exist_ok=True)

    for rat in requested:
        print(f"\nComputing both windows for {rat}...")
        try:
            data, sleep_fracs, paired = compute_both_windows(rat)
        except Exception as e:
            print(f"[SKIP] {rat}: {type(e).__name__}: {e}")
            continue

        fig, (ax_gc, ax_s1) = plt.subplots(1, 2, figsize=(13, 5.5), sharey=False)
        plot_region(ax_gc, 'GC', data['GC'], rat, sleep_fracs, paired)
        plot_region(ax_s1, 'S1', data['S1'], rat, sleep_fracs, paired)
        ax_gc.set_ylabel("Fano factor (Var/Mean, 1s bins)", fontsize=10.5, color=SECONDARY_INK)
        fig.suptitle(f"{rat}: 4min pre-block vs. sleep-selected 5min window (≥{SLEEP_FRACTION_THRESHOLD:.0%} asleep)",
                     fontsize=13, color=PRIMARY_INK, x=0.02, ha='left', fontweight='medium')
        fig.tight_layout(rect=[0, 0, 1, 0.94])

        local_path = f"/tmp/FanoFactor_WindowCompare_{rat}_GC_S1.png"
        plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
        plt.close(fig)
        print(f"Wrote {local_path}")
        copy_to_share_safely(local_path, nas_dir)
    print(f"Copied to {nas_dir}/")


if __name__ == '__main__':
    main()
