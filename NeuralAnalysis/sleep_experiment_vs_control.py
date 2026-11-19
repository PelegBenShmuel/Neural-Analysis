"""
Does the Experimental group (got LiCl paired with the CTA taste) sleep
differently from Control/Familiar (MS15/MS18/MS20)? Peleg's question,
2026-11-19, continuing the sleep-characteristics work from the same day
(window-count/fragmentation findings) -- this compares those same
per-rat sleep characteristics ACROSS the group split itself, rather than
against a neural metric.

Three per-rat sleep characteristics, computed directly from sleep-state
data only (no spike-data reload, same as window_sleep_fraction_plot.py):
  1. total_sleep_pct -- % of the post-LiCl Training day spent asleep.
  2. n_qualifying_windows -- block-independent 30min/>25min-asleep windows
     (metric_sleep_trajectory.py's find_qualifying_windows()).
  3. fragmentation_pct -- % of all possible overlapping 30min slides
     (stepping every 60s across the whole day) that clear the 25min
     threshold -- the 2026-11-17 MS14 finding's own metric, now computed
     for every rat instead of ad hoc for two.

Mann-Whitney U per metric (Experiment n=7 vs Control n=3) is reported for
reference only -- n=3 in the Control group is too small to treat any
p-value here as a real statistical answer; read the plot, not the p-value.

Usage (np_analysis): python sleep_experiment_vs_control.py
"""
import os

import numpy as np
import openpyxl
from openpyxl.styles import Font
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu

from fano_factor_total import RAT_KEYS, CONTROL_RATS, group_of
from plot_fano_block_trend import RAT_COLORS, SURFACE, PRIMARY_INK, SECONDARY_INK, MUTED_INK, GRIDLINE
from training_day_sleep_state_extraction import load_states, training_day_window
from metric_sleep_trajectory import SLEEP_CODES, STEP_S, find_qualifying_windows
from MS_buzcode_analysis import ANIMALS, NAS_PELEG, copy_to_share_safely

RNG = np.random.default_rng(0)
GROUPS = ['Experiment', 'Control']
METRICS = [
    ('total_sleep_pct', '% of post-LiCl day asleep'),
    ('n_qualifying_windows', 'Qualifying sleep windows (count)'),
    ('fragmentation_pct', '% of 30min slides clearing the sleep threshold'),
]


def compute_sleep_characteristics(rat):
    key = RAT_KEYS[rat]
    cfg = ANIMALS[key]
    licl_time_s = cfg['licl_time_s']
    _day_start, day_end, _wh0, _wh1 = training_day_window(cfg, licl_time_s)

    t, states, _bouts = load_states(cfg['mat_file'])
    dt = np.diff(t, append=t[-1])
    is_sleep = np.isin(states, SLEEP_CODES)

    mask = (t >= licl_time_s) & (t < day_end)
    total_sleep_pct = 100 * dt[mask & is_sleep].sum() / dt[mask].sum()

    n_qualifying_windows = len(find_qualifying_windows(cfg, 30, 25))

    window_s, min_sleep_s = 30 * 60, 25 * 60
    n_dense, n_slides, start = 0, 0, licl_time_s
    while start + window_s <= day_end:
        end = start + window_s
        m = (t >= start) & (t < end)
        n_slides += 1
        if dt[m & is_sleep].sum() > min_sleep_s:
            n_dense += 1
        start += STEP_S
    fragmentation_pct = 100 * n_dense / n_slides if n_slides else float('nan')

    return total_sleep_pct, n_qualifying_windows, fragmentation_pct


