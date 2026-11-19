"""
Correlation between how many qualifying sleep windows a rat had and how
much its neural metric changes -- Peleg's question, 2026-11-19, continuing
the sleep-characteristics thread from the same day. One point per rat,
GC | S1 panels. Two modes, picked by the 2nd CLI argument:

  window_diff (default) -- Y = that rat/region's own
    mean(fixed_value - sleep_value) across all blocks, from the
    "Window Diff Trajectory" sheet (the Window Compare sleep-effect size).
  block1to7 -- Y = % change in the metric from Block 1 to Block 7, using
    ONLY the standard fixed pre-block window (no sleep-window selection at
    all) -- i.e. does the day-long trend itself relate to how much
    qualifying sleep a rat got, regardless of the window-compare effect.

X also has two choices (3rd CLI argument), both from SleepCharacteristics.xlsx
"Per Rat" (already saved, no recompute):
  n_windows (default) -- block-independent qualifying-window COUNT (how many
    good opportunities the rat had; reflects fragmentation more than amount,
    see the 2026-11-17/19 MS14 finding).
  total_sleep -- total_sleep_pct, how much of the day the rat actually spent
    asleep overall ("did a rat that slept MORE show a different change").
These are genuinely different quantities -- a rat can have few windows but
high total sleep (fragmented) or the reverse.

Both X and Y are read from already-saved xlsx sheets -- no spike-data
reload either way. Spearman correlation (not Pearson -- small n, no
assumption of linearity needed) reported per region; genuinely small
sample (<=10 rats per region), read the scatter, not just the p-value.

Usage (np_analysis): python sleep_neural_correlation.py <fano|fr|cv> [window_diff|block1to7] [n_windows|total_sleep]
"""
import sys
import os
from collections import defaultdict

import numpy as np
import openpyxl
from openpyxl.styles import Font
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

from fano_factor_total import RAT_KEYS
from plot_fano_block_trend import SHEET_GROUP, RAT_COLORS, SURFACE, PRIMARY_INK, SECONDARY_INK, MUTED_INK, GRIDLINE
from plot_metric_block_trend import METRIC_CONFIG
from MS_buzcode_analysis import NAS_PELEG, copy_to_share_safely

MODES = {
    'window_diff': {
        'sheet': 'Window Diff Trajectory', 'out_suffix': 'SleepWindowCount_vs_EffectSize',
        'result_sheet': 'Sleep Window Count vs Effect', 'y_col': 'mean_diff_fixed_minus_sleep',
        'ylabel': lambda m: f"{m['display_name']} diff (fixed − sleep window)",
        'title': lambda m, x: f"{x['xlabel']} vs. {m['display_name']} sleep effect, per rat",
    },
    'block1to7': {
        'sheet': None, 'out_suffix': 'SleepWindowCount_vs_Block1to7Change',
        'result_sheet': 'Sleep vs Block1-7 Change', 'y_col': 'pct_change_block1_to_block7',
        'ylabel': lambda m: f"{m['display_name']} % change, Block 1 → Block 7 (fixed window only)",
        'title': lambda m, x: f"{x['xlabel']} vs. {m['display_name']} Block1→7 trend, per rat",
    },
}


X_MODES = {
    'n_windows': {'col': 'n_qualifying_windows', 'xlabel': 'Qualifying sleep windows (count)'},
    'total_sleep': {'col': 'total_sleep_pct', 'xlabel': '% of post-LiCl day asleep'},
}


def load_x_per_rat(x_mode):
    xlsx_path = f"{NAS_PELEG}/CrossRatAnalysis/SleepCharacteristics.xlsx"
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb['Per Rat']
    rows = list(ws.iter_rows(values_only=True))
    header, data = rows[0], rows[1:]
    idx = {name: i for i, name in enumerate(header)}
    col = X_MODES[x_mode]['col']
    return {r[idx['rat']]: r[idx[col]] for r in data}


