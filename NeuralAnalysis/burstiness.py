"""
Burst Index (fraction of ISIs < 10ms) during REST -- the 30 minutes of
spontaneous activity immediately BEFORE a Training-day block starts --
compared Block 1 vs Block 7, per unit, same Block1-vs-Block7 principle as
rest_firing_rate.py and pre_block_baseline_fano_factor.py (see
project_neural_changes_training_day_2026_10 memory for the full
methodology discussion).

Supersedes the original per-block-trend version of this script (built
2026-10-22, all 7 blocks + population-mean overlay) -- Peleg's explicit
request (2026-11-03) to replace that with this Block1-vs-Block7 comparison,
same as the other two Rest-category analyses.

Burst Index = (# of ISIs below BURST_THRESHOLD_S) / (total # of ISIs) --
a RATIO computed across many ISIs at once, same situation as Fano factor
(not firing rate): a single 1-second bin can't yield its own burst-index
value, so there's no free per-second sample to test on directly. Same fix
as pre_block_baseline_fano_factor.py: split each 1800s (30min) window into
10 non-overlapping 180s (3min) sub-windows, compute one burst index per
sub-window -> 10 samples/block/unit -> Mann-Whitney U between Block 1's 10
values and Block 7's 10 values. Same n=10/side power caveat as the Fano
factor test (less power than rest_firing_rate.py's n=600 test -- real
differences may go undetected).

The population summary plot's axes use each unit's full-window (1800s)
burst index per block -- the sub-window values are only used to build the
significance test.

**2026-11-04 update:** every population-level output is now split into GC
and S1 -- the standing rule from Anan Moran (relayed by Peleg that day, see
feedback_gc_s1_separation memory): never pool GC and S1 units into one
population. A unit ventral to GC (per assign_regions/this animal's
gc_bounds_um config) is excluded entirely, not folded into either region.

Usage (from peleg_env): python burstiness.py [ANIMAL]   (default: MS08)
Requires this animal to have a gc_bounds_um entry in ANIMALS (MS_buzcode_analysis.py).
Writes output locally first (to /tmp/<animal>_burstiness), then copies onto
Z:\\Peleg\\<animal>\\Analysis\\single neuron\\Burstiness\\GC\\ and
\\...\\Burstiness\\S1\\, after first clearing out whatever was there.
"""
import sys
import os
import csv
import shutil

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import (ANIMALS, assign_regions, copy_tree_to_share_safely,
                                  derive_training_blocks, load_spike_sorted_data)
from training_day_response_phases import label_blocks

PRE_BLOCK_SECONDS = 30 * 60   # 30 minutes, same window as pre_block_baseline_fano_factor.py
BURST_THRESHOLD_S = 0.010     # 10ms
SUB_WINDOW_SECONDS = 180      # 3 minutes -> 10 sub-windows per 1800s block
N_SUB_WINDOWS = PRE_BLOCK_SECONDS // SUB_WINDOW_SECONDS


def burst_index_of_window(spikes, window_start, window_end):
    """Fraction of ISIs < BURST_THRESHOLD_S within [window_start, window_end).
    None if fewer than 2 spikes in the window (no ISI can be formed)."""
    win_spikes = spikes[(spikes >= window_start) & (spikes < window_end)]
    isis = np.diff(win_spikes)
    if len(isis) == 0:
        return None
    return float(np.sum(isis < BURST_THRESHOLD_S) / len(isis))


def sub_window_burst_indices(spikes, window_start, window_end):
    out = []
    for i in range(N_SUB_WINDOWS):
        sw_start = window_start + i * SUB_WINDOW_SECONDS
        b = burst_index_of_window(spikes, sw_start, sw_start + SUB_WINDOW_SECONDS)
        if b is not None:
            out.append(b)
    return np.array(out)


