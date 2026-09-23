#!/usr/bin/env python3
"""
Parse an ITK-SNAP-format .label file (e.g. WHS_SD_rat_atlas_v4.01.label)
into a plain CSV of {id, name}, and report any structure whose name looks
gustatory-cortex-related.

ITK-SNAP label file lines look like:
    IDX   -R-  -G-  -B-  -A-  VIS MSH  "LABEL"
Comment lines start with '#'.
"""
import sys
import csv
import re

def parse(label_path):
    rows = []
    with open(label_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^(-?\d+)\s+\d+\s+\d+\s+\d+\s+[\d.]+\s+\d+\s+\d+\s+\"(.*)\"", line)
            if m:
                idx, name = m.group(1), m.group(2)
                rows.append({"id": int(idx), "name": name})
    return rows

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: parse_whs_labels.py path/to/WHS_SD_rat_atlas_v4.01.label")
        sys.exit(1)
    rows = parse(sys.argv[1])
    out_csv = "whs_v4_labels.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "name"])
        w.writeheader()
        w.writerows(rows)
    print(f"parsed {len(rows)} labels -> {out_csv}")

    print("\nlikely gustatory-cortex-related matches:")
    hits = [r for r in rows if re.search(r"gustatory|GC\b|insular|piriform", r["name"], re.I)]
    for h in hits:
        print(f"  id={h['id']:>4}  {h['name']}")
    if not hits:
        print("  (none found by keyword — will need to scan the full list manually)")
