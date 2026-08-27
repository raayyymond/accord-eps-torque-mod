r"""ROUTE `a6` -- Q1/Q2' PART 3.  ONE BUG FIX, ONE MISSING NULL, ONE STRONGER SANITY CHECK.

🛑 SELF-CORRECTION 3.  `studies/ra6/ra6_dose2.py` section 2 returned **1.02x** for the delivered multiplier and
   that number is WRONG -- a `np.interp` misuse, not a property of the data.  `np.interp` requires
   its `xp` to be INCREASING; the code passed `-dA[::-1]`, which for a decreasing duty curve is
   DECREASING.  Both builds got the same wrong treatment, so the error cancelled to ~1.  Read off
   the printed curves by hand and the shift is obvious: V106 has duty 0.268 at alpha 220, and
   V105 does not fall to 0.268 until alpha ~ 640.  **`studies/ra6/ra6_dose2.py` section 2 is RETRACTED and
   replaced by section 1 here.**

⭐ ADDITION 1.  A WITHIN-DRIVE SPLIT-HALF NULL ON THE ALPHA STATISTIC.  `studies/ra6/ra6_dose2.py` section 4
   reported a 3.45x drop in engaged alpha p90 and a 7-of-7 speed-matched sweep, but quoted NO
   null.  On this corpus that is exactly the error that withdrew two headlines last session.

⭐ ADDITION 2.  A REAL SANITY CHECK ON THE CLAMP LAW.  `studies/ra6/ra6_dose2.py` "verified" the law by
   reproducing a duty of 0.00000 with a prediction of 0.00000 -- two zeros agreeing is not a
   check.  Here the law is asked to reproduce r77's measured p50/p90/p99 and its `duty >= 256`,
   and is then applied to **r78 (V91, x1.5)** as a HELD-OUT route at the correct k.

Usage:  python studies/ra6/ra6_dose3.py
"""
import os
import sys
import json

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis-2020accord"))
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
    return d, e, v, a


def eps_of(e, min_s=2.5):
    idx = np.flatnonzero(np.diff(e.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(e)]))
    return [(int(x), int(y)) for x, y in zip(b[:-1], b[1:])
            if e[x] and (y - x) >= int(min_s * FS)]


DAT = {}
for tag in ('ra4', 'ra5', 'ra6'):
    d, e, v, a = load(tag)
    DAT[tag] = dict(b5=np.asarray(d[B5KEY[tag]], float) > 0.5, a=a, e=e, v=v, ep=eps_of(e))

# ================================================================== 1. multiplier, FIXED
print("=" * 124)
print("1.  ⭐⭐ THE DELIVERED MULTIPLIER -- horizontal shift of the `b5` duty-vs-alpha curve on")
print("    its FALLING branch, with `np.interp` used correctly this time.")
print("    Expected 2.00 if V105 really ran x1.5 and V106 runs x3.0.")
print("    A value near 3.00 would mean the x1.5 was NEVER IN FORCE (Q7 / open item #6).")
print("=" * 124)


def falling_curve(b5, a, e, lo=200.0, nq=14):
    m = e & (a >= lo)
    if m.sum() < 2000:
        return None
    q = np.exp(np.linspace(np.log(lo), np.log(np.percentile(a[m], 99.0)), nq))
    c, du = [], []
    for j in range(len(q) - 1):
        s = m & (a >= q[j]) & (a < q[j + 1])
        if s.sum() >= 150:
            c.append(np.sqrt(q[j] * q[j + 1]))
            du.append(float(b5[s].mean()))
    c, du = np.array(c), np.array(du)
    # enforce monotone-decreasing by isotonic-from-the-right (the curve IS monotone in theory;
    # tiny bin-noise reversals otherwise break the inverse interpolation)
    du = np.minimum.accumulate(du)
    return (c, du) if len(c) >= 5 else None


def shift(cA, dA, cB, dB):
    """alpha_A(p) / alpha_B(p), median over the overlapping duty range.
    Both curves are DECREASING in alpha, so the inverse needs xp = duty ASCENDING."""
    lo, hi = max(dA.min(), dB.min()), min(dA.max(), dB.max())
    if not (hi > lo):
        return np.nan
    out = []
    for p in np.linspace(lo + 1e-9, hi - 1e-9, 25):
        xa = np.interp(p, dA[::-1], np.log(cA[::-1]))
        xb = np.interp(p, dB[::-1], np.log(cB[::-1]))
        out.append(np.exp(xa - xb))
    return float(np.median(out))


CUR = {t: falling_curve(DAT[t]['b5'], DAT[t]['a'], DAT[t]['e']) for t in DAT}
for t in ('ra4', 'ra5', 'ra6'):
    if CUR[t]:
        print("  %-16s " % NAMES[t] + "  ".join("%.0f:%.3f" % (c, d) for c, d in zip(*CUR[t])))
