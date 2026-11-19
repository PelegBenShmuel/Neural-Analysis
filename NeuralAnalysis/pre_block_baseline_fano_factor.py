"""
Fano factor of SPONTANEOUS background firing in the 30 minutes immediately
BEFORE a Training-day block starts -- compared Block 1 vs Block 7, per unit,
to test whether a unit's resting-activity variability actually changed
across the Training day. Different from baseline_fano_factor.py (which uses
the 1s pre-TRIAL window, locked to each taste delivery): here there is no
taste delivery at all, a genuinely taste-free quiet period.

Supersedes the original per-block-trend version of this script (2026-10-20,
all 7 blocks plotted with a population-mean overlay) -- Peleg's explicit
request (2026-11-03) to replace that view in Z:\\Peleg with this
Block1-vs-Block7 comparison instead, same principle as rest_firing_rate.py's
equivalent change (see project_neural_changes_training_day_2026_10 memory
for the full discussion).

Fano factor is a RATIO (Var/Mean of 1s-binned spike counts) computed ACROSS
many bins at once -- unlike firing rate, a single 1-second bin can't yield
its own Fano value, so there's no free 600-sample distribution to test. To
get a distribution of FF values to run Mann-Whitney on, each 30min (1800s)
window is split into 10 non-overlapping 180-second (3min) sub-windows, and
FF is computed separately within each one -- 10 independent FF samples per
block per unit. Mann-Whitney U test between Block 1's 10 values and Block
7's 10 values. Trade-off vs rest_firing_rate.py's n=600 test: much less
statistical power here (n=10/side) -- real differences may go undetected,
rather than rest_firing_rate.py's opposite concern (trivial differences
looking "significant"). A shorter sub-window would raise power but make
each individual FF estimate noisier; 180s was chosen as a middle ground.

The population summary plot's axes use each unit's full-window (1800s) FF
per block (the standard single FF number for that block) -- the sub-window
FFs are only used to build the significance test, not to redefine "the" FF
value for a block.

**2026-11-04 update:** every population-level output is now split into GC
and S1 -- the standing rule from Anan Moran (relayed by Peleg that day, see
feedback_gc_s1_separation memory): never pool GC and S1 units into one
population. A unit ventral to GC (per assign_regions/this animal's
gc_bounds_um config) is excluded entirely, not folded into either region.

Usage (from peleg_env): python pre_block_baseline_fano_factor.py [ANIMAL]   (default: MS08)
Requires this animal to have a gc_bounds_um entry in ANIMALS (MS_buzcode_analysis.py).
Writes output locally first (to /tmp/<animal>_pre_block_baseline_fano_factor),
then copies onto Z:\\Peleg\\<animal>\\Analysis\\single neuron\\Rest\\Baseline
Fano Factor\\Pre_Block\\GC\\ and \\...\\Pre_Block\\S1\\, clearing out whatever
was there first.
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

PRE_BLOCK_SECONDS = 30 * 60   # 30 minutes
BIN_WIDTH = 1.0               # s -- same duration as the per-trial baseline window elsewhere
SUB_WINDOW_SECONDS = 180      # 3 minutes -> 10 sub-windows per 1800s block
N_SUB_WINDOWS = PRE_BLOCK_SECONDS // SUB_WINDOW_SECONDS


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


def sub_window_fanos(spikes, window_start, window_end):
    out = []
    for i in range(N_SUB_WINDOWS):
        sw_start = window_start + i * SUB_WINDOW_SECONDS
        f = fano_of_window(spikes, sw_start, sw_start + SUB_WINDOW_SECONDS)
        if f is not None:
            out.append(f)
    return np.array(out)


def plot_region_population(region, region_results, local_root, animal):
    """Population summary scatter + group-counts bar chart, scoped to one
    region's units."""
    colors = {'increased': 'crimson', 'decreased': 'steelblue', 'no change': 'lightgray'}
    counts_by_dir = {'increased': 0, 'decreased': 0, 'no change': 0}

    fig, ax = plt.subplots(figsize=(6, 6))
    for r in region_results:
        ax.scatter(r['ff_b1'], r['ff_b7'], color=colors[r['direction']], s=18,
                   edgecolor='black', linewidth=0.3, alpha=0.85,
                   zorder=3 if r['direction'] != 'no change' else 2)
        counts_by_dir[r['direction']] += 1
    lims = [0, max(max(r['ff_b1'] for r in region_results), max(r['ff_b7'] for r in region_results)) * 1.05]
    ax.plot(lims, lims, color='black', linewidth=1, linestyle='--', zorder=1)
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel("Block 1 Fano factor (30min window)")
    ax.set_ylabel("Block 7 Fano factor (30min window)")
    ax.set_title(f"{animal} ({region}): every unit's Fano factor, Block 1 vs Block 7\n"
                 f"(Mann-Whitney p<0.05 on {SUB_WINDOW_SECONDS}s sub-window FFs; n={len(region_results)} units)")
    handles = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markeredgecolor='black',
                          markersize=7, label=f"{d} (n={counts_by_dir[d]})") for d, c in colors.items()]
    ax.legend(handles=handles, fontsize=9, loc='upper left')
    plt.tight_layout()
    summary_path = f"{local_root}/{region}/{animal}_{region}_pre_block_fano_factor_block1_vs_block7_summary.png"
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
    ax.set_title(f"{animal} ({region}): Fano factor change, Block 1 vs Block 7\n"
                 f"(Mann-Whitney p<0.05 on {SUB_WINDOW_SECONDS}s sub-window FFs;\n"
                 f"n={len(region_results)} units)", fontsize=10)
    plt.tight_layout()
    group_counts_path = f"{local_root}/{region}/{animal}_{region}_pre_block_fano_factor_block1_vs_block7_group_counts.png"
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

    local_root = f"/tmp/{animal}_pre_block_baseline_fano_factor"
    os.makedirs(local_root, exist_ok=True)
    for region in ('GC', 'S1'):
        os.makedirs(f"{local_root}/{region}", exist_ok=True)

    results = []
    skipped = []
    for cid in good_clusters:
        spikes = neuron_spikes_by_cluster[cid]
        full_ff_b1 = fano_of_window(spikes, *win_b1)
        full_ff_b7 = fano_of_window(spikes, *win_b7)
        sub_b1 = sub_window_fanos(spikes, *win_b1)
        sub_b7 = sub_window_fanos(spikes, *win_b7)
        if full_ff_b1 is None or full_ff_b7 is None or len(sub_b1) < 3 or len(sub_b7) < 3:
            skipped.append(cid)
            continue
        stat, p = mannwhitneyu(sub_b1, sub_b7, alternative='two-sided')
        direction = 'no change' if p >= 0.05 else ('increased' if full_ff_b7 > full_ff_b1 else 'decreased')
        results.append(dict(cluster=cid, region=region_by_cluster[cid], ff_b1=full_ff_b1, ff_b7=full_ff_b7,
                             n_sub_b1=len(sub_b1), n_sub_b7=len(sub_b7),
                             U=stat, p=p, direction=direction, sub_b1=sub_b1, sub_b7=sub_b7))

    print(f"{len(results)} units tested, {len(skipped)} skipped (too few valid sub-windows / silent unit)")

    csv_path = f"{local_root}/{animal}_pre_block_fano_factor_block1_vs_block7.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cluster", "region", "ff_b1", "ff_b7", "n_sub_b1", "n_sub_b7", "U", "p", "direction"])
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in ["cluster", "region", "ff_b1", "ff_b7", "n_sub_b1", "n_sub_b7", "U", "p", "direction"]})
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
        ax.axhline(1, color='gray', linewidth=0.8, linestyle='--')
        ax.set_xticks([0, 1])
        ax.set_xticklabels(['Block 1', 'Block 7'])
        ax.set_ylabel(f"Fano factor\n(one point per {SUB_WINDOW_SECONDS}s sub-window, "
                       f"{r['n_sub_b1']}/{r['n_sub_b7']} per block)")
        sig_txt = f"p={r['p']:.3f} ({r['direction']})" if r['p'] < 0.05 else f"p={r['p']:.3f} (not significant)"
        ax.set_title(f"{animal} ({r['region']}), cluster {r['cluster']}: Fano factor, Block 1 vs Block 7\n"
                     f"Mann-Whitney U, {sig_txt}")
        plt.tight_layout()
        plt.savefig(f"{local_root}/{r['region']}/cluster{r['cluster']}_pre_block_fano_factor.png", dpi=120)
        plt.close(fig)
    print(f"Wrote {len(results)} per-unit box plots to {local_root}")

    for region in ('GC', 'S1'):
        region_results = [r for r in results if r['region'] == region]
        if not region_results:
            print(f"No {region} units for {animal} -- skipping population plots for this region")
            continue
        plot_region_population(region, region_results, local_root, animal)

    nas_dir = f"{cfg['out_dir'].rsplit('/', 1)[0]}/Analysis/single neuron/Rest/Baseline Fano Factor/Pre_Block"
    os.makedirs(nas_dir, exist_ok=True)

    # Clear everything already there (2026-11-04: this replaces both the old
    # per-block-trend outputs AND the pre-GC/S1-split flat Block1-vs-Block7
    # layout -- every run regenerates the full set deterministically from the
    # current good_clusters, so nothing should be left behind from a layout
    # this run doesn't reproduce).
    for entry in list(os.listdir(nas_dir)):
        if entry == 'Thumbs.db':
            continue
        entry_path = os.path.join(nas_dir, entry)
        try:
            shutil.rmtree(entry_path) if os.path.isdir(entry_path) else os.remove(entry_path)
        except Exception as e:
            print(f"  [WARNING] could not remove {entry}: {e}")
    print(f"Cleared {nas_dir}")

    copied, failed = copy_tree_to_share_safely(local_root, nas_dir)
    print(f"Copied {copied} files to {nas_dir}")
    if failed:
        for relpath, err in failed:
            print(f"  FAILED: {relpath}: {err}")


if __name__ == '__main__':
    main()