def plot_region_population(region, region_results, local_root, animal):
    """Population summary scatter + group-counts bar chart, scoped to one
    region's units."""
    colors = {'increased': 'crimson', 'decreased': 'steelblue', 'no change': 'lightgray'}
    counts_by_dir = {'increased': 0, 'decreased': 0, 'no change': 0}

    fig, ax = plt.subplots(figsize=(6, 6))
    for r in region_results:
        ax.scatter(r['bi_b1'], r['bi_b7'], color=colors[r['direction']], s=18,
                   edgecolor='black', linewidth=0.3, alpha=0.85,
                   zorder=3 if r['direction'] != 'no change' else 2)
        counts_by_dir[r['direction']] += 1
    ax.plot([0, 1], [0, 1], color='black', linewidth=1, linestyle='--', zorder=1)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xlabel("Block 1 burst index (30min window)")
    ax.set_ylabel("Block 7 burst index (30min window)")
    ax.set_title(f"{animal} ({region}): every unit's burst index, Block 1 vs Block 7\n"
                 f"(Mann-Whitney p<0.05 on {SUB_WINDOW_SECONDS}s sub-window burst indices; n={len(region_results)} units)",
                 fontsize=10)
    handles = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markeredgecolor='black',
                          markersize=7, label=f"{d} (n={counts_by_dir[d]})") for d, c in colors.items()]
    ax.legend(handles=handles, fontsize=9, loc='upper left')
    plt.tight_layout()
    summary_path = f"{local_root}/{region}/{animal}_{region}_burstiness_block1_vs_block7_summary.png"
    plt.savefig(summary_path, dpi=130)
    plt.close(fig)
    print(f"Wrote {summary_path}")
    print(f"  {region} counts: {counts_by_dir}")

    fig, ax = plt.subplots(figsize=(5, 5))
    order = ['decreased', 'no change', 'increased']
    bar_colors = [colors[d] for d in order]
    bar_vals = [counts_by_dir[d] for d in order]
    bars = ax.bar(order, bar_vals, color=bar_colors, edgecolor='black', linewidth=0.5)
    for b, v in zip(bars, bar_vals):
        ax.text(b.get_x() + b.get_width() / 2, v + max(bar_vals) * 0.01, str(v),
                ha='center', va='bottom', fontsize=10)
    ax.set_ylabel("number of units")
    ax.set_title(f"{animal} ({region}): burst index change, Block 1 vs Block 7\n"
                 f"(Mann-Whitney p<0.05 on {SUB_WINDOW_SECONDS}s sub-window burst indices;\n"
                 f"n={len(region_results)} units)", fontsize=10)
    plt.tight_layout()
    group_counts_path = f"{local_root}/{region}/{animal}_{region}_burstiness_block1_vs_block7_group_counts.png"
    plt.savefig(group_counts_path, dpi=130)
    plt.close(fig)
    print(f"Wrote {group_counts_path}")


