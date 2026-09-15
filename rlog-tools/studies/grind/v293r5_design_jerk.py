# -*- coding: utf-8 -*-
"""v293r5_design_jerk.py -- rev 5 must not buy tracking with MORE 2 Hz mode energy (the operator's "jerky on hard turns").
(orchestrator's own, 2026-09-15.)  The DOBB sweep showed the observer with a model b ABOVE the plant's installs the model's
damping below its corner (T2 overshoot 0.4-0.6 -> 0.1-0.3, hold error -50..-90 %) but de-damps the 2-2.7 Hz mode
(hard-turn 1.6-3 Hz rate rms +40..+150 % vs rev 4): damping from the observer = dB * Re Q(jw), positive below f_Q and
NEGATIVE above it.  This sweep sizes the model b as a DESIGN target (0.002 / 0.003 flat), lowers Kp back toward 0.85,
leans on the rate loop (Kv 1e-3, RC 0.01) for 1-2.8 Hz, and tries the notch at the CLOSED-loop mode.  ANALYSIS ONLY.
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v293r2_simlib as S
import v293r3_read as R3
import v293r5_design as D
import v293r5_design_lowspeed as DL
import v293r5_design_pred as P

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []
def pr(s=""):
    print(s, flush=True); OUT.append(s)


def mk(name, kp=1.2, ki=0.3, ki_hi=0.0, ref=0.12, kv=0.0006, rc=0.03, notch_q=1.0, notch_scale=1.0, hyst=0.015, dob=0.8,
       dob_b="ident", dob_max=0.3):
    def make(v):
        return S.Cfg(name, 14.0, kp, D.ki_sched(v, ki, ki_hi), 0.0, rate_gain=0.5, hold_fn=D.hold_ff_scaled(1.0), fric_hyst=hyst,
                     fric_band=3.0, il_kd=(lambda vv, k=kv: k) if kv else None, il_tau=rc,
                     kv_taper=lambda vv: min(1.0, 12.0 / max(vv, 0.1)), notch_q=notch_q,
                     notch_fn=lambda vv, sc=notch_scale: sc * float(R3.mode_hz(vv)), ref_tau=ref, lat_delay=D.LAT_DELAY,
                     dob_fc=dob, dob_td=0.06, dob_b=(D.b_ident if dob_b == "ident" else (lambda vv, bb=dob_b: bb)), dob_J=1.0e-4,
                     dob_use_J=True, dob_max=dob_max)
    make.name = name
    return make


CANDS = [
    D.mk("R4-flown"),
    mk("R5 ident Kp1.2"),
    mk("R5 ident Kp.85", kp=0.85),
    mk("R5 ident Kp.85 Kv1e-3 rc.01", kp=0.85, kv=0.001, rc=0.01),
    mk("R5 ident Kp1.0 Kv1e-3 rc.01 DOB.6", kp=1.0, kv=0.001, rc=0.01, dob=0.6),
    mk("R5 b.002 Kp1.2", dob_b=0.002),
    mk("R5 b.002 Kp.85 Kv1e-3 rc.01", kp=0.85, kv=0.001, rc=0.01, dob_b=0.002),
    mk("R5 b.002 Kp1.0 Kv1e-3 rc.01 DOB.6", kp=1.0, kv=0.001, rc=0.01, dob=0.6, dob_b=0.002),
    mk("R5 b.003 Kp1.0 Kv1e-3 rc.01 DOB.6", kp=1.0, kv=0.001, rc=0.01, dob=0.6, dob_b=0.003),
    mk("R5 b.003 Kp.85 Kv1e-3 rc.01 DOB.6", kp=0.85, kv=0.001, rc=0.01, dob=0.6, dob_b=0.003),
    mk("R5 ident Kp1.2 notchx1.35", notch_scale=1.35),
    mk("R5 ident Kp1.2 notchQ.7", notch_q=0.7),
    mk("R5 b.002 Kp1.0 Kv1e-3 rc.01 DOB.6 nx1.3", kp=1.0, kv=0.001, rc=0.01, dob=0.6, dob_b=0.002, notch_scale=1.3),
]

WORLDS = {k: P.WORLDS[k] for k in ("mode (b .0006, J 1e-4)", "ident (b F1, J 1e-4)", "ident, delays x1.5", "mode, delays x1.5")}

def main():
    pr("v293r5_design_jerk -- tracking vs 2 Hz mode energy.  Ki .3 flat, hyst .015, ref .12 throughout.")
    for wname, world in WORLDS.items():
        for need in ((1.0, 1.5) if "ident (b" in wname else (1.0,)):
            pr("\n" + "=" * 150)
            pr("WORLD %s | hold NEED x%.1f" % (wname, need))
            pr("  %-38s %3s | %-18s | %-7s | %-30s | %-40s" % ("cfg", "v", "T2 rise ov rms", "T3 pkpk", "T7 t50 t90 ov pk-rate past", "T8 mode-rms bursts max|e|hold ov rms-e damp"))
            for cf in CANDS:
                for v in (6.0, 8.0, 12.0, 19.0, 26.0):
                    a2 = D.t2(cf, v, world, need); a3 = D.t3(cf, v, world, need); a7 = DL.t7(cf, v, world, need); a8 = P.t8(cf, v, world, need)
                    pr("  %-38s %3.0f | %4.2f %+5.2f %5.3f  | %6.2f  | %4.2f %4.2f %+5.2f %5.1f %+5.2f     | %5.2f %2d %5.3f %+5.3f %5.3f %4.2f"
                       % (cf.name, v, *a2, a3[0], a7[0], a7[1], a7[2], a7[3], a7[5], *a8))
    out = os.path.join(HERE, "V293-REV5-DESIGN-JERK-2026-09-15.txt")
    open(out, "w", encoding="utf-8").write("\n".join(OUT)); pr("\nwritten " + out)

if __name__ == "__main__":
    main()
