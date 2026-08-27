#!/usr/bin/env python3
r"""PRE-REGISTRATION + READY-TO-RUN ANALYSIS for the LATERAL-MANEUVER drive.

Written BEFORE the drive.  Kit law: *"Before cutting, write the sentence a null will license."*
That sentence is in section 6.  Run: `python score/prereg_maneuver_hs.py --route <hex>` after extraction.

==================================================================================================
0.  WHAT THIS DRIVE IS FOR, AND WHY IT IS NOT A REPEAT
==================================================================================================
The kit has two mutually inconsistent readings of the same 8 Hz line:

  (i)  `docs/research/ANALYSIS-2026-08-20-torsion-bar-and-lane-weight.md` -- "THE TORSION-BAR MODE,
       CONFIRMED": f_n = 8.162 Hz, Q = 10.21, zeta = 0.0490, CI [8.015, 8.187] / [7.49, 13.61].
  (ii) `memory/accord/mechanism/accord-the-8hz-mode-is-the-loop-not-the-plant.md` (2026-08-21) -- the identified
       PASSIVE plant is `Z0 = 2792 @ -92.45 deg`, `Re(Z0)/|Z0| = -0.043`, a near-LOSSLESS SPRING,
       and 100 % of `Re(Z) = -3761` is LOOP-generated.

Both cannot be right: a Q = 10 mechanical resonance is not a lossless spring, and a lossless spring
does not have Q = 10.  **This drive is the tie-break**, and it is the over-determination that
(ii) itself asks for under "LARGEST REMAINING WEAKNESS" (it has only 2 + 3 engaged episodes).

⭐ WHY THE MANEUVER SUITE AND NOT ANOTHER ORDINARY DRIVE.  On ordinary driving `e4tq` is NOT
exogenous -- openpilot sees `steeringAngleDeg`, so the "drive" is partly the car's own response,
and every |T_s/e4tq| number inherits that.  Under `LateralManeuverMode` the command is a SCRIPTED
open-loop step with a **logged trigger instant** and **~36 replicate edges**, which is the one thing
the kit's ring-down work has never had (`accord-ringdown-q-needs-a-step-control`: 7 clean disengage
edges corpus-wide, and see section 3 below for why 7 is not enough).

==================================================================================================
1.  WHAT WAS ALREADY MEASURED FROM EXISTING LOGS -- do not re-do these
==================================================================================================
  * `studies/damping-q/ringdown_validate.py`  -- E1 (`stock_r97_ringdown`) and E2 (`r67_ringdown_q2`) SATURATE at
    zeta ~0.05 and reverse above it (Spearman +0.83 / +0.37, dynamic range 7.6x / 1.7x against a
    truth span of 40x), and their answer moves 3.5x / 6.3x with the FIT-WINDOW LENGTH alone.
    E3 (matrix pencil, residue-selected, variance-gated) orders the whole range (rho +1.000,
    range 41x), is duration-invariant, and refuses white noise, a perfect step and a
    phase-randomised surrogate 0/40 each.  **E3 is the estimator this file uses.**
  * `studies/identification/plant_recon.py` / `studies/identification/plant_zcurve.py` -- `ang` is quantisation-limited in band; `rate_c` is
    exactly 1.25 x `rate_f` (ONE channel); the 0x18F-vs-0x14A relative delay is **12.5 ms**,
    measured from a linear phase slope of -4.51 deg/Hz.
  * `studies/identification/plant_phase_corner.py` -- SCALE-FREE: `J_w/b_w` = 21.4-36.6 ms on five routes (STOCK
    36.6 [32.4, 48.1] ms, CV across 4-10 Hz bins = 0.147).  A wheel-on-torsion-bar mode AT 8.16 Hz
    would then have **Q = 1.10 - 1.88**, not 10.  ⚠ measured ENGAGED, so it is an UPPER bound on
    the passive Q (the loop is anti-damping at 6-9 Hz, which inflates apparent Q).
  * `studies/identification/plant_fit_final.py` -- the MAGNITUDE fit for J_w, b_w separately is **NOT SUPPORTED**
    (R^2 0.01-0.32, arms dropping out).  Its J_w and f_n numbers are WITHDRAWN.  Only the ratio
    survives.

==================================================================================================
2.  THE MEASUREMENT
==================================================================================================
INPUT   `e4tq`   -- openpilot's LKAS torque command as seen on the bus (0xE4), 100 Hz, already in
                    every cache.  It is a COMMANDED quantity, so it carries no sensor noise:
                    **H1 = S_uT/S_uu is the correct, unbiased estimator here** -- unlike the
                    passive-data fits above, there is no errors-in-variables problem.
OUTPUT  `tq`     -- 0x18F torsion-bar torque, counts, 100 Hz, same frame as `rate_f`.
SECOND  `rate_f` -- gives Z = tq/rate_f for the scale-free phase statistic, as a within-drive
                    replication of `studies/identification/plant_phase_corner.py` under a KNOWN excitation.

    H(f) = S_{u,T}(f) / S_{u,u}(f)          coherence-gated, coherently averaged over edges

EVENT DEFINITION.  🛑 Edges are taken from the LOGGED TRIGGER -- the rising transition of
`lateralManeuverPlan.valid`, plus interior discontinuities of the commanded lateral accel
(>= 0.30 m/s^2 over 0.10 s) **while that flag is true**.  An amplitude-only detector is NOT
admissible: see blocker B0, where the maneuver's own edges are shown to sit inside ordinary
engaged driving's range.  Amplitude is measured on the 100 Hz `cc_curv * v^2` reconstruction, NOT
on `lateralManeuverPlan.desiredCurvature`, which is published at 20 Hz -- its Nyquist is 10 Hz and
it cannot resolve the band.  The plan message supplies the WHEN; the 100 Hz stream supplies the
WHAT.  Window: **-0.5 s to +2.0 s** around the edge, NFFT 256 at 100 Hz.
A RUN (one `Maneuver` repetition, 3 per maneuver) is the BOOTSTRAP UNIT -- `feedback-episodes-not-
windows`.  Expected: 6 maneuvers x 3 runs x 2 usable edges = **~36 edges in ~18 runs**.

==================================================================================================
3.  POWER -- computed from real data BEFORE the drive, and it is the reason to take it
==================================================================================================
E3 was given REAL post-edge segments from all 22 disengage edges in the corpus with a KNOWN
ring-down injected at A x the pre-edge 6-9 Hz band RMS:

    zeta 0.05, A = 1.0  -> detected on  3/22 (14 %)      recovered 0.038-0.062  (true 0.050)
    zeta 0.05, A = 2.0  -> detected on  9/22 (41 %)      recovered 0.043-0.063
    zeta 0.05, A = 4.0  -> detected on 12/22 (55 %)      recovered 0.033-0.059
    zeta 0.02, A = 4.0  -> detected on 14/22 (64 %)      recovered 0.015-0.021  (true 0.020)

🛑 **AT THE PHYSICALLY REALISTIC AMPLITUDE (A = 1) THE DISENGAGE-EDGE RING-DOWN HAS ~14 % POWER.**
With 7 clean edges corpus-wide, the expected number of detections if a zeta = 0.05 ring WERE
present is ~1.  E3 detected 0/7.  ⇒ **that null is UNINTERPRETABLE and licenses nothing.**  The
kit's existing ring-down numbers rest on E1/E2, which return a finite zeta on 6 of those same 7
edges -- values spanning 0.0002 to 0.0998, a 500x spread -- i.e. they are not measuring damping.

⇒ The drive's job is to buy amplitude and replicates: ~36 edges instead of 7, each with a KNOWN
trigger instant so they can be COHERENTLY averaged (sqrt(36) = 6x SNR), and a known input so the
transfer function can be formed instead of a bare ring-down.

==================================================================================================
4.  🛑 THE EXCITATION IS RATE-LIMITED -- quantified, and it constrains the bands
==================================================================================================
`lateral_maneuversd` commands a TRUE step (`np.interp` on a single breakpoint holds a constant),
but `selfdrive/controls/lib/drive_helpers.py:clip_curvature` slews desired curvature at
`MAX_LATERAL_JERK = 5.0 m/s^3`, so the delivered input is a RAMP of duration |da|/5.0 s,
**independent of speed**.  A ramp has |sinc(fT)| spectrum:

    edge                     |da|   T       nulls <= 15 Hz     6 Hz     8 Hz    12 Hz    14 Hz
    step onset / release     0.5   0.100 s  10.0             -5.9 dB -12.6 dB -16.1 dB -13.3 dB
    step REVERSAL            1.0   0.200 s  5.0, 10.0, 15.0 -16.1 dB -14.5 dB -18.0 dB -23.5 dB

⇒ 🛑 **EXCLUDED BINS, PRE-DECLARED: 9.5-10.5 Hz (both edges) and 4.5-5.5 Hz (reversal edges).**
   A dip there is openpilot's jerk limiter, not the car.  Reporting one would be reporting our own
   instrument -- the V97 failure class.
⇒ The 12-19 dB attenuation is NOT fatal because H = T/u is a RATIO: the sinc divides out
   everywhere except AT a null.  It costs coherence, not accuracy.  Coherence is therefore the
   gate, and it is pre-registered at **coh^2 >= 0.30** per bin.
⚠ **No openpilot change is proposed.**  `feedback-no-openpilot-side-modifications` is standing:
   openpilot is a measurement instrument only.  If the orchestrator ever wanted flat excitation
   through 14 Hz it would take raising `MAX_LATERAL_JERK` in maneuver mode -- I am NAMING it, not
   doing it, and I do not recommend it: the ratio estimator does not need it.

==================================================================================================
5.  RUNNABILITY OF THE SUITE ON THIS CAR -- checked in the tree, all green
==================================================================================================
  ✅ `LateralManeuverMode` registered  `common/params_keys.h:101` (BOOL, CLEAR_ON_MANAGER_START)
  ✅ `LateralManeuverStatus` registered `common/params_keys.h:425` (JSON)
  ✅ process wired  `system/manager/process_config.py:159`, gate at `:49`
     -- 🛑 **requires `LongitudinalManeuverMode` to be OFF**; both on = the process never starts.
  ✅ UI toggle exists `selfdrive/ui/mici/layouts/settings/developer.py:61` and in The Galaxy
     (`starpilot/system/the_galaxy/the_galaxy.py:4409`), so no manual `echo` into /data/params.
  ✅ `lateralManeuverPlan` in `cereal/services.py:53` (20 Hz) and `cereal/log.capnp:1280`
  ✅ consumed by `selfdrive/controls/controlsd.py` -- overrides `desiredCurvature` when
     `sm.valid['lateralManeuverPlan']` and `CC.latActive`
  ✅ no car whitelist -- `lateral_maneuversd` imports only `Action`/`Maneuver` from the
     longitudinal tool and does NOT call its `get_..._support` capability gate
  ✅ speed: Honda Bosch `minEnableSpeed` = 3 mph, `STEER_GLOBAL_MIN_SPEED` = 3 mph; the suite runs
     at 20 and 30 mph -- clear
  ✅ `generate_report.py` reads a normal route via `openpilot.tools.lib.logreader.LogReader` and
     needs `matplotlib` + `tabulate`; it keys runs off `alertDebug.alertText1 == "Complete"`, so
     ALERTDEBUG MUST BE IN THE LOG (it is, `cereal/services.py`, 20 Hz)

  🛑 BLOCKERS / CONDITIONS ON THE DRIVE, in order of how likely they are to waste it:
  B0 🛑🛑 **THE EXTRACTOR MUST CAPTURE `lateralManeuverPlan` (`valid` + `desiredCurvature`)
     AND `alertDebug`.**  No existing `extract_r*.py` does.  Without the logged trigger the
     drive is UNANALYSABLE: measured on routes 0x9e/0x97/0x96/0x73, the maneuver's own
     0.5 m/s^2 onset edge sits at ordinary engaged driving's **99.99th percentile** over a
     0.1 s window, and its 1.0 m/s^2 reversal is at ordinary driving's **maximum**.  An
     amplitude threshold therefore cannot tell them apart in either direction.
     ⭐ Corollary worth stating to the operator: **the maneuver is NOT a bigger excitation
     than ordinary driving.**  Its whole value is the KNOWN TRIGGER INSTANT and the ~36
     REPLICATES, which buy coherent averaging (sqrt(36) = 6x SNR).  Do not sell it as
     'a harder shove'; it is not one.
  B1 **`steeringPressed` ABORTS AND REPEATS THE MANEUVER** (`lateral_maneuversd.py`, the
     `maneuver.reset()` branch).  The operator must keep HANDS OFF for the whole suite.
     🛑 This is in direct tension with the kit's own finding that the symptom regime is
     ENGAGED + HANDS-ON OVERRIDE (`reference-accord-steeringpressed-mask-excludes-the-symptom-
     regime`).  **This drive measures the PLANT, not the symptom.**  It must not be scored against
     grinding / ratcheting, and the operator should be told that before he drives it.
  B2 **Road conditions gate hard**: `MAX_CURV = 0.002` (500 m radius), `MAX_ROLL = 0.08` (4.6 deg),
     `MAX_SPEED_DEV = 0.7 m/s`, 2.0 s of stable conditions before each run.  Needs a genuinely
     straight, flat, low-traffic road with ACC holdable at 20 and then 30 mph.
  B3 **ACC must be set manually to each target speed**; the suite will sit in "Set speed to X mph"
     until it is.  20 mph first, then 30 mph -- the order is fixed by `MANEUVERS`.
  B4 The 0.5 m/s^2 steps are commanded lateral acceleration.  At 20 mph that is ~16 deg of steering
     angle, at 30 mph ~7 deg.  **Confirm the operator is content with that on a public road.**
  B5 `LateralManeuverMode` is `CLEAR_ON_MANAGER_START | CLEAR_ON_OFFROAD_TRANSITION` -- it must be
     set and then the vehicle turned back on, exactly as the README says, or it self-clears.
  B6 Sine maneuvers (0.5 Hz) contribute NOTHING to this analysis and cost ~1/3 of the drive.  They
     cannot be skipped without editing `MANEUVERS`, which is an openpilot change -- so do not skip
     them, just do not analyse them.  (They are a useful positive control for the report generator.)

==================================================================================================
6.  🛑 THE PRE-REGISTRATION -- statistics, bands, masks, controls, and the sentence a null licenses
==================================================================================================
MASKS (fixed now, not after seeing data)
  M1 engaged        `cc_lat > 0.5` on every frame of the window.  NOT `cruiseState`.
  M2 hands-off      window p90|tq| < 300 counts (`studies/ratchet/v97_return_to_centre.py`'s HOLD_OFF).  The suite
                    enforces this anyway by aborting on `steeringPressed`.
  M3 speed          |v - v_target| < 0.7 m/s, matching the suite's own gate.  Speed is reported as
                    a per-window census (`accord-averaged-spectrum-needs-matched-speed-
                    distributions`).
  M4 excluded bins  9.5-10.5 Hz always; 4.5-5.5 Hz on reversal edges.  See section 4.
  M5 coherence      coh^2 >= 0.30 per bin, else the bin is dropped and the drop is REPORTED.

ENDPOINT 1 (PRIMARY, scale-free, and the one that adjudicates the two readings)
    `tau = J_w/b_w = tan(180 - |arg Z|)/w`, pooled over 4-14 Hz excluding M4, Z = tq/rate_f,
    bootstrap over RUNS.  Then  **Q_implied(8.16 Hz) = 2 pi * 8.16 * tau**.
      PASS-LOOP   Q_implied <= 3   -> the column cannot support a Q ~ 10 mode at 8.16 Hz
                                     => (ii) stands, the 8 Hz line is the LOOP.
      PASS-PLANT  Q_implied >= 7   -> it can => (i) stands, it IS the torsion-bar mode.
      AMBIGUOUS   3 < Q_implied < 7 -> stated as ambiguous, no claim either way.
    Existing-data prior: 1.10-1.88 across five routes.  🛑 A drive result near 1.5 is a
    REPLICATION under known excitation, not a new claim.

ENDPOINT 2 (SHAPE)  |H(f)| = |T_bar/e4tq| over 4-14 Hz, coherently averaged over edges.
      A PASSIVE 2-pole at 8.16 Hz with Q = 10 predicts a peak of **10x** over the 3-5 Hz level.
      The 2026-08-20 measurement on ordinary driving was **12.38 at 7.90 Hz** (coh^2 0.366).
      PASS-PLANT  peak/(3-5 Hz level) >= 5 AND the peak is within 7.5-8.8 Hz
      PASS-LOOP   peak/(3-5 Hz level) <= 2.5
    ⭐ THE POINT: under the maneuver `e4tq` is a SCRIPTED step, so if the 8 Hz peak in |T/e4tq|
      SURVIVES with the same height under exogenous excitation, it is the plant; if it COLLAPSES
      relative to ordinary driving, the 12.38 was feedback and it is the loop.

ENDPOINT 3 (RING-DOWN, secondary, E3 only)  per-edge (f_n, zeta) from the matrix pencil on the
      1.5 s after the RELEASE edge of each run.  Report the REFUSAL COUNT beside every value.
      Quotable only if E3 fires on >= 8 of ~18 release edges; below that, say UNDERPOWERED.

CONTROLS, all run BEFORE any number is quoted (`feedback-run-the-control-before-the-measurement`)
  C1 NEGATIVE BAND      15-22 Hz carried through every statistic.  A broadband change must not
                        read as an 8 Hz result.
  C2 SURROGATE          pair each edge's OUTPUT with a DIFFERENT run's INPUT (circular shift over
                        runs).  Gives the null distribution of coh^2 and of the |H| peak.
  C3 NO-EXCITATION ARM  the engaged stretches BETWEEN maneuvers, matched on speed, analysed
                        identically.  If the 8 Hz peak is the same there, the maneuver added
                        nothing and the drive is a null on its own terms.
  C4 SPLIT-HALF         runs split at random into halves; the half/half ratio is the RESOLUTION
                        FLOOR.  No effect below that floor is quotable.
  C5 SPEED CENSUS       per-window speed distribution printed for every arm.
  C6 POSITIVE CONTROL   the section-3 injection re-run on THIS route's own backgrounds, so the
                        power statement is about this drive and not about the old corpus.

🛑🛑 THE SENTENCE A NULL WILL LICENSE, WRITTEN BEFORE THE DRIVE
  > "Under a scripted, exogenous, ~36-replicate step excitation with a known trigger instant, the
  >  torsion-bar torque's response at 4-14 Hz showed no resonant peak above 2.5x the 3-5 Hz level
  >  (C2 surrogate floor X, C4 split-half floor Y), and the column's own measured J_w/b_w admits a
  >  Q of at most Z at 8.16 Hz.  The 8.16 Hz line therefore is not a passive wheel-on-torsion-bar
  >  resonance, and `docs/research/ANALYSIS-2026-08-20-torsion-bar-and-lane-weight.md` section 2 is
  >  RETRACTED in favour of `memory/accord/mechanism/accord-the-8hz-mode-is-the-loop-not-the-plant.md`."

  And the sentence the OPPOSITE null licenses, equally pre-committed:
  > "The peak survived at >= 5x under exogenous excitation and J_w/b_w admitted Q >= 7, so the
  >  passive plant DOES carry the mode, and the loop identification's `Z0 = 2792 @ -92.45 deg` is
  >  wrong -- most likely because its 4x/8x pair is confounded by Lever B, which that memory
  >  already flags."

🛑 AND THE HONEST ANSWER TO "COULD WE TELL?"
  YES for endpoints 1 and 2 -- both have a measured prior, a pre-declared threshold, and a
  surrogate floor, and endpoint 1 is scale-free so it cannot die to the `rate_c`/`rate_f` scale
  ambiguity.  **NO for endpoint 3** on current expectations: section 3's power table says a
  ring-down needs the ring to start at >= 2x the pre-edge band RMS to be seen, and nothing
  guarantees the maneuver delivers that.  Endpoint 3 is carried as a bonus, NOT as a reason to
  drive.  If the orchestrator wants the drive justified on endpoint 3 alone, it is NOT ready.

==================================================================================================
7.  WHAT THIS DRIVE CANNOT DO -- say it to the operator before he drives
==================================================================================================
  * It CANNOT score grinding, vibrating, micro-ratcheting or ratcheting.  Those are his words for
    symptoms produced ENGAGED + HANDS-ON, and this suite aborts the moment he touches the wheel.
  * It CANNOT test any firmware lever.  V103 is on the car; nothing here depends on which build is
    flashed, which is exactly why it is worth doing -- it measures the PLANT, which no build moves.
  * It CANNOT settle `k` (the torsion-bar rate) on its own; endpoint 1 is a RATIO and endpoint 2 is
    a SHAPE.  Both are deliberately chosen to avoid needing `k` or the counts->N.m scale.
"""
from __future__ import annotations
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L                      # noqa: E402
from ringdown_validate import e3_pencil      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = L.FS
NFFT = 256
F = np.fft.rfftfreq(NFFT, 1 / FS)
PRE_S, POST_S = 0.5, 2.0
EDGE_MIN_DA = 0.30                   # m/s^2 change over a 0.10 s window, INSIDE an
                                     # active maneuver window only -- see find_edges
