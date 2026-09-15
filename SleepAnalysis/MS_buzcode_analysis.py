import h5py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import scipy.io as sio
from scipy import signal
from scipy.stats import gaussian_kde
from scipy.signal import find_peaks
from lspopt import spectrogram_lspopt
from datetime import datetime, timedelta
import os

# ── Config ────────────────────────────────────────────────────────────────────
MAT_FILE  = '/media/anan/diskh2/MS11/MS11_hab3/MS11_hab3.SleepState.states.mat'
LFP_MAT   = '/media/anan/diskh2/MS11/MS11_hab3/MS11_hab3.SleepScoreLFP.LFP.mat'
MOV_FILE  = '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Peleg/MS11/MS11_old_pipeline/data/11_VideoMovement.npy'
SYNC_FILE = '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Peleg/MS11/MS11_raw_data/MS11_hab3_g0_tcat.nidq.xd_0_7_0.txt'
TASTE_FILES = {
    'Water'  : '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Peleg/MS11/MS11_raw_data/MS11_hab3_g0_tcat.nidq.xd_0_1_0.txt',
    'Sucrose': '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Peleg/MS11/MS11_raw_data/MS11_hab3_g0_tcat.nidq.xd_0_2_0.txt',
    'Salt'   : '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Peleg/MS11/MS11_raw_data/MS11_hab3_g0_tcat.nidq.xd_0_3_0.txt',
    'Acid'   : '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Peleg/MS11/MS11_raw_data/MS11_hab3_g0_tcat.nidq.xd_0_4_0.txt',
}
TASTE_COLORS = {'Water': 'blue', 'Sucrose': 'orange', 'Salt': 'red', 'Acid': 'green'}

OUT_DIR   = '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Peleg/MS11/MS11_hab3_buzcode_analysis'
LFP_CH    = 65
FS_OUT    = 250
MOV_FPS   = 25
REC_START = datetime(2025, 5, 27, 9, 41, 49)

STATE_Y   = {1: 2,         3: 0,         5: 1}
STATE_COL = {1: '#e06c3a', 3: '#4a90d9', 5: '#5cb85c'}
STATE_LBL = {1: 'WAKE',   3: 'NREM',    5: 'REM'}

os.makedirs(OUT_DIR, exist_ok=True)

# ── Load buzcode metrics ──────────────────────────────────────────────────────
print('Loading SleepState...')
with h5py.File(MAT_FILE, 'r') as f:
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

# ── Load LFP (ch 65, 250 Hz) ─────────────────────────────────────────────────
print('Loading LFP...')
lfp_mat  = sio.loadmat(LFP_MAT, struct_as_record=False, squeeze_me=True)
lfp_data = lfp_mat['SleepScoreLFP'].thLFP.astype(np.float32)
print(f'  {lfp_data.shape[0]} samples  ({lfp_data.shape[0]/FS_OUT/3600:.2f} h at {FS_OUT} Hz)')

# ── Load video movement ───────────────────────────────────────────────────────
print('Loading video movement...')
mov_raw = np.load(MOV_FILE).astype(np.float32)
n_sec   = len(mov_raw) // MOV_FPS
mov_1hz = mov_raw[:n_sec * MOV_FPS].reshape(n_sec, MOV_FPS).mean(axis=1)
log_mov      = np.log1p(mov_1hz)
mov_wake_thr = float(np.expm1(log_mov.mean() + 1.5 * log_mov.std()))

# ── Video sync offset ─────────────────────────────────────────────────────────
with open(SYNC_FILE) as f:
    video_sync_offset = float(f.readline().strip())
print(f'  Video sync offset: {video_sync_offset:.1f} s')

# ── Taste events ──────────────────────────────────────────────────────────────
print('Loading taste events...')
taste_events = []
for name, path in TASTE_FILES.items():
    times = [float(l.strip()) for l in open(path) if l.strip()]
    for t_sec in times:
        taste_events.append((t_sec, t_sec / 60.0, name, TASTE_COLORS[name]))
    print(f'  {name}: {len(times)} events')

# ── Notch filter ──────────────────────────────────────────────────────────────
b_notch, a_notch = signal.iirnotch(50, 200, FS_OUT)

total_hours = int(np.ceil(t[-1] / 3600))


# ══════════════════════════════════════════════════════════════════════════════
#  PART 1 — 3 separate distribution PNGs
# ══════════════════════════════════════════════════════════════════════════════
print(f'\n[1/2] Saving metric distribution plots...')

dist_cfg = [
    ('SW_distribution',     bsw,     sw_thr, '#4a90d9', 'Slow Wave Power',       'NREM',    'Wake / REM'),
    ('Theta_distribution',  thratio, th_thr, '#9b59b6', 'Theta Ratio',           'Low θ',   'REM'),
    ('Motion_distribution', motion,  mo_thr, '#27ae60', 'Motion (EMG from LFP)', 'Still',   'Moving / Wake'),
]

