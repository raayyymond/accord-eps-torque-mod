# -*- coding: utf-8 -*-
"""as2_inner.py -- (a) the inner acceleration loop, V294 vs A, on every family member x speed x delay x J x b corner,
plus two-mass scans.  Two methods: my frequency-domain return ratio (margins, Ms, min Re L) and my exact-ZOH state-space
eigenvalues (closed-loop pole damping).  Reports every case where A is less damped than V294 and the worst of each."""
import os, sys, json, itertools
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/plant"))
import advlib as A
import v294_plant as VP

c294 = A.read_cells("V294")
cA = dict(c294); cA["b"] = 1106
fam = VP.family()
F = np.logspace(np.log10(0.03), np.log10(499.0), 5000)
SPEEDS = (3.1, 8.0, 11.9, 17.0, 26.9)
TAUS = (0, 2, 3, 4, 6, 9, 12, 18)


def pdict(mbr, v, tau=None, Jx=1.0, bx=1.0, f2=0.0, zeta2=0.05, r2=0.2):
    a = mbr.arrays_at(np.array([v]))
    return dict(J=float(a["J"][0]) * Jx, b=float(a["b"][0]) * bx, k=float(a["k"][0]), tau_ms=(mbr.tau_ms if tau is None else tau),
                f2=f2, zeta2=zeta2, r2=r2, w=3)


def osc_modes(md, lo=0.05, hi=60.0):
    return [(f, z) for f, z in md if lo < f < hi]


def case(p):
    out = {}
    for tag, c in (("V294", c294), ("A", cA)):
        L = A.inner_L(c, p, F)
        mg = A.margins(F, L)
        md, rho = A.closed_poles(c, p)
        out[tag] = dict(mg=mg, modes=osc_modes(md), rho=rho, L13=float(np.max(np.abs(L[(F >= 1) & (F <= 3)]))),
                        L38=float(np.max(np.abs(L[(F >= 3) & (F <= 8)]))), Lhf=float(np.max(np.abs(L[(F >= 8) & (F <= 60)]))))
    md0, _ = A.closed_poles(c294, p, lane_on=False)
    out["open"] = dict(modes=osc_modes(md0))
    return out


def match(modes_a, modes_ref, f0, tol=0.4):
    """least-damped mode within +-tol*f0 of f0 in each list"""
    pick = lambda ms: min([m for m in ms if abs(m[0] - f0) <= tol * f0], key=lambda t: t[1], default=(np.nan, np.nan))
    return pick(modes_a), pick(modes_ref)


rows = []
worst = dict(GM=(np.inf, None), PM=(np.inf, None), Ms=(0, None), minRe=(np.inf, None), rho=(0, None))
less_damped = []
# ---- 1. rigid members: identified family + light_b + J and b corners, every speed, every delay
members = [k for k in fam]
for name in members:
    mbr = fam[name]
    for v in SPEEDS:
        for tau in TAUS:
            for Jx in ((1.0,) if name not in ("nominal", "light_b") else (0.5, 1.0, 1.5, 2.5)):
                for bx in ((1.0,) if name not in ("nominal", "light_b") else (1.0 / 1.8, 1.0, 1.5)):
                    p = pdict(mbr, v, tau, Jx, bx)
                    r = case(p)
                    tagp = "%s v%.1f tau%d Jx%.2f bx%.2f" % (name, v, tau, Jx, bx)
                    ra, rv = r["A"], r["V294"]
                    rows.append(dict(case=tagp, A_GM=ra["mg"]["GM"], V_GM=rv["mg"]["GM"], A_PM=ra["mg"]["PM"], V_PM=rv["mg"]["PM"],
                                     A_Ms=ra["mg"]["Ms"], V_Ms=rv["mg"]["Ms"], A_minRe=ra["mg"]["minReL"], A_rho=ra["rho"],
                                     A_L13=ra["L13"], V_L13=rv["L13"], A_Lhf=ra["Lhf"],
                                     A_modes=ra["modes"][:4], V_modes=rv["modes"][:4], open_modes=r["open"]["modes"][:3]))
                    for k, key, better in (("GM", "GM", min), ("PM", "PM", min), ("minRe", "minReL", min)):
                        val = ra["mg"][key]
                        if val < worst[k][0]:
                            worst[k] = (val, tagp)
                    if ra["mg"]["Ms"] > worst["Ms"][0]:
                        worst["Ms"] = (ra["mg"]["Ms"], tagp)
                    if ra["rho"] > worst["rho"][0]:
                        worst["rho"] = (ra["rho"], tagp)
                    # least damped oscillatory mode A vs V294 (every mode A has, matched by frequency)
                    for fA, zA in ra["modes"]:
                        zV = min([z for f, z in rv["modes"] if abs(f - fA) <= 0.4 * fA], default=np.nan)
                        if np.isfinite(zV) and zA < zV - 1e-3 and zA < 0.3:
                            less_damped.append((tagp, fA, zA, zV))
