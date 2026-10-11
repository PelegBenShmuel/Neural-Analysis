# PRA atlas registration status (electrode/dye-track verification)

Goal: for each animal, register the cleared, light-sheet-imaged, dye-labeled
brain to the Princeton RAtlas (PRA) common coordinate framework (Dennis et
al. 2023, `Articles/Princeton RAtlas...pdf`), then look up which atlas region
the dye track lands in, to confirm claimed electrode placement (e.g. GC).

## UPDATE (2026-10-06): MS24 and MS25 registered

Source CTLS data for both was on the NAS at `Z:\Peleg\CTLS-MS24-25\`
(`24b.dir\...Pos34...MontageComplete...` / `25.dir\...Pos35...MontageComplete...`)
— a different location than MS19/21/23's `Z:\Mai\CTLS\`, since Peleg copied
these himself this time. Same imaging setup as before (561nm single
channel, `mMicronPerPixel=6.4039412`, `optovar=3.25` → same
`SRC_XY_UM=1.9704434461538463` constant reused).

**New finding: this session's mounting needed a different axis
*permutation*, not just different flip signs.** Every prior animal
(MS19/21/23) used `transpose(1,2,0)` and only varied in which axes got
flipped. For MS24 and MS25, that transpose produced an axis arrangement that
didn't match the atlas's convention at all (checked by comparing which
axis, when held fixed, produces a coronal-vs-sagittal-vs-horizontal-looking
slice — see `qc_explore/baseline_vs_pra.png` in each animal's tnvme folder)
— both needed `transpose(2,1,0)` instead. This makes sense once you know
to look for it (a sample can physically be mounted rotated 90° differently
session to session) but is a real escalation of the existing
"don't assume orientation carries over" rule from flip-signs to the
permutation itself — **check the permutation too for any future animal**,
don't just assume `transpose(1,2,0)` and start testing flips.

**SUPERSEDED (see UPDATE 2026-10-08 below) — kept for the historical record:**
~~Per-animal orientation found (both via the established
visual-AP-check-then-registration-based-disambiguation method):~~
- ~~**MS24**: no AP flip ... **DV-flip won** (Dice 0.81 vs ML-flip's 0.79)~~
  — wrong, this was candB, see below.
- ~~**MS25**: cerebellum was at the *wrong* end ... AP flip *was* needed ...
  no additional ML/DV flip~~ — wrong, this was AP-only, see below.

Both per-animal single-flip calls above turned out to be incomplete: each
looked plausible in isolation (reasonable Dice, not visually garbled) but
was wrong on exactly one axis when checked carefully — this single-slice +
coarse-Dice method is **not reliable enough** for this bilaterally-symmetric,
near-180°-rotation-prone orientation problem. See the 2026-10-08 update.

## UPDATE (2026-10-08): both MS24 and MS25 actually need AP+DV flip together

Peleg kept reporting the registered brain looked wrong in napari after each
"fix" — first "upside down", then "MS24 and MS25 facing different
directions relative to each other", then specifically "DV axis doesn't
match" even after supposedly orientation-correct candidates. Each time,
Claude's own checks (Dice, NCC against atlas, static slice renders, even a
multi-slice coronal scan) said the result looked fine, and each time Peleg
was right and Claude was wrong — **see
[[feedback_registration_qc_verification]]: Peleg's direct napari inspection
is the actual verification step, not Claude's own metrics.**

What actually happened, worked out by testing every one of the 8 possible
`transpose(2,1,0)`-based orientation candidates (naming: A=ML-flip only,
B=DV-flip only, C=AP-flip only, D=AP+DV together, E=all three together):

- candA, candB, candC (the 3 single-axis flips): each completes registration
  without crashing and isn't visually garbled, so each *looked* like a
  plausible candidate in isolation — but each has exactly one axis visibly
  wrong against the atlas when Peleg checked closely (candB: AP wrong;
  candC: DV wrong, confirmed "only DV axis, not ML" by Peleg directly).
- **candD (AP+DV together) is the actually-correct one for both animals.**
  Running it from a cold start (rigid+affine+bspline all at once) crashes
  immediately for MS24 ("Too many samples map outside moving image buffer:
  0/10000" partway through the affine stage) but runs cleanly end-to-end for
  MS25 — same orientation math, different numerical behavior per animal.
- candE (all three axes flipped) was also tried for MS24 as a hedge in case
  ML was secretly wrong too — crashes the same way as candD. Peleg confirmed
  directly that ML is fine, only DV — so candD (not E) is the real target.
- **Root cause of MS24's candD crash, isolated**: splitting candD's
  registration into stages showed rigid (EulerTransform, 8 resolutions) and
  affine (general 12-param matrix, 8 resolutions) **both complete with
  sane, non-degenerate parameters** — it's specifically the **Order3 bspline
  stage** that diverges to 0 valid samples right at its first resolution.
  This is a bspline step-size/stability issue, not an orientation/chirality
  problem — confirmed by resampling the moving image through *just* the
  saved rigid+affine transform (bypassing the crashing bspline) via
  `itk.transformix_filter`, which Peleg confirmed looks globally correctly
  oriented even though it's coarse (no fine deformation yet).

**Current state:**
- **MS25**: candD ran all the way through Order1→Order3→Order4→Order5
  successfully. Confirmed correct by Peleg. Final:
  `Z:\Peleg\MS25\MS25_Registration\registration_output_order5_candD\result_Order5.tif`.
  `view_ms25_registration.py` (repo + NAS `view_registration_windows.py`)
  already updated to point here, no cosmetic flip needed.
- **MS24**: candD's rigid+affine stages are confirmed correct, but there is
  **no finished fine-registration result yet** — Order3 bspline keeps
  crashing. Interim rigid+affine-only result (coarse, no local deformation):
  `Z:\Peleg\MS24\MS24_Registration\candD_rigidaffine_only\result.tif`. Local
  working files: `/mnt/tnvme/peleg_MS24_registration/` —
  `MS24_25um_oriented_candD.tif` (the correct input orientation),
  `registration_output_rigidcandD/TransformParameters.1.txt` (the valid
  saved rigid+affine transform to chain Order3 from).
  **Next step when resuming:** get a stable Order3 bspline run for candD —
  try a gentler initial step length or a coarser starting bspline grid
  (rather than retrying the exact Order3 params that already crashed twice),
  chained from that saved affine transform, then Order4/Order5 as usual.
- candA/candB/candC/candE and all their order4/order5 variants are kept on
  disk as dead ends, not used.

**Real bug found and fixed in the stage-1 (Order1+Order3) scripts
(`run_stage1_candidate.py` / `run_stage1.py`):** running Order1 and Order3
as two separate `itk.ElastixRegistrationMethod.Update()` calls into the
*same* output directory silently corrupts the chain — the second stage's
`TransformParameters.0.txt` overwrites the first's, and since elastix
records the init transform's *path* (not its content) in
`InitialTransformParameterFileName`, the saved file ends up pointing to
itself. The already-computed result images were still valid (Dice scores
computed from them hold up), but the saved transform can't be correctly
chained into order4/order5 afterward. **Fixed by matching the original,
proven pattern** (`elastix_mv_to_fx.py`'s approach): one `ParameterObject`
with *both* parameter files added via `AddParameterFile`, one single
`itk.elastix_registration_method(...)` call — elastix then manages the
two stages' indexing (`.0.txt`, `.1.txt`) correctly internally. Reusable
template: `PRA/src/stage1_combined_template.py`. **If writing a new
multi-stage registration script, always use one call with a combined
parameter object (or at minimum, separate output directories per stage)
— never two separate `Update()` calls sharing one output folder.**

Final Dice (order5, vs. atlas mask) for the superseded candB/AP-only
results: MS24 = 0.815, MS25 = 0.807 — **these numbers are stale**, computed
on the wrong-orientation candidates (see 2026-10-08 update above). Not yet
recomputed for MS25's candD (the confirmed-correct one) or for MS24 once it
has a finished bspline result.

Copied to NAS: MS25's candD result at
`Z:\Peleg\MS25\MS25_Registration\registration_output_order5_candD\result_Order5.tif`;
MS24 only has the interim rigid+affine-only candD result at
`Z:\Peleg\MS24\MS24_Registration\candD_rigidaffine_only\result.tif` (see
2026-10-08 update above for why). Viewer scripts:
`Registration/view_ms24_registration.py` / `view_ms25_registration.py`,
same pattern as MS21's (standalone, hardcoded, shared atlas from
`Z:\Peleg\Atlas\`), synced to each animal's own NAS folder as
`view_registration_windows.py` — MS25's already points at the candD result;
MS24's still points at the old candC path and needs updating once a
finished candD result exists.

**Not yet done:** MS23 still has no NAS viewer package at all (same
`/mnt/tnvme/peleg_MS23_registration/` pipeline output as the others, never
copied over) — lowest priority since nobody's asked for it recently, but
same quick recipe as MS24/25 above whenever needed.

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
- `Atlas\` — the shared, animal-independent atlas copy (PRA.tif,
  PRA_WHS_v4_anns.tif, whs_v4_labels.csv), used by the viewer scripts.
  Created 2026-09-24 from `/mnt/tnvme/peleg_MS19_registration/atlas/`.
- `MS19\` — **deleted 2026-09-24** (MS19 excluded from the study), including
  its registration package and the atlas copy that used to live there.
  The local working dir on `/mnt/tnvme/peleg_MS19_registration/` is untouched.
- `MS21\MS21_Registration\MS21_Registartion_data\` — MS21's own `result_Order5.tif` + synced copy of
  `view_ms21_registration.py` (atlas from `Z:\Peleg\Atlas\`).
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
`Z:\Peleg\Atlas\` for the viewer scripts).

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

**Windows security quirk found:** `viewer.add_labels(...)` can fail with
`ImportError: DLL load failed while importing conversion: An Application
Control policy has blocked this file` — napari's Labels layer transitively
imports pandas, and Windows 11's **Smart App Control** (Settings → Windows
Security → App & browser control) blocked one of pandas's compiled `.pyd`
files on Peleg's machine. `viewer.add_image`/`tifffile` alone never hit this
(no pandas import needed) — only `add_labels` did. Fixed via Windows
Security → **Protection history** → find the blocked-file event → allow it
for this device, rather than disabling Smart App Control entirely (which
Microsoft only lets you turn back on via a clean Windows reinstall — a much
worse trade for a one-file problem). If this recurs on a different Windows
machine, check Protection history first.

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

## Gotcha: array size ≠ physical brain size

Came up when Peleg asked how many mm separate consecutive slices in napari's
horizontal view. The voxel size answer is simple and reliable: **25 µm
(0.025 mm) between any two adjacent slices, in all three anatomical planes**
— both the atlas and every animal's registered volume were deliberately
resampled to 25 µm *isotropic* resolution (same in X/Y/Z), confirmed both by
the PRA paper's own abstract ("25 μm resolution") and by the downsampling
logs' achieved voxel size. Since it's isotropic, this holds regardless of
which of the three planes (sagittal/coronal/horizontal) you're scrolling.

**But total-slice-count × 0.025 mm is *not* the brain's physical size** —
the array is a padded bounding box, not a tight crop around the tissue.
Checked this directly on `PRA.tif` (shape `618×1150×355`): naively
multiplying the full 1150-slice AP axis by 25 µm gives 28.75 mm, but the
actual non-background tissue only spans slices ~200–1149 (~950 slices ≈
23.8 mm) — confirmed anatomically plausible via an independent volume
cross-check (ellipsoid approximation using the atlas's own measured AP ×
ML × DV extents ≈ 1600 mm³, close to the ~1765 mm³ published average adult
rat brain volume; a genuinely larger AP extent would overshoot that badly).
**Always measure where real tissue starts/ends (threshold out background)
before converting a slice range to a physical distance** — don't just use
the full array dimension.

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
