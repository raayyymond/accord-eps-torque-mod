# -*- coding: utf-8 -*-
"""v293r5_design_lowspeed.py -- the rev-5 shortlist at LOW SPEED and on SMALL STEPS against stiction (orchestrator's own,
2026-09-15).  Complements v293r5_design.py (12/19/26 m/s): the operator's "jerky on hard turns" and "the command has to
overshoot to get over friction" live at 5-12 m/s and at small corrections.

  T7 small step: planner step of 0.15 m/s^2 at t = 1 s (a 1-3 deg correction), Coulomb F x1.5 (0.018):
     time to 50 % and 90 % of the step, overshoot (fraction of the step), peak wheel rate, the torque the command added
     between the step and the first wheel motion ("wind-up"), and how far past the target the wheel went (deg).
  T1 disturbance step 0.03 torque (as before), T3 kick, T5 ramp stiction -- at 6 and 8 m/s.
Worlds: ident b (unidentified below 8 m/s -- the ident's 1-8 band fit b 0.0018 is used) and the "mode" world b 0.0006.
ANALYSIS ONLY.
"""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v293r2_simlib as S
import v293r3_read as R3
import v293r5_design as D

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DT = S.DT
OUT = []
def pr(s=""):
    print(s, flush=True); OUT.append(s)

SHORT = [
    D.mk("R4-flown"),
    D.mk("R4+DOB.8 Ki.3flat", ki=0.3, ki_hi=0.0, dob=0.8),
    D.mk("Kp1.2 notch DOB.8 Ki.3", kp=1.2, ki=0.3, ki_hi=0.0, dob=0.8),
    D.mk("Kp1.5 notch DOB.8 Ki.3", kp=1.5, ki=0.3, ki_hi=0.0, dob=0.8),
    D.mk("Kp2 NOnotch Kv1e-3 DOB1 Ki.3", kp=2.0, ki=0.3, ki_hi=0.0, kv=0.001, notch_q=0.0, dob=1.0),
    D.mk("Kp1.5 notch DOB.8 Ki.3 max.15", kp=1.5, ki=0.3, ki_hi=0.0, dob=0.8, dob_max=0.15),
    D.mk("Kp1.5 notch DOB.5 Ki.3", kp=1.5, ki=0.3, ki_hi=0.0, dob=0.5),
]


def t7(cfgf, v, world, need, step=0.15, Fscale=1.5):
    out = D.run(cfgf, v, lambda t: (step if t >= 1.0 else 0.0) / v ** 2, T=7.0, world=world, need=need, Fscale=Fscale)
    t, u, phi, meas, rate = out[:, 0], out[:, 1], out[:, 2], out[:, 3], out[:, 5]
    k0 = int(1.0 / DT)
    A = S.lat_accel_per_deg(v, S.steer_ratio(10.0, 16.88))
    target_deg = step / A
    def t_to(frac):
        idx = np.where(meas[k0:] >= frac * step)[0]
        return idx[0] * DT if len(idx) else np.nan
    ov = (np.max(meas[k0:]) - step) / step
    pk_rate = float(np.max(np.abs(rate[k0:])))
    moving = np.where(np.abs(rate[k0:]) > 0.5)[0]
    k_move = k0 + moving[0] if len(moving) else len(t) - 1
    windup = u[k_move] - u[k0 - 1]
    past = (np.max(phi[k0:]) - target_deg)
    e_tail = step - meas[int(4.0 / DT):int(6.0 / DT)]
    return [t_to(0.5), t_to(0.9), ov, pk_rate, windup, past, float(np.sqrt(np.mean(e_tail ** 2)))]


def main():
    pr("v293r5_design_lowspeed -- shortlist at 6 / 8 / 12 m/s, and the SMALL-STEP stiction test T7 at 8 / 12 / 19 / 26 m/s (F x1.5)")
    for wname in ("ident (b F1, J 1e-4)", "mode (b .0006, J 1e-4)"):
        world = D.WORLDS[wname]
        for need in (1.0, 1.5):
            pr("\n" + "=" * 140)
            pr("WORLD %s | NEED x%.1f | low speed" % (wname, need))
            pr("  %-30s %3s | %-30s | %-22s | %-7s | %-34s" % ("cfg", "v", "T1 dist |e| .5 1 2 s, rms", "T2 rise ov rms", "T3 pkpk", "T5 stiction: rms e, pk rate, dwells, max|e|"))
            for cf in SHORT:
                for v in (6.0, 8.0, 12.0):
                    a1 = D.t1(cf, v, world, need); a2 = D.t2(cf, v, world, need); a3 = D.t3(cf, v, world, need); a5 = D.t5(cf, v, world, need)
                    pr("  %-30s %3.0f | %6.3f %6.3f %6.3f %6.3f    | %5.2f %+6.2f %6.3f    | %6.2f  | %6.3f %7.1f %3d %6.3f"
                       % (cf.name, v, *a1, *a2, a3[0], *a5))
            pr("\n  T7 small step 0.15 m/s^2, F x1.5:  %-30s %3s | %6s %6s %6s | %7s | %7s %7s | %6s" % ("cfg", "v", "t50", "t90", "ov", "pk r/s", "windup", "past deg", "tail e"))
            for cf in SHORT:
                for v in (8.0, 12.0, 19.0, 26.0):
                    a7 = t7(cf, v, world, need)
                    pr("  %-30s %3.0f | %6.2f %6.2f %+6.2f | %7.1f | %+7.4f %+7.2f | %6.3f" % (cf.name, v, *a7))
    out = os.path.join(HERE, "V293-REV5-DESIGN-LOWSPEED-2026-09-15.txt")
    open(out, "w", encoding="utf-8").write("\n".join(OUT)); pr("\nwritten " + out)


if __name__ == "__main__":
    main()