HOLD_OFF = 300.0
COH_MIN = 0.30
EXCL = [(9.5, 10.5)]                 # always; reversal edges add (4.5, 5.5)
BAND = (4.0, 14.0)
NEG = (15.0, 22.0)
NBOOT = 2000


def hdr(s):
    print("\n" + "=" * 104); print(s); print("=" * 104, flush=True)


def excl_mask(f, reversal=False):
    m = np.ones_like(f, bool)
    for lo, hi in EXCL + ([(4.5, 5.5)] if reversal else []):
        m &= ~((f >= lo) & (f <= hi))
    return m


def find_edges(u, v, plan_valid=None):
    r"""Edges of the commanded lateral accel.

    🛑 THE LOGGED TRIGGER IS MANDATORY, NOT A CONVENIENCE.  An amplitude detector CANNOT separate
    maneuver edges from ordinary engaged driving on this car -- measured over routes 0x9e/0x97/
    0x96/0x73, engaged, the change in commanded lateral accel over the maneuver's own ramp lengths:

        window        ordinary p99.9   p99.99      max      maneuver delivers
        10 fr (0.1 s)     0.313        0.460      0.531     0.500   (step onset / release)
        20 fr (0.2 s)     0.560        0.743      1.015     1.000   (step reversal)

    ⇒ the onset edge sits at ordinary driving's 99.99th percentile and the reversal edge is at its
    MAXIMUM.  A threshold that catches the maneuver also catches ordinary driving, and one that
    excludes ordinary driving also excludes the maneuver.  **`plan_valid` must be supplied.**

    `plan_valid` = `lateralManeuverPlan.valid` resampled onto the 100 Hz grid.  Edges are taken at
    its rising transition and at every interior discontinuity of the commanded accel WHILE it is
    true -- i.e. inside a window the tool itself declares active, where no ordinary-driving
    excursion can intrude.
    """
    a = np.asarray(u, float) * np.maximum(np.asarray(v, float), 1.0) ** 2
    if plan_valid is None:
        raise RuntimeError(
            "lateralManeuverPlan.valid is absent from this cache. The extractor MUST capture it "
            "(see section 5, blocker B0). An amplitude-only edge detector is NOT admissible here.")
    pv = np.asarray(plan_valid, float) > 0.5
    W = int(0.10 * FS)
    idx = list(np.flatnonzero(np.diff(pv.astype(int)) > 0) + 1)          # run onsets
    d = np.abs(a[W:] - a[:-W])
    inner = np.flatnonzero((d >= EDGE_MIN_DA) & pv[W:] & pv[:-W]) + W // 2
    idx += list(inner)
    keep, last = [], -10 ** 9
    for i in sorted(int(x) for x in idx):
        if i - last > int(0.5 * FS):
            keep.append(i); last = i
    return keep, a


