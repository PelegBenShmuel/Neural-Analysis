"""
Per-hour buzcode sleep-scoring visualization: loads buzcode sleep-state
output + LFP + video movement + taste-event timestamps for one animal/
session and plots hourly hypnogram/spectrogram panels, plus 3 metric-
distribution summary plots.

One script, parameterized by animal (ANIMALS dict below) -- not a separate
copy per animal. See feedback_no_script_duplication memory / TODO.md's
"Generalize MS_buzcode_analysis.py" item for why: a prior version of this
took the mirror-a-new-copy-per-animal shortcut (MS_buzcode_analysis_ms08.py)
and that's exactly the debt this consolidation pays down.

Usage: python MS_buzcode_analysis.py [ANIMAL]   (default: MS08)

Writes all output locally first (to /tmp/<animal>_buzcode_analysis_hourly),
then prints a `cp` command to copy the batch onto the NAS -- writing
matplotlib figures directly to the Z:\\Peleg SMB share has corrupted files
before (see plot_full_hypnogram.py's notes).
"""
import sys
import os
import shutil
import time
from datetime import datetime, timedelta

import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mpl_lines
import scipy.io as sio
from scipy import signal
from scipy.stats import gaussian_kde
from scipy.signal import find_peaks
from lspopt import spectrogram_lspopt

# ── Per-animal config ─────────────────────────────────────────────────────────
NAS_MAI   = '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Mai'
NAS_PELEG = '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Peleg'

