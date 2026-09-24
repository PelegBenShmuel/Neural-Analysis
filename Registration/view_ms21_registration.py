"""
View MS21's PRA-registered brain + atlas + GC-candidate region labels in
napari, running locally on Windows against the NAS share directly (no SSH,
no remote desktop, no X11 forwarding needed).

Run standalone (python view_ms21_registration.py), or paste the body below
the imports into napari's built-in console if napari is already open.
"""
import sys

# This napari env has numexpr/bottleneck built against an older NumPy, which
# hard-crashes on import under this env's NumPy version. Both are optional
# pandas accelerators (pulled in transitively by napari's Labels layer) --
# pretending they're absent makes pandas skip them gracefully instead of
# raising. Must happen before napari (and therefore pandas) is imported.
sys.modules["numexpr"] = None
sys.modules["bottleneck"] = None

import csv
import numpy as np
import tifffile as tf
import napari

BASE = r"Z:\Peleg\MS21\MS21_Registration\MS21_Registartion_data"
# Atlas is animal-independent -- kept in one shared place rather than
# duplicated per animal (was under MS19's folder until MS19 was excluded).
ATLAS_BASE = r"Z:\Peleg\Atlas"

print("Loading volumes...", flush=True)
registered = tf.imread(BASE + r"\registration_output_order5\result_Order5.tif")
atlas = tf.imread(ATLAS_BASE + r"\PRA.tif")

# tf.imread() fails on this one specific file over a mapped network drive
# with "OSError: [Errno 22] Invalid argument" -- Windows doesn't like a
# single huge read() over SMB for a file this size. tf.memmap() reads it in
# OS-page-sized chunks instead, which works fine.
labels = np.asarray(tf.memmap(ATLAS_BASE + r"\PRA_WHS_v4_anns.tif")).astype("int32")
print("Loaded:", registered.shape, atlas.shape, flush=True)

id_to_name = {}
with open(ATLAS_BASE + r"\whs_v4_labels.csv", newline="") as f:
    for row in csv.DictReader(f):
        id_to_name[int(row["id"])] = row["name"]

# Percentile-based contrast, NOT .max() -- both volumes have a hot-pixel
# outlier at 65535 that crushes the real signal to black if used directly.
atlas_hi = np.percentile(atlas, 99.9)
reg_hi = np.percentile(registered, 99.9)

viewer = napari.Viewer(title="MS21 registration QC - result_Order5 vs PRA atlas")
viewer.add_image(
    atlas, name="PRA atlas", colormap="green",
    blending="additive", contrast_limits=(0, atlas_hi),
)
viewer.add_image(
    registered, name="MS21 registered", colormap="magenta",
    blending="additive", contrast_limits=(0, reg_hi),
)
viewer.add_labels(labels, name="PRA region labels (all)", visible=False)

# Rat gustatory cortex isn't a separately-named structure in this atlas --
# anatomically it's the granular/dysgranular insular cortex.
keep_ids = [409, 410, 414, 416, 424]
filtered = np.where(np.isin(labels, keep_ids), labels, 0).astype(labels.dtype)
viewer.add_labels(filtered, name="Insular cortex (G/AG/DG) - GC candidates", visible=True)

print("\nGC candidate regions:")
for i in keep_ids:
    print(f"  id={i}: {id_to_name.get(i)}")

if __name__ == "__main__":
    napari.run()
