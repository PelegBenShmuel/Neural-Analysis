"""
One PSTH image per (unit x block), showing all 4 tastes overlaid on the
same axes -- Peleg's request (2026-10-19): "בלוק 1 קלאסטר x PSTH של כל 4
הטעמים... לכל הבלוקים וכל הנוירונים" (Block 1, cluster X, PSTH of all 4
tastes... for all blocks and all neurons). 7 blocks x 41 units = 287
images.

Complements (doesn't replace) the two Sucrose-only per-(unit x block)
files within_block_dynamics.py already writes into Block<N>/ -- this adds
a third file there, the all-tastes view, since those two are deliberately
scoped to Sucrose only while this one needs all 4 tastes' events per
block.

Same PSTH convention as psth_by_block.py (-1 to 2.5s around taste
delivery, 100ms bins, Gaussian smoothing sigma=2 bins).

Usage (from peleg_env): python psth_per_unit_per_block_alltastes.py [ANIMAL]   (default: MS08)
Writes output locally first (to /tmp/<animal>_psth_per_unit_per_block_alltastes/Block<N>/),
then copies each block's folder onto Z:\\Peleg\\<animal>\\Analysis\\single neuron\\PSTH\\Block<N>\\
(the same folders within_block_dynamics.py already populates).
"""
import sys
import os

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, TASTE_COLORS, copy_to_share_safely, derive_training_blocks, load_spike_sorted_data
from training_day_response_phases import label_blocks

WINDOW = (-1.0, 2.5)
PSTH_BIN = 0.1
SMOOTH_SIGMA_BINS = 2


def smoothed_psth_curve(neuron_spikes, event_times, edges):
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
    cfg = ANIMALS[animal]

    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_spike_sorted_data(cfg)
    training_blocks = derive_training_blocks(all_events, cfg['licl_time_s'])
    block_labels = label_blocks(training_blocks)

    edges = np.arange(WINDOW[0], WINDOW[1] + PSTH_BIN, PSTH_BIN)
    bin_centers = (edges[:-1] + edges[1:]) / 2
    neuron_spikes_by_cluster = {
        cid: spike_times_samples[spike_clusters == cid] / sample_rate for cid in good_clusters
    }

    local_root = f"/tmp/{animal}_psth_per_unit_per_block_alltastes"
    nas_base = f"{cfg['out_dir'].rsplit('/', 1)[0]}/Analysis/single neuron/PSTH"

    for label, (t0, t1) in block_labels:
        block_num = label.split()[1]
        events_by_taste_this_block = {}
        for taste in TASTE_COLORS:
            all_ev = events_by_taste[taste]
            events_by_taste_this_block[taste] = all_ev[(all_ev >= t0) & (all_ev <= t1)]

        local_dir = f"{local_root}/Block{block_num}"
        os.makedirs(local_dir, exist_ok=True)

        for cid in good_clusters:
            fig, ax = plt.subplots(figsize=(7, 4.5))
            for taste, color in TASTE_COLORS.items():
                events = events_by_taste_this_block[taste]
                if len(events) < 3:
                    continue
                curve = smoothed_psth_curve(neuron_spikes_by_cluster[cid], events, edges)
                ax.plot(bin_centers, curve, color=color, linewidth=1.6, label=taste)
            ax.axvline(0, color='black', linestyle='--', linewidth=0.8)
            ax.set_xlabel("time relative to taste delivery (s)")
            ax.set_ylabel("spikes/second")
            ax.set_title(f"{animal}, cluster {cid}, {label}: PSTH, all 4 tastes")
            ax.legend(fontsize=9, loc='upper right')
            plt.tight_layout()
            fname = f"cluster{cid}_PSTH_block{block_num}_alltastes.png"
            plt.savefig(f"{local_dir}/{fname}", dpi=110)
            plt.close(fig)

        print(f"{label}: {len(good_clusters)} units done locally", flush=True)

        nas_dir = f"{nas_base}/Block{block_num}"
        os.makedirs(nas_dir, exist_ok=True)
        failed = []
        for fname in os.listdir(local_dir):
            try:
                copy_to_share_safely(os.path.join(local_dir, fname), nas_dir)
            except Exception as e:
                failed.append((fname, str(e)))
        print(f"  copied {len(os.listdir(local_dir)) - len(failed)}/{len(os.listdir(local_dir))} to {nas_dir}")
        if failed:
            print("  FAILED (likely stuck gvfs-SMB file -- needs clearing from a Windows client):")
            for fname, err in failed:
                print(f"    {fname}: {err}")

    print("All done.")


if __name__ == '__main__':
    main()
