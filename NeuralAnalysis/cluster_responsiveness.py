"""
Per-cluster taste-responsiveness analysis for one animal's Training day:
builds a PSTH (raster + rate curve, colored by taste) for every "good"
Kilosort/Phy unit in each of the 7 Training-day blocks, and classifies each
(unit x taste x block) as responsive or not via two independent tests.

Built entirely from raw spike-sorter output -- spike_times.npy,
spike_clusters.npy, cluster_group.tsv (Phy curation label, "good" units
only), the true AP-band sample rate from *.imec0.ap.meta -- plus the raw
TPrime-corrected taste-event *_corr.txt files already used by
MS_buzcode_analysis.py. Deliberately NOT Mai's derived analysis tables
(kilosort4_23_49h_mai/analysis/): Peleg asked for an analysis he
understands/owns end to end, not one that consumes her results.

One script, parameterized by animal (ANIMALS dict, imported from
MS_buzcode_analysis.py so the per-animal paths/LiCl-time/taste-files live in
exactly one place) -- not a separate copy per animal. See
feedback_no_script_duplication memory / TODO.md's "Port the ad-hoc
PSTH/ZETA/ANOVA scratch scripts" item for why this exists: the analysis was
first built and run for MS08 as a sequence of one-off scratchpad scripts
during a Claude session (2026-09-16 to 2026-09-22); this is that work
consolidated into the repo, generalized for reuse on the next animal (MS09
next -- see TODO.md).

Two independent responsiveness tests are computed per (cluster x taste x
block), rather than trusting one method alone (see TODO.md "Built a
from-scratch PSTH..." entry for the full rationale and the 85% agreement
rate found on MS08):
  - ZETA test (zetapy.zetatest, Montijn et al. 2021) -- parameter-free, most
    sensitive to a real but temporally localized/jittery response. Requires
    the `np_analysis` conda env (has zetapy + openpyxl; peleg_env doesn't).
  - Repeated-measures ANOVA (statsmodels.stats.anova.AnovaRM) -- main effect
    of 250ms time-bin (Piette et al. 2012-style binning), the same
    statistical family already used in this project's own literature.

Known limitation: ZETA can fail to compute on a very low-firing-rate unit
(too few spikes in the analysis window) -- this is recorded explicitly here
as zeta_p=None / responsive_zeta=None ("insufficient data"), NOT as a
default p=1.0 / responsive=False (an earlier version of this analysis did
that and it's misleading -- see TODO.md). Don't read a None as "not
responsive."

Usage (from the np_analysis conda env): python cluster_responsiveness.py [ANIMAL]   (default: MS08)

Writes all output locally first (to /tmp/<animal>_cluster_analysis), then
copies the whole tree onto Z:\\Peleg\\<animal>\\Cluster_analysis\\ using the
same copy_to_share_safely() helper MS_buzcode_analysis.py uses elsewhere in
this repo, file by file (never writing a final filename's content directly
over the share -- see that function's docstring for why).
"""
import sys
import os
import re
import csv
import glob
import time
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from statsmodels.stats.anova import AnovaRM
from zetapy import zetatest
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import ANIMALS, TASTE_COLORS, copy_to_share_safely

# ── Analysis parameters ───────────────────────────────────────────────────────
WINDOW = (-1.0, 2.5)       # seconds relative to taste delivery
PSTH_BIN = 0.1             # PSTH plotting bin width (s)
ANOVA_BIN = 0.25           # repeated-measures ANOVA bin width (s), Piette et al.-style
ZETA_DUR = 2.5             # post-event window ZETA/ANOVA evaluate (s)
GAP_THRESH = 1000.0        # seconds; a gap bigger than this starts a new taste-delivery block
ALPHA = 0.05               # significance threshold for both tests
ZETA_RESAMPLES = 1000

BLOCK_COLORS = {  # for the xlsx background shading, one color per Training-day block
    1: "DCE6F1", 2: "E2EFDA", 3: "FFF2CC", 4: "FCE4D6",
    5: "E4DFEC", 6: "F8CBAD", 7: "D9D9D9",
}


