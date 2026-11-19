"""
How much sleep was actually in each rat's qualifying sleep window, and how
many windows did it get -- Peleg's question, 2026-11-19. **Block-independent**
(his explicit correction after the first version of this script wrongly used
the per-block window-compare windows): reads the "Sleep Trajectory" sheet
(metric_sleep_trajectory.py), whose qualifying windows are found by sliding
from LiCl through the end of the Training day (30min window, >25min asleep),
with NO reference to block timing at all -- unlike "Window Compare Pairs",
whose window is always anchored to a specific block. Both sheets were already
saved in a previous session, so this is xlsx-only, no spike-data reload.

The 8 rats metric_sleep_trajectory.py was run for (its default good_rats()
filter, >=15 units in GC or S1) already have this sheet populated. MS22 and
MS24 (in RAT_KEYS, just under that unit threshold) are filled in here by
calling find_qualifying_windows() directly -- it only needs sleep-state
data (buzcode's states.mat) and licl_time_s, nothing spike-derived, so this
is still cheap, no spike-data reload, for exactly these two. MS23 is not in
RAT_KEYS at all (dropped from the whole cross-rat project 2026-11-05, no
GC/S1 boundary data) and is correctly absent here too.

Usage (np_analysis): python window_sleep_fraction_plot.py
"""
import os

import numpy as np
import openpyxl
import matplotlib.pyplot as plt

from fano_factor_total import CROSS_RAT_FANO_DIR, RAT_KEYS
from plot_fano_block_trend import RAT_COLORS, SURFACE, PRIMARY_INK, SECONDARY_INK, MUTED_INK, GRIDLINE
from plot_metric_block_trend import METRIC_CONFIG, MIN_UNITS_TO_DISPLAY
from metric_sleep_trajectory import find_qualifying_windows, block1_means_and_counts
from MS_buzcode_analysis import ANIMALS, NAS_PELEG, copy_to_share_safely

RNG = np.random.default_rng(0)
WINDOW_MINUTES, MIN_SLEEP_MINUTES = 30, 25  # metric_sleep_trajectory.py's own defaults


def load_qualifying_windows_per_rat():
    xlsx_path = f"{CROSS_RAT_FANO_DIR}/FanoFactorTotal.xlsx"
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb['Sleep Trajectory']
    rows = list(ws.iter_rows(values_only=True))
    header, data = rows[0], rows[1:]
    idx = {name: i for i, name in enumerate(header)}

    # One (window_index -> sleep_fraction) per rat -- dedup across region,
    # since the same qualifying window (and its sleep duration) is shared by
    # both regions' rows for that window.
    by_rat = {}
    for r in data:
        if r[idx['point_type']] != 'sleep_window':
            continue
        rat, win_idx = r[idx['rat']], r[idx['window_index']]
        win_start, win_end, sleep_s = r[idx['window_start_s']], r[idx['window_end_s']], r[idx['sleep_duration_s']]
        frac = sleep_s / (win_end - win_start)
        by_rat.setdefault(rat, {})[win_idx] = frac

    # Fill in any RAT_KEYS rat the sheet skipped (MS22, MS24) directly --
    # sleep-state-only, no spike data needed.
    for rat, key in RAT_KEYS.items():
        if rat in by_rat:
            continue
        cfg = ANIMALS[key]
        windows = find_qualifying_windows(cfg, WINDOW_MINUTES, MIN_SLEEP_MINUTES)
        if not windows:
            continue
        by_rat[rat] = {i: sleep_s / (we - ws) for i, (ws, we, sleep_s) in enumerate(windows, start=1)}
    return by_rat


def low_unit_rats(rats):
    """Rats with fewer than MIN_UNITS_TO_DISPLAY units in BOTH GC and S1 --
    same threshold plot_metric_block_trend.py uses to drop a rat from a
    region's display."""
    low = set()
    for rat in rats:
        _baseline, counts = block1_means_and_counts(METRIC_CONFIG['fano'], rat)
        if max(counts.get('GC', 0), counts.get('S1', 0)) < MIN_UNITS_TO_DISPLAY:
            low.add(rat)
    return low


def main():
    by_rat = load_qualifying_windows_per_rat()
    rats = [rat for rat in RAT_KEYS if rat in by_rat]
    low = low_unit_rats(rats)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    ax.set_facecolor(SURFACE)
    ax.margins(x=0.04)
    threshold_pct = 100 * 25 / 30  # min_sleep_minutes / window_minutes, metric_sleep_trajectory.py defaults
    ax.axhline(threshold_pct, color=GRIDLINE, linewidth=1.2, linestyle='--', zorder=1)
    ax.annotate(f"{threshold_pct:.0f}% qualifying threshold", (0.995, threshold_pct),
                xycoords=('axes fraction', 'data'), ha='right', va='bottom', fontsize=9, color=MUTED_INK)

    for x, (color, rat) in enumerate(zip(RAT_COLORS, rats)):
        fracs = [by_rat[rat][w] * 100 for w in sorted(by_rat[rat])]
        jitter = RNG.uniform(-0.12, 0.12, size=len(fracs))
        ax.scatter(np.full(len(fracs), x) + jitter, fracs, color=color, s=70, alpha=0.85,
                   edgecolors=SURFACE, linewidths=1, zorder=3)
        ax.scatter([x], [np.mean(fracs)], color=PRIMARY_INK, marker='_', s=400, linewidths=2, zorder=4)

    ax.set_xticks(range(len(rats)))
    ax.set_xticklabels([f"{rat}{'*' if rat in low else ''}\n(n={len(by_rat[rat])})" for rat in rats],
                        fontsize=10.5, color=SECONDARY_INK)
    for x, rat in enumerate(rats):
        if rat in low:
            ax.get_xticklabels()[x].set_color(MUTED_INK)
            ax.get_xticklabels()[x].set_fontstyle('italic')
    ax.set_ylabel("Sleep fraction within the qualifying window (%)", fontsize=10.5, color=SECONDARY_INK)
    ax.set_title("Block-independent qualifying sleep windows: sleep fraction and count per rat",
                 fontsize=13, color=PRIMARY_INK, pad=14, loc='left', fontweight='medium')
    ax.tick_params(colors=MUTED_INK)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('left', 'bottom'):
        ax.spines[spine].set_color(GRIDLINE)
    if low:
        fig.text(0.01, 0.005, f"* fewer than {MIN_UNITS_TO_DISPLAY} units in both GC and S1 ({', '.join(sorted(low))})",
                 fontsize=9.5, color=MUTED_INK, ha='left')
    fig.tight_layout()

    local_path = "/tmp/WindowSleepFraction_AllRats.png"
    plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
    print(f"Wrote {local_path}")
    nas_dir = f"{NAS_PELEG}/CrossRatAnalysis"
    os.makedirs(nas_dir, exist_ok=True)
    copy_to_share_safely(local_path, nas_dir)
    print(f"Copied to {nas_dir}/")


if __name__ == '__main__':
    main()
