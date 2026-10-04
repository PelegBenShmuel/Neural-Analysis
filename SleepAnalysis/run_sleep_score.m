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

% MS14's theta-channel search (2026-09-29) found a tight, low-dynamic-range
% cluster (ch9 peakTH 0.344 vs ch65's 0.325 at rank 240/384) rather than one
% clear standout -- the same suspicious shape that preceded MS09/MS11's
% channel-search failures. Confirmed 2026-09-29: ch9 failed, AND channel 65
% also failed both bimodal-dip tests (unlike MS09/MS11, where 65 passed the
% retry) -- accepted 65 anyway as the least-arbitrary default; MS14's REM is
% unreliable regardless of channel choice (see project memory for detail).

% MS15's theta-channel search (2026-09-29) found the same suspicious shape as
% MS14: a tight, low-dynamic-range cluster (ch191 peakTH 0.337 vs ch65's
% 0.328 at rank 214/384). ch191 confirmed bad 2026-09-30: unlike MS14's
% failure mode (REM inflated), ch191 gave essentially ZERO REM (1 bout, 2s,
% over 72.7h) -- passed the bimodal-dip test but the wrong side of it.
% Archived at ch191_rejected_20260930/. Falling back to channel 65.

ANIMAL = 'MS24_CTAtoExt';

% MS18's theta-channel search (2026-09-30) found channel 37 (peakTH 0.413)
% with a somewhat larger gap over channel 65 (0.364, rank 338/384) than
% MS14/MS15 had. Confirmed bad 2026-09-30: same severe failure as MS15's
% ch65 attempt, not just MS14-style borderline -- WAKE collapsed to 10.5%,
% REM inflated to 43.2%, only 18.0% of tastes in WAKE. Archived at
% ch37_rejected_20260930/. Trying channel 65 next for comparison.

% MS20's theta-channel search (2026-09-30) found channel 229 (peakTH 0.456)
% with a real gap over channel 65 (0.311, rank 337/384) -- better separation
% than MS14/15/18 had. MS20 is the third Control/Familiar-group animal (with
% MS15/MS18, per README's group table) -- an important test case for whether
% the WAKE-collapse pattern is Control-group-specific or coincidental.

% MS21's theta-channel search (2026-09-30) found channel 214 (peakTH 0.406)
% with a gap over channel 65 (0.358, rank 299/384). MS21 is Experimental
% group (per README) -- a test case for whether the WAKE-collapse pattern
% really is Control-specific (MS15/18/20) or shows up here too.

% MS22's theta-channel search (2026-09-30) found channel 201 (peakTH 0.439)
% with a gap over channel 65 (0.399, rank 317/384). Confirmed bad
% 2026-10-01: WAKE/NREM were fine (52.0%/46.4%) but REM collapsed to
% essentially zero (2 bouts, 13s each, over 72.7h) -- a different failure
% mode than the Control-group WAKE-collapse (MS15/18/20), localized to
% theta/REM detection only. Archived at ch201_rejected_20261001/. Trying
% channel 65 next.

% MS21_ch65: Peleg asked (2026-09-30) to also try channel 65 for MS21 (even
% though ch214 already gave a clean result) so the two can be compared
% side-by-side via compare_theta_channels.py. Separate basePath
% (MS21_hab3toExt_ch65) so it doesn't overwrite the accepted ch214 output.

% MS23's theta-channel search (2026-10-01) found channel 73 (peakTH 0.395),
% but channel 65 itself ranks 9th of 384 (0.383) -- a tight cluster of
% nearby channels (64-77, all near 65), so little gap this time. MS23 is
% Experimental group.

% MS24_hab3toExt's theta-channel search (2026-10-01) found channel 243
% (peakTH 0.403) with a gap over channel 65 (0.333, rank 321/384). Confirmed
% bad 2026-10-01: WAKE/NREM fine (47.9%/48.9%) but REM collapsed to near-zero
% (1 bout, 2s, over 18.5h) -- same localized theta/REM-only failure as
% MS22's ch201. Archived at ch243_rejected_20261001/. Trying channel 65.
% (Also recall this segment has a known LF gap 04:00-09:57, see
% project_data_collection_2026_09 memory -- not a scoring bug.)

% MS24_CTAtoExt's theta-channel search (2026-10-01) found channel 254
% (peakTH 0.415) with a real gap over channel 65 (0.307, rank 326/384).

% MS25's theta-channel search (2026-10-01) found channel 264 (peakTH 0.392)
% with a gap over channel 65 (0.309, rank 355/384). Last rat in the queue.
% Recall MS25's LF ends at 40.5h though video runs 48.1h -- key Training-day
% window is fully covered (see project_data_collection_2026_09 memory).

ANIMALS = struct( ...
    'MS25', struct( ...
        'basePath',      '/media/anan/diskh2/MS25/MS25_hab3toExt', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [264]), ...  % find_theta_channel.m, 2026-10-01 -- see comment above
    'MS24_CTAtoExt', struct( ...
        'basePath',      '/media/anan/diskh2/MS24/MS24_CTAtoExt', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [65]), ...  % ch254 rejected 2026-10-04, trying ch65 instead (see above)
    'MS24_hab3toExt', struct( ...
        'basePath',      '/media/anan/diskh2/MS24/MS24_hab3toExt', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [65]), ...  % ch243 rejected 2026-10-01, see comment above
    'MS23', struct( ...
        'basePath',      '/media/anan/diskh2/MS23/MS23_hab3toExt', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [73]), ...  % find_theta_channel.m, 2026-10-01 -- see comment above
    'MS21_ch65', struct( ...
        'basePath',      '/media/anan/diskh2/MS21/MS21_hab3toExt_ch65', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [65]), ...  % see comment above
    'MS22', struct( ...
        'basePath',      '/media/anan/diskh2/MS22/MS22_hab3toExt', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [65]), ...  % ch201 rejected 2026-10-01, see comment above
    'MS21', struct( ...
        'basePath',      '/media/anan/diskh2/MS21/MS21_hab3toExt', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [214]), ...  % find_theta_channel.m, 2026-09-30 -- see comment above
    'MS20', struct( ...
        'basePath',      '/media/anan/diskh2/MS20/MS20_hab3toExt', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [229]), ...  % find_theta_channel.m, 2026-09-30 -- see comment above
    'MS18', struct( ...
        'basePath',      '/media/anan/diskh2/MS18/MS18_hab3toExt', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [65]), ...  % ch37 rejected 2026-09-30, see comment above
    'MS15', struct( ...
        'basePath',      '/media/anan/diskh2/MS15/MS15_hab3toExt', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [65]), ...  % ch191 rejected 2026-09-30, see comment above
    'MS14', struct( ...
        'basePath',      '/media/anan/diskh2/MS14/MS14_hab3toExt', ...
        'rejectChannels', [384], ...
        'SWChannels',     [65], ...
        'ThetaChannels',  [65]), ...  % ch9 rejected 2026-09-29, see comment above -- reverted to 65
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
