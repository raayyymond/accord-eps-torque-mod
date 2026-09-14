# -*- coding: utf-8 -*-
"""v293_ident_n.py -- THE CANDIDATE CONFIGS on the identified plant.  Subagent v293plant, 2026-09-13.
ANALYSIS ONLY.

THE BRANCH ALGEBRA (as the orchestrator states it, and as the fork's source reads):
  with AccordRatePlantFF ON:  output = (P + I)/SteerLatAccel + plant_ff_torque + friction_torque
  so SteerLatAccel scales ONLY P and I there.
  error_with_lsf = e*(1 + lsf/Kp)  =>  P = (Kp + lsf)*e  and  I = Ki*(Kp+lsf)/Kp * Int(e)
  so  Kp_eff = SteerKP + lsf(v)  and  Ki_eff = AccordTorqueKi * Kp_eff / SteerKP
  normalised loop:  L(s) = (Kp_eff + Ki_eff/s) * (LAF_true(v)/SteerLatAccel) * e^{-sd}/(1+sT)
The FEEDFORWARD does not enter L(s) at all -- it sets the error the loop starts from, which is why the
step response below is simulated WITH the feedforward rather than as a pure feedback step.

'LOOSE' IS A FEEDBACK QUANTITY, not a feedforward one: if the wheel is displaced from where the plan
wants it, the feedforward does not change (it follows the plan), so only P and I restore it.  The
controller's hold stiffness is therefore  Kp_eff * (lat accel per degree) / SteerLatAccel, in torque
per degree, and it is compared against the plant's own return spring a(v).
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
DT = 0.01
SR, WB = 16.88, 2.83
G_BP, G_V = [5.0, 12.5, 18.5, 28.5], [120.0, 95.0, 85.0, 70.0]
K_BP, K_V = [4.0, 8.0, 12.5, 18.5, 28.5], [0.17, 0.28, 0.35, 0.45, 0.50]
G_NEW = [550.0, 271.0, 246.0, 205.0]
K_NEW = [0.93, 1.64, 2.15, 2.77, 3.15]
# the identified plant, from v293_ident_d.py D2 (M1 on the LAF channel) and v293_ident_m.py M1
CELLS = [  # label, v, LAF_true, dead d, lag T, plant spring a(v), Coulomb F
    ("1-8 @3",   3.0,  4.03, 0.129, 0.287, 0.00168, 0.0120),
    ("1-8 @4.5", 4.5,  4.03, 0.129, 0.287, 0.00168, 0.0120),
    ("8-15",    11.96, 5.94, 0.046, 0.259, 0.00764, 0.0119),
    ("15-22",   18.94, 5.52, 0.240, 0.000, 0.01149, 0.0112),
    (">22",     22.80, 6.88, 0.200, 0.000, 0.01539, 0.0098),
]
CONFIGS = [
    # name, plantFF?, spring_scale, gain_scale, rate_gain, new_tables?, friction, LAF, Kp, Ki
    ("C0 as flown",        False, 1.0,  1.0, 0.5, False, 0.000,  6.0, 0.30, 0.15),
    ("C1 toggle 3.3",      True,  3.3,  1.0, 0.3, False, 0.012, 12.0, 0.50, 0.30),
    ("C1' toggle 2.15",    True,  2.15, 1.0, 0.3, False, 0.012, 12.0, 0.50, 0.30),
    ("C2 new tables",      True,  1.0,  1.0, 1.0, True,  0.012, 12.0, 0.50, 0.30),
    ("C3 hotter",          True,  1.0,  1.0, 1.0, True,  0.012,  9.0, 0.35, 0.30),
    ("C4 stiffer",         True,  1.0,  1.0, 1.0, True,  0.012, 12.0, 0.70, 0.50),
    # C5/C6 added by the subagent: the five configs above ALL cut the controller's hold stiffness
    # below C0's, because SteerLatAccel 12 halves P and I -- the opposite of fixing "loose".
    # These keep SteerLatAccel at 6 so the feedback authority is not thrown away.
    ("C5 new tbl, LAF 6",   True,  1.0,  1.0, 1.0, True,  0.012,  6.0, 0.50, 0.30),
    ("C6 new tbl, LAF 6+",  True,  1.0,  1.0, 1.0, True,  0.012,  6.0, 0.70, 0.35),
    # C7/C8: C5/C6 fail Ms at speed because Ki_eff/Kp_eff = 0.6-0.5 /s puts the integrator's corner
    # (0.08-0.10 Hz) ABOVE the crossover (0.08-0.18 Hz is marginal, and below 15 m/s it is well
    # above), which is the classic sensitivity peak.  WITH THE FEEDFORWARD CORRECT THE INTEGRATOR NO
    # LONGER HAS A STEADY ERROR TO CANCEL, so it can be an order of magnitude smaller.
    ("C7 LAF 6, low Ki",    True,  1.0,  1.0, 1.0, True,  0.012,  6.0, 0.50, 0.05),
    ("C8 LAF 6, stiff+low", True,  1.0,  1.0, 1.0, True,  0.012,  6.0, 0.70, 0.07),
    # C9: the Ms peak at speed is NOT the integrator -- with T = 0 and a 0.20-0.24 s dead time the
    # Nyquist plot passes at |1 - Kp_n| near the phase crossover, so Ms ~ 1/(1 - Kp_n) and Ms <= 2
    # requires Kp_n <= 0.5.  At LAF 6 that means SteerKP <= 0.34-0.35.  C9 sits exactly there, which
    # keeps the controller's hold stiffness at or above C0's while meeting the margin bound.
    ("C9 LAF 6, Kp at bound", True, 1.0, 1.0, 1.0, True, 0.012,  6.0, 0.34, 0.07),
    # C10 = C4 with the integrator cut.  Ms at speed is Kp-dominated (Ms ~ 1/(1 - Kp_n) at the dead
    # time's phase crossover), so Ki barely moves it -- but with the feedforward CORRECT the
    # integrator no longer has a steady feedforward error to cancel (that was its measured 38 %
    # share on route 70), and a smaller Ki is what stops the low-speed wind-up.
    ("C10 = C4, Ki cut",     True,  1.0,  1.0, 1.0, True,  0.012, 12.0, 0.70, 0.20),
]


def lsf(v):
    return (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 0.3)) ** 2


def la_per_deg(v):
    return np.radians(1.0) / (SR * WB) * v ** 2


def hold_of(cfg, v):
    """the feedforward's hold torque per degree, in openpilot torque units."""
    _, pff, ss, gs, rg, newt, fr, laf, kp, ki = cfg
    if not pff:
        return la_per_deg(v) / laf
    if newt:
        return float(np.interp(v, K_BP, K_NEW)) / float(np.interp(v, G_BP, G_NEW))
    return ss * float(np.interp(v, K_BP, K_V)) / (gs * float(np.interp(v, G_BP, G_V)))


