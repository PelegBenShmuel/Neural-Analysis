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
| MS11 | `hab3`, ~73h — buzcode scoring is labeled "hab3" but actually spans the full hab3-to-extinction recording, same as MS08/MS09 (corrected 2026-09-22, see below) | `MS_11_Raw_Data\` | `MS11_Buzaki_results\` | `MS11_buzcode_analysis\` (74 plots) |

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
- [x] ~~Reconcile MS11's shorter scored span~~ — resolved 2026-09-22: it
      wasn't shorter. The `SleepState.states.mat` itself already spans the
      full ~73h (confirmed independently via `sleep_sanity_check.py`'s
      73.03h recording-span readout, matching MS08/MS09); only the *session
      label* ("hab3") and the assumption built on it ("no Training day")
      were wrong — see the MS11-Training-day item above for the fix.
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
      far gives it a clean theta split, unlike MS08. MS11's equivalent
      channel-81 test/revert happened later (see "Applied and tested MS11's
      channel-81 theta-channel candidate" below), same outcome, reverted to 65.
      **Resolved 2026-09-22 (Peleg's explicit call): `Z:\Peleg\MS09\MS09_Buzaki_results\`
      (July 5) and `Z:\Peleg\MS11\MS11_Buzaki_results\` (June 24) are
      deliberately left untouched, not re-synced from `diskh2`.** Both predate
      every one of the failed channel experiments above and already hold the
      channel-65 baseline scoring that both animals were ultimately reverted
      back to — Peleg considers these **the most accurate results for MS09
      and MS11**, not stale files needing a refresh. Don't overwrite them with
      a "fresher" `diskh2` copy; this is an intentional exception to the
      general "keep `Z:\Peleg` in sync with `diskh2`" rule, specific to these
      two files.
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

## Data inventory — all rats (as of 2026-09-29)

Goal set 2026-09-24: every rat with a folder in `Z:\Peleg` gets (a) its full
LF band on the **NPdata3** 10TB disk and (b) a `MS_<NN>_Raw_Data\` folder
matching the MS08/MS09/MS11 template. Which physical disk holds each rat's
raw recording is documented in `Z:\Mai\disk_contents.md` (by disk serial).

**`MS_<NN>_Raw_Data\` template** (learned from MS08/MS09/MS11):
`<run>_t0.imec0.lf.bin` + `.lf.meta`; `<run>_tcat.nidq.xd_0_{1,2,3,4}_0[_corr].txt`
(Water / Sucrose / NaCl / CA event times; `_corr` = TPrime-corrected onto the
probe clock); `<run>_tcat.nidq.xd_0_7_0[_corr].txt` (camera-frame sync);
the session `.mp4`; `<animal>_VideoMovement.npy`. Mai's source videos live in
`Z:\Mai\vids\<rat>\`; nidq files in `Z:\Mai\MS<NN>\<run>\`.

**MS16 and MS19 excluded and deleted from `Z:\Peleg` (2026-09-24)** — per
Mai's `track.txt`: MS16 never ran the protocol (head-fixer failures, one
~8.6h session, perfused); MS19's recording was stopped on Training day before
LiCl (bad signal, rat died under anesthesia). MS19's LF copy on NPdata3 was
deleted too; its original raw data is untouched on Mai's disk
WD-WX22A82N3LLN.

| Rat | nidq 1–4 | xd_0_7 | Video (on NPdata3) | VideoMovement (`Z:\Peleg`) | LF on NPdata3 | Training-day window* |
|---|---|---|---|---|---|---|
| MS08 | ✅ | ✅ corr | ✅ | ✅ | ✅ 73.2h | ✅ full |
| MS09 | ✅ | ✅ corr | ✅ `_clean` | ✅ | ✅ 72.9h | ✅ full |
| MS11 | ✅ | uncorrected only | ✅ | ⚠️ night 1 black | ✅ 73.0h | ✅ full |
| MS14 | ✅ | ⚠️ corr truncated → use uncorrected | ✅ `_clean` (repaired) | ✅ | ✅ 72.9h | ✅ full |
| MS15 | ✅ | ✅ corr | — none recorded | — n/a | ✅ 72.7h | ✅ full |
| MS18 (hab3toExt only) | ✅ | ✅ | ✅ | ✅ | ✅ 48.2h | ✅ full |
| MS20 | ✅ | ✅ recreated (see note) | ✅ | ✅ | ✅ 72.3h | ✅ full |
| MS21 | ✅ | ✅ | ✅ | ✅ | ✅ 72.8h | ✅ full |
| MS22 | ✅ | ✅ | ✅ | ✅ | ✅ 72.7h | ✅ full |
| MS23 | ✅ | ✅ | ✅ | ✅ | ✅ 72.8h (from `.lf.cbin`, SHA1-verified) | ✅ full |
| MS24 | ✅ hab3toExt + CTAtoExt | ✅ both | ✅ ×2 | ✅ ×2 (`MS24_hab3toExt_` / `MS24_CTAtoExt_VideoMovement.npy`) | ✅ 18.5h + 48.2h | ⚠️ first 57 min missing |
| MS25 (hab3toExt only) | ✅ | ✅ | ✅ | ✅ | ✅ 40.5h | ✅ full |

\*Peleg's key window (2026-09-29): **09:00 on Training day until 1h after the last
Training-day session ends** (~01:07 next day; 7 sessions, the last ~23:57–00:08).

**Where things live now (final layout, 2026-09-29):**
- **NPdata3** (10TB, serial JEH8AA4N): `MS<NN>\<run>_t0.imec0.lf.bin` + `.lf.meta` +
  the session `.mp4`. Every `lf.bin` checked = `.meta` `fileSizeBytes` (strip the
  CRLF `\r` first) and head/tail-1GiB md5 = source.
- **`Z:\Peleg\MS<NN>\MS_<NN>_Raw_Data\`**: nidq event files, `xd_0_7` sync,
  camera `.csv` where it exists, `<rat>_VideoMovement.npy`. **No videos and no LF
  here any more** — videos were *moved* to NPdata3 (each byte-verified before the
  `Z:\Peleg` copy was deleted, ~370 GB freed). MS08/09/11 still also keep their LF
  in `Z:\Peleg` (they did before this effort).
- **`diskh2`** local backups (keep, per Peleg): `/media/anan/diskh2/MS<NN>_video/`
  (MS18, MS20–MS25; MS24 as `MS24_hab3toExt_video` / `MS24_CTAtoExt_video`),
  `/media/anan/diskh2/MS14/` (repaired MS14 video), `/media/anan/diskh2/MS20_nidq/`
  (MS20 raw nidq.bin used to recreate line 7).
- Out of scope by Peleg's decision: anything after the extinction day (MS18
  `Ext2End_v3`, MS25 `ext2end1`); MS16/MS19 excluded; MS17 never in the protocol
  (moved to Oren's experiment).

Open follow-ups:

- [x] ~~MS18 lf.bin~~ — appeared on disk 72K0A087FWTG on 2026-09-29 (restored there
      after our 2026-09-27 search found only `ap.bin` + `lf.meta`; file date 28/11/2025
      10:00, size = `.meta` `fileSizeBytes`). Copied to NPdata3 and verified the same day.
- [ ] **MS21 LiCl time** — not written in `track.txt`; Block 1 is doubled (47
      sucrose / 24 each other: first session lost balloon pressure, repeated at
      rec 25:08), so the "5 min after Block 1's last tastant" rule gives a wrong
      ~10:59. **Ask Mai** for the real injection time before any MS21 LiCl-aligned
      analysis.
- [ ] **MS22 Hab3 taste delivery** — per `track.txt` the balloon pressure was zero
      and in some Hab3 sessions no taste was delivered, but nidq still logs every
      valve opening (10/block). **Ask Mai** which sessions, or detect from licking
      / GC responses, before using Hab3 responses as a baseline.
- [ ] **MS24 Hab3 night gap** — `hab3toExt` LF holds only 18.5h (its meta says
      24.4h with `fileSizeBytes=0`: recording cut off ~04:00 on 1/7, meta never
      finalised); `CTAtoExt` starts 09:57. So **no LF 1/7 04:00–09:57** (Hab3 night
      and the first 57 min of the Training-day window); video is continuous.
- [ ] **MS25 LF ends at 40.5h** (30/7 02:08) though its video runs 48.1h — the
      key Training-day window is fully covered; only the rest of that night is missing.
- [ ] **MS14 `xd_0_7_0_corr.txt` is truncated** (to 61,844 s of 262,452 s) — use the
      complete uncorrected `xd_0_7_0.txt` (frame k = pulse k for the `_clean` video).
- [ ] **MS11 `xd_0_7_0_corr.txt`** doesn't exist (Mai's TPrime run only did lines
      1–4) — keep using the uncorrected file; could be recreated the same way as
      MS20's if ever needed.
- [ ] **MS11 video is black for most of night 1** — `MS11_VideoMovement.npy` is ~0
      for recording hours 13–21 (frames are black; camera/IR off). Treat as
      *missing*, not rest, in movement-based checks — add a black-frame mask shared
      by all rats. All other rats checked: no black hours.
- [ ] **MS15 has no video** (confirmed by Mai) → movement-based checks use
      EMG-from-LFP only for MS15.
- [x] ~~Next step: buzcode sleep scoring on every rat~~ — **done 2026-09-29 → 2026-10-04,
      see the dedicated "Done in the buzcode-scoring effort" block below** for the full
      per-rat results and the open items it left (MS24_CTAtoExt still being finalized;
      MS15/MS18/MS20 untouched, severe WAKE-collapse, paused by Peleg's own call).

Done in this data-collection effort (2026-09-24 → 2026-09-29):

- [x] **Final check 2026-09-29:** every `lf.bin` on NPdata3 re-checked against its
      `.meta` (all match; MS24 `hab3toExt` meta has `fileSizeBytes=0` by design of the
      04:01 cut-off), every rat's video present (MS15 has none), no partial/temp files
      left; all source disks unmounted.
- [x] LF collected on NPdata3 for all 12 rats, one at a time (parallel copies onto
      the same HDD dropped to ~13 MB/s). MS23's LF was mtscomp-compressed on Mai's
      disk Y190A1K8FWTG → decompressed onto NPdata3 (mtscomp installed privately in
      Claude's scratchpad) and **SHA1 = the original's** stored in Mai's `.lf.ch`.
- [x] Videos moved to NPdata3 for every rat with a video; `Z:\Peleg` copies deleted
      only after a full `cmp`. MS09's broken original stays only at Mai.
- [x] VideoMovement for MS11, MS14, MS18, MS20–MS25 (MS24 as two files), from local
      `diskh2` copies (faster than over the NAS); each output checked for zeros/NaN.
- [x] MS14 video repaired (camera ran 12 days, no `moov`) with
      `SleepAnalysis/repair_mp4_no_moov.py` (SPS/PPS from MS11's same-settings
      video, no re-encode; `-use_editlist 0` so no frames vanish), trimmed to
      6,526,137 frames (72.51h), frame k = sync pulse k.
- [x] MS20 `xd_0_7` recreated from its raw `nidq.bin` (Mai's CatGT skipped line 7);
      see `MS_20_Raw_Data\MS20_xd_0_7_NOTE.txt`.
- [x] MS24 `CTAtoExt` nidq (lines 1–4 + 7, `_corr`) copied into `MS_24_Raw_Data\`;
      MS21/MS22/MS23 camera `.csv` copied.
- [x] MS16/MS19 excluded and their `Z:\Peleg` folders deleted; the shared
      registration atlas moved to `Z:\Peleg\Atlas\` and the MS21 viewer fixed.

Done in the buzcode-scoring effort (2026-09-29 → 2026-10-04) — ran
`find_theta_channel.m` / `run_sleep_score.m` / `sleep_sanity_check.py` /
`MS_buzcode_analysis.py` (all already-shared, `ANIMALS`-config'd scripts,
extended with an entry per rat, not copied) on every rat with raw data ready:

- [x] **MS14, MS18, MS20, MS21, MS22, MS23, MS24 (both segments), MS25**
      scored. Of these, **MS08, MS09, MS11, MS22, MS23, MS24_hab3toExt
      ended up with a genuine, buzcode-validated theta split** (nonzero
      `THthresh`, a real bimodal dip found) — MS22 and MS24_hab3toExt only
      after their first-choice theta channel (found by `find_theta_channel.m`)
      failed and the SW-channel fallback (65) worked instead.
- [x] **Root-caused a real buzcode bug, not just "our channel picks are
      bad"**: `ClusterStates_GetMetrics.m` hard-codes `THthresh=0` whenever
      no bimodal split is found (even after retrying with NREM excluded),
      and the line that would recompute `REMtimes` for that fallback branch
      is commented out in buzcode's own source — so REM silently becomes
      "not moving and low SW power," no theta signal involved at all.
      Affected **7 of 13 rats checked**: MS14, MS15, MS18, MS20, MS21,
      MS23 (before its fix), MS24_CTAtoExt. Added an explicit
      `check_theta_threshold()` to `sleep_sanity_check.py` (now the first
      thing it reports) so this never goes unnoticed again.
- [x] Built **`manual_theta_threshold.m`** (forces a chosen `THthresh` by
      reusing already-computed metrics — seconds, not a 2h+ rescore) and
      **`video_correct_rem.py`** (vetoes any REM timepoint whose independent
      video-movement signal is too high, reclassifying it to WAKE). Standard
      combined method now: theta threshold = that rat's own thratio
      `mean + 1*SD`, then the video correction on top.
- [x] Applied the combined method to **MS14, MS21, MS23, MS25** (MS25 despite
      already having a real automatic threshold — Peleg wanted consistency).
      Result is a real, usable fix for MS23 (REM 6.3%, in range, passes
      every check); for MS14/MS21/MS25 it leaves REM quantitatively flagged
      low/fragmented, which Peleg explicitly accepted anyway over the
      alternatives. **MS09/MS11's pre-existing sparse-REM caveat (probe
      placement) stands unchanged** — not re-touched this round.
- [x] All finalized rats' hypnogram+spectrogram+distribution plots
      (`MS_buzcode_analysis.py` output) synced to each rat's own
      `Z:\Peleg\<rat>\<rat>_buzcode_analysis\` (or `<segment>_buzcode_
      analysis\` for MS24's two segments) — same folder as the sanity-check
      summary PNG, matching the original MS08/09/11 convention.
- [x] **Found 2026-10-04**: `MS24_CTAtoExt` (not `MS24_hab3toExt`) is the
      segment that actually contains the real Training day / LiCl injection
      — its own block 1 (00:17:51 into the segment) is the baseline-IOC
      double-Sucrose block, LiCl at segment-time 1971.24s = wall-clock
      2026-07-01 10:30:02. `MS24_hab3toExt` ends ~04:00 the same morning,
      entirely before the Training day even starts. The Training-day window
      Peleg needs (1.7 09:00 → 2.7 ~01:07) is covered by `MS24_CTAtoExt`
      except the first 57 min (1.7 09:00–09:57, a real gap, in neither
      segment).

Still open from this effort:

- [ ] **MS24_CTAtoExt not yet finalized** — its search-found channel 254
      (mean+1SD+video-corr) gave REM=0.4% *and* a new taste-alignment flag
      (88.2%, worse than every other rat) — something more than just REM
      looked off. Currently re-running with channel 65 instead (the same
      channel that gave a real threshold for MS24_hab3toExt). Once done:
      sanity-check, decide if ch65 is better, apply mean+1SD+video-corr on
      top if still needed, regenerate hypnograms. **This is the segment
      Peleg actually needs**, so worth getting right rather than just
      accepting the first attempt.
- [ ] **MS15, MS18, MS20 untouched** — all three Control/Familiar-group rats
      show a severe WAKE-collapse failure (WAKE drops to ~8-17%, REM
      inflates to ~35-43%), confirmed regardless of theta channel tried.
      Paused by Peleg's own explicit call back when this was found — never
      applied the mean+1SD/video-correction method to these yet. Next big
      piece of unstarted work.
- [ ] A recurring gvfs-SMB mount bug left stuck `??????????` ghost file/
      folder entries several times while overwriting a `<rat>_buzcode_
      analysis` folder in place (MS14, MS21, MS23, MS25) — not fixable from
      this machine, needs Peleg to delete from a Windows client (sometimes
      with a cache-clear delay after). Mitigation: write new output to a
      differently-named temp folder first, verify it, then swap names —
      don't `rm -rf` + `mkdir` + `cp` directly in place.

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

- [x] ~~Port the ad-hoc PSTH/ZETA/ANOVA scratch scripts into a real,
      git-tracked script~~ — done 2026-09-22: `NeuralAnalysis/cluster_responsiveness.py`,
      `ANIMALS`-config-based (imports `ANIMALS`/`TASTE_COLORS`/
      `copy_to_share_safely` from `MS_buzcode_analysis.py` rather than
      redefining them). Fixed two real bugs found while consolidating:
      (1) ZETA silently defaulting to `p=1.0` on too-few-spikes is now
      recorded as `zeta_p=None`/`responsive_zeta=None` instead; (2)
      `copy_to_share_safely`'s `os.replace` doesn't reliably overwrite an
      existing destination over this gvfs-SMB mount (`FileExistsError`) —
      added a remove-then-retry fallback.
- [x] **Found and fixed a wrong assumption: MS11 does have a real Training
      day** — `ANIMALS['MS11']['licl_time_s']` was `None` ("hab-day-only
      recording; no CTA/LiCl event"), based only on buzcode sleep-scoring
      having been done for Hab D3 alone, never checked against MS11's own
      Neuropixels/Kilosort recording. Peleg pushed back on this 2026-09-22
      when it surfaced as a reason MS11 was being skipped; checking the raw
      data directly showed MS11's Block 1 has the same double-Sucrose
      signature as MS08/MS09 (20 vs. 10, at t=88694.3-89292.2s) — a real
      Training day, just never organized/scored as one. Fixed: `licl_time_s`
      set (89592.2s, same 5-min-after-Block-1 rule), spike-sorted data
      mirrored to `Z:\Peleg\MS11\MS11_Spike_Sorted_Data\` (same minimal set
      as MS08/MS09) and taste-event files upgraded to the `_corr` (TPrime-
      corrected) versions in `Z:\Peleg\MS11\MS_11_Raw_Data\` (previously only
      uncorrected copies existed there). **Follow-up closed 2026-09-22**: ran
      `training_day_sleep_state_extraction.py MS11` and `sleep_char.py MS11`
      — `Z:\Peleg\MS11\MS11_Training_Day\` now exists, matching MS08/MS09's
      structure exactly. MS11's Training day: 50.1% asleep over the 24h
      window, REM rises from 5.9% pre-injection to a 6-12h Consolidation
      peak of 10.0% (25 REM bouts) — same qualitative post-LiCl REM-increase
      shape as MS08/MS09, on the (reverted-to-original) channel 65 scoring.
- [ ] **Curation-quality difference found across animals, worth checking
      with Mai/Anan**: MS08's `cluster_group.tsv` was manually curated from
      245 raw Kilosort clusters down to 41 "good" units (100% of survivors).
      MS09 (537 raw -> 225 survivors, 224 "good") and MS11 (256 "good" out of
      257) show a much blunter cut -- most of what survives an initial prune
      gets labeled "good" without MS08's apparent per-unit scrutiny. Numbers
      from `cluster_responsiveness.py` runs on MS09/MS11 should be treated
      with more caution than MS08's until this is confirmed one way or the
      other.
      `sleep_char.py` already use) — right now this analysis exists only as a
      sequence of one-off scratchpad scripts (`step1_explore.py` through
      `step11_make_xlsx.py`, in Claude's session scratchpad, not the repo).
      That's a real gap relative to this project's no-per-animal-duplication
      norm; needed before running it on MS09 or re-running it on MS08.

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
- [x] **Built a from-scratch PSTH + taste-responsiveness pipeline for MS08's
      Training day, using only raw spike-sorter output** — deliberately not
      Mai's derived analysis tables (`kilosort4_23_49h_mai/analysis/`), per
      Peleg's request to understand/own the method rather than consume her
      results. Built incrementally through this session (2026-09-16 to
      2026-09-22):
      - **PSTH construction** from raw `spike_times.npy` + `spike_clusters.npy`
        (Kilosort4, Phy-curated) + `cluster_group.tsv` (`good` units only) +
        the true AP-band sample rate from `*.imec0.ap.meta`'s `imSampRate`
        (~29999.56 Hz, not nominal 30000) + the raw TPrime-corrected
        taste-event `_corr.txt` files. Block boundaries (7 Training-day
        blocks) re-derived independently via gap-detection on the raw event
        timestamps, not copied from Mai's `blocks_by_day_*.json` — cross-
        validated as matching.
      - **Two independent responsiveness tests**, run per (cluster x taste x
        block), so results can be cross-checked against each other rather
        than trusted from one method alone:
        - **ZETA test** (`zetapy`, Montijn et al. 2021 — same package Mai
          already uses) — parameter-free, no bin-size choice, most sensitive
          to a real but temporally localized/jittery response.
        - **Repeated-measures ANOVA** (`statsmodels.stats.anova.AnovaRM`,
          main effect of 250ms time-bin, Piette et al. 2012-style binning) —
          same statistical family already used in this project's own
          literature (Piette 2012, Arieli 2022).
        - Across all 41 good units x 4 tastes x 7 blocks (1148 tests, pooled-
          taste rows since removed per Peleg's request): the two tests agree
          85% of the time (25.5% both-responsive, 59.5% both-not; 15%
          disagree) — a reasonable cross-check, not perfect concordance.
      - **Real finding worth following up (single-neuron, not yet
        generalized)**: cluster 19's Sucrose responsiveness (ZETA) was
        significant pre-LiCl (Block 1), lost in Blocks 2-3 (immediately
        post-LiCl), and regained from Block 4 onward — a responsive-to-non-
        responsive-to-responsive trajectory across the LiCl-pairing moment,
        for the one taste most directly relevant to CTA. NaCl showed close
        to the reverse (silent early, responsive from Block 4 on). Needs
        checking across more units before treating as a real population
        effect.
      - **Known limitation**: ZETA fails (defaults to `p=1.0`, not a real
        null result) when a unit has too few spikes in the test window —
        hit this in 198/1435 tests (mostly very low-firing-rate units, e.g.
        cluster 109 at 0.07 Hz overall). Don't read `responsive=False` at
        face value for a low-firing-rate unit without checking its overall
        rate first.
      - **Output**, all 41 good units, saved to
        `Z:\Peleg\MS08\Cluster_analysis\cluster_<ID>\`: 7 per-block PSTH
        PNGs (raster + PSTH, colored by taste) + one
        `cluster<ID>_responsiveness_by_taste_and_block.csv` (block x taste x
        n_trials x zeta_p/responsive_zeta x anova_p/responsive_anova) + a
        matching `.xlsx` with each block's rows shaded a distinct background
        color for fast visual scanning.
      - See the two "Ready to start" follow-ups above (extend to MS09;
        port scratch scripts into a real repo script) for what's left.
- [x] **Added per-hour sleep amount (minutes) and a 24h total to
      `sleep_char.py`** — it previously only reported each hour's % of the
      day's total sleep, with no absolute amount and no running total.
      Added a printed table + a `Total` row in `<animal>_hourly_sleep_pct.csv`,
      and switched the hourly plot panel from "% of total sleep" to "minutes
      asleep" (with a 60min reference line and the 24h total in the panel
      title). Regenerated and re-synced for MS08 (11.83h/24h total), MS09
      (10.82h/24h), and MS11 (12.02h/24h) (2026-09-22).
- [x] **Data-collection day (2026-09-24)** — learned the lab's hot-swap
      disk procedure (`sudo labdisk mount/umount`, see README "Data
      locations"); located every rat's raw disk via `Z:\Mai\disk_contents.md`;
      copied matching `lf.meta` files for MS08/MS09/MS11/MS14 and the full
      MS24 hab3toExt `lf.bin`+`meta` (from `diskh2`) onto NPdata3; audited
      every `MS_<NN>_Raw_Data\` against the MS08/MS09/MS11 template (table in
      "Data inventory — all rats" above); excluded and deleted MS16/MS19;
      moved the shared registration atlas to `Z:\Peleg\Atlas\` and fixed the
      MS21 viewer.
