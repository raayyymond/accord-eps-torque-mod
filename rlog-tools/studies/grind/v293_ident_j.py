# -*- coding: utf-8 -*-
"""v293_ident_j.py -- THE PLANT IN THE FORK'S OWN PARAMETRISATION, with bootstrap intervals.
Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

THE FORK'S MODEL (latcontrol_vehicle_tunes.py, get_honda_accord_rate_plant_ff):
    steering-wheel rate [deg/s] = G(v) * u  -  k(v) * angle [deg]        u in [-1, 1]
    hold torque = spring(v)*spring_scale * angle / (G(v)*gain_scale)
    move torque = rate_gain * d(angle)/dt   / (G(v)*gain_scale)
    G_BP = [5.0, 12.5, 18.5, 28.5]   G_V = [120, 95, 85, 70]   deg/s per unit torque
    K_BP = [4.0, 8.0, 12.5, 18.5, 28.5]  K_V = [0.17,0.28,0.35,0.45,0.50]  1/s
    HONDA_ACCORD_FF_RATE_GAIN = 0.5
Those tables were identified on the OLD closed-rate-servo firmware (r34/r35/r39/r3a/r3c).

HOW THIS DRIVE IDENTIFIES THEM.  The fork's model, solved for the torque, is exactly the
quasi-static balance this study already fits:
    u = (k/G) * angle + (1/G) * d(angle)/dt          [+ a Coulomb term the fork puts in friction]
so with  u = a*angle + b*d(angle)/dt + F*sign(d(angle)/dt) + u0  fitted directly in openpilot torque
units, the fork's parameters follow ALGEBRAICALLY and with no extra assumption:
    G = 1 / b            [deg/s per unit torque]
    k = a / b            [1/s]
    k/G = a              [the hold term, torque per degree]
This resolves the G/k identifiability the orchestrator flagged: the RATIO comes from the slow data
(a, the steady hold torque per degree) and the POLE from the rate term (b), and they are fitted
jointly on the same frames rather than stitched from two estimators.

Bootstrap: 2000 resamples over whole clean stretches (not frames), so the CI respects the
correlation inside a stretch.
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v293_ident_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []
pr = L.pr_factory(OUT)
g = L.load("r70_v293")
DT = 1.0 / L.FS
RES = {}
NBOOT = 2000
rng = np.random.default_rng(11)

G_BP, G_V = [5.0, 12.5, 18.5, 28.5], [120.0, 95.0, 85.0, 70.0]
K_BP, K_V = [4.0, 8.0, 12.5, 18.5, 28.5], [0.17, 0.28, 0.35, 0.45, 0.50]
RATE_GAIN = 0.5
BANDS = [(1.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 99.0)]
BNAME = ["1-8", "8-15", "15-22", ">22"]

pr("=" * 108)
pr("V293 -- THE PLANT IN THE FORK'S OWN PARAMETRISATION  (route 70)")
pr("=" * 108)

u = -g["op_torque"]                     # = output_torque, the frame LAF and the plant FF live in
th = -g["ang"]                          # angle in the same frame
mask = L.clean_mask(g, hands_off=True, min_v=1.0, buffer_s=0.5)
strets = L.stretches(mask, int(4 * L.FS))
sos = signal.butter(4, 0.5, "lowpass", fs=L.FS, output="sos")
pr("\n%d clean stretches >= 4 s (engaged, hands-off, unsaturated, 0.5 s buffer), %.0f s total."
   % (len(strets), sum(b - a for a, b in strets) * DT))

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 108)
pr("J1. THE JOINT FIT  u = a*theta + b*theta' + F*sign(theta') + u0,  per speed band,")
pr("    on 0.5 Hz low-passed clean data with |theta'| > 0.3 deg/s.  2000-resample block bootstrap")
pr("    over whole stretches.  a = k/G (torque per degree), b = 1/G (torque per deg/s), F = Coulomb.")
pr("=" * 108)
CELL = {}
for k in range(len(BANDS)):
    lo, hi = BANDS[k]
    blocks = []
    for (a0, b0) in strets:
        idx = np.arange(a0, b0)
        sel = (g["v"][idx] >= lo) & (g["v"][idx] < hi)
        if sel.sum() < 200:
            continue
        uu = signal.sosfiltfilt(sos, u[a0:b0])
        tt = signal.sosfiltfilt(sos, th[a0:b0])
        td = np.gradient(tt, DT)
        q = sel & (np.abs(td) > 0.3)
        if q.sum() < 100:
            continue
        blocks.append((tt[q], td[q], uu[q], float(np.median(g["v"][idx][sel]))))
    if len(blocks) < 3:
        pr("    %-8s  only %d usable stretches -- not fitted" % (BNAME[k], len(blocks)))
        continue

    def fit(bl):
        TH = np.concatenate([x[0] for x in bl]); TD = np.concatenate([x[1] for x in bl])
        U = np.concatenate([x[2] for x in bl])
        A = np.vstack([TH, TD, np.sign(TD), np.ones(len(TH))]).T
        c, *_ = np.linalg.lstsq(A, U, rcond=None)
        return c, L.r2(U, A @ c), len(TH)

    c0, r2_0, n0 = fit(blocks)
    boots = []
    for _ in range(NBOOT):
        bl = [blocks[i] for i in rng.integers(0, len(blocks), len(blocks))]
        try:
            cb, _, _ = fit(bl)
            boots.append(cb)
        except Exception:
            pass
    B = np.array(boots)
    vmed = float(np.median([x[3] for x in blocks]))
    CELL[BNAME[k]] = dict(v=vmed, a=c0[0], b=c0[1], F=c0[2], u0=c0[3], r2=r2_0, n=n0,
                          nstr=len(blocks), boot=B)
    pr("\n    %-8s v med %5.2f m/s   %d stretches, %.0f s of fitted frames, R2 %.3f"
       % (BNAME[k], vmed, len(blocks), n0 * DT, r2_0))
    for i, nm in enumerate(("a  torque/deg", "b  torque/(deg/s)", "F  torque (Coulomb)",
                            "u0 torque (offset)")):
        pr("       %-22s %10.5f   95%% CI [%+.5f, %+.5f]"
           % (nm, c0[i], np.percentile(B[:, i], 2.5), np.percentile(B[:, i], 97.5)))
    Gv = 1.0 / c0[1] if c0[1] != 0 else np.nan
    kv = c0[0] / c0[1] if c0[1] != 0 else np.nan
    gb = 1.0 / B[:, 1]; kb = B[:, 0] / B[:, 1]
    pr("       %-22s %10.1f   95%% CI [%.1f, %.1f]  deg/s per unit torque"
       % ("=> G = 1/b", Gv, np.percentile(gb, 2.5), np.percentile(gb, 97.5)))
    pr("       %-22s %10.3f   95%% CI [%.3f, %.3f]  1/s   (pole at %.2f Hz)"
       % ("=> k = a/b", kv, np.percentile(kb, 2.5), np.percentile(kb, 97.5), kv / (2 * np.pi)))
    CELL[BNAME[k]].update(G=Gv, k=kv, G_ci=[float(np.percentile(gb, 2.5)), float(np.percentile(gb, 97.5))],
                          k_ci=[float(np.percentile(kb, 2.5)), float(np.percentile(kb, 97.5))])

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 108)
pr("J2. IS THE FIRST-ORDER FORM ENOUGH?  a second pole would show as a roll-off inside 0.15-1.5 Hz.")
pr("=" * 108)
pr("\n    🛑 THE POLE IS THE LEAST WELL DETERMINED QUANTITY HERE, AND TWO ESTIMATORS DISAGREE.")
pr("    Both are reported; this drive does not settle it.")
pr("      (i) the joint fit above gives k = a/b = %s rad/s, i.e. a pole at %s Hz.  Its 95%% CIs are"
   % (" / ".join("%.2f" % CELL[n]["k"] for n in CELL),
      " / ".join("%.2f" % (CELL[n]["k"] / 6.2832) for n in CELL)))
pr("          wide (15-22 band: 1.92 to 7.38 rad/s) and the 1-8 band's crosses zero, identifying")
pr("          nothing there.")
pr("      (ii) part B measured the log-log slope of the torque->ANGLE transfer over 0.15-1.2 Hz as")
pr("          +0.111 (15-22) and +0.117 (>22) -- FLAT -- at coherence 0.82-0.93.  A pole at 0.45 Hz")
pr("          would roll that off at slope -1 over half the fitted range.  It does not, so THAT")
pr("          estimator puts the pole ABOVE ~1.2 Hz, i.e. k > 7.5 rad/s.")
pr("    WHAT BOTH AGREE ON: the fork's k = 0.35-0.50 1/s corners at 0.056-0.080 Hz, 5-40x below")
pr("    either estimate.  The fork's pole is wrong by at least 5x whichever estimator is right.")
pr("    [EVIDENCE for the direction and the lower bound; the magnitude within 5-40x is BELIEF.]")
pr("\n    THE HOLD TERM IS UNAFFECTED by that disagreement -- it uses only the RATIO k/G, which the")
pr("    joint fit pins to +-12 %% at 15-22 m/s.  ⚠ But two values of it exist in this study and they")
pr("    differ 1.6x: the JOINT FIT gives a = 0.0115 torque/deg at 15-22, part B's frequency-domain")
pr("    IV DC gain gives 0.0182.  USE THE JOINT FIT FOR A FEEDFORWARD: it carries an explicit")
pr("    Coulomb term and the IV fit does not, so the IV number has the friction folded into the")
pr("    spring -- and the fork applies friction separately (SteerFriction), which would double-count.")
pr("\n    NO INERTIA TERM IS NEEDED in this band: part B's second-order fit reached VAF 0.98-0.99")
pr("    where the first-order one reached 0.98, and failed (0.07-0.10) where the first-order one did")
pr("    not.  Any resonance is above 1.5 Hz, where this drive has no coherent excitation. [EVIDENCE]")
pr("\n    DEAD TIME beyond the first-order lag: part B's M1 fits give 0.20-0.29 s on the torque->angle")
pr("    and torque->lat-accel channels, with the zero-lag and 200 ms controls both passing (0 ms and")
pr("    196 ms).  ⚠ [BELIEF] that is not a credible transport delay for a rack; read it as the")
pr("    accumulated phase of everything between the tap and the angle, and use it as tau_eq, not as")
pr("    a dead time to put in a model of the actuator alone.")

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 108)
pr("J3. G(v) AND k(v) AT THE FORK'S OWN BREAKPOINTS")
pr("    Linear interpolation between the measured band medians; EXTRAPOLATION is marked BELIEF.")
pr("    The drive's engaged speed range is 2.5-26.6 m/s (p95 25.0), so 28.5 m/s is extrapolated and")
pr("    4.0-5.0 m/s rests on the single weak 1-8 band.")
pr("=" * 108)
vs = np.array([CELL[n]["v"] for n in CELL])
Gs = np.array([CELL[n]["G"] for n in CELL])
ks = np.array([CELL[n]["k"] for n in CELL])
asr = np.array([CELL[n]["a"] for n in CELL])
order = np.argsort(vs)
vs, Gs, ks, asr = vs[order], Gs[order], ks[order], asr[order]


def interp_mark(x, xp, fp):
    val = float(np.interp(x, xp, fp))
    tag = "EVIDENCE" if xp.min() <= x <= xp.max() else "BELIEF (extrapolated)"
    return val, tag


pr("\n    G(v), deg/s per unit torque:")
pr("    %-10s %14s %14s %10s   %s" % ("v (m/s)", "fork G_V", "measured G", "ratio", "status"))
newG = []
for x in G_BP:
    val, tag = interp_mark(x, vs, Gs)
    fk = float(np.interp(x, G_BP, G_V))
    newG.append(val)
    pr("    %-10.1f %14.1f %14.1f %10.2f   %s" % (x, fk, val, val / fk, tag))
pr("\n    k(v), 1/s:")
pr("    %-10s %14s %14s %10s   %s" % ("v (m/s)", "fork K_V", "measured k", "ratio", "status"))
newK = []
for x in K_BP:
    val, tag = interp_mark(x, vs, ks)
    fk = float(np.interp(x, K_BP, K_V))
    newK.append(val)
    pr("    %-10.1f %14.2f %14.2f %10.2f   %s" % (x, fk, val, val / fk, tag))
pr("\n    the HOLD term k/G (torque per degree) -- the only combination the feedforward's hold uses:")
pr("    %-10s %14s %14s %10s" % ("v (m/s)", "fork k/G", "measured a", "ratio"))
for x in G_BP:
    fk = float(np.interp(x, K_BP, K_V)) / float(np.interp(x, G_BP, G_V))
    val, _ = interp_mark(x, vs, asr)
    pr("    %-10.1f %14.5f %14.5f %10.2f" % (x, fk, val, val / fk))
RES["fork_tables"] = dict(G_BP=G_BP, G_new=newG, K_BP=K_BP, K_new=newK,
                          measured=[dict(band=n, **{kk: CELL[n][kk] for kk in
                                                    ("v", "a", "b", "F", "u0", "G", "k", "r2", "nstr")})
                                    for n in CELL])

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 108)
pr("J4. 🛑 CAN TWO SCALARS DO IT, OR MUST THE TABLES BE RESHAPED?")
pr("    The toggles multiply the whole table: k -> k*spring_scale, G -> G*gain_scale.  So the")
pr("    question is whether ONE spring_scale and ONE gain_scale reproduce the measured a(v) and")
pr("    b(v) across the bands, or whether their SHAPE in v differs from the tables'.")
pr("=" * 108)
pr("\n    HOLD term.  hold(v) = k(v)*ss / (G(v)*gs); the toggles enter only as ss/gs, so ONE number.")
pr("    %-10s %10s %12s %12s %12s" % ("band", "v", "fork hold", "measured a", "ratio needed"))
rat = []
for n in CELL:
    vv = CELL[n]["v"]
    fh = float(np.interp(vv, K_BP, K_V)) / float(np.interp(vv, G_BP, G_V))
    r = CELL[n]["a"] / fh
    rat.append(r)
    pr("    %-10s %10.2f %12.5f %12.5f %12.2f" % (n, vv, fh, CELL[n]["a"], r))
if rat:
    best = float(np.median(rat))
    resid = [abs(r / best - 1.0) for r in rat]
    pr("\n    one scalar ss/gs = %.2f (the median) leaves a residual of %s  -- worst %.0f %%"
       % (best, ", ".join("%.0f%%" % (100 * x) for x in resid), 100 * max(resid)))
    RES["spring_scale"] = best
    RES["spring_resid"] = resid
pr("\n    MOVE term.  move(v) = rate_gain / (G(v)*gs); with gs = 1 the toggle is rate_gain alone.")
pr("    %-10s %10s %12s %12s %14s" % ("band", "v", "fork move", "measured b", "rate_gain needed"))
rg = []
for n in CELL:
    vv = CELL[n]["v"]
    fm = RATE_GAIN / float(np.interp(vv, G_BP, G_V))
    need = RATE_GAIN * CELL[n]["b"] / fm
    rg.append(need)
    pr("    %-10s %10.2f %12.5f %12.5f %14.3f" % (n, vv, fm, CELL[n]["b"], need))
if rg:
    pr("\n    one rate_gain = %.2f (the median) against the installed 0.50; spread %.2f-%.2f."
       % (float(np.median(rg)), min(rg), max(rg)))
    RES["rate_gain"] = float(np.median(rg))
pr("\n    VERDICT.  The HOLD term's correction is close to a single scalar: the ratio it needs is")
pr("    printed above and its spread across the bands is the residual.  The MOVE term's is not as")
pr("    tight, and the two cannot both be exact with gain_scale shared -- but the hold term is what")
pr("    carries the steady-state feedforward, and it is the one that is 3x wrong today.")
pr("    ⚠ [BELIEF] I would take the toggles first (they are reversible from Galaxy and need no")
pr("    build) and only reshape HONDA_ACCORD_EPS_K_V / _G_V if a second drive shows the residual")
pr("    matters.  The residual above is the number that decides it.")

# ------------------------------------------------------------------------------------------------
pr("\n" + "=" * 108)
pr("J5. THE TWO BRANCHES COMPARED on the identified plant")
pr("    `else` branch (flown):  torque = (D - roll - offset)/LAF + (Kp*e + Ki*Int e)/LAF")
pr("    `accord_rate_plant_ff`: torque = k*angle_des/G + rate_gain*d(angle_des)/dt/G  + the same PID")
pr("    Evaluated as the STEADY-STATE feedforward error: what fraction of the demand the FF alone")
pr("    delivers, per band, with the measured plant.")
pr("=" * 108)
LAF_TRUE = {"1-8": 3.19, "8-15": 5.32, "15-22": 5.39, ">22": 6.37}
SR, WB = 16.88, 2.83
pr("\n    %-8s %8s %14s %16s %16s %16s"
   % ("band", "v", "LAF FF now", "plantFF as-is", "plantFF x %.2f" % RES.get("spring_scale", 1.0),
      "ideal"))
for n in CELL:
    vv = CELL[n]["v"]
    # a 1 deg steady angle: lat accel through the vehicle model, and the torque each FF commands
    la = np.radians(1.0) / (SR * WB) * vv ** 2
    t_need = CELL[n]["a"]
    t_laf = la / 6.0
    fh = float(np.interp(vv, K_BP, K_V)) / float(np.interp(vv, G_BP, G_V))
    t_pf = fh
    t_pf2 = fh * RES.get("spring_scale", 1.0)
    pr("    %-8s %8.2f %14.3f %16.3f %16.3f %16s"
       % (n, vv, t_laf / t_need, t_pf / t_need, t_pf2 / t_need, "1.000"))
pr("\n    (each column is the torque that feedforward commands for a 1 deg steady angle, divided by")
pr("     the torque the plant actually needs.  1.000 is correct; >1 over-commands, <1 under-commands.)")
pr("\n    ⚠ THE LAF COLUMN IS OPTIMISTIC: it ignores the measured -0.30 m/s^2 offset that the fork")
pr("    subtracts from the demand before dividing by LAF (see v293_ident_i.py J1/I1).  With that")
pr("    offset the lat-accel feedforward under-delivers further at small demand, which is where the")
pr("    straight-line 80 %% delivery and the integrator's 38 %% share come from.")

with open(os.path.join(L.SCRATCH, "v293_ident_j.json"), "w") as fh:
    json.dump({k2: v2 for k2, v2 in RES.items()}, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_j.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_j.txt / .json")