# ── Data loading ───────────────────────────────────────────────────────────────
def load_animal_data(cfg):
    spike_dir = cfg['spike_sorted_dir']
    if spike_dir is None:
        raise ValueError("This animal has no spike_sorted_dir configured (no Training day recorded).")

    meta_files = glob.glob(f"{spike_dir}/*.imec0.ap.meta")
    assert len(meta_files) == 1, f"expected exactly one .imec0.ap.meta in {spike_dir}, found {meta_files}"
    meta_text = open(meta_files[0]).read()
    sample_rate = float(re.search(r"imSampRate=([\d.]+)", meta_text).group(1))

    spike_times_samples = np.load(f"{spike_dir}/spike_times.npy").flatten()
    spike_clusters = np.load(f"{spike_dir}/spike_clusters.npy").flatten()

    good_clusters = []
    with open(f"{spike_dir}/cluster_group.tsv") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["group"] == "good":
                good_clusters.append(int(row["cluster_id"]))

    events_by_taste = {t: np.loadtxt(path) for t, path in cfg['taste_files'].items()}
    all_events = np.sort(np.concatenate(list(events_by_taste.values())))

    return spike_times_samples, spike_clusters, sample_rate, good_clusters, events_by_taste, all_events


def derive_training_blocks(all_events, sorted_min, sorted_max, licl_time_s):
    """Group taste events into delivery blocks by gap-detection on the raw
    timestamps themselves (not any pre-computed block-boundary file), then
    anchor on the LiCl injection time to pick out the Training day's Block
    1-7 specifically -- NOT just "however many blocks happen to fall inside
    the sorted window". That distinction matters: MS08's standard sorted
    window (kilosort4_23_49h_mai, hours 23-49) happens to stop just short of
    Day 5's "Block 8" (per Experiment Protocol and Procedure.md), so for
    MS08 counting blocks-in-window gives 7 either way -- but MS09's sorted
    window includes Block 8 too, so a naive count finds 8 and silently
    includes a Day-5 block in what's supposed to be a Training-day-only
    analysis. Block 1 = the block ending most recently before licl_time_s;
    Blocks 2-7 are the 6 blocks immediately following it."""
    gaps = np.diff(all_events)
    starts_idx = np.concatenate([[0], np.where(gaps > GAP_THRESH)[0] + 1])
    ends_idx = np.concatenate([np.where(gaps > GAP_THRESH)[0] + 1, [len(all_events)]])
    all_blocks = [(all_events[s], all_events[e - 1]) for s, e in zip(starts_idx, ends_idx)]

    pre_licl = [i for i, (t0, t1) in enumerate(all_blocks) if t1 < licl_time_s]
    assert pre_licl, "no taste-delivery block found ending before the configured LiCl injection time"
    block1_idx = pre_licl[-1]

    training_blocks = all_blocks[block1_idx:block1_idx + 7]
    assert len(training_blocks) == 7, (
        f"only found {len(training_blocks)} blocks from Block 1 onward, expected 7 "
        f"-- check this animal's spike_sorted_dir covers the full Training day"
    )
    t0_first, t1_last = training_blocks[0][0], training_blocks[-1][1]
    assert t0_first >= sorted_min and t1_last <= sorted_max, (
        f"Training day blocks span {t0_first:.1f}-{t1_last:.1f}s but sorted spikes only cover "
        f"{sorted_min:.1f}-{sorted_max:.1f}s"
    )

    next_idx = block1_idx + 7
    if next_idx < len(all_blocks):
        extra_t0, extra_t1 = all_blocks[next_idx]
        if extra_t0 >= sorted_min and extra_t1 <= sorted_max:
            print(f"  (note: an 8th block at {extra_t0:.1f}-{extra_t1:.1f}s is also inside the sorted "
                  f"window -- almost certainly Day 5's 'Block 8'; deliberately excluded, Training day only)")

    return training_blocks


# ── The two responsiveness tests ──────────────────────────────────────────────
def run_zeta(neuron_spikes, event_times):
    """Returns (zeta_p, valid). valid=False means ZETA couldn't compute a
    real result (too few spikes in the window) -- zeta_p is None in that
    case, NOT a default p=1.0, so it isn't mistaken for "tested and not
    responsive."""
    if len(event_times) < 3:
        return None, False
    event_on_off = np.column_stack([event_times, event_times + ZETA_DUR])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        zeta_p, _, _ = zetatest(neuron_spikes, event_on_off, dblUseMaxDur=ZETA_DUR,
                                 intResampNum=ZETA_RESAMPLES, boolReturnRate=False)
        failed = any("too few spikes" in str(w.message) or "calculation failed" in str(w.message)
                     for w in caught)
    if failed:
        return None, False
    return zeta_p, True