def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal]

    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_spike_sorted_data(cfg)

    region_by_cluster = assign_regions(good_clusters, cfg)
    if not region_by_cluster:
        raise SystemExit(f"No GC/S1 boundary data for {animal} yet (see "
                          f"feedback_gc_s1_separation memory) -- add gc_bounds_um "
                          f"to its ANIMALS config before running this.")
    excluded = [cid for cid in good_clusters if cid not in region_by_cluster]
    good_clusters = [cid for cid in good_clusters if cid in region_by_cluster]
    if excluded:
        print(f"Excluded {len(excluded)} units ventral to GC (no region assigned)")

    training_blocks = derive_training_blocks(all_events, cfg['licl_time_s'])
    block_labels = label_blocks(training_blocks)
    t0_b1 = block_labels[0][1][0]
    t0_b7 = block_labels[6][1][0]
    win_b1 = (t0_b1 - PRE_BLOCK_SECONDS, t0_b1)
    win_b7 = (t0_b7 - PRE_BLOCK_SECONDS, t0_b7)

    neuron_spikes_by_cluster = {
        cid: spike_times_samples[spike_clusters == cid] / sample_rate for cid in good_clusters
    }

    local_root = f"/tmp/{animal}_burstiness"
    os.makedirs(local_root, exist_ok=True)
    for region in ('GC', 'S1'):
        os.makedirs(f"{local_root}/{region}", exist_ok=True)

    results = []
    skipped = []
    for cid in good_clusters:
        spikes = neuron_spikes_by_cluster[cid]
        full_bi_b1 = burst_index_of_window(spikes, *win_b1)
        full_bi_b7 = burst_index_of_window(spikes, *win_b7)
        sub_b1 = sub_window_burst_indices(spikes, *win_b1)
        sub_b7 = sub_window_burst_indices(spikes, *win_b7)
        if full_bi_b1 is None or full_bi_b7 is None or len(sub_b1) < 3 or len(sub_b7) < 3:
            skipped.append(cid)
            continue
        stat, p = mannwhitneyu(sub_b1, sub_b7, alternative='two-sided')
        direction = 'no change' if p >= 0.05 else ('increased' if full_bi_b7 > full_bi_b1 else 'decreased')
        results.append(dict(cluster=cid, region=region_by_cluster[cid], bi_b1=full_bi_b1, bi_b7=full_bi_b7,
                             n_sub_b1=len(sub_b1), n_sub_b7=len(sub_b7),
                             U=stat, p=p, direction=direction, sub_b1=sub_b1, sub_b7=sub_b7))

    print(f"{len(results)} units tested, {len(skipped)} skipped (too few valid sub-windows / silent unit)")

    csv_path = f"{local_root}/{animal}_burstiness_block1_vs_block7.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cluster", "region", "bi_b1", "bi_b7", "n_sub_b1", "n_sub_b7", "U", "p", "direction"])
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in ["cluster", "region", "bi_b1", "bi_b7", "n_sub_b1", "n_sub_b7", "U", "p", "direction"]})
    print(f"Wrote {csv_path}")

    for r in results:
        fig, ax = plt.subplots(figsize=(5.5, 5))
        bp = ax.boxplot([r['sub_b1'], r['sub_b7']], positions=[0, 1], widths=0.5,
                         patch_artist=True, showmeans=True,
                         medianprops=dict(color='black'),
                         meanprops=dict(marker='D', markerfacecolor='white', markeredgecolor='black'))
        for patch, color in zip(bp['boxes'], ['black', 'crimson']):
            patch.set_facecolor(color)
            patch.set_alpha(0.5)
        ax.set_ylim(0, 1)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(['Block 1', 'Block 7'])
        ax.set_ylabel(f"burst index (fraction of ISIs < 10ms)\n(one point per {SUB_WINDOW_SECONDS}s sub-window, "
                       f"{r['n_sub_b1']}/{r['n_sub_b7']} per block)")
        sig_txt = f"p={r['p']:.3f} ({r['direction']})" if r['p'] < 0.05 else f"p={r['p']:.3f} (not significant)"
        ax.set_title(f"{animal} ({r['region']}), cluster {r['cluster']}: burst index, Block 1 vs Block 7\n"
                     f"Mann-Whitney U, {sig_txt}")
        plt.tight_layout()
        plt.savefig(f"{local_root}/{r['region']}/cluster{r['cluster']}_burstiness.png", dpi=120)
        plt.close(fig)
    print(f"Wrote {len(results)} per-unit box plots to {local_root}")

    for region in ('GC', 'S1'):
        region_results = [r for r in results if r['region'] == region]
        if not region_results:
            print(f"No {region} units for {animal} -- skipping population plots for this region")
            continue
        plot_region_population(region, region_results, local_root, animal)

    nas_dir = f"{cfg['out_dir'].rsplit('/', 1)[0]}/Analysis/single neuron/Burstiness"
    os.makedirs(nas_dir, exist_ok=True)

    # Peleg's explicit request (2026-11-03): clear out old content first, not
    # just specific stale filenames. Extended 2026-11-04 to also clear the
    # pre-GC/S1-split flat Block1-vs-Block7 layout -- every run regenerates
    # the full set deterministically from the current good_clusters.
    removed, remove_failed = 0, []
    for fname in list(os.listdir(nas_dir)):
        if fname == 'Thumbs.db':
            continue
        fpath = os.path.join(nas_dir, fname)
        try:
            shutil.rmtree(fpath) if os.path.isdir(fpath) else os.remove(fpath)
            removed += 1
        except Exception as e:
            remove_failed.append((fname, str(e)))
    print(f"Cleared {removed} old entries from {nas_dir}")
    if remove_failed:
        for fname, err in remove_failed:
            print(f"  [WARNING] could not remove {fname}: {err}")

    copied, failed = copy_tree_to_share_safely(local_root, nas_dir)
    print(f"Copied {copied} files to {nas_dir}")
    if failed:
        for relpath, err in failed:
            print(f"  FAILED: {relpath}: {err}")


if __name__ == '__main__':
    main()
