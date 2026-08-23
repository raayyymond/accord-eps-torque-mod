r"""ROUTE `a6` -- Q1/Q2' PART 2.  THREE CORRECTIONS AND ONE ADDITION TO `ra6_dose.py`.

🛑 SELF-CORRECTION 1.  `ra6_dose.py`'s `alpha_at()` IS DEFECTIVE AND ITS "delivered multiplier"
   ROW MUST NOT BE USED.  The `b5`-duty-vs-alpha curve is **NOT MONOTONIC** -- it RISES to a
   maximum near alpha ~ 200 deg/s^2 and falls after -- because BOTH comparator operands grow with
   activity (`gp-0x6ae2` is |model|-proportional).  A first-crossing search therefore lands on the
   RISING branch for one build and the FALLING branch for another and returns nonsense
   (0.26-1.76 with CIs spanning 226).  **Only the FALLING branch carries the dose.**

🛑 SELF-CORRECTION 2.  The reconstruction in `ra6_dose.py` 3(A) used the POINT prediction, so its
   "duty >= 511 = 0.00000" is the duty of a NOISELESS reconstruction.  The calibration's own
   residual sd is 0.826 log units (x2.28).  This file redoes it with the **full predictive
   distribution** -- residuals resampled from r77's own empirical residuals.

⭐ ADDITION.  The one thing that needs no comparator and no transfer at all: **the distribution of
   the measured motor ACCELERATION itself**, engaged, across builds.  `gp-0x6b26 = -K*alpha`, so
   alpha is exactly what this term is supposed to remove.  If V106 works, a6's own alpha
   distribution should be smaller -- and that is a direct symptom measure, not a proxy.

Usage:  python ra6_dose2.py
"""
import os
import sys
import json

import math

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "analysis-2020accord"))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
FS = L.FS
CLAMP = 511.0
B5KEY = {'ra4': 'v104_b5', 'ra5': 'v105_b5', 'ra6': 'v106_b5'}
NAMES = {'ra4': 'V104 (x1.5)', 'ra5': 'V105 (x1.5)', 'ra6': 'V106 (x3.0)'}
OUT = {}


def load(tag):
    d = L.load(tag)
    e = np.asarray(d['cc_lat'], float) > 0.5
    v = (np.asarray(d['v_rear'], float) if 'v_rear' in d.files
         else 0.5 * (np.asarray(d['ws_rl'], float) + np.asarray(d['ws_rr'], float))) * KPH
    rf = np.asarray(d['rate_f'], float)
    a = np.abs(np.gradient(rf) * FS)
    k = int(round(0.05 * FS)) | 1
    a = np.convolve(a, np.ones(k) / k, mode='same')
    return d, e, v, np.abs(np.asarray(d['rate_c'], float)), np.abs(np.asarray(d['tq'], float)), a


def eps_of(e, min_s=2.5):
    idx = np.flatnonzero(np.diff(e.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(e)]))
    return [(int(a), int(c)) for a, c in zip(b[:-1], b[1:])
            if e[a] and (c - a) >= int(min_s * FS)]


# ================================================================== 1. matched-alpha contrast
print("=" * 124)
print("1.  ⭐⭐ THE DOSE PROOF -- `b5` DUTY AT MATCHED MEASURED ALPHA, ENGAGED, WITH EPISODE CIs.")
print("    This is the estimator that is immune to the closed-loop `K*alpha` invariance: at a")
print("    FIXED alpha the comparator's operand B is proportional to k.")
print("=" * 124)
AE = np.array([0, 30, 60, 120, 250, 500, 1000, 2000, 4000], float)
AL = ['<30', '30-60', '60-120', '120-250', '250-500', '500-1k', '1k-2k', '2k-4k']
DAT = {}
for tag in ('ra4', 'ra5', 'ra6'):
    d, e, v, rc, tq, a = load(tag)
    DAT[tag] = (np.asarray(d[B5KEY[tag]], float) > 0.5, a, e, v, rc, tq, eps_of(e))

