# PRA atlas registration status (electrode/dye-track verification)

Goal: for each animal, register the cleared, light-sheet-imaged, dye-labeled
brain to the Princeton RAtlas (PRA) common coordinate framework (Dennis et
al. 2023, `Articles/Princeton RAtlas...pdf`), then look up which atlas region
the dye track lands in, to confirm claimed electrode placement (e.g. GC).

## Where things live

**The registration pipeline itself is not in this git repo** — it runs on
local fast storage on the Linux server (`anan-beast`), not synced anywhere
else yet:
- `/mnt/tnvme/peleg_MS19_registration/`
- `/mnt/tnvme/peleg_MS21_registration/`
- `/mnt/tnvme/peleg_MS23_registration/`

This work already existed before the 2026-09-23 session that produced this
file (dated 2026-08-25 to 2026-08-31) — it wasn't captured in memory, so it
was rediscovered from scratch. If starting fresh on this again, point at
`/mnt/tnvme/peleg_*_registration/` first rather than re-cloning/re-running.

Source light-sheet images are on `Z:\Mai\CTLS`. The PRA GitHub repo
(`github.com/emilyjanedennis/PRA`) is cloned once, shared by all three
animals, at `peleg_MS19_registration/PRA/`. The atlas volumes (`PRA.tif`,
`PRA_WHS_v4_anns.tif` — Waxholm Space v4 annotations) live in
`peleg_MS19_registration/atlas/` and are likewise shared.

**This repo** (`Registration/`) holds:
- `view_ms19_registration.py`, `view_ms21_registration.py` — standalone
  napari viewer scripts, meant to be run **on Peleg's own Windows machine**
  against the mapped NAS drive (see "Viewing the results" below).
- `atlas_labels/parse_whs_labels.py`, `atlas_labels/whs_v4_labels.csv` — the
  WHS v4 atlas's region ID → name table (see "Atlas region labels" below).

**On the NAS** (`Z:\Peleg\`, i.e. `smb://anannas/data/Peleg`):
- `MS19\final_MS_19 Registration\` — MS19's full package: `result_Order5.tif`,
  `atlas\` (PRA.tif, PRA_WHS_v4_anns.tif, whs_v4_labels.csv — the shared
  atlas copy, kept here rather than duplicated per animal), and
  `view_registration_windows.py` (synced copy of this repo's
  `view_ms19_registration.py`).
- `MS21\MS21_Registration\` — same idea for MS21 (its own `result_Order5.tif`
  + synced copy of `view_ms21_registration.py`; reuses MS19's atlas folder).
- `WHS_SD_rat_atlas_v4_pack.zip` — sitting at the top of `Z:\Peleg\`,
  contains the official WHS v4 label file (see below).

## Pipeline as built (per animal)

1. Downsample raw light-sheet channel to 25 µm isotropic (`downsample_ms*.py`)
   → `MS##_25um.tif`.
2. Manually re-orient to roughly match the atlas's axis convention
   (`orient_and_qc*.py`): a fixed `transpose(1,2,0)`, then flip AP and DV.
   The ML (left/right) flip was decided via a masked normalized-cross-
   correlation score on a single mid-slice — the winning orientation won by
   only a 3.1% margin (see "orientation was fine" below — this thin margin
   turned out not to matter). → `MS##_25um_oriented.tif`.
3. Register oriented volume to `atlas/PRA.tif` via elastix, chained through
   4 stages using the PRA repo's own parameter files
   (`PRA/parameter_folder/Order{1,3,4,5}_*.txt`): Order1 affine (Mattes MI,
   AdaptiveStochasticGradientDescent, 8-level pyramid) → Order3/4/5
   progressively finer bspline refinement, each initialized from the
   previous stage's `TransformParameters` via elastix's own
   `SetInitialTransformParameterFileName` (confirmed correct — not a
   transform-chaining bug).
4. Final result: `registration_output_order5/result_Order5.tif`, resampled
   onto the atlas's exact voxel grid (confirmed: shape matches `PRA.tif`
   exactly, `(618, 1150, 355)`, for all three animals).

Known cosmetic bug (not blocking, not fixed): `PRA/src/elastix_mv_to_fx.py`
crashes on `tif.imsave(...)` because installed `tifffile` (2025.5.10, in
`peleg_env`) removed the `imsave` alias in favor of `imwrite`. Only affects
an intermediate stage-1 QC save — the order1/order3 transform parameters are
computed and written before the crash, so the pipeline continued past it
unaffected. One-line fix if needed: `tif.imsave(...)` → `tif.imwrite(...)`.

