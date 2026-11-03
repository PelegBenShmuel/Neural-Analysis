"""
REST firing rate (spikes/second) during the 10 minutes of spontaneous
activity immediately BEFORE a Training-day block starts -- compared
Block 1 vs Block 7, per unit, to test whether a unit's rest firing rate
actually changed across the Training day.

Supersedes the original per-block-trend version of this script (2026-10-20,
all 7 blocks plotted with a population-mean overlay) -- Peleg's explicit
request (2026-11-03) to replace that view in Z:\\Peleg with this
Block1-vs-Block7 comparison instead, after working through which
statistical test is appropriate (see project_neural_changes_training_day_2026_10
memory for the full discussion, including why Mann-Whitney over a t-test).

Per unit: each 1-second bin's spike count IS already a rate sample (bin
width = 1s), so the 600-second REST window before Block 1 gives 600
independent rate samples, and likewise for Block 7 -- a Mann-Whitney U
test between the two 600-sample sets asks whether the unit's rest rate
distribution genuinely shifted between the start and end of the Training
day (non-parametric: no normality assumption, robust to the single-second
spike-count outliers/bursts seen throughout this project).

Caveat: with n=600 per side, Mann-Whitney has very high power -- a
"significant" result here means "a consistent difference, not noise," not
necessarily "a large change."

Outputs per unit: one box plot (x = Block 1 / Block 7, y = spikes/second,
one point per 1-second bin). Plus one population summary scatter (x = unit's
Block 1 mean rate, y = unit's Block 7 mean rate, colored by the
Mann-Whitney verdict for that unit) across all units.

Usage (from peleg_env): python rest_firing_rate.py [ANIMAL]   (default: MS08)
Writes output locally first (to /tmp/<animal>_rest_firing_rate), then
copies onto Z:\\Peleg\\<animal>\\Analysis\\single neuron\\Rest\\Rest_FR\\,
removing the superseded mean-by-block plot/CSV there.
"""
import sys
import os
import csv

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, copy_to_share_safely, derive_training_blocks, load_spike_sorted_data
from training_day_response_phases import label_blocks

REST_WINDOW_SECONDS = 10 * 60  # 10 minutes
BIN_WIDTH = 1.0                # seconds -- one bin's count = one rate sample


def bin_counts(spikes, window_start, window_end):
    edges = np.arange(window_start, window_end + BIN_WIDTH, BIN_WIDTH)
    counts, _ = np.histogram(spikes, bins=edges)
    return counts


