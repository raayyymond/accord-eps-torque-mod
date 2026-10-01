# REFUTE C2 round 1: NONLINEAR lens (2026-10-01)

**Verdict: REFUTED, because there is nothing to clear.** The C2 synthesis halted before it produced a design.
There is no primary, no fallback, no cave listing, no cals, no scripts and no design document. A refuter cannot
clear a design that does not exist, and the lens cannot be run on an empty object. This is **not** a finding that
any candidate design misbehaves nonlinearly. It is a finding that **no C2 claim exists that could be verified.**

**Nothing in this report scores D2a, B0r or any other panel candidate.** Running my lens on a design I chose myself
would be refuting the wrong object (the image rule: *a null from the wrong image is not a null*). The orchestrator
has to name the target.

---

## 1. What I checked, and how

| # | Claim in the C2 handoff | Method | Result |
|---|---|---|---|
| 1 | `DESIGN-ANGLE-LOOP-C2-2026-10-01.md` was not written | `ls docs/specs/design/` and `docs/specs/design/panel/`; `find . -iname "*C2*2026-10*"` across the repo (`.git` excluded) | **EVIDENCE: absent.** The design folder holds only C0, C1 and C1-rev1-REFUTED. The panel folder holds DESIGN-PANEL-A/B/C/D. |
| 2 | `analysis-2020accord/studies/angle_loop/c2/` was not created | `ls` of that path; `find -ipath "*angle_loop*" -iname "*c2*"` | **EVIDENCE: absent** ("No such file or directory"; the find returns nothing). |
| 3 | `panel/score_time.py` does not exist (the common time scorer halted) | `ls analysis-2020accord/studies/angle_loop/panel/` | **EVIDENCE: absent.** The folder holds only `score_freq.py`, `SCORE-FREQ-2026-10-01.md` and `JUDGE-bytes-risk-2026-10-01.md`, plus the four designer subfolders. |
| 4 | Only the bytes-risk judge ranked: D2a 82 and B0r 81, a statistical tie | grep of `JUDGE-bytes-risk-2026-10-01.md` | **EVIDENCE: confirmed as written.** The ranking table lists D2a at 82 and B0r at 81, and M1 says "D2a and B0r are statistically tied (82 vs 81)". The judge also says "**The common TIME scorer was halted and produced nothing**" and "**No common time-domain scoring exists**". |

I did no byte work. Nothing in this report reads the image, so the firmware-decompile traps do not apply.

---

## 2. Why this returns `refuted = true`

The brief says: *"If you cannot verify a decision-bearing claim yourself, say which and return refuted = true for
that reason."* Every decision-bearing claim the lens exists to test is missing:

- **The cave's exact arithmetic.** There is no instruction listing to mirror. That covers the sar/shift chain, the
  e5 floor, saturation widths, sign-hold and the guard.
- **Stick-slip and dwell-then-jump at ≥ 8 m/s** on nominal, bc, F_hi and b_lo × J_hi. There is no configuration to
  simulate.
- **Dead band, tracking at 0.2/0.5 Hz, turn-hold.** Not computable.
- **Override lurch** (light hand |tq| ≤ 1000 and firm hand), **co-steer, release, engage droop and ramp-in wind-up.**
  Not computable.
- **The 510 ms timeout hold and the sentinel pulse**, under C2's guard set. Not computable, because the guard set C2
  would ship is unknown. A2/B2 are listed in the FACTS block, but C2 never said which ones it adopted.
- **Pre-declared misses and stop bands.** None were declared, so no miss can be excused, even in principle.

Under the CLAUDE.md rule *"the pass must be able to return 'do not flash'"*, an empty design gets **DO NOT FLASH**:
there is nothing to flash, and nothing has been verified.

---

## 3. A gap the halt leaves, which falls under this lens (a report, not licence to act)

**No candidate in the panel has passed a common, independent nonlinear time-domain gate.** The bytes-risk judge
ranked D2a and B0r without one. It used time-domain numbers *"only where a designer reports a failure against its own
interest"*. So the two front-runners' stick-slip, lurch, droop, wind-up, timeout-hold and texture behaviour comes
from the designers' own runs, not from an adversary.

- **BELIEF (not verified by me):** the D-structure designer ran its own time suite at
  `analysis-2020accord/studies/angle_loop/panel/D-structure/ds_time.py`. It has a light-hand override scenario
  (`ov_light<tq>`), a sentinel command path, a droop/overshoot metric and a 40–200 Hz texture measure. Its
  `final_track.txt` carries per-member tracking factors for B0 and B0r (and, by its header, more). I did not re-run or
  audit either file. They are the designer's own evidence, and they do not replace this lens.
- **What a re-briefed nonlinear refutation of D2a and/or B0r would need** (the orchestrator decides whether to issue
  one):
  1. The exact cave bytes. They exist at `panel/D-structure/ds_cave_D2a.hex` and `ds_cave_B0r.hex`. The run must
     mirror them byte-exactly, not through the designer's harness model.
  2. The exact in-place edit set and guards adopted. In particular, D2a's `gp-0x6abe` validity guard, which the
     bytes-risk judge calls MANDATORY on any read of that cell.
  3. Members nominal, bc, F_hi and b_lo × J_hi, on the ≤ 0.25 m/s grid including the knots, with hold ages 1–20.
  4. The lens's full scenario list: stick-slip, dwell-then-jump, dead zone, tracking at 0.2/0.5 Hz, turn-hold,
     light-hand and firm-hand override, co-steer, release lurch, engage droop and ramp-in wind-up, the sentinel pulse,
     the 510 ms timeout hold, and 5–30 Hz texture.
  5. Each design's pre-declared misses and stop bands, so that a declared miss can be told apart from an undeclared
     one.

---

## 4. Footprint

Read-only checks only: directory listings, `find`, and `grep` over two panel files. I did not open Ghidra, run
Python, touch the image, build anything, or send anything. This file is the only one written. I created no scratch
directory, because there was nothing to compute.
