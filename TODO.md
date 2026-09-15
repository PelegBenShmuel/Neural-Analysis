# TODO / Project Tracker

Living backlog for ProjectPeleg. See [README.md](README.md) for background and
terminology. Update this file as tasks are added, started, or finished — don't
let status live only in chat.

## Blocked / external

- [ ] **Full-recording Kilosort** for baseline (day 1) and extinction (day 3) —
      currently unavailable per Anan Moran. Unblocks: any within-unit
      before/after-CTA GC comparison. Re-check status periodically; this is the
      single biggest constraint on the project's scope right now.

## Data inventory & organization (MS08 / MS09 / MS11)

Three animals have completed buzcode sleep-scoring. Reviewed directly on disk
2026-09-15 (`diskh2` locally, `Z:\Peleg` = `smb://anannas/data/Peleg`, the lab
share):

| Animal | Session scored | Raw data | Buzcode results | On `Z:\Peleg`? | Plots |
|---|---|---|---|---|---|
| MS08 | `hab3toExp`, ~73h (confirmed via video length) | `diskh2/MS08/` (flat, no Raw_Data subfolder) | `diskh2/MS08/MS08_hab3toExp/` only | ❌ raw+meta present at `Z:\Peleg\MS08`, but the buzcode results themselves are **not copied there yet** | ✅ `Z:\Peleg\MS08\MS08_buzcode_analysis` (74 hourly plots) |
| MS09 | `hab3_ext`, ~73h | `Z:\Peleg\MS09\MS09_Raw_Data\` | `Z:\Peleg\MS09\MS09_Buzaki_results\` | ✅ fully organized | ✅ `Z:\Peleg\MS09\MS09_buzcode_analysis` (73 plots) |
| MS11 | `hab3` **only** (single day, not hab3-to-extinction) | `Z:\Peleg\MS11\MS11_raw_data\` | `Z:\Peleg\MS11\MS11-buzaki_pipeline_results\` | ✅ organized (naming differs slightly from MS09) | ✅ `Z:\Peleg\MS11\MS11_hab3_buzcode_analysis` |

Concrete follow-ups:

- [ ] **Copy MS08's buzcode results to `Z:\Peleg\MS08`** — it's the only one of
      the three not mirrored to the shared drive; everything else (this
      project's git repo, MS09, MS11) treats `Z:\Peleg` as the canonical place.
      Suggest `Z:\Peleg\MS08\MS08_Buzaki_results\`, matching MS09's naming.
- [ ] **Standardize the results-folder naming** across animals — MS09 uses
      `_Buzaki_results`, MS11 uses `-buzaki_pipeline_results`. Pick one
      convention going forward (MS09's is cleaner) and use it for MS08 and any
      new animal.
- [ ] **Reconcile MS11's shorter scored span** — MS11 is only scored for `hab3`
      alone, unlike MS08/MS09's full `hab3toExt`/`hab3_ext`. Check whether
      MS11's raw data for the rest of the protocol exists somewhere and just
      hasn't been scored, or was never fully recorded (same open question raised
      by MS24 having only an ~18.5h recording instead of the expected ~72h).
- [ ] **Codify the real `SleepScoreMaster` invocation** — found the actual
      working script at `Z:\Peleg\MS11\run_sleep_score.m`:
      ```matlab
      addpath(genpath('/media/anan/diskh1/Matlab_packages/buzcode/buzcode-master'));
      addpath('/home/peleg/matlab_mex');
      SleepScoreMaster(basePath, 'rejectChannels', [384], ...
          'SWChannels', [65], 'ThetaChannels', [65], 'noPrompts', true);
      ```
      Channel 65 was **manually chosen** for MS11 (not buzcode's auto-detect
      default) — picking a good SW/Theta channel per animal is a required manual
      step before scoring a new rat, not something to copy-paste from MS11.
- [ ] **Decide the source of truth for the Python scripts** — `MS_buzcode_analysis.py`
      and `VideoMovement.py` exist both in this git repo (`SleepAnalysis/`) and
      at `Z:\Peleg\ImportantScripts\` (which also has `lightsheet_to_tiff.py`,
      matching `Registration/`). These could silently drift apart; pick one and
      treat the other as a mirror, or symlink them together.

## Ready to start

- [ ] **Sleep-architecture comparison across the 3 days** — quantify WAKE/NREM/REM
      proportions, bout durations, and transition structure for baseline vs.
      CTA-day vs. extinction-day using existing buzcode output. No spike sorting
      needed; usable immediately for all animals with sleep scoring done.
      - Watch out for the LiCl-induced REM suppression documented in
        Venkatakrishna-Bhatt & Bureš 1978 (~3h post-injection) — don't treat the
        first few hours after LiCl as a clean "post-CTA sleep" baseline.
- [ ] **GC unit analysis within the CTA day** — align spike-sorted GC units to
      (a) taste delivery events and (b) sleep state (WAKE/NREM/REM, and ideally
      UP/DOWN within NREM), comparing before vs. after the LiCl injection moment
      within that single day. Bin by the Arieli et al. (2022) phase timeline
      (0–3h acquisition / 3–6h intermediate / 6–12h consolidation / 12–18h
      postconsolidation) so results are directly comparable to that paper, and
      separate early-epoch (identity) vs. late-epoch (palatability) responses
      rather than pooling the whole post-taste window.
- [ ] **Sleep vs. consolidation-phase ensemble quickening** — the sharpest current
      version of the hypothesis (see README Core hypothesis): Arieli et al. (2022)
      found GC ensemble-state dynamics quicken specifically during the 6–12h
      consolidation phase, hours after CTA induction. Test whether REM/NREM amount
      or timing in the intervening hours predicts the size or timing of that
      quickening (and of the late-epoch response-magnitude changes) on the CTA day.
      Needs: sleep-state timeline + GC units, both already available for the CTA day.
- [ ] **Generalize `MS_buzcode_analysis.py`** — currently hardcoded to
      `MS11_hab3` (paths, channel numbers, animal-specific config at the top of
      the file). Turn into a reusable per-animal/per-session pipeline as more
      animals come in.

## Under consideration

- [ ] Cross-check buzcode's motion/EMG-proxy channel against an ICA-derived
      IC-EMG (Osanai et al. 2023 method) for sleep-state scoring accuracy,
      particularly REM false-positive rate.
- [ ] UP/DOWN-state-resolved analysis of GC activity during NREM (method basis:
      Saleem et al. 2010), once there's a specific question that needs
      sub-NREM-state resolution.
- [ ] Once full-recording Kilosort becomes available: unit-tracked (or at least
      population-level) comparison of GC taste responses baseline vs. extinction,
      and reactivation-style analysis of CTA-day GC ensembles during subsequent
      sleep (NREM/REM).

## Done

- [x] Read and summarized the 7 papers in `Articles/` (see README Literature section).
- [x] Set up README.md + TODO.md as project sync documents (2026-09-15).
- [x] Re-read updated `Articles/` folder (4 CTA/PSD behavioral papers removed, 2
      Moran-authored papers added), sharpened the Core hypothesis around the Arieli
      et al. (2022) consolidation-phase ensemble-quickening finding (2026-09-15).
- [x] Reviewed `SleepAnalysis/` + the lab's data disks directly; confirmed
      buzcode is already proven on MS08/MS09/MS11, found the real
      `SleepScoreMaster` invocation (`run_sleep_score.m`) and the `.meta`→`.xml`
      generation logic; wrote `SleepAnalysis/generate_buzcode_xml.py`; did a full
      data inventory (see "Data inventory & organization" above) (2026-09-15).