## Registration quality: workable, not perfect (resolved 2026-09-23)

First pass at QC (comparing `qc_final/final_axis{0,1,2}_*.png` across all
three animals) looked alarming: the registered brain sits at a visible tilt
relative to the atlas in every view. Chased this as a bug for a while
(tested whether the thin 3.1%-margin orientation flip was wrong, tested
whether registering with true ~25 µm spacing instead of the default
`(1,1,1)` metadata changed anything) — both dead ends. **The tilt is a false
alarm**, not a bug:

- A correctly-rotated volume, resampled onto the atlas's grid and displayed
  against a black background, naturally looks like a tilted rectangle — that
  visual is just what a legitimate rotation correction looks like on screen.
- Confirmed the rotation is real and correctly applied: an independent
  **rigid-only** (rotation+translation, no scale/shear) pre-alignment found
  almost the same ~20° rotation the full affine stage found. Two
  different-DOF methods landing on the same rotation is evidence it's a real
  correction, not a bug in either one.
- Measured properly instead of eyeballing: **Dice overlap of whole-brain
  masks** (foreground > 60th percentile) against the atlas mask — rigid-only
  0.76 → affine-only 0.83 → full pipeline (order5) 0.84. Each stage
  genuinely improves overlap, and 0.84 is a solid score for whole-brain
  registration.

