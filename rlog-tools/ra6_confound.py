r"""ROUTE `a6` -- 🛑 THE CONFOUND THAT COULD SINK THE HEADLINE, TESTED BEFORE THE HEADLINE IS SENT.

=================================================================================================
THE THREAT
=================================================================================================
Route a6's engaged LKAS demand is **far smaller** than a5's:
        |e4tq| engaged     p50    p90     p99
        a5 (V105)          263   3341    4096
        a6 (V106)          134    791    4096
a 4.2x difference at p90.  The 21-27 Hz mode is **command-driven** -- that is the whole post-V38
arc (`accord-vibration-requires-lkas-engaged`: 9,200x less power with LKAS off;
`reference-accord-vibration-needs-applied-torque`).  So **"a6's 18-30 Hz band collapsed" is
equally consistent with "V106 damped it" and with "openpilot simply did not push as hard."**

⇒ **NOTHING ABOUT V106 MAY BE CALLED A FIX UNTIL THIS IS CUT AWAY.**

=================================================================================================
THE TEST
=================================================================================================
Re-run the band statistics in cells of **(speed regime) x (ABSOLUTE |e4tq| bin)** -- absolute, not
route-relative, so a cell means the same command on both drives.  Report:
  * 18-30 Hz RMS per cell, a6 vs a5 vs a4;
  * the PROMINENCE of the strongest 15-35 Hz line per cell -- a within-spectrum, level-invariant
    quantity that a demand difference cannot manufacture;
  * the per-cell window counts, so an underpowered cell is visible rather than silently averaged.

⭐ PROMINENCE IS THE KEY COLUMN.  Less command gives a SMALLER mode, not a LESS PEAKY one: a
   lightly-damped resonance driven at 1/4 the amplitude still stands the same number of dB above
   its own local background.  Killing the resonance flattens it.  **A prominence collapse at
   MATCHED command is not reproducible by an excitation difference.**

Usage:  python ra6_confound.py
"""
import os
import sys
import json

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
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
NPER = int(round(4 * FS))
FB = np.fft.rfftfreq(NPER, 1 / FS)
WIN = np.hanning(NPER + 1)[:NPER]
UU = (WIN ** 2).sum()
DF = FB[1] - FB[0]
TAGS = ('r97', 'ra4', 'ra5', 'ra6')
NAMES = {'r97': 'STOCK 1x', 'ra4': 'V104 6x', 'ra5': 'V105 NOTCH', 'ra6': 'V106 6b26x3'}
OUT = {}