for other in ('ra5', 'ra4'):
    if not (CUR['ra6'] and CUR[other]):
        continue
    pt = shift(CUR[other][0], CUR[other][1], CUR['ra6'][0], CUR['ra6'][1])
    rg = np.random.default_rng(77)
    vals = []
    for _ in range(500):
        cc = {}
        for tg in ('ra6', other):
            D = DAT[tg]
            pick = rg.integers(0, len(D['ep']), len(D['ep']))
            eb = np.zeros(len(D['a']), bool)
            for j in pick:
                eb[D['ep'][j][0]:D['ep'][j][1]] = True
            cc[tg] = falling_curve(D['b5'], D['a'], eb)
        if cc['ra6'] and cc[other]:
            vals.append(shift(cc[other][0], cc[other][1], cc['ra6'][0], cc['ra6'][1]))
    vals = np.array(vals, float)
    q = np.nanpercentile(vals, [2.5, 97.5]) if np.isfinite(vals).sum() > 50 else [np.nan] * 2
    print("  ⭐ delivered multiplier, a6 vs %-14s = **%.2fx**  [%.2f, %.2f]   (n boot %d)"
          % (NAMES[other], pt, q[0], q[1], int(np.isfinite(vals).sum())))
    OUT.setdefault('multiplier', {})[NAMES[other]] = dict(point=float(pt),
                                                          ci=[float(q[0]), float(q[1])])
print("  ⚠ CAVEAT that travels with this number: the comparator's OTHER operand `gp-0x6ae2` is")
print("    |model|-proportional, so it is not literally constant across two different drives.")
print("    The 8/8 matched-alpha ratio in `studies/ra6/ra6_dose2.py` section 1 is the ROBUST result; this")
print("    multiplier is the QUANTITATIVE one and carries that extra assumption.  [BELIEF]")

# ================================================================== 2. alpha + its null
print()
print("=" * 124)
print("2.  ⭐ THE MOTOR ACCELERATION ITSELF -- **AND THE WITHIN-DRIVE NULL THAT `studies/ra6/ra6_dose2.py`")
print("    OWED IT.**  `gp-0x6b26 = -K*alpha`, so alpha is exactly what this term removes.")
print("    The null is a split-half-by-episode ratio of the SAME statistic inside route a6.")
print("=" * 124)
VE = [0, 8, 16, 25, 40, 60, 80, 1e9]
VL = ['<8', '8-16', '16-25', '25-40', '40-60', '60-80', '80+']


def p90_by_speed(D, eb=None):
    e = D['e'] if eb is None else eb
    out = []
    for i in range(len(VL)):
        m = e & (D['v'] >= VE[i]) & (D['v'] < VE[i + 1])
        out.append(float(np.percentile(D['a'][m], 90)) if m.sum() >= 300 else np.nan)
    return np.array(out)


print("%16s" % 'build' + "".join("%10s" % s for s in VL))
BASE = {}
for t in ('ra4', 'ra5', 'ra6'):
    BASE[t] = p90_by_speed(DAT[t])
    print("%16s" % NAMES[t] + "".join("    --    " if not np.isfinite(x) else "%10.1f" % x
                                      for x in BASE[t]))
print()
print("  a6/a5 and a6/a4 ratios, and route a6's OWN split-half null for the same statistic:")
D6 = DAT['ra6']
rg = np.random.default_rng(2026)
nullr = []
for _ in range(1000):
    perm = rg.permutation(len(D6['ep']))
    h = len(D6['ep']) // 2
    ma = np.zeros(len(D6['a']), bool)
    mb = np.zeros(len(D6['a']), bool)
    for j in perm[:h]:
        ma[D6['ep'][j][0]:D6['ep'][j][1]] = True
    for j in perm[h:]:
        mb[D6['ep'][j][0]:D6['ep'][j][1]] = True
    nullr.append(p90_by_speed(D6, ma) / p90_by_speed(D6, mb))
nullr = np.array(nullr, float)
nlo = np.nanpercentile(nullr, 2.5, axis=0)
nhi = np.nanpercentile(nullr, 97.5, axis=0)
print("%16s" % 'a6/a5' + "".join("    --    " if not np.isfinite(x) else "%10.3f" % x
                                 for x in BASE['ra6'] / BASE['ra5']))
print("%16s" % 'a6/a4' + "".join("    --    " if not np.isfinite(x) else "%10.3f" % x
                                 for x in BASE['ra6'] / BASE['ra4']))
print("%16s" % 'a6 null lo' + "".join("    --    " if not np.isfinite(x) else "%10.3f" % x
                                      for x in nlo))
print("%16s" % 'a6 null hi' + "".join("    --    " if not np.isfinite(x) else "%10.3f" % x
                                      for x in nhi))
cl5 = [bool(np.isfinite(r) and np.isfinite(l) and (r < l or r > h))
       for r, l, h in zip(BASE['ra6'] / BASE['ra5'], nlo, nhi)]
cl4 = [bool(np.isfinite(r) and np.isfinite(l) and (r < l or r > h))
       for r, l, h in zip(BASE['ra6'] / BASE['ra4'], nlo, nhi)]
