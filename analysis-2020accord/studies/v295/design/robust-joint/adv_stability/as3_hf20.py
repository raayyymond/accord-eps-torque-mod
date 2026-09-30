# -*- coding: utf-8 -*-
"""as3_hf20.py -- (b) the 20 Hz question against the ON-CAR record.
 1. my closed_poles vs the harness closed_loop_modes (second method) on the harness stress members
 2. the designer's stress-member zetas reproduced with my code
 3. the trim's damping sign at 8-30 Hz vs transport delay (V294 / A / V282)
 4. CALIBRATION: two-mass plants x delay on which V282's lane reproduces the measured 20 Hz de-damping
    (zeta_open >= 0.05 -> zeta_V282 in [0.010, 0.035] at 19-21.5 Hz); then V294 and A on exactly those plants."""
import os, sys, json, itertools, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/plant"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/design/harness"))
import advlib as A
import v294_plant as VP
import v295_harness as H

c294 = A.read_cells("V294"); cA = dict(c294); cA["b"] = 1106; c282 = A.read_cells("V282")
fam = VP.family()
hfam = H.family()


def pd(mbr, v, tau=None, f2=None, z2=None, r2=None):
    a = mbr.arrays_at(np.array([v]))
    return dict(J=float(a["J"][0]), b=float(a["b"][0]), k=float(a["k"][0]), tau_ms=(mbr.tau_ms if tau is None else tau),
                f2=(mbr.f2 if f2 is None else f2), zeta2=(mbr.zeta2 if z2 is None else z2), r2=(mbr.r2 if r2 is None else r2), w=3)


def flex(md, f0, tol=0.35):
    c = [m for m in md if abs(m[0] - f0) < tol * f0]
    return min(c, key=lambda t: t[1]) if c else (np.nan, np.nan)


# ---- 1 + 2: stress members, my code vs harness, V294 / A / open / V282
print("1-2. harness stress members: (f, zeta) of the flexible mode, MINE (exact ZOH) vs HARNESS (semi-implicit Euler)")
hb = H.Cells.v294(); hA = hb.replace(fb_b=1106, name="A"); h282 = H.Cells.v282()
for name in ("mode13", "mode20", "mode20_lo"):
    mbr = hfam[name]
    for v in (5.0, 12.0, 25.0):
        p = pd(mbr, v)
        pp = mbr.at(v)
        row = []
        for tag, c, hc in (("open", c294, hb), ("V294", c294, hb), ("A", cA, hA), ("V282", c282, h282)):
            md, rho = A.closed_poles(c, p, lane_on=(tag != "open"))
            mh, rh = H.closed_loop_modes(pp, hc, lane_on=(tag != "open"))
            fm = flex(md, mbr.f2); fh = flex(mh, mbr.f2)
            row.append("%s mine %.2f/%.4f harn %.2f/%.4f" % (tag, fm[0], fm[1], fh[0], fh[1]))
        print("  %-9s v%4.1f  " % (name, v) + " | ".join(row))

# ---- 3: damping sign of the trim vs frequency and delay
print("\n3. opposing torque per deg/s, damping component Re{T/om * e^{-j w tau}} (T per deg/s), by transport delay")
f = np.array([8.0, 10.0, 13.0, 16.0, 20.0, 25.0, 30.0])
for tag, c in (("V294", c294), ("A", cA), ("V282", c282)):
    for tau in (0, 2, 4, 6, 9, 12, 18):
        To = A.opposing_T_per_omega(c, f, extra_delay_ms=tau)
        print("  %-5s tau %2d ms: " % (tag, tau) + "  ".join("%g Hz %+.2f(%+.0f)" % (ff, t.real, np.degrees(np.angle(t))) for ff, t in zip(f, To)))
# frequency where the damping component flips sign, by delay
fg = np.linspace(2, 60, 5801)
for tau in (0, 2, 4, 6, 9, 12, 18):
    To = A.opposing_T_per_omega(cA, fg, extra_delay_ms=tau)
    i = np.flatnonzero(To.real < 0)
    print("  A: damping flips negative at %.1f Hz with tau %d ms (w/ 3 ms rate former + output lag in T/om)" % (fg[i[0]] if len(i) else np.nan, tau))

