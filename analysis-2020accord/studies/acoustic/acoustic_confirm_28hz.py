r"""CONFIRMATION LEG -- the four scan candidates, tested properly instead of quoted.

THE SCAN produced four cells meeting a deliberately loose rule (eng/man > 1.15 on >= 2 of three 6x
routes, and <= 1.0 on stock), out of **24 frequencies x 2 readings = 48 tests**:
      12 Hz direct | 28 Hz direct | 28 Hz AM | 34 Hz direct
Four hits from 48 loosely-thresholded tests is what CHANCE produces.  None of them is at 43-47 Hz,
so none is grind #2 or #3 as localised.  The only one where all THREE 6x routes exceed 1.0 with
stock below is **28 Hz AM** (6x 1.59 / 1.11 / 1.24, stock 0.97), so that is the one that gets a
real test.  The scan values were NOT speed-matched and carried NO interval.

WHAT A REAL TEST ADDS, all three of which the scan lacked:
   1. SPEED MATCHING by re-weighting to a common 2 km/h mixture.
   2. A BLOCK-BOOTSTRAP CI on the engaged/manual ratio.
   3. A PERMUTATION NULL on the whole decision rule -- shuffle the engaged/manual labels within
      route and re-run the identical scan, so the question becomes "how many candidates does this
      rule produce when there is nothing there?"  That is the only honest way to read 4-from-48.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import os
import sys
import json
import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import acoustic_lib as A                                            # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TAGS = ['r97', 'r85', 'r96', 'r9e', 'ra4', 'r95']
SIX = ['r96', 'r9e', 'ra4']
VLO, VHI = 0.0, 16.0
FSE = 500.0

D = {}
for t in TAGS:
    g = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s_grind.npz' % t))
    c = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s.npz' % t), allow_pickle=True)
    ct = c['t'].astype(float)
    ec = (c['cc_lat'].astype(float) > 0.5).astype(float)
    vc = c['v_rear'].astype(float) * 3.6
    te = g['t_env'].astype(float)
    D[t] = dict(env=g['env'].astype(float), env_f=g['env_f'], splice=g['splice'].astype(bool),
                eng=np.interp(te, ct, ec) > 0.5, v=np.interp(te, ct, vc))
BF = D['r97']['env_f']


def msk(t, engaged=True):
    d = D[t]
    m = (d['eng'] if engaged else ~d['eng']) & (d['v'] >= VLO) & (d['v'] < VHI) & ~d['splice']
    if not engaged:
        m = m & (d['v'] >= A.V_ROLL)
    return m


def runs(m, min_s=3.0):
    m = np.asarray(m, bool)
    i = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], i, [len(m)]))
    return [(int(b[k]), int(b[k + 1])) for k in range(len(b) - 1)
            if m[b[k]] and (b[k + 1] - b[k]) / FSE >= min_s]


def am_at(x, lo, hi, nper=1024):
    if len(x) < nper:
        return None
    f, p = signal.welch(x - x.mean(), fs=FSE, nperseg=nper, noverlap=nper // 2, detrend='linear')
    tgt = (f >= lo) & (f <= hi)
    bg = ((f >= 6) & (f <= 70)) & ~((f >= lo - 4) & (f <= hi + 4))
    if tgt.sum() < 2 or bg.sum() < 10:
        return None
    cf = np.polyfit(np.log(f[bg]), np.log(p[bg]), 1)
    return float(np.mean(p[tgt] / np.exp(np.polyval(cf, np.log(f[tgt])))))


def blocks(t, engaged, j, lo, hi, blk=6.0):
    """(AM excess, mean speed) per 6 s block -- the resampling unit and the speed-matching unit."""
    d = D[t]
    nb = int(blk * FSE)
    out = []
    for a, b in runs(msk(t, engaged), 3.0):
        for s in range(a, b - nb // 2, nb):
            e = min(s + nb, b)
            x = am_at(d['env'][s:e, j], lo, hi)
            if x is not None:
                out.append((x, float(d['v'][s:e].mean())))
    return out


def matched(be, bm, nboot=2000, seed=9):
    ed = np.arange(VLO, VHI + 2, 2.0)
    if len(be) < 4 or len(bm) < 4:
        return None

    def agg(bl):
        s = np.zeros(len(ed) - 1)
        c = np.zeros(len(ed) - 1)
        for x, v in bl:
            k = int(np.clip(np.digitize(v, ed) - 1, 0, len(ed) - 2))
            s[k] += x
            c[k] += 1
        return s, c
    se, ce = agg(be)
    sm, cm = agg(bm)
    ok = (ce >= 2) & (cm >= 2)
    if not ok.any():
        return None
    w = np.minimum(ce, cm) * ok
    w = w / w.sum()
    f = lambda s, c: float(np.sum(w * np.where(c > 0, s / np.maximum(c, 1), 0.0)))
    pt = f(se, ce) / max(f(sm, cm), 1e-300)
    rg = np.random.default_rng(seed)
    # 🛑 DEFECT FOUND AND FIXED.  The first version divided by `max(denominator, 1e-300)`.  With
    #    only 5-13 blocks per arm a resample can leave a WEIGHTED speed bin empty, the denominator
    #    collapses toward zero, and the ratio explodes -- the run printed upper CI bounds of ~1e300.
    #    Those intervals were an artefact of this line, not a property of the data.  A draw that
    #    fails to populate every weighted bin on BOTH arms is now DISCARDED, and the number of
    #    usable draws is reported so a thin arm is visible rather than hidden.
    bo = []
    for i in range(nboot):
        s1, c1 = agg([be[k] for k in rg.integers(0, len(be), len(be))])
        s2, c2 = agg([bm[k] for k in rg.integers(0, len(bm), len(bm))])
        if np.any(c1[ok] == 0) or np.any(c2[ok] == 0):
            continue
        d = f(s2, c2)
        if d <= 0:
            continue
        bo.append(f(s1, c1) / d)
    bo = np.array([x for x in bo if np.isfinite(x)])
    if len(bo) < nboot * 0.2:
        return dict(r=pt, lo=np.nan, hi=np.nan, ne=len(be), nm=len(bm), ndraw=len(bo))
    return dict(r=pt, lo=float(np.percentile(bo, 2.5)), hi=float(np.percentile(bo, 97.5)),
                ne=len(be), nm=len(bm), ndraw=len(bo))


print("=" * 122)
print("LEG 1 -- 28 Hz AM, SPEED-MATCHED, with a block-bootstrap CI, every carrier")
print("=" * 122)
LO, HI = 27.0, 29.0
OUT = {}
for j in range(len(BF)):
    print("\n  ---- carrier %g-%g Hz ----" % tuple(BF[j]))
    print("%-6s %-9s %8s %28s %10s %10s" %
          ('route', 'build', 'gain', 'ENG/MAN 28 Hz AM [95% CI]', 'n eng blk', 'n man blk'))
    for t in TAGS:
        r = matched(blocks(t, True, j, LO, HI), blocks(t, False, j, LO, HI))
        OUT.setdefault("%g-%g" % tuple(BF[j]), {})[t] = r if r is None else \
            dict(r=r['r'], lo=r['lo'], hi=r['hi'])
        if r is None:
            cell = '-'
        elif np.isfinite(r['lo']):
            cell = "%.2f [%.2f, %.2f]" % (r['r'], r['lo'], r['hi'])
        else:
            cell = "%.2f  CI VOID (%d draws)" % (r['r'], r['ndraw'])
        print("%-6s %-9s %8.0fx %28s %10s %10s"
              % (t, A.NAMES[t], A.GAIN[t], cell,
                 r['ne'] if r else '-', r['nm'] if r else '-'))

print()
print("=" * 122)
print("LEG 2 -- THE PERMUTATION NULL ON THE DECISION RULE ITSELF")
print("   Shuffle the engaged/manual labels WITHIN each route (block-wise, preserving speed and")
print("   block structure) and re-run the identical 48-test scan.  How many candidates does the")
print("   rule produce when there is nothing there?")
print("=" * 122)
GRID = np.arange(12, 60, 2.0)
JC = int(np.flatnonzero((BF[:, 0] == 300) & (BF[:, 1] == 3000))[0])

# pre-compute per-route block sets ONCE per frequency, then permute labels
rng = np.random.default_rng(77)
real_hits, null_counts = [], []
CACHE = {}
for f0 in GRID:
    for t in TAGS:
        CACHE[(t, f0)] = (blocks(t, True, JC, f0 - 1, f0 + 1),
                          blocks(t, False, JC, f0 - 1, f0 + 1))


def rule_hits(permute):
    n = 0
    for f0 in GRID:
        vals = {}
        for t in TAGS:
            be, bm = CACHE[(t, f0)]
            if permute:
                allb = be + bm
                idx = rng.permutation(len(allb))
                be = [allb[k] for k in idx[:len(be)]]
                bm = [allb[k] for k in idx[len(be):]]
            if len(be) < 4 or len(bm) < 4:
                vals[t] = np.nan
                continue
            vals[t] = np.mean([x for x, _ in be]) / max(np.mean([x for x, _ in bm]), 1e-12)
        s = vals.get('r97', np.nan)
        six = [vals.get(t, np.nan) for t in SIX]
        if not np.isfinite(s) or any(not np.isfinite(x) for x in six):
            continue
        if sum(x > 1.15 for x in six) >= 2 and s <= 1.0:
            n += 1
            if not permute:
                real_hits.append(f0)
    return n


nreal = rule_hits(False)
for _ in range(200):
    null_counts.append(rule_hits(True))
null_counts = np.array(null_counts)
print("  REAL: %d candidate frequencies out of %d tested (AM reading, 300-3000 Hz carrier): %s"
      % (nreal, len(GRID), real_hits))
print("  PERMUTED labels, 200 draws: median %d, 95th percentile %d, max %d"
      % (np.median(null_counts), np.percentile(null_counts, 95), null_counts.max()))
print("  p(null >= real) = %.3f" % float((null_counts >= nreal).mean()))
print()
if (null_counts >= nreal).mean() > 0.05:
    print("  ⇒ THE SCAN'S CANDIDATE COUNT IS INDISTINGUISHABLE FROM CHANCE.  None of the four")
    print("    candidates is evidence of anything, and they must not be quoted as leads.")
else:
    print("  ⇒ the scan produced more candidates than label-shuffling does; worth pursuing.")

json.dump({'leg1_28hz': OUT, 'real_hits': real_hits,
           'null_median': float(np.median(null_counts)),
           'p': float((null_counts >= nreal).mean())},
          open(os.path.join(A.HERE, '_scratch/out/_acoustic_confirm28.json'), 'w'), indent=1, default=float)
print("\n  wrote _scratch/out/_acoustic_confirm28.json")