print("%16s" % 'build' + "".join("%11s" % s for s in AL))
for tag in ('ra4', 'ra5', 'ra6'):
    b5, a, e, _, _, _, _ = DAT[tag]
    row = []
    for i in range(len(AL)):
        m = e & (a >= AE[i]) & (a < AE[i + 1])
        row.append(float(b5[m].mean()) if m.sum() >= 200 else np.nan)
    print("%16s" % NAMES[tag] + "".join("     --    " if not np.isfinite(x) else "%11.4f" % x
                                        for x in row))
    OUT.setdefault('duty_vs_alpha', {})[NAMES[tag]] = [float(x) for x in row]

print()
print("  ⭐ RATIO a6/a5 and a6/a4 AT MATCHED ALPHA, episode bootstrap (2000 draws).")
print("     A dose that arrived shows as a ratio BELOW 1 in EVERY bin.  The sign test across")
print("     bins is the headline: it needs no distributional assumption at all.")
print("%16s" % 'pair' + "".join("%11s" % s for s in AL) + "%14s" % 'sign test p')
for other in ('ra5', 'ra4'):
    pts, los, his, sgn = [], [], [], 0
    nb = 0
    for i in range(len(AL)):
        vals = []
        rg = np.random.default_rng(900 + i)
        ok = True
        for _ in range(2000):
            o = []
            for tg in ('ra6', other):
                b5, a, e, _, _, _, ep = DAT[tg]
                pick = rg.integers(0, len(ep), len(ep))
                idx = np.concatenate([np.arange(*ep[j]) for j in pick])
                m = (a[idx] >= AE[i]) & (a[idx] < AE[i + 1])
                o.append(b5[idx][m].mean() if m.sum() >= 100 else np.nan)
            vals.append(o[0] / o[1])
        vals = np.array(vals, float)
        if np.isfinite(vals).sum() < 200:
            pts.append(np.nan); los.append(np.nan); his.append(np.nan); ok = False
        else:
            pts.append(float(np.nanmedian(vals)))
            q = np.nanpercentile(vals, [2.5, 97.5])
            los.append(float(q[0])); his.append(float(q[1]))
        if ok:
            nb += 1
            sgn += (pts[-1] < 1.0)
    p = ((0.5 ** nb) * sum(math.comb(nb, j) for j in range(sgn, nb + 1))) if nb else float('nan')
    print("%16s" % ('a6/%s' % other)
          + "".join("     --    " if not np.isfinite(x) else "%11.3f" % x for x in pts)
          + "%14.4f" % p)
    print("%16s" % '  95 % CI'
          + "".join("     --    " if not np.isfinite(l) else "%11s" % ("%.2f-%.2f" % (l, h))
                    for l, h in zip(los, his)) + "   (%d/%d below 1)" % (sgn, nb))
    OUT.setdefault('matched_alpha_ratio', {})['a6/%s' % other] = dict(
        bins=AL, ratio=pts, lo=los, hi=his, n_below_1=int(sgn), n_bins=int(nb), sign_p=p)

# ================================================================== 2. the horizontal shift
print()
print("=" * 124)
print("2.  THE DELIVERED MULTIPLIER -- horizontal shift on the **FALLING BRANCH ONLY**.")
print("    (`ra6_dose.py`'s version searched both branches and is RETRACTED.)")
print("    Expected 2.00 if V105 ran x1.5 and V106 runs x3.0;  3.00 if the x1.5 was never live.")
print("=" * 124)


def falling_curve(b5, a, e, lo=200.0):
    """duty vs alpha on the falling branch, on a log-spaced grid; returns (centres, duties)."""
    m = e & (a >= lo)
    if m.sum() < 2000:
        return None
    q = np.exp(np.linspace(np.log(lo), np.log(np.percentile(a[m], 99.0)), 14))
    c, du = [], []
    for j in range(len(q) - 1):
        s = m & (a >= q[j]) & (a < q[j + 1])
        if s.sum() >= 150:
            c.append(np.sqrt(q[j] * q[j + 1]))
            du.append(float(b5[s].mean()))
    return (np.array(c), np.array(du)) if len(c) >= 4 else None


