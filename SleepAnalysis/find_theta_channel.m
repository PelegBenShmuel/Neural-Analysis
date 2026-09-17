% Memory-safe theta-channel search -- one script for every rat, not a copy
% per animal (see feedback_no_script_duplication memory / TODO.md). Edit
% ANIMAL below to pick which rat to search; add a new ANIMALS entry for a
% new rat rather than copying this file.
%
% Context (found on MS08, 2026-09-16): a naive full-recording, all-384-
% channel, 20-worker auto-search nearly exhausted the machine's 376GB RAM,
% because PickSWTHChannel.m loads ALL candidate channels' LFP for the
% ENTIRE scoretime into memory *before* the parfor loop even starts, and
% each parallel worker needs its own copy.
%
% Fix: call PickSWTHChannel directly (bypassing SleepScoreMaster) with:
%   - a short, bounded scoretime (first 2h -- already shown by
%     sleep_sanity_check.py's hourly plot to contain full WAKE/NREM/REM
%     cycling) instead of the full recording, and
%   - a capped parallel pool (3 workers) instead of the default 20,
% so peak memory stays a small, known fraction of the full-recording case
% instead of scaling with all candidate channels x full duration x default
% worker count.
%
% This only picks the channel -- it doesn't save a partial SleepScoreLFP.LFP.mat
% or touch the existing SleepState.states.mat. Once you're happy with the
% pick, add it to run_sleep_score.m's ANIMALS struct as that animal's
% ThetaChannels and run the actual (cheap, 2-channel, full-length) scoring.

ANIMAL = 'MS11';

ANIMALS = struct( ...
    'MS08', struct( ...
        'basePath',       '/media/anan/diskh2/MS08/MS08_hab3toExp', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...   % kept fixed -- already has a fine dip test
        'probeWindow',    [0 7200]), ...
    'MS09', struct( ...
        'basePath',       '/media/anan/diskh2/MS09/MS09_hab3_ext', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...   % kept fixed -- already has a fine dip test
        'probeWindow',    [0 7200]), ...
    'MS11', struct( ...
        'basePath',       '/media/anan/diskh2/MS11/MS11_hab3', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...   % kept fixed -- already has a fine dip test
        'probeWindow',    [0 7200]) ...
);

cfg = ANIMALS.(ANIMAL);

addpath(genpath('/media/anan/diskh1/Matlab_packages/buzcode/buzcode-master'));
addpath('/home/peleg/matlab_mex');

delete(gcp('nocreate'));
parpool('Processes', 3);

[SleepScoreLFP_probe, PickChannelStats] = PickSWTHChannel(cfg.basePath, cfg.probeWindow, 'PSS', ...
    0, 0, 0, 0, cfg.SWChannels, 0, cfg.rejectChannels, true, ...
    'noPrompts', true, 'saveFiles', false, ...
    'window', 2, 'smoothfact', 15, 'IRASA', true, 'thIRASA', true);

bestTheta = SleepScoreLFP_probe.THchanID;
fprintf('\n[%s] Best theta channel found: %d\n', ANIMAL, bestTheta);

[sortedvals, sortidx] = sort(PickChannelStats.peakTH, 'descend');
topN = min(10, length(sortidx));
disp('Top candidate theta channels (channel : peakTH ratio):');
for i = 1:topN
    fprintf('  ch %3d : %.4f\n', PickChannelStats.ThetaChannels(sortidx(i)), sortedvals(i));
end

for refCh = cfg.SWChannels
    refidx = find(PickChannelStats.ThetaChannels == refCh);
    refrank = find(sortidx == refidx);
    fprintf('\nChannel %d (SW channel, for reference) peakTH = %.4f (rank %d of %d)\n', ...
        refCh, PickChannelStats.peakTH(refidx), refrank, length(sortidx));
end

save(fullfile(cfg.basePath, sprintf('%s_theta_channel_pick.mat', ANIMAL)), ...
    'bestTheta', 'PickChannelStats');
disp('Done - channel pick complete.');
