# -*- coding: utf-8 -*-
"""studies/grind/v288_describing_function.py -- ITEM 4: re-run slewburst's A2 prediction with the
CORRECTED V288 gains, derived from the cave arithmetic rather than interpolated.
Subagent `combsize`, 2026-09-10.  ANALYSIS ONLY.

THE CORRECTION OF RECORD (orchestrator, 2026-09-10).  V288 rev 2's setpoint pre-filter is NOT the LTI
first-order lag `y += (x-y)>>4` that slewburst's A1b assumed.  The cave is

    delta = sp - y_prev
    step  = delta >> 4                      # ARITHMETIC shift, floors toward -inf
    if step == 0 and delta != 0:  step = 1  # ANTI-STICK
    y += step

The integer floor plus the anti-stick make the gain AMPLITUDE-DEPENDENT.  slewburst applied the LTI
|H(20 Hz)| = 0.4572 (a x2.19 cut) at every amplitude; the orchestrator's measured figures are 0.99 at
A = 4, 0.95 at A = 8, 0.61 at A = 16, 0.45 at A >= 40 setpoint counts, and the ring itself converts to
only 4.0-10.7 sp counts -- so the real attenuation on the ring is a few percent, not x2.19.

This file does not interpolate those four points.  It RE-DERIVES the describing function from the
arithmetic above, confirms it reproduces them, and then re-states what the echo/comb hypothesis
actually predicted for V288.  🛑 The point of the exercise is that the prediction flips: under the LTI
reading V288 was a decisive test that returned a null; under the correct arithmetic V288 BARELY
TOUCHED the ring, so its null is uninformative in BOTH directions.

Run: python rlog-tools/studies/grind/v288_describing_function.py
Writes _scratch/v288_describing_function.txt beside it.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS1K = 1000.0
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def cave(x):
    """V288 rev 2's setpoint pre-filter, integer-exact, one sample per 1 kHz tick.

    `delta >> 4` on a signed integer is an ARITHMETIC shift: it floors toward -infinity, so it is
    np.floor(delta / 16) and NOT int(delta / 16).  That asymmetry is part of the mechanism.
    """
    y = np.int64(np.round(x[0]))
    out = np.empty(len(x), np.int64)
    for i, xi in enumerate(np.round(x).astype(np.int64)):
        delta = xi - y
        step = delta >> 4                       # arithmetic shift, floors toward -inf
        if step == 0 and delta != 0:
            step = 1 if delta > 0 else -1       # anti-stick, symmetric
        y += step
        out[i] = y
    return out


def fundamental_gain(A, f, n_cyc=60, dc=0.0):
    """describing-function gain: |Y(f)| / |X(f)| for x = dc + A sin(2 pi f t), integer input."""
    n = int(round(n_cyc * FS1K / f))
    t = np.arange(n) / FS1K
    x = dc + A * np.sin(2 * np.pi * f * t)
    y = cave(x).astype(float)
    skip = n // 4                                # drop the start-up transient
    t2, x2, y2 = t[skip:], x[skip:], y[skip:]
    e = np.exp(-2j * np.pi * f * t2)
    X = (x2 - x2.mean()) @ e
    Y = (y2 - y2.mean()) @ e
    return float(np.abs(Y) / max(np.abs(X), 1e-30)), float(np.degrees(np.angle(Y / X)))


def main():
    OUT.clear()
    pr("=" * 118)
    pr("ITEM 4 -- V288's REAL PRE-FILTER GAIN, RE-DERIVED FROM THE CAVE ARITHMETIC")
    pr("=" * 118)
    pr("")
    pr("A1  THE DESCRIBING FUNCTION at 20.3 Hz, 1 kHz, against the orchestrator's measured figures")
    pr("")
    pr("%10s %12s %12s %14s %14s" % ("A (sp cts)", "gain", "phase deg", "orch. figure", "agreement"))
    pr("-" * 118)
    REF = {4: 0.99, 8: 0.95, 16: 0.61, 40: 0.45}
    for A in (2, 4, 6, 8, 10.7, 12, 16, 24, 40, 80, 160):
        gmag, gph = fundamental_gain(A, 20.3)
        ref = REF.get(A if isinstance(A, int) else None)
        pr("%10.1f %12.4f %12.1f %14s %14s" %
           (A, gmag, gph, ("%.2f" % ref) if ref else "-",
            ("%+.3f" % (gmag - ref)) if ref else "-"))
    pr("")
    lti = (1 / 16.0) / abs(1 - (15 / 16.0) * np.exp(-1j * 2 * np.pi * 20.3 / FS1K))
    pr("For comparison, the LTI first-order lag y += (x-y)/16 that slewburst's A1b assumed:")
    pr("   |H(20.3 Hz)| = %.4f   (a x%.2f cut, -%.1f dB) -- INDEPENDENT of amplitude." %
       (lti, 1 / lti, -20 * np.log10(lti)))
    pr("")
    pr("🛑 THE GAP.  At the ring's OWN amplitude the cave is nearly TRANSPARENT; the LTI reading says it")
    pr("cuts the drive by more than half.  The LTI figure is only approached at A >~ 40 sp counts, and")
    pr("the ring never gets there.")
    pr("")

    pr("=" * 118)
    pr("A2  WHERE THE RING ACTUALLY SITS ON THAT CURVE")
    pr("=" * 118)
    pr("The measured 20 Hz command line is 15-40 raw 0xE4 counts.  Converting to setpoint counts:")
    pr("   raw / 16.125736 raw-per-idx-LSB  ->  idx LSB;   x 4.30 sp per idx  ->  setpoint counts")
    pr("")
    pr("%10s %14s %14s %12s %14s" % ("raw counts", "idx LSB", "sp counts", "gain", "attenuation"))
    pr("-" * 118)
    for raw in (15, 20, 25, 30, 40):
        sp = raw / 16.125736 * 4.30
        gmag, _ = fundamental_gain(sp, 20.3)
        pr("%10.0f %14.3f %14.2f %12.4f %14s" % (raw, raw / 16.125736, sp, gmag,
                                                 "%.1f %%" % (100 * (1 - gmag))))
    pr("")
    g_lo, _ = fundamental_gain(15 / 16.125736 * 4.30, 20.3)
    g_hi, _ = fundamental_gain(40 / 16.125736 * 4.30, 20.3)
    pr("⇒ V288's pre-filter attenuated the grinding band by %.0f-%.0f %%, NOT the 54 %% the LTI reading"
       % (100 * (1 - max(g_lo, g_hi)), 100 * (1 - min(g_lo, g_hi))))
    pr("  gave.  A slew-capped frame is 32.8 sp counts and DOES see real attenuation (gain %.2f) -- so"
       % fundamental_gain(32.8, 20.3)[0])
    pr("  the cave was working; it simply was not working ON THE RING.")
    pr("")

    pr("=" * 118)
    pr("A3  WHAT THE ECHO / COMB HYPOTHESIS THEREFORE PREDICTED FOR V288 -- and what the car did")
    pr("=" * 118)
    pr("The sustaining criterion used throughout is  ratio x 6.00 >= 1,  where ratio = (command-side")
    pr("delivered in-band counts) / (measured in-band counts) and 6.00 = 1/(1-exp(-2 pi zeta)) at")
    pr("zeta = 0.029.  My measured r39/V282 command leg is 11.56 / 57.21 = 0.2021, ceiling 1.213.")
    pr("")
    pr("%-46s %10s %10s %s" % ("reading", "gain", "ceiling", "prediction for V288"))
    pr("-" * 118)
    base = 6.0 * 11.56 / 57.21
    pr("%-46s %10s %10.3f %s" % ("V282, no pre-filter (the flown baseline)", "-", base,
                                 "(this is the baseline)"))
    pr("%-46s %10.4f %10.3f %s" % ("slewburst A1b -- LTI lag, amplitude-blind", lti, base * lti,
                                   "RING COLLAPSES (falls below 1)"))
    for raw, lab in ((15, "corrected -- ring at 15 raw counts"), (40, "corrected -- ring at 40 raw counts")):
        gmag, _ = fundamental_gain(raw / 16.125736 * 4.30, 20.3)
        c = base * gmag
        pr("%-46s %10.4f %10.3f %s" % (lab, gmag, c,
                                       "NO VISIBLE CHANGE" if c >= 1.0 else "marginal, below 1"))
    pr("")
    pr("WHAT THE CAR DID (r5e_v288 vs r39, GRIND1-CENSUS-V288-R5E-2026-09-08.md): same 20.0-20.4 Hz")
    pr("line at all three operator bookmarks; 258 vs 239 episodes/h; envelope p50 126 vs 127; f 20.06")
    pr("vs 20.03 Hz; rung-bell ratio 2.41 vs 2.25; no new line above 22 Hz -- with the cave demonstrably")
    pr("running (b4.5 live on 99.5 %% of engaged frames).  EVERY RING STATISTIC UNCHANGED.")
    pr("")
    pr("⇒ THE CORRECTED PREDICTION IS 'NO VISIBLE CHANGE', AND THE CAR AGREED.  [EVIDENCE]")
    pr("")
    pr("🛑 AND THE CONSEQUENCE THAT MATTERS MORE THAN THE AGREEMENT.  Under the LTI reading, V288 was a")
    pr("DECISIVE test of the reference/excitation-side class and it returned a null -- which is how")
    pr("STATE.md came to say that class is EXHAUSTED.  Under the correct arithmetic V288 changed the")
    pr("ring's drive by a few percent, so its null CANNOT falsify the class: an experiment that did not")
    pr("move the independent variable cannot test the dependent one.  V288's null is uninformative in")
    pr("BOTH directions -- it neither supports nor refutes the comb or the echo.  The reference-side")
    pr("class is UNTESTED, not exhausted.  [EVIDENCE for the arithmetic; BELIEF for the reading]")
    pr("")
    pr("⚠ AND WHAT THIS DOES NOT RESCUE.  Re-opening the reference-side class does not make the comb or")
    pr("the echo SUFFICIENT -- that is settled separately, and against them, by the mirror sizing: the")
    pr("whole command leg is 20 %% of the delivered in-band torque on V282 and 4 %% on V289, while the")
    pr("feedback leg is 88-100 %% everywhere.  V288 being uninformative removes a FALSE CONFIRMATION of")
    pr("a conclusion that the sizing reaches on much stronger grounds.")
    with open(os.path.join(SCR, "v288_describing_function.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/v288_describing_function.txt")


if __name__ == "__main__":
    main()