print("rigid cases:", len(rows))
print("WORST over rigid cases, candidate A:")
for k, (val, where) in worst.items():
    print("  %-6s %.4g  at %s" % (k, val, where))
# V294 worst for reference
wv = dict(GM=min((r["V_GM"], r["case"]) for r in rows), Ms=max((r["V_Ms"], r["case"]) for r in rows))
print("  V294 worst GM %.4g at %s ; worst Ms %.4g at %s" % (wv["GM"][0], wv["GM"][1], wv["Ms"][0], wv["Ms"][1]))
unstable = [r["case"] for r in rows if r["A_rho"] >= 1.0]
print("A unstable cases:", unstable[:10], "count", len(unstable))
# F-IN-2: where V294 GM >= 3, A GM < 2 or PM < 45 or Ms > 2
f2hits = [r for r in rows if (r["V_GM"] >= 3 and r["A_GM"] < 2) or (r["A_PM"] < 45) or r["A_Ms"] > 2.0]
print("F-IN-2 hits:", len(f2hits))
for r in f2hits[:12]:
    print("   ", r["case"], "A GM %.2f PM %.1f Ms %.3f | V294 GM %.2f PM %.1f Ms %.3f" % (r["A_GM"], r["A_PM"], r["A_Ms"], r["V_GM"], r["V_PM"], r["V_Ms"]))
# Ms by tau (worst over members) for A and V294
print("\nMs worst over members by delay (A / V294):")
for tau in TAUS:
    sel = [r for r in rows if (" tau%d " % tau) in r["case"]]
    ra = max(sel, key=lambda r: r["A_Ms"]); rv = max(sel, key=lambda r: r["V_Ms"])
    ga = min(sel, key=lambda r: r["A_GM"]); gv = min(sel, key=lambda r: r["V_GM"])
    print("  tau %2d ms: Ms A %.3f (%s) V294 %.3f | GM A %.2f (%s) V294 %.2f" % (tau, ra["A_Ms"], ra["case"], rv["V_Ms"], ga["A_GM"], ga["case"], gv["V_GM"]))
# less damped than V294
print("\nmodes where A is LESS damped than V294 (by > 0.001 in zeta, zeta_A < 0.3): %d cases" % len(less_damped))
ld = sorted(less_damped, key=lambda t: t[2])
for t in ld[:25]:
    print("   %-45s f %.2f Hz  zeta A %.4f  V294 %.4f  ratio %.3f" % (t[0], t[1], t[2], t[3], t[2] / t[3]))
# worst ratio
if ld:
    wr = min(ld, key=lambda t: t[2] / t[3])
    print("   worst ratio: %s f %.2f zeta A %.4f V294 %.4f ratio %.3f" % (wr[0], wr[1], wr[2], wr[3], wr[2] / wr[3]))

