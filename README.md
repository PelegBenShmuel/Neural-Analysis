# ProjectPeleg — Sleep & the Gustatory Cortex After CTA

Working notes for Peleg Ben Shmuel's project on how gustatory cortex (GC) activity
changes after conditioned taste aversion (CTA) induction, and how sleep — especially
REM / paradoxical sleep (PS) — shapes that change. This file and [TODO.md](TODO.md)
are the sync point between Peleg and Claude across sessions: update them as the
project evolves rather than relying on chat history.

## Hypothesis question

**Are the sleep patterns that follow CTA induction relevant to the neural
changes in gustatory cortex (GC) that occur after CTA?** That's the question
this project exists to answer — everything below is context and scaffolding for
investigating it.

The reasoning that motivates asking it:

- Classic behavioral pharmacology (Bureš/Burešová/Venkatakrishna-Bhatt group,
  1976–1988; no longer in `Articles/` but summarized from memory below)
  established that REM sleep deprivation blocks CTA *acquisition* and
  *extinction* without affecting *retrieval* — implying REM is needed to modify
  the aversion engram, not to read it out.
- This project's direct electrophysiological precursor, **Elor Arieli, Nadia
  Younis & Anan Moran (2022)** — Anan's own paper, from this lab — tracked GC
  activity continuously for 24h around CTA induction, *without* a sleep readout,
  and found that a network-level signature of memory consolidation (ensemble-state
  dynamics quickening) emerges hours after CTA induction, specifically during a
  6–12h "consolidation" phase — well after the initiating LiCl injection (see
  Scientific background below for the full result).
- That hours-long delay between the triggering event and the network-level change
  is exactly the kind of gap intervening sleep could plausibly fill. This
  project's angle: test whether the amount/timing of REM and NREM sleep in the
  hours between CTA induction and that consolidation window predicts the size or
  timing of the neural changes Arieli et al. (2022) described.

## Experimental design & protocol

Full day-by-day protocol (confirmed directly by Mai Shafiki, the Masters student
running the experiment): **[Experiment Protocol and Procedure.md](Experiment%20Protocol%20and%20Procedure.md)**.
Summary:

- Chronic **Neuropixels 1.0** implant in GC + **IOC** (intraoral cannula) taste
  delivery, Long-Evans rats.
- Fixed **6-day protocol**: 3 habituation days (Hab D1–D3) → Training/CTA day
  (Day 4, LiCl pairing) → Test + Extinction day (Day 5) → Final test day (Day 6).
- Neuropixels recording starts on **Hab D3** and runs continuously through Day 6
  — roughly 72h total, but spanning **4 calendar days**, not 3 (an earlier
  version of this doc assumed a simpler 3-day baseline/CTA/extinction split —
  that was wrong; see the protocol doc for the corrected breakdown).
- **Kilosort / spike-sorting constraint:** currently sorted only for the
  Training day (all 7 blocks) **plus "Block 8"** — the first IOC session of Day
  5 — per `np_analysis`'s block numbering. The rest of Day 5 and all of Day 6
  are recorded but unsorted. Hab D3 (the pre-CTA baseline day) is also unsorted.
  This is a stated constraint from Anan Moran, not just a pending step.
- **Within the sorted window**, align analyses to the Arieli et al. (2022) phase
  timeline so results are directly comparable to that paper: 0–3h post-CTA =
  acquisition, 3–6h = intermediate, 6–12h = consolidation, 12–18h =
  postconsolidation.

