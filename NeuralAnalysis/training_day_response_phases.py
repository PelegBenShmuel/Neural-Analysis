"""
Characterizes how GC taste responses change across the Training day itself
-- the "Neural changes" question Peleg asked to focus on (2026-10-12, see
project_neural_changes_training_day_2026_10 memory), not a per-block
responsive/not-responsive table (that's cluster_responsiveness.py's job).

Kept deliberately simple, per two corrections from Peleg while building this
(2026-10-12, see feedback_peleg_workflow memory): one response-magnitude
number per (cluster x taste x block), whole post-taste window -- **no**
early/late-epoch split and **no** pooling blocks into Arieli et al. (2022)'s
named phase bins. Both of those were me importing that paper's methodology
unasked; he only asked to look at the raw block-by-block picture. Each of
the 7 Training-day blocks is kept separate (Block 1 = pre-LiCl, Blocks 2-7
post-LiCl, each labeled with its own hours-since-LiCl purely for context).

Explicitly NOT doing in this first pass (Peleg's instruction, 2026-10-12):
no sleep-state (WAKE/NREM/REM) integration yet -- that's a deliberate next
step once this response-only picture exists, not this script's job.

Reuses ANIMALS/TASTE_COLORS/copy_to_share_safely/derive_training_blocks/
load_spike_sorted_data from MS_buzcode_analysis.py (same shared-helpers
pattern as cluster_responsiveness.py) rather than redefining them. Unlike
cluster_responsiveness.py, this needs no zetapy/statsmodels/openpyxl --
runs in `peleg_env`, not `np_analysis`.

Per (cluster x taste x block): paired t-test, evoked rate (Hz) in the whole
0-2.5s post-taste window vs. the same -1..0s pre-stimulus baseline window
cluster_responsiveness.py uses, same ALPHA=0.05 convention and same window
convention as that script's own paired-t-test. This is the simplest of that
script's three tests (kept deliberately simple for a first pass on a small
per-block trial count, ~10-20 trials); the existing ZETA/ANOVA tests already
live in cluster_responsiveness.py if finer per-block significance testing is
wanted later.

Usage (from peleg_env): python training_day_response_phases.py [ANIMAL]   (default: MS08)

Writes all output locally first (to /tmp/<animal>_response_blocks), then
copies the whole tree onto Z:\\Peleg\\<animal>\\Analysis\\single neuron\\ via
copy_to_share_safely, same convention as cluster_responsiveness.py.
"""
import sys
import os
import csv
import time

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import ttest_rel

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import (ANIMALS, TASTE_COLORS, copy_to_share_safely,
                                  derive_training_blocks, load_spike_sorted_data)

# ── Analysis parameters ───────────────────────────────────────────────────────
BASELINE_WINDOW = (-1.0, 0.0)   # s relative to taste delivery
RESPONSE_WINDOW = (0.0, 2.5)    # whole post-taste window -- no epoch split
ALPHA = 0.05


def label_blocks(training_blocks):
    """One label per raw Training-day block, no Arieli-phase pooling
    (Peleg's explicit call, 2026-10-12). Plain "Block N" labels only (no
    hours-since-LiCl annotation -- Peleg's explicit call, same date: keep
    the x-axis to just the block and its number)."""
    return [(f"Block {i}", block) for i, block in enumerate(training_blocks, start=1)]


def epoch_rates(neuron_spikes, event_times, window):
    """Per-trial firing rate (Hz) in `window` (s, relative to each event)."""
    lo, hi = window
    dur = hi - lo
    rates = []
    for ev in event_times:
        rel = neuron_spikes - ev
        rates.append(np.sum((rel >= lo) & (rel < hi)) / dur)
    return np.array(rates, dtype=float)


def paired_test(baseline_rates, evoked_rates):
    if np.all(baseline_rates == evoked_rates):
        return 1.0  # no trial-to-trial difference: nothing for the test to find
    try:
        _, p = ttest_rel(evoked_rates, baseline_rates)
        return float(p)
    except Exception:
        return None