def shift(cA, dA, cB, dB):
    """How far RIGHT must B's curve move to sit on A's?  Median over A's duty levels that are
    inside B's range.  Returns the multiplier alpha_B/alpha_A (>1 means B needs LESS alpha)."""
    out = []
    for p in np.linspace(max(dA.min(), dB.min()) + 1e-6, min(dA.max(), dB.max()) - 1e-6, 25):
        xa = np.interp(-p, -dA[::-1], np.log(cA[::-1])) if dA[0] > dA[-1] else np.nan
        xb = np.interp(-p, -dB[::-1], np.log(cB[::-1])) if dB[0] > dB[-1] else np.nan
        if np.isfinite(xa) and np.isfinite(xb):
            out.append(np.exp(xa - xb))
    return float(np.median(out)) if out else np.nan


CUR = {}
for tag in ('ra4', 'ra5', 'ra6'):
    b5, a, e, _, _, _, ep = DAT[tag]
    CUR[tag] = falling_curve(b5, a, e)
    if CUR[tag]:
        print("  %-16s falling branch: " % NAMES[tag]
              + "  ".join("%.0f:%.3f" % (c, d) for c, d in zip(*CUR[tag])))
for other in ('ra5', 'ra4'):
    if not (CUR['ra6'] and CUR[other]):
        continue
    pt = shift(CUR[other][0], CUR[other][1], CUR['ra6'][0], CUR['ra6'][1])
    rg = np.random.default_rng(77)
    vals = []
    for _ in range(600):
        cc = {}
        for tg in ('ra6', other):
            b5, a, e, _, _, _, ep = DAT[tg]
            pick = rg.integers(0, len(ep), len(ep))
            idx = np.concatenate([np.arange(*ep[j]) for j in pick])
            eb = np.zeros(len(a), bool)
            eb[idx] = True
            cc[tg] = falling_curve(b5, a, eb)
        if cc['ra6'] and cc[other]:
            vals.append(shift(cc[other][0], cc[other][1], cc['ra6'][0], cc['ra6'][1]))
    vals = np.array(vals, float)
    q = np.nanpercentile(vals, [2.5, 97.5]) if np.isfinite(vals).sum() > 50 else [np.nan] * 2
    print("  ⭐ delivered multiplier a6 vs %s  =  **%.2fx**  [%.2f, %.2f]"
          % (NAMES[other], pt, q[0], q[1]))
    OUT.setdefault('multiplier', {})[NAMES[other]] = dict(point=float(pt),
                                                          ci=[float(q[0]), float(q[1])])

# ================================================================== 3. clamp, with residual
print()
print("=" * 124)
print("3.  Q2' -- THE CLAMP, WITH THE CALIBRATION'S OWN RESIDUAL SPREAD FOLDED IN.")
print("    Reconstruction: r77's measured alpha -> |gp-0x6b26| law (r77 ran x1.00 stock), x3.0,")
print("    with residuals RESAMPLED from r77's own empirical residuals -- so the duty below is a")
print("    PREDICTIVE duty, not a noiseless one.  🛑 Still a reconstruction, not a measurement.")
print("=" * 124)
d77 = L.load('r77')
mt = np.asarray(d77['ab_mt'], float)
abt = np.asarray(d77['ab_t1ab'], float)
t77 = np.asarray(d77['t'], float)
j = np.clip(np.searchsorted(abt, t77, side='right') - 1, 0, len(mt) - 1)
b77 = mt[j] * 8.0 / 5.0
e77 = np.asarray(d77['cc_lat'], float) > 0.5
rf = np.asarray(d77['rate_f'], float)
a77 = np.abs(np.gradient(rf) * FS)
kk = int(round(0.05 * FS)) | 1
a77 = np.convolve(a77, np.ones(kk) / kk, mode='same')
m = e77 & (b77 > 0) & (a77 > 0)
sl, ic = np.polyfit(np.log(a77[m]), np.log(b77[m]), 1)
res = np.log(b77[m]) - (sl * np.log(a77[m]) + ic)
print("  r77 law: log|b26| = %.4f*log(alpha) %+.4f;  residual sd %.3f  (x%.2f)"
      % (sl, ic, res.std(), np.exp(res.std())))
print("  ⊕ SANITY: applying the law to r77 itself (k=1) reproduces its own measured duty>=511 of"
      " %.5f -> predicted %.5f" % (float(np.mean(b77[e77] >= CLAMP)),
                                   float(np.mean(np.exp(sl * np.log(np.clip(a77[e77], 1e-6, None))
                                                        + ic + np.random.default_rng(3).choice(
                                                            res, e77.sum())) >= CLAMP))))
