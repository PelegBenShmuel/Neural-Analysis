"""
Cross-rat hourly sleep table -- Peleg's request, 2026-11-08: for every rat,
minutes of each clock hour spent asleep (NREM+REM) across the Training
day's 24h window (9:00 AM on the LiCl day through 9:00 AM the next day --
the same window training_day_sleep_state_extraction.py cuts to). First
built in % of the hour, then converted to minutes same day at Peleg's
request ("אני רוצה שתהפוך את הקובץ... לדקות ולא לאחוזים") -- same
underlying per-hour-seconds-asleep data either way, just /60 instead of
/36.

Reuses existing helpers rather than reimplementing: training_day_window()
and load_states() from training_day_sleep_state_extraction.py,
hourly_sleep_pct() from sleep_char.py for the per-hour seconds-asleep array
(that function's OWN "pct" return is a different question -- % of the
day's total sleep that fell in each hour, not minutes/% of that hour spent
asleep -- so only its per_hour_s array is reused here). ANIMAL_KEYS (the
established 12-rat "all rats, sleep context" list, video-corrected variant
where one exists, MS08/09/11 stay plain per the standing decision) is
imported from total_sleep_rat.py rather than redefined -- broader than
fano_factor_total.py's 10-rat RAT_KEYS since sleep scoring doesn't depend
on GC boundaries.

Usage: python hourly_sleep_all_rats.py [ANIMAL ...]
Defaults to all rats in ANIMAL_KEYS. Writes locally to /tmp/ first, then
copies to Z:\\Peleg\\CrossRatAnalysis\\ as HourlySleepMinutes_AllRats.xlsx
(supersedes the first version's HourlySleepPercent_AllRats.xlsx).
"""
import sys
import os

import numpy as np
import openpyxl
from openpyxl.styles import Font

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from MS_buzcode_analysis import ANIMALS, NAS_PELEG, copy_to_share_safely
from training_day_sleep_state_extraction import STATE_CODE, load_states, training_day_window
from sleep_char import hourly_sleep_pct
from total_sleep_rat import ANIMAL_KEYS

SLEEP_CODES = (STATE_CODE['NREM'], STATE_CODE['REM'])


def plain_name(key):
    """'MS21_videocorr' -> 'MS21', etc. -- for the row label."""
    for rat in ('MS08', 'MS09', 'MS11', 'MS14', 'MS15', 'MS18', 'MS20',
                'MS21', 'MS22', 'MS23', 'MS24', 'MS25'):
        if key.startswith(rat):
            return rat
    return key


def hourly_minutes_for_rat(key):
    cfg = ANIMALS[key]
    licl_time_s = cfg.get('licl_time_s')
    if licl_time_s is None:
        return None, "no licl_time_s (no Training day to anchor on)"

    window_start_s, _window_end_s, _wh0, _wh1 = training_day_window(cfg, licl_time_s)
    t, states, _bouts = load_states(cfg['mat_file'])
    dt = np.diff(t, append=t[-1])
    is_sleep = np.isin(states, SLEEP_CODES)

    per_hour_s, _wrong_pct = hourly_sleep_pct(t, dt, is_sleep, window_start_s)
    minutes_of_hour = per_hour_s / 60.0   # Peleg's explicit request, 2026-11-08:
    # minutes asleep that hour, not % of the hour -- same per_hour_s data,
    # just /60 instead of /36.
    return minutes_of_hour, None


def main():
    requested = sys.argv[1:] if len(sys.argv) > 1 else ANIMAL_KEYS

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hourly Sleep (min)"
    # Columns label real clock hours (09:00 through next day's 08:00),
    # matching the Training-day 9AM-9AM convention -- h cycles 9..32, taking
    # %24 for the label only.
    header = ["rat"] + [f"{(h % 24):02d}:00-{((h + 1) % 24):02d}:00" for h in range(9, 33)]
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for key in requested:
        rat = plain_name(key)
        print(f"Computing {rat} ({key})...")
        try:
            minutes_of_hour, skip_reason = hourly_minutes_for_rat(key)
        except Exception as e:
            print(f"[SKIP] {rat}: {type(e).__name__}: {e}")
            continue
        if minutes_of_hour is None:
            print(f"[SKIP] {rat}: {skip_reason}")
            continue
        ws.append([rat] + [round(float(m), 2) for m in minutes_of_hour])
        print(f"{rat}: mean {minutes_of_hour.mean():.1f} min/hour asleep across the 24h Training day")

    for col_idx in range(1, len(header) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 14

    local_xlsx = "/tmp/HourlySleepMinutes_AllRats.xlsx"
    wb.save(local_xlsx)
    print(f"Wrote {local_xlsx}")

    nas_dir = f"{NAS_PELEG}/CrossRatAnalysis"
    os.makedirs(nas_dir, exist_ok=True)
    copy_to_share_safely(local_xlsx, nas_dir)
    print(f"Copied to {nas_dir}/")


if __name__ == '__main__':
    main()
