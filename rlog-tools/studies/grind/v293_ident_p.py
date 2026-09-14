# -*- coding: utf-8 -*-
"""v293_ident_p.py -- R1 / R2 / R3 on the identified plant, plus a DESCRIBING-FUNCTION check of the
SteerFriction relay.  Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

All three share: AccordRatePlantFF 1, AccordEpsSpringScale 2.15, AccordEpsGainScale 1.0,
AccordFFRateGain 0.40, SteerFriction 0.011, SteerDelay 0.2, latAccelOffset CLEARED.
  R1  SteerLatAccel 6,  SteerKP 0.30, Ki 0.15
  R2  SteerLatAccel 14, SteerKP 1.20, Ki 0.35
  R3  SteerLatAccel 12, SteerKP 1.00, Ki 0.30

THE DESCRIBING FUNCTION.  friction_torque = F * clip((e_lsf + 0.22*jerk)/0.30, -1, +1) with
e_lsf = e*(1 + lsf/Kp), so in RAW error units it is a SATURATION of limit F and linear half-width
    delta = 0.30 / (1 + lsf/Kp)
sitting in PARALLEL with the PID (both act on the error).  Its describing function is real:
    N(A) = F/delta                                             for A <= delta
    N(A) = (2F/(pi*delta)) * [asin(d/A) + (d/A)*sqrt(1-(d/A)^2)], d = delta,  for A > delta
and it DECREASES from F/delta towards 0 as the amplitude grows.  The loop, with everything in
normalised (lat-accel error -> lat-accel) units, is
    L(s, A) = [ Cn(s) + Fn(A) ] * e^{-sd}/(1+sT),
    Cn(s) = (Kp_eff + Ki_eff/s) * LAF_true / SteerLatAccel,     Fn(A) = N(A) * LAF_true
A limit cycle needs  Fn(A) = -1/Plant(jw) - Cn(jw)  with the right-hand side REAL and POSITIVE and no
larger than Fn_max = (F/delta)*LAF_true.  The jerk term is exogenous (it comes from the plan, not the
error), so it biases the saturation off-centre rather than entering the loop; that REDUCES the
effective gain at the origin, so treating it as zero is the CONSERVATIVE choice and is what is done.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v293_ident_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []
pr = L.pr_factory(OUT)
RES = {}
DT, SR, WB = 0.01, 16.88, 2.83
G_BP, G_V = [5.0, 12.5, 18.5, 28.5], [120.0, 95.0, 85.0, 70.0]
K_BP, K_V = [4.0, 8.0, 12.5, 18.5, 28.5], [0.17, 0.28, 0.35, 0.45, 0.50]
SPRING_SCALE, RATE_GAIN, FRIC = 2.15, 0.40, 0.011
CELLS = [  # label, v, LAF_true, dead d, lag T, plant spring a(v), plant viscous b(v), Coulomb F
    ("1-8 @3.0",  3.0,  4.03, 0.129, 0.287, 0.00168, 0.00180, 0.0120),
    ("1-8 @4.5",  4.5,  4.03, 0.129, 0.287, 0.00168, 0.00180, 0.0120),
    ("8-15",     11.96, 5.94, 0.046, 0.259, 0.00764, 0.00366, 0.0119),
    ("15-22",    18.94, 5.52, 0.240, 0.000, 0.01149, 0.00409, 0.0112),
    (">22",      22.80, 6.88, 0.200, 0.000, 0.01539, 0.00489, 0.0098),
]
CONFIGS = [("R1", 6.0, 0.30, 0.15), ("R2", 14.0, 1.20, 0.35), ("R3", 12.0, 1.00, 0.30),
           # R2'/R3': the same configs with SteerKP set to the Ms <= 2 bound.  Ms at speed is
           # 1/(1 - Kp_norm) at the dead time's phase crossover, so Ms <= 2 needs Kp_norm <= 0.5,
           # i.e. SteerKP <= 0.5*LAF_set/LAF_true - lsf(v).  The >22 cell binds (LAF_true 6.88).
           ("R2' Kp at bound", 14.0, 0.92, 0.35), ("R3' Kp at bound", 12.0, 0.78, 0.30)]


def lsf(v):
    return float((np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 0.3)) ** 2)


def la_per_deg(v):
    return np.radians(1.0) / (SR * WB) * v ** 2


def ff_hold(v):
    return SPRING_SCALE * float(np.interp(v, K_BP, K_V)) / float(np.interp(v, G_BP, G_V))


def margins(kpn, kin, d, T, fmax=8.0):
    w = 2 * np.pi * np.logspace(-3, np.log10(fmax), 9000)
    s = 1j * w
    Lw = (kpn + kin / s) * np.exp(-s * d) / (1 + s * T)
    mag, ph = np.abs(Lw), np.unwrap(np.angle(Lw)) * 180 / np.pi
    Ms = float(np.max(np.abs(1.0 / (1.0 + Lw))))
    idx = np.where(np.diff(np.sign(mag - 1.0)) != 0)[0]
    if not len(idx):
        return np.nan, np.nan, Ms
    i = idx[-1]
    wc = float(np.interp(0.0, [np.log(mag[i + 1]), np.log(mag[i])], [w[i + 1], w[i]])
               if mag[i] > mag[i + 1] else
               np.interp(0.0, [np.log(mag[i]), np.log(mag[i + 1])], [w[i], w[i + 1]]))
    return 180.0 + float(np.interp(wc, w, ph)), wc / (2 * np.pi), Ms


def step_sim(kpn, kin, d, T, ffr, tmax=8.0):
    n = int(tmax / DT); nd = int(round(d / DT))
    a = float(np.exp(-DT / T)) if T > 1e-6 else 0.0
    y = np.zeros(n); x = 0.0; integ = 0.0; buf = np.zeros(max(nd + 1, 1))
    for i in range(1, n):
        e = 1.0 - y[i - 1]
        integ += e * DT
        u = kpn * e + kin * integ + ffr
        buf[1:] = buf[:-1]; buf[0] = u
        ud = buf[nd] if nd > 0 else u
        x = a * x + (1 - a) * ud if T > 1e-6 else ud
        y[i] = x
    if not np.all(np.isfinite(y)) or np.max(np.abs(y)) > 20.0:
        return np.inf
    return float(max(np.max(y) - 1.0, 0.0))


pr("=" * 112)
pr("V293 -- R1 / R2 / R3 ON THE IDENTIFIED PLANT, AND THE FRICTION RELAY")
pr("=" * 112)
pr("\n    shared: plant FF on, SpringScale 2.15, GainScale 1.0, FFRateGain 0.40, SteerFriction 0.011,")
pr("    SteerDelay 0.2, latAccelOffset cleared.   R1 LAF 6 / Kp 0.30 / Ki 0.15   R2 LAF 14 / 1.20 /")
pr("    0.35   R3 LAF 12 / 1.00 / 0.30")
pr("\n    🛑 ONE CORRECTION TO THE RATIONALE AS SENT.  'Ki_eff = 0.35*LAF_true/14 equals the flown")
pr("    0.15*LAF_true/6' holds only for the BASE Ki (both are 0.025).  The live integral gain is")
pr("    Ki_eff = Ki*Kp_eff/Kp, and Kp differs, so the lsf boost differs: at 4.5 m/s R1 multiplies Ki")
pr("    by 22.1 and R2 by only 6.3.  R2's integral action is therefore 3.5x LOWER at low speed and")
pr("    1.4x lower at 19 m/s -- not unchanged.  That is in the right direction (less wind-up), but it")
pr("    should be known rather than assumed.")
pr("\n    ⚠ the 1-8 rows use LAF_true 4.03 (the M1 fit).  The rationale as sent used 3.19 (the M0 fit")
pr("    of the same cell); with 4.03 the R2 low-speed loop gain is 2.17, not 1.72.  Both are printed.")

for nm, laf, kp, ki in CONFIGS:
    pr("\n" + "=" * 112)
    pr("%s   SteerLatAccel %.0f   SteerKP %.2f   AccordTorqueKi %.2f" % (nm, laf, kp, ki))
    pr("=" * 112)
    pr("    %-10s %6s %9s %9s %9s %9s %7s %8s %7s %10s %10s %9s"
       % ("cell", "v", "Kp_eff", "Ki_eff", "Kp norm", "Ki norm", "PM", "wc Hz", "Ms",
          "stiff u/deg", "plant a", "step ov"))
    rows = []
    for lab, v, laf_t, d, T, a_, b_, F_ in CELLS:
        lv = lsf(v)
        kpe, kie = kp + lv, ki * (kp + lv) / kp
        kpn, kin = kpe * laf_t / laf, kie * laf_t / laf
        pm, wc, ms = margins(kpn, kin, d, T)
        stiff = kpe * la_per_deg(v) / laf
        ov = step_sim(kpn, kin, d, T, min(ff_hold(v) / a_, 3.0))
        flag = "  <-- FAIL" if ((np.isfinite(pm) and pm < 45) or ms > 2.0) else ""
        pr("    %-10s %6.2f %9.3f %9.3f %9.3f %9.3f %7.1f %8.3f %7.2f %10.5f %10.5f %9s%s"
           % (lab, v, kpe, kie, kpn, kin, pm, wc, ms, stiff, a_,
              "DIVERGES" if not np.isfinite(ov) else "%.3f" % ov, flag))
        rows.append(dict(cell=lab, v=v, kp_eff=kpe, ki_eff=kie, kp_n=kpn, ki_n=kin, pm=pm, wc=wc,
                         ms=ms, stiff=stiff, plant_a=a_,
                         ov=None if not np.isfinite(ov) else ov))
    RES[nm] = dict(laf=laf, kp=kp, ki=ki, rows=rows)

# ======================================================================================================
pr("\n" + "=" * 112)
pr("P2. THE FRICTION RELAY -- describing-function check at 3.0 / 4.5 / 8 / 12 m/s, R1 and R2")
pr("    delta = 0.30/(1 + lsf/Kp) is the RAW-ERROR half-width of the saturation; below it the term is")
pr("    a linear gain F/delta, above it a softening relay.  A limit cycle needs")
pr("       Fn(A) = -1/Plant(jw) - Cn(jw)   REAL, POSITIVE and <= Fn_max = (F/delta)*LAF_true.")
pr("=" * 112)


def dfun(A, delta, F):
    if A <= delta:
        return F / delta
    r = delta / A
    return (2.0 * F / (np.pi * delta)) * (np.arcsin(r) + r * np.sqrt(max(1.0 - r * r, 0.0)))


def limit_cycle(laf_set, kp, ki, v, laf_t, d, T, F=FRIC):
    lv = lsf(v)
    kpe, kie = kp + lv, ki * (kp + lv) / kp
    kpn, kin = kpe * laf_t / laf_set, kie * laf_t / laf_set
    delta = 0.30 / (1.0 + lv / kp)
    fnmax = (F / delta) * laf_t
    w = 2 * np.pi * np.logspace(-2, np.log10(20.0), 40000)
    s = 1j * w
    P = np.exp(-s * d) / (1 + s * T)
    Z = -1.0 / P - (kpn + kin / s)
    im = Z.imag
    out = []
    for i in range(len(w) - 1):
        if im[i] == 0 or im[i] * im[i + 1] < 0:
            t = im[i] / (im[i] - im[i + 1]) if im[i] != im[i + 1] else 0.0
            wz = w[i] + t * (w[i + 1] - w[i])
            re = Z.real[i] + t * (Z.real[i + 1] - Z.real[i])
            if re <= 0 or re > fnmax:
                continue
            lo, hi = delta, 400.0 * delta
            for _ in range(200):
                mid = 0.5 * (lo + hi)
                if dfun(mid, delta, F) > re:
                    lo = mid
                else:
                    hi = mid
            A = 0.5 * (lo + hi)
            out.append((wz / (2 * np.pi), A, re))
    return delta, fnmax, out


pr("\n    %-6s %6s %10s %11s %11s %12s %12s %12s"
   % ("cfg", "v", "delta", "Fn_max", "limit cyc?", "freq Hz", "A m/s^2", "angle deg pk"))
for nm, laf, kp, ki in (("R1", 6.0, 0.30, 0.15), ("R2", 14.0, 1.20, 0.35)):
    for lab, v, laf_t, d, T, a_, b_, F_ in CELLS:
        if v not in (3.0, 4.5, 11.96) and abs(v - 8.0) > 0.01:
            continue
        delta, fnmax, lc = limit_cycle(laf, kp, ki, v, laf_t, d, T)
        if not lc:
            pr("    %-6s %6.2f %10.5f %11.3f %11s" % (nm, v, delta, fnmax, "NO"))
        for (f_, A, re) in lc:
            pr("    %-6s %6.2f %10.5f %11.3f %11s %12.2f %12.5f %12.3f"
               % (nm, v, delta, fnmax, "YES", f_, A, A / la_per_deg(v)))
        RES.setdefault("lc", {}).setdefault(nm, {})[lab] = dict(
            delta=delta, fnmax=fnmax, cycles=[dict(f=x[0], A=x[1]) for x in lc])
    # the 8 m/s point is not one of the fitted cells; interpolate the plant there
    lab, v = "interp @8", 8.0
    laf_t = float(np.interp(8.0, [4.5, 11.96], [4.03, 5.94]))
    d = float(np.interp(8.0, [4.5, 11.96], [0.129, 0.046]))
    T = float(np.interp(8.0, [4.5, 11.96], [0.287, 0.259]))
    delta, fnmax, lc = limit_cycle(laf, kp, ki, v, laf_t, d, T)
    if not lc:
        pr("    %-6s %6.2f %10.5f %11.3f %11s   (plant interpolated between the 1-8 and 8-15 cells)"
           % (nm, v, delta, fnmax, "NO"))
    for (f_, A, re) in lc:
        pr("    %-6s %6.2f %10.5f %11.3f %11s %12.2f %12.5f %12.3f   (plant interpolated)"
           % (nm, v, delta, fnmax, "YES", f_, A, A / la_per_deg(v)))

pr("\n    THE SteerFriction AT WHICH ANY SURVIVING CYCLE DISAPPEARS:")
for nm, laf, kp, ki in (("R1", 6.0, 0.30, 0.15), ("R2", 14.0, 1.20, 0.35)):
    for lab, v, laf_t, d, T, a_, b_, F_ in CELLS:
        if v not in (3.0, 4.5, 11.96):
            continue
        found = None
        for Ftry in np.arange(0.001, 0.0301, 0.0005):
            _, _, lc = limit_cycle(laf, kp, ki, v, laf_t, d, T, F=float(Ftry))
            if lc and found is None:
                found = float(Ftry)
        _, _, lc0 = limit_cycle(laf, kp, ki, v, laf_t, d, T)
        pr("    %-6s %6.2f  at 0.011: %-4s | first F that sustains a cycle: %s"
           % (nm, v, "YES" if lc0 else "NO",
              ("%.4f" % found) if found is not None else "none up to 0.030"))

with open(os.path.join(L.SCRATCH, "v293_ident_p.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_p.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_p.txt / .json")
