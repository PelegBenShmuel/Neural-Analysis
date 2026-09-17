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

% MS11's rescore with channel 81 (found via find_theta_channel.m,
% 2026-09-17 -- channel 65 ranks 262nd of 384, channel 81 has the best
% theta separation) is NOT YET APPLIED. MS11's local raw .lf.bin is gone
% (moved/deleted from diskh2 at some point), so its .lfp symlink was
% repointed at the NAS copy for this -- reading 2 channels across 73h that
% way turned out to be extremely slow (>90min without finishing even the
% initial LFP load) and was killed 2026-09-17 rather than left running
% indefinitely. MS11 is still on its original channel 65 (data intact,
% verified after the kill). See TODO.md for the plan to revisit this
% (likely: copy the 506GB raw file back to local disk first, ~1.2TB free
% on diskh2, rather than rescoring over SMB again).

ANIMAL = 'MS11';

ANIMALS = struct( ...
    'MS11', struct( ...
        'basePath',      '/media/anan/diskh2/MS11/MS11_hab3', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [65]), ...  % channel 81 found but not yet applied, see comment above
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
