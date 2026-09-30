# -*- coding: utf-8 -*-
"""as5b_lowspeed.py -- follow-up of as5: the lateral-accel error (0.15-2.4 Hz, the bands report's J metric) ROSE with A
at 0-10 m/s under lp on every member, and a 0.59 Hz wheel-rate line on light_b chunk 0 rose +3.1 dB.  Decompose:
 (1) J_err split 0.15-0.5 / 0.5-1 / 1-2.4 Hz per band, V294 vs A (CRN, lp and full), nominal / light_b / b_lo / J_hi2
 (2) the chunks behind the 0.59 Hz line: wheel-rate and la error PSD at 0.3-1 Hz, V294 vs A
 (3) the linear outer loop: |S| (error / plan) and |T| (act / plan) at 0.2-1.5 Hz, V294 vs A, light_b and nominal,
     3.1 / 5 / 8 m/s (my outer_L; plan -> act through the fork's setpoint path = complementary sensitivity)."""
import os, sys, json
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/design/harness"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/plant"))
import v295_harness as H
import advlib as A
import v294_plant as VP

base = H.Cells.v294(); cand = base.replace(fb_b=1106, name="A_b1106")
fam = H.family()
MEM = ["nominal", "light_b", "b_lo", "J_hi2"]
chunks = H.route_chunks()
nC = len(chunks)
R = {}
for dist in ("lp", "full"):
    for tag, c in (("V294", base), ("A", cand)):
        R[(dist, tag)] = H.simulate([c], [fam[m] for m in MEM], chunks, H.SimOpts(mode="B", dist=dist, seed=0))


def bp(x, lo, hi):
    b, a = signal.butter(2, [lo / 50.0, hi / 50.0], btype="band")
    return signal.filtfilt(b, a, x)


print("(1) lat-accel error (plan - act) rms by sub-band, per speed band: V294 -> A (ratio)")
for dist in ("lp", "full"):
    for mi, m in enumerate(MEM):
        line = []
        for bn, lo, hi in H.BANDS[:3]:
            acc = {k: [[], []] for k in ("a", "b", "c")}
            for k in range(nC):
                j = mi * nC + k
                n = R[(dist, "V294")]["lens"][j]
                v = R[(dist, "V294")]["v"][j, :n]
                mk = (v >= lo) & (v < hi)
                mk[:100] = False; mk[-100:] = False
                if mk.sum() < 100:
                    continue
                for ti, tag in enumerate(("V294", "A")):
                    Rr = R[(dist, tag)]
                    e = Rr["la_plan"][j, :n] - Rr["la_act"][j, :n]
                    for key, (f1, f2) in (("a", (0.15, 0.5)), ("b", (0.5, 1.0)), ("c", (1.0, 2.4))):
                        acc[key][ti].append(bp(e, f1, f2)[mk])
            if not acc["a"][0]:
                continue
            s = []
            for key in ("a", "b", "c"):
                v0 = np.sqrt(np.mean(np.concatenate(acc[key][0]) ** 2)); v1 = np.sqrt(np.mean(np.concatenate(acc[key][1]) ** 2))
                s.append("%.4f->%.4f(x%.2f)" % (v0, v1, v1 / v0))
            line.append("%s: 0.15-0.5 %s  0.5-1 %s  1-2.4 %s" % (bn, *s))
        print("  %-4s %-8s %s" % (dist, m, " | ".join(line)))

print("\n(2) the chunks behind the 0.59 Hz line (light_b, lp): wheel-rate PSD peak and la-error PSD at 0.4-0.8 Hz")
mi = MEM.index("light_b")
for k in range(nC):
    j = mi * nC + k
    RV, RA = R[("lp", "V294")], R[("lp", "A")]
    n = RV["lens"][j]
    v = float(np.mean(RV["v"][j, :n]))
    if v > 12:
        continue
    out = []
    for Rr in (RV, RA):
        f, P = signal.welch(Rr["rate18"][j, 50:n], fs=100.0, nperseg=min(512, n - 50))
        e = Rr["la_plan"][j, :n] - Rr["la_act"][j, :n]
        f2, Pe = signal.welch(e[50:] - e[50:].mean(), fs=100.0, nperseg=min(512, n - 50))
        band = (f >= 0.4) & (f <= 0.8)
        out.append((float(np.sqrt(np.sum(P[band]) * (f[1] - f[0]))), float(np.sqrt(np.sum(Pe[band]) * (f2[1] - f2[0])))))
    fp, Pp = signal.welch(RV["la_plan"][j, 50:n], fs=100.0, nperseg=min(512, n - 50))
    bandp = (fp >= 0.4) & (fp <= 0.8)
    print("  chunk %2d v %5.1f  plan 0.4-0.8 Hz rms %.3f | rate 0.4-0.8 Hz %.2f -> %.2f deg/s (x%.2f) | la err 0.4-0.8 Hz %.3f -> %.3f (x%.2f)" % (
        k, v, float(np.sqrt(np.sum(Pp[bandp]) * (fp[1] - fp[0]))), out[0][0], out[1][0], out[1][0] / max(out[0][0], 1e-9), out[0][1], out[1][1],
        out[1][1] / max(out[0][1], 1e-9)))

print("\n(3) linear outer loop: sensitivity |S| = |1/(1+L)| and |T| = |L/(1+L)| at 0.2..1.5 Hz, V294 -> A")
sys.path.insert(0, HERE)
import as4_outer_lib as OL
c294 = A.read_cells("V294"); cA = dict(c294); cA["b"] = 1106
vfam = VP.family()
f = np.array([0.2, 0.3, 0.45, 0.6, 0.8, 1.0, 1.5])
for name in ("nominal", "light_b", "b_lo", "J_hi2"):
    for v in (3.1, 5.0, 8.0, 11.9):
        a = vfam[name].arrays_at(np.array([v]))
        p = dict(J=float(a["J"][0]), b=float(a["b"][0]), k=float(a["k"][0]), tau_ms=vfam[name].tau_ms, w=3)
        LV = OL.outer_L(c294, p, v, f); LA = OL.outer_L(cA, p, v, f)
        sV, sA = np.abs(1 / (1 + LV)), np.abs(1 / (1 + LA))
        tV, tA = np.abs(LV / (1 + LV)), np.abs(LA / (1 + LA))
        print("  %-8s v%4.1f |S| %s -> %s | |T| %s -> %s" % (name, v, np.round(sV, 2), np.round(sA, 2), np.round(tV, 2), np.round(tA, 2)))
