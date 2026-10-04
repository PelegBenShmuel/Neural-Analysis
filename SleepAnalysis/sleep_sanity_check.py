"""
Sanity check for buzcode sleep-scoring output — run this BEFORE trusting a
session's WAKE/NREM/REM states for any downstream (e.g. GC neural) analysis.

Answers, in plain numbers, five questions:
  1. Coverage    — how much of the recording is actually scored (vs. undefined,
                   state 0)?
  2. Proportions — are WAKE/NREM/REM percentages in the range expected for a
                   rat, or does something look broken?
  3. Bouts       — are state bouts physiologically plausible durations, or is
                   the scoring flickering (many <10s bouts)?
  4. Cross-checks — do independent signals (video movement, taste-delivery
                   timing) agree with what buzcode calls WAKE? Taste is only
                   delivered to an awake animal, so taste events landing in
                   NREM/REM would indicate a timestamp/state misalignment.
  5. REM plausibility — REM sleep is defined by cortical activation (theta)
                   *combined with* muscle atonia, so real REM bouts should
                   look like NREM (low movement), not WAKE, on an independent
                   movement signal. Checks buzcode's own EMG-from-LFP metric
                   and the separate video-movement trace against the states
                   buzcode assigned, to see whether "REM" epochs are actually
                   quiescent or whether they look like mislabeled active WAKE.

Prints a plain-text report and saves one summary figure
(<animal>_sanity_check.png: hourly state composition + bout-duration
histograms) to OUT_DIR.

Usage: python sleep_sanity_check.py [ANIMAL]   (default: MS08)
"""
import sys
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

# ── Per-animal config ─────────────────────────────────────────────────────────
NAS_MAI   = '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Mai'
NAS_PELEG = '/run/user/1005/gvfs/smb-share:server=anannas,share=data/Peleg'