b5_6, a6, e6, v6, rc6, tq6, ep6 = DAT['ra6']
rg = np.random.default_rng(11)
NS = 12
pred = np.exp(sl * np.log(np.clip(a6, 1e-6, None))[None, :] + ic
              + rg.choice(res, (NS, len(a6)))) * 3.0
print("\n%16s %10s %10s %10s %14s %14s"
      % ('stratum', 'n eng', 'p50', 'p99', 'duty>=511', 'duty>=256'))
STRATA = [('engaged all', None), ('<8 km/h (S1)', (0, 8)), ('<16 km/h', (0, 16)),
          ('16-40', (16, 40)), ('40-95 (S3)', (40, 95)), ('S2c hard turn', 'S2c'),
          ('|rate|40-100', 'R40'), ('|rate|>=100', 'R100')]
for lbl, sp in STRATA:
    if sp is None:
        m6 = e6
    elif sp == 'S2c':
        m6 = e6 & (v6 < 20) & (tq6 >= 500) & (rc6 >= 15) & (rc6 < 40)
    elif sp == 'R40':
        m6 = e6 & (rc6 >= 40) & (rc6 < 100)
    elif sp == 'R100':
        m6 = e6 & (rc6 >= 100)
    else:
        m6 = e6 & (v6 >= sp[0]) & (v6 < sp[1])
    if m6.sum() < 100:
        continue
    P = pred[:, m6]
    print("%16s %10d %10.1f %10.1f %14.5f %14.5f"
          % (lbl, int(m6.sum()), np.percentile(P, 50), np.percentile(P, 99),
             float(np.mean(P >= CLAMP)), float(np.mean(P >= 256))))
    OUT.setdefault('clamp_predictive', {})[lbl] = dict(
        n=int(m6.sum()), p50=float(np.percentile(P, 50)), p99=float(np.percentile(P, 99)),
        duty511=float(np.mean(P >= CLAMP)), duty256=float(np.mean(P >= 256)))

# ================================================================== 4. alpha itself
print()
print("=" * 124)
print("4.  ⭐ THE ADDITION -- THE MEASURED MOTOR ACCELERATION ITSELF, ENGAGED, deg/s^2.")
print("    `gp-0x6b26 = -K*alpha`, so alpha is EXACTLY what this term removes.  No comparator,")
print("    no transfer, no reconstruction -- this is the 0x18F channel, differenced.")
print("=" * 124)
print("%16s %10s %9s %9s %9s %9s %9s" % ('build', 'n eng', 'p50', 'p90', 'p99', 'p99.9', 'max'))
for tag in ('ra4', 'ra5', 'ra6'):
    b5, a, e, v, rc, tq, ep = DAT[tag]
    x = a[e]
    print("%16s %10d %9.1f %9.1f %9.1f %9.1f %9.1f"
          % (NAMES[tag], len(x), *[np.percentile(x, p) for p in (50, 90, 99, 99.9)], x.max()))
    OUT.setdefault('alpha_engaged', {})[NAMES[tag]] = dict(
        n=int(len(x)), **{("p%g" % p): float(np.percentile(x, p))
                          for p in (50, 90, 99, 99.9)}, mx=float(x.max()))
print("\n  SPEED-MATCHED (engaged, alpha p90 by speed bin) -- removes the exposure confound:")
VE = [0, 8, 16, 25, 40, 60, 80, 1e9]
VL = ['<8', '8-16', '16-25', '25-40', '40-60', '60-80', '80+']
print("%16s" % 'build' + "".join("%11s" % s for s in VL))
for tag in ('ra4', 'ra5', 'ra6'):
    b5, a, e, v, rc, tq, ep = DAT[tag]
    row = []
    for i in range(len(VL)):
        m = e & (v >= VE[i]) & (v < VE[i + 1])
        row.append(float(np.percentile(a[m], 90)) if m.sum() >= 300 else np.nan)
    print("%16s" % NAMES[tag] + "".join("     --    " if not np.isfinite(x) else "%11.1f" % x
                                        for x in row))
    OUT.setdefault('alpha_by_speed_p90', {})[NAMES[tag]] = [float(x) for x in row]

json.dump(OUT, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 'analysis-2020accord', '_ra6_dose2.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_ra6_dose2.json")