def spec(x, y):
    w = np.hanning(len(x))
    X = np.fft.rfft((x - x.mean()) * w)
    Y = np.fft.rfft((y - y.mean()) * w)
    return np.abs(X) ** 2, np.conj(X) * Y, np.abs(Y) ** 2


def pool(ws):
    return tuple(np.sum([w[i] for w in ws], axis=0) for i in range(3))


def tau_from_Z(Sxx, Sxy, Syy, reversal=False):
    ch = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
    H = Sxy / np.maximum(Sxx, 1e-30)
    m = (F >= BAND[0]) & (F <= BAND[1]) & (ch >= COH_MIN) & excl_mask(F, reversal)
    if m.sum() < 5:
        return np.nan, int(m.sum())
    a = 180.0 - np.abs(np.angle(H[m], deg=True))
    ok = (a > 3) & (a < 87)
    if ok.sum() < 4:
        return np.nan, int(ok.sum())
    return float(np.average(np.tan(np.radians(a[ok])) / (2 * np.pi * F[m][ok]),
                            weights=ch[m][ok])), int(ok.sum())


def analyse(route):
    if route not in L.ROUTES:
        L.ROUTES[route] = L._mk(route, "maneuver", gain=0, clamp=0, leverB=False, idcode=0, bits="")
    if not L.ROUTES[route]["segs"]:
        print("no cache for route 0x%s -- extract it first (see rlog-tools/decode/extract_r9e.py)" % route)
        return

    hdr("EDGE CENSUS -- did the suite actually run, and how many edges did we get?")
    runs = []                                    # each run = list of (Sxx,Sxy,Syy) for tq/e4tq
    zruns = []                                   # same for tq/rate_f
    rel_segs = []
    nedge = 0
    for blk in L.all_blocks(route):
        lat = np.asarray(blk["cc_lat"], float) > 0.5
        tq = np.asarray(blk["tq"], float)
        rf = np.asarray(blk["rate_f"], float)
        u = np.asarray(blk["e4tq"], float)
        v = np.asarray(blk.get("v_rear", blk["cs_v"]), float)
        cc = np.asarray(blk.get("cc_curv", blk.get("ct_curv", np.zeros_like(tq))), float)
        if "man_valid" not in blk:
            print("    🛑 cache has no `man_valid` (lateralManeuverPlan.valid). See blocker B0 --")
            print("       the drive is UNANALYSABLE without it.  Re-extract before running this.")
            return
        idx, acmd = find_edges(cc, v, blk["man_valid"])
        npre, npost = int(PRE_S * FS), int(POST_S * FS)
        for i in idx:
            if i - npre < 0 or i + npost >= len(tq):
                continue
            sl = slice(i - npre, i - npre + NFFT)
            if sl.stop > len(tq):
                continue
            if lat[sl].mean() < 0.98:
                continue
            if np.percentile(np.abs(tq[sl]), 90) >= HOLD_OFF:
                continue
            nedge += 1
            runs.append(spec(u[sl], tq[sl]))
            zruns.append(spec(rf[sl], tq[sl]))
            rel_segs.append(tq[i:i + int(1.5 * FS)])
    print("    usable edges (engaged, hands-off, full window): %d" % nedge)
    if nedge < 6:
        print("    🛑 fewer than 6 usable edges. The suite did not run, or every run aborted.")
        print("       Check `LateralManeuverStatus` history and the alertDebug stream first.")
        return

    hdr("ENDPOINT 1 (PRIMARY) -- scale-free J_w/b_w and the Q it admits at 8.16 Hz")
    t0, nb = tau_from_Z(*pool(zruns))
    boot = []
    rng = np.random.default_rng(11)
    for _ in range(NBOOT):
        pk = rng.integers(0, len(zruns), len(zruns))
        t, _n = tau_from_Z(*pool([zruns[i] for i in pk]))
        if np.isfinite(t) and t > 0:
            boot.append(t)
    if np.isfinite(t0) and len(boot) > 200:
        lo, hi = np.percentile(boot, 2.5), np.percentile(boot, 97.5)
        q = lambda tt: 2 * np.pi * 8.16 * tt
        print("    J_w/b_w = %.1f ms [%.1f, %.1f]   (%d bins passed coh >= %.2f)"
              % (t0 * 1e3, lo * 1e3, hi * 1e3, nb, COH_MIN))
        print("    Q_implied(8.16 Hz) = %.2f [%.2f, %.2f]" % (q(t0), q(lo), q(hi)))
        verdict = ("PASS-LOOP  (<= 3: the column cannot carry a Q~10 mode at 8.16 Hz)"
                   if q(hi) <= 3 else
                   "PASS-PLANT (>= 7: it can)" if q(lo) >= 7 else
                   "AMBIGUOUS  (3 < Q < 7) -- state as ambiguous, claim nothing")
        print("    ⇒ PRE-REGISTERED VERDICT: %s" % verdict)
        print("    prior from existing logs (studies/identification/plant_phase_corner.py): Q = 1.10 - 1.88, five routes")
    else:
        print("    🛑 insufficient coherent bins -- ENDPOINT 1 UNRESOLVED. Say so; claim nothing.")

    hdr("ENDPOINT 2 (SHAPE) -- |H| = |T_bar/e4tq|, coherently averaged over edges")
    Sxx, Sxy, Syy = pool(runs)
    ch = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
    H = np.abs(Sxy) / np.maximum(Sxx, 1e-30)
    ok = excl_mask(F)
    ref = float(np.median(H[(F >= 3) & (F <= 5) & ok]))
    m = (F >= 6.5) & (F <= 10.5) & ok & (ch >= COH_MIN)
    print("    %-8s %10s %10s %10s" % ("f Hz", "|H|", "|H|/ref", "coh2"))
    for f0 in (3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 16, 18, 20):
        b = (F >= f0 - 0.5) & (F < f0 + 0.5)
        print("    %-8d %10.4g %10.2f %10.3f"
              % (f0, np.median(H[b]), np.median(H[b]) / max(ref, 1e-12), np.median(ch[b])))
    if m.any():
        i = int(np.argmax(H[m]))
        pk, fpk = float(H[m][i]), float(F[m][i])
        print("\n    peak in 6.5-10.5 Hz: %.4g at %.2f Hz -> %.2f x the 3-5 Hz level"
              % (pk, fpk, pk / max(ref, 1e-12)))
        print("    ⇒ PRE-REGISTERED VERDICT: %s"
              % ("PASS-PLANT" if (pk / ref >= 5 and 7.5 <= fpk <= 8.8) else
                 "PASS-LOOP" if pk / ref <= 2.5 else "AMBIGUOUS"))
    else:
        print("\n    🛑 no bin in 6.5-10.5 Hz reached coh >= %.2f -- ENDPOINT 2 UNRESOLVED." % COH_MIN)

    hdr("CONTROLS")
    # C2 surrogate: pair each edge's output with another edge's input
    sur = []
    for k in range(len(runs)):
        j = (k + len(runs) // 2) % len(runs)
        sur.append((runs[k][0], np.conj(np.sqrt(runs[k][0] + 0j)) * np.sqrt(runs[j][2] + 0j),
                    runs[j][2]))
    sSxx, sSxy, sSyy = pool(sur)
    sch = np.abs(sSxy) ** 2 / np.maximum(sSxx * sSyy, 1e-30)
    bb = (F >= BAND[0]) & (F <= BAND[1])
    print("    C2 SURROGATE (output paired with another edge's input): coh2 median %.3f "
          "vs TRUE %.3f" % (np.median(sch[bb]), np.median(ch[bb])))
    print("    C1 NEGATIVE BAND 15-22 Hz: |H| median %.4g  (vs 3-5 Hz ref %.4g)"
          % (np.median(H[(F >= NEG[0]) & (F <= NEG[1])]), ref))
    # C4 split-half
    rng = np.random.default_rng(5)
    ratios = []
    for _ in range(200):
        p = rng.permutation(len(runs))
        a, b = p[:len(p) // 2], p[len(p) // 2:]
        Ha = np.abs(pool([runs[i] for i in a])[1]) / np.maximum(pool([runs[i] for i in a])[0], 1e-30)
        Hb = np.abs(pool([runs[i] for i in b])[1]) / np.maximum(pool([runs[i] for i in b])[0], 1e-30)
        mm = (F >= 6.5) & (F <= 10.5)
        ratios.append(np.median(Ha[mm]) / max(np.median(Hb[mm]), 1e-30))
    ratios = np.array(ratios)
    print("    C4 SPLIT-HALF resolution floor: half/half |H| ratio = %.3f [%.3f, %.3f]"
          % (np.median(ratios), np.percentile(ratios, 2.5), np.percentile(ratios, 97.5)))
    print("       🛑 no effect smaller than this spread is quotable.")

    hdr("ENDPOINT 3 (SECONDARY) -- E3 ring-down on the release edges")
    got = []
    for s in rel_segs:
        f3, z3 = e3_pencil(s, FS, f_lo=4.0, f_hi=14.0)
        if np.isfinite(z3):
            got.append((f3, z3))
    print("    E3 fired on %d of %d release segments." % (len(got), len(rel_segs)))
    if len(got) >= 8:
        z = np.array([g[1] for g in got]); f = np.array([g[0] for g in got])
        print("    f_n = %.2f-%.2f Hz (med %.2f) · zeta = %.3f-%.3f (med %.3f) · Q = %.1f-%.1f"
              % (f.min(), f.max(), np.median(f), z.min(), z.max(), np.median(z),
                 1 / (2 * z.max()), 1 / (2 * z.min())))
    else:
        print("    🛑 fewer than 8 -- ENDPOINT 3 is UNDERPOWERED, exactly as pre-registered.")
        print("       Report it as underpowered.  Do NOT quote E1/E2 numbers in its place.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", required=True, help="hex route tag with an extracted cache, e.g. 9f")
    analyse(ap.parse_args().route)


if __name__ == "__main__":
    main()