def run_anova(neuron_spikes, event_times):
    if len(event_times) < 3:
        return None
    edges = np.arange(WINDOW[0], WINDOW[1] + ANOVA_BIN, ANOVA_BIN)
    rows = []
    for trial_id, ev in enumerate(event_times):
        rel = neuron_spikes - ev
        counts, _ = np.histogram(rel, bins=edges)
        for bin_id, rate in enumerate(counts / ANOVA_BIN):
            rows.append({"trial": trial_id, "bin": bin_id, "rate": rate})
    df = pd.DataFrame(rows)
    if df["rate"].std() == 0:
        return 1.0  # completely silent/flat: nothing for the test to find
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = AnovaRM(df, depvar="rate", subject="trial", within=["bin"]).fit()
        return float(res.anova_table["Pr > F"].iloc[0])
    except Exception:
        return None


# ── Per-cluster PSTH + responsiveness table ──────────────────────────────────
def build_cluster_outputs(cluster_id, neuron_spikes_sec, events_by_taste, all_events, training_blocks, cluster_dir):
    os.makedirs(cluster_dir, exist_ok=True)
    edges = np.arange(WINDOW[0], WINDOW[1] + PSTH_BIN, PSTH_BIN)
    bin_centers = (edges[:-1] + edges[1:]) / 2
    csv_rows = []

    for i, (t0, t1) in enumerate(training_blocks):
        block_num = i + 1
        fig, axes = plt.subplots(5, 1, figsize=(7, 11), sharex=True,
                                  gridspec_kw={'height_ratios': [1, 1, 1, 1, 1.3]})
        taste_psths = {}
        for j, (taste, color) in enumerate(TASTE_COLORS.items()):
            events = events_by_taste[taste]
            events = events[(events >= t0) & (events <= t1)]

            raster = []
            for ev in events:
                rel = neuron_spikes_sec - ev
                rel = rel[(rel >= WINDOW[0]) & (rel < WINDOW[1])]
                raster.append(rel)
            counts_per_trial = np.array([np.histogram(rel, bins=edges)[0] for rel in raster]) \
                if len(raster) else np.zeros((0, len(bin_centers)))
            mean_rate_hz = counts_per_trial.mean(axis=0) / PSTH_BIN if len(raster) else np.zeros(len(bin_centers))
            taste_psths[taste] = mean_rate_hz

            zeta_p, zeta_valid = run_zeta(neuron_spikes_sec, events)
            anova_p = run_anova(neuron_spikes_sec, events)
            csv_rows.append({
                "block": block_num, "taste": taste, "n_trials": len(events),
                "zeta_p": zeta_p, "responsive_zeta": (zeta_p is not None and zeta_p < ALPHA) if zeta_valid else None,
                "anova_p": anova_p, "responsive_anova": (anova_p is not None and anova_p < ALPHA),
            })

            ax = axes[j]
            for r, rel in enumerate(raster):
                ax.vlines(rel, r, r + 0.8, color=color, linewidth=1)
            ax.axvline(0, color='black', linestyle='--', linewidth=0.8)
            ax.set_ylabel("trial #")
            ax.set_title(f"{taste} (n={len(events)} trials)", fontsize=10, loc='left')

        ax_psth = axes[4]
        for taste, color in TASTE_COLORS.items():
            ax_psth.plot(bin_centers, taste_psths[taste], color=color, linewidth=1.5, label=taste)
        ax_psth.axvline(0, color='black', linestyle='--', linewidth=0.8)
        ax_psth.set_xlabel("time relative to taste delivery (s)")
        ax_psth.set_ylabel("firing rate (Hz)")
        ax_psth.set_title("PSTH, all tastes overlaid", fontsize=10, loc='left')
        ax_psth.legend(loc='upper right', fontsize=9)

        fig.suptitle(f"Cluster {cluster_id}, Block {block_num} ({t0:.1f}s-{t1:.1f}s)", y=0.995, fontsize=11)
        plt.tight_layout()
        plt.savefig(f"{cluster_dir}/cluster{cluster_id}_block{block_num}_psth.png", dpi=110)
        plt.close(fig)

    csv_path = f"{cluster_dir}/cluster{cluster_id}_responsiveness_by_taste_and_block.csv"
    fieldnames = ["block", "taste", "n_trials", "zeta_p", "responsive_zeta", "anova_p", "responsive_anova"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    make_xlsx(csv_path, fieldnames)
    return csv_path


def make_xlsx(csv_path, fieldnames):
    """Same data as the CSV, but with each block's rows shaded a distinct
    background color for fast visual scanning (Peleg's request)."""
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))

    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(name="Arial", bold=True, color="FFFFFF")
    body_font = Font(name="Arial")
    border = Border(*(Side(style="thin", color="BFBFBF") for _ in range(4)))

    wb = Workbook()
    ws = wb.active
    ws.title = "responsiveness"
    for col_idx, name in enumerate(fieldnames, start=1):
        cell = ws.cell(row=1, column=col_idx, value=name)
        cell.font, cell.fill, cell.border = header_font, header_fill, border
        cell.alignment = Alignment(horizontal="center")
    ws.freeze_panes = "A2"

    for row_idx, row in enumerate(rows, start=2):
        fill = PatternFill(start_color=BLOCK_COLORS[int(row["block"])],
                            end_color=BLOCK_COLORS[int(row["block"])], fill_type="solid")
        for col_idx, name in enumerate(fieldnames, start=1):
            raw = row[name]
            if name in ("block", "n_trials"):
                value = int(raw)
            elif name in ("zeta_p", "anova_p"):
                value = float(raw) if raw not in ("", "None") else None
            elif name in ("responsive_zeta", "responsive_anova"):
                value = {"True": True, "False": False, "None": None, "": None}[raw]
            else:
                value = raw
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font, cell.fill, cell.border = body_font, fill, border
            if isinstance(value, float):
                cell.number_format = "0.0000"
            if isinstance(value, bool):
                cell.alignment = Alignment(horizontal="center")

    widths = {"block": 8, "taste": 12, "n_trials": 10, "zeta_p": 12,
              "responsive_zeta": 16, "anova_p": 12, "responsive_anova": 17}
    for col_idx, name in enumerate(fieldnames, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = widths.get(name, 12)

    wb.save(csv_path.replace(".csv", ".xlsx"))


# ── Driver ─────────────────────────────────────────────────────────────────────
def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal]

    (spike_times_samples, spike_clusters, sample_rate, good_clusters,
     events_by_taste, all_events) = load_animal_data(cfg)
    sorted_min = spike_times_samples.min() / sample_rate
    sorted_max = spike_times_samples.max() / sample_rate
    training_blocks = derive_training_blocks(all_events, sorted_min, sorted_max, cfg['licl_time_s'])

    print(f"{animal}: {len(good_clusters)} good clusters, "
          f"Training day blocks: {[(round(t0), round(t1)) for t0, t1 in training_blocks]}")

    local_root = f"/tmp/{animal}_cluster_analysis"
    os.makedirs(local_root, exist_ok=True)

    t_start = time.time()
    for ci, cluster_id in enumerate(good_clusters):
        neuron_spikes_sec = spike_times_samples[spike_clusters == cluster_id] / sample_rate
        cluster_dir = f"{local_root}/cluster_{cluster_id}"
        build_cluster_outputs(cluster_id, neuron_spikes_sec, events_by_taste, all_events,
                               training_blocks, cluster_dir)
        print(f"  [{ci+1}/{len(good_clusters)}] cluster {cluster_id} done "
              f"(total elapsed {(time.time()-t_start)/60:.1f} min)", flush=True)

    print(f"\nAll clusters done locally in {(time.time()-t_start)/60:.1f} min: {local_root}")

    nas_root = f"{cfg['out_dir'].rsplit('/', 1)[0]}/Cluster_analysis"
    print(f"Copying to {nas_root} ...")
    for cluster_id in good_clusters:
        local_dir = f"{local_root}/cluster_{cluster_id}"
        nas_dir = f"{nas_root}/cluster_{cluster_id}"
        os.makedirs(nas_dir, exist_ok=True)
        for fname in os.listdir(local_dir):
            copy_to_share_safely(os.path.join(local_dir, fname), nas_dir)
    print("Done.")


if __name__ == '__main__':
    main()