ANIMALS = {
    'MS11': dict(
        session   = 'MS11_hab3',
        mat_file  = '/media/anan/diskh2/MS11/MS11_hab3/MS11_hab3.SleepState.states.mat',
        lfp_mat   = '/media/anan/diskh2/MS11/MS11_hab3/MS11_hab3.SleepScoreLFP.LFP.mat',
        mov_file  = f'{NAS_PELEG}/MS11/MS11_old_pipeline/data/11_VideoMovement.npy',
        # No _corr variant of the sync file exists for MS11 (unlike the taste
        # files below) -- this is the only one Mai's share has.
        sync_file = f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_7_0.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir   = f'{NAS_PELEG}/MS11/MS11_buzcode_analysis',
        lfp_ch    = 65,
        rec_start = datetime(2025, 5, 27, 9, 41, 49),
        # CORRECTED 2026-09-22 -- this was wrongly `None` ("hab-day-only
        # recording; no CTA/LiCl event in this session"), based only on
        # buzcode sleep-scoring having been done for Hab D3 alone. The
        # Neuropixels/Kilosort recording (MS11_hab3_g0) actually extends
        # through a full Training day: its own taste-event blocks show the
        # same double-Sucrose Block 1 signature as MS08/MS09 (20 Sucrose vs.
        # 10 each Water/NaCl/Acid, at t=88694.3-89292.2s), confirmed directly
        # from the raw _corr.txt event files, not assumed. Same rule as
        # MS08/MS09: LiCl ~5min after Block 1's last tastant.
        licl_time_s = 89292.224696 + 5 * 60,
        # Mirrored from Z:\Mai\MS11\MS11_hab3_g0\kilosort4_23_49h_mai\
        # 2026-09-22, same minimal file set as MS08/MS09.
        spike_sorted_dir = f'{NAS_PELEG}/MS11/MS11_Spike_Sorted_Data',
    ),
    'MS08': dict(
        session   = 'MS08_hab3toExp',
        mat_file  = '/media/anan/diskh2/MS08/MS08_hab3toExp/MS08_hab3toExp.SleepState.states.mat',
        lfp_mat   = '/media/anan/diskh2/MS08/MS08_hab3toExp/MS08_hab3toExp.SleepScoreLFP.LFP.mat',
        mov_file  = f'{NAS_PELEG}/MS08/MS_08_Raw_Data/MS08_VideoMovement.npy',
        sync_file = f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir   = f'{NAS_PELEG}/MS08/MS08_buzcode_analysis',
        lfp_ch    = 370,  # theta channel; SW channel is fixed at 65 for both -- see run_sleep_score_ms08.m
        rec_start = datetime(2025, 3, 4, 9, 0, 9),
        # Derived empirically from taste-event blocks, not assumed: grouping
        # all taste events into blocks (gap>30min = new block) gives 7
        # zero-Sucrose blocks (Hab D3, hours 1.5-15h) then 7 more blocks
        # starting at hour ~25.0h whose first block has *double* Sucrose
        # deliveries (20 vs the usual 10) -- the CTA-induction block (this
        # is "Block 1" in Experiment Protocol and Procedure.md's own
        # numbering: 50 trials, 20 Sucrose + 10 each Water/NaCl/CA).
        # LiCl is injected ~5min AFTER Block 1 ends (its last tastant,
        # t=90588.5s), not after it starts -- corrected 2026-09-17 after
        # Peleg caught the LiCl marker landing mid-block on the hourly
        # plots; the earlier version wrongly used firstevent+7min.
        licl_time_s = 90588.5 + 5 * 60,
        # Minimal raw Kilosort4/Phy output (kilosort4_23_49h_mai, Phy-curated,
        # 41 "good" units), mirrored from Z:\Mai\MS08\MS08_hab3toExp_g1\ --
        # see TODO.md "Mirrored MS08's minimal raw spike-sorted data" (2026-09-17).
        spike_sorted_dir = f'{NAS_PELEG}/MS08/MS08_Spike_Sorted_Data',
    ),
    'MS09': dict(
        session   = 'MS09_hab3_ext',
        mat_file  = '/media/anan/diskh2/MS09/MS09_hab3_ext/MS09_hab3_ext.SleepState.states.mat',
        lfp_mat   = '/media/anan/diskh2/MS09/MS09_hab3_ext/MS09_hab3_ext.SleepScoreLFP.LFP.mat',
        mov_file  = f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_VideoMovement.npy',
        sync_file = f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir   = f'{NAS_PELEG}/MS09/MS09_buzcode_analysis',
        lfp_ch    = 65,  # reverted to original -- no clean theta channel found for MS09,
                         # see run_sleep_score.m and README "Known limitations"
        rec_start = datetime(2025, 3, 18, 9, 20, 11),
        # Same derivation as MS08: 7 zero-Sucrose blocks (Hab D3, hours
        # 0.66-14.66h) then 7 more blocks starting at hour ~24.66h whose
        # first block has double Sucrose (20 vs the usual 10) -- the
        # CTA-induction block ("Block 1"). LiCl is injected ~5min after
        # Block 1's last tastant (t=89388.7s), not after its first --
        # corrected 2026-09-17, see MS08's comment above.
        licl_time_s = 89388.7 + 5 * 60,
        # Same Kilosort4/Phy mirror pattern as MS08 -- see TODO.md "Mirrored the
        # same minimal spike-sorted data set for MS09" (2026-09-17).
        spike_sorted_dir = f'{NAS_PELEG}/MS09/MS09_Spike_Sorted_Data',
    ),
}

TASTE_COLORS = {'Water': 'blue', 'Sucrose': 'orange', 'Salt': 'red', 'Acid': 'green'}
FS_OUT  = 250
MOV_FPS = 25

STATE_Y   = {1: 2,         3: 0,         5: 1}
STATE_COL = {1: '#e06c3a', 3: '#4a90d9', 5: '#5cb85c'}
STATE_LBL = {1: 'WAKE',   3: 'NREM',    5: 'REM'}


