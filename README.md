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
readout independent of LFP-derived EMG.

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
    movement + taste-event timestamps for one session and visualizes them
    together. Currently hardcoded to one animal/session (`MS11_hab3`) — a
    candidate for generalizing into a reusable per-animal pipeline.
  - `VideoMovement.py` — per-frame movement via MOG2 background subtraction on
    session video, used as a video-based behavioral/EMG-proxy signal.
- **`Registration/`** — `lightsheet_to_tiff.py`: converts lightsheet microscopy
  channel data to TIFF, likely for histological verification of probe/fiber
  placement.
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

## How we work together

- Peleg's primary ask of Claude is **analysis code** (Python, possibly touching
  MATLAB/buzcode outputs).
- **TODO.md is Peleg's own tracker** — Claude doesn't edit it unless asked.
  README.md (this file) is background/reference and Claude keeps it accurate
  when asked to, but neither file should be edited reflexively every turn.
- Claude should be able to explain any article above, or underlying neuroscience
  concepts, on request.
