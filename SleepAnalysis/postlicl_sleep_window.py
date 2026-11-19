"""
For each "good" rat (>=15 units in at least one region, GC or S1 -- same
threshold as plot_metric_block_trend.py's display filter), finds the
FIRST window of WINDOW_MINUTES after the LiCl injection that contains at
least MIN_SLEEP_MINUTES of sleep (NREM+REM) -- Peleg's build-up,
2026-11-10, toward Anan Moran's request #5 (align blocks/rats by a
sufficient-sleep criterion rather than strictly by block number -- see
project_anan_meeting_2026_11_08 memory). Exploratory first pass: reports
where this window falls (hours after LiCl) for every qualifying rat, not
yet used to actually re-align any block-based analysis.

Reuses load_states()/training_day_window() (training_day_sleep_state_
extraction.py) for sleep state, and plot_metric_block_trend.py's
load_region_rows() (reads the already-built FanoFactorTotal.xlsx, no
spike-data reload) purely to determine each rat's GC/S1 unit counts for
the ">=15 in at least one region" filter -- consistent with that script's
own MIN_UNITS_TO_DISPLAY convention, not a new threshold invented here.

Usage: python postlicl_sleep_window.py [WINDOW_MINUTES MIN_SLEEP_MINUTES]
Defaults to 20min window / 15min sleep (Peleg's last example, 2026-11-10).
"""
import sys
import os

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from MS_buzcode_analysis import ANIMALS
from training_day_sleep_state_extraction import STATE_CODE, load_states, training_day_window

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'NeuralAnalysis'))
from fano_factor_total import RAT_KEYS
from plot_metric_block_trend import METRIC_CONFIG, MIN_UNITS_TO_DISPLAY, load_region_rows

SLEEP_CODES = (STATE_CODE['NREM'], STATE_CODE['REM'])
STEP_S = 60   # sliding-search step


def good_rats():
    """Rats with >=MIN_UNITS_TO_DISPLAY units in at least one of GC/S1,
    per the already-built FanoFactorTotal.xlsx -- same filter
    plot_metric_block_trend.py applies per-plot, applied here per-rat."""
    counts = {}
    for region in ('GC', 'S1'):
        by_rat = load_region_rows(METRIC_CONFIG['fano'], region)
        for rat, entry in by_rat.items():
            n = max(len(v) for v in entry['blocks'])
            counts[rat] = max(counts.get(rat, 0), n)
    # load_region_rows already drops rats below MIN_UNITS_TO_DISPLAY for a
    # given region, so anything present in either call already qualifies;
    # the max() above just merges the two region passes for one list.
    return sorted(counts)


def first_sleep_window_after_licl(cfg, window_minutes, min_sleep_minutes):
    licl_time_s = cfg.get('licl_time_s')
    if licl_time_s is None:
        return None, "no licl_time_s"

    window_s = window_minutes * 60
    min_sleep_s = min_sleep_minutes * 60
    _day_start_s, day_end_s, _wh0, _wh1 = training_day_window(cfg, licl_time_s)

    t, states, _bouts = load_states(cfg['mat_file'])
    dt = np.diff(t, append=t[-1])
    is_sleep = np.isin(states, SLEEP_CODES)

    start = licl_time_s
    while start + window_s <= day_end_s:
        end = start + window_s
        mask = (t >= start) & (t < end)
        sleep_s = dt[mask & is_sleep].sum()
        if sleep_s >= min_sleep_s:
            return (start, end, sleep_s), None
        start += STEP_S
    return None, f"no qualifying {window_minutes}min window found after LiCl in the Training day"


def main():
    window_minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    min_sleep_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 15

    rats = good_rats()
    print(f"Good rats (>={MIN_UNITS_TO_DISPLAY} units in GC or S1): {rats}\n")
    print(f"{'Rat':<8}{'hours after LiCl':<20}{'sleep (min)':>14}")
    for rat in rats:
        key = RAT_KEYS[rat]
        cfg = ANIMALS[key]
        result, skip_reason = first_sleep_window_after_licl(cfg, window_minutes, min_sleep_minutes)
        if result is None:
            print(f"{rat:<8}[SKIP] {skip_reason}")
            continue
        start, end, sleep_s = result
        licl_time_s = cfg['licl_time_s']
        h0, h1 = (start - licl_time_s) / 3600, (end - licl_time_s) / 3600
        print(f"{rat:<8}{h0:>6.2f}h - {h1:<10.2f}h{sleep_s / 60:>12.1f}")


if __name__ == '__main__':
    main()