def wins(tag):
    """Per-window spectrum + per-window covariates + a 30 s block id, ENGAGED only."""
    d = L.load(tag)
    e = np.asarray(d['cc_lat'], float) > 0.5
    v = np.asarray(d['v_rear'], float) * KPH
    x = np.asarray(d['rate_f'], float)
    dem = np.abs(np.asarray(d['e4tq'], float))
    rc = np.abs(np.asarray(d['rate_c'], float))
    idx = np.flatnonzero(np.diff(e.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(e)]))
    P, V, D, R, B = [], [], [], [], []
    for a, c in zip(b[:-1], b[1:]):
        if not (e[a] and (c - a) >= NPER):
            continue
        for s in range(a, c - NPER + 1, NPER // 2):
            xs = x[s:s + NPER] - x[s:s + NPER].mean()
            X = np.fft.rfft(xs * WIN)
            P.append((X.conj() * X).real / (FS * UU))
            V.append(float(np.mean(v[s:s + NPER])))
            D.append(float(np.percentile(np.abs(dem[s:s + NPER]), 90)))
            R.append(float(np.mean(rc[s:s + NPER])))
            B.append(int(s // int(30 * FS)))
    return (np.array(P), np.array(V), np.array(D), np.array(R), np.array(B))


W = {t: wins(t) for t in TAGS}


def rms(S, lo=18.0, hi=30.0):
    k = (FB >= lo) & (FB < hi)
    return float(np.sqrt(S[k].sum() * DF))


def prom(S, lo=15.0, hi=35.0):
    k = np.flatnonzero((FB >= lo) & (FB <= hi))
    best = (np.nan, 0.0)
    for j in k:
        w = (FB >= FB[j] - 1.0) & (FB <= FB[j] + 1.0)
        if S[j] != S[w].max():
            continue
        bg = np.median(S[(FB >= FB[j] - 3) & (FB <= FB[j] + 3)])
        pr = float(S[j] / bg) if bg > 0 else np.nan
        if np.isfinite(pr) and pr > best[1]:
            best = (float(FB[j]), pr)
    return best


VE = [(0, 16), (16, 40), (40, 95)]
VL = ['<16', '16-40', '40-95']
DE = [(200, 700), (700, 1600), (1600, 4200)]
DL = ['200-700', '700-1.6k', '1.6k-4.2k']

print("=" * 124)
print("MATCHED-COMMAND CELLS.  Each cell is (speed band) x (ABSOLUTE window-p90 |e4tq| band),")
print("so a cell means THE SAME COMMAND on every route.  n = windows in the cell.")
print("=" * 124)
for vi, vl in enumerate(VL):
    for di, dl in enumerate(DL):
        rows = []
        for t in TAGS:
            P, V, D, R, B = W[t]
            m = ((V >= VE[vi][0]) & (V < VE[vi][1]) & (D >= DE[di][0]) & (D < DE[di][1]))
            if m.sum() < 5:
                rows.append((t, int(m.sum()), None, None, None))
                continue
            S = P[m].mean(0)
            f0, pr = prom(S)
            rows.append((t, int(m.sum()), rms(S), f0, pr))
        if all(r[2] is None for r in rows):
            continue
        print("\n  speed %-7s   demand %-10s" % (vl, dl))
        print("%14s %7s %12s %10s %12s" % ('build', 'n win', '18-30 RMS', 'line Hz', 'PROMINENCE'))
        for t, n, r, f0, pr in rows:
            if r is None:
                print("%14s %7d   -- too few windows --" % (NAMES[t], n))
                continue
            print("%14s %7d %12.4f %10.2f %12.2f" % (NAMES[t], n, r, f0, pr))
            OUT.setdefault('cells', {}).setdefault("%s|%s" % (vl, dl), {})[NAMES[t]] = dict(
                n=n, rms=r, line_hz=f0, prominence=pr)
        d6 = dict((t, r) for t, n, r, f0, pr in rows)
        p6 = dict((t, pr) for t, n, r, f0, pr in rows)
        if d6.get('ra6') and d6.get('ra5'):
            print("      a6/a5  RMS %.3f   PROMINENCE %.3f"
                  % (d6['ra6'] / d6['ra5'], p6['ra6'] / p6['ra5']))
        if d6.get('ra6') and d6.get('ra4'):
            print("      a6/a4  RMS %.3f   PROMINENCE %.3f"
                  % (d6['ra6'] / d6['ra4'], p6['ra6'] / p6['ra4']))

# ---------------------------------------------------------------- pooled, demand-standardised
print()
print("=" * 124)
print("POOLED BUT DEMAND-STANDARDISED: the a6/a5 ratio computed per cell and then combined as a")
print("weighted GEOMETRIC MEAN (weights = the smaller of the two cells' window counts), with a")
print("30 s contiguous-BLOCK bootstrap.  ⚠ Blocks, not episodes -- a6 has only 7 engaged runs.")
print("=" * 124)


def cellwise(tagA, tagB, stat):
    num, den = [], []
    for vi in range(len(VL)):
        for di in range(len(DL)):
            out = {}
            for t in (tagA, tagB):
                P, V, D, R, B = W[t]
                m = ((V >= VE[vi][0]) & (V < VE[vi][1]) & (D >= DE[di][0]) & (D < DE[di][1]))
                out[t] = (P[m].mean(0), int(m.sum())) if m.sum() >= 5 else None
            if out[tagA] and out[tagB]:
                a_ = stat(out[tagA][0])
                b_ = stat(out[tagB][0])
                if a_ > 0 and b_ > 0:
                    num.append(np.log(a_ / b_))
                    den.append(min(out[tagA][1], out[tagB][1]))
    if not num:
        return np.nan, 0
    return float(np.exp(np.average(num, weights=den))), len(num)


for stat, nm in ((rms, '18-30 RMS'), (lambda S: prom(S)[1], 'PROMINENCE')):
    for other in ('ra5', 'ra4', 'r97'):
        pt, nc = cellwise('ra6', other, stat)
        # within-a6 split-half null on the SAME cellwise statistic
        P, V, D, R, B = W['ra6']
        ub = np.unique(B)
        rg = np.random.default_rng(1234)
        nl = []
        for _ in range(400):
            pm = rg.permutation(ub)
            h = len(ub) // 2
            mA = np.isin(B, pm[:h])
            mB = np.isin(B, pm[h:])
            num, den = [], []
            for vi in range(len(VL)):
                for di in range(len(DL)):
                    c = ((V >= VE[vi][0]) & (V < VE[vi][1]) & (D >= DE[di][0]) & (D < DE[di][1]))
                    if (c & mA).sum() >= 5 and (c & mB).sum() >= 5:
                        a_ = stat(P[c & mA].mean(0))
                        b_ = stat(P[c & mB].mean(0))
                        if a_ > 0 and b_ > 0:
                            num.append(np.log(a_ / b_))
                            den.append(min((c & mA).sum(), (c & mB).sum()))
            if num:
                nl.append(np.exp(np.average(num, weights=den)))
        q = np.percentile(nl, [2.5, 97.5]) if len(nl) > 50 else [np.nan] * 2
        cl = np.isfinite(q[0]) and not (q[0] <= pt <= q[1])
        print("  %-12s  a6 / %-12s = %.3f  (%d matched cells)   a6 split-half null [%.3f, %.3f]"
              "  =>  %s" % (nm, NAMES[other], pt, nc, q[0], q[1], "CLEARS" if cl else "inside"))
        OUT.setdefault('standardised', {}).setdefault(nm, {})[NAMES[other]] = dict(
            ratio=float(pt), n_cells=int(nc), null=[float(q[0]), float(q[1])], clears=bool(cl))

json.dump(OUT, open(os.path.join(ROOT, 'analysis-2020accord', '_ra6_confound.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_ra6_confound.json")
