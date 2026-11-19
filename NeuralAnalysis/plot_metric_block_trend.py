"""
Per-rat trend across the 7 Training-day blocks, for one region and one
metric at a time -- generalizes plot_fano_block_trend.py (Peleg's request,
2026-11-10: the same "all rats, normalized" trend plot, but for
Firing Rate and Coefficient of Variation too, not just Fano factor).
One script parameterized by METRIC_CONFIG rather than copy-pasting
plot_fano_block_trend.py twice (see feedback_no_script_duplication
memory). Fano factor itself is left in its own script/file since several
other Fano-specific scripts already import constants from it
(plot_fano_region_compare.py, fano_window_compare.py, etc.); this script
imports those same shared style constants rather than redefining them.

Reads <Metric>Total.xlsx (built by fano_factor_total.py /
firing_rate_total.py / coefficient_of_variation_total.py) rather than
recomputing from raw spike data. One line per rat (mean +/- SEM per
block), solid = Experimental group / dashed = Control, optional
--normalize (% of each rat's own Block 1 mean, SEM rescaled by the same
factor).

Display filter: a rat is shown only if it has >= MIN_UNITS_TO_DISPLAY (15)
units in the requested region -- Peleg's explicit call, 2026-11-10,
replacing the earlier hardcoded EXCLUDED_FROM_DISPLAY name-list (MS15/22/24)
with a dynamic per-region/per-plot threshold instead (a rat excluded for
GC because it has <15 GC units may still show up in the S1 plot if it has
enough S1 units, and vice versa). Display-only -- the underlying xlsx
tables are untouched either way.

Usage (peleg_env is enough): python plot_metric_block_trend.py <fano|fr|cv> [GC|S1|undefined] [--normalize]
Defaults to fano GC.
"""
import sys
import os

import numpy as np
import openpyxl
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'SleepAnalysis'))
from MS_buzcode_analysis import copy_to_share_safely
from fano_factor_total import CROSS_RAT_FANO_DIR
from firing_rate_total import CROSS_RAT_FR_DIR
from coefficient_of_variation_total import CROSS_RAT_CV_DIR
from plot_fano_block_trend import SHEET_GROUP, RAT_COLORS, SURFACE, PRIMARY_INK, SECONDARY_INK, MUTED_INK, GRIDLINE

MIN_UNITS_TO_DISPLAY = 15

METRIC_CONFIG = {
    'fano': dict(xlsx_dir=CROSS_RAT_FANO_DIR, xlsx_name="FanoFactorTotal.xlsx",
                 col_suffix="_fano", display_name="Fano factor",
                 raw_ylabel="Fano factor (Var/Mean, 1s bins, 4min pre-block)",
                 out_prefix="FanoFactor"),
    'fr': dict(xlsx_dir=CROSS_RAT_FR_DIR, xlsx_name="FiringRateTotal.xlsx",
               col_suffix="_fr", display_name="Firing rate",
               raw_ylabel="Firing rate (Hz, 4min pre-block)",
               out_prefix="FiringRate"),
    'cv': dict(xlsx_dir=CROSS_RAT_CV_DIR, xlsx_name="CoefficientOfVariationTotal.xlsx",
               col_suffix="_cv", display_name="Coefficient of Variation",
               raw_ylabel="CV of ISI (SD/Mean, 4min pre-block)",
               out_prefix="CoefficientOfVariation"),
}


def load_region_rows(metric_cfg, region):
    """Returns {rat: {'group': ..., 'blocks': [[block1 vals], ..., [block7 vals]]}},
    rats with fewer than MIN_UNITS_TO_DISPLAY units in this region dropped."""
    xlsx_path = f"{metric_cfg['xlsx_dir']}/{metric_cfg['xlsx_name']}"
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    block_fields = [f"block{i}{metric_cfg['col_suffix']}" for i in range(1, 8)]

    by_rat = {}
    unit_counts = {}
    for sheet_name, group in SHEET_GROUP.items():
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        header, data = rows[0], rows[1:]
        idx = {name: i for i, name in enumerate(header)}
        for r in data:
            cluster = r[idx['cluster']]
            if isinstance(cluster, str):   # skip the bold "MEAN (n=...)" summary rows
                continue
            if r[idx['region']] != region:
                continue
            rat = r[idx['rat']]
            unit_counts[rat] = unit_counts.get(rat, 0) + 1
            entry = by_rat.setdefault(rat, {'group': group, 'blocks': [[] for _ in range(7)]})
            for i, field in enumerate(block_fields):
                val = r[idx[field]]
                if val not in (None, ""):
                    entry['blocks'][i].append(val)

    excluded = [rat for rat, n in unit_counts.items() if n < MIN_UNITS_TO_DISPLAY]
    if excluded:
        print(f"Excluding from display (<{MIN_UNITS_TO_DISPLAY} {region} units): "
              f"{', '.join(f'{r} (n={unit_counts[r]})' for r in sorted(excluded))}")
    return {rat: entry for rat, entry in by_rat.items() if unit_counts[rat] >= MIN_UNITS_TO_DISPLAY}