def margins(kp_n, ki_n, d, T, fmax=8.0):
    w = 2 * np.pi * np.logspace(-3, np.log10(fmax), 8000)
    s = 1j * w
    Lw = (kp_n + ki_n / s) * np.exp(-s * d) / (1 + s * T)
    mag = np.abs(Lw)
    ph = np.unwrap(np.angle(Lw)) * 180 / np.pi
    idx = np.where(np.diff(np.sign(mag - 1.0)) != 0)[0]
    Ms = float(np.max(np.abs(1.0 / (1.0 + Lw))))
    if len(idx) == 0:
        return np.nan, np.nan, Ms
    i = idx[-1]
    wc = float(np.interp(0.0, [np.log(mag[i + 1]), np.log(mag[i])], [w[i + 1], w[i]])
               if mag[i] > mag[i + 1] else
               np.interp(0.0, [np.log(mag[i]), np.log(mag[i + 1])], [w[i], w[i + 1]]))
    return 180.0 + float(np.interp(wc, w, ph)), wc / (2 * np.pi), Ms


def step_sim(kp_n, ki_n, d, T, ff_ratio, tmax=8.0):
    """closed loop on a 1 m/s^2 setpoint step, WITH the feedforward delivering ff_ratio of it."""
    n = int(tmax / DT)
    nd = int(round(d / DT))
    a = float(np.exp(-DT / T)) if T > 1e-6 else 0.0
    y = np.zeros(n); xlag = 0.0; integ = 0.0
    buf = np.zeros(max(nd + 1, 1))
    for i in range(1, n):
        e = 1.0 - y[i - 1]
        integ += e * DT
        uc = kp_n * e + ki_n * integ            # feedback, already normalised
        u = uc + ff_ratio                        # the FF delivers ff_ratio of the unit step
        buf[1:] = buf[:-1]; buf[0] = u
        ud = buf[nd] if nd > 0 else u
        xlag = a * xlag + (1 - a) * ud if T > 1e-6 else ud
        y[i] = xlag
    if not np.all(np.isfinite(y)) or np.max(np.abs(y)) > 20.0:
        return np.inf, np.nan, y          # DIVERGENT -- the loop is unstable on this plant
    ov = (np.max(y) - 1.0) if np.max(y) > 1.0 else 0.0
    within = np.abs(y - 1.0) <= 0.05
    ts = np.nan
    for i in range(n - 1, 0, -1):
        if not within[i]:
            ts = (i + 1) * DT
            break
    if np.all(within[int(0.5 / DT):]):
        ts = 0.5
    return ov, (ts if np.isfinite(ts) and ts < tmax - DT else np.nan), y


