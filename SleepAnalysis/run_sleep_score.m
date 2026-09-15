% Copied verbatim from Z:\Peleg\MS11\run_sleep_score.m (2026-09-15) -- this is
% the actual script used to produce MS11_hab3's buzcode sleep-scoring output.
% It is MS11-specific: basePath and the channel numbers below (SWChannels/
% ThetaChannels = 65, rejectChannels = 384 for the sync channel) were chosen
% for that animal. To score a new rat: copy this file, point basePath at the
% new session folder (see generate_buzcode_xml.py for building its .xml/.lfp
% first), and pick that animal's own good SW/Theta channel -- don't reuse 65
% without checking.

addpath(genpath('/media/anan/diskh1/Matlab_packages/buzcode/buzcode-master'));
addpath('/home/peleg/matlab_mex');

basePath = '/media/anan/diskh2/MS11/MS11_hab3';

SleepState = SleepScoreMaster(basePath, ...
    'rejectChannels', [384], ...
    'SWChannels',     [65],  ...
    'ThetaChannels',  [65],  ...
    'noPrompts',      true);

disp('Done!');
