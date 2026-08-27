r"""ROUTE `a6` -- Q3 FINAL: THE PEAK LOCATION **CONDITIONED ON LKAS COMMAND**.

🛑 SELF-CORRECTION 6.  `studies/ra6/ra6_peak.py`'s pooled low-speed argmax for V106 (17.98 Hz, "the mode moved
   DOWN") IS MISLEADING and must not be quoted on its own.  Route a6's engaged command
   distribution is ~4x smaller than a5's at p90 (|e4tq| p90 791 vs 3341), so the pooled a6 average
   is dominated by windows in which openpilot was barely steering and NO mode exists.  The argmax
   of that average is the argmax of a floor.

   `studies/ra6/ra6_confound.py`'s matched cells show what conditioning does.  In the best-powered low-speed
   cell -- <16 km/h, |e4tq| 1.6k-4.2k, HIS grind-#1 scenario at real command, 38 a6 windows:
        STOCK  21.98 Hz prom 1.81 | V104 22.23 prom 6.89 | V105 20.48 prom 3.42 | V106 28.22 prom 2.08
   **The line is at 28.22 Hz on V106 against 20.48 on V105 -- UP 7.7 Hz.**  That is the operator's
   *"notably increased in frequency"*, and it only appears once the command is held fixed.
   ⇒ This is `accord-averaged-spectrum-needs-matched-speed-distributions` applied to the DEMAND
     axis instead of the speed axis, and it bites exactly the same way.

This file re-does the peak with CIs inside the high-command mask, and adds the two controls that
decide whether a shifted argmax is real: a **BAND-EDGE SWEEP** (does the peak move when the search
band moves?) and the **per-window presence census** (is it in many windows or one loud one?).

Usage:  python studies/ra6/ra6_peak2.py
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
NPER = int(round(4 * FS))
FB = np.fft.rfftfreq(NPER, 1 / FS)
WIN = np.hanning(NPER + 1)[:NPER]
UU = (WIN ** 2).sum()
DF = FB[1] - FB[0]
TAGS = ('r97', 'ra4', 'ra5', 'ra6')
NAMES = {'r97': 'STOCK 1x', 'ra4': 'V104 6x', 'ra5': 'V105 NOTCH', 'ra6': 'V106 6b26x3'}
DEMLO = 1600.0                 # the operator's "max LKAS demand" arm, absolute counts
OUT = {}


def wins(tag):
    d = L.load(tag)
    e = np.asarray(d['cc_lat'], float) > 0.5
    v = np.asarray(d['v_rear'], float) * KPH
    x = np.asarray(d['rate_f'], float)
    dem = np.abs(np.asarray(d['e4tq'], float))
    idx = np.flatnonzero(np.diff(e.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(e)]))
    P, V, D, B = [], [], [], []
    for a, c in zip(b[:-1], b[1:]):
        if not (e[a] and (c - a) >= NPER):
            continue
        for s in range(a, c - NPER + 1, NPER // 2):
            xs = x[s:s + NPER] - x[s:s + NPER].mean()
            X = np.fft.rfft(xs * WIN)
            P.append((X.conj() * X).real / (FS * UU))
            V.append(float(np.mean(v[s:s + NPER])))
            D.append(float(np.percentile(dem[s:s + NPER], 90)))
            B.append(int(s // int(30 * FS)))
    return np.array(P), np.array(V), np.array(D), np.array(B)


W = {t: wins(t) for t in TAGS}
REG = [('<16 km/h  (grind #1)', 0, 16), ('16-40 km/h', 16, 40), ('40-95 km/h (grind #3)', 40, 95)]

print("=" * 124)
print("1.  ⭐⭐ PEAK LOCATION 15-35 Hz, ENGAGED **AND |e4tq| >= %g** (his 'max LKAS demand' arm)."
      % DEMLO)
print("    Block bootstrap over contiguous 30 s blocks (route a6 has only 7 engaged runs, so an")
print("    episode bootstrap has 7 units; blocks are contiguous and >> the 4 s window).")
print("=" * 124)
for lbl, vlo, vhi in REG:
    print("\n  %s" % lbl)
    print("%14s %7s %7s %10s %22s %12s %12s"
          % ('build', 'n win', 'blocks', 'peak Hz', 'peak 95 % CI', 'PROMINENCE', '18-30 RMS'))
    for t in TAGS:
        P, V, D, B = W[t]
        m = (V >= vlo) & (V < vhi) & (D >= DEMLO)
        if m.sum() < 8:
            print("%14s %7d   -- too few windows --" % (NAMES[t], m.sum()))
            continue
        Pm, Bm = P[m], B[m]
        ub = np.unique(Bm)
        k = (FB >= 15) & (FB <= 35)
        ff = FB[k]

        def stats(S):
            j = int(np.argmax(S[k]))
            f0 = float(ff[j])
            bg = np.median(S[(FB >= f0 - 3) & (FB <= f0 + 3)])
            kk = (FB >= 18) & (FB < 30)
            return f0, (float(S[k][j] / bg) if bg > 0 else np.nan), \
                float(np.sqrt(S[kk].sum() * DF))
        f0, pr, rr = stats(Pm.mean(0))
        rg = np.random.default_rng(31415)
        bp = []
        for _ in range(3000):
            pick = rg.choice(ub, len(ub))
            sel = np.concatenate([np.flatnonzero(Bm == j) for j in pick])
            bp.append(stats(Pm[sel].mean(0))[0])
        q = np.percentile(bp, [2.5, 97.5])
        print("%14s %7d %7d %10.2f %22s %12.2f %12.4f"
              % (NAMES[t], int(m.sum()), len(ub), f0, "[%.2f, %.2f]" % (q[0], q[1]), pr, rr))
        OUT.setdefault('peak_highdemand', {}).setdefault(lbl, {})[NAMES[t]] = dict(
            nwin=int(m.sum()), blocks=int(len(ub)), peak=f0,
            ci=[float(q[0]), float(q[1])], prominence=float(pr), rms=float(rr))
    # paired shift a6 - a5
    for other in ('ra5', 'ra4'):
        Pa, Va, Da, Ba = W['ra6']
        Pb, Vb, Db, Bb = W[other]
        ma = (Va >= vlo) & (Va < vhi) & (Da >= DEMLO)
        mb = (Vb >= vlo) & (Vb < vhi) & (Db >= DEMLO)
        if ma.sum() < 8 or mb.sum() < 8:
            continue
        k = (FB >= 15) & (FB <= 35)
        ff = FB[k]
        rg = np.random.default_rng(2718)
        dd = []
        ua, ub2 = np.unique(Ba[ma]), np.unique(Bb[mb])
        Pa_, Ba_ = Pa[ma], Ba[ma]
        Pb_, Bb_ = Pb[mb], Bb[mb]
        for _ in range(3000):
            sa = np.concatenate([np.flatnonzero(Ba_ == j) for j in rg.choice(ua, len(ua))])
            sb = np.concatenate([np.flatnonzero(Bb_ == j) for j in rg.choice(ub2, len(ub2))])
            dd.append(ff[int(np.argmax(Pa_[sa].mean(0)[k]))]
                      - ff[int(np.argmax(Pb_[sb].mean(0)[k]))])
        q = np.percentile(dd, [2.5, 97.5])
        print("     peak SHIFT a6 - %-12s %+7.2f Hz  [%+.2f, %+.2f]"
              % (NAMES[other], np.median(dd), q[0], q[1]))
        OUT.setdefault('shift_highdemand', {}).setdefault(lbl, {})['a6-%s' % other] = dict(
            shift=float(np.median(dd)), ci=[float(q[0]), float(q[1])])

print()
print("=" * 124)
print("2.  🛑 CONTROL A -- THE BAND-EDGE SWEEP.  If the argmax follows the search band, there is")
print("    no line and the number is an artefact.  A real mode does not move.")
print("=" * 124)
BANDS = [(15, 35), (18, 30), (15, 45), (20, 34), (12, 40)]
for lbl, vlo, vhi in REG:
    print("\n  %s   (engaged, |e4tq| >= %g)" % (lbl, DEMLO))
    print("%14s" % 'build' + "".join("%12s" % ("%g-%g" % b) for b in BANDS))
    for t in TAGS:
        P, V, D, B = W[t]
        m = (V >= vlo) & (V < vhi) & (D >= DEMLO)
        if m.sum() < 8:
            continue
        S = P[m].mean(0)
        row = []
        for lo, hi in BANDS:
            kk = (FB >= lo) & (FB <= hi)
            row.append(float(FB[kk][int(np.argmax(S[kk]))]))
        print("%14s" % NAMES[t] + "".join("%12.2f" % x for x in row))
        OUT.setdefault('bandsweep', {}).setdefault(lbl, {})[NAMES[t]] = row

print()
print("=" * 124)
print("3.  🛑 CONTROL B -- THE PER-WINDOW PRESENCE CENSUS.  A route-wide line is carried by MANY")
print("    windows.  Share of windows whose own 15-35 Hz argmax lands within +-1.5 Hz of the")
print("    pooled peak, and the MEDIAN per-window argmax (robust to one loud episode).")
print("=" * 124)
print("%22s %14s %10s %12s %14s %14s"
      % ('regime', 'build', 'n win', 'pooled pk', 'median win pk', 'share +-1.5 Hz'))
for lbl, vlo, vhi in REG:
    for t in TAGS:
        P, V, D, B = W[t]
        m = (V >= vlo) & (V < vhi) & (D >= DEMLO)
        if m.sum() < 8:
            continue
        k = (FB >= 15) & (FB <= 35)
        ff = FB[k]
        S = P[m].mean(0)
        pk = float(ff[int(np.argmax(S[k]))])
        wp = ff[np.argmax(P[m][:, k], axis=1)]
        print("%22s %14s %10d %12.2f %14.2f %14.3f"
              % (lbl, NAMES[t], int(m.sum()), pk, float(np.median(wp)),
                 float(np.mean(np.abs(wp - pk) <= 1.5))))
        OUT.setdefault('census', {}).setdefault(lbl, {})[NAMES[t]] = dict(
            nwin=int(m.sum()), pooled_peak=pk, median_window_peak=float(np.median(wp)),
            share_within_1p5=float(np.mean(np.abs(wp - pk) <= 1.5)))

json.dump(OUT, open(os.path.join(ROOT, 'analysis-2020accord', '_scratch/out/_ra6_peak2.json'), 'w'),
          indent=1, default=float)
print("\nwrote analysis-2020accord/_scratch/out/_ra6_peak2.json")
