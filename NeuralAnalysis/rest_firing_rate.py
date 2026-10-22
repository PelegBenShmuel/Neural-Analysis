"""
Mean firing rate (spikes/second) during REST -- the 10 minutes of
spontaneous activity immediately BEFORE each Training-day block starts --
per unit, across blocks 1-7. Peleg's request (2026-10-20), under Anan
Moran's "Rest: Baseline Firing Rate" category (see
project_neural_changes_training_day_2026_10 memory): complements
pre_block_baseline_fano_factor.py (which measures how VARIABLE the resting
rate is) with the rate itself (how FAST the neuron fires at rest).

Window is 10 minutes (600s) before block start -- shorter than the 30min
window pre_block_baseline_fano_factor.py uses, per Peleg's explicit choice
here ("let's start with 10 minutes").

One firing rate per (cluster, block): total spike count in the 600s window
divided by 600 -- no taste dimension (no taste is delivered in this window).

Usage (from peleg_env): python rest_firing_rate.py [ANIMAL]   (default: MS08)
Writes output locally first (to /tmp/<animal>_rest_firing_rate), then
copies onto Z:\\Peleg\\<animal>\\Analysis\\single neuron\\Rest\\Rest_FR\\.
"""
import sys
import os
import csv

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, copy_to_share_safely, derive_training_blocks, load_spike_sorted_data
from training_day_response_phases import label_blocks

REST_WINDOW_SECONDS = 10 * 60  # 10 minutes


def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal]

    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_spike_sorted_data(cfg)
    training_blocks = derive_training_blocks(all_events, cfg['licl_time_s'])
    block_labels = label_blocks(training_blocks)
    blocks = [label for label, _ in block_labels]
    neuron_spikes_by_cluster = {
        cid: spike_times_samples[spike_clusters == cid] / sample_rate for cid in good_clusters
    }

    local_root = f"/tmp/{animal}_rest_firing_rate"
    os.makedirs(local_root, exist_ok=True)

    out_rows = []
    rate_by_cluster = {cid: [] for cid in good_clusters}

    for label, (t0, t1) in block_labels:
        window_start = t0 - REST_WINDOW_SECONDS
        window_end = t0
        for cid in good_clusters:
            spikes = neuron_spikes_by_cluster[cid]
            n_spikes = int(np.sum((spikes >= window_start) & (spikes < window_end)))
            rate = n_spikes / REST_WINDOW_SECONDS
            out_rows.append({
                "cluster": cid, "block": label,
                "window_start_s": round(window_start, 1), "window_end_s": round(window_end, 1),
                "n_spikes": n_spikes, "firing_rate_hz": rate,
            })
            rate_by_cluster[cid].append(rate)

    csv_path = f"{local_root}/{animal}_rest_firing_rate.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cluster", "block", "window_start_s", "window_end_s",
                                                "n_spikes", "firing_rate_hz"])
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows to {csv_path}")

    for cid in good_clusters:
        vals = rate_by_cluster[cid]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(range(len(blocks)), vals, color='black', marker='o', linewidth=1.5)
        ax.set_xticks(range(len(blocks)))
        ax.set_xticklabels(blocks, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel("mean firing rate at rest (spikes/second)")
        ax.set_title(f"{animal}, cluster {cid}: rest firing rate, 10min BEFORE each block starts")
        plt.tight_layout()
        plt.savefig(f"{local_root}/cluster{cid}_rest_firing_rate.png", dpi=120)
        plt.close(fig)
    print(f"Wrote {len(good_clusters)} per-unit plots to {local_root}")

    # Population mean (+- SEM) across units, per block -- Peleg's request, 2026-10-20:
    # "the rate goes up or down, across all MS08's neurons?"
    fig, ax = plt.subplots(figsize=(7, 4.5))
    means, sems = [], []
    for i in range(len(blocks)):
        vals = np.array([rate_by_cluster[cid][i] for cid in good_clusters])
        means.append(vals.mean())
        sems.append(vals.std(ddof=1) / np.sqrt(len(vals)))
    ax.errorbar(range(len(blocks)), means, yerr=sems, color='black', marker='o', capsize=4)
    ax.set_xticks(range(len(blocks)))
    ax.set_xticklabels(blocks, rotation=45, ha='right', fontsize=9)
    ax.set_ylabel("mean firing rate at rest ± SEM\n(spikes/second, averaged across units)")
    ax.set_title(f"{animal}: population-mean rest firing rate, 10min BEFORE each block\n"
                 f"(n={len(good_clusters)} units)", fontsize=11)
    plt.tight_layout()
    mean_fig_path = f"{local_root}/{animal}_rest_firing_rate_mean_by_block.png"
    plt.savefig(mean_fig_path, dpi=130)
    plt.close(fig)
    print(f"Wrote {mean_fig_path}")

    nas_dir = f"{cfg['out_dir'].rsplit('/', 1)[0]}/Analysis/single neuron/Rest/Rest_FR"
    os.makedirs(nas_dir, exist_ok=True)
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
