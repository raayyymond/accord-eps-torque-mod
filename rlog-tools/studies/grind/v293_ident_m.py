# -*- coding: utf-8 -*-
"""v293_ident_m.py -- THE V293 TABLES IN THE FORK'S PARAMETRISATION, the estimator adjudication, and
a REPLAY of route 70 through three feedforwards.  Subagent v293plant, 2026-09-13.  ANALYSIS ONLY.

THREE ESTIMATES OF a(v) EXIST IN THIS STUDY AND THEY DISAGREE.  Adjudicated here, per band:
  A  the JOINT BOOTSTRAP FIT, v293_ident_j.py: u = a*th + b*th' + F*sign(th') + u0 on 0.5 Hz
     low-passed clean data, 0.5 s override buffer, 2000-resample block bootstrap.  Has an EXPLICIT
     Coulomb term and CIs.  a = 0.00228 / 0.00764 / 0.01149 / 0.01539.
  B  the FREQUENCY-DOMAIN IV DC GAIN, v293_ident_f.py: 1/(deg per unit torque) from the coherence-
     weighted transfer estimate.  NO friction term.  a = 0.00345 / 0.01666 / 0.01815 / 0.01932.
  C  the same joint form as A but on the 2 s-buffer, stretch-based mask, v293_ident_f.py F2.
     a = 0.00168 / 0.01010 / 0.01245 / 0.01548.
VERDICT: B is systematically the largest because it has NO Coulomb term, so the friction is folded
into the spring -- and the fork applies friction SEPARATELY (SteerFriction), so using B would
double-count it.  B is rejected for a feedforward.  A and C agree to 8-30 % where both are well
determined, and A carries the CIs, so A is the primary and C is the check.  Where they disagree and
neither dominates, the CONSERVATIVE (smaller) value is taken, per the orchestrator's rule: an
under-holding feedforward is corrected by P and I, an over-holding one over-steers into low-speed turns.

THE REPLAY uses the MEASURED angle as every feedforward's input, not the desired angle, on purpose:
that isolates each feedforward's GAIN error from the loop's tracking error, which is the quantity
being decided.  In steady state the two inputs coincide anyway.
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
G_BP, G_V = [5.0, 12.5, 18.5, 28.5], [120.0, 95.0, 85.0, 70.0]
K_BP, K_V = [4.0, 8.0, 12.5, 18.5, 28.5], [0.17, 0.28, 0.35, 0.45, 0.50]
BANDS = [(1.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 99.0)]
BNAME = ["1-8", "8-15", "15-22", ">22"]
VMED = [4.93, 11.96, 18.94, 22.80]
# method A (joint bootstrap fit, v293_ident_j.py J1)
A_a = [0.00228, 0.00764, 0.01149, 0.01539]
A_a_ci = [(0.00089, 0.00657), (0.00617, 0.01063), (0.01007, 0.01329), (0.01475, 0.01809)]
A_b = [0.00180, 0.00366, 0.00409, 0.00489]
A_b_ci = [(-0.00067, 0.00235), (0.00231, 0.00444), (0.00168, 0.00606), (0.00339, 0.01297)]
A_F = [0.01201, 0.01187, 0.01121, 0.00979]
A_u0 = [0.00374, -0.00517, -0.00277, -0.00810]
B_a = [0.00345, 0.01666, 0.01815, 0.01932]
C_a = [0.00168, 0.01010, 0.01245, 0.01548]
C_b = [0.00002, 0.00400, 0.00270, 0.00568]

pr("=" * 110)
pr("V293 -- THE FORK TABLES, THE ESTIMATOR ADJUDICATION, AND A THREE-FEEDFORWARD REPLAY")
pr("=" * 110)

# ======================================================================================================
pr("\nM1. THE ADJUDICATION, band by band")
pr("    A = joint bootstrap fit (explicit Coulomb term, CIs)   B = frequency-domain IV DC gain (no")
pr("    Coulomb term)   C = the same joint form on the 2 s-buffer mask")
pr("\n    %-8s %7s %10s %10s %10s %10s %14s   %s"
   % ("band", "v", "A", "A CI lo", "A CI hi", "B", "C", "verdict"))
CHOSEN_a, WHY = [], []
for i in range(4):
    if i == 0:
        ch, why = min(A_a[i], C_a[i]), "CONSERVATIVE (smaller of A and C): A's b CI crosses zero, nothing is identified here"
    elif i == 1:
        ch, why = A_a[i], "A; C (0.01010) sits at A's upper CI, so A is not contradicted"
    else:
        ch, why = A_a[i], "A; C agrees to %.0f %%, B rejected (folds friction into the spring)" % (
            100 * abs(C_a[i] / A_a[i] - 1))
    CHOSEN_a.append(ch); WHY.append(why)
    pr("    %-8s %7.2f %10.5f %10.5f %10.5f %10.5f %14.5f   %s"
       % (BNAME[i], VMED[i], A_a[i], A_a_ci[i][0], A_a_ci[i][1], B_a[i], C_a[i], why))
pr("\n    chosen a(v): " + "  ".join("%s %.5f" % (BNAME[i], CHOSEN_a[i]) for i in range(4)))
# 🛑 THE CONSERVATIVE RULE APPLIES TO THE HOLD (a), NOT TO b.  Taking the smaller b in the 1-8 band
# (C gives 0.00002) sends G = 1/b to 17 800 and poisons every interpolated point below 12.5 m/s.
# b is therefore taken from A in every band, with the 1-8 value marked low confidence.
CHOSEN_b = list(A_b)
pr("    chosen b(v): " + "  ".join("%s %.5f" % (BNAME[i], CHOSEN_b[i]) for i in range(4)))
pr("    🛑 b IS TAKEN FROM A IN EVERY BAND, including 1-8.  The conservative rule applies to the")
pr("    HOLD, not to b: taking the smaller b at 1-8 (C gives 0.00002) would send G = 1/b to 17 800")
pr("    and poison every interpolated point below 12.5 m/s.  A's 1-8 b = 0.00180 has a CI that")
pr("    crosses zero, so that entry is LOW CONFIDENCE -- but it is finite and it sits below the")
pr("    trend extrapolated down from the higher bands (~0.003), which is the safe side for a")
pr("    move term.")
RES["chosen"] = dict(v=VMED, a=CHOSEN_a, b=CHOSEN_b, F=A_F, u0=A_u0)

# ======================================================================================================
pr("\n" + "=" * 110)
pr("M2. THE NEW TABLES, at the fork's own breakpoints.   G = 1/b,  K = a/b  (so hold = K/G = a).")
pr("    EXTRAPOLATION is marked BELIEF: the drive's engaged range is 2.5-26.6 m/s (p95 25.0).")
pr("=" * 110)
vv = np.array(VMED)
aa = np.array(CHOSEN_a)
bb = np.array(CHOSEN_b)


def interp(x, xp, fp):
    return float(np.interp(x, xp, fp)), ("EVIDENCE" if xp.min() <= x <= xp.max() else "BELIEF")


pr("\n    HONDA_ACCORD_EPS_G_V at G_BP = %s   (deg/s per unit torque)" % G_BP)
pr("    %-8s %12s %12s %10s   %s" % ("v", "current", "NEW", "ratio", "status"))
G_new = []
for i, x in enumerate(G_BP):
    b_, tag = interp(x, vv, bb)
    val = 1.0 / b_ if b_ > 1e-9 else np.nan
    G_new.append(val)
    pr("    %-8.1f %12.1f %12.1f %10.2f   %s" % (x, G_V[i], val, val / G_V[i], tag))
pr("\n    HONDA_ACCORD_EPS_K_V at K_BP = %s   (1/s)" % K_BP)
pr("    %-8s %12s %12s %10s   %s" % ("v", "current", "NEW", "ratio", "status"))
K_new = []
for i, x in enumerate(K_BP):
    a_, tag = interp(x, vv, aa)
    b_, _ = interp(x, vv, bb)
    val = a_ / b_ if b_ > 1e-9 else np.nan
    K_new.append(val)
    pr("    %-8.1f %12.2f %12.2f %10.2f   %s" % (x, K_V[i], val, val / K_V[i], tag))
pr("\n    and the HOLD they produce, K/G, against the current tables':")
pr("    %-8s %14s %14s %10s" % ("v", "current K/G", "NEW K/G", "ratio"))
for x in G_BP:
    cur = float(np.interp(x, K_BP, K_V)) / float(np.interp(x, G_BP, G_V))
    new = float(np.interp(x, K_BP, K_new)) / float(np.interp(x, G_BP, G_new))
    pr("    %-8.1f %14.5f %14.5f %10.2f" % (x, cur, new, new / cur))
pr("\n    🛑 THE POLE THESE TABLES IMPLY (k = 1.3-3.1 1/s, cornering at 0.20-0.50 Hz) IS THE WEAK")
pr("    PART: part B's flat torque->angle magnitude to 1.2 Hz puts it ABOVE 1.2 Hz instead, and the")
pr("    joint fit's own CI at 15-22 spans 1.92-7.38.  The HOLD term (K/G) is not affected, because it")
pr("    uses only the ratio.  If the pole matters to a later design, it needs its own experiment.")
RES["tables"] = dict(G_BP=G_BP, G_new=G_new, K_BP=K_BP, K_new=K_new)

# ======================================================================================================
pr("\n" + "=" * 110)
pr("M3. THE REPLAY -- route 70's measured angle through three feedforwards")
pr("    'needed' = the fitted u = a*th + b*th' + F*sign(th') + u0 with each band's own parameters.")
pr("    (i)   the NEW tables, rate gain 1.0")
pr("    (ii)  the OLD tables with SpringScale 3.3 / GainScale 1.0 / FFRateGain 0.3  (toggle-only)")
pr("    (iii) the flown else-branch with SteerLatAccel 5.4, on the measured lateral acceleration")
pr("    Each is scored with NO friction term and again with SteerFriction = 0.011 added, because the")
pr("    fork applies friction separately and it is the largest single term in 'needed'.")
pr("=" * 110)
mask = L.clean_mask(g, hands_off=True, min_v=1.0, buffer_s=0.5)
sos = signal.butter(4, 0.5, "lowpass", fs=L.FS, output="sos")
u_meas = -g["op_torque"]
th_raw = -g["ang"]
strets = L.stretches(mask, int(4 * L.FS))
TH = np.full(len(th_raw), np.nan); TD = np.full(len(th_raw), np.nan)
for (a0, b0) in strets:
    t_ = signal.sosfiltfilt(sos, th_raw[a0:b0])
    TH[a0:b0] = t_
    TD[a0:b0] = np.gradient(t_, DT)
ok = mask & np.isfinite(TH) & np.isfinite(g["la_act"]) & (np.abs(TD) > 0.3)
vg = g["v"]
K_new_i = np.interp(vg, K_BP, K_new)
G_new_i = np.interp(vg, G_BP, G_new)
K_old_i = np.interp(vg, K_BP, K_V)
G_old_i = np.interp(vg, G_BP, G_V)
ff_i = K_new_i * TH / G_new_i + 1.0 * TD / G_new_i
ff_ii = 3.3 * K_old_i * TH / G_old_i + 0.3 * TD / G_old_i
ff_iii = g["la_act"] / 5.4
ff_iii_off = (g["la_act"] - 0.30) / 5.4
need = np.full(len(TH), np.nan)
for i in range(4):
    lo, hi = BANDS[i]
    s = (vg >= lo) & (vg < hi)
    need[s] = (CHOSEN_a[i] * TH[s] + CHOSEN_b[i] * TD[s] + A_F[i] * np.sign(TD[s]) + A_u0[i])
FRIC = 0.011 * np.sign(TD)
pr("\n    %-8s %8s | %-26s %10s %10s | %-26s %10s %10s"
   % ("band", "n s", "feedforward (no friction)", "resid rms", "bias", "with SteerFriction 0.011",
      "resid rms", "bias"))
for i in range(4):
    lo, hi = BANDS[i]
    s = ok & (vg >= lo) & (vg < hi)
    if s.sum() < 300:
        pr("    %-8s %8.1f  (too little)" % (BNAME[i], s.sum() * DT)); continue
    for nm, ff in (("(i) new tables, rg 1.0", ff_i), ("(ii) old x3.3, rg 0.3", ff_ii),
                   ("(iii) else-branch LAF 5.4", ff_iii), ("(iii+) same, offset removed", ff_iii_off)):
        r0 = ff[s] - need[s]
        r1 = (ff[s] + FRIC[s]) - need[s]
        first = nm.startswith("(i) ")
        pr("    %-8s %8s | %-26s %10.5f %+10.5f | %10.5f %+10.5f"
           % (BNAME[i] if first else "", ("%.0f" % (s.sum() * DT)) if first else "",
              nm, np.sqrt(np.mean(r0 ** 2)), np.mean(r0),
              np.sqrt(np.mean(r1 ** 2)), np.mean(r1)))
        RES.setdefault("replay", {}).setdefault(BNAME[i], {})[nm] = dict(
            rms=float(np.sqrt(np.mean(r0 ** 2))), bias=float(np.mean(r0)),
            rms_fric=float(np.sqrt(np.mean(r1 ** 2))), bias_fric=float(np.mean(r1)))
    pr("")

pr("    THE HOLD OVER/UNDER-DELIVERY RATIO -- the steady-state part only, ff_hold / a, per band:")
pr("    %-8s %8s %16s %16s %16s" % ("band", "v", "(i) new tables", "(ii) old x3.3", "(iii) LAF 5.4"))
SR, WB = 16.88, 2.83
for i in range(4):
    v_ = VMED[i]
    h_i = float(np.interp(v_, K_BP, K_new)) / float(np.interp(v_, G_BP, G_new))
    h_ii = 3.3 * float(np.interp(v_, K_BP, K_V)) / float(np.interp(v_, G_BP, G_V))
    la_per_deg = np.radians(1.0) / (SR * WB) * v_ ** 2
    h_iii = la_per_deg / 5.4
    pr("    %-8s %8.2f %16.3f %16.3f %16.3f"
       % (BNAME[i], v_, h_i / CHOSEN_a[i], h_ii / CHOSEN_a[i], h_iii / CHOSEN_a[i]))
    RES.setdefault("hold_ratio", {})[BNAME[i]] = dict(new=h_i / CHOSEN_a[i], old33=h_ii / CHOSEN_a[i],
                                                      laf54=h_iii / CHOSEN_a[i])
pr("\n    1.000 is correct; above 1 over-holds (the operator's 'oversteer' into a turn), below 1")
pr("    under-holds (corrected by P and I, at the cost of tracking error and integrator share).")

with open(os.path.join(L.SCRATCH, "v293_ident_m.json"), "w") as fh:
    json.dump(RES, fh, indent=1, default=float)
with open(os.path.join(L.SCRATCH, "v293_ident_m.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT))
print("\n[written] v293_ident_m.txt / .json")