# ---- 2. two-mass scan: f2 x zeta2 x r2 x base member x speed x delay
tm = []
for base in ("nominal", "light_b", "J_lo", "b_lo"):
    mbr = fam[base]
    for v, f2, z2, r2, tau in itertools.product((3.1, 11.9, 26.9), (8, 10, 13, 16, 20, 25, 30, 40, 60), (0.02, 0.05, 0.1),
                                                (0.2, 0.5, 0.8), (2, 6, 9, 18)):
        p = pdict(mbr, v, tau, f2=f2, zeta2=z2, r2=r2)
        mdA, rhoA = A.closed_poles(cA, p)
        mdV, rhoV = A.closed_poles(c294, p)
        md0, _ = A.closed_poles(c294, p, lane_on=False)
        # the flexible mode: the open-loop pole closest to f2*sqrt(1/(1-r2)) (motor locked -> wheel-side resonance scale)
        fo = [m for m in md0 if m[0] > 4.0]
        if not fo:
            continue
        fflex, zo = min(fo, key=lambda t: abs(t[0] - f2))     # free-free mode sqrt(K/mu) = f2 (collocated poles)
        mA = min([m for m in mdA if abs(m[0] - fflex) < 0.35 * fflex], key=lambda t: t[1], default=(np.nan, np.nan))
        mV = min([m for m in mdV if abs(m[0] - fflex) < 0.35 * fflex], key=lambda t: t[1], default=(np.nan, np.nan))
        tm.append(dict(base=base, v=v, f2=f2, z2=z2, r2=r2, tau=tau, f_open=fflex, z_open=zo, fA=mA[0], zA=mA[1],
                       fV=mV[0], zV=mV[1], rhoA=rhoA, rhoV=rhoV))
print("\ntwo-mass cases:", len(tm))
print("unstable A:", sum(1 for t in tm if t["rhoA"] >= 1), " unstable V294:", sum(1 for t in tm if t["rhoV"] >= 1))
ratio = lambda t: t["zA"] / min(t["zV"], t["z_open"])
tm_ok = [t for t in tm if np.isfinite(t["zA"]) and np.isfinite(t["zV"])]
tm_sorted = sorted(tm_ok, key=ratio)
print("worst zeta_A / min(zeta_V294, zeta_open) (F-IN-3 rule: < 0.8 AND zeta_A < 0.10):")
for t in tm_sorted[:20]:
    print("   %-8s v%4.1f f2 %2d z2 %.2f r2 %.1f tau %2d | flex %.2f Hz z_open %.4f | V294 %.4f | A %.4f | A/min %.3f  A/V294 %.3f" % (
        t["base"], t["v"], t["f2"], t["z2"], t["r2"], t["tau"], t["f_open"], t["z_open"], t["zV"], t["zA"], ratio(t), t["zA"] / t["zV"]))
fin3 = [t for t in tm_ok if ratio(t) < 0.8 and t["zA"] < 0.10]
print("F-IN-3 hits (two-mass):", len(fin3))
for tau in (2, 6, 9, 18):
    s = [t for t in fin3 if t["tau"] == tau]
    print("  tau %2d: %d hits" % (tau, len(s)))
    for t in sorted(s, key=ratio)[:8]:
        print("     %-8s v%4.1f f2 %2d z2 %.2f r2 %.1f | flex %.2f z_open %.4f V294 %.4f A %.4f  A/min %.3f" % (
            t["base"], t["v"], t["f2"], t["z2"], t["r2"], t["f_open"], t["z_open"], t["zV"], t["zA"], ratio(t)))
# rigid-case F-IN-2 by tau
for tau in TAUS:
    s = [r for r in rows if (" tau%d " % tau) in r["case"] and ((r["V_GM"] >= 3 and r["A_GM"] < 2) or r["A_PM"] < 45 or r["A_Ms"] > 2.0)]
    print("F-IN-2 rigid hits at tau %2d: %d  %s" % (tau, len(s), [r["case"] for r in s][:6]))
# by delay: the worst A/V294 ratio and worst A/open
for tau in (2, 6, 9, 18):
    s = [t for t in tm_ok if t["tau"] == tau]
    w1 = min(s, key=lambda t: t["zA"] / t["zV"]); w2 = min(s, key=lambda t: t["zA"] / t["z_open"])
    print("  tau %2d: worst A/V294 %.3f (%s f2 %d z2 %.2f r2 %.1f v%.1f) ; worst A/open %.3f (V294/open %.3f) (%s f2 %d z2 %.2f r2 %.1f v%.1f)" % (
        tau, w1["zA"] / w1["zV"], w1["base"], w1["f2"], w1["z2"], w1["r2"], w1["v"], w2["zA"] / w2["z_open"], w2["zV"] / w2["z_open"],
        w2["base"], w2["f2"], w2["z2"], w2["r2"], w2["v"]))
json.dump(dict(rows=rows, twomass=tm), open(os.path.join(HERE, "as2_inner.json"), "w"), default=float)