for fname, data, thresh, clr, title, ll, rl in dist_cfg:
    fig, ax = plt.subplots(figsize=(8, 5), facecolor='white')
    fig.suptitle(f'MS11_hab3  —  {title}\n'
                 f'WAKE {wake_pct:.1f}%   NREM {nrem_pct:.1f}%   REM {rem_pct:.1f}%',
                 fontsize=12, fontweight='bold')

    data_clean = data[np.isfinite(data)]
    counts, edges = np.histogram(data_clean, bins=55, range=(0, 1), density=False)
    counts  = counts / counts.sum()
    centers = (edges[:-1] + edges[1:]) / 2
    width   = edges[1] - edges[0]
    c_rgb   = np.array(plt.matplotlib.colors.to_rgb(clr))
    c_light = c_rgb * 0.4 + 0.6

    ax.bar(centers[centers <= thresh], counts[centers <= thresh],
           width=width, color=c_rgb,   alpha=0.75)
    ax.bar(centers[centers >= thresh], counts[centers >= thresh],
           width=width, color=c_light, alpha=0.60)

    kde   = gaussian_kde(data_clean, bw_method=0.07)
    x_kde = np.linspace(0, 1, 600)
    y_kde = kde(x_kde) * width
    ax.plot(x_kde, y_kde, color=c_rgb * 0.5, linewidth=2.2, zorder=5)

    peaks, _ = find_peaks(y_kde, prominence=y_kde.max() * 0.08, distance=25)
    for p in peaks:
        ax.axvline(x_kde[p], color='#444', linestyle='--', linewidth=1.1, alpha=0.7)
        ax.text(x_kde[p], y_kde[p] * 1.07, f'{x_kde[p]:.2f}',
                ha='center', va='bottom', fontsize=9, color='#333')

    y_top = max(counts.max(), y_kde.max()) * 1.4
    ax.set_ylim(0, y_top)
    ax.axvline(thresh, color='#c0392b', linewidth=2.2, zorder=6)
    ax.text(thresh + 0.02, y_top * 0.93, f'thr\n{thresh:.2f}',
            color='#c0392b', fontsize=9, fontweight='bold', va='top')
    ax.text(thresh * 0.5,            y_top * 0.80, ll, ha='center',
            fontsize=11, fontweight='bold', color=c_rgb * 0.55)
    ax.text(thresh + (1-thresh)*0.5, y_top * 0.80, rl, ha='center',
            fontsize=11, fontweight='bold', color=c_light * 0.65)

    ax.set_xlabel('Normalized value (0 → 1)', fontsize=11)
    ax.set_ylabel('Proportion of time', fontsize=11)
    ax.set_xlim(0, 1)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.2)
    plt.tight_layout()

    out = os.path.join(OUT_DIR, f'{fname}.png')
    fig.savefig(out, dpi=180, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'  Saved → {out}')