# ---- 4: calibration against V282's measured de-damping
print("\n4. calibration scan")
t0 = time.time()
cons = []
allc = 0
bases = ("nominal", "light_b", "b_lo", "b_hi", "J_lo", "J_hi")
for base, v, f2, z2, r2, tau in itertools.product(bases, (3.1, 11.9), (14, 16, 18, 20, 22, 24, 27, 30),
                                                  (0.01, 0.02, 0.03, 0.05, 0.08), (0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9),
                                                  (0, 1, 2, 3, 4, 6, 9, 12, 18)):
    allc += 1
    p = pd(fam[base], v, tau, f2, z2, r2)
    md0, _ = A.closed_poles(c294, p, lane_on=False)
    o = [m for m in md0 if m[0] > 6]
    if not o:
        continue
    fo, zo = min(o, key=lambda t: abs(t[0] - f2))
    if zo < 0.05:                      # the on-car open-loop bound zeta_open >= 0.05
        continue
    md2, rho2 = A.closed_poles(c282, p)
    if rho2 >= 1.0:
        continue
    f282, z282 = flex(md2, fo)
    if not (19.0 <= f282 <= 21.5 and 0.010 <= z282 <= 0.035):
        continue
    mdV, rhoV = A.closed_poles(c294, p)
    mdA, rhoA = A.closed_poles(cA, p)
    fV, zV = flex(mdV, fo); fA, zA = flex(mdA, fo)
    # least-damped mode of V294 / A anywhere 5-40 Hz (a DIFFERENT mode could be the weak one)
    wV = min([m for m in mdV if 5 < m[0] < 40], key=lambda t: t[1]); wA = min([m for m in mdA if 5 < m[0] < 40], key=lambda t: t[1])
    cons.append(dict(base=base, v=v, f2=f2, z2=z2, r2=r2, tau=tau, fo=fo, zo=zo, f282=f282, z282=z282, fV=fV, zV=zV, fA=fA, zA=zA,
                     wV=wV, wA=wA, rhoA=rhoA))
print("  scanned %d plants in %.0f s; CONSISTENT with V282's on-car 20 Hz (zeta_open >= 0.05, V282 zeta 0.010-0.035 at 19-21.5 Hz): %d" % (
    allc, time.time() - t0, len(cons)))
if cons:
    frac = lambda t: (t["zo"] - t["zA"]) / max(t["zo"] - t["z282"], 1e-9)
    print("  by delay: n, zeta_open range, V282, and A/open (worst), A de-damping as a fraction of V282's (worst), V294 same")
    for tau in (0, 1, 2, 3, 4, 6, 9, 12, 18):
        s = [t for t in cons if t["tau"] == tau]
        if not s:
            print("   tau %2d: none" % tau); continue
        w = min(s, key=lambda t: t["zA"] / t["zo"]); wf = max(s, key=frac)
        fracV = lambda t: (t["zo"] - t["zV"]) / max(t["zo"] - t["z282"], 1e-9)
        wv = max(s, key=fracV)
        print("   tau %2d: n %4d  zeta_open %.3f-%.3f | worst A/open %.3f (V294/open %.3f; zo %.3f zA %.4f; %s f2 %d z2 %.2f r2 %.2f v%.1f) | "
              "worst A frac %.3f (V294 %.3f) | worst V294 frac %.3f" % (
                  tau, len(s), min(t["zo"] for t in s), max(t["zo"] for t in s), w["zA"] / w["zo"], w["zV"] / w["zo"], w["zo"], w["zA"],
                  w["base"], w["f2"], w["z2"], w["r2"], w["v"], frac(wf), fracV(wf), fracV(wv)))
    print("  F-HF-1 hits (A zeta < 0.8 zeta_open OR A de-damping > 25 % of V282's):")
    hits = [t for t in cons if t["zA"] < 0.8 * t["zo"] or frac(t) > 0.25]
    print("   %d of %d consistent plants" % (len(hits), len(cons)))
    for t in sorted(hits, key=lambda t: t["zA"] / t["zo"])[:15]:
        print("     %-7s v%4.1f f2 %2d z2 %.2f r2 %.2f tau %2d | open %.2f/%.4f V282 %.2f/%.4f V294 %.4f A %.4f | A/open %.3f frac %.3f" % (
            t["base"], t["v"], t["f2"], t["z2"], t["r2"], t["tau"], t["fo"], t["zo"], t["f282"], t["z282"], t["zV"], t["zA"],
            t["zA"] / t["zo"], frac(t)))
    # weakest mode anywhere 5-40 Hz with A vs V294
    wwA = min(cons, key=lambda t: t["wA"][1]); wwV = min(cons, key=lambda t: t["wV"][1])
    print("  weakest 5-40 Hz mode over the consistent set: A %.2f Hz zeta %.4f (%s tau %d) ; V294 %.2f Hz zeta %.4f" % (
        wwA["wA"][0], wwA["wA"][1], wwA["base"], wwA["tau"], wwV["wV"][0], wwV["wV"][1]))
    print("  overall: A/open min %.3f median %.3f ; V294/open min %.3f median %.3f ; A/V294 min %.3f" % (
        min(t["zA"] / t["zo"] for t in cons), float(np.median([t["zA"] / t["zo"] for t in cons])),
        min(t["zV"] / t["zo"] for t in cons), float(np.median([t["zV"] / t["zo"] for t in cons])),
        min(t["zA"] / t["zV"] for t in cons)))
json.dump(cons, open(os.path.join(HERE, "as3_hf20.json"), "w"), default=float)