pr("=" * 116)
pr("V293 -- THE CANDIDATE CONFIGS ON THE IDENTIFIED PLANT")
pr("=" * 116)
pr("\n    PLANT USED (v293_ident_d.py D2 M1 on the LAF channel; a(v) and F from v293_ident_m.py M1):")
pr("    %-10s %7s %10s %9s %9s %12s %10s" % ("cell", "v", "LAF_true", "dead s", "lag T s",
                                             "spring a", "Coulomb F"))
for lab, v, laf_t, d, T, a_, F_ in CELLS:
    pr("    %-10s %7.2f %10.2f %9.3f %9.3f %12.5f %10.4f" % (lab, v, laf_t, d, T, a_, F_))
pr("    ⚠ the two 1-8 rows share one cell's parameters (band median 5.4 m/s) and that cell is the")
pr("    weakest in the study -- its b interval crosses zero.  Read those rows as indicative.")

for cfg in CONFIGS:
    name, pff, ss, gs, rg, newt, fr, laf, kp, ki = cfg
    pr("\n" + "=" * 116)
    pr("%s   %s | SteerLatAccel %.1f  SteerKP %.2f  Ki %.2f  SteerFriction %.3f%s"
       % (name, "plant FF" if pff else "else-branch (lat-accel FF)", laf, kp, ki, fr,
          ("  spring x%.2f rate %.1f" % (ss, rg)) if pff and not newt else
          ("  NEW TABLES, rate %.1f" % rg) if pff else ""))
    pr("=" * 116)
    pr("    %-10s %7s %9s %9s %10s %10s %8s %8s %8s %9s %9s %9s"
       % ("cell", "v", "Kp_eff", "Ki_eff", "Kp norm", "Ki norm", "PM", "wc Hz", "Ms",
          "FF hold", "step ov", "settle s"))
    rows = []
    for lab, v, laf_t, d, T, a_, F_ in CELLS:
        lv = lsf(v)
        kpe = kp + lv
        kie = ki * kpe / kp
        kpn = kpe * laf_t / laf
        kin = kie * laf_t / laf
        pm, wc, ms = margins(kpn, kin, d, T)
        h = hold_of(cfg, v)
        r = h / a_
        ov, ts, _ = step_sim(kpn, kin, d, T, min(max(r, 0.0), 3.0))
        flag = ""
        if (np.isfinite(pm) and pm < 45) or ms > 2.0:
            flag = "  <-- PM/Ms FAIL"
        ovs = "DIVERGES" if not np.isfinite(ov) else "%.3f" % ov
        pr("    %-10s %7.2f %9.3f %9.3f %10.3f %10.3f %8.1f %8.3f %8.2f %9.3f %9s %9s%s"
           % (lab, v, kpe, kie, kpn, kin, pm, wc, ms, r, ovs,
              ("%.2f" % ts) if np.isfinite(ts) else "  >8", flag))
        rows.append(dict(cell=lab, v=v, kp_eff=kpe, ki_eff=kie, kp_n=kpn, ki_n=kin, pm=pm,
                         wc=wc, ms=ms, ff_hold_ratio=r,
                         overshoot=(None if not np.isfinite(ov) else float(ov)),
                         settle=float(ts) if np.isfinite(ts) else None))
    # the four symptom channels
    pr("\n    SYMPTOM CHANNELS")
    pr("    %-10s %7s %16s %16s %14s %14s"
       % ("cell", "v", "snap: fric FF", "loose: ctrl stiff", "oversteer: FF", "overshoot"))
    for lab, v, laf_t, d, T, a_, F_ in CELLS:
        lv = lsf(v)
        kpe = kp + lv
        stiff = kpe * la_per_deg(v) / laf
        r = hold_of(cfg, v) / a_
        row = [x for x in rows if x["cell"] == lab][0]
        if row["overshoot"] is None:
            row = dict(row); row["overshoot"] = np.inf
        pr("    %-10s %7.2f %16s %16.5f %14.3f %14s"
           % (lab, v, "%.3f of %.4f" % (fr, F_), stiff, r,
              "DIVERGES" if not np.isfinite(row["overshoot"]) else "%.3f" % row["overshoot"]))
    RES[name] = dict(rows=rows, cfg=dict(plantff=pff, spring=ss, gain=gs, rate=rg, newtables=newt,
                                         friction=fr, laf=laf, kp=kp, ki=ki))

