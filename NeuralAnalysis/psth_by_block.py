"""
Per-neuron PSTH for one taste (default Sucrose), overlaid across the
Training day's 7 blocks -- one figure per single unit (2026-10-12, Peleg's
explicit call to stay at single-neuron level, not population-averaged: "אני
רוצה להישאר ב-single neuron level analysis ולא לעבור לאוכלוסייה"). An
earlier version of this script averaged across all good clusters into one
population PSTH per block -- see git history if that view is wanted again;
this version keeps every cluster's own curve separate, one plot per cluster.

Same PSTH convention cluster_responsiveness.py uses (-1 to 2.5s around taste
delivery, 100ms bins): for one cluster, one block, average the PSTH across
that block's trials -- then overlay all 7 blocks' curves on one axes per
cluster, so a single neuron's whole response time-course across the day is
visible at a glance.

Curves are Gaussian-smoothed (2026-10-12, Peleg's request -- the raw 100ms
bins were too jagged with only ~10-20 trials per block/cluster) with
scipy.ndimage.gaussian_filter1d, sigma=SMOOTH_SIGMA_BINS bins -- smooths the
displayed curve shape only, the underlying 100ms bin width/trial counts are
unchanged.

Reuses ANIMALS/copy_to_share_safely/derive_training_blocks/
load_spike_sorted_data from MS_buzcode_analysis.py and label_blocks from
training_day_response_phases.py.

Usage (from peleg_env): python psth_by_block.py [ANIMAL] [TASTE]   (default: MS08 Sucrose)
Writes output locally first (to /tmp/<animal>_psth_by_block), then copies
the whole tree onto Z:\\Peleg\\<animal>\\Analysis\\single neuron\\<taste>_PSTH_per_unit\\
(one file per cluster).
"""
import sys
import os

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, copy_to_share_safely, derive_training_blocks, load_spike_sorted_data
from training_day_response_phases import label_blocks

WINDOW = (-1.0, 2.5)   # s relative to taste delivery -- same convention as cluster_responsiveness.py
PSTH_BIN = 0.1
SMOOTH_SIGMA_BINS = 2  # Gaussian smoothing width, in bins (2 bins = 200ms at PSTH_BIN=0.1)

# 7 fixed, maximally-distinguishable colors (2026-10-12, replacing viridis -- Peleg found
# viridis's adjacent samples too similar to tell apart at a glance). First 7 of the
# dataviz skill's 8-slot categorical order (blue/orange/aqua/yellow/magenta/green/violet);
# paired with a distinct marker shape per block as secondary encoding, since 7 overlapping
# line series exceeds that palette's documented all-pairs-safe cap of 3 -- color alone
# isn't guaranteed distinguishable for every pair here, the marker shape is the backup cue.
BLOCK_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6']
BLOCK_MARKERS = ['o', 's', '^', 'D', 'v', 'P', 'X']


def cluster_psth(neuron_spikes, event_times, edges):
    """Trial-averaged, Gaussian-smoothed PSTH curve (Hz) for one cluster, one block."""
    counts_per_trial = []
    for ev in event_times:
        rel = neuron_spikes - ev
        rel = rel[(rel >= WINDOW[0]) & (rel < WINDOW[1])]
        counts, _ = np.histogram(rel, bins=edges)
        counts_per_trial.append(counts)
    rate = np.mean(counts_per_trial, axis=0) / PSTH_BIN
    return gaussian_filter1d(rate, sigma=SMOOTH_SIGMA_BINS, mode='nearest')


def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    taste = sys.argv[2] if len(sys.argv) > 2 else 'Sucrose'
    cfg = ANIMALS[animal]

    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_spike_sorted_data(cfg)
    training_blocks = derive_training_blocks(all_events, cfg['licl_time_s'])
    block_labels = label_blocks(training_blocks)

    edges = np.arange(WINDOW[0], WINDOW[1] + PSTH_BIN, PSTH_BIN)
    bin_centers = (edges[:-1] + edges[1:]) / 2
    all_events_taste = events_by_taste[taste]
    events_by_block = {}
    for label, (t0, t1) in block_labels:
        events = all_events_taste[(all_events_taste >= t0) & (all_events_taste <= t1)]
        if len(events) >= 3:
            events_by_block[label] = events

    local_root = f"/tmp/{animal}_psth_by_block/{taste}"
    os.makedirs(local_root, exist_ok=True)

    for ci, cluster_id in enumerate(good_clusters):
        neuron_spikes_sec = spike_times_samples[spike_clusters == cluster_id] / sample_rate

        fig, ax = plt.subplots(figsize=(8, 5))
        for color, marker, (label, events) in zip(BLOCK_COLORS, BLOCK_MARKERS, events_by_block.items()):
            curve = cluster_psth(neuron_spikes_sec, events, edges)
            ax.plot(bin_centers, curve, color=color, label=label, linewidth=1.5,
                    marker=marker, markevery=5, markersize=5)
        ax.axvline(0, color='black', linestyle='--', linewidth=0.8)
        ax.set_xlabel("time relative to taste delivery (s)")
        ax.set_ylabel("spikes/second")
        ax.set_title(f"{animal}, cluster {cluster_id}: {taste} PSTH across Training-day blocks")
        ax.legend(fontsize=8, loc='upper right')
        plt.tight_layout()
        fname = f"cluster{cluster_id}_{taste}_PSTH_by_block.png"
        plt.savefig(f"{local_root}/{fname}", dpi=110)
        plt.close(fig)
        print(f"  [{ci+1}/{len(good_clusters)}] cluster {cluster_id} done", flush=True)

    nas_dir = f"{cfg['out_dir'].rsplit('/', 1)[0]}/Analysis/single neuron/Taste_Based_PSTH/{taste}_PSTH_per_unit"
    os.makedirs(nas_dir, exist_ok=True)
    failed = []
    for fname in os.listdir(local_root):
        try:
            copy_to_share_safely(os.path.join(local_root, fname), nas_dir)
        except Exception as e:
            # Don't let one stuck gvfs-SMB file (see project_buzcode_all_rats_2026_09
            # memory) block every file after it in this loop -- keep going and report
            # failures at the end instead.
            failed.append((fname, str(e)))
    print(f"Copied {len(good_clusters) - len(failed)}/{len(good_clusters)} plots to {nas_dir}")
    if failed:
        print("FAILED to copy (likely stuck gvfs-SMB file -- needs clearing from a Windows client):")
        for fname, err in failed:
            print(f"  {fname}: {err}")


if __name__ == '__main__':
    main()
