# TODO / Project Tracker

Living backlog for ProjectPeleg. See [README.md](README.md) for background and
terminology. Update this file as tasks are added, started, or finished — don't
let status live only in chat.

## Blocked / external

- [ ] **Full-recording Kilosort** for baseline (day 1) and extinction (day 3) —
      currently unavailable per Anan Moran. Unblocks: any within-unit
      before/after-CTA GC comparison. Re-check status periodically; this is the
      single biggest constraint on the project's scope right now.

## Data inventory & organization (MS08 / MS09 / MS11 only)

These are the three animals with a **full recording** and completed buzcode
sleep-scoring — the only ones in active discussion right now. (MS18, MS23, and
others exist on the lab share too, but are out of scope here: MS18 went through
a different, non-buzcode pipeline; the rest aren't organized yet.)

Current state on `Z:\Peleg` (`smb://anannas/data/Peleg`), as of 2026-09-15 —
**all three now follow the same 3-folder pattern** (raw data / buzcode results
/ analysis plots), though the exact naming still isn't consistent:

| Animal | Session scored | Raw data folder | Buzcode results folder | Plots folder |
|---|---|---|---|---|
| MS08 | `hab3toExp`, ~73h (confirmed via video length) | `MS_08_Raw_Data\` | `MS08_Buzaki_results\` | `MS08_buzcode_analysis\` (74 plots) |
| MS09 | `hab3_ext`, ~73h | `MS09_Raw_Data\` | `MS09_Buzaki_results\` | `MS09_buzcode_analysis\` (73 plots) |
| MS11 | `hab3` **only** (single day, not hab3-to-extinction) | `MS11_raw_data\` | `MS11-buzaki_pipeline_results\` | `MS11_hab3_buzcode_analysis\` (74 plots) |

Concrete follow-ups:

- [x] ~~Copy MS08's buzcode results to `Z:\Peleg\MS08`~~ — done 2026-09-15:
      created `MS08_Buzaki_results\` with all 5 `.mat` files, the `.xml`, and
      `StateScoreFigures\`, copied from `diskh2`. Also moved MS08's raw files
      (already sitting flat in the folder) into the pre-existing
      `MS_08_Raw_Data\`.
- [ ] **Add a pointer note inside `MS08_Buzaki_results`** — the one thing that
      didn't copy over was the `.lfp` file itself, because on `diskh2` it's a
      Unix symlink to the raw `.lf.bin`, and SMB shares can't hold symlinks
      (`cp: cannot create symbolic link ... Operation not supported`). The raw
      data it pointed to now lives in `MS_08_Raw_Data\` instead — worth a short
      text note in `MS08_Buzaki_results\` saying so, so it's not a silent gap.
- [ ] **Standardize the raw-data/results folder naming** — now three different
      spellings across three animals: `MS_08_Raw_Data` / `MS09_Raw_Data` /
      `MS11_raw_data`, and `MS08_Buzaki_results` / `MS09_Buzaki_results` /
      `MS11-buzaki_pipeline_results`. Pick one convention (MS09's is cleanest)
      and apply it to all three.
- [ ] **Reconcile MS11's shorter scored span** — MS11 is only scored for `hab3`
      alone, unlike MS08/MS09's full `hab3toExt`/`hab3_ext`. Check whether
      MS11's raw data for the rest of the protocol exists somewhere and just
      hasn't been scored yet, or was never fully recorded.
- [x] ~~Codify the real `SleepScoreMaster` invocation~~ — done 2026-09-15:
      copied `Z:\Peleg\MS11\run_sleep_score.m` into
      `SleepAnalysis/run_sleep_score.m` (git-tracked), with a header noting it's
      MS11-specific — channel 65 was **manually chosen** for SW/Theta detection
      (not buzcode's auto-default), so picking a good channel per animal is a
      required manual step before scoring a new rat.
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
- [x] Reorganized MS08 on `Z:\Peleg` to match MS09/MS11's raw-data/results/
      analysis folder pattern — moved raw files into `MS_08_Raw_Data\`, copied
      buzcode `.mat`/`.xml`/`StateScoreFigures` output into a new
      `MS08_Buzaki_results\` (2026-09-15).
- [x] Committed and pushed all of today's changes to `origin/main`
      (`3d0ee2f..4da55ca`): README.md, TODO.md, Experiment Protocol and
      Procedure.md, the Articles swap, `generate_buzcode_xml.py`, and
      `run_sleep_score.m` (2026-09-15).