def load_mean_diff_per_rat_region(metric_cfg):
    xlsx_path = f"{metric_cfg['xlsx_dir']}/{metric_cfg['xlsx_name']}"
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    ws = wb['Window Diff Trajectory']
    rows = list(ws.iter_rows(values_only=True))
    header, data = rows[0], rows[1:]
    idx = {name: i for i, name in enumerate(header)}

    by_rat_region = defaultdict(list)
    for r in data:
        rat, region, diff = r[idx['rat']], r[idx['region']], r[idx['mean_diff_fixed_minus_sleep']]
        by_rat_region[(rat, region)].append(diff)
    return {k: float(np.mean(v)) for k, v in by_rat_region.items()}


def load_block1to7_pct_change_per_rat_region(metric_cfg):
    """% change from Block 1 to Block 7, fixed window only -- no sleep-window
    selection involved at all, reused straight from the Experiment/Control
    sheets (the same data plot_metric_block_trend.py's normalized plots use)."""
    xlsx_path = f"{metric_cfg['xlsx_dir']}/{metric_cfg['xlsx_name']}"
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    col1 = f"block1{metric_cfg['col_suffix']}"
    col7 = f"block7{metric_cfg['col_suffix']}"

    by_rat_region = defaultdict(lambda: {'b1': [], 'b7': []})
    for sheet_name in SHEET_GROUP:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        header, data = rows[0], rows[1:]
        idx = {name: i for i, name in enumerate(header)}
        for r in data:
            if isinstance(r[idx['cluster']], str):
                continue
            rat, region = r[idx['rat']], r[idx['region']]
            if region not in ('GC', 'S1'):
                continue
            v1, v7 = r[idx[col1]], r[idx[col7]]
            if v1 not in (None, ''):
                by_rat_region[(rat, region)]['b1'].append(v1)
            if v7 not in (None, ''):
                by_rat_region[(rat, region)]['b7'].append(v7)

    out = {}
    for key, vals in by_rat_region.items():
        if vals['b1'] and vals['b7']:
            mean1, mean7 = np.mean(vals['b1']), np.mean(vals['b7'])
            if mean1:
                out[key] = float(100 * (mean7 / mean1 - 1))
    return out


