# -*- coding: utf-8 -*-
"""studies/grind/task5_consequence.py -- WHAT THE ALIAS AMBIGUITY ACTUALLY COSTS THE V286 DECISION,
and one within-channel control that separates the 27-32 Hz feature from the folded shelf.

Two parts.

A  THE COST OF BEING WRONG ABOUT THE FREQUENCY.  Aliasing relocates a frequency label; it does not
   destroy energy (there is no anti-alias filter, so nothing is attenuated on the way down).  So the
   channel is an HONEST ENERGY METER and a DISHONEST FREQUENCY METER.  That distinction is the whole
   answer for V286: a decision of the form "did HF energy grow?" is safe on this channel; a decision of
   the form "the binding mode is AT 27-32 Hz, so the phase margin there is X" is not.  This section
   prints, from the exact decompiled 1 kHz chain, how different the controller looks at 30 Hz vs at
   70 Hz -- i.e. how wrong the margin arithmetic is if the frequency label is wrong.

B  IS THE 27-32 FEATURE THE SAME OBJECT AS THE FOLDED SHELF?   The near-Nyquist shelf (33-49.9 Hz) is
   the folded image of true 50-67 Hz.  If the 27-32 EXCESS OVER THAT SHELF is engagement-gated while
   the shelf itself is not, the two are different objects and the excess is a loop-side phenomenon
   observed in its own right.  If both gate together, the excess is probably more of the same fold.
   The shelf is used as the CONTROL BAND, which is the adjacent-control-band discipline the kit's own
   acoustic work had to learn twice.

Run: python rlog-tools/studies/grind/task5_consequence.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
sys.path.insert(0, HERE)
from task5_1ab_discriminator import Hchain, load, runs, bandpow, FS18   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TAGS = ("r34", "r35", "r36", "r37", "r38")
LINES = []


def pr(s=""):
    print(s)
    LINES.append(s)


# ================================================================== A: the cost of a wrong frequency
def sec_a():
    pr("=" * 100)
    pr("A  WHAT A WRONG FREQUENCY LABEL COSTS -- the exact 1 kHz chain, Kp = 248, Kd = 128 (D = dE*16)")
    pr("=" * 100)
    pr("   %6s %10s %10s %10s %10s" % ("f Hz", "|H|", "arg(H) deg", "D/P ratio", "grp delay ms"))
    for f in (7.0, 20.0, 30.0, 50.0, 70.0, 130.0):
        h = Hchain(f)
        eps = 0.01
        ph = np.unwrap(np.angle([Hchain(f - eps), Hchain(f), Hchain(f + eps)]))
        gd = -(ph[2] - ph[0]) / (2 * 2 * np.pi * eps) * 1000.0
        z = np.exp(2j * np.pi * f / 1000.0)
        dp = abs(16.0 * (1 - 1 / z)) / (248.0 / 256.0)
        pr("   %6.1f %10.5f %10.1f %10.2f %10.3f"
           % (f, abs(h), np.degrees(np.angle(h)), dp, gd))
    h30, h70 = Hchain(30.0), Hchain(70.0)
    dphi = np.degrees(np.angle(h70) - np.angle(h30))
    pr()
    pr("   30 Hz vs 70 Hz:  |H| ratio %.3f (%.2f dB)   PHASE DIFFERENCE %.1f deg   D/P 3.1 vs 7.2"
       % (abs(h70) / abs(h30), 20 * np.log10(abs(h70) / abs(h30)), dphi))
    pr("   => if a mode read as '30 Hz' is really at 70 Hz, the CONTROLLER's own contribution to the")
    pr("      loop phase at that mode is wrong by %.0f deg, and the plant's is wrong by more." % abs(dphi))
    pr("      A phase-margin argument built on the 27-32 Hz label does NOT survive the ambiguity.")
    pr("   => but note what aliasing does NOT do: with no anti-alias filter there is no attenuation,")
    pr("      so folded power arrives at FULL amplitude somewhere in 0-50 Hz.  Energy is conserved;")
    pr("      only the frequency label is destroyed.")


# ============================================== B: is the 27-32 excess a different object to the shelf
def sec_b():
    pr()
    pr("=" * 100)
    pr("B  27-32 Hz EXCESS OVER THE FOLDED SHELF, engaged vs manual  (shelf 33-38 Hz = the CONTROL BAND)")
    pr("=" * 100)
    pr("   the shelf at 33-38 Hz is the folded image of true 62-67 Hz; the near-Nyquist shelf 45-49.9 Hz")
    pr("   is the folded image of true 50.1-55 Hz.  Both are reported so the shelf's own gating is visible.")
    pr()
    pr("   %-5s %-8s %7s %9s %9s %9s %9s" %
       ("route", "state", "n", "P(27-32)", "P(33-38)", "excess", "shelf45/33"))
    for tag in TAGS:
        D = load(tag)
        req = np.interp(D["t18"], D["te4"], D["req"].astype(float)) > 0.5
        eng = (np.asarray(D["sca"], float) > 0.5) & req
        rate = np.asarray(D["rate"], float)
        res = {}
        for nm, m in (("engaged", eng), ("manual", ~eng)):
            segs = runs(m, 2048)
            if not segs:
                continue
            w = np.array([b - a for a, b in segs], float)
            g = lambda lo, hi: np.average([bandpow(rate[a:b], FS18, 2048, lo, hi)      # noqa: E731
                                           for a, b in segs], weights=w)
            p2732, p3338, p4549 = g(27, 32), g(33, 38), g(45, 49.9)
            res[nm] = (w.sum(), p2732, p3338, p2732 / p3338, p4549 / p3338)
            pr("   %-5s %-8s %7d %9.3f %9.3f %9.3f %9.3f"
               % (tag, nm, int(w.sum()), p2732, p3338, p2732 / p3338, p4549 / p3338))
        if "engaged" in res and "manual" in res:
            pr("   %-5s %-8s %7s %9.2fx %8.2fx %8.2fx %8.2fx   <- engaged/manual"
               % (tag, "RATIO", "",
                  res["engaged"][1] / res["manual"][1], res["engaged"][2] / res["manual"][2],
                  res["engaged"][3] / res["manual"][3], res["engaged"][4] / res["manual"][4]))
    pr()
    pr("   READING: if 'excess' gates with engagement while 'shelf45/33' does not, the 27-32 feature is")
    pr("   a loop-side object and the shelf is a background the loop does not drive.")


def main():
    sec_a()
    sec_b()
    out = os.path.join(HERE, "_scratch", "task5_consequence.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(LINES) + "\n")
    print("\nwrote %s" % out)


if __name__ == "__main__":
    main()
