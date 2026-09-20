# -*- coding: utf-8 -*-
"""c1 -- VALIDATE the inherited frontier engine before extending it.

Checks, each of which must land or the extension is not usable:
  V1  as-flown positive control: metric 1.3512, shake_cmd 1.000, shake_L ~0.10
  V2  the analytic C used by the engine reproduces the fork source EXACTLY (re-read from the fork
      today, not from lp_lib): notch coefficients, PI, the (1+lsf/kp) factor, the LAF divide
  V3  the flown-anchor calibration of the shake axis: T64 / T3(r72) / T2(r71) shake-band |L|
  V4  the ARM-KP2 headline (SteerKP 3.0 + Q 0.60) reproduces the brief's J 1.058 / 33.3 % / x1.148
  V5  the metric's window population is entirely >= 15 m/s (so a low-speed schedule is metric-inert)
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
FRONT = STUDY / "shapedgain" / "frontier"
sys.path.insert(0, str(FRONT))
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP                                   # noqa: E402
from f5_frontier import Engine, FLOWN, C_of           # noqa: E402

# --- the fork's own constants, RE-READ from the source today (not inherited) -------------------
FORK = Path("C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot")
TUNES = FORK / "selfdrive/controls/lib/latcontrol_vehicle_tunes.py"
TORQ = FORK / "selfdrive/controls/lib/latcontrol_torque.py"
VARS = FORK / "starpilot/common/starpilot_variables.py"


def grab(path, name):
    for ln in open(path, encoding="utf-8", errors="replace"):
        if ln.strip().startswith(name + " ="):
            return eval(ln.split("=", 1)[1].split("#")[0].strip())
    return None


if __name__ == "__main__":
    print("=" * 100)
    print("V2  FORK SOURCE vs lp_lib constants (re-read from the fork today)")
    pairs = [("HONDA_ACCORD_HOLD_V_BP", TUNES, LP.HOLD_V_BP), ("HONDA_ACCORD_HOLD_K_V", TUNES, LP.HOLD_K_V),
             ("HONDA_ACCORD_EPS_INERTIA", TUNES, LP.EPS_INERTIA),
             ("HONDA_ACCORD_KI_SCHEDULE_V_BP", TUNES, LP.KI_SCHED_BP),
             ("LOW_SPEED_X", TORQ, LP.LOW_SPEED_X), ("LOW_SPEED_Y", TORQ, LP.LOW_SPEED_Y),
             ("MIN_SPEED", TORQ, LP.MIN_SPEED), ("STEER_KP_MAX_MULT", VARS, None),
             ("LAT_ACCEL_FACTOR_MAX_MULT", VARS, None), ("STEER_KP_MIN", VARS, None)]
    for nm, p, expect in pairs:
        got = grab(p, nm)
        ok = "MISSING" if got is None else "-" if expect is None else ("OK " if np.allclose(np.atleast_1d(got), np.atleast_1d(expect)) else "MISMATCH")
        print(f"   {ok:9s} {nm:32s} = {got}")

    # notch: the engine's inline coefficients vs the fork class, brute-forced in the time domain
    import math
    dt = 0.01
    rng = np.random.default_rng(5)
    x = rng.standard_normal(40000)
    for f0, q in ((1.95, 0.60), (1.05, 0.60), (2.10, 3.0)):
        x1 = x2 = y1 = y2 = 0.0
        yv = np.empty_like(x)
        k = math.tan(math.pi * min(f0, 0.45 / dt) * dt)
        norm = 1.0 / (1.0 + k / q + k * k)
        b0 = (1.0 + k * k) * norm
        b1 = 2.0 * (k * k - 1.0) * norm
        a2 = (1.0 - k / q + k * k) * norm
        for j, xv in enumerate(x):
            y = b0 * xv + b1 * x1 + b0 * x2 - b1 * y1 - a2 * y2
            x2, x1, y2, y1 = x1, xv, y1, y
            yv[j] = y
        from scipy import signal
        fw, pxx = signal.welch(x, 100.0, nperseg=4096)
        _, pxy = signal.csd(x, yv, 100.0, nperseg=4096)
        He = pxy / pxx
        Ha = LP.notch_response(fw, f0, q)
        m = (fw > 0.15) & (fw < 12)
        print(f"   notch f0 {f0:.2f} Q {q:.2f}: max|empirical-analytic| {np.max(np.abs(He[m]-Ha[m])):.2e}"
              f"   |N(0.3)| {abs(LP.notch_response(0.3,f0,q)):.4f} @ {np.degrees(np.angle(LP.notch_response(0.3,f0,q))):+.1f} deg")

    print()
    print("=" * 100)
    eng = Engine()
    print(f"V5  window population: n {len(eng.v)}  speed min {eng.v.min():.2f}  "
          f"p05 {np.percentile(eng.v,5):.2f}  median {np.median(eng.v):.2f}  max {eng.v.max():.2f} m/s")
    print(f"    windows below 15 m/s: {int((eng.v < 15.0).sum())}   below 8 m/s: {int((eng.v < 8.0).sum())}")
    print()
    base = eng.run(**FLOWN)
    print(f"V1  AS FLOWN  metric {base['metric']:.4f} (want 1.3512)   shake_cmd {base['shake_cmd']:.4f} (want 1.000)"
          f"   shake_L {base['shake_L']:.4f}   Ms {base['Ms']:.3f}")
    print(f"    bands {['%.4f' % b for b in base['bands']]}  (0.15-0.30 / 0.30-0.60 / 0.60-1.20 / 1.20-2.40)")
    lo = base['bands'][0] + base['bands'][1]
    print(f"    share of the metric below 0.60 Hz: {lo/base['metric']*100:.1f} %")
    print()
    a2 = eng.run(3.0, 14.0, 0.30, 0.0, 0.60)
    print(f"V4  ARM-KP2 (SteerKP 3.0, Q 0.60)  metric {a2['metric']:.4f} (brief 1.058)  "
          f"closure {a2['closure']*100:.2f} % (brief 33.3)  shake_cmd {a2['shake_cmd']:.4f} (brief 1.148)  "
          f"shake_L {a2['shake_L']:.4f} (brief 0.195)")
    print(f"    wc {a2['wc']:.4f} Hz (brief 0.20)  PM {a2['pm']:.1f} deg (brief 141)  Ms {a2['Ms']:.3f}")
    print()
    print("=" * 100)
    print("V3  shake-axis calibration: shake-band |L| AS FLOWN on the three anchors")
    import json
    S = json.load(open(FRONT / "out" / "f4_plant.json"))
    for fam, lbl in (("T64", "rev 6.4 (target)"), ("T3", "r72 flew clean"), ("T2", "r71 LIMIT-CYCLED")):
        D = S.get(f"{fam}|15+")
        if D is None:
            print(f"   {fam}: no 15+ bin")
            continue
        f = np.array(D["f"])
        P = np.array(D["P"][0]) + 1j * np.array(D["P"][1])
        route = [r for r, g in LP.GROUPS.items() if g == fam][0]
        p = LP.FLOWN[route]
        v = D["v"]
        C = LP.c_fb_analytic(f, p["kp"], float(LP.ki_of(v, p["ki"], p["ki_hi"])), D["laf"],
                             float(LP.low_speed_factor(v)), float(LP.mode_hz(v)) if p["notch"] else None, 1.0)
        L = P * C
        b = (f >= 1.8) & (f <= 3.5)
        print(f"   {fam:5s} {lbl:18s} v {v:4.1f}  |L|shake mean {np.mean(np.abs(L[b])):.3f}  "
              f"@1.95 {abs(L[int(np.argmin(abs(f-1.95)))]):.3f} @2.54 {abs(L[int(np.argmin(abs(f-2.54)))]):.3f} "
              f"@3.03 {abs(L[int(np.argmin(abs(f-3.03)))]):.3f}")