Also present in the recording: taste-delivery event markers (Water / Sucrose /
Salt / Acid, from nidq sync channels) and video for a movement-based behavioral
readout independent of LFP-derived EMG. Taste code convention in the raw data
(matches the `xd_0_<N>_0` sync-channel file suffix, e.g.
`MS_buzcode_analysis.py`'s `TASTE_FILES`): **1 = Water, 2 = Sucrose, 3 = NaCl
(Salt), 4 = Acid (Citric Acid)**.

## Spike-level analysis — current focus: Training day only

Peleg's own spike-level analysis (PSTHs, responsiveness, etc.) is scoped to
**the Training day (Day 4)** — the LiCl-pairing day — not Day 5/Block 8 or any
other sorted window, until stated otherwise.

- **Where the raw spike-sorted data lives (MS08):** `Z:\Mai\MS08\MS08_hab3toExp_g1\`
  (this recording file spans Hab D3 → Training day). Three independent
  sorter outputs exist there — `kilosort3_23_50h_mai`, `kilosort4_23_49h`,
  `kilosort4_23_49h_mai` — **currently using `kilosort4_23_49h_mai`** (Phy-curated,
  41 "good" units). The other two are *not* confirmed to share the same time
  base as this one (a spot check found `kilosort3_23_50h_mai`'s spike times
  spanning 0–97,202s, not the expected ~82,800–176,400s) — don't swap sorter
  outputs without re-verifying alignment first.
- **Files actually needed for a PSTH** (the minimal raw set, deliberately not
  Mai's derived analysis tables in that same folder's `analysis/` subfolder):
  `spike_times.npy` + `spike_clusters.npy` (raw Kilosort output) +
  `cluster_group.tsv` (Phy curation label, keep `good` only) + the AP-band
  sample rate from `*.imec0.ap.meta`'s `imSampRate` (~29999.56 Hz measured, not
  the nominal 30000 Hz) + the raw TPrime-corrected taste-event `_corr.txt`
  files (already synced to the same clock as the spikes).
- **Training day block structure** (per `Experiment Protocol and Procedure.md`):
  **Block 1** = pre-injection reference (50 trials: 20 Sucrose + 10 each
  Water/NaCl/CA) → **LiCl injected** ~5 min after Block 1 ends → **Blocks 2–7**
  = post-LiCl (40 trials each, 10/taste, ~2h spacing). In this recording,
  Block 1 falls at ~89,993–90,589s and Block 7 at ~140,394–140,868s.
- MS08 is inferred **Experimental group** (not in the Control/Fam trio
  MS15/MS18/MS20) — Sucrose is a genuinely novel CS here, making it the taste
  most directly relevant to a CTA-driven responsiveness change.
- **MS09 and MS11 have the same minimal spike-sorted file set mirrored** to
  `Z:\Peleg\<animal>\<animal>_Spike_Sorted_Data\` now, so this analysis isn't
  MS08-only going forward. **MS11 needed a correction first (2026-09-22)**:
  its `licl_time_s` was wrongly `None` ("hab-day-only recording"), assumed
  rather than checked — its raw taste-event data actually shows the same
  double-Sucrose Block 1 signature as MS08/MS09 (20 vs. 10, at
  t=88694.3-89292.2s), so it does have a real Training day; fixed and its
  sleep-side Training-day extraction (`Z:\Peleg\MS11\MS11_Training_Day\`) now
  exists to match MS08/MS09.
- **`NeuralAnalysis/cluster_responsiveness.py`** ports the PSTH/ZETA/ANOVA
  method above into a real, git-tracked script (previously ad-hoc scratch
  scripts). Built and run on MS08's 41 good units first: the two
  responsiveness tests agree 85% of the time (25.5% both-responsive, 59.5%
  both-not, 15% disagree) — a real but imperfect cross-check. One
  single-neuron finding worth following up: cluster 19's Sucrose
  responsiveness was significant pre-LiCl, lost in Blocks 2-3, and regained
  from Block 4 on — not yet checked across more units. **Caution before
  trusting MS09/MS11 numbers from this script as much as MS08's**: MS08's
  `cluster_group.tsv` was manually curated down to 41 "good" units from 245
  raw clusters (100% of survivors kept), while MS09 (225 of 537) and MS11
  (256 of 257) show a much blunter cut — most of what survives an initial
  prune gets labeled "good" without MS08's apparent per-unit scrutiny, worth
  confirming with Mai/Anan before reading too much into per-unit results
  there.

## Animals & groups

Per Mai's protocol, animals are split into an **Experimental** group (sucrose
withheld until Day 4 — a genuinely novel CS, real CTA) and a **Control/Fam**
group (sucrose included in the taste battery from Day 1 — pre-exposed/familiar,
used to isolate LiCl/malaise/time effects from the CTA-specific association;
same logic as Arieli et al. 2022's Exp/Fam design).

- **Control (Familiar): MS15, MS18, MS20**
- **Experimental: all other animals** (e.g. `MS11`)

This matters for interpretation: any GC/sleep effect seen in a Control/Fam
animal should *not* be attributed to CTA learning itself, since sucrose wasn't
novel for them.

## Repository layout

- **`SleepAnalysis/`** — sleep scoring and state-related analysis.
  - `buzcode/` (git-ignored, third-party) — Buzsáki-lab MATLAB toolbox; produces
    WAKE / NREM / REM classification from LFP (broadband slow-wave power, theta
    ratio, EMG-derived motion) — see `*.SleepState.states.mat` output.
  - `MS_buzcode_analysis.py` — loads buzcode sleep-state output + LFP + video
    movement + taste-event timestamps and visualizes them together, hourly.
    Takes an `ANIMAL` argument and reads all paths/channels/LiCl time from an
    `ANIMALS` config dict (MS08, MS09, MS11) — one script, not a copy per
    animal (see "How we work together").
  - `sleep_sanity_check.py` — coverage/state-proportion/bout-duration/
    taste-alignment/REM-plausibility/fragmentation checks for one animal's
    buzcode output, run before trusting it for anything downstream. Same
    `ANIMAL`-argument convention.
  - `run_sleep_score.m` / `find_theta_channel.m` — the actual
    `SleepScoreMaster` invocation and a memory-safe (bounded-window, capped-
    worker) full-channel theta search, respectively. Same per-animal
    `ANIMALS`-struct convention as the Python scripts, switched via an
    `ANIMAL` variable.
  - `training_day_sleep_state_extraction.py` — cuts an animal's buzcode
    classification down to just the Training day (9AM-9AM around LiCl
    injection), reporting WAKE/NREM/REM by Arieli et al. (2022) phase.
  - `sleep_char.py` — sleep-bout-duration distribution and per-hour sleep
    amount (minutes asleep + % of that day's total, with a 24h total) for
    an animal's Training-day cut; reads the same output
    `training_day_sleep_state_extraction.py` writes.
  - `compare_theta_channels.py` — compares two scorings of the same
    recording that differ only in theta channel (e.g. MS11's channel 65 vs.
    81), reusing `sleep_sanity_check.py`'s loading/checking functions rather
    than duplicating them; produces a side-by-side stats table and a stacked
    hypnogram figure.
  - `VideoMovement.py` — per-frame movement via MOG2 background subtraction on
    session video, used as a video-based behavioral/EMG-proxy signal.
- **`NeuralAnalysis/`** — spike-level analysis (see "Spike-level analysis"
  above).
  - `cluster_responsiveness.py` — per-(cluster x taste x Training-day-block)
    responsiveness: builds PSTHs from raw Kilosort/Phy output and runs two
    independent tests (ZETA and a repeated-measures ANOVA over 250ms bins)
    so results can be cross-checked against each other. Imports shared
    config/helpers (`ANIMALS`, `TASTE_COLORS`, `copy_to_share_safely`) from
    `SleepAnalysis/MS_buzcode_analysis.py` rather than redefining them.
- **`Registration/`** — `lightsheet_to_tiff.py`: converts lightsheet microscopy
  channel data to TIFF, likely for histological verification of probe/fiber
  placement. `registration_status.md` — status/debugging log for registering
  dye-labeled cleared brains (MS19/MS21/MS23) to the Princeton RAtlas (PRA)
  common coordinate framework, to verify claimed electrode placement (e.g.
  GC); the actual pipeline/atlas/outputs live on `/mnt/tnvme/peleg_*_registration/`
  and `Z:\Peleg\<animal>\...`, not in this repo — see that file before
  starting new registration work. `view_ms19_registration.py` /
  `view_ms21_registration.py` — standalone napari viewer scripts (one per
  animal, deliberately not shared/generalized) meant to be run on Peleg's own
  Windows machine against the mapped NAS drive, not through Claude Code.
  `atlas_labels/` — the WHS v4 atlas's region ID→name table
  (`parse_whs_labels.py` + `whs_v4_labels.csv`).
- **`Articles/`** — the literature backbone (see below).

## Scientific background

Articles is an actively curated folder — check back here when it changes, since
what's "live" reading material shifts as the project focuses. Current contents,
as of 2026-09-15.

**Elior Arieli's and Anan Moran's foundational work — the direct precursor to
this project:**
- ⭐ **Arieli, Younis & Moran (2022)**, *J Neurosci* — "Distinct Progressions of
  Neuronal Activity Changes Underlie the Formation and Consolidation of a
  Gustatory Associative Memory." Elor (Elior) Arieli and Nadia Younis, first
  authors, with Anan Moran as senior author — this lab's own prior paper, on
  essentially the same rig this project extends (chronic GC electrode bundle,
  intraoral cannulae taste delivery, LiCl CTA induction, Exp vs.
  taste-familiarized Fam control group) but tracked continuously for 24h
  *without* sleep scoring. This is the paper whose gap in explanation — a
  network-level change that appears hours after the neurons' own activity has
  already shifted — motivates this project's hypothesis question above. Defines
  the phase timeline this project should align to: **0–3h post-CTA =
  acquisition, 3–6h = intermediate, 6–12h = consolidation, 12–18h =
  postconsolidation.** Key results:
  - Single-neuron taste responsiveness and population response *magnitude*
    increase specifically during acquisition (0–3h) and again during
    consolidation (6–12h) — but dip back toward baseline in the 3–6h intermediate
    phase. This "double-peak" pattern is driven by the **late-epoch (LE, 1000–2500ms
    post-taste)** response, i.e. the palatability-coding part of the taste
    response, not the early-epoch (EE, 200–800ms) identity-coding part.
  - **Ensemble-state dynamics** (HMM-fit transition speed from identity-coding to
    palatability-coding ensemble states) only quicken *after* the consolidation
    phase (significant at 6–12h) — i.e. this network-level signature lags the
    single-neuron-level changes by hours. This is the specific gap this project's
    sleep hypothesis targets (see Core hypothesis above).
  - Individual neurons change their taste responsiveness "chaotically" (no fixed
    order/identity of which neurons respond when), but these are balanced at the
    population level — a useful reminder not to expect single "CTA-encoding"
    neurons to behave uniformly.
  - Methodological notes worth reusing: a Fam (taste-familiarized) control group to
    separate LiCl/malaise/time effects from the CTA-taste-association per se; an
    aversion index (water / (water+saccharin) consumption) as the behavioral
    readout; movement/video tracking used only to rule out confounds, not as a
    primary variable.

**GC circuit context:**
- **Piette, Baez-Santiago, Reid, Katz & Moran (2012)**, *J Neurosci* — "Inactivation
  of Basolateral Amygdala Specifically Eliminates Palatability-Related Information
  in Cortical Sensory Responses." From Anan's postdoc (Katz lab). Shows that
  temporarily silencing basolateral amygdala (BLA) leaves GC taste-identity coding
  (early epoch) intact but abolishes/reduces palatability-related coding (late
  epoch) in nearly all taste-responsive GC neurons. **Relevance:** it's specifically
  the late-epoch/palatability signal — the same one that drives the Arieli et al.
  2022 consolidation-phase changes — that depends on amygdala input. If this
  project finds sleep-dependent changes in GC late-epoch responses, BLA-GC
  interaction is the natural circuit-level explanation to reach for, even without
  BLA recordings of our own.

**Modern electrophysiology/methods** (tools and framework for the sleep side):
- *Network Homeostasis and State Dynamics of Neocortical Sleep* (Watson, Levenstein,
  Buzsáki et al., 2016, *Neuron*) — key conceptual anchor. Shows sleep doesn't
  uniformly suppress firing: fast-firing neurons decrease and slow-firing neurons
  *increase* their rates over sleep, with REM and NREM/microarousals making
  distinct, cooperating contributions to this homogenization. Directly motivates
  looking at *rate-dependent* (not just population-average) changes in GC units
  across sleep, and at REM vs. NREM contributions separately rather than lumping
  "sleep" together.
- *Methods for predicting cortical UP and DOWN states from deep-layer LFP phase*
  (Saleem et al., 2010) — the method basis for detecting UP/DOWN states from LFP
  phase (<4Hz bands) and/or multi-unit activity when intracellular ground truth
  isn't available. Relevant if we want UP/DOWN-state-resolved analysis of GC
  activity during NREM, not just NREM/REM/WAKE-level.
- *Extracting EMG signals from multichannel LFPs using ICA* (Osanai et al., 2023) —
  method to recover an EMG-like signal (IC-EMG) directly from multichannel LFP via
  ICA, without a dedicated EMG electrode; validated against real EMG and shown to
  improve REM detection accuracy (fewer false positives) versus video-alone scoring.
  Worth considering as a cross-check/supplement to the buzcode motion-channel proxy
  currently used for sleep scoring.
- *Electrophysiological changes induced by PSD and LiCl* (Venkatakrishna-Bhatt &
  Bureš, 1978) — LiCl poisoning itself suppresses REM sleep for ~3h post-injection,
  and prior REM deprivation blocks the normal compensatory REM rebound after LiCl.
  **Implication:** the CTA-induction moment (LiCl) perturbs the very sleep
  architecture we're using as an explanatory variable — post-LiCl REM suppression
  needs to be accounted for, not treated as a clean baseline, especially since it
  overlaps the 0–3h acquisition phase from Arieli et al. (2022).

**Background, not currently in the folder** (read previously, summarized from
memory — re-add to `Articles/` if we want to cite these directly): the
Bureš/Burešová/Venkatakrishna-Bhatt behavioral series (1976–1988) established that
24–96h REM sleep deprivation (PSD) blocks CTA *acquisition* when applied
beforehand, slows CTA *extinction* ~3x when applied before extinction sessions,
but leaves *retrieval* of an already-formed CTA unaffected or even improved —
the behavioral basis for "REM sleep is needed to modify the engram, not read it."

## Glossary (ask Claude to expand any of these)

- **CTA** — Conditioned Taste Aversion: pairing a novel taste (CS) with visceral
  malaise (US, typically LiCl injection) produces long-lasting avoidance of that taste.
- **PSD** — Paradoxical Sleep Deprivation (REM sleep deprivation), classically via
  the pedestal/flower-pot technique.
- **GC** — Gustatory cortex; here specifically the taste-responsive cortical area
  being recorded.
- **BLA** — Basolateral amygdala; monosynaptically connected to GC, drives the
  palatability (late-epoch) component of GC taste responses (Piette et al. 2012).
- **EE / LE** — Early epoch (~200–800ms post-taste, codes taste *identity*) vs. Late
  epoch (~1000–2500ms post-taste, codes taste *palatability*) of a GC taste
  response (Arieli et al. 2022 terminology, consistent with the broader GC literature).
- **Exp / Fam groups** — Arieli et al. (2022) design: Exp = experimental animals
  that get a genuinely novel taste paired with LiCl (real CTA); Fam = control
  animals pre-familiarized to the same taste before LiCl (reduces/prevents CTA via
  latent inhibition) — isolates CTA-specific effects from generic LiCl/malaise/
  passage-of-time effects.
- **Ensemble-state dynamics** — sequences of population activity states (fit via
  Hidden Markov Model) that a GC ensemble transitions through during a taste
  response; the speed of the identity→palatability state transition is itself a
  learning-sensitive readout, independent of firing-rate magnitude.
- **buzcode states** — WAKE / NREM / REM, auto-classified from LFP broadband
  slow-wave power, theta/delta ratio, and an EMG-proxy motion signal.
- **UP/DOWN states** — sub-second bistable population activity states within NREM;
  UP = depolarized/spiking, DOWN = hyperpolarized/silent.

## Known limitations

- **REM/theta detection is structurally limited by electrode placement.**
  buzcode's REM scoring depends on a clean theta-band signal, which cortical
  LFP only picks up well at sites that are strongly coupled to the
  hippocampal theta generator (e.g. medial prefrontal cortex, per Watson,
  Levenstein, Greene, Gelinas & Buzsáki 2016 — the *Network Homeostasis and
  State Dynamics of Neocortical Sleep* paper this scoring pipeline is built
  around, which recorded from frontal cortical areas: mPFC, OFC, ACC,
  secondary motor cortex). **Gustatory cortex is not part of that
  hippocampal-theta-synchronized network** — GC's local rhythms are
  dominated by taste/ingestion-related activity instead. Confirmed on MS08
  2026-09-16: searching all 384 channels for the best theta separation
  (`SleepAnalysis/find_theta_channel.m`) found a real channel (370, vs. the
  poorly-separated channel 65 reused from MS11) and REM detection improved
  methodologically (a genuine bimodal split now exists), but overall REM
  still comes out sparse and short-bout (~1% of the recording, see
  `sleep_sanity_check.py`) — a probe-placement ceiling, not a
  channel-picking bug. Treat REM-timing results from this pipeline as
  provisional/conservative for any animal recorded from GC rather than a
  theta-coupled region.
  **MS09 is worse, not just similarly limited:** its highest-raw-theta-power
  channel (295) turned out to be actively misleading rather than merely
  weak — theta rose *with* EMG/movement (a licking/chewing-rhythm artifact,
  not real theta), inflating REM to an implausible 33% of the recording and
  putting most taste deliveries outside WAKE. A follow-up channel (107),
  chosen instead for having theta correctly *decoupled* from EMG, gave a
  near-identical bad result because its theta-ratio distribution isn't
  bimodal at all (buzcode's threshold-picking silently degenerates to 0 in
  that case). MS09 is reverted to its original channel 65 — no channel
  tested so far gives it a usable theta split, unlike MS08. **MS11** has a
  real candidate (channel 81, channel 65 ranks 262nd of 384) that was
  actually applied and tested (2026-09-18, after copying its 506GB raw file
  to local disk so the rescore ran at a reasonable speed) — but it hit the
  same degenerate-threshold failure as MS09's alternates: buzcode's
  bimodal-dip test failed *and* its NREM-exclusion fallback also failed,
  inflating REM to 16.7%/789 bouts (outside the typical 3-15% range) vs.
  channel 65's 6.7%/284 bouts. It passed the EMG-quiescence check (unlike
  MS09's channel 295), so it isn't an obvious movement artifact, but the
  extra REM likely comes from an unvalidated threshold rather than real
  sensitivity. MS11 is reverted to channel 65, same call as MS09; the
  channel-81 result is archived (not deleted) at `Z:\Peleg\MS11\
  MS11_Buzaki_results_ch81\` and the comparison at `Z:\Peleg\MS11\
  MS11_theta_channel_comparison\` (see `SleepAnalysis/compare_theta_channels.py`),
  in case an independent video-movement trace for MS11 is worth building
  later to settle it either way.

## How we work together

- Peleg's primary ask of Claude is **analysis code** (Python, possibly touching
  MATLAB/buzcode outputs).
- **TODO.md is Peleg's own tracker** — Claude doesn't edit it unless asked.
  README.md (this file) is background/reference and Claude keeps it accurate
  when asked to, but neither file should be edited reflexively every turn.
- Claude should be able to explain any article above, or underlying neuroscience
  concepts, on request.