# ══════════════════════════════════════════════════════════════════════════════
#  PART 2 — Hourly hypnograms (exactly like plot_hypnogram_presentation.py)
# ══════════════════════════════════════════════════════════════════════════════
print(f'\n[2/2] Plotting {total_hours} hourly hypnograms...')

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

    # Real clock labels
    hour_start = REC_START + timedelta(seconds=t0)
    hour_end   = REC_START + timedelta(seconds=t1)
    tick_minutes = range(0, 61, 10)
    x_tick_pos   = [t0 + m * 60 for m in tick_minutes]
    x_tick_lbl   = [(REC_START + timedelta(seconds=p)).strftime('%H:%M') for p in x_tick_pos]
    date_s   = hour_start.strftime('%Y-%m-%d')
    time_lbl = f"{hour_start.strftime('%H:%M')} – {hour_end.strftime('%H:%M')}"

    # LFP spectrogram slice
    s0 = t0 * FS_OUT
    s1 = min(t1 * FS_OUT, len(lfp_data))
    chunk = signal.filtfilt(b_notch, a_notch, lfp_data[s0:s1]).astype(np.float32)
    f_ax, _, Sxx = spectrogram_lspopt(chunk, FS_OUT, nperseg=FS_OUT, noverlap=0, c_parameter=20.0)
    freq_mask  = (f_ax >= 0.5) & (f_ax <= 40)
    freqs_plot = f_ax[freq_mask]
    spec_db    = (10 * np.log10(Sxx[freq_mask, :] + 1e-10)).astype(np.float32)
    vmin = np.percentile(spec_db, 5)
    vmax = np.percentile(spec_db, 99)

    # Video movement slice
    lfp_secs = np.arange(t0, t1)
    mov_idx  = (lfp_secs - video_sync_offset).astype(int)
    valid    = (mov_idx >= 0) & (mov_idx < len(mov_1hz))
    mov_seg  = np.where(valid, mov_1hz[np.clip(mov_idx, 0, len(mov_1hz)-1)], 0.0)
    mov_tmin = lfp_secs / 60.0

    # Figure — 6 panels
    fig, axes = plt.subplots(6, 1, figsize=(15, 16), sharex=True,
                             gridspec_kw={'height_ratios': [3, 1.5, 1.5, 1, 1, 2]})
    fig.suptitle(f'MS11_hab3  —  {date_s}  {time_lbl}  (hour {hour+1})',
                 fontsize=13, fontweight='bold', y=1.005)

    x_ext = [t0 / 60.0, t1 / 60.0]
    t_min  = t_seg  / 60.0
    tc_min = tc_seg / 60.0

    # 1. Multitaper spectrogram
    ax = axes[0]
    ax.imshow(spec_db, aspect='auto', origin='lower', cmap='jet',
              extent=[x_ext[0], x_ext[1], freqs_plot[0], freqs_plot[-1]],
              vmin=vmin, vmax=vmax)
    ax.set_ylabel('Freq [Hz]', fontsize=11)
    ax.set_title(f'Ch {LFP_CH}  —  Multitaper Spectrogram', fontsize=11, loc='left')
    ax.set_ylim(0, 40)

    # 2. Broadband SW power
    ax = axes[1]
    ax.plot(tc_min, bsw_seg, color='#4a90d9', linewidth=0.8)
    ax.axhline(sw_thr, color='red', linestyle='--', linewidth=1.2,
               label=f'SW thr = {sw_thr:.2f}')
    ax.set_ylabel('SW Power', fontsize=9)
    ax.set_title('Broadband Slow-Wave Power', fontsize=9, loc='left', pad=2)
    ax.legend(loc='upper right', fontsize=8, framealpha=0.7)

    # 3. Theta ratio
    ax = axes[2]
    ax.plot(tc_min, thr_seg, color='#9b59b6', linewidth=0.8)
    ax.axhline(th_thr, color='red', linestyle='--', linewidth=1.2,
               label=f'TH thr = {th_thr:.2f}')
    ax.set_ylabel('Theta ratio', fontsize=9)
    ax.set_title('Theta / Broadband Ratio  [5–10 Hz]', fontsize=9, loc='left', pad=2)
    ax.legend(loc='upper right', fontsize=8, framealpha=0.7)

    # 4. EMG / motion
    ax = axes[3]
    ax.plot(tc_min, mot_seg, color='#27ae60', linewidth=0.8)
    ax.axhline(mo_thr, color='red', linestyle='--', linewidth=1.2,
               label=f'EMG thr = {mo_thr:.2f}')
    ax.set_ylabel('EMG', fontsize=9)
    ax.legend(loc='upper right', fontsize=8, framealpha=0.7)

    # 5. Video movement
    ax = axes[4]
    ax.fill_between(mov_tmin, mov_seg, alpha=0.6, color='steelblue')
    ax.axhline(mov_wake_thr, color='darkorange', linestyle='--', linewidth=1.2,
               label=f'Wake thr = {mov_wake_thr:.0f} px')
    ax.set_ylabel('Movement\n(px/frame)', fontsize=9)
    ax.set_title('Video Movement', fontsize=9, loc='left', pad=2)
    ax.legend(loc='upper right', fontsize=8, framealpha=0.7)

    # 6. Hypnogram
    ax = axes[5]
    for i in range(len(t_seg) - 1):
        s = int(st_seg[i])
        if s in STATE_Y:
            ax.fill_between([t_min[i], t_min[i+1]],
                            STATE_Y[s] - 0.45, STATE_Y[s] + 0.45,
                            color=STATE_COL[s], linewidth=0)
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(['NREM', 'REM', 'WAKE'], fontsize=10)
    ax.set_ylim(-0.6, 2.6)
    ax.set_ylabel('State', fontsize=11)
    ax.set_title('Hypnogram', fontsize=11, loc='left')
    patches = [mpatches.Patch(color=STATE_COL[k], label=STATE_LBL[k]) for k in [1, 3, 5]]
    ax.legend(handles=patches, loc='upper right', ncol=3, fontsize=9, framealpha=0.7)
    ax.set_xlabel('Time', fontsize=11)

    # Shared x-axis
    for ax in axes:
        ax.set_xlim(x_ext[0], x_ext[1])
        ax.set_xticks([p / 60.0 for p in x_tick_pos])
        ax.set_xticklabels(x_tick_lbl)
        ax.grid(axis='x', linestyle='--', alpha=0.25)

    # Taste events
    plotted = {}
    for t_sec, t_min_ev, name, color in taste_events:
        t_min_ev_f = t_sec / 60.0
        if x_ext[0] <= t_min_ev_f <= x_ext[1]:
            for ax in axes:
                ax.axvline(x=t_min_ev_f, color=color, linestyle=':', linewidth=1.5, alpha=0.85)
            plotted[name] = color
    if plotted:
        taste_patches = [mpatches.Patch(color=c, label=n) for n, c in plotted.items()]
        axes[5].legend(handles=taste_patches, loc='upper left', ncol=len(plotted),
                       fontsize=9, framealpha=0.7, title='Taste')

    plt.subplots_adjust(hspace=0.45)
    out = os.path.join(OUT_DIR, f'MS11_buz_{hour+1:02d}.png')
    fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'  [{hour+1:02d}/{total_hours}]  {time_lbl}')

print(f'\nDone. All files in:\n  {OUT_DIR}')
