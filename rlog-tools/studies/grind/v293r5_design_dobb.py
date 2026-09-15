# -*- coding: utf-8 -*-
"""v293r5_design_dobb.py -- which viscous coefficient should the DISTURBANCE OBSERVER's model carry?  (orchestrator's own,
2026-09-15.)  The observer's residual is (b_model - b_true) * rate + ...; above its corner Q(f) lags ~136 deg at 2 Hz, so a
model b ABOVE the truth turns that term into NEGATIVE damping of the 2-2.7 Hz mode (the predictor sweep showed the ident b
0.0049 at 26 m/s de-damping the mode world), while a model b BELOW the truth adds damping there and is merely cancelled
back toward the model inside the Q bandwidth.  The real drives (r72, r75, S7 free fit) read b 0.0005-0.0009 below 15 m/s
and ~0.004 only above 22 m/s.  So: sweep the model b in every world.  ANALYSIS ONLY.
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v293r2_simlib as S
import v293r5_design as D
import v293r5_design_lowspeed as DL
import v293r5_design_pred as P

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []
def pr(s=""):
    print(s, flush=True); OUT.append(s)

CANDS = [
    D.mk("R4-flown"),
    P.mk("R5 dobb ident"),
    P.mk("R5 dobb .0006", dob_b=0.0006),
    P.mk("R5 dobb .0010", dob_b=0.0010),
    P.mk("R5 dobb .0006 Kv1e-3 rc.01", dob_b=0.0006, kv=0.001, rc=0.01),
    P.mk("R5 dobb .0006 Kv1e-3 rc.03", dob_b=0.0006, kv=0.001, rc=0.03),
    P.mk("R5 dobb .0006 Kp1.0", dob_b=0.0006, kp=1.0),
    P.mk("R5 dobb .0006 DOB.6", dob_b=0.0006, dob=0.6),
    P.mk("R5 dobb .0006 DOB1.0", dob_b=0.0006, dob=1.0),
]

def main():
    pr("v293r5_design_dobb -- the observer's model b, every world.  R5 = Kp 1.2, notch Q1, Kv 6e-4 rc .03, DOB .8, Ki .3 flat unless named.")
    for wname, world in P.WORLDS.items():
        for need in (1.0, 1.5):
            pr("\n" + "=" * 150)
            pr("WORLD %s | hold NEED x%.1f" % (wname, need))
            pr("  %-28s %3s | %-26s | %-18s | %-7s | %-30s | %-30s | %-40s" % ("cfg", "v", "T1 dist |e| .5 1 2 s, rms", "T2 rise ov rms", "T3 pkpk",
                                                                           "T5 rms e, pk rate, dwells, max|e|", "T7 t50 t90 ov pk-rate past", "T8 mode-rms bursts max|e|hold ov rms-e damp"))
            for cf in CANDS:
                for v in (6.0, 8.0, 12.0, 19.0, 26.0):
                    a1 = D.t1(cf, v, world, need); a2 = D.t2(cf, v, world, need); a3 = D.t3(cf, v, world, need)
                    a5 = D.t5(cf, v, world, need); a7 = DL.t7(cf, v, world, need); a8 = P.t8(cf, v, world, need)
                    pr("  %-28s %3.0f | %5.3f %5.3f %5.3f %5.3f    | %4.2f %+5.2f %5.3f  | %6.2f  | %5.3f %6.1f %2d %5.3f          | %4.2f %4.2f %+5.2f %5.1f %+5.2f     | %5.2f %2d %5.3f %+5.3f %5.3f %4.2f"
                       % (cf.name, v, *a1, *a2, a3[0], *a5, a7[0], a7[1], a7[2], a7[3], a7[5], *a8))
    out = os.path.join(HERE, "V293-REV5-DESIGN-DOBB-2026-09-15.txt")
    open(out, "w", encoding="utf-8").write("\n".join(OUT)); pr("\nwritten " + out)

if __name__ == "__main__":
    main()