pr("\n" + "=" * 116)
pr("THE COLUMNS, and what each symptom needs")
pr("=" * 116)
pr("  snap  -> the friction feedforward.  Measured Coulomb F is 0.0098-0.0120 of full scale; a config")
pr("           with SteerFriction 0 cancels NONE of it, one with 0.012 cancels essentially all of it.")
pr("           C0 is the only candidate at 0.  [the ratchet is a friction symptom -- section E/H]")
pr("  loose -> the CONTROLLER's hold stiffness, Kp_eff * (lat accel per deg) / SteerLatAccel, in torque")
pr("           per degree, against the plant's own spring a(v).  The feedforward does NOT contribute:")
pr("           it follows the plan and does not respond to a displacement.  Measured on route 70 the")
pr("           total loop stiffness was 0.0032 / 0.0065 / 0.0128 / 0.0227 (section G2).")
pr("  oversteer -> the FF hold ratio above 15 m/s.  1.000 is correct; the flown config reads 1.9-2.1.")
pr("  overshoot -> the simulated 1 m/s^2 step, WITH each config's own feedforward error included.")

pr("\n" + "=" * 116)
pr("SUMMARY -- the four symptom channels at the two best-determined bands, plus the low-speed flag")
pr("=" * 116)
pr("\n    %-22s | %-30s | %-30s | %s"
   % ("config", "15-22 m/s: Ms / stiff / FF / ov", "  >22 m/s: Ms / stiff / FF / ov", "1-8 m/s"))
for name in RES:
    r15 = [x for x in RES[name]["rows"] if x["cell"] == "15-22"][0]
    r22 = [x for x in RES[name]["rows"] if x["cell"] == ">22"][0]
    rlo = [x for x in RES[name]["rows"] if x["cell"] == "1-8 @4.5"][0]
    cf = RES[name]["cfg"]
    st15 = (cf["kp"] + lsf(18.94)) * la_per_deg(18.94) / cf["laf"]
    st22 = (cf["kp"] + lsf(22.80)) * la_per_deg(22.80) / cf["laf"]
    ov15 = "div" if r15["overshoot"] is None else "%.2f" % r15["overshoot"]
    ov22 = "div" if r22["overshoot"] is None else "%.2f" % r22["overshoot"]
    pr("    %-22s | %5.2f / %7.5f / %5.3f / %-5s | %5.2f / %7.5f / %5.3f / %-5s | PM %6.1f Ms %5.2f"
       % (name, r15["ms"], st15, r15["ff_hold_ratio"], ov15,
          r22["ms"], st22, r22["ff_hold_ratio"], ov22, rlo["pm"], rlo["ms"]))
pr("\n    stiff = the CONTROLLER's hold stiffness in torque per degree (C0 reads 0.01071 and 0.01262);")
pr("    FF = the feedforward hold ratio (1.000 correct); ov = the simulated 1 m/s^2 step overshoot.")
pr("    EVERY config, C0 included, fails PM/Ms in the 1-8 m/s band -- the low-speed factor, not the")
pr("    config, and the band where the identified plant is weakest.")

with open(os.path.join(L.SCRATCH, "v293_ident_n.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_n.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_n.txt / .json")