ANIMALS = {
    'MS08': dict(
        session   = 'MS08_hab3toExp',
        mat_file  = '/media/anan/diskh2/MS08/MS08_hab3toExp/MS08_hab3toExp.SleepState.states.mat',
        sync_file = f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_MAI}/MS08/MS08_hab3toExp_g1/MS08_hab3toExp_g1_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS08/MS08_buzcode_analysis',
        video_file = '/media/anan/diskh2/MS08/MS08_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS09': dict(
        session   = 'MS09_hab3_ext',
        mat_file  = '/media/anan/diskh2/MS09/MS09_hab3_ext/MS09_hab3_ext.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_hab3_ext_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS09/MS09_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS09/MS_09_Raw_Data/MS09_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS25': dict(
        session   = 'MS25_hab3toExt',
        mat_file  = '/media/anan/diskh2/MS25/MS25_hab3toExt/MS25_hab3toExt.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS25/MS25_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS24_CTAtoExt': dict(
        session   = 'MS24_CTAtoExt',
        mat_file  = '/media/anan/diskh2/MS24/MS24_CTAtoExt/MS24_CTAtoExt.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS24/MS24_CTAtoExt_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS24_hab3toExt': dict(
        session   = 'MS24_hab3toExt',
        mat_file  = '/media/anan/diskh2/MS24/MS24_hab3toExt/MS24_hab3toExt.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS24/MS24_hab3toExt_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_hab3toExt_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS23': dict(
        session   = 'MS23_hab3toExt',
        mat_file  = '/media/anan/diskh2/MS23/MS23_hab3toExt/MS23_hab3toExt.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS23/MS23_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS22': dict(
        session   = 'MS22_hab3toExt',
        mat_file  = '/media/anan/diskh2/MS22/MS22_hab3toExt/MS22_hab3toExt.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS22/MS_22_Raw_Data/MS22_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS22/MS_22_Raw_Data/MS22_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS22/MS_22_Raw_Data/MS22_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS22/MS_22_Raw_Data/MS22_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS22/MS_22_Raw_Data/MS22_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS22/MS22_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS22/MS_22_Raw_Data/MS22_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS21': dict(
        session   = 'MS21_hab3toExt',
        mat_file  = '/media/anan/diskh2/MS21/MS21_hab3toExt/MS21_hab3toExt.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS21/MS21_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS20': dict(
        session   = 'MS20_hab3toExt',
        mat_file  = '/media/anan/diskh2/MS20/MS20_hab3toExt/MS20_hab3toExt.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS20/MS_20_Raw_Data/MS20_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS20/MS_20_Raw_Data/MS20_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS20/MS_20_Raw_Data/MS20_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS20/MS_20_Raw_Data/MS20_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS20/MS_20_Raw_Data/MS20_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS20/MS20_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS20/MS_20_Raw_Data/MS20_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS18': dict(
        session   = 'MS18_hab3toExt',
        mat_file  = '/media/anan/diskh2/MS18/MS18_hab3toExt/MS18_hab3toExt.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS18/MS_18_Raw_Data/MS18_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS18/MS_18_Raw_Data/MS18_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS18/MS_18_Raw_Data/MS18_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS18/MS_18_Raw_Data/MS18_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS18/MS_18_Raw_Data/MS18_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS18/MS18_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS18/MS_18_Raw_Data/MS18_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS15': dict(
        session   = 'MS15_hab3toExt',
        mat_file  = '/media/anan/diskh2/MS15/MS15_hab3toExt/MS15_hab3toExt.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS15/MS_15_Raw_Data/MS15_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS15/MS_15_Raw_Data/MS15_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS15/MS_15_Raw_Data/MS15_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS15/MS_15_Raw_Data/MS15_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS15/MS_15_Raw_Data/MS15_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS15/MS15_buzcode_analysis',
        # No video_file: MS15 has no video (confirmed by Mai) -- REM
        # plausibility check falls back to EMG-from-LFP only.
    ),
    'MS21_manualTH': dict(
        session   = 'MS21_hab3toExt_manualTH',
        mat_file  = '/media/anan/diskh2/MS21/MS21_hab3toExt_manualTH/MS21_hab3toExt_manualTH.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS21/MS21_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS21_videocorr': dict(
        session   = 'MS21_hab3toExt_manualTH_videocorr',
        mat_file  = '/media/anan/diskh2/MS21/MS21_hab3toExt_manualTH/MS21_hab3toExt_manualTH_videocorr.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS21/MS21_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS21/MS_21_Raw_Data/MS21_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS23_videocorr': dict(
        session   = 'MS23_hab3toExt_manualTH_videocorr',
        mat_file  = '/media/anan/diskh2/MS23/MS23_hab3toExt_manualTH/MS23_hab3toExt_manualTH_videocorr.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS23/MS23_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS25_manualTH_videocorr': dict(
        session   = 'MS25_manualTH_videocorr',
        mat_file  = '/media/anan/diskh2/MS25/MS25_hab3toExt_manualTH/MS25_manualTH_videocorr.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS25/MS25_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS25_videocorr': dict(
        session   = 'MS25_hab3toExt_videocorr',
        mat_file  = '/media/anan/diskh2/MS25/MS25_hab3toExt/MS25_hab3toExt_videocorr.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS25/MS25_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS24_CTAtoExt_videocorr': dict(
        session   = 'MS24_CTAtoExt_manualTH_videocorr',
        mat_file  = '/media/anan/diskh2/MS24/MS24_CTAtoExt_manualTH/MS24_CTAtoExt_manualTH_videocorr.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS24/MS24_CTAtoExt_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS14_videocorr': dict(
        session   = 'MS14_hab3toExt_manualTH_videocorr',
        mat_file  = '/media/anan/diskh2/MS14/MS14_hab3toExt_manualTH/MS14_hab3toExt_manualTH_videocorr.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_7_0.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS14/MS14_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS23_manualTH': dict(
        session   = 'MS23_hab3toExt_manualTH',
        mat_file  = '/media/anan/diskh2/MS23/MS23_hab3toExt_manualTH/MS23_hab3toExt_manualTH.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS23/MS23_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS23/MS_23_Raw_Data/MS23_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS24_CTAtoExt_manualTH': dict(
        session   = 'MS24_CTAtoExt_manualTH',
        mat_file  = '/media/anan/diskh2/MS24/MS24_CTAtoExt_manualTH/MS24_CTAtoExt_manualTH.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS24/MS24_CTAtoExt_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS24/MS_24_Raw_Data/MS24_CTAtoExt_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS25_manualTH': dict(
        session   = 'MS25_manualTH',
        mat_file  = '/media/anan/diskh2/MS25/MS25_hab3toExt_manualTH/MS25_manualTH.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_7_0_corr.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS25/MS25_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS25/MS_25_Raw_Data/MS25_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS14_manualTH': dict(
        session   = 'MS14_hab3toExt_manualTH',
        mat_file  = '/media/anan/diskh2/MS14/MS14_hab3toExt_manualTH/MS14_hab3toExt_manualTH.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_7_0.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS14/MS14_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS14': dict(
        session   = 'MS14_hab3toExt',
        mat_file  = '/media/anan/diskh2/MS14/MS14_hab3toExt/MS14_hab3toExt.SleepState.states.mat',
        # xd_0_7_0_corr.txt is truncated (61,844s of 262,452s) -- use the
        # complete uncorrected file instead (frame k = pulse k for the
        # _clean video), per project_data_collection_2026_09 memory.
        sync_file = f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_7_0.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_1_0_corr.txt',
            'Sucrose': f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_2_0_corr.txt',
            'Salt'   : f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_3_0_corr.txt',
            'Acid'   : f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_hab3toExt_g0_tcat.nidq.xd_0_4_0_corr.txt',
        },
        out_dir = f'{NAS_PELEG}/MS14/MS14_buzcode_analysis',
        video_file = f'{NAS_PELEG}/MS14/MS_14_Raw_Data/MS14_VideoMovement.npy',
        mov_fps = 25,
    ),
    'MS11': dict(
        session   = 'MS11_hab3',
        mat_file  = '/media/anan/diskh2/MS11/MS11_hab3/MS11_hab3.SleepState.states.mat',
        sync_file = f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_7_0.txt',
        taste_files = {
            'Water'  : f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_1_0.txt',
            'Sucrose': f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_2_0.txt',
            'Salt'   : f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_3_0.txt',
            'Acid'   : f'{NAS_PELEG}/MS11/MS_11_Raw_Data/MS11_hab3_g0_tcat.nidq.xd_0_4_0.txt',
        },
        out_dir = f'{NAS_PELEG}/MS11/MS11_buzcode_analysis',
        # No video_file: MS11's video-movement .npy is missing on both shares
        # (the old_pipeline path it used to live at is gone after the
        # raw-data reorg) -- REM plausibility check falls back to EMG-from-LFP
        # only. Flagged to Peleg 2026-09-16, not recomputed without asking
        # (VideoMovement.py can regenerate it from MS_11_Raw_Data's raw .mp4
        # if wanted -- that's a real compute job on a ~73h video, not a quick step).
    ),
}

# Expected ranges for a rat over a multi-day recording (Watson/Buzsaki-lab
# rodent norms) — flags, not hard failures.
EXPECTED_PCT = {'WAKE': (35, 60), 'NREM': (35, 60), 'REM': (3, 15)}
FLICKER_S    = 10   # bouts shorter than this are suspect (scoring noise)

STATE_CODE = {'WAKE': 1, 'NREM': 3, 'REM': 5}
STATE_COL  = {'WAKE': '#e06c3a', 'NREM': '#4a90d9', 'REM': '#5cb85c'}


def load_states(mat_file):
    with h5py.File(mat_file, 'r') as f:
        t       = np.array(f['SleepState/idx/timestamps']).flatten()
        states  = np.array(f['SleepState/idx/states']).flatten()
        bouts   = {name: np.array(f[f'SleepState/ints/{name}state'])
                   for name in STATE_CODE}
        metrics = f['SleepState/detectorinfo/detectionparms/SleepScoreMetrics']
        t_clus  = np.array(metrics['t_clus']).flatten()
        motion  = np.array(metrics['motiondata']).flatten()
        mo_thr  = float(np.array(metrics['histsandthreshs/MotionThresh']).flatten()[0])
        th_thr  = float(np.array(metrics['histsandthreshs/THthresh']).flatten()[0])
        th_chan = float(np.array(metrics['THchanID']).flatten()[0])
    return t, states, bouts, t_clus, motion, mo_thr, th_thr, th_chan


def check_theta_threshold(th_thr, th_chan):
    """buzcode's ClusterStates_GetMetrics.m hard-codes THthresh=0 (and never
    recomputes REMtimes for that branch -- the recompute line is commented
    out in buzcode's own source) when it can't find a bimodal split in the
    theta-ratio histogram, even after widening bins and retrying with NREM
    excluded. THthresh=0 means the 'thratio > THthresh' REM criterion is
    satisfied by essentially every sample (thratio is a positive ratio), so
    REM silently degenerates to 'not moving AND low SW power' -- no real
    theta signal involved at all. Check this FIRST: if it fires, nothing
    downstream that depends on REM (proportions, bout stats, even the
    EMG/video 'plausibility' checks, which only confirm REM-time is quiet --
    already guaranteed by construction, not an independent check) actually
    validates REM electrophysiologically.
    """
    print('── 0. Theta threshold (does REM mean anything here?) ────────')
    print(f'  Theta channel {th_chan:.0f}, THthresh={th_thr:.4f}')
    if th_thr == 0:
        print('  [FLAG] THthresh is exactly 0 -- buzcode never found a real '
              'bimodal split in the theta ratio and fell back to its hard-coded '
              'default. REM is NOT validated by any theta signal here -- it is '
              'just "not moving and low SW power" by elimination. Treat REM '
              '(and anything downstream that depends on it) as unreliable '
              'regardless of how plausible the overall proportions look.')
    else:
        print('  [OK] Nonzero threshold -- a real bimodal split was found.')


def check_coverage(t, states):
    print('── 1. Coverage ──────────────────────────────────────────────')
    dur_h = t[-1] / 3600
    dt = np.diff(t, append=t[-1])
    undefined_s = dt[states == 0].sum()
    print(f'  Recording span   : {dur_h:.2f} h ({len(t)} samples)')
    print(f'  Undefined (0)    : {undefined_s/3600:.2f} h '
          f'({100*undefined_s/t[-1]:.1f}% of recording)')
    if undefined_s / t[-1] > 0.10:
        print('  [FLAG] >10% of the recording is unscored — check for LFP '
              'dropouts or a broken SW/Theta channel before trusting the rest.')
    else:
        print('  [OK] Unscored fraction is small.')
    return dur_h


def check_proportions(t, states):
    print('\n── 2. State proportions ─────────────────────────────────────')
    dt = np.diff(t, append=t[-1])
    pct = {}
    for name, code in STATE_CODE.items():
        pct[name] = 100 * dt[states == code].sum() / t[-1]
    for name in STATE_CODE:
        lo, hi = EXPECTED_PCT[name]
        flag = '' if lo <= pct[name] <= hi else '  [FLAG outside typical range]'
        print(f'  {name:5s}: {pct[name]:5.1f}%   (typical rat range {lo}-{hi}%){flag}')
    ratio = pct['NREM'] / pct['REM'] if pct['REM'] > 0 else np.inf
    print(f'  NREM:REM ratio    : {ratio:.1f} (typical rat range ~4-8)')
    if not (3 <= ratio <= 10):
        print('  [FLAG] NREM:REM ratio outside the usual range — check REM '
              'detection (theta channel/threshold) specifically.')
    return pct


def check_bouts(bouts):
    print('\n── 3. Bout durations ────────────────────────────────────────')
    durations = {}
    for name in STATE_CODE:
        iv = bouts[name]
        d = np.atleast_1d(iv[1] - iv[0]) if iv.size else np.array([])
        durations[name] = d
        if len(d) == 0:
            print(f'  {name:5s}:    0 bouts')
            print(f'  [FLAG] {name} has zero bouts for the whole recording — '
                  'the theta/SW channel or threshold is almost certainly wrong.')
            continue
        n_flicker = int((d < FLICKER_S).sum())
        print(f'  {name:5s}: {len(d):4d} bouts | median {np.median(d):6.1f}s '
              f'| mean {d.mean():6.1f}s | max {d.max()/60:5.1f}min | '
              f'{n_flicker} bouts <{FLICKER_S}s ({100*n_flicker/len(d):.1f}%)')
        if n_flicker / len(d) > 0.25:
            print(f'  [FLAG] >25% of {name} bouts are <{FLICKER_S}s — scoring '
                  'may be flickering rather than resolving real bouts.')
    return durations


def check_taste_alignment(t, states, sync_file, taste_files):
    print('\n── 4. Cross-check: taste events vs. state ───────────────────')
    if not (os.path.exists(sync_file) and all(os.path.exists(p) for p in taste_files.values())):
        print('  [SKIPPED] taste/sync files not reachable from this machine '
              '(NAS not mounted?).')
        return
    with open(sync_file) as f:
        offset = float(f.readline().strip())

    # states are sampled ~1/s starting at t[0]; nearest-sample lookup
    def state_at(t_sec):
        idx = np.searchsorted(t, t_sec)
        idx = np.clip(idx, 0, len(t) - 1)
        return states[idx]

    total, in_wake = 0, 0
    for name, path in taste_files.items():
        times = [float(l.strip()) for l in open(path) if l.strip()]
        st = [state_at(tt) for tt in times]
        n_wake = sum(1 for s in st if s == STATE_CODE['WAKE'])
        n_sleep = sum(1 for s in st if s in (STATE_CODE['NREM'], STATE_CODE['REM']))
        print(f'  {name:8s}: {len(times):4d} deliveries | {n_wake} in WAKE, '
              f'{n_sleep} in NREM/REM, {len(times)-n_wake-n_sleep} unscored')
        total += len(times)
        in_wake += n_wake
    pct_wake = 100 * in_wake / total if total else 0
    print(f'  Overall: {pct_wake:.1f}% of taste deliveries fall in WAKE.')
    if pct_wake < 90:
        print('  [FLAG] Taste is normally delivered to an awake, engaged '
              'animal — a large fraction landing outside WAKE suggests a '
              'timestamp offset between the states clock and the taste '
              'events clock, not necessarily a real sleep-deprived delivery.')
    else:
        print('  [OK] Taste events line up with WAKE as expected — the '
              'states clock and event clock agree.')


def check_rem_plausibility(t, states, t_clus, motion, mo_thr, video_file, mov_fps,
                            sync_file):
    print('\n── 5. REM plausibility: movement cross-check ────────────────')

    # (a) buzcode's own EMG-from-LFP metric, already computed at t_clus times
    def nearest(ref_t, query_t, values):
        idx = np.searchsorted(ref_t, query_t)
        idx = np.clip(idx, 0, len(ref_t) - 1)
        return values[idx]

    motion_at_state_t = nearest(t_clus, t, motion)
    print('  EMG-from-LFP motion metric by state (0=still, 1=moving; '
          f'WAKE threshold={mo_thr:.2f}):')
    med = {}
    for name, code in STATE_CODE.items():
        vals = motion_at_state_t[states == code]
        med[name] = np.median(vals) if len(vals) else np.nan
        print(f'    {name:5s}: median {med[name]:.3f}  '
              f'(mean {vals.mean():.3f}, n={len(vals)})' if len(vals) else
              f'    {name:5s}: no samples (0 bouts)')
    if len(motion_at_state_t[states == STATE_CODE["REM"]]) == 0:
        print('  [SKIPPED] REM has zero samples -- nothing to cross-check.')
    elif med['REM'] > 0.5 * (med['WAKE'] + med['NREM']):
        print('  [FLAG] REM epochs have EMG-motion closer to WAKE than NREM — '
              'expected muscle atonia during REM is not showing up; these '
              '"REM" bouts may actually be mislabeled brief WAKE.')
    else:
        print('  [OK] REM epochs look quiescent (EMG-motion close to NREM), '
              'consistent with real REM muscle atonia rather than mislabeled WAKE.')

    # (b) independent video movement signal, if reachable
    if video_file is None:
        print('  [SKIPPED] no video_file configured for this animal -- only '
              'the EMG-from-LFP cross-check above is available.')
        return
    if not (os.path.exists(video_file) and os.path.exists(sync_file)):
        print('  [SKIPPED] video/sync files not reachable from this machine.')
        return
    with open(sync_file) as f:
        offset = float(f.readline().strip())
    mov_raw = np.load(video_file).astype(np.float32)
    n_sec = len(mov_raw) // mov_fps
    mov_1hz = mov_raw[:n_sec * mov_fps].reshape(n_sec, mov_fps).mean(axis=1)
    log_mov = np.log1p(mov_1hz)
    mov_wake_thr = float(np.expm1(log_mov.mean() + 1.5 * log_mov.std()))

    idx = (t - offset).astype(int)
    valid = (idx >= 0) & (idx < len(mov_1hz))
    mov_at_t = np.where(valid, mov_1hz[np.clip(idx, 0, len(mov_1hz) - 1)], np.nan)

    print(f'\n  Video movement by state (px/frame; WAKE threshold='
          f'{mov_wake_thr:.0f}):')
    vmed = {}
    for name, code in STATE_CODE.items():
        vals = mov_at_t[(states == code) & valid]
        vmed[name] = np.median(vals) if len(vals) else np.nan
        pct_above_wake_thr = 100 * (vals > mov_wake_thr).sum() / len(vals) if len(vals) else np.nan
        print(f'    {name:5s}: median {vmed[name]:6.1f}  '
              f'({pct_above_wake_thr:.1f}% of time above WAKE threshold, n={len(vals)})')
    if len(mov_at_t[(states == STATE_CODE["REM"]) & valid]) == 0:
        print('  [SKIPPED] REM has zero samples -- nothing to cross-check.')
    elif vmed['REM'] > 0.5 * (vmed['WAKE'] + vmed['NREM']):
        print('  [FLAG] REM epochs move nearly as much as WAKE on video — '
              'independent confirmation that these REM bouts look like '
              'active behavior, not real muscle-atonia REM.')
    else:
        print('  [OK] REM epochs are as still as NREM on video — independent '
              'confirmation that these are physiologically plausible REM bouts, '
              'even though they are short.')


def check_rem_fragmentation(bouts, states, t, merge_gap_s=30):
    print('\n── 6. REM bout fragmentation ─────────────────────────────────')
    iv = bouts['REM']
    starts_raw = np.atleast_1d(iv[0]) if iv.size else np.array([])
    stops_raw  = np.atleast_1d(iv[1]) if iv.size else np.array([])
    if len(starts_raw) < 2:
        print(f'  [SKIPPED] only {len(starts_raw)} REM bout(s) -- no inter-bout '
              'gaps to check.')
        return starts_raw  # 0 or 1 bout: nothing to fragment/merge
    order = np.argsort(starts_raw)
    starts, stops = starts_raw[order], stops_raw[order]
    n = len(starts)
    gaps = starts[1:] - stops[:-1]
    print(f'  {n} REM bouts, {n-1} inter-bout gaps.')
    print(f'  Gap to next REM bout: median {np.median(gaps):.1f}s, '
          f'{100*(gaps < merge_gap_s).sum()/len(gaps):.1f}% are <{merge_gap_s}s.')

    def state_at(t_sec):
        idx = np.searchsorted(t, t_sec)
        return states[np.clip(idx, 0, len(t) - 1)]

    # Merge consecutive REM bouts whose gap is short AND entirely NREM/undefined
    # (never WAKE) -- a real WAKE interruption argues against "one continuous
    # quiescent period", a brief NREM-only gap is consistent with the
    # threshold noisily dipping mid-episode.
    merged_starts, merged_stops = [starts[0]], [stops[0]]
    n_merged = 0
    for i in range(1, n):
        gap = starts[i] - merged_stops[-1]
        gap_samples = np.arange(int(merged_stops[-1]), int(starts[i]))
        gap_is_wake = len(gap_samples) > 0 and np.any(state_at(gap_samples) == STATE_CODE['WAKE'])
        if gap < merge_gap_s and not gap_is_wake:
            merged_stops[-1] = stops[i]
            n_merged += 1
        else:
            merged_starts.append(starts[i])
            merged_stops.append(stops[i])

    merged_dur = np.array(merged_stops) - np.array(merged_starts)
    orig_dur = stops - starts
    print(f'  Merging bouts separated by <{merge_gap_s}s of pure NREM/undefined '
          f'(never WAKE) folds {n_merged} gaps, leaving {len(merged_dur)} '
          f'"episodes":')
    print(f'    Before merge: median {np.median(orig_dur):.1f}s, '
          f'mean {orig_dur.mean():.1f}s (n={len(orig_dur)})')
    print(f'    After merge : median {np.median(merged_dur):.1f}s, '
          f'mean {merged_dur.mean():.1f}s (n={len(merged_dur)})')
    if np.median(merged_dur) > 3 * np.median(orig_dur) and np.median(merged_dur) >= 60:
        print('  [FINDING] Merged episode durations look much more physiologically '
              'normal (approaching the 1-3+ min range) — the short raw bout '
              'durations are likely an artifact of the threshold briefly dipping '
              'mid-episode, not truly separate micro-REM events.')
    else:
        print('  [FINDING] Merging nearby bouts does not substantially change '
              'typical durations — these look like genuinely separate short '
              'REM episodes rather than one fragmented period.')
    return merged_dur


def plot_summary(animal, t, states, durations, out_dir):
    total_hours = int(np.ceil(t[-1] / 3600))
    hourly = np.zeros((total_hours, 3))
    dt = np.diff(t, append=t[-1])
    hour_idx = (t // 3600).astype(int)
    for i, name in enumerate(STATE_CODE):
        code = STATE_CODE[name]
        mask = states == code
        for h in range(total_hours):
            hourly[h, i] = dt[mask & (hour_idx == h)].sum() / 3600 * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), facecolor='white')

    bottom = np.zeros(total_hours)
    for i, name in enumerate(STATE_CODE):
        ax1.bar(np.arange(1, total_hours + 1), hourly[:, i], bottom=bottom,
                color=STATE_COL[name], width=0.9, label=name)
        bottom += hourly[:, i]
    ax1.set_xlabel('Hour of recording')
    ax1.set_ylabel('% of hour')
    ax1.set_title(f'{animal} — hourly state composition (sanity view)')
    ax1.legend(loc='upper right', ncol=3, framealpha=0.8)
    ax1.set_xlim(0.5, total_hours + 0.5)
    ax1.set_ylim(0, 100)

    for name in STATE_CODE:
        ax2.hist(durations[name], bins=np.logspace(0, 3.5, 40),
                  color=STATE_COL[name], alpha=0.6, label=name)
    ax2.set_xscale('log')
    ax2.axvline(FLICKER_S, color='k', linestyle='--', linewidth=1,
                label=f'{FLICKER_S}s flicker cutoff')
    ax2.set_xlabel('Bout duration (s, log scale)')
    ax2.set_ylabel('Count')
    ax2.set_title('Bout-duration distributions')
    ax2.legend()

    plt.tight_layout()
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f'{animal}_sanity_check.png')
    fig.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSummary figure saved → {out}')


def main():
    animal = sys.argv[1] if len(sys.argv) > 1 else 'MS08'
    cfg = ANIMALS[animal]
    print(f'=== Sleep sanity check: {animal} ({cfg["session"]}) ===\n')

    t, states, bouts, t_clus, motion, mo_thr, th_thr, th_chan = load_states(cfg['mat_file'])
    check_theta_threshold(th_thr, th_chan)
    check_coverage(t, states)
    check_proportions(t, states)
    durations = check_bouts(bouts)
    check_taste_alignment(t, states, cfg['sync_file'], cfg['taste_files'])
    check_rem_plausibility(t, states, t_clus, motion, mo_thr,
                            cfg.get('video_file'), cfg.get('mov_fps'),
                            cfg['sync_file'])
    check_rem_fragmentation(bouts, states, t)
    plot_summary(animal, t, states, durations, cfg['out_dir'])


if __name__ == '__main__':
    main()
