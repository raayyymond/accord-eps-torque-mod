# -*- coding: utf-8 -*-
"""a2_hf.py -- (b) the 13-25 Hz question against the ON-CAR record.
1. gain and phase of the lane x -> T (tap vs rate) at 13-25 Hz: V294 / b964 / V282 (V282 on-car: -69 deg, 1.90, GRINDING-DEEP 2026-09-03)
2. delay sweep 0..16 ms on the collocated stress modes: zeta open / V294 / b964 / V282, my exact-ZOH closed loop
3. calibration: at which total delay does the SAME model make V282 de-damp a zeta-0.05 20 Hz mode to the on-car 0.016?
   and what does b964 do there?
Output: a2_hf_out.txt"""
import os
import sys
from dataclasses import replace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import adv_lib as A  # noqa: E402
import v294_plant as VP  # noqa: E402

out = open(os.path.join(HERE, "a2_hf_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")
    out.flush()


V294 = A.read_cells("V294")
B964 = A.with_b(V294, 964)
V282 = A.read_cells("V282")
G3 = A.with_b(V294, 1701, "b1701(G3)")
fam = VP.family()
nom = fam["nominal"]

P("1. lane x -> T at 13-25 Hz: |T/x| T per x-count, phase of T re the wheel rate x (damping = 0 deg, kit convention)")
ff = np.array([7.0, 10.0, 13.0, 16.0, 20.0, 25.0])
for c in (V294, B964, G3, V282):
    H = -A.ctrl_frf(c, ff)          # T per x (x = -x_in)
    P("  %-10s" % c["name"], " ".join("%4.0fHz %.4f/%+.1f" % (fq, abs(h), np.degrees(np.angle(h))) for fq, h in zip(ff, H)))
H294, H964, H282 = (-A.ctrl_frf(c, ff) for c in (V294, B964, V282))
P("  ratio |b964|/|V282| :", np.round(np.abs(H964) / np.abs(H282), 4), " |V294|/|V282| :", np.round(np.abs(H294) / np.abs(H282), 4))
P("  Re (damping part) per x-count: V294", np.round(H294.real, 4), " b964", np.round(H964.real, 4), " V282", np.round(H282.real, 4))
P("  on-car (V280r2/V282 era, creep, 20 Hz): LKAS lane 1.90 per rate count at -69 deg, Re +0.68; r24 3.23 at +5 deg (GRINDING-DEEP s2)")

P()
P("2. delay sweep (tau = transport delay after the tap, ms; rate former w = 3 ms): flexible-mode zeta  open | V294 | b964 | V282")
cases = [("mode20", nom.with_mode20(20.0, 0.05, 0.2)), ("mode20_lo", nom.with_mode20(20.0, 0.02, 0.5)),
         ("mode16_lo", nom.with_mode20(16.5, 0.02, 0.5)), ("mode13", nom.with_mode20(13.0, 0.1, 0.2)),
         ("mode13_lo", nom.with_mode20(13.0, 0.03, 0.5)), ("lb_mode20_lo", fam["light_b"].with_mode20(20.0, 0.02, 0.5)),
         ("mode20_r08", nom.with_mode20(20.0, 0.05, 0.8))]


def flex(p, c, on, tau):
    Acl = A.closed_loop_A(p, c, lane_on=on, tau=tau)
    rho, md = A.modes_of(Acl)
    fl = [m for m in md if 8 < m[0] < 45]
    m = min(fl, key=lambda t: abs(t[0] - p.f2)) if fl else (np.nan, np.nan)
    return m, rho


table = {}
for nm, mb in cases:
    for v in (5.0, 12.0, 25.0):
        p = mb.at(v)
        line = []
        for tau in (0, 2, 4, 6, 8, 10, 12, 14, 16):
            r = [flex(p, c, on, tau) for c, on in ((V294, False), (V294, True), (B964, True), (V282, True))]
            table[(nm, v, tau)] = r
            line.append("t%2d %.3f|%.3f|%.3f|%.3f%s" % (tau, r[0][0][1], r[1][0][1], r[2][0][1], r[3][0][1],
                                                     "*" if r[3][1] >= 1 else ""))
        P("  %-12s %4.0f  " % (nm, v) + "  ".join(line))
P("  (* = V282 closed loop UNSTABLE in the model at that delay)")

P()
P("3. calibration against the ON-CAR record: V282 engaged zeta at 20 Hz = 0.016 [0.013, 0.022] (loop-open zeta >= 0.05)")
for nm, mb in cases[:3] + cases[5:]:
    for v in (5.0, 12.0):
        p = mb.at(v)
        taus = np.arange(0, 21)
        z282 = []
        for tau in taus:
            (m, rho) = flex(p, V282, True, int(tau))
            z282.append(m[1] if rho < 1 else -1.0)
        z282 = np.array(z282)
        hit = [int(t) for t, z in zip(taus, z282) if 0.010 <= z <= 0.025]
        if not hit:
            P("  %-12s %4.0f: V282 model zeta over tau 0..20 ms:" % (nm, v), np.round(z282, 3), " -> NO delay reproduces 0.016")
            continue
        for tau in hit[:3]:
            (mo, _), (m4, _), (mb9, _), (m2, _) = (flex(p, c, on, tau) for c, on in ((V294, False), (V294, True), (B964, True), (V282, True)))
            P("  %-12s %4.0f: tau %2d ms reproduces V282 zeta %.4f (open %.4f) -> V294 %.4f (d %+.4f)  b964 %.4f (d %+.4f)  "
              "b964-V294 %+.4f" % (nm, v, tau, m2[1], mo[1], m4[1], m4[1] - mo[1], mb9[1], mb9[1] - mo[1], mb9[1] - m4[1]))

P()
P("4. linear-in-gain extrapolation of the ON-CAR zeta-vs-Kp strata (MODE-NATURE-RECENSUS: zeta 0.033 at Kp 240-320,"
  " 0.030 at 320-450, 0.018 at 450-700; V282 alone 0.0164)")
# |(P+D)/x| at 20 Hz for Kp in each stratum (Kd 128 fixed), V282 fb lag
fq = np.array([20.0])
def pd_gain(kp):
    c = dict(V282)
    c["kp_y"] = (kp,) * 5
    h = -A.ctrl_frf(c, fq, part="P")[0]
    return abs(h), np.degrees(np.angle(h))
strata = [(280, 0.033), (385, 0.030), (575, 0.018)]
g = np.array([pd_gain(k)[0] for k, _ in strata])
ph = np.array([pd_gain(k)[1] for k, _ in strata])
zz = np.array([z for _, z in strata])
# damping-projected gain: Re part at the controller output relative to the trim's own phase
P("  |(P+D)/x| at 20 Hz by stratum Kp 280/385/575:", np.round(g, 2), "phase (pre-output-lag)", np.round(ph, 1))
cf = np.polyfit(g, zz, 1)
P("  fit zeta = %.4f + %.6f * |(P+D)/x|" % (cf[1], cf[0]), "-> zero-gain intercept %.4f (on-car loop-open bound >= 0.05)" % cf[1])
for c in (V294, B964, G3):
    gg = abs(A.ctrl_frf(c, fq, part="P")[0])
    P("  %-10s |P/x| %.3f -> zeta %.4f  (delta vs zero gain %+.4f)" % (c["name"], gg, np.polyval(cf, gg), np.polyval(cf, gg) - cf[1]))
out.close()
