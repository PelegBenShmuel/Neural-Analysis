# Experiment Protocol and Procedure

**Status: confirmed directly by Mai Shafiki, 2026-09-15.** This replaces the
earlier version of this file, which was built from a spoken/approximate
recollection and got some details wrong (notably the day count and which day
counts as the recording baseline). Source: Moran Lab "GC CTA Protocol" reference
(Mai's `docs/STATISTICAL_CONCERNS.md` §104–105, which supersede an earlier
script-inferred picture there; valve/bolus numbers from MS09's task-control
scripts in `Mai/u_pyton_proj_example/`; see also `docs/THESIS_DRAFT.md` §3.2 and
`notebooks/sessions.py`). None of those source files live in this repo
(`ProjectPeleg`) — ask Mai for access if deeper detail than what's summarized
here is needed.

## Overview

- Chronic **Neuropixels 1.0** implant in gustatory cortex (GC) + **IOC**
  (intraoral cannula) taste delivery, in Long-Evans rats.
- Fixed **6-day protocol**: 3 habituation days (Hab D1–D3), Training day (Day 4,
  the LiCl pairing), Test + Extinction day (Day 5), Final test day (Day 6).
- Preceded by ~3 days of chamber acclimation (ad libitum food/water, no IOC — not
  counted in the 6 days) and, further back, surgery + recovery — both separate
  protocols, not detailed here.
- Two animal groups, paralleling Arieli et al. (2022)'s Exp/Fam design (see
  README.md Literature section): **Experimental** — sucrose withheld until Day 4,
  so it's a genuinely novel CS — vs. **Control/Fam** — sucrose included in the
  IOC battery from Day 1, i.e. pre-exposed/familiar, used to isolate LiCl/malaise/
  time effects from the CTA-specific association.
- Neuropixels recording: **not connected Days 1–2; starts Day 3; continuous,
  uninterrupted through Day 6.**
- Water restriction begins with Day 1's morning drinking session.

## Day-by-day

### Days 1–3 — Habituation (Hab D1 / D2 / D3)

Identical daily sequence across all three days:

| Time | Event |
|---|---|
| ~9:30 | Water drinking session, 20 min |
| 10:00 | IOC session 1 of 7 |
| 12:00, 14:00, 16:00, 18:00, 20:00, 00:00 | IOC sessions 2–7 (~2h spacing) |
| afternoon | Quinine drinking session, 20 min |

- **IOC sessions:** 7/day, identical across all 3 habituation days. 10 shuffled
  repeats per session (Fisher–Yates order), 12s inter-trial interval.
- **Taste battery:** Water (10/session), NaCl 0.1M (10/session), Citric acid 0.1M
  (10/session), Sucrose 0.2M — **Control/Fam group only**. In the Experimental
  group, sucrose is withheld through Day 3 to stay novel for the Day 4 pairing.
- **Quinine:** not a taste-coding probe — never appears in the IOC battery. It's a
  vet-mandated minimum-daily-fluid-intake measure during water restriction: its
  bitterness caps intake while keeping the animal thirsty enough to stay
  motivated for the IOC task. Runs every afternoon Days 1–5 (skipped Day 6);
  rats usually drink little to none.
- **Recording:** not yet connected Days 1–2; **starts Day 3**, continuous
  thereafter through Day 6. Day 3 is the actual pre-CTA recording baseline.

### Day 4 — Training day (LiCl pairing)

| Time | Event |
|---|---|
| Morning | Sucrose drinking session, 20 min |
| +10 min | **Block 1** (pre-injection reference): 4 tastes, sucrose delivered *twice* per repeat — 20 sucrose + 10 each water/NaCl/citric acid = 50 trials |
| Block 1 ends, +5 min | **LiCl injection, IP, by hand** |
| → | **Blocks 2–7**: 4 tastes, 10 each (40 trials/block), same ~2h spacing as habituation |

- The morning sucrose drinking session is the **Experimental** group's
  first-ever sucrose exposure; **Control/Fam** rats are already familiar with it.
- **LiCl prep & dose:** 0.32 g LiCl / 25 mL ddH₂O (≈0.30 M), injected IP at 1%
  body weight (≈3.0 mmol/kg, ≈127 mg/kg) — in line with classic Bureš/Garcia-era
  CTA dosing.
- Injection timing is synced to the recording via a manual keypress to the
  task-control microcontroller — this timestamps the moment but does not control
  the injection itself.

### Day 5 — Test + Extinction

- **Extinction criterion:** opens with a 20-min sucrose drinking session (the
  test measurement), then another every hour, repeated **until intake matches
  what the rat drank in Day 4's pre-LiCl training session** — that intake match
  is the stopping criterion (not a fixed number of sessions).
- **IOC sessions:** the standard 7/day schedule also runs (as in habituation),
  full 4-taste battery, no LiCl.

> **Analysis note (important):** Day 5's first IOC session is what
> `np_analysis`'s block numbering calls **"Block 8."** The standard
> Kilosort/analysis window covers **Training day + this one Day-5 session** —
> the rest of Day 5 and all of Day 6 are recorded but not normally part of the
> sorted/analyzed window.
>
> **This refines the project's earlier "spike-sorted units exist only for the
> CTA/training day" understanding** (see project memory / README.md) — it's
> more precisely *Training day (all 7 blocks) + Block 8 (Day 5's first IOC
> session)*, not the full Day 5.

### Day 6 — Final test

One final IOC session confirms the endpoint. No further LiCl.

## Recording & sorting status by day

| Day | Neuropixels recording | Kilosort / spike-sorted? |
|---|---|---|
| Hab D1 | not connected | — |
| Hab D2 | not connected | — |
| Hab D3 | ✅ starts here (baseline) | ❌ (per current Kilosort constraint) |
| Training (Day 4) | ✅ | ✅ full day (Blocks 1–7) |
| Test + Extinction (Day 5) | ✅ | ✅ **only Block 8** (first IOC session); rest of the day ❌ |
| Final test (Day 6) | ✅ | ❌ |

## Trial & solution parameters

| Parameter | Value | Note |
|---|---|---|
| Inter-trial interval | 12 s | |
| Repeats/session | 10 | Fisher–Yates (shuffled) order |
| Target bolus | ≈30 µL per delivery | |
| Water valve | 110 ms | MS09's own calibration |
| Sucrose valve | 200 ms, 0.2 M | MS09's own calibration |
| NaCl valve | 180 ms, 0.1 M | MS09's own calibration |
| Citric acid valve | 170 ms, 0.1 M | MS09's own calibration |
| LiCl solution | 0.30 M (0.32 g / 25 mL ddH₂O) | |
| LiCl dose | 1% b.w., IP, ≈127 mg/kg | |
| Quinine (drinking only) | ≈1 mM | Never in the IOC battery |
| Delivery mechanism | IOC solenoid valves + sync "report" pin per delivery | |

**Caveat: valve-open durations are animal-specific**, calibrated per-rat via
`calib.py` — the table above shows **MS09's own numbers**. Don't reuse them for
another animal (e.g. MS11) without revalidating that animal's own calibration.

## Open items / still worth checking

- Whether animals already in this project's dataset (e.g. MS11) are
  Experimental or Control/Fam group — determines whether sucrose was novel or
  pre-exposed for that animal, which matters for interpreting any CTA effect.
- Whether the ~3 days of pre-habituation chamber acclimation are recorded at
  all, given they're "not counted" in the 6-day protocol and have no IOC.
- Exact clock time of the "afternoon" quinine session (not pinned to a specific
  time in Mai's confirmed description).
