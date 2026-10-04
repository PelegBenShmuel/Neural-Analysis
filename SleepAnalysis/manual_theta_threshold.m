% Re-cluster WAKE/NREM/REM using a manually-forced theta threshold, reusing
% the already-computed SleepScoreMetrics (broadbandSlowWave/thratio/
% motiondata/t_clus) instead of redoing the expensive LFP load + EMG
% computation -- only ClusterStates_DetermineStates.m (fast, no LFP I/O)
% re-runs. One script for every rat/threshold tried, not a copy per attempt
% -- see feedback_no_script_duplication memory. Edit ANIMAL/MANUAL_TH_THRESH
% below; add a new ANIMALS entry for a new rat rather than copying this file.
%
% Why this is worth trying: buzcode's automatic theta-threshold picker
% (ClusterStates_GetMetrics.m) hard-codes THthresh=0 whenever it can't find
% a bimodal split, silently making REM = "not moving and low SW power" with
% no real theta signal (see project_buzcode_all_rats_2026_09 memory). This
% script lets us force a manually-chosen threshold instead and compare the
% result via sleep_sanity_check.py / compare_theta_channels.py.

ANIMAL = 'MS25';
MANUAL_TH_THRESH = 0.5931;  % mean+1SD, video-correction to follow, 2026-10-04

ANIMALS = struct( ...
    'MS25', struct( ...
        'orig_mat',  '/media/anan/diskh2/MS25/MS25_hab3toExt/MS25_hab3toExt.SleepState.states.mat', ...
        'out_dir',   '/media/anan/diskh2/MS25/MS25_hab3toExt_manualTH'), ...
    'MS24_CTAtoExt', struct( ...
        'orig_mat',  '/media/anan/diskh2/MS24/MS24_CTAtoExt/MS24_CTAtoExt.SleepState.states.mat', ...
        'out_dir',   '/media/anan/diskh2/MS24/MS24_CTAtoExt_manualTH'), ...
    'MS23', struct( ...
        'orig_mat',  '/media/anan/diskh2/MS23/MS23_hab3toExt/MS23_hab3toExt.SleepState.states.mat', ...
        'out_dir',   '/media/anan/diskh2/MS23/MS23_hab3toExt_manualTH'), ...
    'MS14', struct( ...
        'orig_mat',  '/media/anan/diskh2/MS14/MS14_hab3toExt/MS14_hab3toExt.SleepState.states.mat', ...
        'out_dir',   '/media/anan/diskh2/MS14/MS14_hab3toExt_manualTH'), ...
    'MS21', struct( ...
        'orig_mat',  '/media/anan/diskh2/MS21/MS21_hab3toExt/MS21_hab3toExt.SleepState.states.mat', ...
        'out_dir',   '/media/anan/diskh2/MS21/MS21_hab3toExt_manualTH') ...
);

cfg = ANIMALS.(ANIMAL);

addpath(genpath('/media/anan/diskh1/Matlab_packages/buzcode/buzcode-master'));
addpath('/home/peleg/matlab_mex');

if ~exist(cfg.out_dir, 'dir')
    mkdir(cfg.out_dir);
end

fprintf('Loading existing SleepScoreMetrics from %s ...\n', cfg.orig_mat);
S = load(cfg.orig_mat);
detectionparms = S.SleepState.detectorinfo.detectionparms;
metrics = detectionparms.SleepScoreMetrics;

hats_orig = metrics.histsandthreshs;
hats_manual = hats_orig;
hats_manual.THthresh = MANUAL_TH_THRESH;

fprintf('[%s] Original THthresh=%.4f -> manual THthresh=%.4f\n', ...
    ANIMAL, hats_orig.THthresh, MANUAL_TH_THRESH);

fprintf('Re-clustering states with the manual threshold (no LFP reload)...\n');
[ints, idx, MinTimeWindowParms] = ClusterStates_DetermineStates(metrics, ...
    detectionparms.MinTimeWindowParms, hats_manual);

% Mirror SleepScoreMaster.m's own save schema exactly, with the manual
% threshold baked into detectionparms.SleepScoreMetrics.histsandthreshs so
% anything reading THthresh downstream (sleep_sanity_check.py etc) sees it.
metrics.histsandthreshs = hats_manual;
detectionparms.SleepScoreMetrics = metrics;
detectionparms.MinTimeWindowParms = MinTimeWindowParms;
detectionparms.histsandthreshs_orig = hats_orig;  % the real original, for provenance

SleepState = struct();
SleepState.ints = ints;
SleepState.idx = idx;
SleepState.detectorinfo.detectorname = 'manual_theta_threshold.m (forced THthresh)';
SleepState.detectorinfo.detectionparms = detectionparms;
SleepState.detectorinfo.detectiondate = datestr(now, 'yyyy-mm-dd');

out_mat = fullfile(cfg.out_dir, sprintf('%s_manualTH.SleepState.states.mat', ANIMAL));
save(out_mat, 'SleepState', '-v7.3');
fprintf('Saved -> %s\nDone.\n', out_mat);
