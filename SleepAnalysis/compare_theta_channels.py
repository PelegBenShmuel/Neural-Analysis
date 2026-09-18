"""
Compare two buzcode sleep-scoring runs of the same recording that differ only
in which theta channel was used (e.g. MS11's original channel 65 vs. the
channel 81 found by find_theta_channel.m). Reuses sleep_sanity_check.py's
loading/checking functions on each .mat file rather than reimplementing them,
and adds a stacked hypnogram so the two scorings can be eyeballed directly.

Usage: python compare_theta_channels.py [COMPARISON]   (default: MS11_ch65_vs_ch81)
"""
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

from sleep_sanity_check import (
    ANIMALS, STATE_CODE, STATE_COL, EXPECTED_PCT,
    load_states, check_coverage, check_proportions, check_bouts,
    check_taste_alignment, check_rem_plausibility, check_rem_fragmentation,
    NAS_PELEG,
)

COMPARISONS = {
    'MS11_ch65_vs_ch81': dict(
        animal  = 'MS11',
        out_dir = f'{NAS_PELEG}/MS11/MS11_theta_channel_comparison',
        variants = [
            dict(label='ch65 (original)',
                 mat_file='/media/anan/diskh2/MS11/MS11_hab3/'
                          'pre_channel81_backup_20260918_0900/'
                          'MS11_hab3.SleepState.states.mat'),
            dict(label='ch81 (2026-09-18 rescore)',
                 mat_file='/media/anan/diskh2/MS11/MS11_hab3/'
                          'MS11_hab3.SleepState.states.mat'),
        ],
    ),
}


def hypnogram_row(ax, t, states, label):
    for name, code in STATE_CODE.items():
        mask = states == code
        ax.fill_between(t / 3600, 0, 1, where=mask, color=STATE_COL[name],
                         step='post', linewidth=0)
    ax.set_yticks([])
    ax.set_ylabel(label, rotation=0, ha='right', va='center', fontsize=10)
    ax.set_xlim(0, t[-1] / 3600)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'MS11_ch65_vs_ch81'
    cmp_cfg = COMPARISONS[name]
    animal = cmp_cfg['animal']
    cfg = ANIMALS[animal]

    results = []
    for v in cmp_cfg['variants']:
        print(f'\n{"="*70}\n{animal} -- {v["label"]}  ({v["mat_file"]})\n{"="*70}')
        t, states, bouts, t_clus, motion, mo_thr = load_states(v['mat_file'])
        check_coverage(t, states)
        pct = check_proportions(t, states)
        durations = check_bouts(bouts)
        check_taste_alignment(t, states, cfg['sync_file'], cfg['taste_files'])
        check_rem_plausibility(t, states, t_clus, motion, mo_thr,
                                cfg.get('video_file'), cfg.get('mov_fps'),
                                cfg['sync_file'])
        results.append(dict(label=v['label'], t=t, states=states, pct=pct,
                             durations=durations, bouts=bouts))

    # ── Side-by-side summary table ──────────────────────────────────────────
    print(f'\n{"="*70}\nSide-by-side summary\n{"="*70}')
    header = f'{"":18s}' + ''.join(f'{r["label"]:>26s}' for r in results)
    print(header)
    for name_ in STATE_CODE:
        row = f'{name_+" %":18s}' + ''.join(
            f'{r["pct"][name_]:25.1f}%' for r in results)
        print(row)
    for name_ in STATE_CODE:
        row = f'{name_+" bouts":18s}' + ''.join(
            f'{len(r["bouts"][name_][0]):26d}' for r in results)
        print(row)
    ratios = [r['pct']['NREM'] / r['pct']['REM'] for r in results]
    print(f'{"NREM:REM ratio":18s}' + ''.join(f'{x:26.1f}' for x in ratios))

    # ── Stacked hypnogram figure ────────────────────────────────────────────
    fig, axes = plt.subplots(len(results), 1, figsize=(16, 1.2 * len(results)),
                              sharex=True)
    if len(results) == 1:
        axes = [axes]
    for ax, r in zip(axes, results):
        hypnogram_row(ax, r['t'], r['states'], r['label'])
    axes[-1].set_xlabel('Hours into recording')
    handles = [mpatches.Patch(color=STATE_COL[s], label=s) for s in STATE_CODE]
    fig.legend(handles=handles, loc='upper right', ncol=3)
    fig.suptitle(f'{animal}: theta-channel comparison ({name})')
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    os.makedirs('/tmp/theta_channel_comparison', exist_ok=True)
    local_png = f'/tmp/theta_channel_comparison/{name}_hypnogram.png'
    fig.savefig(local_png, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    out_dir = cmp_cfg['out_dir']
    os.makedirs(out_dir, exist_ok=True)
    out_png = os.path.join(out_dir, f'{name}_hypnogram.png')
    with open(local_png, 'rb') as src, open(out_png, 'wb') as dst:
        dst.write(src.read())
    print(f'\nComparison hypnogram saved -> {out_png}')


if __name__ == '__main__':
    main()
