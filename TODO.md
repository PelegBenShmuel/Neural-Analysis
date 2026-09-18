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

**Standing process (2026-09-17):** data-completeness/organization work is not
MS08-only by default. When a gap like the ones below gets fixed for one
animal (a stale `Z:\Peleg` copy, missing spike-sorted data, a new per-animal
analysis script/output), add a matching follow-up item for MS09 and MS11 (and
future animals) here rather than treating the MS08 fix as the end of it —
see the two "not yet checked" items below for the current instances of this.

Current state on `Z:\Peleg` (`smb://anannas/data/Peleg`), as of 2026-09-16 —
**all three now follow the exact same 3-folder pattern and naming**
(`MS_<NN>_Raw_Data` / `MS<NN>_Buzaki_results` / `MS<NN>_buzcode_analysis`):

| Animal | Session scored | Raw data folder | Buzcode results folder | Plots folder |
|---|---|---|---|---|
| MS08 | `hab3toExp`, ~73h (confirmed via video length) | `MS_08_Raw_Data\` | `MS08_Buzaki_results\` | `MS08_buzcode_analysis\` (74 plots) |
| MS09 | `hab3_ext`, ~73h | `MS_09_Raw_Data\` | `MS09_Buzaki_results\` | `MS09_buzcode_analysis\` (73 plots) |
| MS11 | `hab3` **only** (single day, not hab3-to-extinction) | `MS_11_Raw_Data\` | `MS11_Buzaki_results\` | `MS11_buzcode_analysis\` (74 plots) |

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
- [x] ~~Standardize the raw-data/results folder naming~~ — done 2026-09-16:
      renamed `MS09_Raw_Data`→`MS_09_Raw_Data`, `MS11_raw_data`→`MS_11_Raw_Data`,
      `MS11-buzaki_pipeline_results`→`MS11_Buzaki_results`, and
      `MS11_hab3_buzcode_analysis`→`MS11_buzcode_analysis`, matching MS08's
      pattern exactly. As a direct consequence, fixed 6 now-stale hardcoded
      paths in `SleepAnalysis/MS_buzcode_analysis.py` (`SYNC_FILE`,
      `TASTE_FILES`, `OUT_DIR`) that pointed at the old MS11 folder names.
      **Not yet fixed**: the separate copy at `Z:\Peleg\ImportantScripts\MS_buzcode_analysis.py`
      still has the old paths — another argument for resolving the
      source-of-truth item below.
- [ ] **Reconcile MS11's shorter scored span** — MS11 is only scored for `hab3`
      alone, unlike MS08/MS09's full `hab3toExt`/`hab3_ext`. Check whether
      MS11's raw data for the rest of the protocol exists somewhere and just
      hasn't been scored yet, or was never fully recorded.
- [x] ~~Sync MS08's corrected (theta-channel-370) buzcode output to
      `Z:\Peleg`~~ — done 2026-09-17: `Z:\Peleg\MS08\MS08_Buzaki_results\` had
      gone stale after the 2026-09-16 theta-channel fix (it still held the
      channel-65 scoring from 2026-09-15's original sync). Re-synced all 5
      `.mat` files + the `SWTHChannels.jpg` figure from `diskh2`, verified
      byte-identical by size.
- [x] ~~Check MS09/MS11 for the same rerun-then-forgot-to-sync gap~~ —
      checked 2026-09-17: MS09 does **not** have a working alternate channel
      after all. Channel 295 (highest raw theta power, from
      `find_theta_channel.m`) turned out to be a licking/movement artifact
      (theta rose *with* EMG, `sleep_sanity_check.py` showed REM at an
      implausible 33% and video movement during "REM" nearly matching WAKE).
      Channel 107 (found via a follow-up theta-vs-EMG decoupling scan,
      correlation in the *correct* direction) gave a near-identical result —
      turned out its theta-ratio distribution isn't actually bimodal, so
      buzcode's threshold degenerated to 0 for both attempts. **MS09 is
      reverted to its original channel 65** (verified via `sleep_sanity_check.py`:
      back to REM 1.8%, matching the pre-fix baseline) — no channel tested so
      far gives it a clean theta split, unlike MS08. `Z:\Peleg\MS09\MS09_Buzaki_results\`
      was never touched by any of this (all work was on the `diskh2` working
      copy), so it's already consistent with the reverted state. MS11's
      equivalent gap is now its own Blocked item above (channel 81 found but
      rescore not applied).
- [x] ~~Mirror MS08's raw spike-sorted data onto `Z:\Peleg`~~ — done
      2026-09-17: it previously lived only on `Z:\Mai\MS08\MS08_hab3toExp_g1\`
      (a different share). Added `Z:\Peleg\MS08\MS08_Spike_Sorted_Data\` with
      the minimal raw set Peleg's own PSTH analysis actually reads --
      `spike_times.npy`, `spike_clusters.npy`, the `cluster_*.tsv` label
      files, `good_units.csv`/`good_units_info.json`, both
      `blocks_by_day_*.json` block-timing files, and the `imec0.ap.meta`
      (AP sample rate) -- verified byte-identical by size. Deliberately
      **not** mirrored: Mai's derived analysis tables
      (`kilosort4_23_49h_mai/analysis/`) and ~50GB of extra Kilosort
      byproducts (`pc_features.npy` etc.) nobody here reads, and the raw
      video/AP-band binary (~80GB, `diskh2`-only) -- Peleg confirmed these
      aren't needed right now.
- [x] ~~Codify the real `SleepScoreMaster` invocation~~ — done 2026-09-15:
      copied `Z:\Peleg\MS11\run_sleep_score.m` into
      `SleepAnalysis/run_sleep_score.m` (git-tracked), with a header noting it's
      MS11-specific — channel 65 was **manually chosen** for SW/Theta detection
      (not buzcode's auto-default), so picking a good channel per animal is a
      required manual step before scoring a new rat.
- [x] ~~Decide the source of truth for the Python scripts~~ — decided
      2026-09-16, then **revised same day**: the git repo
      (`ProjectPeleg/SleepAnalysis`/`Registration`) is the **sole** source of
      truth. `Z:\Peleg\ImportantScripts\` is now considered obsolete/irrelevant
      — it is *not* maintained as a mirror going forward (the earlier plan to
      manually re-sync it is dropped). It was synced once on 2026-09-16 before
      this decision, so it isn't currently stale, but no future git changes
      will be propagated there. Leave the folder as-is on disk; don't delete it
      unless asked.

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
- [x] ~~Generalize `MS_buzcode_analysis.py`~~ — done: it now takes an
      `ANIMAL` argument and reads all paths/channel numbers/LiCl time from an
      `ANIMALS` config dict (MS08, MS09, MS11). Not one-copy-per-animal.
- [x] ~~Add MS09 to `MS_buzcode_analysis.py`'s and
      `training_day_sleep_state_extraction.py`'s shared `ANIMALS` config~~ —
      done 2026-09-17: found MS09's LiCl injection time the same way as
      MS08's (taste-event blocks, double-Sucrose CTA-induction block at hour
      ~24.66h). Training-day extraction now runs for MS09 too.

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
- [x] Found and fixed MS08's theta-channel problem (channel 65, reused
      from MS11, gave near-zero REM separation on MS08) via a full-384-channel
      search (`SleepAnalysis/find_theta_channel.m`) — channel 370 found and
      re-scored; wrote `SleepAnalysis/sleep_sanity_check.py` to catch this
      class of problem automatically for any animal/session going forward
      (2026-09-16).
- [x] Built `SleepAnalysis/training_day_sleep_state_extraction.py`
      (renamed 2026-09-17 from `training_day_sleep_classification.py`) — cuts
      an animal's buzcode WAKE/NREM/REM classification down to a 24h Training
      day window (9:00 AM on the day LiCl was injected through 9:00 AM the
      next day), reports WAKE/NREM/REM %s and REM bout counts per Arieli et
      al. (2022) phase (pre-injection / acquisition / intermediate /
      consolidation / postconsolidation), and saves the cut
      `.SleepState.states.mat` + a phase-breakdown CSV + a hypnogram plot to
      `Z:\Peleg\<animal>\<animal>_Training_Day\`. Shares the `ANIMALS` config
      with `MS_buzcode_analysis.py` (not a per-animal copy). Run for MS08
      2026-09-17; needs MS09 added to `ANIMALS` first to run for MS09 (see
      Ready to start, above); not applicable to MS11 (no Training day).
- [x] Mirrored MS08's minimal raw spike-sorted data and re-synced its
      corrected buzcode output to `Z:\Peleg\MS08\` (see "Data inventory &
      organization" above for both) (2026-09-17).
- [x] Mirrored the same minimal spike-sorted data set for MS09 — MS09 already
      had an equivalent Kilosort output (`kilosort4_23_49h_mai`) on
      `Z:\Mai\MS09\`, just not yet copied to `Z:\Peleg\MS09\MS09_Spike_Sorted_Data\`.
      Copied the same file set as MS08's (plus MS09's extra `cluster_depth.tsv`),
      verified byte-identical by size. Also ran `training_day_sleep_state_extraction.py`
      for MS09, creating `Z:\Peleg\MS09\MS09_Training_Day\` (2026-09-17).
- [x] Deleted all `StateScoreFigures\` folders (and their `_SWTHChannels.jpg`)
      for MS08, MS09, and MS11 — both the local `diskh2` copies and the one on
      `Z:\Peleg\MS08\MS08_Buzaki_results\`. Peleg confirmed the figure isn't
      useful (it's a coarse, single-session, all-channels-aggregated diagnostic
      that wouldn't have caught the MS09 channel-295 licking-artifact problem
      anyway); `sleep_sanity_check.py` is more diagnostic. Buzcode regenerates
      this figure automatically (best-effort, wrapped in try/catch) on any
      future `SleepScoreMaster` run, so nothing needs to reference it (2026-09-17).
- [x] **Fixed a real bug in the LiCl-injection-time formula** — it was computed
      as 7 minutes after Block 1's *first* tastant, which visibly placed the
      marker in the middle of the still-active taste-delivery block on the
      hourly plots. Peleg caught this by inspecting `Z:\Peleg\MS08\MS08_buzcode_analysis`
      directly. Correct rule (confirmed against `Experiment Protocol and
      Procedure.md`): LiCl is injected ~5 minutes after Block 1's *last*
      tastant. Fixed in `MS_buzcode_analysis.py`'s `ANIMALS` dict for both
      MS08 (t=90888.5s) and MS09 (t=89688.7s); regenerated and re-synced all
      hourly plots for both animals plus both `MS08_Training_Day`/
      `MS09_Training_Day` outputs, which depend on the same value (2026-09-17).
- [x] Consolidated the two MATLAB channel-search/scoring scripts the same way
      `MS_buzcode_analysis.py` was — `find_theta_channel.m` and
      `run_sleep_score.m` each now hold one `ANIMALS`-style struct (MS08/MS09/
      MS11) switched via an `ANIMAL` variable at the top, instead of a
      `_ms08`-suffixed copy per animal. Applies the same
      no-script-duplication standard used for the Python side (2026-09-17).
- [x] Built `SleepAnalysis/sleep_char.py` — sleep-bout-duration
      characterization for a single animal's Training-day cut. Bins sleep
      bouts (continuous NREM+REM stretches, merged across NREM<->REM
      transitions) into 0-2min / 2-5min / 5-10min / >10min (the last bin
      added so no bout is silently dropped from the accounting), and reports
      what % of the day's *total* sleep time fell in each of the 24 clock
      hours (a different question from "% of each hour spent asleep,"
      already covered by the Training-day hypnogram's phase-composition
      plot). Shares the `ANIMALS` config, not a per-animal copy. Run for MS08
      (287 sleep bouts, 61% under 2min, sleep concentrated overnight/
      post-consolidation) and MS09 (237 bouts, similar shape) 2026-09-17.
      Output saved into each animal's own `<animal>_Training_Day\` folder,
      alongside the Training-day extraction it reads.
- [x] **Found and fixed a real corruption bug in the NAS-copy pattern shared
      by `sleep_char.py` and `training_day_sleep_state_extraction.py`** — the
      original pattern (`shutil.copyfile` straight to the destination
      filename, then an immediate `assert` that its size matches) crashing on
      a mismatch appears to race with the gvfs-SMB mount's async write-flush,
      and reproducibly left one destination file (`MS08_sleep_char.png`)
      permanently corrupted server-side, twice in a row — `stat`/`rm`/
      overwrite all failed with `EINVAL` from this machine, recoverable only
      by deleting it from a Windows client directly (Peleg did this both
      times). Root-caused and fixed 2026-09-17: added
      `copy_to_share_safely()` to `MS_buzcode_analysis.py` (copy to a hidden
      temp filename, verify size via a short retry loop instead of an
      instant crash, then an atomic `os.replace` onto the real name) and
      switched both scripts to use it instead of duplicating the fix.
      **Unrelated self-inflicted complication during the same incident:**
      restarting the `gvfsd-smb` process to try to clear the first stuck
      file (assuming a client-cache issue, which was wrong — it was
      server-side) dropped this machine's entire `Z:\Peleg` connection until
      Peleg reconnected it manually. Lesson for next time: ask Peleg to clear
      a stuck file from a Windows client rather than restarting the SMB
      connection process again.
- [x] **Applied and tested MS11's channel-81 theta-channel candidate, then
      reverted — same outcome as MS09.** Copied the 506GB raw `.lf.bin` back
      to local `diskh2` (~3h over SMB at ~45MB/s, `/media/anan/diskh2/MS11/
      MS11_hab3_g0_t0.imec0.lf.bin`), repointed the `.lfp` symlink there, and
      rescored channel 81 at local-NVMe speed (2026-09-18). Result: passed
      the EMG-quiescence check (REM epochs are quiet, not WAKE-like — not an
      obvious movement artifact like MS09's channel 295), but hit the same
      degenerate-threshold failure that sank MS09's alternates — buzcode's
      bimodal-dip test failed *and* its "exclude NREM and retry" fallback
      also failed (channel 65 only fails the first test), so REM ballooned
      to 16.7%/789 bouts (outside the 3-15% typical range) vs. channel 65's
      6.7%/284 bouts (in range). Built `SleepAnalysis/compare_theta_channels.py`
      (reuses `sleep_sanity_check.py`'s loading/checking functions on two
      `.mat` files instead of duplicating them) to produce the side-by-side
      table + stacked hypnogram, saved to `Z:\Peleg\MS11\
      MS11_theta_channel_comparison\`. Peleg's call: revert to channel 65 as
      the trusted baseline (`run_sleep_score.m` updated back to
      `ThetaChannels=[65]`); the channel-81 result set is archived, not
      deleted, at `diskh2/MS11/MS11_hab3/channel81_explored_not_adopted_20260918/`
      and `Z:\Peleg\MS11\MS11_Buzaki_results_ch81\`, in case it's worth
      another look after MS11 gets an independent video-movement trace.
      Also fixed a real bug found along the way in `sleep_sanity_check.py`:
      the REM-plausibility check (section 5) was being skipped *entirely*
      for any animal missing a `video_file`, even though its EMG-only
      cross-check doesn't need video — meant MS11 was never getting that
      check run at all before today.