def main():
    rats = list(RAT_KEYS)
    color_for_rat = dict(zip(rats, RAT_COLORS))
    per_rat = {}
    for rat in rats:
        total_sleep_pct, n_windows, fragmentation_pct = compute_sleep_characteristics(rat)
        per_rat[rat] = {
            'group': group_of(rat),
            'total_sleep_pct': total_sleep_pct,
            'n_qualifying_windows': n_windows,
            'fragmentation_pct': fragmentation_pct,
        }
        print(f"{rat} ({group_of(rat)}): sleep={total_sleep_pct:.1f}%, "
              f"n_windows={n_windows}, fragmentation={fragmentation_pct:.1f}%")

    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    for ax, (key, ylabel) in zip(axes, METRICS):
        ax.set_facecolor(SURFACE)
        exp_vals = [per_rat[r][key] for r in rats if per_rat[r]['group'] == 'Experiment']
        ctrl_vals = [per_rat[r][key] for r in rats if per_rat[r]['group'] == 'Control']

        for gx, group in enumerate(GROUPS):
            group_rats = [r for r in rats if per_rat[r]['group'] == group]
            vals = [per_rat[r][key] for r in group_rats]
            jitter = RNG.uniform(-0.12, 0.12, size=len(vals))
            for r, v, j in zip(group_rats, vals, jitter):
                ax.scatter([gx + j], [v], color=color_for_rat[r], s=90, alpha=0.9,
                           edgecolors=SURFACE, linewidths=1, zorder=3, label=r)
            ax.scatter([gx], [np.mean(vals)], color=PRIMARY_INK, marker='_', s=500, linewidths=2.2, zorder=4)

        stat, p = mannwhitneyu(exp_vals, ctrl_vals)
        ax.text(0.5, -0.17, f"Mann-Whitney: p={p:.3g} (n=7 vs n=3 -- reference only)",
                transform=ax.transAxes, ha='center', fontsize=9, color=MUTED_INK)

        ax.set_xticks([0, 1])
        ax.set_xticklabels(['Experiment\n(n=7)', 'Control\n(n=3)'], fontsize=11, color=SECONDARY_INK)
        ax.set_xlim(-0.5, 1.5)
        ax.set_ylabel(ylabel, fontsize=10, color=SECONDARY_INK)
        ax.tick_params(colors=MUTED_INK)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        for spine in ('left', 'bottom'):
            ax.spines[spine].set_color(GRIDLINE)

    handles, labels = axes[0].get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    fig.legend(by_label.values(), by_label.keys(), loc='upper center', bbox_to_anchor=(0.5, 1.0),
               ncol=10, frameon=False, fontsize=9, labelcolor=SECONDARY_INK)
    fig.suptitle("Sleep characteristics: Experiment vs. Control", fontsize=14, color=PRIMARY_INK,
                 x=0.02, ha='left', fontweight='medium', y=1.08)
    fig.tight_layout(rect=[0, 0, 1, 0.92])

    local_path = "/tmp/SleepCharacteristics_ExperimentVsControl.png"
    plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
    print(f"\nWrote {local_path}")
    nas_dir = f"{NAS_PELEG}/CrossRatAnalysis"
    os.makedirs(nas_dir, exist_ok=True)
    copy_to_share_safely(local_path, nas_dir)
    print(f"Copied to {nas_dir}/")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Per Rat"
    header = ['rat', 'group', 'total_sleep_pct', 'n_qualifying_windows', 'fragmentation_pct']
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for rat in rats:
        row = per_rat[rat]
        ws.append([rat, row['group'], round(row['total_sleep_pct'], 2),
                   row['n_qualifying_windows'], round(row['fragmentation_pct'], 2)])
    for col_idx, field in enumerate(header, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(14, len(field) + 2)

    ws2 = wb.create_sheet("Group Test")
    header2 = ['metric', 'n_experiment', 'n_control', 'U_statistic', 'p_value', 'note']
    ws2.append(header2)
    for cell in ws2[1]:
        cell.font = Font(bold=True)
    for key, _ylabel in METRICS:
        exp_vals = [per_rat[r][key] for r in rats if per_rat[r]['group'] == 'Experiment']
        ctrl_vals = [per_rat[r][key] for r in rats if per_rat[r]['group'] == 'Control']
        stat, p = mannwhitneyu(exp_vals, ctrl_vals)
        ws2.append([key, len(exp_vals), len(ctrl_vals), round(float(stat), 2), p,
                    "reference only -- n=3 in Control is underpowered"])
    for col_idx, field in enumerate(header2, start=1):
        ws2.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(14, len(field) + 2)

    local_xlsx = "/tmp/SleepCharacteristics.xlsx"
    wb.save(local_xlsx)
    copy_to_share_safely(local_xlsx, nas_dir)
    print(f"Wrote {nas_dir}/SleepCharacteristics.xlsx")


if __name__ == '__main__':
    main()
