# -*- coding: utf-8 -*-
"""v293r5_design_ship.py -- the exact rev-5 shipping candidates, every world, every test (orchestrator's own, 2026-09-15).
SHIP  = Kp 1.0, Ki 0.3 flat, Kv 1e-3 (RC 0.03 as in the fork), notch Q1 at sqrt(k/J), hyst 0.015, ref 0.12, DOB 0.6 Hz with the
        fork's own 1/G(v) as the model damping.
ALT-A = SHIP with the rate-measurement RC 0.01 (would need a fork constant change).
ALT-B = SHIP with Kp 0.85 (config-only relative to rev 4 apart from the observer).
ALT-C = SHIP with Kv 6e-4 (rate loop unchanged from rev 4).
ANALYSIS ONLY.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v293r5_design as D
import v293r5_design_lowspeed as DL
import v293r5_design_pred as P
import v293r5_design_jerk as J

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []
def pr(s=""):
    print(s, flush=True); OUT.append(s)

CANDS = [
    D.mk("R4-flown"),
    J.mk("SHIP Kp1.0 Kv1e-3 rc.03 DOB.6", kp=1.0, kv=0.001, rc=0.03, dob=0.6),
    J.mk("ALT-A rc.01", kp=1.0, kv=0.001, rc=0.01, dob=0.6),
    J.mk("ALT-B Kp.85", kp=0.85, kv=0.001, rc=0.03, dob=0.6),
    J.mk("ALT-C Kv6e-4", kp=1.0, kv=0.0006, rc=0.03, dob=0.6),
    J.mk("SHIP DOB.8", kp=1.0, kv=0.001, rc=0.03, dob=0.8),
]

def main():
    pr("v293r5_design_ship -- shipping candidates x every world x every test")
    for wname, world in P.WORLDS.items():
        for need in (1.0, 1.5):
            pr("\n" + "=" * 150)
            pr("WORLD %s | hold NEED x%.1f" % (wname, need))
            pr("  %-30s %3s | %-26s | %-18s | %-7s | %-30s | %-30s | %-40s" % ("cfg", "v", "T1 dist |e| .5 1 2 s, rms", "T2 rise ov rms", "T3 pkpk",
                                                                           "T5 rms e, pk rate, dwells, max|e|", "T7 t50 t90 ov pk-rate past", "T8 mode-rms bursts max|e|hold ov rms-e damp"))
            for cf in CANDS:
                for v in (6.0, 8.0, 12.0, 19.0, 26.0):
                    a1 = D.t1(cf, v, world, need); a2 = D.t2(cf, v, world, need); a3 = D.t3(cf, v, world, need)
                    a5 = D.t5(cf, v, world, need); a7 = DL.t7(cf, v, world, need); a8 = P.t8(cf, v, world, need)
                    pr("  %-30s %3.0f | %5.3f %5.3f %5.3f %5.3f    | %4.2f %+5.2f %5.3f  | %6.2f  | %5.3f %6.1f %2d %5.3f          | %4.2f %4.2f %+5.2f %5.1f %+5.2f     | %5.2f %2d %5.3f %+5.3f %5.3f %4.2f"
                       % (cf.name, v, *a1, *a2, a3[0], *a5, a7[0], a7[1], a7[2], a7[3], a7[5], *a8))
    out = os.path.join(HERE, "V293-REV5-DESIGN-SHIP-2026-09-15.txt")
    open(out, "w", encoding="utf-8").write("\n".join(OUT)); pr("\nwritten " + out)

if __name__ == "__main__":
    main()