# ── Per-cluster computation ───────────────────────────────────────────────────
def compute_cluster_rows(cluster_id, neuron_spikes_sec, events_by_taste, block_labels):
    rows = []
    for taste in TASTE_COLORS:
        all_events = events_by_taste[taste]
        for label, (t0, t1) in block_labels:
            events = all_events[(all_events >= t0) & (all_events <= t1)]
            if len(events) < 3:
                continue
            baseline = epoch_rates(neuron_spikes_sec, events, BASELINE_WINDOW)
            evoked = epoch_rates(neuron_spikes_sec, events, RESPONSE_WINDOW)
            p = paired_test(baseline, evoked)
            rows.append({
                "cluster": cluster_id, "taste": taste, "block": label,
                "n_trials": len(events),
                "mean_baseline_hz": baseline.mean(), "mean_evoked_hz": evoked.mean(),
                "delta_hz": evoked.mean() - baseline.mean(),
                "p_value": p, "responsive": (p is not None and p < ALPHA),
            })
    return rows


# ── Population-level summary plots ────────────────────────────────────────────
def plot_population_summary(all_rows, animal, block_labels, out_dir):
    """One figure per metric (mean delta firing rate, proportion responsive)
    -- one line per taste across the 7 raw Training-day blocks."""
    block_order = [label for label, _ in block_labels]

    for metric, ylabel, fname in [
        ("delta_hz", "mean \u0394 firing rate (evoked - baseline, Hz)", "mean_delta_by_block.png"),
        ("responsive", "proportion of units responsive (p<0.05)", "proportion_responsive_by_block.png"),
    ]:
        fig, ax = plt.subplots(figsize=(7.5, 5))
        for taste, color in TASTE_COLORS.items():
            xs, ys = [], []
            for i, block in enumerate(block_order):
                subset = [r for r in all_rows if r["taste"] == taste and r["block"] == block]
                if not subset:
                    continue
                xs.append(i)
                ys.append(np.mean([r[metric] for r in subset]))
            ax.plot(xs, ys, color=color, marker='o', label=taste)
        ax.set_xticks(range(len(block_order)))
        ax.set_xticklabels(block_order, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel(ylabel)
        if metric == "delta_hz":
            ax.axhline(0, color='gray', linewidth=0.6)
        ax.legend(fontsize=9)
        ax.set_title(f"{animal}: Training-day taste-response trajectory", fontsize=11)
        plt.tight_layout()
        plt.savefig(f"{out_dir}/{fname}", dpi=130)
        plt.close(fig)


# ── Driver ─────────────────────────────────────────────────────────────────────
def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal]

    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_spike_sorted_data(cfg)

    training_blocks = derive_training_blocks(all_events, cfg['licl_time_s'])
    block_labels = label_blocks(training_blocks)
    print(f"{animal}: {len(good_clusters)} good clusters")
    for label, (t0, t1) in block_labels:
        print(f"  {label}: {t0:.1f}-{t1:.1f}s")

    local_root = f"/tmp/{animal}_response_blocks"
    os.makedirs(local_root, exist_ok=True)

    all_rows = []
    t_start = time.time()
    for ci, cluster_id in enumerate(good_clusters):
        neuron_spikes_sec = spike_times_samples[spike_clusters == cluster_id] / sample_rate
        all_rows.extend(compute_cluster_rows(cluster_id, neuron_spikes_sec, events_by_taste, block_labels))
        print(f"  [{ci+1}/{len(good_clusters)}] cluster {cluster_id} done "
              f"(elapsed {(time.time()-t_start):.1f}s)", flush=True)

    csv_path = f"{local_root}/{animal}_response_blocks.csv"
    fieldnames = ["cluster", "taste", "block", "n_trials",
                  "mean_baseline_hz", "mean_evoked_hz", "delta_hz", "p_value", "responsive"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Wrote {len(all_rows)} rows to {csv_path}")

    plot_population_summary(all_rows, animal, block_labels, local_root)
    print(f"All done locally in {(time.time()-t_start):.1f}s: {local_root}")

    nas_dir = f"{cfg['out_dir'].rsplit('/', 1)[0]}/Analysis/single neuron"
    print(f"Copying to {nas_dir} ...")
    os.makedirs(nas_dir, exist_ok=True)
    for fname in os.listdir(local_root):
        copy_to_share_safely(os.path.join(local_root, fname), nas_dir)
    print("Done.")


if __name__ == '__main__':
    main()