def main():
    args = sys.argv[1:]
    if not args or args[0] not in METRIC_CONFIG:
        raise SystemExit(f"First argument must be a metric: {list(METRIC_CONFIG)}")
    metric_cfg = METRIC_CONFIG[args[0]]
    mode = args[1] if len(args) > 1 else 'window_diff'
    if mode not in MODES:
        raise SystemExit(f"2nd argument must be a mode: {list(MODES)}")
    mode_cfg = MODES[mode]
    x_mode = args[2] if len(args) > 2 else 'n_windows'
    if x_mode not in X_MODES:
        raise SystemExit(f"3rd argument must be an X mode: {list(X_MODES)}")
    x_cfg = X_MODES[x_mode]

    n_windows = load_x_per_rat(x_mode)
    mean_diff = (load_mean_diff_per_rat_region(metric_cfg) if mode == 'window_diff'
                 else load_block1to7_pct_change_per_rat_region(metric_cfg))
    color_for_rat = dict(zip(RAT_KEYS, RAT_COLORS))  # stable per-rat color, never positional --
    # a rat missing from one region's panel must not shift every later rat's color (bug found
    # and fixed 2026-11-19: the original positional zip(RAT_COLORS, rats_here) did exactly that).

    fig, (ax_gc, ax_s1) = plt.subplots(1, 2, figsize=(13, 5.5))
    data_rows = []
    for ax, region in [(ax_gc, 'GC'), (ax_s1, 'S1')]:
        ax.set_facecolor(SURFACE)
        ax.axhline(0, color=GRIDLINE, linewidth=1.2, linestyle='--', zorder=1)

        xs, ys, rats_here = [], [], []
        for rat in RAT_KEYS:
            if rat not in n_windows or (rat, region) not in mean_diff:
                continue
            xs.append(n_windows[rat])
            ys.append(mean_diff[(rat, region)])
            rats_here.append(rat)
            data_rows.append({'rat': rat, 'region': region, x_cfg['col']: n_windows[rat],
                               mode_cfg['y_col']: mean_diff[(rat, region)]})

        for rat, x, y in zip(rats_here, xs, ys):
            ax.scatter([x], [y], color=color_for_rat[rat], s=110, zorder=3, label=rat)

        if len(xs) >= 3:
            rho, p = spearmanr(xs, ys)
            z = np.polyfit(xs, ys, 1)
            xs_line = np.linspace(min(xs), max(xs), 20)
            ax.plot(xs_line, np.polyval(z, xs_line), color=MUTED_INK, linewidth=1.3, linestyle=':', zorder=2)
            ax.text(0.03, 0.03, f"Spearman ρ={rho:.2f}, p={p:.3g} (n={len(xs)})",
                    transform=ax.transAxes, fontsize=9.5, color=MUTED_INK, ha='left', va='bottom')

        ax.set_xlabel(x_cfg['xlabel'], fontsize=10.5, color=SECONDARY_INK)
        ax.set_title(region, fontsize=12, color=PRIMARY_INK, pad=14, loc='left', fontweight='medium')
        ax.tick_params(colors=MUTED_INK)
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        for spine in ('left', 'bottom'):
            ax.spines[spine].set_color(GRIDLINE)

    ax_gc.set_ylabel(mode_cfg['ylabel'](metric_cfg), fontsize=10.5, color=SECONDARY_INK)
    # Union of both panels' handles -- a rat present in only one region
    # (e.g. MS24, GC-only) must still show up in the shared legend.
    handles, labels = ax_gc.get_legend_handles_labels()
    h2, l2 = ax_s1.get_legend_handles_labels()
    handles, labels = handles + h2, labels + l2
    by_label = dict(zip(labels, handles))
    fig.legend(by_label.values(), by_label.keys(), loc='upper center', bbox_to_anchor=(0.5, 1.04),
               ncol=10, frameon=False, fontsize=9, labelcolor=SECONDARY_INK)
    fig.suptitle(mode_cfg['title'](metric_cfg, x_cfg), fontsize=13, color=PRIMARY_INK, x=0.02, ha='left',
                 fontweight='medium', y=1.14)
    fig.tight_layout(rect=[0, 0, 1, 0.88])

    x_suffix = '' if x_mode == 'n_windows' else f"_{x_mode}"
    local_path = f"/tmp/{metric_cfg['out_prefix']}_{mode_cfg['out_suffix']}{x_suffix}.png"
    plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
    print(f"Wrote {local_path}")
    os.makedirs(metric_cfg['xlsx_dir'], exist_ok=True)
    copy_to_share_safely(local_path, metric_cfg['xlsx_dir'])
    print(f"Copied to {metric_cfg['xlsx_dir']}/")

    xlsx_path = f"{metric_cfg['xlsx_dir']}/{metric_cfg['xlsx_name']}"
    wb = openpyxl.load_workbook(xlsx_path)
    sheet_name = mode_cfg['result_sheet'] + ('' if x_mode == 'n_windows' else ' -TS')
    assert len(sheet_name) <= 31, f"Excel sheet name too long ({len(sheet_name)} chars): {sheet_name!r}"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)
    header = ['rat', 'region', x_cfg['col'], mode_cfg['y_col']]
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in data_rows:
        ws.append([row['rat'], row['region'], row[x_cfg['col']],
                   round(row[mode_cfg['y_col']], 6)])
    for col_idx, field in enumerate(header, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(14, len(field) + 2)

    local_xlsx = f"/tmp/{metric_cfg['xlsx_name']}"
    wb.save(local_xlsx)
    copy_to_share_safely(local_xlsx, metric_cfg['xlsx_dir'])
    print(f"Added '{sheet_name}' sheet to {xlsx_path}")


if __name__ == '__main__':
    main()
