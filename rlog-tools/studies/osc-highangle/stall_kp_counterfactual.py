# -*- coding: utf-8 -*-
"""stall_kp_counterfactual.py -- Q3: what a Kp CUT (248 -> 200/176/148/128/100), Ki still 0, would
have done to the P-only DEADBAND / STALL census on the flown routes.

USES THE EXISTING METRIC, UNCHANGED -- it literally calls `v281r3_read_r35.moving_runs`, the same
function that produced "r35 = 7 stall runs / 14.8 s at idx 54-79".  The definition, for the record:
segment ENGAGED & |angle| >= 30 & idx >= 40 into runs >= 1.0 s; a run is STALLED if its MEDIAN
rate/ref < 0.5 AND its median |driver torque| < 1000 (hands-light, so it is not the driver holding).
Nothing new is invented and no threshold is moved.

THE COUNTERFACTUAL MAP.  With Ki = 0 the steady-state chain from rate error to delivered torque is a
pure static gain proportional to Kp (P = E*Kp>>8 is the only DC term; the 254/256 taper, the output
lag, the 5346 forward gain and the feedback EMA are all Kp-independent and cancel).  A run whose
MEASURED median rate/ref = x had closed-loop DC return ratio L = x/(1-x) at Kp 248; at Kp' the same
run, same road load, same reference, has L' = L * Kp'/248 and x' = L'/(1+L').  The map is monotone,
so the run's median maps to the run's median.  The stall gate x' < 0.5 becomes a gate on the
MEASURED median:   x < 0.5 / (0.5 + 0.5*Kp'/248).

  [EVIDENCE] the static-gain structure and its Kp-linearity: byte-exact, FUN_00028ea6, Ki = 0.
  [EVIDENCE] the type-0 plant that makes x/(1-x) the DC return ratio: zn285 sec 1.2/1.3 -- four
             (|T|, rate) pairs held 1-3 s, and the DC chain closing to a few percent with no fit.
  [BELIEF]   that road load and the openpilot demand index would be UNCHANGED at the lower Kp.  They
             would not be exactly: a slower wheel changes the path error openpilot sees, so it winds
             idx UP, which raises `ref` and makes the stall gate HARDER.  ==> this is a LOWER bound
             on the worsening.

Run: python rlog-tools/studies/osc-highangle/stall_kp_counterfactual.py
Subagent znback, 2026-09-04.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strongturn_r32_r33 as ST  # noqa: E402
import strongturn_r35 as S35  # noqa: E402
import stutter_v283 as SV  # noqa: E402
import v281r3_read_r35 as R35  # noqa: E402

V = ST.V
FS = ST.FS
V280R2 = ST.V280R2
KP_FLAT = S35.KP_FLAT
ROUTES = ("r35", "r36", "r37", "r38")
KI_ONCAR = {"r35": 0, "r36": 50, "r37": 50, "r38": 50}
KPS = (248, 200, 176, 148, 128, 100)
gate = lambda kp: 0.5 / (0.5 + 0.5 * kp / 248.0)     # noqa: E731  the equivalent MEASURED-x gate


def main():
    out = []

    def pr(s=""):
        print(s, flush=True)
        out.append(s)

    pr("=" * 150)
    pr("Q3 -- THE Kp CUT vs THE P-ONLY DEADBAND.  Counterfactual stall census on the FLOWN routes.")
    pr("      Metric = v281r3_read_r35.moving_runs(idx_lo=40), CALLED DIRECTLY, thresholds untouched.")
    pr("=" * 150)
    pr("  r35 = V281 rev 3 (Kp flat 248, Ki 0) -- the P-ONLY build that CREATED the deadband.")
    pr("  r36/r37/r38 = V283 (Kp flat 248, Ki 50) -- the cure.  Ki-50 rows are for scale; a Kp-cut")
    pr("  candidate is a Ki-0 image, so r35 is the LIKE-FOR-LIKE baseline.")
    pr("")
    pr("  map: measured median x = rate/ref  ->  x' = k*x/(1 - x + k*x), k = Kp'/248")
    pr("  equivalent measured-x stall gate:  " + " | ".join("Kp %3d: x < %.3f" % (kp, gate(kp)) for kp in KPS))
    pr("")

    tot = {kp: [0, 0.0] for kp in KPS}
    per = {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        r = V.Route(tag)
        R = SV.sim_ki(r, *V280R2, kpY=KP_FLAT["flat 248"], ki=KI_ONCAR[tag])
        runs = R35.moving_runs(r, R, 40)                 # <-- the published definition, verbatim
        light = [x for x in runs if x["tq50"] < 1000]
        rrs = np.array([x["rr"] for x in light], float)
        durs = np.array([x["dur"] for x in light], float)
        per[tag] = (runs, light)
        pr("  --- %s (Ki on car %2d): %d runs >= 1 s in the context mask, %d of them hands-light (%.1f s); "
           "median rate/ref over those: p10 %.2f p25 %.2f p50 %.2f p75 %.2f ---"
           % (tag, KI_ONCAR[tag], len(runs), len(light), durs.sum(),
              *[np.percentile(rrs, q) for q in (10, 25, 50, 75)]))
        pr("      %6s %10s %12s %11s %11s %12s %12s"
           % ("Kp", "gate x<", "stall runs", "stall secs", "longest", "idx p50", "DC track %"))
        for kp in KPS:
            g = gate(kp)
            st = [x for x in light if x["rr"] < g]
            secs = sum(x["dur"] for x in st)
            longest = max([x["dur"] for x in st] or [0.0])
            idxp = float(np.median([x["idx"] for x in st])) if st else float("nan")
            Ldc = 1.1512 * kp / 248.0
            pr("      %6d %10.3f %12d %10.1f s %10.1f s %12.0f %11.1f"
               % (kp, g, len(st), secs, longest, idxp, 100 * Ldc / (1 + Ldc)))
            tot[kp][0] += len(st)
            tot[kp][1] += secs
        pr("")

    pr("=" * 150)
    pr("  r35 ALONE -- the LIKE-FOR-LIKE Ki-0 baseline (the build that produced the symptom):")
    runs, light = per["r35"]
    for kp in KPS:
        st = [x for x in light if x["rr"] < gate(kp)]
        pr("      Kp %3d : %2d stall runs, %5.1f s   (published r35/V281r3 baseline at Kp 248: 7 runs / 14.8 s)"
           % (kp, len(st), sum(x["dur"] for x in st)))
    pr("")
    pr("  POOLED r35+r36+r37+r38 (mixed Ki, for scale):  " + " | ".join(
        "Kp %3d: %d runs / %.1f s" % (kp, tot[kp][0], tot[kp][1]) for kp in KPS))
    pr("=" * 150)
    pr("")
    pr("  THE V283 COMPARISON POINT: Ki 50 took r35's 7 runs -> 1 run pooled over r36/r37/r38 at Kp 248.")
    pr("  The Kp column above is the size of the move in the OPPOSITE direction, on the same metric.")

    with open(os.path.join(HERE, "STALL-KP-COUNTERFACTUAL.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("wrote STALL-KP-COUNTERFACTUAL.txt")


if __name__ == "__main__":
    main()
