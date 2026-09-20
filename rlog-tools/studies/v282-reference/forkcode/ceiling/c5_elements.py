# -*- coding: utf-8 -*-
"""c5 -- THE CODE ELEMENTS, ONE AT A TIME AND TOGETHER.

  A. SteerKP past 3.0            (one constant: STEER_KP_MAX_MULT, starpilot_variables.py:459)
  B. SPEED-SCHEDULED notch Q     (call site, latcontrol_torque.py:347-348)
  C. I-PATH lsf DECOUPLING       (latcontrol_torque.py:342 + the pid call)
  D. THE k_d SLOT (a lead/damping term) -- the brief asks me to TEST the reasoning, not assume it.
     The fork already wires error_rate = -measurement_rate (torque.py, the pid.update call), and
     measurement_rate is filtered at MAX_LAT_JERK_UP - 0.5 = 2.0 Hz.  So "adding a D term" is
     literally k_d != 0, and it is a MEASUREMENT-RATE feedback, not an error derivative.
  E. A ROLL-OFF on the error (not in the fork; the shape the cost function actually asks for).

B and C are metric-INERT by construction: c1/V5 shows every metric window is >= 15.75 m/s, so a
schedule that only changes behaviour below 15 m/s cannot move J.  Their value is the LOW-SPEED
price they refund, so they are priced on the analytic low-speed transfer, not on J.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
FRONT = STUDY / "shapedgain" / "frontier"
sys.path.insert(0, str(FRONT))
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP                                        # noqa: E402
from f5_frontier import FLOWN                              # noqa: E402
from c3_ceiling import Ceiling, C_gen, fmt, HDR, lp1, KP_REF   # noqa: E402

np.seterr(divide="ignore", invalid="ignore")
OUTD = HERE / "out"
KD_LP = 2.0            # MAX_LAT_JERK_UP - 0.5, torque.py:93
VGRID = [2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 18.0, 23.0, 28.0]


def notch_at(f, v, q):
    return LP.notch_response(np.asarray([f]), float(LP.mode_hz(v)), q)[0]


if __name__ == "__main__":
    E = Ceiling()
    print("=" * 132)
    print("B. THE LOW-SPEED PRICE OF A WIDE NOTCH -- what a speed schedule refunds.")
    print("   The notch centre is get_honda_accord_mode_hz(v) = sqrt(interp(v,HOLD_V_BP,HOLD_K_V)/8e-5)/2pi;")
    print("   it is ALREADY a function of speed.  Only Q is a scalar today.")
    print(f"{'v m/s':>7s} {'f0 Hz':>7s} | " + " | ".join(f"Q={q:<4.2f} |N|@0.3  deg" for q in (1.00, 0.60, 0.35, 0.15)))
    for v in VGRID:
        f0 = float(LP.mode_hz(v))
        cells = []
        for q in (1.00, 0.60, 0.35, 0.15):
            n = notch_at(0.30, v, q)
            cells.append(f"        {abs(n):.3f} {np.degrees(np.angle(n)):+6.1f}")
        print(f"{v:7.1f} {f0:7.3f} | " + " | ".join(cells))
    print()
    print("   the same at the metric band edges, and the EXTRA lag a wide notch costs vs today's Q=1.0")
    print(f"{'v m/s':>7s} {'f0':>6s} | {'lag@0.15 Q1->Q0.35':>19s} {'0.30':>7s} {'0.60':>7s} | "
          f"{'lag@0.15 Q1->Q0.15':>19s} {'0.30':>7s} {'0.60':>7s}")
    for v in VGRID:
        row = []
        for q in (0.35, 0.15):
            d = [np.degrees(np.angle(notch_at(ff, v, q))) - np.degrees(np.angle(notch_at(ff, v, 1.0)))
                 for ff in (0.15, 0.30, 0.60)]
            row.append(f"{d[0]:19.1f} {d[1]:7.1f} {d[2]:7.1f}")
        print(f"{v:7.1f} {float(LP.mode_hz(v)):6.3f} | " + " | ".join(row))

    print()
    print("=" * 132)
    print("C. THE I-PATH COUPLING, SIZED.  error_with_lsf = error*(1+lsf/kp) multiplies BOTH paths,")
    print("   but kp cancels only in P.  Column 'I x' is the integral gain relative to the flown")
    print("   SteerKP 1.0 build at the same speed; 'I x (fix)' is the same with the I path given")
    print(f"   its own reference KP_REF = {KP_REF} (the platform Kp).  P is unaffected either way.")
    print(f"{'v m/s':>7s} {'lsf':>8s} | " + " | ".join(f"KP {k:<4.1f}  I x   I x(fix)" for k in (3.0, 6.0, 8.0)))
    for v in VGRID:
        lsf = float(LP.low_speed_factor(v))
        base = 1.0 + lsf / 1.0
        cells = []
        for kp in (3.0, 6.0, 8.0):
            cells.append(f"      {(1+lsf/kp)/base:6.3f}   {(1+lsf/KP_REF)/base:7.3f}")
        print(f"{v:7.1f} {lsf:8.3f} | " + " | ".join(cells))
    print()
    print("   and what the fix is worth ON THE METRIC (>=15 m/s), where lsf is 0.05-0.38:")
    print(HDR)
    for kp in (1.0, 3.0, 6.0, 8.0):
        for dec in (False, True):
            r = E.score(kp=kp, laf=14.0, q=0.35 if kp > 3 else 0.60, decouple_i=dec)
            print(fmt(f"KP {kp:.1f}  I-decoupled={str(dec):5s}", r))
    print()
    print("   vs the AccordTorqueKi workaround the adjudication already has (raise ki instead):")
    for kp, ki in ((3.0, 0.30), (3.0, 0.60), (3.0, 0.90), (8.0, 0.30), (8.0, 0.60)):
        r = E.score(kp=kp, laf=14.0, q=0.35 if kp > 3 else 0.60, ki=ki)
        print(fmt(f"KP {kp:.1f}  AccordTorqueKi {ki:.2f}", r))

    print()
    print("=" * 132)
    print("D. THE k_d SLOT.  In the fork, error_rate = -measurement_rate (filtered at 2.0 Hz), so a")
    print("   non-zero k_d is MEASUREMENT-RATE FEEDBACK -- plant damping, not setpoint lead.")
    print("   Its transfer adds k_d * (1-z)/dt * LP(2 Hz) to the P+I numerator: |C| RISES with f.")
    print(HDR + "   note")
    for kd in (0.0, 0.05, 0.1, 0.2, 0.4, 0.8):
        r = E.score(kp=3.0, laf=14.0, q=0.60, kd=kd, kd_lp_hz=KD_LP)
        print(fmt(f"KP 3.0 Q0.60  k_d {kd:.2f}", r))
    for kd in (0.0, 0.1, 0.4):
        r = E.score(kp=8.0, laf=14.0, q=0.15, kd=kd, kd_lp_hz=KD_LP)
        print(fmt(f"KP 8.0 Q0.15  k_d {kd:.2f}", r))
    print("   |C_kd/C_0| across frequency at k_d 0.4, KP 3.0 (where the term puts its gain):")
    f = E.f
    j = [int(np.argmin(np.abs(f - q))) for q in (0.20, 0.30, 0.59, 0.98, 1.95, 2.54, 3.03)]
    v1 = np.array([23.0])
    C0 = C_gen(f, v1, 3.0, 14.0, 0.3, 0.0, 0.60)[0]
    Cd = C_gen(f, v1, 3.0, 14.0, 0.3, 0.0, 0.60, kd=0.4, kd_lp_hz=KD_LP)[0]
    print("      " + " ".join(f"{f[i]:.2f}Hz {abs(Cd[i]/C0[i]):5.2f}x" for i in j))

    print()
    print("=" * 132)
    print("E. A ROLL-OFF ON THE ERROR (first/second order low-pass in the same slot as the notch).")
    print("   This is the shape the cost function asks for: gain below 0.6 Hz, none at 1.8-3.5 Hz.")
    print(HDR + "   config")
    rows = []
    for kp, hz, o, q in itertools.product([3.0, 6.0, 8.0, 12.0, 16.0], [0.6, 0.8, 1.0, 1.5, 2.0], [1, 2],
                                          [0.0, 0.35, 0.6, 1.0]):
        r = E.score(kp=kp, laf=14.0, q=q, lp_hz=hz, lp_ord=o)
        r.update(kp=kp, hz=hz, o=o, q=q)
        rows.append(r)
    for ceil in (32.4, 36.0, 40.0, 50.0):
        ok = [r for r in rows if r["shake_common"] <= ceil]
        if not ok:
            continue
        b = min(ok, key=lambda r: r["metric"])
        print(fmt(f"LP frontier shake<= {ceil:5.1f}", b,
                  f"KP {b['kp']:.0f} LP {b['hz']:.1f}Hz x{b['o']} Q {b['q']:.2f}"))
    json.dump([{k: v for k, v in r.items() if k != "bands"} for r in rows], open(OUTD / "c5_lp.json", "w"))

    print()
    print("=" * 132)
    print("F. THE HEADLINE LADDER -- the minimal diff at each step, all on the calibrated shake axis.")
    print(HDR + "   what it costs in code")
    LAD = [("as flown rev 6.4", dict(kp=1.0, laf=14.0, q=1.0), "nothing"),
           ("ARM-KP2  KP 3.0 Q 0.60 (toggles)", dict(kp=3.0, laf=14.0, q=0.60), "0 lines -- at the toggle ceiling"),
           ("KP 3.0 Q 0.35 (toggles)", dict(kp=3.0, laf=14.0, q=0.35), "0 lines"),
           ("KP 4 Q 0.25", dict(kp=4.0, laf=14.0, q=0.25), "1 constant (MAX_MULT)"),
           ("KP 5 Q 0.20", dict(kp=5.0, laf=14.0, q=0.20), "1 constant"),
           ("KP 8 Q 0.15", dict(kp=8.0, laf=14.0, q=0.15), "1 constant"),
           ("KP 8 Q 0.20", dict(kp=8.0, laf=14.0, q=0.20), "1 constant"),
           ("KP 8 Q 0.25", dict(kp=8.0, laf=14.0, q=0.25), "1 constant"),
           ("KP 12 Q 0.15", dict(kp=12.0, laf=14.0, q=0.15), "1 constant"),
           ("KP 16 Q 0.15", dict(kp=16.0, laf=14.0, q=0.15), "1 constant"),
           ("KP 8 Q 0.15 + I-decoupled", dict(kp=8.0, laf=14.0, q=0.15, decouple_i=True), "1 constant + 2 lines"),
           ("KP 8 Q 0.15 + LP 1.0Hz", dict(kp=8.0, laf=14.0, q=0.15, lp_hz=1.0), "1 constant + a new filter"),
           ]
    for lbl, kw, cost in LAD:
        print(fmt(lbl, E.score(**kw), cost))
    print()
    A = E.E - E.V * E.D
    print(f"   THE CLASS ASYMPTOTE (rho -> 0): J_inf {float(np.sum(np.abs(A[:, E.b])**2))/E.px:.3f} "
          f"=> {(1.3512 - float(np.sum(np.abs(A[:, E.b])**2))/E.px)/(1.3512-0.442)*100:.0f} % closure at INFINITE gain")