**Bottom line: the existing MS19/MS21/MS23 registrations are workable.** Not
perfect — 0.84 Dice leaves real room for error at fine region boundaries, so
a claim like "exactly GC, not the adjacent insular cortex" still deserves a
sanity check (does the dye track's estimated location sit solidly inside a
region's boundary, or right at the edge?) — but there's no evidence of a
pipeline bug needing a fix before moving on.

Exploratory dead-end files kept for the record in
`/mnt/tnvme/peleg_MS19_registration/`: `MS19_25um_oriented_v2.tif`,
`reorient_ms19_v2.py`, `qc_reorient_v2/` (an attempt to re-derive the
orientation more rigorously — made things worse, not better, since the
original AP/DV flip was already correct and a full-volume correlation
metric is too weak a signal for a near-bilaterally-symmetric rat brain to
improve on it), `test_rigid_prealign.py`, `test_spacing_fix.py`.

## Atlas region labels obtained

The WHS v4 annotation volume (`PRA_WHS_v4_anns.tif`) has no bundled
ID → region-name table in the PRA GitHub repo (an oversight there — the
notebooks that would build one reference a file only on the original
author's own Desktop). The official table lives on NITRC behind a manual
license click-through a bot can't do — but it turned out to already be
sitting on the NAS: `Z:\Peleg\WHS_SD_rat_atlas_v4_pack.zip` contains
`WHS_SD_rat_atlas_v4.label`. Parsed via
`Registration/atlas_labels/parse_whs_labels.py` into
`Registration/atlas_labels/whs_v4_labels.csv` (223 labels; also copied to
`Z:\Peleg\MS19\final_MS_19 Registration\atlas\` for the viewer scripts).

**Rat GC is not a separately-named structure in this atlas** — anatomically
it corresponds to the granular/dysgranular insular cortex. Candidate region
IDs (by keyword search — confirm anatomically before treating as ground
truth):
- **416 — Granular insular cortex** (strongest GC candidate)
- **414 — Dysgranular insular cortex** (strongest GC candidate)
- 409 / 410 / 424 — Agranular insular cortex (ventral / dorsal / posterior)

Both viewer scripts (below) load a Labels layer filtered down to just these
five IDs, so the dye track's overlap with them is easy to see directly.

## Viewing the results: run locally on Windows, not through Claude Code

Peleg's Claude Code runs on the Linux server via VSCode Remote-SSH from his
own separate Windows machine, so nothing launched by Claude can display on
his screen. Spent a long time chasing remote-display options before landing
on the actual answer:

- **X11 forwarding (VcXsrv + SSH config + VSCode's "Enable X11 Forwarding"
  setting): didn't work.** Confirmed at the socket level that VSCode's
  Remote-SSH extension simply never requested X11 forwarding on the
  connection (no forwarded socket, no xauth cookie), regardless of client
  config. A stale multi-day-old `.vscode-server` background process also
  meant early "reconnects" weren't actually restarting anything.
- **The machine's xrdp remote-desktop sessions can't use the GPU either** —
  confirmed via the Xorg log: `systemd-logind: failed to take device
  /dev/dri/card{0,1}: Operation not permitted`. An RTX 4090 sits unused;
  fixing this needs VirtualGL (not installed) and root access.
- **Actual solution: skip remote display entirely.** Copy the handful of
  needed files to the NAS (already mostly there from the August work) and
  have Peleg run napari directly on his own Windows machine against the
  mapped drive (`Z:` → `\\192.168.100.2\data`) — no SSH, no remote desktop,
  no GPU forwarding, uses his machine's own real GPU. This mirrors what an
  August Claude Code session had already worked out once before (found
  `OPEN_REGISTRATION_INSTRUCTIONS.md` on the NAS, written for "Claude Code
  on another machine" — its atlas files had just never actually been copied
  over, and its paths were stale).
- Napari installed via the official bundled Windows app (no separate Python
  needed) — https://github.com/napari/napari/releases. Scripts are run by
  pasting their body into napari's built-in console (bottom-left `>_`
  icon), since that avoids needing a separate Python install to run a
  `.py` file directly.

**Windows/SMB quirk found:** `tifffile.imread()` fails on
`PRA_WHS_v4_anns.tif` (~1GB) read over the mapped drive, with `OSError:
[Errno 22] Invalid argument` — Windows doesn't like one huge `read()` over
SMB for a file this size. `tifffile.memmap()` works fine (reads in
OS-page-sized chunks instead). `PRA.tif` and `result_Order5.tif` (similar
size) load fine via plain `imread()`, so this seems specific to this one
file/size combination — if it recurs for other animals, reach for
`memmap()` first rather than re-debugging from scratch. Both viewer scripts
already use `memmap()` for this file.

**Scripts are deliberately separate per animal, not a shared config-dict
abstraction** — built the dict version first, but Peleg explicitly asked
for two clean standalone hardcoded scripts instead ("each one a clean path,
don't dress it up"); see [[feedback_no_script_duplication]] for the noted
exception to the usual generalize-don't-duplicate default.

## Dye-track length: browser tool built (native-space, not atlas-warped)

Separately from the napari/atlas-region work: Peleg noticed the electrode
length he measures in the atlas-registered image (`result_Order5.tif`)
doesn't match the real surgical insertion length. Expected — that image has
been non-uniformly warped to match the atlas, so it does not preserve the
animal's own true physical distances. Built a browser tool (published as a
Claude.ai Artifact, "Dye Track Ruler") that instead works in MS19's own
native, un-warped 25 µm image (`MS19_25um_oriented.tif`), with three
switchable anatomical planes (sagittal/coronal/horizontal) built from
cropped/sprite-sheet slices of the region around the two bright dye
clusters found automatically (connected-component threshold at intensity
>5000): one cluster near the cortical surface (likely entry point) and one
deeper (likely tip), consistent with a single track where dye labeled the
entry and tip brightly but not the shank in between. Click two points in
any view (or across views — they resolve to one consistent 3D position) and
it computes the true 3D distance in mm live. Not yet compared against the
real surgical measurement — Peleg said to set that comparison aside for now
in favor of the napari/region-lookup approach, so the tool is built but the
actual length discrepancy is still open.

## Current status / not yet done

- Napari is set up locally on Peleg's Windows machine with MS19 (and now
  MS21) registered brain + atlas + full region labels + the GC-candidate-
  filtered label layer all loading correctly.
- **Not done yet: actually reading off where the dye track sits relative to
  the GC-candidate regions (416/414 etc.) and drawing a conclusion.** This
  is the actual point of the whole pipeline and hasn't happened yet — next
  session should pick up here.
- MS23 has the same `/mnt/tnvme/peleg_MS23_registration/` pipeline output as
  MS19/MS21 but has not yet gotten a NAS viewer package or a
  `view_ms23_registration.py` script — same recipe as MS21 (copy
  `result_Order5.tif` to a NAS folder, write the third hardcoded script)
  whenever Peleg wants to look at it.
- The dye-track native-space length (via the browser Ruler tool) vs. the
  real surgical measurement discrepancy is still open — set aside, not
  resolved.

## Output location note

Per [[feedback_output_location]], analysis outputs should also be copied to
`Z:\Peleg`. The core pipeline outputs are already there for MS19/MS21 as
described above; MS23 and the exploratory dead-end files on `tnvme` are not.