def copy_to_share_safely(local_path, nas_dir):
    """Copy local_path onto the gvfs-SMB share via a hidden temp name, then
    an atomic rename onto the real filename -- never writes the final
    filename's content directly.

    Why: copying straight to the destination filename and asserting
    `size matches` immediately after `shutil.copyfile` can crash the process
    (on a mismatch) right as the gvfs-SMB mount is still flushing the write.
    That reproducibly left one destination file (MS08_sleep_char.png)
    permanently corrupted server-side -- stat/rm/overwrite all failing with
    EINVAL, recoverable only by deleting it from a Windows client directly --
    twice in a row, 2026-09-17. Verifying via a retry loop instead of an
    instant crash, and only ever writing full content to a throwaway temp
    name, avoids repeating that failure mode against the real filename.

    Second bug found 2026-09-22 (NeuralAnalysis/cluster_responsiveness.py,
    re-running against output that already existed on the share from a prior
    run): `os.replace` is supposed to atomically overwrite `dest` if it
    already exists, per POSIX -- but over this gvfs-SMB mount it raised
    `FileExistsError` instead, killing a 27-minute run at the copy step,
    after all the real computation had already finished locally. Falling
    back to an explicit remove-then-rename handles that mount's rename
    semantics without weakening the atomicity guarantee on a normal
    filesystem (where the `except` branch simply never triggers).
    """
    dest = os.path.join(nas_dir, os.path.basename(local_path))
    tmp_dest = os.path.join(nas_dir, f'.tmp_{os.path.basename(local_path)}')
    shutil.copyfile(local_path, tmp_dest)

    local_size = os.path.getsize(local_path)
    for attempt in range(5):
        if os.path.getsize(tmp_dest) == local_size:
            break
        time.sleep(0.5)
    else:
        print(f'  [WARNING] {tmp_dest} did not match {local_path}\'s size after '
              f'retries -- leaving it in place rather than renaming over {dest}.')
        return

    try:
        os.replace(tmp_dest, dest)
    except FileExistsError:
        os.remove(dest)
        os.replace(tmp_dest, dest)


