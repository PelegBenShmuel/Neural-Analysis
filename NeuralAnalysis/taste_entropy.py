"""
Taste-tuning breadth (entropy) per unit, per Training-day block -- how
narrowly ("specialist") vs. broadly ("generalist") each single neuron is
tuned across the 4 tastes, and whether that changes across the day.
Peleg asked for this (2026-10-19) after reading Raymond et al. (2026,
Articles/"Neural coding in gustatory cortex.pdf"), which uses this exact
measure (Smith & Travers, 1979) -- not yet summarized in README.md.

H = -sum(p_i * log2(p_i)), where p_i is taste i's share of a unit's total
evoked firing rate across the 4 tastes in a given block (NOT the delta/
evoked-minus-baseline metric used elsewhere in this project -- entropy
needs non-negative values that sum to a proportion, and delta can be
negative). Normalized to [0, 1] by dividing by log2(4) (the maximum
possible entropy with 4 equally-likely categories) so units are
comparable regardless of taste count. H near 1 = responds about equally
to all 4 tastes (broadly tuned); H near 0 = response is dominated by one
taste (narrowly tuned/"specialist").

Reads the already-computed per-cluster table from
training_day_response_phases.py (MS08_response_blocks.csv's mean_evoked_hz
column) rather than re-touching raw spikes -- entropy is a function of
that table alone.

Usage (from peleg_env): python taste_entropy.py [ANIMAL]   (default: MS08)
Reads Z:\\Peleg\\<animal>\\Analysis\\single neuron\\<animal>_response_blocks.csv
Writes output locally first (to /tmp/<animal>_taste_entropy), then copies
onto Z:\\Peleg\\<animal>\\Analysis\\single neuron\\.
"""
import sys
import os
import csv
import re

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, copy_to_share_safely

N_TASTES = 4
MAX_ENTROPY = np.log2(N_TASTES)


def block_sort_key(label):
    return int(re.search(r'\d+', label).group())


def entropy(rates):
    """rates: array of non-negative evoked firing rates (Hz), one per taste."""
    total = rates.sum()
    if total <= 0:
        return None  # silent in every taste this block -- undefined tuning
    p = rates / total
    nonzero = p > 0
    terms = np.zeros_like(p)
    terms[nonzero] = p[nonzero] * np.log2(p[nonzero])  # p*log2(p) -> 0 as p -> 0, by convention
    return -terms.sum()


def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal]
    response_blocks_dir = f"{cfg['out_dir'].rsplit('/', 1)[0]}/Analysis/single neuron"
    nas_dir = f"{response_blocks_dir}/Entropy"
    csv_path = f"{response_blocks_dir}/{animal}_response_blocks.csv"
    rows = list(csv.DictReader(open(csv_path)))

    clusters = sorted({int(r['cluster']) for r in rows})
    blocks = sorted({r['block'] for r in rows}, key=block_sort_key)

    local_root = f"/tmp/{animal}_taste_entropy"
    os.makedirs(local_root, exist_ok=True)

    out_rows = []
    entropy_by_cluster = {c: [] for c in clusters}
    for cluster in clusters:
        for block in blocks:
            cluster_block_rows = [r for r in rows if int(r['cluster']) == cluster and r['block'] == block]
            rates = np.array([float(r['mean_evoked_hz']) for r in cluster_block_rows])
            rates = np.clip(rates, 0, None)  # entropy needs non-negative weights
            h = entropy(rates)
            h_norm = h / MAX_ENTROPY if h is not None else None
            out_rows.append({
                "cluster": cluster, "block": block,
                "entropy_bits": h, "entropy_normalized": h_norm,
            })
            entropy_by_cluster[cluster].append(h_norm)

    csv_out = f"{local_root}/{animal}_taste_entropy.csv"
    with open(csv_out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cluster", "block", "entropy_bits", "entropy_normalized"])
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows to {csv_out}")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    for cluster in clusters:
        vals = entropy_by_cluster[cluster]
        xs = [i for i, v in enumerate(vals) if v is not None]
        ys = [v for v in vals if v is not None]
        ax.plot(xs, ys, color='#2a78d6', alpha=0.35, linewidth=1)
    ax.set_xticks(range(len(blocks)))
    ax.set_xticklabels(blocks, rotation=45, ha='right', fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("normalized taste entropy (0=specialist, 1=generalist)")
    ax.set_title(f"{animal}: per-unit taste-tuning breadth across Training-day blocks\n"
                 f"(n={len(clusters)} units, each line = one real unit)", fontsize=11)
    plt.tight_layout()
    fig_path = f"{local_root}/{animal}_taste_entropy_by_block.png"
    plt.savefig(fig_path, dpi=130)
    plt.close(fig)
    print(f"Wrote {fig_path}")

    # Population mean entropy per block (2026-10-19, Peleg's explicit request, to compare
    # directly against Raymond et al.'s "Mean Entropy ~0.5" population-level figure --
    # an addition alongside the per-unit plot above, not a replacement for it).
    mean_per_block, sem_per_block, n_per_block = [], [], []
    for i in range(len(blocks)):
        vals = [entropy_by_cluster[c][i] for c in clusters if entropy_by_cluster[c][i] is not None]
        vals = np.array(vals)
        mean_per_block.append(vals.mean())
        sem_per_block.append(vals.std(ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else 0)
        n_per_block.append(len(vals))

    fig2, ax2 = plt.subplots(figsize=(7, 4.5))
    x = range(len(blocks))
    ax2.errorbar(x, mean_per_block, yerr=sem_per_block, color='black', marker='o', capsize=4)
    ax2.set_xticks(x)
    ax2.set_xticklabels(blocks, rotation=45, ha='right', fontsize=9)
    ax2.set_ylim(0, 1.05)
    ax2.set_ylabel("mean normalized taste entropy ± SEM\n(averaged across units)")
    ax2.set_title(f"{animal}: population-mean taste entropy across Training-day blocks\n"
                  f"(n per block: {', '.join(str(n) for n in n_per_block)})", fontsize=10)
    plt.tight_layout()
    fig2_path = f"{local_root}/{animal}_taste_entropy_mean_by_block.png"
    plt.savefig(fig2_path, dpi=130)
    plt.close(fig2)
    print(f"Wrote {fig2_path}")
    print("mean entropy by block:", [round(v, 3) for v in mean_per_block])

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
