"""
Fano factor of SPONTANEOUS background firing in the 30 minutes immediately
BEFORE each Training-day block starts -- Peleg's request (2026-10-20).
Different from baseline_fano_factor.py (which uses the 1s pre-TRIAL window,
locked to each taste delivery): here there is no taste delivery at all --
it's a genuinely taste-free quiet period right before the block begins.

Since there are no discrete "trials" in a pre-block quiet period, Fano
factor is computed the way point-process dispersion is normally estimated
over a continuous span (see Chapter 14 of Articles/"Biological Signal
Analysis.pdf"): chop the PRE_BLOCK_WINDOW (30 min = 1800s before block
start) into equal, non-overlapping BIN_WIDTH-second bins (1s each, same
duration as the per-trial baseline window used elsewhere in this project,
for consistency), count spikes per bin, and compute
Fano = Var(bin counts) / Mean(bin counts) across all 1800 bins.

One Fano factor per (cluster, block) -- no taste dimension here at all
(there's no taste being delivered in this window to split by). Outputs a
plot per unit (single-neuron level) plus one population-mean (± SEM
across units) plot, per block.

Usage (from peleg_env): python pre_block_baseline_fano_factor.py [ANIMAL]   (default: MS08)
Writes output locally first (to /tmp/<animal>_pre_block_baseline_fano_factor),
then copies onto Z:\\Peleg\\<animal>\\Analysis\\single neuron\\Rest\\Baseline Fano Factor\\Pre_Block\\.
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

PRE_BLOCK_SECONDS = 30 * 60  # 30 minutes
BIN_WIDTH = 1.0              # s -- same duration as the per-trial baseline window elsewhere


def fano_factor_continuous(neuron_spikes, window_start, window_end):
    """Chop [window_start, window_end) into BIN_WIDTH-second bins, count
    spikes per bin, Fano = Var(counts)/Mean(counts). None if the unit never
    spiked in the whole window (mean=0, Fano undefined)."""
    edges = np.arange(window_start, window_end + BIN_WIDTH, BIN_WIDTH)
    counts, _ = np.histogram(neuron_spikes, bins=edges)
    counts = counts.astype(float)
    mean_count = counts.mean()
    if mean_count == 0:
        return None, mean_count, counts.var(ddof=1), len(counts)
    var_count = counts.var(ddof=1)
    return var_count / mean_count, mean_count, var_count, len(counts)


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

    local_root = f"/tmp/{animal}_pre_block_baseline_fano_factor"
    os.makedirs(local_root, exist_ok=True)

    out_rows = []
    fano_by_cluster = {cid: [] for cid in good_clusters}

    for label, (t0, t1) in block_labels:
        window_start = t0 - PRE_BLOCK_SECONDS
        window_end = t0
        for cid in good_clusters:
            fano, mean_count, var_count, n_bins = fano_factor_continuous(
                neuron_spikes_by_cluster[cid], window_start, window_end)
            out_rows.append({
                "cluster": cid, "block": label,
                "window_start_s": round(window_start, 1), "window_end_s": round(window_end, 1),
                "n_bins": n_bins, "mean_count": mean_count, "var_count": var_count,
                "fano_factor": fano,
            })
            fano_by_cluster[cid].append(fano)

    csv_path = f"{local_root}/{animal}_pre_block_baseline_fano_factor.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cluster", "block", "window_start_s", "window_end_s",
                                                "n_bins", "mean_count", "var_count", "fano_factor"])
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows to {csv_path}")

    for cid in good_clusters:
        vals = fano_by_cluster[cid]
        xs = [i for i, v in enumerate(vals) if v is not None]
        ys = [v for v in vals if v is not None]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(xs, ys, color='black', marker='o', linewidth=1.5)
        ax.axhline(1, color='gray', linewidth=0.8, linestyle='--')
        ax.set_xticks(range(len(blocks)))
        ax.set_xticklabels(blocks, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel("Fano factor (Var/Mean of 1s-binned spike count)")
        ax.set_title(f"{animal}, cluster {cid}: Fano factor of the 30min BEFORE each block starts")
        plt.tight_layout()
        plt.savefig(f"{local_root}/cluster{cid}_pre_block_fano_factor.png", dpi=120)
        plt.close(fig)
    print(f"Wrote {len(good_clusters)} per-unit plots to {local_root}")

    # Population mean (+- SEM) across units, per block -- Peleg's request, 2026-10-20
    fig, ax = plt.subplots(figsize=(7, 4.5))
    means, sems, xs = [], [], []
    for i, label in enumerate(blocks):
        vals = np.array([v for cid in good_clusters for v in [fano_by_cluster[cid][i]] if v is not None])
        if len(vals) == 0:
            continue
        xs.append(i)
        means.append(vals.mean())
        sems.append(vals.std(ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0)
    ax.errorbar(xs, means, yerr=sems, color='black', marker='o', capsize=4)
    ax.axhline(1, color='gray', linewidth=0.8, linestyle='--')
    ax.set_xticks(range(len(blocks)))
    ax.set_xticklabels(blocks, rotation=45, ha='right', fontsize=9)
    ax.set_ylabel("mean Fano factor ± SEM\n(averaged across units)")
    ax.set_title(f"{animal}: population-mean Fano factor of the 30min BEFORE each block starts\n"
                 f"(n={len(good_clusters)} units)", fontsize=11)
    plt.tight_layout()
    mean_fig_path = f"{local_root}/{animal}_pre_block_fano_factor_mean_by_block.png"
    plt.savefig(mean_fig_path, dpi=130)
    plt.close(fig)
    print(f"Wrote {mean_fig_path}")

    nas_dir = f"{cfg['out_dir'].rsplit('/', 1)[0]}/Analysis/single neuron/Rest/Baseline Fano Factor/Pre_Block"
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