def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal]

    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_spike_sorted_data(cfg)
    training_blocks = derive_training_blocks(all_events, cfg['licl_time_s'])
    block_labels = label_blocks(training_blocks)
    t0_b1 = block_labels[0][1][0]
    t0_b7 = block_labels[6][1][0]
    win_b1 = (t0_b1 - REST_WINDOW_SECONDS, t0_b1)
    win_b7 = (t0_b7 - REST_WINDOW_SECONDS, t0_b7)

    neuron_spikes_by_cluster = {
        cid: spike_times_samples[spike_clusters == cid] / sample_rate for cid in good_clusters
    }

    local_root = f"/tmp/{animal}_rest_firing_rate"
    os.makedirs(local_root, exist_ok=True)

    results = []
    for cid in good_clusters:
        spikes = neuron_spikes_by_cluster[cid]
        b1_counts = bin_counts(spikes, *win_b1)
        b7_counts = bin_counts(spikes, *win_b7)
        stat, p = mannwhitneyu(b1_counts, b7_counts, alternative='two-sided')
        rate_b1, rate_b7 = b1_counts.mean(), b7_counts.mean()
        direction = 'no change' if p >= 0.05 else ('increased' if rate_b7 > rate_b1 else 'decreased')
        results.append(dict(cluster=cid, rate_b1=rate_b1, rate_b7=rate_b7, U=stat, p=p,
                             direction=direction, b1_counts=b1_counts, b7_counts=b7_counts))

    csv_path = f"{local_root}/{animal}_rest_firing_rate_block1_vs_block7.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cluster", "rate_b1", "rate_b7", "U", "p", "direction"])
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in ["cluster", "rate_b1", "rate_b7", "U", "p", "direction"]})
    print(f"Wrote {len(results)} rows to {csv_path}")

    for r in results:
        fig, ax = plt.subplots(figsize=(5.5, 5))
        bp = ax.boxplot([r['b1_counts'], r['b7_counts']], positions=[0, 1], widths=0.5,
                         patch_artist=True, showmeans=True,
                         medianprops=dict(color='black'),
                         meanprops=dict(marker='D', markerfacecolor='white', markeredgecolor='black'))
        for patch, color in zip(bp['boxes'], ['black', 'crimson']):
            patch.set_facecolor(color)
            patch.set_alpha(0.5)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(['Block 1', 'Block 7'])
        ax.set_ylabel("rest firing rate (spikes/second)\n(one point per 1-second bin, 600 per block)")
        sig_txt = f"p={r['p']:.2e} ({r['direction']})" if r['p'] < 0.05 else f"p={r['p']:.2e} (not significant)"
        ax.set_title(f"{animal}, cluster {r['cluster']}: rest firing rate, Block 1 vs Block 7\n"
                     f"Mann-Whitney U, {sig_txt}")
        plt.tight_layout()
        plt.savefig(f"{local_root}/cluster{r['cluster']}_rest_firing_rate.png", dpi=120)
        plt.close(fig)
    print(f"Wrote {len(results)} per-unit box plots to {local_root}")

    fig, ax = plt.subplots(figsize=(6, 6))
    colors = {'increased': 'crimson', 'decreased': 'steelblue', 'no change': 'lightgray'}
    counts_by_dir = {'increased': 0, 'decreased': 0, 'no change': 0}
    for r in results:
        ax.scatter(r['rate_b1'], r['rate_b7'], color=colors[r['direction']], s=18,
                   edgecolor='black', linewidth=0.3, alpha=0.85,
                   zorder=3 if r['direction'] != 'no change' else 2)
        counts_by_dir[r['direction']] += 1
    lims = [0, max(max(r['rate_b1'] for r in results), max(r['rate_b7'] for r in results)) * 1.05]
    ax.plot(lims, lims, color='black', linewidth=1, linestyle='--', zorder=1)
    ax.set_xlim(lims); ax.set_ylim(lims)
    ax.set_xlabel("Block 1 rest firing rate (spikes/s)")
    ax.set_ylabel("Block 7 rest firing rate (spikes/s)")
    ax.set_title(f"{animal}: every unit's rest firing rate, Block 1 vs Block 7\n"
                 f"(Mann-Whitney p<0.05 on 1s-binned counts; n={len(results)} units)")
    handles = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markeredgecolor='black',
                          markersize=7, label=f"{d} (n={counts_by_dir[d]})") for d, c in colors.items()]
    ax.legend(handles=handles, fontsize=9, loc='upper left')
    plt.tight_layout()
    summary_path = f"{local_root}/{animal}_rest_firing_rate_block1_vs_block7_summary.png"
    plt.savefig(summary_path, dpi=130)
    plt.close(fig)
    print(f"Wrote {summary_path}")
    print(f"Counts: {counts_by_dir}")

    # Group-counts bar chart -- how many units fall in each of the 3
    # Mann-Whitney verdict groups, same format as
    # pre_block_baseline_fano_factor.py's equivalent (2026-11-03).
    fig, ax = plt.subplots(figsize=(5, 5))
    order = ['decreased', 'no change', 'increased']
    bar_colors = [colors[d] for d in order]
    bar_vals = [counts_by_dir[d] for d in order]
    bars = ax.bar(order, bar_vals, color=bar_colors, edgecolor='black', linewidth=0.5)
    for b, v in zip(bars, bar_vals):
        ax.text(b.get_x() + b.get_width() / 2, v + max(bar_vals) * 0.01, str(v),
                ha='center', va='bottom', fontsize=10)
    ax.set_ylabel("number of units")
    ax.set_title(f"{animal}: rest firing rate change, Block 1 vs Block 7\n"
                 f"(Mann-Whitney p<0.05 on 1s-binned counts;\n"
                 f"n={len(results)} units)", fontsize=10)
    plt.tight_layout()
    group_counts_path = f"{local_root}/{animal}_rest_firing_rate_block1_vs_block7_group_counts.png"
    plt.savefig(group_counts_path, dpi=130)
    plt.close(fig)
    print(f"Wrote {group_counts_path}")

    nas_dir = f"{cfg['out_dir'].rsplit('/', 1)[0]}/Analysis/single neuron/Rest/Rest_FR"
    os.makedirs(nas_dir, exist_ok=True)

    # remove the superseded per-block-trend outputs this replaces
    for stale in [f"{animal}_rest_firing_rate.csv", f"{animal}_rest_firing_rate_mean_by_block.png"]:
        stale_path = os.path.join(nas_dir, stale)
        try:
            if os.path.exists(stale_path):
                os.remove(stale_path)
                print(f"  Removed superseded {stale}")
        except Exception as e:
            print(f"  [WARNING] could not remove {stale}: {e}")

    failed = []
    for fname in os.listdir(local_root):
        try:
            copy_to_share_safely(os.path.join(local_root, fname), nas_dir)
        except Exception as e:
            failed.append((fname, str(e)))
    print(f"Copied {len(os.listdir(local_root)) - len(failed)}/{len(os.listdir(local_root))} to {nas_dir}")
    if failed:
        for fname, err in failed:
            print(f"  FAILED: {fname}: {err}")


if __name__ == '__main__':
    main()