def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal]
    out_dir = f'/tmp/{animal}_buzcode_analysis_hourly'
    os.makedirs(out_dir, exist_ok=True)

    # ── Load buzcode metrics ──────────────────────────────────────────────
    print('Loading SleepState...')
    with h5py.File(cfg['mat_file'], 'r') as f:
        t       = np.array(f['SleepState/idx/timestamps']).flatten()
        states  = np.array(f['SleepState/idx/states']).flatten()
        t_clus  = np.array(f['SleepState/detectorinfo/detectionparms/SleepScoreMetrics/t_clus']).flatten()
        bsw     = np.array(f['SleepState/detectorinfo/detectionparms/SleepScoreMetrics/broadbandSlowWave']).flatten()
        thratio = np.array(f['SleepState/detectorinfo/detectionparms/SleepScoreMetrics/thratio']).flatten()
        motion  = np.array(f['SleepState/detectorinfo/detectionparms/SleepScoreMetrics/motiondata']).flatten()
        sw_thr  = float(np.array(f['SleepState/detectorinfo/detectionparms/SleepScoreMetrics/histsandthreshs/swthresh']).flatten()[0])
        th_thr  = float(np.array(f['SleepState/detectorinfo/detectionparms/SleepScoreMetrics/histsandthreshs/THthresh']).flatten()[0])
        mo_thr  = float(np.array(f['SleepState/detectorinfo/detectionparms/SleepScoreMetrics/histsandthreshs/MotionThresh']).flatten()[0])

    dt       = np.diff(t, append=t[-1])
    wake_pct = 100 * dt[states == 1].sum() / t[-1]
    nrem_pct = 100 * dt[states == 3].sum() / t[-1]
    rem_pct  = 100 * dt[states == 5].sum() / t[-1]
    print(f'  Duration {t[-1]/3600:.1f}h  |  WAKE {wake_pct:.1f}%  NREM {nrem_pct:.1f}%  REM {rem_pct:.1f}%')
    print(f'  Thresholds  SW={sw_thr:.3f}  TH={th_thr:.3f}  EMG={mo_thr:.3f}')

    print('Loading LFP...')
    lfp_mat  = sio.loadmat(cfg['lfp_mat'], struct_as_record=False, squeeze_me=True)
    lfp_data = lfp_mat['SleepScoreLFP'].thLFP.astype(np.float32)
    print(f'  {lfp_data.shape[0]} samples  ({lfp_data.shape[0]/FS_OUT/3600:.2f} h at {FS_OUT} Hz)')

    print('Loading video movement...')
    mov_raw = np.load(cfg['mov_file']).astype(np.float32)
    n_sec   = len(mov_raw) // MOV_FPS
    mov_1hz = mov_raw[:n_sec * MOV_FPS].reshape(n_sec, MOV_FPS).mean(axis=1)
    log_mov      = np.log1p(mov_1hz)
    mov_wake_thr = float(np.expm1(log_mov.mean() + 1.5 * log_mov.std()))

    with open(cfg['sync_file']) as f:
        video_sync_offset = float(f.readline().strip())
    print(f'  Video sync offset: {video_sync_offset:.3f} s')

    print('Loading taste events...')
    taste_events = []
    for name, path in cfg['taste_files'].items():
        times = [float(l.strip()) for l in open(path) if l.strip()]
        for t_sec in times:
            taste_events.append((t_sec, name, TASTE_COLORS[name]))
        print(f'  {name}: {len(times)} events')

    licl_time_s = cfg.get('licl_time_s')
    if licl_time_s is not None:
        print(f'  LiCl injection marker: t={licl_time_s:.1f}s ({licl_time_s/3600:.3f}h) = '
              f'{cfg["rec_start"] + timedelta(seconds=licl_time_s)}')

    b_notch, a_notch = signal.iirnotch(50, 200, FS_OUT)
    total_hours = int(np.ceil(t[-1] / 3600))

    # ══════════════════════════════════════════════════════════════════════
    #  PART 1 — 3 distribution PNGs
    # ══════════════════════════════════════════════════════════════════════
    print('\n[1/2] Saving metric distribution plots...')
    dist_cfg = [
        ('SW_distribution',     bsw,     sw_thr, '#4a90d9', 'Slow Wave Power',       'NREM',   'Wake / REM'),
        ('Theta_distribution',  thratio, th_thr, '#9b59b6', 'Theta Ratio',           'Low θ',  'REM'),
        ('Motion_distribution', motion,  mo_thr, '#27ae60', 'Motion (EMG from LFP)', 'Still',  'Moving / Wake'),
    ]
    for fname, data, thresh, clr, title, ll, rl in dist_cfg:
        fig, ax = plt.subplots(figsize=(8, 5), facecolor='white')
        fig.suptitle(f'{cfg["session"]}  —  {title}\n'
                     f'WAKE {wake_pct:.1f}%   NREM {nrem_pct:.1f}%   REM {rem_pct:.1f}%',
                     fontsize=12, fontweight='bold')

        data_clean = data[np.isfinite(data)]
        counts, edges = np.histogram(data_clean, bins=55, range=(0, 1), density=False)
        counts  = counts / counts.sum()
        centers = (edges[:-1] + edges[1:]) / 2
        width   = edges[1] - edges[0]
        c_rgb   = np.array(plt.matplotlib.colors.to_rgb(clr))
        c_light = c_rgb * 0.4 + 0.6

        ax.bar(centers[centers <= thresh], counts[centers <= thresh], width=width, color=c_rgb, alpha=0.75)
        ax.bar(centers[centers >= thresh], counts[centers >= thresh], width=width, color=c_light, alpha=0.60)

        kde   = gaussian_kde(data_clean, bw_method=0.07)
        x_kde = np.linspace(0, 1, 600)
        y_kde = kde(x_kde) * width
        ax.plot(x_kde, y_kde, color=c_rgb * 0.5, linewidth=2.2, zorder=5)

        peaks, _ = find_peaks(y_kde, prominence=y_kde.max() * 0.08, distance=25)
        for p in peaks:
            ax.axvline(x_kde[p], color='#444', linestyle='--', linewidth=1.1, alpha=0.7)
            ax.text(x_kde[p], y_kde[p] * 1.07, f'{x_kde[p]:.2f}', ha='center', va='bottom', fontsize=9, color='#333')

        y_top = max(counts.max(), y_kde.max()) * 1.4
        ax.set_ylim(0, y_top)
        ax.axvline(thresh, color='#c0392b', linewidth=2.2, zorder=6)
        ax.text(thresh + 0.02, y_top * 0.93, f'thr\n{thresh:.2f}', color='#c0392b', fontsize=9, fontweight='bold', va='top')
        ax.text(thresh * 0.5,            y_top * 0.80, ll, ha='center', fontsize=11, fontweight='bold', color=c_rgb * 0.55)
        ax.text(thresh + (1-thresh)*0.5, y_top * 0.80, rl, ha='center', fontsize=11, fontweight='bold', color=c_light * 0.65)

        ax.set_xlabel('Normalized value (0 → 1)', fontsize=11)
        ax.set_ylabel('Proportion of time', fontsize=11)
        ax.set_xlim(0, 1)
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.2)
        plt.tight_layout()

        out = os.path.join(out_dir, f'{fname}.png')
        fig.savefig(out, dpi=180, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f'  Saved → {out}')

    # ══════════════════════════════════════════════════════════════════════
    #  PART 2 — Hourly hypnograms
    # ══════════════════════════════════════════════════════════════════════
    print(f'\n[2/2] Plotting {total_hours} hourly hypnograms...')
    rec_start = cfg['rec_start']

    for hour in range(total_hours):
        t0 = hour * 3600
        t1 = t0 + 3600

        mask_t = (t      >= t0) & (t      < t1)
        mask_c = (t_clus >= t0) & (t_clus < t1)
        t_seg  = t[mask_t];       st_seg  = states[mask_t]
        tc_seg = t_clus[mask_c];  bsw_seg = bsw[mask_c]
        thr_seg = thratio[mask_c]; mot_seg = motion[mask_c]
        if len(t_seg) == 0:
            continue

        hour_start = rec_start + timedelta(seconds=t0)
        hour_end   = rec_start + timedelta(seconds=t1)
        tick_pos   = [t0 + m * 600 for m in range(7)]
        tick_lbl   = [(rec_start + timedelta(seconds=p)).strftime('%H:%M') for p in tick_pos]
        date_s     = hour_start.strftime('%Y-%m-%d')
        time_lbl   = f"{hour_start.strftime('%H:%M')} – {hour_end.strftime('%H:%M')}"

        s0 = t0 * FS_OUT
        s1 = min(t1 * FS_OUT, len(lfp_data))
        chunk = signal.filtfilt(b_notch, a_notch, lfp_data[s0:s1]).astype(np.float32)
        f_ax, _, Sxx = spectrogram_lspopt(chunk, FS_OUT, nperseg=FS_OUT, noverlap=0, c_parameter=20.0)
        freq_mask  = (f_ax >= 0.5) & (f_ax <= 40)
        freqs_plot = f_ax[freq_mask]
        spec_db    = (10 * np.log10(Sxx[freq_mask, :] + 1e-10)).astype(np.float32)
        vmin = np.percentile(spec_db, 5)
        vmax = np.percentile(spec_db, 99)

        lfp_secs = np.arange(t0, t1)
        mov_idx  = (lfp_secs - video_sync_offset).astype(int)
        valid    = (mov_idx >= 0) & (mov_idx < len(mov_1hz))
        mov_seg  = np.where(valid, mov_1hz[np.clip(mov_idx, 0, len(mov_1hz)-1)], 0.0)
        mov_tmin = lfp_secs / 60.0

        fig, axes = plt.subplots(6, 1, figsize=(15, 16), sharex=True,
                                 gridspec_kw={'height_ratios': [3, 1.5, 1.5, 1, 1, 2]})
        fig.suptitle(f'{cfg["session"]}  —  {date_s}  {time_lbl}  (hour {hour+1})',
                     fontsize=13, fontweight='bold', y=1.005)

        x_ext  = [t0 / 60.0, t1 / 60.0]
        t_min  = t_seg  / 60.0
        tc_min = tc_seg / 60.0

        axes[0].imshow(spec_db, aspect='auto', origin='lower', cmap='jet',
                       extent=[x_ext[0], x_ext[1], freqs_plot[0], freqs_plot[-1]],
                       vmin=vmin, vmax=vmax)
        axes[0].set_ylabel('Freq [Hz]', fontsize=11)
        axes[0].set_title(f'Ch {cfg["lfp_ch"]}  —  Multitaper Spectrogram', fontsize=11, loc='left')
        axes[0].set_ylim(0, 40)

        axes[1].plot(tc_min, bsw_seg, color='#4a90d9', linewidth=0.8)
        axes[1].axhline(sw_thr, color='red', linestyle='--', linewidth=1.2, label=f'SW thr={sw_thr:.2f}')
        axes[1].set_ylabel('SW Power', fontsize=9)
        axes[1].legend(loc='upper right', fontsize=8, framealpha=0.7)

        axes[2].plot(tc_min, thr_seg, color='#9b59b6', linewidth=0.8)
        axes[2].axhline(th_thr, color='red', linestyle='--', linewidth=1.2, label=f'TH thr={th_thr:.2f}')
        axes[2].set_ylabel('Theta ratio', fontsize=9)
        axes[2].legend(loc='upper right', fontsize=8, framealpha=0.7)

        axes[3].plot(tc_min, mot_seg, color='#27ae60', linewidth=0.8)
        axes[3].axhline(mo_thr, color='red', linestyle='--', linewidth=1.2, label=f'EMG thr={mo_thr:.2f}')
        axes[3].set_ylabel('EMG', fontsize=9)
        axes[3].legend(loc='upper right', fontsize=8, framealpha=0.7)

        axes[4].fill_between(mov_tmin, mov_seg, alpha=0.6, color='steelblue')
        axes[4].axhline(mov_wake_thr, color='darkorange', linestyle='--', linewidth=1.2,
                        label=f'Wake thr={mov_wake_thr:.0f} px')
        axes[4].set_ylabel('Movement\n(px/frame)', fontsize=9)
        axes[4].set_title('Video Movement', fontsize=9, loc='left', pad=2)
        axes[4].legend(loc='upper right', fontsize=8, framealpha=0.7)

        ax = axes[5]
        for i in range(len(t_seg) - 1):
            s = int(st_seg[i])
            if s in STATE_Y:
                ax.fill_between([t_min[i], t_min[i+1]], STATE_Y[s] - 0.45, STATE_Y[s] + 0.45,
                                color=STATE_COL[s], linewidth=0)
        ax.set_yticks([0, 1, 2])
        ax.set_yticklabels(['NREM', 'REM', 'WAKE'], fontsize=10)
        ax.set_ylim(-0.6, 2.6)
        ax.set_ylabel('State', fontsize=11)
        ax.set_title('Hypnogram', fontsize=11, loc='left')
        state_patches = [mpatches.Patch(color=STATE_COL[k], label=STATE_LBL[k]) for k in [1, 3, 5]]
        state_legend = ax.legend(handles=state_patches, loc='upper right', ncol=3, fontsize=9, framealpha=0.7)
        ax.add_artist(state_legend)
        ax.set_xlabel('Time', fontsize=11)

        for a in axes:
            a.set_xlim(x_ext[0], x_ext[1])
            a.set_xticks([p / 60.0 for p in tick_pos])
            a.set_xticklabels(tick_lbl)
            a.grid(axis='x', linestyle='--', alpha=0.25)

        plotted = {}
        for t_sec, name, color in taste_events:
            t_min_f = t_sec / 60.0
            if x_ext[0] <= t_min_f <= x_ext[1]:
                for a in axes:
                    a.axvline(x=t_min_f, color=color, linestyle=':', linewidth=1.5, alpha=0.85)
                plotted[name] = color

        # LiCl injection marker -- solid black line; legend entry (not inline
        # text) so it doesn't collide with the spectrogram's title.
        licl_in_view = licl_time_s is not None and x_ext[0] <= licl_time_s / 60.0 <= x_ext[1]
        if licl_in_view:
            licl_min = licl_time_s / 60.0
            for a in axes:
                a.axvline(x=licl_min, color='black', linestyle='-', linewidth=2.2, alpha=0.9, zorder=10)

        if plotted or licl_in_view:
            legend_handles = [mpatches.Patch(color=c, label=n) for n, c in plotted.items()]
            if licl_in_view:
                legend_handles.append(mpl_lines.Line2D([0], [0], color='black', linewidth=2.2,
                                                         label='LiCl injection'))
            axes[5].legend(handles=legend_handles, loc='upper left', ncol=len(legend_handles),
                           fontsize=9, framealpha=0.7, title='Taste / event')

        plt.subplots_adjust(hspace=0.45)
        out = os.path.join(out_dir, f'{animal}_buz_{hour+1:02d}.png')
        fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f'  [{hour+1:02d}/{total_hours}]  {time_lbl}')

    print(f'\nDone. All files saved locally in:\n  {out_dir}')
    print('Copy to the NAS with, e.g.:')
    print(f'  cp {out_dir}/*.png "{cfg["out_dir"]}/"')


if __name__ == '__main__':
    main()
