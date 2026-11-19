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

Reuses ANIMALS/TASTE_COLORS/assign_regions/copy_tree_to_share_safely/
derive_training_blocks/load_spike_sorted_data from MS_buzcode_analysis.py
(same shared-helpers pattern as cluster_responsiveness.py) rather than
redefining them. Unlike cluster_responsiveness.py, this needs no
zetapy/statsmodels/openpyxl -- runs in `peleg_env`, not `np_analysis`.

Per (cluster x taste x block): paired t-test, evoked rate (Hz) in the whole
0-2.5s post-taste window vs. the same -1..0s pre-stimulus baseline window
cluster_responsiveness.py uses, same ALPHA=0.05 convention and same window
convention as that script's own paired-t-test. This is the simplest of that
script's three tests (kept deliberately simple for a first pass on a small
per-block trial count, ~10-20 trials); the existing ZETA/ANOVA tests already
live in cluster_responsiveness.py if finer per-block significance testing is
wanted later. The t-test itself is always run per taste separately (one
independent test per cluster x taste x block, each its own p-value); the
responsiveness heatmap pools these 4 per-taste verdicts into "responsive to
>=1 taste" per block only for that one visualization, per Peleg's explicit
request for a single combined plot (2026-11-04).

**2026-11-04 update:** GC/S1 split is now mandatory throughout (standing
rule from Anan Moran, relayed by Peleg that day -- see
feedback_gc_s1_separation memory): a unit ventral to GC (per
assign_regions/this animal's gc_bounds_um config) is excluded entirely, and
every population-level plot (the per-taste trend lines, the responsiveness
heatmap) is produced once per region, not pooled.

Usage (from peleg_env): python training_day_response_phases.py [ANIMAL]   (default: MS08)
Requires this animal to have a gc_bounds_um entry in ANIMALS (MS_buzcode_analysis.py).

Writes all output locally first (to /tmp/<animal>_response_blocks, with GC/
and S1/ subfolders for the region-scoped plots), then copies the whole tree
onto Z:\\Peleg\\<animal>\\Analysis\\single neuron\\ via
copy_tree_to_share_safely.
"""
import sys
import os
import csv
import time

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from scipy.stats import ttest_rel

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import (ANIMALS, TASTE_COLORS, assign_regions,
                                  copy_tree_to_share_safely, derive_training_blocks,
                                  load_spike_sorted_data)

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
def compute_cluster_rows(cluster_id, neuron_spikes_sec, events_by_taste, block_labels, region):
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
                "cluster": cluster_id, "region": region, "taste": taste, "block": label,
                "n_trials": len(events),
                "mean_baseline_hz": baseline.mean(), "mean_evoked_hz": evoked.mean(),
                "delta_hz": evoked.mean() - baseline.mean(),
                "p_value": p, "responsive": (p is not None and p < ALPHA),
            })
    return rows


# ── Population-level summary plots ────────────────────────────────────────────
def plot_population_summary(all_rows, animal, block_labels, out_dir, region):
    """One figure per metric (mean delta firing rate, proportion responsive)
    -- one line per taste across the 7 raw Training-day blocks, scoped to one
    region's units (2026-11-04: GC/S1 split is now mandatory, per Anan
    Moran's standing rule -- see feedback_gc_s1_separation memory)."""
    block_order = [label for label, _ in block_labels]

    for metric, ylabel, fname in [
        ("delta_hz", "mean \u0394 firing rate (evoked - baseline, Hz)", f"{animal}_{region}_mean_delta_by_block.png"),
        ("responsive", "proportion of units responsive (p<0.05)", f"{animal}_{region}_proportion_responsive_by_block.png"),
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
        ax.set_title(f"{animal} ({region}): Training-day taste-response trajectory", fontsize=11)
        plt.tight_layout()
        plt.savefig(f"{out_dir}/{fname}", dpi=130)
        plt.close(fig)


def plot_responsiveness_heatmap(all_rows, animal, block_labels, out_dir, region, clusters):
    """One row per unit, one column per block -- responsive (to >=1 taste,
    per the paired t-test above) vs not, sorted by each unit's 7-block
    pattern (as a binary number) so similar trajectories group together.
    Peleg's request, 2026-11-04, built on top of the already-computed
    per-(cluster,taste,block) responsiveness rather than a new test. Scoped
    to one region's `clusters` (GC/S1 split is now mandatory, per Anan
    Moran's standing rule, same date -- see feedback_gc_s1_separation
    memory) -- `clusters` must already be filtered to that region, not
    inferred from `all_rows`."""
    block_order = [label for label, _ in block_labels]

    resp_matrix = []
    for cid in clusters:
        row = []
        for block in block_order:
            row.append(any(r["responsive"] for r in all_rows
                            if r["cluster"] == cid and r["block"] == block))
        resp_matrix.append(row)
    resp_matrix = np.array(resp_matrix, dtype=int)

    weights = np.array([2 ** i for i in range(len(block_order))][::-1])
    order = np.argsort(-(resp_matrix @ weights))
    resp_sorted = resp_matrix[order]

    SURFACE = "#fcfcfb"
    RESPONSIVE = "#c21e3c"
    MUTED_INK = "#898781"
    SECONDARY_INK = "#52514e"
    PRIMARY_INK = "#0b0b0b"
    GRIDLINE = "#e1e0d9"
    cmap = ListedColormap([SURFACE, RESPONSIVE])

    fig, ax = plt.subplots(figsize=(5.5, 9))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.imshow(resp_sorted, aspect='auto', cmap=cmap, interpolation='none', vmin=0, vmax=1)
    for x in np.arange(0.5, len(block_order) - 0.5, 1):
        ax.axvline(x, color=GRIDLINE, linewidth=0.8, zorder=2)
    ax.set_xticks(range(len(block_order)))
    ax.set_xticklabels([f"B{i}" for i in range(1, len(block_order) + 1)],
                        fontsize=10, color=SECONDARY_INK)
    ax.tick_params(axis='x', length=0)
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_ylabel(f"{len(clusters)} units, sorted by response pattern", fontsize=10, color=MUTED_INK)
    ax.set_title(f"{animal} ({region}) — taste responsiveness across the Training day", fontsize=13,
                 color=PRIMARY_INK, pad=14, loc='left', fontweight='medium')
    legend_handles = [
        Patch(facecolor=RESPONSIVE, edgecolor='none', label='Responsive (≥1 taste)'),
        Patch(facecolor=SURFACE, edgecolor=GRIDLINE, linewidth=0.8, label='Not responsive'),
    ]
    ax.legend(handles=legend_handles, loc='upper center', bbox_to_anchor=(0.5, -0.045),
              ncol=2, frameon=False, fontsize=9.5, labelcolor=SECONDARY_INK,
              handlelength=1.4, handleheight=1.4)
    plt.tight_layout()
    plt.savefig(f"{out_dir}/{animal}_{region}_responsiveness_heatmap.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


# ── Driver ─────────────────────────────────────────────────────────────────────
def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal]

    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_spike_sorted_data(cfg)

    # GC/S1 split is mandatory (2026-11-04, standing rule from Anan Moran --
    # see feedback_gc_s1_separation memory): a unit ventral to GC is excluded
    # entirely, not pooled into either region.
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
    print(f"{animal}: {len(good_clusters)} good clusters")
    for label, (t0, t1) in block_labels:
        print(f"  {label}: {t0:.1f}-{t1:.1f}s")

    local_root = f"/tmp/{animal}_response_blocks"
    os.makedirs(local_root, exist_ok=True)
    for region in ('GC', 'S1'):
        os.makedirs(f"{local_root}/{region}", exist_ok=True)

    all_rows = []
    t_start = time.time()
    for ci, cluster_id in enumerate(good_clusters):
        neuron_spikes_sec = spike_times_samples[spike_clusters == cluster_id] / sample_rate
        all_rows.extend(compute_cluster_rows(cluster_id, neuron_spikes_sec, events_by_taste,
                                              block_labels, region_by_cluster[cluster_id]))
        print(f"  [{ci+1}/{len(good_clusters)}] cluster {cluster_id} done "
              f"(elapsed {(time.time()-t_start):.1f}s)", flush=True)

    csv_path = f"{local_root}/{animal}_response_blocks.csv"
    fieldnames = ["cluster", "region", "taste", "block", "n_trials",
                  "mean_baseline_hz", "mean_evoked_hz", "delta_hz", "p_value", "responsive"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Wrote {len(all_rows)} rows to {csv_path}")

    for region in ('GC', 'S1'):
        region_rows = [r for r in all_rows if r["region"] == region]
        region_clusters = sorted(cid for cid in good_clusters if region_by_cluster[cid] == region)
        if not region_rows:
            print(f"No {region} units for {animal} -- skipping plots for this region")
            continue
        plot_population_summary(region_rows, animal, block_labels, f"{local_root}/{region}", region)
        plot_responsiveness_heatmap(region_rows, animal, block_labels, f"{local_root}/{region}",
                                     region, region_clusters)
    print(f"All done locally in {(time.time()-t_start):.1f}s: {local_root}")

    nas_dir = f"{cfg['out_dir'].rsplit('/', 1)[0]}/Analysis/single neuron"
    print(f"Copying to {nas_dir} ...")
    os.makedirs(nas_dir, exist_ok=True)
    copied, failed = copy_tree_to_share_safely(local_root, nas_dir)
    print(f"Copied {copied} files to {nas_dir}")
    if failed:
        for relpath, err in failed:
            print(f"  FAILED: {relpath}: {err}")
    print("Done.")


if __name__ == '__main__':
    main()
