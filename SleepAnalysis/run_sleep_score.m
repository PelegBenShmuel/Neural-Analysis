% Buzcode SleepScoreMaster runner -- one script for every rat, not a copy
% per animal (see feedback_no_script_duplication memory / TODO.md). Edit
% ANIMAL below to pick which rat to (re-)score; add a new ANIMALS entry
% for a new rat rather than copying this file.
%
% SWChannels/ThetaChannels/rejectChannels are animal-specific -- a good SW/
% Theta channel for one rat does NOT carry over to another (confirmed on
% MS08: channel 65 worked for MS11 but gave "No bimodal dip found in theta"
% for MS08, because it ranked 342nd of 384 candidates there -- see
% find_theta_channel.m and README.md's "Known limitations" section). Run
% find_theta_channel.m first for any new rat instead of guessing/reusing
% another animal's channel.

% MS09 is reverted to its original channel 65 (2026-09-17), after two
% channel-search attempts both failed: 295 (highest raw theta power, via
% find_theta_channel.m) turned out to be a licking/movement artifact --
% theta rose *with* EMG (corr +0.06..+0.08). 107 (best by a custom
% theta-vs-EMG decoupling scan across all 384 channels -- real REM theta
% should rise *during stillness*) had the right correlation sign but its
% theta-ratio distribution isn't actually bimodal (a broad, mostly-unimodal
% hump, not two separable populations), so buzcode's threshold-picking
% degenerated to THthresh=0 for both attempts, which is why they gave
% near-identical, implausible results (REM ~33% of the recording). Unlike
% MS08, no channel tested so far gives MS09 a clean theta split -- treat
% its REM as unreliable regardless of channel choice. See README's "Known
% limitations" section.

% MS11 is reverted to its original channel 65 (2026-09-18), same call as
% MS09, after channel 81 (found via find_theta_channel.m, 2026-09-17 --
% channel 65 ranks 262nd of 384, channel 81 has the best raw theta
% separation) was actually applied and tested. Getting there required
% copying the 506GB raw .lf.bin back to local disk first (MS11's local
% copy was gone; rescoring over the NAS symlink was killed 2026-09-17
% after >90min without even finishing the LFP load) -- copied to
% /media/anan/diskh2/MS11/MS11_hab3_g0_t0.imec0.lf.bin on 2026-09-18 and
% repointed the .lfp symlink there, then rescored at local-NVMe speed.
% Result: channel 81 passed the EMG-quiescence check (REM epochs look
% quiet, not WAKE-like) but hit the SAME degenerate-threshold failure
% that sank MS09's alternates -- buzcode's bimodal-dip test failed AND
% its "exclude NREM and retry" fallback also failed (channel 65 only
% failed the first test), falling through to a last-resort default
% threshold. REM ballooned to 16.7% (789 bouts, outside the 3-15%
% typical range) vs. channel 65's 6.7% (284 bouts, in range) -- treat
% that extra REM as an artifact of an unvalidated threshold, not a real
% improvement. See compare_theta_channels.py and
% Z:\Peleg\MS11\MS11_theta_channel_comparison\ for the full comparison;
% the channel-81 result set is archived (not deleted) at
% diskh2/MS11/MS11_hab3/channel81_explored_not_adopted_20260918/ and
% Z:\Peleg\MS11\MS11_Buzaki_results_ch81\.

ANIMAL = 'MS11';

ANIMALS = struct( ...
    'MS11', struct( ...
        'basePath',      '/media/anan/diskh2/MS11/MS11_hab3', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [65]), ...  % reverted -- 81 tested and rejected, see comment above, 2026-09-18
    'MS08', struct( ...
        'basePath',      '/media/anan/diskh2/MS08/MS08_hab3toExp', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [370]), ...  % found via find_theta_channel.m, 2026-09-16
    'MS09', struct( ...
        'basePath',      '/media/anan/diskh2/MS09/MS09_hab3_ext', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [65]) ...  % reverted -- see comment above, 2026-09-17
);

cfg = ANIMALS.(ANIMAL);

addpath(genpath('/media/anan/diskh1/Matlab_packages/buzcode/buzcode-master'));
addpath('/home/peleg/matlab_mex');

SleepState = SleepScoreMaster(cfg.basePath, ...
    'rejectChannels', cfg.rejectChannels, ...
    'SWChannels',     cfg.SWChannels,     ...
    'ThetaChannels',  cfg.ThetaChannels,  ...
    'noPrompts',      true);

disp('Done!');