def main():
    args = sys.argv[1:]
    normalize = '--normalize' in args
    args = [a for a in args if a != '--normalize']
    metric = args[0] if args else 'fano'
    region = args[1] if len(args) > 1 else 'GC'

    if metric not in METRIC_CONFIG:
        raise SystemExit(f"Unknown metric '{metric}'. Known: {list(METRIC_CONFIG)}")
    metric_cfg = METRIC_CONFIG[metric]

    by_rat = load_region_rows(metric_cfg, region)
    if not by_rat:
        raise SystemExit(f"No rat has >={MIN_UNITS_TO_DISPLAY} '{region}' units in {metric_cfg['xlsx_name']}")

    assert len(RAT_COLORS) >= len(by_rat), (
        f"{len(by_rat)} rats have '{region}' data but RAT_COLORS only has "
        f"{len(RAT_COLORS)} slots -- zip() would silently drop the rest. Add more colors.")

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.set_facecolor(SURFACE)
    ax.margins(x=0)
    for i in range(1, 7):
        ax.axvline(i + 0.5, color=GRIDLINE, linewidth=0.8, zorder=1)
    if normalize:
        ax.axhline(100, color=GRIDLINE, linewidth=1.2, linestyle='--', zorder=1)

    blocks_x = np.arange(1, 8)
    for color, rat in zip(RAT_COLORS, sorted(by_rat)):
        entry = by_rat[rat]
        means = [np.mean(v) if v else np.nan for v in entry['blocks']]
        sems = [np.std(v, ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0 for v in entry['blocks']]
        n_units = max(len(v) for v in entry['blocks'])

        if normalize:
            # % of Block 1 (same convention as plot_fano_block_trend.py's
            # --normalize, Anan Moran's request via Peleg): every rat's own
            # Block 1 mean becomes 100%, SEM rescaled by the same factor.
            baseline = means[0]
            if not baseline or np.isnan(baseline):
                print(f"[SKIP] {rat}: no valid Block 1 mean to normalize against")
                continue
            means = [100 * m / baseline for m in means]
            sems = [100 * s / baseline for s in sems]

        linestyle = '-' if entry['group'] == 'Experiment' else '--'
        label = f"{rat} ({'Exp' if entry['group'] == 'Experiment' else 'Ctrl'}, n={n_units})"
        ax.errorbar(blocks_x, means, yerr=sems, color=color, linestyle=linestyle,
                     marker='o', markersize=6, linewidth=2, capsize=3, label=label, zorder=3)

    ax.set_xticks(blocks_x)
    ax.set_xlabel("Training-day block", fontsize=10.5, color=SECONDARY_INK)
    if normalize:
        ax.set_ylabel(f"{metric_cfg['display_name']} (% of Block 1)", fontsize=10.5, color=SECONDARY_INK)
        title_suffix = " — normalized to Block 1 = 100%"
    else:
        ax.set_ylabel(metric_cfg['raw_ylabel'], fontsize=10.5, color=SECONDARY_INK)
        title_suffix = ""
    ax.set_title(f"{metric_cfg['display_name']} across Training-day blocks — {region} population "
                 f"(mean ± SEM per rat){title_suffix}",
                 fontsize=12, color=PRIMARY_INK, pad=14, loc='left', fontweight='medium')
    ax.tick_params(colors=MUTED_INK)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('left', 'bottom'):
        ax.spines[spine].set_color(GRIDLINE)
    ax.legend(frameon=False, fontsize=9.5, labelcolor=SECONDARY_INK, loc='upper left',
              bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()

    suffix = "_Normalized" if normalize else ""
    local_path = f"/tmp/{metric_cfg['out_prefix']}_{region}_AllRats_Block1to7{suffix}.png"
    plt.savefig(local_path, dpi=150, facecolor=SURFACE, bbox_inches='tight')
    print(f"Wrote {local_path}")

    os.makedirs(metric_cfg['xlsx_dir'], exist_ok=True)
    copy_to_share_safely(local_path, metric_cfg['xlsx_dir'])
    print(f"Copied to {metric_cfg['xlsx_dir']}/")


if __name__ == '__main__':
    main()