print("%16s" % 'a6/a5 clears?' + "".join("%10s" % ("YES" if c else "no") for c in cl5))
print("%16s" % 'a6/a4 clears?' + "".join("%10s" % ("YES" if c else "no") for c in cl4))
OUT['alpha_p90'] = dict(bins=VL, **{NAMES[t]: [float(x) for x in BASE[t]] for t in BASE},
                        null_lo=[float(x) for x in nlo], null_hi=[float(x) for x in nhi],
                        a6_over_a5=[float(x) for x in BASE['ra6'] / BASE['ra5']],
                        a6_over_a4=[float(x) for x in BASE['ra6'] / BASE['ra4']],
                        a5_clears=cl5, a4_clears=cl4)

# ================================================================== 3. clamp law, checked
print()
print("=" * 124)
print("3.  THE CLAMP LAW, CHECKED PROPERLY -- fitted on r77 (x1.00 stock), then asked to")
print("    reproduce r77's OWN percentiles, then applied HELD-OUT to r78 (V91, x1.50).")
print("=" * 124)


def wire_b26(tag, scale=8.0 / 5.0):
    d = L.load(tag)
    mt = np.asarray(d['ab_mt'], float)
    abt = np.asarray(d['ab_t1ab'], float)
    t = np.asarray(d['t'], float)
    j = np.clip(np.searchsorted(abt, t, side='right') - 1, 0, len(mt) - 1)
    e = np.asarray(d['cc_lat'], float) > 0.5
    rf = np.asarray(d['rate_f'], float)
    a = np.abs(np.gradient(rf) * FS)
    k = int(round(0.05 * FS)) | 1
    return mt[j] * scale, e, np.convolve(a, np.ones(k) / k, mode='same')


b77, e77, a77 = wire_b26('r77')
b78, e78, a78 = wire_b26('r78')
m = e77 & (b77 > 0) & (a77 > 0)
sl, ic = np.polyfit(np.log(a77[m]), np.log(b77[m]), 1)
res = np.log(b77[m]) - (sl * np.log(a77[m]) + ic)
rg = np.random.default_rng(5)


def predict(a, k, ns=12):
    return np.exp(sl * np.log(np.clip(a, 1e-6, None))[None, :] + ic
                  + rg.choice(res, (ns, len(a)))) * k


print("%22s %9s %9s %9s %9s %12s %12s"
      % ('', 'p50', 'p90', 'p99', 'p99.9', 'duty>=256', 'duty>=511'))
for lbl, bb, ee, aa, k in (('r77 MEASURED (x1.0)', b77, e77, a77, 1.0),
                           ('r77 predicted', None, e77, a77, 1.0),
                           ('r78 MEASURED (x1.5)', b78, e78, a78, 1.5),
                           ('r78 predicted HELD-OUT', None, e78, a78, 1.5)):
    x = bb[ee] if bb is not None else predict(aa[ee], k)
    print("%22s %9.1f %9.1f %9.1f %9.1f %12.5f %12.5f"
          % (lbl, *[np.percentile(x, p) for p in (50, 90, 99, 99.9)],
             float(np.mean(x >= 256)), float(np.mean(x >= CLAMP))))
    OUT.setdefault('law_check', {})[lbl] = dict(
        duty256=float(np.mean(x >= 256)), duty511=float(np.mean(x >= CLAMP)),
        **{("p%g" % p): float(np.percentile(x, p)) for p in (50, 90, 99, 99.9)})
print("  🛑 READ THE ROWS AS A PAIR.  If the predicted row over- or under-states the measured")
print("     tail, the a6 clamp duties in `studies/ra6/ra6_dose2.py` section 3 inherit that bias in the same")
print("     direction, and the HEADROOM statement must be adjusted accordingly.")

print()
print("  ⭐ HEADROOM: what dose multiple k (relative to STOCK) first puts route a6's own engaged")
print("     distribution at a given clamp duty?  V106 = k 3.0.  This is the V107 sizing table.")
D6 = DAT['ra6']
print("%18s" % 'stratum' + "".join("%9s" % ("k=%g" % k) for k in (2, 3, 4, 5, 6, 8, 12)))
for lbl, mm in (('engaged all', D6['e']),
                ('<16 km/h', D6['e'] & (D6['v'] < 16)),
                ('40-95 km/h', D6['e'] & (D6['v'] >= 40) & (D6['v'] < 95)),
                ('alpha top decile', D6['e'] & (D6['a'] >= np.percentile(D6['a'][D6['e']], 90)))):
    if mm.sum() < 200:
        continue
    P1 = predict(D6['a'][mm], 1.0)
    row = [float(np.mean(P1 * k >= CLAMP)) for k in (2, 3, 4, 5, 6, 8, 12)]
    print("%18s" % lbl + "".join("%9.5f" % r for r in row))
    OUT.setdefault('headroom', {})[lbl] = {("k=%g" % k): r
                                           for k, r in zip((2, 3, 4, 5, 6, 8, 12), row)}

json.dump(OUT, open(os.path.join(ROOT, 'analysis-2020accord', '_scratch/out/_ra6_dose3.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_scratch/out/_ra6_dose3.json")
